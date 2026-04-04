import asyncio
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

# 실행 파일(.exe) 위치 기준 경로 계산 (PyInstaller 환경 대응)
_EXE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
_LOCAL_FFMPEG = _EXE_DIR / "ffmpeg.exe"
FFMPEG_BIN = str(_LOCAL_FFMPEG) if _LOCAL_FFMPEG.exists() else (shutil.which("ffmpeg") or "ffmpeg")

import httpx
import streamlit as st
import yt_dlp
from playwright.async_api import async_playwright

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
DOWNLOAD_DIR = _EXE_DIR / "downloads"


# ──────────────────────────────────────────────
# ENV CHECK
# ──────────────────────────────────────────────
def prepare_env():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not (_LOCAL_FFMPEG.exists() or shutil.which("ffmpeg")):
        return "ffmpeg.exe가 없습니다. 프로젝트 폴더에 ffmpeg.exe를 복사하거나 winget install ffmpeg 실행 필요"
    return None


# ──────────────────────────────────────────────
# ASYNC RUNNER (Windows ProactorEventLoop)
# ──────────────────────────────────────────────
def run_async(coro):
    loop = asyncio.ProactorEventLoop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    except Exception as e:
        st.error(f"Async 실행 실패: {e}")
        return []
    finally:
        loop.close()


