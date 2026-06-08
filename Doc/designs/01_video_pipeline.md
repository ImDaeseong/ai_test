# 설계문서 01 — 영상 생성 파이프라인

> 프로젝트: lyricvideo, imagevideo, ai_anime_production, Pexels, ai-webtoon, ai-webtoon_capcut

---

## 1. 프로젝트별 한줄 정의

| 프로젝트 | 정의 |
|---------|------|
| **lyricvideo** | LRC/SRT + 음악 → Remotion 가사 영상 (16:9 + 9:16 동시 출력) |
| **imagevideo** | LRC/SRT + 음악 + 배경 → FFmpeg 4단계 파이프라인 가사 영상 |
| **ai_anime_production** | 이미지 + 텍스트 프롬프트 → Remotion 애니메이션 클립 |
| **Pexels** | 음악 + Gemini 장면분석 → Pexels 스톡영상 합성 MP4 |
| **ai-webtoon** | 음악 메타데이터 → 스켈레톤 밴드 웹툰 패널 프롬프트 생성 |
| **ai-webtoon_capcut** | 웹툰 패널 + 음악 → Remotion 초벌 영상 + CapCut 타임라인 |

---

## 2. 공통 아키텍처 패턴

### 입력 → 파이프라인 → 출력 구조
모든 프로젝트가 동일한 패턴을 따릅니다:
```
input/ (사용자 자산 배치)
  ↓
자동 감지 스크립트 (파일 스캔 + 유효성 검사)
  ↓
중간 명세서 생성 (manifest.json / production_plan.json)
  ↓
렌더 엔진 (Remotion / FFmpeg)
  ↓
output/ (최종 MP4)
```

### 핵심 원칙
1. **input/output 읽기 전용 분리** — input은 수정 안 함, output은 자동 생성
2. **명세서(manifest) 중간 계층** — 파싱 결과를 JSON으로 분리 → 재실행 가능
3. **하드코딩 금지** — 곡명/씬 수/BPM/길이는 파일에서 추출, 코드에 없음
4. **배치 스크립트(.bat)** — Windows에서 npm install → 실행 자동화
5. **단계별 독립 실행** — `--skip-plan`, `--skip-subtitles` 등 각 단계 건너뛰기 지원

---

## 3. lyricvideo

### 기술 스택
- **Remotion** 4.0.458 + **React** 19 + **TypeScript** 5
- `@remotion/media-utils` (오디오 파형 분석)
- `@remotion/captions` (자막)
- Vite (빌드)

### 파일 구조
```
src/
├── index.ts          # registerRoot() 진입점
├── Root.tsx          # Composition 등록 (delayRender로 미디어 로드 대기)
├── LyricVideo.tsx    # 메인 렌더 컴포넌트 (526줄)
├── config.ts         # 모든 상수 중앙화
└── parsers.ts        # LRC/SRT 파싱
public/media/         # 입력 자산 (음악, 가사, 배경)
scripts/
└── write-media-manifest.mjs  # public/media/ 스캔 → 자동 감지
```

### 핵심 설계
```
Root.tsx
├── delayRender() → 미디어 파일 비동기 로드 대기
├── useAudioData() → 파형 분석 데이터
└── Composition (16:9) + Composition (9:16) 동시 등록

LyricVideo.tsx
├── 배경: Img / Video / 단색
├── Html5Audio (음악 재생)
├── 파형 시각화 (스파이크 + 파티클, useAudioData 기반)
├── 가사 3줄 표시 (이전 36% / 현재 100% / 다음 28% 불투명도)
└── 인트로(3.2초) + 아웃트로(2.5초) 애니메이션
```

### 설정 파일 (config.ts)
```typescript
TIMING_CONFIG = { introSeconds: 3.2, outroSeconds: 2.5, outroBufferSeconds: 1.5 }
LYRIC_STYLE = { currentFontSize: 'clamp(24px, 2.8vw, 44px)', containerTopPercent: 64 }
WAVEFORM_STYLE = { numSpikes: 56, numParticles: 10, topPercent: 82.7 }
```

