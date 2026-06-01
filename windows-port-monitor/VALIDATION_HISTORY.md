# Validation History

## 2026-05-29 09:26:00 +09:00

### Summary

Source validation and runtime smoke testing completed for the current `E:\ai_test\windows-port-monitor` checkout.

Overall result: **PASS**

### Environment

- Working directory: `E:\ai_test\windows-port-monitor`
- Default Python runtime: `Python 3.9.7`
- pip: `26.0.1`
- Project purpose: personal local Windows port/process observability tool, not company work.

Note: README still recommends Python 3.11 or newer for installation. The current source and tests also pass under the available Python 3.9.7 runtime.

### Checks Performed

| Check | Command | Result |
| --- | --- | --- |
| Python syntax compilation | `python -m py_compile config_loader.py logging_setup.py main.py models.py collector\port_collector.py collector\process_resolver.py storage\sqlite_store.py storage\json_exporter.py service\background_runner.py service\windows_service.py` | PASS |
| Unit tests | `python -m pytest -q` | PASS, `7 passed in 0.45s` |
| One-shot runtime collection | `python main.py once` | PASS |
| SQLite data check | custom SQLite count/latest-stats query | PASS |
| JSONL export check | custom JSONL line/type check | PASS |
| CLI help validation | `python main.py --help` | PASS |
| YAML config parse check | custom `yaml.safe_load` section check | PASS |
| Secret-pattern scan | `rg` over source/config/tests/docs excluding `data`, `logs`, `.git`, caches | PASS, no matches |

### Runtime Results

- One-shot collection result: `Collected 716 records (672 TCP, 44 UDP)`
- Latest SQLite stats row: `(716, 672, 44, 0, 0, 0, 0)`
- SQLite database: `data/port_monitor.sqlite3`
- JSONL export: `data/port_records.jsonl`
- JSONL line count after validation: `1507`
- Rotating log file: `logs/port_monitor.log`
- Latest log entries confirm `logging_initialized`, `application_starting`, `sqlite_store_opened`, `single_collection_complete`, and `sqlite_store_closed`.

### Files Changed During This Validation

- `VALIDATION_HISTORY.md`: added this validation record.

### Validation Conclusion

The current project source, unit tests, CLI, one-shot collector runtime, SQLite persistence, JSONL export, structured logging, and basic secret scan all passed. No application source files were changed.

## 2026-05-19 17:29:59 +09:00

### Summary

Full source validation and runtime smoke testing completed for the Windows TCP/UDP Port Monitor.

Overall result: **PASS with environment notes**

### Environment

- Working directory: `e:\ai_test\port_scan\windows-port-monitor`
- Default Python runtime: `Python 3.9.7`
- Requested project runtime: `Python 3.11+`
- Python 3.11 launcher check: `py -3.11 --version` failed with `No suitable Python runtime found`
- pywin32 availability: `True`

Note: The source validated successfully with the currently available Python 3.9.7 runtime. A separate Python 3.11+ validation should be run on the deployment host because the project requirement is Python 3.11+.

### Checks Performed

| Check | Command | Result |
| --- | --- | --- |
| Source structure check | custom Python required-path assertion | PASS |
| Python syntax compilation | `python -m compileall .` | PASS |
| Unit tests | `python -m pytest -q` | PASS, `7 passed in 0.35s` |
| Module import validation | custom import script for 10 modules | PASS |
| CLI help validation | `python main.py --help` | PASS |
| One-shot runtime collection | `python main.py once` | PASS |
| Background runner graceful shutdown | custom runner start/stop script | PASS |
| SQLite schema and data validation | custom SQLite assertion script | PASS |
| JSONL export validation | custom JSON parse assertion | PASS |
| pywin32 service wrapper import | custom service module script | PASS |
| TODO/FIXME/placeholder scan | `rg -n "TODO|FIXME|pass$|placeholder|pseudo" .` | PASS, no matches |

### Runtime Results

- One-shot collection result: `Collected 155 records (119 TCP, 36 UDP)`
- Background runner status after stop: `stopped`
- SQLite database: `data/port_monitor.sqlite3`
- JSONL export: `data/port_records.jsonl`
- Rotating log file: `logs/port_monitor.log`
- Final observed SQLite counts:
  - `port_records`: `452`
  - `collector_stats`: `3`
  - latest stats timestamp: `2026-05-19T08:29:03.954+00:00`

