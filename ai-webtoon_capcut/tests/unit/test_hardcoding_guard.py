"""Regression tests for the semantic fixture-name guard."""
from pathlib import Path
import tempfile
import unittest
import sys

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from check_song_hardcoding import find_hardcoded_song_names  # noqa: E402

class SongHardcodingGuardTests(unittest.TestCase):
    def test_detects_fixture_name_in_executable_literal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bad.py").write_text('title = "UPGRADE"\nif title == "UPGRADE":\n    pass\n', encoding="utf-8")
            self.assertTrue(find_hardcoded_song_names(root))

    def test_ignores_docstrings_and_non_source_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "safe.py").write_text('\"\"\"UPGRADE fixture documentation.\"\"\"\ndef run():\n    \"\"\"디저트 example only.\"\"\"\n    return "generic"\n', encoding="utf-8")
            vendor = root / "node_modules"
            vendor.mkdir()
            (vendor / "README.md").write_text("UPGRADE", encoding="utf-8")
            self.assertEqual(find_hardcoded_song_names(root), [])

if __name__ == "__main__":
    unittest.main()
