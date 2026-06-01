# AI Anime Production — 영상 제작 파이프라인 상세 문서

> 수정 및 개선 시 이 문서를 기준으로 참조한다.  
> 최종 업데이트: 2026-05-18

---

## 0. 핵심 설계 원칙 — 코드 수정 전 반드시 확인

### 음악·씬 값은 절대 하드코딩 금지

> **음악은 곡마다 BPM, 길이, 분위기, 카메라 연출이 모두 다르다.**  
> 코드 어디에도 특정 곡에 종속된 값(BPM 숫자, 초, intensity 문자열 등)을 직접 넣어서는 안 된다.

```
❌ 금지 (음악 파생 값 하드코딩): const bpm = 174;  /  duration = 30;  /  intensity = 'low'
✅ 허용 (프롬프트 추출):         const bpm = manifest.bpm ?? 120;  /  scene.duration_seconds  /  scene.intensity
✅ 허용 (시각 디자인 상수):       interpolate(progress, [0, 1], [-120, 120])  /  borderTop: '58px'
```

**금지 대상**: 음악에서 파생되는 값 — BPM, 길이(초), intensity 문자열, 곡 제목  
**허용 대상**: 시각 효과의 픽셀 범위, 불투명도, 레터박스 크기 등 디자인 고정값

모든 음악·씬 값은 반드시 프롬프트 파일에서 추출된 manifest를 통해서만 전달된다.

### 소스 수정 시 체크리스트

| 확인 항목 | 관련 위치 | 점검 내용 |
|----------|----------|---------|
| BPM 추출 | `import_input.mjs:extractBpm()` | 새 프롬프트 형식에서 BPM이 올바르게 추출되는가 |
| 길이 추출 | `import_input.mjs:extractDuration()` | duration 패턴이 프롬프트와 일치하는가 |
| intensity 추출 | `import_input.mjs:extractIntensity()` | 키워드가 프롬프트 표현과 일치하는가 |
| camera 추출 | `import_input.mjs:extractCameraDirection()` | "Camera motion:" 패턴이 유지되는가 |
| 키워드 매핑 | `promptMotion.ts` | push-in/pullback/beat 등 키워드가 프롬프트 텍스트와 일치하는가 |
| 하드코딩 여부 | 모든 파일 | 특정 BPM·초·강도 숫자가 코드에 직접 박혀 있지 않은가 |
| 기본값 타당성 | `render_scenes.mjs`, `promptMotion.ts` | fallback 값이 곡에 관계없이 안전한가 |

### 프롬프트 → 코드 추출 체인

```
input/scene_NN_name.md
  ├─ extractTitle()          → song_master.title
  ├─ extractBpm()            → manifest.bpm          → getPromptMotion(bpm)
  ├─ extractDuration()       → scene.duration_seconds → scene.duration_frames
  ├─ extractIntensity()      → scene.intensity        → intensityAmount() → amount
  ├─ extractCameraDirection()→ scene.camera_direction → pushIn/pullback/lateral
  └─ selected_video_prompt   → beat/neon/dark 등 분위기 키워드
```

이 흐름 외의 경로로 값이 전달되면 안 된다.

---

## 1. 전체 흐름 한눈에 보기

### 현재 기본 흐름 — input/ 폴더 기반

```
[input/ 폴더]
  character_reference_prompt.png  ← 캐릭터 참고 이미지 (선택, 최대 1개)
  scene_01_intro.png              ← 씬 이미지 (scene_NN_name 패턴, 1개 이상)
  scene_01_intro.md               ← 씬 프롬프트 (이미지와 동일 basename)
  scene_02_verse.png              ← 추가 씬 (선택)
  scene_02_verse.md
       │
       │  npm run import:input
       ▼
[public/assets/images/]
  character_reference.png         ← character_reference_prompt.png 복사
  scene_01_intro.png              ← 씬 이미지 복사 (슬러그명)
  scene_02_verse.png
[prompts/video_prompts/]
  scene_01_intro.md               ← 씬 프롬프트 복사
  scene_02_verse.md
[manifests/source/]
  song_master.json                ← 프롬프트에서 자동 생성 (title, bpm, duration)
  scene_list.json                 ← 씬 목록 (scene_number, section, duration_seconds)
       │
       │  (import:input 내부에서 자동 실행)
       │  node scripts/create_manifest.mjs
       ▼
[manifests/render_manifest.json]  — 렌더링 명세서
       │
       ├──── [외부 AI 영상 생성]  ← 선택사항
       │       입력: video_gen_images (character + scene)
       │       프롬프트: selected_video_prompt (플랫폼 선택)
       │       출력: public/assets/videos/scene_NN_slug.mp4
       │
       │  npm run render:scenes
       ▼
[output/clips/]
  scene_01_intro.mp4              ← 씬별 개별 클립 (오디오 없음, 1920×1080)
  scene_02_verse.mp4
       │
       │  외부 편집 소프트웨어(CapCut 등)에서
       │  클립 합치기 + 자막 + 음악 추가
       ▼
최종 영상
```

