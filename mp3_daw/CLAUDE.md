# Claude Code Instructions — mp3_daw

## 프로젝트 목적

Go 제어 레이어 + Python 음성 처리 엔진으로 구성된 로컬 음원 DAW 시스템.
inbox 폴더 감시 → 자동 분석(BPM/Key/LUFS) + 마스터링 파이프라인.

## 구조

```
main.go            # Go 진입점 (폴더 감시 + Python 프로세스 제어)
engine.py          # Python 분석·마스터링 엔진
demucs_compat.py   # Demucs 음원 분리 호환 레이어
static/            # 웹 UI
```

## 실행

```bat
run.bat
```

## 테스트

```bash
go test ./...
```

## 환경 변수

| 변수 | 기본값 |
|------|--------|
| `PYTHON_BIN` | `python` |
| `WATCH_DIR` | `./inbox` |
| `OUT_DIR` | `./output` |
| `MAX_PYTHON_PROCS` | `2` |
| `PYTHON_TIMEOUT_MINUTES` | `90` |

## 주의사항

- Go↔Python 통신은 stdin/stdout JSON — 프로토콜 변경 시 양쪽 동시 수정
- `MAX_PYTHON_PROCS` 초과 시 큐잉 처리 — 동시성 로직 건드릴 때 주의
- `demucs_compat.py`는 Demucs 버전 호환 래퍼 — Demucs API 변경 시 이 파일만 수정
