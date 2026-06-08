"""Section boundary resolver.

Attempts to assign time boundaries to storyboard sections in priority order:

  Level 1 – explicit_sidecar      (not yet implemented, skipped)
  Level 2 – trusted_section_cue   (timed metadata cues from subtitle document)
  Level 3 – storyboard_weight     (recommended_duration_ms proportional split)
  Level 4 – uniform_fallback      (equal split by panel count)

Each produced SectionEntry records the BoundarySource and confidence so that
downstream stages and human reviewers can assess reliability.
"""
from __future__ import annotations

import re
from collections import defaultdict

from webtoon_capcut.domain.enums import BoundarySource, CanonicalType, CueType
from webtoon_capcut.domain.models import (
    Config,
    SectionEntry,
    SectionTimeline,
    Storyboard,
    SubtitleDocument,
)
from webtoon_capcut.sections.canonicalizer import canonicalize_label, assign_occurrences
from webtoon_capcut.sections.confidence import calc_alignment_confidence, needs_review

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _group_panels_by_section(
    storyboard: Storyboard,
) -> list[tuple[str, CanonicalType, int, list[str], int]]:
    """Return an ordered list of ``(label, canonical_type, occurrence, panel_ids, total_ms)``
    for each distinct section run in the storyboard.

    Panels that share consecutive (label, canonical_type, occurrence) values are
    merged into a single logical section group.
    """
    if not storyboard.panels:
        return []

    groups: list[tuple[str, CanonicalType, int, list[str], int]] = []
    current_label = storyboard.panels[0].section_label
    current_type = storyboard.panels[0].section_type
    current_occ = storyboard.panels[0].section_occurrence
    current_panel_ids: list[str] = []
    current_ms = 0

    for panel in storyboard.panels:
        same_section = (
            panel.section_label == current_label
            and panel.section_type == current_type
            and panel.section_occurrence == current_occ
        )
        if same_section:
            current_panel_ids.append(panel.panel_id)
            current_ms += panel.recommended_duration_ms or 0
        else:
            groups.append((current_label, current_type, current_occ, current_panel_ids, current_ms))
            current_label = panel.section_label
            current_type = panel.section_type
            current_occ = panel.section_occurrence
            current_panel_ids = [panel.panel_id]
            current_ms = panel.recommended_duration_ms or 0

    groups.append((current_label, current_type, current_occ, current_panel_ids, current_ms))
    return groups


def _section_id(canonical_type: CanonicalType, occurrence: int) -> str:
    return f"{canonical_type.value}-{occurrence}"


# ---------------------------------------------------------------------------
# Level 2 – trusted_section_cue
# ---------------------------------------------------------------------------

# Matches bracket-enclosed section labels such as [Chorus], [Verse 2], [Bridge]
_SECTION_CUE_RE = re.compile(r"^\[([^\[\]]+)\]$")


def _try_trusted_section_cue(
    storyboard: Storyboard,
    subtitle_doc: SubtitleDocument,
    audio_duration_ms: int,
) -> SectionTimeline | None:
    """Build a SectionTimeline from timed metadata cues in the subtitle document.

    Only ``CueType.metadata`` cues whose raw_text matches a bracket-enclosed
    section label are used.  Returns ``None`` if fewer cues than storyboard
    sections are found (insufficient coverage).
    """
    # Collect timed section cues, sorted by start_ms.
    timed_cues: list[tuple[int, str, CanonicalType]] = []
    for cue in subtitle_doc.cues:
        if cue.cue_type != CueType.metadata:
            continue
        m = _SECTION_CUE_RE.match(cue.raw_text.strip())
        if not m:
            continue
        label = m.group(1)
        canonical = canonicalize_label(label)
        timed_cues.append((cue.start_ms, label, canonical))

    timed_cues.sort(key=lambda t: t[0])

    groups = _group_panels_by_section(storyboard)
    if not timed_cues or len(timed_cues) < len(groups):
        # Not enough cues to cover all sections — fall through.
        return None

    # Map each group to the closest cue by canonical type / occurrence alignment.
    # Simple strategy: iterate cues in order and match to groups by position.
    # Assign occurrences to the cue sequence independently.
    cue_pairs = [(label, ct) for _, label, ct in timed_cues]
    cue_triples = assign_occurrences(cue_pairs)

    # Build a lookup: (canonical_type, occurrence) -> start_ms from cues.
    cue_timing: dict[tuple[CanonicalType, int], int] = {}
    for idx, (start_ms, _label, _ct) in enumerate(timed_cues):
        _, _, occ = cue_triples[idx]
        ct = _ct
        cue_timing[(ct, occ)] = start_ms

    # Build section entries using cue boundaries.
    entries: list[SectionEntry] = []
    for i, (label, ct, occ, panel_ids, _ms) in enumerate(groups):
        start_ms = cue_timing.get((ct, occ))
        if start_ms is None:
            # Can't resolve this section — fall through to next level.
            return None
        # End boundary: next section's start or audio end.
        end_ms = audio_duration_ms
        if i + 1 < len(groups):
            next_label, next_ct, next_occ, *_ = groups[i + 1]
            candidate = cue_timing.get((next_ct, next_occ))
            if candidate is not None:
                end_ms = candidate

        confidence = 0.90
        entries.append(
            SectionEntry(
                section_id=_section_id(ct, occ),
                label=label,
                canonical_type=ct,
                occurrence=occ,
                start_ms=start_ms,
                end_ms=end_ms,
                boundary_source=BoundarySource.trusted_section_cue,
                confidence=confidence,
                panel_ids=panel_ids,
                review_required=needs_review(confidence),
            )
        )

    return SectionTimeline(sections=entries)


