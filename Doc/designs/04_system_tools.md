# 설계문서 04 — 시스템 도구

> 프로젝트: windows-port-monitor, run_game, security_scanning, check_FileEncoding, findstring_foldfiles

---

## 1. 프로젝트별 한줄 정의

| 프로젝트 | 정의 | 언어 |
|---------|------|------|
| **windows-port-monitor** | Windows TCP/UDP 포트 모니터링 → SQLite + JSONL 저장 | Python |
| **run_game** | Steam/Epic/Netmarble 게임 자동 탐지·실행 MFC 앱 | C++ |
| **security_scanning** | OWASP 기반 웹/시스템 취약점 스캔 → JSON 보고서 | Python |
| **check_FileEncoding** | 파일/폴더 인코딩 판별 웹 UI | Go |
| **findstring_foldfiles** | 폴더 전체 문자열 검색 GUI | Python |

---

## 2. windows-port-monitor

### 기술 스택
- **Python** 3.9+ (권장 3.11)
- `psutil` → TCP/UDP 소켓 수집
- `PyYAML` → 설정 파일
- `pywin32` → Windows Service (조건부)
- SQLite3 + JSON Lines

### 아키텍처
```
CLI (main.py)
  ↓
Config Loader → YAML 파싱
  ↓
BackgroundRunner
  ├── PortCollector
  │   └── psutil.net_connections() → raw 소켓
  │       └── ProcessResolver
  │           ├── psutil.Process() → 메타데이터
  │           └── sc.exe queryex → Windows Service 이름
  ├── SQLiteStore → port_records + collector_stats
  └── JsonExporter → JSONL 추가 전용
```

### config.yaml 핵심 항목
```yaml
collector:
  polling_interval_seconds: 3.0
  include_tcp: true
  include_udp: true
  include_ipv6: true
  process_cache_ttl_seconds: 30.0

storage:
  sqlite_enabled: true
  json_export_enabled: true
  database_path: data/port_monitor.sqlite3
  retention_days: 30
  batch_size: 500

logging:
  level: INFO
  max_bytes: 5242880   # 5MB
  backup_count: 5
```

### SQLite 스키마
```sql
CREATE TABLE port_records (
    id INTEGER PRIMARY KEY,
    collection_time REAL,
    protocol TEXT,         -- 'tcp' | 'udp'
    local_address TEXT,
    local_port INTEGER,
    remote_address TEXT,
    remote_port INTEGER,
    status TEXT,
    pid INTEGER,
    process_name TEXT,
    exe_path TEXT,
    username TEXT,
    service_name TEXT,
    identity_hash TEXT,
    created_at REAL
);
-- 인덱스: collection_time, protocol+local_port, pid, identity_hash
```

### 다중 실행 모드
```powershell
python main.py run        # 지속적 폴링
python main.py once       # 단회 수집
python main.py install    # Windows Service 설치
python main.py start      # Service 시작
start_background.bat      # 백그라운드 숨김 실행
stop_background.bat       # 우아한 종료 + 보고서
```

### Windows Service 설계 원칙
```python
# windows_service.py
import win32serviceutil
class WindowsPortMonitorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WindowsPortMonitor"
    _svc_display_name_ = "Windows TCP/UDP Port Monitor"

    def SvcDoRun(self):
        self.runner = BackgroundRunner(config)
        self.runner.start(blocking=True)

    def SvcStop(self):
        self.runner.stop()
```

### 프로세스 캐싱 패턴
```python
# process_resolver.py
_cache: dict[int, tuple[ProcessInfo, float]] = {}
TTL = 30.0  # 초

def resolve(pid: int) -> ProcessInfo | None:
    if pid in _cache:
        info, ts = _cache[pid]
        if time.time() - ts < TTL:
            return info
    try:
        proc = psutil.Process(pid)
        info = ProcessInfo(name=proc.name(), ...)
        _cache[pid] = (info, time.time())
        return info
    except psutil.AccessDenied:
        return None  # 보호 프로세스 → None 반환
```

### 우아한 종료 패턴
```python
# background_runner.py
import threading

class BackgroundRunner:
    def __init__(self):
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def start(self, blocking=True):
        while not self._stop_event.is_set():
            self._collect_and_store()
            self._stop_event.wait(timeout=self.config.polling_interval)
```

### 테스트 (7개, 전원 통과)
```python
test_collector_converts_tcp_and_udp()
test_collector_handles_access_denied()
test_config_loading_defaults()
test_logging_initialization()
test_background_runner_graceful_shutdown()
test_sqlite_store_writes_records()
test_json_exporter_writes_jsonl()
```

---

## 3. run_game

### 기술 스택
- **C++** (Visual Studio 2015+)
- **MFC** (Microsoft Foundation Classes) — 다이얼로그 UI
- **jsoncpp** (JSON 파싱, 소스 포함)
- **Win32 API** (레지스트리, 프로세스 실행)

