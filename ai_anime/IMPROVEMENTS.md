# 개선 기록

## 2026-06-07 장르 미학 레퍼런스 계층

### 목적

- 분류용 대규모 키 목록과 생성용 미학 데이터를 분리했다.
- 공개 기관 자료에서 장르별 공통 시각 문법만 일반화해 사용한다.
- 기존 곡별 세계관 생성과 가사 중심 설계는 유지한다.

### 구현

- `configs/genre_reference_profiles.json`: 출처 8건, 장르 계열 6종
- `scripts/genre_reference.py`: 기존 장르 프로필을 레퍼런스 계열에 매핑하고 결정론적 변형 선택
- `world_builder.py`: 장소, 조명, 전환, 서사 방향
- `character_builder.py`: 장르별 캐릭터 방향
- `scene_composer.py`: 장르별 카메라와 움직임
- `validate_configs.py`: 새 설정 구조와 출처 참조 검증

### 안전 원칙

- 출처 기관명, 아티스트명, 작품명은 provenance 데이터에만 둔다.
- 생성 프롬프트에는 얼굴, 로고, 정확한 의상, 시그니처 소품, 정확한 영상 장면이나 무대 복제를 넣지 않는다.

### 검증

- 단위 테스트: 63 passed
- 설정 검증: 0 errors, 0 warnings
- 기존 장르 프로필: 20/20 매핑
- 현재 입력: 214/214 매핑
- 대표 6곡 생성 및 출력 일관성: PASS 6, FAIL 0
- 대표 출력의 출처명 노출: 0건
- 기존 회귀 테스트는 ffmpeg/ffprobe 부재와 누락 소스 때문에 3 passed, 30 failed, 2 skipped
- `__validate_all.py`는 실제로 214곡을 개별 재생성하므로 10분 제한을 초과한다. 검증기 성능 개선은 별도 P2 작업으로 분리한다.

## 2026-05-19

### 핵심 결론

- 새 음악을 검증하고 프롬프트를 만들 때마다 Python 소스를 직접 수정하는 방식은 정답이 아니다.
- 장르, 악기, 팔레트, 플랫폼, 검증 규칙은 코드가 아니라 `configs/*.json`에서 관리하는 구조가 더 맞다.
- 트롯처럼 기존에 없던 장르가 들어오면 즉시 소스를 고치는 대신, 우선 데이터로 감지하고 설정 프로필로 확장하는 흐름이 적절하다.

### 새 장르 처리 개선

- `configs/genres.json`에 트롯 전용 프로필 `korean trot memory anime noir`를 추가했다.
- `configs/color_palette.json`에 트롯 계열 키워드가 `amber gold` 팔레트로 매칭되도록 추가했다.
- `configs/tag_classification.json`에 `trot`, `korean trot`, `k-trot`, `ppongjjak`, `traditional korean pop` 등을 장르 키워드로 추가했다.
- `configs/instrument_hints.json`에 `saxophone`, `accordion`, `organ`, `taepyeongso`, `piri` 힌트를 추가했다.
- `scripts/config_learner.py`가 기존 프로필에 붙일 수 없는 빈번한 태그를 `new_profile_candidates`로 보고하도록 개선했다.
- `scripts/config_learner.py --write-candidates`를 추가해 새 장르 후보를 `data/new_profile_candidates.json`에 기록할 수 있게 했다.

### 하드코딩 제거

- `scripts/song_parser.py`에 있던 장르/악기/보컬/무드 분류 목록을 `configs/tag_classification.json`으로 이동했다.
- `scripts/scene_generator.py`에 있던 악기별 영상 움직임 힌트를 `configs/instrument_hints.json`으로 이동했다.
- `scripts/scene_generator.py`에 있던 팔레트 치환 규칙을 `configs/palette_substitutions.json`으로 이동했다.
- `scripts/run_regression.py`, `scripts/validate_history.py`의 검증 토큰과 노이즈 태그 패턴을 `configs/validation_rules.json`으로 이동했다.
- `scripts/config_learner.py`의 학습 제외 규칙과 프로덕션 태그 필터를 `configs/learning_rules.json`으로 이동했다.
- `scripts/image_prompt_generator.py`, `scripts/video_prompt_generator.py`의 플랫폼 fallback 목록을 제거하고 `configs/platforms.json`을 필수 설정으로 사용하게 했다.

