# AI Anime Cinematic MV System

곡 정보(가사, 장르, BPM 등)를 입력하면 애니메이션 스타일의 뮤직비디오 제작용 스토리보드와 이미지·영상 프롬프트를 자동으로 생성하는 로컬 파이프라인입니다.  
외부 AI API 없이 Python 표준 라이브러리만으로 동작하며, 웹 UI를 통해 브라우저에서 바로 사용할 수 있습니다.

---

## 빠른 시작

```bat
run_web.bat
```

배치 파일을 더블클릭하면 웹 서버가 실행되고 브라우저에서 `http://127.0.0.1:8000` 이 자동으로 열립니다.

---

## 폴더 구조

```text
ai_anime/
├─ input/              ← 현재 작업 중인 곡 입력 파일
├─ analysis/           ← 감정·영상·영화 스타일 분석 결과
├─ character/          ← 주인공 캐릭터 설정 및 프롬프트
├─ storyboard/         ← 생성된 스토리보드 전체
├─ prompts/            ← 씬별 이미지·영상 프롬프트
│  ├─ image_prompts/
│  └─ video_prompts/
├─ configs/            ← 파이프라인 동작 규칙 설정 파일 (15개)
├─ data/               ← Suno 이력 및 Config 자동 학습 데이터
├─ output/             ← 파이프라인 실행 결과물 저장소
│  ├─ <노래제목>/       ← 웹 UI Generate 결과
│  ├─ storyboard/      ← CLI --snapshot 결과
│  ├─ web_inputs/      ← 웹 UI 입력 파일 자동 백업
│  ├─ images/          ← 생성된 이미지 보관 (향후)
│  └─ videos/          ← 생성된 영상 보관 (향후)
├─ scripts/            ← 핵심 Python 스크립트 (11개)
├─ build.bat           ← PyInstaller EXE 빌드
└─ run_web.bat         ← 웹 UI 실행
```

---

## 폴더별 상세 설명

### `input/` — 곡 입력 파일

현재 작업 중인 곡의 원본 데이터를 보관합니다. 웹 UI에서 가사를 붙여넣거나 파일을 업로드하면 이 폴더에 저장됩니다.

| 파일 | 설명 |
|---|---|
| `raw_song.txt` | 가사 원문, 장르·BPM·분위기 등 메타데이터 포함 |
| `song_master.json` | 파서가 raw_song.txt를 처리해 생성한 구조화 데이터 |
| `ui_state.json` | 웹 UI 마지막 상태 저장 (탭, 옵션 등) |

---

### `analysis/` — 음악 분석 결과

`song_master.json`을 바탕으로 감정·비주얼·영화적 스타일을 분석한 결과입니다. `emotion_engine.py`가 자동 생성합니다.

| 파일 | 설명 |
|---|---|
| `emotion_analysis.json` | 섹션별 감정 곡선, 에너지 레벨, 분위기 키워드 |
| `visual_world.json` | 색상 팔레트, 조명, 배경 세계관 설정 |
| `cinematic_style.json` | 카메라 무빙, 편집 템포, 영화적 레퍼런스 스타일 |

---

### `character/` — 캐릭터 설정

곡 안에서 일관성을 유지하는 주인공 또는 주요 비주얼 주체를 정의합니다. 먼저 곡 메타데이터로 `human_solo`, `human_duo`, `group`, `object_symbol`, `environment_only`를 판단하고, 사람 중심일 때는 남성형·여성형·혼성·중성 표현을 함께 반영합니다. 캐릭터는 장르 프로필을 기반으로 만들되, 곡 제목·장르·BPM·에너지·무드·섹션 구조에서 만든 고유 시드로 얼굴 디테일, 헤어 변주, 의상 포인트, 액세서리, 제스처를 추가합니다.

| 파일/폴더 | 설명 |
|---|---|
| `protagonist_bible.json` | 헤어·의상·색상 규칙·성격 등 주인공 전체 설정 |
| `character_prompt.md` | 이미지 생성 AI용 캐릭터 묘사 프롬프트 |
| `character_reference_prompt.md` | 캐릭터 턴어라운드 시트(모델시트) 생성용 프롬프트 |
| `character_reference/` | 생성된 캐릭터 레퍼런스 이미지 보관 폴더 |

> **작업 순서 권장:** 씬 이미지 생성 전에 `character_reference_prompt.md`로 캐릭터 레퍼런스 이미지를 먼저 만들면 씬 간 비주얼 일관성이 높아집니다.

---

### `storyboard/` — 스토리보드

