# AI Pexels Video Generator

Local automation tool that turns files in `data/` into stock-footage music videos using Gemini, Pexels, and FFmpeg.

## Quick Start

Double-click:

```bat
run.bat
```

It creates both final videos and opens a browser report:

- `output/final_landscape.mp4`: regular YouTube landscape video, 1920x1080, 16:9
- `output/final_shorts.mp4`: YouTube Shorts portrait video, 1080x1920, 9:16
- `output/index.html`: preview page for both videos and scene-level clips

## Data

Put files in `data/`:

- Lyrics/script: `.lrc`, `.srt`, `.txt`
- Audio: `.wav`, `.mp3`, `.m4a`, `.aac`
- Subtitle track: `.srt`

The final video duration is matched to the music duration.

## Environment

Copy `.env.example` to `.env` and set:

```env
GEMINI_API_KEY=...
PEXELS_API_KEY=...
```

FFmpeg must be installed and available in `PATH`.

## Developer Tools

```bat
dev_tools.bat
```

Use it to run tests, validate data, generate without opening the browser, or clean generated cache files.

## Bug Fixes (2026-05-20)

| # | 파일 | 수정 내용 |
|---|------|-----------|
| 1 | `pexels_service.py` | Pexels API URL `/v1/` 경로 누락 수정 (공식 엔드포인트) |
| 2 | `ffmpeg_service.py` | `export_youtube_mp4`에서 이미 인코딩된 영상을 재인코딩하던 이중 인코딩 제거 → `-c:v copy` 적용으로 화질 손실 없이 속도 개선 |
| 3 | `ffmpeg_service.py` | GOP 크기 `-g 15` → `-g 60` 수정 (YouTube 권장 2초 키프레임 간격, 30fps 기준) |
| 4 | `pexels_service.py` | 빈 검색 결과(`videos: []`)가 캐시에 저장되어 이후 실행마다 불필요한 폴백 API 호출이 반복되던 버그 수정 |
| 5 | `pexels_service.py` | `per_page` 10 → 15 (Pexels 공식 기본값, 스코어링 후보 풀 확대) |
| 6 | `ffmpeg_service.py` | vf 필터의 `format=yuv420p`와 `-r 30` 중복 지정 제거 |
| 7 | `ffmpeg_service.py` | MP3 파일에 내장된 앨범아트(video stream)를 `.m4a` 컨테이너에 쓰려다 실패하던 버그 수정 → `trim_audio`에 `-vn` 플래그 추가 |
