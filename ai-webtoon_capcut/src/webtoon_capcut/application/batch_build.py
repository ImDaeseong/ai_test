"""batch_build use-case.

Discovers all songs under output_root and runs plan_song() on each,
collecting per-song results and summary counts.
"""
from __future__ import annotations

import traceback
from pathlib import Path

from webtoon_capcut.domain.enums import SongStatus
from webtoon_capcut.domain.models import Config
from webtoon_capcut.infrastructure.config_loader import load_config
from webtoon_capcut.infrastructure.paths import make_song_id, ensure_dir
from webtoon_capcut.discovery.song_discovery import discover_songs
from webtoon_capcut.application.plan_song import plan_song


# Statuses considered "ready to build"
_BUILD_THRESHOLD: frozenset[SongStatus] = frozenset(
    {SongStatus.BUILD_READY, SongStatus.SUBTITLE_READY}
)


def build_all(
    output_root: str | Path,
    workspace_root: str | Path,
    config: Config | None = None,
    ready_only: bool = True,
) -> dict:
    """Discover and process all songs under output_root.

    Args:
        output_root:    Directory that contains one sub-folder per song.
        workspace_root: Root workspace for all per-song outputs.
        config:         Optional Config; load_config() used when None.
        ready_only:     When True (default), skip songs below BUILD_READY.

    Returns:
        JSON-serialisable dict with keys:
          total, pass, review, skip, fail, songs
    """
    output_root = Path(output_root)
    workspace_root = Path(workspace_root)
    if config is None:
        config = load_config()

    candidates = discover_songs(output_root)

    total = len(candidates)
    count_pass = 0
    count_review = 0
    count_skip = 0
    count_fail = 0
    song_results: list[dict] = []

    for candidate in candidates:
        song_dir = Path(candidate.song_dir)
        song_id = make_song_id(candidate.title, candidate.song_dir)

        # Skip songs that are not ready when ready_only is set
        if ready_only and candidate.status not in _BUILD_THRESHOLD:
            count_skip += 1
            song_results.append(
                {
                    "song_id": song_id,
                    "title": candidate.title,
                    "status": candidate.status.value,
                    "result": "skip",
                    "reason": f"status {candidate.status.value!r} below BUILD_READY threshold",
                }
            )
            continue

        per_song_workspace = ensure_dir(workspace_root / song_id)

        try:
            plan_result = plan_song(
                song_dir=song_dir,
                workspace_dir=per_song_workspace,
                config=config,
            )

            # Determine pass/review based on validation issues
            has_gaps = plan_result.get("validation", {}).get("gap_count", 0) > 0
            has_invalid = (
                plan_result.get("validation", {}).get("invalid_clip_count", 0) > 0
            )
            has_issues = bool(plan_result.get("issues"))

            if has_gaps or has_invalid:
                result_label = "review"
                count_review += 1
            elif has_issues:
                result_label = "review"
                count_review += 1
            else:
                result_label = "pass"
                count_pass += 1

            song_results.append(
                {
                    "song_id": song_id,
                    "title": candidate.title,
                    "status": candidate.status.value,
                    "result": result_label,
                    "clip_count": plan_result.get("clip_count", 0),
                    "section_count": plan_result.get("section_count", 0),
                    "audio_duration_ms": plan_result.get("audio_duration_ms", 0),
                    "validation": plan_result.get("validation", {}),
                    "issues": plan_result.get("issues", []),
                    "output_timeline": plan_result.get("output_timeline"),
                }
            )

        except Exception as exc:  # noqa: BLE001
            count_fail += 1
            song_results.append(
                {
                    "song_id": song_id,
                    "title": candidate.title,
                    "status": candidate.status.value,
                    "result": "fail",
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
            # Continue processing remaining songs — one failure must not
            # block the batch (per 07_CODING_RULES.md §batch exception policy).

    return {
        "total": total,
        "pass": count_pass,
        "review": count_review,
        "skip": count_skip,
        "fail": count_fail,
        "songs": song_results,
    }
