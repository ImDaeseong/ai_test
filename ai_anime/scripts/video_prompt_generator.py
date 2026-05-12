from __future__ import annotations

import argparse
from pathlib import Path

from common import PROJECT_ROOT, ensure_directories, read_json, write_text


PLATFORM_NOTES = {
    "runway": "Use image-to-video if a storyboard image exists. Keep motion subtle, cinematic, and continuous.",
    "kling": "Prioritize consistent character identity, clear camera motion, and restrained atmospheric movement.",
    "pika": "Use shorter clips with simple motion instructions and a clean end transition.",
    "luma": "Emphasize camera path, depth, parallax, and environmental atmosphere.",
    "veo": "Use the highest quality cinematic mode available. Keep the shot coherent, physically plausible, and faithful to the reference image.",
    "flow": "Treat this as a scene-building prompt for Google Flow/Veo workflows. Preserve shot intent, character continuity, and the fixed channel palette across generated clips.",
    "sora": "Favor a concise cinematic prompt with clear subject, camera motion, lighting, and temporal continuity. Avoid adding extra characters or unrelated visual ideas.",
    "hailuo": "Keep action simple and readable. Emphasize stable anime identity, controlled motion, and clean neon atmosphere.",
    "pixverse": "Use image-to-video when possible. Keep camera movement direct, avoid overcomplicated effects, and preserve the cyber pink palette.",
}


PLATFORM_DISPLAY_NAMES = {
    "runway": "Runway",
    "kling": "Kling",
    "pika": "Pika",
    "luma": "Luma",
    "veo": "Veo",
    "flow": "Flow",
    "sora": "Sora",
    "hailuo": "Hailuo",
    "pixverse": "PixVerse",
}


def run(scene_list_path: Path | None = None) -> None:
    ensure_directories()
    path = scene_list_path or (PROJECT_ROOT / "storyboard" / "scene_list.json")
    scene_list = read_json(path)
    out_dir = PROJECT_ROOT / "prompts" / "video_prompts"
    for old_file in out_dir.glob("scene_*.md"):
        old_file.unlink()
    for scene in scene_list["scenes"]:
        content = [f"# Scene {scene['scene_number']:02d} - {scene['music_section']}\n"]
        for platform, note in PLATFORM_NOTES.items():
            content.append(f"## {PLATFORM_DISPLAY_NAMES.get(platform, platform.title())}")
            content.append(f"{scene['video_prompt']} {note}\n")
        filename = out_dir / f"scene_{scene['scene_number']:02d}_{scene['music_section'].lower().replace('-', '_')}.md"
        write_text(filename, "\n".join(content))
    print(f"Wrote {len(scene_list['scenes'])} video prompt files")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write per-scene video prompts for major AI video platforms.")
    parser.add_argument("--scene-list", default=str(PROJECT_ROOT / "storyboard" / "scene_list.json"))
    args = parser.parse_args()

    run(scene_list_path=Path(args.scene_list))


if __name__ == "__main__":
    main()
