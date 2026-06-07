# AI Anime MV Builder — Claude Code 작업 지침

> 이 파일은 Claude Code가 이 프로젝트에서 작업할 때 항상 자동으로 로드됩니다.
> 모든 소스 수정·추가 시 아래 규칙을 **반드시** 준수하십시오.

---

## 핵심 설계 원칙 — 절대 원칙

### 음악은 항상 다양하다. 프롬프트에 고정값이 있어서는 안 된다.

이 파이프라인이 처리하는 곡은 장르·BPM·감정·분위기·언어가 모두 다르다.  
**어떤 코드도 특정 색상·스타일·감정·언어를 하드코딩해서는 안 된다.**

```
금지 예시:
  ❌ "neon magenta" 색상을 문자열 리터럴로 출력
  ❌ "cyber noir" 스타일을 특정 장르에 고정
  ❌ "rain on glass", "empty bench" 등 특정 상징을 기본값으로 강제
  ❌ 감정 조명 설명에 특정 색상 이름을 직접 포함
  ❌ "medium close-up" 같은 카메라 샷을 특정 섹션에 고정

허용 예시:
  ✅ BRAND_PALETTE.get("main_color", "accent color") — 항상 팔레트에서 참조
  ✅ _apply_color(text, main_color) — 색상 토큰을 곡별 색상으로 치환
  ✅ configs/*.json 에서 키워드 매칭으로 값 결정
  ✅ {main_color} 플레이스홀더를 포맷팅으로 채우기
```

**Python 스크립트는 순수 실행 엔진이다. 모든 규칙과 값은 `configs/*.json`에 있다.**

---

## 오류 수정·개선 후 전체 소스 검증 — 필수 절차

> **소스 수정 또는 개선이 완료된 직후 반드시 아래 두 단계를 모두 실행해야 한다.**  
> 어느 하나라도 실패하면 작업이 완료된 것이 아니다.

### Step 1 — 전체 파이프라인 + 프롬프트 품질 검증

```bash
python __validate_all.py
```

- 26곡 전체를 파이프라인 재실행 후 출력 프롬프트를 검증한다
- 확인 항목: RAW COLOR 잔존, Kling 단어수·마침표, Sora 5섹션, Wan Negative prompt
- **PASS 26곡 / FAIL 0곡이 되어야 작업 완료**

### Step 2 — Regression 검증

```bash
python scripts/run_regression.py
```

- 29개 픽스처 (26곡 + byeol_jineun_bam + 100-seconds + heojin_nal) 전체 통과 여부를 확인한다
- 확인 항목: BPM, energy, genre_profile, timing_mode, scene_count, sections, main_color, no_duplicate_cameras, no_raw_palette_in_lighting
- **29 passed / 0 failed이 되어야 작업 완료**

> **픽스처 업데이트가 필요한 경우**: 의도적인 동작 변경으로 기대값이 달라졌을 때만  
> `python scripts/build_all_fixtures.py --overwrite` 로 재생성한 뒤 변경 내용이 올바른지 직접 확인 후 사용한다.

---

## 소스 수정·추가 시 반드시 확인하는 체크리스트

### 1. 색상 관련 수정

코드 어디서든 색상값을 다룰 때:

- [ ] `BRAND_PALETTE.get("main_color")` 를 통해 참조하는가?
- [ ] `_apply_color(text, main_color)` 로 `"neon magenta"` / `"cyber pink"` 패턴을 치환하는가?
- [ ] `_apply_full_palette(text)` 로 ambient 색상 4종 (`neon magenta`, `deep plum`, `icy cyan`, `silver-white`)을 모두 치환하는가?
- [ ] `emotions.json` 의 lighting 설명에 특정 색상 이름을 직접 쓰지 않았는가?
- [ ] `genres.json` 의 `hair` / `outfit` / `prop` / `texture` 필드에 색상이 필요하면 `cyber pink` 또는 `neon magenta` 패턴을 사용했는가? (→ `_apply_color()`가 자동 치환)
- [ ] 새 config 필드에 `{main_color}` 플레이스홀더가 필요한 경우 `.format(main_color=...)` 을 반드시 적용했는가?

