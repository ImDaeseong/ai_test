"""
Reporter — risk-level colour-coded console output and structured JSON report.

Colour scheme:
  Critical → bright RED      (\033[91m)
  High     → ORANGE          (\033[33m  — dark yellow, renders orange in most terminals)
  Medium   → YELLOW          (\033[93m  — bright yellow)
  Low      → CYAN            (\033[96m  — bright cyan)
  Info     → WHITE           (\033[97m  — bright white)

Uses colorama for cross-platform ANSI support on Windows 10+.
Falls back to raw ANSI + manual VT100 enable when colorama is absent.
"""

import datetime
import json
import platform
import socket
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
    except Exception:
        pass

try:
    from colorama import Fore, Style, init as _colorama_init
    _colorama_init(autoreset=False, strip=False)
    _COLORAMA = True
except ImportError:
    _COLORAMA = False

# ---------------------------------------------------------------------------
# ANSI colour primitives
# ---------------------------------------------------------------------------

def _raw(code: str) -> str:
    return f"\033[{code}m"


if _COLORAMA:
    _R_CRITICAL = Fore.LIGHTRED_EX        # \033[91m  bright red
    _R_HIGH     = Fore.YELLOW             # \033[33m  dark yellow / orange
    _R_MEDIUM   = Fore.LIGHTYELLOW_EX     # \033[93m  bright yellow
    _R_LOW      = Fore.LIGHTCYAN_EX       # \033[96m  bright cyan
    _R_INFO     = Fore.LIGHTWHITE_EX      # \033[97m  bright white
    _R_GREEN    = Fore.LIGHTGREEN_EX      # \033[92m
    _R_BLUE     = Fore.LIGHTBLUE_EX       # \033[94m
    _R_GRAY     = Fore.WHITE              # \033[37m  muted white
    _R_BOLD     = Style.BRIGHT
    _R_RESET    = Style.RESET_ALL
else:
    _R_CRITICAL = _raw("91")
    _R_HIGH     = _raw("33")
    _R_MEDIUM   = _raw("93")
    _R_LOW      = _raw("96")
    _R_INFO     = _raw("97")
    _R_GREEN    = _raw("92")
    _R_BLUE     = _raw("94")
    _R_GRAY     = _raw("37")
    _R_BOLD     = _raw("1")
    _R_RESET    = _raw("0")

# Risk level → colour string
_RISK_COLOR: Dict[str, str] = {
    "Critical": _R_CRITICAL,
    "High":     _R_HIGH,
    "Medium":   _R_MEDIUM,
    "Low":      _R_LOW,
    "Info":     _R_INFO,
}

# Finding status → colour string
_STATUS_COLOR: Dict[str, str] = {
    "FAIL":  _R_CRITICAL,
    "WARN":  _R_MEDIUM,
    "PASS":  _R_GREEN,
    "INFO":  _R_INFO,
    "SKIP":  _R_GRAY,
    "ERROR": _R_CRITICAL,
}

_RISK_ORDER = ["Critical", "High", "Medium", "Low", "Info"]

_COL = 68
_INDENT = " " * 24

_RISK_KO: Dict[str, str] = {
    "Critical": "Critical",
    "High":     "High",
    "Medium":   "Medium",
    "Low":      "Low",
    "Info":     "Info",
}
_RISK_ICON = {
    "Critical": "!!!",
    "High":     "!! ",
    "Medium":   " ! ",
    "Low":      " - ",
    "Info":     "   ",
}
_STATUS_TEXT = {
    "FAIL":  "FAIL",
    "WARN":  "WARN",
    "PASS":  "PASS",
    "INFO":  "INFO",
    "SKIP":  "SKIP",
    "ERROR": "ERROR",
}
_SEP_H = "=" * _COL
_SEP_L = "-" * _COL

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _risk_rank(f: Dict[str, Any]) -> int:
    """Sort key: lower number = higher severity."""
    rl = f.get("risk_level", "")
    if rl in _RISK_ORDER:
        return _RISK_ORDER.index(rl)
    sev = f.get("severity", "INFO").title()
    try:
        return _RISK_ORDER.index(sev)
    except ValueError:
        return len(_RISK_ORDER)


def _pct(n: int, of: int) -> str:
    return f"{round(100 * n / of):3d}%" if of > 0 else "  0%"