### 파일 구조
```
run_game/
├── run_gameDlg.cpp / .h     → MFC 다이얼로그
├── GameInstallSearch.cpp     → 공통 탐색 로직
├── SteamLauncherSearch.cpp   → Steam Registry 탐색
├── EpicLauncherSearch.cpp    → Epic Games Launcher 탐색
├── NetmarbleLauncherSearch.cpp → Netmarble 탐색
├── GameInfoConfig.cpp        → GameConfig.json 파싱
└── AppLog.cpp                → 로깅
```

### 플랫폼별 탐색 전략
```
Steam:
  → HKCU\Software\Valve\Steam\SteamPath
  → steamapps/libraryfolders.vdf 파싱
  → 각 라이브러리의 appmanifest_*.acf 파싱

Epic Games:
  → C:\ProgramData\Epic\UnrealEngineLauncher\LauncherInstalled.dat
  → JSON 파싱 → 설치 목록

Netmarble:
  → 레지스트리 / 알려진 설치 경로 탐색
```

### C++ HANDLE 누수 방지 패턴 (버그 수정)
```cpp
// EpicLauncherSearch.cpp:44
HANDLE hFind = FindFirstFile(searchPath, &findData);
if (hFind != INVALID_HANDLE_VALUE) {
    TRY {
        do {
            // 파일 처리
        } while (FindNextFile(hFind, &findData));
    }
    CATCH_ALL(e) {
        // 예외 시에도 반드시 닫기
    }
    END_CATCH_ALL
    FindClose(hFind);  // ← 누수 방지
}
```

### GameConfig.json 구조
```json
{
  "games": [
    {
      "name": "게임이름",
      "platform": "steam|epic|netmarble",
      "appId": "12345",
      "exePath": "GameName.exe"
    }
  ]
}
```

---

## 4. security_scanning

### 기술 스택
- **Python** 3.8+
- `requests`, `urllib3` (HTTP 요청)
- `psutil` (시스템 정보)
- `colorama` (컬러 콘솔)

### 스캔 모듈 구조
```
modules/
├── web_scanner.py    → HTTP 취약점 스캔
│   ├── SQL Injection 탐지
│   ├── XSS 탐지
│   ├── 보안 헤더 검사 (HSTS, CSP, X-Frame-Options)
│   ├── SSL/TLS 검사
│   └── 디렉토리 열거
│
├── system_scanner.py → Windows 시스템 스캔
│   ├── icacls ACL 파싱
│   ├── 열린 포트 검사
│   ├── 실행 중 서비스 검사
│   └── 보안 정책 검사
│
└── reporter.py       → JSON 보고서 생성
```

### CLI 사용법
```bash
# 웹 스캔
python main.py --url https://target.example.com

# 시스템 스캔 (관리자 권한 권장)
python main.py --system

# 전체
python main.py --url https://target.example.com --system
```

### ACL 파싱 버그 수정 패턴
```python
# 잘못된 패턴 (캡처 그룹 중첩 오류)
pattern = r'(\([A-Z,IO]+\))*'

# 올바른 패턴 (비캡처 그룹)
pattern = r'(?:\([A-Z,IO]+\))*'
```

### 보고서 구조 (JSON)
```json
{
  "scan_time": "ISO8601",
  "target": "https://...",
  "findings": [
    {
      "severity": "HIGH|MEDIUM|LOW|INFO",
      "category": "XSS|SQLi|Header|...",
      "description": "...",
      "evidence": "...",
      "recommendation": "..."
    }
  ],
  "summary": { "HIGH": 0, "MEDIUM": 2, "LOW": 5 }
}
```

### 보안 원칙
- 패킷 스니핑 아님 (HTTP 요청만)
- 인가된 대상만 스캔 (펜테스트 전용)
- 관리자 권한: 시스템 스캔 시 권장

---

## 5. check_FileEncoding

### 기술 스택
- **Go** 1.22.3 (표준 라이브러리만)
- 외부 의존성 없음

### 인코딩 감지 로직
```go
func detectEncoding(data []byte) string {
    if len(data) == 0 {
        return "Empty"
    }
    // BOM 체크
    if bytes.HasPrefix(data, []byte{0xEF, 0xBB, 0xBF}) {
        return "UTF-8 BOM"
    }
    if bytes.HasPrefix(data, []byte{0xFF, 0xFE}) {
        return "UTF-16 LE"
    }
    if bytes.HasPrefix(data, []byte{0xFE, 0xFF}) {
        return "UTF-16 BE"
    }
    // UTF-8 유효성 검사
    if utf8.Valid(data) {
        return "UTF-8"
    }
    // EUC-KR (CP949) 추정
    return "EUC-KR"
}
```

### 웹 서버 (표준 라이브러리)
```go
http.HandleFunc("/scan", handleScan)
http.HandleFunc("/", handleIndex)
http.ListenAndServe(":8765", nil)
```

