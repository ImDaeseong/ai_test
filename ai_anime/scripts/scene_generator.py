from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from common import PROJECT_ROOT, _key_matches, _rule_matches, ensure_directories, load_config, read_json, write_json, write_text
from policy_safety import safety_normalize_data, safety_normalize_prompt

# ---------------------------------------------------------------------------
# 팔레트 엔진 — BRAND_PALETTE 상태와 치환 함수를 palette_engine.py에서 임포트.
# 하위 호환성을 위해 기존 이름(_apply_full_palette, select_theme 등)은 그대로 노출.
# ---------------------------------------------------------------------------
import palette_engine as _pe
import output_docs

# 공개 재임포트 — 외부 코드(run_regression.py, web_app.py 등)가 scene_generator.BRAND_PALETTE로 접근 가능
def select_theme(style_id: str | None = None) -> None:
    _pe.select_theme(style_id)
    # scene_generator 모듈 스코프에도 동기화
    global BRAND_PALETTE, COLOR_BALANCE_BY_STAGE, ACTIVE_STYLE_ID
    BRAND_PALETTE = _pe.BRAND_PALETTE
    COLOR_BALANCE_BY_STAGE = _pe.COLOR_BALANCE_BY_STAGE
    ACTIVE_STYLE_ID = _pe.ACTIVE_STYLE_ID


def _inject_song_color(main_color: str) -> None:
    """곡별 주색을 팔레트에 주입하고 모듈 스코프 레퍼런스를 동기화."""
    _pe.inject_song_color(main_color)
    global BRAND_PALETTE
    BRAND_PALETTE = _pe.BRAND_PALETTE


def _apply_full_palette(text: str) -> str:
    """palette_engine의 단일 진입점으로 위임."""
    return _pe.apply_full_palette(text)


def _apply_color(text: str, color: str) -> str:
    """주색 토큰만 치환. 새 코드는 _apply_full_palette() 사용."""
    return _pe.apply_main_color_only(text, color)


# 모듈 스코프 전역 — palette_engine과 동기화됨
BRAND_PALETTE: dict[str, Any] = _pe.BRAND_PALETTE
COLOR_BALANCE_BY_STAGE: dict[str, Any] = _pe.COLOR_BALANCE_BY_STAGE
ACTIVE_STYLE_ID: str = _pe.ACTIVE_STYLE_ID

# 애니메이션 공통 제약
_STYLE_POSITIVE = _pe.STYLE_POSITIVE
_STYLE_NEGATIVE = _pe.STYLE_NEGATIVE
_VIDEO_NEGATIVE = _pe.VIDEO_NEGATIVE

# ---------------------------------------------------------------------------
# genre_selector re-exports — 외부 코드(run_regression.py 등)가
# scene_generator.choose_genre_profile 등으로 접근 가능
# ---------------------------------------------------------------------------
from genre_selector import (  # noqa: E402
    GENRE_PROFILES,
    _has_any,
    _score_profiles,
    build_adaptive_default,
    choose_genre_profile,
    match_inference_profile_song,
    match_inference_profile_text,
    match_inference_profile_world,
    normalized_genre_text,
    normalized_song_text,
)

# _song_helpers — 로컬에서 사용하는 공유 유틸리티
from _song_helpers import (  # noqa: E402
    _BPM_THRESHOLDS,
    _bpm_desc,
    _bpm_tempo,
    _is_instrumental_section,
    _profile_value,
    _section_seed,
    _select_variant,
    _stable_choice,
    _with_color,
    song_character_seed,
)

# world_builder re-exports
from world_builder import (  # noqa: E402
    create_visual_world,
    infer_locations,
    infer_song_motif,
    instrument_visual_hint,
    lighting_language,
    normalize_symbols,
    transition_language,
)

# character_builder re-exports
from character_builder import (  # noqa: E402
    character_prompt,
    character_reference_prompt,
    create_protagonist,
    infer_subject_profile,
    song_unique_traits,
)

# scene_composer re-exports
from scene_composer import (  # noqa: E402
    apply_story_arc_to_scenes,
    create_story_arc,
    generate_scenes,
    infer_lyric_idea,
    choose_location,
    choose_scene_action,
    choose_shot,
    choose_movement,
    video_rhythm,
    has_broken_text,
    clean_excerpt,
)

# prompt_writer re-exports
from prompt_writer import (  # noqa: E402
    character_visual,
    compact_lyric_idea,
    image_prompt,
    video_prompt,
    write_camera_markdown,
    write_production_guide,
    write_storyboard_markdown,
    write_story_summary_markdown,
)
from shot_expander import expand_scene_to_shots  # noqa: E402

# ---------------------------------------------------------------------------
# Config loading — all rule tables and thresholds live in configs/*.json.
# ---------------------------------------------------------------------------
_STYLE_CONFIG = load_config("visual_styles")
_COLOR_CONFIG = load_config("color_palette")




