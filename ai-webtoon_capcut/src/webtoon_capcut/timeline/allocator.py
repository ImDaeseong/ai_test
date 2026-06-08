"""
Timeline allocator: convert Storyboard + SectionTimeline into EditTimeline.

Design rules (from 09_REUSABLE_PROGRAM_ARCHITECTURE.md):
- No song-name or panel-count hard-coding.
- Clip duration policy comes entirely from ClipPolicy.
- Images are reused up to ClipPolicy.max_reuse_per_image times.
- The last clip always ends exactly at audio_duration_ms.
- Frame rounding: all ms values are rounded to the nearest frame boundary
  at config.canvas.fps.
- Motion presets are derived from PanelType and reuse_index, never from
  song name or panel number.

Only stdlib is used (math, logging).
"""
from __future__ import annotations

import logging

from webtoon_capcut.domain.models import (
    AssetInventory,
    Clip,
    Config,
    EditTimeline,
    SectionTimeline,
    Storyboard,
    TimelineValidation,
    TransitionOut,
)
from webtoon_capcut.domain.enums import PanelType
from webtoon_capcut.timeline.duration_policy import (
    calc_clip_duration,
    calc_needed_clips,
    frame_align_ms,
)
from webtoon_capcut.timeline.reuse_policy import expand_images
from webtoon_capcut.timeline.motion_policy import assign_motion
from webtoon_capcut.timeline.validator import validate_timeline, build_validation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _image_path_for_panel(panel_id: str, inventory: AssetInventory) -> str:
    """Return the media_path for panel_id from inventory.

    Returns the path of the first MATCHED ImageCandidate whose panel_id
    equals the requested id.  Falls back to any candidate with that
    panel_id regardless of status if no MATCHED entry is found.
    Returns an empty string if no candidate exists at all.
    """
    matched: str = ""
    fallback: str = ""
    for img in inventory.images:
        if img.panel_id == panel_id:
            if img.status == "MATCHED":
                matched = img.path
                break
            elif not fallback:
                fallback = img.path
    return matched or fallback


