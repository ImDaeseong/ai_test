# ai-webtoon

> 귀여운 오리지널 cartoon 스켈레톤 밴드 기준 이미지를 유지하면서,
> 곡마다 BPM·장르·감정에 맞는 웹툰 패널 이미지 프롬프트를 자동 생성하는 CLI 도구.
> **영상 AI 불필요 — 이미지만 생성하고 CapCut/DaVinci Resolve로 편집.**

> **2026-06-07 기준 — 214곡 전체 검증 PASS. ai_multi_agent 연동 완료.**

> **실제 MV 제작 방법 (이미지 생성 → CapCut 편집 → 업로드):**
> [MV_제작_가이드.md](MV_제작_가이드.md) 참조

---

## ai_img_video_prompt와의 관계

| 항목 | ai_img_video_prompt | ai-webtoon |
|------|--------------------|-|
| 입력 형식 | `input/[곡명].txt` | **동일** |
| CLI 명령 | create / create-all / validate / summarize-all | **동일** |
| 캐릭터 | 스켈레톤 밴드 고정 | **동일** (귀여운 cartoon 스타일) |
| 출력 파일 | 고정 9개 (01~09_*.md) | **동적 패널** (BPM·섹션 기반) |
| 영상 프롬프트 | 있음 (09번) | **없음** |
| 편집 방식 | AI 영상 생성 | **이미지 슬라이드쇼 편집** |
| 독립 뷰어 | 포트 5100 | **포트 5350** |
| api_multi_agent | 포트 5200 | **포트 5600** |

---

## 빠른 시작

```powershell
# 패키지 설치
pip install flask

# 단일 곡 생성
python main.py create --input "input\너는 완벽했어.txt"

# input/ 전체 일괄 생성
python main.py create-all --input-dir input --force

# 배치 파일 실행
.\run_all.bat

# 독립 웹 뷰어 (프롬프트 복사용)
.\실행_web.bat        # → http://127.0.0.1:5350

# ai_multi_agent 뷰어 (이미지 자동 생성)
ai_multi_agent\실행_web_webtoon.bat   # → http://127.0.0.1:5600
```

---

## 프로젝트 구조

```
ai-webtoon/
├── main.py                   ← 핵심 엔진 (파싱 → 스타일 선택 → 패널 생성 → 검증)
├── web_app.py                ← 독립 패널 뷰어 (포트 5350, 프롬프트 복사용)
├── run_all.bat               ← input/ 전체 일괄 처리 + summarize-all
├── 실행_web.bat              ← 독립 웹 뷰어 실행
├── requirements.txt          ← flask
├── MV_제작_가이드.md          ← 이미지 생성 → CapCut 편집 전체 흐름
│
├── configs/                  ← 모든 스타일·타이밍·캐릭터 규칙 (코드 하드코딩 없음)
│   ├── character_lock.json   ← 오리지널 cartoon 스켈레톤 밴드 정체성 + 아트 스타일
│   ├── webtoon_styles.json   ← cute 스타일 (감정/BPM 기반 자동 선택)
│   ├── band_performance_profiles.json ← 실제 공연 조사 기반 무대·조명·카메라 프로필
│   ├── panel_types.json      ← 8가지 패널 타입 (카메라·구도·피사체 규칙)
│   ├── cut_timing.json       ← BPM 4구간 × 7섹션 (웹툰 MV 기준 5~8초 타이밍)
│   ├── panel_sequences.json  ← 섹션별 short/default/extended 패널 타입 순서
│   ├── platforms.json        ← GPT/Nijijourney/FLUX.1/Gemini 프롬프트 형식 규칙
│   └── lyric_visual_map.json ← 가사 키워드 → 시각 장면 매핑 (5개 카테고리)
│
├── reference/                ← 레퍼런스 이미지 (이미지 생성 시 반드시 첨부)
│   ├── 00_master_reference_prompt.md  ← 레퍼런스 이미지 생성용 프롬프트 7종
│   ├── 밴드전체화면 마스터.png         ← 전체 밴드 (모든 패널에 필수 첨부)
│   ├── 보컬.png
│   ├── 기타.png
│   ├── 베이스.png
│   ├── 전체 무대 장면.png
│   ├── 드럼.png
│   └── 군중 장면.png
│
├── input/                    ← 곡 정보 txt 파일 (ai_img_video_prompt와 동일 형식)
│
└── output/                   ← 곡별 생성 결과 (직접 편집 금지)
    └── {곡제목}/
        ├── 00_style_reference.md   ← 웹툰 스타일 + 캐릭터 고정 블록
        ├── 00_prompt_overview.md   ← 한글 요약 (검증 상태 포함)
        ├── 01_storyboard.md        ← 전체 패널 계획표 (섹션·타입·타이밍)
        └── panels/
            ├── panel_001_intro_wide.md
            └── panel_NNN_[section]_[type].md
```

