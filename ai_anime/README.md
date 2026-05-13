# AI Anime Cinematic MV System

A reusable Python pipeline for turning raw song information into an anime-style cinematic music video package.

---

## 프로젝트 개요 (한국어)

곡 정보(가사, 장르, BPM 등)를 입력하면 애니메이션 스타일의 뮤직비디오 제작용 스토리보드와 이미지·영상 프롬프트를 자동으로 생성하는 로컬 파이프라인입니다.  
외부 AI API 없이 Python 표준 라이브러리만으로 동작하며, 웹 UI를 통해 브라우저에서 바로 사용할 수 있습니다.

### 시작하기

```bat
run_web.bat
```

배치파일을 더블클릭하면 웹 서버가 실행되고 브라우저에서 `http://127.0.0.1:8000` 이 열립니다.

---

## 폴더 구조 및 기능 설명

```text
ai_anime/
├─ input/              ← 현재 작업 중인 곡 입력 파일
├─ analysis/           ← 감정·영상·영화 스타일 분석 결과
├─ character/          ← 주인공 캐릭터 설정 및 프롬프트
├─ storyboard/         ← 생성된 스토리보드 전체
├─ prompts/            ← 씬별 이미지·영상 프롬프트
├─ configs/            ← 파이프라인 동작 규칙 설정 파일 (15개)
├─ data/               ← Suno 이력 및 Config 자동 학습 데이터
├─ output/             ← 파이프라인 실행 결과물 저장소
└─ scripts/            ← 핵심 Python 스크립트
```

---

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

곡 안에서 일관성을 유지하는 주인공 비주얼 아이덴티티를 정의합니다.

| 파일 | 설명 |
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
| `image_prompts/scene_XX_*.md` | 씬별 이미지 프롬프트 (Midjourney, DALL-E 등 사용) |
| `video_prompts/scene_XX_*.md` | 씬별 영상 프롬프트 (Runway, Kling, Pika, Luma, Veo 등 사용) |
| `style_rules.md` | 전체 시리즈에 적용되는 비주얼 스타일 규칙 |

---

### `configs/` — 파이프라인 설정 파일 (15개)

씬 생성 엔진의 동작 규칙을 정의하는 JSON 설정 파일 모음입니다.  
`Config 자동 학습` 버튼으로 `genres.json`과 `atmosphere_rules.json`이 자동 업데이트됩니다.

| 파일 | 설명 |
|---|---|
| `genres.json` | 장르 프로파일 13종 및 스타일 키워드 (현재 1,602개) |
| `color_palette.json` | 장르·분위기 키워드 → 주 색상 매핑 (9개 규칙, 기본값 neon magenta) |
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
| `song_sections.json` | 곡 섹션(Intro/Verse/Chorus 등) 정의 |
| `visual_styles.json` | 비주얼 스타일 프리셋 |
| `character_defaults.json` | 캐릭터 기본값 설정 |

---

### `data/` — 학습 데이터

이 폴더가 파이프라인의 핵심 데이터 자산입니다. `configs/`와 함께 별도로 관리·백업하는 것을 권장합니다.

| 파일 | 설명 |
|---|---|
| `suno_history.jsonl` | Suno 곡 이력 (현재 196곡). 웹 UI의 **가져오기** 버튼과 **Generate Storyboard** 버튼 클릭 시 모두 누적됨 |
| `config_backups/` | Config 자동 학습 적용 시 자동 생성되는 백업 (모든 이력 누적 보관) |

#### 두 수집 경로의 데이터 품질 차이

| 항목 | 가져오기 (suno_import) | Generate Storyboard |
|---|---|---|
| 태그·장르 | Suno 페이지 HTML 파싱 | song_master.json 완전 처리 결과 |
| mood / energy / instruments | 태그에서 추정 (불완전) | 가사 전체 분석 결과 |
| section_structure | 항상 빈 값 | 실제 섹션 구조 [Intro, Verse, Chorus...] |
| Config 자동 학습 기여도 | 장르·분위기 키워드 | 위 항목 모두 + 정확한 섹션 구조 |

> **앱 시작 시 자동 처리:** `suno_import` 항목은 최신 패턴 분석 로직으로 재적용하고 URL 기준 중복 제거합니다. `generate_storyboard` 항목은 song_master.json 기반의 고품질 데이터를 그대로 보존합니다.

---

### `output/` — 실행 결과물

