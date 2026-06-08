"""CLI entry point for webtoon_capcut.

Usage:
    python -m webtoon_capcut <subcommand> [options]

Subcommands:
    discover    Scan output root and list song readiness status.
    inspect     Inspect a single song folder.
    normalize   Normalise subtitles for a song.
    plan        Generate edit timeline for a song.
    build       Normalise + plan for a single song.
    build-all   Batch build all (or ready-only) songs under an output root.

Exit codes:
    0  Success, no issues requiring review.
    1  Error (exception or fatal failure).
    2  Success but one or more REVIEW_REQUIRED issues present.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from webtoon_capcut.application.inspect_song import inspect_song
from webtoon_capcut.application.normalize_song import normalize_song
from webtoon_capcut.application.plan_song import plan_song
from webtoon_capcut.application.batch_build import build_all
from webtoon_capcut.discovery.song_discovery import discover_songs
from webtoon_capcut.infrastructure.logging import get_logger
from webtoon_capcut.infrastructure.paths import ensure_dir

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def _configure_logging(level: str) -> None:
    """Set the root logging level for the CLI run."""
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.root.setLevel(numeric)


def _output(data: object, use_json: bool) -> None:
    """Write *data* to stdout.

    When *use_json* is True, emit a single JSON Lines record.
    Otherwise pretty-print a human-readable representation.
    """
    if use_json:
        print(json.dumps(data, ensure_ascii=False), flush=True)
    else:
        _print_human(data)


def _print_human(data: object) -> None:
    """Print *data* in a readable table / summary format."""
    if isinstance(data, dict):
        _print_dict_human(data)
    elif isinstance(data, list):
        for item in data:
            _print_dict_human(item)
            print()
    else:
        print(data)


def _print_dict_human(d: dict) -> None:
    """Print a dict as aligned key: value pairs."""
    for key, value in d.items():
        if isinstance(value, (dict, list)):
            print(f"  {key}:")
            _print_nested(value, indent=4)
        else:
            print(f"  {key}: {value}")


def _print_nested(value: object, indent: int = 4) -> None:
    pad = " " * indent
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                print(f"{pad}{k}:")
                _print_nested(v, indent + 2)
            else:
                print(f"{pad}{k}: {v}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                _print_dict_human(item)
            else:
                print(f"{pad}- {item}")
    else:
        print(f"{pad}{value}")


def _has_review_issues(result: dict) -> bool:
    """Return True if *result* signals that human review is required."""
    # Check explicit status field
    status = result.get("status", "")
    if isinstance(status, str) and "REVIEW" in status.upper():
        return True

    # Check issues list for severity REVIEW/HOLD/BLOCKER
    for issue in result.get("issues", []):
        if isinstance(issue, dict):
            sev = issue.get("severity", "").upper()
            if sev in ("REVIEW", "HOLD", "BLOCKER"):
                return True

    # build-all songs sub-list
    for song in result.get("songs", []):
        if isinstance(song, dict) and song.get("result") in ("review", "fail"):
            return True

    return False


def _auto_workspace(song_dir: Path) -> Path:
    """Derive a default workspace path from song_dir.

    Convention: {cwd}/workspace/{song_id_slug}
    """
    from webtoon_capcut.infrastructure.paths import slugify
    slug = slugify(song_dir.name) or "song"
    return Path.cwd() / "workspace" / slug


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------


def _cmd_discover(args: argparse.Namespace) -> int:
    logger = get_logger(__name__)
    logger.info("discover started", extra={"output_root": args.output_root})

    output_root = Path(args.output_root)
    try:
        candidates = discover_songs(output_root)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    rows = [
        {
            "title": c.title,
            "status": c.status.value,
            "song_dir": c.song_dir,
            "reasons": list(c.reasons),
        }
        for c in candidates
    ]

    result = {"output_root": str(output_root), "count": len(rows), "songs": rows}

    if args.json:
        _output(result, use_json=True)
    else:
        print(f"Output root : {output_root}")
        print(f"Songs found : {len(rows)}")
        print()
        # Table header
        print(f"{'TITLE':<40}  {'STATUS':<18}  REASONS")
        print("-" * 80)
        for row in rows:
            reason_str = "; ".join(row["reasons"][:2])
            print(f"{row['title']:<40}  {row['status']:<18}  {reason_str}")

    has_review = any(r["status"] == "REVIEW_REQUIRED" for r in rows)
    return 2 if has_review else 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    logger = get_logger(__name__)
    song_dir = Path(args.song_dir)
    logger.info("inspect started", extra={"song_dir": str(song_dir)})

    try:
        result = inspect_song(song_dir)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    _output(result, use_json=args.json)
    return 2 if _has_review_issues(result) else 0


def _cmd_normalize(args: argparse.Namespace) -> int:
    logger = get_logger(__name__)
    song_dir = Path(args.song_dir)
    workspace_dir = Path(args.workspace)
    logger.info(
        "normalize started",
        extra={"song_dir": str(song_dir), "workspace": str(workspace_dir)},
    )

    try:
        ensure_dir(workspace_dir)
        result = normalize_song(song_dir=song_dir, workspace_dir=workspace_dir)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    _output(result, use_json=args.json)
    return 2 if _has_review_issues(result) else 0


def _cmd_plan(args: argparse.Namespace) -> int:
    logger = get_logger(__name__)
    song_dir = Path(args.song_dir)
    workspace_dir = Path(args.workspace)
    logger.info(
        "plan started",
        extra={"song_dir": str(song_dir), "workspace": str(workspace_dir)},
    )

    try:
        ensure_dir(workspace_dir)
        result = plan_song(song_dir=song_dir, workspace_dir=workspace_dir)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    _output(result, use_json=args.json)
    return 2 if _has_review_issues(result) else 0


def _cmd_build(args: argparse.Namespace) -> int:
    logger = get_logger(__name__)
    song_dir = Path(args.song_dir)

    if args.workspace:
        workspace_dir = Path(args.workspace)
    else:
        workspace_dir = _auto_workspace(song_dir)

    logger.info(
        "build started",
        extra={"song_dir": str(song_dir), "workspace": str(workspace_dir)},
    )

    try:
        ensure_dir(workspace_dir)

        norm_result = normalize_song(song_dir=song_dir, workspace_dir=workspace_dir)
        plan_result = plan_song(song_dir=song_dir, workspace_dir=workspace_dir)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    combined = {
        "song_dir": str(song_dir),
        "workspace": str(workspace_dir),
        "normalize": norm_result,
        "plan": plan_result,
    }
    _output(combined, use_json=args.json)

    review = _has_review_issues(norm_result) or _has_review_issues(plan_result)
    return 2 if review else 0


def _cmd_build_all(args: argparse.Namespace) -> int:
    logger = get_logger(__name__)
    output_root = Path(args.output_root)

    if args.workspace:
        workspace_root = Path(args.workspace)
    else:
        workspace_root = Path.cwd() / "workspace"

    ready_only = args.ready_only

    logger.info(
        "build-all started",
        extra={
            "output_root": str(output_root),
            "workspace_root": str(workspace_root),
            "ready_only": ready_only,
        },
    )

    try:
        ensure_dir(workspace_root)
        result = build_all(
            output_root=output_root,
            workspace_root=workspace_root,
            ready_only=ready_only,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    _output(result, use_json=args.json)
    return 2 if _has_review_issues(result) else 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="webtoon_capcut",
        description="Webtoon CapCut pipeline CLI",
    )
    # Top-level has no action — subcommand is required.
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- discover ---
    p_discover = subparsers.add_parser(
        "discover",
        help="Scan output root and list song readiness.",
    )
    p_discover.add_argument(
        "--output-root",
        required=True,
        metavar="PATH",
        help="Root directory containing one sub-folder per song.",
    )
    p_discover.add_argument("--json", action="store_true", help="Output JSON Lines.")
    p_discover.add_argument(
        "--log-level",
        default="INFO",
        choices=_LOG_LEVELS,
        metavar="LEVEL",
        help="Logging verbosity (default: INFO).",
    )

    # --- inspect ---
    p_inspect = subparsers.add_parser("inspect", help="Inspect a single song folder.")
    p_inspect.add_argument(
        "--song-dir",
        required=True,
        metavar="PATH",
        help="Path to the song folder.",
    )
    p_inspect.add_argument("--json", action="store_true", help="Output JSON Lines.")
    p_inspect.add_argument(
        "--log-level",
        default="INFO",
        choices=_LOG_LEVELS,
        metavar="LEVEL",
    )

    # --- normalize ---
    p_normalize = subparsers.add_parser(
        "normalize",
        help="Normalise subtitles for a song.",
    )
    p_normalize.add_argument("--song-dir", required=True, metavar="PATH")
    p_normalize.add_argument("--workspace", required=True, metavar="PATH")
    p_normalize.add_argument("--json", action="store_true")
    p_normalize.add_argument(
        "--log-level",
        default="INFO",
        choices=_LOG_LEVELS,
        metavar="LEVEL",
    )

    # --- plan ---
    p_plan = subparsers.add_parser("plan", help="Generate edit timeline for a song.")
    p_plan.add_argument("--song-dir", required=True, metavar="PATH")
    p_plan.add_argument("--workspace", required=True, metavar="PATH")
    p_plan.add_argument("--json", action="store_true")
    p_plan.add_argument(
        "--log-level",
        default="INFO",
        choices=_LOG_LEVELS,
        metavar="LEVEL",
    )

    # --- build ---
    p_build = subparsers.add_parser(
        "build",
        help="Normalise + plan for a single song (normalize then plan).",
    )
    p_build.add_argument("--song-dir", required=True, metavar="PATH")
    p_build.add_argument(
        "--workspace",
        default=None,
        metavar="PATH",
        help=(
            "Workspace directory for outputs. "
            "When omitted, defaults to {cwd}/workspace/{song_slug}."
        ),
    )
    p_build.add_argument("--json", action="store_true")
    p_build.add_argument(
        "--log-level",
        default="INFO",
        choices=_LOG_LEVELS,
        metavar="LEVEL",
    )

    # --- build-all ---
    p_build_all = subparsers.add_parser(
        "build-all",
        help="Batch build all (or ready-only) songs under an output root.",
    )
    p_build_all.add_argument("--output-root", required=True, metavar="PATH")
    p_build_all.add_argument(
        "--workspace",
        default=None,
        metavar="PATH",
        help="Workspace root for all per-song outputs (default: {cwd}/workspace).",
    )
    p_build_all.add_argument(
        "--ready-only",
        action="store_true",
        default=False,
        help="Process only BUILD_READY / SUBTITLE_READY songs.",
    )
    p_build_all.add_argument("--json", action="store_true")
    p_build_all.add_argument(
        "--log-level",
        default="INFO",
        choices=_LOG_LEVELS,
        metavar="LEVEL",
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    _configure_logging(args.log_level)

    _HANDLERS = {
        "discover": _cmd_discover,
        "inspect": _cmd_inspect,
        "normalize": _cmd_normalize,
        "plan": _cmd_plan,
        "build": _cmd_build,
        "build-all": _cmd_build_all,
    }

    handler = _HANDLERS.get(args.command)
    if handler is None:
        print(f"ERROR: unknown command '{args.command}'", file=sys.stderr)
        sys.exit(1)

    exit_code = handler(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
