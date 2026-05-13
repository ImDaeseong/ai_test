from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from common import PROJECT_ROOT, ensure_directories, load_config, read_json, slugify, write_json, write_text


# ---------------------------------------------------------------------------
# Config loading — all rule tables and thresholds live in configs/*.json.
# Python is a pure execution engine; no domain rules are hardcoded here.
# ---------------------------------------------------------------------------
_STYLE_CONFIG    = load_config("visual_styles")
_GENRE_CONFIG    = load_config("genres")
_BPM_CONFIG      = load_config("bpm_thresholds")
_SECTIONS_CONFIG = load_config("song_sections")
_LOC_CONFIG      = load_config("location_rules")
_ACTION_CONFIG   = load_config("action_rules")
_FOCUS_CONFIG    = load_config("focus_rules")
_MOTIF_CONFIG    = load_config("motif_rules")
_SHOT_CONFIG     = load_config("shot_rules")
_PROP_CONFIG     = load_config("prop_rules")
_CHAR_CONFIG     = load_config("character_defaults")
_COLOR_CONFIG    = load_config("color_palette")

GENRE_PROFILES: list[dict[str, Any]] = _GENRE_CONFIG if isinstance(_GENRE_CONFIG, list) else []

# Global anime + limited-color constraints (enforced on every prompt)
_ANIME            = _STYLE_CONFIG.get("global_anime_constraints", {})
_STYLE_POSITIVE   = ", ".join(_ANIME.get("style_enforcement", []))
_STYLE_NEGATIVE   = ". ".join(_ANIME.get("negative_enforcement", []))
_VIDEO_NEGATIVE   = ". ".join(_ANIME.get("video_negative_enforcement", []))

BRAND_PALETTE: dict[str, Any] = {}
COLOR_BALANCE_BY_STAGE: dict[str, Any] = {}


def select_theme(style_id: str | None = None) -> None:
    global BRAND_PALETTE, COLOR_BALANCE_BY_STAGE
    style_id = style_id or _STYLE_CONFIG.get("default_style", "cyber_noir")
    style_data = _STYLE_CONFIG.get("styles", {}).get(style_id, {})
    if not style_data:
        first_key = next(iter(_STYLE_CONFIG.get("styles", {}).keys()), "cyber_noir")
        style_data = _STYLE_CONFIG.get("styles", {}).get(first_key, {})
    BRAND_PALETTE = style_data.get("brand_palette", {})
    COLOR_BALANCE_BY_STAGE = style_data.get("color_balance_by_stage", {})


select_theme()

_COLOR_SUB = re.compile(r"neon magenta(?: and cyber pink)?|cyber[- ]?pink", re.IGNORECASE)


def _inject_song_color(main_color: str) -> None:
    """Override BRAND_PALETTE color fields with the song-derived single color."""
    BRAND_PALETTE["main_color"] = main_color
    BRAND_PALETTE["visual_identity"] = f"dark anime with {main_color} dominance"
    BRAND_PALETTE["palette_rule"] = (
        f"limited-color anime palette: {main_color} dominant, "
        "dark shadows, near-black backgrounds, subtle secondary reflections, silver-white rim highlights"
    )


# ---------------------------------------------------------------------------
# BPM helpers — read thresholds from config, never hardcoded
# ---------------------------------------------------------------------------

_BPM_THRESHOLDS = _BPM_CONFIG.get("thresholds", {})


def _bpm_tempo(bpm: int | None) -> str:
    """Return 'fast', 'slow', or 'medium' based on config thresholds."""
    if not bpm:
        return "medium"
    if bpm >= _BPM_THRESHOLDS.get("fast", {}).get("min_bpm", 120):
        return "fast"
    if bpm <= _BPM_THRESHOLDS.get("slow", {}).get("max_bpm", 80):
        return "slow"
    return "medium"


def _bpm_desc(bpm: int | None, key: str, fallback: str) -> str:
    tempo = _bpm_tempo(bpm)
    return _BPM_THRESHOLDS.get(tempo, {}).get(key, fallback)


def _bpm_lighting_desc(bpm: int | None) -> str:
    return _bpm_desc(bpm, "lighting_desc", "measured cyber-pink pulses with subtle icy cyan response lights")