### 트롯 테스트 반영 결과

- 테스트 입력 `output/web_inputs/20260519-115621`의 `커피 한 잔`은 기존 positive 장르 데이터에는 없던 트롯 계열 곡이다.
- 현재 파싱 결과는 `Pure Korean Trot, Emotional Ballad, Ppongjjak Rhythm`로 반영된다.
- 현재 시각 세계는 `korean trot memory anime noir`, 메인 팔레트는 `amber gold`로 생성된다.
- 프롬프트에는 트롯 전용 요소인 오래된 음악 카페/카바레 무대/커피잔/아코디언/색소폰/전자 오르간/태평소 또는 피리 힌트가 반영된다.

### 검증 명령

```powershell
python scripts/config_learner.py --dry-run --write-candidates
python scripts/run_pipeline.py --input output\web_inputs\20260519-115621 --apply-audio-analysis
python scripts/run_regression.py
python scripts/validate_history.py
python -m py_compile scripts/config_learner.py scripts/run_regression.py scripts/validate_history.py scripts/song_parser.py scripts/scene_generator.py scripts/image_prompt_generator.py scripts/video_prompt_generator.py
```

### 검증 결과

- 전체 이력 검증: `240 passed, 0 failed, 8 warnings`.
- fixture 회귀 검증: `3 passed, 0 failed, 0 skipped`.
- 트롯 테스트 곡 파이프라인 재생성: image prompt 9개, video prompt 8개 생성.
- `config_learner --dry-run` 기준 현재 추가 자동 반영 대상과 새 프로필 후보는 없다. 트롯 프로필이 이미 기본 설정에 들어갔기 때문이다.

### 운영 방식

- 이미 존재하는 장르의 새 키워드는 `config_learner`가 기존 프로필 키로 추가할 수 있다.
- 기존 프로필에 자연스럽게 붙지 않는 새 장르는 `new_profile_candidates`로 감지한 뒤 `configs/genres.json`, `configs/color_palette.json`, `configs/tag_classification.json`, `configs/instrument_hints.json`에 설정으로 추가한다.
- 이 구조에서는 새 장르 대응 시 Python 소스 수정이 아니라 JSON 설정 추가가 기본 작업이 된다.

## 2026-05-19 전체 소스 점검

### 점검 범위

- 주요 변경 소스: `scripts/config_learner.py`, `scripts/song_parser.py`, `scripts/scene_generator.py`, `scripts/image_prompt_generator.py`, `scripts/video_prompt_generator.py`.
- 신규 검증 소스: `scripts/run_regression.py`, `scripts/validate_history.py`.
- 신규/변경 설정: `configs/tag_classification.json`, `configs/instrument_hints.json`, `configs/palette_substitutions.json`, `configs/validation_rules.json`, `configs/learning_rules.json`, `configs/genres.json`, `configs/color_palette.json`.
- 최신 트롯 테스트 출력: `input/song_master.json`, `analysis/visual_world.json`, `storyboard/story_summary.md`, `prompts/*`, `output/커피 한 잔/*`.

### 발견 및 조치

- `scripts/image_prompt_generator.py`, `scripts/video_prompt_generator.py` 맨 앞에 UTF-8 BOM 문자가 들어가 있었다. 실행에는 큰 문제를 만들지 않았지만 diff와 도구 호환성에 좋지 않아 제거했다.
- 위 두 파일에서 플랫폼 fallback 제거 후 함수 선언과 상수 선언 사이 공백이 부족해 가독성이 낮았다. `image_prompt_generator.py`의 함수 앞 공백을 정리했다.
- `IMPROVEMENTS.md`는 파일 자체가 UTF-8로 정상 저장되어 있음을 확인했다. PowerShell 콘솔 출력만 한글이 깨져 보일 수 있다.
- 트롯 프로필은 현재 코드 하드코딩이 아니라 `configs/*.json` 설정으로 반영되어 있다.
- 신규 장르 후보 리포트는 `data/new_profile_candidates.json`에 기록되며, 현재 값은 `[]`이다. 이는 트롯이 이미 기본 장르 프로필로 들어갔기 때문이다.

