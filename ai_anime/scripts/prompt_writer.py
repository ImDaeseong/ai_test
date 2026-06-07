from __future__ import annotations

from typing import Any

import palette_engine as _pe
from policy_safety import append_policy_safe_note, safety_normalize_prompt
from world_builder import normalize_symbols


# ---------------------------------------------------------------------------
# Prompt assembly — anime + limited-color constraints applied here
# ---------------------------------------------------------------------------

def character_visual(protagonist: dict[str, Any]) -> str:
    if protagonist.get("subject_type") in ("environment_only", "object_symbol"):
        return (
            f"{protagonist['identity']}, {protagonist['silhouette']}, "
            f"primary recurring subject: {protagonist['signature_prop']}"
        )
    return (
        f"{protagonist['identity']}, {protagonist['hair']}, {protagonist['outfit']}, "
        f"{protagonist['silhouette']}, holding {protagonist['signature_prop']}"
    )


def compact_lyric_idea(scene: dict[str, Any]) -> str:
    idea = scene.get("lyric_visual_idea", "")
    idea = _pe.apply_full_palette(idea.replace("lyric cue: ", "").replace("music cue: ", "").replace("scene atmosphere: ", ""))
    anchors: list[str] = scene.get("lyric_visual_anchors", [])
    if anchors:
        anchor_str = ", ".join(anchors[:2])
        return f"{idea} — {anchor_str}"[:240]
    return idea[:220]