def _bpm_transition_desc(bpm: int | None) -> str:
    return _bpm_desc(bpm, "transition_desc", "smooth rhythmic match cuts and gentle push transitions")


# ---------------------------------------------------------------------------
# Word-boundary keyword matching (prevents e.g. "live" ⊂ "delivery")
# ---------------------------------------------------------------------------

def _key_matches(key: str, text: str) -> bool:
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])", text))


def _rule_matches(rule: dict[str, Any], text: str) -> bool:
    """Match a config rule against text. Uses word-boundary for flagged rules."""
    keys = rule.get("keys", [])
    if rule.get("word_boundary", False):
        return any(_key_matches(k, text) for k in keys)
    return any(k in text for k in keys)


# ---------------------------------------------------------------------------
# Genre profile selection
# ---------------------------------------------------------------------------

def normalized_song_text(song: dict[str, Any]) -> str:
    positive_tags = [t for t in song.get("style_tags", []) if not t.lstrip().startswith(("‑", "-"))]
    fields = [
        song.get("genre", ""),
        " ".join(positive_tags),
        " ".join(song.get("mood", [])),
        " ".join(song.get("instruments", [])),
        song.get("atmosphere", ""),
    ]
    for section in song.get("sections", []):
        fields.extend([section.get("description", ""), section.get("lyrics", "")])
    return " ".join(fields).lower()


def pick_main_color(song: dict[str, Any]) -> str:
    """Derive one accent color from song genre/mood/atmosphere."""
    text = normalized_song_text(song)
    for rule in _COLOR_CONFIG.get("rules", []):
        if any(k in text for k in rule["keys"]):
            return rule["color"]
    return _COLOR_CONFIG.get("default", "neon magenta")


def _apply_color(text: str, color: str) -> str:
    """Replace hardcoded color keywords in genre profile strings with the song's color."""
    return _COLOR_SUB.sub(color, text)


def normalized_genre_text(song: dict[str, Any]) -> str:
    positive_tags = [t for t in song.get("style_tags", []) if not t.lstrip().startswith(("‑", "-"))]
    fields = [
        song.get("genre", ""),
        " ".join(positive_tags),
        " ".join(song.get("mood", [])),
        " ".join(song.get("instruments", [])),
        song.get("atmosphere", ""),
    ]
    return " ".join(fields).lower()


def _score_profiles(text: str) -> tuple[int, dict[str, Any] | None]:
    best_score, best_profile = 0, None
    for profile in GENRE_PROFILES:
        score = sum(1 for key in profile["keys"] if _key_matches(key, text))
        if score > best_score:
            best_score, best_profile = score, profile
    return best_score, best_profile


def build_adaptive_default(song: dict[str, Any]) -> dict[str, Any]:
    """Fallback character profile when no genre profile matches."""
    text = normalized_song_text(song)
    energy = (song.get("energy") or "medium").lower()
    mood = ((song.get("mood") or ["melancholic"])[0]).lower().strip()
    bpm = song.get("bpm") or 100
    main_color = BRAND_PALETTE.get("main_color", "neon magenta")
    tempo = _bpm_tempo(bpm)

    # 1. Identity, Silhouette, Texture from config
    char_defs = _CHAR_CONFIG.get("adaptive_identities", {})
    energy_group = "fast" if (tempo == "fast" or energy in ("high", "very high")) else ("slow" if (tempo == "slow" or energy in ("low", "very low")) else "medium")
    traits = char_defs.get(energy_group, char_defs.get("medium", {}))
    
    identity = traits.get("identity", "").format(main_color=main_color)
    silhouette = traits.get("silhouette", "").format(main_color=main_color)
    texture = traits.get("texture", "").format(main_color=main_color)

    # 2. Hair rules
    hair = _CHAR_CONFIG.get("hair_default", "").format(main_color=main_color)
    for rule in _CHAR_CONFIG.get("hair_rules", []):
        if any(k in text for k in rule["keys"]):
            hair = rule["hair"].format(main_color=main_color)
            break

    # 3. Outfit rules
    outfit = _CHAR_CONFIG.get("outfit_default", "").format(main_color=main_color)
    for rule in _CHAR_CONFIG.get("outfit_rules", []):
        if any(k in text for k in rule["keys"]):
            outfit = rule["outfit"].format(main_color=main_color)
            break

    # 4. Props
    prop_rules = _PROP_CONFIG.get("rules", [])
    prop = _PROP_CONFIG.get("default", "small glowing symbolic keepsake")
    for rule in prop_rules:
        if _rule_matches(rule, text):
            prop = rule["prop"]
            break

    # 5. Locations (Using _LOC_CONFIG rules)
    locations: list[str] = []
    for rule in _LOC_CONFIG.get("rules", []):
        if _rule_matches(rule, text):
            loc = rule["location"]
            if loc not in locations:
                locations.append(loc)
    
    if len(locations) < 2:
        locations.extend(_LOC_CONFIG.get("fallbacks", ["quiet urban threshold space", "empty street under neon light"]))

    return {
        "name": f"{mood} cinematic anime noir",
        "identity": identity,
        "hair": hair,
        "outfit": outfit,
        "silhouette": silhouette,
        "prop": prop,
        "locations": locations[:4],
        "texture": texture,
    }