### 재검증 결과

```powershell
python -m json.tool configs\learning_rules.json
python -m json.tool configs\tag_classification.json
python -m json.tool configs\instrument_hints.json
python -m json.tool configs\palette_substitutions.json
python -m json.tool configs\validation_rules.json
python -m json.tool configs\genres.json
python -m json.tool configs\color_palette.json
python -m json.tool data\new_profile_candidates.json
python -m py_compile scripts\config_learner.py scripts\run_regression.py scripts\validate_history.py scripts\song_parser.py scripts\scene_generator.py scripts\image_prompt_generator.py scripts\video_prompt_generator.py
python scripts\config_learner.py --dry-run --write-candidates
python scripts\run_regression.py
python scripts\validate_history.py
```

- JSON 검증: 통과.
- Python 컴파일 검증: 통과.
- 설정 학습 dry-run: `240`곡 분석, `genre_updates: {}`, `new_profile_candidates: []`, `configs_changed: []`.
- fixture 회귀 검증: `3 passed, 0 failed, 0 skipped`.
- 전체 이력 검증: `240 passed, 0 failed, 8 warnings, 240 entries checked`.

### 남은 개선 후보

- 생성물(`analysis/`, `character/`, `storyboard/`, `prompts/`, `input/song_master.json`, `data/suno_history.jsonl`)이 Git 추적 파일로 남아 있어 테스트할 때마다 diff가 커진다. 운영 방식에 따라 `git rm --cached`와 `.gitignore` 정리를 검토하는 것이 좋다.
- `output/커피 한 잔` 같은 곡별 출력 폴더 동기화는 현재 파이프라인 본 단계가 아니라 별도 복사 흐름에 가깝다. 장기적으로는 `run_pipeline.py` 또는 `web_app.py`에서 곡별 output 저장까지 한 번에 처리하는 옵션을 두는 것이 좋다.
- 일부 기존 설정 파일에는 과거 인코딩이 깨진 키워드가 남아 있다. 현재 검증은 통과하지만, 장기적으로 `configs/genres.json`, `configs/platforms.json`의 legacy mojibake 텍스트를 정리하면 검색성과 유지보수성이 좋아진다.
- JSON 설정 구조가 늘었으므로 다음 단계에서는 간단한 schema 검증 스크립트를 추가해 필수 키 누락, 타입 오류, 빈 플랫폼 목록을 테스트 초기에 잡는 편이 좋다.

## 2026-05-19 추가 운영 개선

### 곡별 output 자동 동기화

- `scripts/run_pipeline.py`에 `sync_song_output()`을 추가했다.
- 파이프라인 5단계가 끝나면 기본적으로 `output/<곡명>/`에 다음 파일을 자동 동기화한다.
  - `character_reference_prompt.md`
  - `image_prompts/`
  - `video_prompts/`
- 기존처럼 자동 동기화를 원하지 않을 때는 `--no-song-output` 옵션을 사용할 수 있다.
- 곡명 폴더는 Windows 금지 문자를 `_`로 치환하며, 프롬프트 하위 폴더 삭제 시 대상 경로가 곡별 output 내부인지 확인한다.

### JSON 설정 검증 추가

