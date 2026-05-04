from __future__ import annotations
import psutil
import socket
import ssl
import json
import struct
import time
import logging
import ctypes
import sys
import os
import argparse
import threading
import concurrent.futures
from collections import deque
from datetime import datetime
from logging.handlers import RotatingFileHandler
from urllib.parse import urlsplit, urlunsplit

# ──────────────────────────────────────────
# 설정
# ──────────────────────────────────────────
COLLECT_INTERVAL = 0.5                  # 백그라운드 수집 주기 (초)
DISPLAY_INTERVAL = 5                    # 터미널 출력 주기 (초)
PROTO_TIMEOUT    = 0.4                  # 프로토콜 탐지 소켓 타임아웃
MAX_WORKERS      = 20                   # 병렬 스캔 스레드 수
MAX_LOG_BYTES    = 10 * 1024 * 1024     # 로그 rotate 기준 (10 MB)
MAX_HISTORY      = 20_000               # 세션 연결 이력 최대 보관 건수
MAX_HTTP_LOG     = 5_000                # HTTP/HTTPS 캡처 이력 최대 보관 건수
ACTIVE_PROBE     = False                # 서비스에 직접 접속하는 웹 탐지 기본 비활성화
ENABLE_SNIFFER   = True                 # raw socket HTTP/HTTPS 캡처 사용 여부
ENABLE_RDNS      = True                 # 원격 IP reverse DNS 조회 사용 여부
JSONL_LOG        = False                # 스냅샷을 JSON Lines append 로그로 저장
REDACT_URL_QUERY = False                # URL query 문자열 마스킹

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
LOG_TEXT  = os.path.join(BASE_DIR, "network_monitor.log")
LOG_JSON  = os.path.join(BASE_DIR, "network_log.json")
LOG_JSONL = os.path.join(BASE_DIR, "network_log.jsonl")

# Windows 시스템 프로세스 이름 (소문자) — 기본적으로 모니터링 제외
SYSTEM_PROCESS_NAMES = {
    'system', 'system idle process', 'idle', 'registry',
    'smss.exe', 'csrss.exe', 'wininit.exe', 'services.exe',
    'lsass.exe', 'svchost.exe', 'dwm.exe', 'winlogon.exe',
    'fontdrvhost.exe', 'sihost.exe', 'taskhostw.exe',
    'spoolsv.exe', 'searchindexer.exe', 'searchhost.exe',
    'wmiprvse.exe', 'dllhost.exe', 'conhost.exe', 'ctfmon.exe',
    'ntoskrnl.exe', 'msdtc.exe', 'lsm.exe', 'audiodg.exe',
    'wlanext.exe', 'securityhealthservice.exe', 'runtimebroker.exe',
    'startmenuexperiencehost.exe', 'textinputhost.exe', 'applicationframehost.exe',
    'msseces.exe', 'sppsvc.exe', 'wuauclt.exe', 'trustedinstaller.exe',
    'tiworker.exe', 'msiexec.exe', 'taskeng.exe', 'taskhost.exe',
}

_WINDIR = os.environ.get('WINDIR', 'C:\\Windows').lower()