씬 구성, 이야기 흐름, 카메라 연출이 담긴 스토리보드 전체입니다. `scene_generator.py`가 자동 생성합니다.

| 파일 | 설명 |
|---|---|
| `scene_list.json` | 전체 씬 목록, 섹션 매핑, 감정·카메라 메타데이터 |
| `story_arc.json` | 서사 구조 (도입→전개→절정→결말) |
| `story_summary.md` | 한국어 스토리 요약 및 씬별 연속성 설명 |
| `storyboard_prompts.md` | 전체 씬의 이미지 프롬프트 통합 문서 |
| `camera_directions.md` | 씬별 카메라 앵글·무빙·편집 컷 가이드 |

---

### `prompts/` — 이미지·영상 프롬프트

이미지 생성 AI와 영상 생성 AI에 직접 붙여넣을 수 있는 씬별 프롬프트입니다.

| 경로 | 설명 |
|---|---|
| `image_prompts/00_character_turnaround_model_sheet.md` | 캐릭터 모델시트 생성용 통합 프롬프트 |
| `image_prompts/scene_XX_*.md` | 씬별 이미지 프롬프트 (Midjourney, DALL-E 등 사용) |
| `video_prompts/scene_XX_*.md` | 씬별 영상 프롬프트 (10개 플랫폼 최적화) |
| `style_rules.md` | 전체 시리즈에 적용되는 비주얼 스타일 규칙 |

**지원 영상 생성 플랫폼 (10개):** Runway · Kling · Pika · Luma · Veo · Flow · Sora · Hailuo · PixVerse · Remotion

---

### `configs/` — 파이프라인 설정 파일 (15개)

씬 생성 엔진의 동작 규칙을 정의하는 JSON 설정 파일 모음입니다.  
`Config 자동 학습` 버튼으로 `genres.json`과 `atmosphere_rules.json`이 자동 업데이트됩니다.

| 파일 | 설명 |
|---|---|
| `genres.json` | 장르 프로파일 13종 및 스타일 키워드 (현재 1,602개) |
| `color_palette.json` | 장르·분위기 키워드 → 주 색상 매핑 (기본값: neon magenta) |
| `emotions.json` | 17개 감정 키워드 및 시각적 연출 매핑 (66개 별칭 포함) |
| `emotion_transitions.json` | 섹션 간 감정 전환 패턴 (Chorus 고조, Bridge 심화, Outro 해소) |
| `atmosphere_rules.json` | 도시 키워드, 계절 규칙 등 분위기 설정 |
| `bpm_thresholds.json` | BPM 구간별 템포·편집 속도 기준 |
| `shot_rules.json` | BPM·에너지별 카메라 샷 유형 규칙 |
| `location_rules.json` | 감정·장르별 배경 장소 선택 규칙 |
| `action_rules.json` | 섹션·감정별 캐릭터 동작 연출 규칙 |
| `focus_rules.json` | 씬별 피사체 초점 및 구도 규칙 |
| `motif_rules.json` | 반복 등장하는 시각적 모티프 설정 |
| `prop_rules.json` | 소품 배치 규칙 |
| `song_sections.json` | 곡 섹션(Intro/Verse/Chorus 등) 정의 및 동작 오버라이드 |
| `visual_styles.json` | 비주얼 스타일 프리셋 |
| `character_defaults.json` | 캐릭터 기본값 및 곡별 고유 변주 설정 |

---

### `data/` — 학습 데이터

파이프라인의 핵심 데이터 자산입니다. `configs/`와 함께 별도로 관리·백업하는 것을 권장합니다.

| 파일/폴더 | 설명 |
|---|---|
| `suno_history.jsonl` | Suno 곡 이력 (현재 196곡). 웹 UI의 **가져오기**·**Generate Storyboard** 클릭 시 누적 |
| `config_backups/` | Config 자동 학습 적용 시 타임스탬프별 자동 생성되는 백업 |

#### 두 수집 경로의 데이터 품질 차이

| 항목 | 가져오기 (suno_import) | Generate Storyboard |
|---|---|---|
| 태그·장르 | Suno 페이지 HTML 파싱 | song_master.json 완전 처리 결과 |
| mood / energy / instruments | 태그에서 추정 (불완전) | 가사 전체 분석 결과 |
| section_structure | 항상 빈 값 | 실제 섹션 구조 [Intro, Verse, Chorus…] |
| Config 자동 학습 기여도 | 장르·분위기 키워드 | 위 항목 모두 + 정확한 섹션 구조 |

> **앱 시작 시 자동 처리:** `suno_import` 항목은 최신 패턴 분석 로직으로 재적용하고 URL 기준 중복을 제거합니다. `generate_storyboard` 항목은 song_master.json 기반 고품질 데이터를 그대로 보존합니다.

