from __future__ import annotations

import re
from typing import Any

import palette_engine as _pe
from common import _rule_matches, load_config
from genre_selector import (
    _has_any,
    match_inference_profile_song,
    match_inference_profile_text,
    match_inference_profile_world,
)
from _song_helpers import (
    _BPM_THRESHOLDS,
    _bpm_tempo,
    _is_instrumental_section,
    _section_seed,
    _select_variant,
    _stable_choice,
)
from genre_reference import reference_variant

_SECTIONS_CONFIG  = load_config("song_sections")
_LOC_CONFIG       = load_config("location_rules")
_ACTION_CONFIG    = load_config("action_rules")
_FOCUS_CONFIG     = load_config("focus_rules")
_SHOT_CONFIG      = load_config("shot_rules")
_LYRIC_VISUAL_MAP = load_config("lyric_visual_map")
_INFERENCE_CONFIG = load_config("song_inference")

# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def has_broken_text(text: str) -> bool:
    if not text:
        return False
    mojibake_markers = ("�", "Ã", "Â", "ì", "ê", "ë", "í", "諛", "蹂", "醫", "怨", "媛")
    marker_count = sum(text.count(marker) for marker in mojibake_markers)
    if marker_count >= 3:
        return True
    suspicious_question_marks = len(re.findall(r"(?<!\w)\?(?!\w)|\?\?", text))
    return suspicious_question_marks >= 3


def clean_excerpt(value: str, limit: int = 180) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    if has_broken_text(value):
        return "lyrics text appears encoding-damaged; use the section description and song metadata as the visual guide"
    return value[:limit]


# ---------------------------------------------------------------------------
# Story arc
# ---------------------------------------------------------------------------

def create_story_arc(song: dict[str, Any], emotion: dict[str, Any], world: dict[str, Any], protagonist: dict[str, Any]) -> dict[str, Any]:
    title = song.get("title", "Untitled")
    genre = song.get("genre", "unknown genre")
    bpm = song.get("bpm") or "unknown"
    motif = world.get("song_motif", protagonist["signature_prop"])
    primary = emotion.get("primary_emotion", "melancholic")
    return {
        "title": title,
        "theme_ko": f"{genre}, {bpm} BPM, {primary} mood에 맞춘 곡별 애니메이션 뮤직비디오",
        "logline_ko": (
            f"'{title}'는 {protagonist['identity']}가 {motif}를 따라가며 "
            f"{', '.join(world.get('core_locations', [])[:3])}를 통과하는 {world['genre_profile']} MV입니다."
        ),
        "story_summary_ko": (
            f"이 뮤직비디오는 고정된 색상톤은 유지하되, 장면과 캐릭터는 '{genre}'의 리듬, "
            f"{bpm} BPM의 속도감, 섹션별 가사와 감정 변화에 맞춰 전개됩니다. "
            f"반복 상징은 {motif}이며, 각 장면은 같은 주인공을 유지하면서도 장소, 행동, 카메라, 영상 움직임을 다르게 설계합니다."
        ),
        "acts": [
            {"name": "opening",     "purpose_ko": "곡의 사운드 질감, 주인공, 핵심 상징을 소개합니다."},
            {"name": "development", "purpose_ko": "벌스와 프리코러스의 가사 정서를 행동과 공간 변화로 보여줍니다."},
            {"name": "climax",      "purpose_ko": "코러스와 브리지에서 BPM과 에너지에 맞춰 카메라와 빛의 강도를 높입니다."},
            {"name": "resolution",  "purpose_ko": "마지막 가사와 잔향에 맞춰 상징을 정리하고 다음 감정으로 닫습니다."},
        ],
        "continuity_rules": [
            "한 곡 안에서는 같은 주인공, 같은 의상, 같은 대표 소품을 유지합니다.",
            "곡이 바뀌면 장르, BPM, 가사, 분위기에 맞춰 새 주인공과 새 소품을 생성합니다.",
            f"색상톤은 유지합니다: {_pe.BRAND_PALETTE['palette_rule']}.",
            "각 섹션은 가사, 섹션 설명, 강도, BPM에 따라 다른 장소, 행동, 카메라 움직임을 가져야 합니다.",
        ],
    }