def image_prompt(scene: dict[str, Any], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    _cb_raw = _pe.COLOR_BALANCE_BY_STAGE.get(scene.get("story_stage", "development"), _pe.COLOR_BALANCE_BY_STAGE.get("development", ""))
    color_balance = _cb_raw.format(main_color=_pe.BRAND_PALETTE.get("main_color", "accent color")) if _cb_raw else ""
    symbols = ", ".join(normalize_symbols(scene.get("symbolism", [])[:4]))
    inst_hint = world.get("instrument_hint", "")
    _lyric_label = "Scene atmosphere" if scene.get("is_instrumental") else "Lyric mood"
    lines = [
        "Create a visibly song-unique primary subject, not a reused series character or reused visual identity.",
        f"{scene['camera_direction']} in {scene['environment']}.",
        f"{character_visual(protagonist)}.",
        f"Identity lock: {protagonist['accent_detail']}.",
        f"Action: {scene['scene_action']}.",
        f"{_lyric_label}: {compact_lyric_idea(scene)}.",
        f"Visual symbol: {scene['symbolic_focus']}; supporting symbols: {symbols}.",
        f"{scene['emotion']} {world['genre_profile']} mood, {scene['lighting']}.",
        f"Instrument-driven motion: {inst_hint}." if inst_hint else "",
        f"{_pe.BRAND_PALETTE['palette_rule']}; {color_balance}.",
        f"{_pe.STYLE_POSITIVE}.",
        f"{_pe.STYLE_NEGATIVE}.",
    ]
    return append_policy_safe_note(" ".join(line for line in lines if line.strip()))


def video_prompt(scene: dict[str, Any], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    _cb_raw = _pe.COLOR_BALANCE_BY_STAGE.get(scene.get("story_stage", "development"), _pe.COLOR_BALANCE_BY_STAGE.get("development", ""))
    color_balance = _cb_raw.format(main_color=_pe.BRAND_PALETTE.get("main_color", "accent color")) if _cb_raw else ""
    inst_hint = world.get("instrument_hint", "")
    accent_detail = protagonist.get("accent_detail", "").strip()
    if protagonist.get("subject_type") in ("environment_only", "object_symbol"):
        preserve = f"Preserve the primary visual subject: {protagonist['identity']}, {protagonist['silhouette']}, {protagonist['signature_prop']}."
    else:
        preserve = f"Preserve the character design: {protagonist['hair']}, {protagonist['outfit']}, {protagonist['signature_prop']}."
    if accent_detail:
        preserve = f"{preserve} Identity lock: {accent_detail}."
    _lyric_label = "Scene atmosphere" if scene.get("is_instrumental") else "Lyric mood"
    lines = [
        "Image-to-video from the attached scene image.",
        preserve,
        f"Camera motion: {scene['movement']}; composition stays {scene['camera_direction']}.",
        f"Action over time: {scene['scene_action']}.",
        f"Musical timing: {scene['video_rhythm']}.",
        f"Instrument-driven motion: {inst_hint}." if inst_hint else "",
        f"{_lyric_label}: {compact_lyric_idea(scene)}.",
        f"Atmosphere: {world['lighting_language']}; symbolic motion: {scene['symbolic_focus']}.",
        f"Palette: {_pe.BRAND_PALETTE['palette_rule']}; {color_balance}.",
        f"Smooth coherent anime motion, subtle parallax, clean motivated transition at the end. {_pe.VIDEO_NEGATIVE}.",
    ]
    return append_policy_safe_note(" ".join(line for line in lines if line.strip()))


# ---------------------------------------------------------------------------
# Markdown writers
# ---------------------------------------------------------------------------

def write_storyboard_markdown(scenes: list[dict[str, Any]], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    workflow = "\n".join(f"- {step}" for step in protagonist.get("reference_workflow", []))
    blocks = ["# Storyboard Prompts\n", "## Reference Workflow", workflow, ""]
    for scene in scenes:
        blocks.append(f"## Scene {scene['scene_number']} - {scene['music_section']}")
        blocks.append(f"- Story stage: {scene.get('story_stage', '')}")
        blocks.append(f"- Story beat: {scene.get('story_beat_en', '')}")
        blocks.append(f"- Lyric idea: {scene.get('lyric_visual_idea', '')}")
        blocks.append(f"- Emotion: {scene['emotion']}")
        blocks.append(f"- Environment: {scene['environment']}")
        blocks.append(f"- Action: {scene['scene_action']}")
        blocks.append(f"- Symbol: {scene['symbolic_focus']}")
        blocks.append(f"- Camera: {scene['camera_direction']}")
        blocks.append(f"- Movement: {scene['movement']}")
        blocks.append(f"- Video rhythm: {scene['video_rhythm']}")
        blocks.append(f"- Image prompt: {image_prompt(scene, protagonist, world)}")
        blocks.append(f"- Video prompt: {video_prompt(scene, protagonist, world)}\n")
    return "\n".join(blocks)


def write_camera_markdown(scenes: list[dict[str, Any]]) -> str:
    lines = ["# Camera Directions\n"]
    for scene in scenes:
        lines.append(
            f"{scene['scene_number']}. {scene['music_section']}: {scene['camera_direction']} | "
            f"{scene['movement']} | {scene['video_rhythm']}"
        )
    return "\n".join(lines) + "\n"


# Final override for the legacy guide writer above.
def write_story_summary_markdown(story_arc: dict[str, Any], scenes: list[dict[str, Any]]) -> str:
    lines = [
        "# Story Summary", "",
        "## Logline", story_arc.get("logline_ko", ""), "",
        "## Summary", story_arc.get("story_summary_ko", ""), "",
        "## Scene Flow",
    ]
    for scene in scenes:
        lines.append(f"{scene['scene_number']}. {scene['music_section']}: {scene.get('story_beat_en', '')}")
    lines += ["", "## Continuity Rules"]
    for rule in story_arc.get("continuity_rules", []):
        lines.append(f"- {rule}")
    lines += [
        "", "## Recommended Production Order",
        "1. Generate `character/character_reference_prompt.md` as the song-specific character model sheet.",
        "2. Attach that model sheet when generating every scene image for this song.",
        "3. Use each approved scene image as the first-frame/image-to-video input for that scene.",
        f"4. Keep the fixed {_pe.BRAND_PALETTE.get('main_color', 'neon magenta')} palette, but vary action, location, rhythm, and symbolism per song and section.",
    ]
    return "\n".join(lines) + "\n"


def write_production_guide(
    song: dict[str, Any],
    scenes: list[dict[str, Any]],
    protagonist: dict[str, Any],
    world: dict[str, Any],
) -> str:
    """사용자가 실제 AI 툴에서 프롬프트를 사용하는 순서와 방법을 안내하는 가이드."""
    title      = song.get("title", "Untitled")
    n_scenes   = len(scenes)
    n_clips    = n_scenes * 4
    total_sec  = n_clips * 6
    total_min  = total_sec // 60
    total_s    = total_sec % 60
    main_color = _pe.BRAND_PALETTE.get("main_color", "accent color")
    palette    = _pe.BRAND_PALETTE.get("palette_rule", "")

    scene_rows = []
    for s in scenes:
        scene_rows.append(
            f"| {s['scene_number']:02d} | {s['music_section']} | "
            f"{s.get('environment','')[:40]} | {s.get('emotion','')} |"
        )

    lines = [
        f"# 제작 가이드 — {title}",
        "",
        "> 이 파일은 파이프라인이 자동 생성한 사용 안내서입니다.",
        "> 파일 경로는 모두 이 곡의 출력 폴더 기준입니다.",
        "",
        "---",
        "",
        "## 곡 정보",
        "",
        f"- **제목:** {title}",
        f"- **씬 수:** {n_scenes}개",
        f"- **총 클립 수:** {n_clips}개 (씬당 4클립 × 약 6초)",
        f"- **예상 총 영상 길이:** 약 {total_min}분 {total_s}초",
        f"- **주색상:** {main_color}",
        f"- **팔레트 규칙:** {palette}",
        "",
        "---",
        "",
        "## 씬 목록",
        "",
        "| 씬 | 섹션 | 배경 | 감정 |",
        "|---|---|---|---|",
        *scene_rows,
        "",
        "---",
        "",
        "## 제작 순서",
        "",
        "### STEP 0 — 캐릭터 참조 시트 생성 (필수 선행)",
        "",
        "> **모든 씬 이미지 생성 전에 반드시 먼저 완료해야 합니다.**",
        "> 이 시트를 모든 씬 이미지 프롬프트에 첨부(Reference)해야 캐릭터 일관성이 유지됩니다.",
        "",
        "**사용 파일:**",
        "- `prompts/image_prompts/00_character_turnaround_model_sheet.md`",
        "- `character/character_reference_prompt.md` (상세 지침)",
        "",
        "**필수 뷰 목록:**",
    ]

    for view in protagonist.get("required_reference_views", []):
        lines.append(f"- {view}")

    lines += [
        "",
        "**플랫폼별 사용법:**",
        "- **Midjourney / Nijijourney**: 프롬프트 그대로 입력 → `--niji 7 --ar 2:3` 권장",
        "- **GPT Image**: 프롬프트 입력, `no watermark, no text` 필수 추가",
        "- **Leonardo**: Character Reference(ID:397) + Fixed Seed 조합으로 이후 씬 재사용",
        "- **FLUX.1**: 40~75단어 자연어 문장만 사용 (키워드 나열 금지)",
        "",
        "---",
        "",
        "### STEP 1 — 씬별 이미지 생성 (4샷 × 씬)",
        "",
        "각 씬마다 4가지 카메라 거리 이미지를 생성합니다.",
        "**STEP 0 캐릭터 참조 시트를 모든 씬 이미지에 첨부(Reference)하세요.**",
        "",
        "| 샷 | 파일명 패턴 | 내용 | 용도 |",
        "|---|---|---|---|",
        "| **Wide** | `scene_NN_섹션_wide.md` | 전체 환경 + 실루엣 | 씬 배경 확립, 클립1 첫 프레임 |",
        "| **Action** | `scene_NN_섹션_action.md` | 미디엄 캐릭터 행동 | 메인 장면, 클립2 첫 프레임 |",
        "| **Emotion** | `scene_NN_섹션_emotion.md` | 클로즈업 표정·감정 | 감정 강조, 클립3 첫 프레임 |",
        "| **Detail** | `scene_NN_섹션_detail.md` | 소품·상징 익스트림 클로즈업 | 디테일 강조, 클립4 첫 프레임 |",
        "",
        "**플랫폼별 사용법:**",
        "- **Midjourney**: `--v 7 --ar 16:9` 추가 (가로형 MV 프레임)",
        "- **Nijijourney**: `--niji 7 --ar 16:9 --s 250` (애니메이션 특화)",
        "- **GPT Image**: `1536×1024` (가로형), `1024×1536` (세로형)",
        "- **Gemini Image**: 한국어 프롬프트 직접 사용 가능, 생성 후 자연어 수정 가능",
        "- **FLUX.1**: ComfyUI — clip_l에 짧은 키워드, t5xxl에 상세 문장 분리 입력",
        "- **Leonardo**: Phoenix 2.0 + Alchemy on + CINEMATIC 프리셋",
        "",
        "---",
        "",
        "### STEP 2 — 씬별 영상 클립 생성 (4클립 × 씬)",
        "",
        "**STEP 1에서 생성한 이미지를 첫 프레임(Image-to-Video)으로 사용합니다.**",
        "",
        "| 클립 | 파일명 패턴 | 첫 프레임 이미지 | 카메라 |",
        "|---|---|---|---|",
        "| Clip 01 | `scene_NN_섹션_clip_01.md` | `_wide` 이미지 | Wide 풀백·드리프트 |",
        "| Clip 02 | `scene_NN_섹션_clip_02.md` | `_action` 이미지 | Medium 행동 추적 |",
        "| Clip 03 | `scene_NN_섹션_clip_03.md` | `_emotion` 이미지 | Close-up 푸시인 |",
        "| Clip 04 | `scene_NN_섹션_clip_04.md` | `_detail` 이미지 | Extreme CU 포커스 |",
        "",
        "**레퍼런스 플로우:**",
        "```",
        "클립01: [wide 이미지] → 영상 생성",
        "클립02: [action 이미지] → 영상 생성  (또는 클립01 마지막 프레임 사용 가능)",
        "클립03: [emotion 이미지] → 영상 생성  (또는 클립02 마지막 프레임 사용 가능)",
        "클립04: [detail 이미지] → 영상 생성  (또는 클립03 마지막 프레임 사용 가능)",
        "```",
        "",
        "**플랫폼별 사용법:**",
        "- **Kling**: 40~60단어, 완전한 문장으로 마침표 종료 필수",
        "- **Runway Gen-4**: `[camera_type]:` 로 시작 + References 패널에 이미지 업로드",
        "- **Sora**: Scene / Cinematography / Actions / Style / Sound 5섹션 그대로 입력",
        "- **Pika**: `-camera -motion -fps -neg` 파라미터 구문 사용",
        "- **Wan 2.1**: shot + scene + motion + camera + style 구조, Negative prompt 필수",
        "- **Luma Dream Machine**: 이미지 업로드 후 모션 프롬프트 입력",
        "- **Flow**: 이미지 업로드 → 모션 프롬프트 입력",
        "",
        "**타임라인 계획:** `prompts/video_clip_prompts/timeline_plan.md` 참조",
        "",
        "---",
        "",
        "### STEP 3 — 최종 편집",
        "",
        f"총 {n_clips}개 클립을 아래 순서로 이어붙입니다.",
        "",
        "```",
    ]

    for s in scenes:
        n   = s["scene_number"]
        sec = s["music_section"]
        lines.append(f"씬{n:02d} {sec}: clip_01(Wide) → clip_02(Action) → clip_03(Emotion) → clip_04(Detail)")

    lines += [
        "```",
        "",
        "**편집 팁:**",
        "- 같은 씬의 4클립은 연속으로 이어붙이거나 일부만 선택 사용 가능",
        "- 클립 길이(~6초)를 조절해 노래 길이에 맞게 타이밍 조정",
        "- Wide → Action → Emotion → Detail 순서는 영화적 편집 문법에 맞음",
        "- Chorus 씬은 Action+Emotion 클립을 반복 사용하면 강조 효과",
        "",
        "---",
        "",
        "## 전체 파일 구조",
        "",
        "```",
        "character/",
        "  character_prompt.md              ← 캐릭터 기본 프롬프트",
        "  character_reference_prompt.md    ← 캐릭터 참조 시트 상세 지침",
        "  protagonist_bible.json           ← 캐릭터 속성 JSON",
        "",
        "storyboard/",
        "  story_summary.md                 ← MV 스토리 요약 (한글)",
        "  storyboard_prompts.md            ← 씬별 스토리 + 프롬프트 전체",
        "  camera_directions.md             ← 카메라 무빙 요약",
        "",
        "prompts/",
        "  image_prompts/",
        "    00_character_turnaround_model_sheet.md  ← [STEP 0] 캐릭터 시트",
        f"    scene_NN_섹션_wide.md    × {n_scenes}개  ← [STEP 1] Wide 이미지",
        f"    scene_NN_섹션_action.md  × {n_scenes}개  ← [STEP 1] Action 이미지",
        f"    scene_NN_섹션_emotion.md × {n_scenes}개  ← [STEP 1] Emotion 이미지",
        f"    scene_NN_섹션_detail.md  × {n_scenes}개  ← [STEP 1] Detail 이미지",
        "  video_prompts/",
        f"    scene_NN_섹션.md         × {n_scenes}개  ← 씬 전체 방향 참조용",
        "  video_clip_prompts/",
        f"    scene_NN_섹션_clip_01~04 × {n_scenes}씬  ← [STEP 2] 클립별 영상 프롬프트",
        "    timeline_plan.md                         ← 클립 타임라인 계획",
        "  00_production_guide.md                     ← 이 파일",
        "```",
    ]

    return "\n".join(lines) + "\n"