### 보조 흐름 — ai_anime 프로젝트 연동

```
[ai_anime 프로젝트]
  song_master.json / scene_list.json / prompts/
       │
       │  npm run import -- --from ../ai_anime
       ▼
[manifests/source/] + [prompts/] + [public/assets/audio/, subtitles/]
       │
       │  npm run manifest
       ▼
[manifests/render_manifest.json]
       │
       │  npm run render   (전체 합본, 오디오 포함)
       │  npm run postprocess
       ▼
output/final/final_mv.mp4 → final_mv_web.mp4
```

---

## 2. 단계별 상세 설명

### Step 0 — input/ 폴더 파일 규칙

`input/` 폴더에 아래 규칙으로 파일을 배치한다.

| 파일 패턴 | 역할 | 필수 |
|----------|------|------|
| `character_reference_prompt.{png,jpg,jpeg,webp}` | 캐릭터 참고 이미지 | 선택 (최대 1개) |
| `scene_NN_name.{png,jpg,jpeg,webp}` | 씬 이미지 | 필수 (1개 이상) |
| `scene_NN_name.md` | 씬별 영상 생성 프롬프트 | 필수 (씬당 1개) |

**규칙:**
- 씬 이미지와 프롬프트는 반드시 동일한 basename을 가져야 한다 (`scene_01_intro.png` ↔ `scene_01_intro.md`)
- 이미지에 매칭 프롬프트가 없거나 그 반대이면 import가 즉시 중단된다
- 위 세 종류 외 파일(오디오, SRT, LRC 등)이 있으면 import가 중단된다
- 씬 번호 `NN` 순서대로 정렬하여 처리한다

---

### Step 1 — import:input (`scripts/import_input.mjs`)

```powershell
npm run import:input
```

**동작 순서:**

1. `input/` 폴더 스캔 → 파일 유형별 분류 (`character_reference_prompt.*`, `scene_NN_name.*`)
2. 예상치 못한 파일(오디오·SRT·LRC 등)이 있으면 즉시 오류 종료
3. 씬 이미지와 프롬프트를 basename으로 1:1 매칭
4. 매칭 실패 시 즉시 오류 종료
5. 씬 번호(NN) 순으로 정렬
6. 캐릭터 이미지 → `public/assets/images/character_reference.png`로 복사 (없으면 기존 파일 삭제)
7. 씬마다:
   - 씬 이미지 → `public/assets/images/{slug}.png`로 복사
   - 씬 프롬프트 → `prompts/video_prompts/{slug}.md`로 복사
   - 프롬프트에서 title·BPM·duration·intensity·camera_direction 자동 추출
8. `manifests/source/song_master.json`, `scene_list.json` 생성
9. `scripts/create_manifest.mjs` 자동 실행 → `render_manifest.json` 생성

**자동 추출 항목 (scene_NN_name.md에서):**

| 항목 | 추출 패턴 | 기본값 |
|------|---------|--------|
| 프로젝트 제목 | `^# 제목` (H1 헤딩) | `AI Anime Scene` |
| BPM | `\b(\d+)\s*BPM\b` | `null` |
| 씬 길이 | `duration_seconds: N`, `duration: Ns`, `Ns duration` | 30초 |
| intensity | `intensity (low\|medium\|high\|emotional peak\|...)` | 빈 문자열 |
| camera_direction | `Camera motion: ...` (첫 번째 구절) | 빈 문자열 |

