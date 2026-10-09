"""Create a path-safe editor handoff bundle from a completed render."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _sanitize_path_fields(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if key.endswith("_path") and isinstance(item, str):
                name = Path(item).name
                sanitized[key] = f"source-media-not-included/{name}" if name else ""
            else:
                sanitized[key] = _sanitize_path_fields(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_path_fields(item) for item in value]
    return value

def create_editor_handoff(
    video_path: str | Path,
    timeline_path: str | Path,
    output_dir: str | Path,
    *,
    subtitles_path: str | Path | None = None,
) -> dict[str, Any]:
    """Create an atomic, portable bundle without retaining source paths."""
    video = Path(video_path).resolve(strict=True)
    timeline_file = Path(timeline_path).resolve(strict=True)
    destination = Path(output_dir).resolve()
    if video.suffix.lower() != ".mp4":
        raise ValueError("handoff video must use the .mp4 extension")
    if destination.exists():
        raise FileExistsError(f"handoff destination already exists: {destination}")
    timeline = json.loads(timeline_file.read_text(encoding="utf-8"))
    clips = timeline.get("clips")
    if not isinstance(clips, list) or not clips:
        raise ValueError("timeline requires a non-empty clips list")
    for clip in clips:
        if not Path(str(clip.get("media_path", ""))).name:
            raise ValueError("every timeline clip requires media_path")
    sanitized_timeline = _sanitize_path_fields(timeline)

    subtitles = Path(subtitles_path).resolve(strict=True) if subtitles_path else None
    if subtitles and subtitles.suffix.lower() != ".srt":
        raise ValueError("handoff subtitles must use the .srt extension")

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        video_target = staging / "video.mp4"
        timeline_target = staging / "timeline.json"
        shutil.copy2(video, video_target)
        timeline_target.write_text(
            json.dumps(sanitized_timeline, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        files = [
            {"path": "video.mp4", "sha256": _sha256(video_target)},
            {"path": "timeline.json", "sha256": _sha256(timeline_target)},
        ]
        if subtitles:
            subtitle_target = staging / "subtitles.srt"
            shutil.copy2(subtitles, subtitle_target)
            files.append({"path": "subtitles.srt", "sha256": _sha256(subtitle_target)})
        readme_target = staging / "README.txt"
        readme_target.write_text(
            "편집기 전달 묶음\n\n"
            "1. video.mp4를 CapCut 또는 다른 편집기에 가져옵니다.\n"
            "2. subtitles.srt가 있으면 자막으로 가져옵니다.\n"
            "3. timeline.json은 편집 판단을 확인하는 참고 자료입니다.\n"
            "4. manifest.json의 사람 검토 항목을 모두 확인하기 전에는 출시하지 않습니다.\n"
            "이 묶음은 CapCut 전용 프로젝트 파일이 아닙니다.\n",
            encoding="utf-8",
        )
        files.append({"path": "README.txt", "sha256": _sha256(readme_target)})
        manifest = {
            "schema_version": "1.0",
            "bundle_type": "generic-editor-handoff",
            "native_capcut_project": False,
            "review_status": "HOLD",
            "files": files,
            "required_human_review": [
                "music_sync",
                "crop_and_safe_area",
                "subtitle_readability",
                "media_rights",
                "final_edit_quality",
            ],
        }
        manifest_target = staging / "manifest.json"
        manifest_target.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(staging, destination)
        return {
            "output": str(destination),
            "files": len(files) + 1,
            "review_status": "HOLD",
        }
    finally:
        shutil.rmtree(staging, ignore_errors=True)

def verify_editor_handoff(bundle_dir: str | Path) -> dict[str, Any]:
    """Verify bundle membership, path containment, and recorded hashes."""
    bundle = Path(bundle_dir).resolve(strict=True)
    if not bundle.is_dir():
        raise ValueError(f"handoff bundle is not a directory: {bundle}")
    manifest_file = bundle / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "1.0":
        raise ValueError("unsupported handoff manifest schema_version")
    if manifest.get("bundle_type") != "generic-editor-handoff":
        raise ValueError("unsupported handoff bundle_type")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise ValueError("handoff manifest requires a non-empty files list")

    expected = {"manifest.json"}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("handoff manifest file entries must be objects")
        relative = entry.get("path")
        recorded_hash = entry.get("sha256")
        if (
            not isinstance(relative, str)
            or not relative
            or Path(relative).is_absolute()
            or "/" in relative
            or "\\" in relative
            or relative in {".", ".."}
        ):
            raise ValueError(f"unsafe handoff path: {relative!r}")
        if relative in expected:
            raise ValueError(f"duplicate handoff path: {relative}")
        candidate = bundle / relative
        if not candidate.exists():
            raise ValueError(f"handoff file missing: {relative}")
        target = candidate.resolve(strict=True)
        try:
            target.relative_to(bundle)
        except ValueError as exc:
            raise ValueError(f"handoff path escapes bundle: {relative}") from exc
        if not target.is_file():
            raise ValueError(f"handoff entry is not a file: {relative}")
        if not isinstance(recorded_hash, str) or _sha256(target) != recorded_hash:
            raise ValueError(f"handoff hash mismatch: {relative}")
        expected.add(relative)

    actual = {item.name for item in bundle.iterdir()}
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"handoff membership mismatch: missing={missing}, extra={extra}")
    return {
        "bundle": str(bundle),
        "integrity_status": "PASS",
        "review_status": manifest.get("review_status", "HOLD"),
        "files": len(actual),
    }
