"""plan_song use-case.

Generates the edit timeline for a song:
  - Parses storyboard, probes audio, normalises subtitles.
  - Resolves section boundaries.
  - Allocates clips via plan_timeline().
  - Writes timeline.json and timeline.csv into workspace.
"""
from __future__ import annotations

import csv
import dataclasses
import json
from pathlib import Path

from webtoon_capcut.domain.models import Config, EditTimeline
from webtoon_capcut.infrastructure.config_loader import load_config
from webtoon_capcut.infrastructure.paths import make_song_id, ensure_dir
from webtoon_capcut.discovery.asset_resolver import resolve_assets
from webtoon_capcut.adapters.storyboard_markdown import parse_storyboard
from webtoon_capcut.adapters.audio_probe import probe_audio
from webtoon_capcut.adapters.lrc import parse_lrc
from webtoon_capcut.adapters.srt import parse_srt
from webtoon_capcut.subtitles.suno_normalizer import normalize_subtitles, select_best_subtitle
from webtoon_capcut.sections.boundary_resolver import resolve_sections
from webtoon_capcut.timeline.allocator import plan_timeline
from webtoon_capcut.domain.enums import SubtitleFormat


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_STORYBOARD_PRIMARY = "01_storyboard.md"
_STORYBOARD_FALLBACK_GLOB = "*storyboard*.md"


def _find_storyboard(song_dir: Path) -> Path | None:
    """Locate the storyboard file within song_dir."""
    primary = song_dir / _STORYBOARD_PRIMARY
    if primary.is_file():
        return primary
    candidates = sorted(song_dir.glob(_STORYBOARD_FALLBACK_GLOB))
    return candidates[0] if candidates else None


def _timeline_to_json_dict(timeline: EditTimeline) -> dict:
    """Convert EditTimeline to a JSON-serialisable dict."""

    def _convert(obj):
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return {
                k: _convert(v)
                for k, v in dataclasses.asdict(obj).items()
            }
        if hasattr(obj, "value"):  # Enum
            return obj.value
        if isinstance(obj, list):
            return [_convert(i) for i in obj]
        return obj

    return _convert(timeline)


def _write_timeline_csv(timeline: EditTimeline, output_path: Path) -> None:
    """Write timeline clips to CSV.

    Columns: clip_id, start_ms, end_ms, panel_id, section_id, motion
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["clip_id", "start_ms", "end_ms", "panel_id", "section_id", "motion"],
        )
        writer.writeheader()
        for clip in timeline.clips:
            writer.writerow(
                {
                    "clip_id": clip.clip_id,
                    "start_ms": clip.start_ms,
                    "end_ms": clip.end_ms,
                    "panel_id": clip.panel_id,
                    "section_id": clip.section_id,
                    "motion": clip.motion_preset,
                }
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def plan_song(
    song_dir: str | Path,
    workspace_dir: str | Path,
    config: Config | None = None,
) -> dict:
    """Generate the edit timeline for a song and write it to workspace.

    Steps:
    1. resolve_assets() to confirm assets exist.
    2. parse_storyboard() to load panel ordering.
    3. probe_audio() to get audio duration.
    4. Normalise subtitles (reuses normalize_song logic inline).
    5. resolve_sections() to obtain section boundaries.
    6. plan_timeline() to allocate clips.
    7. Write workspace_dir/timeline/timeline.json
    8. Write workspace_dir/timeline/timeline.csv

    Args:
        song_dir:      Path to the raw song folder.
        workspace_dir: Per-song workspace root.
        config:        Optional Config; load_config() used when None.

    Returns:
        JSON-serialisable dict with keys:
          song_id, audio_duration_ms, section_count, clip_count,
          validation, issues, output_timeline
    """
    song_dir = Path(song_dir)
    workspace_dir = Path(workspace_dir)
    if config is None:
        config = load_config()

    song_id = make_song_id(song_dir.name, str(song_dir))
    issues: list[str] = []

    # Step 1: resolve assets
    inventory = resolve_assets(song_dir, config)

    # Step 2: parse storyboard
    storyboard_path = _find_storyboard(song_dir)
    if storyboard_path is None:
        issues.append("STORYBOARD_MISSING: no storyboard file found")
        from webtoon_capcut.domain.models import Storyboard
        storyboard = Storyboard()
    else:
        storyboard = parse_storyboard(storyboard_path)

    # Step 3: probe audio
    audio_duration_ms = 0
    if not inventory.audio_candidates:
        issues.append("AUDIO_MISSING: no audio file found")
    elif len(inventory.audio_candidates) > 1:
        issues.append(
            f"AUDIO_AMBIGUOUS: {len(inventory.audio_candidates)} audio candidates"
        )
        # Use the first candidate — it was sorted by filename (deterministic)
        best_audio = inventory.audio_candidates[0]
        probed = probe_audio(best_audio.path)
        if probed.duration_ms is not None:
            audio_duration_ms = probed.duration_ms
        else:
            issues.append("AUDIO_MISSING: could not determine audio duration")
    else:
        probed = probe_audio(inventory.audio_candidates[0].path)
        if probed.duration_ms is not None:
            audio_duration_ms = probed.duration_ms
        else:
            issues.append("AUDIO_MISSING: could not determine audio duration")

    # Step 4: obtain subtitle document (optional)
    subtitle_doc = None
    lrc_cues = None
    srt_cues = None

    for candidate in inventory.subtitle_candidates:
        try:
            if candidate.fmt == SubtitleFormat.lrc and lrc_cues is None:
                lrc_cues = parse_lrc(candidate.path)
            elif candidate.fmt == SubtitleFormat.srt and srt_cues is None:
                srt_cues = parse_srt(candidate.path)
        except Exception:  # noqa: BLE001
            pass

    best_cues, _reason = select_best_subtitle(lrc_cues, srt_cues)
    if best_cues:
        subtitle_doc = normalize_subtitles(best_cues, config.subtitles)

    # Step 5: resolve section boundaries
    sections = resolve_sections(
        storyboard=storyboard,
        subtitle_doc=subtitle_doc,
        audio_duration_ms=audio_duration_ms,
        config=config,
    )

    # Step 6: plan timeline
    timeline: EditTimeline = plan_timeline(
        storyboard=storyboard,
        inventory=inventory,
        sections=sections,
        audio_duration_ms=audio_duration_ms,
        config=config,
    )

    # Step 7 & 8: write outputs
    timeline_dir = ensure_dir(workspace_dir / "timeline")
    json_path = timeline_dir / "timeline.json"
    csv_path = timeline_dir / "timeline.csv"

    timeline_dict = _timeline_to_json_dict(timeline)
    json_path.write_text(
        json.dumps(timeline_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_timeline_csv(timeline, csv_path)

    return {
        "song_id": song_id,
        "audio_duration_ms": audio_duration_ms,
        "section_count": len(sections.sections),
        "clip_count": len(timeline.clips),
        "validation": {
            "gap_count": timeline.validation.gap_count,
            "invalid_clip_count": timeline.validation.invalid_clip_count,
        },
        "issues": issues,
        "output_timeline": str(json_path),
    }
