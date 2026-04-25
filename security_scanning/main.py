"""
DefenseScan v1.0 — Defensive Security Scanner
OWASP-aligned, passive, non-destructive.

Entry point: parse arguments, orchestrate scan modules, produce console output
and a JSON report.  Handles admin detection and Windows version identification.
"""

import argparse
import ctypes
import datetime
import platform
import sys
import time
from typing import Any, Dict, List

from modules.reporter import Reporter
from modules.system_scanner import SystemScanner
from modules.web_scanner import WebScanner

_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Windows version detection
# ---------------------------------------------------------------------------

# Map minimum build numbers to human-readable marketing names (newest first).
_WIN_BUILDS = (
    (26100, "Windows 11 24H2"),
    (22631, "Windows 11 23H2"),
    (22621, "Windows 11 22H2"),
    (22000, "Windows 11 21H2"),
    (19045, "Windows 10 22H2"),
    (19044, "Windows 10 21H2"),
    (19043, "Windows 10 21H1"),
    (19042, "Windows 10 20H2"),
    (19041, "Windows 10 2004"),
    (18363, "Windows 10 1909"),
    (17763, "Windows Server 2019 / Windows 10 LTSC 2019"),
    (17134, "Windows 10 1803 (EOL)"),
    (16299, "Windows 10 1709 (EOL)"),
    (14393, "Windows Server 2016 / Windows 10 LTSB 2016 (EOL)"),
)


def _detect_windows() -> Dict[str, Any]:
    """
    Return a dict with windows_name, windows_build, version, machine,
    and processor derived from platform module.
    """
    raw_ver = platform.version()       # e.g. "10.0.22621"
    release = platform.release()       # "10" or "11"

    try:
        build = int(raw_ver.split(".")[2])
    except (IndexError, ValueError):
        build = 0

    name = f"Windows {release}"
    for min_build, label in _WIN_BUILDS:
        if build >= min_build:
            name = label
            break

    return {
        "windows_name":  name,
        "windows_build": build,
        "version":       raw_ver,
        "machine":       platform.machine(),
        "processor":     platform.processor()[:80],
    }

# ---------------------------------------------------------------------------
# Admin detection
# ---------------------------------------------------------------------------