**생성 파일 예시 (단일 씬):**

`manifests/source/song_master.json`
```json
{
  "title": "Scene 01 - Intro",
  "duration_seconds": 30,
  "bpm": 174,
  "audio_files": [],
  "timed_lyrics": [],
  "character_reference_enabled": true,
  "subtitle_enabled": false
}
```

`manifests/source/scene_list.json`
```json
{
  "song_title": "Scene 01 - Intro",
  "scenes": [
    {
      "scene_number": 1,
      "music_section": "intro",
      "duration_seconds": 30,
      "camera_direction": "slow push-in that reveals the song-specific prop",
      "movement": "",
      "intensity": "low",
      "emotion": ""
    }
  ]
}
```

---

### Step 2 — manifest 생성 (`scripts/create_manifest.mjs`)

```powershell
npm run manifest
# 또는 플랫폼 지정 시
$env:VIDEO_PROMPT_PLATFORM="Kling"
npm run manifest
```

`import:input` 실행 시 자동으로 호출되므로 별도 실행은 플랫폼 변경 시에만 필요하다.

#### 2-1. 씬 시작 시간 결정 (`findSceneStarts`)

**우선순위:**

1. `scene_list.json` 각 씬에 `duration_seconds`가 모두 있으면 → 씬별 duration으로 정확한 시작 시간 계산
   ```
   scene 1: duration=30s → start=0s
   scene 2: duration=20s → start=30s
   scene 3: duration=25s → start=50s
   ```
2. `song_master.timed_lyrics` 배열에서 `[SectionName]` 마커 탐색 (ai_anime 연동 방식)
3. 둘 다 없으면: `(총길이 / 씬수) × 인덱스`로 균등 분할

첫 씬 시작이 1초 이후면 강제로 0으로 보정.

#### 2-2. 플랫폼별 프롬프트 선택 (`parseSelectedPrompt`)

`prompts/video_prompts/scene_NN_*.md` 파일을 읽어 `## Platform` 헤딩으로 분리한다.

**우선순위 (높음 → 낮음):**
```
1. VIDEO_PROMPT_PLATFORM 환경변수와 일치하는 ## Platform
2. ## Runway  (fallback)
3. 첫 번째 ## 섹션  (최후 fallback)
```

| 환경변수 | 결과 | manifest 레이블 |
|---------|------|----------------|
| `Remotion` (기본) | Runway 텍스트 사용 | `Remotion (from Runway)` |
| `Kling` | Kling 텍스트 사용 | `Kling` |
| `Runway` | Runway 텍스트 사용 | `Runway` |

**지원 플랫폼:** Runway, Kling, Pika, Luma, Veo, Flow, Sora, Hailuo, PixVerse

#### 2-3. 캐릭터 이미지 탐지 (`resolveCharacterImage`)

아래 순서로 `public/assets/images/`를 확인한다:
1. `character_reference.png` (표준명 — `import:input`이 자동으로 여기에 복사)
2. `00_character_turnaround_model_sheet.png` (ai_anime 연동 방식 대체명)

#### 2-4. 자막 파일 결정 (`subtitlePath`)

`public/assets/subtitles/` 폴더를 아래 우선순위로 탐색한다:

1. `lyrics_clean.srt` — 정제된 자막 (최우선)
2. `lyrics_original.srt` — 원본 자막 (fallback)
3. 없으면 `null` (자막 비활성화)

`lyrics_original.srt` 가 선택되면 manifest에 경고 필드가 추가된다:

```json
"subtitle_note": "Original subtitle file may need encoding cleanup."
```

`song_master.json`에 `subtitle_enabled: false`가 있으면 이 단계를 건너뛰고 자막을 항상 `null`로 처리한다.

---

#### 2-5. render_manifest.json 생성

