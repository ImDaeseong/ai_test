# ai_test 프로젝트 설계문서 인덱스

> 작성일: 2026-06-08 | 최종 갱신: 2026-10-09 | 총 18개 프로젝트 설계 기록

이 문서들은 `e:\ai_test` 폴더에서 진행한 모든 프로젝트의 최종 설계를 기록합니다.
새 프로젝트 설계 시 참조용으로 활용하세요.

---

## 문서 목록

| 문서 | 대상 프로젝트 | 핵심 기술 |
|------|-------------|---------|
| [01_video_pipeline.md](designs/01_video_pipeline.md) | lyricvideo, imagevideo, ai_anime_production, Pexels, ai-webtoon, ai-webtoon_capcut | Remotion, FFmpeg, Motion Canvas, 품질·권리 해시 게이트 |
| [02_music_tools.md](designs/02_music_tools.md) | Analysis_music, mp3_daw, master_tag, lyrics_tag | librosa, pedalboard, Flask |
| [03_media_downloader.md](designs/03_media_downloader.md) | mp4_tag | yt-dlp, Playwright, Streamlit |
| [04_system_tools.md](designs/04_system_tools.md) | windows-port-monitor, run_game, security_scanning, check_FileEncoding, findstring_foldfiles | Python, Go, C++/MFC |
| [05_bot_notification.md](designs/05_bot_notification.md) | weather_alarm | Discord.py, python-telegram-bot, aiohttp |

---

## 프로젝트 전체 지도

```
[음악 입력]
    ├── Analysis_music    → Suno 프롬프트 분석 → 악보/리포트/비주얼 프롬프트
    ├── mp3_daw           → 음원 마스터링 파이프라인
    ├── master_tag        → 마스터링 체인 (EQ→컴프→LUFS→리미터)
    └── lyrics_tag        → LRC/SRT 가사 타임스탬프 편집

[이미지/프롬프트 입력]
    ├── ai-webtoon        → 음악 → 웹툰 패널 프롬프트 자동 생성
    └── ai_anime_production → 이미지+프롬프트 → 애니메이션 영상 클립

[영상 생성]
    ├── lyricvideo        → LRC/SRT + 음악 → Remotion 가사 영상 (16:9, 9:16)
    ├── imagevideo        → LRC/SRT + 음악 → FFmpeg 4단계 파이프라인
    ├── Pexels            → 음악 + Gemini → Pexels 스톡영상 합성
    └── ai-webtoon_capcut → 웹툰 패널 → Remotion + CapCut 타임라인

[시스템 도구]
    ├── windows-port-monitor → TCP/UDP 포트 모니터링 (SQLite + JSONL)
    ├── run_game             → Steam/Epic/Netmarble 게임 런처 (C++/MFC)
    ├── security_scanning    → OWASP 기반 웹/시스템 취약점 스캔
    ├── check_FileEncoding   → 파일 인코딩 판별 (Go 웹UI)
    └── findstring_foldfiles → 폴더 전체 문자열 검색 (Python tkinter)

[미디어 다운로드]
    └── mp4_tag → yt-dlp + Playwright 웹 미디어 다운로더

[알림/봇]
    └── weather_alarm → 기상청 API → Discord/Telegram 날씨 봇
```

---

## 공통 패턴 요약

### Windows 실행 스크립트
- 모든 프로젝트: `run.bat` 또는 `run_*.bat` 제공
- venv 자동 생성/활성화 + pip install 포함
- `.ps1` 분리 없이 `.bat` 단일 파일로 유지 (피드백 정책)

### 테스트 전략
- Python: `tests/test_core.py` + pytest
- Go: `*_test.go` + go test
- Node: 프로젝트별 `npm test` + 타입/렌더 계약 검사
- 미디어 프로젝트는 기술 검사와 창작·권리·공개 사람 승인을 분리

### 설정 관리
- 환경변수: `.env` + python-dotenv
- 설정 파일: `config.yaml` (YAML) 또는 `config.json` (JSON)
- 하드코딩 금지: 곡명, 씬 수, 경로 등은 설정 파일/프롬프트에서만 추출

### 로깅
- Python: loguru 또는 표준 logging + RotatingFileHandler
- 구조화 로그: JSON 형식 (파싱 용이)
- 파일: `logs/` 폴더, 5MB 로테이션
