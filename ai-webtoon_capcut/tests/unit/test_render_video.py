"""Tests for the Python-to-Remotion render boundary."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from webtoon_capcut.application.render_video import render_timeline


class RenderTimelineTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path, Path]:
        media = root / "panel.svg"
        media.write_text("<svg/>", encoding="utf-8")
        audio = root / "audio.wav"
        audio.write_bytes(b"RIFFfixture")
        timeline = root / "timeline.json"
        timeline.write_text(json.dumps({
            "schema_version": "2.0",
            "audio_duration_ms": 1000,
            "canvas": {"width": 960, "height": 540, "fps": 30},
            "clips": [{"clip_id": "c1", "panel_id": "p1", "section_id": "intro", "media_path": "panel.svg", "start_ms": 0, "end_ms": 1000, "duration_ms": 1000, "motion_preset": "static", "fit": "cover"}],
        }), encoding="utf-8")
        remotion = root / "remotion"
        (remotion / "src").mkdir(parents=True)
        (remotion / "src" / "index.ts").write_text("", encoding="utf-8")
        cli = remotion / "node_modules" / ".bin" / ("remotion.cmd" if __import__("os").name == "nt" else "remotion")
        cli.parent.mkdir(parents=True)
        cli.write_text("", encoding="utf-8")
        return timeline, audio, remotion

    def test_stages_props_runs_renderer_and_removes_private_media(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            timeline, audio, remotion = self._fixture(root)
            output = root / "final.mp4"
            captured: dict = {}
            render_target: Path | None = None

            def fake_run(command, **kwargs):
                nonlocal render_target
                props_path = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("--props=")))
                captured.update(json.loads(props_path.read_text(encoding="utf-8")))
                render_target = Path(command[4])
                render_target.write_bytes(b"mp4")
                return type("Completed", (), {"returncode": 0, "stderr": ""})()

            with patch("webtoon_capcut.application.render_video.subprocess.run", side_effect=fake_run):
                result = render_timeline(timeline, audio, output, remotion)

            self.assertEqual(result["bytes"], 3)
            self.assertNotEqual(render_target, output)
            self.assertTrue(output.is_file())
            self.assertFalse(render_target.exists())
            self.assertTrue(captured["timeline"]["clips"][0]["media_path"].startswith("jobs/"))
            self.assertFalse(any((remotion / "public" / "jobs").iterdir()))
            self.assertFalse(any((remotion / ".remotion" / "jobs").iterdir()))

    def test_rejects_a_gap_before_invoking_remotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            timeline, audio, remotion = self._fixture(root)
            data = json.loads(timeline.read_text(encoding="utf-8"))
            data["clips"][0]["start_ms"] = 1
            timeline.write_text(json.dumps(data), encoding="utf-8")
            with patch("webtoon_capcut.application.render_video.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "gap"):
                    render_timeline(timeline, audio, root / "bad.mp4", remotion)
                run.assert_not_called()

    def test_rejects_unsupported_media_before_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            timeline, audio, remotion = self._fixture(root)
            data = json.loads(timeline.read_text(encoding="utf-8"))
            unsupported = root / "panel.exe"
            unsupported.write_bytes(b"not-media")
            data["clips"][0]["media_path"] = unsupported.name
            timeline.write_text(json.dumps(data), encoding="utf-8")
            with patch("webtoon_capcut.application.render_video.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "unsupported image format"):
                    render_timeline(timeline, audio, root / "bad.mp4", remotion)
                run.assert_not_called()

    def test_failure_keeps_existing_output_and_removes_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            timeline, audio, remotion = self._fixture(root)
            output = root / "existing.mp4"
            output.write_bytes(b"previous")

            def fake_run(command, **kwargs):
                Path(command[4]).write_bytes(b"partial")
                return type("Completed", (), {"returncode": 1, "stderr": "fixture failure"})()

            with patch("webtoon_capcut.application.render_video.subprocess.run", side_effect=fake_run):
                with self.assertRaisesRegex(RuntimeError, "fixture failure"):
                    render_timeline(timeline, audio, output, remotion)

            self.assertEqual(output.read_bytes(), b"previous")
            self.assertEqual(list(root.glob(".*.tmp.mp4")), [])

if __name__ == "__main__":
    unittest.main()