### 2. ambient 팔레트 치환 시스템 (`scene_generator.py`)

현재 4개의 치환 패턴이 있다. 새 ambient 색상 토큰이 config에 추가되면 패턴도 함께 추가해야 한다.

```python
_COLOR_SUB           → "neon magenta" / "cyber pink"   → main_color
_PALETTE_SHADOW_SUB  → "deep plum (and dark violet)"   → BRAND_PALETTE["shadow_color"]
_PALETTE_SECONDARY_SUB → 수식어? + "icy cyan" + 후행명사?  → BRAND_PALETTE["secondary_light"]
_PALETTE_HIGHLIGHT_SUB → "silver-white ..." / "silver rim ..." → BRAND_PALETTE["highlight"]
```

`_PALETTE_SECONDARY_SUB` 는 주변 수식어(`subtle/faint/minimal` 등)와 후행 명사(`reflections/edge light/fringe` 등)까지 통째로 매칭한다.  
새 ambient 색상이 config나 emotions.json 에 추가되면 대응 패턴을 추가하고 `_apply_full_palette()` 에도 포함시켜야 한다.

### 3. `emotions.json` 수정

- [ ] lighting 설명에 `neon magenta`, `cyber pink`, `cyber-pink` 를 직접 쓰는 것은 허용 (→ `_apply_color()` 가 치환)
- [ ] `icy cyan`, `deep plum`, `silver-white` 은 cyber_noir 전용 ambient 색상 — 이미 치환 패턴 있음
- [ ] **새로운 ambient 색상을 추가할 경우** `_PALETTE_*_SUB` 패턴과 `_apply_full_palette()` 를 함께 추가해야 한다

### 4. `genres.json` 수정

- [ ] 새 장르 프로필의 `prop` / `hair` / `texture` 에 색상이 포함될 경우: `cyber pink` 또는 `neon magenta` 사용 → `_apply_color()` 자동 치환
- [ ] "neon reflections" 처럼 수식어 없이 단독으로 쓰면 `_COLOR_SUB` 가 잡지 못한다 → `"neon magenta reflections"` 로 써야 한다
- [ ] 새 프로필에 `"style_id"` 가 있는가? → 자동 스타일 선택에 필수

### 4-1. `genre_reference_profiles.json` 수정

- [ ] 분류 키워드는 추가하지 않았는가? 분류는 계속 `genres.json`이 담당한다.
- [ ] 출처는 공개 기관 자료이며 `sources`에 URL과 사용 근거가 기록되어 있는가?
- [ ] 생성용 필드에 기관명·아티스트명·작품명·고유 무대명이 들어가지 않았는가?
- [ ] 얼굴·로고·정확한 의상·시그니처 소품·정확한 무대 복제를 금지하는가?
- [ ] 기존 20개 장르 프로필이 모두 한 계열에 매핑되는지 단위 테스트가 통과하는가?
- [ ] 새 계열 추가 시 장소·카메라·움직임·전환·조명·캐릭터·회피 항목이 모두 있는가?

### 5. `config_learner.py` — 이력 중복 제거 수정 시

`suno_history.jsonl` 항목의 고유 키는 **3단계 복합 키**로 결정된다.

```
1순위: url        (Suno URL, 비어있지 않으면 사용)
2순위: audio_hash (SHA256 of uploaded MP3/WAV bytes)
3순위: content_fp (SHA256(title.lower() + "|" + raw_tags[:200]))
```

- [ ] `dedupe_by_url()` 는 `dedupe_composite()` 의 래퍼 — 직접 수정하지 말 것
- [ ] 새 항목 저장 시 MP3 경로가 있으면 `audio_hash` 필드 기록 (`_audio_file_hash()` 사용)
- [ ] `backfill_history_patterns()` 는 **서버 시작 시 자동 실행 금지** — 명시적 호출로만

### 6. 플랫폼 특화 포맷 (`video_prompt_generator.py`)