def _is_admin() -> bool:
    """Return True when the process is running with administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Default output path
# ---------------------------------------------------------------------------

def _default_output(web: bool = False, system: bool = False) -> str:
    parts = []
    if web:
        parts.append("web")
    if system:
        parts.append("system")
    tag = "_".join(parts) if parts else "scan"
    return f"report_{tag}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="defensescan",
        description=(
            f"DefenseScan v{_VERSION} - OWASP-aligned Defensive Security Scanner\n"
            "Passive, non-destructive analysis for Windows systems and web targets."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --web https://example.com
  python main.py --system
  python main.py --web https://example.com --system
  python main.py --web https://example.com --output scan.json --threads 10 --timeout 15
  python main.py --system --verbose
  python main.py --web https://example.com --no-color > scan.txt
        """,
    )

    targets = parser.add_argument_group("Scan targets")
    targets.add_argument(
        "--web",
        metavar="URL",
        help="Target URL for web vulnerability scan (HTTP or HTTPS)",
    )
    targets.add_argument(
        "--system",
        action="store_true",
        help="Run Windows system security scan (administrator rights recommended)",
    )

    opts = parser.add_argument_group("Options")
    opts.add_argument(
        "--output",
        metavar="FILE",
        help="JSON report output path (default: report_YYYYMMDD_HHMMSS.json)",
    )
    opts.add_argument(
        "--threads",
        metavar="N",
        type=int,
        default=5,
        help="Concurrent worker threads for web scan (default: 5, max: 50)",
    )
    opts.add_argument(
        "--timeout",
        metavar="SEC",
        type=int,
        default=10,
        help="HTTP request timeout in seconds (default: 10)",
    )
    opts.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show all findings including informational results and full detail",
    )
    opts.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colour output (use when redirecting to a file)",
    )

    return parser

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_args(args: argparse.Namespace, reporter: Reporter) -> None:
    """Check argument constraints and exit with a clear message on failure."""
    if not args.web and not args.system:
        print(reporter.error("스캔 대상을 지정하세요: --web URL 또는 --system (또는 둘 다)"))
        sys.exit(1)

    if args.system and platform.system() != "Windows":
        print(reporter.error("--system 스캔은 Windows에서만 지원됩니다."))
        sys.exit(1)

    if not (1 <= args.threads <= 50):
        print(reporter.error("--threads는 1에서 50 사이의 값이어야 합니다."))
        sys.exit(1)

    if not (1 <= args.timeout <= 300):
        print(reporter.error("--timeout은 1에서 300초 사이의 값이어야 합니다."))
        sys.exit(1)

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = _build_parser()
    args   = parser.parse_args()

    # Reporter is created early so we can use its colour helpers in error messages.
    reporter = Reporter(use_color=not args.no_color, verbose=args.verbose)

    _validate_args(args, reporter)

    # ---- Platform / privilege detection ----
    win_info: Dict[str, Any] = {}
    if platform.system() == "Windows":
        win_info = _detect_windows()

    admin = _is_admin()

    # ---- Banner ----
    targets: List[str] = []
    if args.web:
        targets.append(args.web)
    if args.system:
        targets.append("Windows 시스템")

    reporter.print_banner(
        admin=admin,
        windows_name=win_info.get("windows_name", ""),
        windows_build=win_info.get("windows_build", 0),
        targets=targets,
        threads=args.threads,
        timeout=args.timeout,
    )

    # Warn about limited results without admin rights (system scan only)
    if args.system and not admin:
        print(reporter.warn(
            "관리자 권한 없이 시스템 스캔 중 — "
            "프로세스 경로, 다른 사용자의 네트워크 연결, 일부 레지스트리 키에 접근할 수 없습니다. "
            "완전한 결과를 위해 관리자 권한으로 다시 실행하세요."
        ))
        print()

    # ---- Run scans ----
    scan_start   = time.monotonic()
    all_findings: List[Dict[str, Any]] = []
    web_count    = 0
    sys_count    = 0

    if args.web:
        print(reporter.info(f"웹 스캔 시작 → {args.web}"))
        web_scanner = WebScanner(
            timeout=args.timeout,
            verbose=args.verbose,
            max_workers=args.threads,
        )
        web_findings = web_scanner.scan(args.web)
        all_findings.extend(web_findings)
        web_count = len(web_findings)
        reporter.print_section_results(web_findings, f"웹(WEB) 스캔  {args.web}")
        print(reporter.info(
            f"웹 스캔 완료 — 총 {web_count}개 항목 "
            f"(조치 필요: {sum(1 for f in web_findings if f.get('risk_level','Info') != 'Info')}개)"
        ))

    if args.system:
        print(reporter.info("Windows 시스템 스캔 시작 …"))
        sys_scanner = SystemScanner(is_admin=admin, verbose=args.verbose)
        sys_findings = sys_scanner.scan()
        all_findings.extend(sys_findings)
        sys_count = len(sys_findings)
        reporter.print_section_results(
            sys_findings, "시스템(SYSTEM) 스캔  Windows 보안 진단"
        )
        print(reporter.info(
            f"시스템 스캔 완료 — 총 {sys_count}개 항목 "
            f"(조치 필요: {sum(1 for f in sys_findings if f.get('risk_level','Info') != 'Info')}개)"
        ))

    # ---- Combined note (both modules) ----
    if args.web and args.system:
        actionable_total = sum(
            1 for f in all_findings if f.get("risk_level", "Info") != "Info"
        )
        print(f"\n{reporter.info(f'통합 결과: 웹 {web_count}개 + 시스템 {sys_count}개 항목 (조치 필요: {actionable_total}개)')}")

    scan_duration = time.monotonic() - scan_start

    # ---- Top risks + summary ----
    reporter.print_top_risks(all_findings, n=5)
    reporter.print_summary(all_findings, duration_s=scan_duration)

    # ---- JSON report (always written; default name includes timestamp) ----
    output_path = args.output or _default_output(web=bool(args.web), system=args.system)
    modules_run: List[str] = []
    if args.web:
        modules_run.append("web")
    if args.system:
        modules_run.append("system")

    meta: Dict[str, Any] = {
        "modules_run":  modules_run,
        "web_target":   args.web or "",
        "threads":      args.threads,
        "timeout":      args.timeout,
        "admin_mode":   admin,
        "verbose":      args.verbose,
        "duration_s":   round(scan_duration, 2),
        **win_info,
    }

    try:
        reporter.save_json(all_findings, output_path, meta=meta)
        print(f"\n{reporter.success(f'JSON 보고서 저장 완료 → {output_path}')}")
    except OSError as exc:
        print(reporter.error(f"JSON 보고서를 '{output_path}'에 저장할 수 없습니다: {exc}"))
        sys.exit(1)


if __name__ == "__main__":
    main()
