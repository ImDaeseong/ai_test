import queue
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Optional

from find_string_app import EXTENSION_PRESETS, Match, SearchWorker


class SearchWorkerTests(unittest.TestCase):
    def run_worker(
        self,
        root: Path,
        keyword: str,
        *,
        case_sensitive: bool = False,
        include_binary_like: bool = False,
        extensions: Optional[set[str]] = None,
    ):
        outbox = queue.Queue()
        worker = SearchWorker(
            root_path=root,
            keyword=keyword,
            case_sensitive=case_sensitive,
            include_binary_like=include_binary_like,
            extensions=extensions or set(),
            outbox=outbox,
            stop_event=threading.Event(),
        )
        worker.run()

        messages = []
        while not outbox.empty():
            messages.append(outbox.get_nowait())
        return messages

    def test_extension_presets_are_name_value_pairs(self):
        for preset in EXTENSION_PRESETS:
            self.assertIsInstance(preset, tuple)
            self.assertEqual(2, len(preset))
            self.assertIsInstance(preset[0], str)
            self.assertIsInstance(preset[1], str)

    def test_finds_keyword_case_insensitively_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "note.txt").write_text("Alpha\nneedle here\n", encoding="utf-8")

            messages = self.run_worker(root, "NEEDLE")

            matches = [message[1] for message in messages if message[0] == "match"]
            self.assertEqual([Match(root / "note.txt", 2, "needle here")], matches)
            self.assertEqual("done", messages[-1][0])

    def test_case_sensitive_search_does_not_match_different_case(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "note.txt").write_text("needle here\n", encoding="utf-8")

            messages = self.run_worker(root, "NEEDLE", case_sensitive=True)

        self.assertFalse([message for message in messages if message[0] == "match"])

    def test_extension_filter_limits_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "keep.py").write_text("target\n", encoding="utf-8")
            (root / "skip.txt").write_text("target\n", encoding="utf-8")

            messages = self.run_worker(root, "target", extensions={".py"})

        matches = [message[1].path.name for message in messages if message[0] == "match"]
        self.assertEqual(["keep.py"], matches)

    def test_binary_like_files_are_skipped_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "binary.bin").write_bytes(b"target\x00target")

            messages = self.run_worker(root, "target")

        self.assertFalse([message for message in messages if message[0] == "match"])


if __name__ == "__main__":
    unittest.main()
