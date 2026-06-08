"""Asset resolver module.

Resolves all media assets for a single song folder into an AssetInventory:
  - Panel images (matched by panel_NNN filename pattern)
  - Audio candidates (found at song folder root)
  - Subtitle candidates (LRC/SRT, quality-scored)
  - Storyboard panel count

Design rules applied (from 09_REUSABLE_PROGRAM_ARCHITECTURE.md §9):
  - Image directories are searched in config-defined order.
  - Matching key is ``panel_NNN`` extracted from the filename stem.
  - Duplicate panel IDs across directories → recorded in conflicts.
  - Audio found at song folder root; all supported extensions probed.
  - Both LRC and SRT parsed when present; quality score computed for each.
  - Storyboard: ``01_storyboard.md`` preferred; falls back to *storyboard*.md.

Only stdlib is used (pathlib, re).
"""

from __future__ import annotations

import re
from pathlib import Path

from webtoon_capcut.adapters.audio_probe import probe_audio
from webtoon_capcut.adapters.image_probe import probe_image
from webtoon_capcut.adapters.lrc import lrc_quality_score, parse_lrc
from webtoon_capcut.adapters.srt import parse_srt, srt_quality_score
from webtoon_capcut.adapters.storyboard_markdown import parse_storyboard
from webtoon_capcut.domain.enums import SubtitleFormat
from webtoon_capcut.domain.models import (
    AssetInventory,
    AudioCandidate,
    Config,
    ImageCandidate,
    SubtitleCandidate,
)
from webtoon_capcut.infrastructure.hashing import sha256_file
from webtoon_capcut.infrastructure.config_loader import load_config  # noqa: F401 (re-exported for callers)

# ---------------------------------------------------------------------------
# Constants / defaults (mirrors config/default.json §assets)
# ---------------------------------------------------------------------------

_DEFAULT_IMAGE_DIRS: list[str] = ["img", "images", "generated", "generated/images"]
_DEFAULT_IMAGE_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".webp"})
_DEFAULT_AUDIO_EXTENSIONS: frozenset[str] = frozenset({".wav", ".flac", ".mp3", ".m4a"})

_PANEL_ID_RE = re.compile(r"panel[_\-]?(\d{3,})", re.IGNORECASE)