```jsonc
{
  "title": "Scene 01 - Intro",
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "duration_seconds": 30,
  "duration_frames": 900,
  "bpm": 90,
  "audio": null,
  "subtitles": null,
  "subtitle_note": "",
  "character_image": "assets/images/character_reference.png",
  "character_image_exists": true,
  "scenes": [
    {
      "scene_number": 1,
      "section": "intro",
      "slug": "scene_01_intro",
      "start": 0,
      "end": 30,
      "duration": 30,
      "start_frame": 0,
      "duration_frames": 900,
      "image": "assets/images/scene_01_intro.png",
      "image_exists": true,
      "video": "assets/videos/scene_01_intro.mp4",
      "video_exists": false,
      "video_prompt": "prompts/video_prompts/scene_01_intro.md",
      "selected_video_prompt_platform": "Remotion (from Runway)",
      "selected_video_prompt": "...(Runway 섹션 텍스트)...",
      "video_gen_images": [
        {"path": "assets/images/character_reference.png", "exists": true,  "role": "character"},
        {"path": "assets/images/scene_01_intro.png",      "exists": true,  "role": "scene"}
      ],
      "camera_direction": "slow push-in that reveals the song-specific prop",
      "intensity": "low"
    }
  ]
}
```

---

### Step 3 — 자산 검증 (`scripts/check_assets.mjs`)

```powershell
npm run check
npm run check:placeholders   # 이미지 없이도 통과
```

**출력 예시:**
```
Title: Scene 01 - Intro
Scenes: 1
Audio: not used
Subtitles: not used
Character image: assets/images/character_reference.png [ready]

Video prompt platform: Remotion (from Runway)
  Note: set VIDEO_PROMPT_PLATFORM=<tool> and re-run npm run manifest

Video generation inputs:
  scene_01_intro: 2/2 images ready [character:ready scene:ready]

OK: render can run from images and selected video prompts.
```

**종료 코드:** `0` = 렌더 진행 가능, `1` = 필수 자산 누락

---

### Step 4 — 영상 생성 (외부 AI 도구, 선택사항)

이 단계는 선택사항이다. 영상이 없으면 Remotion이 이미지를 Ken Burns 애니메이션으로 대체한다.

`render_manifest.json`의 각 씬에서 `video_gen_images`와 `selected_video_prompt`를 읽어 사용한다.

| 준비된 이미지 | 입력 방법 |
|-------------|----------|
| character + scene (2장) | character를 스타일 레퍼런스로, scene을 기반 프레임으로 첨부 |
| scene만 (1장) | scene을 기반 프레임으로 첨부 |

- `exists: false` 항목은 제외
- 생성된 영상 배치 위치: `public/assets/videos/scene_NN_slug.mp4`
- 배치 후 `npm run manifest` 재실행 시 `video_exists: true`로 갱신

#### 플랫폼별 프롬프트 교체

```powershell
$env:VIDEO_PROMPT_PLATFORM="Kling"
npm run manifest
```

---

### Step 5 — 씬 클립 렌더링 (`scripts/render_scenes.mjs`)

```powershell
npm run render:scenes
```

#### 동작 순서

1. `manifests/render_manifest.json` 읽기
2. `image_exists: true` 또는 `video_exists: true` 인 씬만 대상 선정
3. 씬별 props JSON을 `manifests/scene_props/{slug}.json`에 저장
4. 씬마다 Remotion `SceneOnly` 컴포지션으로 개별 렌더 실행
   - Windows: `node_modules/.bin/remotion.cmd` 자동 감지
5. `output/clips/{slug}.mp4` 생성 (오디오 없음, 1920×1080)

#### 출력

```
output/clips/
  scene_01_intro.mp4   ← 씬 1 클립 (1920×1080, 오디오 없음)
  scene_02_verse.mp4   ← 씬 2 클립
  ...
```

#### 컴포넌트 트리

```
Root.tsx
├── Composition(id="MusicVideo", calculateMetadata)   ← 전체 합본용
│   └── MusicVideo.tsx(manifest)
│       ├── Html5Audio(src=manifest.audio)
│       ├── Sequence × 씬수
│       │   └── SceneClip(scene, fps, bpm)
│       └── CaptionLayer(src=subtitles, fps)
│
└── Composition(id="SceneOnly", calculateMetadata)    ← 씬별 개별 클립용
    └── SceneOnly.tsx(scene, fps, bpm)
        └── SceneClip(scene, fps, bpm)
            ├── [video_exists] Html5Video(loop, muted) + LookOverlay
            ├── [image_exists] Img(Ken Burns 애니메이션) + LookOverlay
            └── [없음]         Placeholder 텍스트
```

