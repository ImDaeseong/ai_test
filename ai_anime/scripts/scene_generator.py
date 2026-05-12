from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import PROJECT_ROOT, ensure_directories, read_json, slugify, write_json, write_text


BRAND_PALETTE = {
    "visual_identity": "dark cyber noir anime with neon magenta and cyber pink dominance",
    "base": "graphite gray and near-black backgrounds",
    "main_color": "neon magenta and cyber pink",
    "shadow_color": "deep plum and dark violet",
    "secondary_light": "subtle icy cyan secondary reflections",
    "highlight": "silver-white rim highlights",
    "palette_rule": (
        "limited-color cyber anime palette: neon magenta/cyber pink dominant, deep plum/dark violet shadows, "
        "graphite gray/near-black backgrounds, subtle icy cyan reflections only, and silver-white highlights"
    ),
}


COLOR_BALANCE_BY_STAGE = {
    "opening": "mostly graphite gray and near-black, faint cyber pink glow, tiny icy cyan reflections",
    "development": "graphite gray base with restrained neon magenta light trails and subtle icy cyan reflections",
    "turning point": "stronger neon magenta and cyber pink glow balanced by cool icy cyan reflections",
    "climax": "high-energy neon magenta and cyber pink dominance, silver-white rim light, controlled icy cyan contrast",
    "resolution": "softened cyber pink glow with silver-white highlights and faint icy cyan reflections",
}


def create_visual_world(song: dict[str, Any], emotion: dict[str, Any]) -> dict[str, Any]:
    return {
        "song_slug": slugify(song["title"]),
        "visual_identity": BRAND_PALETTE["visual_identity"],
        "color_palette": {
            "base": BRAND_PALETTE["base"],
            "main_color": BRAND_PALETTE["main_color"],
            "shadow_color": BRAND_PALETTE["shadow_color"],
            "secondary_light": BRAND_PALETTE["secondary_light"],
            "highlight": BRAND_PALETTE["highlight"],
            "rule": BRAND_PALETTE["palette_rule"],
        },
        "base_palette": BRAND_PALETTE["base"],
        "accent_color": BRAND_PALETTE["main_color"],
        "secondary_accent_color": "icy cyan",
        "highlight_color": "silver white",
        "environment_family": emotion.get("urban_rural_mood", "urban emotional atmosphere"),
        "core_locations": infer_locations(song),
        "recurring_symbols": list(dict.fromkeys(emotion.get("visual_symbolism", []) + song.get("visual_cues", [])))[:8],
        "lighting_language": "dark cinematic cyber lighting, neon magenta glow, deep violet shadows, subtle icy cyan reflections, silver rim light",
        "transition_language": "match cuts through neon reflections, paper crane motion, waveform-like light trails, and passing train lights",
        "negative_style_rules": song.get("negative_tags", []),
    }


def infer_locations(song: dict[str, Any]) -> list[str]:
    cues = " ".join(song.get("visual_cues", [])).lower()
    locations = []
    if "train" in cues or "platform" in cues or "subway" in cues:
        locations.append("empty train platform")
    if "rooftop" in cues:
        locations.append("rain-wet rooftop skyline")
    if "city" in cues or "street" in cues:
        locations.append("quiet city street after rain")
    if not locations:
        locations = ["empty street", "window-lit room", "open skyline"]
    return locations


