# imagevideo — Lyric Video Generation Pipeline

가사 파일과 음악 파일로 완성된 뮤직비디오를 자동 생성합니다.

## 요구사항

- Node.js 20+
- FFmpeg (PATH에 등록되어 있어야 함)
- `npm install`

## 빠른 시작

### 1. 입력 파일 준비

`input/` 폴더에 다음 파일들을 넣습니다:

| 파일 | 형식 | 필수 |
|------|------|------|
| 가사 | `.srt` / `.lrc` / `lyrics.json` | 필수 |
| 음악 | `.mp3` / `.wav` | 필수 |
| 배경 이미지 | `.png` / `.jpg` / `.jpeg` / `.webp` | 선택 |
| 배경 영상 | `.mp4` / `.mov` / `.webm` | 선택 |

### 2. 파이프라인 실행

```bash
npm run lyric-video -- --title "곡 제목" --artist "아티스트명"
```

완성된 영상이 `output/lyric_video.mp4`로 저장됩니다.

## 파이프라인 구조

```
input/ (가사 + 음악 + 배경)
  ↓ Phase 1: generateProductionPlan.js
output/production_plan.json  (씬별 타이밍, 감정, 스타일 자동 계획)
  ↓ Phase 2: generateAssSubtitles.js
output/subtitles.ass         (타이밍 자막, Karaoke 모드 지원)
  ↓ Phase 3: renderTypographyVideo.js (FFmpeg)
output/rendered_typography_video.mp4  (배경 + 자막 합성)
  ↓ Phase 4: composeFinalVideo.js
output/lyric_video.mp4       ← 최종 완성본
```

## CLI 옵션

```
npm run lyric-video -- [options]

--title <text>               인트로 4초 동안 표시할 곡 제목
--artist <text>              인트로 4초 동안 표시할 아티스트명
--motion-strength <level>    카메라/배경 모션 강도: low | medium | high (기본: low)
--clean                      이전 output 전체 삭제 후 시작
--debug                      각 Phase의 전체 명령어 출력
--skip-plan                  production_plan.json 재생성 건너뜀
--skip-subtitles             subtitles.ass 재생성 건너뜀
--skip-motion                typography 영상 렌더 건너뜀
--skip-compose               최종 FFmpeg 합성 건너뜀
```

### 예시

```bash
# 기본 실행
npm run lyric-video

# 타이틀 + 아티스트 오버레이 포함
npm run lyric-video -- --title "환승역" --artist "싱어" --motion-strength medium

# 처음부터 다시 실행
npm run lyric-video -- --clean

# 렌더만 다시 (Plan은 유지)
npm run lyric-video -- --skip-plan --skip-subtitles
```

## 가사 파일 형식

### SRT (권장)
```
1
00:00:01,000 --> 00:00:04,500
첫 번째 가사

2
00:00:05,000 --> 00:00:08,000
두 번째 가사
```

### LRC
```
[00:01.00]첫 번째 가사
[00:05.00]두 번째 가사
```

### lyrics.json (설정 포함)
```json
{
  "lyrics": "첫 번째 가사\n두 번째 가사",
  "aspect_ratio": "16:9",
  "mood": "reflective",
  "genre": "contemporary pop",
  "karaoke_highlight": false
}
```

`timed_segments`가 없으면 `duration_per_line`(기본 4초)으로 균등 분배합니다.

## 출력 해상도

`lyrics.json`의 `aspect_ratio` 설정으로 변경합니다:

| 값 | 해상도 | 용도 |
|----|--------|------|
| `16:9` | 1920×1080 | YouTube 기본 (기본값) |
| `9:16` | 1080×1920 | YouTube Shorts / Instagram Reels |
| `1:1` | 1080×1080 | Instagram 피드 |

## Motion Canvas (고급)

FFmpeg 렌더 대신 Motion Canvas 애니메이션을 사용하려면:

```bash
# 씬 데이터만 생성
npm run motion:generate

# Motion Canvas 개발 서버 실행 (GUI에서 렌더)
npm run motion:dev
```

→ 브라우저에서 `Video (FFmpeg)` exporter 선택 → `output/rendered_typography_video.mp4` 저장  
→ `npm run lyric-video -- --skip-plan --skip-subtitles --skip-motion` 으로 최종 합성만 실행

## 개별 Phase 실행

```bash
npm run plan          # Phase 1: production_plan.json 생성
npm run subtitles     # Phase 2: subtitles.ass 생성
npm run render:typography  # Phase 3: FFmpeg 타이포그래피 렌더
npm run compose       # Phase 4: 최종 합성
```

## 로그

```
output/logs/pipeline.log   전체 파이프라인 로그
output/logs/render.log     Phase 3 상세 로그
output/logs/ffmpeg.log     Phase 4 상세 로그
```