def _configure_console_encoding() -> None:
    """Windows 콘솔에서 한글/유니코드 출력이 예외를 내지 않도록 보정한다."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_configure_console_encoding()


# ──────────────────────────────────────────
# 텍스트 로거
# ──────────────────────────────────────────
def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("net_monitor")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    fh = RotatingFileHandler(LOG_TEXT, maxBytes=MAX_LOG_BYTES, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

logger = _setup_logger()


# ──────────────────────────────────────────
# 관리자 권한 확인
# ──────────────────────────────────────────
def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ──────────────────────────────────────────
# 시스템 프로세스 판별
# ──────────────────────────────────────────
def _is_system_process(name: str, exe: str, pid: int) -> bool:
    """Windows 시스템 프로세스이면 True를 반환한다."""
    if pid in (0, 4):
        return True
    if name.lower() in SYSTEM_PROCESS_NAMES:
        return True
    if exe and exe.lower().startswith(_WINDIR):
        return True
    return False


# ──────────────────────────────────────────
# 프로토콜 정밀 검증 (HTTP / HTTPS)
# ──────────────────────────────────────────
def check_web_protocol(ip: str, port: int, timeout: float = PROTO_TIMEOUT) -> str | None:
    """실제 소켓 통신으로 HTTP 또는 HTTPS 여부를 판별한다."""
    # HTTPS (SSL/TLS) — 공개 API 사용, 인증서 검증 비활성화
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((ip, port), timeout=timeout) as raw:
            with ctx.wrap_socket(raw, server_hostname=ip):
                return "HTTPS"
    except Exception:
        pass

    # HTTP
    try:
        with socket.create_connection((ip, port), timeout=timeout) as s:
            s.sendall(b"HEAD / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
            data = s.recv(64)
            if b"HTTP" in data or b"html" in data.lower():
                return "HTTP"
    except Exception:
        pass

    return None


def _connectable_ip(ip: str) -> str:
    """바인딩 주소(0.0.0.0 등)를 실제 연결 가능한 주소로 변환한다."""
    if ip in ('0.0.0.0', ''):
        return '127.0.0.1'
    if ip == '::':
        return '::1'
    return ip


# ──────────────────────────────────────────
# 프로세스 정보 캐시 구축
# ──────────────────────────────────────────
def _build_proc_cache() -> dict[int, dict]:
    """PID → {name, exe, is_system} 매핑 캐시를 구성한다."""
    cache: dict[int, dict] = {}
    for p in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            pid  = p.info['pid']
            name = p.info['name'] or 'Unknown'
            exe  = p.info['exe']  or ''
            cache[pid] = {
                'name':      name,
                'exe':       exe,
                'is_system': _is_system_process(name, exe, pid),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return cache


# ──────────────────────────────────────────
# 공유 상태 (백그라운드 스레드 <-> 메인 루프)
# ──────────────────────────────────────────
_lock         = threading.Lock()
_accumulated: dict[tuple, dict] = {}  # 수집된 연결 누적 (5초마다 초기화)
_history:     deque[dict] = deque(maxlen=MAX_HISTORY)   # 세션 연결 이력 (상한 보관)
_http_log:    deque[dict] = deque(maxlen=MAX_HTTP_LOG)   # HTTP 요청 이력 (상한 보관)
_http_lock    = threading.Lock()
_web_lock     = threading.Lock()
_web_cache:   dict[str, str] = {}     # "ip:port" -> "HTTP"|"HTTPS" (확인된 것만)
_web_pending: set[str] = set()        # 현재 탐지 중인 포트 키
_dns_lock     = threading.Lock()
_dns_cache:   dict[str, str | None] = {}
_dns_pending: set[str] = set()
_stop_event   = threading.Event()

HTTP_METHODS = {b'GET ', b'POST', b'PUT ', b'PATC', b'DELE', b'HEAD', b'OPTI'}

# import 시 부작용 방지: 스레드풀은 main()에서 초기화
_web_executor:  concurrent.futures.ThreadPoolExecutor | None = None
_rdns_executor: concurrent.futures.ThreadPoolExecutor | None = None


def _redact_url_query(url: str) -> str:
    if not REDACT_URL_QUERY:
        return url
    parts = urlsplit(url)
    if not parts.query:
        return url
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "REDACTED", parts.fragment))


# ──────────────────────────────────────────
# 패킷 파서 (raw socket 캡처용)
# ──────────────────────────────────────────
def _extract_ip_tcp(data: bytes) -> tuple | None:
    """IP+TCP 헤더를 파싱해 (src_ip, src_port, dst_ip, dst_port, payload)를 반환."""
    try:
        if len(data) < 20:
            return None
        iph = struct.unpack('!BBHHHBBH4s4s', data[:20])
        if iph[6] != 6:            # TCP 만
            return None
        ip_hdr_len  = (iph[0] & 0xF) * 4
        src_ip      = socket.inet_ntoa(iph[8])
        dst_ip      = socket.inet_ntoa(iph[9])

        if len(data) < ip_hdr_len + 20:
            return None
        tcph = struct.unpack('!HHLLBBHHH', data[ip_hdr_len:ip_hdr_len + 20])
        src_port    = tcph[0]
        dst_port    = tcph[1]
        tcp_hdr_len = (tcph[4] >> 4) * 4

        payload = data[ip_hdr_len + tcp_hdr_len:]
        return src_ip, src_port, dst_ip, dst_port, payload
    except Exception:
        return None


def _parse_http_request(data: bytes) -> dict | None:
    """IP 패킷에서 HTTP 요청 정보를 추출한다."""
    parsed = _extract_ip_tcp(data)
    if parsed is None:
        return None
    src_ip, src_port, dst_ip, dst_port, payload = parsed

    if len(payload) < 8 or payload[:4] not in HTTP_METHODS:
        return None

    try:
        text      = payload.split(b'\r\n\r\n')[0].decode('utf-8', errors='replace')
        lines     = text.split('\r\n')
        req_parts = lines[0].split(' ')
        if len(req_parts) < 2:
            return None
        method = req_parts[0]
        path   = req_parts[1]

        host = dst_ip
        for line in lines[1:]:
            if line.lower().startswith('host:'):
                host = line.split(':', 1)[1].strip()
                break

        url = _redact_url_query(f"http://{host}{path}")
        return {
            'timestamp': datetime.now().isoformat(timespec='milliseconds'),
            'scheme':    'http',
            'src_ip':    src_ip,
            'src_port':  src_port,
            'dst_ip':    dst_ip,
            'dst_port':  dst_port,
            'method':    method,
            'host':      host,
            'path':      path,
            'url':       url,
        }
    except Exception:
        return None


def _parse_tls_sni(data: bytes) -> dict | None:
    """TLS ClientHello 패킷에서 SNI(도메인명)를 추출한다.
    SNI는 평문이므로 암호화 여부와 무관하게 읽을 수 있다."""
    parsed = _extract_ip_tcp(data)
    if parsed is None:
        return None
    src_ip, src_port, dst_ip, dst_port, payload = parsed

    try:
        # TLS Record: ContentType=0x16(Handshake), Version, Length
        if len(payload) < 6 or payload[0] != 0x16:
            return None

        # Handshake: Type=0x01(ClientHello)
        hs = payload[5:]
        if len(hs) < 4 or hs[0] != 0x01:
            return None

        # ClientHello body: skip HandshakeType(1)+Length(3)+Version(2)+Random(32)
        offset = 4 + 2 + 32

        # Session ID
        if len(hs) < offset + 1:
            return None
        offset += 1 + hs[offset]

        # Cipher Suites
        if len(hs) < offset + 2:
            return None
        offset += 2 + struct.unpack('!H', hs[offset:offset+2])[0]

        # Compression Methods
        if len(hs) < offset + 1:
            return None
        offset += 1 + hs[offset]

        # Extensions length
        if len(hs) < offset + 2:
            return None
        ext_end = offset + 2 + struct.unpack('!H', hs[offset:offset+2])[0]
        offset += 2

        # 개별 Extension 탐색
        while offset + 4 <= ext_end and offset + 4 <= len(hs):
            ext_type = struct.unpack('!H', hs[offset:offset+2])[0]
            ext_len  = struct.unpack('!H', hs[offset+2:offset+4])[0]
            offset  += 4

            if ext_type == 0x0000:  # SNI extension
                # ServerNameList(2) + NameType(1) + NameLen(2) + Name
                if ext_len >= 5 and hs[offset+2] == 0x00:
                    name_len = struct.unpack('!H', hs[offset+3:offset+5])[0]
                    sni = hs[offset+5:offset+5+name_len].decode('ascii', errors='replace')
                    host = f"{sni}:{dst_port}" if dst_port not in (443,) else sni
                    return {
                        'timestamp': datetime.now().isoformat(timespec='milliseconds'),
                        'scheme':    'https',
                        'src_ip':    src_ip,
                        'src_port':  src_port,
                        'dst_ip':    dst_ip,
                        'dst_port':  dst_port,
                        'method':    '(TLS)',
                        'host':      sni,
                        'path':      '(encrypted)',
                        'url':       f"https://{host}",
                    }
            offset += ext_len

    except Exception:
        pass
    return None


# ──────────────────────────────────────────
# 스니퍼 스레드 팩토리
# bind_ip 별로 독립 raw socket 생성 — loopback + 외부 인터페이스 모두 커버
# ──────────────────────────────────────────
def _sniff_on(bind_ip: str) -> None:
    """지정된 IP 인터페이스에서 HTTP/HTTPS 패킷을 캡처한다."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
        sock.bind((bind_ip, 0))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
        sock.settimeout(1.0)
    except Exception as e:
        logger.warning(f"스니퍼 비활성 [{bind_ip}] (관리자 권한 필요): {e}")
        return

    logger.info(f"스니퍼 시작 [{bind_ip}] — HTTP + HTTPS(SNI) 캡처 중")

    try:
        while not _stop_event.is_set():
            try:
                raw, _ = sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                # 소켓이 닫혔거나 인터페이스가 사라진 경우
                break

            entry = _parse_http_request(raw) or _parse_tls_sni(raw)
            if entry is None:
                continue

            with _http_lock:
                _http_log.append(entry)
            scheme = entry['scheme'].upper()
            if scheme == 'HTTP':
                logger.info(
                    f"[{scheme}] {entry['src_ip']}:{entry['src_port']} -> "
                    f"{entry['method']} {entry['url']}"
                )
            else:
                logger.info(
                    f"[{scheme}] {entry['src_ip']}:{entry['src_port']} -> "
                    f"{entry['url']}  (경로 암호화)"
                )
    finally:
        try:
            sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
            sock.close()
        except Exception:
            pass
        logger.info(f"스니퍼 종료 [{bind_ip}]")