# ---------------------------------------------------------------------------
# Per-scene generators — all rules read from configs
# ---------------------------------------------------------------------------

def story_stage(index: int, total: int, section: str) -> str:
    """Determine story stage from config; Chorus past the climax_position_ratio → climax."""
    stages = _SECTIONS_CONFIG.get("story_stages", {})
    climax_sections = _SECTIONS_CONFIG.get("climax_sections", ["Bridge", "Chorus"])
    ratio = _SECTIONS_CONFIG.get("climax_position_ratio", 0.6)

    if section == next(iter(stages), "Intro") or index == 1:
        return "opening"
    if index == total:
        return "resolution"

    if stages.get(section) == "resolution":
        return "resolution"

    if section == "Bridge":
        return "climax"

    if section in climax_sections and index >= max(1, int(total * ratio)):
        return "climax"

    return stages.get(section, "development")


def story_beat_ko(scene: dict[str, Any], stage: str) -> str:
    section = scene["music_section"]
    action  = scene.get("scene_action", "감정 공간을 통과합니다")
    symbol  = scene.get("symbolic_focus", "곡의 모티프")
    if stage == "opening":
        return f"{section}에서 주인공이 {symbol}을 소개합니다. 행동: {action}."
    if stage == "development":
        return f"{section}에서 가사의 감정이 행동으로 가시화됩니다: {action}."
    if stage == "turning point":
        return f"{section}에서 리듬과 머뭇거림이 바뀌며 {symbol}이(가) 주인공을 앞으로 이끕니다."
    if stage == "climax":
        return f"{section}에서 반복된 감정이 정점에 달하며 카메라가 행동을 따라갑니다: {action}."
    return f"{section}에서 {symbol}이(가) 마지막 이미지로 자리잡으며 움직임이 해결로 마무리됩니다."


def story_beat_en(scene: dict[str, Any], stage: str) -> str:
    section = scene["music_section"]
    action  = scene.get("scene_action", "moves through the emotional space")
    symbol  = scene.get("symbolic_focus", "the song motif")
    if stage == "opening":
        return f"In the {section}, the protagonist introduces {symbol}; action: {action}."
    if stage == "development":
        return f"In the {section}, the lyric emotion becomes visible through the action: {action}."
    if stage == "turning point":
        return f"In the {section}, rhythm and hesitation shift as {symbol} pulls the protagonist forward."
    if stage == "climax":
        return f"In the {section}, the repeated emotion peaks while the camera follows the action: {action}."
    return f"In the {section}, {symbol} settles into the final image as the motion slows into resolution."


_BRACKET_NOTE_RE = re.compile(r'^\[.+\]$')
_LEADING_BRACKETS_RE = re.compile(r'^(?:\[.*?\]\s*)+')


def _pick_key_lyric_phrase(lyrics: str) -> str:
    """Return the single most visually rich phrase from a lyric string."""
    if not lyrics or "encoding-damaged" in lyrics:
        return ""
    raw_frags = [f.strip() for f in re.split(r"[\n\r.。!?…,，、]+", lyrics) if f.strip()]
    fragments = []
    for f in raw_frags:
        cleaned = _LEADING_BRACKETS_RE.sub("", f).strip()
        if len(cleaned) >= 4 and not _BRACKET_NOTE_RE.match(cleaned):
            fragments.append(cleaned)
    if not fragments:
        return ""
    score_keys: list[str] = _LYRIC_VISUAL_MAP.get("phrase_score_keys", [])
    def _score(phrase: str) -> int:
        lower = phrase.lower()
        return sum(1 for k in score_keys if k in lower)
    scored = sorted(enumerate(fragments), key=lambda t: -_score(t[1]))
    best = scored[0][1] if scored else fragments[0]
    return best[:100].strip()


