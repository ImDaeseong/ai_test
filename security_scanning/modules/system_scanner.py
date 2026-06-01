"""
Windows system security scanner — class-based, concurrent OWASP-aligned checks.
Targets Windows 10 / Windows 11 / Windows Server 2016+.

Architecture:
  Finding               — dataclass matching web_scanner.Finding interface
  _ProcessInfo          — snapshot of one running process (psutil attributes)
  _SystemSnapshot       — pre-gathered psutil data shared across all check classes
  BaseCheck             — abstract base class; all checks implement run()
  PortScanner           — listening ports, process mapping, malware port detection
  ProcessMonitor        — exe path analysis, spoofing detection, suspicious locations
  NetworkMonitor        — per-process connection analysis, foreign IPs, multi-IP flags
  StartupScanner        — registry Run keys + startup folder, signature checks
  SecuritySoftwareCheck — Windows Defender (Get-MpComputerStatus) + Firewall profiles
  FilePermissionChecker — icacls-based weak ACL detection on sensitive directories
  SystemScanner         — orchestrator: snapshot → concurrent checks → sorted dicts
"""

import ipaddress
import json
import os
import re
import subprocess
import platform
from abc import ABC, abstractmethod
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

try:
    import winreg
except ImportError:
    winreg = None

try:
    import psutil
    _PSUTIL_OK = True
except ImportError:
    _PSUTIL_OK = False

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

RISK_ORDER = ["Critical", "High", "Medium", "Low", "Info"]
_RISK_RANK: Dict[str, int] = {r: i for i, r in enumerate(RISK_ORDER)}

_RISK_TO_SEVERITY: Dict[str, str] = {
    "Critical": "CRITICAL", "High": "HIGH", "Medium": "MEDIUM",
    "Low":  "LOW",  "Info": "INFO",
}
_RISK_TO_STATUS: Dict[str, str] = {
    "Critical": "FAIL", "High": "FAIL", "Medium": "FAIL",
    "Low":  "WARN", "Info": "INFO",
}

# ---- Port tables ----

# Ports definitively associated with malware / RATs / worms
_MALWARE_PORTS: Dict[int, Tuple[str, str]] = {
    31337: ("Critical", "Back Orifice default port"),
    54321: ("Critical", "Back Orifice 2000 / common RAT"),
    12345: ("Critical", "NetBus RAT default port"),
    27374: ("Critical", "Sub7/SubSeven RAT default port"),
    1243:  ("High",     "Sub7 RAT alternate port"),
    4444:  ("Critical", "Metasploit default reverse shell handler"),
    1234:  ("High",     "Common Metasploit listener"),
    6666:  ("High",     "IRC botnet command-and-control"),
    6667:  ("High",     "IRC botnet command-and-control"),
    6668:  ("High",     "IRC botnet command-and-control"),
    6669:  ("High",     "IRC botnet command-and-control"),
    2745:  ("High",     "Bagle worm"),
    3127:  ("High",     "MyDoom worm"),
    5554:  ("High",     "Sasser worm"),
    9996:  ("High",     "Sasser / NetSky worm"),
    10080: ("High",     "MyDoom worm"),
    1337:  ("Medium",   "Common hacking/malware port"),
    7777:  ("Medium",   "Common backdoor port"),
    9999:  ("Medium",   "Common RAT/backdoor port"),
    65535: ("Medium",   "Commonly used by malware to avoid notice"),
    8888:  ("Medium",   "Common RAT/C2 port"),
    9090:  ("Medium",   "Common alternative C2 port"),
}

# Risky but legitimately used ports
_RISKY_PORTS: Dict[int, Tuple[str, str]] = {
    21:    ("High",     "FTP — transmits credentials in plaintext"),
    23:    ("Critical", "Telnet — completely unencrypted protocol"),
    25:    ("Medium",   "SMTP — ensure AUTH and TLS are enforced"),
    69:    ("High",     "TFTP — no authentication mechanism"),
    135:   ("Medium",   "RPC endpoint mapper — restrict via firewall"),
    137:   ("Medium",   "NetBIOS Name Service — leaks host info"),
    139:   ("Medium",   "NetBIOS Session Service — disable if not needed"),
    445:   ("High",     "SMB — verify patched against EternalBlue/MS17-010"),
    1433:  ("High",     "Microsoft SQL Server — restrict to trusted hosts"),
    1521:  ("High",     "Oracle Database — restrict to trusted hosts"),
    3306:  ("High",     "MySQL/MariaDB — restrict to localhost / trusted subnet"),
    3389:  ("High",     "RDP — ensure NLA enabled, restrict via firewall"),
    4899:  ("High",     "Radmin remote admin — verify legitimacy"),
    5432:  ("High",     "PostgreSQL — restrict to trusted hosts"),
    5900:  ("High",     "VNC — ensure strong authentication is configured"),
    5985:  ("Medium",   "WinRM HTTP (unencrypted) — prefer HTTPS port 5986"),
    5986:  ("Low",      "WinRM HTTPS — restrict to administrative hosts only"),
    6379:  ("Critical", "Redis — no authentication by default"),
    8080:  ("Low",      "HTTP alternate port — verify if intentional"),
    9200:  ("Critical", "Elasticsearch — unauthenticated by default"),
    27017: ("Critical", "MongoDB — unauthenticated by default"),
}

# ---- Process integrity tables ----

# Critical Windows processes and the only legitimate exe paths for each
_SYSTEM_PROCESS_PATHS: Dict[str, FrozenSet[str]] = {
    "svchost.exe":   frozenset({r"c:\windows\system32\svchost.exe"}),
    "lsass.exe":     frozenset({r"c:\windows\system32\lsass.exe"}),
    "csrss.exe":     frozenset({r"c:\windows\system32\csrss.exe"}),
    "winlogon.exe":  frozenset({r"c:\windows\system32\winlogon.exe"}),
    "explorer.exe":  frozenset({r"c:\windows\explorer.exe"}),
    "wininit.exe":   frozenset({r"c:\windows\system32\wininit.exe"}),
    "services.exe":  frozenset({r"c:\windows\system32\services.exe"}),
    "smss.exe":      frozenset({r"c:\windows\system32\smss.exe"}),
    "spoolsv.exe":   frozenset({r"c:\windows\system32\spoolsv.exe"}),
    "dwm.exe":       frozenset({r"c:\windows\system32\dwm.exe"}),
    "taskhostw.exe": frozenset({r"c:\windows\system32\taskhostw.exe"}),
    "userinit.exe":  frozenset({r"c:\windows\system32\userinit.exe",
                                r"c:\windows\syswow64\userinit.exe"}),
    "conhost.exe":   frozenset({r"c:\windows\system32\conhost.exe"}),
    "audiodg.exe":   frozenset({r"c:\windows\system32\audiodg.exe"}),
    "wscript.exe":   frozenset({r"c:\windows\system32\wscript.exe",
                                r"c:\windows\syswow64\wscript.exe"}),
    "cscript.exe":   frozenset({r"c:\windows\system32\cscript.exe",
                                r"c:\windows\syswow64\cscript.exe"}),
    "mshta.exe":     frozenset({r"c:\windows\system32\mshta.exe",
                                r"c:\windows\syswow64\mshta.exe"}),
    "regsvr32.exe":  frozenset({r"c:\windows\system32\regsvr32.exe",
                                r"c:\windows\syswow64\regsvr32.exe"}),
    "rundll32.exe":  frozenset({r"c:\windows\system32\rundll32.exe",
                                r"c:\windows\syswow64\rundll32.exe"}),
}

