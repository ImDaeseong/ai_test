"""SRT subtitle parser.

Parses SubRip (.srt) files with standard block format:
    <index>
    HH:MM:SS,mmm --> HH:MM:SS,mmm
    Text line(s)

    <next block>
"""
from __future__ import annotations

import re
from pathlib import Path

from webtoon_capcut.domain.enums import CueType, SubtitleFormat
from webtoon_capcut.domain.models import SubtitleCue

# SRT timecode: HH:MM:SS,mmm
_SRT_TIME_RE = re.compile(
    r"^(\d{1,2}):(\d{2}):(\d{2})[,\.](\d{3})$"
)

# SRT arrow line: HH:MM:SS,mmm --> HH:MM:SS,mmm (with optional leading whitespace)
_ARROW_RE = re.compile(
    r"^\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})"
)

# HTML tags to strip from text
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _parse_srt_time(s: str) -> int:
    """Parse an SRT timecode string and return milliseconds.

    Accepts both ``,`` and ``.`` as the millisecond separator.

    Args:
        s: Timecode string like ``01:23:45,678`` or ``01:23:45.678``.

    Returns:
        Time in milliseconds as an integer.

    Raises:
        ValueError: If the string does not match the expected format.
    """
    m = _SRT_TIME_RE.match(s.strip())
    if not m:
        raise ValueError(f"Cannot parse SRT timecode: {s!r}")
    hours = int(m.group(1))
    minutes = int(m.group(2))
    seconds = int(m.group(3))
    millis = int(m.group(4))
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def _strip_html(text: str) -> str:
    """Remove HTML tags (<b>, <i>, <u>, etc.) from *text*."""
    return _HTML_TAG_RE.sub("", text)


def parse_srt(path: str | Path) -> list[SubtitleCue]:
    """Parse an SRT file and return a list of SubtitleCue objects.

    Rules applied:
    - Blocks are separated by one or more blank lines.
    - Each block must contain a sequence number, a timecode arrow line,
      and at least one text line.
    - HTML tags are removed from the displayed text; raw_text retains them.
    - Cues with no visible text after stripping are typed CueType.metadata.

    Args:
        path: Filesystem path to the ``.srt`` file.

    Returns:
        Ordered list of SubtitleCue objects (sorted by start_ms).
    """
    raw = Path(path).read_text(encoding="utf-8-sig", errors="replace")

    # Normalise line endings and split into blocks on blank lines
    blocks = re.split(r"\r?\n\s*\r?\n", raw.strip())

    cues: list[SubtitleCue] = []
    cue_index = 0

    for block in blocks:
        lines = [ln.rstrip() for ln in block.strip().splitlines()]
        if not lines:
            continue

        # Find the timecode arrow line (may be line 0 or 1)
        arrow_line_idx: int | None = None
        for idx, ln in enumerate(lines):
            if _ARROW_RE.match(ln):
                arrow_line_idx = idx
                break

        if arrow_line_idx is None:
            # No timecode found in this block — skip
            continue

        arrow_m = _ARROW_RE.match(lines[arrow_line_idx])
        if not arrow_m:
            continue

        try:
            start_ms = _parse_srt_time(arrow_m.group(1))
            end_ms = _parse_srt_time(arrow_m.group(2))
        except ValueError:
            continue

        # Clamp: end must be after start
        if end_ms <= start_ms:
            end_ms = start_ms + 1

        # Text lines: everything after the arrow line
        text_lines = lines[arrow_line_idx + 1:]
        raw_text = "\n".join(text_lines)
        clean_text = _strip_html(raw_text).strip()

        cue_type = CueType.lyric if clean_text else CueType.metadata

        cue = SubtitleCue(
            cue_id=f"srt_{cue_index:04d}",
            start_ms=start_ms,
            end_ms=end_ms,
            raw_text=raw_text,
            text=clean_text,
            cue_type=cue_type,
            source_format=SubtitleFormat.srt,
            confidence=0.90,
            review_required=False,
        )
        cues.append(cue)
        cue_index += 1

    # Sort by start time (SRT files should already be ordered, but be safe)
    cues.sort(key=lambda c: c.start_ms)

    # Re-assign sequential cue_ids after sorting
    for i, cue in enumerate(cues):
        cue.cue_id = f"srt_{i:04d}"

    return cues


def srt_quality_score(cues: list[SubtitleCue]) -> float:
    """Compute a quality score in the range [0.0, 1.0] for a parsed SRT document.

    Scoring components (equal weight):
    1. Cue count: 0.0 for 0 cues, 1.0 for >=10 cues (linear).
    2. Timing integrity: penalises inversions (end <= start) and overlaps
       between consecutive cues.
    3. Non-empty text ratio: fraction of cues with non-blank text.

    Args:
        cues: List of SubtitleCue objects from ``parse_srt``.

    Returns:
        Float in [0.0, 1.0].
    """
    if not cues:
        return 0.0

    # Component 1: cue count score (saturates at 10)
    count_score = min(len(cues) / 10.0, 1.0)

    # Component 2: timing integrity
    bad_timing = 0
    overlap_count = 0
    for i, cue in enumerate(cues):
        if cue.end_ms <= cue.start_ms:
            bad_timing += 1
        if i > 0 and cues[i].start_ms < cues[i - 1].end_ms:
            overlap_count += 1

    total_issues = bad_timing + overlap_count
    timing_score = max(0.0, 1.0 - total_issues / len(cues))

    # Component 3: non-empty text ratio
    non_empty = sum(1 for c in cues if c.text)
    text_score = non_empty / len(cues)

    return (count_score + timing_score + text_score) / 3.0
