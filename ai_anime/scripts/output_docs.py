from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from common import PROJECT_ROOT, read_json, write_text


SHOT_REFERENCE_BY_CLIP = {
    1: "wide",
    2: "action",
    3: "emotion",
    4: "detail",
}


def _load_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def _section_slug(section: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", section.lower()).strip("_")
    return slug or "scene"


def _scan_scene_list(output_dir: Path) -> dict[str, Any]:
    scene_map: dict[int, str] = {}
    video_dir = output_dir / "video_prompts"
    image_dir = output_dir / "image_prompts"

    if video_dir.exists():
        for path in sorted(video_dir.glob("scene_*.md")):
            match = re.match(r"scene_(\d+)_([^.]+)$", path.stem)
            if match:
                scene_map[int(match.group(1))] = match.group(2)

    if image_dir.exists():
        for path in sorted(image_dir.glob("scene_*.md")):
            match = re.match(r"scene_(\d+)_(.+?)_(?:wide|action|emotion|detail)$", path.stem)
            if match:
                scene_map.setdefault(int(match.group(1)), match.group(2))

    scenes = [
        {
            "scene_number": number,
            "music_section": section.replace("_", " ").title() if section != "scene" else "Scene",
        }
        for number, section in sorted(scene_map.items())
    ]
    return {"song_title": output_dir.name, "scenes": scenes}


def _scene_rows(scenes: list[dict[str, Any]]) -> list[str]:
    rows = ["| Scene | Section | Image prompts | Video prompt | Clip prompts |", "|---:|---|---|---|---|"]
    for scene in scenes:
        scene_no = int(scene.get("scene_number", 0) or 0)
        section = scene.get("music_section", "Scene")
        section_slug = _section_slug(section)
        rows.append(
            f"| {scene_no:02d} | {section} | "
            f"`scene_{scene_no:02d}_{section_slug}_wide/action/emotion/detail.md` | "
            f"`scene_{scene_no:02d}_{section_slug}.md` | "
            f"`scene_{scene_no:02d}_{section_slug}_clip_01~04.md` |"
        )
    return rows


def build_output_folder_info(song: dict[str, Any], scene_list: dict[str, Any]) -> str:
    title = song.get("title") or scene_list.get("song_title") or "Untitled"
    scenes = scene_list.get("scenes", [])
    rows = _scene_rows(scenes)
    return "\n".join(
        [
            f"# Output Folder Guide - {title}",
            "",
            "이 폴더는 한 곡의 이미지/영상 프롬프트 패키지입니다. 곡마다 캐릭터와 세계관은 달라도, 한 곡 폴더 안에서는 같은 캐릭터 기준 시트, 팔레트, 소품, 제목 잠금 문구를 반복해서 일관성을 유지합니다.",
            "",
            "## Folder Roles",
            "",
            "| Path | Role | Use When |",
            "|---|---|---|",
            "| `character_reference_prompt.md` | 곡 전용 캐릭터 또는 주 피사체 기준 문서 | 생성 전 기준 설정 확인 |",
            "| `image_prompts/` | 정지 이미지 생성 프롬프트 | 캐릭터 시트와 씬별 기준 이미지 생성 |",
            "| `video_prompts/` | 씬 단위 영상 연출 프롬프트 | 섹션 전체의 분위기, 카메라, 움직임 확인 |",
            "| `video_clip_prompts/` | 실제 5-8초 클립 생성 프롬프트 | 영상툴에 직접 넣을 짧은 클립 제작 |",
            "| `00_image_generation_guide.md` | 이미지 생성 순서 | 이미지부터 만들 때 사용 |",
            "| `00_prompt_to_video_workflow.md` | 이미지+영상 전체 제작 순서 | MV 제작 전체 흐름 확인 |",
            "| `00_production_guide.md` | 한 파일짜리 제작 요약 | 빠른 체크리스트로 사용 |",
            "",
            "## Scene File Map",
            "",
            *rows,
            "",
            "## Consistency Rule",
            "",
            "- 먼저 `image_prompts/00_character_turnaround_model_sheet.md`로 기준 시트를 만듭니다.",
            "- 모든 씬 이미지는 같은 기준 시트를 reference로 붙입니다.",
            "- `wide`, `action`, `emotion`, `detail` 이미지는 서로 다른 샷이지만 같은 곡 전용 정체성을 유지해야 합니다.",
            "- 영상 생성은 승인된 씬 이미지를 첫 프레임 또는 reference로 사용합니다.",
            "- `video_clip_prompts`에서는 가능하면 이전 클립의 마지막 프레임을 다음 클립 reference로 이어 씁니다.",
            "",
        ]
    )


def build_image_generation_guide(song: dict[str, Any], scene_list: dict[str, Any]) -> str:
    title = song.get("title") or scene_list.get("song_title") or "Untitled"
    scenes = scene_list.get("scenes", [])
    return "\n".join(
        [
            f"# Image Generation Guide - {title}",
            "",
            "이미지는 영상보다 먼저 만듭니다. 이 단계에서 곡 전용 캐릭터/피사체, 팔레트, 소품, 장면 분위기를 고정해야 뒤의 영상 클립이 흔들리지 않습니다.",
            "",
            "## Step 0. Reference Sheet",
            "",
            "1. `image_prompts/00_character_turnaround_model_sheet.md`를 엽니다.",
            "2. 사용할 이미지 툴 섹션을 선택합니다. 예: GPT Image, Nijijourney, Midjourney, Leonardo, FLUX.",
            "3. 생성된 기준 시트를 저장하고, 이후 모든 씬 이미지 생성에 같은 reference로 붙입니다.",
            "",
            "## Step 1. Scene Images",
            "",
            "각 씬은 4가지 이미지로 나뉩니다.",
            "",
            "| Variant | Purpose | Recommended Use |",
            "|---|---|---|",
            "| `wide` | 배경과 캐릭터/피사체 실루엣을 잡는 넓은 샷 | 클립 01 첫 프레임 |",
            "| `action` | 캐릭터 행동과 메인 장면 | 클립 02 첫 프레임 |",
            "| `emotion` | 얼굴, 표정, 감정 클로즈업 | 클립 03 첫 프레임 |",
            "| `detail` | 소품, 상징, 빛, 질감 인서트 | 클립 04 첫 프레임 |",
            "",
            "## Required Consistency",
            "",
            "- `Identity lock` 또는 `belong only to '<song title>'` 문구가 유지되는지 확인합니다.",
            "- 캐릭터가 등장하지 않는 `detail` 이미지도 같은 소품, 팔레트, 곡 전용 motif를 유지해야 합니다.",
            "- `wide` 이미지에서 캐릭터가 작게 보여도 실루엣, 색상 포인트, 세계관은 같은 기준을 따라야 합니다.",
            "- 이미지에 글자, 워터마크, 로고가 생기면 다시 생성합니다.",
            "",
            "## Scene Count",
            "",
            f"- Scenes: {len(scenes)}",
            f"- Scene images: {len(scenes) * 4}",
            "- Reference sheet: 1",
            "",
        ]
    )


def build_prompt_to_video_workflow(song: dict[str, Any], scene_list: dict[str, Any]) -> str:
    title = song.get("title") or scene_list.get("song_title") or "Untitled"
    scenes = scene_list.get("scenes", [])
    return "\n".join(
        [
            f"# Image + Video Prompt Workflow - {title}",
            "",
            "`video_prompts`는 씬 전체의 연출 방향이고, `video_clip_prompts`는 영상툴에 직접 넣는 짧은 클립 실행 프롬프트입니다.",
            "",
            "## Recommended Order",
            "",
            "1. `image_prompts/00_character_turnaround_model_sheet.md`로 기준 시트를 생성합니다.",
            "2. 각 씬의 `wide`, `action`, `emotion`, `detail` 이미지를 생성합니다.",
            "3. `video_prompts/scene_NN_section.md`로 씬 전체의 카메라, 분위기, 움직임을 확인합니다.",
            "4. `video_clip_prompts/scene_NN_section_clip_01~04.md`를 영상툴에 넣어 5-8초 클립을 만듭니다.",
            "5. 클립 02 이후는 가능하면 이전 클립의 마지막 프레임을 reference로 이어서 씁니다.",
            "",
            "## Clip Reference Map",
            "",
            "| Clip | Primary reference image | Role |",
            "|---:|---|---|",
            "| 01 | `*_wide` | 장소, 실루엣, 팔레트 소개 |",
            "| 02 | `*_action` | 메인 행동과 장면 진행 |",
            "| 03 | `*_emotion` | 표정, 감정, 보컬/가사 강조 |",
            "| 04 | `*_detail` | 소품, 상징, 전환용 디테일 |",
            "",
            "## When To Use Each Folder",
            "",
            "- `video_prompts`: 긴 씬의 연출 감을 보고 싶거나, 한 번에 긴 영상을 뽑는 툴을 쓸 때 참고합니다.",
            "- `video_clip_prompts`: 실제 제작에서는 이 폴더를 주로 씁니다. 짧게 뽑고 이어 붙이는 방식이 캐릭터 일관성 유지에 더 유리합니다.",
            "",
            "## Platform Notes",
            "",
            "- Runway, Pika, Luma, Sora, Veo, Kling, Wan 계열은 먼저 승인된 이미지를 image-to-video reference로 넣습니다.",
            "- 캐릭터가 흔들리면 기준 시트를 보조 reference로 추가합니다.",
            "- 얼굴이 바뀌거나 옷/소품이 달라지면 해당 클립만 다시 생성합니다.",
            "- 긴 씬 하나를 한 번에 생성하기보다 클립별로 생성한 뒤 편집에서 붙이는 편이 안정적입니다.",
            "",
            "## Output Size",
            "",
            f"- Scenes: {len(scenes)}",
            f"- Expected clips: {len(scenes) * 4} when no audio timecode changes the clip count",
            "",
        ]
    )


def build_production_guide(song: dict[str, Any], scene_list: dict[str, Any]) -> str:
    title = song.get("title") or scene_list.get("song_title") or "Untitled"
    scenes = scene_list.get("scenes", [])
    visual_world = scene_list.get("visual_world", {})
    protagonist = scene_list.get("protagonist", {})
    palette = visual_world.get("color_palette", {})
    return "\n".join(
        [
            f"# Production Guide - {title}",
            "",
            "## Core Idea",
            "",
            "곡마다 다른 캐릭터와 세계관을 만들되, 한 곡 내부에서는 같은 기준 시트, 같은 팔레트, 같은 소품/실루엣/제목 잠금 문구를 반복 사용합니다.",
            "",
            "## Identity",
            "",
            f"- Primary subject: {protagonist.get('identity', 'song-specific primary subject')}",
            f"- Signature prop: {protagonist.get('signature_prop', '')}",
            f"- Accent detail: {protagonist.get('accent_detail', '')}",
            f"- Palette: {palette.get('palette_rule', palette)}",
            "",
            "## Folder Workflow",
            "",
            "1. `image_prompts`에서 기준 시트와 4종 씬 이미지를 만듭니다.",
            "2. `video_prompts`에서 씬 전체 연출을 확인합니다.",
            "3. `video_clip_prompts`에서 클립별 영상 생성 프롬프트를 사용합니다.",
            "4. 생성된 클립을 씬 순서대로 편집합니다.",
            "",
            "## Quality Check",
            "",
            "- 이미지 4종 모두 같은 캐릭터/피사체 정체성을 유지하는지 확인합니다.",
            "- 영상 프롬프트에 `Preserve the character design` 또는 주 피사체 보존 문구가 있는지 확인합니다.",
            "- 다른 노래 제목이나 이전 곡의 캐릭터 설명이 섞여 있으면 재생성합니다.",
            "- `detail` 샷은 사람이 없어도 소품, 색, motif가 같은 곡 전용이어야 합니다.",
            "",
            f"Scenes: {len(scenes)}",
            "",
        ]
    )


def build_output_root_guide(output_root: Path) -> str:
    song_dirs = [
        path
        for path in sorted(output_root.iterdir(), key=lambda p: p.name.casefold())
        if path.is_dir()
        and path.name not in {"images", "storyboard", "videos", "web_inputs"}
        and (
            (path / "image_prompts").is_dir()
            or (path / "video_prompts").is_dir()
            or (path / "video_clip_prompts").is_dir()
        )
    ] if output_root.exists() else []

    rows = [
        "| Song folder | Start here |",
        "|---|---|",
    ]
    for path in song_dirs:
        rows.append(f"| `{path.name}/` | `{path.name}/00_prompt_to_video_workflow.md` |")

    return "\n".join(
        [
            "# Output Guide",
            "",
            "이 폴더는 노래별 이미지/영상 프롬프트 결과물 모음입니다.",
            "각 노래 폴더 안에 이미지 생성 방법, 영상 프롬프트 사용 방법, 클립 제작 흐름 문서가 들어 있습니다.",
            "",
            "## Where To Read First",
            "",
            "노래 하나를 작업할 때는 해당 노래 폴더 안의 문서를 이 순서로 보면 됩니다.",
            "",
            "1. `00_output_folder_guide.md` - 폴더 구조와 각 프롬프트 폴더 역할",
            "2. `00_image_generation_guide.md` - 이미지 생성 순서",
            "3. `00_prompt_to_video_workflow.md` - 이미지에서 영상 클립까지 만드는 순서",
            "4. `00_production_guide.md` - 전체 제작 체크리스트",
            "",
            "## Folder Roles",
            "",
            "- `image_prompts/`: 캐릭터 기준 시트와 `wide/action/emotion/detail` 이미지 생성 프롬프트",
            "- `video_prompts/`: 씬 전체의 영상 연출 방향",
            "- `video_clip_prompts/`: 실제 5-8초 영상 클립 생성에 넣는 실행 프롬프트",
            "",
            "## Song Folders",
            "",
            *rows,
            "",
        ]
    )


def write_output_docs(output_dir: Path) -> None:
    song = _load_json_or_empty(PROJECT_ROOT / "input" / "song_master.json")
    scene_list = _load_json_or_empty(PROJECT_ROOT / "storyboard" / "scene_list.json")
    if scene_list.get("song_title") != output_dir.name:
        song = {"title": output_dir.name}
        scene_list = _scan_scene_list(output_dir)
    write_text(output_dir / "00_output_folder_guide.md", build_output_folder_info(song, scene_list))
    write_text(output_dir / "00_image_generation_guide.md", build_image_generation_guide(song, scene_list))
    write_text(output_dir / "00_prompt_to_video_workflow.md", build_prompt_to_video_workflow(song, scene_list))
    write_text(output_dir / "00_production_guide.md", build_production_guide(song, scene_list))


def write_output_root_guide(output_root: Path | None = None) -> None:
    root = output_root or (PROJECT_ROOT / "output")
    write_text(root / "00_OUTPUT_GUIDE.md", build_output_root_guide(root))
