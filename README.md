# 소스 설명

> 작성일: 2026-05-08 / 최종 수정: 2026-08-17 (간결화 — 프로젝트별 상세 내용은 각 프로젝트 `README.md`/`CLAUDE.md`로 이동)
> 총 18개 소스 프로젝트 수록 (`Doc/` 폴더에 프로젝트별 AI 개발 프롬프트·설계 문서 통합 보관)
> 설계 문서 인덱스: [`Doc/DESIGN_INDEX.md`](Doc/DESIGN_INDEX.md) — 5개 카테고리별 아키텍처·기술 스택·핵심 패턴 기록
> 검증 현황·테스트 결과: [`PROJECT_STATUS.md`](PROJECT_STATUS.md)

## 저장소 목표

`ai_test`는 개인 도구 개발과 실험을 위한 작업 공간입니다(집 PC: `C:\Users\cs930\Desktop\ai_test`, 회사 PC: `E:\ai_test` — 실제 경로는 사용 중인 PC에 따라 다릅니다).

프로그램 자체를 많이 만드는 것이 목표가 아니라, 음악, 영상 제작, AI 활용, 자동화, 수익화 실험, 생산성, 생활 개선을 더 빠르고 반복 가능하게 만드는 도구를 개발하는 것이 목적입니다.

주요 판단 기준은 실제 목표 달성, 반복 가능성, 유지보수성, 비용 통제, 보안, 현실성입니다.

각 프로젝트의 상세 기능·폴더 구조·버그 수정 이력은 해당 프로젝트 폴더의 `README.md`(사용법)와 `CLAUDE.md`(AI 작업 규칙)를 참조하세요. 이 문서는 전체를 훑어보기 위한 요약 인덱스입니다.

---

## 환경 설정

API 키가 필요한 프로젝트는 각 디렉토리의 `.env.example`을 `.env`로 복사한 뒤 키를 입력하세요.

```bat
copy Pexels\.env.example Pexels\.env
copy weather_alarm\.env.example weather_alarm\.env
```