def create_protagonist(song: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    mood_words = ", ".join(song.get("mood", ["melancholic"]))
    return {
        "role": "unique protagonist for this song",
        "identity": "solitary anime teenager carrying a folded paper crane",
        "age_style": "late-teen anime character, stylized and non-photorealistic",
        "hair": "short layered black hair with a long side fringe, slightly wind-tossed",
        "outfit": "dark school coat over a white shirt, narrow tie, simple shoulder bag",
        "silhouette": "slim figure, coat hem and side fringe readable in silhouette",
        "emotional_state": mood_words,
        "signature_prop": "small paper crane",
        "accent_detail": "neon magenta/cyber pink is dominant, with deep plum shadows, subtle icy cyan reflections, and silver-white rim highlights",
        "consistency_rules": [
            "Keep the same hairstyle in every scene.",
            "Keep the same outfit and shoulder bag in every scene.",
            "Preserve the paper crane as the recurring symbol.",
            "Use anime cinematic styling, never live-action realism.",
            "First create a full character turnaround model sheet from character_reference_prompt.md.",
            "The model sheet must show front, left side, right side, back, and three-quarter views.",
            "Attach that same character model sheet when generating every scene image.",
            "Attach the final scene image as the primary image-to-video reference when generating the video for that scene.",
            "If the video tool supports multiple references, also attach the character model sheet as a secondary identity reference.",
        ],
        "reference_workflow": [
            "Generate a clean character turnaround model sheet before scene production.",
            "The model sheet should include front, back, left side, right side, three-quarter view, full body, and face close-up references.",
            "Use the same model sheet as an input/reference for every scene image prompt.",
            "After each scene image is approved, use that scene image as the primary image-to-video input with the matching video prompt.",
            "When possible, include the model sheet as a secondary reference during video generation to protect character identity.",
        ],
        "required_reference_views": [
            "front full-body view",
            "left side full-body view",
            "right side full-body view",
            "back full-body view",
            "three-quarter full-body view",
            "face close-up",
            "prop close-up of the paper crane",
        ],
    }


def create_story_arc(song: dict[str, Any], emotion: dict[str, Any], world: dict[str, Any], protagonist: dict[str, Any]) -> dict[str, Any]:
    title = song.get("title", "Untitled")
    accent = world.get("accent_color", "accent color")
    accent_ko = ko_accent(accent)
    locations_ko = ", ".join(ko_location(location) for location in world.get("core_locations", []))
    symbols_ko = ", ".join(ko_symbol(symbol) for symbol in world.get("recurring_symbols", [])[:4])
    primary_emotion = emotion.get("primary_emotion", "melancholic")
    primary_emotion_ko = ko_emotion(primary_emotion)

    return {
        "title": title,
        "theme_ko": "상실을 품고 걷던 주인공이 반복되는 도시의 신호와 빛을 지나며 스스로 앞으로 나아갈 이유를 발견하는 이야기",
        "logline_ko": f"'{title}'은 종이학을 든 외로운 청소년 주인공이 주요 공간인 {locations_ko}를 지나며 {symbols_ko} 같은 상징을 단서처럼 따라가고, 마지막에는 {accent_ko} 빛 속에서 작은 결심을 되찾는 사이버 애니메이션 MV입니다.",
        "story_summary_ko": (
            f"이 뮤직비디오는 {primary_emotion_ko} 감정에서 출발합니다. 주인공은 같은 옷차림과 종이학을 지닌 채 비에 젖은 도시를 걷고, "
            "각 장면은 도망치거나 멈춰 서는 대신 조금씩 앞으로 이동하는 행동으로 이어집니다. 벌스에서는 아직 말하지 못한 감정을 품고 걷고, "
            "프리코러스에서는 신호등과 빛의 변화가 내면의 망설임을 흔듭니다. 코러스에서는 카메라와 걸음이 함께 앞으로 밀려 나가며 감정이 커지고, "
            "마지막 아웃트로에서는 종이학과 악센트 빛이 남아 주인공이 과거를 지우지 않은 채 다음 아침으로 넘어간다는 결말을 만듭니다."
        ),
        "acts": [
            {
                "name": "시작",
                "purpose_ko": "주인공, 소품, 세계의 감정을 소개하고 아직 멈춰 있는 상태를 보여줍니다.",
            },
            {
                "name": "전개",
                "purpose_ko": "가사와 리듬을 따라 주인공이 도시를 이동하며 감정의 단서를 마주합니다.",
            },
            {
                "name": "고조",
                "purpose_ko": "코러스와 반복 구간에서 같은 공간을 더 강한 빛과 움직임으로 통과하며 결심이 선명해집니다.",
            },
            {
                "name": "결말",
                "purpose_ko": "종이학과 악센트 빛을 통해 감정이 정리되고 다음 장면 이후의 여운을 남깁니다.",
            },
        ],
        "continuity_rules": [
            "모든 씬은 같은 주인공, 같은 헤어스타일, 같은 의상, 같은 종이학 소품을 유지합니다.",
            "각 씬의 이동 방향은 이전 씬의 감정에서 다음 씬의 감정으로 이어지는 흐름을 보여줍니다.",
            f"채널 브랜드 팔레트와 {accent_ko} 중심의 사이버 컬러 규칙은 전체 영상에서 유지됩니다.",
            "씬 전환은 비, 반사, 종이학, 신호등, 도시의 빛 같은 반복 심볼을 이용합니다.",
        ],
    }


def ko_accent(value: str) -> str:
    return {
        "neon magenta and cyber pink": "네온 마젠타와 사이버 핑크",
        "deep blue": "짙은 파란색",
        "pale cyan": "옅은 청록색",
        "faded blue": "바랜 파란색",
        "sunset orange": "노을빛 주황색",
        "crimson red": "짙은 붉은색",
    }.get(value.lower(), value)


def ko_emotion(value: str) -> str:
    return {
        "melancholic": "쓸쓸하고 서정적인",
        "cinematic": "영화적인",
        "lonely": "외로운",
        "loneliness": "외로운",
        "nostalgic": "그리운",
        "hopeful": "희망적인",
        "hope": "희망적인",
        "sad": "슬픈",
    }.get(value.lower(), value)


def ko_location(value: str) -> str:
    return {
        "quiet city street after rain": "비가 그친 조용한 도시 거리",
        "empty train platform": "텅 빈 기차 플랫폼",
        "rain-wet rooftop skyline": "비에 젖은 옥상과 도시 스카이라인",
        "empty street": "텅 빈 거리",
        "window-lit room": "창가에 불빛이 남은 방",
        "open skyline": "탁 트인 도시 하늘",
    }.get(value.lower(), value)


def ko_symbol(value: str) -> str:
    return {
        "silhouette": "실루엣",
        "wind": "바람",
        "distant city lights": "멀리 보이는 도시 불빛",
        "empty street": "텅 빈 거리",
        "rain": "비",
        "paper crane": "종이학",
        "sunrise edge": "새벽빛",
        "opening sky": "열리는 하늘",
    }.get(value.lower(), value)


def apply_story_arc_to_scenes(scenes: list[dict[str, Any]], story_arc: dict[str, Any]) -> list[dict[str, Any]]:
    total = len(scenes)
    enriched = []
    for index, scene in enumerate(scenes):
        previous_scene = scenes[index - 1] if index > 0 else None
        next_scene = scenes[index + 1] if index + 1 < total else None
        stage = story_stage(index + 1, total, scene["music_section"])
        beat_ko = story_beat_ko(scene, stage)
        beat_en = story_beat_en(scene, stage)
        continuity_from = (
            "첫 장면이므로 주인공의 고립감, 종이학, 네온 마젠타 중심의 사이버 도시 규칙을 분명히 소개합니다."
            if previous_scene is None
            else f"이전 {previous_scene['music_section']} 장면의 {previous_scene['emotion']} 감정을 이어받아 같은 이동 방향과 소품으로 연결합니다."
        )
        continuity_to = (
            "마지막 장면이므로 종이학과 악센트 빛을 남기며 감정을 조용히 닫습니다."
            if next_scene is None
            else f"다음 {next_scene['music_section']} 장면으로 감정이 넘어가도록 시선, 발걸음, 빛의 방향을 이어 둡니다."
        )
        story_prompt_context = (
            f"Narrative continuity: this is the {stage} beat of the music video. "
            f"Continue from the previous scene through the same protagonist, paper crane, walking direction, rain reflections, "
            f"and the fixed neon magenta cyber palette. Story beat: {beat_en}"
        )
        enriched.append(
            {
                **scene,
                "story_stage": stage,
                "story_beat_ko": beat_ko,
                "story_beat_en": beat_en,
                "continuity_from_previous_ko": continuity_from,
                "continuity_to_next_ko": continuity_to,
                "story_prompt_context": story_prompt_context,
            }
        )
    return enriched


def story_stage(index: int, total: int, section: str) -> str:
    if section == "Intro" or index == 1:
        return "opening"
    if section == "Outro" or index == total:
        return "resolution"
    if section == "Chorus" and index >= max(1, int(total * 0.6)):
        return "climax"
    if section in {"Chorus", "Post-Chorus"}:
        return "turning point"
    return "development"


def story_beat_ko(scene: dict[str, Any], stage: str) -> str:
    section = scene["music_section"]
    environment = ko_location(scene["environment"])
    if stage == "opening":
        return f"{section}에서는 주인공이 {environment}에 홀로 등장하며, 종이학과 빛의 규칙을 처음 보여줍니다."
    if stage == "development":
        return f"{section}에서는 주인공이 멈추지 않고 이동하면서 가사 속 감정을 도시의 반사와 신호로 마주합니다."
    if stage == "turning point":
        return f"{section}에서는 걸음과 카메라가 앞으로 밀려 나가며 망설임이 결심으로 바뀌기 시작합니다."
    if stage == "climax":
        return f"{section}에서는 반복되던 감정이 가장 크게 터지고, 주인공은 같은 소품을 쥔 채 빛을 향해 나아갑니다."
    return f"{section}에서는 종이학과 악센트 빛을 남기며 주인공이 과거를 품은 채 다음 아침으로 넘어갑니다."


def story_beat_en(scene: dict[str, Any], stage: str) -> str:
    section = scene["music_section"]
    environment = scene["environment"]
    if stage == "opening":
        return f"In the {section}, the protagonist appears alone in {environment}, introducing the paper crane and the visual rules of the world."
    if stage == "development":
        return f"In the {section}, the protagonist keeps moving forward while confronting the emotion of the lyrics through city reflections and signal lights."
    if stage == "turning point":
        return f"In the {section}, the forward camera movement and footsteps begin turning hesitation into resolve."
    if stage == "climax":
        return f"In the {section}, the repeated emotion reaches its peak as the protagonist moves toward the light while holding the same prop."
    return f"In the {section}, the paper crane and accent light remain as the protagonist carries the past into the next morning."


def generate_scenes(song: dict[str, Any], emotion: dict[str, Any], world: dict[str, Any], protagonist: dict[str, Any]) -> list[dict[str, Any]]:
    scenes = []
    progression_by_section = {item["section"]: item for item in emotion.get("emotional_progression", [])}
    for index, section in enumerate(song.get("sections", []), start=1):
        section_emotion = progression_by_section.get(section["name"], {})
        location = world["core_locations"][(index - 1) % len(world["core_locations"])]
        shot = choose_shot(section["name"], section_emotion.get("emotion", emotion.get("primary_emotion", "melancholic")))
        movement = choose_movement(section["name"])
        scene = {
            "scene_number": index,
            "music_section": section["name"],
            "lyrics_excerpt": section.get("lyrics", ""),
            "emotion": section_emotion.get("emotion", emotion.get("primary_emotion", "melancholic")),
            "intensity": section.get("intensity", "medium"),
            "environment": location,
            "lighting": section_emotion.get("lighting", world["lighting_language"]),
            "camera_direction": shot,
            "movement": movement,
            "cinematic_style": world["visual_identity"],
            "symbolism": section_emotion.get("visual_symbols", world["recurring_symbols"]),
            "protagonist_continuity": protagonist["identity"],
        }
        scenes.append(scene)
    return scenes


def choose_shot(section: str, emotion: str) -> str:
    if section == "Intro":
        return "wide cinematic silhouette shot with the protagonist small in frame"
    if section == "Chorus":
        return "forward tracking shot, low angle, rain reflections stretching toward dawn"
    if section == "Bridge":
        return "close-up side profile, hair crossing one eye, city lights behind"
    if section == "Outro":
        return "upward crane shot as the paper crane catches the accent light"
    if emotion in {"lonely", "loneliness"}:
        return "wide side-profile walking shot with strong negative space"
    return "medium close-up with soft parallax background"


def choose_movement(section: str) -> str:
    return {
        "Intro": "slow push-in through rainfall",
        "Verse": "gentle lateral dolly following footsteps",
        "Pre-Chorus": "subtle handheld drift as signal lights blink",
        "Chorus": "steady forward dolly, faster cuts on drum hits",
        "Bridge": "slow tilt from hand to face, then match cut to skyline",
        "Outro": "slow upward crane and dissolve to white-gray morning",
    }.get(section, "slow cinematic drift")


def image_prompt(scene: dict[str, Any], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    color_balance = COLOR_BALANCE_BY_STAGE.get(scene.get("story_stage", "development"), COLOR_BALANCE_BY_STAGE["development"])
    return (
        "Use the attached character turnaround model sheet as the identity lock. Match the same face, hairstyle, outfit, "
        "body proportions, shoulder bag, silhouette, and signature paper crane exactly. Use the model sheet views "
        "front, side, back, and three-quarter as canonical design references. Only change pose, camera angle, expression, "
        "lighting, and environment for this scene. Do not invent new clothes, hair shape, accessories, or body proportions. "
        f"{scene.get('story_prompt_context', '')} "
        f"{protagonist['identity']}, {protagonist['hair']}, {protagonist['outfit']}, "
        f"in {scene['environment']}, emotion: {scene['emotion']}, {scene['lighting']}, "
        f"{scene['camera_direction']}, {scene['movement']}, dark cinematic anime music video frame, "
        f"{BRAND_PALETTE['palette_rule']}, scene color balance: {color_balance}, strong silhouette, "
        "soft film grain, manga panel atmosphere, glowing waveform-like light trails, high contrast atmospheric depth, "
        "non-photorealistic, no live action, no rainbow colors, no warm daylight palette, no natural pastel palette, "
        "no heavy lip sync, no text, no watermark"
    )


def video_prompt(scene: dict[str, Any], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    color_balance = COLOR_BALANCE_BY_STAGE.get(scene.get("story_stage", "development"), COLOR_BALANCE_BY_STAGE["development"])
    return (
        "Use the attached scene image as the primary first-frame/image-to-video reference. If the tool supports multiple "
        "references, also attach the character turnaround model sheet as a secondary identity reference. Preserve the "
        "character identity from the model sheet and the scene image. Do not redesign the face, hair, outfit, shoulder bag, "
        "paper crane, body proportions, or color rules. "
        f"{scene.get('story_prompt_context', '')} "
        f"Anime cinematic music video shot. Maintain protagonist: {protagonist['hair']}, {protagonist['outfit']}. "
        f"Scene in {scene['environment']} with {scene['emotion']} mood. Camera: {scene['movement']}; "
        f"composition: {scene['camera_direction']}. Atmosphere: rain, dark cyber depth, neon magenta/cyber pink glow, "
        f"deep plum shadows, subtle icy cyan reflections, silver-white rim highlights. Scene color balance: {color_balance}. "
        "Keep motion slow and emotional, avoid dialogue and lip sync, preserve the fixed channel color palette, "
        "use a clean cinematic transition at the end."
    )


def write_storyboard_markdown(scenes: list[dict[str, Any]], protagonist: dict[str, Any], world: dict[str, Any], story_arc: dict[str, Any]) -> str:
    workflow = "\n".join(f"- {step}" for step in protagonist.get("reference_workflow", []))
    blocks = [
        "# Storyboard Prompts\n",
        "## Reference Workflow",
        workflow,
        "",
    ]
    for scene in scenes:
        blocks.append(f"## Scene {scene['scene_number']} - {scene['music_section']}")
        blocks.append(f"- Story stage: {scene.get('story_stage', '')}")
        blocks.append(f"- Story beat: {scene.get('story_beat_en', '')}")
        blocks.append(f"- Emotion: {scene['emotion']}")
        blocks.append(f"- Environment: {scene['environment']}")
        blocks.append(f"- Camera: {scene['camera_direction']}")
        blocks.append(f"- Movement: {scene['movement']}")
        blocks.append(f"- Image prompt: {image_prompt(scene, protagonist, world)}")
        blocks.append(f"- Video prompt: {video_prompt(scene, protagonist, world)}\n")
    return "\n".join(blocks)


def write_camera_markdown(scenes: list[dict[str, Any]]) -> str:
    lines = ["# Camera Directions\n"]
    for scene in scenes:
        lines.append(
            f"{scene['scene_number']}. {scene['music_section']}: {scene['camera_direction']} | {scene['movement']}"
        )
    return "\n".join(lines) + "\n"


def write_story_summary_markdown(story_arc: dict[str, Any], scenes: list[dict[str, Any]]) -> str:
    lines = [
        "# 전체 스토리 설명",
        "",
        f"## 로그라인",
        story_arc.get("logline_ko", ""),
        "",
        f"## 줄거리",
        story_arc.get("story_summary_ko", ""),
        "",
        "## 씬별 서사 흐름",
    ]
    for scene in scenes:
        lines.append(f"{scene['scene_number']}. {scene['music_section']}: {scene.get('story_beat_ko', '')}")
    lines.append("")
    lines.append("## 일관성 규칙")
    for rule in story_arc.get("continuity_rules", []):
        lines.append(f"- {rule}")
    lines.append("")
    lines.append("## 권장 제작 순서")
    lines.append("1. `character/character_reference_prompt.md`로 정면, 좌우 측면, 후면, 3/4뷰, 얼굴 클로즈업이 포함된 캐릭터 턴어라운드 모델시트를 먼저 생성합니다.")
    lines.append("2. 각 씬의 이미지 프롬프트를 실행할 때 같은 모델시트를 참조 이미지로 첨부합니다.")
    lines.append("3. 씬별 이미지가 완성되면 그 이미지를 비디오 생성의 첫 프레임 또는 이미지 투 비디오 입력으로 사용합니다.")
    lines.append("4. 비디오 생성 도구가 여러 참조 이미지를 지원하면 씬 이미지와 함께 캐릭터 모델시트도 보조 참조로 첨부합니다.")
    return "\n".join(lines) + "\n"


def character_prompt(protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    rules = "\n".join(f"- {rule}" for rule in protagonist["consistency_rules"])
    return (
        "# Character Prompt\n\n"
        f"{protagonist['identity']}, {protagonist['age_style']}, {protagonist['hair']}, "
        f"{protagonist['outfit']}, {protagonist['silhouette']}. Signature prop: {protagonist['signature_prop']}. "
        f"Accent detail: {protagonist['accent_detail']}. Visual world: {world['visual_identity']}.\n\n"
        "Consistency rules:\n"
        f"{rules}\n"
    )


def character_reference_prompt(protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    rules = "\n".join(f"- {rule}" for rule in protagonist["consistency_rules"])
    workflow = "\n".join(f"- {step}" for step in protagonist.get("reference_workflow", []))
    views = "\n".join(f"- {view}" for view in protagonist.get("required_reference_views", []))
    return (
        "# Character Turnaround Model Sheet Prompt\n\n"
        "Create the master character turnaround model sheet for the entire music video. This model sheet will be attached "
        "as the identity reference for every later scene image, and optionally as a secondary reference for video generation.\n\n"
        "Required views:\n"
        f"{views}\n\n"
        f"Character design: {protagonist['identity']}, {protagonist['age_style']}, {protagonist['hair']}, "
        f"{protagonist['outfit']}, {protagonist['silhouette']}. Signature prop: {protagonist['signature_prop']}. "
        f"Accent detail: {protagonist['accent_detail']}. Visual world: {world['visual_identity']}.\n\n"
        "Composition: clean anime production model sheet, neutral simple background, aligned character views at the same scale, "
        "full body visible from head to toe in each turnaround pose, clear face close-up, clear hairstyle silhouette, clear outfit seams, "
        "clear shoulder bag shape, clear paper crane prop, no dramatic camera angle, no cropped limbs, no environmental scene, no action pose. "
        f"{BRAND_PALETTE['palette_rule']}. Non-photorealistic, no live action, no text, no watermark.\n\n"
        "Consistency rules:\n"
        f"{rules}\n\n"
        "Production workflow:\n"
        f"{workflow}\n"
    )


def _generate_and_write(song: dict, emotion: dict) -> None:
    world = create_visual_world(song, emotion)
    protagonist = create_protagonist(song, world)
    scenes = generate_scenes(song, emotion, world, protagonist)
    story_arc = create_story_arc(song, emotion, world, protagonist)
    scenes = apply_story_arc_to_scenes(scenes, story_arc)

    scene_payload = {
        "song_title": song["title"],
        "story_arc": story_arc,
        "visual_world": world,
        "protagonist": protagonist,
        "character_model_sheet": {
            "step": 0,
            "purpose": "Generate this character turnaround model sheet before any scene image.",
            "prompt_file": "prompts/image_prompts/00_character_turnaround_model_sheet.md",
            "character_reference_prompt": character_reference_prompt(protagonist, world),
            "required_views": protagonist.get("required_reference_views", []),
            "usage": [
                "Attach this model sheet as the identity reference for every scene image prompt.",
                "Use each generated scene image as the primary image-to-video reference.",
                "If the video tool supports multiple references, attach this model sheet as a secondary video reference.",
            ],
        },
        "scenes": [
            {
                **scene,
                "image_prompt": image_prompt(scene, protagonist, world),
                "video_prompt": video_prompt(scene, protagonist, world),
            }
            for scene in scenes
        ],
    }
    cinematic_style = {
        "style_name": world["visual_identity"],
        "color_rules": {
            **world["color_palette"],
        },
        "camera_language": [scene["camera_direction"] for scene in scenes],
        "transition_language": world["transition_language"],
        "negative_style_rules": world["negative_style_rules"],
    }

    write_json(PROJECT_ROOT / "analysis" / "visual_world.json", world)
    write_json(PROJECT_ROOT / "analysis" / "cinematic_style.json", cinematic_style)
    write_json(PROJECT_ROOT / "character" / "protagonist_bible.json", protagonist)
    write_text(PROJECT_ROOT / "character" / "character_prompt.md", character_prompt(protagonist, world))
    write_text(PROJECT_ROOT / "character" / "character_reference_prompt.md", character_reference_prompt(protagonist, world))
    write_json(PROJECT_ROOT / "storyboard" / "story_arc.json", story_arc)
    write_text(PROJECT_ROOT / "storyboard" / "story_summary.md", write_story_summary_markdown(story_arc, scenes))
    write_json(PROJECT_ROOT / "storyboard" / "scene_list.json", scene_payload)
    write_text(PROJECT_ROOT / "storyboard" / "storyboard_prompts.md", write_storyboard_markdown(scenes, protagonist, world, story_arc))
    write_text(PROJECT_ROOT / "storyboard" / "camera_directions.md", write_camera_markdown(scenes))
    print("Wrote visual world, protagonist bible, and storyboard files")


def run(
    song_path: Path | None = None,
    emotion_path: Path | None = None,
) -> None:
    ensure_directories()
    song = read_json(song_path or (PROJECT_ROOT / "input" / "song_master.json"))
    emotion = read_json(emotion_path or (PROJECT_ROOT / "analysis" / "emotion_analysis.json"))
    _generate_and_write(song, emotion)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate visual world, protagonist bible, and storyboard scenes.")
    parser.add_argument("--song", default=str(PROJECT_ROOT / "input" / "song_master.json"))
    parser.add_argument("--emotion", default=str(PROJECT_ROOT / "analysis" / "emotion_analysis.json"))
    args = parser.parse_args()

    run(song_path=Path(args.song), emotion_path=Path(args.emotion))


if __name__ == "__main__":
    main()