---

### `output/` — 실행 결과물

파이프라인이 실행될 때마다 결과물이 저장되는 폴더입니다.

| 경로 | 설명 |
|---|---|
| `output/<노래제목>/` | 웹 UI에서 Generate Storyboard 실행 시 자동 생성 (analysis·character·storyboard·prompts 전체 복사) |
| `output/storyboard/<slug-timestamp>/` | CLI `--snapshot` 옵션 사용 시 타임스탬프별 전체 패키지 저장 |
| `output/web_inputs/<timestamp>/` | 웹 UI 입력 파일 자동 백업 |
| `output/images/` | 생성된 이미지 보관 (향후) |
| `output/videos/` | 생성된 영상 보관 (향후) |

---

### `scripts/` — 핵심 스크립트 (11개)

| 파일 | 역할 |
|---|---|
| `main_entry.py` | EXE 빌드용 진입점. 웹 서버 실행 후 브라우저를 자동으로 엽니다 |
| `web_app.py` | 웹 UI 서버. Suno 가져오기·패턴 분석·Config 자동 학습·실시간 미리보기 포함 |
| `run_pipeline.py` | 전체 파이프라인을 순서대로 일괄 실행하는 CLI 진입점 |
| `song_parser.py` | raw_song.txt·lrc·srt·오디오 파일을 파싱해 `song_master.json` 생성 |
| `emotion_engine.py` | 감정 분석 및 비주얼 월드 생성 (emotion_analysis·visual_world·cinematic_style) |
| `scene_generator.py` | 스토리보드·씬 목록·카메라 연출 생성. 장르 기반 동적 색상 선택 포함 |
| `image_prompt_generator.py` | 씬별 이미지 프롬프트 생성 (캐릭터 모델시트 포함) |
| `video_prompt_generator.py` | 씬별 영상 프롬프트 생성 (10개 플랫폼 최적화) |
| `config_learner.py` | Suno 이력 분석 → `genres.json`·`atmosphere_rules.json` 자동 업데이트 |
| `common.py` | 공통 경로·JSON I/O·유틸리티 함수 (PyInstaller exe 호환 포함) |
| `__init__.py` | 패키지 초기화 |

---

## 입력 형식

`input/` 폴더에 곡 파일을 넣거나 웹 UI에서 직접 입력합니다. 파서가 폴더를 스캔해 `song_master.json`을 자동 생성합니다.

**지원 파일 형식:**
- `.txt` — 가사 + 메타데이터 (권장)
- `.lrc` — 타임스탬프 가사 (`MM:SS.centiseconds`)
- `.srt` — 자막 형식 타임스탬프 (`HH:MM:SS,milliseconds`)
- `.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`, `.ogg` — 오디오 참조 메타데이터 (선택)

**지원 메타데이터 필드:**

```text
Genre:
BPM:
Mood:
Energy:
Instruments:
Music style tags:
Negative tags:
Visual cues:
Atmosphere:
Pacing:
```

**지원 섹션 레이블:**

```text
[Intro]  [Verse]  [Pre-Chorus]  [Chorus]  [Post-Chorus]  [Bridge]  [Outro]
```

---

## 실행 방법

### 웹 UI (권장)

```bat
run_web.bat
```

또는:

```powershell
python scripts/web_app.py
```

브라우저에서 `http://127.0.0.1:8000` 열기

**웹 UI 주요 기능:**

- **가져오기**: Suno URL에서 제목·태그·가사를 자동 추출해 `data/suno_history.jsonl`에 저장
- **Generate Storyboard**: 전체 파이프라인 실행 → `output/<노래제목>/`에 결과물 저장
- **Config 자동 학습**: `suno_history.jsonl` 분석 → `configs/genres.json`·`atmosphere_rules.json` 자동 업데이트
- 씬·이미지 프롬프트·영상 프롬프트·JSON 결과를 브라우저에서 바로 확인

### CLI 전체 파이프라인

```powershell
# 기본 실행
python scripts/run_pipeline.py

# 타임스탬프 스냅샷 저장
python scripts/run_pipeline.py --snapshot

# 커스텀 입력 파일 또는 폴더
python scripts/run_pipeline.py --input input/my_song.txt --snapshot
python scripts/run_pipeline.py --input input --snapshot

# 오디오 분석 힌트 적용 (ffmpeg 필요)
python scripts/run_pipeline.py --input input --apply-audio-analysis --snapshot
```

### 단계별 개별 실행