# Path substrings (lowercase) that indicate a suspicious executable location
_SUSPICIOUS_PATH_FRAGS: Tuple[str, ...] = (
    "\\temp\\",
    "\\tmp\\",
    "appdata\\local\\temp",
    "\\users\\public\\",
    "\\downloads\\",
    "\\windows\\temp\\",
)

# AppData\Roaming is suspicious for executables unless it belongs to a known app
_ROAMING_WHITELIST = re.compile(
    r"(?i)appdata\\roaming\\"
    r"(?:microsoft\\|adobe\\|mozilla\\|google\\|slack\\|microsoft\\teams\\"
    r"|discord\\|zoom\\|spotify\\|dropbox\\|1password\\|bitwarden\\|signal\\)",
)

# ---- Network analysis ----

# Processes that legitimately establish many concurrent outbound connections
_KNOWN_MULTI_CONN_PROCS: FrozenSet[str] = frozenset({
    "chrome.exe", "chromium.exe", "firefox.exe", "msedge.exe",
    "iexplore.exe", "opera.exe", "brave.exe", "vivaldi.exe",
    "svchost.exe", "lsass.exe", "services.exe",
    "onedrive.exe", "dropbox.exe", "googledrivefs.exe",
    "teams.exe", "slack.exe", "zoom.exe", "discord.exe",
    "outlook.exe", "thunderbird.exe", "skype.exe",
    "msmpeng.exe", "nissrv.exe", "securityhealthservice.exe",
    "wuauclt.exe", "wudfhost.exe",
    "microsoftedgeupdate.exe", "googleupdate.exe",
    "msiexec.exe", "searchindexer.exe",
})

_MULTI_IP_THRESHOLD = 10      # flag non-whitelisted process with > N distinct foreign IPs

# ---- Startup analysis ----

if winreg is not None:
    _AUTORUN_KEYS: Tuple[Tuple[int, str, str], ...] = (
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
         "HKLM\\Run"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
         "HKLM\\RunOnce"),
        (winreg.HKEY_CURRENT_USER,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
         "HKCU\\Run"),
        (winreg.HKEY_CURRENT_USER,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
         "HKCU\\RunOnce"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
         "HKLM\\Run (WOW64)"),
    )
else:
    _AUTORUN_KEYS = ()

_SUSPICIOUS_CMD = re.compile(
    r"(?i)"
    r"(powershell[^\s]*\s+.*-e(nc)?\s"           # Base64 encoded command
    r"|powershell[^\s]*\s+.*-w(indow)?\s*hidden"  # Hidden-window PS
    r"|cmd(\.exe)?\s+/c\s+\w+\.exe"              # cmd.exe launching binary
    r"|wscript|cscript"                            # Script hosts
    r"|mshta"                                      # HTA host (common LOLbin)
    r"|regsvr32[^\s]*\s+/s.*scrobj"               # COM scriptlet
    r"|certutil.*-decode"                          # Payload extraction
    r"|bitsadmin.*transfer"                        # BITS download
    r"|rundll32[^\s]*.*javascript:"               # Rundll32 JS
    r"|\\\\[a-z0-9._-]{1,32}\\)"                  # UNC path execution
)

# ---- File permission analysis ----

_PERM_DIRS: Tuple[Tuple[str, str], ...] = (
    (r"C:\Windows\Temp",     "Windows System Temp (C:\\Windows\\Temp)"),
    (r"C:\Temp",             "Root Temp Directory (C:\\Temp)"),
    (r"C:\ProgramData",      "ProgramData Directory"),
    (r"C:\Users\Public",     "Public User Directory"),
    (r"C:\Windows\System32", "Windows System32"),
    (r"C:\Windows",          "Windows Root Directory"),
)

# icacls permission flags indicating write capability
_WRITE_FLAGS: FrozenSet[str] = frozenset({"F", "M", "W", "WD", "AD"})

# Principals whose write access should trigger a finding
_HIGH_RISK_WRITE_PRINCIPALS   = ("everyone",)
_MEDIUM_RISK_WRITE_PRINCIPALS = (
    "authenticated users", "nt authority\\authenticated users",
    "builtin\\users",
)


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """
    Single scanner result — identical interface to web_scanner.Finding.
    to_report() returns a reporter-compatible dict with both the new extended
    fields and the legacy keys (severity, status, check, detail, owasp).
    """
    check:          str
    risk_level:     str   # Critical | High | Medium | Low | Info
    title:          str
    detail:         str
    recommendation: str
    evidence:       str
    owasp:          str = ""

    @property
    def rank(self) -> int:
        return _RISK_RANK.get(self.risk_level, len(RISK_ORDER))

    def to_report(self) -> Dict[str, Any]:
        display = self.detail
        if self.recommendation:
            display += f"\n  Recommendation: {self.recommendation}"
        return {
            # Legacy keys used by Reporter
            "category": "system",
            "check":    self.title,
            "severity": _RISK_TO_SEVERITY.get(self.risk_level, "INFO"),
            "status":   _RISK_TO_STATUS.get(self.risk_level,   "INFO"),
            "detail":   display,
            "owasp":    self.owasp,
            # Extended keys present in JSON report
            "risk_level":     self.risk_level,
            "title":          self.title,
            "recommendation": self.recommendation,
            "evidence":       self.evidence,
        }


# ---------------------------------------------------------------------------
# Process snapshot — gathered once, shared across all checks
# ---------------------------------------------------------------------------

@dataclass
class _ProcessInfo:
    pid:        int
    name:       str
    exe:        Optional[str]       # None = access denied
    status:     str
    memory_mb:  float
    username:   Optional[str]
    connections: List[Any] = field(default_factory=list)   # psutil conn namedtuples


