"""Prove the public license guard accepts its files and rejects exact defects."""

import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from check_license_scope import LICENSE, NOTICES, README, ROOT, check, main  # noqa: E402


class LicenseScopeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        for path in (LICENSE, NOTICES, README):
            shutil.copy2(ROOT / path, self.root / path)
        self.tracked = {path.as_posix() for path in (LICENSE, NOTICES, README)}

    def tearDown(self):
        self.folder.cleanup()

    def test_complete_scope_passes(self):
        self.assertEqual(check(self.root, self.tracked), [])

    def test_changed_license_reports_the_intended_failure(self):
        (self.root / LICENSE).write_text("not the MIT license\n", encoding="utf-8")
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main(self.root, self.tracked), 1)
        self.assertIn("ROOT_LICENSE_CHANGED", stdout.getvalue())
        self.assertNotIn("README_MISSING", stdout.getvalue())

    def test_crlf_line_endings_do_not_change_the_license_text(self):
        license_file = self.root / LICENSE
        lf_bytes = license_file.read_bytes().replace(b"\r\n", b"\n")
        license_file.write_bytes(lf_bytes.replace(b"\n", b"\r\n"))
        self.assertEqual(check(self.root, self.tracked), [])

    def test_unrelated_missing_readme_is_not_accepted_as_license_tampering(self):
        (self.root / README).unlink()
        errors = check(self.root, self.tracked)
        self.assertIn("README_MISSING", errors)
        self.assertNotIn("ROOT_LICENSE_CHANGED", errors)


if __name__ == "__main__":
    unittest.main()
