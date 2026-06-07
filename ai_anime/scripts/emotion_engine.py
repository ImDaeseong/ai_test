from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from common import PROJECT_ROOT, ensure_directories, load_config, read_json, write_json


_CONFIG = load_config("emotions")
EMOTION_MAP: dict = _CONFIG.get("emotions", {})
EMOTION_ALIASES: dict = _CONFIG.get("aliases", {})
_EMOTION_DEFAULT: dict = _CONFIG.get("default", {
    "symbols": ["silhouette", "wind", "distant city lights"],
    "lighting": "cinematic lighting with deep shadows, subtle accent color glow, and soft rim highlights",
    "camera": "film-like composition with slow push-in",
    "environment": "atmospheric city space",
})

_TRANSITIONS = load_config("emotion_transitions")
_CHORUS_LIFT = set(_TRANSITIONS.get("chorus_lift_emotions", []))
_CHORUS_LIFT_TARGET = _TRANSITIONS.get("chorus_lift_target", "hopeful")
_CHORUS_LIFT_EXCEPTIONS = _TRANSITIONS.get("chorus_lift_exceptions", {})
_BRIDGE_DEEPEN = _TRANSITIONS.get("bridge_deepen", {})
_OUTRO_RESOLVE = _TRANSITIONS.get("outro_resolve", {})
_OUTRO_DEFAULT = _TRANSITIONS.get("outro_resolve_default", "hope")
_CLIMAX_SECTIONS = set(_TRANSITIONS.get("climax_sections", ["Chorus", "Bridge"]))

_ATMOSPHERE = load_config("atmosphere_rules")
_INFERENCE_CONFIG = load_config("song_inference")


def song_text(song: dict[str, Any]) -> str:
    fields = [
        song.get("genre", ""),
        " ".join(song.get("style_tags", [])),
        " ".join(song.get("mood", [])),
        " ".join(song.get("visual_cues", [])),
        song.get("atmosphere", ""),
    ]
    for section in song.get("sections", []):
        fields.extend(
            [
                section.get("name", ""),
                section.get("description", ""),
                section.get("lyrics", ""),
                " ".join(section.get("visual_cues", [])),
            ]
        )
    return " ".join(fields).lower()


def has_any(text: str, terms: list[str]) -> bool:
    return any(term_matches(term, text) for term in terms)


def term_matches(term: str, text: str) -> bool:
    key = term.lower()
    if re.search(r"[a-z0-9]", key):
        return bool(re.search(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])", text))
    return key in text


def match_inference_profile(text: str) -> dict[str, Any]:
    for profile in _INFERENCE_CONFIG.get("profiles", []):
        if has_any(text, profile.get("keys", [])):
            return profile
    return {}


def choose_primary_emotion(moods: list[str]) -> str:
    for mood in moods:
        key = mood.lower().strip()
        if key in EMOTION_MAP:
            return key
        alias = EMOTION_ALIASES.get(key)
        if alias and alias in EMOTION_MAP:
            return alias
    return moods[0].lower().strip() if moods else "melancholic"


def map_emotion(emotion: str) -> dict[str, Any]:
    return EMOTION_MAP.get(emotion) or _EMOTION_DEFAULT


def map_song_emotion(emotion: str, profile: dict[str, Any], energy: str = "medium") -> dict[str, Any]:
    """감정 데이터를 반환한다. energy가 제공되면 lighting_by_energy에서 에너지별 조명을 선택한다."""
    profile_maps = profile.get("emotion_maps", {}) if profile else {}
    if profile_maps:
        fallback_key = profile.get("primary_emotion", "hopeful")
        base = profile_maps.get(emotion) or profile_maps.get(fallback_key) or map_emotion(emotion)
    else:
        base = map_emotion(emotion)

    # 에너지별 조명 선택 — lighting_by_energy 키가 있을 때만 적용
    by_energy = base.get("lighting_by_energy", {})
    if by_energy:
        energy_key = energy if energy in by_energy else "medium"
        selected_lighting = by_energy.get(energy_key) or base.get("lighting", "")
        if selected_lighting and selected_lighting != base.get("lighting"):
            return {**base, "lighting": selected_lighting}

    return base