@dataclass
class _SystemSnapshot:
    processes:   List[_ProcessInfo]
    connections: List[Any]          # all psutil net_connections
    is_admin:    bool
    os_build:    int

    # ------------------------------------------------------------------ derived views

    def _proc_by_pid(self) -> Dict[int, _ProcessInfo]:
        return {p.pid: p for p in self.processes}

    def listening(self) -> List[Tuple[int, Optional["_ProcessInfo"]]]:
        """Returns (local_port, process_or_None) for every LISTEN-state connection."""
        pbp = self._proc_by_pid()
        seen: Set[int] = set()
        result: List[Tuple[int, Optional[_ProcessInfo]]] = []
        for conn in self.connections:
            if conn.status == "LISTEN" and conn.laddr:
                port = conn.laddr.port
                if port not in seen:
                    seen.add(port)
                    result.append((port, pbp.get(conn.pid) if conn.pid else None))
        return result

    def established_by_proc(self) -> Dict[int, List[Any]]:
        """Returns pid → list of ESTABLISHED connections."""
        mapping: Dict[int, List[Any]] = defaultdict(list)
        for conn in self.connections:
            if conn.status == "ESTABLISHED" and conn.raddr and conn.pid:
                mapping[conn.pid].append(conn)
        return mapping


# ---------------------------------------------------------------------------
# BaseCheck
# ---------------------------------------------------------------------------

class BaseCheck(ABC):
    NAME: str = ""

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout

    @abstractmethod
    def run(self) -> List[Finding]:
        ...

    # -- helpers -------------------------------------------------------

    @staticmethod
    def _f(check: str, risk: str, title: str, detail: str,
           rec: str, evidence: str, owasp: str = "") -> Finding:
        return Finding(check=check, risk_level=risk, title=title,
                       detail=detail, recommendation=rec,
                       evidence=evidence, owasp=owasp)

    def _ps(self, script: str) -> Optional[str]:
        """Run a PowerShell one-liner; return stdout or None on any error."""
        try:
            r = subprocess.run(
                ["powershell", "-NonInteractive", "-NoProfile", "-Command", script],
                capture_output=True, text=True,
                timeout=self.timeout, encoding="utf-8", errors="replace",
            )
            return r.stdout.strip() or None
        except Exception:
            return None

    def _cmd(self, args: List[str]) -> Optional[str]:
        """Run a command-line tool; return stdout or None on any error."""
        try:
            r = subprocess.run(
                args, capture_output=True, text=True,
                timeout=self.timeout, encoding="utf-8", errors="replace",
            )
            return r.stdout.strip() or None
        except Exception:
            return None

    @staticmethod
    def _is_public_ip(ip_str: str) -> bool:
        if not ip_str:
            return False
        try:
            addr = ipaddress.ip_address(ip_str)
            return not (addr.is_private or addr.is_loopback or
                        addr.is_link_local or addr.is_multicast or
                        addr.is_unspecified or addr.is_reserved)
        except ValueError:
            return False

    @staticmethod
    def _is_suspicious_path(exe: Optional[str]) -> bool:
        if not exe:
            return False
        low = exe.lower()
        if any(frag in low for frag in _SUSPICIOUS_PATH_FRAGS):
            return True
        if "appdata\\roaming\\" in low and not _ROAMING_WHITELIST.search(low):
            return True
        return False


# ---------------------------------------------------------------------------
# Check 1 — Open Port Scanner
# ---------------------------------------------------------------------------

class PortScanner(BaseCheck):
    """
    Enumerates all TCP/UDP listening ports via psutil, maps each port
    to its owning process, and flags malware-associated or risky ports.
    """

    NAME = "Port Scanner"

    def __init__(self, snapshot: _SystemSnapshot, timeout: int = 15) -> None:
        super().__init__(timeout)
        self._snap = snapshot

    def run(self) -> List[Finding]:
        if not _PSUTIL_OK:
            return [self._f(self.NAME, "Info", "psutil Not Installed",
                            "psutil is required for port scanning. Install it with: pip install psutil",
                            "pip install psutil", "Import failed", "N/A")]

        findings: List[Finding] = []
        listening = self._snap.listening()

        if not listening:
            findings.append(self._f(
                self.NAME, "Info", "No Listening Ports Detected",
                "No listening TCP/UDP ports were detected. "
                "(Limited results without administrator privileges.)",
                "", "psutil.net_connections() returned no LISTEN entries", "N/A",
            ))
            return findings

        port_list = sorted(p for p, _ in listening)
        findings.append(self._f(
            self.NAME, "Info",
            f"Listening Ports Summary ({len(port_list)} ports)",
            f"Active listening ports detected on this host.",
            "", f"Ports: {', '.join(str(p) for p in port_list[:60])}"
                + ("…" if len(port_list) > 60 else ""),
            "N/A",
        ))

        for port, proc in listening:
            proc_str = self._proc_label(proc)
            findings.extend(self._classify_port(port, proc_str))

        return findings

    def _proc_label(self, proc: Optional[_ProcessInfo]) -> str:
        if proc is None:
            return "unknown process (access denied or no PID)"
        exe = proc.exe or "path unknown"
        return f"{proc.name} (PID {proc.pid}, {exe})"

    def _classify_port(self, port: int, proc_str: str) -> List[Finding]:
        findings: List[Finding] = []

        if port in _MALWARE_PORTS:
            risk, description = _MALWARE_PORTS[port]
            findings.append(self._f(
                self.NAME, risk,
                f"Malware-Associated Port Listening: {port}",
                f"Port {port} ({description}) is open and listening. "
                "This port is strongly associated with malware, RATs, or backdoors. "
                "Investigate the owning process immediately.",
                f"Terminate the process if unauthorized, then run a full malware scan. "
                f"Block port {port} at the firewall.",
                f"Port {port} — {proc_str}",
                "A05:2021 - Security Misconfiguration",
            ))
            return findings

        if port in _RISKY_PORTS:
            risk, description = _RISKY_PORTS[port]
            findings.append(self._f(
                self.NAME, risk,
                f"Risky Port Listening: {port} ({description.split('—')[0].strip()})",
                f"Port {port} is open: {description}. "
                "Verify this service is intentionally exposed and access is restricted.",
                f"If not required externally, add a firewall rule blocking port {port}. "
                "If the service must be accessible, enforce authentication and encryption.",
                f"Port {port} — {proc_str}",
                "A05:2021 - Security Misconfiguration",
            ))

        return findings


