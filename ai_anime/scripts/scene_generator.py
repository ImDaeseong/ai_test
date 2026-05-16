from __future__ import annotations

import argparse
import hashlib
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
_INFERENCE_CONFIG = load_config("song_inference")

GENRE_PROFILES: list[dict[str, Any]] = _GENRE_CONFIG if isinstance(_GENRE_CONFIG, list) else []

# Global anime + limited-color constraints (enforced on every prompt)
_ANIME            = _STYLE_CONFIG.get("global_anime_constraints", {})
_STYLE_POSITIVE   = ", ".join(_ANIME.get("style_enforcement", []))
_STYLE_NEGATIVE   = ". ".join(_ANIME.get("negative_enforcement", []))
_VIDEO_NEGATIVE   = ". ".join(_ANIME.get("video_negative_enforcement", []))

BRAND_PALETTE: dict[str, Any] = {}
COLOR_BALANCE_BY_STAGE: dict[str, Any] = {}
ACTIVE_STYLE_ID = ""


def select_theme(style_id: str | None = None) -> None:
    global BRAND_PALETTE, COLOR_BALANCE_BY_STAGE, ACTIVE_STYLE_ID
    style_id = style_id or _STYLE_CONFIG.get("default_style", "dreamy_synth")
    style_data = _STYLE_CONFIG.get("styles", {}).get(style_id, {})
    if not style_data:
        first_key = next(iter(_STYLE_CONFIG.get("styles", {}).keys()), "dreamy_synth")
        style_id = first_key
        style_data = _STYLE_CONFIG.get("styles", {}).get(first_key, {})
    ACTIVE_STYLE_ID = style_id
    BRAND_PALETTE = style_data.get("brand_palette", {})
    COLOR_BALANCE_BY_STAGE = style_data.get("color_balance_by_stage", {})


select_theme()

_COLOR_SUB = re.compile(r"neon magenta(?: and cyber pink)?|cyber[- ]?pink", re.IGNORECASE)

# Ambient palette substitution — replaces cyber_noir fallback colors when a different style is active
_PALETTE_SHADOW_SUB    = re.compile(r"deep\s+plum(?:\s+and\s+dark\s+violet)?", re.IGNORECASE)
_PALETTE_SECONDARY_SUB = re.compile(
    r"(?:(?:subtle|faint|soft|gentle|minimal|unsteady|restrained)\s+)?"
    r"icy\s+cyan"
    r"(?:\s+(?:secondary\s+)?(?:pavement\s+)?(?:reflections?|edge\s+light|fringe|glow|flickers?))?",
    re.IGNORECASE,
)
_PALETTE_HIGHLIGHT_SUB = re.compile(
    r"silver[-\s]white(?:\s+(?:rim\s+)?(?:highlights?|light|glow|emphasis|bloom|shimmer))?"
    r"|silver\s+rim\s+(?:light|highlights?)",
    re.IGNORECASE,
)
_CYBER_STYLE_SUB = re.compile(r"\bcyber(?:punk|[-\s]?noir|[-\s]?anime)?\b", re.IGNORECASE)
_NEON_STYLE_SUB = re.compile(r"\bneon(?:[-\s](?:lit|tinted|edged|reflected))?\b", re.IGNORECASE)
_FUTURISTIC_STYLE_SUB = re.compile(r"\bfuturistic\b", re.IGNORECASE)