def _http_sniffer() -> None:
    """loopback + 외부 인터페이스 모두 캡처하는 스니퍼를 시작한다."""
    bind_ips: list[str] = ['127.0.0.1']
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip not in bind_ips and not ip.startswith('127.'):
                bind_ips.append(ip)
    except Exception:
        pass

    threads = []
    for ip in bind_ips:
        t = threading.Thread(target=_sniff_on, args=(ip,), daemon=True,
                             name=f"sniffer-{ip}")
        t.start()
        threads.append(t)

    # stop_event로 종료됨; 최대 3초 대기해 무한 블록 방지
    for t in threads:
        t.join(timeout=3)


# ──────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────
def _normalize_filters(names: list[str] | None) -> set[str] | None:
    if not names:
        return None
    result: set[str] = set()
    for n in names:
        n = n.strip().lower()
        if not n:
            continue
        result.add(n)
        if not n.endswith('.exe'):
            result.add(n + '.exe')
    # 공백만 전달된 경우 빈 set 대신 None 반환 (호출부의 falsy 검사와 일관성 유지)
    return result or None


def _check_and_cache(ip: str, port: int) -> None:
    """단일 포트에 대해 HTTP/HTTPS 탐지 후 캐시에 저장. 탐지 스레드풀에서 실행된다."""
    key = f"{ip}:{port}"
    try:
        proto = check_web_protocol(_connectable_ip(ip), port)
        if proto:
            with _web_lock:
                _web_cache[key] = proto
    except Exception:
        pass
    finally:
        with _web_lock:
            _web_pending.discard(key)


