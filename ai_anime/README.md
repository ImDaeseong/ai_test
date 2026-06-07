# AI Anime Cinematic MV System

> 곡 정보(가사·장르·BPM)를 입력하면 애니메이션 뮤직비디오 제작용 스토리보드와 이미지·영상 프롬프트를 자동 생성하는 로컬 파이프라인.  
> 외부 AI API 없이 Python 표준 라이브러리만으로 동작하며, 웹 UI로 브라우저에서 바로 사용 가능.

---

## 빠른 시작

```bat
run_web.bat
```

배치 파일을 더블클릭하면 웹 서버가 실행되고 브라우저에서 `http://127.0.0.1:8000` 이 자동으로 열립니다.

---

## 폴더 구조

```
ai_anime/
├─ input/              ← 현재 작업 중인 곡 입력 파일
├─ analysis/           ← 감정·영상·영화 스타일 분석 결과
├─ character/          ← 주인공 캐릭터 설정 및 프롬프트
├─ storyboard/         ← 생성된 스토리보드 전체
├─ prompts/            ← 씬별 이미지·영상 프롬프트
│  ├─ image_prompts/
│  └─ video_prompts/
├─ configs/            ← 파이프라인 동작 규칙 설정 파일 (23개)
├─ data/               ← Suno 이력 및 Config 자동 학습 데이터
├─ tests/fixtures/     ← 회귀 검증용 픽스처 (29곡)
├─ output/             ← 파이프라인 실행 결과물 저장소
├─ scripts/            ← 핵심 Python 스크립트
├─ build.bat           ← PyInstaller EXE 빌드
└─ run_web.bat         ← 웹 UI 실행
```

---

## 파이프라인 구조

```
[입력: txt / lrc / srt / 오디오]
        │
        ▼
song_parser.py          → input/song_master.json
        │
        ▼
emotion_engine.py       → analysis/ (emotion_analysis, visual_world, cinematic_style)
        │
        ▼
scene_generator.py      → storyboard/ + character/
        │
        ├─▶ image_prompt_generator.py → prompts/image_prompts/*.md  (6개 플랫폼)
        │
        └─▶ video_prompt_generator.py → prompts/video_prompts/*.md  (11개 플랫폼)
```

**영상 생성 지원 플랫폼 (11개):** Runway · Kling · Pika · Luma · Veo · Flow · Sora · Hailuo · PixVerse · Wan 2.2 · Remotion

---

## 실행 방법

### 웹 UI (권장)
```bat
run_web.bat
```
또는 `python scripts/web_app.py` → `http://127.0.0.1:8000`

### CLI 전체 파이프라인
```powershell
python scripts/run_pipeline.py
python scripts/run_pipeline.py --snapshot               # 타임스탬프 스냅샷
python scripts/run_pipeline.py --input input/my.txt    # 커스텀 입력
python scripts/run_pipeline.py --apply-audio-analysis  # 오디오 분석 반영 (ffmpeg 필요)
```

### 검증 명령
```powershell
python __validate_all.py              # 26곡 전체 파이프라인 + 즉시 검증 (PASS 26 / FAIL 0 목표)
python scripts/run_regression.py      # 29개 픽스처 회귀 검증 (29 passed / 0 failed 목표)
python scripts/run_regression.py --verbose  # 통과 픽스처 소스 경로 포함 출력
python scripts/validate_configs.py   # Config JSON 구조 유효성 검사
```

---

## 지원 입력 형식

| 형식 | 설명 |
|------|------|
| `.txt` | 가사 + 메타데이터 (권장) |
| `.lrc` | 타임스탬프 가사 |
| `.srt` | 자막 형식 타임스탬프 |
| `.mp3/.wav/.m4a` | 오디오 참조 메타데이터 (선택) |

**지원 메타데이터:** `Genre:` `BPM:` `Mood:` `Energy:` `Instruments:` `Music style tags:`

**지원 섹션:** `[Intro]` `[Verse]` `[Pre-Chorus]` `[Chorus]` `[Post-Chorus]` `[Bridge]` `[Outro]` `[Build]` `[Drop]` `[Hook]` `[Final Chorus]`

---

## 핵심 설계 원칙

- **Config 중심**: 모든 규칙은 `configs/*.json`. Python 스크립트는 순수 실행 엔진.
- **동적 색상**: 장르·분위기 키워드로 주 색상을 곡마다 다르게 결정.
- **연주 섹션 자동 처리**: 한국어 가사 없는 섹션은 `Scene atmosphere:`로 처리.
- **감정 매핑**: 17개 감정 + 66개 별칭, 섹션별 전환 자동 적용.
- **자동 학습**: `config_learner.py`가 Suno 이력 → config 자동 업데이트.
- **플랫폼 정책 안전화**: 이미지·영상·클립 프롬프트 저장 직전 `policy_safety.py`로 위험 표현을 안전한 애니메이션 MV 공연 표현으로 정규화.