# ---------------------------------------------------------------------------
# Check 2 — Process Monitor
# ---------------------------------------------------------------------------

class ProcessMonitor(BaseCheck):
    """
    Analyses running processes for:
      - Name-spoofing: known system binary running from an unexpected path
      - Suspicious exe locations: Temp, AppData, Downloads, Public
      - Processes making outbound connections from suspicious paths
    """

    NAME = "Process Monitor"

    def __init__(self, snapshot: _SystemSnapshot, timeout: int = 15) -> None:
        super().__init__(timeout)
        self._snap = snapshot

    def run(self) -> List[Finding]:
        if not _PSUTIL_OK:
            return []

        findings: List[Finding] = []
        established = self._snap.established_by_proc()

        findings.append(self._f(
            self.NAME, "Info",
            f"Running Processes ({len(self._snap.processes)} total)",
            "Total number of processes enumerated on this host.",
            "",
            f"{len(self._snap.processes)} processes (some may be inaccessible without admin rights)",
            "N/A",
        ))

        for proc in self._snap.processes:
            findings.extend(self._check_spoofing(proc))
            findings.extend(self._check_suspicious_path(proc, established))

        return findings

    def _check_spoofing(self, proc: _ProcessInfo) -> List[Finding]:
        name_lc = proc.name.lower()
        expected = _SYSTEM_PROCESS_PATHS.get(name_lc)
        if not expected or not proc.exe:
            return []

        exe_lc = proc.exe.lower().rstrip()
        if exe_lc not in expected:
            return [self._f(
                self.NAME, "Critical",
                f"Process Name Spoofing Detected: {proc.name}",
                f"'{proc.name}' (PID {proc.pid}) is running from an unexpected path. "
                f"Legitimate '{proc.name}' runs from: {', '.join(sorted(expected))}. "
                "This is a classic masquerading technique used by malware to hide as a "
                "trusted Windows system process.",
                "Terminate the process immediately if not authorized. Run a full malware "
                "scan. Check startup/scheduled tasks for persistence mechanisms.",
                f"Process: {proc.name} | PID: {proc.pid} | Actual path: {proc.exe}",
                "A08:2021 - Software and Data Integrity Failures",
            )]
        return []

    def _check_suspicious_path(
        self,
        proc: _ProcessInfo,
        established: Dict[int, List[Any]],
    ) -> List[Finding]:
        if not self._is_suspicious_path(proc.exe):
            return []

        has_connections = bool(established.get(proc.pid))
        risk = "High" if has_connections else "Medium"

        conn_detail = ""
        if has_connections:
            conns = established[proc.pid]
            remote_ips = {c.raddr.ip for c in conns if c.raddr}
            conn_detail = (
                f" It also has {len(conns)} active network connection(s) to: "
                f"{', '.join(list(remote_ips)[:5])}"
                + (" …" if len(remote_ips) > 5 else "") + "."
            )

        return [self._f(
            self.NAME, risk,
            f"Process Running from Suspicious Path: {proc.name}",
            f"'{proc.name}' (PID {proc.pid}) is executing from '{proc.exe}', "
            f"which is not a standard installation location.{conn_detail} "
            "Legitimate software rarely runs from Temp, Downloads, or Public directories. "
            "This is a common pattern for malware droppers and post-exploitation tools.",
            "Investigate the process origin. Check if any scheduled task or startup entry "
            "is responsible. Run Get-AuthenticodeSignature on the executable.",
            f"Process: {proc.name} | PID: {proc.pid} | Path: {proc.exe} "
            f"| Memory: {proc.memory_mb:.1f} MB | Network: {'Yes' if has_connections else 'No'}",
            "A08:2021 - Software and Data Integrity Failures",
        )]


# ---------------------------------------------------------------------------
# Check 3 — Network Connection Monitor
# ---------------------------------------------------------------------------

class NetworkMonitor(BaseCheck):
    """
    Analyses ESTABLISHED TCP connections per process:
      - Flags connections to remote malware-associated ports
      - Flags non-whitelisted processes connecting to many distinct foreign IPs
      - Flags processes from suspicious paths with any outbound public-IP connection
      - Reports all active connections as an Info summary
    """

    NAME = "Network Monitor"

    def __init__(self, snapshot: _SystemSnapshot, timeout: int = 15) -> None:
        super().__init__(timeout)
        self._snap = snapshot

    def run(self) -> List[Finding]:
        if not _PSUTIL_OK:
            return []

        established = self._snap.established_by_proc()
        if not established:
            return [self._f(
                self.NAME, "Info",
                "No Established Outbound Connections",
                "No active ESTABLISHED TCP connections were detected. "
                "(Results may be incomplete without administrator privileges.)",
                "", "psutil ESTABLISHED connections: 0", "N/A",
            )]

        findings: List[Finding] = []
        pbp = self._snap._proc_by_pid()
        total_conns = sum(len(v) for v in established.values())

        findings.append(self._f(
            self.NAME, "Info",
            f"Active Network Connections ({total_conns} established)",
            f"{total_conns} ESTABLISHED TCP connections across "
            f"{len(established)} process(es).",
            "", f"{len(established)} processes with active connections", "N/A",
        ))

        for pid, conns in established.items():
            proc = pbp.get(pid)
            if not proc:
                continue
            findings.extend(self._analyse_process_connections(proc, conns))

        return findings

    def _analyse_process_connections(
        self, proc: _ProcessInfo, conns: List[Any]
    ) -> List[Finding]:
        findings: List[Finding] = []
        name_lc = proc.name.lower()

        foreign_ips: Set[str] = set()
        malware_port_hits: List[str] = []

        for conn in conns:
            if not conn.raddr:
                continue
            rip, rport = conn.raddr.ip, conn.raddr.port

            # Flag connection to a malware-associated remote port
            if rport in _MALWARE_PORTS:
                _, desc = _MALWARE_PORTS[rport]
                malware_port_hits.append(f"{rip}:{rport} ({desc})")

            if self._is_public_ip(rip):
                foreign_ips.add(rip)

        # Process making connection to a malware port
        if malware_port_hits:
            findings.append(self._f(
                self.NAME, "Critical",
                f"Process Connected to Malware-Associated Port: {proc.name}",
                f"'{proc.name}' (PID {proc.pid}) has ESTABLISHED connection(s) to "
                "remote port(s) strongly associated with malware C2 or RAT activity.",
                "Isolate this host immediately. Terminate the process. "
                "Capture memory and disk for forensic analysis.",
                f"Process: {proc.name} | PID: {proc.pid}\n"
                f"  Suspicious connections: {'; '.join(malware_port_hits[:5])}",
                "A05:2021 - Security Misconfiguration",
            ))

        # Process from suspicious path with any public-IP connection
        if self._is_suspicious_path(proc.exe) and foreign_ips:
            findings.append(self._f(
                self.NAME, "High",
                f"Process from Suspicious Path Making Outbound Connections: {proc.name}",
                f"'{proc.name}' (PID {proc.pid}) runs from a non-standard path "
                f"AND has outbound connections to {len(foreign_ips)} public IP(s). "
                "This combination is a strong indicator of malware C2 communication.",
                "Terminate the process and block its outbound connections at the firewall. "
                "Investigate the executable with Get-AuthenticodeSignature and VirusTotal.",
                f"Process: {proc.name} | PID: {proc.pid} | Path: {proc.exe}\n"
                f"  Foreign IPs: {', '.join(list(foreign_ips)[:8])}",
                "A08:2021 - Software and Data Integrity Failures",
            ))

        # Non-whitelisted process connecting to unusually many distinct foreign IPs
        if (name_lc not in _KNOWN_MULTI_CONN_PROCS
                and len(foreign_ips) > _MULTI_IP_THRESHOLD):
            findings.append(self._f(
                self.NAME, "Medium",
                f"Process with Unusually Many Foreign Connections: {proc.name}",
                f"'{proc.name}' (PID {proc.pid}) has ESTABLISHED connections to "
                f"{len(foreign_ips)} distinct public IP address(es), which exceeds the "
                f"threshold of {_MULTI_IP_THRESHOLD} for a non-browser process. "
                "This may indicate scanning, botnet participation, or data exfiltration.",
                "Investigate the process purpose. Capture network traffic for analysis. "
                "If the behaviour is unexpected, terminate and run a malware scan.",
                f"Process: {proc.name} | PID: {proc.pid}\n"
                f"  {len(foreign_ips)} distinct foreign IPs "
                f"(sample): {', '.join(list(foreign_ips)[:10])}",
                "A05:2021 - Security Misconfiguration",
            ))

        return findings