# ──────────────────────────────────────────────
# PLAYWRIGHT — 미디어 URL 수집
# ──────────────────────────────────────────────
async def _collect_media_urls(page_url: str) -> list:
    found = []
    seen: set = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            ctx = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = await ctx.new_page()

            async def on_request(request):
                url = request.url
                if url in seen:
                    return
                if (
                    re.search(r"\.(m3u8|mp4|ts)(\?|$)", url, re.I)
                    or "googlevideo.com/videoplayback" in url
                ):
                    seen.add(url)
                    headers = dict(request.headers)
                    headers.setdefault("referer", page_url)

                    if "googlevideo" in url:
                        stype = "YouTube"
                    elif ".m3u8" in url.lower():
                        stype = "HLS"
                    else:
                        stype = "MP4"

                    found.append({"url": url, "type": stype, "headers": headers})

            page.on("request", on_request)
            await page.goto(page_url, wait_until="domcontentloaded", timeout=60_000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(6)

        except Exception as e:
            st.error(f"Playwright 오류: {e}")
        finally:
            await browser.close()

    return found


def collect_media_urls(url: str) -> list:
    return run_async(_collect_media_urls(url))


# ──────────────────────────────────────────────
# HLS — 최고 화질 스트림 선택
# ──────────────────────────────────────────────
def pick_best_stream(text: str, base: str) -> str:
    lines = text.splitlines()
    streams = []

    for i, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF"):
            bw = 0
            m = re.search(r"BANDWIDTH=(\d+)", line)
            if m:
                bw = int(m.group(1))
            for j in range(i + 1, len(lines)):
                uri = lines[j].strip()
                if uri and not uri.startswith("#"):
                    streams.append((bw, uri))
                    break

    if not streams:
        return ""
    _, best = max(streams, key=lambda x: x[0])
    return best if best.startswith("http") else urljoin(base, best)


def resolve_url(stream: dict) -> str:
    url = stream["url"]
    if ".m3u8" not in url.lower():
        return url

    hdrs = {
        k: v for k, v in stream["headers"].items()
        if k.lower() in ("referer", "cookie")
    }
    try:
        r = httpx.get(url, headers=hdrs, timeout=15)
        if "#EXT-X-STREAM-INF" in r.text:
            return pick_best_stream(r.text, url.rsplit("/", 1)[0] + "/")
    except Exception:
        pass
    return url


# ──────────────────────────────────────────────
# FFMPEG — 다운로드 (실시간 진행률 표시)
# ──────────────────────────────────────────────
def _to_sec(t: str) -> float:
    try:
        h, m, s = t.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        return 0.0


def download_ffmpeg(url: str, headers: dict, output: Path, progress_bar=None):
    allowed = ("user-agent", "referer", "cookie", "origin")
    hdr_str = "\r\n".join(
        f"{k}: {v}" for k, v in headers.items() if k.lower() in allowed
    ) + "\r\n"

    cmd = [
        FFMPEG_BIN, "-y",
        "-headers", hdr_str,
        "-i", url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        str(output),
    ]

    proc = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    duration = 0.0
    lines_log: list = []
    char_buf = ""

    def handle_line(line: str):
        nonlocal duration
        line = line.strip()
        if not line:
            return
        lines_log.append(line)

        # 총 길이 파싱 (초반 메타데이터에서)
        m = re.search(r"Duration:\s*(\d+:\d+:\d+\.\d+)", line)
        if m:
            duration = _to_sec(m.group(1))

        # 현재 처리 시간 파싱 → 진행률 계산
        m = re.search(r"\btime=(\d+:\d+:\d+\.\d+)", line)
        if m and progress_bar is not None:
            current = _to_sec(m.group(1))
            if duration > 0:
                pct = min(current / duration, 1.0)
                progress_bar.progress(
                    pct,
                    text=f"다운로드 중... {pct * 100:.1f}%  ({m.group(1)} / {duration:.0f}s)",
                )
            else:
                progress_bar.progress(0, text=f"다운로드 중... {m.group(1)}")

    # ffmpeg는 \r 과 \n 혼용 → 문자 단위 읽기
    while True:
        ch = proc.stderr.read(1)
        if not ch:
            if char_buf:
                handle_line(char_buf)
            break
        if ch in ("\r", "\n"):
            if char_buf:
                handle_line(char_buf)
                char_buf = ""
        else:
            char_buf += ch

    proc.wait()

    if proc.returncode == 0:
        if progress_bar is not None:
            progress_bar.progress(1.0, text="✅ 다운로드 완료!")
        return True, output.name

    return False, "\n".join(lines_log[-15:])


# ──────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────
st.set_page_config(page_title="🎬 Video Downloader", layout="wide")
st.title("🎬 Video Downloader")

# 세션 상태 초기화
for _key, _default in [("streams", []), ("dl_status", {}), ("page_url", "")]:
    if _key not in st.session_state:
        st.session_state[_key] = _default

env_err = prepare_env()
if env_err:
    st.error(env_err)
    st.stop()

# ── URL 입력 + 분석 버튼 ──
col_url, col_btn = st.columns([6, 1])
with col_url:
    url_input = st.text_input(
        "URL",
        placeholder="https://example.com/video",
        label_visibility="collapsed",
    )
with col_btn:
    analyze_clicked = st.button("🔍 분석")

if analyze_clicked:
    u = url_input.strip()
    if not u:
        st.warning("URL을 입력해 주세요.")
    elif not u.startswith(("http://", "https://")):
        st.warning("http:// 또는 https://로 시작하는 올바른 URL을 입력해 주세요.")
    else:
        st.session_state.page_url = u
        st.session_state.dl_status = {}
        st.session_state.streams = []
        with st.spinner("🔎 페이지 분석 중... (최대 60초 소요)"):
            st.session_state.streams = collect_media_urls(u)
        if not st.session_state.streams:
            st.warning("⚠️ 감지된 미디어 스트림이 없습니다. 다른 URL을 시도해 주세요.")

# ── 스트림 목록 표시 ──
streams: list = st.session_state.streams
page_url: str = st.session_state.page_url

if streams:
    st.markdown(f"**발견된 스트림: {len(streams)}개**")

if "dl_status" not in st.session_state:
    st.session_state["dl_status"] = {}

for i, s in enumerate(streams):
    status = st.session_state["dl_status"].get(i)

    with st.expander(f"{i + 1}. [{s['type']}]  {s['url'][:100]}", expanded=(i == 0)):
        st.code(s["url"], language=None)

        if status is None:
            # 다운로드 대기 상태
            if st.button("⬇️ 다운로드", key=f"dl_{i}"):
                ts = datetime.now().strftime("%H%M%S")
                out = DOWNLOAD_DIR / f"video_{ts}.mp4"

                prog_ydl = st.progress(0, text="⏳ 다운로드 준비 중... (yt-dlp)")
                ydl_ok = False

                def _ydl_hook(d):
                    if d.get("status") == "downloading":
                        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                        downloaded = d.get("downloaded_bytes", 0)
                        speed = d.get("_speed_str", "").strip() or "?"
                        eta = d.get("_eta_str", "").strip() or "?"
                        if total > 0:
                            pct = min(downloaded / total, 1.0)
                            prog_ydl.progress(pct, text=f"다운로드 중... {pct*100:.1f}%  |  속도: {speed}  |  남은 시간: {eta}")
                        else:
                            mb = downloaded / 1024 / 1024
                            prog_ydl.progress(0, text=f"다운로드 중... {mb:.1f} MB  |  속도: {speed}")
                    elif d.get("status") == "finished":
                        prog_ydl.progress(1.0, text="✅ 다운로드 완료!")

                try:
                    with yt_dlp.YoutubeDL({
                        "outtmpl": str(DOWNLOAD_DIR / f"yt_{ts}.%(ext)s"),
                        "quiet": True,
                        "no_warnings": True,
                        "progress_hooks": [_ydl_hook],
                        "http_headers": {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        },
                    }) as ydl:
                        ydl.download([page_url])
                    ydl_ok = True
                    st.session_state["dl_status"][i] = {
                        "state": "done",
                        "message": f"yt_{ts}.*",
                    }
                except Exception:
                    pass

                if not ydl_ok:
                    prog_ydl.progress(0, text="⏳ yt-dlp 미지원 사이트, ffmpeg로 직접 다운로드 중...")
                    prog = st.progress(0, text="⏳ 다운로드 준비 중...")
                    target = resolve_url(s) if s["type"] == "HLS" else s["url"]
                    ok, msg = download_ffmpeg(target, s["headers"], out, progress_bar=prog)
                    if ok:
                        st.session_state.dl_status[i] = {"state": "done", "message": msg}
                    else:
                        st.session_state.dl_status[i] = {"state": "error", "message": msg}

                st.rerun()

        elif status["state"] == "done":
            # 완료 상태
            st.success(f"✅ 다운로드 완료: `{status['message']}`")
            st.caption(f"📁 저장 위치: {DOWNLOAD_DIR.resolve()}")
            if st.button("🔄 다시 받기", key=f"redo_{i}"):
                del st.session_state.dl_status[i]
                st.rerun()

        else:
            # 실패 상태
            st.error("❌ 다운로드 실패")
            st.text_area("오류 상세 내용", value=status["message"], height=100, disabled=True, key=f"err_{i}")
            if st.button("🔄 재시도", key=f"retry_{i}"):
                del st.session_state.dl_status[i]
                st.rerun()

st.markdown("---")
st.caption(
    f"Python {sys.version.split()[0]} · yt-dlp · Playwright · FFmpeg"
    f" | 다운로드 폴더: {DOWNLOAD_DIR.resolve()}"
)