### 플랫폼 정책 안전화

일부 이미지/영상 AI 플랫폼은 음악 MV 의도와 무관하게 특정 단어를 폭력, 구속, 위험 도구, 인체 잔해 맥락으로 오탐할 수 있습니다.  
`ai_anime`는 곡마다 세계관과 캐릭터가 달라지는 프로젝트이므로, `ai_img_video_prompt`처럼 세계관을 고정하지 않고 **위험 표현만 후처리로 안전화**합니다.

안전화 대상:

- `blood / gore / corpse / human remains` → 비폭력적 상징, 조명, 부재의 흔적 표현
- `weapon / knife / gun` → 무대 소품, 조명 장치, 반사형 공연 소품 표현
- `chain / bound / tied up / restraint` → 장식성 의상 디테일, 음악적 절제, 비구속적 동작 표현
- `violent / dangerous / headbanging / screams aggressively` → 고대비 연출, 고에너지 공연 동작, 음악적 긴장 표현

적용 위치:

- `scripts/prompt_writer.py`: 기본 이미지·영상 프롬프트
- `scripts/shot_expander.py`: wide/action/emotion/detail 샷 프롬프트
- `scripts/image_prompt_generator.py`: 플랫폼별 이미지 프롬프트 파일 저장 직전
- `scripts/video_prompt_generator.py`: 플랫폼별 영상·클립 프롬프트 파일 저장 직전
- `scripts/validate_output_consistency.py`, `__validate_all.py`: 정책 위험 표현 잔여 검사

2026-06-03 확인:

```text
python -m py_compile ...                              → 통과
python scripts/run_pipeline.py --input input\위험해.txt → 이미지 49개, 영상 12개, 클립 48개 생성
output\위험해 정책 위험 표현 검색                     → 0건
output\위험해 내부 일관성 검증                         → PASS, warnings 0
```

### 텍스트·워터마크 제외 조건 (2026-06-07 추가)

AI 이미지 생성기가 프롬프트 없이도 글자·숫자·로고를 삽입하는 경향이 있어 `image_prompt_generator.py`에 플랫폼별 명시적 제외 조건을 추가했습니다.

| 플랫폼 | 제외 조건 형식 |
|--------|--------------|
| GPT Image / Gemini / Leonardo | `Do not add any text, letters, numbers, watermarks, logos, or UI overlays to the image.` |
| FLUX.1 | `No text, letters, numbers, watermarks, logos, or UI overlays.` |
| Midjourney / Nijijourney | `--no watermark, text, letters, numbers, logo, UI overlay, signature` |

2026-06-07 확인: 214곡 × 이미지 프롬프트 파일 7429개 전수 검증 PASS (FAIL 0)

### 비주얼 스타일 (6종)

| style_id | 특징 |
|----------|------|
| `warm_acoustic` | 따뜻한 어쿠스틱·친밀감 |
| `idol_bright` | 밝은 아이돌 팝 |
| `urban_noir` | 도시 스트리트 누아르 |
| `dreamy_synth` | 몽환적 신스 |
| `rock_edge` | 하이 콘트라스트 록 |
| `ethereal_dark` | 오케스트라 다크 시네마틱 |

### 장르 미학 레퍼런스 계층

`configs/genre_reference_profiles.json`은 기존 장르 분류 결과에 장르별 시각 문법을 보완합니다.

- 분류 키워드와 생성 미학 데이터를 분리합니다.
- 록, 어쿠스틱/발라드, 힙합/트랩, 전자/신스, 아이돌 팝, 재즈/소울 6계열을 우선 지원합니다.
- 장소, 카메라, 움직임, 전환, 조명, 캐릭터 방향을 곡별 결정론적 변형으로 선택합니다.
- 공개 기관 자료의 출처는 데이터에만 보관하며 생성 프롬프트에는 기관·아티스트·작품명을 노출하지 않습니다.
- 기존 프로필에 매핑되지 않는 장르는 이전 생성 동작을 그대로 사용합니다.

상세 출처와 안전 정책은 `GENRE_REFERENCE_DATA.md`를 참고하십시오.

---

## 요구사항

- Python 3.10 이상
- 외부 패키지 불필요 (표준 라이브러리만 사용)
- 오디오 분석 시 ffmpeg 필요 (선택)