def _submit_web_check(ip: str, port: int) -> None:
    """캐시·진행 중이 아닌 포트만 웹 탐지 태스크를 제출한다."""
    if not ACTIVE_PROBE or _web_executor is None:
        return
    key = f"{ip}:{port}"
    with _web_lock:
        if key in _web_cache or key in _web_pending:
            return
        _web_pending.add(key)
    try:
        _web_executor.submit(_check_and_cache, ip, port)
    except Exception:
        # submit 실패 시 pending에서 제거해 영구 오염 방지
        with _web_lock:
            _web_pending.discard(key)


def _reverse_dns(ip: str) -> str | None:
    """원격 IP의 cached reverse DNS를 반환하고, 필요하면 백그라운드 조회를 예약한다."""
    if not ENABLE_RDNS or _rdns_executor is None:
        return None
    if any(ip.startswith(pfx) for pfx in ('127.', '10.', '192.168.', '172.16.', '172.17.',
                                          '172.18.', '172.19.', '172.20.', '172.21.',
                                          '172.22.', '172.23.', '172.24.', '172.25.',
                                          '172.26.', '172.27.', '172.28.', '172.29.',
                                          '172.30.', '172.31.', 'fe80')):
        return None

    with _dns_lock:
        if ip in _dns_cache:
            return _dns_cache[ip]
        if ip in _dns_pending:
            return None
        _dns_pending.add(ip)

    try:
        _rdns_executor.submit(_resolve_dns_worker, ip)
    except Exception:
        # submit 실패 시 pending에서 제거해 영구 오염 방지
        with _dns_lock:
            _dns_pending.discard(ip)
    return None