def _extract_visual_anchors(lyrics: str) -> list[str]:
    """Extract concrete visual element strings from lyric keywords."""
    if not lyrics or "encoding-damaged" in lyrics:
        return []
    text = lyrics.lower()
    anchors: list[str] = []
    seen: set[str] = set()
    for rule in _LYRIC_VISUAL_MAP.get("visual_anchors", []):
        if any(k in text for k in rule.get("keys", [])):
            visual: str = rule["visual"]
            if visual not in seen:
                anchors.append(visual)
                seen.add(visual)
        if len(anchors) >= 3:
            break
    return anchors


def _get_lyric_visuals(lyrics: str) -> dict[str, Any]:
    """Compute location boost words and visual anchors from raw lyric text."""
    if not lyrics:
        return {"location_boost_words": [], "visual_anchors": []}
    text = lyrics.lower()
    boost_words: list[str] = []
    seen_boost: set[str] = set()
    for rule in _LYRIC_VISUAL_MAP.get("location_boost", []):
        if any(k in text for k in rule.get("keys", [])):
            for w in rule.get("boost_words", []):
                if w not in seen_boost:
                    boost_words.append(w)
                    seen_boost.add(w)
    return {"location_boost_words": boost_words, "visual_anchors": _extract_visual_anchors(lyrics)}


_INSTRUMENTAL_KEYWORDS: list[tuple[list[str], str]] = [
    (["build", "rising", "swell", "crescendo", "dynamic"],
     "anticipatory atmosphere, ambient energy building through light and space"),
    (["fade", "decay", "dim", "quiet", "ending", "dissolve"],
     "gradually quieting space, light retreating toward stillness"),
    (["break", "breakdown", "pause", "silent"],
     "held stillness, breath suspended, light frozen at peak intensity"),
    (["bridge", "transition", "shift"],
     "visual space in transition, mood shifting through ambient light and movement"),
]


def _instrumental_visual_atmosphere(section: dict[str, Any]) -> str:
    """Map production-note keywords to a visual atmosphere description for instrumental sections."""
    desc = (section.get("description", "") + " " + section.get("name", "")).lower()
    for keywords, atmosphere in _INSTRUMENTAL_KEYWORDS:
        if any(k in desc for k in keywords):
            return _pe.apply_full_palette(atmosphere)
    return _pe.apply_full_palette("instrumental visual atmosphere, musical energy expressed through ambient light and space")


def infer_lyric_idea(section: dict[str, Any]) -> str:
    if _is_instrumental_section(section):
        return f"scene atmosphere: {_instrumental_visual_atmosphere(section)}"
    raw_lyrics = section.get("lyrics", "")
    lyrics = clean_excerpt(raw_lyrics, 300)
    description = section.get("description", "").strip()
    if lyrics and "encoding-damaged" not in lyrics:
        key_phrase = _pick_key_lyric_phrase(raw_lyrics)
        if key_phrase:
            return _pe.apply_full_palette(f"lyric cue: {key_phrase}")
    if description:
        return _pe.apply_full_palette(f"music cue: {description}")
    return f"{section['name']} emotional cue"


def choose_location(
    section: dict[str, Any],
    world: dict[str, Any],
    index: int,
    used_locations: list[str] | None = None,
    lyric_hints: dict[str, Any] | None = None,
) -> str:
    text = f"{section.get('lyrics', '')} {section.get('description', '')}".lower()
    section_name = section["name"]
    used = used_locations or []
    core = world["core_locations"]

    inference_profile = match_inference_profile_world(world)
    if inference_profile:
        for rule in inference_profile.get("extra_locations", []):
            if _has_any(text, rule.get("keys", [])):
                loc = _pe.apply_full_palette(_select_variant(rule["location"], _section_seed(section), f"inference_location_{index}"))
                if loc in core and loc not in used:
                    return loc
        preferences = inference_profile.get("section_location_preferences", {}).get(section_name, [])
        preferred_locs = [loc for loc in core if _has_any(loc.lower(), preferences)]
        for loc in preferred_locs:
            if loc not in used:
                return loc
        unused_profile_locs = [loc for loc in core if loc not in used]
        if unused_profile_locs:
            return unused_profile_locs[0]
        if not core:
            return "open cinematic space"
        return core[(index - 1) % len(core)]

    if _SECTIONS_CONFIG.get("story_stages", {}).get(section_name) == "resolution":
        dawn_keywords = _SECTIONS_CONFIG.get("resolution_location_keywords", ["dawn", "skyline", "rooftop", "sunrise"])
        dawn_locs = [loc for loc in world["core_locations"] if any(k in loc.lower() for k in dawn_keywords) and loc not in used]
        if dawn_locs:
            return dawn_locs[0]

    boost_words: list[str] = (lyric_hints or {}).get("location_boost_words", [])
    if boost_words:
        for loc in core:
            if any(w in loc.lower() for w in boost_words) and loc not in used:
                return loc

    for rule in _LOC_CONFIG.get("rules", []):
        if _rule_matches(rule, text):
            loc = _pe.apply_full_palette(_select_variant(rule["location"], _section_seed(section), f"location_rule_{index}"))
            if loc not in used:
                return loc

    unused = [loc for loc in core if loc not in used]
    if unused:
        return unused[0]
    if not core:
        return "open cinematic space"
    return core[(index - 1) % len(core)]


