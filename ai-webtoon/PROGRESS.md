# ai-webtoon 진행 상태

마지막 작업일: 2026-06-04

---

## 완료된 작업 (전체)

### 프로젝트 구조
```
ai-webtoon/
├── CLAUDE.md              ✅ 설계 원칙, 파이프라인 구조, 체크리스트
├── README.md              ✅ 프로젝트 개요, CLI, 스타일 시스템, 검증 현황
├── MV_제작_가이드.md       ✅ 이미지 생성 → CapCut 편집 전체 흐름
├── PROGRESS.md            ✅ 이 파일
├── main.py                ✅ 단일 파일 파이프라인 (파싱→스타일→패널→검증)
├── web_app.py             ✅ Flask 패널 뷰어 (포트 5300)
├── run_all.bat            ✅ input/ 전체 일괄 처리
├── 실행_web.bat           ✅ 웹 뷰어 실행
├── requirements.txt       ✅ flask
├── configs/
│   ├── character_lock.json   ✅ 오리지널 귀여운 cartoon 스켈레톤 밴드 고정
│   ├── webtoon_styles.json   ✅ 5가지 cute 스타일 (감정/BPM 기반 자동 선택)
│   ├── panel_types.json      ✅ 8가지 패널 타입 구도 규칙
│   ├── cut_timing.json       ✅ BPM 4구간 × 7섹션 (웹툰 MV 기준 타이밍)
│   ├── panel_sequences.json  ✅ 섹션별 short/default/extended 패널 순서
│   ├── platforms.json        ✅ GPT/Niji/FLUX.1/Gemini 형식 규칙
│   └── lyric_visual_map.json ✅ 가사 키워드 → 시각 장면 매핑
├── input/                 ✅ 212개 곡 .txt 파일
├── output/                ✅ 212곡 전체 생성 완료 (212/212 PASS)
├── reference/
│   ├── 00_master_reference_prompt.md  ✅ 레퍼런스 이미지 생성용 프롬프트 7종
│   ├── 밴드전체화면 마스터.png         ✅
│   ├── 보컬.png                       ✅
│   ├── 기타.png                       ✅
│   ├── 베이스.png                     ✅
│   ├── 전체 무대 장면.png              ✅
│   ├── 드럼.png                       ✅
│   └── 군중 장면.png                  ✅
└── scripts/               (비어있음 — 파이프라인은 main.py에 통합)
```

---

## 핵심 설계 결정 (변경 금지)

1. **Python은 순수 실행 엔진** — 모든 값은 configs/*.json에 있음. 코드 하드코딩 없음
2. **오리지널 cartoon 스켈레톤 밴드** — character_lock.json 기반, 귀엽고 단순한 Western cartoon 미감. 특정 상용 IP 미참조
3. **스타일 선택 우선순위** — 감정/분위기 키워드 우선 → BPM 보조. (Bittersweet → cute_manhwa, 발라드 → cute_emotional)
4. **입력 형식 동일** — ai_img_video_prompt와 완전히 동일한 .txt 형식
5. **영상 프롬프트 없음** — 이미지만 생성, CapCut/DaVinci Resolve로 편집
6. **레퍼런스 독립** — ai-webtoon/reference/ 폴더 자립 (ai_img_video_prompt 의존 제거)

---

## 검증 현황

| 항목 | 결과 |
|------|------|
| 212곡 전체 처리 | 212/212 PASS |
| 구문 오류 | 없음 (py_compile 통과) |
| 정책 위험 표현 | 없음 |
| 저작권 안전 스타일 | 확인됨 |
| 파이프 구분자 섹션 지원 | 확인됨 (`[Intro \| ...]`) |
| 스타일 오매칭 버그 수정 | 확인됨 |
| 레퍼런스 폴더 독립 | 확인됨 |

---

## 남은 작업

### ai_multi_agent 연결 (선택적, 나중에)

`ai_multi_agent/docs/OUTPUT_PROMPT_STRUCTURES.md`에 ai-webtoon 섹션 추가.
현재는 수동 이미지 생성 → CapCut 편집 방식으로 진행 중이므로 즉시 필요 없음.

---

## hermes 연동 완료

- `DEPENDENCIES.md`: 시스템 3 (ai-webtoon) 추가 완료 ✅
- `HANDOFF.md`: ai-webtoon 완성 기록 추가 필요