---

---

# 헤르메스 분석 보고서 (2026-05-29)

> 이 섹션은 프로젝트의 현재 상태를 객관적으로 진단하고 나아가야 할 방향을 제시합니다.  
> 새 기능 추가 전 반드시 이 섹션을 먼저 읽으십시오.

---

## 현재 상태 진단

**이 프로젝트는 "원칙상 올바른 설계"를 가지고 있으나, 구현 과정에서 기술 부채가 누적되어 유지보수 비용이 지속적으로 증가하고 있습니다.**

| 지표 | 2026-05 (개선 전) | 2026-06-02 (현재) |
|------|-----------------|-----------------|
| scene_generator.py | 1,616줄 (God Object) | **235줄** (6개 모듈 분리 ✅) |
| 색상 치환 레이어 | 3층 분산 | **common.py 단일 처리 ✅** |
| CLAUDE.md 버그 목록 | 30+ 항목 | 30+ 항목 (P2 이후 신규 발생 없음) |
| 새 곡 추가 시 버그 확률 | 높음 | **낮음** — 모듈별 격리로 범위 특정 가능 |
| run_regression.py 통과 | 29 passed | **33 passed** |

---

## 인접 프로젝트와의 정확한 비교

같은 저장소의 `ai_img_video_prompt`도 "새 곡 테스트 → 수정 → 반복" 사이클을 거쳤으나 2026-05-29에 안정화되었습니다. 그러나 **두 프로젝트를 같은 기준으로 비교하는 것은 목적 자체가 다르기 때문에 적절하지 않습니다.**

| 항목 | ai_img_video_prompt | ai_anime |
|------|---------------------|----------|
| **핵심 목적** | 하나의 고정 밴드 세계관에서 에너지·분위기만 교체 | 곡마다 완전히 다른 시각 세계관·캐릭터·색상·씬을 새로 생성 |
| 세계관 | 고정 (스켈레톤 밴드, 네온 마젠타 달) | 곡별 완전 독립 생성 |
| 프롬프트 형식 | **하나의 고정 템플릿** + 장르별 미세 조정 | **곡마다 다른 내용** — 장르·감정·캐릭터 모두 다름 |
| 안정화 방식 | 제약을 통한 안정화 (형식 고정) | 커버리지 확장을 통한 안정화 (가능한 조합을 모두 검증) |

**`ai_img_video_prompt`의 안정화 패턴을 `ai_anime`에 적용하는 것은 옳지 않습니다.**  
그렇게 하면 `ai_anime`가 하려는 일 — "장르와 곡에 따라 완전히 다른 시각 세계관 생성" — 을 포기해야 합니다.

`ai_anime`의 복잡성은 설계 실수가 아닙니다. **더 어려운 문제를 풀고 있기 때문에 발생하는 정당한 복잡성입니다.**  
따라서 이 프로젝트의 안정화 전략은 "제약을 추가하는 것"이 아니라 "더 넓은 커버리지를 체계적으로 검증하는 것"입니다.

---

## 핵심 설계 문제 (심각도 순)

### 🔴 1. scene_generator.py — God Object (1,594줄)

한 파일이 **색상 팔레트 관리 + 장르 선택 + 캐릭터 생성 + 씬 생성 + 프롬프트 조립 + 마크다운 출력**을 모두 담당합니다.

- 색상 버그 발생 시 수십 개 함수 전체가 영향을 받음
- 새 기능 추가 시 부작용 범위를 예측할 수 없음
- 단위 테스트 작성이 사실상 불가능한 구조

### 🔴 2. 색상 치환 시스템 — 3층 누적 구조

```
emotions.json (색상 토큰 포함)
  ↓ _apply_color()          ← 층 1
  ↓ _apply_full_palette()   ← 층 2
  ↓ _AMBIENT_SUBS 패턴      ← 층 3
```

새 색상 토큰 추가 시 3개 파일을 함께 수정해야 합니다. 누락 시 `neon magenta` 같은 raw 토큰이 프롬프트에 그대로 노출됩니다. **CLAUDE.md 버그 30+ 항목 중 11건이 이 원인에서 발생했습니다.**

### 🟠 3. 글로벌 상태 오염

```python
BRAND_PALETTE = {}  # 전역 변수 — 배치 처리 시 이전 곡 색상이 다음 곡에 오염
```

임시 패치(`dict()` shallow copy)로 막았지만, 근본 구조는 유지되고 있습니다.

### 🟠 4. 정규식 파싱의 취약성