# ---------------------------------------------------------------------------
# Check 4 — Startup Programs
# ---------------------------------------------------------------------------

class StartupScanner(BaseCheck):
    """
    Enumerates autostart entries from:
      - Registry Run / RunOnce keys (HKLM + HKCU + WOW64 variant)
      - Per-user and all-users Startup folders
    Flags entries with suspicious commands, unsigned binaries, or anomalous paths.
    """

    NAME = "Startup Scanner"

    def __init__(self, is_admin: bool = False, timeout: int = 15) -> None:
        super().__init__(timeout)
        self._is_admin = is_admin

    def run(self) -> List[Finding]:
        findings: List[Finding] = []
        findings.extend(self._scan_registry())
        findings.extend(self._scan_startup_folders())
        return findings

    # -- Registry run keys ------------------------------------------------

    def _scan_registry(self) -> List[Finding]:
        findings: List[Finding] = []
        total = 0

        if winreg is None:
            return [self._f(
                self.NAME, "Info",
                "Registry Autorun Scan Skipped",
                "The Windows registry API is unavailable on this platform.",
                "Run this check on Windows to inspect registry autorun entries.",
                "winreg import failed", "N/A",
            )]

        for hive, subkey, label in _AUTORUN_KEYS:
            try:
                key = winreg.OpenKey(hive, subkey)
            except OSError:
                continue

            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    i += 1
                    total += 1
                    findings.extend(self._evaluate_entry(label, name, str(value)))
                except OSError:
                    break
            winreg.CloseKey(key)

        findings.insert(0, self._f(
            self.NAME, "Info",
            f"Registry Autorun Entries ({total} found)",
            f"{total} startup entries found across Run/RunOnce registry keys.",
            "", f"Scanned keys: {', '.join(lbl for _, _, lbl in _AUTORUN_KEYS)}", "N/A",
        ))
        return findings

    # -- Startup folder entries -------------------------------------------

    def _scan_startup_folders(self) -> List[Finding]:
        findings: List[Finding] = []
        folders = {
            "User Startup Folder": Path(os.environ.get(
                "APPDATA", r"C:\Users\Default\AppData\Roaming"
            )) / r"Microsoft\Windows\Start Menu\Programs\Startup",
            "All-Users Startup Folder": Path(os.environ.get(
                "PROGRAMDATA", r"C:\ProgramData"
            )) / r"Microsoft\Windows\Start Menu\Programs\Startup",
        }

        for label, folder in folders.items():
            if not folder.exists():
                continue
            try:
                entries = list(folder.iterdir())
            except PermissionError:
                continue

            findings.append(self._f(
                self.NAME, "Info",
                f"{label}: {len(entries)} item(s)",
                f"Startup folder contains {len(entries)} file(s).",
                "", str(folder), "N/A",
            ))

            for entry in entries:
                if entry.suffix.lower() in (".lnk", ".exe", ".bat", ".cmd",
                                            ".vbs", ".js", ".ps1", ".hta"):
                    findings.extend(self._evaluate_entry(label, entry.name, str(entry)))

        return findings

    # -- Per-entry evaluation ---------------------------------------------

    def _evaluate_entry(
        self, source: str, name: str, value: str
    ) -> List[Finding]:
        findings: List[Finding] = []

        # Suspicious command pattern
        if _SUSPICIOUS_CMD.search(value):
            findings.append(self._f(
                self.NAME, "High",
                f"Suspicious Startup Command: {name}",
                f"The startup entry '{name}' uses a command pattern associated with "
                "malware persistence, LOLbin abuse, or obfuscated execution.",
                "Remove this entry if it is not an authorized application. "
                "Investigate the command and the binary it launches.",
                f"Source: {source}\n  Name: {name}\n  Command: {value[:200]}",
                "A08:2021 - Software and Data Integrity Failures",
            ))

        # Suspicious exe path
        if self._is_suspicious_path(self._extract_exe(value)):
            findings.append(self._f(
                self.NAME, "High",
                f"Startup Entry from Suspicious Path: {name}",
                f"Startup entry '{name}' launches an executable from a non-standard "
                "location (Temp, Downloads, Public, etc.). Legitimate software "
                "installed on a system does not typically autostart from these paths.",
                "Verify the legitimacy of this entry. Run Get-AuthenticodeSignature "
                "on the executable. Remove if not authorized.",
                f"Source: {source}\n  Name: {name}\n  Command: {value[:200]}",
                "A08:2021 - Software and Data Integrity Failures",
            ))
            return findings   # already high-risk — don't also check signature below

        # Signature check for non-suspicious-path executables (admin-only paths)
        exe = self._extract_exe(value)
        if exe and os.path.exists(exe):
            sig = self._check_signature(exe)
            if sig and sig not in ("Valid", ""):
                findings.append(self._f(
                    self.NAME, "Medium",
                    f"Startup Entry: Unsigned or Untrusted Binary: {name}",
                    f"The executable launched by startup entry '{name}' has an "
                    f"authenticode signature status of '{sig}'. "
                    "Unsigned binaries in startup can indicate malware persistence.",
                    "Verify the executable is legitimate. Remove if unauthorized.",
                    f"Source: {source}\n  Exe: {exe}\n  Signature: {sig}",
                    "A08:2021 - Software and Data Integrity Failures",
                ))

        return findings

    @staticmethod
    def _extract_exe(command: str) -> Optional[str]:
        """Extract the executable path from a startup command string."""
        command = command.strip()
        if not command:
            return None
        # Quoted path
        m = re.match(r'^"([^"]+)"', command)
        if m:
            return m.group(1)
        # Unquoted path (up to first space or flag)
        m = re.match(r'^([^\s]+\.(?:exe|com|bat|cmd|vbs|js|ps1|hta))', command, re.I)
        if m:
            return m.group(1)
        return None

    def _check_signature(self, exe_path: str) -> Optional[str]:
        """Returns authenticode status string from PowerShell, or None on failure."""
        safe_path = exe_path.replace("'", "''")
        out = self._ps(f"(Get-AuthenticodeSignature '{safe_path}').Status")
        return out if out else None