def choose_scene_action(section: dict[str, Any], lyric_idea: str, protagonist: dict[str, Any], used_actions: list[str] | None = None) -> str:
    text         = f"{section.get('lyrics', '')} {section.get('description', '')}".lower()
    prop         = protagonist["signature_prop"]
    section_name = section["name"]
    used         = used_actions or []

    def fmt(template: str) -> str:
        return template.replace("{prop}", prop)

    def pick_template(value: Any, salt: str) -> str:
        return fmt(_select_variant(value, _section_seed(section, prop), salt))

    inference_profile = match_inference_profile_text(text)
    if not inference_profile:
        for profile in _INFERENCE_CONFIG.get("profiles", []):
            if _has_any(prop.lower(), profile.get("action_context_prop_keys", [])):
                inference_profile = profile
                break
    if inference_profile:
        section_actions = inference_profile.get("section_actions", {})
        if section_name in section_actions:
            return _pick_action_avoiding(section_actions[section_name], _section_seed(section, prop), f"inference_section_{section_name}", prop, used)
        for rule in inference_profile.get("action_rules", []):
            if _has_any(text, rule.get("keys", [])):
                return _pe.apply_full_palette(pick_template(rule["action"], "inference_rule_action"))
        if inference_profile.get("default_action"):
            return _pe.apply_full_palette(pick_template(inference_profile["default_action"], "inference_default_action"))

    if protagonist.get("subject_type") == "environment_only":
        if section_name == "Intro":
            return _pe.apply_full_palette(f"the empty environment slowly reveals {prop} through light, weather, and camera drift")
        if section_name == "Chorus":
            return _pe.apply_full_palette(f"the environment blooms around {prop}, making the space itself feel like the singer")
        if section_name == "Outro":
            return _pe.apply_full_palette(f"{prop} fades into the final empty space as the environment settles")
        return _pe.apply_full_palette(f"light, shadow, and atmosphere move around {prop} without introducing a recurring human lead")

    if protagonist.get("subject_type") == "object_symbol":
        if section_name == "Intro":
            return _pe.apply_full_palette(f"{prop} appears as the first emotional anchor, held by light rather than a full human lead")
        if section_name == "Chorus":
            return _pe.apply_full_palette(f"{prop} becomes the dominant subject, pulling reflections and memory fragments toward it")
        if section_name == "Outro":
            return _pe.apply_full_palette(f"{prop} remains after all human presence has passed out of frame")
        return _pe.apply_full_palette(f"{prop} reacts to the lyric emotion through glow, reflection, and small environmental movement")

    overrides = _SECTIONS_CONFIG.get("action_overrides", {})
    if section_name in overrides:
        ov = overrides[section_name]
        if "music_cue_prefix" in ov and lyric_idea.startswith(ov["music_cue_prefix"]):
            return _pe.apply_full_palette(pick_template(ov["music_cue_action"], "intro_music_cue_action"))
        if "hide_keywords" in ov and any(k in text for k in ov["hide_keywords"]):
            return _pe.apply_full_palette(pick_template(ov["hide_action"], "hide_action"))
        if "cry_keywords" in ov and any(k in text for k in ov["cry_keywords"]):
            return _pe.apply_full_palette(pick_template(ov["cry_action"], "cry_action"))
        if "smile_keywords" in ov and any(k in text for k in ov["smile_keywords"]):
            return _pe.apply_full_palette(pick_template(ov["smile_action"], "smile_action"))
        if "default_action" in ov:
            return _pe.apply_full_palette(pick_template(ov["default_action"], "section_default_action"))

    for rule in _ACTION_CONFIG.get("rules", []):
        if any(k in text for k in rule["keys"]):
            return _pe.apply_full_palette(pick_template(rule["action"], "keyword_action"))

    return _pe.apply_full_palette(pick_template(_ACTION_CONFIG.get("default", "shows the section emotion through posture, hand movement, and the recurring {prop}"), "default_action"))


