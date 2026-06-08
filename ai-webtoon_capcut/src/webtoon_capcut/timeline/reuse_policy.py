"""
Reuse policy: image repetition calculations for under-stocked sections.
"""

import math


def calc_reuse_count(
    needed_clips: int,
    available_images: int,
    max_reuse: int,
) -> int:
    """Return the repetition count required to fill needed_clips.

    ``repetition count`` is the number of full cycles through the
    image list, equivalent to ceil(needed_clips / available_images).
    If the calculated value exceeds max_reuse, max_reuse is returned.
    Callers that care about the shortfall should check whether the
    returned value equals max_reuse.

    Parameters
    ----------
    needed_clips:
        Total clip slots that must be filled.
    available_images:
        Number of distinct images in the section.
    max_reuse:
        Maximum allowed repetitions per image (from ClipPolicy).
    """
    if available_images <= 0:
        raise ValueError("available_images must be >= 1")
    if needed_clips <= 0:
        raise ValueError("needed_clips must be >= 1")

    reuse = math.ceil(needed_clips / available_images)
    return min(reuse, max_reuse)


def expand_images(
    panel_ids: list[str],
    needed_count: int,
    max_reuse: int,
) -> list[str]:
    """Cycle through panel_ids until needed_count entries are produced.

    If cycling panel_ids to the max_reuse limit cannot reach
    needed_count, the result is truncated to max_reuse * len(panel_ids)
    and the caller is responsible for raising any shortage warning.

    Parameters
    ----------
    panel_ids:
        Ordered list of panel ids for one section.
    needed_count:
        Target number of clip slots to fill.
    max_reuse:
        Maximum times each panel id may appear in the result.
    """
    if not panel_ids:
        return []

    max_producible = len(panel_ids) * max_reuse
    effective_count = min(needed_count, max_producible)

    result: list[str] = []
    idx = 0
    while len(result) < effective_count:
        result.append(panel_ids[idx % len(panel_ids)])
        idx += 1

    return result