def _bar(n: int, of: int, width: int = 22) -> str:
    if of <= 0 or n <= 0:
        return "-" * width
    filled = max(1, round((n / of) * width))
    return "#" * filled + "-" * (width - filled)


def _safe_hostname() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


def _split_detail(combined: str) -> tuple:
    """
    Separate the combined 'detail\\n  Recommendation: ...' string
    that to_report() produces back into (main_detail, recommendation).
    """
    marker = "\n  Recommendation:"
    if marker in combined:
        parts = combined.split(marker, 1)
        return parts[0].strip(), parts[1].strip()
    return combined.strip(), ""


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------

class Reporter:
    """
    Renders DefenseScan findings to the console and/or a JSON file.

    print_banner()          — scan header with platform / target info
    print_section_results() — per-module finding list
    print_top_risks()       — top-N cross-module risk summary
    print_summary()         — risk distribution chart + verdict
    save_json()             — full structured JSON report
    """

    def __init__(self, use_color: bool = True, verbose: bool = False) -> None:
        self.verbose   = verbose
        self.use_color = use_color and self._can_color()

    # ------------------------------------------------------------------
    # Colour support detection
    # ------------------------------------------------------------------

    @staticmethod
    def _can_color() -> bool:
        """Enable Windows 10 VT100 processing; return True if ANSI is usable."""
        _platform: str = sys.platform
        if _platform != "win32":
            return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        try:
            import ctypes
            kernel = ctypes.windll.kernel32
            handle = kernel.GetStdHandle(-11)          # STD_OUTPUT_HANDLE
            mode   = ctypes.c_ulong()
            kernel.GetConsoleMode(handle, ctypes.byref(mode))
            kernel.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VT_PROCESSING
            return True
        except Exception:
            return _COLORAMA   # colorama can still strip/translate codes

    # ------------------------------------------------------------------
    # Primitive colouriser
    # ------------------------------------------------------------------

    def _c(self, color: str, text: str) -> str:
        if not self.use_color:
            return text
        return f"{color}{text}{_R_RESET}"

    def _bold(self, text: str) -> str:
        return self._c(_R_BOLD, text)

    # ------------------------------------------------------------------
    # Public utility: formatted status strings for main.py
    # ------------------------------------------------------------------

    def warn(self, msg: str) -> str:
        return self._c(_R_HIGH, f"[경고] {msg}")

    def info(self, msg: str) -> str:
        return self._c(_R_BLUE, f"[*] {msg}")

    def success(self, msg: str) -> str:
        return self._c(_R_GREEN, f"[+] {msg}")

    def error(self, msg: str) -> str:
        return self._c(_R_CRITICAL, f"[!] {msg}")

    # ------------------------------------------------------------------
    # Banner
    # ------------------------------------------------------------------

    def print_banner(
        self,
        *,
        admin:          bool            = False,
        windows_name:   str             = "",
        windows_build:  int             = 0,
        targets:        Optional[List[str]] = None,
        threads:        int             = 5,
        timeout:        int             = 10,
    ) -> None:
        now      = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        platform_str = windows_name or f"{platform.system()} {platform.release()}"
        build_str    = f"  (Build {windows_build})" if windows_build else ""
        priv_str     = (
            self._c(_R_GREEN, "관리자 (전체 스캔 가능)")
            if admin else
            self._c(_R_HIGH, "일반 사용자  ← 스캔 범위 제한됨")
        )
        target_str = ", ".join(targets) if targets else "—"

        # 한국어 라벨: 각 글자가 터미널에서 2칸을 차지하므로 :<7 로 표시 너비 11칸 맞춤
        print("\n" + self._c(_R_BLUE, _SEP_H))
        print(self._bold("  DefenseScan v1.0  —  보안 취약점 스캐너"))
        print(self._c(_R_BLUE,
              "  OWASP Top 10 기반  │  수동 분석  │  시스템 무손상"))
        print(self._c(_R_BLUE, _SEP_H))
        print(f"  {'시작 시각':<7} {now}")
        print(f"  {'운영체제':<7} "
              f"{self._c(_R_INFO, platform_str + build_str)}")
        print(f"  {'권한 레벨':<7} {priv_str}")
        print(f"  {'스캔 대상':<7} {self._c(_R_INFO, target_str)}")
        print(f"  {'스레드':<8} {threads}   "
              f"제한시간 {timeout}초")
        print(self._c(_R_BLUE, _SEP_H) + "\n")

    # ------------------------------------------------------------------
    # Section results
    # ------------------------------------------------------------------

    def print_section_results(
        self, findings: List[Dict[str, Any]], title: str
    ) -> None:
        """
        Print findings for one scan module.
        Non-verbose: skips Info-level findings and truncates detail.
        Verbose:     shows every finding with full detail.
        """
        actionable = [f for f in findings
                      if f.get("risk_level", "Info") != "Info"]
        info_only  = len(findings) - len(actionable)
        display    = findings if self.verbose else actionable

        print(f"\n{self._c(_R_BOLD, _SEP_L)}")
        header_line = f"  {title}"
        if findings:
            counts_str = (
                f"  ({len(actionable)}개 조치 필요"
                + (f", {info_only}개 정보성 항목 숨김" if info_only and not self.verbose else "")
                + ")"
            )
            print(self._bold(header_line))
            print(self._c(_R_GRAY, counts_str))
        else:
            print(self._bold(header_line))
        print(self._c(_R_BLUE, _SEP_L))

        if not findings:
            print(f"  {self._c(_R_GRAY, '검출된 항목이 없습니다.')}")
            return

        if not display:
            print(f"  {self._c(_R_GREEN, '✓  이 섹션에서 조치가 필요한 항목이 없습니다.')}")
            return

        for f in sorted(display, key=_risk_rank):
            self._print_finding(f)

    def _print_finding(self, f: Dict[str, Any]) -> None:
        rl     = f.get("risk_level", "Info")
        status = f.get("status", "INFO")
        title  = f.get("title") or f.get("check", "Unknown")
        owasp  = f.get("owasp", "")
        combined_detail = f.get("detail", "")

        main_detail, recommendation = _split_detail(combined_detail)

        risk_clr   = _RISK_COLOR.get(rl, _R_INFO)
        status_clr = _STATUS_COLOR.get(status, _R_INFO)

        # 한국어 위험 등급: 2글자(표시 4칸) + 공백 4칸 = 표시 8칸
        ko_rl = _RISK_KO.get(rl, rl)
        icon  = self._c(risk_clr,   f"[{_RISK_ICON.get(rl, '   ')}]")
        badge = self._c(status_clr, f"[{_STATUS_TEXT.get(status, '오류')}]")
        label = self._c(risk_clr,   ko_rl + "    ")

        print(f"\n  {icon} {label} {badge}  {title}")

        if main_detail:
            lines     = main_detail.splitlines()
            max_lines = len(lines) if self.verbose else min(2, len(lines))
            for line in lines[:max_lines]:
                shown = line if self.verbose else (line[:100] + "…" if len(line) > 100 else line)
                print(f"{_INDENT}{self._c(_R_GRAY, shown)}")
            if not self.verbose and len(lines) > 2:
                print(f"{_INDENT}{self._c(_R_GRAY, f'(+{len(lines)-2}줄 생략 — 전체 내용은 --verbose 옵션 사용)')}")

        if self.verbose:
            if recommendation:
                print(f"{_INDENT}{self._c(_R_BLUE, '→ ' + recommendation)}")
            evidence = f.get("evidence", "")
            if evidence:
                for ev_line in evidence.splitlines():
                    print(f"{_INDENT}{self._c(_R_GRAY, '  ' + ev_line)}")
            if owasp and owasp != "N/A":
                print(f"{_INDENT}{self._c(_R_GRAY, owasp)}")

    # ------------------------------------------------------------------
    # Top N risks
    # ------------------------------------------------------------------

    def print_top_risks(
        self, findings: List[Dict[str, Any]], n: int = 5
    ) -> None:
        """
        Display the N highest-risk findings across all scan modules,
        labelled with their source category [web] / [system].
        """
        actionable = [f for f in findings
                      if f.get("risk_level", "Info") != "Info"]
        top = sorted(actionable, key=_risk_rank)[:n]

        if not top:
            return

        print(f"\n{self._c(_R_BOLD, _SEP_H)}")
        print(self._bold(f"  상위 {n}개 최고위험 항목"))
        print(self._c(_R_BLUE, _SEP_H))

        for i, f in enumerate(top, start=1):
            rl    = f.get("risk_level", "Info")
            cat   = f.get("category", "")
            title = f.get("title") or f.get("check", "Unknown")
            clr   = _RISK_COLOR.get(rl, _R_INFO)
            cat_s = self._c(_R_GRAY, f"[{cat:<6}]") if cat else " " * 8

            num_s  = self._bold(f"  #{i}")
            # 한국어 위험 등급: 2글자(표시 4칸) + 공백 5칸 = 표시 9칸
            ko_rl  = _RISK_KO.get(rl, rl)
            risk_s = self._c(clr, ko_rl + "     ")
            title_s = title[:(_COL - 32)] + ("…" if len(title) > _COL - 32 else "")

            print(f"{num_s}  {risk_s}  {cat_s}  {title_s}")

        print(self._c(_R_BLUE, _SEP_H))

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def print_summary(
        self,
        findings: List[Dict[str, Any]],
        duration_s: Optional[float] = None,
    ) -> None:
        """
        Risk distribution bar chart, status breakdown, and overall verdict.
        """
        counts:   Dict[str, int] = {r: 0 for r in _RISK_ORDER}
        statuses: Dict[str, int] = {
            "FAIL": 0, "WARN": 0, "PASS": 0, "SKIP": 0, "INFO": 0, "ERROR": 0,
        }

        for f in findings:
            rl = f.get("risk_level", "Info")
            st = f.get("status", "INFO")
            if rl in counts:
                counts[rl] += 1
            if st in statuses:
                statuses[st] += 1

        actionable = sum(counts[r] for r in _RISK_ORDER[:-1])   # exclude Info
        total      = len(findings)

        dur_s = f"  소요 시간: {duration_s:.1f}초" if duration_s is not None else ""

        print(f"\n{self._c(_R_BOLD, _SEP_H)}")
        print(f"  {self._bold('스캔 결과 요약')}{self._c(_R_GRAY, dur_s)}")
        print(self._c(_R_BLUE, _SEP_H))

        # ---- 위험 등급 분포 차트 ----
        print(f"\n  {self._c(_R_BOLD, '위험 등급 분포')}")
        print(f"  {self._c(_R_GRAY, _SEP_L[:50])}")

        # 막대 길이는 가장 많은 항목 수 기준으로 상대적으로 결정
        max_count = max((counts[r] for r in _RISK_ORDER[:-1]), default=1) or 1

        for rl in _RISK_ORDER[:-1]:
            n    = counts[rl]
            clr  = _RISK_COLOR[rl]
            bar  = self._c(clr, _bar(n, max_count))
            pct  = _pct(n, max(actionable, 1))

            flag = ""
            if rl in ("Critical", "High") and n > 0:
                flag = self._c(_R_CRITICAL, "  ← 즉시 조치 필요")

            # 한국어 위험 등급: 2글자(표시 4칸) + 공백 6칸 = 표시 10칸
            ko_rl = _RISK_KO.get(rl, rl)
            ko_rl_padded = ko_rl + " " * 6
            print(f"  {self._c(clr, ko_rl_padded)} {n:>4}  {bar}  {pct}{flag}")

        info_n = counts["Info"]
        # "정보" 2글자(표시 4칸) + 공백 6칸 = 표시 10칸
        info_line = f"정보       {info_n:>4}  (참고용 항목, 위험 없음)"
        print(f"  {self._c(_R_GRAY, info_line)}")
        print(f"  {self._c(_R_GRAY, _SEP_L[:50])}")

        # ---- 상태별 통계 ----
        print(
            f"\n  정상: {self._c(_R_GREEN,    str(statuses['PASS'])  )}"
            f"   실패: {self._c(_R_CRITICAL,  str(statuses['FAIL'])  )}"
            f"   경고: {self._c(_R_MEDIUM,    str(statuses['WARN'])  )}"
            f"   생략: {self._c(_R_GRAY,      str(statuses['SKIP'])  )}"
        )
        print(
            f"\n  조치 필요 항목: "
            f"{self._c(_R_BOLD, str(actionable))}개 / 전체 {total}개"
        )

        # ---- 최종 판정 ----
        print()
        if counts["Critical"] > 0:
            print(f"  {self._c(_R_CRITICAL, '█  위험(Critical) 문제 발견 — 즉시 조치가 필요합니다!')}")
        elif counts["High"] > 0:
            print(f"  {self._c(_R_HIGH,     '▲  높음(High) 심각도 문제 발견 — 신속히 조치하세요.')}")
        elif counts["Medium"] > 0:
            print(f"  {self._c(_R_MEDIUM,   '●  중간(Medium) 심각도 문제 발견 — 조치 일정을 수립하세요.')}")
        elif counts["Low"] > 0:
            print(f"  {self._c(_R_LOW,      '◆  낮음(Low) 심각도 문제 발견 — 가능한 시점에 검토하세요.')}")
        else:
            print(f"  {self._c(_R_GREEN,    '✓  심각한 문제가 없습니다. 보안 상태가 양호합니다.')}")

        print(f"\n{self._c(_R_BLUE, _SEP_H)}")

    # ------------------------------------------------------------------
    # JSON report
    # ------------------------------------------------------------------

    def save_json(
        self,
        findings:   List[Dict[str, Any]],
        path:       str,
        meta:       Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Write a fully structured JSON report.

        Schema:
          tool, version, scan_id, timestamp, duration_seconds,
          platform, scan_config, summary { by_risk_level, by_status,
          top_5_findings }, findings[]
        """
        counts:   Dict[str, int] = {r: 0 for r in _RISK_ORDER}
        statuses: Dict[str, int] = {
            "FAIL": 0, "WARN": 0, "PASS": 0, "SKIP": 0, "INFO": 0,
        }

        cleaned: List[Dict] = []
        for f in sorted(findings, key=_risk_rank):
            rl = f.get("risk_level", "Info")
            st = f.get("status", "INFO")
            if rl in counts:
                counts[rl] += 1
            if st in statuses:
                statuses[st] += 1
            cleaned.append(self._clean_for_json(f))

        actionable = sum(counts[r] for r in _RISK_ORDER[:-1])

        # Top 5 actionable findings (clean format)
        top5 = [
            self._clean_for_json(f)
            for f in sorted(findings, key=_risk_rank)
            if f.get("risk_level", "Info") != "Info"
        ][:5]

        meta = meta or {}
        now = datetime.datetime.now()
        report: Dict[str, Any] = {
            "tool":     "DefenseScan",
            "version":  "1.0",
            "scan_id":  now.strftime("ds_%Y%m%d_%H%M%S"),
            "timestamp": now.isoformat(),
            "platform": {
                "system":   platform.system(),
                "release":  platform.release(),
                "version":  platform.version(),
                "name":     meta.get("windows_name", ""),
                "build":    meta.get("windows_build", 0),
                "machine":  platform.machine(),
                "hostname": _safe_hostname(),
            },
            "scan_config": {
                "modules_run":  meta.get("modules_run", []),
                "web_target":   meta.get("web_target", ""),
                "threads":      meta.get("threads", 5),
                "timeout":      meta.get("timeout", 10),
                "admin_mode":   meta.get("admin_mode", False),
                "verbose":      meta.get("verbose", False),
                "verify_tls":   meta.get("verify_tls", True),
                "allow_private_targets": meta.get("allow_private_targets", False),
                "duration_s":   meta.get("duration_s", 0),
            },
            "summary": {
                "total_findings":      len(findings),
                "actionable_findings": actionable,
                "by_risk_level": {k.lower(): v for k, v in counts.items()},
                "by_status":     statuses,
                "top_5_findings": top5,
            },
            "findings": cleaned,
        }

        output_path = Path(path)
        if output_path.exists() and output_path.is_dir():
            raise OSError(f"Output path is a directory: {output_path}")
        if output_path.parent and str(output_path.parent) != ".":
            output_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = output_path.with_name(output_path.name + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        tmp_path.replace(output_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_for_json(f: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produce a clean finding dict for JSON output.

        Separates detail from the recommendation that to_report() appended,
        keeps all extended fields, and drops the legacy combined 'detail' key.
        """
        main_detail, rec_from_detail = _split_detail(f.get("detail", ""))
        recommendation = f.get("recommendation") or rec_from_detail

        return {
            "category":       f.get("category", ""),
            "risk_level":     f.get("risk_level", ""),
            "title":          f.get("title") or f.get("check", ""),
            "detail":         main_detail,
            "recommendation": recommendation,
            "evidence":       f.get("evidence", ""),
            "owasp":          f.get("owasp", ""),
        }
