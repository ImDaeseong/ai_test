from __future__ import annotations

import argparse
import asyncio
import os
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

from downloader_core import (
    DownloadResult,
    collect_media_urls,
    download_stream,
    download_ytdlp,
    is_valid_http_url,
    prepare_env,
    timestamped_output,
)


@dataclass
class SelectedStream:
    number: int
    stream: dict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the web downloader UI, or pass a URL to use CLI mode."
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Page URL to download in CLI mode. If omitted, the web UI starts.",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=3,
        help="Maximum parallel fallback downloads. Default: 3.",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=8,
        help="Seconds to watch browser network requests. Default: 8.",
    )
    parser.add_argument(
        "--skip-ytdlp-first",
        action="store_true",
        help="Skip the initial direct yt-dlp attempt and analyze media requests immediately.",
    )
    return parser.parse_args()


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


def run_web_ui() -> None:
    import streamlit.web.cli as stcli

    app_path = resource_path("app.py")
    if not Path(app_path).exists():
        print(f"[error] Web app file was not found: {app_path}")
        return

    print("Starting web UI...")
    print("If the browser does not open automatically, visit http://localhost:8501")
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())


def parse_selection(raw: str, total: int) -> list[int]:
    raw = raw.strip().lower()
    if raw in {"all", "a", "*"}:
        return list(range(1, total + 1))

    selected: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            try:
                start = int(start_text)
                end = int(end_text)
            except ValueError:
                raise ValueError(f"Invalid range '{part}'. Expected format: start-end (e.g. 1-3)")
            if start > end:
                start, end = end, start
            selected.update(range(start, end + 1))
        else:
            try:
                selected.add(int(part))
            except ValueError:
                raise ValueError(f"Invalid number '{part}'. Expected a number, range, or 'all'")

    invalid = [item for item in selected if item < 1 or item > total]
    if invalid:
        raise ValueError(f"Out of range: {invalid}")
    return sorted(selected)


def print_streams(streams: list[dict]) -> None:
    print("\n" + "=" * 100)
    for index, stream in enumerate(streams, 1):
        print(f"{index:<4} | {stream['type']:<8} | {stream['url'][:110]}")
    print("=" * 100)


async def run_ytdlp_first(page_url: str) -> bool:
    print("\n[1/4] Trying yt-dlp direct download first...")
    result = await asyncio.to_thread(
        download_ytdlp,
        page_url,
        None,
        None,
        True,
    )
    if result.ok:
        location = f" ({result.output.resolve()})" if result.output else ""
        print(f"[done] yt-dlp succeeded: {result.message}{location}")
        return True

    print(f"[info] yt-dlp direct download failed: {result.message}")
    return False


async def download_one(
    page_url: str,
    selected: SelectedStream,
    semaphore: asyncio.Semaphore,
    print_lock: threading.Lock,
) -> DownloadResult:
    stream = selected.stream

    async with semaphore:
        def progress(ratio: float | None, label: str) -> None:
            if ratio is None:
                text = f"[{selected.number}] working... {label}"
            else:
                text = f"[{selected.number}] {ratio * 100:5.1f}% ({label})"
            with print_lock:
                print(text)

        with print_lock:
            method = "yt-dlp" if stream["type"] == "YouTube" else "ffmpeg"
            print(f"[start] #{selected.number} {stream['type']} -> {method}")

        if stream["type"] == "YouTube":
            result = await asyncio.to_thread(
                download_ytdlp,
                page_url,
                timestamped_output(f"youtube_{selected.number}", ".%(ext)s"),
                None,
                True,
            )
        else:
            result = await asyncio.to_thread(
                download_stream,
                stream,
                f"{stream['type'].lower()}_{selected.number}",
                progress,
            )

        with print_lock:
            if result.ok:
                location = result.output.resolve() if result.output else "unknown"
                print(f"[done] #{selected.number} saved: {location}")
            else:
                print(f"[fail] #{selected.number} {result.method or 'download'} failed")
                print(result.message)
        return result


async def main(
    page_url: str,
    workers: int = 3,
    wait_seconds: int = 8,
    skip_ytdlp_first: bool = False,
) -> None:
    try:
        prepare_env()
    except RuntimeError as exc:
        print(f"[environment error] {exc}")
        return

    if not skip_ytdlp_first and await run_ytdlp_first(page_url):
        return

    print(f"\n[2/4] Analyzing browser network requests for media URLs: {page_url}")
    try:
        streams = await collect_media_urls(
            page_url,
            wait_seconds=wait_seconds,
            on_found=lambda stream: print(f"  found {stream['type']}: {stream['url'][:90]}"),
        )
    except Exception as exc:
        print(f"[analysis error] {exc}")
        return

    if not streams:
        print("[no result] Could not find downloadable media URLs.")
        return

    print_streams(streams)
    choice = input("\nDownload number(s), e.g. 1 or 1,3,5-7 or all. Press Enter to cancel: ").strip()
    if not choice:
        print("Canceled.")
        return

    try:
        selected_numbers = parse_selection(choice, len(streams))
    except ValueError as exc:
        print(f"[input error] {exc}")
        return

    selected = [SelectedStream(number, streams[number - 1]) for number in selected_numbers]
    max_workers = max(1, min(workers, len(selected)))

    print(f"\n[3/4] Starting {len(selected)} download(s) with {max_workers} worker(s)...")
    semaphore = asyncio.Semaphore(max_workers)
    print_lock = threading.Lock()
    results = await asyncio.gather(
        *(download_one(page_url, item, semaphore, print_lock) for item in selected),
        return_exceptions=True,
    )

    print("\n[4/4] Summary")
    ok_count = 0
    for item, result in zip(selected, results):
        if isinstance(result, Exception):
            print(f"  #{item.number}: crashed - {result}")
            continue
        if result.ok:
            ok_count += 1
            print(f"  #{item.number}: ok - {result.output.resolve() if result.output else result.message}")
        else:
            print(f"  #{item.number}: failed - {result.message.splitlines()[-1] if result.message else 'unknown error'}")

    print(f"\nCompleted: {ok_count}/{len(selected)}")


if __name__ == "__main__":
    args = parse_args()
    if not args.url:
        run_web_ui()
    elif not is_valid_http_url(args.url):
        print("Enter a URL that starts with http:// or https://.")
    else:
        asyncio.run(
            main(
                args.url,
                workers=args.workers,
                wait_seconds=args.wait,
                skip_ytdlp_first=args.skip_ytdlp_first,
            )
        )
