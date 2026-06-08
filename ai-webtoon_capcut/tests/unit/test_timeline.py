"""Unit tests for timeline policy modules.

Covers: calc_needed_clips, expand_images, validate_timeline,
and canonicalize_label.
"""
import unittest

from webtoon_capcut.domain.enums import CanonicalType
from webtoon_capcut.domain.models import (
    CanvasConfig,
    Clip,
    ClipPolicy,
    EditTimeline,
    TimelineValidation,
    TransitionOut,
)
from webtoon_capcut.sections.canonicalizer import canonicalize_label
from webtoon_capcut.timeline.duration_policy import calc_needed_clips
from webtoon_capcut.timeline.reuse_policy import expand_images
from webtoon_capcut.timeline.validator import validate_timeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_clip(clip_id: str, start_ms: int, end_ms: int) -> Clip:
    return Clip(
        clip_id=clip_id,
        panel_id="panel_001",
        section_id="section_001",
        media_path="img/panel_001.png",
        start_ms=start_ms,
        end_ms=end_ms,
        duration_ms=end_ms - start_ms,
        motion_preset="slow_zoom_in",
        reuse_index=0,
        fit="cover",
        transition_out=TransitionOut(),
    )


def _make_timeline(clips: list[Clip], audio_duration_ms: int) -> EditTimeline:
    return EditTimeline(
        schema_version="2.0",
        audio_duration_ms=audio_duration_ms,
        canvas=CanvasConfig(fps=30),
        clips=clips,
        validation=TimelineValidation(
            first_start_ms=clips[0].start_ms if clips else 0,
            last_end_ms=clips[-1].end_ms if clips else 0,
            gap_count=0,
            invalid_clip_count=0,
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCalcNeededClips(unittest.TestCase):
    """calc_needed_clips: section 30 s, preferred_max 8 s → 4 clips."""

    def test_calc_needed_clips(self) -> None:
        policy = ClipPolicy(preferred_max_seconds=8.0)
        section_ms = 30_000  # 30 seconds
        result = calc_needed_clips(section_ms, policy)
        # ceil(30000 / 8000) = ceil(3.75) = 4
        self.assertEqual(result, 4)


class TestExpandImagesExact(unittest.TestCase):
    """expand_images: 3 panels, need 3 → same order, no duplication."""

    def test_expand_images_exact(self) -> None:
        panels = ["panel_001", "panel_002", "panel_003"]
        result = expand_images(panels, needed_count=3, max_reuse=3)
        self.assertEqual(result, panels)
        self.assertEqual(len(result), 3)


class TestExpandImagesReuse(unittest.TestCase):
    """expand_images: 2 panels, need 5, max_reuse 3 → 5 items returned."""

    def test_expand_images_reuse(self) -> None:
        panels = ["panel_001", "panel_002"]
        result = expand_images(panels, needed_count=5, max_reuse=3)
        # max_producible = 2 * 3 = 6, effective = min(5, 6) = 5
        self.assertEqual(len(result), 5)
        # Every returned id must be one of the originals
        for pid in result:
            self.assertIn(pid, panels)
        # No single panel appears more than max_reuse times
        for panel in panels:
            self.assertLessEqual(result.count(panel), 3)


class TestValidateTimelineOk(unittest.TestCase):
    """validate_timeline: valid EditTimeline returns no errors."""

    def test_validate_timeline_ok(self) -> None:
        clips = [
            _make_clip("c1", 0, 8000),
            _make_clip("c2", 8000, 16000),
            _make_clip("c3", 16000, 24000),
        ]
        timeline = _make_timeline(clips, audio_duration_ms=24000)
        errors = validate_timeline(timeline)
        self.assertEqual(errors, [])


class TestValidateTimelineGap(unittest.TestCase):
    """validate_timeline: gap between clips produces error messages."""

    def test_validate_timeline_gap(self) -> None:
        clips = [
            _make_clip("c1", 0, 8000),
            # 500 ms gap before c2
            _make_clip("c2", 8500, 16000),
        ]
        timeline = _make_timeline(clips, audio_duration_ms=16000)
        errors = validate_timeline(timeline)
        # At least one error must mention the gap
        gap_errors = [e for e in errors if "gap" in e.lower()]
        self.assertGreater(len(gap_errors), 0)


class TestCanonicalizeLabel(unittest.TestCase):
    """canonicalize_label: known alias maps to expected CanonicalType."""

    def test_canonicalize_label(self) -> None:
        result = canonicalize_label("Final Chorus")
        self.assertEqual(result, CanonicalType.chorus)


class TestCanonicalizeUnknown(unittest.TestCase):
    """canonicalize_label: unknown label maps to CanonicalType.other."""

    def test_canonicalize_unknown(self) -> None:
        result = canonicalize_label("RandomSection")
        self.assertEqual(result, CanonicalType.other)


if __name__ == "__main__":
    unittest.main()
