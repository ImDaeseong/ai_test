"""LRC subtitle parser.

Supports timestamps in [MM:SS.xx] and [MM:SS.xxx] format.
Skips metadata tags: [ar:], [ti:], [al:], [by:], [offset:].
"""
from __future__ import annotations

import re
from pathlib import Path

from webtoon_capcut.domain.enums import CueType, SubtitleFormat
from webtoon_capcut.domain.models import SubtitleCue

# [MM:SS.xx] or [MM:SS.xxx]
_TIMESTAMP_RE = re.compile(r"^\[(\d{1,2}):(\d{2})\.(\d{2,3})\](.*)$")

# Metadata tags to skip (key-value form inside brackets)
_METADATA_TAG_RE = re.compile(
    r"^\[(ar|ti|al|by|offset|length|re|ve):", re.IGNORECASE
)

# Lines that contain ONLY a bracket expression with no plain text after
_BRACKET_ONLY_RE = re.compile(r"^\[.*\]\s*$")


def _parse_lrc_time(s: str) -> int:
    """Parse [MM:SS.xx] or [MM:SS.xxx] bracket string (without outer brackets)
    and return milliseconds.

    Args:
        s: String in the form ``MM:SS.xx`` or ``MM:SS.xxx``.

    Returns:
        Time in milliseconds as an integer.
    """
    m = re.match(r"^(\d{1,2}):(\d{2})\.(\d{2,3})$", s.strip())
    if not m:
        raise ValueError(f"Cannot parse LRC timestamp: {s!r}")
    minutes = int(m.group(1))
    seconds = int(m.group(2))
    frac = m.group(3)
    # Normalise to ms: 2 digits = centiseconds, 3 digits = milliseconds
    if len(frac) == 2:
        ms = int(frac) * 10
    else:
        ms = int(frac)
    return (minutes * 60 + seconds) * 1000 + ms


def parse_lrc(path: str | Path) -> list[SubtitleCue]:
    """Parse an LRC file and return a list of SubtitleCue objects.

    Rules applied:
    - Blank lines are skipped.
    - Lines matching known metadata tags ([ar:], [ti:], [al:], [by:],
      [offset:]) are skipped.
    - Each valid lyric line produces one SubtitleCue.
    - end_ms of cue N = start_ms of cue N+1; last cue gets +5000 ms.
    - A line whose text portion is empty or only spaces after the timestamp
      bracket is typed CueType.metadata; otherwise CueType.lyric.

    Args:
        path: Filesystem path to the ``.lrc`` file.

    Returns:
        Ordered list of SubtitleCue objects.
    """
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    raw_entries: list[tuple[int, str]] = []  # (start_ms, raw_text)

    for line in lines:
        line_stripped = line.strip()

        # Skip blank lines
        if not line_stripped:
            continue

        # Skip metadata tags
        if _METADATA_TAG_RE.match(line_stripped):
            continue

        # Match timestamp line
        m = _TIMESTAMP_RE.match(line_stripped)
        if not m:
            # No recognisable timestamp — skip (could be extended meta)
            continue

        minutes = int(m.group(1))
        seconds = int(m.group(2))
        frac = m.group(3)
        if len(frac) == 2:
            frac_ms = int(frac) * 10
        else:
            frac_ms = int(frac)
        start_ms = (minutes * 60 + seconds) * 1000 + frac_ms

        lyric_text = m.group(4)  # everything after the first timestamp bracket
        raw_entries.append((start_ms, lyric_text))

    # Sort by start time so overlapping/repeated timestamps are in order
    raw_entries.sort(key=lambda x: x[0])

    cues: list[SubtitleCue] = []
    for i, (start_ms, raw_text) in enumerate(raw_entries):
        stripped = raw_text.strip()

        # Determine end_ms
        if i + 1 < len(raw_entries):
            end_ms = raw_entries[i + 1][0]
        else:
            end_ms = start_ms + 5000

        # Clamp: end_ms must be > start_ms
        if end_ms <= start_ms:
            end_ms = start_ms + 5000

        # Determine cue type
        # If the remaining text (after timestamp) is empty or bracket-only, treat as metadata
        if not stripped or _BRACKET_ONLY_RE.match(raw_text.strip()):
            cue_type = CueType.metadata
        else:
            cue_type = CueType.lyric

        cue = SubtitleCue(
            cue_id=f"lrc_{i:04d}",
            start_ms=start_ms,
            end_ms=end_ms,
            raw_text=raw_text,
            text=stripped,
            cue_type=cue_type,
            source_format=SubtitleFormat.lrc,
            confidence=0.85,
            review_required=False,
        )
        cues.append(cue)

    return cues


def lrc_quality_score(cues: list[SubtitleCue]) -> float:
    """Compute a quality score in the range [0.0, 1.0] for a parsed LRC document.

    Scoring components (equal weight):
    1. Cue count: 0.0 for 0 cues, 1.0 for >=10 cues (linear).
    2. No timing inversions or duplicates: 1.0 if clean, penalised otherwise.
    3. Non-empty text ratio: fraction of cues with non-blank text.

    Args:
        cues: List of SubtitleCue objects from ``parse_lrc``.

    Returns:
        Float in [0.0, 1.0].
    """
    if not cues:
        return 0.0

    # Component 1: cue count score (saturates at 10)
    count_score = min(len(cues) / 10.0, 1.0)

    # Component 2: timing integrity (inversions / duplicates)
    inversion_count = 0
    seen_starts: set[int] = set()
    duplicate_count = 0
    for cue in cues:
        if cue.start_ms in seen_starts:
            duplicate_count += 1
        seen_starts.add(cue.start_ms)
        if cue.end_ms <= cue.start_ms:
            inversion_count += 1

    total_issues = inversion_count + duplicate_count
    timing_score = max(0.0, 1.0 - total_issues / len(cues))

    # Component 3: non-empty text ratio
    non_empty = sum(1 for c in cues if c.text)
    text_score = non_empty / len(cues)

    return (count_score + timing_score + text_score) / 3.0