# ---------------------------------------------------------------------------
# Check 5 — Security Software Status
# ---------------------------------------------------------------------------

class SecuritySoftwareCheck(BaseCheck):
    """
    Checks Windows Defender status (via Get-MpComputerStatus) and
    Windows Firewall profile status (via Get-NetFirewallProfile).
    Falls back to registry and netsh if PowerShell commands are unavailable.
    """

    NAME = "Security Software"

    def __init__(self, is_admin: bool = False, timeout: int = 25) -> None:
        super().__init__(timeout)
        self._is_admin = is_admin

    def run(self) -> List[Finding]:
        findings: List[Finding] = []
        findings.extend(self._check_defender())
        findings.extend(self._check_firewall())
        return findings

    # -- Windows Defender ------------------------------------------------

    def _check_defender(self) -> List[Finding]:
        raw = self._ps(
            "Get-MpComputerStatus | Select-Object "
            "RealTimeProtectionEnabled,AntivirusEnabled,AntispywareEnabled,"
            "BehaviorMonitorEnabled,AntivirusSignatureAge,AMRunningMode "
            "| ConvertTo-Json"
        )

        if not raw:
            # Fallback: check registry for Security Center
            return self._defender_registry_fallback()

        try:
            data = json.loads(raw)
        except Exception:
            return self._defender_registry_fallback()

        findings: List[Finding] = []
        rt  = data.get("RealTimeProtectionEnabled", False)
        av  = data.get("AntivirusEnabled", False)
        bm  = data.get("BehaviorMonitorEnabled", False)
        age = data.get("AntivirusSignatureAge", -1)

        if not rt or not av:
            findings.append(self._f(
                self.NAME, "High",
                "Windows Defender Real-Time Protection Disabled",
                f"Windows Defender real-time protection is {'disabled' if not rt else 'partially disabled'}. "
                f"(RealTimeProtection={rt}, AntivirusEnabled={av}). "
                "The system is unprotected against known malware.",
                "Re-enable Windows Defender via Settings → Windows Security → "
                "Virus & Threat Protection. If a third-party AV is installed, "
                "ensure it is active and up-to-date.",
                f"RealTimeProtectionEnabled={rt}, AntivirusEnabled={av}, "
                f"BehaviorMonitorEnabled={bm}",
                "A06:2021 - Vulnerable and Outdated Components",
            ))
        else:
            findings.append(self._f(
                self.NAME, "Info",
                "Windows Defender Active",
                f"Real-time protection is enabled. BehaviorMonitor={bm}.",
                "", f"AMRunningMode: {data.get('AMRunningMode', 'unknown')}",
                "A06:2021 - Vulnerable and Outdated Components",
            ))

        if isinstance(age, int) and age >= 0:
            if age > 7:
                findings.append(self._f(
                    self.NAME, "High",
                    f"Defender Signatures Outdated ({age} Days Old)",
                    f"Antivirus signatures are {age} days old. Signatures older than "
                    "7 days leave the system exposed to recent malware variants.",
                    "Update Defender signatures immediately: "
                    "Update-MpSignature (PowerShell) or Windows Security → Check for Updates.",
                    f"AntivirusSignatureAge: {age} days",
                    "A06:2021 - Vulnerable and Outdated Components",
                ))
            elif age > 3:
                findings.append(self._f(
                    self.NAME, "Medium",
                    f"Defender Signatures Aging ({age} Days Old)",
                    f"Antivirus signatures are {age} days old. Update soon to maintain coverage.",
                    "Run Update-MpSignature or open Windows Security to update definitions.",
                    f"AntivirusSignatureAge: {age} days",
                    "A06:2021 - Vulnerable and Outdated Components",
                ))
            else:
                findings.append(self._f(
                    self.NAME, "Info",
                    "Defender Signatures Current",
                    f"Signatures were updated {age} day(s) ago.",
                    "", f"AntivirusSignatureAge: {age}", "N/A",
                ))

        return findings

    def _defender_registry_fallback(self) -> List[Finding]:
        """Check Windows Security Center registry when PS is unavailable."""
        if winreg is None:
            return [self._f(
                self.NAME, "Info",
                "Windows Defender Status Unknown",
                "The Windows registry API is unavailable on this platform.",
                "Run this check on Windows or verify antivirus status manually.",
                "winreg import failed", "N/A",
            )]

        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows Defender",
            )
            disabled, _ = winreg.QueryValueEx(key, "DisableAntiSpyware")
            winreg.CloseKey(key)
            if disabled:
                return [self._f(
                    self.NAME, "High",
                    "Windows Defender Appears Disabled (Registry)",
                    "The DisableAntiSpyware registry key is set, indicating Defender "
                    "may have been disabled. Verify via Windows Security Center.",
                    "Remove the DisableAntiSpyware key or re-enable Defender via Group Policy.",
                    r"HKLM\SOFTWARE\Microsoft\Windows Defender\DisableAntiSpyware=1",
                    "A06:2021 - Vulnerable and Outdated Components",
                )]
        except OSError:
            pass
        return [self._f(
            self.NAME, "Info",
            "Windows Defender Status Unknown",
            "Could not determine Defender status via PowerShell or registry. "
            "Verify manually via Windows Security.",
            "Open Windows Security → Virus & Threat Protection to confirm status.",
            "Get-MpComputerStatus failed; registry check inconclusive", "N/A",
        )]

    # -- Windows Firewall ------------------------------------------------

    def _check_firewall(self) -> List[Finding]:
        raw = self._ps(
            "Get-NetFirewallProfile | "
            "Select-Object Name,Enabled,DefaultInboundAction,DefaultOutboundAction "
            "| ConvertTo-Json"
        )

        if raw:
            try:
                profiles = json.loads(raw)
                if isinstance(profiles, dict):
                    profiles = [profiles]
                return self._evaluate_firewall_profiles(profiles)
            except Exception:
                pass

        # Fallback: netsh advfirewall
        return self._firewall_netsh_fallback()

    def _evaluate_firewall_profiles(self, profiles: List[dict]) -> List[Finding]:
        findings: List[Finding] = []
        disabled: List[str] = []
        allow_all_inbound: List[str] = []

        for p in profiles:
            name    = p.get("Name", "unknown")
            enabled = p.get("Enabled", False)
            inbound = str(p.get("DefaultInboundAction", "")).lower()

            if not enabled:
                disabled.append(name)
            elif "allow" in inbound:
                allow_all_inbound.append(name)

        if disabled:
            findings.append(self._f(
                self.NAME, "High",
                f"Windows Firewall Disabled: {', '.join(disabled)}",
                f"The Windows Firewall is disabled for profile(s): {', '.join(disabled)}. "
                "A disabled firewall allows unrestricted inbound network access.",
                "Re-enable all firewall profiles: Set-NetFirewallProfile -All -Enabled True",
                f"Disabled profiles: {', '.join(disabled)}",
                "A05:2021 - Security Misconfiguration",
            ))
        else:
            findings.append(self._f(
                self.NAME, "Info",
                "Windows Firewall Enabled (All Profiles)",
                "Windows Firewall is active on Domain, Private, and Public profiles.",
                "", "All profiles: Enabled", "N/A",
            ))

        if allow_all_inbound:
            findings.append(self._f(
                self.NAME, "Medium",
                f"Firewall DefaultInboundAction=Allow: {', '.join(allow_all_inbound)}",
                f"Profile(s) {', '.join(allow_all_inbound)} are set to Allow all inbound "
                "connections by default. This negates the protection of the firewall.",
                "Change DefaultInboundAction to Block: "
                "Set-NetFirewallProfile -All -DefaultInboundAction Block",
                f"Allow-all inbound profiles: {', '.join(allow_all_inbound)}",
                "A05:2021 - Security Misconfiguration",
            ))

        return findings

    def _firewall_netsh_fallback(self) -> List[Finding]:
        out = self._cmd(["netsh", "advfirewall", "show", "allprofiles", "state"])
        if not out:
            return [self._f(
                self.NAME, "Info", "Firewall Status Unknown",
                "Could not determine firewall status via PowerShell or netsh.",
                "Check firewall status manually: netsh advfirewall show allprofiles",
                "Both Get-NetFirewallProfile and netsh failed", "N/A",
            )]

        findings: List[Finding] = []
        off_profiles = re.findall(r"([\w\s]+?)\s+Profile.*?State\s+OFF", out, re.I | re.S)

        if off_profiles:
            findings.append(self._f(
                self.NAME, "High",
                f"Firewall OFF (netsh): {', '.join(p.strip() for p in off_profiles)}",
                "netsh reports firewall disabled for one or more profiles.",
                "Enable firewall: netsh advfirewall set allprofiles state on",
                f"netsh output: {out[:300]}",
                "A05:2021 - Security Misconfiguration",
            ))
        else:
            findings.append(self._f(
                self.NAME, "Info",
                "Windows Firewall Enabled (netsh)",
                "netsh reports no firewall profiles in OFF state.",
                "", "netsh advfirewall show allprofiles: no OFF state found", "N/A",
            ))
        return findings


