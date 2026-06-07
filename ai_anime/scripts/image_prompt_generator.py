from __future__ import annotations

import argparse
from pathlib import Path

from common import PROJECT_ROOT, ensure_directories, load_config, read_json, write_text
from policy_safety import safety_normalize_prompt

_image_platforms_raw = load_config("platforms").get("image_platforms", [])
if not _image_platforms_raw:
    raise RuntimeError("configs/platforms.json must define image_platforms.")
_IMAGE_PLATFORMS: list[dict] = _image_platforms_raw


def _build_flux_compact(scene: dict) -> str:
    """40-75 word FLUX.1-optimized prompt from scene fields (natural language sentence).
    Style anchor is always preserved — content is trimmed if needed to stay within budget.
    """
    subject = scene.get("protagonist_continuity", "").split(",")[0].strip()
    action = scene.get("scene_action", "")
    env = scene.get("environment", "")
    lighting = scene.get("lighting", "").split(",")[0].strip()
    focus = scene.get("symbolic_focus", "")
    style_anchor = "anime style, cel-shading, 2D anime illustration, cinematic key visual. No text, letters, numbers, watermarks, logos, or UI overlays."
    # Reserve style_anchor words; content fills remaining budget up to 75
    MAX_CONTENT_WORDS = 75 - len(style_anchor.split())
    content_parts = [
        f"{subject} {action} in {env}.",
        f"{lighting}." if lighting else "",
        f"{focus}." if focus else "",
    ]
    content = " ".join(p for p in content_parts if p.strip())
    content_words = content.split()
    if len(content_words) > MAX_CONTENT_WORDS:
        trimmed = " ".join(content_words[:MAX_CONTENT_WORDS])
        last_period = trimmed.rfind(".")
        content = trimmed[:last_period + 1] if last_period > 20 else trimmed
    return f"{content} {style_anchor}"


def _build_image_platform_section(base: str, platform: dict, scene: dict | None = None) -> str:
    """Format the base image prompt according to each platform's official guidelines."""
    pid = platform.get("id", "")
    note = platform.get("note", "")
    base = safety_normalize_prompt(base)

    if pid == "gpt_image":
        # gpt-image-2: append exclusion footer, specify model + size params
        params = (
            "**Model:** `gpt-image-2` | **Quality:** `high` | "
            "**Size:** `1536x1024` (landscape) / `1024x1536` (portrait) / `1024x1024` (square)\n"
            "**필수 추가:** `Do not add any text, letters, numbers, watermarks, logos, or UI overlays to the image.`"
        )
        no_text = "Do not add any text, letters, numbers, watermarks, logos, or UI overlays to the image."
        return f"{base}\n\n{no_text}\n\n{params}\n\n> {note}"

    if pid == "gemini_image":
        # Google Gemini / Imagen 3: natural language, Korean supported
        no_text = "Do not add any text, letters, numbers, watermarks, logos, or UI overlays to the image."
        params = (
            "**비율:** `16:9` (가로형 MV 프레임) / `9:16` (세로형/숏폼)\n"
            "**언어:** 한국어 프롬프트 직접 사용 가능\n"
            "**편집:** 생성 후 자연어로 반복 수정 가능 (예: '배경만 밤으로 바꿔줘')"
        )
        return f"{base}\n\n{no_text}\n\n{params}\n\n> {note}"

    if pid == "midjourney":
        # Parameters always AFTER text; no commas between params
        params = "--v 7 --ar 16:9 --s 300 --no watermark, text, letters, numbers, logo, UI overlay, signature"
        return f"{base} {params}\n\n> {note}"

    if pid == "nijijourney":
        # Anime-focused; strict literal prompting; background must be explicit
        params = "--niji 7 --ar 16:9 --s 250 --no watermark, text, letters, numbers, logo, UI overlay, signature"
        return (
            f"{base} {params}\n\n"
            f"**주의:** 배경을 상세히 명시하지 않으면 최소 배경 생성됨 (Niji 7 특성)\n\n"
            f"> {note}"
        )

    if pid == "flux1":
        # FLUX.1 requires 40-75 word natural language sentences (no keyword lists, no weights)
        # Build compact prompt from scene fields if available; fall back to truncated base
        style_anchor = "anime style, cel-shading, 2D anime illustration, cinematic key visual. No text, letters, numbers, watermarks, logos, or UI overlays."
        if scene:
            flux_text = safety_normalize_prompt(_build_flux_compact(scene))
        else:
            # Character model sheet: extract first meaningful sentence, append style anchor
            MAX_CONTENT_WORDS = 75 - len(style_anchor.split())
            words = base.split()
            content = " ".join(words[:MAX_CONTENT_WORDS])
            last_period = content.rfind(".")
            content = content[:last_period + 1] if last_period > 20 else content
            flux_text = safety_normalize_prompt(f"{content} {style_anchor}")
        style_note = (
            "**규칙:** 자연어 문장만 사용. 가중치 문법(`(word:1.5)`) 사용 금지. "
            "부정 프롬프트 미지원 (dev/schnell). 키워드 나열 금지. 40-75단어 유지.\n"
            "**ComfyUI:** clip_l에 짧은 키워드, t5xxl에 상세 문장 분리 입력."
        )
        return f"{flux_text}\n\n{style_note}\n\n> {note}"

    if pid == "leonardo":
        # Natural language; Alchemy pipeline; Character Reference for consistency
        no_text = "Do not add any text, letters, numbers, watermarks, logos, or UI overlays to the image."
        params = (
            "**Model:** Phoenix 2.0 | **Alchemy:** `on` | **Guidance:** `7` | "
            "**Style preset:** `CINEMATIC` (Generic 'Anime' 사용 금지)\n"
            "**캐릭터 일관성:** Character Reference (ID:397) + Fixed Seed 조합"
        )
        return f"{base}\n\n{no_text}\n\n{params}\n\n> {note}"

    return f"{base}\n\n> {note}"