# ---------------------------------------------------------------------------
# Level 3 – storyboard_weight
# ---------------------------------------------------------------------------

def _try_storyboard_weight(
    storyboard: Storyboard,
    audio_duration_ms: int,
) -> SectionTimeline | None:
    """Distribute audio_duration_ms proportionally by recommended_duration_ms weights.

    Returns ``None`` when the storyboard has no panels or all
    recommended_duration_ms values are zero/None (no weights to work with).
    """
    groups = _group_panels_by_section(storyboard)
    if not groups:
        return None

    total_weight = sum(ms for *_, ms in groups)
    if total_weight == 0:
        return None

    entries: list[SectionEntry] = []
    cursor_ms = 0
    confidence = 0.70

    for i, (label, ct, occ, panel_ids, weight_ms) in enumerate(groups):
        start_ms = cursor_ms
        if i == len(groups) - 1:
            # Last section always ends exactly at audio end to avoid rounding drift.
            end_ms = audio_duration_ms
        else:
            end_ms = round(audio_duration_ms * weight_ms / total_weight) + cursor_ms
            # Accumulate proportional share from the start to avoid drift.
            accumulated = sum(ms for *_, ms in groups[: i + 1])
            end_ms = round(audio_duration_ms * accumulated / total_weight)

        cursor_ms = end_ms

        entries.append(
            SectionEntry(
                section_id=_section_id(ct, occ),
                label=label,
                canonical_type=ct,
                occurrence=occ,
                start_ms=start_ms,
                end_ms=end_ms,
                boundary_source=BoundarySource.storyboard_weight,
                confidence=confidence,
                panel_ids=panel_ids,
                review_required=needs_review(confidence),
            )
        )

    return SectionTimeline(sections=entries)


# ---------------------------------------------------------------------------
# Level 4 – uniform_fallback
# ---------------------------------------------------------------------------

def _uniform_fallback(
    storyboard: Storyboard,
    audio_duration_ms: int,
) -> SectionTimeline:
    """Distribute audio_duration_ms equally across all panels regardless of section.

    Each panel becomes its own unit; the total panel count drives the equal split.
    If the storyboard has no panels at all, a single section spanning the full
    audio is produced.
    """
    panels = storyboard.panels
    confidence = 0.40

    if not panels:
        # Edge case: no storyboard data at all.
        return SectionTimeline(
            sections=[
                SectionEntry(
                    section_id=_section_id(CanonicalType.other, 1),
                    label="unknown",
                    canonical_type=CanonicalType.other,
                    occurrence=1,
                    start_ms=0,
                    end_ms=audio_duration_ms,
                    boundary_source=BoundarySource.uniform_fallback,
                    confidence=confidence,
                    panel_ids=[],
                    review_required=True,
                )
            ]
        )

    groups = _group_panels_by_section(storyboard)
    total_panels = len(panels)
    entries: list[SectionEntry] = []
    panel_cursor = 0

    for i, (label, ct, occ, panel_ids, _ms) in enumerate(groups):
        start_ms = round(audio_duration_ms * panel_cursor / total_panels)
        panel_cursor += len(panel_ids)
        if i == len(groups) - 1:
            end_ms = audio_duration_ms
        else:
            end_ms = round(audio_duration_ms * panel_cursor / total_panels)

        entries.append(
            SectionEntry(
                section_id=_section_id(ct, occ),
                label=label,
                canonical_type=ct,
                occurrence=occ,
                start_ms=start_ms,
                end_ms=end_ms,
                boundary_source=BoundarySource.uniform_fallback,
                confidence=confidence,
                panel_ids=panel_ids,
                review_required=True,
            )
        )

    return SectionTimeline(sections=entries)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def resolve_sections(
    storyboard: Storyboard,
    subtitle_doc: SubtitleDocument | None,
    audio_duration_ms: int,
    config: Config,
) -> SectionTimeline:
    """Resolve section time boundaries using the best available strategy.

    Tries each level in priority order and returns the first successful result.

    Parameters
    ----------
    storyboard:
        Parsed storyboard with ordered panels and section metadata.
    subtitle_doc:
        Parsed and normalised subtitle document, or ``None`` when unavailable.
    audio_duration_ms:
        Total audio duration in milliseconds.
    config:
        Run-time configuration (reserved for future policy injection).

    Returns
    -------
    SectionTimeline
        Ordered list of SectionEntry objects covering [0, audio_duration_ms].
    """
    # Level 1 – explicit_sidecar: not yet implemented.

    # Level 2 – trusted_section_cue
    if subtitle_doc is not None:
        result = _try_trusted_section_cue(storyboard, subtitle_doc, audio_duration_ms)
        if result is not None:
            return result

    # Level 3 – storyboard_weight
    result = _try_storyboard_weight(storyboard, audio_duration_ms)
    if result is not None:
        return result

    # Level 4 – uniform_fallback (always succeeds)
    return _uniform_fallback(storyboard, audio_duration_ms)