def _panel_type_for_panel(panel_id: str, storyboard: Storyboard) -> PanelType:
    """Return the PanelType for a panel_id from the storyboard."""
    for panel in storyboard.panels:
        if panel.panel_id == panel_id:
            return panel.panel_type
    return PanelType.unknown


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def plan_timeline(
    storyboard: Storyboard,
    inventory: AssetInventory,
    sections: SectionTimeline,
    audio_duration_ms: int,
    config: Config,
) -> EditTimeline:
    """Build an EditTimeline from storyboard, inventory, and section timing.

    Algorithm
    ---------
    For each SectionEntry in sections.sections:
      1. Collect the section's panel_ids.
      2. Look up each panel's image path from inventory.
      3. Compute section duration = section.end_ms - section.start_ms.
      4. Determine needed_clips via calc_needed_clips().
      5. Expand panel list to needed_clips via expand_images(), honouring
         max_reuse_per_image.  Log a warning if the expanded list is
         shorter than needed_clips (INSUFFICIENT_IMAGES).
      6. For each expanded panel slot, compute frame-aligned start/end
         times relative to the section start.
      7. Assign a motion preset via assign_motion() based on panel_type
         and reuse_index.
      8. Append a Clip object (clip_id = "clip_{i:04d}" globally).

    After all sections are processed:
      - Snap the last clip's end_ms to audio_duration_ms and update
        duration_ms accordingly.
      - Run validate_timeline() and log any errors as warnings.
      - Build TimelineValidation via build_validation().
      - Return the completed EditTimeline.

    Transitions
    -----------
    Every clip except the last gets a TransitionOut(type="crossfade",
    duration_ms=config.canvas.transition_ms).  The last clip has
    transition_out=None.

    clip_id
    -------
    Global sequential index across all sections: "clip_0000",
    "clip_0001", ...

    media_path
    ----------
    The path stored in AssetInventory (inventory-relative or absolute,
    exactly as recorded).  Empty string if no image was found for the
    panel.
    """
    policy = config.clips
    fps = config.canvas.fps if config.canvas.fps > 0 else 30
    fit = config.canvas.fit
    transition_ms = config.canvas.transition_ms

    clips: list[Clip] = []
    global_clip_index = 0

    for section in sections.sections:
        panel_ids = section.panel_ids
        section_duration_ms = section.end_ms - section.start_ms

        if section_duration_ms <= 0:
            logger.warning(
                "section '%s' has non-positive duration %d ms -- skipping",
                section.section_id,
                section_duration_ms,
            )
            continue

        if not panel_ids:
            logger.warning(
                "section '%s' has no panel_ids -- skipping",
                section.section_id,
            )
            continue

        # How many clip slots do we need?
        needed_clips = calc_needed_clips(section_duration_ms, policy)

        # Expand the panel list, respecting the reuse cap.
        expanded = expand_images(panel_ids, needed_clips, policy.max_reuse_per_image)

        if len(expanded) < needed_clips:
            logger.warning(
                "INSUFFICIENT_IMAGES: section '%s' needs %d clips but only "
                "%d can be produced from %d images with max_reuse=%d. "
                "Consider generating additional images.",
                section.section_id,
                needed_clips,
                len(expanded),
                len(panel_ids),
                policy.max_reuse_per_image,
            )

        actual_clip_count = len(expanded)
        if actual_clip_count == 0:
            continue

        # Per-clip duration, frame-aligned.
        per_clip_ms = calc_clip_duration(section_duration_ms, actual_clip_count, policy)
        per_clip_ms = frame_align_ms(per_clip_ms, fps)

        # Track how many times each original panel_id has appeared so far
        # within this section for reuse_index bookkeeping.
        reuse_counters: dict[str, int] = {}

        for slot_index, pid in enumerate(expanded):
            reuse_index = reuse_counters.get(pid, 0)
            reuse_counters[pid] = reuse_index + 1

            # Compute start/end relative to section start.
            clip_start = section.start_ms + frame_align_ms(slot_index * per_clip_ms, fps)
            clip_end = section.start_ms + frame_align_ms((slot_index + 1) * per_clip_ms, fps)

            # Snap the last clip of this section to section.end_ms to avoid
            # rounding drift accumulating across clips.
            if slot_index == actual_clip_count - 1:
                clip_end = section.end_ms

            duration = clip_end - clip_start

            # Look up image path and panel type.
            media_path = _image_path_for_panel(pid, inventory)
            panel_type = _panel_type_for_panel(pid, storyboard)

            motion = assign_motion(panel_type, reuse_index)

            clip = Clip(
                clip_id=f"clip_{global_clip_index:04d}",
                panel_id=pid,
                section_id=section.section_id,
                media_path=media_path,
                start_ms=clip_start,
                end_ms=clip_end,
                duration_ms=duration,
                motion_preset=motion,
                reuse_index=reuse_index,
                fit=fit,
                transition_out=None,  # will be patched below
            )
            clips.append(clip)
            global_clip_index += 1

    if not clips:
        logger.warning("plan_timeline produced zero clips")
        empty_validation = TimelineValidation(
            first_start_ms=0,
            last_end_ms=0,
            gap_count=0,
            invalid_clip_count=0,
        )
        return EditTimeline(
            audio_duration_ms=audio_duration_ms,
            canvas=config.canvas,
            clips=[],
            validation=empty_validation,
        )

    # Snap last clip to audio_duration_ms.
    last = clips[-1]
    snapped_end = audio_duration_ms
    clips[-1] = Clip(
        clip_id=last.clip_id,
        panel_id=last.panel_id,
        section_id=last.section_id,
        media_path=last.media_path,
        start_ms=last.start_ms,
        end_ms=snapped_end,
        duration_ms=snapped_end - last.start_ms,
        motion_preset=last.motion_preset,
        reuse_index=last.reuse_index,
        fit=last.fit,
        transition_out=None,
    )

    # Assign transition_out to all clips except the last.
    for i in range(len(clips) - 1):
        c = clips[i]
        clips[i] = Clip(
            clip_id=c.clip_id,
            panel_id=c.panel_id,
            section_id=c.section_id,
            media_path=c.media_path,
            start_ms=c.start_ms,
            end_ms=c.end_ms,
            duration_ms=c.duration_ms,
            motion_preset=c.motion_preset,
            reuse_index=c.reuse_index,
            fit=c.fit,
            transition_out=TransitionOut(type="crossfade", duration_ms=transition_ms),
        )

    # Build the timeline object so we can validate it.
    timeline = EditTimeline(
        schema_version="2.0",
        audio_duration_ms=audio_duration_ms,
        canvas=config.canvas,
        clips=clips,
        validation=TimelineValidation(
            first_start_ms=0, last_end_ms=0, gap_count=0, invalid_clip_count=0
        ),
    )

    # Validate and attach the final validation record.
    errors = validate_timeline(timeline)
    for err in errors:
        logger.warning("timeline validation: %s", err)

    validation = build_validation(timeline)
    timeline.validation = validation

    return timeline
