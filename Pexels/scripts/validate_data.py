from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.request import GenerateVideoRequest
from app.services.pipeline_service import VideoPipeline


DATA_DIR = Path("data")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate local data files and optionally run an E2E smoke render.")
    parser.add_argument("--smoke", action="store_true", help="Run Gemini/Pexels/FFmpeg smoke render using data lyrics.")
    parser.add_argument("--output", default="storage/output/data_smoke.mp4", help="Smoke render output path.")
    args = parser.parse_args()

    validate_env(require_api_keys=args.smoke)
    validate_data_dir()
    validate_subtitles()
    validate_media_files()
    run_tests()

    if args.smoke:
        run_smoke_render(args.output)

    print("DATA_VALIDATION_OK")
    return 0


def validate_env(require_api_keys: bool = False) -> None:
    values = dotenv_values(".env")
    missing = [
        key
        for key in ["GEMINI_API_KEY", "PEXELS_API_KEY"]
        if not values.get(key) or str(values.get(key)).startswith("your_")
    ]
    if missing and require_api_keys:
        raise RuntimeError(f"Missing required .env values: {', '.join(missing)}")
    if missing:
        print(f"env: API keys missing for optional smoke render: {', '.join(missing)}")
    else:
        print("env: GEMINI_API_KEY=SET, PEXELS_API_KEY=SET")


def validate_data_dir() -> None:
    if not DATA_DIR.exists():
        raise RuntimeError("data directory does not exist.")
    files = sorted(path for path in DATA_DIR.iterdir() if path.is_file())
    if not files:
        raise RuntimeError("data directory is empty.")
    print(f"data files: {len(files)}")
    for path in files:
        print(f"  {path.name} ({path.stat().st_size} bytes)")


def validate_subtitles() -> None:
    lrc_files = sorted(DATA_DIR.glob("*.lrc"))
    srt_files = sorted(DATA_DIR.glob("*.srt"))
    if not lrc_files and not srt_files:
        raise RuntimeError("No .lrc or .srt file found in data directory.")

    for path in lrc_files:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        timed_lines = [line for line in text.splitlines() if re.search(r"\[\d{2}:\d{2}\.\d{2}\]", line)]
        print(f"lrc: {path.name}, timed_lines={len(timed_lines)}, chars={len(text)}")

    for path in srt_files:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        cue_count = len(re.findall(r"\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}", text))
        print(f"srt: {path.name}, cues={cue_count}, chars={len(text)}")


def validate_media_files() -> None:
    media_files = [
        path
        for pattern in ["*.wav", "*.mp3", "*.png", "*.jpg", "*.jpeg"]
        for path in DATA_DIR.glob(pattern)
    ]
    if not media_files:
        print("media: no audio/image files found")
        return

    for path in sorted(media_files):
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size,format_name:stream=codec_name,width,height,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
        payload = json.loads(result.stdout)
        fmt = payload.get("format", {})
        streams = payload.get("streams", [])
        first = streams[0] if streams else {}
        print(
            "media:"
            f" {path.name}, format={fmt.get('format_name')}, duration={fmt.get('duration')},"
            f" codec={first.get('codec_name')}, size={fmt.get('size')},"
            f" width={first.get('width')}, height={first.get('height')},"
            f" sample_rate={first.get('sample_rate')}, channels={first.get('channels')}"
        )


def run_tests() -> None:
    subprocess.run([sys.executable, "-m", "pytest"], check=True)


def run_smoke_render(output: str) -> None:
    text = extract_smoke_text()
    print("smoke input:")
    print(text)
    result = VideoPipeline().generate(
        GenerateVideoRequest(
            text=text,
            orientation="portrait",
            style="cinematic music video",
            output_path=output,
        )
    )
    print(f"smoke status: {result.status}")
    print(f"smoke project_id: {result.project_id}")
    print(f"smoke scenes: {len(result.scenes)}")
    print(f"smoke output: {result.output_file}")


def extract_smoke_text() -> str:
    lrc_files = sorted(DATA_DIR.glob("*.lrc"))
    if lrc_files:
        raw = lrc_files[0].read_text(encoding="utf-8-sig", errors="replace")
        lines: list[str] = []
        for line in raw.splitlines():
            clean = re.sub(r"\[[^\]]*\]", "", line).strip()
            if clean and not clean.lower().startswith("instrumental"):
                lines.append(clean)
            if len(lines) >= 4:
                break
        if lines:
            return "\n".join(lines)

    srt_files = sorted(DATA_DIR.glob("*.srt"))
    if srt_files:
        raw = srt_files[0].read_text(encoding="utf-8-sig", errors="replace")
        lines = [
            line.strip()
            for line in raw.splitlines()
            if line.strip()
            and not line.strip().isdigit()
            and "-->" not in line
        ]
        if lines:
            return "\n".join(lines[:4])

    raise RuntimeError("Could not extract smoke text from .lrc or .srt files.")


if __name__ == "__main__":
    raise SystemExit(main())
