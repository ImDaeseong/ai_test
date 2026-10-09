"""Stage validated media and render a timeline through the local Remotion project."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


_IMAGE_SUFFIXES = {".jpeg", ".jpg", ".png", ".svg", ".webp"}
_AUDIO_SUFFIXES = {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".wav"}


def _load_timeline(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "2.0":
        raise ValueError("timeline schema_version must be 2.0")
    canvas = data.get("canvas") or {}
    if not all(isinstance(canvas.get(key), int) and canvas[key] > 0 for key in ("width", "height", "fps")):
        raise ValueError("timeline canvas width, height, and fps must be positive integers")
    duration = data.get("audio_duration_ms")
    clips = data.get("clips")
    if not isinstance(duration, int) or duration <= 0 or not isinstance(clips, list) or not clips:
        raise ValueError("timeline requires positive audio_duration_ms and clips")
    cursor = 0
    for clip in clips:
        if clip.get("start_ms") != cursor or clip.get("end_ms", 0) <= cursor:
            raise ValueError(f"timeline gap, overlap, or invalid duration at {clip.get('clip_id', '<unknown>')}")
        if clip.get("duration_ms") != clip["end_ms"] - clip["start_ms"]:
            raise ValueError(f"duration mismatch at {clip.get('clip_id', '<unknown>')}")
        if not clip.get("media_path"):
            raise ValueError(f"missing media_path at {clip.get('clip_id', '<unknown>')}")
        cursor = clip["end_ms"]
    if cursor != duration:
        raise ValueError("timeline end must equal audio_duration_ms")
    return data


def _resolve_input(raw: str, timeline_dir: Path) -> Path:
    candidate = Path(raw)
    resolved = (candidate if candidate.is_absolute() else timeline_dir / candidate).resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"media input is not a file: {resolved}")
    return resolved


def _require_suffix(path: Path, allowed: set[str], kind: str) -> None:
    if path.suffix.lower() not in allowed:
        raise ValueError(f"unsupported {kind} format: {path.suffix or '<none>'}")


def _digest_file(path: Path) -> bytes:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.digest()


def render_timeline(
    timeline_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
    remotion_dir: str | Path,
    *,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    """Render one validated timeline without retaining staged user media."""
    timeline_file = Path(timeline_path).resolve(strict=True)
    audio_file = Path(audio_path).resolve(strict=True)
    output_file = Path(output_path).resolve()
    renderer = Path(remotion_dir).resolve(strict=True)
    if output_file.suffix.lower() != ".mp4":
        raise ValueError("render output must use the .mp4 extension")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    _require_suffix(audio_file, _AUDIO_SUFFIXES, "audio")
    cli = renderer / "node_modules" / ".bin" / ("remotion.cmd" if os.name == "nt" else "remotion")
    entry = renderer / "src" / "index.ts"
    if not cli.is_file() or not entry.is_file():
        raise RuntimeError("Remotion dependencies or src/index.ts are missing; run npm install in remotion/")
    timeline = _load_timeline(timeline_file)
    media_sources = [_resolve_input(str(clip["media_path"]), timeline_file.parent) for clip in timeline["clips"]]
    for source in media_sources:
        _require_suffix(source, _IMAGE_SUFFIXES, "image")
    job_seed = timeline_file.read_bytes() + _digest_file(audio_file)
    for source in media_sources:
        job_seed += _digest_file(source)
    job_id = hashlib.sha256(job_seed).hexdigest()[:12]
    stage = renderer / "public" / "jobs" / job_id
    props_dir = renderer / ".remotion" / "jobs"
    props_file = props_dir / f"{job_id}.json"
    temporary_output = output_file.with_name(f".{output_file.stem}.{job_id}.tmp.mp4")
    stage.mkdir(parents=True, exist_ok=False)
    props_dir.mkdir(parents=True, exist_ok=True)
    try:
        staged_clips: list[dict[str, Any]] = []
        for index, (clip, source) in enumerate(zip(timeline["clips"], media_sources, strict=True), start=1):
            target_name = f"clip-{index:04d}{source.suffix.lower()}"
            shutil.copy2(source, stage / target_name)
            staged_clips.append({**clip, "media_path": f"jobs/{job_id}/{target_name}"})
        audio_target = f"audio{audio_file.suffix.lower()}"
        shutil.copy2(audio_file, stage / audio_target)
        props = {"timeline": {**timeline, "clips": staged_clips, "audio_path": f"jobs/{job_id}/{audio_target}"}}
        props_file.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        temporary_output.unlink(missing_ok=True)
        command = [str(cli), "render", str(entry), "WebtoonVideo", str(temporary_output), f"--props={props_file}", "--codec=h264", "--crf=23"]
        completed = subprocess.run(command, cwd=renderer, capture_output=True, text=True, timeout=timeout_seconds, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"Remotion render failed ({completed.returncode}): {completed.stderr[-2000:]}")
        if not temporary_output.is_file() or temporary_output.stat().st_size == 0:
            raise RuntimeError("Remotion reported success without a non-empty MP4")
        os.replace(temporary_output, output_file)
        return {"output": str(output_file), "bytes": output_file.stat().st_size, "job_id": job_id}
    finally:
        shutil.rmtree(stage, ignore_errors=True)
        props_file.unlink(missing_ok=True)
        temporary_output.unlink(missing_ok=True)