```powershell
python scripts/song_parser.py --input input
python scripts/emotion_engine.py
python scripts/scene_generator.py
python scripts/image_prompt_generator.py
python scripts/video_prompt_generator.py
python scripts/config_learner.py --dry-run   # 분석만 (파일 변경 없음)
python scripts/config_learner.py             # 분석 후 configs/ 업데이트
```

### EXE 빌드 (선택)

```bat
build.bat
```

PyInstaller로 `dist/ai_anime_mv_builder.exe` 생성. 일반 사용 시에는 필요하지 않습니다.

---

## 파이프라인 흐름

```text
[Suno URL 가져오기]
        │
        ↓
data/suno_history.jsonl ──→ [Config 자동 학습] ──→ configs/ 업데이트
                                                      (config_backups/ 자동 백업)

[입력 파일 (txt / lrc / srt / 오디오)]
        │
        ↓
song_parser.py
        │
        ↓
input/song_master.json
        │
        ├──→ emotion_engine.py ←── emotions.json / emotion_transitions.json
        │           │
        │           ↓
        │    analysis/ (emotion_analysis, visual_world, cinematic_style)
        │           │
        └──→ scene_generator.py ←── color_palette.json / shot_rules.json
                    │                genres.json / atmosphere_rules.json
                    ↓
        storyboard/ (scene_list, story_arc, story_summary, camera_directions)
        character/  (protagonist_bible, character_prompt)
                    │
                    ↓
        image_prompt_generator.py
                    │
                    ↓
        prompts/image_prompts/scene_XX_*.md
                    │
                    ↓
        video_prompt_generator.py
                    │
                    ↓
        prompts/video_prompts/scene_XX_*.md
        (Runway · Kling · Pika · Luma · Veo · Flow · Sora · Hailuo · PixVerse · Remotion)
                    │
                    ↓
        output/<노래제목>/  ←── 웹 UI Generate Storyboard 실행 시 전체 복사
        output/storyboard/<slug-timestamp>/  ←── CLI --snapshot 실행 시
```

---

## 출력 결과물

파이프라인 완료 시 생성되는 파일 목록:

```text
input/song_master.json
analysis/
  emotion_analysis.json
  visual_world.json
  cinematic_style.json
character/
  protagonist_bible.json
  character_prompt.md
  character_reference_prompt.md
storyboard/
  scene_list.json
  story_arc.json
  story_summary.md
  storyboard_prompts.md
  camera_directions.md
prompts/
  image_prompts/
    00_character_turnaround_model_sheet.md
    scene_XX_*.md  (씬별)
  video_prompts/
    scene_XX_*.md  (씬별, 10개 플랫폼 섹션 포함)
output/<노래제목>/
  (위 결과물 전체 복사본)
```

---

## 핵심 개념

**Config 중심 설계**: 모든 규칙이 `configs/*.json`에 정의되고 Python은 순수 실행 엔진 역할만 합니다. 규칙 수정 시 Python 코드를 건드리지 않아도 됩니다.

**동적 색상 선택**: 장르·분위기 키워드 기반으로 주 색상을 동적으로 선택합니다.
- rock → crimson red, jazz → amber gold, k-pop → electric blue
- dark / noir / urban 계열 → neon magenta (기본값)

**감정 매핑**: 17개 감정(lonely, nostalgic, sad, hopeful, angry, defiant, romantic, longing, anxious, peaceful, excited, bittersweet, fearful, dreamy, tense 등)과 66개 별칭을 지원합니다. 섹션별 감정 전환이 자동 적용됩니다.

**주체/캐릭터 일관성**: 한 곡 내에서 주인공 또는 오브젝트/배경 주체를 일관되게 유지합니다. 보컬·장르·제목·시각 단서로 사람/듀오/그룹/오브젝트/배경 중심 여부와 성별 표현을 판단하고, 다른 노래로 생성할 때는 얼굴 디테일·헤어 변주·의상 포인트·액세서리·대표 제스처 또는 주요 오브젝트/환경 주체가 달라집니다.

**자동 학습**: `config_learner.py`가 `suno_history.jsonl`을 분석해 장르 프로파일과 분위기 규칙을 자동으로 업데이트합니다. 변경 전 자동 백업이 생성됩니다.

**멀티 플랫폼 최적화**: 각 영상 생성 AI 플랫폼의 특성에 맞게 최적화된 프롬프트를 씬마다 생성합니다.

---

## 요구사항

- Python 3.10 이상
- 외부 패키지 불필요 (표준 라이브러리만 사용)
- 오디오 분석 힌트(`--apply-audio-analysis`) 사용 시 ffmpeg 필요 (선택)

