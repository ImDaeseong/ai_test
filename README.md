# 소스 설명

> 작성일: 2026-05-08 / 최종 수정: 2026-06-08 (ai_anime 제거, ai-webtoon_capcut CLI 구현 완료, Doc 폴더 정리, 설계 문서 작성 완료)
> 총 18개 소스 프로젝트 수록 (`Doc/` 폴더에 프로젝트별 AI 개발 프롬프트·설계 문서 통합 보관)
> 설계 문서 인덱스: [`Doc/DESIGN_INDEX.md`](Doc/DESIGN_INDEX.md) — 5개 카테고리별 아키텍처·기술 스택·핵심 패턴 기록

## 저장소 목표

`E:\ai_test`는 개인 도구 개발과 실험을 위한 작업 공간입니다.

프로그램 자체를 많이 만드는 것이 목표가 아니라, 음악, 영상 제작, AI 활용, 자동화, 수익화 실험, 생산성, 생활 개선을 더 빠르고 반복 가능하게 만드는 도구를 개발하는 것이 목적입니다.

주요 판단 기준은 실제 목표 달성, 반복 가능성, 유지보수성, 비용 통제, 보안, 현실성입니다.

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

## 목차

| # | 폴더명 | 주요 기능 | 언어/스택 | 완성도 |
|---|--------|-----------|-----------|--------|
| 1 | [Analysis_music](#1-analysis_music) | Suno AI 음악 분석 및 악보·비주얼 생성 | Python + Flask | ★★★★☆ |
| 2 | [check_FileEncoding](#2-check_fileencoding) | C/C++ 소스 파일 인코딩 검사 | Go | ★★★★★ |
| 3 | [extensions](#3-extensions) | Suno.com 동기화 가사 다운로드 Chrome 확장 | React/JS (MV3) | ★★★★★ |
| 4 | [imagevideo](#4-imagevideo) | 가사 파일 + 오디오 → 가사 영상(MP4) 파이프라인 | Node.js + FFmpeg | ★★★★☆ |
| 5 | [Pexels](#5-pexels) | Gemini + Pexels + FFmpeg 기반 스톡 영상 자동 생성 | Python + FFmpeg | ★★★★★ |
| 6 | [lyrics_tag](#6-lyrics_tag) | LRC 동기화 가사 수동 타이밍 작성 도구 | Python + Flask | ★★★★★ |
| 7 | [lyricvideo](#7-lyricvideo) | Remotion 기반 가사 비디오 자동 생성 | TypeScript + React | ★★★★★ |
| 8 | [master_tag](#8-master_tag) | Suno AI 음원 자동 마스터링 (웹 UI) | Python + Flask | ★★★★★ |
| 9 | [mp3_daw](#9-mp3_daw) | 로컬 오디오 분석·마스터링·Stem 분리 DAW | Go + Python | ★★★★☆ |
| 10 | [mp4_tag](#10-mp4_tag) | 웹사이트 HLS/MP4 영상 자동 감지 & 다운로드 | Python + Playwright | ★★★★☆ |
| 11 | [security_scanning](#11-security_scanning) | 웹·시스템 보안 취약점 스캐너 | Python | ★★★★☆ |
| 12 | [weather_alarm](#12-weather_alarm) | 기상청 날씨 → Discord/Telegram 알림 봇 | Python (asyncio) | ★★★★☆ |
| 13 | [ai_anime_production](#13-ai_anime_production) | 별도 MV 프롬프트 워크플로 기반 Remotion 씬 렌더링 워크스페이스 | TypeScript + React + Remotion | ★★★★☆ |
| 14 | [findstring_foldfiles](#14-findstring_foldfiles) | 폴더·드라이브 문자열 멀티스레드 검색 GUI | Python (tkinter) | ★★★★★ |
| 15 | [windows-port-monitor](#15-windows-port-monitor) | Windows TCP/UDP 포트 연결 이력 모니터링 서비스 | Python + SQLite | ★★★★★ |
| 16 | [run_game](#16-run_game) | Steam·Epic·Netmarble 게임 설치 탐지 및 런처 실행기 | C++ / MFC (Visual Studio 2022) | ★★★★★ |
| 17 | [ai-webtoon](#17-ai-webtoon) | 웹툰 만화 패널 이미지 프롬프트 자동 생성 | Python + Flask | ★★★★★ |
| 18 | [ai-webtoon_capcut](#18-ai-webtoon_capcut) | 웹툰 패널 이미지 → 편집 타임라인 자동 생성 Python CLI | Python 3.12 | ★★★★☆ |

---

## 1. Analysis_music

### 기능 개요
Suno AI 음악 프롬프트와 오디오 파일을 입력받아 음악 이론 분석, LilyPond 악보 코드, 비주얼 콘텐츠 프롬프트를 자동 생성하는 도구.

### 주요 기능
- **Suno 프롬프트 파싱**: 제목, 장르, BPM, 키, 섹션, 가사 메타데이터 추출 (130+ 장르 자동 감지)
- **오디오 분석**: librosa로 실제 MP3/WAV 분석 (BPM, 키, 동적 범위, 섹션 에너지)
- **음악 이론 보고서**: 장르별 화음 진행, 전조 제안, 구조 최적화 권고 (`report.md`)
- **LilyPond 악보 생성**: 음표·화음·한글 가사 포함 악보 코드 (`.ly`)
- **비주얼 프롬프트**: Midjourney/DALL·E 앨범아트 프롬프트, Runway/Kling 영상 씬, Reels 스타일 가이드 (`visual_prompts.md`)
- **웹 UI**: Flask + SSE 실시간 진행률, 결과 탭별 표시, 파일 다운로드

### 폴더 구조
```
Analysis_music/
├── analyzer/        # suno_parser.py, audio_analyzer.py
├── generators/      # report_gen.py, lilypond_gen.py, visual_gen.py
├── web/             # app.py (Flask), static/, templates/
├── config.py        # 장르→BPM 매핑, 조성→LilyPond 변환 테이블
├── main.py          # CLI 진입점
├── run_web.bat      # Windows 웹서버 실행 스크립트
└── requirements.txt
```

### 사용 방법
```bash
# 웹 UI (권장)
run_web.bat
# → http://localhost:5000

# CLI 모드
python main.py --prompt sample_prompt.txt --audio song.mp3
python main.py --prompt sample_prompt.txt --no-lilypond --no-visual
```

### 기술 스택
- 백엔드: Python 3.9+ / Flask 3.0
- 오디오: librosa, soundfile, scipy, numpy
- 한글 지원: UTF-8, colorama (Windows)

### 개발 완성도: ★★★★☆
웹 UI·CLI·4종 출력물 모두 동작. LilyPond 악보는 외부 LilyPond 설치 시 PDF 렌더링 가능. 오디오 없이 프롬프트만으로도 실행 가능.

---

## 2. check_FileEncoding

### 기능 개요
C/C++ 소스 파일(`.cpp`, `.h`, `.hpp`, `.c`, `.rc`)의 문자 인코딩과 BOM(Byte Order Mark) 여부를 폴더 단위로 일괄 검사하는 웹 기반 도구.

### 주요 기능
- **인코딩 감지**: UTF-8 BOM / UTF-8 No BOM / UTF-16 LE / UTF-16 BE / EUC-KR(CP949) 판별
- **병렬 스캔**: 64개 goroutine 워커로 대규모 프로젝트 고속 처리
- **웹 UI**: 인코딩별 필터 카드, 200개/페이지 페이지네이션, CSV 내보내기(Excel 호환)
- **취소 및 타이머**: 10분 타임아웃, AbortController 기반 취소 지원
- **외부 의존성 없음**: Go 표준 라이브러리만 사용

### 폴더 구조
```
check_FileEncoding/
├── main.go          # HTTP 서버 + 인코딩 감지 로직
├── main_test.go     # 유닛 테스트
├── go.mod           # go 1.22.3
└── index.html       # 웹 UI
```

### 사용 방법
```bash
go build
.\fileencoding.exe        # 실행 → 브라우저 자동 열림
# → http://localhost:8080
# 경로 입력 후 스캔 버튼 클릭
```

### 기술 스택
- Go 1.22.3 / net/http (표준 라이브러리만)
- 프론트엔드: HTML5 + Vanilla JS

### 개발 완성도: ★★★★★
단독 실행 바이너리, 유닛 테스트 포함, 에러 처리 완비. 실무 바로 투입 수준.

---

## 3. extensions

### 기능 개요
Suno.com 노래 페이지에서 동기화 가사를 LRC 또는 SRT 형식으로 다운로드하는 Chrome 브라우저 확장 프로그램.

### 주요 기능
- **LRC 다운로드**: `[MM:SS.mm]` 싱크 가사 형식 (음악 플레이어 호환)
- **SRT 다운로드**: `HH:MM:SS,MMM` 자막 형식 (영상 편집 프로그램 호환)
- **지능형 타이밍**: words vs lines 데이터 품질 자동 비교 후 최적 소스 선택
- **파형 에너지 기반 보정**: 누락 타이밍을 음성 파형 에너지로 자동 보간
- **SPA 지원**: pushState/replaceState 감지 → 페이지 이동 시 버튼 자동 재주입
- **다국어 UI**: 12개 언어 자동 감지 (한국어 포함)

### 폴더 구조
```
extensions/suno-lyric-downloader/
├── src/
│   ├── background.js        # Service Worker (URL 변경 감지)
│   ├── contentScript.js     # 메인 로직 (550줄 - 버튼 주입, 파형 분석, 포맷 변환)
│   └── popup/               # React 18 팝업 UI
├── dist/                    # 배포용 빌드 결과물
├── _locales/                # 12개 언어 다국어 파일
├── manifest.json            # Manifest V3
└── package.json             # vite + React + Tailwind CSS
```

### 사용 방법
```bash
# 빌드
npm install && npm run build

# Chrome 설치
# chrome://extensions/ → 개발자 모드 → 압축해제된 확장 로드 → dist/ 폴더 선택
# suno.com/song/* 페이지에서 커버 이미지 위에 LRC / SRT 버튼 클릭
```

### 기술 스택
- Chrome Extension Manifest V3
- React 18 + Tailwind CSS 4 (팝업 UI)
- Vite 6 (번들러)
- Suno Studio API (가사/음성 파형 데이터)

### 개발 완성도: ★★★★★
v2.0.5 완성 버전. dist/ 폴더에 빌드된 배포 파일 포함. 신호 처리 알고리즘(파형 에너지 배분, 퍼센타일 기반 임계값)까지 구현된 고품질 확장.

---

## 4. imagevideo

### 기능 개요
LRC/SRT/JSON 가사 파일과 오디오, 배경 이미지 또는 배경 영상을 입력받아 FFmpeg 기반 4단계 파이프라인으로 가사 영상(MP4)을 자동 생성하는 Node.js 프로젝트.

### 주요 기능
- **4단계 파이프라인**: plan → subtitles → render → compose
  1. **생산 계획 생성**: 가사→타이밍 세그먼트, 색상·조명·카메라 모션 자동 추론
  2. **ASS 자막 생성**: Advanced SubStation Alpha 고급 자막 (카라오케 모드 포함)
  3. **타이포그래피 렌더링**: FFmpeg 줌/팬 모션, 배경 영상 루프, 어두운 오버레이, 비네트(`vignette=angle=`), 곡물 노이즈
  4. **최종 합성**: 오디오 + 인트로 타이틀 오버레이(선택) + H.264/AAC MP4 출력
- **다중 형식 지원**: SRT / LRC / JSON 가사, MP3/WAV 오디오, PNG/JPG/WEBP 배경 이미지, MP4/MOV/WEBM 배경 영상
- **종횡비**: 16:9 / 9:16 / 1:1
- **자동 파일 감지**: `input/` 폴더에서 파일 타입 자동 인식
- **실행 옵션**: `--title`, `--artist`, `--audio`, `--clean`, `--debug`, 단계별 `--skip-*` 옵션 지원
- **검증 자동화**: ffprobe로 최종 MP4 해상도·코덱·재생시간 검증

### 버그 수정 이력 (2026-05-20)
| # | 파일 | 버그 내용 | 수정 내용 |
|---|------|-----------|-----------|
| 1 | `renderTypographyVideo.js` | `vignette` 필터 positional 2번째 인자가 강도가 아닌 `x0` (x 중심 좌표) | named `angle=` 파라미터로 변경; vignetteStrength(0.28–0.44) → angle(PI/4–PI/7) 매핑 |
| 2 | `composeFinalVideo.js` | Windows에서 `drawtext` fontconfig 부재로 exit 0xC0000005 크래시 (한글 제목 포함) | `resolveFontParam()`으로 `malgun.ttf`→`arial.ttf`→`ARIALUNI.TTF` 순서로 탐색, `fontfile=` 자동 주입 |
| 3 | `motion/project.ts` | `makeProject({ variables: {...} })`는 캔버스 크기·FPS에 영향 없음 (user data 전용 필드) | `variables` 블록 제거; `renderLyricsScene.ts`에서 `project.meta` 자동 생성으로 대체 |
| 4 | `motion/scenes/lyricsScene.tsx` | `filters={{ blur: value }}` — `filters` prop 타입은 `Filter[]` 배열 | `import {blur}` 추가; `filters={[blur(initial.blur)]}` 형식으로 수정 |
| 5 | `motion/styles/typography.ts` | 일반 객체 리터럴은 `PossibleCanvasStyle`에 할당 불가 | `import {Gradient}`; `new Gradient({...})` 인스턴스 생성으로 수정 |
| 6 | `tsconfig.json` (신규) | Motion Canvas `.tsx` 씬 파일 TypeScript 설정 없음 → `?scene` 모듈 미해석, JSX 타입 오류 숨김 | `tsconfig.json` 생성; `jsxImportSource: "@motion-canvas/2d/lib"`, `types: ["@motion-canvas/core/project"]` |

### 폴더 구조
```
imagevideo/
├── src/
│   ├── planner/             # generateProductionPlan.js
│   ├── subtitles/           # generateAssSubtitles.js
│   ├── render/              # renderTypographyVideo.js
│   ├── ffmpeg/              # composeFinalVideo.js
│   ├── pipeline/            # runLyricVideoPipeline.js (전체 파이프라인)
│   ├── validate/            # validateMediaOutput.js
│   ├── motion/              # Motion Canvas 실험 경로 (씬/스타일/생성 스크립트)
│   └── utils/               # inputDiscovery, lyricParsers, timecode, mediaProbe
├── input/                   # 입력 파일 (가사, 오디오, 배경)
├── output/                  # 생성 결과물 + 로그
├── tsconfig.json            # Motion Canvas 씬 전용 TypeScript 설정
└── package.json             # ESM, Motion Canvas 3.17 포함
```

### 사용 방법
```bash
# input/ 폴더에 가사 파일(LRC/SRT/JSON), 오디오(WAV/MP3), 배경 이미지/영상(선택) 배치

npm run lyric-video -- --clean              # 전체 파이프라인 실행
npm run lyric-video -- --clean --title "곡명"   # 인트로 제목 오버레이 포함
npm run plan                                # 1단계만 실행
npm run render:typography -- --motion-strength high  # 3단계, 모션 강도 지정
npm run motion:dev                          # Motion Canvas 실험 경로 미리보기
npm run validate:media                      # 최종 MP4 검증
```

### 기술 스택
- Node.js 20+ / ESM 모듈
- FFmpeg 8.1 / ffprobe (시스템 설치 필요)
- Motion Canvas 3.17.2 (실험적 경로; TypeScript 설정 완비)

### 개발 완성도: ★★★★☆
실데이터(`환승역.mp3`, LRC/SRT, JPEG)로 전체 파이프라인 end-to-end 검증 완료. 출력: 1920×1080, h264/aac, 195.967s, 22.4MB. FFmpeg 공식 문서 기준 버그 6건 수정 (vignette named parameter, Windows fontconfig, Motion Canvas makeProject variables, filters prop, Gradient 인스턴스, tsconfig). Motion Canvas 경로는 씬 생성·개발 미리보기까지 준비되어 있으나, 패키지의 안정적인 비대화형 렌더 CLI가 없어 실험 경로로 분리 유지.

---

## 5. Pexels

### 기능 개요
`data/` 폴더의 가사·대본·오디오·자막 파일을 기반으로 Gemini가 장면 JSON을 생성하고, Pexels에서 장면별 스톡 영상을 검색·다운로드한 뒤 FFmpeg로 YouTube용 가로 영상과 Shorts용 세로 영상을 자동 생성하는 로컬 자동화 도구.

### 주요 기능
- **Gemini 장면 분석**: 입력 텍스트를 검증된 씬 JSON으로 변환 (Pydantic 모델 검증)
- **Pexels 영상 검색**: 장면별 키워드로 스톡 영상 검색·스코어링 후 최적 MP4 선택 (`/v1/` 공식 엔드포인트, `per_page=15`)
- **다운로드 캐시**: 선택된 Pexels MP4를 다운로드하고 기존 캐시 파일 재사용 (빈 결과 캐시 방지)
- **FFmpeg 렌더링**: 클립 트림(`-g 60` YouTube 권장 GOP) → concat → 음악/자막 오버레이 (`-c:v copy` 무손실 export)
- **이중 출력**: `final_landscape.mp4`(1920×1080, 16:9)와 `final_shorts.mp4`(1080×1920, 9:16) 동시 생성
- **HTML 리포트**: 최종 영상과 장면별 클립을 확인하는 `output/index.html` 브라우저 리포트 생성
- **안전 처리**: 외부 API 타임아웃/재시도, Gemini JSON 검증, FFmpeg 인자 리스트 호출로 shell injection 방지, MP3 앨범아트 스트림 자동 제외(`-vn`)

### 폴더 구조
```
Pexels/
├── app/
│   ├── main.py                  # CLI 진입점
│   ├── config.py                # 환경변수·경로 설정
│   ├── models/                  # Pydantic 요청/응답/장면 스키마
│   ├── services/                # Gemini, Pexels, 다운로드, FFmpeg, 리포트, 프로젝트 저장소
│   └── utils/                   # 재시도, 파일 유틸
├── data/                        # 입력 파일 (.lrc/.srt/.txt + 오디오)
├── storage/                     # 캐시, 원본 영상, 처리 중간 파일
├── output/                      # final_landscape.mp4, final_shorts.mp4, index.html
├── scripts/                     # 데이터 검증, 생성, 스토리지 정리
├── tests/                       # 서비스별 pytest 테스트 (21개)
├── run.bat                      # 전체 자동 실행
├── dev_tools.bat                # 테스트/검증/정리 개발 도구
└── requirements.txt
```

### 사용 방법
```bash
# 1. .env.example을 .env로 복사하고 API 키 설정
#    GEMINI_API_KEY, PEXELS_API_KEY

# 2. data/ 폴더에 입력 파일 배치
#    가사/대본: .lrc, .srt, .txt
#    오디오:    .wav, .mp3, .m4a, .aac
#    자막:      .srt

run.bat                 # 테스트 실행 후 가로/세로 영상 생성 및 리포트 열기
dev_tools.bat           # 테스트, 데이터 검증, 캐시 정리 등 개발 메뉴

# CLI 직접 실행
python -m app.main --input data\lyrics.txt --orientation landscape
python -m app.main --text "scene text" --orientation portrait --style cinematic
```

### 기술 스택
- Python / Pydantic 2
- Gemini API (`gemini-2.5-flash`), Pexels API (`/v1/`), httpx
- FFmpeg (PATH 설치 필요) — H.264 CRF18, AAC 320kbps, yuv420p, faststart
- pytest 21개 테스트 (서비스별 단위 테스트 + 실 API 통합 검증)

### 개발 완성도: ★★★★★
Pexels `/v1/` URL 수정, FFmpeg 이중 인코딩 제거(`-c:v copy`), YouTube 권장 GOP(`-g 60`), 빈 검색 결과 캐싱 버그 수정, MP3 앨범아트 스트림 처리(`-vn`) 등 공식 문서 기준 버그 7건 수정 완료. `.env`에 API 키 설정 후 `run.bat` 한 번으로 테스트 → landscape/shorts 동시 생성 → HTML 리포트 자동 열기까지 end-to-end 동작 확인.

---

## 6. lyrics_tag

### 기능 개요
오디오 파일을 재생하면서 가사 줄마다 현재 재생 시간을 수동으로 태깅하여 LRC 동기화 가사 파일을 생성하는 웹 기반 도구.

### 주요 기능
- **오디오 재생**: MP3, MP4, M4A, WebM 등 지원
- **수동 타이밍 태깅**: Space 키 또는 클릭으로 현재 시간을 해당 가사 줄에 기록
- **실시간 강조**: 재생 위치에 해당하는 가사 줄 자동 하이라이트
- **LRC 다운로드**: 표준 `[MM:SS.mm]` 형식으로 파일 다운로드
- **단축키**: Space(태그+다음줄), P(재생/정지), ←→(2초 이동), ↑↓(줄 이동)
- **PyInstaller 패키징**: 단독 exe 배포 가능

### 폴더 구조
```
lyrics_tag/
├── app.py              # Flask 서버 (환경변수 기반 제한 설정)
├── templates/
│   └── index.html      # 웹 UI (다크 테마)
├── static/
│   ├── app.js          # 프론트엔드 로직
│   └── style.css
├── run.bat             # 실행 스크립트 (백그라운드 + 브라우저 자동 오픈)
├── stop.bat            # 종료 스크립트
├── requirements.txt    # Flask, waitress
└── LRCTagger.spec      # PyInstaller 빌드 설정
```

### 사용 방법
```bash
run.bat                 # 실행 → http://127.0.0.1:5000 자동 오픈
stop.bat                # 종료

# 또는
python app.py
```

### 기술 스택
- Python / Flask 3.1 / Waitress WSGI
- HTML5 + CSS3 + Vanilla JS (다크 테마)

### 개발 완성도: ★★★★★
단순·명확한 기능 완성. PyInstaller exe 빌드 설정 포함. 환경변수로 세그먼트 수·파일 크기 제한 조절 가능.

---

## 7. lyricvideo

### 기능 개요
Remotion 프레임워크(React 기반 비디오 생성)를 사용하여 LRC/SRT 가사 파일과 오디오를 조합해 가사 비디오(MP4)를 프로그래밍 방식으로 렌더링하는 프로젝트. 애니메이션 품질 개선 완료.

### 주요 기능
- **가사 동기화 시각화**: 현재/이전/다음 3줄 동시 표시, `interpolate()` 기반 페이드 인/아웃
- **음파형 시각화**: SVG 기반 실시간 음파형 (스파이크 바 + 라인 웨이브 + 파티클) — 결정적 계산(`Math.sin`) 사용으로 렌더링 재현성 보장
- **인트로 애니메이션 (`spring()`)**: 곡명 오버레이 진입 시 `spring({damping:14, stiffness:100, mass:0.8})`으로 물리 기반 자연 감속 — 기존 선형 `interpolate` 대비 품질 향상
- **Sequence 타임라인 관리**: 인트로 구간을 Remotion `Sequence`로 명시, 수명 자동 관리 (Remotion 공식 권장 방식)
- **아웃트로**: `interpolate()` 기반 검은 페이드아웃
- **배경 유연성**: 이미지(줌 애니메이션) / 비디오(`OffthreadVideo`) / 그라디언트 기본 배경
- **이중 포맷**: 16:9(1920×1080, YouTube) / 9:16(1080×1920, Shorts/Reels/TikTok)
- **자동 매니페스트**: `public/media/` 폴더 파일 자동 감지 스크립트 (`write-media-manifest.mjs`)
- **오디오**: `Html5Audio` — Remotion 4.x 공식 권장 컴포넌트 (`Audio`는 동일 버전에서 deprecated)
- **메타데이터**: `meta.json`으로 제목/아티스트 지정 시 인트로 오버레이에 표시

### 폴더 구조
```
lyricvideo/
├── src/
│   ├── index.ts             # Remotion 루트 등록
│   ├── Root.tsx             # 컴포지션 정의 (오디오 길이 자동 계산, delayRender/continueRender)
│   ├── LyricVideo.tsx       # 메인 렌더링 컴포넌트 (spring·Sequence·Html5Audio 적용)
│   ├── config.ts            # 해상도·타이밍·스타일 중앙 설정
│   ├── parsers.ts           # LRC/SRT 파서
│   └── mediaManifest.ts     # 자동 생성 (gitignore)
├── scripts/
│   └── write-media-manifest.mjs  # 미디어 파일 자동 감지
├── public/media/            # 입력 파일 저장소 (gitignore)
├── out/                     # 렌더링 출력 (gitignore)
├── render-video.bat         # 렌더링 배치 스크립트 (포맷 선택)
├── start-studio.bat         # Remotion Studio 개발 환경 시작
└── package.json             # Remotion 4.0.458 + React 19
```

### 사용 방법
```bash
# 1. public/media/ 폴더에 파일 배치
#    - 오디오: *.mp3 또는 *.wav
#    - 가사:   *.lrc 또는 *.srt
#    - 배경:   (선택) 이미지/비디오
#    - 메타:   meta.json {"title":"곡명","artist":"아티스트"}  ← 인트로 표시용

render-video.bat             # 포맷 선택 후 out/ 폴더에 MP4 생성
start-studio.bat             # 개발 미리보기 → http://localhost:3000

npm run build                # 16:9 렌더링 (H.264, CRF 18)
npm run build:vertical       # 9:16 렌더링
```

### 기술 스택
- Remotion 4.0.458 + React 19 (`spring`, `Sequence`, `interpolate`, `Html5Audio`, `OffthreadVideo`)
- TypeScript 5.9 / Vite 7
- `@remotion/media-utils` (오디오 FFT 시각화)
- FFmpeg (Remotion 내장 렌더러)

### 개발 완성도: ★★★★★
전체 렌더링 테스트 완료 (환승역.mp3, 21.8MB, 5909프레임 / 약 3분 17초). TypeScript 타입 검사 통과. Remotion 베스트 프랙티스(`spring()`, `Sequence`) 반영 완료. `public/media/`에 오디오·가사 파일 배치 후 즉시 렌더링 가능.

---

## 8. master_tag

### 기능 개요
Suno AI로 생성한 음원을 YouTube 업로드 표준(-14 LUFS)으로 자동 마스터링하는 웹 기반 오디오 처리 도구.

### 주요 기능
- **5단계 마스터링 파이프라인**:
  1. 오디오 분석 (Peak dBFS / RMS / Duration / Sample Rate)
  2. Gain Staging (피크 → -6 dBFS 조정)
  3. DSP 체인: HPF(30Hz) + 4밴드 EQ + Compressor(3:1, 10ms/150ms)
  4. LUFS 정규화 (ITU-R BS.1770-4 기준 -14 LUFS)
  5. 브릭월 리미터 (-1 dBFS 피크 보호)
- **웹 UI**: 드래그앤드롭, SSE 실시간 진행률, 단계별 애니메이션
- **병렬 처리**: CPU 코어 수 기반 동시 작업 (기본 CPU/2 워커)
- **자동 정리**: 6시간 TTL 만료 작업 및 파일 자동 삭제
- **PyInstaller 배포**: 단독 exe 번들 가능

### 폴더 구조
```
master_tag/
├── main.py             # 오디오 처리 엔진 (DSP 체인, LUFS 정규화)
├── server.py           # Flask REST API + SSE 스트림 + 작업 큐 관리
├── index.html          # 웹 UI (다크 테마, 5단계 진행 카드)
├── requirements.txt    # Flask, pedalboard, librosa, pyloudnorm
└── SunoMastering.spec  # PyInstaller 빌드 설정
```

### 사용 방법
```bash
python server.py        # 서버 실행 → http://localhost:5000
# 드래그앤드롭으로 WAV/MP3/FLAC/M4A 파일 업로드 → 마스터링 → 다운로드

# CLI
python main.py "song.mp3"   # → song_mastered.wav 생성
```

### 기술 스택
- Python / Flask 3.0
- pedalboard 0.9 (Spotify 오픈소스 오디오 DSP 라이브러리)
- librosa, pyloudnorm, soundfile, numpy

### 개발 완성도: ★★★★★
멀티스레딩, 재시도 로직, 자동 정리, REST API, SSE 스트림 모두 완성. 파일 크기 제한(300MB), 에러 처리, 로깅까지 프로덕션 수준.

---

## 9. mp3_daw

### 기능 개요
오디오 파일의 분석, 인텔리전트 마스터링, AI 기반 Stem 분리(보컬/드럼/베이스/기타)를 제공하는 로컬 클라우드 프리 DAW 시스템. Go 웹 서버 + Python 오디오 엔진의 하이브리드 아키텍처.

### 주요 기능
- **오디오 분석**: BPM, Key, 7개 주파수 대역, LUFS (librosa)
- **인텔리전트 마스터링**: HPF + 적응형 EQ + Glue Compressor + M/S 스테레오 처리 + pyloudnorm 정규화
- **AI Stem 분리**: Demucs 딥러닝 모델 (보컬/드럼/베이스/기타 4-track)
- **파일 감시 자동화**: `inbox/` 폴더 모니터링 → 오디오 자동 파이프라인 처리 (fsnotify)
- **웹 UI**: Wavesurfer.js 파형 뷰어, 주파수 대역 막대 그래프
- **REST API**: 분석/마스터링/분리/파이프라인 4개 엔드포인트 + 작업 폴링
- **클라이언트 식별**: Cookie 기반 세션, 24시간 작업 이력 자동 정리

### 폴더 구조
```
mp3_daw/
├── engine.py           # Python 오디오 처리 엔진 (CLI 포함)
├── main.go             # Go 웹 서버 (Gin), Worker 풀, 파일 감시
├── go.mod              # gin, fsnotify
├── requirements.txt    # librosa, pedalboard, demucs, pyloudnorm
└── static/
    └── index.html      # 웹 UI (Wavesurfer.js, 4탭)
```

### 사용 방법
```bash
# Go 서버 빌드 및 실행
go build && .\main.exe
# → http://localhost:8080

# Python 엔진 직접 CLI
python engine.py analyze song.mp3
python engine.py master song.mp3 --lufs -14
python engine.py separate song.mp3 --model htdemucs
python engine.py pipeline song.mp3 --lufs -14

# 폴더 자동 처리: inbox/ 폴더에 오디오 파일 복사하면 자동 분석+마스터링
```

### 기술 스택
- Go 1.21 (Gin 1.9, fsnotify 1.7) - 웹 서버
- Python 3.9+ (librosa, pedalboard, demucs, pyloudnorm) - 오디오 엔진
- Wavesurfer.js - 파형 시각화

### 개발 완성도: ★★★★☆
4탭 웹 UI, 파일 감시, 병렬 Worker 풀 모두 동작. Demucs는 GPU 없이 CPU로도 실행 가능하나 처리 시간이 길다. Stem 분리는 초대용량 모델 다운로드 필요.

---

## 10. mp4_tag

### 기능 개요
웹 페이지를 Playwright 브라우저로 로드하여 HLS/DASH/MP4 스트림을 자동 감지하고 yt-dlp/FFmpeg으로 다운로드하는 멀티소스 영상 다운로더.

### 주요 기능
- **스트림 자동 감지**: Playwright Chromium이 네트워크 요청 분석 (m3u8, mp4, ts, m4s, mpd)
- **YouTube 다운로드**: 8개 클라이언트 전략 폴백 (web, ios, android, tv 등)
- **HLS/DASH 지원**: master.m3u8에서 최고 대역폭 스트림 자동 선택
- **진행률 추적**: FFmpeg stderr 파싱, yt-dlp 후크 기반 실시간 진행률
- **Streamlit 웹 UI**: 스트림 목록 표시, 개별/Fallback 다운로드, 2초 자동 새로고침
- **병렬 다운로드**: ThreadPoolExecutor (기본 3개 동시)
- **PyInstaller exe 배포**: Playwright Chromium 자동 설치 포함

### 폴더 구조
```
mp4_tag/
├── main.py             # CLI 진입점 + Streamlit 실행
├── app.py              # Streamlit 웹 UI
├── downloader_core.py  # 핵심 다운로드 엔진 (감지, 분류, 다운로드)
├── job_manager.py      # 비동기 작업 큐 (UUID, 상태, 재시도)
├── server_limits.py    # 동시성 제한 (분석: 2, 다운로드: 3)
├── build_exe.py        # PyInstaller 빌드 스크립트
├── requirements.txt    # streamlit, playwright, yt-dlp, httpx, curl_cffi
└── downloads/          # 다운로드 저장 폴더
```

### 사용 방법
```bash
python main.py                                    # 웹 UI → http://localhost:8501
python main.py "https://example.com/video"        # CLI 다운로드
python main.py "https://..." --workers 5 --wait 10

# exe 빌드
python build_exe.py       # → dist/VideoDownloader.exe
```

### 기술 스택
- Python 3.12 / Streamlit 1.56
- Playwright 1.58 (Chromium 브라우저 자동화)
- yt-dlp 2026.3.17 (YouTube 다운로드)
- FFmpeg (스트림 다운로드), httpx, curl_cffi

### 개발 완성도: ★★★★☆
웹 UI·CLI·exe 배포 모두 지원. 8가지 YouTube 전략·Fallback 다운로드·재시도 로직 완성. Playwright 첫 실행 시 Chromium 다운로드 필요 (~200MB).

---

## 11. security_scanning

### 기능 개요
OWASP Top 10 기준으로 웹사이트 보안 헤더·TLS·디렉토리 노출을 검사하고, Windows 시스템의 열린 포트·의심 프로세스·시작프로그램·방화벽 상태를 스캔하는 통합 보안 진단 도구.

### 주요 기능

**웹 스캔 (4개 체크)**
- SecurityHeadersCheck: HSTS, CSP, X-Frame-Options 등 9개 헤더 검증
- TlsCheck: SSL/TLS 버전, 암호 스위트, 인증서 만료일 검사
- DirectoryListingCheck: 49개 민감 경로 프로브 (`/admin/`, `/backup/`, `/.git/` 등)
- HttpResponseCheck: 응답시간, 리다이렉트 체인, Mixed Content 감지

**시스템 스캔 (6개 체크)**
- PortScanner: 악성 포트(31337, 4444 등 45개) 및 위험 포트(23, 445, 3389 등) 감지
- ProcessMonitor: 프로세스 이름 스푸핑 감지, 의심 경로(Temp, Downloads, AppData) 프로세스
- NetworkMonitor: 악성 포트 연결, 의심 프로세스의 공개 IP 연결 과다 감지
- StartupScanner: 레지스트리 Run 키 + Startup 폴더, 의심 명령 패턴 (`powershell -e`, LOLbins)
- SecuritySoftwareCheck: Windows Defender 실시간 보호, 서명 날짜, 방화벽 3개 프로필
- FilePermissionChecker: 민감 디렉토리 icacls ACL (Everyone/Authenticated Users 쓰기 권한)

**리포팅**
- 위험 등급: Critical / High / Medium / Low / Info (ANSI 컬러 코딩)
- JSON 리포트: OWASP 매핑, 권고사항, 증거 포함
- 상위 5개 위험 항목 요약

### 폴더 구조
```
security_scanning/
├── main.py                  # CLI 진입점 (argparse, 권한 감지)
├── modules/
│   ├── web_scanner.py       # 웹 취약점 스캐너 (1323줄)
│   ├── system_scanner.py    # 시스템 보안 스캐너 (1391줄)
│   └── reporter.py          # 출력 및 JSON 리포트 (594줄)
├── requirements.txt         # requests, psutil, colorama
└── run_scan.bat             # 실행 예시 스크립트
```

### 사용 방법
```bash
python main.py --web https://example.com --system    # 웹+시스템 동시 스캔
python main.py --web https://example.com --threads 10 --timeout 15
python main.py --system --verbose                    # 시스템만, 전체 항목 표시
python main.py --web https://example.com --allow-private-targets

# 배치 실행
run_scan.bat
```

### 기술 스택
- Python 3.8+ / requests, psutil, colorama
- PowerShell (시스템 스캔 일부 기능), icacls, netsh

### 개발 완성도: ★★★★☆
웹·시스템 양방향 스캔, OWASP 매핑, JSON 리포트 완성. 총 10개 체크 모듈. OWASP Top 10 A02·A03·A05·A06 커버. 관리자 권한 없이도 기본 기능 동작 (일부 체크 제한).

---

## 12. weather_alarm

### 기능 개요
기상청 초단기실황 API로 서울 가산동 실시간 날씨를 조회하여 Discord 슬래시 명령 봇과 Telegram 텍스트 명령 봇을 통해 구독자에게 자동 브로드캐스트하는 알림 시스템.

### 주요 기능
- **날씨 수집**: 기상청 API → 기온, 습도, 강수형태, 풍향/풍속 파싱 (5분 캐시)
- **Discord 봇**: 슬래시 명령 (`/가산날씨`, `/날씨구독`, `/날씨구독해제`)
- **Telegram 봇**: 텍스트 명령 (`/weather`, `/subscribe`, `/unsubscribe`)
- **구독 시스템**: SQLite(로컬) / PostgreSQL(Docker) 자동 전환
- **발송 큐**: 비동기 발송 큐 + 지수 백오프 재시도 (최대 5회)
- **속도 제한**: Telegram 25 msg/s, Discord 20 msg/s AsyncRateLimiter
- **영구 실패 처리**: 권한 없음·채널 없음 등 영구 오류 시 구독자 자동 제거

### 폴더 구조
```
weather_alarm/
├── main.py                # 메인 루프 (설정 로드, 봇 병렬 실행)
├── weather_client.py      # 기상청 API 클라이언트 (aiohttp, 캐시)
├── broadcaster.py         # 발송 큐 처리 (재시도, 속도 제한)
├── notification_store.py  # SQLite/PostgreSQL DB 계층 (구독자 + 발송 큐)
├── discord_bot.py         # Discord 슬래시 명령 봇 (discord.py 2.x)
├── telegram_bot.py        # Telegram 명령 봇 (python-telegram-bot 20)
├── .env                   # API 키, 토큰, DB 연결 설정
├── run_local.bat          # 로컬 실행 (SQLite 모드)
└── requirements.txt       # aiohttp, discord.py, python-telegram-bot, loguru
```

### 사용 방법
```bash
# 1. .env 파일에 API 키 및 토큰 설정
#    WEATHER_SERVICE_KEY, DISCORD_TOKEN, TELEGRAM_TOKEN

# 2. 로컬 실행 (SQLite 사용)
run_local.bat

# 3. Discord에서
/날씨구독     → 현재 채널 구독 등록
/가산날씨     → 즉시 날씨 조회

# 4. Telegram에서
/subscribe   → 구독 등록
/weather     → 즉시 날씨 조회
```

### .env 필수 설정
| 키 | 설명 |
|----|------|
| `WEATHER_SERVICE_KEY` | 기상청 공공데이터 API 키 |
| `DISCORD_TOKEN` | Discord 봇 토큰 |
| `TELEGRAM_TOKEN` | Telegram BotFather 토큰 |
| `WEATHER_ALARM_LOCAL=1` | SQLite 사용 (미설정 시 PostgreSQL) |

### 기술 스택
- Python 3.12 / asyncio
- aiohttp (기상청 API), discord.py 2.x, python-telegram-bot 20
- loguru (로깅), SQLite / PostgreSQL

### 개발 완성도: ★★★★☆
양방향 봇(Discord/Telegram), 구독 DB, 발송 큐, 재시도 로직 완성. .env API 키 설정 후 즉시 실행 가능. Docker Compose + PostgreSQL + Redis + Celery 기반 리팩터링 예정.

---

## 13. ai_anime_production

### 기능 개요
별도 관리되는 애니메이션 MV 프롬프트 워크플로에서 생성된 씬 이미지와 영상 프롬프트를 입력받아 Remotion으로 개별 씬 클립(MP4)을 렌더링하는 프로덕션 워크스페이스.

### 주요 기능
- **입력 파이프라인**: `input/scene_NN_name.png` + `input/scene_NN_name.md` 쌍을 스캔하여 render manifest 자동 생성
- **프롬프트 자동 추출**: `.md` 파일에서 BPM, 씬 길이(`duration_seconds`), 카메라 방향, 강도 자동 파싱 — 하드코딩 금지
- **씬 클립 렌더링**: `SceneOnly` 컴포지션으로 씬별 1920×1080 MP4 생성 (`output/clips/`)
- **Remotion Studio**: `npm run studio`로 씬 미리보기 및 디버깅
- **캐릭터 참고 이미지**: `character_reference_prompt.png` (선택) — 없으면 풍경/배경 중심 씬으로 처리
- **run.bat**: 전체 파이프라인(import → typecheck → render) Windows 더블클릭 실행

### 폴더 구조
```
ai_anime_production/
├── src/
│   ├── index.ts                    # Remotion 루트 등록
│   ├── compositions/
│   │   └── SceneOnly.tsx           # 씬 클립 컴포지션
│   └── lib/
│       └── promptMotion.ts         # 프롬프트 키워드 → 카메라 모션 매핑
├── scripts/
│   ├── import_input.mjs            # input/ 스캔 → manifests/ 생성
│   ├── render_scenes.mjs           # output/clips/ MP4 렌더
│   └── check_assets.mjs            # manifest ↔ public/assets 일치 검증
├── input/                          # 씬 이미지(.png) + 프롬프트(.md) 입력
├── manifests/                      # render_manifest.json (자동 생성)
├── public/assets/images/           # import 후 복사된 씬 이미지
├── output/clips/                   # 렌더링된 씬 MP4
├── run.bat                         # Windows 실행 스크립트
└── package.json                    # Remotion 4.0.461 + React 19
```

### 사용 방법
```bash
# 1. input/ 폴더에 씬 파일 배치
#    scene_01_intro.png + scene_01_intro.md (반드시 basename 일치)
#    character_reference_prompt.png (선택)

# 2. 전체 파이프라인 실행
run.bat
# 또는
npm run build          # import:input → typecheck → render:scenes

# 단계별 실행
npm run import:input   # input/ 스캔 → manifests/render_manifest.json 생성
npm run check          # asset 검증
npm run render:scenes  # output/clips/{slug}.mp4 렌더

# Remotion Studio (미리보기)
npm run studio         # → http://localhost:3000
```

### 기술 스택
- TypeScript 5.8 + React 19
- Remotion 4.0.461 (`@remotion/cli`, `@remotion/media-utils`)
- Node.js (ESM 스크립트)

### 개발 완성도: ★★★★☆
입력 파이프라인·manifest 생성·씬 렌더링 완성. `input/`에 AI 생성 씬 이미지와 프롬프트를 넣고 `run.bat` 실행으로 씬별 MP4 클립 생성 가능. 별도 관리되는 애니메이션 MV 프롬프트 워크플로와 연계하여 사용.

---

## 14. findstring_foldfiles

### 기능 개요
폴더 또는 전체 드라이브에서 특정 문자열을 **멀티스레드로 빠르게 검색**하는 Python 데스크톱 GUI 앱.  
외부 패키지 없이 Python 표준 라이브러리(tkinter)만으로 동작하며 Windows/macOS/Linux 모두 지원.

### 주요 기능
- **폴더 검색**: Browse 버튼으로 폴더 선택 후 하위 전체 재귀 검색
- **드라이브 검색**: 드롭다운에서 드라이브 선택 또는 "Search all drives" 체크로 전체 드라이브 동시 검색
- **대소문자 구분**: "Case sensitive" 체크박스로 전환
- **확장자 필터**: 직접 입력 또는 프리셋 선택 (C/C++, Java, Kotlin, Swift, Web, 전체 텍스트)
- **바이너리 포함**: "Include binary-like files" 체크 시 모든 파일 검색
- **결과 표시**: 파일 경로, 줄 번호, 미리보기를 목록으로 표시
- **파일 열기**: 결과 더블클릭 또는 "Open selected file" 버튼으로 기본 앱에서 열기
- **검색 중단**: Stop 버튼으로 언제든 검색 취소

### 폴더 구조
```
findstring_foldfiles/
├── find_string_app.py   # 메인 소스 (SearchWorker + FindStringApp)
├── run.bat              # Windows 실행 배치파일
└── README.md
```

### 아키텍처
| 컴포넌트 | 클래스 | 설명 |
|---|---|---|
| 검색 엔진 | `SearchWorker(threading.Thread)` | 멀티스레드 파일 열거·검색, 결과를 `queue.Queue`에 PUT |
| GUI | `FindStringApp(tk.Tk)` | 100ms마다 큐 폴링, 최대 200개/사이클로 UI 동결 방지 |
| 결과 모델 | `@dataclass Match` | path, line_number, preview 저장 |

**텍스트 파일 판별 로직:**
1. 확장자가 49종 텍스트 목록(`.py`, `.js`, `.java`, `.go` 등)에 있으면 텍스트로 처리
2. 목록에 없으면 앞 2 KB를 읽어 null 바이트(`\x00`) 없으면 텍스트로 판별
3. `--include-binary-like` 옵션 시 모든 파일 강제 포함

**검색 제외 디렉터리:** `.git`, `.hg`, `.svn`, `__pycache__`, `node_modules`, `$Recycle.Bin`, `System Volume Information`

### 사용 방법
```bat
run.bat
```
또는:
```powershell
python find_string_app.py
```

### 기술 스택
- Python 3.10+ / **외부 패키지 없음** (표준 라이브러리만 사용)
- GUI: tkinter
- 동시성: threading + queue

### 개발 완성도: ★★★★★
멀티스레드 검색·UI 동결 방지·확장자 프리셋·드라이브 전체 검색 모두 완성.

---

## 15. windows-port-monitor

### 기능 개요
Windows 로컬 시스템의 TCP/UDP 포트 연결과 프로세스 소유권을 실시간 수집하여 SQLite에 이력을 저장하고 JSONL로 내보내는 백그라운드 모니터링 서비스.

### 주요 기능
- **포트 수집**: `psutil.net_connections`으로 TCP/UDP 소켓 전체 폴링 (기본 3초 주기)
- **프로세스 메타데이터**: PID → 프로세스명·실행 경로·사용자·서비스명 해석 (캐시 + `sc.exe queryex`)
- **SQLite 영구 저장**: WAL 모드, 인덱스 완비, 보존 기간(일) 설정으로 자동 정리
- **JSONL 내보내기**: append-only 형식으로 외부 분석 도구 연동 가능
- **백그라운드 실행**: `start_background.bat` → 숨김 프로세스로 시작, `stop_background.bat` → 우아한 종료 후 활동 리포트(Notepad)
- **Windows 서비스 등록**: `python main.py install/start/stop/remove` (pywin32)
- **단일 사이클 실행**: `python main.py once` — 스냅샷 용도
- **7/7 테스트 통과**: collector·storage·service·config 4개 모듈 pytest 완비

### 폴더 구조
```
windows-port-monitor/
├── main.py                     # CLI 진입점 (run / once / install / start / stop / remove / debug)
├── models.py                   # PortRecord·CollectorStats 데이터 모델
├── config_loader.py            # config/config.yaml 로더
├── logging_setup.py            # JSON 포맷 RotatingFileHandler
├── collector/
│   ├── port_collector.py       # psutil 기반 소켓 수집
│   └── process_resolver.py     # PID → 프로세스 메타데이터 해석
├── storage/
│   ├── sqlite_store.py         # SQLite WAL 저장소
│   └── json_exporter.py        # JSONL 내보내기
├── service/
│   ├── background_runner.py    # 폴링 루프·graceful shutdown·보존 정리
│   └── windows_service.py      # pywin32 서비스 래퍼
├── tests/                      # test_collector / test_storage / test_service / test_config_logging
├── config/config.yaml          # 폴링 주기·DB 경로·보존 기간·로그 레벨 설정
├── start_background.bat        # 숨김 백그라운드 시작
├── stop_background.bat         # 우아한 종료 + 활동 리포트
└── requirements.txt            # psutil, PyYAML, pywin32 (Windows), pytest
```

### 사용 방법
```powershell
# 환경 설정 (Python 3.11+)
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 수동 실행
python main.py run         # 연속 모니터링 (Ctrl+C로 종료)
python main.py once        # 1회 수집 스냅샷

# 백그라운드 실행 (권장)
start_background.bat       # 숨김 프로세스로 시작
stop_background.bat        # 종료 + data/port_process_history.txt 리포트 열기

# Windows 서비스 등록 (관리자 권한 필요)
python main.py install
python main.py start
python main.py stop
python main.py remove

# 테스트
pytest tests/
```

### config/config.yaml 주요 설정
| 키 | 기본값 | 설명 |
|----|--------|------|
| `collector.polling_interval_seconds` | `3.0` | 수집 주기 (초) |
| `storage.database_path` | `data/port_monitor.sqlite3` | SQLite DB 경로 |
| `storage.json_export_path` | `data/port_records.jsonl` | JSONL 내보내기 경로 |
| `storage.retention_days` | `7` | SQLite 이력 보존 기간 |
| `logging.level` | `INFO` | 로그 레벨 |

### 기술 스택
- Python 3.11+ / psutil 5.9+
- PyYAML (설정), pywin32 (Windows 서비스)
- SQLite (WAL 모드), JSONL
- pytest (7/7 테스트 통과)

### 개발 완성도: ★★★★★
collector·storage·service 전 계층 완성, 4개 모듈 pytest 통과. 백그라운드 배치 스크립트·Windows 서비스·단일 사이클 3가지 실행 모드 지원. 관리자 권한 없이도 기본 수집 가능 (일부 프로세스 정보 제한).

---

## 16. run_game

### 기능 개요
`GameConfig.json`에 정의된 게임 정보를 기준으로 Windows PC에서 Steam·Epic Games·Netmarble 설치 위치와 실행 가능한 런처를 탐지하고, 해당 플랫폼 런처를 통해 게임을 실행하는 MFC 다이얼로그 애플리케이션.

### 주요 기능
- **JSON 기반 설정**: `GameConfig.json`이 탐지 대상 게임의 유일한 설정 소스 — C++ 소스에 게임명·ID·경로 하드코딩 없음
- **3 플랫폼 탐지**: Steam(레지스트리 + ACF manifest + A–Z 드라이브 전탐색), Epic Games(레지스트리 + `.item` manifest + 드라이브 전탐색), Netmarble(레지스트리 + 드라이브 전탐색)
- **64비트 레지스트리 대응**: `KEY_WOW64_64KEY` → `KEY_WOW64_32KEY` → 기본 순서로 3단계 fallback
- **PC방 무하드 환경 대응**: 레지스트리 없을 때 FIXED/REMOTE 드라이브 전체를 순차 탐색
- **런처 경유 실행 전용**: Steam(프로토콜 URL) / Epic(프로토콜 URL) / Netmarble(런처 EXE 직접 기동) — EXE 직접 실행은 anti-cheat(XIGNCODE3)·Always-Online 인증 불가로 진단용에만 허용
- **버전 정보 추출**: Steam ACF `buildid`, Epic manifest `AppVersionString` 자동 파싱
- **일별 로테이션 로그**: `Log\LogEx{DD}.txt` (CP949, `CCriticalSection` 스레드 안전)
- **UAC RequireAdministrator**: 레지스트리 전역 읽기 보장

### 클래스 구조

| 클래스 | 파일 | 역할 |
|--------|------|------|
| `CGameInfo` | `GameInfoConfig.h/.cpp` | `GameConfig.json` 활성 게임 설정 보관 |
| `CGameInstallInfoManager` | `GameInstallInfoManager.h/.cpp` | 싱글톤 — 탐지 조율·결과 보관·실행 요청 |
| `CGameInstallSearch` | `GameInstallSearch.h/.cpp` | 3 플랫폼 탐지 진입점 (`SearchAll`) |
| `CSteamLauncherSearch` | `SteamLauncherSearch.h/.cpp` | Steam 설치·런처·manifest 탐지 |
| `CEpicLauncherSearch` | `EpicLauncherSearch.h/.cpp` | Epic manifest와 launch URL 탐지 |
| `CNetmarbleLauncherSearch` | `NetmarbleLauncherSearch.h/.cpp` | Netmarble 레지스트리·런처·게임 폴더 탐지 |
| `CGameInstallSearchCommon` | `GameInstallSearchCommon.h/.cpp` | 파일·경로·레지스트리·실행 공통 정적 함수 |
| `CAppLog` | `AppLog.h/.cpp` | 싱글톤 로그 (일별 로테이션) |

### 폴더 구조
```
run_game/
├── run_game/
│   ├── json/              # JsonCpp 번들 (allocator/reader/writer/value.h 등)
│   ├── res/               # 아이콘, RC2
│   ├── AppLog.h/.cpp
│   ├── GameInfoConfig.h/.cpp
│   ├── GameInstallSearchCommon.h/.cpp
│   ├── GameInstallSearch.h/.cpp
│   ├── GameInstallInfoManager.h/.cpp
│   ├── SteamLauncherSearch.h/.cpp
│   ├── EpicLauncherSearch.h/.cpp
│   ├── NetmarbleLauncherSearch.h/.cpp
│   ├── run_gameDlg.h/.cpp       # MFC 다이얼로그 (Steam/Netmarble/Epic 버튼)
│   └── run_game.vcxproj
├── GameConfig.json              # 게임 탐지 설정 (단일 진실 소스)
├── run_game.sln
└── README.md
```

### 사용 방법
```powershell
# Debug 빌드
& 'C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\amd64\MSBuild.exe' 'run_game.sln' /t:Clean,Build /p:Configuration=Debug /p:Platform=x64 /m

# Release 빌드
& 'C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\amd64\MSBuild.exe' 'run_game.sln' /t:Clean,Build /p:Configuration=Release /p:Platform=x64 /m

# GameConfig.json 스키마 검증
python -m json.tool GameConfig.json
```

빌드 산출물: `run_game\x64\Debug\run_game.exe` / `run_game\x64\Release\run_game.exe`

실행 시 관리자 권한 필요 (UAC RequireAdministrator).

게임 전환: `GameConfig.json`의 `games[]` 배열에서 실행할 게임 하나만 `"enabled": true`로 설정하고 나머지는 `false`로 지정.

### 기술 스택
- Visual C++ 2022 (VC++ 17.x) / MFC / Unicode / Static MFC / x64
- JsonCpp (번들) — `run_game\json\`
- Win32 API: `RegOpenKeyEx`, `RegQueryValueEx`, `ShellExecute`, `ShellExecuteEx`, `GetFileVersionInfo`
- `version.lib` (`#pragma comment(lib, "version.lib")`)
- `CCriticalSection` 기반 스레드 안전 로깅

### 개발 완성도: ★★★★★
2026-05-28 검증: Debug/Release 클린 빌드 warning 0 / error 0. `GameConfig.json` 파싱 정상. 레거시 심볼(Diskless 탐지, 서버 JSON 다운로드, Kingsroad 하드코딩 폴백) 완전 제거 확인. AI 개발 프롬프트: `run_game_codex_Prompts/2.초기화 프롬프트.md`.

---

## 17. ai-webtoon

### 기능 개요
귀여운 오리지널 cartoon 스켈레톤 밴드 세계관을 유지하면서, 곡마다 BPM·장르·감정에 맞는 웹툰 만화 패널 이미지 프롬프트를 자동 생성합니다. 영상 AI 없이 이미지만으로 뮤직비디오를 제작합니다.

### 주요 기능
- `ai_img_video_prompt`와 완전히 동일한 입력 형식 (txt 파일 재사용)
- BPM·감정 키워드 기반 5가지 스타일 자동 선택 (cute_manhwa / cute_action / cute_pop / cute_emotional / cute_dramatic)
- 곡당 25~50개 패널 자동 생성 (섹션 × BPM 구간)
- 4개 이미지 플랫폼 프롬프트 동시 생성 (GPT Image / Nijijourney / FLUX.1 / Gemini)
- 저작권 안전 오리지널 캐릭터 디자인 (특정 IP 미참조)
- 웹 뷰어 제공 (프롬프트 복사용 포트 5350)

### 폴더 구조
```
ai-webtoon/
├── main.py           # CLI 진입점 (create / create-all / summarize-all)
├── web_app.py        # Flask 웹 뷰어
├── configs/          # 스타일·패널·플랫폼 설정 JSON
├── scripts/          # 파이프라인·검증 스크립트
├── input/            # 곡 정보 txt 파일
├── output/           # 생성된 프롬프트 (곡별 폴더)
├── tests_unit.py     # 52개 단위 테스트
├── run_all.bat       # 전체 input/ 일괄 처리
└── requirements.txt  # flask
```

### 사용 방법
```bash
pip install flask
.\run_all.bat                                        # 전체 input/ 처리
python main.py create --input "input\곡명.txt"       # 단일 곡
python main.py create-all --input-dir input --force  # 전체 배치
python -m pytest tests_unit.py -q                    # 테스트
실행_web.bat                                         # 웹 뷰어 → http://127.0.0.1:5350
```

### 기술 스택
- Python 3.x / Flask (웹 뷰어)
- 외부 AI API 없음 (이미지 생성 시 GPT Image / Nijijourney 등 선택)

### 개발 완성도: ★★★★★
212/212 PASS, 52개 단위 테스트 통과. 웹 뷰어 포함. 프로덕션 사용 중.

---

## 18. ai-webtoon_capcut

### 기능 개요
`ai-webtoon`이 생성한 웹툰 패널 이미지·음악·LRC/SRT를 입력받아 곡 길이에 맞는 편집 타임라인(JSON/CSV)을 자동 생성하는 Python CLI. 패널 수·음악 길이·자막 유무가 곡마다 달라도 동일 명령으로 처리.

### 주요 기능
- **214곡 탐색**: `ai-webtoon/output` 전체 스캔, 곡별 준비 상태(PROMPTS_ONLY → BUILD_READY) 자동 판정
- **LRC/SRT 정규화**: Suno 메타데이터 분리, 긴 cue 탐지, 신뢰도 점수 비교 후 최적 자막 선택
- **섹션 경계 추론**: trusted section cue → storyboard weight → 균등 폴백 3단계 전략, 신뢰도 기록
- **타임라인 생성**: 섹션별 이미지 배분, 자동 반복·모션 프리셋 할당, 프레임 경계 정렬, timeline.json/CSV 출력
- **배치 처리**: `build-all` 명령으로 준비된 곡 전체 처리, 곡별 예외 격리
- **14개 단위 테스트 통과**

### 입력 구조
```
ai-webtoon/output/{곡명}/
├─ 01_storyboard.md
├─ {곡명}.wav / .mp3
├─ lyrics.lrc / lyrics.srt
└─ panels/  (또는 img/)
   └─ panel_001_*.png  ...
```

### 폴더 구조
```
ai-webtoon_capcut/
├── src/webtoon_capcut/   # Python CLI (domain/adapters/discovery/subtitles/sections/timeline/application)
├── remotion/             # Remotion 렌더러 (Node.js) — 미구현
├── config/default.json   # 클립 길이·캔버스·자막 정책
├── schemas/              # JSON Schema (manifest/timeline/subtitles)
├── scripts/              # webtoon-capcut.ps1, test.ps1, validate-project.ps1
├── tests/unit/           # 14개 단위 테스트
└── docs/                 # 설계 문서 15개
```

### 사용 방법
```powershell
# 설치 (Python 3.12 필요)
py -3.12 -m pip install -e .

# 곡 목록 탐색
.\scripts\webtoon-capcut.ps1 discover --output-root "..\ai-webtoon\output"

# 단일 곡 타임라인 생성
.\scripts\webtoon-capcut.ps1 build --song-dir "..\ai-webtoon\output\곡명"

# 준비된 곡 전체 배치 처리
.\scripts\webtoon-capcut.ps1 build-all --output-root "..\ai-webtoon\output" --ready-only

# 테스트
.\scripts\test.ps1
```

### 기술 스택
- Python 3.12 / stdlib만 사용 (외부 의존성 없음)
- ffprobe (오디오·이미지 프로브, 선택)

### 개발 완성도: ★★★★☆
Python CLI 전 계층 구현 완료 (43개 모듈, 14 tests passed). 타임라인 생성·자막 정규화·섹션 추론·배치 처리 동작. 현재 `ai-webtoon/output`에 실제 이미지·오디오 파일 생성 후 end-to-end 검증 필요. Remotion 렌더러·CapCut 패키징은 미구현(HOLD).

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
