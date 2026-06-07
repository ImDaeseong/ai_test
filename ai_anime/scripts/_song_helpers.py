"""Shared low-level helpers used by world_builder, character_builder, scene_composer."""
from __future__ import annotations

import hashlib
from typing import Any

import palette_engine as _pe
from common import load_config

_BPM_CONFIG = load_config("bpm_thresholds")
_BPM_THRESHOLDS = _BPM_CONFIG.get("thresholds", {})


# ---------------------------------------------------------------------------
# Deterministic selection helpers
# ---------------------------------------------------------------------------

def _stable_choice(options: list[str], seed: str, salt: str) -> str:
    """Pick a deterministic option so one song stays consistent while other songs diverge."""
    if not options:
        return ""
    digest = hashlib.sha256(f"{seed}|{salt}".encode("utf-8")).hexdigest()
    return options[int(digest[:8], 16) % len(options)]


def _stable_order(options: list[str], seed: str, salt: str) -> list[str]:
    return sorted(
        [item for item in options if item],
        key=lambda item: hashlib.sha256(f"{seed}|{salt}|{item}".encode("utf-8")).hexdigest(),
    )


def _select_variant(value: Any, seed: str, salt: str) -> str:
    if isinstance(value, list):
        return _stable_choice([str(item) for item in value if str(item).strip()], seed, salt)
    return str(value or "")


def _profile_value(profile: dict[str, Any], key: str, seed: str, salt: str) -> str:
    plural = f"{key}s"
    if plural in profile:
        return _select_variant(profile.get(plural), seed, salt)
    return _select_variant(profile.get(key), seed, salt)


# ---------------------------------------------------------------------------
# Seed generators
# ---------------------------------------------------------------------------

def _section_seed(section: dict[str, Any], extra: str = "") -> str:
    return "|".join(
        str(value)
        for value in [
            section.get("index", ""),
            section.get("name", ""),
            section.get("lyrics", ""),
            section.get("description", ""),
            section.get("start_time", ""),
            extra,
        ]
    )


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


# ---------------------------------------------------------------------------
# BPM helpers
# ---------------------------------------------------------------------------

def _bpm_tempo(bpm: int | None) -> str:
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
    return template.format(main_color=_pe.BRAND_PALETTE.get("main_color", "accent color"))


def _bpm_transition_desc(bpm: int | None) -> str:
    return _bpm_desc(bpm, "transition_desc", "smooth rhythmic match cuts and gentle push transitions")


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def _with_color(text: str, main_color: str) -> str:
    return text.format(main_color=main_color) if text else ""


# ---------------------------------------------------------------------------
# Section helpers
# ---------------------------------------------------------------------------

def _is_instrumental_section(section: dict[str, Any]) -> bool:
    """Return True when a section has no Korean lyrics — production notes or silence only."""
    return not any("가" <= c <= "힣" for c in section.get("lyrics", ""))
