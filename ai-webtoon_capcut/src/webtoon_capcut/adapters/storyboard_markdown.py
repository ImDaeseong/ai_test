"""
Storyboard Markdown adapter.

Parses the 01_storyboard.md files produced by the ai-webtoon project.

Expected table format (Korean headers are also accepted):
| 패널 번호 | 섹션 | 타입 | 지속 시간 | 가사 미리보기 |
|-----------|------|------|-----------|--------------|
| panel_001 | Intro | wide | 5초 | Instrumental |
...

The parser is intentionally robust:
- Accepts any column order as long as each cell can be identified.
- Works even when the table is absent (returns empty Storyboard).
- Works when panel IDs are missing (derives them from row order).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from webtoon_capcut.domain.enums import CanonicalType, PanelType
from webtoon_capcut.domain.models import PanelEntry, Storyboard
from webtoon_capcut.domain.policies import SECTION_ALIASES

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_RE_PANEL_ID = re.compile(r"panel[_\-]?(\d{3,})", re.IGNORECASE)
_RE_DURATION_S = re.compile(r"(\d+(?:\.\d+)?)\s*초", re.IGNORECASE)
_RE_DURATION_SEC = re.compile(r"(\d+(?:\.\d+)?)\s*s(?:ec(?:onds?)?)?\b", re.IGNORECASE)
_RE_DURATION_MS = re.compile(r"(\d+(?:\.\d+)?)\s*ms\b", re.IGNORECASE)

# Supported panel types (lower-cased for matching)
_PANEL_TYPE_KEYWORDS: dict[str, PanelType] = {
    pt.value: pt for pt in PanelType if pt != PanelType.unknown
}


def _resolve_panel_type(text: str) -> PanelType:
    """Return the first PanelType keyword found in *text*, or PanelType.unknown."""
    lower = text.lower()
    for keyword, ptype in _PANEL_TYPE_KEYWORDS.items():
        if keyword in lower:
            return ptype
    return PanelType.unknown


def _resolve_canonical(label: str) -> CanonicalType:
    """Map a raw section label to CanonicalType via SECTION_ALIASES.

    Falls back to CanonicalType.other for unknown labels.
    """
    stripped = label.strip()
    # Direct lookup first
    if stripped in SECTION_ALIASES:
        return SECTION_ALIASES[stripped]
    # Case-insensitive lookup
    lower = stripped.lower()
    for alias_key, ctype in SECTION_ALIASES.items():
        if alias_key.lower() == lower:
            return ctype
    return CanonicalType.other


def _parse_duration_ms(text: str) -> int | None:
    """Parse duration strings like '5초', '5s', '5000ms'.

    Returns duration in milliseconds, or None when unrecognised.
    """
    # Korean seconds: 5초
    m = _RE_DURATION_S.search(text)
    if m:
        return int(float(m.group(1)) * 1000)
    # English seconds: 5s / 5sec
    m = _RE_DURATION_SEC.search(text)
    if m:
        return int(float(m.group(1)) * 1000)
    # Milliseconds: 5000ms
    m = _RE_DURATION_MS.search(text)
    if m:
        return int(float(m.group(1)))
    return None


def _split_table_row(line: str) -> list[str]:
    """Split a markdown table row by pipe characters.

    Strips leading/trailing pipes and whitespace from each cell.
    Returns an empty list if the line is a separator row (e.g. |---|---|).
    """
    stripped = line.strip().strip("|")
    cells = [c.strip() for c in stripped.split("|")]
    # Separator rows contain only dashes/colons
    if all(re.fullmatch(r"[-:]+", c) for c in cells if c):
        return []
    return cells


# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------

# Keywords that identify each logical column (lower-cased)
_COL_PANEL = {"패널", "panel", "패널 번호", "번호"}
_COL_SECTION = {"섹션", "section", "섹션명"}
_COL_TYPE = {"타입", "type", "패널타입"}
_COL_DURATION = {"지속 시간", "지속시간", "duration", "권장시간", "권장 시간", "시간"}
_COL_LYRIC = {"가사", "lyric", "가사 미리보기", "가사미리보기", "미리보기", "preview"}


@dataclass
class _ColMap:
    panel: int = -1
    section: int = -1
    ptype: int = -1
    duration: int = -1
    lyric: int = -1


def _detect_columns(headers: list[str]) -> _ColMap:
    """Match header cells to logical columns by keyword lookup."""
    cmap = _ColMap()
    for idx, h in enumerate(headers):
        lower = h.lower().strip()
        if cmap.panel == -1 and any(k in lower for k in _COL_PANEL):
            cmap.panel = idx
        elif cmap.section == -1 and any(k in lower for k in _COL_SECTION):
            cmap.section = idx
        elif cmap.ptype == -1 and any(k in lower for k in _COL_TYPE):
            cmap.ptype = idx
        elif cmap.duration == -1 and any(k in lower for k in _COL_DURATION):
            cmap.duration = idx
        elif cmap.lyric == -1 and any(k in lower for k in _COL_LYRIC):
            cmap.lyric = idx
    return cmap


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_storyboard(path: str | Path) -> Storyboard:
    """Parse an ai-webtoon 01_storyboard.md file and return a Storyboard.

    The parser never raises on malformed input — it returns whatever it
    could extract.  If no panels are found, an empty Storyboard is returned.
    """
    path = Path(path)
    if not path.exists():
        return Storyboard()

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return Storyboard()

    lines = text.splitlines()
    panels: list[PanelEntry] = []

    # Track section-group occurrence counters.
    # A new occurrence is counted when the canonical_type (or the raw section
    # label) changes compared to the immediately preceding panel row.  All
    # panels that belong to the same contiguous section block share the same
    # occurrence number, e.g.:
    #
    #   Intro  occ=1, Intro  occ=1, Verse 1 occ=1, Chorus occ=1,
    #   Verse 2 occ=2, Chorus occ=2
    occurrence_counter: dict[CanonicalType, int] = {}
    prev_section_label: str | None = None

    cmap = _ColMap()
    in_table = False
    header_found = False
    order = 0

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            header_found = False
            continue

        cells = _split_table_row(stripped)
        if not cells:
            # Separator row — marks end of header, start of data rows
            if not header_found:
                in_table = False
            continue

        if not header_found:
            # Treat this pipe row as a header candidate
            cmap = _detect_columns(cells)
            header_found = True
            in_table = True
            continue

        if not in_table:
            continue

        # Data row
        def _cell(idx: int) -> str:
            if idx < 0 or idx >= len(cells):
                return ""
            return cells[idx]

        # --- Panel ID ---
        panel_cell = _cell(cmap.panel)
        m = _RE_PANEL_ID.search(panel_cell)
        if m:
            panel_id = f"panel_{int(m.group(1)):03d}"
        else:
            # Try the whole row for a panel_NNN pattern (may be in filename context)
            m_row = _RE_PANEL_ID.search(stripped)
            if m_row:
                panel_id = f"panel_{int(m_row.group(1)):03d}"
            else:
                panel_id = f"panel_{order + 1:03d}"

        # --- Section label ---
        section_label = _cell(cmap.section)
        if not section_label and cmap.section < 0:
            # No section column detected; try second column heuristically
            section_label = _cell(1) if len(cells) > 1 else ""

        canonical_type = _resolve_canonical(section_label)

        # Increment occurrence counter only when the section label changes,
        # i.e. when a new section block begins.
        if section_label != prev_section_label:
            occurrence_counter[canonical_type] = (
                occurrence_counter.get(canonical_type, 0) + 1
            )
            prev_section_label = section_label

        section_occurrence = occurrence_counter.get(canonical_type, 1)

        # --- Panel type ---
        type_cell = _cell(cmap.ptype)
        if not type_cell and cmap.ptype < 0:
            type_cell = _cell(2) if len(cells) > 2 else ""
        # Also scan panel_id and the filename for panel type hints
        panel_type = _resolve_panel_type(type_cell)
        if panel_type == PanelType.unknown:
            panel_type = _resolve_panel_type(panel_id)

        # --- Duration ---
        duration_cell = _cell(cmap.duration)
        recommended_duration_ms = _parse_duration_ms(duration_cell)

        # --- Lyric preview ---
        lyric_cell = _cell(cmap.lyric) or None
        if lyric_cell == "":
            lyric_cell = None

        panels.append(
            PanelEntry(
                panel_id=panel_id,
                order=order,
                section_label=section_label,
                section_type=canonical_type,
                section_occurrence=section_occurrence,
                panel_type=panel_type,
                recommended_duration_ms=recommended_duration_ms,
                lyric_preview=lyric_cell,
            )
        )
        order += 1

    return Storyboard(panels=panels)
