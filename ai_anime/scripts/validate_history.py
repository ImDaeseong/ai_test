from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import config_learner
import emotion_engine
import scene_generator
from common import PROJECT_ROOT, load_config


HISTORY_FILE = PROJECT_ROOT / "data" / "suno_history.jsonl"
_VALIDATION_CONFIG = load_config("validation_rules")
NOISY_LEARNABLE_RE = re.compile(
    _VALIDATION_CONFIG.get("noisy_learnable_tag_pattern", r"$^"),
    re.I,
)


def load_history(path: Path = HISTORY_FILE) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            entries.append({"_error": f"line {line_no}: invalid json: {exc}"})
            continue
        entry["_line_no"] = line_no
        entries.append(entry)
    return entries


def patterns_for(entry: dict[str, Any]) -> dict[str, Any]:
    patterns = entry.get("patterns")
    return patterns if isinstance(patterns, dict) else {}


def synthetic_sections(patterns: dict[str, Any]) -> list[dict[str, Any]]:
    names = patterns.get("section_structure") or ["Intro"]
    if not isinstance(names, list) or not names:
        names = ["Intro"]
    sections = []
    for index, name in enumerate(names, start=1):
        section_name = str(name or "Intro")
        sections.append(
            {
                "index": index,
                "name": section_name,
                "lyrics": "",
                "description": "history metadata validation",
                "intensity": "high" if section_name == "Chorus" else "medium",
                "visual_cues": ["song-specific setting", "signature prop", "expressive lighting"],
            }
        )
    return sections


def synthetic_song(entry: dict[str, Any]) -> dict[str, Any]:
    patterns = patterns_for(entry)
    mood = patterns.get("mood") if isinstance(patterns.get("mood"), list) else []
    style_tags = patterns.get("style_tags") if isinstance(patterns.get("style_tags"), list) else []
    instruments = patterns.get("instruments") if isinstance(patterns.get("instruments"), list) else []
    return {
        "title": entry.get("title") or f"history line {entry.get('_line_no', '?')}",
        "source_file": "suno_history.jsonl",
        "genre": patterns.get("genre") or "",
        "bpm": patterns.get("bpm"),
        "energy": patterns.get("energy") or "medium",
        "mood": mood or ["cinematic"],
        "instruments": instruments,
        "vocal_style": patterns.get("vocal_style") or "",
        "style_tags": style_tags,
        "negative_tags": [],
        "visual_cues": ["song-specific setting", "signature prop", "expressive lighting"],
        "atmosphere": ", ".join(mood) if mood else "cinematic",
        "pacing": "history metadata validation",
        "sections": synthetic_sections(patterns),
        "timed_lyrics": [],
        "timing_mode": "history_metadata",
    }


def validate_entry(entry: dict[str, Any], prompt_smoke: str) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, Any] = {}

    if entry.get("_error"):
        return [entry["_error"]], warnings, stats

    patterns = patterns_for(entry)
    if not patterns:
        errors.append("missing patterns")
        return errors, warnings, stats

    bpm = patterns.get("bpm")
    if bpm is not None and not (isinstance(bpm, int) and 40 <= bpm <= 220):
        errors.append(f"invalid bpm: {bpm!r}")

    sections = patterns.get("section_structure")
    section_count = patterns.get("section_count")
    if isinstance(sections, list) and isinstance(section_count, int) and section_count != len(sections):
        errors.append(f"section_count mismatch: {section_count} != {len(sections)}")

    learnable_tags = config_learner.tags_from_entry(entry)
    noisy_tags = [tag for tag in learnable_tags if NOISY_LEARNABLE_RE.search(tag)]
    if noisy_tags:
        errors.append(f"production tags accepted as learnable: {noisy_tags[:5]!r}")
    stats["learnable_tag_count"] = len(learnable_tags)

    song = synthetic_song(entry)
    try:
        profile = scene_generator.choose_genre_profile(song)
        scene_generator.select_theme(profile.get("style_id"))
        main_color = scene_generator.pick_main_color(song)
        scene_generator._inject_song_color(main_color)
        stats["genre_profile"] = profile.get("name", "")
        stats["main_color"] = main_color
    except Exception as exc:
        errors.append(f"genre/color matching failed: {exc}")

    should_smoke = prompt_smoke == "all" or (
        prompt_smoke == "structured" and bool(patterns.get("section_count"))
    )
    if should_smoke and not errors:
        try:
            profile = scene_generator.choose_genre_profile(song)
            scene_generator.select_theme(profile.get("style_id"))
            scene_generator._inject_song_color(scene_generator.pick_main_color(song))
            emotion = emotion_engine.analyze_song(song)
            world = scene_generator.create_visual_world(song, emotion)
            protagonist = scene_generator.create_protagonist(song, world)
            scenes = scene_generator.generate_scenes(song, emotion, world, protagonist)
            if scenes:
                image_prompt = scene_generator.image_prompt(scenes[0], protagonist, world)
                video_prompt = scene_generator.video_prompt(scenes[0], protagonist, world)
                if not image_prompt.strip() or not video_prompt.strip():
                    errors.append("empty prompt generated")
            stats["scene_count"] = len(scenes)
            stats["prompt_smoked"] = True
        except Exception as exc:
            errors.append(f"metadata prompt smoke test failed: {exc}")

    if not learnable_tags:
        warnings.append("no learnable genre/style tags after filtering")

    return errors, warnings, stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate all data/suno_history.jsonl entries as metadata/config regression coverage."
    )
    parser.add_argument("--limit", type=int, help="Validate only the first N deduped entries.")
    parser.add_argument(
        "--prompt-smoke",
        choices=["none", "structured", "all"],
        default="structured",
        help="Run prompt smoke tests for no entries, entries with section_count, or all entries.",
    )
    parser.add_argument("--show-ok", action="store_true", help="Print passing rows as well as failures.")
    args = parser.parse_args()

    raw_entries = load_history()
    parse_errors = [entry for entry in raw_entries if entry.get("_error")]
    valid_entries = [entry for entry in raw_entries if not entry.get("_error")]
    entries = [*parse_errors, *config_learner.dedupe_composite(valid_entries)]
    if args.limit:
        entries = entries[: args.limit]

    counts = {"pass": 0, "fail": 0, "warn": 0}
    profile_counter: Counter[str] = Counter()
    color_counter: Counter[str] = Counter()
    learnable_tag_total = 0

    for entry in entries:
        errors, warnings, stats = validate_entry(entry, args.prompt_smoke)
        label = f"line {entry.get('_line_no', '?')} {entry.get('title', '')}".strip()
        if errors:
            counts["fail"] += 1
            print(f"[FAIL] {label}")
            for error in errors:
                print(f"  - {error}")
        else:
            counts["pass"] += 1
            if warnings:
                counts["warn"] += 1
            if args.show_ok:
                prefix = "WARN" if warnings else "PASS"
                print(f"[{prefix}] {label}")
                for warning in warnings:
                    print(f"  - {warning}")

        if stats.get("genre_profile"):
            profile_counter[stats["genre_profile"]] += 1
        if stats.get("main_color"):
            color_counter[stats["main_color"]] += 1
        learnable_tag_total += int(stats.get("learnable_tag_count", 0))

    print(
        "\nSummary: "
        f"{counts['pass']} passed, {counts['fail']} failed, "
        f"{counts['warn']} warnings, {len(entries)} entries checked"
    )
    print(f"Learnable tags after filtering: {learnable_tag_total}")
    print("Top genre profiles:", dict(profile_counter.most_common(8)))
    print("Top main colors:", dict(color_counter.most_common(8)))

    if counts["fail"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