# ---------------------------------------------------------------------------
# Check 6 — File Permission Checker
# ---------------------------------------------------------------------------

class FilePermissionChecker(BaseCheck):
    """
    Uses icacls to inspect ACLs on sensitive system directories.
    Flags world-writable (Everyone) or overly broad (Authenticated Users / Users)
    write permissions that could be exploited for privilege escalation.
    """

    NAME = "File Permissions"

    def __init__(self, is_admin: bool = False, timeout: int = 15) -> None:
        super().__init__(timeout)
        self._is_admin = is_admin

    def run(self) -> List[Finding]:
        findings: List[Finding] = []

        # Also check user temp directory
        user_temp = os.environ.get("TEMP", "")
        dirs_to_check = list(_PERM_DIRS)
        if user_temp and user_temp.lower() not in {d[0].lower() for d in _PERM_DIRS}:
            dirs_to_check.append((user_temp, f"User Temp ({user_temp})"))

        for path, label in dirs_to_check:
            if not os.path.exists(path):
                continue
            findings.extend(self._check_dir(path, label))

        return findings

    def _check_dir(self, path: str, label: str) -> List[Finding]:
        findings: List[Finding] = []
        out = self._cmd(["icacls", path])

        if not out:
            findings.append(self._f(
                self.NAME, "Info",
                f"Permission Check Skipped: {label}",
                f"Could not run icacls on '{path}'. "
                "Administrator rights may be required.",
                "", f"icacls '{path}' returned no output", "N/A",
            ))
            return findings

        aces = self._parse_aces(out)
        flagged = False

        for principal, write_perm in aces:
            p_low = principal.lower()

            if any(hrp in p_low for hrp in _HIGH_RISK_WRITE_PRINCIPALS):
                findings.append(self._f(
                    self.NAME, "Critical",
                    f"World-Writable Directory: {label}",
                    f"'{path}' grants '{principal}' {write_perm} access. "
                    "'Everyone' includes unauthenticated users in some configurations. "
                    "World-writable system directories enable DLL planting, "
                    "log tampering, and privilege escalation attacks.",
                    f"Remove write access for '{principal}': "
                    f"icacls \"{path}\" /remove:g \"{principal}\"",
                    f"Path: {path}\n  ACE: {principal} → {write_perm}",
                    "A01:2021 - Broken Access Control",
                ))
                flagged = True

            elif any(mrp in p_low for mrp in _MEDIUM_RISK_WRITE_PRINCIPALS):
                # Users with Modify/Full on system dirs is overly permissive
                if write_perm in ("Full Control", "Modify"):
                    findings.append(self._f(
                        self.NAME, "High",
                        f"Overly Permissive Directory ACL: {label}",
                        f"'{path}' grants '{principal}' {write_perm} access. "
                        "Granting broad user groups full or modify rights on system "
                        "directories enables privilege escalation via file planting.",
                        f"Restrict '{principal}' to Read & Execute on '{path}':\n"
                        f"icacls \"{path}\" /grant \"{principal}:(OI)(CI)(RX)\"",
                        f"Path: {path}\n  ACE: {principal} → {write_perm}",
                        "A01:2021 - Broken Access Control",
                    ))
                    flagged = True

        if not flagged:
            findings.append(self._f(
                self.NAME, "Info",
                f"Directory Permissions Look Acceptable: {label}",
                f"No world-writable or overly permissive ACEs detected on '{path}'.",
                "", f"icacls '{path}': no high-risk ACEs found", "N/A",
            ))

        return findings

    @staticmethod
    def _parse_aces(icacls_output: str) -> List[Tuple[str, str]]:
        """
        Parse icacls output and return (principal, highest_write_perm) tuples
        for ACEs that include any write-capable permission flag.

        icacls line format examples:
          C:\\Windows\\Temp BUILTIN\\Administrators:(OI)(CI)(F)
                            NT AUTHORITY\\SYSTEM:(OI)(CI)(F)
                            BUILTIN\\Users:(OI)(CI)(RX)
                            BUILTIN\\Users:(CI)(WD)
        """
        results: List[Tuple[str, str]] = []
        # Match "PRINCIPAL:(optional_inherit_flags)(PERM_FLAG)" anywhere on a line
        ace_re = re.compile(
            r"([A-Za-z0-9\\\s_\-]+?)"    # principal
            r":\([A-Z,IO]+\)"             # optional inheritance flags (OI)(CI) etc.
            r"*"
            r"\(([A-Z,]+)\)",             # actual permission flag(s)
            re.I,
        )

        # Map permission flag strings to human-readable names
        perm_rank = {"F": "Full Control", "M": "Modify", "W": "Write",
                     "WD": "Write Data", "AD": "Append Data"}

        for line in icacls_output.splitlines():
            for match in ace_re.finditer(line):
                principal = match.group(1).strip()
                flags = {f.strip().upper() for f in match.group(2).split(",")}
                write_flags = flags & _WRITE_FLAGS
                if write_flags and principal:
                    # Report the most severe write flag
                    best = next(
                        (perm_rank[f] for f in ("F", "M", "W", "WD", "AD")
                         if f in write_flags),
                        list(write_flags)[0],
                    )
                    results.append((principal, best))

        return results


