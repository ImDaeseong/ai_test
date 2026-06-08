from __future__ import annotations


def calc_alignment_confidence(
    matched_ratio: float,
    timing_consistency: float,
) -> float:
    """Compute a composite confidence score in the range [0.0, 1.0].

    Parameters
    ----------
    matched_ratio:
        Fraction of items successfully matched (0.0–1.0).  Weighted at 60 %.
    timing_consistency:
        Measure of how consistent timing estimates are across the section
        (0.0–1.0).  Weighted at 40 %.

    Returns
    -------
    float
        Clamped composite score: ``matched_ratio * 0.6 + timing_consistency * 0.4``.
    """
    score = matched_ratio * 0.6 + timing_consistency * 0.4
    # Defensive clamp in case callers pass values slightly outside [0, 1].
    return max(0.0, min(1.0, score))


def needs_review(confidence: float, threshold: float = 0.7) -> bool:
    """Return ``True`` when *confidence* falls below *threshold*.

    Parameters
    ----------
    confidence:
        Score returned by :func:`calc_alignment_confidence` or set directly
        by a boundary resolver level.
    threshold:
        Minimum acceptable confidence.  Defaults to 0.7.
    """
    return confidence < threshold
