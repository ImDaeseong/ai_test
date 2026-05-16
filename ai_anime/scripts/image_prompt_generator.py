from __future__ import annotations

import argparse
from pathlib import Path

from common import PROJECT_ROOT, ensure_directories, load_config, read_json, write_text

_image_platforms_raw = load_config("platforms").get("image_platforms", [])
_IMAGE_PLATFORMS: list[dict] = _image_platforms_raw if _image_platforms_raw else [
    {
        "id": "gpt_image",
        "display_name": "GPT Image (gpt-image-2 / OpenAI)",
        "note": "quality='high'. Size: 1536x1024 (landscape) or 1024x1536 (portrait). Append: no watermark, no logos, no extra text.",
    },
    {
        "id": "gemini_image",
        "display_name": "Google Gemini (나노바나 프로 / Imagen 3)",
        "note": "한국어 프롬프트 직접 사용 가능. 자연어로 작성. 비율: 16:9 (가로), 9:16 (세로) 권장.",
    },
    {
        "id": "midjourney",
        "display_name": "Midjourney v7",
        "note": "Parameters at end: --v 7 --ar 16:9 --s 300 --no watermark, text, logo. Use --oref for character consistency.",
    },
    {
        "id": "nijijourney",
        "display_name": "Nijijourney (--niji 7)",
        "note": "Anime-focused. Describe background explicitly — Niji 7 generates minimal background if not specified.",
    },
    {
        "id": "flux1",
        "display_name": "FLUX.1 (Black Forest Labs)",
        "note": "Natural language sentences only. No (word:1.5) weights. No negative prompts in dev/schnell. 40-75 words.",
    },
    {
        "id": "leonardo",
        "display_name": "Leonardo.Ai Phoenix 2.0",
        "note": "Alchemy: on. Style preset: CINEMATIC. Character Reference (ID:397) + Fixed Seed for consistency.",
    },
]


def _build_image_platform_section(base: str, platform: dict) -> str:
    """Format the base image prompt according to each platform's official guidelines."""
    pid = platform.get("id", "")
    note = platform.get("note", "")

    if pid == "gpt_image":
        # gpt-image-2: append exclusion footer, specify model + size params
        params = (
            "**Model:** `gpt-image-2` | **Quality:** `high` | "
            "**Size:** `1536x1024` (landscape) / `1024x1536` (portrait) / `1024x1024` (square)\n"
            "**필수 추가:** `no watermark, no logos, no extra text`"
        )
        return f"{base}\n\nno watermark, no logos, no extra text\n\n{params}\n\n> {note}"

    if pid == "gemini_image":
        # Google Gemini / Imagen 3: natural language, Korean supported
        params = (
            "**비율:** `16:9` (가로형 MV 프레임) / `9:16` (세로형/숏폼)\n"
            "**언어:** 한국어 프롬프트 직접 사용 가능\n"
            "**편집:** 생성 후 자연어로 반복 수정 가능 (예: '배경만 밤으로 바꿔줘')"
        )
        return f"{base}\n\n{params}\n\n> {note}"

    if pid == "midjourney":
        # Parameters always AFTER text; no commas between params
        params = "--v 7 --ar 16:9 --s 300 --no watermark, text, logo, signature"
        return f"{base} {params}\n\n> {note}"

    if pid == "nijijourney":
        # Anime-focused; strict literal prompting; background must be explicit
        params = "--niji 7 --ar 16:9 --s 250 --no watermark, text, logo, signature"
        return (
            f"{base} {params}\n\n"
            f"**주의:** 배경을 상세히 명시하지 않으면 최소 배경 생성됨 (Niji 7 특성)\n\n"
            f"> {note}"
        )

    if pid == "flux1":
        # Natural language ONLY — no weights, no negative prompts in dev/schnell
        style_note = (
            "**규칙:** 자연어 문장만 사용. 가중치 문법(`(word:1.5)`) 사용 금지. "
            "부정 프롬프트 미지원 (dev/schnell). 키워드 나열 금지.\n"
            "**ComfyUI:** clip_l에 짧은 키워드, t5xxl에 상세 문장 분리 입력"
        )
        return f"{base}\n\n{style_note}\n\n> {note}"

    if pid == "leonardo":
        # Natural language; Alchemy pipeline; Character Reference for consistency
        params = (
            "**Model:** Phoenix 2.0 | **Alchemy:** `on` | **Guidance:** `7` | "
            "**Style preset:** `CINEMATIC` (Generic 'Anime' 사용 금지)\n"
            "**캐릭터 일관성:** Character Reference (ID:397) + Fixed Seed 조합"
        )
        return f"{base}\n\n{params}\n\n> {note}"

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
        write_text(out_dir / "00_character_turnaround_model_sheet.md", "\n".join(lines))

    # Per-scene image prompts — with image platform sections
    for scene in scene_list["scenes"]:
        base = scene.get("image_prompt", "")
        lines = [f"# Scene {scene['scene_number']:02d} - {scene['music_section']}\n"]
        for platform in _IMAGE_PLATFORMS:
            lines.append(f"## {platform['display_name']}")
            lines.append(f"{_build_image_platform_section(base, platform)}\n")
        filename = out_dir / f"scene_{scene['scene_number']:02d}_{scene['music_section'].lower().replace('-', '_')}.md"
        write_text(filename, "\n".join(lines))

    extra_count = 1 if ref_prompt else 0
    print(f"Wrote {len(scene_list['scenes']) + extra_count} image prompt files "
          f"({len(_IMAGE_PLATFORMS)} platform sections each)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write per-scene image prompts for AI image platforms.")
    parser.add_argument("--scene-list", default=str(PROJECT_ROOT / "storyboard" / "scene_list.json"))
    args = parser.parse_args()
    run(scene_list_path=Path(args.scene_list))


if __name__ == "__main__":
    main()