각 플랫폼의 공식 가이드 규칙을 확인하고 수정한다.

| 플랫폼 | 필수 규칙 | 확인 항목 |
|--------|-----------|----------|
| **Kling** | 40–60 단어, 완전한 문장으로 종료, 동작 결말 필수 | 단어수 ≤ 65, `ends with "."`, 결말 트리거 존재 |
| **Sora** | 5섹션: Scene / Cinematography / Actions / Style / Sound | 5개 섹션 모두 출력 |
| **Runway** | `[camera_type]:` 로 시작 | `camera:` 앞 선행 |
| **Pika** | `-camera -motion -fps -neg` 파라미터 구문 | 플래그 블록 존재 |
| **Wan 2.1** | shot + scene + motion + camera + style 구조, neg 필수 | Negative prompt 블록 존재 |
| **Remotion** | React/Remotion 구현 명세 (산문 비디오 프롬프트 아님) | `remotion_prompt()` 함수 호출 |

### 6. 검증 자동화 — 수정 후 반드시 실행

```python
# 씬 리스트 검증
# - neon magenta / cyber pink 잔존 여부
# - 이중 단어 (subtle subtle, reflections reflections 등)
python -c "
import json, re, os
with open('storyboard/scene_list.json', encoding='utf-8') as f:
    data = json.load(f)
issues = []
for s in data.get('scenes', []):
    lighting = s.get('lighting', '')
    if 'neon magenta' in lighting.lower() or 'cyber pink' in lighting.lower():
        issues.append(f'Sc{s[\"scene_number\"]:02d}: RAW COLOR in lighting')
    m = re.search(r'(\b\w+\b) \1\b', lighting)
    if m: issues.append(f'Sc{s[\"scene_number\"]:02d}: DOUBLE WORD [{m.group(0)}]')
print('Issues:', issues if issues else 'none')
"

# 비디오 프롬프트 검증
python -c "
import re, os
video_dir = 'prompts/video_prompts'
for fname in sorted(os.listdir(video_dir)):
    with open(f'{video_dir}/{fname}', encoding='utf-8') as f:
        content = f.read()
    # Kling
    m = re.search(r'## Kling AI\n(.*?)\n\n>', content, re.DOTALL)
    if m:
        k = m.group(1).strip()
        wc = len(k.split())
        ok = wc <= 65 and k.endswith('.') and any(t in k.lower() for t in ('settles','stillness','returns to','fades','comes to rest'))
        if not ok: print(f'Kling FAIL {fname}: {wc}w')
    # Sora
    for sec in ['**Scene:**','**Cinematography:**','**Actions:**','**Style:**','**Sound:**']:
        if sec not in content: print(f'Sora missing {sec} in {fname}')
print('done')
"
```

---

## 파이프라인 구조 요약

```
song_parser.py          → input/song_master.json
emotion_engine.py       → analysis/emotion_analysis.json
scene_generator.py      → storyboard/ + character/ + analysis/
image_prompt_generator.py → prompts/image_prompts/*.md  (6 image platforms)
video_prompt_generator.py → prompts/video_prompts/*.md  (11 video platforms)
```

전체 파이프라인: `python scripts/run_pipeline.py`

---

## 색상 결정 파이프라인 (코드 수정 시 참조)

```
곡 입력
  │
  ├─ choose_genre_profile()  → genre 프로필 + style_id
  ├─ select_theme(style_id)  → BRAND_PALETTE (shadow/secondary/highlight 모두 스타일별 고유값)
  ├─ pick_main_color()       → 곡별 강조색 (color_palette.json 키워드 매칭)
  └─ _inject_song_color()    → BRAND_PALETTE["main_color"] 덮어씀

프롬프트 생성 시:
  _apply_color(text, main_color)     → neon magenta / cyber pink → main_color
  _apply_full_palette(text)          → main_color + shadow + secondary + highlight 모두 치환
  .format(main_color=main_color)     → {main_color} 플레이스홀더 채우기
```

---

## 자주 발생한 버그 패턴 (재발 방지)

