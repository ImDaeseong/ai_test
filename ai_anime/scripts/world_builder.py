from __future__ import annotations

from typing import Any

import palette_engine as _pe
from common import _rule_matches, load_config, slugify
from genre_selector import (
    _has_any,
    choose_genre_profile,
    match_inference_profile_song,
    normalized_song_text,
)
from genre_reference import reference_variant, select_genre_reference
from _song_helpers import (
    _bpm_lighting_desc,
    _bpm_transition_desc,
    _profile_value,
    _select_variant,
    _stable_order,
    song_character_seed,
)

_MOTIF_CONFIG            = load_config("motif_rules")
_LOC_CONFIG              = load_config("location_rules")
_INSTRUMENT_HINT_CONFIG  = load_config("instrument_hints")

_INSTRUMENT_HINTS: dict[str, str] = _INSTRUMENT_HINT_CONFIG.get("hints", {})
_MAX_INSTRUMENT_HINTS = int(_INSTRUMENT_HINT_CONFIG.get("max_hints", 3))


# ---------------------------------------------------------------------------
# Visual world builders
# ---------------------------------------------------------------------------

def infer_song_motif(song: dict[str, Any], profile: dict[str, Any]) -> str:
    main_color = _pe.BRAND_PALETTE.get("main_color", "neon magenta")
    text = normalized_song_text(song)
    inference_profile = match_inference_profile_song(song)
    if inference_profile.get("motif_template"):
        return _pe.apply_full_palette(inference_profile["motif_template"].format(main_color=main_color))
    for rule in _MOTIF_CONFIG.get("rules", []):
        if any(k in text for k in rule["keys"]):
            return _pe.apply_full_palette(rule["motif"])
    return f"{_pe.apply_full_palette(profile['prop'])} recurring as the song's main visual motif"


def instrument_visual_hint(instruments: list[str]) -> str:
    """Return visual motion hints derived from detected instruments (up to 3)."""
    hints: list[str] = []
    for inst in instruments:
        key = inst.lower().strip()
        for name, hint in _INSTRUMENT_HINTS.items():
            if name in key and hint not in hints:
                hints.append(hint)
                break
    return _pe.apply_full_palette("; ".join(hints[:_MAX_INSTRUMENT_HINTS]))


def lighting_language(
    song: dict[str, Any],
    profile: dict[str, Any],
    reference: dict[str, Any] | None = None,
) -> str:
    bpm = song.get("bpm") or 0
    tempo_light = _bpm_lighting_desc(bpm)
    shadow = _pe.BRAND_PALETTE.get("shadow_color", "deep plum and dark violet shadows")
    highlight = _pe.BRAND_PALETTE.get("highlight", "silver-white rim highlights")
    seed = song_character_seed(song)
    texture = _profile_value(profile, "texture", seed, "texture")
    reference_light = reference_variant(reference or {}, "lighting_language", seed, "lighting")
    parts = [tempo_light, texture, reference_light, shadow, highlight]
    return _pe.apply_full_palette(", ".join(part for part in parts if part))


def transition_language(
    song: dict[str, Any],
    profile: dict[str, Any],
    motif: str,
    reference: dict[str, Any] | None = None,
) -> str:
    bpm = song.get("bpm") or 0
    rhythm = _bpm_transition_desc(bpm)
    secondary = _pe.BRAND_PALETTE.get("secondary_accent", "accent light")
    seed = song_character_seed(song)
    texture = _profile_value(profile, "texture", seed, "transition_texture")
    reference_edit = reference_variant(reference or {}, "edit_language", seed, "editing")
    parts = [f"{rhythm} through {motif}", f"{secondary} reflections", texture, reference_edit]
    return _pe.apply_full_palette(", ".join(part for part in parts if part))


