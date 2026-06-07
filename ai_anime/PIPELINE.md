# AI Anime MV Builder — 프롬프트 생성 파이프라인 상세 문서

> **최종 수정**: 2026-05-22 (cyber_noir 스타일 제거, 연주 섹션 자동 감지·Scene atmosphere 레이블 처리 추가)  
> **목적**: 프롬프트 생성 과정을 단계별로 정리하여, 수정·개선 시 빠르게 참조할 수 있도록 한다.

---

## 목차

1. [전체 파이프라인 개요](#1-전체-파이프라인-개요)
2. [단계 1 — 입력 파싱 (song_parser.py)](#2-단계-1--입력-파싱-song_parserpy)
3. [단계 2 — 감정 분석 (emotion_engine.py)](#3-단계-2--감정-분석-emotion_enginepy)
4. [단계 3 — 씬 생성 (scene_generator.py)](#4-단계-3--씬-생성-scene_generatorpy)
5. [단계 4 — 이미지 프롬프트 출력 (image_prompt_generator.py)](#5-단계-4--이미지-프롬프트-출력-image_prompt_generatorpy)
6. [단계 5 — 비디오 프롬프트 출력 (video_prompt_generator.py)](#6-단계-5--비디오-프롬프트-출력-video_prompt_generatorpy)
7. [이미지 프롬프트 조립 공식](#7-이미지-프롬프트-조립-공식)
8. [비디오 프롬프트 조립 공식](#8-비디오-프롬프트-조립-공식)
9. [Config 파일 역할 정의](#9-config-파일-역할-정의)
10. [출력 파일 구조](#10-출력-파일-구조)
11. [웹 UI 흐름 (web_app.py)](#11-웹-ui-흐름-web_apppy)
12. [수정·개선 시 참조 체크포인트](#12-수정개선-시-참조-체크포인트)
13. [비주얼 스타일 시스템 상세](#13-비주얼-스타일-시스템-상세)

---

## 1. 전체 파이프라인 개요

```
[입력]
  TXT / LRC / SRT / 오디오 파일
        │
        ▼
┌─────────────────────────────┐
│  단계 1: song_parser.py     │  가사 + 메타데이터 파싱
│  → input/song_master.json  │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│  단계 2: emotion_engine.py  │  감정·시각 매핑
│  → analysis/emotion_        │
│     analysis.json           │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  단계 3: scene_generator.py                 │  비주얼 세계·주인공·씬 생성
│  ① 장르 프로필 → style_id 자동 결정        │  ← 2026-05-15 개선
│  ② 곡별 강조색 (main_color) 결정           │
│  ③ 스타일 초기화 (BRAND_PALETTE)           │
│  ④ 주체 유형/성별 표현 판단              │
│  ⑤ 곡별 캐릭터·오브젝트 고유화 적용      │
│  → analysis/visual_world.json               │
│  → analysis/cinematic_style.json            │
│  → character/protagonist_bible.json         │
│  → character/character_prompt.md            │
│  → character/character_reference_prompt.md  │
│  → storyboard/story_arc.json                │
│  → storyboard/scene_list.json               │
│  → storyboard/story_summary.md              │
│  → storyboard/storyboard_prompts.md         │
│  → storyboard/camera_directions.md          │
└─────────────────────────────────────────────┘
        │
        ├──────────────────────────┐
        ▼                          ▼
┌──────────────────────┐  ┌────────────────────────┐
│ 단계 4:              │  │ 단계 5:                 │
│ image_prompt_        │  │ video_prompt_           │
│ generator.py         │  │ generator.py            │
│ → prompts/           │  │ → prompts/              │
│   image_prompts/     │  │   video_prompts/        │
│   *.md               │  │   *.md                  │
└──────────────────────┘  └────────────────────────┘

[선택] --snapshot 옵션 시 output/storyboard/<slug>-<timestamp>/ 에 전체 복사
```

**핵심 설계 원칙**

- Python 코드 = 순수 실행 엔진 (도메인 규칙 없음)
- 모든 규칙·임계값·매핑 = `configs/*.json`에서 관리
- 외부 의존성 없음 (Python 표준 라이브러리만 사용)
- **각 곡은 장르·무드·스타일에 따라 고유한 비주얼 스타일과 색상을 자동 선택한다**
- **각 곡은 제목·장르·BPM·에너지·무드·섹션 구조로 결정적 캐릭터 또는 주요 오브젝트/배경 주체를 생성한다**
- **명시 무드/시각 단서가 없을 때는 비 오는 도시 기본값을 쓰지 않고, `configs/song_inference.json`의 곡 타입 프로필로 장르·가사·스타일 태그를 해석한다**

---

## 2. 단계 1 — 입력 파싱 (`song_parser.py`)

### 입력

| 파일 형식 | 역할 |
|-----------|------|
| `.txt` | 메타데이터(Genre/BPM/Mood…) + 가사 + 섹션 마커 |
| `.lrc` | 타임스탬프 가사 (타임드 섹션 파싱 우선 사용) |
| `.srt` | 자막 형식 가사 (LRC 없을 때 사용) |
| `.mp3/.wav/…` | 오디오 분석 (duration, 음량, 에너지) |

### 처리 흐름

```
1. discover_input_files()
   └─ 입력 폴더 또는 단일 파일에서 확장자별 파일 목록 수집

2. 텍스트 우선순위: raw_song.txt > *.txt > *.lrc > *.srt

3. extract_metadata(text)
   └─ KEY_ALIASES 딕셔너리로 "Title:", "BPM:", "Mood:" 등을 파싱
   └─ find_style_seed_line()으로 Suno 스타일 시드 라인 추출 (BPM이 포함된 첫 비 메타 라인)
   └─ infer_title_from_text()로 "Cover of" / "artwork" 형식의 Suno 제목 추출

3-1. infer_mood_from_song() / infer_visual_cues_from_song()
   ├─ 명시 Mood/Visual cues가 없으면 `configs/song_inference.json`의 profiles[].keys로 곡 타입 매칭
   ├─ 매칭 프로필의 mood, visual_cues, main_color, season, environment_family를 후속 단계에 전달
   └─ 과거 기본값인 melancholic / empty street / rain / silhouette가 무조건 주입되지 않도록 방지

4. parse_sections(text)
   ├─ SECTION_LABEL_PATTERN 정규식: [Intro], [Verse], [Pre-Chorus], [Chorus], [Bridge], [Outro]
   ├─ 섹션 마커가 있으면 각 마커 아래 가사를 해당 섹션에 배정
   └─ 섹션 마커 없으면 폴백: 가사를 DEFAULT_SECTIONS 수로 균등 분할
      └─ n_sections = min(len(DEFAULT_SECTIONS), len(lyric_lines)) — 가사 줄 수 초과 방지

5. parse_lrc(text) / parse_srt(text)
   └─ 타임스탬프 가사 파싱 → timed_lyrics 리스트

6. sections_from_timed_lyrics()
   └─ timed_lyrics 안에 [Verse] 등 마커가 있으면 섹션 재구성 (LRC 우선)

7. infer_intensity(section, index, total, energy)
   └─ configs/song_sections.json의 intensity_defaults 테이블 참조
   └─ Chorus=high (에너지가 높을 때), Intro=low, Bridge=high, Outro=falling 등

8. structure_sections()
   └─ 각 섹션에 index, name, lyrics, description, intensity, visual_cues 부여

9. 오디오 분석 (ffprobe/ffmpeg 있을 때만)
   ├─ probe_audio_stream(): codec, sample_rate, channels, duration
   ├─ probe_audio_loudness(): mean/max dB
   └─ classify_audio_energy(): high/medium/low 분류
      └─ configs/bpm_thresholds.json의 audio_energy 임계값 참조
```

### 출력: `input/song_master.json` 주요 필드

```json
{
  "title": "곡 제목",
  "genre": "감지된 장르 (style_tags 앞 3개)",
  "bpm": 128,
  "energy": "medium",
  "mood": ["melancholic", "hopeful"],
  "instruments": ["piano", "synth"],
  "style_tags": ["dark pop", "cinematic", "anime"],
  "negative_tags": ["-electric guitar"],
  "visual_cues": ["rain", "neon city"],
  "atmosphere": "urban melancholy",
  "pacing": "medium cinematic pacing",
  "sections": [
    {
      "index": 1,
      "name": "Intro",
      "lyrics": "...",
      "description": "",
      "intensity": "low",
      "visual_cues": ["rain", "neon city"]
    }
  ],
  "timed_lyrics": [{"time": 12.5, "text": "가사 한 줄"}],
  "audio_files": [...],
  "audio_analysis": {...}
}
```

### 수정 포인트

| 항목 | 위치 |
|------|------|
| 섹션 인식 정규식 변경 | `SECTION_LABEL_PATTERN` (line 45) |
| 섹션 별칭 추가 (예: "훅" → "Chorus") | `configs/song_sections.json` > `aliases` |
| 기본 섹션 순서 변경 | `configs/song_sections.json` > `default_sections` |
| 강도 기본값 변경 | `configs/song_sections.json` > `intensity_defaults` |
| 오디오 에너지 임계값 | `configs/bpm_thresholds.json` > `audio_energy` |
| BPM 임계값 (fast/slow) | `configs/bpm_thresholds.json` > `thresholds` |

---

## 3. 단계 2 — 감정 분석 (`emotion_engine.py`)

### 입력

`input/song_master.json`

### 처리 흐름

```
1. choose_primary_emotion(moods)
   ├─ song_master.mood[] 리스트에서 순서대로 시도
   ├─ configs/emotions.json > emotions 에서 직접 매칭
   └─ 없으면 configs/emotions.json > aliases 에서 별칭 매칭
      └─ 예: "melancholic" → "sad", "love" → "romantic"

2. map_emotion(emotion)
   └─ configs/emotions.json > emotions[emotion] 반환
      {symbols, lighting, camera, environment}
      ⚠️ lighting 설명의 색상 참조는 scene_generator 단계에서
         _apply_color()로 곡별 main_color로 치환된다

3. 섹션별 감정 분기 (진행 규칙)
   ├─ Chorus 섹션:
   │   ├─ primary가 chorus_lift 목록에 있으면 → chorus_lift_target (default: "hopeful")
   │   └─ 예외: chorus_lift_exceptions[primary] → 지정 감정
   │   └─ 규칙 출처: configs/emotion_transitions.json
   ├─ Bridge 섹션:
   │   └─ bridge_deepen[primary] → 더 깊은 감정
   └─ Outro 섹션:
       └─ outro_resolve[primary] → 해결 감정 (없으면 outro_resolve_default: "hope")

4. infer_season(song)
   └─ visual_cues + mood를 합쳐서 configs/atmosphere_rules.json > season_rules 매칭

5. infer_urban_rural(song)
   └─ visual_cues에 urban_keywords 포함 여부 → urban_mood / rural_mood 반환
```

### 출력: `analysis/emotion_analysis.json` 주요 필드

```json
{
  "primary_emotion": "sad",
  "secondary_emotions": ["hopeful"],
  "emotional_progression": [
    {
      "section": "Intro",
      "intensity": "low",
      "emotion": "sad",
      "visual_symbols": ["rain on glass", "empty bench"],
      "lighting": "low-key graphite shadows with soft {accent} spill and subtle secondary reflections",
      "environment": "night street or train window",
      "camera_emotion": "close-up profile, slow tilt down"
    },
    {
      "section": "Chorus",
      "emotion": "hopeful",
      ...
    }
  ],
  "visual_symbolism": ["rain on glass", "empty bench", "flickering streetlamp"],
  "emotional_climax": { "section": "Chorus", ... },
  "seasonal_atmosphere": "rainy late spring night",
  "urban_rural_mood": "urban emotional atmosphere",
  "cinematic_pacing": "medium cinematic pacing",
  "tension_curve": ["low", "medium", "high", "high", "medium"]
}
```

### 수정 포인트

| 항목 | 위치 |
|------|------|
| 감정 목록·상징·조명·카메라 추가/변경 | `configs/emotions.json` > `emotions` |
| 감정 별칭 추가 (예: "한" → "longing") | `configs/emotions.json` > `aliases` |
| Chorus에서 감정이 올라가는 규칙 | `configs/emotion_transitions.json` > `chorus_lift_emotions` |
| Chorus 예외 감정 (올리지 않을 것) | `configs/emotion_transitions.json` > `chorus_lift_exceptions` |
| Bridge 깊이 감정 | `configs/emotion_transitions.json` > `bridge_deepen` |
| Outro 해결 감정 | `configs/emotion_transitions.json` > `outro_resolve` |
| 계절 인식 키워드 | `configs/atmosphere_rules.json` > `season_rules` |
| 도시/자연 키워드 | `configs/atmosphere_rules.json` > `urban_keywords` |

---

## 4. 단계 3 — 씬 생성 (`scene_generator.py`)

이 단계가 파이프라인의 핵심이다. 모든 씬의 세부 속성을 결정한다.

### 4-1. 스타일 자동 선택 및 초기화 (2026-05-15 개선)

```
run() 함수 내 실행 순서:

1. song = read_json(song_master.json)            ← 곡 데이터 먼저 로드

2. style_id 결정 (외부에서 지정 없을 때 자동 선택)
   └─ _matched_profile = choose_genre_profile(song)
      └─ style_id = _matched_profile.get("style_id", config_default)
         ┌────────────────────────────────────────────────────────┐
         │ 장르 프로필 → style_id 매핑 (configs/genres.json)       │
         │                                                        │
         │ rhythmic trap-pop anime noir  → urban_noir            │
         │ dreamy synth anime noir       → dreamy_synth          │
         │ high-contrast rock anime noir → rock_edge             │
         │ vivid idol anime pop          → idol_bright           │
         │ intimate acoustic anime noir  → warm_acoustic         │
         │ bright emotional pop anime    → idol_bright           │
         │ soul-infused cinematic anime  → warm_acoustic         │
         │ pastel cyber anime pop        → dreamy_synth          │
         │ quiet ambient anime drift     → dreamy_synth          │
         │ orchestral cinematic anime    → ethereal_dark         │
         │ late-night jazz anime noir    → warm_acoustic         │
         │ vivid urban latin anime       → idol_bright           │
         │ wide-open road anime noir     → warm_acoustic         │
         └────────────────────────────────────────────────────────┘
   └─ 웹 UI에서 style_id를 직접 지정하면 해당 값을 우선 사용

3. select_theme(style_id)
   └─ configs/visual_styles.json > styles[style_id] 로드
      → BRAND_PALETTE 설정:
        base, main_color, shadow_color, secondary_light, highlight,
        secondary_accent, highlight_color_name, palette_rule
      → COLOR_BALANCE_BY_STAGE 설정:
        opening/development/turning point/climax/resolution 별 색상 비율 템플릿
        ({main_color} 플레이스홀더는 나중에 포맷팅)

4. pick_main_color(song)
   └─ genre/tags/mood 텍스트 → configs/color_palette.json > rules 순서 키워드 매칭
      → 예: "ethereal" → "soft violet", "rock" → "crimson red"

5. _inject_song_color(main_color)
   └─ BRAND_PALETTE["main_color"] 를 곡별 고유 색상으로 덮어씀
   └─ visual_identity: _COLOR_SUB 정규식으로 "neon magenta"/"cyber pink" 패턴만 치환
      → 스타일별 고유 identity 문구는 그대로 보존
      (예: warm_acoustic → "intimate acoustic anime with warm luminous palette" 유지)
   └─ palette_rule: main_color를 반영하되 secondary_light, highlight는 스타일별 값 유지
      → 예: warm_acoustic 적용 시 "golden-white and warm cream highlights" 보존
      → 예: rock_edge 적용 시 "sharp white rim highlights" 보존
      (base/shadow_color/secondary_light/highlight 등 나머지 팔레트는 선택된 스타일 유지)
```

**스타일별 기본 팔레트 요약 (6종):**

| style_id | 배경 | 보조광 | 하이라이트 |
|----------|------|--------|-----------|
| `ethereal_dark` | midnight blue | warm silver | pale pearl |
| `warm_acoustic` | deep earth brown | candlelight | golden white |
| `urban_noir` | asphalt gray | cool teal | chrome white |
| `rock_edge` | deep charcoal | white spark | sharp white |
| `idol_bright` | dark navy | rose gold | bright white |
| `dreamy_synth` | deep indigo | soft rose shimmer | cool pearl |

주 강조색(`main_color`)은 스타일 기본값을 출발점으로 하되, 곡별 `pick_main_color()`가 덮어씌운다.

### 4-2. 장르 프로필 선택

```
choose_genre_profile(song)
├─ 1순위: genre 필드만으로 configs/genres.json 프로필 키 매칭
├─ 2순위: genre + style_tags + mood + instruments 전체로 매칭
├─ 3순위: 여기에 lyrics까지 포함한 전체 텍스트로 매칭 (score ≥ 2 필요)
└─ 모두 실패: build_adaptive_default(song)
   └─ BPM + energy 기반 캐릭터 특성 생성
      configs/character_defaults.json > adaptive_identities 참조
      configs/character_defaults.json > hair_rules / outfit_rules
      configs/prop_rules.json > rules (색상 참조는 _apply_color로 치환)
      configs/location_rules.json > rules + fallbacks
   └─ style_id 자동 파생 (에너지 기반):
      fast/high  → urban_noir
      medium     → dreamy_synth
      slow/low   → warm_acoustic

장르 프로필 구조 (configs/genres.json):
{
  "name": "intimate acoustic anime noir",
  "style_id": "warm_acoustic",          ← 2026-05-15 추가: 자동 스타일 선택에 사용
  "keys": ["folk", "acoustic", "piano", ...],
  "identity": "quiet anime storyteller holding one fragile memory close",
  "hair": "soft dark hair with a restrained {main_color} rim glow",
  "outfit": "simple dark cardigan coat, soft shirt layers, worn satchel",
  "silhouette": "gentle compact silhouette with careful hand gestures",
  "prop": "folded handwritten letter with softly glowing cyber pink edges",
  "locations": ["window-lit room above a quiet street", ...],
  "texture": "minimal motion, intimate close framing, quiet dust and rain particles"
}

⚠️ hair/outfit/prop 필드에 "cyber pink" / "neon magenta" 패턴이 있으면
   _apply_color()가 자동으로 곡별 main_color로 치환한다.
```

### 4-3. 비주얼 월드 생성 (`create_visual_world`)

```
입력: song, emotion (emotion_analysis.json)

1. 장르 프로필 결정 (위 4-2 참조)
2. infer_song_motif(song, profile)
   └─ configs/motif_rules.json > rules 키워드 매칭
      결과 문자열에 _apply_color() 적용 (색상 참조 치환)
      없으면: "{colored_prop} recurring as the song's main visual motif"
3. infer_locations(song, profile)
   └─ configs/location_rules.json > rules 키워드 매칭 (word-boundary 옵션)
   └─ 프로필의 locations 추가 (중복 제거)
4. normalize_symbols() - 모티프 + 감정 상징 + visual_cues + prop 합산 최대 8개
5. lighting_language() - BPM 기반 조명 설명 + 프로필 texture + 스타일별 shadow/highlight
   └─ _bpm_lighting_desc: configs/bpm_thresholds.json lighting_desc 로드
      → {main_color} 플레이스홀더를 BRAND_PALETTE.main_color로 포맷팅
   └─ BRAND_PALETTE["shadow_color"]: 스타일별 그림자 색상 사용
      예: warm_acoustic → "deep earth shadow and dark mahogany"
          urban_noir   → "asphalt and dark concrete shadows"
   └─ BRAND_PALETTE["highlight"]: 스타일별 하이라이트 색상 사용
      예: warm_acoustic → "golden-white and warm cream highlights"
          rock_edge    → "sharp white rim highlights"
6. transition_language() - BPM 기반 전환 설명 + 스타일별 보조 강조색
   └─ BRAND_PALETTE["secondary_accent"]: 스타일별 반사 색상 사용
      예: warm_acoustic → "candlelight reflections"
          urban_noir   → "cool teal reflections"
          idol_bright  → "rose gold reflections"

출력 (visual_world.json) 주요 필드:
{
  "song_slug": "my-song-title",
  "visual_identity": "intimate acoustic anime noir within intimate acoustic anime with warm luminous palette",
  "genre_profile": "intimate acoustic anime noir",
  "song_motif": "folded handwritten letter with softly glowing amber gold edges recurring as the song's main visual motif",
  "color_palette": {
    "base": "deep earth brown and dark amber shadow backgrounds",
    "main_color": "amber gold",            ← pick_main_color이 결정한 곡별 색상
    "shadow_color": "deep earth shadow and dark mahogany",
    "secondary_light": "subtle warm candlelight secondary glow",
    "highlight": "golden-white and warm cream highlights",
    "rule": "limited-color acoustic anime palette: ..."
  },
  "accent_color": "amber gold",
  "secondary_accent_color": "candlelight",       ← 스타일별 고유값 (BRAND_PALETTE에서)
  "highlight_color": "golden white",             ← 스타일별 고유값 (BRAND_PALETTE에서)
  "base_palette": "deep earth brown and dark amber shadow backgrounds",
  "core_locations": ["window-lit room above a quiet street", ...],
  "recurring_symbols": [...],
  "lighting_language": "slow breathing amber gold glow with long silver rim fades, soft candlelight film grain, deep earth shadow and dark mahogany, golden-white and warm cream highlights",
  "transition_language": "slow dissolves and lingering match cuts through candle motif, candlelight reflections, and soft candlelight film grain",
  "instrument_hint": "soft weighted motion, keys-timed gentle camera breath; ...",
  "negative_style_rules": ["-electric guitar"]
}
```

### 4-4. 주인공 생성 (`create_protagonist`)

```
입력: song, world

1. 장르 프로필의 identity/hair/outfit/silhouette/prop 사용
2. main_color = BRAND_PALETTE.get("main_color")   ← 곡별 고유 색상
3. infer_subject_profile(song, main_color)
   └─ title/genre/style_tags/mood/instruments/atmosphere/visual_cues 기반 판단
      - subject_type: human_solo / human_duo / group / object_symbol / environment_only
      - gender_presentation: male-presenting / female-presenting / mixed-gender / androgynous / non-human symbolic
   └─ object_symbol/environment_only이면 전신 인간 캐릭터 대신 주요 오브젝트/배경 주체 레퍼런스를 생성
4. song_character_seed(song)
   └─ title + genre + bpm + energy + mood + section names를 결합
5. song_unique_traits(song, main_color)
   └─ configs/character_defaults.json > song_unique_variants에서 결정적 선택
      - face_marks: 얼굴 디테일
      - hair_variants: 헤어 실루엣 변주
      - outfit_accents: 의상 포인트
      - accessories: 액세서리
      - gesture_signatures: 대표 제스처
   └─ 같은 song seed는 항상 같은 조합을 반환하고, 다른 곡은 다른 조합으로 분기
6. _apply_color() 적용 범위 (2026-05-15 확장):
   - hair, outfit: 항상 적용
   - prop: 항상 적용 → colored_prop 변수에 저장
   - required_reference_views의 prop 항목: colored_prop 사용
   → 캐릭터 관련 모든 색상 참조가 곡별 main_color로 치환됨

출력 (protagonist_bible.json) 주요 필드:
{
  "role": "unique protagonist for this song",
  "identity": "quiet anime storyteller holding one fragile memory close, song-specific face detail: ..., signature gesture: ...",
  "age_style": "anime character, stylized and non-photorealistic",
  "hair": "soft dark hair with a restrained amber gold rim glow, one longer side strand crossing the cheek",
  "outfit": "simple dark cardigan coat, soft shirt layers, worn satchel, thin choker with a miniature light bead",
  "silhouette": "gentle compact silhouette with careful hand gestures",
  "emotional_state": "longing, nostalgic, hopeful",
  "signature_prop": "folded handwritten letter with neon edges",    ← prop도 치환됨
  "accent_detail": "... This exact face detail, accessory, and gesture set belong only to '곡 제목'",
  "consistency_rules": [...],       ← 이미지 생성 시 준수할 규칙 (7개)
  "reference_workflow": [...],      ← 제작 순서 안내 (4단계)
  "required_reference_views": [...]  ← 캐릭터 시트 필수 뷰 (7개, prop 항목도 치환됨)
}
```

> 핵심: 장르 프로필은 캐릭터의 큰 방향을 정하고, `song_unique_variants`는 곡별 고유 디테일을 추가한다. 그래서 한 곡 안에서는 캐릭터가 고정되지만, 다른 곡은 같은 장르 프로필을 공유해도 얼굴·헤어·의상·제스처 조합이 달라진다.

### 4-5. 씬 리스트 생성 (`generate_scenes`)

**song_master.sections[]를 순서대로 순회하며 각 씬 결정**

```
각 섹션(section)에 대해 아래 6가지를 결정:

① 위치(Location) — choose_location(section, world, index, used_locations)
   ├─ Outro 등 resolution 섹션: configs/song_sections.json > resolution_location_keywords
   │   해당 키워드가 world.core_locations에 있으면 우선 선택 (새벽/하늘/옥상)
   ├─ 가사+description 텍스트로 configs/location_rules.json > rules 키워드 매칭
   │   (이미 사용된 위치는 건너뜀)
   └─ 폴백: world.core_locations에서 미사용 → 순환

② 액션(Action) — choose_scene_action(section, lyric_idea, protagonist)
   ├─ 섹션별 오버라이드 (configs/song_sections.json > action_overrides):
   │   Intro: music_cue_prefix 매칭 → music_cue_action
   │   Bridge/Outro: hide_keywords/cry_keywords → 특정 행동
   │   Chorus: smile_keywords 매칭 → smile_action
   │   각 섹션의 default_action (Chorus/Bridge/Outro에 설정)
   └─ 일반 키워드: configs/action_rules.json > rules
      → rule["action"]의 {prop} 자리에 signature_prop 치환

③ 상징 포커스(Symbolic Focus) — choose_symbolic_focus(section, world, protagonist)
   └─ configs/focus_rules.json > rules 키워드 매칭
      없으면: world.song_motif 또는 protagonist.signature_prop

④ 샷(Shot) — choose_shot(section, emotion, song)
   ├─ 고정 오버라이드: configs/shot_rules.json > section_overrides (Intro/Bridge/Outro)
   ├─ Chorus + BPM fast: chorus_fast_shot
   ├─ Chorus (일반): chorus_default_shot
   ├─ 거울/반사 키워드: mirror_shot
   ├─ 감정별 샷: emotion_shots[emotion]
   └─ 키워드별 폴백 샷: keyword_shots

⑤ 카메라 무브먼트(Movement) — choose_movement(section, song)
   └─ configs/song_sections.json > movement_patterns[section_name]
      tempo(fast/slow/medium) 기반 분기

⑥ 비디오 리듬(Video Rhythm) — video_rhythm(song, section)
   └─ configs/bpm_thresholds.json > thresholds[tempo].rhythm_desc
      "128 BPM: energetic cuts, camera accents every beat, intensity high"

⑦ 조명(Lighting) — section_emotion["lighting"] (2026-05-15 개선)
   └─ emotion_analysis의 lighting 값을 _apply_color()로 main_color 치환
      → 감정별 조명 설명에서 고정 색상 제거, 곡별 색상으로 교체
```

### 4-6. 스토리 아크 적용 (`apply_story_arc_to_scenes`)

```
각 씬에 story_stage를 부여:
├─ 1번 씬 or Intro → "opening"
├─ 마지막 씬 → "resolution"
├─ Bridge → "climax"
├─ Chorus가 전체의 60% 이상 위치에 있으면 → "climax"
└─ 나머지 → configs/song_sections.json > story_stages[section] (보통 "development")

story_beat_ko: 한국어 스토리 단계 기술 (scene_generator.story_beat_ko())
  opening:      "{section}에서 주인공이 {symbol}을 소개합니다. 행동: {action}."
  development:  "{section}에서 가사의 감정이 행동으로 가시화됩니다: {action}."
  turning point:"{section}에서 리듬과 머뭇거림이 바뀌며 {symbol}이(가) 주인공을 앞으로 이끕니다."
  climax:       "{section}에서 반복된 감정이 정점에 달하며 카메라가 행동을 따라갑니다: {action}."
  resolution:   "{section}에서 {symbol}이(가) 마지막 이미지로 자리잡으며 움직임이 해결로 마무리됩니다."

story_beat_en: 영어 스토리 단계 기술
  opening:     "In the {section}, the protagonist introduces {symbol}; action: {action}."
  development: "In the {section}, the lyric emotion becomes visible through the action: {action}."
  climax:      "In the {section}, the repeated emotion peaks while the camera follows..."
  resolution:  "In the {section}, {symbol} settles into the final image as the motion slows."

추가 필드:
  story_prompt_context: 씬 제작 시 AI에게 제공할 내러티브 맥락 문자열
  continuity_from_previous_ko / continuity_to_next_ko: 연속성 지침

COLOR_BALANCE_BY_STAGE 적용 (2026-05-15 개선):
  story_stage → COLOR_BALANCE_BY_STAGE[stage] 조회
  → {main_color} 플레이스홀더를 BRAND_PALETTE.main_color로 포맷팅 후 프롬프트 삽입
```

---

## 5. 단계 4 — 이미지 프롬프트 출력 (`image_prompt_generator.py`)

### 처리 흐름

```
입력: storyboard/scene_list.json

1. prompts/image_prompts/ 폴더의 기존 *.md 파일 전부 삭제 (새로 생성)

2. character_model_sheet 항목이 있으면:
   → 00_character_turnaround_model_sheet.md 출력
   (scene_generator에서 character_reference_prompt()가 생성한 내용)

3. 각 씬의 image_prompt 필드(이미 scene_list.json에 조립된 상태)를
   scene_01_intro.md, scene_02_verse.md 형식으로 저장
```

### 출력 파일 예시

```
prompts/image_prompts/
  00_character_turnaround_model_sheet.md
  scene_01_intro.md
  scene_02_verse.md
  scene_03_pre_chorus.md
  scene_04_chorus.md
  scene_05_bridge.md
  scene_06_outro.md
```

---

## 6. 단계 5 — 비디오 프롬프트 출력 (`video_prompt_generator.py`)

### 처리 흐름

```
입력: storyboard/scene_list.json

1. prompts/video_prompts/ 폴더의 기존 scene_*.md 파일 삭제

2. 각 씬에 대해 지원 플랫폼(configs/platforms.json)별 섹션을 포함한 마크다운 생성:
   ## Runway
   {video_prompt} {runway_note}
   
   ## Kling
   {video_prompt} {kling_note}
   
   ## Remotion
   [remotion_prompt() 생성 구조화 컴포지션 명세]  ← id=="remotion"이면 별도 함수 호출
   
   ... (총 10개 플랫폼)
   
   ⚠️ configs/platforms.json 로드 실패 시 코드 내 fallback 목록 사용
      fallback에도 Remotion 포함 (runway, kling, pika, luma, sora, remotion)

3. scene_01_intro.md, scene_02_verse.md 형식으로 저장
```

### 지원 플랫폼 (`configs/platforms.json`)

| ID | 표시명 | 특이사항 |
|----|--------|---------|
| runway | Runway | image-to-video, 미세한 움직임 |
| kling | Kling | 캐릭터 일관성 우선 |
| pika | Pika | 짧은 클립, 단순 모션 |
| luma | Luma | 카메라 패스, 뎁스, 패럴랙스 |
| veo | Veo | 최고화질 영화적 모드 |
| flow | Flow | Google Flow/Veo 워크플로우 |
| sora | Sora | 간결한 프롬프트, 시간 연속성 |
| hailuo | Hailuo | 단순 액션, 안정적 아이덴티티 |
| pixverse | PixVerse | image-to-video, 곡별 팔레트 유지 |
| remotion | Remotion | React/Remotion 구현용 컴포지션·레이어·타임라인 명세 |

---

## 7. 이미지 프롬프트 조립 공식

`scene_generator.py`의 `image_prompt()` 함수가 각 씬에 대해 아래 순서로 조립한다.

```
[구성 요소]                         [출처]
─────────────────────────────────────────────────────────────────
① 카메라+장소                        scene.camera_direction + scene.environment
   "{shot_type} in {location}."

② 캐릭터 비주얼                      protagonist의 identity/hair/outfit/silhouette/prop
   "{identity}, {hair}, {outfit}, {silhouette}, holding {prop}."
   (hair, outfit, prop 모두 _apply_color()로 곡별 색상 치환됨)

③ 액션                              scene.scene_action
   "Action: {action}."

④ 가사/분위기                        scene.lyric_visual_idea (앞의 prefix 제거, 최대 220자)
   "Lyric mood: {lyric_idea}."       ← 가사 있는 섹션
   "Scene atmosphere: {idea}."       ← 연주 섹션 (한국어 가사 없음, is_instrumental=True)

⑤ 상징                              scene.symbolic_focus + scene.symbolism[:4]
   "Visual symbol: {focus}; supporting symbols: {sym1}, {sym2}, ..."

⑥ 감정+장르+조명                     scene.emotion + world.genre_profile + scene.lighting
   "{emotion} {genre_profile} mood, {lighting}."
   (lighting은 _apply_color()로 곡별 색상 치환됨)

⑦ 악기 힌트 (있을 때만)              world.instrument_hint
   "Instrument-driven motion: {hint}."

⑧ 팔레트 규칙 + 스테이지 색상 비율    BRAND_PALETTE.palette_rule + COLOR_BALANCE_BY_STAGE[story_stage]
   "{palette_rule}; {color_balance}."
   (color_balance의 {main_color} 플레이스홀더는 실시간 포맷팅)

⑨ 스타일 강제                        configs/visual_styles.json > global_anime_constraints.style_enforcement
   "non-photorealistic anime MV still, stylized and non-photorealistic, ..."

⑩ 스타일 부정                        configs/visual_styles.json > global_anime_constraints.negative_enforcement
   "No text, no watermark, no live action."
─────────────────────────────────────────────────────────────────
```

**실제 출력 예시 (별이 지는 밤 — dark anime pop, soft violet 강조색):**

```
slow zoom into a small detail, then pull back to full isolation in rooftop overlooking city lights.
expressive anime protagonist navigating a wide emotional arc with modern intensity,
soft medium-length dark hair with vibrant soft violet end highlights,
contemporary dark jacket with bold accent trim and clean street shoes,
open natural stance with readable gesture-driven expression,
holding small glowing music token or earphone cord lit in soft violet.
Action: looks slightly past the camera as small glowing music token or earphone cord lit in soft violet
pulses with stored light.
Lyric mood: Verse emotional cue.
Visual symbol: star-shaped light points drifting down around the figure;
supporting symbols: empty window frame, hand reaching toward fading light, distant unanswered signal.
longing bright emotional pop anime mood, muted deep indigo shadows with softened soft violet memory glow
and warm silver highlights.
Instrument-driven motion: soft weighted motion, keys-timed gentle camera breath;
sustained emotional swell, slow arc camera movement; ambient layered depth parallax, wave-like neon light drift.
limited-color idol anime palette: soft violet dominant, dark navy backgrounds, deep purple shadows,
soft rose-gold secondary glow, bright white highlights;
dark navy base with restrained soft violet accent and subtle rose-gold.
non-photorealistic anime MV still, stylized and non-photorealistic, anime cinematic styling, never live-action realism.
No text, no watermark, no live action.
```

---

## 8. 비디오 프롬프트 조립 공식

`scene_generator.py`의 `video_prompt()` 함수가 조립한다.

```
[구성 요소]                         [출처]
─────────────────────────────────────────────────────────────────
① 시작 지시                         고정 텍스트
   "Image-to-video from the attached scene image."

② 캐릭터 유지                        protagonist의 hair/outfit/prop
   "Preserve the character design: {hair}, {outfit}, {prop}."
   (모두 _apply_color()로 곡별 색상 치환됨)

③ 카메라 모션 + 구도 유지             scene.movement + scene.camera_direction
   "Camera motion: {movement}; composition stays {camera_direction}."

④ 시간에 따른 액션                    scene.scene_action
   "Action over time: {action}."

⑤ 음악 타이밍                        scene.video_rhythm (BPM + intensity)
   "Musical timing: {video_rhythm}."

⑥ 악기 힌트 (있을 때만)              world.instrument_hint
   "Instrument-driven motion: {hint}."

⑦ 가사/분위기                        compact_lyric_idea(scene)
   "Lyric mood: {lyric_idea}."       ← 가사 있는 섹션
   "Scene atmosphere: {idea}."       ← 연주 섹션 (is_instrumental=True)

⑧ 분위기 + 상징 모션                  world.lighting_language + scene.symbolic_focus
   "Atmosphere: {lighting_language}; symbolic motion: {symbolic_focus}."
   (lighting_language의 {main_color}는 실시간 포맷팅)

⑨ 팔레트 + 스테이지 색상 비율         BRAND_PALETTE.palette_rule + COLOR_BALANCE_BY_STAGE[story_stage]
   "Palette: {palette_rule}; {color_balance}."
   (color_balance의 {main_color} 플레이스홀더는 실시간 포맷팅)

⑩ 모션·영상 스타일 지시 + 부정        고정 텍스트 + video_negative_enforcement
   "Smooth coherent anime motion, subtle parallax, clean motivated transition at the end.
    Avoid dialogue, heavy lip sync, extra characters, text, and watermark."
   + 플랫폼별 노트 (configs/platforms.json)
─────────────────────────────────────────────────────────────────
```

---

## 9. Config 파일 역할 정의

| 파일 | 역할 | 주요 수정 시나리오 |
|------|------|--------------------|
| `configs/emotions.json` | 감정별 상징·조명·카메라·환경 정의 + 별칭 | 새 감정 추가, 한국어 감정어 별칭 추가 |
| `configs/emotion_transitions.json` | Chorus/Bridge/Outro 감정 변화 규칙 | 클라이맥스 감정 바꾸기 |
| `configs/visual_styles.json` | **6종** 비주얼 스타일 정의 (팔레트, 단계별 색상 비율, 전역 애니메이션 제약) — cyber_noir 제거됨 | 새 스타일 추가, 기존 팔레트 색상 변경 |
| `configs/genres.json` | 장르 프로필 (캐릭터 외형, 소품, 위치, 텍스처, **style_id**) | 새 장르 프로필 추가 |
| `configs/color_palette.json` | 키워드→강조색 매핑, 기본색 | 장르별 색상 규칙 추가 |
| `configs/bpm_thresholds.json` | BPM 임계값, 조명/전환/리듬 설명 (`{main_color}` 플레이스홀더 사용) | BPM 구분 기준 변경 |
| `configs/song_sections.json` | 기본 섹션 목록, 강도, 스테이지, 무브먼트, 액션 오버라이드 | Chorus/Bridge 무브먼트 패턴 변경 |
| `configs/location_rules.json` | 키워드→위치 매핑, 폴백 위치 | 새 위치 규칙 추가 |
| `configs/action_rules.json` | 키워드→액션 매핑, 기본 액션 | 새 액션 패턴 추가 |
| `configs/focus_rules.json` | 키워드→상징 포커스 매핑 | 상징 포커스 규칙 추가 |
| `configs/motif_rules.json` | 키워드→모티프 매핑 | 장르별 반복 상징 추가 |
| `configs/shot_rules.json` | 섹션·감정·키워드→샷 타입 매핑 | 새 샷 타입 추가 |
| `configs/prop_rules.json` | 키워드→소품 매핑, 기본 소품 | 새 소품 규칙 추가 |
| `configs/character_defaults.json` | 폴백 캐릭터 외형 + 곡별 고유 변주(face/hair/outfit/accessory/gesture) | 기본 캐릭터 느낌 또는 곡별 변주 폭 변경 |
| `configs/atmosphere_rules.json` | 계절 규칙, 도시 키워드 | 계절·공간 인식 키워드 추가 |
| `configs/platforms.json` | 영상 플랫폼 목록·표시명·노트 | 새 플랫폼 추가, 노트 수정 |

---

## 10. 출력 파일 구조

```
ai_anime/
├── input/
│   ├── song_master.json          ← 파싱 결과
│   ├── raw_song.txt              ← 마지막으로 입력된 가사 (웹 UI용)
│   └── ui_state.json             ← 웹 UI 상태 저장
│
├── analysis/
│   ├── emotion_analysis.json     ← 감정 분석 결과
│   ├── visual_world.json         ← 비주얼 월드 (곡별 스타일·색상 포함)
│   └── cinematic_style.json      ← 카메라·팔레트 요약
│
├── character/
│   ├── protagonist_bible.json    ← 주인공 전체 정의 (곡별 색상 치환 완료)
│   ├── character_prompt.md       ← 이미지 생성용 캐릭터 프롬프트
│   └── character_reference_prompt.md  ← 턴어라운드 모델 시트 프롬프트
│
├── storyboard/
│   ├── scene_list.json           ← 모든 씬 + 이미지/비디오 프롬프트 통합
│   ├── story_arc.json            ← 스토리 구조
│   ├── story_summary.md          ← 스토리 요약 + 제작 순서
│   ├── storyboard_prompts.md     ← 씬별 전체 프롬프트 마크다운
│   └── camera_directions.md     ← 씬별 카메라 방향 요약
│
├── prompts/
│   ├── style_rules.md            ← 장르 중립적 스타일 가이드 (정적 참조용)
│   ├── image_prompts/
│   │   ├── 00_character_turnaround_model_sheet.md
│   │   ├── scene_01_intro.md
│   │   └── scene_0N_*.md
│   └── video_prompts/
│       ├── scene_01_intro.md     ← 10개 플랫폼 섹션 포함
│       └── scene_0N_*.md
│
└── output/
    ├── storyboard/
    │   └── <slug>-<timestamp>/   ← --snapshot 옵션 시 전체 복사본
    ├── <곡제목>/                  ← 웹 UI Generate 시 프롬프트 복사본
    │   ├── character_reference_prompt.md
    │   ├── image_prompts/
    │   └── video_prompts/
    └── web_inputs/
        └── <timestamp>/          ← 웹 UI 업로드 임시 파일
```

---

## 11. 웹 UI 흐름 (`web_app.py`)

### 요청 흐름

```
GET /          → render_form() 빈 폼
GET /results   → render_results() 최근 결과 표시

POST /generate
├─ _parse_form(rfile, headers)     ← cgi.FieldStorage 대체 커스텀 파서
│   multipart/form-data 파싱
├─ with _generate_lock:            ← 동시 요청 직렬화 (스레드 안전)
│   generate_from_form(form)
│   ├─ 업로드 파일 → output/web_inputs/<timestamp>/ 에 저장
│   ├─ 가사 텍스트 → raw_song.txt에도 저장 (UI 재표시용)
│   ├─ song_parser.run()
│   ├─ emotion_engine.run()
│   ├─ scene_generator.run(style_id=style_id)
│   │   └─ style_id가 None이면 장르 프로필에서 자동 선택
│   ├─ image_prompt_generator.run()
│   ├─ video_prompt_generator.run()
│   ├─ save_generate_to_history(song)  ← suno_history.jsonl에 기록
│   └─ save_prompts_to_song_dir()     ← output/<곡제목>/ 에 복사
└─ render_results() 리다이렉트 없이 결과 렌더링

GET /api/import_suno?url=...
└─ fetch_suno_metadata(url)        ← timeout=10초
   Suno HTML에서 title/tags/lyrics 추출
   → save_to_suno_history()

GET /api/config_learn  (dry_run=True)
POST /api/config_learn (dry_run=False)
└─ config_learner.run()
   suno_history.jsonl 분석 → configs/genres.json, atmosphere_rules.json 업데이트
```

### 웹 UI 스타일 선택

```html
<select name="style_id">
  <!-- configs/visual_styles.json > styles 의 모든 키가 옵션으로 나열 -->
  <option value="">자동 선택 (장르 기반)</option>   ← 기본값: 자동
  <option value="ethereal_dark">Ethereal Dark Cinematic</option>
  <option value="warm_acoustic">Warm Acoustic Intimate</option>
  <option value="urban_noir">Urban Street Noir</option>
  <option value="rock_edge">Rock Edge High Contrast</option>
  <option value="idol_bright">Vivid Idol Anime Pop</option>
  <option value="dreamy_synth">Dreamy Synth Atmospheric</option>
</select>
```

- 빈 값(자동)이면 `scene_generator.run(style_id=None)` → 장르 프로필의 `style_id` 자동 사용  
- 특정 스타일을 선택하면 장르와 무관하게 해당 스타일 강제 적용

---

## 12. 수정·개선 시 참조 체크포인트

### A. 새 감정 추가

1. `configs/emotions.json` > `emotions` 에 새 항목 추가 (symbols/lighting/camera/environment)
2. 필요 시 `configs/emotions.json` > `aliases` 에 한국어·동의어 추가
3. `configs/emotion_transitions.json` 에서 Chorus/Bridge 분기 처리 검토
4. `lighting` 값에 색상 고정값을 쓰지 않도록 주의 — 색상 교체는 `_apply_color()`가 담당

### B. 새 장르 프로필 추가

1. `configs/genres.json` 에 새 오브젝트 추가
   ```json
   {
     "name": "새 장르 프로필 이름",
     "style_id": "어울리는_스타일_id",   ← 필수: 자동 스타일 선택에 사용
     "keys": ["키워드1", "키워드2", ...],
     "identity": "캐릭터 정체성",
     "hair": "헤어 설명 (cyber pink 대신 {main_color} 또는 제거)",
     "outfit": "의상 설명",
     "silhouette": "실루엣 설명",
     "prop": "소품 설명 (cyber pink 대신 {main_color} 또는 제거)",
     "locations": ["위치1", "위치2"],
     "texture": "텍스처 설명"
   }
   ```
2. `style_id`는 `configs/visual_styles.json` > `styles` 의 키 중 하나여야 한다
3. hair/outfit/prop에 색상을 쓸 경우 `cyber pink` / `neon magenta` 패턴을 사용하면 `_apply_color()`가 곡별 색상으로 자동 치환한다

### C. 곡별 캐릭터 변주 조정

1. `configs/character_defaults.json` > `song_unique_variants` 에서 선택지를 조정한다
   - `face_marks`: 얼굴 고유점
   - `hair_variants`: 헤어 실루엣 변주
   - `outfit_accents`: 의상 포인트
   - `accessories`: 액세서리
   - `gesture_signatures`: 대표 제스처
2. 선택은 `song_character_seed()` 기반으로 결정된다
   - seed 구성: title, genre, bpm, energy, mood, section names
   - 같은 곡은 같은 조합, 다른 곡은 다른 조합을 목표로 한다
3. 새 선택지에 색상을 넣어야 하면 `{main_color}` 플레이스홀더를 사용한다
4. 장르 자체의 큰 캐릭터 방향은 `configs/genres.json`, 곡별 미세 차이는 `song_unique_variants`에서 관리한다

### D. 새 비주얼 스타일 추가

1. `configs/visual_styles.json` > `styles` 에 새 스타일 키 추가
   ```json
   "new_style_id": {
     "name": "스타일 표시명",
     "brand_palette": {
       "visual_identity": "...",
       "base": "배경 색상",
       "main_color": "기본 강조색 (pick_main_color()가 덮어씀)",
       "shadow_color": "그림자 색상",
       "secondary_light": "보조광 색상",
       "highlight": "하이라이트 색상",
       "secondary_accent": "보조 강조색 (visual_world.secondary_accent_color로 노출)",
       "highlight_color_name": "하이라이트 이름 (visual_world.highlight_color로 노출)",
       "palette_rule": "limited-color ... palette: ..."
     },
     "color_balance_by_stage": {
       "opening": "... {main_color} glow ...",     ← {main_color} 플레이스홀더 사용
       "development": "... {main_color} ...",
       "turning point": "... {main_color} ...",
       "climax": "... {main_color} ...",
       "resolution": "... {main_color} ..."
     }
   }
   ```
2. 새 스타일을 쓸 장르 프로필에 `"style_id": "new_style_id"` 추가
3. 웹 UI 스타일 드롭다운에서 자동으로 나타남

### E. 씬 수 변경 (예: 8씬으로 확장)

1. `configs/song_sections.json` > `default_sections` 목록 수정
2. `story_stages`, `climax_position_ratio` 재검토
3. `movement_patterns` 에 새 섹션명의 패턴 추가

### F. 이미지 프롬프트 내용 변경

- **카메라/샷 타입 변경** → `configs/shot_rules.json`
- **액션 변경** → `configs/action_rules.json` + `configs/song_sections.json > action_overrides`
- **위치 변경** → `configs/location_rules.json`
- **상징 포커스 변경** → `configs/focus_rules.json`
- **스타일 강제/부정 문구 변경** → `configs/visual_styles.json > global_anime_constraints`
- **팔레트 문구 변경** → `configs/visual_styles.json > styles[id].brand_palette.palette_rule`
- **색상 비율 변경** → `configs/visual_styles.json > styles[id].color_balance_by_stage`

### G. 비디오 프롬프트 플랫폼 추가/수정

1. `configs/platforms.json` > `platforms` 에 새 항목 추가
   - `id`, `display_name`, `note`
2. `video_prompt_generator.py`는 자동으로 로드
3. Remotion 특수 처리: `id == "remotion"` 이면 `remotion_prompt()` 호출 → 산문 대신 구조화 컴포지션 명세 출력
4. platforms.json 로드 실패 대비 fallback 목록도 `video_prompt_generator.py` 상단에 있음 — 새 플랫폼 추가 시 양쪽 모두 수정

### H. 음악 플랫폼 변경 (Suno → 다른 서비스)

1. `scripts/web_app.py` > `fetch_suno_metadata()` 수정 (HTML 파싱 로직)
2. `scripts/web_app.py` > `importSuno()` JavaScript 함수 수정 (UI)
3. `scripts/config_learner.py` > `HISTORY_FILE` 경로 및 이력 스키마 검토

### I. 새 비주얼 규칙 Config 추가

1. `configs/` 에 새 JSON 파일 생성
2. `scripts/scene_generator.py` 상단의 Config 로딩 블록에 추가:
   ```python
   _NEW_CONFIG = load_config("new_config_name")
   ```
3. 해당 데이터를 사용할 함수 작성 (키워드 매칭 패턴은 기존 함수 참조)

---

## 13. 비주얼 스타일 시스템 상세

### 색상 결정 파이프라인 (2026-05-15 완성)

```
곡 입력
  │
  ├─ choose_genre_profile(song)
  │   ├─ 1·2·3순위 매칭 시: 프로필의 style_id 사용
  │   └─ 매칭 실패 시: build_adaptive_default(song)
  │       └─ energy_group으로 style_id 자동 파생
  │           fast/high → urban_noir
  │           medium    → dreamy_synth
  │           slow/low  → warm_acoustic
  │
  ├─ select_theme(style_id)
  │   └─ BRAND_PALETTE = styles[style_id].brand_palette
  │      COLOR_BALANCE_BY_STAGE = styles[style_id].color_balance_by_stage
  │      스타일별 독립 값: shadow_color, secondary_light, highlight,
  │                       secondary_accent, highlight_color_name
  │
  ├─ pick_main_color(song)          ← configs/color_palette.json 키워드 매칭
  │   → 곡별 고유 강조색 (예: "soft violet", "crimson red", "amber gold")
  │   └─ _inject_song_color(main_color)
  │       ├─ BRAND_PALETTE["main_color"] = main_color
  │       ├─ BRAND_PALETTE["visual_identity"]: "neon magenta"/"cyber pink" 패턴만 치환
  │       │   → 스타일별 identity 문구 보존
  │       └─ BRAND_PALETTE["palette_rule"]: main_color 반영 +
  │           BRAND_PALETTE["secondary_light"] + BRAND_PALETTE["highlight"] 보존
  │           → 스타일별 하이라이트/보조광 문구 유지
  │
  ├─ lighting_language(song, profile)
  │   ├─ BPM 기반 조명 설명 (_bpm_lighting_desc)
  │   ├─ BRAND_PALETTE["shadow_color"]: 스타일별 그림자
  │   └─ BRAND_PALETTE["highlight"]: 스타일별 하이라이트
  │
  ├─ transition_language(song, profile, motif)
  │   ├─ BPM 기반 전환 설명
  │   └─ BRAND_PALETTE["secondary_accent"]: 스타일별 반사 색상
  │       warm_acoustic → "candlelight reflections"
  │       urban_noir    → "cool teal reflections"
  │
  └─ 프롬프트 생성 시
      ├─ _apply_color(text, main_color)
      │   └─ "neon magenta", "cyber pink", "cyber-pink" 패턴 → main_color로 치환
      │      적용: hair, outfit, prop, lighting, motif
      └─ COLOR_BALANCE_BY_STAGE[stage].format(main_color=main_color)
          └─ {main_color} 플레이스홀더 → 실제 색상으로 치환
```

### 곡별 색상 결정 규칙 (`configs/color_palette.json`)

| 키워드 | 강조색 |
|--------|--------|
| rock, punk, metal, aggressive | crimson red |
| jazz, blues, vintage, folk, funk | amber gold |
| romantic, love, tender, sweet | rose gold |
| dreamy, ethereal, mystic, fantasy | soft violet |
| nature, acoustic, forest, calm | jade green |
| pop, happy, dance, k-pop | electric blue |
| warm, summer, sunset, tropical | coral orange |
| ocean, rain, cold, winter, snow | teal cyan |
| dark, noir, cyber, night, neon | neon magenta |

### 스타일 선택 예시

| 곡 정보 | 매칭 장르 프로필 | 자동 선택 스타일 | 파생 main_color |
|---------|----------------|----------------|----------------|
| dark anime pop, ethereal ballad | bright emotional pop anime | idol_bright | soft violet |
| melodic pop rock indie hip-hop | rhythmic trap-pop anime noir | urban_noir | crimson red |
| piano, strings, nostalgic ballad | intimate acoustic anime noir | warm_acoustic | amber gold |
| synth, dreamy, ambient | dreamy synth anime noir | dreamy_synth | soft violet |
| k-pop, idol | vivid idol anime pop | idol_bright | electric blue |
| orchestral, cinematic | orchestral cinematic anime | ethereal_dark | soft violet |
| guitar, indie rock | high-contrast rock anime noir | rock_edge | crimson red |

---

## 부록 — 주요 함수 → 데이터 흐름 요약

```
song_parser.py
  extract_metadata()       → song.genre/bpm/mood/instruments/style_tags/negative_tags
  parse_sections()         → song.sections[]
  infer_intensity()        → section.intensity
  build_song_master()      → song_master.json 전체

emotion_engine.py
  choose_primary_emotion() → emotion_analysis.primary_emotion
  map_emotion()            → 각 섹션의 symbols/lighting/camera/environment
  analyze_song()           → emotion_analysis.json 전체

scene_generator.py
  choose_genre_profile()   → 캐릭터 외형/소품/위치 프로필 + style_id
  select_theme(style_id)   → BRAND_PALETTE, COLOR_BALANCE_BY_STAGE (전역)
  pick_main_color()        → 곡별 강조색 결정
  _inject_song_color()     → BRAND_PALETTE.main_color 덮어씀
  _apply_color(text, color)→ "cyber pink"/"neon magenta" 패턴 → main_color 치환
  create_visual_world()    → visual_world.json
  song_character_seed()    → title/genre/bpm/energy/mood/sections 기반 고유 시드
  infer_subject_profile()  → human/object/environment + gender_presentation 판단
  song_unique_traits()     → 곡별 face/hair/outfit/accessory/gesture 결정
  create_protagonist()     → protagonist_bible.json (곡별 변주 + hair/outfit/prop 색상 치환)
  infer_song_motif()       → 모티프 문자열 (색상 치환 적용)
  _is_instrumental_section()→ 한국어 가사 없으면 연주 섹션으로 판정
  _instrumental_visual_atmosphere() → 뮤지컬 키워드 → 시각 분위기 문자열
  infer_lyric_idea()       → 가사 섹션: "lyric cue:…" / 연주 섹션: "scene atmosphere:…"
  generate_scenes()        → 씬별 6가지 요소 결정 + is_instrumental 플래그 포함
  apply_story_arc_to_scenes() → 씬별 story_stage/story_beat 추가
  image_prompt()           → "Lyric mood:" (가사) 또는 "Scene atmosphere:" (연주) 레이블 선택
  video_prompt()           → 동일 레이블 분기 적용
  _generate_and_write()    → 모든 JSON/MD 파일 저장

image_prompt_generator.py
  run()                    → prompts/image_prompts/*.md 저장

video_prompt_generator.py
  run()                    → prompts/video_prompts/*.md 저장 (플랫폼별 섹션 포함)
```
