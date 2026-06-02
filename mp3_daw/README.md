# mp3_daw — Suno AI 음원 처리 DAW

Go 제어 레이어 + Python 음성 처리 엔진으로 구성된 로컬 음원 DAW 시스템.  
inbox 폴더 감시 → 자동 분석(BPM/Key/LUFS) + 마스터링 파이프라인.

## 실행

```bat
run.bat
```

## 환경 변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `PYTHON_BIN` | `python` | Python 실행 파일 경로 |
| `WATCH_DIR` | `./inbox` | 감시 폴더 |
| `OUT_DIR` | `./output` | 출력 폴더 |
| `MAX_PYTHON_PROCS` | `2` | 동시 Python 프로세스 수 |
| `PYTHON_TIMEOUT_MINUTES` | `90` | Python 타임아웃(분) |

## 개선 이력 (2026-06-02)

### 버그 수정
| 파일 | 내용 |
|---|---|
| `engine.py:39` | `import numpy as np` 이중 임포트 제거 |
| `main.go:377` | Python 오류 시 stdout JSON에서 `message` 추출해 job 오류에 반영 |
| `main.go` | 호출되지 않는 `runJobAsync` 데드 코드 제거 |

### 기능 개선
| 파일 | 내용 |
|---|---|
| `main.go:watchFolder` | `recentEvents` 맵 5분 주기 cleanup — 장시간 운영 시 메모리 누수 방지 |
| `main.go:startServer` | `http.Server` + `signal.Notify` graceful shutdown 구현 (SIGINT/SIGTERM, 최대 30초 대기) |
| `engine.py:load_audio_with_retry` | 루프 전 초기 크기 선읽기 — 이미 완성된 파일의 불필요한 2초 대기 제거 |

### 테스트
- `main_test.go` 신규 작성 — 23개 테스트 전원 통과
- 대상: `extractLastJSON`, `isAudioFile`, `safeUploadName`, `allowedCORSOrigin`
