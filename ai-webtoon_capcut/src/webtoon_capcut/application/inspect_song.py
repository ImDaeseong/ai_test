"""inspect_song use-case.

Returns a JSON-serialisable summary of a song folder's current state:
status, reasons, asset inventory counts, and any detected issues.
"""
from __future__ import annotations

from pathlib import Path

from webtoon_capcut.domain.models import Config
from webtoon_capcut.infrastructure.config_loader import load_config
from webtoon_capcut.discovery.song_discovery import assess_song_status
from webtoon_capcut.discovery.asset_resolver import resolve_assets


def inspect_song(
    song_dir: str | Path,
    config: Config | None = None,
) -> dict:
    """Inspect a single song folder and return a JSON-serialisable summary.

    Args:
        song_dir: Absolute path to the song folder.
        config:   Optional pre-loaded Config.  When None, load_config() is
                  called to read ``config/default.json``.

    Returns:
        Dictionary with keys:
          song_dir, title, status, reasons, inventory, issues
    """
    song_dir = Path(song_dir)
    if config is None:
        config = load_config()

    # Assess readiness status (lightweight: no full parse)
    candidate = assess_song_status(song_dir, config)

    issues: list[str] = []

    # Resolve full asset inventory
    try:
        inventory = resolve_assets(song_dir, config)
    except Exception as exc:  # noqa: BLE001
        issues.append(f"Asset resolution failed: {exc}")
        inventory = None

    if inventory is not None:
        inventory_dict = {
            "storyboard_panel_count": inventory.storyboard_panel_count,
            "image_count": len(inventory.images),
            "audio_count": len(inventory.audio_candidates),
            "subtitle_count": len(inventory.subtitle_candidates),
            "conflicts": list(inventory.conflicts),
        }
        # Carry over conflicts as issues
        for conflict in inventory.conflicts:
            issues.append(f"CONFLICT: {conflict}")
        # Warn about missing audio
        if inventory.audio_candidates and len(inventory.audio_candidates) > 1:
            issues.append(
                f"AUDIO_AMBIGUOUS: {len(inventory.audio_candidates)} audio files found"
            )
        if inventory.storyboard_panel_count == 0:
            issues.append("STORYBOARD_MISSING: no panels found in storyboard")
        if not inventory.images:
            issues.append("IMAGE_MISSING: no panel images found")
    else:
        inventory_dict = {
            "storyboard_panel_count": 0,
            "image_count": 0,
            "audio_count": 0,
            "subtitle_count": 0,
            "conflicts": [],
        }

    return {
        "song_dir": str(song_dir),
        "title": candidate.title,
        "status": candidate.status.value,
        "reasons": list(candidate.reasons),
        "inventory": inventory_dict,
        "issues": issues,
    }