### 타임아웃 처리
```go
// 스캔 시간 초과 → 408
ctx, cancel := context.WithTimeout(r.Context(), 30*time.Second)
defer cancel()
```

---

## 6. findstring_foldfiles

### 기술 스택
- **Python** 3.10+ (표준 라이브러리: tkinter, threading, os, queue)
- 외부 의존성 없음

### 멀티스레드 설계
```
MainThread (tkinter UI)
  ├── 검색 시작 → SearchWorker 스레드 생성
  ├── outbox Queue 폴링 (100ms 간격)
  └── UI 업데이트

SearchWorker (threading.Thread)
  ├── _iter_files() → os.walk() 열거
  ├── _should_read() → 텍스트 파일 판별
  └── _find_in_file() → 라인 단위 검색
      → 결과를 outbox Queue에 put
```

### UI 동결 방지 패턴 (버그 수정)
```python
# 잘못된 방식 (무한 루프 → UI 동결)
def _drain_outbox(self):
    while True:
        try:
            item = self._outbox.get_nowait()
            self._add_result(item)
        except queue.Empty:
            break

# 올바른 방식 (배치 처리 상한)
def _drain_outbox(self):
    for _ in range(200):  # 최대 200개 배치
        try:
            item = self._outbox.get_nowait()
            self._add_result(item)
        except queue.Empty:
            break
    self.after(100, self._drain_outbox)  # 다음 폴링 예약
```

### 텍스트 파일 판별 로직
```python
TEXT_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css',
    '.json', '.xml', '.yaml', '.yml', '.md', '.txt',
    '.sh', '.bash', '.ps1', '.go', '.rs', '.c', '.cpp',
    '.h', '.hpp', '.java', '.kt', '.swift', '.sql',
    # ... 총 49종
}

def _should_read(self, filepath):
    ext = Path(filepath).suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return True
    # 첫 2KB에 null 바이트 없으면 텍스트로 간주
    with open(filepath, 'rb') as f:
        chunk = f.read(2048)
    return b'\x00' not in chunk
```

### 스킵 디렉토리
```python
SKIP_DIRS = {
    '.git', '.hg', '.svn',
    '__pycache__', 'node_modules',
    '$Recycle.Bin', 'System Volume Information'
}
```

### 파일 열기 (버그 수정)
```python
# 잘못된 방식 (예외 마스킹)
try:
    os.startfile(filepath)
except:
    pass  # 실패 무시

# 올바른 방식 (OS 명시적 분기)
if os.name == 'nt':
    os.startfile(filepath)
else:
    subprocess.run(['xdg-open', filepath])
```

---

## 7. 공통 패턴 (시스템 도구)

### Go 웹 서버 최소 패턴
```go
// 표준 라이브러리만 사용 (외부 의존성 없음)
package main

import (
    "encoding/json"
    "net/http"
)

func main() {
    http.HandleFunc("/api/scan", handleScan)
    http.HandleFunc("/", handleIndex)
    log.Fatal(http.ListenAndServe(":8765", nil))
}
```

### Python tkinter 백그라운드 작업 패턴
```python
import threading, queue

class App(tk.Tk):
    def __init__(self):
        self._outbox = queue.Queue()
        self.after(100, self._drain_outbox)  # 폴링 시작

    def start_worker(self):
        t = threading.Thread(target=self._worker, daemon=True)
        t.start()

    def _worker(self):
        # 백그라운드 작업
        self._outbox.put(result)  # UI 스레드에 결과 전달

    def _drain_outbox(self):
        for _ in range(200):  # 배치 상한 필수
            try:
                item = self._outbox.get_nowait()
                self._update_ui(item)
            except queue.Empty:
                break
        self.after(100, self._drain_outbox)  # 재예약
```

### Windows 배치 스크립트 패턴 (공통)
```batch
@echo off
SETLOCAL
SET BASE=%~dp0

:: Python 가상환경 자동 관리
IF NOT EXIST "%BASE%.venv" (
    python -m venv "%BASE%.venv"
    "%BASE%.venv\Scripts\pip" install -r "%BASE%requirements.txt" -q
)

:: 실행
"%BASE%.venv\Scripts\python" "%BASE%main.py" %*
```

### psutil 소켓 수집 패턴
```python
import psutil

def collect_ports():
    connections = psutil.net_connections(kind='all')
    records = []
    for conn in connections:
        if conn.status == psutil.CONN_NONE:
            continue
        records.append({
            'protocol': 'tcp' if conn.type == 1 else 'udp',
            'local_address': conn.laddr.ip if conn.laddr else '',
            'local_port': conn.laddr.port if conn.laddr else 0,
            'remote_address': conn.raddr.ip if conn.raddr else '',
            'remote_port': conn.raddr.port if conn.raddr else 0,
            'status': conn.status,
            'pid': conn.pid,
        })
    return records
```