def choose_symbolic_focus(section: dict[str, Any], world: dict[str, Any], protagonist: dict[str, Any]) -> str:
    text = f"{section.get('lyrics', '')} {section.get('description', '')}".lower()
    inference_profile = match_inference_profile_world(world) or match_inference_profile_text(text)
    if inference_profile:
        for rule in inference_profile.get("focus_rules", []):
            if _has_any(text, rule.get("keys", [])):
                return _pe.apply_full_palette(rule["focus"])
        return world.get("song_motif") or protagonist["signature_prop"]
    for rule in _FOCUS_CONFIG.get("rules", []):
        if any(k in text for k in rule["keys"]):
            return _pe.apply_full_palette(rule["focus"])
    return _pe.apply_full_palette(world.get("song_motif") or protagonist["signature_prop"])


def _pick_avoiding(options: Any, seed: str, salt: str, used_shots: list[str]) -> str:
    """Pick from options, preferring items not already in used_shots."""
    if not isinstance(options, list):
        return _pe.apply_full_palette(str(options or ""))
    candidates = [str(o) for o in options if str(o).strip()]
    unused = [c for c in candidates if c not in used_shots]
    pool = unused if unused else candidates
    return _pe.apply_full_palette(_stable_choice(pool, seed, salt))


def _pick_action_avoiding(options: Any, seed: str, salt: str, prop: str, used: list[str]) -> str:
    """Like _pick_avoiding but expands {prop} before checking used list."""
    if not isinstance(options, list):
        return _pe.apply_full_palette(str(options or "").replace("{prop}", prop))
    candidates = [str(o).replace("{prop}", prop) for o in options if str(o).strip()]
    final_used = {_pe.apply_full_palette(a) for a in used}
    unused = [c for c in candidates if _pe.apply_full_palette(c) not in final_used]
    pool = unused if unused else candidates
    return _pe.apply_full_palette(_stable_choice(pool, seed, salt))


def apply_reference_camera(
    base_shot: str,
    reference: dict[str, Any],
    section: dict[str, Any],
    index: int,
    used_shots: list[str],
) -> str:
    """Append genre camera grammar while avoiding duplicate final directions."""
    options = [str(value) for value in reference.get("camera_language", []) if str(value).strip()]
    if not options:
        return base_shot
    seed = _section_seed(section)
    first = reference_variant(reference, "camera_language", seed, f"camera_{index}")
    ordered = [first, *[option for option in options if option != first]]
    for option in ordered:
        candidate = f"{base_shot}; genre framing: {option}"
        if candidate not in used_shots:
            return candidate
    return f"{base_shot}; genre framing variation {index}: {first}"