| 프로젝트 | 필수 환경변수 | 발급처 |
|----------|---------------|--------|
| `Pexels` | `GEMINI_API_KEY`, `PEXELS_API_KEY` | [Google AI Studio](https://aistudio.google.com), [Pexels](https://www.pexels.com/api/) |
| `weather_alarm` | `WEATHER_SERVICE_KEY`, `DISCORD_TOKEN`, `TELEGRAM_TOKEN` | [공공데이터포털](https://www.data.go.kr), Discord/Telegram BotFather |
| `Analysis_music` | `LILYPOND_PATH` (선택) | LilyPond 로컬 설치 경로 |

> `.env` 파일은 `.gitignore`에 등록되어 있으므로 Git에 커밋되지 않습니다.

---

## 프로젝트 목록

| # | 폴더명 | 한 줄 설명 | 언어/스택 | 완성도 | 빠른 실행 |
|---|--------|-----------|-----------|--------|-----------|
| 1 | [Analysis_music](Analysis_music/README.md) | Suno AI 음악 프롬프트+오디오 → 음악이론 리포트·LilyPond 악보·비주얼 프롬프트 생성 | Python + Flask | ★★★★☆ | `run_web.bat` → :5000 |
| 2 | [check_FileEncoding](check_FileEncoding/README.md) | C/C++ 소스 폴더 인코딩(UTF-8/UTF-16/CP949)·BOM 일괄 검사 | Go | ★★★★★ | `fileencoding.exe` → :8080 |
| 3 | [extensions](extensions/README.md) | Suno.com 동기화 가사를 LRC/SRT로 다운로드하는 Chrome 확장 | React/JS (MV3) | ★★★★★ | `npm run build` → Chrome 로드 |
| 4 | [imagevideo](imagevideo/README.md) | 가사 파일+오디오+배경 → FFmpeg 4단계 파이프라인으로 가사 영상(MP4) 생성 | Node.js + FFmpeg | ★★★★☆ | `npm run lyric-video -- --clean` |
| 5 | [Pexels](Pexels/README.md) | Gemini 장면 분석 + Pexels 스톡 영상 검색 → 가로/세로 영상 자동 생성 | Python + FFmpeg | ★★★★★ | `run.bat` |
| 6 | [lyrics_tag](lyrics_tag/README.md) | 오디오 재생하며 가사 줄마다 수동 타이밍 태깅 → LRC 생성 웹 도구 | Python + Flask | ★★★★★ | `run.bat` → :5000 |
| 7 | [lyricvideo](lyricvideo/README.md) | Remotion으로 LRC/SRT 가사+오디오를 가사 비디오(MP4)로 렌더링 | TypeScript + React | ★★★★★ | `render-video.bat` |
| 8 | [master_tag](master_tag/README.md) | Suno 음원을 YouTube 표준(-14 LUFS)으로 자동 마스터링하는 웹 도구 | Python + Flask | ★★★★★ | `python server.py` → :5000 |
| 9 | [mp3_daw](mp3_daw/README.md) | 오디오 분석·마스터링·AI Stem 분리(Demucs) 로컬 DAW | Go + Python | ★★★★☆ | `go build && .\main.exe` → :8080 |
| 10 | [mp4_tag](mp4_tag/README.md) | 웹페이지의 HLS/DASH/MP4 스트림 자동 감지·다운로드 | Python + Playwright | ★★★★☆ | `python main.py` → :8501 |
| 11 | [security_scanning](security_scanning/README.md) | OWASP Top 10 웹 보안 스캔 + Windows 시스템 보안 진단 | Python | ★★★★☆ | `python main.py --web <url> --system` |
| 12 | [weather_alarm](weather_alarm/README.md) | 기상청 날씨 API → Discord/Telegram 구독 알림 봇 | Python (asyncio) | ★★★★☆ | `run_local.bat` |
| 13 | [ai_anime_production](ai_anime_production/README.md) | 씬 이미지+프롬프트(.md) → Remotion 씬 클립(MP4) 렌더링 | TypeScript + Remotion | ★★★★☆ | `run.bat` |
| 14 | [findstring_foldfiles](findstring_foldfiles/README.md) | 폴더/드라이브 전체 멀티스레드 문자열 검색 GUI | Python (tkinter) | ★★★★★ | `run.bat` |
| 15 | [windows-port-monitor](windows-port-monitor/README.md) | Windows TCP/UDP 포트·프로세스 이력을 SQLite로 수집하는 백그라운드 서비스 | Python + SQLite | ★★★★★ | `start_background.bat` |
| 16 | [run_game](run_game/README.md) | Steam/Epic/Netmarble 설치 탐지 후 런처 경유 게임 실행기 | C++ / MFC | ★★★★★ | `run_game.exe` (관리자 권한) |
| 17 | [ai-webtoon](ai-webtoon/README.md) | 곡 BPM·감정에 맞는 웹툰 만화 패널 이미지 프롬프트 자동 생성 | Python + Flask | ★★★★★ | `run_all.bat` |
| 18 | [ai-webtoon_capcut](ai-webtoon_capcut/README.md) | ai-webtoon 패널+음악+자막 → 편집 타임라인(JSON/CSV) 자동 생성 CLI | Python 3.12 | ★★★★☆ | `.\scripts\webtoon-capcut.ps1 build --song-dir ...` |

각 행의 완성도(★)와 상세 기능·기술 스택·알려진 제약은 폴더명 링크를 따라가면 확인할 수 있습니다.

### 주요 미완성/HOLD 항목

- **ai-webtoon_capcut**: Remotion 렌더러·CapCut 패키징 미구현 (HOLD, 설계 범위 밖 대형 기능). Python CLI 계층(타임라인 생성)은 완성.
- **run_game**: 로컬 MFC 빌드는 정기 검증 범위에서 제외 — 2026-05-28 검증 데이터를 인정하되 C++ 소스·프로젝트 설정 변경 시 사람 검토 재개.

검증 이력·테스트 통과 수·의존성 설치 기록의 전체 목록은 [`PROJECT_STATUS.md`](PROJECT_STATUS.md)를 참조하세요.

---

## 공통 특징

- 모든 프로젝트는 **Windows 10 환경** 기준으로 개발 (.bat 실행 스크립트 포함)
- 대부분 **로컬 실행 우선** 설계 (외부 클라우드 API 최소화)
- 음악/미디어 처리 관련 프로젝트가 다수 (Analysis_music, imagevideo, Pexels, lyricvideo, lyrics_tag, master_tag, mp3_daw, extensions)
- 보안/진단 도구 2종 (security_scanning, windows-port-monitor) — 내부망 진단·모니터링 용도
- **C++ / MFC 프로젝트 1종** (run_game) — Visual Studio 2022, Win32 API, 레지스트리 기반 게임 설치 탐지
- **웹툰 MV 제작 도구 2종** (ai-webtoon, ai-webtoon_capcut) — Suno 음원 기반 웹툰 패널 이미지 프롬프트 생성 및 영상 렌더링
- **`Doc/` 폴더**에 프로젝트별 AI 개발 프롬프트·설계 문서 통합 보관 (`{프로젝트명}_claude_Prompts` / `{프로젝트명}_codex_Prompts` 형식)
- **`Doc/designs/`** — 5개 카테고리별 아키텍처 설계 문서 (영상 파이프라인·음악 도구·미디어 다운로더·시스템 도구·알림 봇). 인덱스: [`Doc/DESIGN_INDEX.md`](Doc/DESIGN_INDEX.md)
- **`_ai_rules/` 폴더**에 신규 프로젝트 시작 시 참조할 공통 규칙·체크리스트 보관