def choose_genre_profile(song: dict[str, Any]) -> dict[str, Any]:
    genre_text = song.get("genre", "").lower()
    if genre_text:
        score, profile = _score_profiles(genre_text)
        if score > 0:
            return profile
    score, profile = _score_profiles(normalized_genre_text(song))
    if score > 0:
        return profile
    score, profile = _score_profiles(normalized_song_text(song))
    return profile if score >= 2 else build_adaptive_default(song)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def has_broken_text(text: str) -> bool:
    if not text:
        return False
    mojibake_markers = "里泥愿蹂嫄諛媛怨醫낆쒗꾨뵒쑝"
    marker_count = text.count("?") + sum(text.count(m) for m in mojibake_markers)
    if marker_count >= 3:
        return True
    return bool(re.search(r"[燎-﫿]", text))


def clean_excerpt(value: str, limit: int = 180) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    if has_broken_text(value):
        return "lyrics text appears encoding-damaged; use the section description and song metadata as the visual guide"
    return value[:limit]


# ---------------------------------------------------------------------------
# Visual world builders
# ---------------------------------------------------------------------------

def infer_song_motif(song: dict[str, Any], profile: dict[str, Any]) -> str:
    text = normalized_song_text(song)
    for rule in _MOTIF_CONFIG.get("rules", []):
        if any(k in text for k in rule["keys"]):
            return rule["motif"]
    return f"{profile['prop']} recurring as the song's main visual motif"


_INSTRUMENT_HINTS: dict[str, str] = {
    "piano":      "soft weighted motion, keys-timed gentle camera breath",
    "strings":    "sustained emotional swell, slow arc camera movement",
    "violin":     "precise tight motion, bowing-synced light arcs",
    "guitar":     "rhythmic body accent, pick-strike synced light flash",
    "drums":      "beat-driven cuts, impact-synced rim flash, percussive camera snap",
    "percussion": "sharp staccato cuts, impact light burst on beat",
    "bass":       "deep grounded movement, low-angle weight, subsonic visual pulse",
    "synth":      "ambient layered depth parallax, wave-like neon light drift",
    "choir":      "wide expansive frame, multiple depth layers, breath-held stillness",
    "trumpet":    "bold directional light burst, sharp staccato camera cut",
    "flute":      "airy drifting movement, soft high-key light touches",
    "harp":       "delicate floating motion, soft shimmer light cascade",
}


def instrument_visual_hint(instruments: list[str]) -> str:
    """Return visual motion hints derived from detected instruments (up to 3)."""
    hints: list[str] = []
    for inst in instruments:
        key = inst.lower().strip()
        for name, hint in _INSTRUMENT_HINTS.items():
            if name in key and hint not in hints:
                hints.append(hint)
                break
    return "; ".join(hints[:3])


def lighting_language(song: dict[str, Any], profile: dict[str, Any]) -> str:
    bpm = song.get("bpm") or 0
    tempo_light = _bpm_lighting_desc(bpm)
    return f"{tempo_light}, {profile['texture']}, deep plum shadows, graphite darkness, silver-white rim highlights"