---

## 입력 형식

`ai_img_video_prompt`와 **완전히 동일한 형식**의 `.txt` 파일을 사용합니다.
`[Intro: ...]` 형식과 `[Intro | ...]` 파이프 구분자 형식 모두 지원.

```text
Title: 곡 제목
Genre: 장르, BPM, 보컬 스타일, 악기, 분위기...
Weirdness: 15%
Style Influence: 45%

[Intro: Instrumental Only. ...]
[Verse 1: ...]
가사 첫 번째 줄

[Chorus: ...]
후렴구 가사
```

`ai_img_video_prompt/input/` 의 기존 파일을 그대로 복사해서 사용할 수 있습니다.

---

## CLI 명령

```powershell
# 단일 곡 생성
python main.py create --input "input\곡명.txt" [--force]

# 전체 input/ 처리
python main.py create-all --input-dir input [--force]

# 특정 폴더 검증
python main.py validate --folder "output\곡명"

# 전체 요약 생성
python main.py summarize-all --input-dir input --output-dir output
```

---

## 자동 스타일 선택

스타일과 별도로 공연 연출 프로필도 자동 선택한다. 실존 밴드명은
`BAND_REFERENCE_DATA.md`와 설정의 출처 메타데이터에만 보관하며 이미지
프롬프트에는 포함하지 않는다. 같은 곡은 항상 같은 프로필을 얻지만,
패널 번호에 따라 조명·카메라·동작 변형이 달라진다.

감정/분위기 키워드가 BPM보다 **우선** 적용됩니다.

| 우선순위 | 조건 | 선택 스타일 |
|---------|------|-----------|
| 1 | dark pop / gothic / post-punk / shoegaze | `cute_dramatic` |
| 2 | bittersweet / nostalgic / ballad / acoustic / folk / lo-fi | `cute_emotional` 또는 `cute_manhwa` |
| 3 | dance pop / city pop / j-pop / funk | `cute_pop` |
| 4 | BPM 150+ + metal / punk / hardcore | `cute_action` |
| 5 | BPM 120~149 (에너지) | `cute_action` |
| 6 | BPM 0~89 (느린 곡) | `cute_emotional` |
| 기본 | 기타 | `cute_manhwa` |

**예시:**
- `너는 완벽했어` (BPM 174, Bittersweet) → `cute_manhwa` (감정 키워드 우선, BPM 무시)
- `감기` (BPM 95) → `cute_emotional`
- `UPGRADE` (BPM 175, Hardcore) → `cute_action`

---

## 패널 타입

| 타입 | 설명 | 주요 사용 섹션 |
|------|------|--------------|
| `wide` | 전경 와이드샷, 무대 전체 | Intro, Outro |
| `medium` | 상반신 미디엄샷, 연주 장면 | Verse |
| `closeup` | 감정 클로즈업 | Chorus, Bridge |
| `silhouette` | 달 앞 실루엣 | Intro, Outro, Bridge |
| `detail` | 악기/손 디테일 | Verse |
| `crowd` | 관객 원경 | Pre-Chorus, Chorus |
| `atmosphere` | 배경/분위기 (인물 없음) | 전환부, Instrumental |
| `text` | 가사 자막 패널 (편집 단계) | 필요 시 |

---

## 패널 수 및 지속 시간

웹툰 MV 기준 (Ken Burns 효과 포함 5~8초):

| BPM 구간 | Intro | Verse | Chorus | Bridge | Outro | 초/패널 |
|---------|-------|-------|--------|--------|-------|--------|
| Slow (0~89) | 2 | 4 | 5 | 3 | 2 | 7~8초 |
| Medium (90~119) | 2 | 4 | 6 | 3 | 2 | 6~7초 |
| Fast (120~149) | 3 | 5 | 7 | 4 | 3 | 5~6초 |
| Very Fast (150+) | 3 | 6 | 8 | 4 | 3 | 4~5초 |

---

## 각 패널 파일 구조

```markdown
# Panel 001 — Intro / Wide

## 타이밍
- 섹션: Intro / 컷 번호: 1/42 / 권장 지속 시간: 5초

## 가사 연결
[해당 섹션 가사 또는 Instrumental 설명]

## GPT Image (gpt-image-2) — 1792x1024   ← ai_multi_agent 자동 생성에 사용
[프롬프트] ... Do not add any text, letters, numbers, watermarks, logos, or UI overlays to the image.

## Nijijourney (--niji 7)   ← 캐릭터 고정 블록 포함
[프롬프트] --niji 7 --ar 16:9 --s NNN --no watermark, text, letters, numbers, logo, UI overlay

## FLUX.1 (무료, 자연어)
[자연어 문장 형식 프롬프트] ... No text, letters, numbers, watermarks, logos, or UI overlays.

## Gemini / Imagen 3
[프롬프트] ... Do not add any text, letters, numbers, watermarks, logos, or UI overlays to the image.
```

