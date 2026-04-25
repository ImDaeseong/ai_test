"""
Web vulnerability scanner — class-based, concurrent OWASP Top 10-aligned checks.

Architecture:
  Finding         — dataclass representing a single scanner result
  ScanContext     — shared read-only state passed to every check
  BaseCheck       — abstract base for all check classes
  SecurityHeadersCheck  — security header presence and value analysis
  TlsCheck              — SSL/TLS certificate and protocol analysis
  DirectoryListingCheck — sensitive path and directory listing probing
  HttpResponseCheck     — status codes, redirect chains, timing, mixed content
  WebScanner      — orchestrator: fetches initial response, runs checks concurrently
"""

import re
import ssl
import socket
import time
import urllib.parse
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_UA = "DefenseScan/1.0 (Security Audit)"

RISK_ORDER = ["Critical", "High", "Medium", "Low", "Info"]
_RISK_RANK: Dict[str, int] = {r: i for i, r in enumerate(RISK_ORDER)}

_RISK_TO_SEVERITY: Dict[str, str] = {
    "Critical": "CRITICAL",
    "High":     "HIGH",
    "Medium":   "MEDIUM",
    "Low":      "LOW",
    "Info":     "INFO",
}
_RISK_TO_STATUS: Dict[str, str] = {
    "Critical": "FAIL",
    "High":     "FAIL",
    "Medium":   "FAIL",
    "Low":      "WARN",
    "Info":     "INFO",
}

# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """
    A single scanner result.

    Fields required by the caller:
      check          — which check class produced this
      risk_level     — Critical | High | Medium | Low | Info
      title          — short, descriptive issue name
      detail         — full technical explanation
      recommendation — concrete remediation step
      evidence       — what was observed (header value, URL, snippet, …)
      owasp          — OWASP Top 10 reference (optional)
    """
    check:          str
    risk_level:     str
    title:          str
    detail:         str
    recommendation: str
    evidence:       str
    owasp:          str = ""

    @property
    def rank(self) -> int:
        return _RISK_RANK.get(self.risk_level, len(RISK_ORDER))

    def to_report(self) -> Dict[str, Any]:
        """
        Convert to the dict format expected by Reporter and save_json.
        Combines detail + recommendation so the console shows both.
        Backward-compatible keys (severity, status, check) are preserved.
        """
        display_detail = self.detail
        if self.recommendation:
            display_detail += f"\n  Recommendation: {self.recommendation}"

        return {
            # Reporter-compatible keys
            "category":       "web",
            "check":          self.title,
            "severity":       _RISK_TO_SEVERITY.get(self.risk_level, "INFO"),
            "status":         _RISK_TO_STATUS.get(self.risk_level, "INFO"),
            "detail":         display_detail,
            "owasp":          self.owasp,
            # Extended keys (present in JSON output)
            "risk_level":     self.risk_level,
            "title":          self.title,
            "recommendation": self.recommendation,
            "evidence":       self.evidence,
        }


# ---------------------------------------------------------------------------
# ScanContext — shared read-only snapshot passed to every check
# ---------------------------------------------------------------------------

@dataclass
class ScanContext:
    url:              str
    parsed:           urllib.parse.ParseResult
    response:         requests.Response
    response_time_ms: float
    timeout:          int


# ---------------------------------------------------------------------------
# BaseCheck
# ---------------------------------------------------------------------------

class BaseCheck(ABC):
    """Abstract base class for all check modules."""

    NAME: str = ""

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    @abstractmethod
    def run(self, ctx: ScanContext) -> List[Finding]:
        ...

    # Convenience: each check creates its own session for follow-up requests
    # (requests.Session is not safe to share across threads for writes)
    @staticmethod
    def _new_session() -> requests.Session:
        s = requests.Session()
        s.headers["User-Agent"] = _UA
        s.verify = False
        return s

    @staticmethod
    def _finding(
        check: str,
        risk_level: str,
        title: str,
        detail: str,
        recommendation: str,
        evidence: str,
        owasp: str = "",
    ) -> Finding:
        return Finding(
            check=check,
            risk_level=risk_level,
            title=title,
            detail=detail,
            recommendation=recommendation,
            evidence=evidence,
            owasp=owasp,
        )


# ---------------------------------------------------------------------------
# Check 1 — Security Headers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _HeaderSpec:
    key:          str   # lowercase HTTP header name
    display:      str   # human-readable name
    risk_missing: str   # risk level when absent
    owasp:        str
    fix:          str   # recommended header value to show in recommendation


_HEADER_SPECS: Tuple[_HeaderSpec, ...] = (
    _HeaderSpec(
        "strict-transport-security", "Strict-Transport-Security", "High",
        "A02:2021 - Cryptographic Failures",
        "Strict-Transport-Security: max-age=31536000; includeSubDomains; preload",
    ),
    _HeaderSpec(
        "content-security-policy", "Content-Security-Policy", "High",
        "A03:2021 - Injection",
        "Content-Security-Policy: default-src 'self'; script-src 'self'",
    ),
    _HeaderSpec(
        "x-frame-options", "X-Frame-Options", "Medium",
        "A05:2021 - Security Misconfiguration",
        "X-Frame-Options: DENY",
    ),
    _HeaderSpec(
        "x-content-type-options", "X-Content-Type-Options", "Medium",
        "A05:2021 - Security Misconfiguration",
        "X-Content-Type-Options: nosniff",
    ),
    _HeaderSpec(
        "referrer-policy", "Referrer-Policy", "Low",
        "A05:2021 - Security Misconfiguration",
        "Referrer-Policy: strict-origin-when-cross-origin",
    ),
    _HeaderSpec(
        "permissions-policy", "Permissions-Policy", "Low",
        "A05:2021 - Security Misconfiguration",
        "Permissions-Policy: geolocation=(), camera=(), microphone=()",
    ),
    _HeaderSpec(
        "cross-origin-opener-policy", "Cross-Origin-Opener-Policy", "Low",
        "A05:2021 - Security Misconfiguration",
        "Cross-Origin-Opener-Policy: same-origin",
    ),
    _HeaderSpec(
        "cross-origin-resource-policy", "Cross-Origin-Resource-Policy", "Low",
        "A05:2021 - Security Misconfiguration",
        "Cross-Origin-Resource-Policy: same-origin",
    ),
)

_DISCLOSURE_HEADERS: Tuple[str, ...] = (
    "server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version",
    "x-runtime", "x-generator", "x-cf-powered-by", "via", "x-pingback",
)

_VERSION_RE       = re.compile(r"\d+\.\d+")
_UNSAFE_INLINE_RE = re.compile(r"'unsafe-inline'", re.I)
_UNSAFE_EVAL_RE   = re.compile(r"'unsafe-eval'",   re.I)
_HSTS_MAX_AGE_RE  = re.compile(r"max-age=(\d+)",   re.I)
_HSTS_MIN_AGE     = 15_768_000   # 6 months in seconds


class SecurityHeadersCheck(BaseCheck):
    """
    Checks for presence, correct value, and dangerous misconfigurations
    of HTTP security response headers.
    """

    NAME = "Security Headers"

    def run(self, ctx: ScanContext) -> List[Finding]:
        findings: List[Finding] = []
        hdrs = {k.lower(): v for k, v in ctx.response.headers.items()}

        for spec in _HEADER_SPECS:
            val = hdrs.get(spec.key)
            if val is None:
                findings.append(self._finding(
                    check=self.NAME,
                    risk_level=spec.risk_missing,
                    title=f"Missing Security Header: {spec.display}",
                    detail=(
                        f"The '{spec.display}' header is absent from the response. "
                        "This header provides an important browser-enforced security control."
                    ),
                    recommendation=f"Add the header: {spec.fix}",
                    evidence="Header not present in HTTP response",
                    owasp=spec.owasp,
                ))
            else:
                findings.extend(self._inspect_value(spec, val))

        for hdr in _DISCLOSURE_HEADERS:
            val = hdrs.get(hdr)
            if val:
                findings.extend(self._check_disclosure(hdr, val))

        return findings

    # --- per-header deep value inspection ---

    def _inspect_value(self, spec: _HeaderSpec, value: str) -> List[Finding]:
        findings: List[Finding] = []

        if spec.key == "content-security-policy":
            if _UNSAFE_INLINE_RE.search(value):
                findings.append(self._finding(
                    check=self.NAME,
                    risk_level="Medium",
                    title="CSP: 'unsafe-inline' Directive Detected",
                    detail=(
                        "The Content-Security-Policy contains 'unsafe-inline', allowing "
                        "execution of inline <script> and <style> blocks. This substantially "
                        "weakens XSS protection because injected inline scripts will execute."
                    ),
                    recommendation=(
                        "Remove 'unsafe-inline'. Replace inline scripts with external files "
                        "and use nonces: script-src 'nonce-{random-per-request}'"
                    ),
                    evidence=f"Content-Security-Policy: {value[:150]}",
                    owasp="A03:2021 - Injection",
                ))

            if _UNSAFE_EVAL_RE.search(value):
                findings.append(self._finding(
                    check=self.NAME,
                    risk_level="Medium",
                    title="CSP: 'unsafe-eval' Directive Detected",
                    detail=(
                        "The Content-Security-Policy contains 'unsafe-eval', permitting "
                        "eval(), new Function(), setTimeout(string), and similar dynamic "
                        "code execution. Attackers can use this to escalate reflected XSS."
                    ),
                    recommendation=(
                        "Remove 'unsafe-eval'. Refactor code that uses eval() or "
                        "string-based setTimeout/setInterval."
                    ),
                    evidence=f"Content-Security-Policy: {value[:150]}",
                    owasp="A03:2021 - Injection",
                ))

            if "default-src" not in value and "script-src" not in value:
                findings.append(self._finding(
                    check=self.NAME,
                    risk_level="Medium",
                    title="CSP: No Script Execution Directive",
                    detail=(
                        "The Content-Security-Policy header is present but contains neither "
                        "'default-src' nor 'script-src'. Without these directives the policy "
                        "does not restrict JavaScript execution."
                    ),
                    recommendation="Add: Content-Security-Policy: default-src 'self'",
                    evidence=f"Content-Security-Policy: {value[:150]}",
                    owasp="A03:2021 - Injection",
                ))

        elif spec.key == "strict-transport-security":
            m = _HSTS_MAX_AGE_RE.search(value)
            if m:
                age = int(m.group(1))
                if age < _HSTS_MIN_AGE:
                    findings.append(self._finding(
                        check=self.NAME,
                        risk_level="Low",
                        title=f"HSTS: max-age Too Short ({age}s / {age // 86400} days)",
                        detail=(
                            f"The HSTS max-age is {age} seconds ({age // 86400} days), "
                            f"below the recommended minimum of {_HSTS_MIN_AGE}s (6 months). "
                            "Short max-age values reduce SSL-stripping protection because "
                            "the browser forgets the policy quickly."
                        ),
                        recommendation=(
                            f"Increase max-age to at least {_HSTS_MIN_AGE}: "
                            f"Strict-Transport-Security: max-age={_HSTS_MIN_AGE}; includeSubDomains"
                        ),
                        evidence=f"Strict-Transport-Security: {value}",
                        owasp=spec.owasp,
                    ))

            if "includesubdomains" not in value.lower():
                findings.append(self._finding(
                    check=self.NAME,
                    risk_level="Low",
                    title="HSTS: Missing 'includeSubDomains' Directive",
                    detail=(
                        "The HSTS header does not include 'includeSubDomains'. "
                        "Subdomains can be reached via plain HTTP, enabling SSL stripping "
                        "attacks that can steal cookies with insufficient Secure flags."
                    ),
                    recommendation=(
                        "Add includeSubDomains: "
                        "Strict-Transport-Security: max-age=31536000; includeSubDomains"
                    ),
                    evidence=f"Strict-Transport-Security: {value}",
                    owasp=spec.owasp,
                ))

        elif spec.key == "x-frame-options":
            valid = {"DENY", "SAMEORIGIN"}
            # ALLOW-FROM is deprecated; treat all non-standard values as misconfigured
            normalized = value.strip().upper()
            if not any(normalized.startswith(v) for v in valid):
                findings.append(self._finding(
                    check=self.NAME,
                    risk_level="Medium",
                    title=f"X-Frame-Options: Invalid or Deprecated Value '{value.strip()}'",
                    detail=(
                        f"X-Frame-Options is set to '{value.strip()}', which is not "
                        "a recognised value. Invalid values are ignored by browsers, "
                        "leaving the page vulnerable to clickjacking attacks."
                    ),
                    recommendation="Set X-Frame-Options: DENY (or SAMEORIGIN if self-framing is needed).",
                    evidence=f"X-Frame-Options: {value}",
                    owasp=spec.owasp,
                ))

        return findings

    # --- information-disclosure headers ---

    def _check_disclosure(self, header: str, value: str) -> List[Finding]:
        has_version = bool(_VERSION_RE.search(value))

        if header == "server":
            risk   = "Medium" if has_version else "Low"
            noun   = "Server Version" if has_version else "Server Software"
            detail = (
                f"The 'Server' header discloses {'the exact version: ' if has_version else 'the software: '}"
                f"'{value}'. "
                + ("Attackers can directly target CVEs for that version." if has_version
                   else "Technology disclosure aids fingerprinting and targeted attacks.")
            )
        else:
            risk   = "Medium" if has_version else "Low"
            noun   = f"'{header}' Header"
            detail = (
                f"The '{header}' header leaks internal technology details: '{value[:80]}'. "
                "Exposing framework/runtime information helps attackers identify exploitable components."
            )

        return [self._finding(
            check=self.NAME,
            risk_level=risk,
            title=f"Information Disclosure via {noun}",
            detail=detail,
            recommendation=f"Remove the '{header}' header from all server responses.",
            evidence=f"{header}: {value[:100]}",
            owasp="A06:2021 - Vulnerable and Outdated Components",
        )]


# ---------------------------------------------------------------------------
# Check 2 — SSL/TLS Analysis
# ---------------------------------------------------------------------------

_WEAK_PROTOCOLS:      frozenset = frozenset({"SSLv2", "SSLv3", "TLSv1", "TLSv1.1"})
_WEAK_CIPHER_FRAGS:   frozenset = frozenset({"RC4", "DES", "3DES", "EXPORT", "NULL",
                                              "anon", "ADH", "AECDH", "MD5"})
_CERT_WARN_DAYS     = 30
_CERT_CRITICAL_DAYS = 0


class TlsCheck(BaseCheck):
    """
    Analyses TLS certificate validity and protocol/cipher configuration.
    Makes a direct ssl socket connection so it sees the raw negotiated parameters,
    independent of whether requests' verify flag is True or False.
    """

    NAME = "SSL/TLS"

    def run(self, ctx: ScanContext) -> List[Finding]:
        if ctx.parsed.scheme == "http":
            return [self._finding(
                check=self.NAME,
                risk_level="High",
                title="Plain HTTP — No Transport Encryption",
                detail=(
                    "The target is served over unencrypted HTTP. "
                    "All data exchanged — including credentials, session tokens, "
                    "and personal information — is visible to any network observer "
                    "and trivially modifiable by an on-path attacker (MITM)."
                ),
                recommendation=(
                    "Obtain a TLS certificate (free via Let's Encrypt) and serve the "
                    "site exclusively over HTTPS. Redirect all HTTP requests to HTTPS "
                    "and add an HSTS header."
                ),
                evidence=f"URL scheme: http",
                owasp="A02:2021 - Cryptographic Failures",
            )]

        host = ctx.parsed.hostname or ""
        port = ctx.parsed.port or 443
        return self._inspect_tls(host, port)

    def _inspect_tls(self, host: str, port: int) -> List[Finding]:
        findings: List[Finding] = []
        ctx_ssl = ssl.create_default_context()

        try:
            with socket.create_connection((host, port), timeout=self.timeout) as raw_sock:
                with ctx_ssl.wrap_socket(raw_sock, server_hostname=host) as ssock:
                    cert      = ssock.getpeercert()
                    cipher    = ssock.cipher()     # (name, protocol, bits)
                    tls_ver   = ssock.version() or ""

        except ssl.SSLCertVerificationError as exc:
            findings.append(self._finding(
                check=self.NAME,
                risk_level="High",
                title="TLS Certificate Verification Failed",
                detail=(
                    "The server's certificate could not be verified by the system trust store. "
                    "This may indicate a self-signed certificate, an expired certificate, "
                    "a hostname mismatch, or an active MITM attack."
                ),
                recommendation=(
                    "Replace the certificate with one issued by a publicly trusted CA. "
                    "Ensure the certificate's CN or SAN matches the hostname exactly."
                ),
                evidence=str(exc)[:200],
                owasp="A02:2021 - Cryptographic Failures",
            ))
            return findings

        except ssl.SSLError as exc:
            findings.append(self._finding(
                check=self.NAME,
                risk_level="High",
                title="TLS Handshake Failed",
                detail=(
                    "The TLS handshake could not be completed. "
                    "The server may be offering only deprecated protocols or ciphers "
                    "that the client refuses."
                ),
                recommendation=(
                    "Enable TLS 1.2 and TLS 1.3 on the server. "
                    "Remove SSLv2, SSLv3, TLS 1.0, and TLS 1.1 from the cipher configuration."
                ),
                evidence=str(exc)[:200],
                owasp="A02:2021 - Cryptographic Failures",
            ))
            return findings

        except OSError:
            # Host not reachable on TLS port (e.g. plain HTTP only)
            return findings

        # --- Protocol version ---
        if tls_ver in _WEAK_PROTOCOLS:
            findings.append(self._finding(
                check=self.NAME,
                risk_level="High",
                title=f"Deprecated TLS Protocol Negotiated: {tls_ver}",
                detail=(
                    f"The server negotiated {tls_ver}, which has known vulnerabilities: "
                    "BEAST (TLS 1.0), POODLE (SSLv3), DROWN (SSLv2). "
                    "These protocols are deprecated by RFC and rejected by modern browsers."
                ),
                recommendation=(
                    "Disable TLS 1.0 and TLS 1.1 (and all SSL versions) in your web server "
                    "configuration. Support only TLS 1.2 and TLS 1.3."
                ),
                evidence=f"Negotiated protocol: {tls_ver}",
                owasp="A02:2021 - Cryptographic Failures",
            ))
        else:
            findings.append(self._finding(
                check=self.NAME,
                risk_level="Info",
                title=f"TLS Protocol: {tls_ver}",
                detail=f"Server negotiated {tls_ver}.",
                recommendation="",
                evidence=f"Protocol: {tls_ver}",
                owasp="A02:2021 - Cryptographic Failures",
            ))

        # --- Cipher suite ---
        if cipher:
            cipher_name, _, key_bits = cipher
            weak = any(frag in cipher_name for frag in _WEAK_CIPHER_FRAGS)
            if weak:
                findings.append(self._finding(
                    check=self.NAME,
                    risk_level="High",
                    title=f"Weak Cipher Suite: {cipher_name}",
                    detail=(
                        f"The negotiated cipher '{cipher_name}' uses a broken or weak algorithm. "
                        "Attackers with sufficient resources can decrypt recorded traffic."
                    ),
                    recommendation=(
                        "Configure the server to prefer AEAD ciphers with forward secrecy: "
                        "TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256 (TLS 1.3), "
                        "or ECDHE-ECDSA-AES256-GCM-SHA384 (TLS 1.2)."
                    ),
                    evidence=f"Cipher: {cipher_name} ({key_bits}-bit key)",
                    owasp="A02:2021 - Cryptographic Failures",
                ))
            else:
                findings.append(self._finding(
                    check=self.NAME,
                    risk_level="Info",
                    title=f"Cipher Suite: {cipher_name}",
                    detail=f"Negotiated cipher: {cipher_name} ({key_bits}-bit key).",
                    recommendation="",
                    evidence=f"Cipher: {cipher_name}",
                    owasp="A02:2021 - Cryptographic Failures",
                ))

        # --- Certificate expiry ---
        if cert:
            findings.extend(self._check_cert_expiry(cert))

        return findings

    def _check_cert_expiry(self, cert: dict) -> List[Finding]:
        findings: List[Finding] = []
        not_after = cert.get("notAfter", "")
        if not not_after:
            return findings

        try:
            expire = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(
                tzinfo=timezone.utc
            )
            days = (expire - datetime.now(timezone.utc)).days
        except ValueError:
            return findings

        if days < _CERT_CRITICAL_DAYS:
            findings.append(self._finding(
                check=self.NAME,
                risk_level="Critical",
                title=f"TLS Certificate Expired ({abs(days)} Days Ago)",
                detail=(
                    f"The TLS certificate expired {abs(days)} day(s) ago on {not_after}. "
                    "All modern browsers will refuse the connection and display a full-page "
                    "security warning, making the site inaccessible to users."
                ),
                recommendation=(
                    "Renew the certificate immediately. "
                    "Automate future renewals with Let's Encrypt/Certbot (ACME protocol) "
                    "to prevent recurrence."
                ),
                evidence=f"notAfter: {not_after} — expired {abs(days)} day(s) ago",
                owasp="A02:2021 - Cryptographic Failures",
            ))
        elif days < _CERT_WARN_DAYS:
            findings.append(self._finding(
                check=self.NAME,
                risk_level="High",
                title=f"TLS Certificate Expires in {days} Days",
                detail=(
                    f"The TLS certificate expires in {days} day(s) on {not_after}. "
                    "After expiry, browsers will block access. This often goes unnoticed "
                    "until users start reporting errors."
                ),
                recommendation=(
                    "Renew the certificate now. "
                    "Set up automated renewal (Let's Encrypt + Certbot) and monitoring alerts."
                ),
                evidence=f"notAfter: {not_after}",
                owasp="A02:2021 - Cryptographic Failures",
            ))
        else:
            findings.append(self._finding(
                check=self.NAME,
                risk_level="Info",
                title=f"TLS Certificate Valid ({days} Days Remaining)",
                detail=f"Certificate is valid until {not_after}.",
                recommendation="",
                evidence=f"notAfter: {not_after}",
                owasp="A02:2021 - Cryptographic Failures",
            ))

        return findings


# ---------------------------------------------------------------------------
# Check 3 — Directory Listing Detection
# ---------------------------------------------------------------------------

_PROBE_PATHS: Tuple[str, ...] = (
    "/admin/",
    "/administrator/",
    "/uploads/",
    "/upload/",
    "/files/",
    "/backup/",
    "/backups/",
    "/logs/",
    "/log/",
    "/config/",
    "/conf/",
    "/data/",
    "/tmp/",
    "/temp/",
    "/test/",
    "/old/",
    "/archive/",
    "/private/",
    "/secret/",
    "/db/",
    "/sql/",
    "/dump/",
    "/.git/",
    "/static/",
    "/assets/",
    "/media/",
    "/include/",
    "/includes/",
    "/src/",
    "/dev/",
    "/staging/",
)

# Patterns that indicate a server-generated directory listing in the response body
_LISTING_PATTERNS: Tuple[re.Pattern, ...] = (
    re.compile(r"<title>\s*Index of\s*/", re.I),
    re.compile(r"<h1>\s*Index of\s*/",   re.I),
    re.compile(r"Directory listing for\s*/", re.I),
    re.compile(r"\[To Parent Directory\]",   re.I),
    re.compile(r'<a href="\?C=N[;&]O=',      re.I),   # Apache column-sort links
    re.compile(r"<a href=\"\.\./\">Parent Directory</a>", re.I),
    re.compile(r'<a href="\.\./?">\.\./</a>', re.I),   # Nginx autoindex
)

# Paths whose HTTP 200 is always a concern (even without a visible listing)
_ALWAYS_SENSITIVE: frozenset = frozenset({
    "/admin/", "/administrator/", "/backup/", "/backups/",
    "/config/", "/conf/", "/db/", "/sql/", "/dump/",
    "/private/", "/secret/", "/.git/",
})

# Paths where a 403 is still worth noting (resource confirmed to exist)
_SENSITIVE_403: frozenset = frozenset({
    "/admin/", "/backup/", "/backups/", "/config/",
    "/private/", "/secret/", "/.git/",
})


class DirectoryListingCheck(BaseCheck):
    """
    Probes a curated set of commonly sensitive paths for:
      - Active directory listings (server autoindex enabled)
      - Accessible sensitive directories (HTTP 200)
      - Confirmed-but-forbidden paths (HTTP 403)

    Each path is probed concurrently with its own session to avoid
    thread-safety issues with a shared session.
    """

    NAME = "Directory Listing"

    def __init__(self, timeout: int = 10, max_workers: int = 10) -> None:
        super().__init__(timeout)
        self._max_workers = max_workers

    def run(self, ctx: ScanContext) -> List[Finding]:
        base = ctx.url.rstrip("/")
        findings: List[Finding] = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_map = {
                executor.submit(self._probe_path, base, path): path
                for path in _PROBE_PATHS
            }
            for future in as_completed(future_map):
                try:
                    result = future.result()
                    if result is not None:
                        findings.append(result)
                except Exception:
                    pass

        return sorted(findings, key=lambda f: f.rank)

    def _probe_path(self, base: str, path: str) -> Optional[Finding]:
        url = base + path
        try:
            session = self._new_session()
            response = session.get(url, timeout=self.timeout, allow_redirects=False)
        except Exception:
            return None

        status = response.status_code

        if status not in (200, 403):
            return None

        body      = response.text[:6000] if response.text else ""
        is_listed = any(pat.search(body) for pat in _LISTING_PATTERNS)

        # --- Active directory listing ---
        if status == 200 and is_listed:
            return self._finding(
                check=self.NAME,
                risk_level="High",
                title=f"Directory Listing Enabled: {path}",
                detail=(
                    f"The server is generating an automatic file listing for '{path}'. "
                    "Attackers can enumerate every file and subdirectory, "
                    "discovering backups, configuration files, and source code "
                    "that were never intended to be publicly accessible."
                ),
                recommendation=(
                    "Disable server autoindex: "
                    "Apache → Options -Indexes in httpd.conf/VirtualHost; "
                    "Nginx → remove 'autoindex on'; "
                    "IIS → disable Directory Browsing in site settings."
                ),
                evidence=f"HTTP 200 at {url} — directory listing markup detected in response body",
                owasp="A05:2021 - Security Misconfiguration",
            )

        # --- Accessible sensitive path (no listing, but still open) ---
        if status == 200 and path in _ALWAYS_SENSITIVE:
            return self._finding(
                check=self.NAME,
                risk_level="Medium",
                title=f"Sensitive Path Accessible: {path}",
                detail=(
                    f"The path '{path}' returned HTTP 200 (OK). "
                    "Even without an active directory listing, this path may expose "
                    "an administrative interface, database dump, or configuration file."
                ),
                recommendation=(
                    "Restrict access via authentication and/or firewall rules. "
                    "If the resource is not needed, remove it from the web root entirely."
                ),
                evidence=f"HTTP 200 at {url}",
                owasp="A01:2021 - Broken Access Control",
            )

        # --- 403: resource exists but is forbidden ---
        if status == 403 and path in _SENSITIVE_403:
            return self._finding(
                check=self.NAME,
                risk_level="Low",
                title=f"Sensitive Path Confirmed (Forbidden): {path}",
                detail=(
                    f"The path '{path}' returned HTTP 403 (Forbidden), confirming "
                    "the resource exists on the server. A 403 relies on web-server-level "
                    "ACLs; a misconfiguration or path-traversal technique could bypass it."
                ),
                recommendation=(
                    "Ensure access controls are enforced at the application layer "
                    "in addition to the web server. Consider moving sensitive resources "
                    "outside the web root if public access is never needed."
                ),
                evidence=f"HTTP 403 at {url}",
                owasp="A01:2021 - Broken Access Control",
            )

        return None


# ---------------------------------------------------------------------------
# Check 4 — HTTP Response Analysis
# ---------------------------------------------------------------------------

_SLOW_WARN_MS   = 3_000    # 3 s — worth noting
_SLOW_CRIT_MS   = 10_000   # 10 s — significant
_MAX_REDIRECT_HOPS = 5


class HttpResponseCheck(BaseCheck):
    """
    Analyses the initial HTTP response for:
      - Abnormal response times
      - Redirect chain length and cross-domain hops
      - Anomalous HTTP status codes (4xx/5xx)
      - Mixed content (HTTP resources on an HTTPS page)
    """

    NAME = "HTTP Response"

    def run(self, ctx: ScanContext) -> List[Finding]:
        findings: List[Finding] = []
        findings.extend(self._check_response_time(ctx))
        findings.extend(self._check_redirect_chain(ctx))
        findings.extend(self._check_status_code(ctx))
        findings.extend(self._check_mixed_content(ctx))
        return findings

    # --- response time ---

    def _check_response_time(self, ctx: ScanContext) -> List[Finding]:
        ms = ctx.response_time_ms

        if ms >= _SLOW_CRIT_MS:
            return [self._finding(
                check=self.NAME,
                risk_level="Medium",
                title=f"Critically Slow Response ({ms:.0f} ms)",
                detail=(
                    f"The server took {ms:.0f} ms to respond. "
                    "Extreme latency can indicate server overload, blocking I/O, "
                    "or — in vulnerability assessments — a blind SSRF or time-based injection."
                ),
                recommendation=(
                    "Profile backend processing time. Implement request timeouts, "
                    "caching layers, and capacity scaling. Investigate whether the delay "
                    "is reproducible (potential injection indicator)."
                ),
                evidence=f"Response time: {ms:.0f} ms (threshold: {_SLOW_CRIT_MS} ms)",
                owasp="A05:2021 - Security Misconfiguration",
            )]

        if ms >= _SLOW_WARN_MS:
            return [self._finding(
                check=self.NAME,
                risk_level="Low",
                title=f"Slow Response ({ms:.0f} ms)",
                detail=(
                    f"The server responded in {ms:.0f} ms, above the {_SLOW_WARN_MS} ms warning "
                    "threshold. Slow responses degrade user experience and can worsen under load."
                ),
                recommendation="Review backend query performance, caching strategy, and infrastructure sizing.",
                evidence=f"Response time: {ms:.0f} ms",
                owasp="N/A",
            )]

        return [self._finding(
            check=self.NAME,
            risk_level="Info",
            title=f"Response Time: {ms:.0f} ms",
            detail=f"Server responded in {ms:.0f} ms.",
            recommendation="",
            evidence=f"Response time: {ms:.0f} ms",
            owasp="N/A",
        )]

    # --- redirect chain ---

    def _check_redirect_chain(self, ctx: ScanContext) -> List[Finding]:
        findings: List[Finding] = []
        history: List[requests.Response] = list(ctx.response.history)

        if not history:
            return findings

        # Build a human-readable hop list
        hops = [f"{r.status_code}  {r.url}" for r in history]
        hops.append(f"{ctx.response.status_code}  {ctx.response.url}  ← final")
        chain_str = "\n  ".join(hops)

        # Too many hops
        if len(history) > _MAX_REDIRECT_HOPS:
            findings.append(self._finding(
                check=self.NAME,
                risk_level="Medium",
                title=f"Excessive Redirect Chain ({len(history)} Hops)",
                detail=(
                    f"The request followed {len(history)} redirect(s) before reaching "
                    "the final URL. Long chains add latency and can mask open-redirect "
                    "vulnerabilities when intermediate targets accept arbitrary next URLs."
                ),
                recommendation=(
                    "Reduce the redirect chain to one or two hops (ideally just HTTP→HTTPS). "
                    "Update internal links and bookmarks to point directly to the final URL."
                ),
                evidence=f"Redirect chain ({len(history)} hops):\n  {chain_str}",
                owasp="A01:2021 - Broken Access Control",
            ))

        # HTTP → HTTPS upgrade
        first_url = history[0].url if history else ""
        final_url = ctx.response.url
        if first_url.startswith("http://") and final_url.startswith("https://"):
            findings.append(self._finding(
                check=self.NAME,
                risk_level="Info",
                title="HTTP → HTTPS Redirect Present",
                detail=(
                    "The server redirects HTTP requests to HTTPS. "
                    "The first HTTP request is still unprotected — an on-path attacker "
                    "can intercept it before the redirect fires. HSTS eliminates this gap "
                    "for returning browsers."
                ),
                recommendation=(
                    "Pair this redirect with an HSTS header (max-age ≥ 31536000; "
                    "includeSubDomains) so browsers skip the unencrypted first request entirely."
                ),
                evidence=f"{history[0].status_code} {first_url}  →  {final_url}",
                owasp="A02:2021 - Cryptographic Failures",
            ))

        # Cross-domain hop
        final_host = urllib.parse.urlparse(final_url).hostname or ""
        for r in history:
            hop_host = urllib.parse.urlparse(r.url).hostname or ""
            if hop_host and final_host and hop_host != final_host:
                findings.append(self._finding(
                    check=self.NAME,
                    risk_level="Low",
                    title="Cross-Domain Redirect Detected",
                    detail=(
                        f"The redirect chain crosses a domain boundary "
                        f"({hop_host} → … → {final_host}). "
                        "If a redirect target can be influenced by user input, "
                        "this may represent an open redirect vulnerability."
                    ),
                    recommendation=(
                        "Audit redirect logic. Whitelist permitted destination domains "
                        "explicitly. Never construct redirect URLs from unvalidated user input."
                    ),
                    evidence=f"Cross-domain: {r.url}  →  {final_url}",
                    owasp="A01:2021 - Broken Access Control",
                ))
                break   # report once per chain

        return findings

    # --- status code ---

    def _check_status_code(self, ctx: ScanContext) -> List[Finding]:
        code = ctx.response.status_code

        _ANOMALIES: Dict[int, Tuple[str, str, str, str]] = {
            401: (
                "Low",
                "HTTP 401 — Authentication Required",
                "The server requires authentication. If this endpoint should be public, "
                "investigate why it is gated. Confirm that HTTP Basic Auth (if used) "
                "is transmitted over TLS and paired with account-lockout controls.",
                "Prefer token-based or session-based auth over HTTP Basic. Ensure credentials "
                "are only accepted over HTTPS.",
            ),
            403: (
                "Low",
                "HTTP 403 — Forbidden",
                "Access is forbidden with the current credentials. The resource exists "
                "but access is blocked at the server layer. Forced browsing or header "
                "manipulation may bypass certain server-side ACLs.",
                "Enforce access controls at the application layer (not just web-server ACLs). "
                "Validate authorization on every request.",
            ),
            500: (
                "Medium",
                "HTTP 500 — Internal Server Error",
                "The server encountered an unhandled error. In many configurations this "
                "triggers a verbose error page exposing stack traces, database queries, "
                "or internal file paths that help attackers map the application internals.",
                "Enable custom error pages that show no technical detail. "
                "Log full errors server-side only.",
            ),
            502: (
                "Low",
                "HTTP 502 — Bad Gateway",
                "The upstream service is unreachable or returned an invalid response. "
                "May expose proxy configuration details in some error pages.",
                "Investigate upstream health. Configure the proxy to return a generic error page.",
            ),
            503: (
                "Low",
                "HTTP 503 — Service Unavailable",
                "The server is overloaded or in maintenance mode. "
                "Ensure the maintenance page does not disclose version or path information.",
                "Return a custom maintenance page. Implement health checks and capacity alerts.",
            ),
        }

        if code in _ANOMALIES:
            risk, title, detail, rec = _ANOMALIES[code]
            return [self._finding(
                check=self.NAME,
                risk_level=risk,
                title=title,
                detail=detail,
                recommendation=rec,
                evidence=f"Final HTTP status: {code}",
                owasp="A05:2021 - Security Misconfiguration",
            )]

        return [self._finding(
            check=self.NAME,
            risk_level="Info",
            title=f"HTTP Status: {code}",
            detail=f"Server returned HTTP {code}.",
            recommendation="",
            evidence=f"HTTP {code}",
            owasp="N/A",
        )]

    # --- mixed content ---

    def _check_mixed_content(self, ctx: ScanContext) -> List[Finding]:
        if ctx.parsed.scheme != "https":
            return []

        body = ctx.response.text[:30_000] if ctx.response.text else ""
        # Match src=, href=, action=, url() pointing to http://
        refs = re.findall(
            r'(?:src|href|action)\s*=\s*["\']?\s*(http://[^\s"\'<>]+)',
            body, re.I,
        )
        # Also catch CSS url(http://...)
        refs += re.findall(r"url\(\s*['\"]?(http://[^)'\"]+)", body, re.I)

        unique_refs = list(dict.fromkeys(refs))   # deduplicate, preserve order
        if not unique_refs:
            return []

        sample = unique_refs[:8]
        return [self._finding(
            check=self.NAME,
            risk_level="Medium",
            title=f"Mixed Content: {len(unique_refs)} HTTP Resource(s) on HTTPS Page",
            detail=(
                f"The HTTPS page references {len(unique_refs)} resource(s) via plain HTTP. "
                "Browsers block active mixed content (scripts, iframes) and warn on passive "
                "(images, audio). An on-path attacker can intercept and tamper with HTTP "
                "resources to inject malicious content into the HTTPS page."
            ),
            recommendation=(
                "Change all resource URLs to HTTPS or use protocol-relative URLs (//example.com/…). "
                "Enforce HTTPS at the asset/CDN level and add a CSP upgrade-insecure-requests directive."
            ),
            evidence="HTTP references (sample):\n  " + "\n  ".join(sample),
            owasp="A02:2021 - Cryptographic Failures",
        )]


# ---------------------------------------------------------------------------
# WebScanner — orchestrator
# ---------------------------------------------------------------------------

class WebScanner:
    """
    Fetches the target URL once, then runs all check classes concurrently
    using ThreadPoolExecutor.  Returns a list of reporter-compatible dicts,
    sorted by risk level (Critical first).
    """

    def __init__(
        self,
        timeout:     int  = 10,
        verbose:     bool = False,
        max_workers: int  = 4,
    ) -> None:
        self.timeout     = timeout
        self.verbose     = verbose
        self.max_workers = max_workers

    def scan(self, url: str) -> List[Dict[str, Any]]:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        parsed = urllib.parse.urlparse(url)

        # --- Initial fetch (shared, read-only for all checks) ---
        session = requests.Session()
        session.headers["User-Agent"] = _UA
        session.verify = False
        session.max_redirects = 10

        try:
            t0       = time.monotonic()
            response = session.get(url, timeout=self.timeout, allow_redirects=True)
            elapsed  = (time.monotonic() - t0) * 1000.0

        except requests.exceptions.SSLError as exc:
            return [self._error_finding("SSL Error", "High", str(exc),
                                        "A02:2021 - Cryptographic Failures")]
        except requests.exceptions.ConnectionError as exc:
            return [self._error_finding("Connection Failed", "Critical", str(exc), "N/A")]
        except requests.exceptions.Timeout:
            return [self._error_finding(
                "Connection Timed Out", "Medium",
                f"No response within {self.timeout}s.", "N/A",
            )]

        ctx = ScanContext(
            url=url,
            parsed=parsed,
            response=response,
            response_time_ms=elapsed,
            timeout=self.timeout,
        )

        # --- Run all checks concurrently ---
        checks: List[BaseCheck] = [
            SecurityHeadersCheck(self.timeout),
            TlsCheck(self.timeout),
            DirectoryListingCheck(self.timeout, max_workers=10),
            HttpResponseCheck(self.timeout),
        ]

        all_findings: List[Finding] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {executor.submit(chk.run, ctx): chk for chk in checks}
            for future in as_completed(future_map):
                chk = future_map[future]
                try:
                    all_findings.extend(future.result())
                except Exception as exc:
                    all_findings.append(Finding(
                        check=chk.NAME,
                        risk_level="Info",
                        title=f"Internal Error in {chk.NAME}",
                        detail=f"An unexpected error occurred: {str(exc)[:180]}",
                        recommendation="Report this to the DefenseScan maintainer.",
                        evidence=str(exc)[:180],
                    ))

        all_findings.sort(key=lambda f: f.rank)
        return [f.to_report() for f in all_findings]

    @staticmethod
    def _error_finding(title: str, risk: str, evidence: str, owasp: str) -> Dict[str, Any]:
        return Finding(
            check="Connection",
            risk_level=risk,
            title=title,
            detail=evidence[:200],
            recommendation="Verify the URL and network connectivity.",
            evidence=evidence[:200],
            owasp=owasp,
        ).to_report()
