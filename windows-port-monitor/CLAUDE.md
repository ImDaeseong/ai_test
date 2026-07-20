# Claude Code Instructions — windows-port-monitor

## 프로젝트 목적

Windows 로컬 TCP/UDP 포트·연결 메타데이터·프로세스 소유권을 수집하는 백그라운드 모니터.
psutil 기반 수집 → SQLite 저장 → JSON Lines 내보내기.
수동 실행 / 숨김 백그라운드 / Windows 서비스 세 가지 모드 지원.

## 구조

```
main.py                        # CLI 진입점
collector/port_collector.py    # TCP/UDP 소켓 수집 (psutil)
collector/process_resolver.py  # PID → 프로세스 메타데이터 (캐시 포함)
storage/sqlite_store.py        # SQLite WAL 모드 저장
storage/json_exporter.py       # JSONL 내보내기
service/background_runner.py   # 폴링 루프 + 그레이스풀 셧다운
service/windows_service.py     # pywin32 서비스 래퍼
config/                        # 설정 파일
models.py                      # 데이터 모델
logging_setup.py               # 로깅 설정
tests/                         # pytest 테스트 (7개 전량 통과)
```

## 실행

```powershell
python main.py              # 수동 실행
start_background.bat        # 숨김 백그라운드
stop_background.bat         # 중지
```

## 테스트

```bash
pytest tests/ -v
```

## 주의사항

- RAM 부족 환경에서 자동 시작 비활성화 — 수동 실행 권장 (OpenClaw와 동일 이슈)
- `process_resolver.py`의 PID 캐시: 프로세스 교체 시 캐시 무효화 로직 확인
- SQLite WAL 모드 사용 — 동시 읽기/쓰기 가능하지만 파일 잠금 주의
