"""Song discovery module.

Scans an output root directory for song candidate folders and assesses
the readiness status of each one.

Only stdlib is used (pathlib, re).
"""

from __future__ import annotations

import re
from pathlib import Path

from webtoon_capcut.domain.enums import SongStatus
from webtoon_capcut.domain.models import Config, SongCandidate


# ---------------------------------------------------------------------------
# Status sort order — lower index = higher priority in batch output
# ---------------------------------------------------------------------------

_STATUS_ORDER: dict[SongStatus, int] = {
    SongStatus.BUILD_READY: 0,
    SongStatus.SUBTITLE_READY: 1,
    SongStatus.MEDIA_READY: 2,
    SongStatus.IMAGES_READY: 3,
    SongStatus.REVIEW_REQUIRED: 4,
    SongStatus.PROMPTS_ONLY: 5,
    SongStatus.BLOCKED: 6,
}

# ---------------------------------------------------------------------------
# File-detection helpers
# ---------------------------------------------------------------------------

_STORYBOARD_PRIMARY = "01_storyboard.md"
_STORYBOARD_PATTERN = re.compile(r"storyboard", re.IGNORECASE)

_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp"})
_AUDIO_EXTENSIONS = frozenset({".wav", ".flac", ".mp3", ".m4a"})
_SUBTITLE_EXTENSIONS = frozenset({".lrc", ".srt"})

# Directories that may contain panel images (ordered by preference)
_IMAGE_DIRS = ("img", "images", "generated", "generated/images")

# Regex for the panel_NNN filename pattern
_PANEL_ID_RE = re.compile(r"panel[_\-]?\d{3,}", re.IGNORECASE)


def _find_storyboard(song_dir: Path) -> Path | None:
    """Return the storyboard Markdown file inside *song_dir*, or None.

    Preference order:
    1. ``01_storyboard.md`` (primary canonical name)
    2. Any ``*storyboard*.md`` file (case-insensitive)

    If more than one candidate exists beyond the primary, the first
    alphabetically-sorted match is returned (deterministic, no ambiguity
    error at this layer — ambiguity is reported by the caller).
    """
    primary = song_dir / _STORYBOARD_PRIMARY
    if primary.is_file():
        return primary

    candidates = sorted(
        p for p in song_dir.glob("*.md")
        if _STORYBOARD_PATTERN.search(p.stem)
    )
    return candidates[0] if candidates else None


def _find_images(song_dir: Path) -> list[Path]:
    """Return all image files found in the known image sub-directories."""
    found: list[Path] = []
    for rel_dir in _IMAGE_DIRS:
        img_dir = song_dir / rel_dir
        if img_dir.is_dir():
            for ext in _IMAGE_EXTENSIONS:
                found.extend(img_dir.glob(f"*{ext}"))
                found.extend(img_dir.glob(f"*{ext.upper()}"))
    return found


def _find_audio(song_dir: Path) -> list[Path]:
    """Return all audio files found directly inside *song_dir*."""
    found: list[Path] = []
    for ext in _AUDIO_EXTENSIONS:
        found.extend(song_dir.glob(f"*{ext}"))
        found.extend(song_dir.glob(f"*{ext.upper()}"))
    return found


def _find_subtitles(song_dir: Path) -> list[Path]:
    """Return all LRC/SRT files found directly inside *song_dir*."""
    found: list[Path] = []
    for ext in _SUBTITLE_EXTENSIONS:
        found.extend(song_dir.glob(f"*{ext}"))
        found.extend(song_dir.glob(f"*{ext.upper()}"))
    return found