def pick_main_color(song: dict[str, Any]) -> str:
    """Derive one accent color from song genre/mood/atmosphere."""
    text = normalized_song_text(song)
    inference_profile = match_inference_profile_song(song)
    if inference_profile.get("main_color"):
        return inference_profile["main_color"]
    for rule in _COLOR_CONFIG.get("rules", []):
        if any(_key_matches(k, text) for k in rule["keys"]):
            return rule["color"]
    return _COLOR_CONFIG.get("default", "neon magenta")




# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _generate_and_write(song: dict, emotion: dict) -> None:
    world       = create_visual_world(song, emotion)
    protagonist = create_protagonist(song, world)
    scenes      = generate_scenes(song, emotion, world, protagonist)
    story_arc   = create_story_arc(song, emotion, world, protagonist)
    scenes      = apply_story_arc_to_scenes(scenes)

    character_ref = safety_normalize_prompt(character_reference_prompt(protagonist, world))
    character_main_prompt = safety_normalize_prompt(character_prompt(protagonist, world))
    scenes = safety_normalize_data(scenes)
    story_arc = safety_normalize_data(story_arc)
    world = safety_normalize_data(world)
    protagonist = safety_normalize_data(protagonist)
    scene_payload = {
        "song_title": song["title"],
        "story_arc":  story_arc,
        "visual_world": world,
        "protagonist": protagonist,
        "character_model_sheet": {
            "step":    0,
            "purpose": "Generate this song-specific character turnaround model sheet before any scene image.",
            "prompt_file": "prompts/image_prompts/00_character_turnaround_model_sheet.md",
            "character_reference_prompt": character_ref,
            "required_views": protagonist.get("required_reference_views", []),
            "usage": [
                "Attach this model sheet as the identity reference for every scene image prompt in this song.",
                "Use each generated scene image as the primary image-to-video reference.",
                "If the video tool supports multiple references, attach this model sheet as a secondary video reference.",
            ],
        },
        "scenes": [
            {
                **scene,
                "image_prompt": image_prompt(scene, protagonist, world),
                "video_prompt": video_prompt(scene, protagonist, world),
                "shots": expand_scene_to_shots(scene, protagonist, world),
            }
            for scene in scenes
        ],
    }
    scene_payload = safety_normalize_data(scene_payload)
    cinematic_style = safety_normalize_data({
        "style_name":         world["visual_identity"],
        "genre_profile":      world["genre_profile"],
        "song_motif":         world["song_motif"],
        "color_rules":        {**world["color_palette"]},
        "camera_language":    [scene["camera_direction"] for scene in scenes],
        "transition_language": world["transition_language"],
        "negative_style_rules": world["negative_style_rules"],
    })

    write_json(PROJECT_ROOT / "analysis"   / "visual_world.json",    world)
    write_json(PROJECT_ROOT / "analysis"   / "cinematic_style.json",  cinematic_style)
    write_json(PROJECT_ROOT / "character"  / "protagonist_bible.json", protagonist)
    write_text(PROJECT_ROOT / "character"  / "character_prompt.md",    character_main_prompt)
    write_text(PROJECT_ROOT / "character"  / "character_reference_prompt.md", character_ref)
    write_json(PROJECT_ROOT / "storyboard" / "story_arc.json",        story_arc)
    write_text(PROJECT_ROOT / "storyboard" / "story_summary.md",      write_story_summary_markdown(story_arc, scenes))
    write_json(PROJECT_ROOT / "storyboard" / "scene_list.json",       scene_payload)
    write_text(PROJECT_ROOT / "storyboard" / "storyboard_prompts.md", write_storyboard_markdown(scenes, protagonist, world))
    write_text(PROJECT_ROOT / "storyboard" / "camera_directions.md",  write_camera_markdown(scenes))
    write_text(PROJECT_ROOT / "prompts"    / "00_production_guide.md", output_docs.build_production_guide(song, scene_payload))
    print("Wrote visual world, protagonist bible, storyboard files, and production guide")


def run(song_path: Path | None = None, emotion_path: Path | None = None, style_id: str | None = None) -> None:
    ensure_directories()
    song = read_json(song_path or (PROJECT_ROOT / "input" / "song_master.json"))
    if not style_id:
        _matched_profile = choose_genre_profile(song)
        style_id = _matched_profile.get("style_id", _STYLE_CONFIG.get("default_style", "dreamy_synth"))
    select_theme(style_id)
    _song_color = pick_main_color(song)
    # "neon magenta" is the fallback returned when no song-specific color is found.
    # In that case use the active style's defined main_color instead.
    if _song_color == "neon magenta":
        _song_color = BRAND_PALETTE.get("main_color", "neon magenta")
    _inject_song_color(_song_color)
    emotion = read_json(emotion_path or (PROJECT_ROOT / "analysis" / "emotion_analysis.json"))
    _generate_and_write(song, emotion)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate visual world, protagonist bible, and storyboard scenes.")
    parser.add_argument("--song",    default=str(PROJECT_ROOT / "input"    / "song_master.json"))
    parser.add_argument("--emotion", default=str(PROJECT_ROOT / "analysis" / "emotion_analysis.json"))
    args = parser.parse_args()
    run(song_path=Path(args.song), emotion_path=Path(args.emotion))


if __name__ == "__main__":
    main()