파이프라인이 실행될 때마다 결과물이 저장되는 폴더입니다.

| 경로 | 설명 |
|---|---|
| `output/<노래제목>/` | 웹 UI에서 Generate Storyboard 실행 시 자동 생성 (이미지·영상 프롬프트 파일 저장) |
| `output/storyboard/<slug-timestamp>/` | CLI `--snapshot` 옵션 사용 시 타임스탬프별 스토리보드 전체 패키지 저장 |

---

### `scripts/` — 핵심 스크립트

| 파일 | 역할 |
|---|---|
| `main_entry.py` | EXE 빌드용 진입점. 웹 서버 실행 후 브라우저를 자동으로 엽니다 |
| `web_app.py` | 웹 UI 서버. `run_web.bat`으로 실행. Suno 가져오기·패턴 분석·Config 자동 학습 포함 |
| `song_parser.py` | raw_song.txt·lrc·srt·mp3를 파싱해 `song_master.json` 생성 |
| `emotion_engine.py` | 감정 분석 및 비주얼 월드 생성 |
| `scene_generator.py` | 스토리보드·씬 목록·카메라 연출 생성. 장르별 동적 색상 선택 포함 |
| `image_prompt_generator.py` | 씬별 이미지 프롬프트 생성 |
| `video_prompt_generator.py` | 씬별 영상 프롬프트 생성 |
| `config_learner.py` | Suno 이력을 분석해 `configs/genres.json`·`atmosphere_rules.json` 자동 업데이트 |
| `run_pipeline.py` | 위 단계를 순서대로 일괄 실행하는 엔트리포인트 |
| `common.py` | 공통 경로·유틸리티 함수 |

---

### `build.bat` — EXE 빌드 (선택)

PyInstaller로 독립 실행 파일(.exe)을 생성합니다. 일반 사용 시에는 필요하지 않습니다.

```bat
build.bat
```

---

## Concept

Each song becomes its own emotional cinematic world. Characters may change between songs, but within one song the protagonist identity, hairstyle, outfit, color rules, atmosphere, and visual tone stay consistent.

The visual identity is dynamically generated per song:

- anime cinematic style
- **dominant color selected by genre/mood** — e.g. crimson red for rock, amber gold for jazz, electric blue for k-pop, neon magenta for dark/noir/urban (default)
- dark shadows and near-black backgrounds
- subtle secondary reflections and silver-white rim highlights
- emotional composition tied to lyric content (emotion alignment / affective synchronization)
- 17 mapped emotions: lonely, nostalgic, sad, hopeful, hope, angry, defiant, romantic, longing, anxious, peaceful, excited, bittersweet, fearful, dreamy, tense, and more via aliases
- instrument-driven visual motion hints embedded in every prompt
- soft cinematic lighting and atmospheric environments
- strong silhouettes and film-like framing
- non-photorealistic stylized visuals

---

## Requirements

Python 3.10 or newer is recommended.

No third-party dependencies are required for the core pipeline.

---

## Folder Structure

```text
ai_anime/
├─ input/
│  ├─ raw_song.txt
│  ├─ song_master.json
│  └─ ui_state.json
├─ analysis/
│  ├─ emotion_analysis.json
│  ├─ visual_world.json
│  └─ cinematic_style.json
├─ character/
│  ├─ protagonist_bible.json
│  ├─ character_prompt.md
│  ├─ character_reference_prompt.md
│  └─ character_reference/
├─ storyboard/
│  ├─ scene_list.json
│  ├─ story_arc.json
│  ├─ story_summary.md
│  ├─ storyboard_prompts.md
│  └─ camera_directions.md
├─ prompts/
│  ├─ image_prompts/
│  ├─ video_prompts/
│  └─ style_rules.md
├─ configs/
│  └─ (15개 JSON 설정 파일)
├─ data/
│  ├─ suno_history.jsonl
│  └─ config_backups/
├─ output/
│  ├─ <노래제목>/          ← 웹 UI Generate 결과
│  └─ storyboard/          ← CLI --snapshot 결과
└─ scripts/
   ├─ main_entry.py
   ├─ web_app.py
   ├─ run_pipeline.py
   ├─ song_parser.py
   ├─ emotion_engine.py
   ├─ scene_generator.py
   ├─ image_prompt_generator.py
   ├─ video_prompt_generator.py
   ├─ config_learner.py
   └─ common.py
```

