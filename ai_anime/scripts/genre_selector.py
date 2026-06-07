from __future__ import annotations

import math
from collections import Counter as _Counter
from typing import Any

import palette_engine as _pe
from common import _key_matches, _rule_matches, load_config

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------
_GENRE_CONFIG     = load_config("genres")
_BPM_CONFIG       = load_config("bpm_thresholds")
_INFERENCE_CONFIG = load_config("song_inference")
_STYLE_CONFIG     = load_config("visual_styles")
_CHAR_CONFIG      = load_config("character_defaults")
_LOC_CONFIG       = load_config("location_rules")
_PROP_CONFIG      = load_config("prop_rules")

GENRE_PROFILES: list[dict[str, Any]] = _GENRE_CONFIG if isinstance(_GENRE_CONFIG, list) else []

# ---------------------------------------------------------------------------
# IDF weights
# ---------------------------------------------------------------------------
_KEY_DF: _Counter[str] = _Counter()
for _g in GENRE_PROFILES:
    for _k in _g.get("keys", []):
        _KEY_DF[_k] += 1
_N_PROFILES: int = max(len(GENRE_PROFILES), 1)


def _idf(key: str) -> float:
    """Smoothed log-IDF: higher for keys that appear in fewer genre profiles."""
    df = _KEY_DF.get(key, 1)
    return math.log(_N_PROFILES / df + 1.0)


# ---------------------------------------------------------------------------
# BPM helper (local copy — used only by build_adaptive_default)
# ---------------------------------------------------------------------------
_BPM_THRESHOLDS = _BPM_CONFIG.get("thresholds", {})


def _bpm_tempo(bpm: int | None) -> str:
    if not bpm:
        return "medium"
    if bpm >= _BPM_THRESHOLDS.get("fast", {}).get("min_bpm", 120):
        return "fast"
    if bpm <= _BPM_THRESHOLDS.get("slow", {}).get("max_bpm", 80):
        return "slow"
    return "medium"


# ---------------------------------------------------------------------------
# Song text normalisation
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


# ---------------------------------------------------------------------------
# Inference profile matching
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Genre profile scoring and selection
# ---------------------------------------------------------------------------

def _score_profiles(text: str) -> tuple[int, dict[str, Any] | None]:
    """Score profiles against text using IDF-weighted sums."""
    best_score, best_idf, best_profile = 0, 0.0, None
    for profile in GENRE_PROFILES:
        matched = [key for key in profile["keys"] if _key_matches(key, text)]
        score = len(matched)
        idf_score = sum(_idf(k) for k in matched)
        if (idf_score, score) > (best_idf, best_score):
            best_score, best_idf, best_profile = score, idf_score, profile
    return best_score, best_profile


def build_adaptive_default(song: dict[str, Any]) -> dict[str, Any]:
    """Fallback character profile when no genre profile matches."""
    text = normalized_song_text(song)
    energy = (song.get("energy") or "medium").lower()
    mood = ((song.get("mood") or ["melancholic"])[0]).lower().strip()
    bpm = song.get("bpm") or 100
    main_color = _pe.BRAND_PALETTE.get("main_color", "neon magenta")
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
            prop = _pe.apply_full_palette(rule["prop"])
            break

    # 5. Locations
    locations: list[str] = []
    for rule in _LOC_CONFIG.get("rules", []):
        if _rule_matches(rule, text):
            loc = _pe.apply_full_palette(rule["location"])
            if loc not in locations:
                locations.append(loc)

    if len(locations) < 2:
        locations.extend(
            _pe.apply_full_palette(loc)
            for loc in _LOC_CONFIG.get("fallbacks", ["quiet emotional threshold space", "empty street under accent light"])
        )

    _adaptive_style_map = _STYLE_CONFIG.get("adaptive_style_map", {"fast": "urban_noir", "slow": "warm_acoustic", "medium": "dreamy_synth"})
    style_id = _adaptive_style_map.get(energy_group, _STYLE_CONFIG.get("default_style", "dreamy_synth"))
    _vi = _STYLE_CONFIG.get("styles", {}).get(style_id, {}).get("brand_palette", {}).get("visual_identity", "cinematic anime")
    genre_label = _vi.split(" with ")[0] if " with " in _vi else "cinematic anime"
    return {
        "name": f"{mood} {genre_label}",
        "style_id": style_id,
        "identity": identity,
        "hair": hair,
        "outfit": outfit,
        "silhouette": silhouette,
        "prop": prop,
        "locations": locations[:4],
        "texture": texture,
    }


def choose_genre_profile(song: dict[str, Any]) -> dict[str, Any]:
    """Select the best-matching genre profile using IDF-weighted scoring."""
    genre_text = (song.get("genre") or "").lower()
    metadata_text = normalized_genre_text(song)
    best_rank: tuple = (0.0, 0, 0.0, 0, 0)
    best_profile = None
    for profile in GENRE_PROFILES:
        genre_matched = [k for k in profile["keys"] if _key_matches(k, genre_text)]
        meta_matched = [k for k in profile["keys"] if _key_matches(k, metadata_text)]
        genre_score = len(genre_matched)
        metadata_score = len(meta_matched)
        genre_idf = sum(_idf(k) for k in genre_matched)
        meta_idf = sum(_idf(k) for k in meta_matched)
        total_idf = genre_idf * 2 + meta_idf
        total_score = genre_score * 2 + metadata_score
        rank = (genre_idf, genre_score, total_idf, total_score, metadata_score)
        if rank > best_rank:
            best_rank, best_profile = rank, profile
    if best_rank[1] > 0 and best_profile:
        return best_profile

    score, profile = _score_profiles(normalized_song_text(song))
    return profile if score >= 2 and profile else build_adaptive_default(song)
