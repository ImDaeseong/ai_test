# Claude Code Instructions

---

## 핵심 설계 원칙 — 반드시 준수

### 음악·씬 값은 절대 하드코딩 금지

> 음악은 곡마다 BPM, 길이, 분위기, 카메라 연출이 모두 다르다.  
> 코드 어디에도 특정 곡에 종속된 값을 넣어서는 안 된다.

**금지 — 음악에서 파생된 값을 코드에 직접 기재:**
```ts
const bpm = 174;          // ❌ 특정 곡 BPM 하드코딩
const duration = 30;      // ❌ 특정 곡 길이 하드코딩
const intensity = 'low';  // ❌ 특정 곡 강도 하드코딩
```

**허용 — 프롬프트에서 동적 추출한 값 사용:**
```ts
const bpm = manifest.bpm ?? 120;          // ✅ 추출 실패 시 120은 안전 기본값
const duration = scene.duration_seconds;   // ✅ 씬 프롬프트에서 추출
const intensity = scene.intensity;         // ✅ 씬 프롬프트에서 추출
```

**허용 — 시각 효과의 디자인 상수 (음악과 무관한 픽셀·불투명도 값):**
```ts
interpolate(progress, [0, 1], [-120, 120])  // ✅ 스트릭 오버레이 픽셀 범위
borderTop: '58px solid rgba(0,0,0,0.58)'    // ✅ 레터박스 높이 (디자인 고정값)
```

### 소스 수정 시 항상 확인해야 하는 체크리스트

코드를 추가하거나 수정할 때 아래 항목을 반드시 점검한다.

| 확인 항목 | 관련 파일 | 점검 내용 |
|----------|----------|---------|
| BPM 추출 | `scripts/import_input.mjs:extractBpm()` | 새 프롬프트 형식에서 BPM이 올바르게 추출되는가 |
| 길이 추출 | `scripts/import_input.mjs:extractDuration()` | duration 패턴이 프롬프트와 일치하는가 |
| intensity 추출 | `scripts/import_input.mjs:extractIntensity()` | 키워드가 프롬프트 표현과 일치하는가 |
| camera 추출 | `scripts/import_input.mjs:extractCameraDirection()` | "Camera motion:" 패턴이 유지되는가 |
| 키워드 매핑 | `src/lib/promptMotion.ts` | push-in/pullback/beat 등 키워드가 프롬프트 텍스트와 일치하는가 |
| 하드코딩 여부 | 모든 파일 | 특정 BPM·초·강도 숫자가 코드에 직접 들어가 있지 않은가 |
| 기본값 타당성 | `render_scenes.mjs`, `promptMotion.ts` | `?? 120` 같은 fallback이 곡에 관계없이 안전한가 |

### 프롬프트 → 코드 추출 체인

모든 음악·씬 값은 아래 경로로만 코드에 전달된다. 이 흐름을 우회하면 안 된다.

```
input/scene_NN_name.md
  │
  ├─ extractTitle()         → song_master.title
  ├─ extractBpm()           → song_master.bpm → manifest.bpm → getPromptMotion(bpm)
  ├─ extractDuration()      → scene.duration_seconds → scene.duration_frames
  ├─ extractIntensity()     → scene.intensity → intensityAmount() → amount
  ├─ extractCameraDirection()→ scene.camera_direction → pushIn/pullback/lateral 키워드
  └─ selected_video_prompt  → beat/neon/dark 등 분위기 키워드
```

---

## Remotion API 규칙 (v4.0.461)

참조 문서: `docs/remotion-reference.md`

- `<Html5Video>` 사용 (`<Video>` deprecated)
- `<Html5Audio>` 사용 (`<Audio>` deprecated)
- `trimBefore`/`trimAfter` 사용 (`startFrom`/`endAt` deprecated since v4.0.319)
- `OffthreadVideo`는 `loop` 미지원 — 루프가 필요하면 `Html5Video` 사용
- `public/` 내 파일은 반드시 `staticFile()` 로 감싸기
- 동적 fps/durationInFrames/width/height는 `calculateMetadata` 사용

---

## 프로젝트 구조

입력 파이프라인: `input/` → `scripts/import_input.mjs` → `manifests/` → `scripts/render_scenes.mjs` → `output/clips/`

- 씬 이미지·프롬프트: `input/scene_NN_name.png` + `input/scene_NN_name.md` 쌍
- 캐릭터 참고 이미지: `input/character_reference_prompt.png` (선택, 1개)
- 렌더 출력: 1920×1080, 오디오 없음
- `SceneOnly` 컴포지션 (`src/compositions/SceneOnly.tsx`): 씬별 개별 클립 렌더

---

## 스크립트 진입점

```
npm run import:input   # input/ 스캔 → manifest 생성
npm run render:scenes  # output/clips/{slug}.mp4 렌더
npm run build          # import + typecheck + render
```

또는 `run.bat` (Windows 메뉴).
