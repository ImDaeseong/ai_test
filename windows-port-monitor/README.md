# Windows TCP/UDP Port Monitor

Production-oriented Windows background monitor for local TCP/UDP ports, connection metadata, and process ownership. It uses `psutil` as the primary collector, stores history in SQLite, exports JSON Lines, and can run manually, as a hidden background process, or as a Windows Service.

## Architecture

- `collector/port_collector.py`: collects TCP/UDP sockets through `psutil.net_connections`.
- `collector/process_resolver.py`: resolves PID metadata with cached `psutil.Process` lookups and optional `sc.exe queryex` service mapping.
- `storage/sqlite_store.py`: durable historical storage with WAL mode and indexes.
- `storage/json_exporter.py`: append-only JSONL export.
- `service/background_runner.py`: watchdog-safe polling loop, graceful shutdown, retention.
- `service/windows_service.py`: pywin32 service wrapper.
- `main.py`: command line entry point.

## Installation

Use Python 3.11 or newer on Windows.

```powershell
cd windows-port-monitor
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration

Edit `config/config.yaml`.

Important settings:

- `collector.polling_interval_seconds`: polling cadence. The default is `3.0` seconds.
- `storage.database_path`: SQLite database path.
- `storage.json_export_path`: JSONL export path.
- `storage.retention_days`: SQLite history retention.
- `logging.level`: `DEBUG`, `INFO`, `WARNING`, or `ERROR`.

## Running Manually

Run continuously:

```powershell
python main.py run
```

Run one collection cycle:

```powershell
python main.py once
```

Press `Ctrl+C` to stop. The runner sets a shutdown event and closes storage cleanly.

## Running In The Background

Start hidden background monitoring:

```bat
start_background.bat
```

The start script launches `python main.py run` with `Start-Process`, writes the process ID to `data/port_monitor.pid`, and writes the session start time to `data/port_monitor.started_at`.

Stop hidden background monitoring:

```bat
stop_background.bat
```

The stop script writes `data/port_monitor.stop`, waits up to 20 seconds for graceful shutdown, and opens a Notepad report at `data/port_process_history.txt`.

The stop report:

- Shows only records collected between the latest `start_background.bat` execution and `stop_background.bat`.
- Excludes Windows system processes such as `System`, `svchost.exe`, `C:\Windows\...`, and `NT AUTHORITY\...` records.
- Keeps distinct ports and protocols for the same process, including TCP, UDP, and local web server ports.
- Removes repeated duplicate records for the same protocol, local endpoint, remote endpoint, state, PID, and process name.
- Shows `Process` and `Port` as the first columns.

## Running As A Windows Service

Install from an elevated PowerShell prompt:

```powershell
python main.py install
python main.py start
```

Stop and remove:

```powershell
python main.py stop
python main.py remove
```

Debug service mode interactively:

```powershell
python main.py debug
```

## SQLite Schema

`port_records` contains protocol, local/remote endpoints, state, PID, process metadata, service names, collection timestamps, and an identity hash. Indexes cover collection time, protocol/local port, PID, and identity.

`collector_stats` stores per-cycle totals and failure counters for historical observability.

## Logging

Logs are JSON-formatted through `RotatingFileHandler`. Startup, shutdown, collection cycles, storage failures, permission failures, and exceptions are logged. Console logging is also enabled for manual runs.

Runtime files are written under `data/` and `logs/`. These directories are ignored by git.

## Security And Privileges

This tool is local observability software. It does not sniff packets, intercept credentials, execute remote commands, hide itself, inject into processes, or bypass antivirus.

Administrator privileges are recommended for complete process executable paths, usernames, and service metadata. Without elevation, Windows may deny access to protected processes. Those `AccessDenied` cases are expected, counted in collector stats, and logged without terminating the monitor.

## Troubleshooting

- Empty or partial process fields usually mean the monitor is not elevated or the process exited during collection.
- `pywin32 is required` means service commands were run without the Windows-only dependency installed.
- SQLite lock warnings indicate another process is holding the database. The monitor uses a busy timeout and continues on later cycles.
- Check `logs/port_monitor.log` for structured error records.

## Known Limitations

- UDP does not have a connection state, so records use `NONE`.
- Process and socket data can race because sockets and processes may disappear while being inspected.
- Windows Service metadata is best-effort via `sc.exe queryex`; not every PID maps to a service.
- The collector observes local socket tables only; it is not packet capture.

## Future Improvements

- Add a compact query CLI for historical SQLite reporting.
- Add Prometheus/OpenTelemetry export.
- Add signed installer packaging for enterprise deployment.


## 개선 이력 (2026-06-02)

### 테스트
- pytest 7/7 통과 (이전 세션 검증 완료)
- 추가 코드 변경 없음
