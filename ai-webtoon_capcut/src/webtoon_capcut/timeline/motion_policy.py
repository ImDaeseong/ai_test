"""
Motion policy: deterministic motion preset assignment by panel type and reuse index.
"""

from webtoon_capcut.domain.enums import PanelType
from webtoon_capcut.domain.policies import MOTION_PRESETS


def assign_motion(panel_type: PanelType, reuse_index: int) -> str:
    """Return the motion preset for panel_type at position reuse_index.

    The preset list for panel_type is cycled using modulo so that any
    non-negative reuse_index is valid.

    Parameters
    ----------
    panel_type:
        The PanelType of the image being placed.
    reuse_index:
        Zero-based index of this clip within the repetition cycle.
        Wraps around the preset list automatically.
    """
    presets = MOTION_PRESETS.get(panel_type)
    if not presets:
        # Fallback: try unknown, then hard-coded safe default.
        presets = MOTION_PRESETS.get(PanelType.unknown, ["slow_zoom_in"])
    return presets[reuse_index % len(presets)]


def get_motion_preset(panel_type: PanelType, reuse_index: int = 0) -> str:
    """Alias for assign_motion with a default reuse_index of 0."""
    return assign_motion(panel_type, reuse_index)
