"""Configuration loader for webtoon_capcut.

Loads ``config/default.json`` (or an explicit path) and converts the raw
dictionary into the typed :class:`~webtoon_capcut.domain.models.Config`
dataclass hierarchy.

Only stdlib is used (json, pathlib).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from webtoon_capcut.domain.models import (
    CanvasConfig,
    ClipPolicy,
    Config,
    SubtitlePolicy,
)
from webtoon_capcut.infrastructure.paths import config_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_config(path: str | Path | None = None) -> Config:
    """Load and parse the project configuration file.

    Args:
        path: Path to a JSON configuration file.  When *None* the default
            location returned by :func:`~webtoon_capcut.infrastructure.paths.config_path`
            is used.

    Returns:
        A fully populated :class:`~webtoon_capcut.domain.models.Config` instance.

    Raises:
        FileNotFoundError: If the resolved path does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        KeyError: If required top-level sections are absent.
    """
    resolved: Path = Path(path) if path is not None else config_path()

    with open(resolved, encoding="utf-8") as fh:
        raw: dict[str, Any] = json.load(fh)

    return _dict_to_config(raw)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _dict_to_config(d: dict[str, Any]) -> Config:
    """Convert a raw configuration dictionary into a :class:`Config` dataclass.

    Args:
        d: Dictionary parsed directly from the JSON configuration file.

    Returns:
        :class:`Config` instance with nested :class:`CanvasConfig`,
        :class:`ClipPolicy`, and :class:`SubtitlePolicy`.
    """
    canvas_raw: dict[str, Any] = d.get("canvas", {})
    clips_raw: dict[str, Any] = d.get("clips", {})
    subtitles_raw: dict[str, Any] = d.get("subtitles", {})

    canvas = CanvasConfig(
        width=int(canvas_raw.get("width", 1920)),
        height=int(canvas_raw.get("height", 1080)),
        fps=int(canvas_raw.get("fps", 30)),
        fit=str(canvas_raw.get("fit", "cover")),
        transition_ms=int(canvas_raw.get("transition_ms", 300)),
    )

    clips = ClipPolicy(
        min_seconds=float(clips_raw.get("min_seconds", 2.5)),
        preferred_min_seconds=float(clips_raw.get("preferred_min_seconds", 4.0)),
        preferred_max_seconds=float(clips_raw.get("preferred_max_seconds", 8.0)),
        hard_max_seconds=float(clips_raw.get("hard_max_seconds", 12.0)),
        max_reuse_per_image=int(clips_raw.get("max_reuse_per_image", 3)),
    )

    # Subtitles section has nested objects in default.json.
    long_cue_raw: dict[str, Any] = subtitles_raw.get("long_cue", {})
    alignment_raw: dict[str, Any] = subtitles_raw.get("alignment", {})

    subtitles = SubtitlePolicy(
        long_cue_median_multiplier=float(
            long_cue_raw.get("median_multiplier", 2.5)
        ),
        long_cue_absolute_floor_seconds=float(
            long_cue_raw.get("absolute_floor_seconds", 10.0)
        ),
        alignment_mode=str(alignment_raw.get("mode", "auto")),
        hold_on_unresolved_long_cue=bool(
            alignment_raw.get("hold_on_unresolved_long_cue", True)
        ),
    )

    schema_version: str = str(d.get("schema_version", "3.0"))

    return Config(
        schema_version=schema_version,
        canvas=canvas,
        clips=clips,
        subtitles=subtitles,
    )