### npm 스크립트
```json
"predev": "node scripts/write-media-manifest.mjs",
"dev": "remotion studio src/index.ts",
"build": "remotion render ... lyric-video out/lyric-video.mp4 --codec h264 --crf 18"
```

### 주의사항
- `OffthreadVideo`는 `loop` 미지원 → `Video` (HTML5)로 사용
- `delayRender()`를 쓸 때 `continueRender()` 반드시 finally 블록에서 호출

---

## 4. imagevideo

### 기술 스택
- **Node.js** 20+ (JavaScript ESM)
- **FFmpeg** CLI (필수 외부 의존성)
- **Motion Canvas** 3.17.2 + TypeScript (선택, 고급 애니메이션)
- **ASS** 자막 형식 (Karaoke 하이라이트)

### 4단계 파이프라인
```
Phase 1: generateProductionPlan.js
  → input/ 가사 파싱 + 씬 타이밍 + 감정 분석
  → output/production_plan.json

Phase 2: generateAssSubtitles.js
  → production_plan.json → ASS 자막 (Chorus 스타일 구분)
  → output/subtitles.ass

Phase 3: renderTypographyVideo.js
  → FFmpeg 필터 체인 (scale + subtitles + 모션)
  → output/rendered_typography_video.mp4

Phase 4: composeFinalVideo.js
  → 배경 + 음악 + 자막 FFmpeg 최종 합성
  → output/lyric_video.mp4
```

### CLI 옵션
```bash
npm run lyric-video -- \
  --title "곡 제목" --artist "아티스트" \
  --motion-strength low|medium|high \
  --clean            # 이전 output 삭제
  --skip-plan        # Phase 1 건너뜀
  --skip-subtitles   # Phase 2 건너뜀
  --skip-motion      # Phase 3 건너뜀
  --skip-compose     # Phase 4 건너뜀
```

### 해상도 지원
```javascript
RESOLUTION_BY_ASPECT_RATIO = {
  '16:9': '1920x1080',
  '9:16': '1080x1920',
  '1:1': '1080x1080'    // lyricvideo에 없는 추가 해상도
}
```

### ASS 자막 설계
- Chorus 구간: 폰트 76px, marginV 125 (일반 68px, 100)
- Karaoke 하이라이트: `\k` 태그 지원
- `CHORUS_TONES`: ['uplifting', 'energetic', 'epic', 'triumphant', 'joyful', 'powerful']

### lyricvideo vs imagevideo 비교
| 항목 | lyricvideo | imagevideo |
|------|-----------|-----------|
| 렌더러 | Remotion (통합) | FFmpeg CLI |
| 구조 | 단순 (5파일) | 복잡 (4단계 모듈) |
| 해상도 | 16:9, 9:16 | 16:9, 9:16, 1:1 |
| 자막 | 없음 | ASS 번인 |
| 파형 | 실시간 useAudioData | 없음 |
| 유연성 | Remotion 제약 | FFmpeg 무제한 |

---

## 5. ai_anime_production

### 기술 스택
- **Remotion** 4.0.461 + **React** 19 + **TypeScript** 5.8
- `@remotion/captions` (SRT 자막)
- `@remotion/media-utils` (오디오 분석)
- Node.js 스크립트 (ESM)

### 핵심 파이프라인
```
input/
  ├── scene_NN_name.png   (씬 이미지)
  └── scene_NN_name.md    (씬 프롬프트)
  ↓
scripts/import_input.mjs  (자산 복사 + manifest 생성)
  ↓
manifests/render_manifest.json  (RenderManifest 타입)
  ↓
scripts/render_scenes.mjs → Remotion SceneOnly → output/clips/
```

### 프롬프트 자동 추출 항목
```
# 제목                    → title
174 BPM                   → bpm
duration_seconds: 30      → scene duration
Camera motion: push-in    → camera direction
intensity: low            → animation intensity
## Runway / ## Kling      → 플랫폼별 프롬프트 선택
```

### SceneClip 렌더링 결정 트리
```
video_exists=true → Html5Video (루프) + LookOverlay
image_exists=true → 3층 Img (배경+메인+클로즈) + Ken Burns + LookOverlay
둘 다 없음        → 다크 배경 플레이스홀더
```