def analyze_song(song: dict[str, Any]) -> dict[str, Any]:
    moods = song.get("mood", [])
    primary = choose_primary_emotion(moods)
    text = song_text(song)
    profile = match_inference_profile(text)
    if profile.get("primary_emotion"):
        primary = profile["primary_emotion"]
    energy = (song.get("energy") or "medium").lower()
    primary_map = map_song_emotion(primary, profile, energy)
    progression = []

    for section in song.get("sections", []):
        section_name = section["name"]
        intensity = section["intensity"]
        if section_name == "Chorus":
            if primary in _CHORUS_LIFT:
                emotion = _CHORUS_LIFT_TARGET
            else:
                emotion = _CHORUS_LIFT_EXCEPTIONS.get(primary, primary)
        elif section_name == "Bridge":
            emotion = _BRIDGE_DEEPEN.get(primary, primary)
            if emotion in set(profile.get("bridge_blocked_emotions", [])):
                emotion = profile.get("primary_emotion", primary)
        elif section_name == "Outro":
            emotion = _OUTRO_RESOLVE.get(primary, _OUTRO_DEFAULT)
        else:
            emotion = primary
        # intensity가 high이면 에너지 상승, low/falling이면 에너지 하강으로 조명 보정
        section_energy = energy
        if intensity in ("high", "emotional peak"):
            section_energy = "high"
        elif intensity in ("low", "falling"):
            section_energy = "low"
        mapped = map_song_emotion(emotion, profile, section_energy)
        progression.append(
            {
                "section": section_name,
                "intensity": intensity,
                "emotion": emotion,
                "visual_symbols": mapped["symbols"],
                "lighting": mapped["lighting"],
                "environment": mapped["environment"],
                "camera_emotion": mapped["camera"],
            }
        )

    return {
        "primary_emotion": primary,
        "secondary_emotions": moods[1:],
        "emotional_progression": progression,
        "visual_symbolism": primary_map["symbols"],
        "emotional_climax": next(
            (item for item in progression if item["section"] in _CLIMAX_SECTIONS),
            progression[-1] if progression else {},
        ),
        "seasonal_atmosphere": infer_season(song),
        "urban_rural_mood": infer_urban_rural(song),
        "cinematic_pacing": song.get("pacing", "medium cinematic pacing"),
        "tension_curve": [item["intensity"] for item in progression],
    }


def infer_season(song: dict[str, Any]) -> str:
    text = song_text(song)
    profile = match_inference_profile(text)
    if profile.get("season"):
        return profile["season"]
    for rule in _ATMOSPHERE.get("season_rules", []):
        if has_any(text, rule["keys"]):
            return rule["season"]
    return _ATMOSPHERE.get("season_default", "season-neutral cinematic night")


def infer_urban_rural(song: dict[str, Any]) -> str:
    text = song_text(song)
    profile = match_inference_profile(text)
    if profile.get("environment_family"):
        return profile["environment_family"]
    urban_terms = _ATMOSPHERE.get("urban_keywords", ["city", "street", "neon"])
    urban_mood = _ATMOSPHERE.get("urban_mood", "urban emotional atmosphere")
    rural_mood = _ATMOSPHERE.get("rural_mood", "quiet rural or liminal atmosphere")
    return urban_mood if has_any(text, urban_terms) else rural_mood


def run(
    input_path: Path | None = None,
    output_path: Path | None = None,
) -> None:
    ensure_directories()
    inp = input_path or (PROJECT_ROOT / "input" / "song_master.json")
    out = output_path or (PROJECT_ROOT / "analysis" / "emotion_analysis.json")
    analysis = analyze_song(read_json(inp))
    write_json(out, analysis)
    print(f"Wrote {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze song emotion and visual symbolism.")
    parser.add_argument("--input", default=str(PROJECT_ROOT / "input" / "song_master.json"))
    parser.add_argument("--output", default=str(PROJECT_ROOT / "analysis" / "emotion_analysis.json"))
    args = parser.parse_args()

    run(input_path=Path(args.input), output_path=Path(args.output))


if __name__ == "__main__":
    main()