_STORYBOARD_PRIMARY = "01_storyboard.md"
_STORYBOARD_GLOB_PATTERN = re.compile(r"storyboard", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_image_dirs(config: Config) -> list[str]:
    """Return the ordered list of image sub-directory names from *config*.

    Falls back to the hard-coded defaults when the config object does not
    carry an ``assets`` attribute (current model version).
    """
    assets = getattr(config, "assets", None)
    if assets is not None:
        dirs = getattr(assets, "image_directories", None)
        if dirs:
            return list(dirs)
    return list(_DEFAULT_IMAGE_DIRS)


def _get_image_extensions(config: Config) -> frozenset[str]:
    """Return the set of supported image extensions from *config*."""
    assets = getattr(config, "assets", None)
    if assets is not None:
        exts = getattr(assets, "image_extensions", None)
        if exts:
            return frozenset(e.lower() for e in exts)
    return _DEFAULT_IMAGE_EXTENSIONS


def _get_audio_extensions(config: Config) -> frozenset[str]:
    """Return the set of supported audio extensions from *config*."""
    assets = getattr(config, "assets", None)
    if assets is not None:
        exts = getattr(assets, "audio_extensions", None)
        if exts:
            return frozenset(e.lower() for e in exts)
    return _DEFAULT_AUDIO_EXTENSIONS


def _extract_panel_id(stem: str) -> str | None:
    """Extract a normalised panel ID (``panel_NNN``) from a filename stem.

    Returns ``None`` when the stem contains no recognisable ``panel_NNN``
    pattern.

    Examples::

        "panel_001_intro_wide"  -> "panel_001"
        "panel-042"             -> "panel_042"
        "some_image"            -> None
    """
    m = _PANEL_ID_RE.search(stem)
    if not m:
        return None
    return f"panel_{int(m.group(1)):03d}"


def _find_storyboard(song_dir: Path) -> Path | None:
    """Return the canonical storyboard file in *song_dir*, or None.

    Search order:
    1. ``01_storyboard.md`` (exact primary name)
    2. Any ``*storyboard*.md`` (case-insensitive), alphabetically first
    """
    primary = song_dir / _STORYBOARD_PRIMARY
    if primary.is_file():
        return primary

    candidates = sorted(
        p for p in song_dir.glob("*.md")
        if _STORYBOARD_GLOB_PATTERN.search(p.stem)
    )
    return candidates[0] if candidates else None


# ---------------------------------------------------------------------------
# Sub-resolvers
# ---------------------------------------------------------------------------


def _resolve_images(
    song_dir: Path,
    image_dirs: list[str],
    image_extensions: frozenset[str],
    conflicts: list[str],
) -> list[ImageCandidate]:
    """Scan configured image directories and match files to panel IDs.

    Panel IDs are extracted from filenames using the ``panel_NNN`` pattern.
    Files without a recognisable panel ID are skipped.

    When the same ``panel_NNN`` is found in more than one directory (or more
    than once within the same directory), the first occurrence (in
    ``image_dirs`` order) is kept and all subsequent paths are added to
    *conflicts*.

    Args:
        song_dir:         Root song directory.
        image_dirs:       Ordered list of sub-directory names to search.
        image_extensions: Set of accepted file extensions (lower-cased, with dot).
        conflicts:        Mutable list; conflict descriptions are appended here.

    Returns:
        List of ImageCandidate objects, one per unique panel ID (ordered by
        the ``panel_NNN`` string so the result is deterministic).
    """
    seen: dict[str, ImageCandidate] = {}  # panel_id -> first candidate

    for rel_dir in image_dirs:
        img_dir = song_dir / rel_dir
        if not img_dir.is_dir():
            continue

        # Collect and sort for determinism
        entries: list[Path] = sorted(
            p for p in img_dir.iterdir()
            if p.is_file() and p.suffix.lower() in image_extensions
        )

        for path in entries:
            panel_id = _extract_panel_id(path.stem)
            if panel_id is None:
                continue  # not a panel image

            if panel_id in seen:
                conflicts.append(
                    f"Duplicate panel_id '{panel_id}': "
                    f"keeping {seen[panel_id].path!r}, "
                    f"ignoring {str(path)!r}"
                )
                continue

            candidate = probe_image(path, panel_id)
            seen[panel_id] = candidate

    return sorted(seen.values(), key=lambda c: c.panel_id)


def _resolve_audio(
    song_dir: Path,
    audio_extensions: frozenset[str],
) -> list[AudioCandidate]:
    """Find audio files at the song folder root and probe each one.

    Args:
        song_dir:          Root song directory.
        audio_extensions:  Set of accepted audio extensions (lower-cased, with dot).

    Returns:
        List of AudioCandidate objects sorted by filename for determinism.
    """
    candidates: list[AudioCandidate] = []
    entries = sorted(
        p for p in song_dir.iterdir()
        if p.is_file() and p.suffix.lower() in audio_extensions
    )
    for path in entries:
        candidate = probe_audio(path)
        candidates.append(candidate)
    return candidates


def _resolve_subtitles(song_dir: Path) -> list[SubtitleCandidate]:
    """Find LRC/SRT files in *song_dir*, parse them, and score their quality.

    Both formats are collected when present. The returned list contains one
    SubtitleCandidate per file, sorted by descending quality_score so the
    best candidate appears first.

    Args:
        song_dir: Root song directory.

    Returns:
        List of SubtitleCandidate objects, best quality first.
    """
    candidates: list[SubtitleCandidate] = []

    lrc_files = sorted(song_dir.glob("*.lrc")) + sorted(song_dir.glob("*.LRC"))
    srt_files = sorted(song_dir.glob("*.srt")) + sorted(song_dir.glob("*.SRT"))

    for path in lrc_files:
        try:
            cues = parse_lrc(path)
            score = lrc_quality_score(cues)
        except Exception:  # noqa: BLE001 — parse errors must not crash discovery
            cues = []
            score = 0.0
        try:
            file_hash = sha256_file(path)
        except OSError:
            file_hash = ""
        candidates.append(
            SubtitleCandidate(
                path=str(path),
                fmt=SubtitleFormat.lrc,
                cue_count=len(cues),
                quality_score=score,
                sha256=file_hash,
            )
        )

    for path in srt_files:
        try:
            cues = parse_srt(path)
            score = srt_quality_score(cues)
        except Exception:  # noqa: BLE001
            cues = []
            score = 0.0
        try:
            file_hash = sha256_file(path)
        except OSError:
            file_hash = ""
        candidates.append(
            SubtitleCandidate(
                path=str(path),
                fmt=SubtitleFormat.srt,
                cue_count=len(cues),
                quality_score=score,
                sha256=file_hash,
            )
        )

    candidates.sort(key=lambda c: c.quality_score, reverse=True)
    return candidates


def _resolve_storyboard_panel_count(song_dir: Path) -> int:
    """Return the number of panels found in the song's storyboard.

    Returns 0 when no storyboard file is present or the parse yields no
    panels.

    Args:
        song_dir: Root song directory.

    Returns:
        Integer panel count (>= 0).
    """
    storyboard_path = _find_storyboard(song_dir)
    if storyboard_path is None:
        return 0
    storyboard = parse_storyboard(storyboard_path)
    return len(storyboard.panels)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_assets(song_dir: str | Path, config: Config) -> AssetInventory:
    """Resolve all media assets for a single song folder.

    Applies the asset discovery rules from §9 of
    ``09_REUSABLE_PROGRAM_ARCHITECTURE.md``:

    - Images are searched in the directories listed in
      ``config.assets.image_directories`` (or the built-in defaults).
    - Panel ID is extracted from the ``panel_NNN`` pattern in each filename.
    - Duplicate panel IDs are recorded in ``AssetInventory.conflicts``.
    - Audio is searched at the song root using the extensions in
      ``config.assets.audio_extensions``.
    - LRC and SRT files are both parsed; quality scores are computed.
    - The storyboard panel count is extracted via ``parse_storyboard``.

    Args:
        song_dir: Absolute (or resolvable) path to the song folder.
        config:   Loaded Config instance providing discovery policies.

    Returns:
        A fully populated AssetInventory.
    """
    root = Path(song_dir)

    image_dirs = _get_image_dirs(config)
    image_extensions = _get_image_extensions(config)
    audio_extensions = _get_audio_extensions(config)

    conflicts: list[str] = []

    images = _resolve_images(root, image_dirs, image_extensions, conflicts)
    audio_candidates = _resolve_audio(root, audio_extensions)
    subtitle_candidates = _resolve_subtitles(root)
    storyboard_panel_count = _resolve_storyboard_panel_count(root)

    return AssetInventory(
        schema_version="2.0",
        storyboard_panel_count=storyboard_panel_count,
        images=images,
        audio_candidates=audio_candidates,
        subtitle_candidates=subtitle_candidates,
        conflicts=conflicts,
    )