### Ken Burns 3층 구조
```
Layer 1: 배경 (블러, 전체 채움)
Layer 2: 메인 이미지 (줌/팬 애니메이션)
Layer 3: 클로즈업 (세부 강조)
```

### promptMotion.ts 카메라 매핑
```typescript
'push-in'  → zoomRange: [1.0, 1.18]  (가까워짐)
'pullback' → zoomRange: [1.18, 1.0]  (멀어짐)
'lateral'  → x 오프셋 좌→우
'tilt'     → y 오프셋 상→하
'handheld' → jitter + rotation (흔들림)
'beat'     → BPM 동기 펄스
```

### 중요 원칙 (CLAUDE.md)
- 음악·씬 값 하드코딩 절대 금지
- `const bpm = manifest.bpm ?? 120` (동적 + 안전 기본값)
- 시각 디자인 상수만 코드에 고정 가능

### remotion.config.ts
```typescript
Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setConcurrency(4);
```

---

## 6. Pexels

### 기술 스택
- **Python** 3.8+, **Flask**, **Pydantic**
- **Gemini API** (텍스트 → 장면 JSON)
- **Pexels API** (스톡 영상 검색)
- **FFmpeg** (트림·스케일·인코딩)

### 파이프라인
```
GenerateVideoRequest (음악 + 가사)
  ↓ Gemini API
list[Scene] (Pydantic 스키마)
  ↓ Pexels API
list[SceneWithVideo] (영상 URL)
  ↓ download_service
raw clips
  ↓ ffmpeg_service (트림 + 스케일)
processed clips
  ↓ composeFinalVideo
final_landscape.mp4 (1920×1080)
final_shorts.mp4 (1080×1920)
index.html (리포트)
```

### 서비스 모듈 구조
```
services/
├── gemini_service.py    → 텍스트 분석 → Scene JSON
├── pexels_service.py    → 영상 검색 + 캐시
├── download_service.py  → MP4 다운로드
├── ffmpeg_service.py    → 트림·스케일·인코딩
├── html_report_service.py → 정적 HTML 리포트
└── pipeline_service.py  → 전체 오케스트레이션
```

### FFmpeg 핵심 플래그 (버그 수정 반영)
```python
'-c:v', 'libx264',
'-g', '60',          # GOP: 2초 키프레임 (YouTube 권장)
'-crf', '23',
'-vn',               # MP3 앨범아트 비디오 스트림 제거
```

### 환경변수
```
GEMINI_API_KEY=...
PEXELS_API_KEY=...
```

### 주요 버그 수정 기록
- Pexels API URL `/v1/` 경로 누락
- 이미 인코딩된 영상 재인코딩 → `-c:v copy`
- GOP `-g 15` → `-g 60` (YouTube 최적화)
- 빈 검색결과 캐시 저장 방지
- MP3 앨범아트 처리 → `-vn`

---

## 7. ai-webtoon

