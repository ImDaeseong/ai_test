from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Optional
from urllib.parse import urljoin, urlparse

import httpx
import yt_dlp
from playwright.async_api import async_playwright


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
MEDIA_URL_RE = re.compile(r"\.(m3u8|mp4|ts|m4s|mpd)(\?|$)", re.I)
MEDIA_CONTENT_TYPES = (
    "application/vnd.apple.mpegurl",
    "application/x-mpegurl",
    "application/dash+xml",
    "video/",
    "audio/",
)
ALLOWED_FFMPEG_HEADERS = {"user-agent", "referer", "cookie", "origin"}


ProgressCallback = Callable[[Optional[float], str], None]


@dataclass
class DownloadResult:
    ok: bool
    message: str
    output: Path | None = None
    method: str = ""


class YtdlpLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str) -> None:
        return

    def warning(self, message: str) -> None:
        self.messages.append(message)

    def error(self, message: str) -> None:
        self.messages.append(message)

    def clear(self) -> None:
        self.messages.clear()


def app_dir() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent


def download_dir() -> Path:
    return app_dir() / "downloads"


def ffmpeg_bin() -> str:
    local = app_dir() / "ffmpeg.exe"
    if local.exists():
        return str(local)
    return shutil.which("ffmpeg") or "ffmpeg"


def prepare_env() -> None:
    download_dir().mkdir(parents=True, exist_ok=True)
    local = app_dir() / "ffmpeg.exe"
    if not (local.exists() or shutil.which("ffmpeg")):
        raise RuntimeError(
            "ffmpeg was not found. Put ffmpeg.exe in the project folder "
            "or install it with `winget install ffmpeg`."
        )


def is_valid_http_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def safe_stem(text: str, fallback: str = "video") -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", text)
    cleaned = re.sub(r"_+", "_", cleaned).strip(" ._")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:120] or fallback


def timestamped_output(prefix: str = "video", suffix: str = ".mp4") -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return download_dir() / f"{safe_stem(prefix)}_{stamp}{suffix}"


def output_from_template(output_template: str | Path | None, prefix: str = "video") -> Path:
    if output_template is None:
        return timestamped_output(prefix)
    text = str(output_template)
    if "%(" in text:
        return timestamped_output(prefix)
    path = Path(text)
    if path.suffix:
        return path
    return timestamped_output(prefix)


def filtered_headers(headers: dict, allowed: Iterable[str]) -> dict:
    allowed_lower = {name.lower() for name in allowed}
    return {k: v for k, v in headers.items() if k.lower() in allowed_lower and v}


def classify_media_url(url: str) -> str:
    lower = url.lower()
    if "googlevideo.com/videoplayback" in lower:
        return "YouTube"
    if ".m3u8" in lower:
        return "HLS"
    if ".mpd" in lower:
        return "DASH"
    if ".mp4" in lower:
        return "MP4"
    return "Segment"