def _resolve_dns_worker(ip: str) -> None:
    try:
        domain = socket.gethostbyaddr(ip)[0]
    except Exception:
        domain = None

    with _dns_lock:
        _dns_cache[ip] = domain
        _dns_pending.discard(ip)


# ──────────────────────────────────────────
# 백그라운드 수집 스레드
# 0.5초마다 연결을 수집해 _accumulated에 누적하고,
# 새 LISTEN 포트를 발견하면 즉시 웹 프로토콜 탐지를 시작한다.
# ──────────────────────────────────────────
def _collector(filter_names: list[str] | None, include_system: bool) -> None:
    filters = _normalize_filters(filter_names)
    proc_cache: dict[int, dict] = _build_proc_cache()
    proc_refresh_counter = 0

    while not _stop_event.is_set():
        try:
            proc_refresh_counter += 1
            if proc_refresh_counter >= 5:
                proc_cache = _build_proc_cache()
                proc_refresh_counter = 0

            conns = psutil.net_connections(kind="inet")
            now = datetime.now().isoformat(timespec='seconds')
            new_listen: list[tuple[str, int]] = []
            # 락 밖에서 처리할 로그 메시지 버퍼 — 락 내부 I/O 방지
            log_msgs: list[str] = []

            with _lock:
                for c in conns:
                    if not c.laddr:
                        continue
                    pid  = c.pid or 0
                    proc = proc_cache.get(pid, {'name': 'Unknown', 'exe': '', 'is_system': False})

                    if not include_system and proc['is_system']:
                        continue
                    if filters and proc['name'].lower() not in filters:
                        continue

                    is_tcp = (c.type == socket.SOCK_STREAM)
                    key = (
                        pid,
                        c.laddr.ip,
                        c.laddr.port,
                        c.raddr.ip   if c.raddr else None,
                        c.raddr.port if c.raddr else None,
                        'TCP' if is_tcp else 'UDP',
                        c.status,
                    )

                    if key not in _accumulated:
                        entry = {
                            'pid':         pid,
                            'name':        proc['name'],
                            'exe':         proc['exe'],
                            'local_ip':    c.laddr.ip,
                            'local_port':  c.laddr.port,
                            'remote_ip':   c.raddr.ip   if c.raddr else None,
                            'remote_port': c.raddr.port if c.raddr else None,
                            'proto':       'TCP' if is_tcp else 'UDP',
                            'status':      c.status,
                            'first_seen':  now,
                            'last_seen':   now,
                        }
                        _accumulated[key] = entry
                        _history.append(entry)

                        proto_str = 'TCP' if is_tcp else 'UDP'
                        laddr_str = f"{c.laddr.ip}:{c.laddr.port}"
                        raddr_str = (f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "-")
                        log_msgs.append(
                            f"[NEW] {proc['name']}({pid}) "
                            f"{proto_str} {laddr_str} -> {raddr_str} [{c.status}]"
                        )

                        if is_tcp and c.status == 'LISTEN':
                            new_listen.append((c.laddr.ip, c.laddr.port))
                    else:
                        _accumulated[key]['last_seen'] = now

            # 락 밖에서 I/O 처리 — 잠금 경합 최소화
            for msg in log_msgs:
                logger.info(msg)
            for ip, port in new_listen:
                _submit_web_check(ip, port)

        except psutil.AccessDenied:
            pass
        except Exception as e:
            logger.debug(f"collector 오류: {e}")

        _stop_event.wait(COLLECT_INTERVAL)


