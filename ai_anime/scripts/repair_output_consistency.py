from __future__ import annotations

import argparse
import re
from pathlib import Path

import output_docs
from common import PROJECT_ROOT, read_text


SKIP_OUTPUT_DIRS = {"images", "storyboard", "videos", "web_inputs"}
PROMPT_FOLDERS = ("image_prompts", "video_prompts", "video_clip_prompts")
TITLE_LOCK_PREFIX = "Song identity lock:"
REFERENCE_LABELS = ("wide", "action", "emotion", "detail")
CLIP_ROLES = (
    "opening clip: establish the location, subject silhouette, palette, and motif",
    "action clip: continue the main subject movement while preserving the approved design",
    "emotion clip: move closer to face, gesture, prop, or lyric feeling without redesigning the subject",
    "transition clip: resolve the action and prepare a clean end frame for the next scene",
)


def song_dirs(output_root: Path) -> list[Path]:
    if not output_root.exists():
        return []
    result: list[Path] = []
    for path in sorted(output_root.iterdir(), key=lambda p: p.name.casefold()):
        if not path.is_dir() or path.name in SKIP_OUTPUT_DIRS:
            continue
        if any((path / folder).is_dir() for folder in PROMPT_FOLDERS):
            result.append(path)
    return result


def needs_title_lock(content: str, title: str) -> bool:
    return f"belong only to '{title}'".casefold() not in content.casefold()


def add_title_lock(content: str, title: str) -> str:
    lock = (
        f"{TITLE_LOCK_PREFIX} this prompt, visual subject, palette, motif, and all generated frames "
        f"belong only to '{title}'. Keep it separate from every other song.\n"
    )
    lines = content.splitlines()
    if lines and lines[0].startswith("#"):
        return "\n".join([lines[0], "", lock, *lines[1:]]) + ("\n" if content.endswith("\n") else "")
    return lock + "\n" + content


def _scene_heading_from_video_path(path: Path) -> tuple[str, str] | None:
    match = re.match(r"scene_(\d+)_(.+)$", path.stem)
    if not match:
        return None
    return match.group(1), match.group(2)


def _clip_prompt(title: str, scene_no: str, section_slug: str, clip_index: int, base: str) -> str:
    reference = REFERENCE_LABELS[clip_index - 1]
    role = CLIP_ROLES[clip_index - 1]
    title_lock = (
        f"{TITLE_LOCK_PREFIX} this prompt, visual subject, palette, motif, and all generated frames "
        f"belong only to '{title}'. Keep it separate from every other song."
    )
    return "\n".join(
        [
            f"# Scene {int(scene_no):02d} - {section_slug.replace('_', ' ').title()} - Clip {clip_index:02d}/04",
            "",
            f"Reference flow: use the matching `{reference}` scene image as the first clip reference; use the previous clip end frame for later clips when available.",
            "",
            "## Backfilled Clip Prompt",
            title_lock,
            base.strip(),
            "",
            f"Clip {clip_index}/4: target 6s.",
            f"Clip role: {role}.",
            f"Primary reference image: use the matching scene_{reference} image for this clip when available.",
            "Identity lock: preserve the same song-specific subject, palette, motif, prop, and silhouette. Do not borrow another song's visual identity.",
            "Keep only one main camera move and one subject action in this clip.",
            "",
        ]
    )


def backfill_missing_clips(song_dir: Path) -> int:
    video_dir = song_dir / "video_prompts"
    clip_dir = song_dir / "video_clip_prompts"
    if not video_dir.is_dir():
        return 0
    clip_dir.mkdir(parents=True, exist_ok=True)
    changed = 0
    for video_path in sorted(video_dir.glob("scene_*.md")):
        parsed = _scene_heading_from_video_path(video_path)
        if not parsed:
            continue
        scene_no, section_slug = parsed
        base = read_text(video_path)
        for clip_index in range(1, 5):
            clip_path = clip_dir / f"scene_{int(scene_no):02d}_{section_slug}_clip_{clip_index:02d}.md"
            if clip_path.exists():
                continue
            clip_path.write_text(
                _clip_prompt(song_dir.name, scene_no, section_slug, clip_index, base),
                encoding="utf-8",
            )
            changed += 1
    return changed


def repair_song_dir(song_dir: Path) -> int:
    output_docs.write_output_docs(song_dir)
    changed = 0
    title = song_dir.name
    ref_path = song_dir / "character_reference_prompt.md"
    if ref_path.exists():
        content = read_text(ref_path)
        if needs_title_lock(content, title):
            ref_path.write_text(add_title_lock(content, title), encoding="utf-8")
            changed += 1
    for folder_name in PROMPT_FOLDERS:
        folder = song_dir / folder_name
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.md")):
            if path.name == "timeline_plan.md":
                continue
            content = read_text(path)
            if not needs_title_lock(content, title):
                continue
            path.write_text(add_title_lock(content, title), encoding="utf-8")
            changed += 1
    changed += backfill_missing_clips(song_dir)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill output guide documents and per-song title locks into existing prompt folders."
    )
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "output"))
    args = parser.parse_args()

    output_root = Path(args.output_root)
    songs = song_dirs(output_root)
    changed_files = 0
    for song_dir in songs:
        changed_files += repair_song_dir(song_dir)
    output_docs.write_output_root_guide(output_root)
    print(f"Processed {len(songs)} song folders; updated {changed_files} prompt files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
