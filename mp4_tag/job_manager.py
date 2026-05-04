from __future__ import annotations

import threading
import uuid
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from downloader_core import DownloadResult, download_stream, download_ytdlp, timestamped_output


MAX_DOWNLOAD_WORKERS = 3


@dataclass
class DownloadJob:
    id: str
    page_url: str
    stream: dict | None = None
    streams: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    state: str = "queued"
    message: str = "Queued"
    progress: float | None = None
    output: str | None = None
    error: str | None = None
    current_index: int = 0
    total_candidates: int = 1
    attempts: list[str] = field(default_factory=list)


_jobs: dict[str, DownloadJob] = {}
_futures: dict[str, Future] = {}
_lock = threading.RLock()
_executor = ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS, thread_name_prefix="download")


def list_jobs() -> list[DownloadJob]:
    with _lock:
        return sorted(_jobs.values(), key=lambda job: job.created_at, reverse=True)


def get_job(job_id: str) -> DownloadJob | None:
    with _lock:
        return _jobs.get(job_id)


def submit_download(page_url: str, stream: dict) -> str:
    job_id = uuid.uuid4().hex
    job = DownloadJob(id=job_id, page_url=page_url, stream=stream, streams=[stream])
    return _submit_job(job)


def submit_fallback_download(page_url: str, streams: list[dict]) -> str:
    if not streams:
        raise ValueError("At least one stream candidate is required.")
    job_id = uuid.uuid4().hex
    job = DownloadJob(
        id=job_id,
        page_url=page_url,
        stream=streams[0],
        streams=list(streams),
        message=f"Queued fallback download with {len(streams)} candidates",
        total_candidates=len(streams),
    )
    return _submit_job(job)


def _submit_job(job: DownloadJob) -> str:
    with _lock:
        _jobs[job.id] = job

    future = _executor.submit(_run_download_job, job.id)
    with _lock:
        _futures[job.id] = future
    future.add_done_callback(lambda done: _mark_crashed(job.id, done))
    return job.id


def retry_job(job_id: str) -> str | None:
    old = get_job(job_id)
    if old is None:
        return None
    if len(old.streams) > 1:
        return submit_fallback_download(old.page_url, old.streams)
    if old.stream is None:
        return None
    return submit_download(old.page_url, old.stream)


def forget_job(job_id: str) -> None:
    with _lock:
        _jobs.pop(job_id, None)
        future = _futures.pop(job_id, None)
    if future:
        future.cancel()


def active_counts() -> tuple[int, int, int]:
    with _lock:
        queued = sum(1 for job in _jobs.values() if job.state == "queued")
        running = sum(1 for job in _jobs.values() if job.state == "running")
        done = sum(1 for job in _jobs.values() if job.state in {"done", "error", "canceled"})
    return queued, running, done


def _update(job_id: str, **changes) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        for key, value in changes.items():
            setattr(job, key, value)


def _progress_updater(job_id: str, prefix: str) -> Callable[[float | None, str], None]:
    def update(ratio: float | None, label: str) -> None:
        if ratio is None:
            message = f"{prefix}: {label}"
        else:
            message = f"{prefix}: {ratio * 100:.1f}% ({label})"
        _update(job_id, progress=ratio, message=message)

    return update


def _ytdlp_progress_updater(job_id: str, index: int, total: int) -> Callable[[dict], None]:
    def update(data: dict) -> None:
        if data.get("status") == "downloading":
            total_bytes = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes", 0)
            if total_bytes > 0:
                ratio = min(downloaded / total_bytes, 1.0)
                _update(job_id, progress=ratio, message=f"candidate {index + 1}/{total}: yt-dlp {ratio * 100:.1f}%")
            else:
                mb = downloaded / 1024 / 1024
                _update(job_id, progress=None, message=f"candidate {index + 1}/{total}: yt-dlp {mb:.1f} MB")
        elif data.get("status") == "finished":
            _update(job_id, progress=1.0, message=f"candidate {index + 1}/{total}: yt-dlp finished")

    return update


def _try_candidate(job: DownloadJob, stream: dict, index: int, total: int) -> DownloadResult:
    stream_type = stream.get("type", "video")
    _update(
        job.id,
        stream=stream,
        current_index=index,
        total_candidates=total,
        message=f"Trying candidate {index + 1}/{total}: {stream_type}",
        progress=0.0,
    )

    if stream_type == "YouTube":
        return download_ytdlp(
            job.page_url,
            output_template=timestamped_output(f"youtube_{index + 1}", ".%(ext)s"),
            progress_hook=_ytdlp_progress_updater(job.id, index, total),
        )

    return download_stream(
        stream,
        output_prefix=f"{stream_type.lower()}_{index + 1}",
        progress=_progress_updater(job.id, f"candidate {index + 1}/{total}"),
    )


def _run_download_job(job_id: str) -> None:
    job = get_job(job_id)
    if job is None:
        return

    candidates = job.streams or ([job.stream] if job.stream else [])
    if not candidates:
        _update(
            job_id,
            state="error",
            finished_at=datetime.now(),
            progress=0.0,
            message="Download failed",
            error="No stream candidates are available.",
        )
        return

    _update(
        job_id,
        state="running",
        started_at=datetime.now(),
        message=f"Starting download with {len(candidates)} candidate(s)",
        progress=0.0,
        total_candidates=len(candidates),
    )

    errors: list[str] = []
    result: DownloadResult | None = None
    for index, stream in enumerate(candidates):
        result = _try_candidate(job, stream, index, len(candidates))
        if result.ok:
            break
        stream_type = stream.get("type", "video")
        errors.append(f"{index + 1}. {stream_type}: {result.message}")
        _update(job_id, attempts=list(errors), message=f"Candidate {index + 1} failed. Trying next...")

    if result and result.ok:
        _update(
            job_id,
            state="done",
            finished_at=datetime.now(),
            progress=1.0,
            message=f"Saved from candidate {job.current_index + 1}/{len(candidates)}: {result.message}",
            output=str(result.output) if result.output else None,
            error=None,
        )
    else:
        detail = "\n\n".join(errors) if errors else "Download failed before any candidate could run."
        _update(
            job_id,
            state="error",
            finished_at=datetime.now(),
            progress=0.0,
            message="All candidate URLs failed",
            error=detail,
        )


def _mark_crashed(job_id: str, future: Future) -> None:
    try:
        exc = future.exception()
    except CancelledError:
        _update(
            job_id,
            state="canceled",
            finished_at=datetime.now(),
            progress=0.0,
            message="Canceled",
        )
        return

    if exc is None:
        return

    _update(
        job_id,
        state="error",
        finished_at=datetime.now(),
        progress=0.0,
        message="Download worker crashed",
        error=str(exc),
    )