> **텍스트·워터마크 제외 조건** — 4개 플랫폼 모두 글자·숫자·로고·UI 제외 조건 포함 (2026-06-07, 7333패널 전수 검증 PASS)

---

## 웹 뷰어 2종

### 독립 뷰어 (프롬프트 복사용)
```powershell
.\실행_web.bat   # → http://127.0.0.1:5350
```
- 패널 카드 클릭 → GPT/Niji/FLUX.1/Gemini 탭 → 프롬프트 복사
- 수동으로 AI 도구에 붙여넣어 이미지 생성

### ai_multi_agent 뷰어 (API 자동 생성)
```powershell
ai_multi_agent\실행_web_webtoon.bat   # → http://127.0.0.1:5600
```
- [▶ 이미지 생성] 버튼 → OpenAI API 자동 호출 → 이미지 즉시 표시
- `OPENAI_API_KEY` `.env` 설정 필요 (없어도 뷰어는 동작, 복사만 가능)
- 결과: `ai_multi_agent/output/webtoon/[곡명]/panels/[패널]/image.png`

---

## 레퍼런스 이미지 사용법

```
reference/
├── 밴드전체화면 마스터.png  ← 모든 패널 생성 시 필수 첨부
├── 보컬.png               ← closeup 패널 추가 첨부
├── 기타.png               ← detail/medium 패널 추가 첨부
├── 베이스.png
├── 전체 무대 장면.png      ← wide/silhouette 패널 추가 첨부
├── 드럼.png
└── 군중 장면.png           ← crowd 패널 추가 첨부
```

레퍼런스 이미지 생성 프롬프트: [reference/00_master_reference_prompt.md](reference/00_master_reference_prompt.md)

---

## 검증 기준

`python main.py validate --folder "output\{곡명}"` 통과 조건:

- `00_style_reference.md`, `01_storyboard.md` 존재
- `panels/` 폴더에 패널 파일 1개 이상
- 모든 패널 파일에 캐릭터 정체성 고정 문장 포함
- 정책 위험 표현 없음

---

## 캐릭터 아이덴티티 원칙

**스켈레톤 밴드는 바뀌지 않는다. 웹툰 스타일과 패널 구도만 바뀐다.**

- 오리지널 캐릭터 디자인 — 특정 상용 IP 직접 참조 없음 (저작권 안전)
- 귀엽고 단순한 Western cartoon 미감: 두꺼운 외곽선, 플랫 색상, 통통한 비율
- 모든 패널 프롬프트에 `Do not redesign the band members` 포함
- 이미지 생성 시 `reference/밴드전체화면 마스터.png` 반드시 첨부

---

## 제작 흐름

```
1. input/ 에 곡 .txt 파일 복사
   (ai_img_video_prompt와 동일 파일 사용 가능)

2. run_all.bat
   → 전체 패널 프롬프트 자동 생성 (212곡 예시)

3-A. 수동 이미지 생성
   실행_web.bat (5350) → 패널 클릭 → 프롬프트 복사
   → GPT/Niji/FLUX.1에 붙여넣기 + reference/ 이미지 첨부 → 이미지 저장

3-B. API 자동 이미지 생성
   ai_multi_agent\실행_web_webtoon.bat (5600)
   → 곡 선택 → 패널 클릭 → [▶ 이미지 생성]
   → OpenAI API → image.png 자동 저장

4. CapCut / DaVinci Resolve
   → 이미지 슬라이드쇼 + Ken Burns 효과 + 음악 싱크
   → MV 완성 → YouTube 업로드
```

---

## 검증 현황

| 항목 | 상태 |
|------|------|
| configs 7개 완성 | ✅ |
| main.py 파이프라인 | ✅ |
| 독립 웹 뷰어 (포트 5350) | ✅ |
| ai_multi_agent 연동 (포트 5600) | ✅ |
| 전체 검증 (212곡 / 0 실패) | ✅ 212/212 PASS |
| 파이프 구분자 지원 (`[Intro \| ...]`) | ✅ |
| 감정 키워드 우선 스타일 선택 | ✅ |
| 한글 곡명 onclick 버그 수정 | ✅ |
| 목록 로딩 성능 최적화 (4.2초→0.17초) | ✅ |
| reference/ 폴더 (이미지 7개) | ✅ |
| 저작권 안전 스타일 설명 | ✅ |

*Last Updated: 2026-06-04*
