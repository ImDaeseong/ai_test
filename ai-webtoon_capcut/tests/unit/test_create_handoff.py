"""Tests for portable editor handoff bundles."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from webtoon_capcut.application.create_handoff import (
    create_editor_handoff,
    verify_editor_handoff,
)


class EditorHandoffTests(unittest.TestCase):
    def _inputs(self, root: Path) -> tuple[Path, Path, Path]:
        video = root / "render.mp4"
        video.write_bytes(b"mp4-fixture")
        image = root / "private" / "panel.png"
        image.parent.mkdir()
        image.write_bytes(b"png")
        timeline = root / "timeline.json"
        timeline.write_text(json.dumps({
            "schema_version": "2.0",
            "audio_duration_ms": 1000,
            "audio_path": str(root / "private" / "audio.wav"),
            "clips": [{"clip_id": "c1", "media_path": str(image)}],
        }), encoding="utf-8")
        subtitles = root / "captions.srt"
        subtitles.write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n", encoding="utf-8")
        return video, timeline, subtitles

    def test_creates_relative_path_bundle_with_hashes_and_hold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video, timeline, subtitles = self._inputs(root)
            output = root / "handoff"
            result = create_editor_handoff(video, timeline, output, subtitles_path=subtitles)

            self.assertEqual(result["review_status"], "HOLD")
            self.assertEqual(sorted(p.name for p in output.iterdir()), [
                "README.txt", "manifest.json", "subtitles.srt", "timeline.json", "video.mp4"
            ])
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(manifest["native_capcut_project"])
            self.assertIn("CapCut 전용 프로젝트 파일이 아닙니다", (output / "README.txt").read_text(encoding="utf-8"))
            self.assertTrue(all("/" not in item["path"] and "\\" not in item["path"] for item in manifest["files"]))
            exported = (output / "timeline.json").read_text(encoding="utf-8")
            self.assertNotIn(str(root), exported)
            self.assertIn("source-media-not-included/panel.png", exported)
            self.assertIn("source-media-not-included/audio.wav", exported)

    def test_existing_destination_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video, timeline, _ = self._inputs(root)
            output = root / "handoff"
            output.mkdir()
            marker = output / "keep.txt"
            marker.write_text("keep", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                create_editor_handoff(video, timeline, output)

            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")
            self.assertEqual(list(root.glob(".handoff.*")), [])

    def test_verifier_detects_content_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video, timeline, _ = self._inputs(root)
            output = root / "handoff"
            create_editor_handoff(video, timeline, output)
            self.assertEqual(verify_editor_handoff(output)["integrity_status"], "PASS")
            (output / "video.mp4").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                verify_editor_handoff(output)

    def test_verifier_detects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video, timeline, _ = self._inputs(root)
            output = root / "handoff"
            create_editor_handoff(video, timeline, output)
            (output / "README.txt").unlink()
            with self.assertRaisesRegex(ValueError, "file missing"):
                verify_editor_handoff(output)

    def test_verifier_detects_extra_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video, timeline, _ = self._inputs(root)
            output = root / "handoff"
            create_editor_handoff(video, timeline, output)
            (output / "extra.txt").write_text("extra", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "membership mismatch"):
                verify_editor_handoff(output)

    def test_verifier_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video, timeline, _ = self._inputs(root)
            output = root / "handoff"
            create_editor_handoff(video, timeline, output)
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"][0]["path"] = "../outside.mp4"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsafe handoff path"):
                verify_editor_handoff(output)

if __name__ == "__main__":
    unittest.main()
