from __future__ import annotations

import argparse
from pathlib import Path

from common import PROJECT_ROOT, ensure_directories, read_json, write_text


def run(scene_list_path: Path | None = None) -> None:
    ensure_directories()
    path = scene_list_path or (PROJECT_ROOT / "storyboard" / "scene_list.json")
    scene_list = read_json(path)
    out_dir = PROJECT_ROOT / "prompts" / "image_prompts"
    for old_file in out_dir.glob("*.md"):
        old_file.unlink()
    character_model_sheet = scene_list.get("character_model_sheet", {})
    if character_model_sheet.get("character_reference_prompt"):
        write_text(
            out_dir / "00_character_turnaround_model_sheet.md",
            character_model_sheet["character_reference_prompt"] + "\n",
        )
    for scene in scene_list["scenes"]:
        filename = out_dir / f"scene_{scene['scene_number']:02d}_{scene['music_section'].lower().replace('-', '_')}.md"
        write_text(filename, scene["image_prompt"] + "\n")
    extra_count = 1 if character_model_sheet.get("character_reference_prompt") else 0
    print(f"Wrote {len(scene_list['scenes']) + extra_count} image prompts")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write per-scene GPT image prompts.")
    parser.add_argument("--scene-list", default=str(PROJECT_ROOT / "storyboard" / "scene_list.json"))
    args = parser.parse_args()

    run(scene_list_path=Path(args.scene_list))


if __name__ == "__main__":
    main()
