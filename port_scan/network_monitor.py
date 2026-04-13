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
from datetime import datetime
from logging.handlers import RotatingFileHandler

# ──────────────────────────────────────────
# 설정
# ──────────────────────────────────────────
COLLECT_INTERVAL = 0.5                  # 백그라운드 수집 주기 (초)
DISPLAY_INTERVAL = 5                    # 터미널 출력 주기 (초)
PROTO_TIMEOUT    = 0.4                  # 프로토콜 탐지 소켓 타임아웃
MAX_WORKERS      = 20                   # 병렬 스캔 스레드 수
MAX_LOG_BYTES    = 10 * 1024 * 1024     # 로그 rotate 기준 (10 MB)

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
LOG_TEXT  = os.path.join(BASE_DIR, "network_monitor.log")
LOG_JSON  = os.path.join(BASE_DIR, "network_log.json")

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
    # HTTPS (SSL/TLS)
    try:
        ctx = ssl._create_unverified_context()
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
_history:     list[dict] = []         # 세션 전체 연결 이력 (누적)
_http_log:    list[dict] = []         # HTTP 요청 이력 (스니퍼 캡처)
_web_lock     = threading.Lock()
_web_cache:   dict[str, str] = {}     # "ip:port" -> "HTTP"|"HTTPS" (확인된 것만)
_web_pending: set[str] = set()        # 현재 탐지 중인 포트 키
_stop_event   = threading.Event()

HTTP_METHODS = {b'GET ', b'POST', b'PUT ', b'PATC', b'DELE', b'HEAD', b'OPTI'}

# 웹 프로토콜 탐지 전용 스레드풀 (수집 스레드와 분리)
_web_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=MAX_WORKERS, thread_name_prefix="web-check"
)


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
            'url':       f"http://{host}{path}",
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
            except Exception:
                break

            entry = _parse_http_request(raw) or _parse_tls_sni(raw)
            if entry is None:
                continue

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
    # 캡처 대상 인터페이스 수집
    bind_ips: list[str] = ['127.0.0.1']
    try:
        # 호스트의 외부 IP 추가
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

    # 모든 하위 스레드가 끝날 때까지 대기 (stop_event로 종료됨)
    for t in threads:
        t.join()


# ──────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────
def _normalize_filters(names: list[str] | None) -> set[str] | None:
    if not names:
        return None
    result: set[str] = set()
    for n in names:
        n = n.lower()
        result.add(n)
        result.add(n + '.exe')
    return result


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
    key = f"{ip}:{port}"
    with _web_lock:
        if key in _web_cache or key in _web_pending:
            return
        _web_pending.add(key)
    _web_executor.submit(_check_and_cache, ip, port)