# ---------------------------------------------------------------------------
# SystemScanner — orchestrator
# ---------------------------------------------------------------------------

def _os_build() -> int:
    try:
        return int(platform.version().split(".")[2])
    except (IndexError, ValueError):
        return 0


def _gather_snapshot(is_admin: bool) -> _SystemSnapshot:
    """
    Collect process list and network connections in one pass.
    Called once before spawning concurrent check threads.
    """
    processes: List[_ProcessInfo] = []
    connections: List[Any] = []

    if not _PSUTIL_OK:
        return _SystemSnapshot(
            processes=[], connections=[],
            is_admin=is_admin, os_build=_os_build(),
        )

    # Gather connections first
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, PermissionError):
        connections = []

    # Build pid → connections lookup
    conn_by_pid: Dict[int, List[Any]] = defaultdict(list)
    for conn in connections:
        if conn.pid:
            conn_by_pid[conn.pid].append(conn)

    # Enumerate processes
    attrs = ["pid", "name", "exe", "status", "memory_info", "username"]
    for proc in psutil.process_iter(attrs):
        try:
            info = proc.info
            pid = info["pid"]
            mem_info = info.get("memory_info")
            processes.append(_ProcessInfo(
                pid=pid,
                name=info.get("name") or "",
                exe=info.get("exe"),
                status=info.get("status") or "",
                memory_mb=(mem_info.rss / 1_048_576) if mem_info else 0.0,
                username=info.get("username"),
                connections=conn_by_pid.get(pid, []),
            ))
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            pass

    return _SystemSnapshot(
        processes=processes,
        connections=connections,
        is_admin=is_admin,
        os_build=_os_build(),
    )


class SystemScanner:
    """
    Orchestrates all system security check classes, collects findings,
    and returns a sorted, reporter-compatible list of dicts.
    """

    def __init__(self, is_admin: bool = False, verbose: bool = False) -> None:
        self.is_admin = is_admin
        self.verbose  = verbose

    def scan(self) -> List[Dict[str, Any]]:
        # Phase 1 — gather shared psutil snapshot (sequential, ~0.5–2 s)
        snapshot = _gather_snapshot(self.is_admin)

        if not self.is_admin:
            _warn: List[Finding] = [Finding(
                check="System Scanner",
                risk_level="Info",
                title="Limited Scan: No Administrator Privileges",
                detail=(
                    "Running without administrator rights. "
                    "Process exe paths, network connections from other users, "
                    "and some registry keys may be inaccessible. "
                    "Re-run as Administrator for complete results."
                ),
                recommendation="Right-click the terminal and choose 'Run as Administrator'.",
                evidence=f"is_admin={self.is_admin}",
                owasp="N/A",
            )]
        else:
            _warn = []

        # Phase 2 — run all checks concurrently
        checks: List[BaseCheck] = [
            PortScanner(snapshot),
            ProcessMonitor(snapshot),
            NetworkMonitor(snapshot),
            StartupScanner(is_admin=self.is_admin),
            SecuritySoftwareCheck(is_admin=self.is_admin),
            FilePermissionChecker(is_admin=self.is_admin),
        ]

        all_findings: List[Finding] = list(_warn)

        with ThreadPoolExecutor(max_workers=len(checks)) as executor:
            future_map = {executor.submit(chk.run): chk for chk in checks}
            for future in as_completed(future_map):
                chk = future_map[future]
                try:
                    all_findings.extend(future.result())
                except Exception as exc:
                    all_findings.append(Finding(
                        check=chk.NAME,
                        risk_level="Info",
                        title=f"Check Error: {chk.NAME}",
                        detail=f"An unexpected error occurred in '{chk.NAME}': {str(exc)[:180]}",
                        recommendation="Report this to the DefenseScan maintainer.",
                        evidence=str(exc)[:180],
                    ))

        all_findings.sort(key=lambda f: f.rank)
        return [f.to_report() for f in all_findings]