def run(scene_list_path: Path | None = None) -> None:
    ensure_directories()
    path = scene_list_path or (PROJECT_ROOT / "storyboard" / "scene_list.json")
    scene_list = read_json(path)
    out_dir = PROJECT_ROOT / "prompts" / "image_prompts"
    for old_file in out_dir.glob("*.md"):
        old_file.unlink()

    # Character model sheet — with image platform sections
    character_model_sheet = scene_list.get("character_model_sheet", {})
    ref_prompt = character_model_sheet.get("character_reference_prompt")
    if ref_prompt:
        lines = ["# Character Turnaround / Model Sheet\n"]
        for platform in _IMAGE_PLATFORMS:
            lines.append(f"## {platform['display_name']}")
            lines.append(f"{_build_image_platform_section(ref_prompt, platform)}\n")
        write_text(out_dir / "00_character_turnaround_model_sheet.md", safety_normalize_prompt("\n".join(lines)))

    # Per-scene image prompts — 4 shots per scene if shots array present, else 1
    file_count = 0
    for scene in scene_list["scenes"]:
        scene_num = scene['scene_number']
        section   = scene['music_section'].lower().replace('-', '_')
        shots     = scene.get("shots")

        if shots:
            for shot in shots:
                base      = shot.get("image_prompt", "")
                s_label   = shot.get("shot_label", "shot")
                s_display = shot.get("shot_display", s_label)
                s_idx     = shot.get("shot_index", "")
                lines = [f"# Scene {scene_num:02d}-{s_idx} {scene['music_section']} — {s_display}\n"]
                for platform in _IMAGE_PLATFORMS:
                    lines.append(f"## {platform['display_name']}")
                    lines.append(f"{_build_image_platform_section(base, platform, shot)}\n")
                fname = out_dir / f"scene_{scene_num:02d}_{section}_{s_label}.md"
                write_text(fname, safety_normalize_prompt("\n".join(lines)))
                file_count += 1
        else:
            base = scene.get("image_prompt", "")
            lines = [f"# Scene {scene_num:02d} - {scene['music_section']}\n"]
            for platform in _IMAGE_PLATFORMS:
                lines.append(f"## {platform['display_name']}")
                lines.append(f"{_build_image_platform_section(base, platform, scene)}\n")
            fname = out_dir / f"scene_{scene_num:02d}_{section}.md"
            write_text(fname, safety_normalize_prompt("\n".join(lines)))
            file_count += 1

    extra_count = 1 if ref_prompt else 0
    print(f"Wrote {file_count + extra_count} image prompt files "
          f"({len(_IMAGE_PLATFORMS)} platform sections each)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write per-scene image prompts for AI image platforms.")
    parser.add_argument("--scene-list", default=str(PROJECT_ROOT / "storyboard" / "scene_list.json"))
    args = parser.parse_args()
    run(scene_list_path=Path(args.scene_list))


if __name__ == "__main__":
    main()