# ──────────────────────────────────────────
# 백그라운드 수집 스레드
# 0.5초마다 연결을 수집해 _accumulated에 누적하고,
# 새 LISTEN 포트를 발견하면 즉시 웹 프로토콜 탐지를 시작한다.
# ──────────────────────────────────────────
def _collector(filter_names: list[str] | None, include_system: bool) -> None:
    filters = _normalize_filters(filter_names)
    proc_cache: dict[int, dict] = _build_proc_cache()  # 시작 즉시 초기화
    proc_refresh_counter = 0

    while not _stop_event.is_set():
        try:
            # 프로세스 캐시는 5회(2.5초)마다 갱신
            proc_refresh_counter += 1
            if proc_refresh_counter >= 5:
                proc_cache = _build_proc_cache()
                proc_refresh_counter = 0

            conns = psutil.net_connections(kind="inet")
            now = datetime.now().isoformat(timespec='seconds')
            new_listen: list[tuple[str, int]] = []  # 이번 사이클에 새로 발견한 LISTEN 포트

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
                        _history.append(entry)   # 세션 이력에 즉시 기록

                        # 텍스트 로그에 즉시 기록 — 단기 연결도 누락 없이 남김
                        proto_str = 'TCP' if is_tcp else 'UDP'
                        laddr_str = f"{c.laddr.ip}:{c.laddr.port}"
                        raddr_str = (f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "-")
                        logger.info(
                            f"[NEW] {proc['name']}({pid}) "
                            f"{proto_str} {laddr_str} -> {raddr_str} [{c.status}]"
                        )

                        # 새 TCP LISTEN 포트 → 웹 탐지 예약
                        if is_tcp and c.status == 'LISTEN':
                            new_listen.append((c.laddr.ip, c.laddr.port))
                    else:
                        _accumulated[key]['last_seen'] = now

            # 락 밖에서 비동기 웹 탐지 제출 (수집 지연 없음)
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
            domain = None
            if not any(rip.startswith(pfx) for pfx in ('127.', '10.', '192.168.', 'fe80')):
                try:
                    domain = socket.gethostbyaddr(rip)[0]
                except Exception:
                    pass
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
def save_json_log(data: dict[int, dict], scan_count: int, started_at: str) -> None:
    if os.path.exists(LOG_JSON) and os.path.getsize(LOG_JSON) > MAX_LOG_BYTES:
        rotated = LOG_JSON.replace(".json", f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        os.rename(LOG_JSON, rotated)
        logger.info(f"로그 rotate: {os.path.basename(rotated)}")

    payload = {
        "meta": {
            "started_at":         started_at,
            "hostname":           socket.gethostname(),
            "last_updated":       datetime.now().isoformat(timespec='seconds'),
            "total_scans":        scan_count,
            "display_interval_s": DISPLAY_INTERVAL,
            "collect_interval_s": COLLECT_INTERVAL,
        },
        "current": list(data.values()),   # 최근 5초 윈도우의 프로세스 요약
        "history": list(_history),        # 세션 시작 이후 발견된 모든 연결 이력
        "http_requests": list(_http_log), # 캡처된 HTTP 요청 URL 이력
    }
    with open(LOG_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


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
    if _http_log:
        recent = _http_log[-20:]
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
    return parser.parse_args()


# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────
def main() -> None:
    global COLLECT_INTERVAL, DISPLAY_INTERVAL
    args = _parse_args()
    COLLECT_INTERVAL = args.collect_interval
    DISPLAY_INTERVAL = args.display_interval

    print("=" * 85)
    print("  Windows Network Monitor  —  고속 수집 + 프로세스별 TCP/UDP/웹서버 탐지")
    print(f"  수집 주기: {COLLECT_INTERVAL}s  |  표시 주기: {DISPLAY_INTERVAL}s  |  로그: {LOG_JSON}")
    if args.processes:
        print(f"  필터: {', '.join(args.processes)}")
    else:
        print("  필터: 전체 사용자 프로세스 (시스템 프로세스 제외)")
    print("  종료: Ctrl+C")
    print("=" * 85)

    if not is_admin():
        logger.warning("관리자 권한 없이 실행 중 — 일부 프로세스 정보가 제한될 수 있습니다.")

    # 백그라운드 수집 스레드 시작
    collector_thread = threading.Thread(
        target=_collector,
        args=(args.processes, args.include_system),
        daemon=True,
        name="net-collector",
    )
    collector_thread.start()

    # HTTP 스니퍼 스레드 시작 (관리자 권한 없으면 내부에서 조용히 종료)
    sniffer_thread = threading.Thread(
        target=_http_sniffer,
        daemon=True,
        name="http-sniffer",
    )
    sniffer_thread.start()

    logger.info(f"수집 스레드 시작 | 수집주기: {COLLECT_INTERVAL}s | 표시주기: {DISPLAY_INTERVAL}s")

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
        _stop_event.set()
        collector_thread.join(timeout=2)
        logger.info(f"모니터 종료 | 총 {scan_count}회 표시")
        print(f"\n[종료] 총 {scan_count}회 표시 완료.")


if __name__ == "__main__":
    main()
