"""
Unit tests for security_scanning core pure functions.
Tests cover: URL normalisation, URL validation, Windows version detection,
default output path generation, argument validation logic, reporter helpers,
Finding.to_report(), _risk_rank(), _pct(), _bar(), _split_detail().
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock


# ===========================================================================
# 1. _normalize_url — scheme injection
# ===========================================================================

from modules.web_scanner import _normalize_url

class TestNormalizeUrl:
    def test_https_url_unchanged(self):
        assert _normalize_url("https://example.com") == "https://example.com"

    def test_http_url_unchanged(self):
        assert _normalize_url("http://example.com") == "http://example.com"

    def test_bare_domain_gets_https(self):
        result = _normalize_url("example.com")
        assert result == "https://example.com"

    def test_leading_whitespace_stripped(self):
        result = _normalize_url("  https://example.com  ")
        assert result == "https://example.com"

    def test_path_preserved(self):
        result = _normalize_url("example.com/path/to/page")
        assert result.startswith("https://")
        assert "path/to/page" in result


# ===========================================================================
# 2. _validate_url — URL structural validation
# ===========================================================================

from modules.web_scanner import _validate_url

class TestValidateUrl:
    def test_valid_https_passes(self):
        # Use allow_private_targets=True to skip DNS resolution
        result = _validate_url("https://example.com", allow_private_targets=True)
        assert result.scheme == "https"
        assert result.hostname == "example.com"

    def test_valid_http_passes(self):
        result = _validate_url("http://example.com/path", allow_private_targets=True)
        assert result.scheme == "http"

    def test_ftp_raises(self):
        with pytest.raises(ValueError, match="Only HTTP and HTTPS"):
            _validate_url("ftp://example.com", allow_private_targets=True)

    def test_missing_hostname_raises(self):
        with pytest.raises(ValueError, match="hostname"):
            _validate_url("https://", allow_private_targets=True)

    def test_credentials_in_url_raises(self):
        with pytest.raises(ValueError, match="Credentials"):
            _validate_url("https://user:pass@example.com", allow_private_targets=True)

    def test_invalid_port_raises(self):
        # Python's urllib raises "Port out of range 0-65535" before _validate_url
        # can apply its own message, so match case-insensitively.
        with pytest.raises(ValueError, match="(?i)port"):
            _validate_url("https://example.com:99999", allow_private_targets=True)

    def test_valid_port_passes(self):
        result = _validate_url("https://example.com:8443/path", allow_private_targets=True)
        assert result.port == 8443


# ===========================================================================
# 3. _detect_windows — Windows version name mapping
# ===========================================================================

from main import _detect_windows, _WIN_BUILDS

class TestDetectWindows:
    def _run_with_build(self, build: int):
        fake_version = f"10.0.{build}"
        with patch("main.platform.version", return_value=fake_version), \
             patch("main.platform.release", return_value="10"), \
             patch("main.platform.machine", return_value="AMD64"), \
             patch("main.platform.processor", return_value="Intel"):
            return _detect_windows()

    def test_known_build_returns_correct_name(self):
        result = self._run_with_build(22621)
        assert result["windows_name"] == "Windows 11 22H2"

    def test_build_number_stored(self):
        result = self._run_with_build(19045)
        assert result["windows_build"] == 19045

    def test_unknown_build_falls_back_to_generic(self):
        result = self._run_with_build(10000)
        # No entry in _WIN_BUILDS for build 10000, falls back to "Windows 10"
        assert "Windows" in result["windows_name"]

    def test_result_contains_required_keys(self):
        result = self._run_with_build(22621)
        for key in ("windows_name", "windows_build", "version", "machine", "processor"):
            assert key in result

    def test_processor_truncated_to_80_chars(self):
        long_proc = "x" * 200
        fake_version = "10.0.22621"
        with patch("main.platform.version", return_value=fake_version), \
             patch("main.platform.release", return_value="10"), \
             patch("main.platform.machine", return_value="AMD64"), \
             patch("main.platform.processor", return_value=long_proc):
            result = _detect_windows()
        assert len(result["processor"]) <= 80


# ===========================================================================
# 4. _default_output — output filename generation
# ===========================================================================

from main import _default_output

class TestDefaultOutput:
    def test_web_only_contains_web(self):
        name = _default_output(web=True, system=False)
        assert "web" in name
        assert "system" not in name

    def test_system_only_contains_system(self):
        name = _default_output(web=False, system=True)
        assert "system" in name
        assert "web" not in name

    def test_both_contains_web_and_system(self):
        name = _default_output(web=True, system=True)
        assert "web" in name
        assert "system" in name

    def test_neither_uses_scan_tag(self):
        name = _default_output(web=False, system=False)
        assert "scan" in name

    def test_output_ends_with_json(self):
        name = _default_output(web=True, system=False)
        assert name.endswith(".json")

    def test_output_contains_timestamp(self):
        import re
        name = _default_output(web=True, system=False)
        assert re.search(r"\d{8}_\d{6}", name), "Expected YYYYMMDD_HHMMSS timestamp in filename"


# ===========================================================================
# 5. Reporter utility methods — no-color mode
# ===========================================================================

from modules.reporter import Reporter

class TestReporterUtils:
    def setup_method(self):
        self.r = Reporter(use_color=False, verbose=False)

    def test_info_prefix(self):
        assert self.r.info("hello").startswith("[*]")

    def test_warn_prefix(self):
        assert self.r.warn("caution").startswith("[경고]")

    def test_success_prefix(self):
        assert self.r.success("ok").startswith("[+]")

    def test_error_prefix(self):
        assert self.r.error("fail").startswith("[!]")

    def test_no_color_no_ansi_codes(self):
        text = self.r.info("test message")
        assert "\033[" not in text

    def test_message_content_preserved(self):
        assert "hello world" in self.r.info("hello world")


# ===========================================================================
# 6. Reporter._risk_rank and module-level helpers
# ===========================================================================

from modules.reporter import _risk_rank, _pct, _bar, _split_detail

class TestReporterHelpers:
    def test_risk_rank_critical_is_zero(self):
        assert _risk_rank({"risk_level": "Critical"}) == 0

    def test_risk_rank_info_is_last(self):
        info_rank = _risk_rank({"risk_level": "Info"})
        critical_rank = _risk_rank({"risk_level": "Critical"})
        assert info_rank > critical_rank

    def test_risk_rank_ordering(self):
        order = ["Critical", "High", "Medium", "Low", "Info"]
        ranks = [_risk_rank({"risk_level": r}) for r in order]
        assert ranks == sorted(ranks)

    def test_pct_zero_of_zero(self):
        assert _pct(0, 0) == "  0%"

    def test_pct_half(self):
        result = _pct(1, 2)
        assert "50%" in result

    def test_pct_full(self):
        result = _pct(5, 5)
        assert "100%" in result

    def test_bar_empty_when_zero(self):
        result = _bar(0, 10)
        assert all(c == "-" for c in result)

    def test_bar_full_when_equal(self):
        result = _bar(10, 10)
        assert "#" in result

    def test_split_detail_with_recommendation(self):
        combined = "This is the detail.\n  Recommendation: Fix it now."
        detail, rec = _split_detail(combined)
        assert detail == "This is the detail."
        assert rec == "Fix it now."

    def test_split_detail_without_recommendation(self):
        combined = "Only detail here."
        detail, rec = _split_detail(combined)
        assert detail == "Only detail here."
        assert rec == ""


# ===========================================================================
# 7. Finding.to_report() — dict conversion
# ===========================================================================

from modules.web_scanner import Finding

class TestFindingToReport:
    def _make_finding(self, **kwargs):
        defaults = dict(
            check="Security Headers",
            risk_level="High",
            title="Missing Header: X-Frame-Options",
            detail="The header is absent.",
            recommendation="Add X-Frame-Options: DENY",
            evidence="Header not present",
            owasp="A05:2021",
        )
        defaults.update(kwargs)
        return Finding(**defaults)

    def test_to_report_contains_required_keys(self):
        report = self._make_finding().to_report()
        for key in ("category", "risk_level", "title", "detail", "status", "evidence", "owasp"):
            assert key in report

    def test_high_risk_maps_to_fail_status(self):
        report = self._make_finding(risk_level="High").to_report()
        assert report["status"] == "FAIL"

    def test_low_risk_maps_to_warn_status(self):
        report = self._make_finding(risk_level="Low").to_report()
        assert report["status"] == "WARN"

    def test_info_risk_maps_to_info_status(self):
        report = self._make_finding(risk_level="Info").to_report()
        assert report["status"] == "INFO"

    def test_category_is_web(self):
        assert self._make_finding().to_report()["category"] == "web"

    def test_recommendation_appended_to_detail(self):
        report = self._make_finding().to_report()
        assert "Recommendation:" in report["detail"]

    def test_rank_property_ordering(self):
        critical = self._make_finding(risk_level="Critical")
        high = self._make_finding(risk_level="High")
        info = self._make_finding(risk_level="Info")
        assert critical.rank < high.rank < info.rank


# ===========================================================================
# 8. _validate_args — argument constraint checking
# ===========================================================================

from main import _validate_args

class TestValidateArgs:
    def _make_args(self, **kwargs):
        defaults = dict(web="https://example.com", system=False, threads=5, timeout=10)
        defaults.update(kwargs)
        ns = argparse.Namespace(**defaults)
        return ns

    def _make_reporter(self):
        return Reporter(use_color=False, verbose=False)

    def test_valid_args_does_not_raise(self):
        # Should not call sys.exit
        with patch("sys.exit") as mock_exit:
            _validate_args(self._make_args(), self._make_reporter())
            mock_exit.assert_not_called()

    def test_no_target_calls_sys_exit(self):
        args = self._make_args(web=None, system=False)
        with pytest.raises(SystemExit):
            _validate_args(args, self._make_reporter())

    def test_threads_zero_calls_sys_exit(self):
        args = self._make_args(threads=0)
        with pytest.raises(SystemExit):
            _validate_args(args, self._make_reporter())

    def test_threads_above_50_calls_sys_exit(self):
        args = self._make_args(threads=51)
        with pytest.raises(SystemExit):
            _validate_args(args, self._make_reporter())

    def test_timeout_zero_calls_sys_exit(self):
        args = self._make_args(timeout=0)
        with pytest.raises(SystemExit):
            _validate_args(args, self._make_reporter())

    def test_timeout_above_300_calls_sys_exit(self):
        args = self._make_args(timeout=301)
        with pytest.raises(SystemExit):
            _validate_args(args, self._make_reporter())

    def test_system_flag_only_on_non_windows_exits(self):
        args = self._make_args(web=None, system=True)
        with patch("main.platform.system", return_value="Linux"):
            with pytest.raises(SystemExit):
                _validate_args(args, self._make_reporter())