# ──────────────────────────────────────────
# 누적 데이터 -> 프로세스별 구조로 변환
# ──────────────────────────────────────────
def _snapshot_and_group() -> dict[int, dict]:
    """_accumulated 를 스냅샷 후 초기화하고, PID별로 그룹화해 반환한다."""
    with _lock:
        snapshot = dict(_accumulated)
        _accumulated.clear()

    grouped: dict[int, dict] = {}
    for row in snapshot.values():
        pid = row['pid']
        if pid not in grouped:
            grouped[pid] = {
                'pid':        pid,
                'name':       row['name'],
                'exe':        row['exe'],
                'tcp_listen': [],
                'udp_listen': [],
                'tcp_estab':  [],
            }
        g = grouped[pid]

        if row['proto'] == 'TCP' and row['status'] == 'LISTEN':
            key = f"{row['local_ip']}:{row['local_port']}"
            with _web_lock:
                web_proto = _web_cache.get(key)
            g['tcp_listen'].append({
                'local_ip':   row['local_ip'],
                'local_port': row['local_port'],
                'web_proto':  web_proto,
            })

        elif row['proto'] == 'UDP' and row['remote_ip'] is None:
            g['udp_listen'].append({
                'local_ip':   row['local_ip'],
                'local_port': row['local_port'],
            })

        elif row['proto'] == 'TCP' and row['status'] == 'ESTABLISHED' and row['remote_ip']:
            rip = row['remote_ip']
            domain = _reverse_dns(rip)
            g['tcp_estab'].append({
                'local_ip':    row['local_ip'],
                'local_port':  row['local_port'],
                'remote_ip':   rip,
                'remote_port': row['remote_port'],
                'domain':      domain,
                'first_seen':  row['first_seen'],
                'last_seen':   row['last_seen'],
            })

    # 중복 제거 (같은 주기 내 여러 번 수집된 동일 항목)
    for g in grouped.values():
        g['tcp_listen'] = list({(t['local_ip'], t['local_port']): t for t in g['tcp_listen']}.values())
        g['udp_listen'] = list({(u['local_ip'], u['local_port']): u for u in g['udp_listen']}.values())

    return grouped


# ──────────────────────────────────────────
# JSON 로그 저장
# ──────────────────────────────────────────
def _rotate_if_needed(path: str) -> None:
    if os.path.exists(path) and os.path.getsize(path) > MAX_LOG_BYTES:
        stem, ext = os.path.splitext(path)
        rotated = f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        os.rename(path, rotated)
        logger.info(f"로그 rotate: {os.path.basename(rotated)}")


def _build_log_payload(data: dict[int, dict], scan_count: int, started_at: str) -> dict:
    # _lock으로 _history를, _http_lock으로 _http_log를 보호해 레이스 컨디션 방지
    with _lock:
        history_snapshot = list(_history)
    with _http_lock:
        http_snapshot = list(_http_log)

    return {
        "meta": {
            "started_at":         started_at,
            "hostname":           socket.gethostname(),
            "last_updated":       datetime.now().isoformat(timespec='seconds'),
            "total_scans":        scan_count,
            "display_interval_s": DISPLAY_INTERVAL,
            "collect_interval_s": COLLECT_INTERVAL,
            "active_probe":       ACTIVE_PROBE,
            "sniffer":            ENABLE_SNIFFER,
            "reverse_dns":        ENABLE_RDNS,
            "jsonl":              JSONL_LOG,
            "redact_url_query":   REDACT_URL_QUERY,
            "history_limit":      MAX_HISTORY,
            "http_log_limit":     MAX_HTTP_LOG,
        },
        "current":       list(data.values()),
        "history":       history_snapshot,
        "http_requests": http_snapshot,
    }


def save_json_log(data: dict[int, dict], scan_count: int, started_at: str) -> None:
    payload = _build_log_payload(data, scan_count, started_at)

    if JSONL_LOG:
        _rotate_if_needed(LOG_JSONL)
        with open(LOG_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            f.write("\n")
        return

    _rotate_if_needed(LOG_JSON)
    tmp_path = LOG_JSON + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, LOG_JSON)