def choose_shot(section: dict[str, Any], emotion: str, song: dict[str, Any], used_shots: list[str] | None = None) -> str:
    name  = section["name"]
    bpm   = song.get("bpm") or 0
    text  = f"{section.get('lyrics', '')} {section.get('description', '')}".lower()
    tempo = _bpm_tempo(bpm)
    used  = used_shots or []

    section_overrides = _SHOT_CONFIG.get("section_overrides", {})
    if name in section_overrides:
        return _pick_avoiding(section_overrides[name], _section_seed(section, emotion), f"shot_{name}", used)

    if name == "Chorus":
        if tempo == "fast":
            return _pick_avoiding(_SHOT_CONFIG.get("chorus_fast_shot"), _section_seed(section, emotion), "chorus_fast_shot", used)
        return _pick_avoiding(_SHOT_CONFIG.get("chorus_default_shot"), _section_seed(section, emotion), "chorus_default_shot", used)

    mirror_keys = _SHOT_CONFIG.get("mirror_keywords", ["거울", "mirror", "반사"])
    if any(k in text for k in mirror_keys):
        return _pick_avoiding(_SHOT_CONFIG.get("mirror_shot"), _section_seed(section, emotion), "mirror_shot", used)

    emotion_shots = _SHOT_CONFIG.get("emotion_shots", {})
    if emotion in emotion_shots:
        return _pick_avoiding(emotion_shots[emotion], _section_seed(section, emotion), f"emotion_shot_{emotion}", used)

    for rule in _SHOT_CONFIG.get("keyword_shots", []):
        if any(k in text for k in rule["keys"]):
            return _pick_avoiding(rule["shot"], _section_seed(section, emotion), "keyword_shot", used)

    return _pick_avoiding(_SHOT_CONFIG.get("default"), _section_seed(section, emotion), "default_shot", used)


def choose_movement(section: dict[str, Any], song: dict[str, Any]) -> str:
    name    = section["name"]
    tempo   = _bpm_tempo(song.get("bpm"))
    patterns = _SECTIONS_CONFIG.get("movement_patterns", {})
    section_patterns = patterns.get(name, {})
    inference_profile = match_inference_profile_song(song)
    if inference_profile.get("movement_patterns"):
        profile_patterns = inference_profile["movement_patterns"]
        return _pe.apply_full_palette(_select_variant(profile_patterns.get(name, profile_patterns.get("default", "song-tempo-aware cinematic drift")), _section_seed(section, name), f"profile_movement_{name}"))

    if "any" in section_patterns:
        return _pe.apply_full_palette(_select_variant(section_patterns["any"], _section_seed(section, name), f"movement_{name}_any"))
    if tempo in section_patterns:
        return _pe.apply_full_palette(_select_variant(section_patterns[tempo], _section_seed(section, name), f"movement_{name}_{tempo}"))
    if "medium" in section_patterns:
        return _pe.apply_full_palette(_select_variant(section_patterns["medium"], _section_seed(section, name), f"movement_{name}_medium"))
    return _pe.apply_full_palette(_select_variant(_SECTIONS_CONFIG.get("default_movement", "song-tempo-aware cinematic drift"), _section_seed(section, name), "default_movement"))


def video_rhythm(song: dict[str, Any], section: dict[str, Any]) -> str:
    bpm       = song.get("bpm")
    intensity = section.get("intensity", "medium")
    tempo     = _bpm_tempo(bpm)
    desc      = _BPM_THRESHOLDS.get(tempo, {}).get("rhythm_desc", "measured musical motion, camera accents every phrase")
    timing = ""
    if section.get("start_time") is not None:
        start = float(section["start_time"])
        end = section.get("end_time")
        timing = f", section starts at {start:.2f}s"
        if end is not None:
            timing += f" and ends at {float(end):.2f}s"
    if bpm:
        return f"{bpm} BPM: {desc}, intensity {intensity}{timing}"
    return f"follow the section intensity {intensity} with coherent cinematic motion{timing}"


_SCENE_PALETTE_TEXT_FIELDS = frozenset({
    "lighting", "movement", "scene_action", "symbolic_focus",
    "environment", "camera_direction", "lyric_visual_idea",
    "protagonist_continuity", "cinematic_style", "video_rhythm",
    "section_description", "story_beat_ko", "story_beat_en",
    "story_prompt_context",
})


def _sanitize_scene_palette(scene: dict[str, Any]) -> dict[str, Any]:
    """Guarantee no raw palette tokens remain in any scene text field."""
    result = {}
    for key, value in scene.items():
        if key in _SCENE_PALETTE_TEXT_FIELDS and isinstance(value, str):
            result[key] = _pe.apply_full_palette(value)
        elif key == "symbolism" and isinstance(value, list):
            result[key] = [_pe.apply_full_palette(s) if isinstance(s, str) else s for s in value]
        else:
            result[key] = value
    return result