#### SceneOnly 컴포지션 특징

- `durationInFrames`: `scene.duration_frames`으로 동적 결정 (`calculateMetadata`)
- 해상도: 고정 1920×1080 (YouTube HD 16:9)
- 오디오 없음 — 나중에 외부에서 합산
- 자막 없음 — 씬 클립 단위에는 불필요

#### SceneClip 렌더 우선순위

```
1. scene.video_exists == true  → Html5Video (루프 재생, LookOverlay 오버레이)
2. scene.image_exists == true  → Img + Ken Burns 애니메이션 + LookOverlay
3. 둘 다 없음                  → 다크 배경 플레이스홀더 텍스트
```

#### getVirtualShot — Ken Burns 3단계 애니메이션 키워드 (`SceneClip.tsx`)

이미지 렌더 경로에서 `selected_video_prompt` 텍스트를 파싱해 Ken Burns 파라미터를 조정한다.

| 키워드 | 효과 |
|--------|------|
| `push-in`, `push in`, `push/pull`, `camera push` | 줌 범위 확대 (0.18) |
| `wide establishing`, `establishing` | 베이스 줌 축소 (1.02) — 넓은 구도 |
| `close-up`, `close up`, `medium shot`, `medium close` | 클로즈 레이어 불투명도 증가 (0.62) |

#### LookOverlay 시각 효과 트리거 키워드 (`SceneClip.tsx`)

`selected_video_prompt` 텍스트에서 아래 키워드가 감지되면 해당 레이어가 활성화된다.

| 키워드 | 효과 |
|--------|------|
| `reflection`, `wet`, `bass pulses` | 반사 스트릭 오버레이 (하단 42% 영역, 애니메이션) |
| `motif`, `particle`, `memory`, `lyric note`, `waveform` | 파티클 모티프 레이어 (18개 수직 상승) |
| `fracture`, `crimson`, `sharp` | 파편 그라디언트 오버레이 (screen 블렌드) |
| `layer plan`, `animation plan` | 동적 방사형 그라디언트 풀 활성화 (overlay 블렌드) |

**컬러 팔레트 선택** (`colorFromPrompt`):

| 키워드 | 메인 컬러 | 보조 컬러 |
|--------|----------|----------|
| `coral`, `orange`, `rose-gold` | 코랄 (255,118,64) | (255,210,168) |
| `amber`, `gold` | 앰버 (255,188,64) | 시안 (94,210,255) |
| `crimson`, `red` | 크림슨 (255,38,82) | 시안 (88,210,255) |
| `cyan`, `blue` | 시안 (88,210,255) | 흰색 |
| 없음 (기본값) | 마젠타 (255,0,96) | 시안 (0,200,255) |

---

### Step 6 — PromptMotion 엔진 (`src/lib/promptMotion.ts`)

씬의 텍스트 프롬프트와 메타데이터를 파싱하여 프레임별 애니메이션 파라미터를 계산한다.

#### 강도 계수 (`intensityAmount`)

| intensity 값 | 계수 `amount` |
|-------------|--------------|
| `emotional peak`, `peak` | 1.35 |
| `medium-high`, `high` | 1.15 |
| `medium` | 1.0 |
| `falling`, `low`, `subtle` | 0.7 |
| 그 외 | 0.9 |

#### 카메라 키워드 매핑

| 키워드 | 효과 |
|--------|------|
| `push-in`, `push in`, `dolly forward`, `forward dolly`, `zoom in` | scale 증가 (push-in) |
| `pullback`, `pull back`, `pull-out`, `pull out`, `zoom out` | scale 감소 (pullback) |
| `lateral`, `tracking`, `track`, `pan` | x축 이동 |
| `tilt` | y축 이동 |
| `handheld`, `shake` | 지터 + 미세 회전 |
| `close-up`, `close up`, `intimate` | 줌 범위 +0.06 (클로즈 강조) |

#### 분위기·비주얼 키워드 매핑

