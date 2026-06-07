from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

import emotion_engine
import image_prompt_generator
import output_docs
import song_parser
import scene_generator
import video_prompt_generator
from common import PROJECT_ROOT, ensure_directories, read_json, slugify, versioned_run_dir


def safe_folder_name(title: str) -> str:
    """Remove Windows-forbidden path characters while preserving readable song titles."""
    name = re.sub(r'[\\/:*?"<>|]', "_", title.strip())
    return name or "untitled"


def _reset_child_dir(parent: Path, child_name: str) -> Path:
    target = parent / child_name
    resolved_parent = parent.resolve()
    resolved_target = target.resolve() if target.exists() else target.absolute()
    if not str(resolved_target).lower().startswith(str(resolved_parent).lower()):
        raise RuntimeError(f"Unsafe output path: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    return target


def sync_song_output(song_title: str) -> Path:
    """Copy current prompts and character reference into output/<song title>/."""
    out_dir = PROJECT_ROOT / "output" / safe_folder_name(song_title)
    out_dir.mkdir(parents=True, exist_ok=True)

    char_ref = PROJECT_ROOT / "character" / "character_reference_prompt.md"
    if char_ref.exists():
        shutil.copy2(char_ref, out_dir / "character_reference_prompt.md")

    for source_name, target_name in [
        ("prompts/image_prompts", "image_prompts"),
        ("prompts/video_prompts", "video_prompts"),
        ("prompts/video_clip_prompts", "video_clip_prompts"),
    ]:
        source_dir = PROJECT_ROOT / source_name
        if source_dir.exists():
            target_dir = _reset_child_dir(out_dir, target_name)
            shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)

    output_docs.write_output_docs(out_dir)
    output_docs.write_output_root_guide(PROJECT_ROOT / "output")
    return out_dir


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
    for prompt_folder in ["prompts/image_prompts", "prompts/video_prompts", "prompts/video_clip_prompts"]:
        source_dir = PROJECT_ROOT / prompt_folder
        target_dir = run_dir / prompt_folder
        if source_dir.exists():
            shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
    return run_dir


def _run_step(name: str, fn, *args, **kwargs) -> None:
    print(f"[{name}] 시작...")
    try:
        fn(*args, **kwargs)
        print(f"[{name}] 완료")
    except Exception as exc:
        print(f"[{name}] 실패: {exc}")
        raise SystemExit(1) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full AI anime MV generation pipeline.")
    parser.add_argument("--input", default=str(PROJECT_ROOT / "input"), help="Input file or folder containing .txt/.lrc/.srt/audio files.")
    parser.add_argument("--snapshot", action="store_true", help="Copy generated artifacts into a versioned output folder.")
    parser.add_argument("--no-song-output", action="store_true", help="Do not sync prompts into output/<song title>/ after generation.")
    parser.add_argument("--apply-audio-analysis", action="store_true", help="Apply optional audio analysis hints to generation metadata.")
    args = parser.parse_args()

    ensure_directories()
    _run_step("1/5 파싱", song_parser.run,
              input_path=Path(args.input),
              output_path=PROJECT_ROOT / "input" / "song_master.json",
              apply_audio_analysis=args.apply_audio_analysis)
    _run_step("2/5 감정 분석", emotion_engine.run)
    _run_step("3/5 씬 생성", scene_generator.run)
    _run_step("4/5 이미지 프롬프트", image_prompt_generator.run)
    _run_step("5/5 비디오 프롬프트", video_prompt_generator.run)

    song = read_json(PROJECT_ROOT / "input" / "song_master.json")
    if not args.no_song_output:
        song_dir = sync_song_output(song["title"])
        print(f"Song output synced to {song_dir}")

    if args.snapshot:
        run_dir = snapshot_outputs(slugify(song["title"]))
        print(f"Snapshot written to {run_dir}")


if __name__ == "__main__":
    main()