async def collect_media_urls(
    page_url: str,
    wait_seconds: int = 8,
    on_found: Callable[[dict], None] | None = None,
) -> list[dict]:
    found: list[dict] = []
    seen: set[str] = set()

    def add_stream(url: str, headers: dict | None = None) -> None:
        if not url or url in seen or url.startswith(("blob:", "data:", "about:")):
            return
        lower = url.lower()
        if not (
            MEDIA_URL_RE.search(url)
            or "googlevideo.com/videoplayback" in lower
            or "mime=video" in lower
            or "mime=audio" in lower
        ):
            return
        seen.add(url)
        stream_headers = dict(headers or {})
        stream_headers.setdefault("referer", page_url)
        stream = {"url": url, "type": classify_media_url(url), "headers": stream_headers}
        found.append(stream)
        if on_found:
            on_found(stream)

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
        except Exception as exc:
            raise RuntimeError(
                "Playwright Chromium is not installed. Run `playwright install chromium`."
            ) from exc

        try:
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()

            def on_request(request) -> None:
                add_stream(request.url, dict(request.headers))

            def on_response(response) -> None:
                content_type = (response.headers.get("content-type") or "").lower()
                if any(kind in content_type for kind in MEDIA_CONTENT_TYPES):
                    add_stream(response.url, {"referer": page_url, "user-agent": USER_AGENT})

            page.on("request", on_request)
            page.on("response", on_response)
            await page.goto(page_url, wait_until="domcontentloaded", timeout=60_000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.evaluate(
                """
                () => {
                    for (const media of document.querySelectorAll('video,audio')) {
                        media.muted = true;
                        const promise = media.play?.();
                        if (promise && promise.catch) promise.catch(() => {});
                    }
                    for (const button of document.querySelectorAll('button,[role=button]')) {
                        const label = (button.innerText || button.ariaLabel || '').toLowerCase();
                        if (/play|재생|시작/.test(label)) button.click();
                    }
                }
                """
            )
            await asyncio.sleep(wait_seconds)
            discovered = await page.evaluate(
                """
                () => {
                    const urls = new Set();
                    for (const el of document.querySelectorAll('video,audio,source,a[href]')) {
                        for (const attr of ['src', 'href']) {
                            const value = el.getAttribute(attr);
                            if (value) {
                                try { urls.add(new URL(value, location.href).href); } catch (_) {}
                            }
                        }
                    }
                    for (const entry of performance.getEntriesByType('resource')) {
                        if (entry.name) urls.add(entry.name);
                    }
                    return Array.from(urls);
                }
                """
            )
            for url in discovered:
                add_stream(url, {"referer": page_url, "user-agent": USER_AGENT})
        finally:
            await browser.close()

    return found


def pick_best_stream(master_m3u8: str, base_url: str) -> str:
    lines = master_m3u8.splitlines()
    streams: list[tuple[int, str]] = []

    for idx, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF"):
            continue

        match = re.search(r"BANDWIDTH=(\d+)", line)
        bandwidth = int(match.group(1)) if match else 0

        for uri_line in lines[idx + 1 :]:
            uri = uri_line.strip()
            if uri and not uri.startswith("#"):
                streams.append((bandwidth, uri))
                break

    if not streams:
        return ""

    _, best_uri = max(streams, key=lambda item: item[0])
    return best_uri if best_uri.startswith(("http://", "https://")) else urljoin(base_url, best_uri)


def resolve_media_url(stream: dict, timeout: int = 15) -> str:
    url = stream["url"]
    if ".m3u8" not in url.lower():
        return url

    headers = filtered_headers(stream.get("headers", {}), ALLOWED_FFMPEG_HEADERS)
    response = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
    response.raise_for_status()

    if "#EXT-X-STREAM-INF" not in response.text:
        return url

    best = pick_best_stream(response.text, url.rsplit("/", 1)[0] + "/")
    return best or url


def seconds_from_ffmpeg_time(value: str) -> float:
    try:
        hours, minutes, seconds = value.split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except ValueError:
        return 0.0


def download_ffmpeg(
    media_url: str,
    headers: dict,
    output_path: Path,
    progress: ProgressCallback | None = None,
) -> DownloadResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    header_str = "\r\n".join(
        f"{k}: {v}" for k, v in filtered_headers(headers, ALLOWED_FFMPEG_HEADERS).items()
    )
    if header_str:
        header_str += "\r\n"

    cmd = [
        ffmpeg_bin(),
        "-y",
        "-headers",
        header_str,
        "-i",
        media_url,
        "-c",
        "copy",
        "-bsf:a",
        "aac_adtstoasc",
        str(output_path),
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        return DownloadResult(False, f"ffmpeg executable was not found: {exc}", output_path, "ffmpeg")
    except Exception as exc:
        return DownloadResult(False, f"Could not start ffmpeg: {exc}", output_path, "ffmpeg")

    duration = 0.0
    logs: list[str] = []
    buffer = ""

    def handle_line(line: str) -> None:
        nonlocal duration
        line = line.strip()
        if not line:
            return
        logs.append(line)

        duration_match = re.search(r"Duration:\s*(\d+:\d+:\d+\.\d+)", line)
        if duration_match:
            duration = seconds_from_ffmpeg_time(duration_match.group(1))

        time_match = re.search(r"\btime=(\d+:\d+:\d+\.\d+)", line)
        if time_match and progress:
            current = seconds_from_ffmpeg_time(time_match.group(1))
            ratio = min(current / duration, 1.0) if duration > 0 else None
            progress(ratio, time_match.group(1))

    if proc.stderr is None:
        proc.kill()
        return DownloadResult(False, "Could not read ffmpeg stderr.", output_path, "ffmpeg")

    while True:
        chunk = proc.stderr.read(4096)
        if not chunk:
            if buffer:
                handle_line(buffer)
            break
        buffer += chunk
        parts = re.split(r"\r|\n", buffer)
        for part in parts[:-1]:
            handle_line(part)
        buffer = parts[-1]

    proc.wait()

    if proc.returncode == 0:
        if progress:
            progress(1.0, "done")
        return DownloadResult(True, output_path.name, output_path, "ffmpeg")

    tail = "\n".join(logs[-20:]) or f"ffmpeg exited with code {proc.returncode}."
    return DownloadResult(False, tail, output_path, "ffmpeg")


def download_ytdlp(
    page_url: str,
    output_template: str | Path | None = None,
    progress_hook: Callable[[dict], None] | None = None,
    quiet: bool = True,
) -> DownloadResult:
    if output_template is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        template = str(download_dir() / f"%(title)s_{stamp}.%(ext)s")
    else:
        template = str(output_template)
    hooks = [progress_hook] if progress_hook else []
    logger = YtdlpLogger()
    base_opts = {
        "outtmpl": template,
        "quiet": quiet,
        "no_warnings": quiet,
        "http_headers": {
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.youtube.com",
            "Referer": page_url,
        },
        "progress_hooks": hooks,
        "logger": logger,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 3,
        "socket_timeout": 30,
        "continuedl": True,
        "concurrent_fragment_downloads": 4,
        "geo_bypass": True,
        "overwrites": False,
    }

    client_attempts = [
        ("default clients", {}),
        ("web client with missing-pot formats", {"youtube": {"player_client": ["web"], "formats": ["missing_pot"]}}),
        ("web safari client", {"youtube": {"player_client": ["web_safari"], "formats": ["missing_pot"]}}),
        ("mobile web client", {"youtube": {"player_client": ["mweb"], "formats": ["missing_pot"]}}),
        ("android client", {"youtube": {"player_client": ["android"]}}),
        ("android vr client", {"youtube": {"player_client": ["android_vr"]}}),
        ("ios client", {"youtube": {"player_client": ["ios"]}}),
        ("tv client", {"youtube": {"player_client": ["tv"]}}),
    ]
    format_attempts = [
        ("bestvideo*+bestaudio/best", "best video + best audio"),
        ("best[ext=mp4]/best", "best single-file MP4-compatible format"),
        ("bv*[height<=1080]+ba/b[height<=1080]/best[height<=1080]/best", "1080p compatible fallback"),
        ("bv*[height<=720]+ba/b[height<=720]/best[height<=720]/best", "720p compatible fallback"),
        ("bv*[height<=480]+ba/b[height<=480]/best[height<=480]/best", "480p compatible fallback"),
        ("worst[ext=mp4]/worst", "lowest compatible fallback"),
    ]

    def _run(run_opts: dict, label: str) -> DownloadResult:
        logger.clear()
        try:
            with yt_dlp.YoutubeDL(run_opts) as ydl:
                info = ydl.extract_info(page_url, download=True)
            title = info.get("title") if isinstance(info, dict) else None
            out: Path | None = None
            if isinstance(info, dict):
                downloads = info.get("requested_downloads") or []
                if downloads and downloads[0].get("filepath"):
                    out = Path(downloads[0]["filepath"])
            message = title or "yt-dlp download completed"
            return DownloadResult(True, f"{message} ({label})", out, "yt-dlp")
        except Exception as exc:
            details = [str(exc), *logger.messages[-5:]]
            return DownloadResult(False, "\n".join(dict.fromkeys(details)), method="yt-dlp")

    failures: list[str] = []
    attempted_opts: list[tuple[dict, str]] = []
    for client_label, extractor_args in client_attempts:
        for format_selector, format_label in format_attempts:
            label = f"{client_label} / {format_label}"
            opts = {**base_opts, "format": format_selector}
            if extractor_args:
                opts["extractor_args"] = extractor_args
            attempted_opts.append((opts, label))
            result = _run(opts, label)
            if result.ok:
                return result
            failures.append(f"{label}: {result.message}")

    direct_result = _download_ytdlp_formats_with_ffmpeg(
        page_url,
        attempted_opts,
        output_from_template(output_template, "ytdlp_direct"),
        progress_hook,
    )
    if direct_result.ok:
        return direct_result
    failures.append(f"direct format URL fallback: {direct_result.message}")

    combined = "\n\n".join(failures[-12:])
    if "403" in combined or "Forbidden" in combined:
        hint = (
            "\n\nHTTP 403 means the server rejected the anonymous download request. "
            "The app tried multiple yt-dlp clients, formats, retries, and direct URL fallback "
            "without storing cookies or history."
        )
        return DownloadResult(False, combined + hint, method="yt-dlp")

    return DownloadResult(False, combined or "yt-dlp download failed.", method="yt-dlp")


def _download_ytdlp_formats_with_ffmpeg(
    page_url: str,
    attempted_opts: list[tuple[dict, str]],
    output_path: Path,
    progress_hook: Callable[[dict], None] | None = None,
) -> DownloadResult:
    failures: list[str] = []
    seen_urls: set[str] = set()

    def progress_bridge(ratio: float | None, _label: str) -> None:
        if not progress_hook:
            return
        if ratio is not None:
            progress_hook({
                "status": "downloading",
                "downloaded_bytes": int(ratio * 1_000_000),
                "total_bytes": 1_000_000,
            })
        else:
            progress_hook({"status": "downloading", "downloaded_bytes": 0, "total_bytes": 0})

    for base_opts, label in attempted_opts[:20]:
        opts = {
            k: v for k, v in base_opts.items()
            if k not in {"progress_hooks", "outtmpl"}
        }
        opts.update({"quiet": True, "no_warnings": True})
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(page_url, download=False)
        except Exception as exc:
            failures.append(f"{label}: extraction failed: {exc}")
            continue

        formats = []
        if isinstance(info, dict):
            formats = info.get("formats") or []
            if info.get("url"):
                formats.append(info)

        ranked = sorted(
            formats,
            key=lambda item: (
                item.get("height") or 0,
                item.get("tbr") or 0,
                item.get("filesize") or item.get("filesize_approx") or 0,
            ),
            reverse=True,
        )
        for fmt in ranked[:12]:
            media_url = fmt.get("url")
            if not media_url or media_url in seen_urls:
                continue
            seen_urls.add(media_url)
            protocol = (fmt.get("protocol") or "").lower()
            if protocol.startswith("mhtml") or media_url.startswith("storyboard"):
                continue

            headers = {
                **(fmt.get("http_headers") or {}),
                "User-Agent": USER_AGENT,
                "Referer": page_url,
            }
            prefix = f"direct_{fmt.get('format_id') or fmt.get('height') or 'video'}"
            candidate_output = output_path if output_path.suffix else timestamped_output(prefix)
            result = download_ffmpeg(media_url, headers, candidate_output, progress=progress_bridge)
            if result.ok:
                return DownloadResult(True, f"ffmpeg direct fallback succeeded ({label})", result.output, "ffmpeg")
            failures.append(f"{label} / format {fmt.get('format_id')}: {result.message.splitlines()[-1] if result.message else 'failed'}")

    return DownloadResult(False, "\n".join(failures[-20:]) or "No direct media formats were usable.", output_path, "ffmpeg")


def download_stream(
    stream: dict,
    output_prefix: str | None = None,
    progress: ProgressCallback | None = None,
) -> DownloadResult:
    if stream.get("type") == "YouTube":
        return DownloadResult(
            False,
            "YouTube media URLs must be downloaded from the original page URL with yt-dlp.",
            method="yt-dlp",
        )

    try:
        final_url = resolve_media_url(stream)
    except Exception as exc:
        final_url = stream["url"]
        if progress:
            progress(None, f"HLS resolution failed, using original URL: {exc}")

    prefix = output_prefix or stream.get("type", "video").lower()
    output_path = timestamped_output(prefix)
    return download_ffmpeg(final_url, stream.get("headers", {}), output_path, progress=progress)