`SECTION_LABEL_PATTERN`이 Suno의 새로운 섹션 형태가 등장할 때마다 수동으로 수정되고 있습니다. CLAUDE.md에 이미 6건이 기록되었습니다.

---

## 버그 반복 패턴 — 사이클 분석

CLAUDE.md의 30+ 버그를 분류하면 4가지 카테고리로 수렴합니다:

| 카테고리 | 건수 | 근본 원인 |
|---------|------|---------|
| 색상 치환 미완 | 11건 | 색상 토큰 + 치환 함수가 여러 파일에 분산 |
| 파싱/정규식 실패 | 6건 | SECTION_LABEL_PATTERN 불완전 |
| 글로벌 상태 오염 | 3건 | BRAND_PALETTE 전역 변수 구조 |
| 플랫폼 포맷 누락 | 5건 | 11개 플랫폼 검증 체계 미흡 |

**패턴의 핵심:** 버그 발생 → **그 위치만 수정(증상 치료)** → 같은 유형의 버그가 **다른 위치에서 재발**. 이 사이클이 반복됩니다.

---

## 구조 개선 완료 현황 (2026-06-02)

| 우선순위 | 항목 | 상태 | 완료일 |
|---------|------|------|--------|
| P1 | 색상 토큰 처리 단일화 | ✅ 완료 | 2026-05 |
| P2 | scene_generator.py 분해 | ✅ 완료 | 2026-06-02 |
| P3 | Section Parser 견고화 | ✅ 완료 | 2026-05 |
| P4 | 검증 커버리지 확장 | 보류 | — |
| P5 | 운영 효율화 | 보류 | — |

### P1 — 색상 토큰 처리 단일화 ✅

- `_apply_color()` · `_apply_full_palette()` · `_AMBIENT_SUBS` 3층 분산 구조를 `common.py`로 통합
- `ColorPalette.apply_all()`로 모든 색상 토큰을 순서 보장하여 한 번에 처리 — 누락 불가 구조

### P2 — scene_generator.py 분해 ✅

**1,616줄 → 235줄 (85% 감소)**

| 파일 | 책임 | 줄수 |
|------|------|------|
| `genre_selector.py` | 장르 프로필 선택, `build_adaptive_default` | ~195줄 |
| `_song_helpers.py` | 공유 유틸리티: `_stable_choice`, BPM 헬퍼 등 | ~110줄 |
| `world_builder.py` | 세계관·위치·색상 생성, `lighting_language` | ~155줄 |
| `character_builder.py` | 캐릭터 생성, `infer_subject_profile` | ~280줄 |
| `scene_composer.py` | 씬 조합, `choose_shot`, `create_story_arc` | ~430줄 |
| `prompt_writer.py` | 이미지·영상 프롬프트 작성, 마크다운 출력 | ~140줄 |
| `scene_generator.py` | re-export hub + 진입점(`run`, `main`) | 235줄 |

- 외부 코드 수정 없이 호환 유지 (re-export hub 패턴)
- 최종 검증: `run_regression.py` **33 passed, 0 failed** / `__validate_all.py` **전체 PASS, 0 FAIL**

### P3 — Section Parser 견고화 ✅

- `SECTION_LABEL_PATTERN`에 `Final/Repeat/Double/Opening/Extended/Bonus` 접두어 그룹 추가
- `Build` · `Drop` · `Hook` · `Solo` · `Interlude` · `Breakdown` 섹션 지원
- `_PRODUCTION_NOTE_SECTION_RE` 체크로 프로덕션 노트의 섹션 오인식 차단
- LRC 파일에 없는 `[Outro]` 소실 문제 해결 (TXT 파싱 섹션 보존 추가)

### 이전 완료 — run_regression.py 강화

- `no_raw_palette_in_lighting` 검증을 `lighting` 필드 단독에서 → `lighting + movement + image_prompt` 3개 필드로 확장
- 픽스처 `expected` 딕셔너리의 **인식되지 않는 키** 자동 경고 (`_KNOWN_EXPECTED_KEYS` 집합)
- `--verbose` 플래그 추가 — 통과 픽스처의 소스 경로 확인 가능
- 결과 레이블에 `title` 병기로 가독성 개선

---

## ai_anime가 안정화되지 못하는 진짜 이유

`ai_img_video_prompt`가 안정화된 것과 비교할 때, `ai_anime`가 아직 안정화되지 못한 이유를 명확히 해야 합니다.

**`ai_img_video_prompt`는 프롬프트 형식이 고정입니다.** 모든 곡이 같은 템플릿을 사용하고, 에너지·분위기·역할만 교체됩니다. 가변 요소의 수가 적기 때문에 안정화가 가능했습니다.