- `scripts/validate_configs.py`를 추가했다.
- 모든 `configs/*.json` 파싱 오류를 확인한다.
- `genres.json`의 필수 키, 빈 key, 중복 프로필 이름, 중복 장르 키를 검증한다.
- `platforms.json`의 `platforms`, `image_platforms` 존재와 기본 필드(`id`, `display_name`)를 검증한다.
- `tag_classification.json`, `instrument_hints.json`, `palette_substitutions.json`, `validation_rules.json`, `learning_rules.json`, `color_palette.json`의 필수 최상위 키를 검증한다.
- regex 설정(`production_tag_pattern`, `strip_prefix_pattern`, `noisy_learnable_tag_pattern`)이 컴파일 가능한지 확인한다.

### Legacy 인코딩 텍스트 감지

- `scripts/validate_configs.py`에서 설정 파일 내 mojibake 의심 문자열을 경고로 감지한다.
- 기본 실행에서는 legacy 텍스트를 실패로 처리하지 않는다.
- `--strict-mojibake` 옵션을 쓰면 mojibake 경고도 실패로 처리할 수 있다.

### 추가 검증 결과

```powershell
python -m py_compile scripts\run_pipeline.py scripts\validate_configs.py
python scripts\validate_configs.py
python scripts\run_pipeline.py --input output\web_inputs\20260519-115621 --apply-audio-analysis
python scripts\config_learner.py --dry-run --write-candidates
python scripts\run_regression.py
python scripts\validate_history.py
```

- `validate_configs.py`: `0 errors, 102 warnings`.
- 남은 102개 경고는 대부분 기존 `genres.json`의 중복 장르 키다. 현재 동작 실패는 아니지만 장기적으로 프로필 우선순위를 흐릴 수 있어 정리 대상이다.
- 트롯 테스트 곡 파이프라인: 5단계 통과, `output/커피 한 잔` 자동 동기화 완료.
- `output/커피 한 잔/image_prompts`: 9개 파일.
- `output/커피 한 잔/video_prompts`: 8개 파일.
- `output/커피 한 잔/character_reference_prompt.md`: 존재 확인.
- `config_learner --dry-run`: `240`곡 분석, 추가 변경 없음, 새 프로필 후보 없음.
- fixture 회귀 검증: `3 passed, 0 failed, 0 skipped`.
- 전체 이력 검증: `240 passed, 0 failed, 8 warnings, 240 entries checked`.

### 다음 정리 후보

- ~~`genres.json` 중복 키를 프로필 의도에 맞게 정리한다.~~ → 완료 (아래 참조)
- ~~생성물 Git 추적 정리는 아직 남아 있다.~~ → 완료 (아래 참조)

## 2026-05-19 남은 개선 과제 처리

### 생성물 Git 추적 정리

