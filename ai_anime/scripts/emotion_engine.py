from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import PROJECT_ROOT, ensure_directories, load_config, read_json, write_json


_CONFIG = load_config("emotions")
EMOTION_MAP = _CONFIG.get("emotions", {})
EMOTION_ALIASES = _CONFIG.get("aliases", {})

_TRANSITIONS = load_config("emotion_transitions")
_CHORUS_LIFT = set(_TRANSITIONS.get("chorus_lift_emotions", []))
_CHORUS_LIFT_TARGET = _TRANSITIONS.get("chorus_lift_target", "hopeful")
_CHORUS_LIFT_EXCEPTIONS = _TRANSITIONS.get("chorus_lift_exceptions", {})
_BRIDGE_DEEPEN = _TRANSITIONS.get("bridge_deepen", {})
_OUTRO_RESOLVE = _TRANSITIONS.get("outro_resolve", {})
_OUTRO_DEFAULT = _TRANSITIONS.get("outro_resolve_default", "hope")
_CLIMAX_SECTIONS = set(_TRANSITIONS.get("climax_sections", ["Chorus", "Bridge"]))

_ATMOSPHERE = load_config("atmosphere_rules")


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
    return EMOTION_MAP.get(
        emotion,
        {
            "symbols": ["silhouette", "wind", "distant city lights"],
            "lighting": "dark cinematic cyber lighting with neon magenta glow, deep violet shadows, subtle icy cyan reflections, and silver rim light",
            "camera": "film-like composition with slow push-in",
            "environment": "atmospheric city space",
        },
    )


def analyze_song(song: dict[str, Any]) -> dict[str, Any]:
    moods = song.get("mood", [])
    primary = choose_primary_emotion(moods)
    primary_map = map_emotion(primary)
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
        elif section_name == "Outro":
            emotion = _OUTRO_RESOLVE.get(primary, _OUTRO_DEFAULT)
        else:
            emotion = primary
        mapped = map_emotion(emotion)
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
    text = " ".join(song.get("visual_cues", []) + song.get("mood", [])).lower()
    for rule in _ATMOSPHERE.get("season_rules", []):
        if any(k in text for k in rule["keys"]):
            return rule["season"]
    return _ATMOSPHERE.get("season_default", "season-neutral cinematic night")


def infer_urban_rural(song: dict[str, Any]) -> str:
    text = " ".join(song.get("visual_cues", [])).lower()
    urban_terms = _ATMOSPHERE.get("urban_keywords", ["city", "street", "neon"])
    urban_mood = _ATMOSPHERE.get("urban_mood", "urban emotional atmosphere")
    rural_mood = _ATMOSPHERE.get("rural_mood", "quiet rural or liminal atmosphere")
    return urban_mood if any(term in text for term in urban_terms) else rural_mood


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
