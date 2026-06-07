from __future__ import annotations

from typing import Any

from _song_helpers import _stable_choice, song_character_seed
from common import load_config


_REFERENCE_CONFIG = load_config("genre_reference_profiles")


def select_genre_reference(profile: dict[str, Any]) -> dict[str, Any]:
    """Return generalized visual grammar for an existing genre profile."""
    profile_name = str(profile.get("name", "")).strip().lower()
    for reference_id, reference in _REFERENCE_CONFIG.get("families", {}).items():
        names = {str(name).strip().lower() for name in reference.get("profile_names", [])}
        if profile_name in names:
            return {"id": reference_id, **reference}
    return {}


def reference_variant(
    reference: dict[str, Any],
    key: str,
    seed: str,
    salt: str,
) -> str:
    values = [str(value).strip() for value in reference.get(key, []) if str(value).strip()]
    return _stable_choice(values, seed, f"genre_reference|{reference.get('id', '')}|{salt}")


def song_reference_variant(
    song: dict[str, Any],
    profile: dict[str, Any],
    key: str,
    salt: str,
) -> str:
    return reference_variant(select_genre_reference(profile), key, song_character_seed(song), salt)


def source_output_terms() -> list[str]:
    """Names that belong to provenance and must not leak into generated prompts."""
    terms: list[str] = []
    for source in _REFERENCE_CONFIG.get("sources", {}).values():
        for field in ("title", "institution"):
            value = str(source.get(field, "")).strip()
            if value and value not in terms:
                terms.append(value)
    return terms