### 기술 스택
- **Python** 3.9+, **Flask** (웹 뷰어)
- **JSON 설정 기반** (7개 configs/*.json, 코드 하드코딩 없음)

### 설정 파일 구조 (configs/)
```
character_lock.json         → 스켈레톤 밴드 캐릭터 정체성 (변경 금지)
webtoon_styles.json         → 5가지 스타일 (cute_dramatic, emotional, manhwa, pop, action)
band_performance_profiles.json → 실제 공연 기반 무대/조명/카메라
panel_types.json            → 8가지 패널 타입
cut_timing.json             → BPM 4구간 × 7섹션 타이밍
panel_sequences.json        → 섹션별 패널 순서
platforms.json              → GPT/Niji/FLUX.1/Gemini 프롬프트 형식
lyric_visual_map.json       → 가사 키워드 → 시각 장면 매핑
```

### 스타일 선택 로직
```python
# 감정 우선 → BPM 보조
감정(슬픔/발라드) → cute_emotional
감정(에너지/신남) → cute_dramatic 또는 cute_action
감정(팝/밝음)     → cute_pop
기본              → cute_manhwa
```

### 패널 수 계산 (BPM 기반)
```
0-89 BPM:  2-5 패널 (Slow)
90-119:    2-6 패널 (Medium)
120-149:   3-8 패널 (Fast)
150+ BPM:  3-8 패널 (Very Fast)
```

### 출력 구조 (output/{곡명}/)
```
00_style_reference.md   → 스타일 + 캐릭터 고정
00_prompt_overview.md   → 한글 요약
01_storyboard.md        → 전체 패널 계획표
panels/
  panel_001_intro_wide.md
  panel_NNN_[섹션]_[타입].md
```

### CLI 명령
```bash
python main.py create --song "UPGRADE"
python main.py create-all
python main.py validate --song "UPGRADE"
python main.py summarize-all
```

---

## 8. ai-webtoon_capcut

### 기술 스택
- **Python** 3.11+ (파이프라인)
- **Remotion** 4.0 + React 19 (렌더)
- **WhisperX** (자막 정렬, 선택)
- **Demucs** (Stem 분리, 선택)

### 10대 설계 원칙
1. input/output 읽기 전용
2. 음악 길이 = 절대 타임라인 종료
3. 곡명·패널 수·씬 하드코딩 금지
4. 추론값에 source·confidence·evidence 기록
5. 파일명은 힌트, 최종 출처 아님
6. 자막 정렬은 품질점수 기반 선택
7. 낮은 신뢰도는 자동 승인 거부
8. Remotion=합성엔진, CapCut=최종 검수
9. CapCut 비공개 포맷 필수 의존성 아님
10. 동일 입력 해시 = 동일 출력 (결정론적)

### 모듈 구조 (Python 패키지)
```
src/webtoon_capcut/
├── domain/         → 모델, 에러, 정책
├── infrastructure/ → 설정, 로깅, 해싱, 경로
├── adapters/       → 오디오/이미지/자막/곡소스 파싱
├── discovery/      → 곡 탐색
├── sections/       → 섹션 추론
├── subtitles/      → 자막 정렬
├── timeline/       → 타임라인 생성
└── application/    → CLI/오케스트레이션
```

### 출력 구조 (output/{곡명}/{run_id}/)
```
manifest.json           → 곡 메타 + 자산 해시
inventory.json          → 자산 목록
timeline/               → 타임라인 데이터
subtitles/              → 정렬된 자막
reports/                → QA 보고서
render/preview.mp4      → Remotion 초벌
handoff/
  subtitles-original.srt
  subtitles-aligned.srt
  timeline.json         → CapCut용
```

### 검증된 테스트 픽스처 (3곡)
- `fixture_upgrade`: 긴 연주, 프롬프트 블록
- `fixture_dessert`: 45장, 섹션 충돌, 혼합 해상도
- `fixture_leave`: 30장, 긴 전주·후주, 누락 Outro

---

## 9. 공통 렌더링 패턴 비교

### Remotion 사용 시
```typescript
// 미디어 로드 대기 패턴
const handle = delayRender('Loading media');
useEffect(() => {
  loadData().then(() => continueRender(handle));
}, []);

// 프레임 기반 애니메이션
const frame = useCurrentFrame();
const { fps } = useVideoConfig();
const progress = frame / fps;  // 초 단위
```

### FFmpeg 사용 시
```python
# 필수 플래그 패턴
cmd = [
    'ffmpeg', '-y',
    '-i', input_video,
    '-c:v', 'libx264',
    '-g', '60',           # 2초 GOP (YouTube)
    '-crf', '23',
    '-preset', 'medium',
    '-c:a', 'aac',
    '-b:a', '192k',
    '-vn',                # MP3 앨범아트 제거 시
    output_path
]
```

### 해상도별 표준
| 용도 | 해상도 | 비율 |
|------|-------|------|
| YouTube 기본 | 1920×1080 | 16:9 |
| Shorts/Reels | 1080×1920 | 9:16 |
| Instagram 피드 | 1080×1080 | 1:1 |
| FPS | 30 | — |
| 코덱 | H.264 | — |
| CRF | 18-23 | — |
