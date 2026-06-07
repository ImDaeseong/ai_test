from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from common import PROJECT_ROOT


CONFIG_DIR = PROJECT_ROOT / "configs"
MOJIBAKE_MARKERS = ("�", "Ã", "Â", "ì", "ê", "ë", "í", "諛", "蹂", "醫", "怨", "媛", "몃", "꾨")


def load_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, str(exc)


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def validate_profile(profile: dict[str, Any], index: int, errors: list[str]) -> None:
    label = f"genres[{index}]"
    required = [
        "keys",
        "name",
        "style_id",
        "identity",
        "hair",
        "outfit",
        "silhouette",
        "prop",
        "locations",
        "texture",
    ]
    for key in required:
        require(key in profile, errors, f"{label}: missing {key}")
    require(
        isinstance(profile.get("keys"), list) and bool(profile.get("keys")),
        errors,
        f"{label}: keys must be a non-empty list",
    )
    require(
        isinstance(profile.get("locations"), list) and bool(profile.get("locations")),
        errors,
        f"{label}: locations must be a non-empty list",
    )


_MIN_UNIQUE_KEYS = 5  # profiles with fewer unique keys than this get a warning


def validate_configs() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    loaded: dict[str, Any] = {}
    for path in sorted(CONFIG_DIR.glob("*.json")):
        data, error = load_json(path)
        if error:
            errors.append(f"{path.name}: invalid JSON: {error}")
        else:
            loaded[path.stem] = data

    genres = loaded.get("genres")
    if genres is not None:
        require(isinstance(genres, list) and bool(genres), errors, "genres.json must be a non-empty list")
        if isinstance(genres, list):
            seen_names: set[str] = set()
            # Count how many profiles each key appears in
            key_profile_count: Counter[str] = Counter()
            for profile in genres:
                if isinstance(profile, dict):
                    for key in profile.get("keys", []):
                        normalized = str(key).strip().lower()
                        if normalized:
                            key_profile_count[normalized] += 1

            for index, profile in enumerate(genres):
                if not isinstance(profile, dict):
                    errors.append(f"genres[{index}]: profile must be an object")
                    continue
                validate_profile(profile, index, errors)
                name = str(profile.get("name", ""))
                if name in seen_names:
                    errors.append(f"genres[{index}]: duplicate profile name {name!r}")
                seen_names.add(name)
                for key in profile.get("keys", []):
                    normalized = str(key).strip().lower()
                    if not normalized:
                        errors.append(f"genres[{index}]: empty key")

            # Warn only when a profile has too few unique (exclusive) keys,
            # which would make it hard to distinguish from other profiles.
            # Shared keys across profiles are expected and intentional — genres
            # naturally overlap — so we do NOT warn per duplicated key.
            for index, profile in enumerate(genres):
                if not isinstance(profile, dict):
                    continue
                name = str(profile.get("name", ""))
                unique_count = sum(
                    1 for key in profile.get("keys", [])
                    if key_profile_count[str(key).strip().lower()] == 1
                )
                if unique_count < _MIN_UNIQUE_KEYS:
                    warnings.append(
                        f"genres.json: profile {name!r} has only {unique_count} unique key(s) "
                        f"— may be hard to distinguish from other profiles"
                    )

    platforms = loaded.get("platforms")
    if isinstance(platforms, dict):
        require(
            isinstance(platforms.get("platforms"), list) and bool(platforms.get("platforms")),
            errors,
            "platforms.json must define non-empty platforms",
        )
        require(
            isinstance(platforms.get("image_platforms"), list) and bool(platforms.get("image_platforms")),
            errors,
            "platforms.json must define non-empty image_platforms",
        )
        for section in ["platforms", "image_platforms"]:
            for index, item in enumerate(platforms.get(section, [])):
                require(isinstance(item, dict), errors, f"platforms.json {section}[{index}] must be an object")
                if isinstance(item, dict):
                    require(bool(item.get("id")), errors, f"platforms.json {section}[{index}] missing id")
                    require(bool(item.get("display_name")), errors, f"platforms.json {section}[{index}] missing display_name")
    elif platforms is not None:
        errors.append("platforms.json must be an object")

    required_object_keys = {
        "tag_classification": [
            "energy_tags",
            "instrument_terms",
            "genre_terms",
            "genre_instrument_exceptions",
            "vocal_terms",
            "mood_tag_map",
            "non_genre_terms",
        ],
        "instrument_hints": ["hints", "max_hints"],
        "palette_substitutions": ["main_color_patterns", "ambient_patterns", "style_word_substitutions"],
        "validation_rules": ["raw_palette_tokens", "noisy_learnable_tag_pattern"],
        "learning_rules": ["default_min_freq", "strip_prefix_pattern", "production_tag_pattern", "non_learnable_tags"],
        "color_palette": ["rules", "default"],
        "emotions": ["emotions"],
        "visual_styles": ["styles", "adaptive_style_map"],
        "genre_reference_profiles": ["schema_version", "safety_rule", "sources", "families"],
        "song_inference": ["profiles"],
        "emotion_transitions": ["chorus_lift_emotions", "chorus_lift_target", "bridge_deepen"],
        "song_sections": ["default_sections", "aliases"],
        "bpm_thresholds": ["thresholds"],
    }
    for name, keys in required_object_keys.items():
        data = loaded.get(name)
        if data is None:
            errors.append(f"{name}.json missing")
            continue
        require(isinstance(data, dict), errors, f"{name}.json must be an object")
        if isinstance(data, dict):
            for key in keys:
                require(key in data, errors, f"{name}.json missing {key}")

    emotions_data = loaded.get("emotions")
    if isinstance(emotions_data, dict):
        for ename, edef in emotions_data.get("emotions", {}).items():
            if not isinstance(edef, dict):
                errors.append(f"emotions.json: emotion {ename!r} must be an object")
                continue
            for required_field in ("lighting", "symbols", "camera"):
                if required_field not in edef:
                    warnings.append(f"emotions.json: emotion {ename!r} missing {required_field!r}")

    visual_styles_data = loaded.get("visual_styles")
    if isinstance(visual_styles_data, dict):
        for sid, sdef in visual_styles_data.get("styles", {}).items():
            if not isinstance(sdef, dict):
                errors.append(f"visual_styles.json: style {sid!r} must be an object")
                continue
            for required_field in ("name", "brand_palette"):
                if required_field not in sdef:
                    errors.append(f"visual_styles.json: style {sid!r} missing {required_field!r}")
            bp = sdef.get("brand_palette", {})
            if isinstance(bp, dict):
                for color_key in ("main_color", "shadow_color", "secondary_light", "highlight"):
                    if color_key not in bp:
                        warnings.append(f"visual_styles.json: style {sid!r} brand_palette missing {color_key!r}")

    reference_data = loaded.get("genre_reference_profiles")
    if isinstance(reference_data, dict):
        sources = reference_data.get("sources", {})
        families = reference_data.get("families", {})
        require(isinstance(sources, dict) and bool(sources), errors, "genre_reference_profiles.json sources must be a non-empty object")
        require(isinstance(families, dict) and bool(families), errors, "genre_reference_profiles.json families must be a non-empty object")
        required_family_fields = [
            "profile_names",
            "source_ids",
            "design_basis",
            "narrative_modes",
            "environments",
            "camera_language",
            "motion_language",
            "edit_language",
            "lighting_language",
            "character_language",
            "avoid",
        ]
        for family_id, family in families.items():
            if not isinstance(family, dict):
                errors.append(f"genre_reference_profiles.json family {family_id!r} must be an object")
                continue
            for field in required_family_fields:
                require(bool(family.get(field)), errors, f"genre_reference_profiles.json family {family_id!r} missing {field}")
            for source_id in family.get("source_ids", []):
                require(source_id in sources, errors, f"genre_reference_profiles.json family {family_id!r} has unknown source {source_id!r}")
        for source_id, source in sources.items():
            if not isinstance(source, dict):
                errors.append(f"genre_reference_profiles.json source {source_id!r} must be an object")
                continue
            for field in ("title", "url", "institution", "used_for"):
                require(bool(source.get(field)), errors, f"genre_reference_profiles.json source {source_id!r} missing {field}")

    for config_name, pattern_key in [
        ("learning_rules", "strip_prefix_pattern"),
        ("learning_rules", "production_tag_pattern"),
        ("validation_rules", "noisy_learnable_tag_pattern"),
    ]:
        data = loaded.get(config_name, {})
        if isinstance(data, dict) and isinstance(data.get(pattern_key), str):
            try:
                re.compile(data[pattern_key])
            except re.error as exc:
                errors.append(f"{config_name}.json {pattern_key} invalid regex: {exc}")

    return errors, warnings