def _inject_song_color(main_color: str) -> None:
    """Override BRAND_PALETTE main color while preserving style-specific highlights and identity."""
    style_highlight = BRAND_PALETTE.get("highlight", "silver-white rim highlights")
    style_secondary = BRAND_PALETTE.get("secondary_light", "subtle secondary reflections")
    BRAND_PALETTE["main_color"] = main_color
    BRAND_PALETTE["visual_identity"] = _COLOR_SUB.sub(
        main_color, BRAND_PALETTE.get("visual_identity", "dark anime")
    )
    BRAND_PALETTE["palette_rule"] = (
        f"limited-color anime palette: {main_color} dominant, "
        f"dark shadows, near-black backgrounds, {style_secondary}, {style_highlight}"
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
    template = _bpm_desc(bpm, "lighting_desc", "measured {main_color} pulses with subtle secondary light response")
    return template.format(main_color=BRAND_PALETTE.get("main_color", "accent color"))


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


def _has_any(text: str, terms: list[str]) -> bool:
    return any(term.lower() in text for term in terms)


def match_inference_profile_text(text: str) -> dict[str, Any]:
    normalized = text.lower()
    for profile in _INFERENCE_CONFIG.get("profiles", []):
        if _has_any(normalized, profile.get("keys", [])):
            return profile
    return {}


def match_inference_profile_song(song: dict[str, Any]) -> dict[str, Any]:
    return match_inference_profile_text(normalized_song_text(song))


def match_inference_profile_world(world: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        [
            world.get("visual_identity", ""),
            world.get("genre_profile", ""),
            world.get("song_motif", ""),
            " ".join(world.get("core_locations", [])),
            " ".join(world.get("recurring_symbols", [])),
        ]
    )
    return match_inference_profile_text(text)


def pick_main_color(song: dict[str, Any]) -> str:
    """Derive one accent color from song genre/mood/atmosphere."""
    text = normalized_song_text(song)
    inference_profile = match_inference_profile_song(song)
    if inference_profile.get("main_color"):
        return inference_profile["main_color"]
    for rule in _COLOR_CONFIG.get("rules", []):
        if any(k in text for k in rule["keys"]):
            return rule["color"]
    return _COLOR_CONFIG.get("default", "neon magenta")


def _apply_color(text: str, color: str) -> str:
    """Replace hardcoded color keywords in genre profile strings with the song's color."""
    return _COLOR_SUB.sub(color, text)


def _apply_full_palette(text: str) -> str:
    """Replace all cyber_noir ambient color tokens with the active style's palette values."""
    text = _apply_color(text, BRAND_PALETTE.get("main_color", "neon magenta"))
    text = _PALETTE_SHADOW_SUB.sub(BRAND_PALETTE.get("shadow_color", "deep plum and dark violet"), text)
    text = _PALETTE_SECONDARY_SUB.sub(BRAND_PALETTE.get("secondary_light", "subtle icy cyan"), text)
    text = _PALETTE_HIGHLIGHT_SUB.sub(BRAND_PALETTE.get("highlight", "silver-white rim highlights"), text)
    if ACTIVE_STYLE_ID != "cyber_noir":
        text = _CYBER_STYLE_SUB.sub("stylized", text)
        text = _NEON_STYLE_SUB.sub("accent-light", text)
        text = _FUTURISTIC_STYLE_SUB.sub("song-specific cinematic", text)
    return text


def _stable_choice(options: list[str], seed: str, salt: str) -> str:
    """Pick a deterministic option so one song stays consistent while other songs diverge."""
    if not options:
        return ""
    digest = hashlib.sha256(f"{seed}|{salt}".encode("utf-8")).hexdigest()
    return options[int(digest[:8], 16) % len(options)]


def song_character_seed(song: dict[str, Any]) -> str:
    sections = "|".join(section.get("name", "") for section in song.get("sections", []))
    return "|".join(
        str(value)
        for value in [
            song.get("title", ""),
            song.get("genre", ""),
            song.get("bpm", ""),
            song.get("energy", ""),
            ",".join(song.get("mood", [])),
            sections,
        ]
    )


def song_unique_traits(song: dict[str, Any], main_color: str) -> dict[str, str]:
    seed = song_character_seed(song)
    variants = _CHAR_CONFIG.get("song_unique_variants", {})
    title = song.get("title", "").strip()

    def pick(key: str) -> str:
        value = _stable_choice(variants.get(key, []), seed, key)
        return value.format(main_color=main_color, title=title)

    return {
        "archetype": pick("archetypes"),
        "face_shape": pick("face_shapes"),
        "hair_base": pick("hair_bases"),
        "face": pick("face_marks"),
        "hair": pick("hair_variants"),
        "body": pick("body_silhouettes"),
        "outfit_base": pick("outfit_bases"),
        "outfit": pick("outfit_accents"),
        "accessory": pick("accessories"),
        "gesture": pick("gesture_signatures"),
        "identity_lock": pick("identity_locks"),
    }


def _with_color(text: str, main_color: str) -> str:
    return text.format(main_color=main_color) if text else ""


def infer_subject_profile(song: dict[str, Any], main_color: str) -> dict[str, Any]:
    """Infer whether the MV should center a person, pair/group, object, or environment."""
    positive_tags = [t for t in song.get("style_tags", []) if not t.lstrip().startswith(("‑", "-"))]
    text = " ".join(
        [
            song.get("title", ""),
            song.get("genre", ""),
            " ".join(positive_tags),
            " ".join(song.get("mood", [])),
            " ".join(song.get("instruments", [])),
            song.get("atmosphere", ""),
            " ".join(song.get("visual_cues", [])),
        ]
    ).lower()
    subject_rules = _CHAR_CONFIG.get("subject_rules", {})
    gender_rules = _CHAR_CONFIG.get("gender_presentation_rules", {})

    def rule_matches(rule: dict[str, Any]) -> bool:
        return any(_key_matches(str(k).lower(), text) for k in rule.get("keys", []))

    subject_type = "human_solo"
    subject_rule: dict[str, Any] = {}
    for candidate in ["human_duo", "group", "object_symbol", "environment_only"]:
        rule = subject_rules.get(candidate, {})
        if rule and rule_matches(rule):
            subject_type = candidate
            subject_rule = rule
            break

    male = rule_matches(gender_rules.get("male", {}))
    female = rule_matches(gender_rules.get("female", {}))
    androgynous = rule_matches(gender_rules.get("androgynous", {}))
    has_lead_vocal = any(
        _key_matches(k, text)
        for k in [
            "vocal",
            "vocals",
            "voice",
            "singer",
            "male vocal",
            "male vocals",
            "female vocal",
            "female vocals",
            "dry male vocals",
            "upfront vocal presence",
            "lead vocal",
        ]
    )
    full_instrumental = any(
        phrase in text
        for phrase in [
            "instrumental only",
            "no vocals",
            "no lead vocal",
            "piano only",
            "strings only",
        ]
    ) or text.strip() == "instrumental"
    if subject_type == "environment_only" and has_lead_vocal and not full_instrumental:
        subject_type = "human_solo"
        subject_rule = {}
    if subject_type in ("environment_only", "object_symbol"):
        gender = "non-human / symbolic"
    elif male and female:
        gender = "mixed-gender"
    elif female:
        gender = gender_rules.get("female", {}).get("description", "female-presenting")
    elif male:
        gender = gender_rules.get("male", {}).get("description", "male-presenting")
    elif androgynous:
        gender = gender_rules.get("androgynous", {}).get("description", "androgynous")
    else:
        gender = "androgynous"

    subject_label = {
        "human_solo": "one human lead character",
        "human_duo": "two human lead characters",
        "group": "small human ensemble with a center lead",
        "environment_only": "environment-led music video",
        "object_symbol": "symbolic object-led music video",
    }.get(subject_type, "one human lead character")

    subject_prop = _with_color(subject_rule.get("prop", ""), main_color)
    if subject_type == "object_symbol":
        if any(_key_matches(k, text) for k in ["perfume", "scent", "향기", "향"]):
            subject_prop = f"translucent perfume-like memory vial releasing {main_color} light and scent trails"
        elif any(_key_matches(k, text) for k in ["letter", "편지"]):
            subject_prop = f"folded handwritten letter glowing with {main_color} edges"
        elif any(_key_matches(k, text) for k in ["photo", "사진"]):
            subject_prop = f"old photo fragment carrying a soft {main_color} reflection"
        elif any(_key_matches(k, text) for k in ["ring", "반지"]):
            subject_prop = f"small ring catching a precise {main_color} rim light"

    return {
        "subject_type": subject_type,
        "subject_label": subject_label,
        "gender_presentation": gender,
        "identity_prefix": subject_rule.get("identity_prefix", ""),
        "identity": _with_color(subject_rule.get("identity", ""), main_color),
        "silhouette": _with_color(subject_rule.get("silhouette", ""), main_color),
        "prop": subject_prop,
        "reference_views": subject_rule.get("reference_views", []),
        "reference_note": subject_rule.get("reference_note", ""),
    }


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
            prop = _apply_full_palette(rule["prop"])
            break

    # 5. Locations (Using _LOC_CONFIG rules)
    locations: list[str] = []
    for rule in _LOC_CONFIG.get("rules", []):
        if _rule_matches(rule, text):
            loc = _apply_full_palette(rule["location"])
            if loc not in locations:
                locations.append(loc)
    
    if len(locations) < 2:
        locations.extend(
            _apply_full_palette(loc)
            for loc in _LOC_CONFIG.get("fallbacks", ["quiet emotional threshold space", "empty street under accent light"])
        )

    _adaptive_style_map = {"fast": "urban_noir", "slow": "warm_acoustic", "medium": "dreamy_synth"}
    return {
        "name": f"{mood} cinematic anime noir",
        "style_id": _adaptive_style_map.get(energy_group, _STYLE_CONFIG.get("default_style", "dreamy_synth")),
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
# Visual world builders
# ---------------------------------------------------------------------------

def infer_song_motif(song: dict[str, Any], profile: dict[str, Any]) -> str:
    main_color = BRAND_PALETTE.get("main_color", "neon magenta")
    text = normalized_song_text(song)
    inference_profile = match_inference_profile_song(song)
    if inference_profile.get("motif_template"):
        return _apply_full_palette(inference_profile["motif_template"].format(main_color=main_color))
    for rule in _MOTIF_CONFIG.get("rules", []):
        if any(k in text for k in rule["keys"]):
            return _apply_full_palette(rule["motif"])
    return f"{_apply_full_palette(profile['prop'])} recurring as the song's main visual motif"


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
    return _apply_full_palette("; ".join(hints[:3]))


def lighting_language(song: dict[str, Any], profile: dict[str, Any]) -> str:
    bpm = song.get("bpm") or 0
    tempo_light = _bpm_lighting_desc(bpm)
    shadow = BRAND_PALETTE.get("shadow_color", "deep plum and dark violet shadows")
    highlight = BRAND_PALETTE.get("highlight", "silver-white rim highlights")
    return _apply_full_palette(f"{tempo_light}, {profile['texture']}, {shadow}, {highlight}")


def transition_language(song: dict[str, Any], profile: dict[str, Any], motif: str) -> str:
    bpm = song.get("bpm") or 0
    rhythm = _bpm_transition_desc(bpm)
    secondary = BRAND_PALETTE.get("secondary_accent", "accent light")
    return _apply_full_palette(f"{rhythm} through {motif}, {secondary} reflections, and {profile['texture']}")


def normalize_symbols(symbols: list[str]) -> list[str]:
    normalized = []
    for symbol in symbols:
        value = str(symbol).strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def infer_locations(song: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    text = normalized_song_text(song)
    locations: list[str] = []
    inference_profile = match_inference_profile_song(song)
    if inference_profile:
        locations.extend(_apply_full_palette(loc) for loc in profile.get("locations", []))
        for rule in inference_profile.get("extra_locations", []):
            if _has_any(text, rule.get("keys", [])):
                locations.append(_apply_full_palette(rule["location"]))
        return list(dict.fromkeys(locations))[:5]
    for rule in _LOC_CONFIG.get("rules", []):
        if _rule_matches(rule, text):
            loc = _apply_full_palette(rule["location"])
            if loc not in locations:
                locations.append(loc)
    locations.extend(_apply_full_palette(loc) for loc in profile.get("locations", []))
    return list(dict.fromkeys(locations))[:5]


def create_visual_world(song: dict[str, Any], emotion: dict[str, Any]) -> dict[str, Any]:
    profile = choose_genre_profile(song)
    colored_prop = _apply_full_palette(profile["prop"])
    motif = infer_song_motif(song, profile)
    locations = infer_locations(song, profile)
    symbols = normalize_symbols(
        [motif, *emotion.get("visual_symbolism", []), *song.get("visual_cues", []), colored_prop]
    )
    inference_profile = match_inference_profile_song(song)
    blocked_symbols = {symbol.lower() for symbol in inference_profile.get("symbol_filter", [])}
    if blocked_symbols:
        symbols = [symbol for symbol in symbols if symbol.strip().lower() not in blocked_symbols]
    symbols = symbols[:8]
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
        "secondary_accent_color": BRAND_PALETTE.get("secondary_accent", "icy cyan"),
        "highlight_color": BRAND_PALETTE.get("highlight_color_name", "silver white"),
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
    colored_prop = _apply_full_palette(profile["prop"])
    unique = song_unique_traits(song, main_color)
    subject = infer_subject_profile(song, main_color)

    if subject["subject_type"] in ("environment_only", "object_symbol"):
        subject_prop = subject.get("prop") or colored_prop
        reference_views = subject.get("reference_views") or [
            "main subject front reference",
            "main subject side/detail reference",
            "main subject in environment",
            "lighting and motif close-up",
        ]
        return {
            "role": "unique primary visual subject for this song",
            "subject_type": subject["subject_type"],
            "subject_label": subject["subject_label"],
            "gender_presentation": subject["gender_presentation"],
            "identity": subject.get("identity") or f"{subject['subject_label']} shaped by {world['genre_profile']}",
            "age_style": "non-human or environment-led anime MV subject, stylized and non-photorealistic",
            "hair": "",
            "outfit": "",
            "silhouette": subject.get("silhouette") or "clear non-human focal silhouette",
            "emotional_state": mood_words,
            "signature_prop": subject_prop,
            "accent_detail": (
                f"{BRAND_PALETTE['main_color']} remains dominant. The main visual focus is {subject['subject_label']}, "
                f"not a reusable human protagonist. This subject system belongs only to '{song.get('title', 'this song')}'"
            ),
            "consistency_rules": [
                f"Primary subject type: {subject['subject_type']} ({subject['subject_label']}).",
                "Do not introduce a full-body recurring lead human unless the scene explicitly needs a partial silhouette.",
                "Keep the same object/environment motif, palette, and spatial identity within this song only.",
                "Do not reuse another song's character face, hairstyle, outfit, or body silhouette.",
                "Use anime cinematic styling, never live-action realism.",
                "First generate Step 00 as the subject reference sheet before creating any scene image.",
                "Attach that same subject reference sheet when generating every scene image for this song.",
            ],
            "reference_workflow": [
                "Generate a clean song-specific subject reference sheet before scene production.",
                "Use the same subject reference sheet as an input/reference for every scene image prompt in this song.",
                "After each scene image is approved, use that scene image as the primary image-to-video input for that scene.",
            ],
            "required_reference_views": reference_views,
        }

    unique_identity_parts = [
        unique.get("archetype", ""),
        f"{subject['gender_presentation']} {subject['subject_label']}",
        subject.get("identity_prefix", ""),
        profile["identity"],
        f"face structure: {unique['face_shape']}" if unique.get("face_shape") else "",
        f"song-specific face detail: {unique['face']}" if unique.get("face") else "",
        f"signature gesture: {unique['gesture']}" if unique.get("gesture") else "",
    ]
    unique_hair = ", ".join(
        part for part in [
            _with_color(unique.get("hair_base", ""), main_color),
            _with_color(unique.get("hair", ""), main_color),
            f"single {main_color} identity accent only, placed exactly as described",
        ] if part
    )
    unique_outfit = ", ".join(
        part for part in [
            _with_color(unique.get("outfit_base", ""), main_color),
            _with_color(unique.get("outfit", ""), main_color),
            _with_color(unique.get("accessory", ""), main_color),
        ] if part
    )
    unique_silhouette = _with_color(unique.get("body", ""), main_color) or profile["silhouette"]
    identity_lock = unique.get("identity_lock", "Treat this as a completely new lead character for this song.")
    identity_lock_sentence = identity_lock.rstrip(".")
    return {
        "role": "unique protagonist for this song",
        "subject_type": subject["subject_type"],
        "subject_label": subject["subject_label"],
        "gender_presentation": subject["gender_presentation"],
        "identity": ", ".join(part for part in unique_identity_parts if part),
        "age_style": "anime character, stylized and non-photorealistic",
        "hair": unique_hair,
        "outfit": unique_outfit,
        "silhouette": unique_silhouette,
        "emotional_state": mood_words,
        "signature_prop": colored_prop,
        "accent_detail": (
            f"{BRAND_PALETTE['main_color']} remains dominant, but the prop and gestures follow this song motif: {motif}. "
            f"This exact face structure, body silhouette, hair shape, outfit category, accessory, and gesture set belong only to '{song.get('title', 'this song')}'. "
            f"{identity_lock_sentence}"
        ),
        "consistency_rules": [
            "Keep the same face, hairstyle, outfit, body proportions, and signature prop within this song only.",
            f"Primary subject type: {subject['subject_type']} ({subject['subject_label']}); gender presentation: {subject['gender_presentation']}.",
            "Do not reuse this character design for a different song unless the user explicitly requests a series identity.",
            identity_lock,
            "Do not average this character into a generic dark-haired anime protagonist; prioritize the face structure, body silhouette, hair base, and outfit base.",
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
            f"prop close-up of {colored_prop}",
            f"gender/subject check: {subject['gender_presentation']} {subject['subject_label']}",
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


def infer_lyric_idea(section: dict[str, Any]) -> str:
    lyrics = clean_excerpt(section.get("lyrics", ""), 220)
    description = section.get("description", "").strip()
    if lyrics and "encoding-damaged" not in lyrics:
        return _apply_full_palette(f"lyric cue: {lyrics}")
    if description:
        return _apply_full_palette(f"music cue: {description}")
    return f"{section['name']} emotional cue"


def choose_location(section: dict[str, Any], world: dict[str, Any], index: int, used_locations: list[str] | None = None) -> str:
    text = f"{section.get('lyrics', '')} {section.get('description', '')}".lower()
    section_name = section["name"]
    used = used_locations or []
    core = world["core_locations"]

    inference_profile = match_inference_profile_world(world)
    if inference_profile:
        for rule in inference_profile.get("extra_locations", []):
            if _has_any(text, rule.get("keys", [])):
                loc = _apply_full_palette(rule["location"])
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
        return core[(index - 1) % len(core)]

    # Resolution sections prefer dawn/skyline locations
    if _SECTIONS_CONFIG.get("story_stages", {}).get(section_name) == "resolution":
        dawn_keywords = _SECTIONS_CONFIG.get("resolution_location_keywords", ["dawn", "skyline", "rooftop", "sunrise"])
        dawn_locs = [loc for loc in world["core_locations"] if any(k in loc.lower() for k in dawn_keywords)]
        if dawn_locs:
            return dawn_locs[0]

    # Keyword-driven match (word-boundary aware, skips already-used locations)
    for rule in _LOC_CONFIG.get("rules", []):
        if _rule_matches(rule, text):
            loc = _apply_full_palette(rule["location"])
            if loc not in used:
                return loc

    # Fallback: prefer unused core locations
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

    inference_profile = match_inference_profile_text(text)
    if not inference_profile:
        for profile in _INFERENCE_CONFIG.get("profiles", []):
            if _has_any(prop.lower(), profile.get("action_context_prop_keys", [])):
                inference_profile = profile
                break
    if inference_profile:
        section_actions = inference_profile.get("section_actions", {})
        if section_name in section_actions:
            return _apply_full_palette(fmt(section_actions[section_name]))
        for rule in inference_profile.get("action_rules", []):
            if _has_any(text, rule.get("keys", [])):
                return _apply_full_palette(fmt(rule["action"]))
        if inference_profile.get("default_action"):
            return _apply_full_palette(fmt(inference_profile["default_action"]))

    if protagonist.get("subject_type") == "environment_only":
        if section_name == "Intro":
            return _apply_full_palette(f"the empty environment slowly reveals {prop} through light, weather, and camera drift")
        if section_name == "Chorus":
            return _apply_full_palette(f"the environment blooms around {prop}, making the space itself feel like the singer")
        if section_name == "Outro":
            return _apply_full_palette(f"{prop} fades into the final empty space as the environment settles")
        return _apply_full_palette(f"light, shadow, and atmosphere move around {prop} without introducing a recurring human lead")

    if protagonist.get("subject_type") == "object_symbol":
        if section_name == "Intro":
            return _apply_full_palette(f"{prop} appears as the first emotional anchor, held by light rather than a full human lead")
        if section_name == "Chorus":
            return _apply_full_palette(f"{prop} becomes the dominant subject, pulling reflections and memory fragments toward it")
        if section_name == "Outro":
            return _apply_full_palette(f"{prop} remains after all human presence has passed out of frame")
        return _apply_full_palette(f"{prop} reacts to the lyric emotion through glow, reflection, and small environmental movement")

    # Section-specific overrides from config (checked before generic keyword scan)
    overrides = _SECTIONS_CONFIG.get("action_overrides", {})
    if section_name in overrides:
        ov = overrides[section_name]
        # Intro: music-cue shortcut
        if "music_cue_prefix" in ov and lyric_idea.startswith(ov["music_cue_prefix"]):
            return _apply_full_palette(fmt(ov["music_cue_action"]))
        # Bridge / Outro: conditional keyword check
        if "hide_keywords" in ov and any(k in text for k in ov["hide_keywords"]):
            return _apply_full_palette(fmt(ov["hide_action"]))
        if "cry_keywords" in ov and any(k in text for k in ov["cry_keywords"]):
            return _apply_full_palette(fmt(ov["cry_action"]))
        # Chorus: smile-specific check
        if "smile_keywords" in ov and any(k in text for k in ov["smile_keywords"]):
            return _apply_full_palette(fmt(ov["smile_action"]))
        # Section has a default override (Bridge, Outro, Chorus)
        if "default_action" in ov:
            return _apply_full_palette(fmt(ov["default_action"]))

    # Generic keyword scan from config
    for rule in _ACTION_CONFIG.get("rules", []):
        if any(k in text for k in rule["keys"]):
            return _apply_full_palette(fmt(rule["action"]))

    return _apply_full_palette(fmt(_ACTION_CONFIG.get("default", "shows the section emotion through posture, hand movement, and the recurring {prop}")))


def choose_symbolic_focus(section: dict[str, Any], world: dict[str, Any], protagonist: dict[str, Any]) -> str:
    text = f"{section.get('lyrics', '')} {section.get('description', '')}".lower()
    inference_profile = match_inference_profile_world(world) or match_inference_profile_text(text)
    if inference_profile:
        for rule in inference_profile.get("focus_rules", []):
            if _has_any(text, rule.get("keys", [])):
                return _apply_full_palette(rule["focus"])
        return world.get("song_motif") or protagonist["signature_prop"]
    for rule in _FOCUS_CONFIG.get("rules", []):
        if any(k in text for k in rule["keys"]):
            return _apply_full_palette(rule["focus"])
    return _apply_full_palette(world.get("song_motif") or protagonist["signature_prop"])


def choose_shot(section: dict[str, Any], emotion: str, song: dict[str, Any]) -> str:
    name  = section["name"]
    bpm   = song.get("bpm") or 0
    text  = f"{section.get('lyrics', '')} {section.get('description', '')}".lower()
    tempo = _bpm_tempo(bpm)

    # Fixed section overrides (Intro, Bridge, Outro)
    section_overrides = _SHOT_CONFIG.get("section_overrides", {})
    if name in section_overrides:
        return _apply_full_palette(section_overrides[name])

    # Chorus: BPM-sensitive shot
    if name == "Chorus":
        if tempo == "fast":
            return _apply_full_palette(_SHOT_CONFIG.get("chorus_fast_shot", "dynamic forward tracking shot, low angle, strong beat-synced foreground streaks"))
        return _apply_full_palette(_SHOT_CONFIG.get("chorus_default_shot", "forward tracking shot with widening background parallax and brighter rim light"))

    # Mirror/reflection keyword: content-driven close-up
    mirror_keys = _SHOT_CONFIG.get("mirror_keywords", ["거울", "mirror", "반사"])
    if any(k in text for k in mirror_keys):
        return _apply_full_palette(_SHOT_CONFIG.get("mirror_shot", "medium close-up reflected in a dark surface with accent fracture light framing the face"))

    # Emotion-driven shot
    emotion_shots = _SHOT_CONFIG.get("emotion_shots", {})
    if emotion in emotion_shots:
        return _apply_full_palette(emotion_shots[emotion])

    # Keyword-driven fallback shots
    for rule in _SHOT_CONFIG.get("keyword_shots", []):
        if any(k in text for k in rule["keys"]):
            return _apply_full_palette(rule["shot"])

    return _apply_full_palette(_SHOT_CONFIG.get("default", "medium shot with lyric-specific hand action and soft parallax background"))


def choose_movement(section: dict[str, Any], song: dict[str, Any]) -> str:
    name    = section["name"]
    tempo   = _bpm_tempo(song.get("bpm"))
    patterns = _SECTIONS_CONFIG.get("movement_patterns", {})
    section_patterns = patterns.get(name, {})
    inference_profile = match_inference_profile_song(song)
    if inference_profile.get("movement_patterns"):
        profile_patterns = inference_profile["movement_patterns"]
        return _apply_full_palette(profile_patterns.get(name, profile_patterns.get("default", "song-tempo-aware cinematic drift")))

    if "any" in section_patterns:
        return _apply_full_palette(section_patterns["any"])
    if tempo in section_patterns:
        return _apply_full_palette(section_patterns[tempo])
    if "medium" in section_patterns:
        return _apply_full_palette(section_patterns["medium"])
    return _apply_full_palette(_SECTIONS_CONFIG.get("default_movement", "song-tempo-aware cinematic drift"))


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
            "lighting":             _apply_full_palette(section_emotion.get("lighting", world["lighting_language"])),
            "camera_direction":     shot,
            "movement":             movement,
            "video_rhythm":         video_rhythm(song, section),
            "cinematic_style":      world["visual_identity"],
            "symbolism":            [_apply_full_palette(s) for s in section_emotion.get("visual_symbols", world["recurring_symbols"])],
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
            "story_beat_ko":           story_beat_ko(scene, stage),
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
    return _apply_full_palette(idea.replace("lyric cue: ", "").replace("music cue: ", ""))[:220]


def image_prompt(scene: dict[str, Any], protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    _cb_raw = COLOR_BALANCE_BY_STAGE.get(scene.get("story_stage", "development"), COLOR_BALANCE_BY_STAGE.get("development", ""))
    color_balance = _cb_raw.format(main_color=BRAND_PALETTE.get("main_color", "accent color")) if _cb_raw else ""
    symbols = ", ".join(normalize_symbols(scene.get("symbolism", [])[:4]))
    inst_hint = world.get("instrument_hint", "")
    lines = [
        "Create a visibly song-unique primary subject, not a reused series character or reused visual identity.",
        f"{scene['camera_direction']} in {scene['environment']}.",
        f"{character_visual(protagonist)}.",
        f"Identity lock: {protagonist['accent_detail']}.",
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
    _cb_raw = COLOR_BALANCE_BY_STAGE.get(scene.get("story_stage", "development"), COLOR_BALANCE_BY_STAGE.get("development", ""))
    color_balance = _cb_raw.format(main_color=BRAND_PALETTE.get("main_color", "accent color")) if _cb_raw else ""
    inst_hint = world.get("instrument_hint", "")
    if protagonist.get("subject_type") in ("environment_only", "object_symbol"):
        preserve = f"Preserve the primary visual subject: {protagonist['identity']}, {protagonist['silhouette']}, {protagonist['signature_prop']}."
    else:
        preserve = f"Preserve the character design: {protagonist['hair']}, {protagonist['outfit']}, {protagonist['signature_prop']}."
    lines = [
        "Image-to-video from the attached scene image.",
        preserve,
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
    if protagonist.get("subject_type") in ("environment_only", "object_symbol"):
        subject_description = (
            f"{protagonist['identity']}, {protagonist['age_style']}, {protagonist['silhouette']}. "
            f"Primary recurring subject: {protagonist['signature_prop']}. "
        )
    else:
        subject_description = (
            f"{protagonist['identity']}, {protagonist['age_style']}, {protagonist['hair']}, "
            f"{protagonist['outfit']}, {protagonist['silhouette']}. Signature prop: {protagonist['signature_prop']}. "
        )
    return (
        "# Character Prompt\n\n"
        "Create a completely new primary visual subject for this song, not a reused design or costume variation.\n\n"
        f"{subject_description}"
        f"Accent detail: {protagonist['accent_detail']}. Visual world: {world['visual_identity']}.\n\n"
        "Consistency rules:\n"
        f"{rules}\n"
    )


def character_reference_prompt(protagonist: dict[str, Any], world: dict[str, Any]) -> str:
    rules    = "\n".join(f"- {rule}" for rule in protagonist["consistency_rules"])
    workflow = "\n".join(f"- {step}" for step in protagonist.get("reference_workflow", []))
    views    = "\n".join(f"- {view}" for view in protagonist.get("required_reference_views", []))
    is_nonhuman = protagonist.get("subject_type") in ("environment_only", "object_symbol")
    title = "Primary Visual Subject Reference Sheet Prompt" if is_nonhuman else "Character Turnaround Model Sheet Prompt"
    purpose = (
        "Create the master primary-subject reference sheet for this song. This sheet will be attached as the visual identity reference for every later scene image.\n\n"
        if is_nonhuman else
        "Create the master character turnaround model sheet for this song. This model sheet will be attached as the identity reference for every later scene image, and optionally as a secondary reference for video generation.\n\n"
    )
    design = (
        f"Subject design: {protagonist['identity']}, {protagonist['age_style']}, {protagonist['silhouette']}. "
        f"Primary recurring subject: {protagonist['signature_prop']}. "
        if is_nonhuman else
        f"Character design: {protagonist['identity']}, {protagonist['age_style']}, {protagonist['hair']}, "
        f"{protagonist['outfit']}, {protagonist['silhouette']}. Signature prop: {protagonist['signature_prop']}. "
    )
    composition = (
        "Composition: clean anime subject reference sheet, neutral simple background where useful, clear scale references, "
        "wide environment/object views plus close-up details, no full-body human turnaround unless the subject type is human, "
        "no readable text, clear recurring motif, no dramatic camera angle for the reference sheet. "
        if is_nonhuman else
        "Composition: clean anime production model sheet, neutral simple background, aligned character views at the same scale, "
        "full body visible from head to toe in each turnaround pose, clear face close-up, clear hairstyle silhouette, "
        "clear outfit seams, clear signature prop, no dramatic camera angle, no cropped limbs, no environmental scene, no action pose. "
    )
    return (
        f"# {title}\n\n"
        f"{purpose}"
        "Identity requirement: create a visibly new primary subject for this song, not a reused design, not a costume variation, "
        "not the same face with different clothes. If the subject is not human, do not force a full-body human character; keep the object/environment as the main subject.\n\n"
        "Required views:\n"
        f"{views}\n\n"
        f"{design}"
        f"Accent detail: {protagonist['accent_detail']}. Visual world: {world['visual_identity']}.\n\n"
        f"{composition}"
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
        f"4. Keep the fixed {BRAND_PALETTE.get('main_color', 'neon magenta')} palette, but vary action, location, rhythm, and symbolism per song and section.",
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
    song = read_json(song_path or (PROJECT_ROOT / "input" / "song_master.json"))
    if not style_id:
        _matched_profile = choose_genre_profile(song)
        style_id = _matched_profile.get("style_id", _STYLE_CONFIG.get("default_style", "dreamy_synth"))
    select_theme(style_id)
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
