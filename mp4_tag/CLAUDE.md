# Claude Code Instructions — mp4_tag

## 프로젝트 목적

Streamlit UI + yt-dlp + Playwright 기반 웹 미디어 다운로드 도구.
yt-dlp 지원 사이트는 직접 다운로드, 그 외 사이트는 Playwright 브라우저 분석으로 미디어 URL 추출.

## 구조

```
app.py / run_app.py    # Streamlit UI 진입점
main.py                # CLI 진입점
downloader_core.py     # yt-dlp + Playwright 다운로드 코어
job_manager.py         # 다운로드 작업 큐 관리
server_limits.py       # 동시 요청 제한
build_exe.py           # PyInstaller 빌드 스크립트
tests/                 # pytest 테스트 (50개)
```

## 실행

```bat
run.bat          # 웹 UI (http://localhost:8501)
run_cli.bat URL  # CLI 모드
```

## 테스트

```bash
pytest tests/ -v
```

## 환경 변수

| 변수 | 기본값 |
|------|--------|
| `MAX_YTDLP_ATTEMPTS` | `12` |
| `MAX_ANALYZE_WORKERS` | `2` |

## 주의사항

- yt-dlp 우선 → 실패 시 Playwright 폴백 순서 유지
- Playwright 브라우저 자동화 코드는 사이트 구조 변경에 취약 — 테스트 시 실제 네트워크 필요
- `job_manager.py` 수정 시 동시 작업 수 제한(`MAX_ANALYZE_WORKERS`) 로직 확인