| 키워드 | 효과 |
|--------|------|
| `beat`, `strobing`, `pulse`, `impact flashes`, `drum accents` | BPM 동기 박자 펄스 (`beatPulse`) |
| `neon`, `cyber`, `crimson`, `magenta`, `pink` | 그레인 오버레이 강도 증가 (`grain: 0.12`) |
| `dark`, `near-black`, `graphite`, `shadow` | 비네트 강도 증가 (`vignette: 0.82`) |

#### BPM 동기 계산

```typescript
const beatHz = bpm / 60;
const beatPulse = beat
  ? Math.max(0, Math.sin((frame / fps) * Math.PI * 2 * beatHz))
  : 0;
const fadeDuration = Math.max(6, Math.round((60 / bpm) * fps));
```

---

### Step 7 — 전체 합본 렌더링 (선택사항)

씬 클립을 외부에서 합친 후, 또는 ai_anime 연동 방식으로 전체 합본을 생성할 때 사용한다.

```powershell
npm run render        # Remotion → output/final/final_mv.mp4 (오디오 포함)
npm run postprocess   # FFmpeg → output/final/final_mv_web.mp4 (배포본)
```

**FFmpeg 후처리 옵션:**

| 옵션 | 값 | 이유 |
|------|-----|------|
| `-c:v libx264` | H.264 | 범용 호환성 |
| `-preset slow` | slow | medium 대비 10~20% 파일 감소, 화질 동일 |
| `-crf 18` | 18 | 시각적으로 무손실 수준, CRF 16 대비 30~40% 파일 감소 |
| `-profile:v high -level 4.1` | high/4.1 | 1080p@30fps 표준 레벨, 모바일·TV 호환 보장 |
| `-pix_fmt yuv420p` | yuv420p | 브라우저 호환 필수 |
| `-movflags +faststart` | — | 웹 스트리밍 최적화 |
| `-colorspace bt709` | BT.709 | HD 컬러 스페이스 표준 |
| `-color_range tv` | limited | BT.709 limited range 명시, 플레이어 색감 일관성 |
| `-c:a aac -b:a 192k` | AAC 192kbps | 고품질 오디오 |

---

## 3. 자산 경로 규칙

```
input/                                ← 작업 입력 폴더 (원본 파일)
  character_reference_prompt.png
  scene_01_intro.png
  scene_01_intro.md

public/assets/                        ← Remotion이 읽는 자산 폴더
  images/
  │ ├── character_reference.png       ← character_reference_prompt.* 복사
  │ └── scene_NN_{section}.png        ← 씬 이미지 복사 (슬러그명)
  videos/
  │ └── scene_NN_{section}.mp4        ← 외부 AI 영상 (선택)
  audio/                              ← ai_anime 연동 방식에서 사용
  └── subtitles/                      ← ai_anime 연동 방식에서 사용

manifests/
  source/
  │ ├── song_master.json              ← import:input 자동 생성
  │ └── scene_list.json               ← import:input 자동 생성
  ├── render_manifest.json            ← npm run manifest 출력
  └── scene_props/
      └── scene_01_intro.json         ← render:scenes 임시 props 파일

prompts/
  └── video_prompts/
      └── scene_NN_{section}.md       ← input/scene_NN_name.md 복사

output/
  clips/                              ← render:scenes 출력 (씬별 개별 클립)
  │ └── scene_01_intro.mp4
  └── final/                          ← 전체 합본 (선택사항)
      ├── final_mv.mp4
      └── final_mv_web.mp4
```

---

## 4. 데이터 타입 (`src/data/manifest.ts`)

```typescript
type RenderScene = {
  scene_number: number;
  section: string;
  slug: string;              // "scene_01_intro"
  start: number;             // 초
  end: number;
  duration: number;
  start_frame: number;
  duration_frames: number;
  image: string;             // "assets/images/scene_01_intro.png"
  image_exists: boolean;
  video: string;
  video_exists: boolean;
  image_prompt: string;
  video_prompt: string;
  selected_video_prompt_platform?: string;
  selected_video_prompt?: string;
  video_gen_images: {path: string; exists: boolean; role: 'character' | 'scene'}[];
  camera_direction: string;
  movement: string;
  intensity: string;
  emotion: string;
};

type RenderManifest = {
  title: string;
  fps: number;               // 항상 30
  width: number;             // 항상 1920
  height: number;            // 항상 1080
  duration_seconds: number;
  duration_frames: number;
  bpm: number | null;
  audio: string | null;
  subtitles: string | null;
  subtitle_note?: string;      // "Original subtitle file may need encoding cleanup."
  character_image: string | null;
  character_image_exists: boolean;
  scenes: RenderScene[];
};
```