def scan_mojibake() -> list[str]:
    warnings: list[str] = []
    for path in sorted(CONFIG_DIR.glob("*.json")):
        text = path.read_text(encoding="utf-8")
        hits: list[int] = []
        for line_no, line in enumerate(text.splitlines(), start=1):
            if any(marker in line for marker in MOJIBAKE_MARKERS):
                hits.append(line_no)
        if hits:
            preview = ", ".join(str(line_no) for line_no in hits[:12])
            suffix = "" if len(hits) <= 12 else f", +{len(hits) - 12} more"
            warnings.append(f"{path.name}: possible legacy mojibake text on lines {preview}{suffix}")
    return warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate config JSON structure and detect legacy mojibake text.")
    parser.add_argument("--strict-mojibake", action="store_true", help="Treat mojibake warnings as failures.")
    args = parser.parse_args()

    errors, warnings = validate_configs()
    mojibake_warnings = scan_mojibake()
    warnings.extend(mojibake_warnings)

    for error in errors:
        print(f"[FAIL] {error}")
    for warning in warnings:
        print(f"[WARN] {warning}")

    print(f"\nSummary: {len(errors)} errors, {len(warnings)} warnings")
    if errors or (args.strict_mojibake and mojibake_warnings):
        sys.exit(1)


if __name__ == "__main__":
    main()
