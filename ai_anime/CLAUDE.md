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

### 5. 플랫폼 특화 포맷 (`video_prompt_generator.py`)

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
    m = re.search(r'(\b\w+\b) \1', lighting)
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

---

## 상세 문서 참조

- **파이프라인 전체 상세**: [PIPELINE.md](PIPELINE.md)
- **프로젝트 구조·실행 방법**: [README.md](README.md)
- **Config 역할 정의**: PIPELINE.md §9
- **수정 시나리오별 체크포인트**: PIPELINE.md §12