---

## 5. npm scripts 전체 목록

| 명령 | 실행 내용 | 언제 사용 |
|------|----------|----------|
| `npm run import:input` | input/ 스캔 → 자산 복사 → manifest 생성 | **주 진입점**: input/ 파일 추가·변경 후 |
| `npm run render:scenes` | 씬별 개별 클립 렌더 → output/clips/ | import:input 후 |
| `npm run build` | import:input + typecheck + render:scenes | 전체 자동화 |
| `npm run validate` | manifest + typecheck + check | 렌더 전 전체 유효성 검사 한 번에 |
| `npm run manifest` | render_manifest.json 재생성 | 플랫폼 변경, 외부 영상 추가 후 |
| `npm run check` | 자산 유효성 검사 | 렌더 전 확인 |
| `npm run check:placeholders` | 이미지 없어도 통과 | 테스트 렌더 시 |
| `npm run typecheck` | TypeScript 타입 검사 | 코드 수정 후 |
| `npm run studio` | Remotion 스튜디오 (브라우저 미리보기) | 시각 확인 시 |
| `npm run import -- --from ../ai_anime` | ai_anime 프로젝트 연동 (보조) | ai_anime 업데이트 후 |
| `npm run render` | 전체 합본 렌더 (오디오 포함) → output/final/ | 합본 생성 시 |
| `npm run postprocess` | FFmpeg 웹 최적화 → final_mv_web.mp4 | 배포본 생성 시 |

---

## 6. 실행 방법 (run.bat)

프로젝트 루트의 `run.bat`을 더블클릭하여 실행한다.

```
==================================================
  AI Anime Production
==================================================

  1. Full run  (import + render, create mp4)
  2. Import    (read input files)
  3. Render    (create scene mp4)
  4. Studio    (browser preview)
  5. Check     (asset check only, no render)
  6. Exit
```

| 선택 | 내용 | 해당 npm 명령 |
|------|------|-------------|
| 1 | 전체 실행 | `import:input` → `render:scenes` |
| 2 | 임포트만 | `import:input` |
| 3 | 렌더만 | `render:scenes` |
| 4 | 미리보기 | `studio` |
| 5 | 자산 확인 | `check:placeholders` |

**주의**: `run.bat`은 CP949 인코딩으로 저장되어야 한국어 CMD에서 정상 표시된다.

---

## 7. 자주 발생하는 문제와 해결

### 문제 1: 모든 씬이 `Remotion (from Runway)`

**원인**: 프롬프트 파일에 `## Remotion` 섹션 없음 → Runway fallback 사용 중  
**해결**: 외부 AI 도구 사용 시 해당 플랫폼으로 지정

```powershell
$env:VIDEO_PROMPT_PLATFORM="Kling"
npm run manifest
```

### 문제 2: import 중 "Unexpected input file(s)" 오류

**원인**: input/ 폴더에 허용되지 않는 파일 존재 (오디오, SRT, LRC, 임시 파일 등)  
**해결**: 해당 파일을 input/ 밖으로 이동하거나 삭제

### 문제 3: "Scene image has no matching prompt" 오류

**원인**: 씬 이미지(`scene_01_intro.png`)와 프롬프트(`scene_01_intro.md`)의 basename 불일치  
**해결**: 파일명을 완전히 동일하게 맞춘다

### 문제 4: run.bat 실행 시 한글 깨짐

**원인**: 배치 파일이 UTF-8로 저장됨 (한국어 Windows CMD는 CP949 기본)  
**해결**: PowerShell로 CP949 재저장

```powershell
$txt = [System.IO.File]::ReadAllText("run.bat", [System.Text.Encoding]::GetEncoding(949))
[System.IO.File]::WriteAllText("run.bat", $txt, [System.Text.Encoding]::GetEncoding(949))
```

### 문제 5: 씬 길이가 항상 30초

