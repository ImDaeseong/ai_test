from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import emotion_engine
import image_prompt_generator
import song_parser
import scene_generator
import video_prompt_generator
from common import PROJECT_ROOT, ensure_directories, read_json, slugify, versioned_run_dir


def snapshot_outputs(song_slug: str) -> Path:
    run_dir = versioned_run_dir(PROJECT_ROOT / "output" / "storyboard", song_slug)
    for relative in [
        "input/song_master.json",
        "analysis/emotion_analysis.json",
        "analysis/visual_world.json",
        "analysis/cinematic_style.json",
        "character/protagonist_bible.json",
        "character/character_prompt.md",
        "character/character_reference_prompt.md",
        "storyboard/story_arc.json",
        "storyboard/story_summary.md",
        "storyboard/scene_list.json",
        "storyboard/storyboard_prompts.md",
        "storyboard/camera_directions.md",
    ]:
        source = PROJECT_ROOT / relative
        if source.exists():
            target = run_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    for prompt_folder in ["prompts/image_prompts", "prompts/video_prompts"]:
        source_dir = PROJECT_ROOT / prompt_folder
        target_dir = run_dir / prompt_folder
        if source_dir.exists():
            shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full AI anime MV generation pipeline.")
    parser.add_argument("--input", default=str(PROJECT_ROOT / "input"), help="Input file or folder containing .txt/.lrc/.srt/audio files.")
    parser.add_argument("--snapshot", action="store_true", help="Copy generated artifacts into a versioned output folder.")
    parser.add_argument("--apply-audio-analysis", action="store_true", help="Apply optional audio analysis hints to generation metadata.")
    args = parser.parse_args()

    ensure_directories()
    song_parser.run(
        input_path=Path(args.input),
        output_path=PROJECT_ROOT / "input" / "song_master.json",
        apply_audio_analysis=args.apply_audio_analysis,
    )
    emotion_engine.run()
    scene_generator.run()
    image_prompt_generator.run()
    video_prompt_generator.run()

    if args.snapshot:
        song = read_json(PROJECT_ROOT / "input" / "song_master.json")
        run_dir = snapshot_outputs(slugify(song["title"]))
        print(f"Snapshot written to {run_dir}")


if __name__ == "__main__":
    main()
