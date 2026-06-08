"""
Song source TXT adapter.

Parses the ai-webtoon input/{song_name}.txt files.

File format example::

    Title: UPGRADE
    Genre: ...

    [Intro]
    [Loud high-gain tube-amp feedback]
    ...

    [Verse 1]
    어제의 껍질을 찢어 발겨
    차가운 핏줄에 다시 불을 질러

    [Chorus]
    업그레이드! 심장을 갈아 끼워!
    ...

Section headers are bracketed labels, e.g. ``[Verse 1]``, ``[Chorus]``.
Lines beneath each header (until the next header or EOF) are the section body.

If the file contains no section headers, the entire content is wrapped in a
single SongSection with canonical_type=CanonicalType.other.

If the file does not exist, SongStructure(title="", sections=[]) is returned.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from webtoon_capcut.domain.enums import CanonicalType
from webtoon_capcut.domain.policies import SECTION_ALIASES

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class SongSection:
    """One labelled section within a song source file."""
    label: str
    canonical_type: CanonicalType
    lines: list[str] = field(default_factory=list)
    occurrence: int = 1


@dataclass
class SongStructure:
    """Parsed representation of an ai-webtoon input TXT file."""
    title: str
    sections: list[SongSection] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_RE_SECTION_HEADER = re.compile(r"^\[([^\[\]]+)\]$")
_RE_TITLE = re.compile(r"^Title\s*:\s*(.+)$", re.IGNORECASE)


def _resolve_canonical(label: str) -> CanonicalType:
    """Map a raw section label to CanonicalType via SECTION_ALIASES.

    Falls back to CanonicalType.other for unknown labels.
    """
    stripped = label.strip()
    if stripped in SECTION_ALIASES:
        return SECTION_ALIASES[stripped]
    # Case-insensitive lookup
    lower = stripped.lower()
    for alias_key, ctype in SECTION_ALIASES.items():
        if alias_key.lower() == lower:
            return ctype
    return CanonicalType.other


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_song_source(path: str | Path) -> SongStructure:
    """Parse an ai-webtoon input TXT file and return a SongStructure.

    The parser never raises on malformed input — it returns whatever it
    could extract.  If the file does not exist, an empty SongStructure is
    returned.

    Args:
        path: Path to the song source .txt file.

    Returns:
        SongStructure with title and a list of SongSection objects.
    """
    path = Path(path)
    if not path.exists():
        return SongStructure(title="")

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return SongStructure(title="")

    lines = text.splitlines()

    title = ""
    sections: list[SongSection] = []

    # Occurrence counters per canonical type (for repeated sections like Chorus 1/2)
    occurrence_counter: dict[CanonicalType, int] = {}

    # Lines that don't belong to any section (preamble before first header)
    preamble_lines: list[str] = []

    current_section: SongSection | None = None

    for raw_line in lines:
        line = raw_line.rstrip()

        # Extract title from metadata lines (before any section header)
        if current_section is None:
            m_title = _RE_TITLE.match(line)
            if m_title:
                title = m_title.group(1).strip()
                continue

        # Detect section header: [Label]
        m_header = _RE_SECTION_HEADER.match(line.strip())
        if m_header:
            label = m_header.group(1).strip()
            canonical_type = _resolve_canonical(label)
            occurrence_counter[canonical_type] = (
                occurrence_counter.get(canonical_type, 0) + 1
            )
            current_section = SongSection(
                label=label,
                canonical_type=canonical_type,
                occurrence=occurrence_counter[canonical_type],
            )
            sections.append(current_section)
            continue

        # Body line
        if current_section is not None:
            # Skip blank lines at the very start of a section
            if line.strip() == "" and not current_section.lines:
                continue
            current_section.lines.append(line)
        else:
            # Preamble — not inside any section yet
            if line.strip() and not _RE_TITLE.match(line):
                preamble_lines.append(line)

    # Trim trailing blank lines from each section
    for sec in sections:
        while sec.lines and sec.lines[-1].strip() == "":
            sec.lines.pop()

    # If no section headers were found, treat the whole content as one unknown section
    if not sections:
        all_lines = [l for l in preamble_lines if l.strip()]
        if all_lines:
            sections.append(
                SongSection(
                    label="",
                    canonical_type=CanonicalType.other,
                    lines=all_lines,
                    occurrence=1,
                )
            )

    # Derive title from file stem if not found in metadata
    if not title:
        title = path.stem

    return SongStructure(title=title, sections=sections)