**원인**: 프롬프트에 `duration_seconds`, `duration: Ns` 같은 패턴이 없어 기본값 30초 사용  
**해결**: 프롬프트 파일에 `duration_seconds: 10` 형식으로 명시하거나, 기본값 30초를 그대로 사용

### 문제 6: 긴 씬 루프로 단조로움

**원인**: 외부 AI 영상(5~10초)이 씬 길이(30초)보다 짧아 루프  
**해결**: 씬 MD 파일을 여러 개로 분할하거나, 여러 AI 클립을 생성하여 씬 수를 늘림

---

## 8. 수정 시 참조 포인트

> **원칙**: 수정 후 반드시 섹션 0의 체크리스트를 확인한다.  
> 특히 새로운 숫자(BPM·초·강도)가 코드에 직접 들어가 있지 않은지 검토한다.

### 추출 함수 — 프롬프트 형식이 바뀌면 가장 먼저 수정

| 수정 내용 | 참조 위치 |
|----------|----------|
| BPM 추출 패턴 | `scripts/import_input.mjs:extractBpm()` |
| duration 추출 패턴 | `scripts/import_input.mjs:extractDuration()` |
| intensity 추출 패턴 | `scripts/import_input.mjs:extractIntensity()` |
| camera_direction 추출 패턴 | `scripts/import_input.mjs:extractCameraDirection()` |
| 제목 추출 패턴 | `scripts/import_input.mjs:extractTitle()` |

### 키워드 매핑 — 새 프롬프트 표현에 키워드가 없으면 효과 미적용

| 수정 내용 | 참조 위치 |
|----------|----------|
| 카메라 키워드 추가 (push-in, pullback 등) | `src/lib/promptMotion.ts` `pushIn/pullback/lateral` |
| 분위기 키워드 추가 (beat, neon, dark 등) | `src/lib/promptMotion.ts` `beat/neon/dark` |
| intensity 레벨 추가 | `src/lib/promptMotion.ts:intensityAmount()` / `beatAmount()` |

### 파이프라인 구조

| 수정 내용 | 참조 위치 |
|----------|----------|
| input/ 파일 인식 규칙 | `scripts/import_input.mjs:scanInput()` |
| 씬 이미지 ↔ 프롬프트 매핑 | `scripts/import_input.mjs` basename 비교 로직 |
| 씬 시작 시간 결정 | `scripts/create_manifest.mjs:findSceneStarts()` |
| 플랫폼별 프롬프트 선택 | `scripts/create_manifest.mjs:parseSelectedPrompt()` |
| 캐릭터 이미지 표준명 | `scripts/create_manifest.mjs:CHARACTER_IMAGE_CANDIDATES` |
| Remotion CLI 실행 방식 | `scripts/render_scenes.mjs:REMOTION_CLI` (`@remotion/cli/remotion-cli.js` 직접 호출) |
| 씬 클립 출력 경로 | `scripts/render_scenes.mjs:CLIPS_DIR` |

### 렌더 파라미터

| 수정 내용 | 참조 위치 |
|----------|----------|
| fps 변경 | `scripts/create_manifest.mjs` `const fps = 30` |
| 해상도 변경 | `src/Root.tsx:calcSceneOnly` width/height |
| LookOverlay 시각 효과 | `src/components/SceneClip.tsx:LookOverlay` |
| LookOverlay 트리거 키워드 | `src/components/SceneClip.tsx` — `reflections` / `motif` / `fracture` / `remotionPlan` 변수 |
| 컬러 팔레트 | `src/components/SceneClip.tsx:colorFromPrompt()` |
| Ken Burns 키워드 | `src/components/SceneClip.tsx:getVirtualShot()` — `push`, `wide`, `close` 변수 |
| 자막 스타일 | `src/components/CaptionLayer.tsx` 인라인 스타일 |
| FFmpeg 인코딩 품질 | `scripts/postprocess.mjs` `-crf` 값 |
| 새 플랫폼 추가 | `scripts/check_assets.mjs` 가용 플랫폼 목록 |
| 자막 파일 우선순위 | `scripts/create_manifest.mjs` `subtitlePath` 결정 로직 |
| 렌더 전 전체 검사 | `npm run validate` (manifest + typecheck + check 연속 실행) |