**`ai_anime`는 곡마다 완전히 다른 프롬프트를 만들어야 합니다.** 장르가 다르면 캐릭터 외형이 다르고, 배경 세계관이 다르고, 색상이 다르고, 씬 분위기가 다릅니다. 이것이 이 프로젝트의 핵심 가치입니다. 따라서 `ai_img_video_prompt`처럼 형식을 고정해 안정화하는 것은 이 프로젝트의 목적 자체를 포기하는 것입니다.

**`ai_anime`의 안정화 전략은 달라야 합니다:**

```
ai_img_video_prompt 방식  →  형식 고정 → 가변 요소 최소화 → 안정
ai_anime 올바른 방식      →  가능한 모든 곡 조합의 커버리지 확장 + 내부 구조 정리
```

버그가 반복되는 이유는 "동적 생성을 한다"는 것 자체가 아닙니다. **동적 생성 코드가 한 파일(scene_generator.py)에 뒤섞여 있고, 색상 토큰 처리가 여러 계층에 분산되어 있어서** 새 곡이 노출하는 엣지케이스를 추적하고 수정하기 어렵기 때문입니다.

---

## 나아가야 할 방향 — 우선순위별 로드맵

### ~~P1 — 색상 토큰 처리 단일화~~ ✅ 완료

~~현재 3개 함수·여러 파일에 분산된 색상 처리를 한 곳으로 모읍니다.~~  
`common.py`의 `ColorPalette.apply_all()`로 완료. 상세 내역은 위 "구조 개선 완료 현황" 참조.

---

### ~~P2 — scene_generator.py 분해~~ ✅ 완료 (2026-06-02)

~~1,594줄을 책임별로 나눕니다.~~  
`scene_generator.py` 1,616줄 → 235줄으로 6개 모듈로 분해 완료. 상세 내역은 위 참조.

---

### ~~P3 — Section Parser 견고화~~ ✅ 완료

~~Suno가 새로운 섹션 표기 형태를 만들 때마다 정규식을 수정하는 사이클을 끊습니다.~~  
접두어 그룹·신규 섹션 타입·프로덕션 노트 차단·LRC Outro 보존까지 실용적으로 완료.

---

### P4 — 검증 커버리지 확장 (보류)

현재 `__validate_all.py`는 Kling·Sora·Wan 3개만 검증합니다. 8개 플랫폼이 검증 밖입니다.

- 나머지 8개 플랫폼 검증 규칙 추가
- 픽스처(33개) → 더 많은 장르 조합 커버
- `dataclass` 타입 강화 → 런타임 이전에 오류 감지

---

### P5 — 운영 효율화 (보류)

- 변경된 곡만 재처리 (현재: 26곡 전체 재실행 ~3초)
- `BRAND_PALETTE` 전역 의존성 제거 → 다중 곡 병렬 처리 가능
- 새 플랫폼 추가 시 `plugins/` 파일 추가만으로 완결되는 구조

---

## 지금 당장 하지 말아야 할 것

| 하지 말 것 | 이유 |
|-----------|------|
| `scene_generator.py`에 새 기능 직접 추가 | 1,594줄에 더 쌓이면 분해가 불가능해짐 |
| `_apply_full_palette()`에 패턴 하나 더 추가 | 3층 → 4층 누적 — 어디서 누락됐는지 더 찾기 어려워짐 |
| 픽스처를 `--overwrite`로 무조건 재생성 | 버그 있는 출력이 "정답"으로 고정될 위험 |
| `emotions.json`에 새 ambient 색 추가 (패턴 등록 없이) | 다음 곡에서 raw 토큰 노출 |
| `ai_img_video_prompt`처럼 프롬프트 형식 고정 | 이 프로젝트의 핵심 가치(곡별 고유 세계관)를 포기하는 것 |

---

## 결론

**이 프로젝트는 더 어려운 문제를 풀고 있습니다.** "모든 장르·모든 곡에 맞는 고유한 시각 세계관을 생성한다"는 목표는 `ai_img_video_prompt`의 고정 형식 방식으로 달성할 수 없습니다. 복잡성은 설계 실수가 아니라 목적에서 오는 것입니다.

**해결책은 복잡성을 줄이는 것이 아니라, 복잡한 코드를 더 잘 구조화하는 것입니다.**

P1(색상 단일화)과 P2(분해)를 3-4주 안에 완료하면, 새 곡에서 버그가 발생할 때 "어디를 고쳐야 하는가"를 현재보다 훨씬 빠르게 파악할 수 있습니다. 안정화의 속도가 빨라집니다.
