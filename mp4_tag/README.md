# mp4_tag — 미디어 다운로더

Streamlit UI + yt-dlp + Playwright 기반 웹 미디어 다운로드 도구.  
YouTube 등 지원 사이트는 yt-dlp 직접 다운로드, 그 외 사이트는 Playwright 브라우저 분석으로 미디어 URL 추출.

## 실행

```bat
run.bat          # 웹 UI (http://localhost:8501)
run_cli.bat URL  # CLI 모드
```

> 최초 실행 시 Python 3.12 가상환경 자동 생성 및 패키지 설치 (수 분 소요)

## 지원 사이트 (yt-dlp 직접 다운로드)

YouTube, Twitter/X, Instagram, TikTok, Vimeo, SoundCloud, Twitch, Dailymotion, NicoNico, Bilibili

## 환경 변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `MAX_YTDLP_ATTEMPTS` | `12` | yt-dlp client×format 시도 최대 횟수 |
| `MAX_ANALYZE_WORKERS` | `2` | 동시 URL 분석 작업 수 |

## 개선 이력 (2026-06-02)

### 버그 수정 및 기능 개선
| 파일 | 내용 |
|---|---|
| `run.bat` | `.venv` 미존재 시 조용히 종료되던 문제 수정 — Python 3.12 venv 자동 생성, 패키지 설치, Playwright 브라우저 설치 로직 추가 |
| `run.bat` | Python 3.14 선택 시 Playwright `NotImplementedError` 발생 수정 — `py -3.12` 명시 고정 |
| `downloader_core.py` | `MAX_YTDLP_ATTEMPTS` 환경변수 추가 — 48회 순차 시도의 최악 대기 시간 제한 (기본 12회) |
| `app.py` | YouTube 등 yt-dlp 전용 사이트 감지 — Analyze 클릭 시 Playwright 건너뛰고 yt-dlp 직접 다운로드 자동 시작 |
| `app.py` | **`yt-dlp ▶`** 버튼 추가 — URL 입력만 되면 즉시 yt-dlp 다운로드 시작 |
| `job_manager.py` | `submit_ytdlp_download()` 함수 추가 |
| `job_manager.py` | `submit_fallback_download()` — 스트림 없어도 yt-dlp로 자동 전환 |

### 테스트
- `tests/test_core.py` 신규 작성 — 50개 테스트 전원 통과
- 대상: URL 유효성, 파일명 처리, 미디어 URL 분류, ffmpeg 시간 파싱, 헤더 필터, 스트림 선택, job 상태 관리