def _storyboard_has_panels(storyboard_path: Path) -> bool:
    """Quick heuristic: return True if the storyboard contains at least one
    panel row (i.e. a line matching the panel_NNN pattern inside a table).

    This avoids a full parse at the discovery stage.
    """
    try:
        text = storyboard_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(_PANEL_ID_RE.search(text))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def assess_song_status(
    song_dir: Path,
    config: Config | None = None,  # noqa: ARG001  (reserved for future policy use)
) -> SongCandidate:
    """Inspect a single song folder and return a SongCandidate with status.

    Status decision tree (first matching rule wins):

    1. BLOCKED     — ``song_dir`` does not exist or is not a directory.
    2. PROMPTS_ONLY — No storyboard **and** no images found.
    3. IMAGES_READY — Storyboard present **and** at least one panel image found.
    4. MEDIA_READY  — IMAGES_READY conditions **plus** at least one audio file.
    5. SUBTITLE_READY — MEDIA_READY conditions **plus** LRC or SRT present.
    6. BUILD_READY  — MEDIA_READY conditions **plus** storyboard contains
                      valid panel entries.
    7. PROMPTS_ONLY — Storyboard present but no images (fallback).

    Notes:
    - SUBTITLE_READY and BUILD_READY are both upgrades from MEDIA_READY.
      When both conditions are satisfied (subtitles present AND storyboard is
      valid), BUILD_READY takes precedence.
    - The ``reasons`` list records each positive or negative finding so the
      caller can diagnose what is missing.

    Args:
        song_dir: Absolute path to the song folder to assess.
        config:   Optional Config instance (reserved for future policy use).

    Returns:
        SongCandidate with ``title``, ``song_dir``, ``status``, and ``reasons``.
    """
    reasons: list[str] = []
    title = song_dir.name

    # Guard: directory must exist
    if not song_dir.is_dir():
        reasons.append(f"Directory does not exist or is not a directory: {song_dir}")
        return SongCandidate(
            title=title,
            song_dir=str(song_dir),
            status=SongStatus.BLOCKED,
            reasons=reasons,
        )

    # --- Probe files ---
    storyboard_path = _find_storyboard(song_dir)
    images = _find_images(song_dir)
    audio_files = _find_audio(song_dir)
    subtitle_files = _find_subtitles(song_dir)

    has_storyboard = storyboard_path is not None
    has_images = len(images) > 0
    has_audio = len(audio_files) > 0
    has_subtitles = len(subtitle_files) > 0

    # Record findings
    if has_storyboard:
        reasons.append(f"Storyboard found: {storyboard_path.name}")
    else:
        reasons.append("No storyboard file found")

    if has_images:
        reasons.append(f"Images found: {len(images)} file(s)")
    else:
        reasons.append("No panel images found")

    if has_audio:
        reasons.append(f"Audio found: {len(audio_files)} file(s)")
    else:
        reasons.append("No audio file found")

    if has_subtitles:
        exts = sorted({p.suffix.lower() for p in subtitle_files})
        reasons.append(f"Subtitles found: {', '.join(exts)}")
    else:
        reasons.append("No subtitle file found (LRC/SRT)")

    # --- Determine status ---

    # No storyboard and no images → prompts only
    if not has_storyboard and not has_images:
        return SongCandidate(
            title=title,
            song_dir=str(song_dir),
            status=SongStatus.PROMPTS_ONLY,
            reasons=reasons,
        )

    # Storyboard present and images present → at least IMAGES_READY
    if has_storyboard and has_images:
        if not has_audio:
            return SongCandidate(
                title=title,
                song_dir=str(song_dir),
                status=SongStatus.IMAGES_READY,
                reasons=reasons,
            )

        # MEDIA_READY baseline
        # Check for BUILD_READY: storyboard must contain valid panel entries
        storyboard_valid = _storyboard_has_panels(storyboard_path)
        if storyboard_valid:
            reasons.append("Storyboard panel entries validated")
            return SongCandidate(
                title=title,
                song_dir=str(song_dir),
                status=SongStatus.BUILD_READY,
                reasons=reasons,
            )

        # Not build-ready; check subtitles
        if has_subtitles:
            return SongCandidate(
                title=title,
                song_dir=str(song_dir),
                status=SongStatus.SUBTITLE_READY,
                reasons=reasons,
            )

        # MEDIA_READY: images + audio, but storyboard not valid
        reasons.append("Storyboard present but no panel entries found")
        return SongCandidate(
            title=title,
            song_dir=str(song_dir),
            status=SongStatus.MEDIA_READY,
            reasons=reasons,
        )

    # Storyboard present but no images, or images present but no storyboard
    # → treat as PROMPTS_ONLY (not enough to proceed)
    if has_storyboard and not has_images:
        reasons.append("Storyboard present but no images — cannot build")
    elif not has_storyboard and has_images:
        reasons.append("Images found but no storyboard — cannot determine panel order")

    return SongCandidate(
        title=title,
        song_dir=str(song_dir),
        status=SongStatus.PROMPTS_ONLY,
        reasons=reasons,
    )


def discover_songs(output_root: str | Path) -> list[SongCandidate]:
    """Scan *output_root* for song candidate folders and rank them by status.

    Each immediate sub-directory of *output_root* is treated as a potential
    song folder. Hidden directories (names starting with ``'.'``) are skipped.

    The returned list is sorted by status importance:
        BUILD_READY → SUBTITLE_READY → MEDIA_READY → IMAGES_READY
        → REVIEW_REQUIRED → PROMPTS_ONLY → BLOCKED

    Args:
        output_root: Path to the root output directory that contains one
            sub-folder per song.

    Returns:
        List of SongCandidate objects, sorted by descending readiness.
    """
    root = Path(output_root)

    if not root.is_dir():
        return []

    candidates: list[SongCandidate] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        candidate = assess_song_status(entry)
        candidates.append(candidate)

    candidates.sort(key=lambda c: _STATUS_ORDER.get(c.status, 99))
    return candidates