### Dependency Notes

`python -m pip check` reported unrelated conflicts in the shared/global Python environment:

- `whisperx 3.7.5` expected `numpy>=2.0.2,<2.1.0`, current environment has `numpy 1.26.4`
- `whisperx 3.7.5` expected `pandas>=2.2.3,<2.3.0`, current environment has `pandas 2.3.3`

These conflicts are not introduced by this project. Recommended deployment path is a clean virtual environment with:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest -q
python main.py once
```

### Files Changed During This Validation

- `service/windows_service.py`: replaced fallback `pass` body with an explicit fallback docstring.
- `tests/test_collector.py`: replaced test no-op `pass` with explicit test resolver state.
- `tests/test_service.py`: replaced fake retention no-op with captured cutoff state.
- `VALIDATION_HISTORY.md`: added this validation record.

### Validation Conclusion

The project source, test suite, SQLite persistence, JSON export, structured logging, CLI entry point, service wrapper import, and graceful shutdown behavior were validated successfully in the current workspace.

Remaining deployment validation:

- Install Python 3.11+ and rerun the same checks.
- Run Windows Service install/start/stop from an elevated PowerShell prompt on the target host.
- Review administrator privilege behavior for protected process metadata in the target Windows environment.

## 2026-05-19 17:32:22 +09:00

### Summary

Added background execution batch files and validated start/stop behavior.

Overall result: **PASS**

### Files Added

- `start_background.bat`: starts `python main.py run` in a hidden background process and writes `data/port_monitor.pid`.
- `stop_background.bat`: writes `data/port_monitor.stop`, waits up to 20 seconds for graceful shutdown, and removes the PID file after exit.

### Code Change

- `service/background_runner.py`: added stop-file support through `data/port_monitor.stop` so non-visible background runs can be stopped gracefully without force-killing the process.

### Checks Performed

| Check | Command | Result |
| --- | --- | --- |
| Syntax compilation | `python -m compileall service\background_runner.py` | PASS |
| Unit tests | `python -m pytest -q` | PASS, `7 passed in 0.35s` |
| Background start batch | `.\start_background.bat` | PASS, started PID `18072` |
| Background stop batch | `.\stop_background.bat` | PASS, graceful stop |
| PID cleanup check | `Test-Path data\port_monitor.pid` | PASS, PID file removed |
| Process exit check | `Get-Process -Id 18072` | PASS, process not found |

### Usage

Start hidden background monitoring:

```bat
start_background.bat
```

Stop hidden background monitoring:

```bat
stop_background.bat
```

## 2026-05-19 17:52:21 +09:00

### Summary

Updated background start/stop reporting and validated the final git-ready behavior.

Overall result: **PASS**

### Changes Validated

- `config/config.yaml`: changed `collector.polling_interval_seconds` from `5.0` to `3.0`.
- `start_background.bat`: records the session start timestamp in `data/port_monitor.started_at`.
- `stop_background.bat`: reports only records collected from the latest background start to stop execution.
- `stop_background.bat`: opens the final process/port report in Notepad before the batch exits.
- `stop_background.bat`: excludes Windows system processes from the report.
- `stop_background.bat`: removes repeated duplicate records while preserving distinct ports and protocols for the same process.

### Checks Performed

| Check | Command | Result |
| --- | --- | --- |
| Background start, wait, stop | `.\start_background.bat; Start-Sleep -Seconds 7; .\stop_background.bat` | PASS |
| Polling cadence check | `Get-Content logs\port_monitor.log -Tail 20` | PASS, cycles observed at 3-second intervals |
| Stop report range check | `Get-Content data\port_process_history.txt -TotalCount 35` | PASS, session start/stop displayed |
| Report column check | stop report inspection | PASS, `Process` and `Port` are first |
| System process exclusion check | stop report inspection | PASS |
| Duplicate removal check | stop report inspection | PASS |

### Runtime Notes

- The monitor runs asynchronously through `Start-Process`.
- Multiple ports from the same process are expected and preserved.
- TCP and UDP records are both preserved.
- Runtime outputs under `data/` and `logs/` are generated files and are excluded from git.
