"""Unit tests for webtoon_capcut adapter modules.

Covers: LRC parser, SRT parser, LRC quality score,
storyboard markdown parser, and frame alignment utility.
"""
import tempfile
import unittest
from pathlib import Path

from webtoon_capcut.adapters.lrc import lrc_quality_score, parse_lrc
from webtoon_capcut.adapters.srt import parse_srt
from webtoon_capcut.adapters.storyboard_markdown import parse_storyboard
from webtoon_capcut.domain.enums import CueType, SubtitleFormat
from webtoon_capcut.timeline.duration_policy import frame_align_ms


class TestParseLrcBasic(unittest.TestCase):
    """parse_lrc: basic two-cue LRC file."""

    def test_parse_lrc_basic(self) -> None:
        lrc_text = "[00:01.00]가사1\n[00:03.50]가사2\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".lrc", encoding="utf-8", delete=False
        ) as tmp:
            tmp.write(lrc_text)
            tmp_path = tmp.name

        try:
            cues = parse_lrc(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        self.assertEqual(len(cues), 2)

        # [00:01.00] => 1*1000 + 0*10 = 1000 ms
        self.assertEqual(cues[0].start_ms, 1000)
        self.assertEqual(cues[0].text, "가사1")
        self.assertEqual(cues[0].source_format, SubtitleFormat.lrc)
        self.assertEqual(cues[0].cue_type, CueType.lyric)

        # [00:03.50] => 3*1000 + 50*10 = 3500 ms
        self.assertEqual(cues[1].start_ms, 3500)
        self.assertEqual(cues[1].text, "가사2")
        # last cue end_ms = start + 5000
        self.assertEqual(cues[1].end_ms, cues[1].start_ms + 5000)

        # first cue end_ms = second cue start_ms
        self.assertEqual(cues[0].end_ms, cues[1].start_ms)


class TestParseSrtBasic(unittest.TestCase):
    """parse_srt: basic one-block SRT file."""

    def test_parse_srt_basic(self) -> None:
        srt_text = (
            "1\n"
            "00:00:01,000 --> 00:00:03,500\n"
            "가사1\n"
            "\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".srt", encoding="utf-8", delete=False
        ) as tmp:
            tmp.write(srt_text)
            tmp_path = tmp.name

        try:
            cues = parse_srt(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].start_ms, 1000)
        self.assertEqual(cues[0].end_ms, 3500)
        self.assertEqual(cues[0].text, "가사1")
        self.assertEqual(cues[0].source_format, SubtitleFormat.srt)
        self.assertEqual(cues[0].cue_type, CueType.lyric)


class TestLrcQualityScore(unittest.TestCase):
    """lrc_quality_score: normal cues produce a score >= 0.7."""

    def test_lrc_quality_score(self) -> None:
        # Build 10 well-formed cues to maximise all three components.
        lines = "".join(
            f"[00:{i:02d}.00]가사{i}\n" for i in range(10)
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".lrc", encoding="utf-8", delete=False
        ) as tmp:
            tmp.write(lines)
            tmp_path = tmp.name

        try:
            cues = parse_lrc(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        score = lrc_quality_score(cues)
        self.assertGreaterEqual(score, 0.7)
        self.assertLessEqual(score, 1.0)


class TestParseStoryboardEmpty(unittest.TestCase):
    """parse_storyboard: empty markdown returns a Storyboard with 0 panels."""

    def test_parse_storyboard_empty(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", encoding="utf-8", delete=False
        ) as tmp:
            tmp.write("# 빈 스토리보드\n\n내용 없음.\n")
            tmp_path = tmp.name

        try:
            storyboard = parse_storyboard(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        self.assertEqual(len(storyboard.panels), 0)


class TestFrameAlignMs(unittest.TestCase):
    """frame_align_ms: 30 fps, 1050 ms rounds to nearest frame boundary.

    Implementation: frame_ms = 1000/fps; rounded_frames = floor(ms/frame_ms + 0.5);
    result = int(rounded_frames * frame_ms).

    At 30 fps, frame_ms = 33.333...
    1050 / 33.333... = 31.5  → rounded_frames = 32
    result = int(32 * 33.333...) = int(1066.666...) = 1066

    The test verifies that the result equals the value computed by the same
    rounding formula (not floating-point division back), and that it is the
    closest frame boundary to the input.
    """

    def test_frame_align_ms(self) -> None:
        import math

        fps = 30
        input_ms = 1050
        result = frame_align_ms(input_ms, fps)

        frame_size = 1000 / fps  # 33.333...

        # Reproduce what the implementation does
        rounded_frames = math.floor(input_ms / frame_size + 0.5)
        expected = int(rounded_frames * frame_size)
        self.assertEqual(result, expected)

        # Also confirm: result is within one frame of the input
        self.assertLessEqual(abs(result - input_ms), frame_size)


if __name__ == "__main__":
    unittest.main()
