"""normalize_song use-case.

Selects the best subtitle source (LRC/SRT), normalises it, and writes
``subtitles/cleaned.srt`` and ``subtitles/review.csv`` into the workspace.
"""
from __future__ import annotations

from pathlib import Path

from webtoon_capcut.domain.enums import SubtitleFormat
from webtoon_capcut.domain.models import Config, SubtitleDocument
from webtoon_capcut.infrastructure.config_loader import load_config
from webtoon_capcut.infrastructure.paths import make_song_id, ensure_dir
from webtoon_capcut.discovery.asset_resolver import resolve_assets
from webtoon_capcut.adapters.lrc import parse_lrc
from webtoon_capcut.adapters.srt import parse_srt
from webtoon_capcut.subtitles.suno_normalizer import normalize_subtitles, select_best_subtitle
from webtoon_capcut.subtitles.exporters import export_srt, export_review_csv


def normalize_song(
    song_dir: str | Path,
    workspace_dir: str | Path,
    config: Config | None = None,
) -> dict:
    """Normalise subtitles for a song and write cleaned outputs to workspace.

    Steps:
    1. resolve_assets() to discover subtitle candidates.
    2. Parse LRC and/or SRT files.
    3. select_best_subtitle() to pick the highest-quality source.
    4. normalize_subtitles() to classify cues and detect issues.
    5. Write workspace_dir/subtitles/cleaned.srt
    6. Write workspace_dir/subtitles/review.csv

    Args:
        song_dir:      Path to the raw song folder.
        workspace_dir: Per-song workspace root for outputs.
        config:        Optional Config; load_config() used when None.

    Returns:
        JSON-serialisable dict with keys:
          song_id, subtitle_source, normalization_state,
          cue_count, issues, output_srt
    """
    song_dir = Path(song_dir)
    workspace_dir = Path(workspace_dir)
    if config is None:
        config = load_config()

    song_id = make_song_id(song_dir.name, str(song_dir))

    # Step 1: resolve assets to get subtitle candidates
    inventory = resolve_assets(song_dir, config)

    # Step 2: parse LRC and SRT cues from discovered candidates
    lrc_cues = None
    srt_cues = None

    for candidate in inventory.subtitle_candidates:
        try:
            if candidate.fmt == SubtitleFormat.lrc and lrc_cues is None:
                lrc_cues = parse_lrc(candidate.path)
            elif candidate.fmt == SubtitleFormat.srt and srt_cues is None:
                srt_cues = parse_srt(candidate.path)
        except Exception:  # noqa: BLE001
            # Parsing failure is non-fatal; the other format may succeed.
            pass

    # Step 3: select best subtitle source
    best_cues, subtitle_source_reason = select_best_subtitle(lrc_cues, srt_cues)

    # Determine subtitle_source label
    if not best_cues:
        subtitle_source = "none"
    elif lrc_cues is not None and best_cues is lrc_cues:
        subtitle_source = "lrc"
    elif srt_cues is not None and best_cues is srt_cues:
        subtitle_source = "srt"
    else:
        # Fallback: inspect format from first cue
        if best_cues and best_cues[0].source_format == SubtitleFormat.lrc:
            subtitle_source = "lrc"
        elif best_cues:
            subtitle_source = "srt"
        else:
            subtitle_source = "none"

    # Step 4: normalise
    doc: SubtitleDocument = normalize_subtitles(best_cues, config.subtitles)

    # Step 5 & 6: write outputs
    subtitle_dir = ensure_dir(workspace_dir / "subtitles")
    srt_path = subtitle_dir / "cleaned.srt"
    csv_path = subtitle_dir / "review.csv"

    output_srt: str | None = None

    if best_cues:
        export_srt(doc, srt_path)
        output_srt = str(srt_path)

    export_review_csv(doc, csv_path)

    # Summarise issues
    issue_summaries = [
        {
            "issue_id": f"norm_{i:04d}",
            "severity": issue.get("severity", ""),
            "code": issue.get("code", ""),
            "message": issue.get("message", ""),
        }
        for i, issue in enumerate(doc.issues)
    ]

    return {
        "song_id": song_id,
        "subtitle_source": subtitle_source,
        "normalization_state": doc.normalization_state.value,
        "cue_count": len(doc.cues),
        "issues": issue_summaries,
        "output_srt": output_srt,
    }
