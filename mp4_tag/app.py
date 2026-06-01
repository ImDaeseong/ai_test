from __future__ import annotations

import asyncio
import sys
import time

import streamlit as st

from downloader_core import (
    collect_media_urls as collect_media_urls_async,
    download_dir,
    is_valid_http_url,
    prepare_env,
)
from job_manager import (
    MAX_DOWNLOAD_WORKERS,
    active_counts,
    forget_job,
    get_job,
    retry_job,
    submit_fallback_download,
    submit_download,
)
from server_limits import MAX_ANALYZE_WORKERS, analysis_slot


def run_async(coro):
    if sys.platform == "win32" and hasattr(asyncio, "ProactorEventLoop"):
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()

    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        asyncio.set_event_loop(None)
        loop.close()


def collect_media_urls(url: str) -> list[dict]:
    return run_async(collect_media_urls_async(url, wait_seconds=6))


def rerun() -> None:
    st.rerun()


def show_progress(value: float, text: str) -> None:
    st.progress(value)
    if text:
        st.caption(text)


def ensure_state() -> None:
    defaults = {
        "streams": [],
        "page_url": "",
        "job_by_stream": {},
        "fallback_job_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def show_job_status(job_id: str, stream_index: int | None = None) -> None:
    job = get_job(job_id)
    if job is None:
        st.info("Job information is no longer available.")
        return

    if job.state == "queued":
        st.info(job.message)
        show_progress(0, "Queued")
    elif job.state == "running":
        value = job.progress if job.progress is not None else 0
        show_progress(value, job.message)
        if job.total_candidates > 1:
            st.caption(f"Candidate {job.current_index + 1} of {job.total_candidates}")
    elif job.state == "done":
        st.success(f"Download completed: `{job.message}`")
        st.caption(f"Saved to: {job.output or download_dir().resolve()}")
    elif job.state == "canceled":
        st.warning("Job was canceled.")
    else:
        st.error("Download failed")
        st.text_area(
            "Error details",
            value=job.error or job.message,
            height=140,
            disabled=True,
            key=f"err_{job_id}",
        )

    col_retry, col_forget = st.columns([1, 1])
    with col_retry:
        if job.state in {"done", "error", "canceled"} and st.button("Retry", key=f"retry_{job_id}"):
            new_job_id = retry_job(job_id)
            if new_job_id:
                if stream_index is None:
                    st.session_state["fallback_job_id"] = new_job_id
                else:
                    st.session_state["job_by_stream"][stream_index] = new_job_id
            rerun()
    with col_forget:
        if job.state in {"done", "error", "canceled"} and st.button("Remove", key=f"forget_{job_id}"):
            forget_job(job_id)
            if stream_index is None:
                st.session_state["fallback_job_id"] = None
            else:
                st.session_state["job_by_stream"].pop(stream_index, None)
            rerun()


st.set_page_config(page_title="Video Downloader", layout="wide")
st.title("Video Downloader")
ensure_state()

try:
    prepare_env()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

queued, running, finished = active_counts()
target_dir = download_dir()
st.caption(
    f"Analysis limit: {MAX_ANALYZE_WORKERS} | Download workers: {MAX_DOWNLOAD_WORKERS} "
    f"| Running: {running} | Queued: {queued} | Finished/failed: {finished}"
)

col_url, col_btn, col_fallback, col_queue, col_refresh = st.columns([5, 1, 1.2, 1, 1])
with col_url:
    url_input = st.text_input(
        "URL",
        value=st.session_state["page_url"],
        placeholder="https://example.com/video",
    )
with col_btn:
    analyze_clicked = st.button("Analyze")
with col_queue:
    queue_all_clicked = st.button("Queue all", disabled=not st.session_state["streams"])
with col_fallback:
    fallback_clicked = st.button("Fallback", disabled=not st.session_state["streams"])
with col_refresh:
    if st.button("Refresh"):
        rerun()

if analyze_clicked:
    url = url_input.strip()
    if not url:
        st.warning("Enter a URL.")
    elif not is_valid_http_url(url):
        st.warning("Enter a URL that starts with http:// or https://.")
    else:
        st.session_state["page_url"] = url
        st.session_state["job_by_stream"] = {}
        st.session_state["fallback_job_id"] = None
        st.session_state["streams"] = []
        with analysis_slot() as acquired:
            if not acquired:
                st.warning("Too many analysis jobs are running. Try again shortly.")
            else:
                with st.spinner("Analyzing page network requests..."):
                    try:
                        st.session_state["streams"] = collect_media_urls(url)
                    except Exception as exc:
                        st.error(f"Could not collect media URLs: {exc}")
                if not st.session_state["streams"]:
                    st.warning("No media streams were detected. Try a different URL.")

if queue_all_clicked:
    page_url = st.session_state["page_url"]
    for index, stream in enumerate(st.session_state["streams"]):
        if index not in st.session_state["job_by_stream"]:
            st.session_state["job_by_stream"][index] = submit_download(page_url, stream)
    rerun()

if fallback_clicked:
    st.session_state["fallback_job_id"] = submit_fallback_download(
        st.session_state["page_url"],
        st.session_state["streams"],
    )
    rerun()

streams: list[dict] = st.session_state["streams"]
page_url: str = st.session_state["page_url"]

if streams:
    st.markdown(f"**Detected streams: {len(streams)}**")

fallback_job_id = st.session_state["fallback_job_id"]
if fallback_job_id:
    st.subheader("Fallback Download")
    show_job_status(fallback_job_id)

for index, stream in enumerate(streams):
    job_id = st.session_state["job_by_stream"].get(index)
    title = f"{index + 1}. [{stream['type']}] {stream['url'][:100]}"

    with st.expander(title, expanded=(index == 0)):
        st.code(stream["url"], language=None)

        if job_id:
            show_job_status(job_id, index)
        elif st.button("Add to download queue", key=f"dl_{index}"):
            st.session_state["job_by_stream"][index] = submit_download(page_url, stream)
            rerun()

st.markdown("---")
st.caption(f"Python {sys.version.split()[0]} | yt-dlp | Playwright | FFmpeg | Download folder: {target_dir.resolve()}")

if running + queued > 0:
    time.sleep(2)
    st.rerun()