def transition_language(song: dict[str, Any], profile: dict[str, Any], motif: str) -> str:
    bpm = song.get("bpm") or 0
    rhythm = _bpm_transition_desc(bpm)
    return f"{rhythm} through {motif}, neon reflections, and {profile['texture']}"


def normalize_symbols(symbols: list[str], signature_prop: str) -> list[str]:
    normalized = []
    for symbol in symbols:
        value = str(symbol).replace("paper crane", signature_prop).strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def infer_locations(song: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    text = normalized_song_text(song)
    locations: list[str] = []
    for rule in _LOC_CONFIG.get("rules", []):
        if _rule_matches(rule, text):
            loc = rule["location"]
            if loc not in locations:
                locations.append(loc)
    locations.extend(profile.get("locations", []))
    return list(dict.fromkeys(locations))[:5]


def create_visual_world(song: dict[str, Any], emotion: dict[str, Any]) -> dict[str, Any]:
    profile = choose_genre_profile(song)
    motif = infer_song_motif(song, profile)
    locations = infer_locations(song, profile)
    symbols = normalize_symbols(
        [motif, *emotion.get("visual_symbolism", []), *song.get("visual_cues", []), profile["prop"]], profile["prop"]
    )[:8]
    return {
        "song_slug": slugify(song["title"]),
        "visual_identity": f"{profile['name']} within {BRAND_PALETTE['visual_identity']}",
        "genre_profile": profile["name"],
        "song_motif": motif,
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
        "core_locations": locations,
        "recurring_symbols": symbols,
        "lighting_language": lighting_language(song, profile),
        "transition_language": transition_language(song, profile, motif),
        "instrument_hint": instrument_visual_hint(song.get("instruments", [])),
        "negative_style_rules": song.get("negative_tags", []),
    }


def create_protagonist(song: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    profile = choose_genre_profile(song)
    main_color = BRAND_PALETTE.get("main_color", "neon magenta")
    mood_words = ", ".join(song.get("mood", ["melancholic"]))
    motif = world.get("song_motif", profile["prop"])
    return {
        "role": "unique protagonist for this song",
        "identity": profile["identity"],
        "age_style": "anime character, stylized and non-photorealistic",
        "hair": _apply_color(profile["hair"], main_color),
        "outfit": _apply_color(profile["outfit"], main_color),
        "silhouette": profile["silhouette"],
        "emotional_state": mood_words,
        "signature_prop": profile["prop"],
        "accent_detail": f"{BRAND_PALETTE['main_color']} remains dominant, but the prop and gestures follow this song motif: {motif}",
        "consistency_rules": [
            "Keep the same face, hairstyle, outfit, body proportions, and signature prop within this song only.",
            "Do not reuse this character design for a different song unless the user explicitly requests a series identity.",
            "Let pose, expression, setting, and action change per section according to lyrics, genre, intensity, and BPM.",
            "Use anime cinematic styling, never live-action realism.",
            "First generate Step 00 (character turnaround model sheet) before creating any scene image.",
            "Attach that same character model sheet when generating every scene image for this song.",
            "Attach the final scene image as the primary image-to-video reference when generating the video for that scene.",
        ],
        "reference_workflow": [
            "Generate a clean song-specific character turnaround model sheet before scene production.",
            "Use the same model sheet as an input/reference for every scene image prompt in this song.",
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
            f"prop close-up of {profile['prop']}",
        ],
    }


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
            f"색상톤은 유지합니다: {BRAND_PALETTE['palette_rule']}.",
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

    # Named resolution sections
    if stages.get(section) == "resolution":
        return "resolution"

    # Bridge always climax
    if section == "Bridge":
        return "climax"

    # Chorus at or past the ratio position → climax
    if section in climax_sections and index >= max(1, int(total * ratio)):
        return "climax"

    return stages.get(section, "development")


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


def infer_lyric_idea(section: dict[str, Any]) -> str:
    lyrics = clean_excerpt(section.get("lyrics", ""), 220)
    description = section.get("description", "").strip()
    if lyrics and "encoding-damaged" not in lyrics:
        return f"lyric cue: {lyrics}"
    if description:
        return f"music cue: {description}"
    return f"{section['name']} emotional cue"


def choose_location(section: dict[str, Any], world: dict[str, Any], index: int, used_locations: list[str] | None = None) -> str:
    text = f"{section.get('lyrics', '')} {section.get('description', '')}".lower()
    section_name = section["name"]
    used = used_locations or []

    # Resolution sections prefer dawn/skyline locations
    if _SECTIONS_CONFIG.get("story_stages", {}).get(section_name) == "resolution":
        dawn_keywords = _SECTIONS_CONFIG.get("resolution_location_keywords", ["dawn", "skyline", "rooftop", "sunrise"])
        dawn_locs = [loc for loc in world["core_locations"] if any(k in loc.lower() for k in dawn_keywords)]
        if dawn_locs:
            return dawn_locs[0]

    # Keyword-driven match (word-boundary aware, skips already-used locations)
    for rule in _LOC_CONFIG.get("rules", []):
        if _rule_matches(rule, text):
            loc = rule["location"]
            if loc not in used:
                return loc

    # Fallback: prefer unused core locations
    core = world["core_locations"]
    unused = [loc for loc in core if loc not in used]
    if unused:
        return unused[0]
    return core[(index - 1) % len(core)]


def choose_scene_action(section: dict[str, Any], lyric_idea: str, protagonist: dict[str, Any]) -> str:
    text         = f"{section.get('lyrics', '')} {section.get('description', '')}".lower()
    prop         = protagonist["signature_prop"]
    section_name = section["name"]

    def fmt(template: str) -> str:
        return template.replace("{prop}", prop)

    # Section-specific overrides from config (checked before generic keyword scan)
    overrides = _SECTIONS_CONFIG.get("action_overrides", {})
    if section_name in overrides:
        ov = overrides[section_name]
        # Intro: music-cue shortcut
        if "music_cue_prefix" in ov and lyric_idea.startswith(ov["music_cue_prefix"]):
            return fmt(ov["music_cue_action"])
        # Bridge / Outro: conditional keyword check
        if "hide_keywords" in ov and any(k in text for k in ov["hide_keywords"]):
            return fmt(ov["hide_action"])
        if "cry_keywords" in ov and any(k in text for k in ov["cry_keywords"]):
            return fmt(ov["cry_action"])
        # Chorus: smile-specific check
        if "smile_keywords" in ov and any(k in text for k in ov["smile_keywords"]):
            return fmt(ov["smile_action"])
        # Section has a default override (Bridge, Outro, Chorus)
        if "default_action" in ov:
            return fmt(ov["default_action"])

    # Generic keyword scan from config
    for rule in _ACTION_CONFIG.get("rules", []):
        if any(k in text for k in rule["keys"]):
            return fmt(rule["action"])

    return fmt(_ACTION_CONFIG.get("default", "shows the section emotion through posture, hand movement, and the recurring {prop}"))


def choose_symbolic_focus(section: dict[str, Any], world: dict[str, Any], protagonist: dict[str, Any]) -> str:
    text = f"{section.get('lyrics', '')} {section.get('description', '')}".lower()
    for rule in _FOCUS_CONFIG.get("rules", []):
        if any(k in text for k in rule["keys"]):
            return rule["focus"]
    fallback = world.get("song_motif") or protagonist["signature_prop"]
    return fallback.replace("paper crane", protagonist["signature_prop"])


def choose_shot(section: dict[str, Any], emotion: str, song: dict[str, Any]) -> str:
    name  = section["name"]
    bpm   = song.get("bpm") or 0
    text  = f"{section.get('lyrics', '')} {section.get('description', '')}".lower()
    tempo = _bpm_tempo(bpm)

    # Fixed section overrides (Intro, Bridge, Outro)
    section_overrides = _SHOT_CONFIG.get("section_overrides", {})
    if name in section_overrides:
        return section_overrides[name]

    # Chorus: BPM-sensitive shot
    if name == "Chorus":
        if tempo == "fast":
            return _SHOT_CONFIG.get("chorus_fast_shot", "dynamic forward tracking shot, low angle, strong beat-synced foreground streaks")
        return _SHOT_CONFIG.get("chorus_default_shot", "forward tracking shot with widening background parallax and brighter rim light")

    # Mirror/reflection keyword: content-driven close-up
    mirror_keys = _SHOT_CONFIG.get("mirror_keywords", ["거울", "mirror", "반사"])
    if any(k in text for k in mirror_keys):
        return _SHOT_CONFIG.get("mirror_shot", "medium close-up reflected in a dark surface with neon fracture light framing the face")

    # Emotion-driven shot
    emotion_shots = _SHOT_CONFIG.get("emotion_shots", {})
    if emotion in emotion_shots:
        return emotion_shots[emotion]

    # Keyword-driven fallback shots
    for rule in _SHOT_CONFIG.get("keyword_shots", []):
        if any(k in text for k in rule["keys"]):
            return rule["shot"]

    return _SHOT_CONFIG.get("default", "medium shot with lyric-specific hand action and soft parallax background")


def choose_movement(section: dict[str, Any], song: dict[str, Any]) -> str:
    name    = section["name"]
    tempo   = _bpm_tempo(song.get("bpm"))
    patterns = _SECTIONS_CONFIG.get("movement_patterns", {})
    section_patterns = patterns.get(name, {})

    if "any" in section_patterns:
        return section_patterns["any"]
    if tempo in section_patterns:
        return section_patterns[tempo]
    if "medium" in section_patterns:
        return section_patterns["medium"]
    return _SECTIONS_CONFIG.get("default_movement", "song-tempo-aware cinematic drift")


def video_rhythm(song: dict[str, Any], section: dict[str, Any]) -> str:
    bpm       = song.get("bpm")
    intensity = section.get("intensity", "medium")
    tempo     = _bpm_tempo(bpm)
    desc      = _BPM_THRESHOLDS.get(tempo, {}).get("rhythm_desc", "measured musical motion, camera accents every phrase")
    if bpm:
        return f"{bpm} BPM: {desc}, intensity {intensity}"
    return f"tempo unknown: follow the section intensity {intensity} with coherent cinematic motion"


def generate_scenes(song: dict[str, Any], emotion: dict[str, Any], world: dict[str, Any], protagonist: dict[str, Any]) -> list[dict[str, Any]]:
    scenes: list[dict[str, Any]] = []
    used_locations: list[str] = []
    progression_by_section = {item["section"]: item for item in emotion.get("emotional_progression", [])}

    for index, section in enumerate(song.get("sections", []), start=1):
        section_emotion = progression_by_section.get(section["name"], {})
        lyric_excerpt   = clean_excerpt(section.get("lyrics", ""))
        lyric_idea      = infer_lyric_idea(section)
        location        = choose_location(section, world, index, used_locations)
        used_locations.append(location)
        scene_action    = choose_scene_action(section, lyric_idea, protagonist)
        symbolic_focus  = choose_symbolic_focus(section, world, protagonist)
        shot            = choose_shot(section, section_emotion.get("emotion", emotion.get("primary_emotion", "melancholic")), song)
        movement        = choose_movement(section, song)

        scenes.append({
            "scene_number":         index,
            "music_section":        section["name"],
            "lyrics_excerpt":       lyric_excerpt,
            "lyric_visual_idea":    lyric_idea,
            "emotion":              section_emotion.get("emotion", emotion.get("primary_emotion", "melancholic")),
            "intensity":            section.get("intensity", "medium"),
            "environment":          location,
            "lighting":             section_emotion.get("lighting", world["lighting_language"]),
            "camera_direction":     shot,
            "movement":             movement,
            "video_rhythm":         video_rhythm(song, section),
            "cinematic_style":      world["visual_identity"],
            "symbolism":            section_emotion.get("visual_symbols", world["recurring_symbols"]),
            "symbolic_focus":       symbolic_focus,
            "scene_action":         scene_action,
            "protagonist_continuity": protagonist["identity"],
            "section_description":  section.get("description", ""),
        })
    return scenes


def apply_story_arc_to_scenes(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = len(scenes)
    enriched = []
    for index, scene in enumerate(scenes):
        stage = story_stage(index + 1, total, scene["music_section"])
        beat_en = story_beat_en(scene, stage)
        enriched.append({
            **scene,
            "story_stage":             stage,
            "story_beat_ko":           beat_en,
            "story_beat_en":           beat_en,
            "continuity_from_previous_ko": "Continue emotional and visual continuity from the previous section.",
            "continuity_to_next_ko":   "Lead the motion and symbol into the next section.",
            "story_prompt_context": (
                f"Narrative continuity: this is the {stage} beat of the music video. "
                f"Keep the song-specific protagonist and signature prop consistent, but make this scene distinct through "
                f"the section lyric idea, location, action, camera, and BPM-aware motion. Story beat: {beat_en}"
            ),
        })
    return enriched


# ---------------------------------------------------------------------------
# Prompt assembly — anime + limited-color constraints applied here
# ---------------------------------------------------------------------------

def character_visual(protagonist: dict[str, Any]) -> str:
    return (
        f"{protagonist['identity']}, {protagonist['hair']}, {protagonist['outfit']}, "
        f"{protagonist['silhouette']}, holding {protagonist['signature_prop']}"
    )


def compact_lyric_idea(scene: dict[str, Any]) -> str:
    idea = scene.get("lyric_visual_idea", "")
    return idea.replace("lyric cue: ", "").replace("music cue: ", "")[:220]


def image_prompt(scene: dict[str, Any], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    color_balance = COLOR_BALANCE_BY_STAGE.get(scene.get("story_stage", "development"), COLOR_BALANCE_BY_STAGE.get("development", ""))
    symbols = ", ".join(normalize_symbols(scene.get("symbolism", [])[:4], protagonist["signature_prop"]))
    inst_hint = world.get("instrument_hint", "")
    lines = [
        f"{scene['camera_direction']} in {scene['environment']}.",
        f"{character_visual(protagonist)}.",
        f"Action: {scene['scene_action']}.",
        f"Lyric mood: {compact_lyric_idea(scene)}.",
        f"Visual symbol: {scene['symbolic_focus']}; supporting symbols: {symbols}.",
        f"{scene['emotion']} {world['genre_profile']} mood, {scene['lighting']}.",
        f"Instrument-driven motion: {inst_hint}." if inst_hint else "",
        f"{BRAND_PALETTE['palette_rule']}; {color_balance}.",
        f"{_STYLE_POSITIVE}.",
        f"{_STYLE_NEGATIVE}.",
    ]
    return " ".join(line for line in lines if line.strip())


def video_prompt(scene: dict[str, Any], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    color_balance = COLOR_BALANCE_BY_STAGE.get(scene.get("story_stage", "development"), COLOR_BALANCE_BY_STAGE.get("development", ""))
    inst_hint = world.get("instrument_hint", "")
    lines = [
        "Image-to-video from the attached scene image.",
        f"Preserve the character design: {protagonist['hair']}, {protagonist['outfit']}, {protagonist['signature_prop']}.",
        f"Camera motion: {scene['movement']}; composition stays {scene['camera_direction']}.",
        f"Action over time: {scene['scene_action']}.",
        f"Musical timing: {scene['video_rhythm']}.",
        f"Instrument-driven motion: {inst_hint}." if inst_hint else "",
        f"Lyric mood: {compact_lyric_idea(scene)}.",
        f"Atmosphere: {world['lighting_language']}; symbolic motion: {scene['symbolic_focus']}.",
        f"Palette: {BRAND_PALETTE['palette_rule']}; {color_balance}.",
        f"Smooth coherent anime motion, subtle parallax, clean motivated transition at the end. {_VIDEO_NEGATIVE}.",
    ]
    return " ".join(line for line in lines if line.strip())


# ---------------------------------------------------------------------------
# Character sheet generators
# ---------------------------------------------------------------------------

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
    rules    = "\n".join(f"- {rule}" for rule in protagonist["consistency_rules"])
    workflow = "\n".join(f"- {step}" for step in protagonist.get("reference_workflow", []))
    views    = "\n".join(f"- {view}" for view in protagonist.get("required_reference_views", []))
    return (
        "# Character Turnaround Model Sheet Prompt\n\n"
        "Create the master character turnaround model sheet for this song. This model sheet will be attached "
        "as the identity reference for every later scene image, and optionally as a secondary reference for video generation.\n\n"
        "Required views:\n"
        f"{views}\n\n"
        f"Character design: {protagonist['identity']}, {protagonist['age_style']}, {protagonist['hair']}, "
        f"{protagonist['outfit']}, {protagonist['silhouette']}. Signature prop: {protagonist['signature_prop']}. "
        f"Accent detail: {protagonist['accent_detail']}. Visual world: {world['visual_identity']}.\n\n"
        "Composition: clean anime production model sheet, neutral simple background, aligned character views at the same scale, "
        "full body visible from head to toe in each turnaround pose, clear face close-up, clear hairstyle silhouette, "
        f"clear outfit seams, clear signature prop, no dramatic camera angle, no cropped limbs, no environmental scene, no action pose. "
        f"{BRAND_PALETTE['palette_rule']}. Non-photorealistic, no live action, no text, no watermark.\n\n"
        "Consistency rules:\n"
        f"{rules}\n\n"
        "Production workflow:\n"
        f"{workflow}\n"
    )


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
        "4. Keep the fixed neon magenta/cyber pink palette, but vary action, location, rhythm, and symbolism per song and section.",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _generate_and_write(song: dict, emotion: dict) -> None:
    world       = create_visual_world(song, emotion)
    protagonist = create_protagonist(song, world)
    scenes      = generate_scenes(song, emotion, world, protagonist)
    story_arc   = create_story_arc(song, emotion, world, protagonist)
    scenes      = apply_story_arc_to_scenes(scenes)

    scene_payload = {
        "song_title": song["title"],
        "story_arc":  story_arc,
        "visual_world": world,
        "protagonist": protagonist,
        "character_model_sheet": {
            "step":    0,
            "purpose": "Generate this song-specific character turnaround model sheet before any scene image.",
            "prompt_file": "prompts/image_prompts/00_character_turnaround_model_sheet.md",
            "character_reference_prompt": character_reference_prompt(protagonist, world),
            "required_views": protagonist.get("required_reference_views", []),
            "usage": [
                "Attach this model sheet as the identity reference for every scene image prompt in this song.",
                "Use each generated scene image as the primary image-to-video reference.",
                "If the video tool supports multiple references, attach this model sheet as a secondary video reference.",
            ],
        },
        "scenes": [
            {**scene, "image_prompt": image_prompt(scene, protagonist, world), "video_prompt": video_prompt(scene, protagonist, world)}
            for scene in scenes
        ],
    }
    cinematic_style = {
        "style_name":         world["visual_identity"],
        "genre_profile":      world["genre_profile"],
        "song_motif":         world["song_motif"],
        "color_rules":        {**world["color_palette"]},
        "camera_language":    [scene["camera_direction"] for scene in scenes],
        "transition_language": world["transition_language"],
        "negative_style_rules": world["negative_style_rules"],
    }

    write_json(PROJECT_ROOT / "analysis"   / "visual_world.json",    world)
    write_json(PROJECT_ROOT / "analysis"   / "cinematic_style.json",  cinematic_style)
    write_json(PROJECT_ROOT / "character"  / "protagonist_bible.json", protagonist)
    write_text(PROJECT_ROOT / "character"  / "character_prompt.md",    character_prompt(protagonist, world))
    write_text(PROJECT_ROOT / "character"  / "character_reference_prompt.md", character_reference_prompt(protagonist, world))
    write_json(PROJECT_ROOT / "storyboard" / "story_arc.json",        story_arc)
    write_text(PROJECT_ROOT / "storyboard" / "story_summary.md",      write_story_summary_markdown(story_arc, scenes))
    write_json(PROJECT_ROOT / "storyboard" / "scene_list.json",       scene_payload)
    write_text(PROJECT_ROOT / "storyboard" / "storyboard_prompts.md", write_storyboard_markdown(scenes, protagonist, world))
    write_text(PROJECT_ROOT / "storyboard" / "camera_directions.md",  write_camera_markdown(scenes))
    print("Wrote visual world, protagonist bible, and storyboard files")


def run(song_path: Path | None = None, emotion_path: Path | None = None, style_id: str | None = None) -> None:
    ensure_directories()
    select_theme(style_id)
    song    = read_json(song_path    or (PROJECT_ROOT / "input"    / "song_master.json"))
    _inject_song_color(pick_main_color(song))
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
