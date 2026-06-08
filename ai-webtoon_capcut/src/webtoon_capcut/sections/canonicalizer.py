from __future__ import annotations

from webtoon_capcut.domain.enums import CanonicalType
from webtoon_capcut.domain.policies import SECTION_ALIASES

# Lowercase-keyed lookup built once at import time for O(1) case-insensitive access.
_ALIASES_LOWER: dict[str, CanonicalType] = {
    k.lower(): v for k, v in SECTION_ALIASES.items()
}


def canonicalize_label(label: str) -> CanonicalType:
    """Return the CanonicalType for *label*, ignoring case.

    Falls back to ``CanonicalType.other`` when the label is not listed in
    ``SECTION_ALIASES``.
    """
    return _ALIASES_LOWER.get(label.strip().lower(), CanonicalType.other)


def assign_occurrences(
    sections: list[tuple[str, CanonicalType]],
) -> list[tuple[str, CanonicalType, int]]:
    """Attach a per-type occurrence counter (1-based) to each section entry.

    Parameters
    ----------
    sections:
        Ordered list of ``(label, canonical_type)`` pairs as they appear in
        the storyboard from top to bottom.

    Returns
    -------
    list of ``(label, canonical_type, occurrence)`` triples where
    ``occurrence`` is the 1-based count of how many times this
    ``CanonicalType`` has appeared up to and including the current entry.
    """
    counters: dict[CanonicalType, int] = {}
    result: list[tuple[str, CanonicalType, int]] = []
    for label, canonical_type in sections:
        counters[canonical_type] = counters.get(canonical_type, 0) + 1
        result.append((label, canonical_type, counters[canonical_type]))
    return result
