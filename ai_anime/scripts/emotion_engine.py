from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import PROJECT_ROOT, ensure_directories, read_json, write_json


EMOTION_MAP = {
    "lonely": {
        "symbols": ["empty train platform", "unanswered signal light", "single window glow"],
        "lighting": "cold silver grayscale with deep blue accent",
        "camera": "wide static frame, small figure against negative space",
        "environment": "rainy city night",
    },
    "loneliness": {
        "symbols": ["empty street", "distant apartment lights", "wet pavement reflection"],
        "lighting": "soft low-key grayscale with pale cyan accent",
        "camera": "slow lateral dolly with strong silhouette",
        "environment": "urban backstreet after rain",
    },
    "nostalgic": {
        "symbols": ["paper crane", "old station sign", "wind through curtains"],
        "lighting": "faded grayscale with pale blue accent",
        "camera": "gentle push-in, shallow atmospheric depth",
        "environment": "quiet transit spaces and rooftops",
    },
    "hope": {
        "symbols": ["sunrise edge", "opening sky", "upward drifting paper crane"],
        "lighting": "bright grayscale bloom with one warm accent",
        "camera": "upward angle, slow crane rise",
        "environment": "rooftop at dawn",
    },
    "hopeful": {
        "symbols": ["thin line of dawn", "opening hand", "city lights turning off"],
        "lighting": "soft white glow with pale cyan accent",
        "camera": "forward tracking shot into open space",
        "environment": "city morning after rain",
    },
    "sad": {
        "symbols": ["rain on glass", "empty bench", "flickering streetlamp"],
        "lighting": "high contrast grayscale with muted crimson accent",
        "camera": "close-up profile, slow tilt down",
        "environment": "night street or train window",
    },
}


def choose_primary_emotion(moods: list[str]) -> str:
    for mood in moods:
        key = mood.lower().strip()
        if key in EMOTION_MAP:
            return key
    return moods[0].lower().strip() if moods else "melancholic"


def map_emotion(emotion: str) -> dict[str, Any]:
    return EMOTION_MAP.get(
        emotion,
        {
            "symbols": ["silhouette", "wind", "distant city lights"],
            "lighting": "soft monochrome light with deep blue accent",
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
            emotion = "hopeful" if "hopeful" in [m.lower() for m in moods] else primary
        elif section_name == "Bridge":
            emotion = "sad" if primary in {"lonely", "loneliness", "nostalgic"} else primary
        elif section_name == "Outro":
            emotion = "hope"
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
            (item for item in progression if item["section"] in {"Chorus", "Bridge"}),
            progression[-1] if progression else {},
        ),
        "seasonal_atmosphere": infer_season(song),
        "urban_rural_mood": infer_urban_rural(song),
        "cinematic_pacing": song.get("pacing", "medium cinematic pacing"),
        "tension_curve": [item["intensity"] for item in progression],
    }


def infer_season(song: dict[str, Any]) -> str:
    text = " ".join(song.get("visual_cues", []) + song.get("mood", [])).lower()
    if "summer" in text:
        return "summer nostalgia"
    if "snow" in text or "winter" in text:
        return "winter stillness"
    if "rain" in text:
        return "rainy late spring night"
    return "season-neutral cinematic night"


def infer_urban_rural(song: dict[str, Any]) -> str:
    text = " ".join(song.get("visual_cues", [])).lower()
    urban_terms = ["city", "train", "subway", "street", "rooftop", "neon", "platform"]
    return "urban emotional atmosphere" if any(term in text for term in urban_terms) else "quiet rural or liminal atmosphere"


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