---

## Input Format

Copy the base files for a song into `input/`. The parser scans the folder and builds `input/song_master.json` from the available files.

Supported input files:

- `.txt` for style, metadata, and section lyrics
- `.lrc` for timestamped lyrics
- `.srt` for subtitle-style timestamped lyrics
- Optional audio files (`.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`, `.ogg`) for reference metadata such as duration

If multiple files are present, `raw_song.txt` is used as the primary metadata/section source when available, `.lrc` or `.srt` is used for timed lyrics, and audio files are stored as optional reference metadata.

Supported metadata fields:

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

Supported section labels:

```text
[Intro]
[Verse]
[Pre-Chorus]
[Chorus]
[Post-Chorus]
[Bridge]
[Outro]
```

LRC timestamped lyrics are also recognized when present.

---

## Run the Web UI

```bat
run_web.bat
```

또는:

```powershell
python scripts/web_app.py
```

Then open: `http://127.0.0.1:8000`

웹 UI 주요 기능:

- **가져오기**: Suno URL에서 제목·태그·가사를 자동 추출해 `data/suno_history.jsonl`에 저장
- **Generate Storyboard**: 전체 파이프라인 실행 후 `output/<노래제목>/`에 프롬프트 파일 저장
- **Config 자동 학습**: `suno_history.jsonl` 분석 → `configs/genres.json`·`atmosphere_rules.json` 자동 업데이트
- 씬·이미지 프롬프트·영상 프롬프트·JSON 결과 브라우저에서 바로 확인

---

## Run the Full Pipeline (CLI)

```powershell
python scripts/run_pipeline.py
```

타임스탬프 스냅샷과 함께 실행:

```powershell
python scripts/run_pipeline.py --snapshot
```

커스텀 입력 파일 또는 폴더 지정:

```powershell
python scripts/run_pipeline.py --input input/my_song.txt --snapshot
python scripts/run_pipeline.py --input input --snapshot
```

오디오 분석 힌트 적용:

```powershell
python scripts/run_pipeline.py --input input --apply-audio-analysis --snapshot
```

---

## Run Individual Steps

```powershell
python scripts/song_parser.py --input input
python scripts/emotion_engine.py
python scripts/scene_generator.py
python scripts/image_prompt_generator.py
python scripts/video_prompt_generator.py
python scripts/config_learner.py --dry-run   # 분석만 (파일 변경 없음)
python scripts/config_learner.py             # 분석 후 configs/ 업데이트
```

---

## Pipeline

```text
[Suno URL 가져오기]──────────────────────────────┐
                                                  ↓
                                         suno_history.jsonl
                                                  ↓
                                        [Config 자동 학습]
                                                  ↓
                                        configs/ 업데이트

[RAW MUSIC INPUT (txt/lrc/srt/mp3)]
↓
song_parser.py
↓
song_master.json
↓
emotion_engine.py  ←── emotions.json / emotion_transitions.json
↓
scene_generator.py ←── color_palette.json / character_defaults.json
↓                       genres.json / atmosphere_rules.json
storyboard + scene_list.json
↓
image_prompt_generator.py
↓
video_prompt_generator.py
↓
output/<노래제목>/  (프롬프트 파일)
```

---

## Output

The system creates:

- `input/song_master.json`
- `analysis/emotion_analysis.json`
- `analysis/visual_world.json`
- `analysis/cinematic_style.json`
- `character/protagonist_bible.json`
- `character/character_prompt.md`
- `character/character_reference_prompt.md`
- `storyboard/scene_list.json`
- `storyboard/story_arc.json`
- `storyboard/story_summary.md`
- `storyboard/storyboard_prompts.md`
- `storyboard/camera_directions.md`
- per-scene image prompts (`prompts/image_prompts/`)
- per-scene video prompts for Runway, Kling, Pika, Luma, Veo, Flow, Sora, Hailuo, and PixVerse (`prompts/video_prompts/`)
- `output/<노래제목>/` — 웹 UI Generate Storyboard 실행 시 프롬프트 파일 복사본

---

## Extension Points

Good next modules to add:

- OpenAI API integration for richer lyric interpretation
- image generation adapter
- Runway, Kling, Pika, Luma, Veo, Flow, Sora, Hailuo, or PixVerse export adapters
- reference image management
- prompt scoring and consistency checks
- final edit decision list generation