# ──────────────────────────────────────────
# 터미널 출력
# ──────────────────────────────────────────
def print_results(data: dict[int, dict], scan_count: int) -> None:
    web_count = sum(
        1 for p in data.values()
        if any(t['web_proto'] for t in p['tcp_listen'])
    )
    print(f"\n{'='*85}")
    print(f"  스캔 #{scan_count}  |  프로세스 {len(data)}개  |  웹서버 {web_count}개"
          f"  |  수집 {COLLECT_INTERVAL}s / 표시 {DISPLAY_INTERVAL}s")
    print(f"{'='*85}")

    if not data:
        print("  (모니터링 대상 프로세스 없음)")
        return

    for pid, p in sorted(data.items(), key=lambda x: x[1]['name'].lower()):
        tcp_l = p['tcp_listen']
        udp_l = p['udp_listen']
        estab = p['tcp_estab']

        if not tcp_l and not udp_l and not estab:
            continue

        print(f"\n  PID {pid:<7} {p['name']}")
        if p['exe']:
            print(f"  {'':10} {p['exe']}")

        if tcp_l:
            parts = []
            for t in sorted(tcp_l, key=lambda x: x['local_port']):
                label = f"{t['local_ip']}:{t['local_port']}"
                if t['web_proto']:
                    label += f" [{t['web_proto']}]"
                parts.append(label)
            print(f"  {'':10} TCP LISTEN : {',  '.join(parts)}")

        if udp_l:
            parts = [f"{u['local_ip']}:{u['local_port']}"
                     for u in sorted(udp_l, key=lambda x: x['local_port'])]
            print(f"  {'':10} UDP        : {',  '.join(parts)}")

        if estab:
            print(f"  {'':10} ESTABLISHED: ({len(estab)}건, 이번 주기 관측)")
            for e in sorted(estab, key=lambda x: x['first_seen'])[:5]:
                remote = e['domain'] or e['remote_ip']
                print(f"  {'':10}   {e['local_ip']}:{e['local_port']} -> "
                      f"{remote}:{e['remote_port']}  (최초 {e['first_seen']})")
            if len(estab) > 5:
                print(f"  {'':10}   ... 외 {len(estab)-5}건")

    # HTTP / HTTPS 요청 이력 출력 (최근 20건)
    with _http_lock:
        recent = list(_http_log)[-20:]

    if recent:
        print(f"\n[HTTP/HTTPS 요청 — 최근 {len(recent)}건]")
        print(f"  {'TIME':<26} {'SRC':<22} {'METHOD':<8} URL")
        print(f"  {'-'*80}")
        for r in recent:
            src    = f"{r['src_ip']}:{r['src_port']}"
            method = r['method']
            url    = r['url']
            note   = "  ※경로암호화" if r['scheme'] == 'https' else ""
            print(f"  {r['timestamp']:<26} {src:<22} {method:<8} {url}{note}")


# ──────────────────────────────────────────
# CLI 인수 파싱
# ──────────────────────────────────────────
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Windows 네트워크 모니터 — 0.5초 고속 수집 + 프로세스별 TCP/UDP/웹서버 탐지"
    )
    parser.add_argument(
        "-p", "--process",
        metavar="NAME",
        action="append",
        dest="processes",
        help="모니터링할 프로세스 이름 (여러 번 사용 가능). 예: -p python -p node",
    )
    parser.add_argument(
        "--include-system",
        action="store_true",
        help="Windows 시스템 프로세스도 포함",
    )
    parser.add_argument(
        "--display-interval",
        type=float,
        default=DISPLAY_INTERVAL,
        metavar="SEC",
        help=f"터미널 출력 주기(초, 기본값: {DISPLAY_INTERVAL})",
    )
    parser.add_argument(
        "--collect-interval",
        type=float,
        default=COLLECT_INTERVAL,
        metavar="SEC",
        help=f"백그라운드 수집 주기(초, 기본값: {COLLECT_INTERVAL})",
    )
    parser.add_argument(
        "--active-probe",
        action="store_true",
        help="LISTEN 포트에 직접 접속해 HTTP/HTTPS 여부를 탐지",
    )
    parser.add_argument(
        "--no-sniffer",
        action="store_true",
        help="raw socket HTTP/HTTPS 패킷 캡처를 비활성화",
    )
    parser.add_argument(
        "--no-rdns",
        action="store_true",
        help="원격 IP reverse DNS 조회를 비활성화",
    )
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="network_log.json 대신 network_log.jsonl에 스냅샷을 append 저장",
    )
    parser.add_argument(
        "--redact-url-query",
        action="store_true",
        help="HTTP URL의 query 문자열을 로그에서 REDACTED로 마스킹",
    )
    return parser.parse_args()


# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────
def main() -> None:
    global COLLECT_INTERVAL, DISPLAY_INTERVAL, ACTIVE_PROBE
    global ENABLE_SNIFFER, ENABLE_RDNS, JSONL_LOG, REDACT_URL_QUERY
    global _web_executor, _rdns_executor

    args = _parse_args()
    COLLECT_INTERVAL = args.collect_interval
    DISPLAY_INTERVAL = args.display_interval
    ACTIVE_PROBE     = args.active_probe
    ENABLE_SNIFFER   = not args.no_sniffer
    ENABLE_RDNS      = not args.no_rdns
    JSONL_LOG        = args.jsonl
    REDACT_URL_QUERY = args.redact_url_query

    # import 시 부작용 방지: 스레드풀을 이 시점에 생성
    _web_executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS, thread_name_prefix="web-check"
    )
    _rdns_executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=4, thread_name_prefix="rdns"
    )

    print("=" * 85)
    print("  Windows Network Monitor  —  고속 수집 + 프로세스별 TCP/UDP/웹서버 탐지")
    log_path = LOG_JSONL if JSONL_LOG else LOG_JSON
    print(f"  수집 주기: {COLLECT_INTERVAL}s  |  표시 주기: {DISPLAY_INTERVAL}s  |  로그: {log_path}")
    print(f"  웹 포트 능동 탐지: {'ON' if ACTIVE_PROBE else 'OFF'}")
    print(f"  패킷 스니퍼: {'ON' if ENABLE_SNIFFER else 'OFF'}  |  Reverse DNS: {'ON' if ENABLE_RDNS else 'OFF'}")
    if REDACT_URL_QUERY:
        print("  URL query 마스킹: ON")
    if args.processes:
        print(f"  필터: {', '.join(args.processes)}")
    else:
        print("  필터: 전체 사용자 프로세스 (시스템 프로세스 제외)")
    print("  종료: Ctrl+C")
    print("=" * 85)

    if not is_admin():
        logger.warning("관리자 권한 없이 실행 중 — 일부 프로세스 정보가 제한될 수 있습니다.")

    collector_thread = threading.Thread(
        target=_collector,
        args=(args.processes, args.include_system),
        daemon=True,
        name="net-collector",
    )
    collector_thread.start()

    sniffer_thread = None
    if ENABLE_SNIFFER:
        sniffer_thread = threading.Thread(
            target=_http_sniffer,
            daemon=True,
            name="http-sniffer",
        )
        sniffer_thread.start()

    logger.info(
        f"수집 스레드 시작 | 수집주기: {COLLECT_INTERVAL}s | "
        f"표시주기: {DISPLAY_INTERVAL}s | 능동탐지: {'ON' if ACTIVE_PROBE else 'OFF'} | "
        f"스니퍼: {'ON' if ENABLE_SNIFFER else 'OFF'} | RDNS: {'ON' if ENABLE_RDNS else 'OFF'}"
    )

    started_at = datetime.now().isoformat(timespec='seconds')
    scan_count = 0

    try:
        while True:
            time.sleep(DISPLAY_INTERVAL)
            data = _snapshot_and_group()
            scan_count += 1
            save_json_log(data, scan_count, started_at)
            web_cnt = sum(
                1 for p in data.values()
                if any(t['web_proto'] for t in p['tcp_listen'])
            )
            logger.info(f"표시 #{scan_count} | 프로세스 {len(data)}개 | 웹서버 {web_cnt}개")
            print_results(data, scan_count)
    except KeyboardInterrupt:
        print(f"\n[종료] 총 {scan_count}회 표시 완료.")
    finally:
        # KeyboardInterrupt 외 SystemExit 등 모든 종료 경로에서 정리
        _stop_event.set()
        collector_thread.join(timeout=2)
        if sniffer_thread:
            sniffer_thread.join(timeout=2)
        if _web_executor:
            _web_executor.shutdown(wait=False)
        if _rdns_executor:
            _rdns_executor.shutdown(wait=False)
        logger.info(f"모니터 종료 | 총 {scan_count}회 표시")


if __name__ == "__main__":
    main()
