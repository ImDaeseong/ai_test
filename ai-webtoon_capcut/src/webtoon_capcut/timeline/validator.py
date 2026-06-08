"""
Timeline validator: structural integrity checks for EditTimeline.
"""

from webtoon_capcut.domain.models import EditTimeline, TimelineValidation


def validate_timeline(timeline: EditTimeline) -> list[str]:
    """Check structural integrity of an EditTimeline.

    Checks performed:
    - First clip start_ms == 0.
    - Last clip end_ms == audio_duration_ms (within one frame tolerance).
    - No gap between adjacent clips (transition overlap is allowed, but
      a positive gap is an error).
    - No time reversal: start_ms < end_ms for every clip.
    - duration_ms == end_ms - start_ms for every clip.

    Returns a list of error message strings.  An empty list means the
    timeline passed all checks.
    """
    errors: list[str] = []
    clips = timeline.clips

    if not clips:
        errors.append("timeline has no clips")
        return errors

    fps = timeline.canvas.fps if timeline.canvas.fps > 0 else 30
    frame_ms = 1000 / fps  # tolerance for floating-point edge cases

    # --- First clip starts at 0 ---
    if clips[0].start_ms != 0:
        errors.append(
            f"first clip '{clips[0].clip_id}' start_ms={clips[0].start_ms} must be 0"
        )

    # --- Last clip ends at audio_duration_ms (within one frame) ---
    last_end = clips[-1].end_ms
    audio_end = timeline.audio_duration_ms
    if abs(last_end - audio_end) > frame_ms:
        errors.append(
            f"last clip '{clips[-1].clip_id}' end_ms={last_end} "
            f"differs from audio_duration_ms={audio_end} "
            f"by more than one frame ({frame_ms:.2f} ms)"
        )

    for i, clip in enumerate(clips):
        # --- No time reversal ---
        if clip.start_ms >= clip.end_ms:
            errors.append(
                f"clip '{clip.clip_id}' has start_ms={clip.start_ms} "
                f">= end_ms={clip.end_ms} (time reversal or zero duration)"
            )

        # --- duration_ms == end_ms - start_ms ---
        expected_duration = clip.end_ms - clip.start_ms
        if clip.duration_ms != expected_duration:
            errors.append(
                f"clip '{clip.clip_id}' duration_ms={clip.duration_ms} "
                f"!= end_ms - start_ms={expected_duration}"
            )

        # --- No gap between adjacent clips ---
        if i > 0:
            prev = clips[i - 1]
            gap = clip.start_ms - prev.end_ms
            if gap > 0:
                errors.append(
                    f"gap of {gap} ms between clip '{prev.clip_id}' "
                    f"(end={prev.end_ms}) and clip '{clip.clip_id}' "
                    f"(start={clip.start_ms})"
                )

    return errors


def build_validation(timeline: EditTimeline) -> TimelineValidation:
    """Compute and return a TimelineValidation for the given timeline.

    Runs validate_timeline() and counts gaps and invalid clips from the
    error messages, then constructs the TimelineValidation dataclass.
    """
    clips = timeline.clips

    first_start_ms = clips[0].start_ms if clips else 0
    last_end_ms = clips[-1].end_ms if clips else 0

    errors = validate_timeline(timeline)

    gap_count = sum(1 for e in errors if e.startswith("gap of"))
    invalid_clip_count = sum(
        1 for e in errors
        if "time reversal" in e or "duration_ms" in e
    )

    return TimelineValidation(
        first_start_ms=first_start_ms,
        last_end_ms=last_end_ms,
        gap_count=gap_count,
        invalid_clip_count=invalid_clip_count,
    )
