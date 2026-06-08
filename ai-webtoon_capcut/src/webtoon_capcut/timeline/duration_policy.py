"""
Duration policy: clip length and frame alignment calculations.

All time values are in milliseconds (int).
"""

import math

from webtoon_capcut.domain.models import ClipPolicy


def calc_clip_duration(
    section_duration_ms: int,
    image_count: int,
    policy: ClipPolicy,
) -> int:
    """Return per-clip duration (ms) clamped to policy bounds.

    Divides section_duration_ms evenly among image_count clips, then
    clamps the result to [min_seconds, hard_max_seconds].  The
    preferred_min/preferred_max range is used as the target window but
    is not enforced as a hard clamp — the hard limits always win.
    """
    if image_count <= 0:
        raise ValueError("image_count must be >= 1")
    if section_duration_ms <= 0:
        raise ValueError("section_duration_ms must be > 0")

    per_clip_ms = section_duration_ms // image_count

    min_ms = int(policy.min_seconds * 1000)
    hard_max_ms = int(policy.hard_max_seconds * 1000)

    # Clamp to absolute limits.
    clamped = max(min_ms, min(per_clip_ms, hard_max_ms))
    return clamped


def calc_needed_clips(section_duration_ms: int, policy: ClipPolicy) -> int:
    """Return the minimum number of clips needed to cover section_duration_ms.

    Uses preferred_max_seconds as the target clip length so that no
    individual clip exceeds that preferred ceiling.
    """
    if section_duration_ms <= 0:
        raise ValueError("section_duration_ms must be > 0")

    preferred_max_ms = policy.preferred_max_seconds * 1000
    return math.ceil(section_duration_ms / preferred_max_ms)


def frame_align_ms(ms: int, fps: int) -> int:
    """Round ms to the nearest frame boundary for the given fps.

    One frame = 1000 / fps milliseconds.  The result is rounded to the
    nearest whole frame (standard rounding — .5 rounds up).
    """
    if fps <= 0:
        raise ValueError("fps must be > 0")

    frame_ms = 1000 / fps
    frames = ms / frame_ms
    rounded_frames = math.floor(frames + 0.5)  # round half-up
    return int(rounded_frames * frame_ms)
