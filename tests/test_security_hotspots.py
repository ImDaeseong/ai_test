"""Regression tests for scripts/check_security_hotspots.py's pattern rules."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# A path-limited commit exports GIT_INDEX_FILE to the pre-commit hook; these tests run `git add -A` in
# scratch repos, which would otherwise write into the caller's real index ("invalid object" at commit).
for _var in ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE"):
    os.environ.pop(_var, None)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_security_hotspots as scanner


class SecurityHotspotScannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_root = Path(tempfile.mkdtemp(prefix="ai_test_hotspot_test_"))
        self.addCleanup(shutil.rmtree, self._tmp_root, ignore_errors=True)
        subprocess.run(["git", "init", "--quiet"], cwd=self._tmp_root, check=True)

    def _scan(self, filename: str, content: str) -> list[str]:
        (self._tmp_root / filename).write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self._tmp_root, check=True, capture_output=True)
        original_root = scanner.REPO_ROOT
        scanner.REPO_ROOT = self._tmp_root
        try:
            return scanner.scan()
        finally:
            scanner.REPO_ROOT = original_root

    def test_detects_hardcoded_api_key(self) -> None:
        findings = self._scan("app.py", 'API_KEY = "zz9f8a7b6c5d4e3f2a1b0c"\n')
        self.assertTrue(any("CWE-798" in f for f in findings))

    def test_detects_cleartext_external_http(self) -> None:
        findings = self._scan("client.py", 'BASE_URL = "http://api.example.org.kr/v1"\n')
        self.assertTrue(any("CWE-319" in f for f in findings))

    def test_detects_cleartext_http_in_fstring_interpolation(self) -> None:
        """2026-09-26 독립 리뷰 발견: 도메인 문자 클래스에 '{'가 빠져서, f-string으로

        보간된 URL(f"http://{host}/api")은 http:// 뒤 첫 글자가 '{'라 매칭에서
        빠져나갔다 — 하드코딩된 리터럴 도메인만 잡고 동적 URL은 놓쳤다."""
        findings = self._scan("client.py", 'url = f"http://{host}/api"\n')
        self.assertTrue(any("CWE-319" in f for f in findings))

    def test_example_domain_not_flagged(self) -> None:
        # Regression: RFC 2606 reserved domains are the standard test/doc
        # fixture -- found live flagging Pexels/mp4_tag/security_scanning
        # test files that use "http://example.com" as their fixture URL.
        for domain in ("example.com", "example.org", "example.net"):
            with self.subTest(domain=domain):
                findings = self._scan("client.py", f'URL = "http://{domain}/path"\n')
                self.assertEqual(findings, [])

    def test_w3_xml_namespace_not_flagged(self) -> None:
        # Regression: "http://www.w3.org/..." is an XML/SVG namespace
        # identifier, never a network fetch -- found live in an SVG string
        # in a browser extension's content script.
        findings = self._scan("view.js", '`<svg xmlns="http://www.w3.org/2000/svg">`;\n')
        self.assertEqual(findings, [])

    def test_excluded_host_lookalike_still_flagged(self) -> None:
        # Regression: an excluded host must end at a host boundary -- "localhost.evil.com" used to
        # pass because the exclusion matched only the prefix (found by an independent review).
        def scan(content: str) -> list[str]:
            c = content
            return self._scan("client.py", c)

        for host in ("www.w3.org.evil.com", "localhost.evil.com", "example.com.evil.com",
                     "localhost@evil.com", "127.0.0.1:80@evil.com"):
            with self.subTest(host=host):
                findings = scan(f'URL = "http://{host}/x"\n')
                self.assertTrue(any("CWE-319" in f for f in findings))
        self.assertEqual(scan('URL = "http://127.0.0.2:8000/x"\n'), [])

    def test_javascript_regexp_exec_not_flagged(self) -> None:
        # Regression: `.exec(` is RegExp.prototype.exec() in JS/TS, not the
        # dangerous exec() builtin -- \b(?:eval|exec)\s*\( matched it because
        # \b only checks the char before "exec", not the preceding ".". Found
        # live flagging lyricvideo/src/parsers.ts's regex parsing code.
        findings = self._scan("parsers.ts", "const match = /^\\d+$/.exec(stamp);\n")
        self.assertEqual(findings, [])

    def test_bare_eval_still_flagged(self) -> None:
        findings = self._scan("app.js", "eval(userInput);\n")
        self.assertTrue(any("CWE-95" in f for f in findings))

    def test_qa_allow_comment_suppresses_finding(self) -> None:
        findings = self._scan(
            "client.py",
            'BASE_URL = "http://api.example.org.kr/v1"  # qa:allow CWE-319 - internal test host\n',
        )
        self.assertEqual(findings, [])

    def test_scanner_self_excludes_own_rule_definitions(self) -> None:
        findings = self._scan(
            "check_security_hotspots.py", "subprocess.Popen(user_input, shell=True)\n",
        )
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