| 버그 | 원인 | 수정 방법 |
|------|------|----------|
| "subtle subtle icy cyan..." 이중 단어 | `_PALETTE_SECONDARY_SUB` 가 "icy cyan" 만 치환해 앞 수식어·뒤 명사 중복 | 패턴을 넓혀 주변 수식어+후행명사까지 통째로 매칭 |
| 감정 조명에 "neon magenta" 잔존 | `_apply_color()` 만 적용하고 `_apply_full_palette()` 를 누락 | `generate_scenes()` 내 lighting 필드에 `_apply_full_palette()` 사용 |
| `profile['texture']` 에 "neon" 잔존 | `lighting_language()` / `transition_language()` 에서 texture 를 그대로 출력 | `_apply_color(profile['texture'], main_color)` 로 감싸기 |
| Kling 프롬프트 문장 중간 절단 | `video_prompt` 전체를 60단어로 자르면 중간 절단 | 씬 필드로 compact body 재구성 후 마지막 `.` 위치에서 트리밍 |
| Sora Sound 섹션 누락 | 코드가 4섹션만 출력 | `**Sound:**` 섹션 추가 (BPM + lyric cue 활용) |
| genres.json "neon reflections" 미치환 | `_COLOR_SUB` 는 "neon magenta" 전체 패턴만 인식 | `"neon magenta reflections"` 으로 명시해야 치환됨 |
| `movement` 필드에 "neon atmosphere" 잔존 | `choose_movement()` 의 모든 return 경로에 `_apply_full_palette()` 누락 | `choose_movement()` 의 모든 return 을 `_apply_full_palette()` 로 감싸기 |
| `symbolism` 배열에 "neon panel" 잔존 | `generate_scenes()` 에서 emotion symbols 를 raw 리스트로 저장 | `[_apply_full_palette(s) for s in ...]` 리스트 컴프리헨션으로 치환 |
| `build_adaptive_default()` 모든 곡에 "cinematic anime noir" 고정 | name 필드에 noir 하드코딩 | visual_styles.json의 style visual_identity 에서 genre_label 파생 |
| Kling 프롬프트 "Medium shot" 고정 | 씬의 camera_direction 무시하고 항상 "Medium shot of" | camera_direction에서 첫 3단어 추출 후 전치사 제거, 콜론 구분자 사용 |
| Wan 프롬프트 "Medium close-up shot" 고정 | cam_kw 를 무시하고 하드코딩 | `{cam_kw.capitalize()}. {base}` 구조로 변경 |
| `_NEON_STYLE_SUB` 모든 non-cyber_noir 에 "accent-light" 일괄 적용 | 스타일 무관하게 단일 치환어 사용 | visual_styles.json 에 style별 `neon_substitute` 추가, BRAND_PALETTE 통해 동적 참조 |
| `_match_camera_keyword()` 단음절 단어 오매칭 | "in","for","a" 같은 단어가 camera_direction 안의 "into","fine" 등에 substring 매칭 | 4자 이하 단어 제외, 의미 있는 단어만 매칭 |
| `dedupe_by_url()` generate_storyboard 항목 대량 유실 | `url=""` 인 항목이 모두 하나의 키로 충돌 → 최신 1개만 남고 나머지 삭제 | `dedupe_composite()` 로 교체: url → audio_hash → content_fp 3단계 복합 키 |
| 같은 감정의 연속 씬이 동일 카메라 방향 (1) | `emotion_shots`에 단일 문자열로 값이 정의되면 `_select_variant()`가 항상 같은 값 반환 | `shot_rules.json` emotion_shots 항목을 2~3개 리스트로 변환 |
| 같은 감정의 연속 씬이 동일 카메라 방향 (2) | 리스트로 변환해도 해시가 같은 인덱스에 매핑되면 중복 발생 | `choose_shot()`에 `used_shots` 파라미터 추가, `generate_scenes()`에서 추적·전달 → `_pick_avoiding()`으로 이미 쓴 샷 우선 제외 |
| `emotions.json` defiant lighting "silver rim emphasis" 미치환 | `_PALETTE_HIGHLIGHT_SUB` 패턴이 "silver rim light/highlights?" 만 허용, "emphasis" 미포함 | `emotions.json`에서 "silver rim emphasis" → "silver-white rim emphasis"로 변경 (pattern 1이 캐치) |
| 새 곡 추가 후 `entries_analyzed` 증가 않음 | 서버 시작 시 `backfill_history_patterns()` 자동 실행 → dedup 재작성으로 추가된 수만큼 제거 | 서버 시작 자동 backfill 제거. backfill은 명시적 호출로만 실행 |
| 이중단어 검증 regex `(\b\w+\b) \1` false positive | "on one" 등 다른 단어가 앞 단어의 substring으로 시작할 때 오매칭 | `\1\b` 로 수정해 단어 경계 추가 |
| Runway 프롬프트 대괄호 없이 출력 | `f"{lead}: {base}"` 로 생성 — `[camera_type]:` 공식 가이드 대괄호 누락 | `f"[{lead}]: {base}"` 로 수정 |
| `[Chorus 1]` / `[Chorus 2]` / `[Chorus 3]` 섹션 누락 | `SECTION_LABEL_PATTERN` 에서 `Chorus` 에 `(?:\s*\d+)?` 가 없어 번호 있는 Chorus 미매칭 → 가사가 앞 섹션에 흡수 | `Chorus(?:\s*\d+)?` 로 수정; `normalize_section_label()` 이 이미 숫자 제거하므로 alias 추가 불필요 |
| 9섹션 곡에서 Outro 위치 중복 | location cap이 8이어서 9씬에 고유 위치 부족 | `infer_locations()` cap 8 → 10, `intimate acoustic anime noir` `location_variants` 2개 추가 |
| Wan/Luma 카메라 `"static shot"` / `"drone shot"` 오매칭 | `"shot"`, `"angle"` 같은 generic 단어가 거의 모든 카메라 설명에 나타나 첫 번째 kw 매칭 유발 (`len > 3` 필터 통과) | `_CAMERA_STOPWORDS = frozenset({"shot", "angle"})` 추가, `_match_camera_keyword()` 에 적용 |
| `[360-degree Rewind FX]` 등 프로덕션 노트가 가사 큐로 출력 | `_pick_key_lyric_phrase()` 가 bracket-only 항목과 앞 bracket 혼합 항목을 필터링하지 않음 | `_BRACKET_NOTE_RE` + `_LEADING_BRACKETS_RE` 로 제거, `infer_lyric_idea()` fallback 을 `lyrics[:80]` 대신 description/section-name 으로 변경 |
| 연주 섹션에 `Lyric mood: Orchestral Build-up...` 출력 | `infer_lyric_idea()` 가 가사 없는 섹션(연주 구간)의 description을 그대로 "music cue: {desc}"로 반환 → 프롬프트에 `Lyric mood:` 레이블로 노출 | `_is_instrumental_section()` 추가 (한국어 없으면 연주 판정), `_instrumental_visual_atmosphere()` 로 뮤지컬 키워드→시각 분위기 변환, 연주 씬은 `Scene atmosphere:` 레이블 사용 |
| `cyber_noir` 스타일이 자동 선택되어 사이버 톤으로만 생성 | `visual_styles.json` 에 cyber_noir 정의, 웹 UI 드롭다운에 노출 → 사용자가 수동 선택 시 모든 곡이 사이버 룩으로 생성 | cyber_noir 스타일 전체 제거 (visual_styles.json에서 삭제), _apply_full_palette 의 cyber_noir 가드 제거 (스타일 치환 항상 적용) |
| `"tempo unknown:"` 구현 레이블이 영상 프롬프트에 노출 | `video_rhythm()` BPM=None 폴백 문자열에 구현 레이블 포함 | prefix 제거 — 지시 문장만 남김 (`"follow the section intensity..."`) |
| inference_profile Chorus 액션이 3개 씬 모두 동일 | `section_actions["Chorus"]` 단일 문자열 + `used_actions` 추적 없음 → `_stable_choice()` 해시 충돌 시 동일 인덱스 선택 | 리스트 변환 + `_pick_action_avoiding()` 헬퍼 추가 + `generate_scenes()` 에 `used_actions` 추적 |
| `build_adaptive_default()` 내 `_adaptive_style_map` 하드코딩 | `energy_group → style_id` 매핑이 함수 내부 딕셔너리 리터럴로 고정 — 스타일 추가 시 코드 수정 필요 | `configs/visual_styles.json` 에 `"adaptive_style_map"` 추가, 코드에서 `_STYLE_CONFIG.get("adaptive_style_map", {...})` 으로 참조 |
| `[Final Chorus]` / `[Chorus 2]` 섹션 누락 | `SECTION_LABEL_PATTERN` 이 bare 섹션명만 인식 — `Final/Repeat/Double` 접두어 미지원 | `(?:(?:Final|Repeat|Double|Opening|Extended|Bonus)\s+)?` 비캡처 그룹을 섹션명 앞에 추가 |
| `[Build]` 섹션이 앞 섹션 가사로 흡수 | `SECTION_LABEL_PATTERN` 에 `Build` / `Drop` / `Hook` / `Solo` / `Interlude` / `Breakdown` 미포함 | 패턴에 추가 + `song_sections.json` aliases 에 `"build": "Bridge"` 등 매핑 |
| `[Build-up: production note]` / `[Drop: Soundscape]` 등이 섹션으로 오인식 | `Build/Drop/Hook/etc.` 가 SECTION_LABEL_PATTERN 에 추가된 후, 섹션 내부 프로덕션 노트도 섹션으로 파싱 (예: `[Pre-Chorus]` 다음에 `[Build-up: Adding legato...]` 가 Bridge 섹션으로 생성됨) | `parse_sections()` + `sections_from_timed_lyrics()` 에 `_PRODUCTION_NOTE_SECTION_RE` 체크 추가: 현재 섹션에 가사가 없을 때 등장하면 프로덕션 노트로 처리 (skip). 가사가 있는 경우만 새 섹션으로 인정 |
| LRC 파일 있을 때 `[Outro]` 소실 | `sections_from_timed_lyrics()` 결과로 TXT 파싱 섹션을 완전 대체 — Suno LRC는 기기 Outro 미포함 | TXT 파싱 섹션 중 LRC에 없는 섹션을 뒤에 보존 추가하는 루프를 `build_song_master_from_input()` 에 추가 |
| `urban_noir` 스타일 곡에서 "neon magenta" 그대로 출력 | `pick_main_color(song)` 가 "dark/noir" 키워드로 인해 "neon magenta" 반환 → `_inject_song_color("neon magenta")` 가 `select_theme()` 이 설정한 올바른 style main_color를 덮어씀 | `run()` 에서 `pick_main_color()` 결과가 "neon magenta" 이면 `BRAND_PALETTE["main_color"]` (style 기본값) 로 대체 후 `_inject_song_color()` 호출 |
| 배치 처리 시 style color가 다음 곡에 오염 | `select_theme()` 이 `BRAND_PALETTE = style_data.get("brand_palette", {})` 로 레퍼런스 복사 → `_inject_song_color()` 로 수정된 값이 `_STYLE_CONFIG` 원본 dict에 영구 반영 → 같은 style_id의 두 번째 곡부터 잘못된 main_color 획득 | `BRAND_PALETTE = dict(style_data.get("brand_palette", {}))` 로 shallow copy 생성 |
| `run_regression.py` 에서 LRC/SRT 미복사로 섹션 파싱 불일치 | `build_song_for_fixture()` 가 임시 디렉토리에 raw_song.txt + MP3만 복사, LRC/SRT 제외 → 타이밍/섹션 파싱 결과가 원본과 달라짐 | `.lrc`, `.srt` 파일도 함께 복사 추가 |
| 같은 제목 폴더가 여러 개일 때 regression 이 잘못된 폴더 탐색 | `find_source_for_fixture()` 가 reverse sort로 최신 폴더 우선 선택 → 최신 폴더가 MP3 없는 불완전 업로드일 경우 timing_mode/color 불일치 | `fixture["input_dir"]` 필드 추가, `find_source_for_fixture()` 에서 해당 필드가 있으면 직접 해당 폴더 사용 |