def generate_scenes(song: dict[str, Any], emotion: dict[str, Any], world: dict[str, Any], protagonist: dict[str, Any]) -> list[dict[str, Any]]:
    scenes: list[dict[str, Any]] = []
    used_locations: list[str] = []
    used_shots: list[str] = []
    used_actions: list[str] = []
    progression_by_section = {item["section"]: item for item in emotion.get("emotional_progression", [])}

    for index, section in enumerate(song.get("sections", []), start=1):
        section_emotion = progression_by_section.get(section["name"], {})
        lyric_excerpt   = clean_excerpt(section.get("lyrics", ""))
        lyric_visuals   = _get_lyric_visuals(section.get("lyrics", ""))
        lyric_idea      = infer_lyric_idea(section)
        location        = choose_location(section, world, index, used_locations, lyric_hints=lyric_visuals)
        used_locations.append(location)
        scene_action    = choose_scene_action(section, lyric_idea, protagonist, used_actions)
        used_actions.append(scene_action)
        symbolic_focus  = choose_symbolic_focus(section, world, protagonist)
        shot            = choose_shot(section, section_emotion.get("emotion", emotion.get("primary_emotion", "melancholic")), song, used_shots)
        reference = world.get("genre_reference", {})
        shot = apply_reference_camera(shot, reference, section, index, used_shots)
        used_shots.append(shot)
        movement        = choose_movement(section, song)
        reference_motion = reference_variant(reference, "motion_language", _section_seed(section), f"motion_{index}")
        if reference_motion:
            movement = f"{movement}; genre motion: {reference_motion}"

        scene = {
            "scene_number":         index,
            "music_section":        section["name"],
            "is_instrumental":      _is_instrumental_section(section),
            "lyrics_excerpt":       lyric_excerpt,
            "lyric_visual_idea":    lyric_idea,
            "lyric_visual_anchors": lyric_visuals.get("visual_anchors", []),
            "emotion":              section_emotion.get("emotion", emotion.get("primary_emotion", "melancholic")),
            "intensity":            section.get("intensity", "medium"),
            "environment":          location,
            "lighting":             _pe.apply_full_palette(section_emotion.get("lighting", world["lighting_language"])),
            "camera_direction":     shot,
            "movement":             movement,
            "video_rhythm":         video_rhythm(song, section),
            "cinematic_style":      world["visual_identity"],
            "symbolism":            [_pe.apply_full_palette(s) for s in section_emotion.get("visual_symbols", world["recurring_symbols"])],
            "symbolic_focus":       symbolic_focus,
            "scene_action":         scene_action,
            "protagonist_continuity": protagonist["identity"],
            "section_description":  section.get("description", ""),
            "genre_narrative_direction": reference.get("narrative_direction", ""),
            "genre_avoid": reference.get("avoid", []),
            "start_time":            section.get("start_time"),
            "end_time":              section.get("end_time"),
        }
        scenes.append(_sanitize_scene_palette(scene))
    return scenes


def apply_story_arc_to_scenes(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = len(scenes)
    enriched = []
    for index, scene in enumerate(scenes):
        stage = story_stage(index + 1, total, scene["music_section"])
        beat_en = story_beat_en(scene, stage)
        enriched.append(_sanitize_scene_palette({
            **scene,
            "story_stage":             stage,
            "story_beat_ko":           story_beat_ko(scene, stage),
            "story_beat_en":           beat_en,
            "continuity_from_previous_ko": "Continue emotional and visual continuity from the previous section.",
            "continuity_to_next_ko":   "Lead the motion and symbol into the next section.",
            "story_prompt_context": (
                f"Narrative continuity: this is the {stage} beat of the music video. "
                f"Keep the song-specific protagonist and signature prop consistent, but make this scene distinct through "
                f"the section lyric idea, location, action, camera, and BPM-aware motion. Story beat: {beat_en}"
            ),
        }))
    return enriched