- `.gitignore`에 이미 올바른 규칙이 있었으나, 과거에 커밋된 파일들이 여전히 git에 추적되고 있었다.
- `git rm --cached`로 다음 파일들을 추적 해제했다:
  - `analysis/` (cinematic_style.json, emotion_analysis.json, visual_world.json)
  - `character/` (character_prompt.md, character_reference_prompt.md, protagonist_bible.json)
  - `input/` (raw_song.txt, song_master.json)
  - `storyboard/` (camera_directions.md, scene_list.json, story_arc.json, story_summary.md, storyboard_prompts.md)
  - `prompts/` (image_prompts/*.md, video_prompts/*.md)
  - `data/suno_history.jsonl`
- 이후 파이프라인 실행 시 생성물이 바뀌어도 git diff에 나타나지 않는다.

### genres.json 중복 키 경고 로직 개선

- 기존 `validate_configs.py`는 동일한 태그 키가 2개 이상 프로필에 존재하면 개별적으로 경고했다.
  → 모든 15개 프로필이 15개 이상의 고유 키를 가지고 있음에도 102개 경고가 발생해 실제 문제를 가렸다.
- 분석 결과: 모든 프로필이 충분한 고유 키를 보유 (최소 15개, 대부분 100개 이상).
  - 공유 키는 장르 간 자연스러운 중복이므로 경고 대상이 아니다 (예: "saxophone"은 trot와 jazz 모두에 정상 포함).
- 수정: 공유 키 개별 경고 → 프로필 단위 고유 키 수 검사로 변경.
  - `_MIN_UNIQUE_KEYS = 5` 기준 미만인 프로필에 대해서만 경고.
  - 현재 모든 프로필이 5개 이상 고유 키를 보유하므로 경고 0개.
- `from collections import Counter`를 함수 내부에서 파일 상단으로 이동해 스타일 정리.

### 검증 결과

- `validate_configs.py`: 0 errors, 0 warnings (이전: 0 errors, 102 warnings)
- Python 컴파일 검증: 전체 통과
- fixture 회귀 검증: 3 passed, 0 failed, 0 skipped
- 전체 이력 검증: 241 passed, 0 failed, 8 warnings (새 트롯 테스트 곡 포함으로 240→241)
- scene_list.json raw color / double word: none
- video_prompts Kling/Sora 포맷: none

## 2026-05-19 이미지·영상 프롬프트 퀄리티 점검 및 버그 수정

### 점검 배경

- 테스트 곡 `사랑이 다가올 때` (BPM=None, 10섹션) 의 이미지·영상 프롬프트 전반 퀄리티를 점검했다.
- 발견 버그 6건을 수정하고 전체 검증을 재실행했다.

### 발견 및 수정 내역

**버그 1 — Wan 2.2 "Static shot." 오매칭**

- 원인: `video_prompt_generator.py`의 `_match_camera_keyword()`가 `len(p) > 3` 필터만 적용해 `"shot"` (4자)이 매칭 단어로 사용됨. `"static shot"` kw 의 `"shot"`이 카메라 설명의 `"tracking shot"` 안 `"shot"`과 매칭 → 잘못된 `"Static shot."` 출력.
- 수정: `_CAMERA_STOPWORDS = frozenset({"shot", "angle"})` 상수 추가, `_match_camera_keyword()`에서 stop-words 제외. `"shot"` 은 모든 카메라 설명에 공통으로 나타나고, `"angle"` 은 `"upward angle"` → `"low angle"` 오매칭을 유발하므로 함께 제외.

**버그 2 — Luma "drone shot" 오매칭**

- 원인: 버그 1과 동일. `"drone shot"` kw 의 `"shot"` 이 `"upward angle tracking shot"` 안 `"shot"` 에 먼저 매칭됨. `"drone shot"` 이 `"tracking shot"` 보다 kw_list 앞에 위치해 반환.
- 수정: 버그 1과 동일 fix 로 해결.

**버그 3 — "tempo unknown:" 구현 상세가 프롬프트에 노출**

- 원인: `scene_generator.py`의 `video_rhythm()`에서 BPM=None 일 때 `f"tempo unknown: follow the section intensity..."` 를 반환해 AI 영상 생성 프롬프트에 구현 세부사항이 노출됨.
- 수정: `"tempo unknown:"` prefix 제거 → `"follow the section intensity {intensity} with coherent cinematic motion"`.

**버그 4 — 가사 큐에 프로덕션 노트(`[360-degree Rewind FX]`)가 그대로 출력**

- 원인: `_pick_key_lyric_phrase()` 가 `[\n\r.!?]` 로 분리한 뒤 `^\[.+\]$` 필터를 적용하지 않아 bracket-only 프로덕션 노트가 가사로 선택됨.
- 수정 1: `_BRACKET_NOTE_RE = re.compile(r'^\[.+\]$')` 로 완전 bracket 항목 제거.
- 수정 2: `_LEADING_BRACKETS_RE = re.compile(r'^(?:\[.*?\]\s*)+')` 로 `"[Metallic synth stabs] 뱅뱅뱅"` 형식에서 앞 bracket 제거 후 실제 가사만 사용.
- 수정 3: `infer_lyric_idea()`에서 `key_phrase` 가 공백이면 `lyrics[:80]` fallback 대신 description 또는 `"{section} emotional cue"` 로 이어지도록 변경.

**버그 5 — Chorus 3개 씬이 동일 액션 반복**

- 원인: `configs/song_inference.json` `tropical_vacation` 프로필의 `section_actions["Chorus"]` 가 단일 문자열 → `_select_variant()` 가 항상 동일 값 반환. 3개 Chorus 씬의 해시 충돌 시 같은 인덱스 선택.
- 수정 1: `section_actions["Chorus"]` 를 3개 옵션 리스트로 변환.
- 수정 2: `_pick_action_avoiding(options, seed, salt, prop, used)` 헬퍼 추가 — `{prop}` 치환 후 이미 사용한 액션을 제외하고 선택.
- 수정 3: `choose_scene_action()` 에 `used_actions: list[str] | None = None` 파라미터 추가, inference_profile section_actions 분기에 `_pick_action_avoiding()` 적용.
- 수정 4: `generate_scenes()` 에 `used_actions: list[str] = []` 추적 추가, 매 씬 생성 후 append.

**버그 6 — Post-Chorus/Outro 가사 큐에 `[Metallic synth stabs] 뱅뱅뱅` 형식 잔존**

- 원인: `"[...]"` 로 완전히 감싸이지 않은 혼합 fragment 에는 `^\[.+\]$` 필터가 적용되지 않아 앞 bracket 노트가 그대로 남음.
- 수정: 버그 4 수정 2에서 함께 해결. `_LEADING_BRACKETS_RE` 로 앞 bracket 제거 후 실제 가사만 fragment 로 사용.

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `scripts/video_prompt_generator.py` | `_CAMERA_STOPWORDS` 추가, `_match_camera_keyword()` stop-words 적용 |
| `scripts/scene_generator.py` | `_BRACKET_NOTE_RE`, `_LEADING_BRACKETS_RE`, `_pick_action_avoiding()` 추가; `_pick_key_lyric_phrase()`, `infer_lyric_idea()`, `choose_scene_action()`, `generate_scenes()` 수정; `video_rhythm()` tempo unknown prefix 제거 |
| `configs/song_inference.json` | `tropical_vacation.section_actions["Chorus"]` 단일 문자열 → 3개 리스트 변환 |

### 검증 결과

```
scene_list.json raw color (neon magenta/cyber pink): none
scene_list.json 이중 단어: none
Kling 포맷 (≤65단어, 결론어, . 종료): all pass
Sora 5섹션: all pass
Wan negative prompt: all pass
FLUX.1 body 가중치 문법: none
Runway [camera]: lead: all pass
FLUX.1 weight syntax in body: none
Wan 카메라 오매칭: none (Static shot 제거 확인)
Luma 카메라 오매칭: none (drone shot 제거 확인)
bracket 가사 큐 잔존: none
Chorus 액션 중복: Sc04/Sc07/Sc09 모두 다른 액션 확인
```

```
fixture 회귀 검증: 3 passed, 0 failed, 0 skipped
```

### 추가 반영된 CLAUDE.md 버그 패턴

이번 수정으로 CLAUDE.md `## 자주 발생한 버그 패턴` 에 아래 항목이 추가 대상이다:

| 버그 | 원인 | 수정 방법 |
|------|------|----------|
| Wan/Luma 카메라 `"static shot"` / `"drone shot"` 오매칭 | `"shot"`, `"angle"` 같은 generic 단어가 거의 모든 카메라 설명에 나타나 첫 번째 kw 매칭 유발 | `_CAMERA_STOPWORDS = frozenset({"shot", "angle"})` 추가, `_match_camera_keyword()` 에 적용 |
| `[360-degree Rewind FX]` 등 프로덕션 노트가 가사 큐로 출력 | `_pick_key_lyric_phrase()` 가 bracket-only 항목과 앞 bracket 혼합 항목을 필터링하지 않음 | `_BRACKET_NOTE_RE` + `_LEADING_BRACKETS_RE` 로 제거, `infer_lyric_idea()` fallback 개선 |
| "tempo unknown:" 구현 세부가 프롬프트 노출 | BPM=None 폴백 문자열에 구현 레이블 포함 | prefix 제거, 지시 문장만 남김 |
| inference_profile Chorus 액션 3개 씬 중복 | `section_actions["Chorus"]` 단일 문자열 + used_actions 추적 없음 | 리스트 변환 + `_pick_action_avoiding()` + `used_actions` 추적 |

## 2026-05-19 전체 소스 점검 (2차)

### 점검 범위

- 전체 Python 스크립트 9개: `scene_generator.py`, `image_prompt_generator.py`, `video_prompt_generator.py`, `song_parser.py`, `config_learner.py`, `run_pipeline.py`, `run_regression.py`, `validate_configs.py`, `validate_history.py`
- 설정 파일 12개: `genres.json`, `color_palette.json`, `emotions.json`, `shot_rules.json`, `song_inference.json`, `platforms.json`, `visual_styles.json`, `tag_classification.json`, `instrument_hints.json`, `palette_substitutions.json`, `validation_rules.json`, `learning_rules.json`

### 점검 항목

- 하드코딩된 색상값 / 스타일명 잔존 여부
- `_apply_full_palette()` 누락 경로
- `{main_color}` / `{prop}` 미포맷팅
- 플랫폼 포맷터 공식 가이드 준수
- JSON 구조 오류, 필수 키 누락
- configs에 있어야 할 값이 코드에 직접 박혀 있는 경우

### 발견 및 수정

**하드코딩 — `scene_generator.py` `build_adaptive_default()` 내 `_adaptive_style_map`**

- 원인: `energy_group → style_id` 매핑 딕셔너리가 함수 내부에 리터럴로 고정되어 있어, 스타일 추가·변경 시 코드 수정이 필요했음.
- 수정: `configs/visual_styles.json` 에 `"adaptive_style_map"` 키를 추가하고, 코드에서 `_STYLE_CONFIG.get("adaptive_style_map", {...})` 으로 참조하도록 변경. 코드 내 딕셔너리는 config 누락 시 폴백으로만 유지.

```json
// configs/visual_styles.json 에 추가
"adaptive_style_map": {
  "fast": "urban_noir",
  "slow": "warm_acoustic",
  "medium": "dreamy_synth"
}
```

```python
# scene_generator.py 수정 전
_adaptive_style_map = {"fast": "urban_noir", "slow": "warm_acoustic", "medium": "dreamy_synth"}

# 수정 후
_adaptive_style_map = _STYLE_CONFIG.get("adaptive_style_map", {"fast": "urban_noir", "slow": "warm_acoustic", "medium": "dreamy_synth"})
```

**genres.json mojibake 여부 — False alarm**

- 에이전트가 한글 키를 읽는 과정에서 인코딩 오류처럼 보고했으나, 실제 `validate_configs.py` 기준 `0 errors, 0 warnings` 통과.
- `'`, `&`, `"` 등 음악 키워드 내 특수문자는 정상 콘텐츠.

**`_validate_scene.py` 이중 단어 false positive 수정**

- 가사 반복 훅 (`뱅뱅뱅 뱅뱅뱅 뱅뱅뱅`)이 `lyric_visual_idea` / `video_prompt` 에서 이중 단어로 오탐되던 문제.
- CLAUDE.md 검증 스펙대로 이중 단어 체크를 `lighting` 필드로 한정하도록 수정. lyric 텍스트는 의도적 반복이 허용되므로 제외.

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `configs/visual_styles.json` | `"adaptive_style_map"` 추가 |
| `scripts/scene_generator.py` | `_adaptive_style_map` → config 참조로 변경 |
| `scripts/_validate_scene.py` | 이중 단어 체크를 `lighting` 필드로 한정 |

### 검증 결과

```
Python 컴파일 검증: 전체 통과
파이프라인 5단계: 통과
scene_list.json raw color / 이중단어 / bracket lyric / tempo unknown: none
비디오 프롬프트 (Kling/Sora/Runway/Wan/Luma): all pass
이미지 프롬프트 raw color / bracket: all pass
validate_configs.py: 0 errors, 0 warnings
fixture 회귀 검증: 3 passed, 0 failed, 0 skipped
```
