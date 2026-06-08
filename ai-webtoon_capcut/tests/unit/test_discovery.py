"""Unit tests for song discovery and status assessment.

Covers: assess_song_status with empty folder and with a
fully-populated folder (storyboard + panel image + audio).
"""
import tempfile
import unittest
from pathlib import Path

from webtoon_capcut.discovery.song_discovery import assess_song_status
from webtoon_capcut.domain.enums import SongStatus


# Minimal storyboard markdown that contains a panel_001 row so that
# _storyboard_has_panels() returns True.
_STORYBOARD_WITH_PANELS = """\
# 스토리보드

| 패널 번호 | 섹션 | 타입 | 지속 시간 | 가사 미리보기 |
|-----------|------|------|-----------|--------------|
| panel_001 | Intro | wide | 5초 | Instrumental |
"""


class TestAssessStatusNoStoryboard(unittest.TestCase):
    """Empty folder → PROMPTS_ONLY (no storyboard, no images)."""

    def test_assess_status_no_storyboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            song_dir = Path(tmp_dir)
            candidate = assess_song_status(song_dir)

        self.assertEqual(candidate.status, SongStatus.PROMPTS_ONLY)


class TestAssessStatusBuildReady(unittest.TestCase):
    """Storyboard + panel image + audio → BUILD_READY (or higher)."""

    def test_assess_status_build_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            song_dir = Path(tmp_dir)

            # Create storyboard
            storyboard_path = song_dir / "01_storyboard.md"
            storyboard_path.write_text(_STORYBOARD_WITH_PANELS, encoding="utf-8")

            # Create panel image in the expected sub-directory
            img_dir = song_dir / "img"
            img_dir.mkdir()
            (img_dir / "panel_001.png").write_bytes(b"\x89PNG\r\n")

            # Create audio file directly inside song_dir
            (song_dir / "song.wav").write_bytes(b"RIFF")

            candidate = assess_song_status(song_dir)

        # Status must be at least BUILD_READY
        build_ready_and_above = {
            SongStatus.BUILD_READY,
            SongStatus.REVIEW_REQUIRED,
        }
        self.assertIn(
            candidate.status,
            build_ready_and_above,
            msg=f"Expected BUILD_READY or above, got {candidate.status}. "
                f"Reasons: {candidate.reasons}",
        )


if __name__ == "__main__":
    unittest.main()