def normalize_symbols(symbols: list[str]) -> list[str]:
    normalized = []
    for symbol in symbols:
        value = str(symbol).strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def infer_locations(
    song: dict[str, Any],
    profile: dict[str, Any],
    reference: dict[str, Any] | None = None,
) -> list[str]:
    text = normalized_song_text(song)
    locations: list[str] = []
    seed = song_character_seed(song)
    reference_locs = _stable_order(
        [str(value) for value in (reference or {}).get("environments", [])],
        seed,
        "genre_reference_locations",
    )
    locations.extend(_pe.apply_full_palette(loc) for loc in reference_locs)
    inference_profile = match_inference_profile_song(song)
    if inference_profile:
        profile_locs = [*profile.get("locations", []), *profile.get("location_variants", [])]
        locations.extend(_pe.apply_full_palette(loc) for loc in _stable_order(profile_locs, seed, "profile_locations"))
        for rule in inference_profile.get("extra_locations", []):
            if _has_any(text, rule.get("keys", [])):
                locations.append(_pe.apply_full_palette(_select_variant(rule["location"], seed, "inference_location")))
        return list(dict.fromkeys(locations))[:10]
    for rule in _LOC_CONFIG.get("rules", []):
        if _rule_matches(rule, text):
            loc = _pe.apply_full_palette(_select_variant(rule["location"], seed, "location_rule"))
            if loc not in locations:
                locations.append(loc)
    profile_locs = [*profile.get("locations", []), *profile.get("location_variants", [])]
    locations.extend(_pe.apply_full_palette(loc) for loc in _stable_order(profile_locs, seed, "profile_locations"))
    return list(dict.fromkeys(locations))[:10]


def create_visual_world(song: dict[str, Any], emotion: dict[str, Any]) -> dict[str, Any]:
    profile = choose_genre_profile(song)
    reference = select_genre_reference(profile)
    seed = song_character_seed(song)
    colored_prop = _pe.apply_full_palette(_profile_value(profile, "prop", seed, "prop"))
    motif = infer_song_motif(song, profile)
    locations = infer_locations(song, profile, reference)
    symbols = normalize_symbols(
        [motif, *emotion.get("visual_symbolism", []), *song.get("visual_cues", []), colored_prop]
    )
    inference_profile = match_inference_profile_song(song)
    blocked_symbols = {symbol.lower() for symbol in inference_profile.get("symbol_filter", [])}
    if blocked_symbols:
        symbols = [symbol for symbol in symbols if symbol.strip().lower() not in blocked_symbols]
    symbols = symbols[:8]
    narrative_direction = reference_variant(reference, "narrative_modes", seed, "narrative")
    character_direction = reference_variant(reference, "character_language", seed, "character")
    camera_language = reference.get("camera_language", [])
    motion_language = reference.get("motion_language", [])
    return {
        "song_slug": slugify(song["title"]),
        "visual_identity": _pe.apply_full_palette(f"{profile['name']} within {_pe.BRAND_PALETTE['visual_identity']}"),
        "genre_profile": _pe.apply_full_palette(profile["name"]),
        "song_motif": motif,
        "color_palette": {
            "base": _pe.BRAND_PALETTE["base"],
            "main_color": _pe.BRAND_PALETTE["main_color"],
            "shadow_color": _pe.BRAND_PALETTE["shadow_color"],
            "secondary_light": _pe.BRAND_PALETTE["secondary_light"],
            "highlight": _pe.BRAND_PALETTE["highlight"],
            "rule": _pe.BRAND_PALETTE["palette_rule"],
        },
        "base_palette": _pe.BRAND_PALETTE["base"],
        "accent_color": _pe.BRAND_PALETTE["main_color"],
        "secondary_accent_color": _pe.BRAND_PALETTE.get("secondary_accent", "icy cyan"),
        "highlight_color": _pe.BRAND_PALETTE.get("highlight_color_name", "silver white"),
        "environment_family": emotion.get("urban_rural_mood", "urban emotional atmosphere"),
        "core_locations": locations,
        "recurring_symbols": symbols,
        "lighting_language": lighting_language(song, profile, reference),
        "transition_language": transition_language(song, profile, motif, reference),
        "instrument_hint": instrument_visual_hint(song.get("instruments", [])),
        "negative_style_rules": song.get("negative_tags", []),
        "genre_reference": {
            "id": reference.get("id", ""),
            "design_basis": reference.get("design_basis", ""),
            "narrative_direction": narrative_direction,
            "character_direction": character_direction,
            "camera_language": camera_language,
            "motion_language": motion_language,
            "avoid": reference.get("avoid", []),
            "safety": "Use broad genre grammar only; do not imitate a recognizable artist, character, costume, prop, logo, video, or stage.",
        } if reference else {},
    }
