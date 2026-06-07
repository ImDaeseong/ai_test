# AI Webtoon MV Builder — Claude Code 작업 지침

> 이 파일은 Claude Code가 이 프로젝트에서 작업할 때 항상 자동으로 로드됩니다.
> 모든 소스 수정·추가 시 아래 규칙을 **반드시** 준수하십시오.

---

## 프로젝트 목적

`ai-webtoon`은 Suno AI 곡을 입력받아 **웹툰/만화 스틸컷 방식 MV**에 사용할 이미지 프롬프트 파일을 자동 생성하는 프롬프트 생성기다.

프롬프트 **실행**은 이 프로젝트가 담당하지 않는다. 실행은 상위 폴더의 `ai_multi_agent`가 담당한다.

### 입력
- `input/[곡명].txt` — ai_anime와 동일한 형식의 Suno 곡 데이터

### 출력
- `output/[곡명]/00_style_reference.md` — 스타일 고정 블록
- `output/[곡명]/01_storyboard.md` — 전체 패널 계획표
- `output/[곡명]/panels/panel_NNN_[section]_[type].md` — 개별 패널 프롬프트

### ai_multi_agent 연결
- 출력 구조는 `ai_multi_agent/docs/OUTPUT_PROMPT_STRUCTURES.md`의 계약을 따른다.
- 미래에 `ai_multi_agent/web_app_webtoon.py`가 이 출력을 읽고 이미지 생성 API를 실행한다.

---

## 핵심 설계 원칙 — 절대 원칙

### 1. Python은 순수 실행 엔진이다. 모든 규칙과 값은 configs/*.json에 있다.

```
금지:
  ❌ 특정 색상, 스타일, 패널 타입을 코드에 하드코딩
  ❌ 특정 곡 제목 기준 분기
  ❌ 특정 섹션에 고정 카메라 앵글

허용:
  ✅ configs/*.json 키워드 매칭으로 값 결정
  ✅ {main_color}, {style_name} 플레이스홀더 포맷팅
  ✅ BPM/에너지/장르 기반 동적 결정
```

### 2. 스켈레톤 밴드 정체성은 절대 변경하지 않는다.

모든 패널 프롬프트는 `configs/character_lock.json`의 고정 블록을 포함해야 한다.
캐릭터 재설계, 인간 캐릭터 대체, 다른 밴드 생성을 절대 허용하지 않는다.

### 3. 웹툰 스타일 파라미터는 곡의 장르/BPM/감정에 따라 동적으로 결정된다.

- 빠른 곡 (BPM 140+): 강한 인크 아웃라인, 고대비, 다이나믹 앵글
- 느린 곡 (BPM 80-): 섬세한 라인, 감성적 색상, 여백 강조
- 장르별 배경 팔레트: `configs/webtoon_styles.json` 참조

---

## 파이프라인 구조

```
입력: input/[곡명].txt
  │
  ├─ song_parser.py      → 곡 메타데이터 파싱 (BPM, 장르, 섹션, 가사)
  ├─ style_selector.py   → 장르/BPM 기반 웹툰 스타일 선택
  ├─ panel_planner.py    → 섹션별 패널 수/타입 계획 (storyboard)
  └─ prompt_generator.py → 개별 패널 프롬프트 파일 생성

출력: output/[곡명]/
```

---

## 출력 파일 구조

```
output/[곡명]/
├── 00_style_reference.md       ← 스타일 고정 블록 (모든 패널에 참조)
├── 01_storyboard.md            ← 전체 패널 계획표 (섹션, 타이밍, 총 패널 수)
└── panels/
    ├── panel_001_intro_wide.md
    ├── panel_002_intro_silhouette.md
    ├── panel_003_verse_medium.md
    └── ...
```

### 패널 파일 네이밍 규칙
```
panel_[NNN]_[section]_[type].md

section: intro / verse / pre_chorus / chorus / bridge / outro
type:    wide / medium / closeup / silhouette / detail / crowd / atmosphere / text

예시:
  panel_001_intro_wide.md
  panel_005_chorus_closeup.md
  panel_012_bridge_silhouette.md
```

### 각 패널 파일 내부 구조
```markdown
# Panel NNN — [Section] [Type]

## 타이밍
- 섹션: [section]
- 컷 번호: [N/전체]
- 권장 지속 시간: [X]초

## 가사 연결
[해당 가사 또는 인스트루멘탈 설명]

## GPT Image (gpt-image-2)
[프롬프트]

## Nijijourney (--niji 7)
[프롬프트] --niji 7 --ar 16:9 --s 250 --no watermark, text, logo

## FLUX.1
[자연어 문장 형식 프롬프트]
```

---

## configs 파일 역할

| 파일 | 역할 |
|------|------|
| `webtoon_styles.json` | 장르별 웹툰 스타일 (아웃라인 굵기, 색상 톤, 그림자 방식) |
| `panel_types.json` | 패널 타입별 카메라 구도, 피사체, 구성 규칙 |
| `cut_timing.json` | BPM별 섹션별 권장 패널 수와 지속 시간 |
| `character_lock.json` | 스켈레톤 밴드 고정 정체성 블록 (모든 프롬프트에 포함) |
| `panel_sequences.json` | 섹션별 권장 패널 타입 순서 패턴 |
| `platforms.json` | 이미지 생성 도구별 프롬프트 형식 규칙 |
| `lyric_visual_map.json` | 가사 키워드 → 시각 장면 매핑 |

---

## ai_multi_agent 연결 계약

ai_multi_agent가 이 프로젝트의 출력을 읽을 때 기대하는 구조:

```
실행 단위: panels/panel_NNN_[section]_[type].md (하나씩)
상태 관리: panels/panel_NNN_.../status.json
결과 저장: ai_multi_agent/output/webtoon/[곡명]/panels/panel_NNN_result.md
```

진행 상태 파일 형식:
```json
{
  "mode": "webtoon",
  "source": "ai-webtoon",
  "title": "[곡명]",
  "total_panels": 0,
  "completed_panels": 0,
  "current_panel": "panel_001_intro_wide"
}
```

---

## 소스 수정 체크리스트

- [ ] 색상값을 코드에 직접 쓰지 않았는가?
- [ ] 모든 스타일 값은 `webtoon_styles.json`에서 참조하는가?
- [ ] 캐릭터 고정 블록은 `character_lock.json`에서 가져오는가?
- [ ] 패널 타입 선택은 `panel_types.json` 키워드 매칭으로 결정하는가?
- [ ] 특정 곡 제목 기준 분기가 없는가?
- [ ] 수정 후 샘플 곡(너는 완벽했어)으로 출력 검증했는가?