---

---

## 새 곡 테스트 프로세스 — 신규 곡 추가 시에만 적용

> 이 섹션은 **새 곡을 처음 파이프라인에 넣을 때만** 따른다.  
> 기존 곡 재처리나 버그 수정만 할 때는 이 프로세스를 생략한다.

### 원칙

이 시스템은 단순 계산기가 아니라 파서/분류기다.  
Suno 원본 텍스트, LRC/SRT, 오디오 분석, 장르 태그, 가사 분위기를 해석하므로  
처음부터 모든 입력 표현을 예측할 수 없다.  
**새 곡 데이터로 계속 깨뜨려 보고, 깨진 원인을 일반 규칙으로 고치는 방식**으로 안정화한다.

### 수정 허용 기준

| 허용 | 금지 |
|------|------|
| ✅ 다른 곡에도 적용되는 일반 규칙 수정 | ❌ 특정 곡 제목 기준 분기 |
| ✅ configs/*.json 키워드 매칭 개선 | ❌ 특정 폴더명·파일명 기준 수정 |
| ✅ 파서 정규식·우선순위 개선 | ❌ 곡별 예외 하드코딩 |
| ✅ 오디오 분석 가중치 조정 | ❌ 특정 제목에만 적용되는 fallback |

### 새 곡 테스트 절차

```
Step 1: 파이프라인 실행
  - 새 곡을 input/에 추가하고 전체 파이프라인 실행
  - python scripts/run_pipeline.py

Step 2: 출력 검증 (CLAUDE.md §6 검증 자동화 실행)
  - scene_list.json neon magenta / cyber pink 잔존 여부
  - 이중 단어, Kling/Sora/Wan 포맷 준수 여부

Step 3: 기대값 비교
  tests/fixtures/ 에 저장된 고정 테스트셋과 비교:
  - title, BPM, energy, genre_profile, timing_mode, scene_count
  - 허용 오차 범위를 벗어나면 오류로 기록

Step 4: 오류 원인 분석 → 일반 규칙으로 수정
  - 원인이 특정 표현 패턴이면 → 파서/정규식 개선
  - 원인이 장르 분류 오류면 → configs/genres.json 키워드 추가
  - 원인이 감정 해석 오류면 → configs/emotions.json 수정

Step 5: 회귀 테스트
  - 수정 후 기존 테스트셋 전체를 다시 실행
  - 이전 곡들의 결과가 달라졌으면 의도적 개선인지 확인
  - 의도치 않은 변화는 반드시 수정 후 다시 검증

Step 6: 테스트셋에 새 곡 추가
  - tests/fixtures/<song_id>.json 에 기대값 저장
  - 이후 모든 수정의 회귀 기준이 됨
```

### 테스트 픽스처 형식 (`tests/fixtures/<song_id>.json`)

```json
{
  "song_id": "unique_id",
  "title": "곡 제목",
  "expected": {
    "bpm": 90,
    "energy": "low",
    "genre_profile": "lo-fi",
    "timing_mode": "minimal",
    "scene_count": 6
  },
  "added_date": "2026-05-18",
  "notes": "4/4박자, 보컬 없음, 오디오 분석 우선 적용 케이스"
}
```

### 회귀 테스트 실행 (수동)

```python
# 전체 픽스처 검증
python scripts/run_regression.py

# 단일 곡만 검증
python scripts/run_regression.py --song_id=<id>
```

---

## 상세 문서 참조

- **파이프라인 전체 상세**: [PIPELINE.md](PIPELINE.md)
- **프로젝트 구조·실행 방법**: [README.md](README.md)
- **Config 역할 정의**: PIPELINE.md §9
- **수정 시나리오별 체크포인트**: PIPELINE.md §12
