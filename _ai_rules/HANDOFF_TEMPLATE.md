# Handoff — {날짜} {발신 도구} → {수신 도구}

> 복사 위치: 작업 저장소 루트 `/HANDOFF.md` (또는 `/SESSION_HANDOFF.md`)
> 작성 시점: 세션 종료 직전 또는 도구 전환 직전
> 소요 시간: 5분 이내
> 원칙: 수신 도구가 이 파일 하나로 작업을 재개할 수 있어야 한다.

---

## 현재 목표 (한 문장)

```
[지금 이 작업 전체가 달성하려는 것을 한 문장으로]
```

---

## 먼저 읽어야 할 파일

```
1. 이 파일 (HANDOFF.md)
2. CLAUDE.md          — 프로젝트 규칙 (Claude Code는 자동 로드, Codex는 수동 지정 필요)
3. [추가 파일명]: [이유]
```

> **Codex 수신 시 주의**: Codex는 CLAUDE.md를 자동 로드하지 않는다.
> 첫 메시지에 "HANDOFF.md와 CLAUDE.md를 먼저 읽어줘"를 명시해야 한다.

---

## 작업 상태

### 완료
- [x] 항목 1
- [x] 항목 2

### 진행 중 (중단 지점)
- [ ] 항목 3
  - 중단 위치: `파일명.py` 의 `함수명()` 수정 중
  - 완료된 부분: [설명]
  - 남은 부분: [설명]

### 다음 할 일 (우선순위 순)
- [ ] 항목 4
- [ ] 항목 5
- [ ] 항목 6

---

## 주요 결정 사항

```
결정 1: [무엇을 선택했는가] — 이유: [왜]
결정 2: [무엇을 선택했는가] — 이유: [왜]
결정 3: 포기한 대안: [무엇을, 왜 버렸는가]
```

---

## 검증 상태

```
테스트/검증 항목          결과           비고
────────────────────────────────────────────────
python -m pytest -q      PASS (N개)    마지막 실행: HH:MM
__validate_all.py        PENDING       WinError 32 이슈 있음
구문 검사 (py_compile)   PASS
```

---

## 알려진 이슈 / 블로커

```
이슈 1: [설명]
  원인: [파악된 원인]
  임시 해결책: [있다면]
  블로킹 여부: Yes / No

이슈 2: [설명]
```

---

## Git 상태

```
브랜치: main
마지막 커밋: [hash] [메시지]
미커밋 변경 파일:
  - 파일 1
  - 파일 2
  (없으면 "없음")
```

> 전환 전 가능하면 커밋할 것. 미커밋 상태로 전환하면 수신 도구가 변경 파일을 오해할 수 있다.

---

## 수신 도구 부팅 프롬프트

아래를 복붙하면 바로 작업을 이어받을 수 있다.

### Claude Code로 전환할 때

```
HANDOFF.md를 읽고 중단된 작업을 이어서 시작해줘.
현재 목표: [현재 목표 복붙]
지금 바로 해야 할 것: [다음 할 일 첫 번째 항목]
```

### Codex로 전환할 때

```
다음 파일들을 먼저 읽어줘:
1. HANDOFF.md
2. CLAUDE.md
3. [관련 파일]

읽은 후 HANDOFF.md의 "다음 할 일" 첫 번째 항목부터 시작해줘.
작업 범위는 HANDOFF.md의 "현재 목표"로 제한해줘.
```

---

## 컨텍스트 한계 도달 시 처리

세션 중 토큰 한계가 가까워질 때:

```
Step 1: /clear 또는 새 세션 시작 전에 이 파일을 업데이트한다.
Step 2: git commit (WIP: [작업명])
Step 3: 새 세션 또는 다른 도구에서 부팅 프롬프트 사용
Step 4: 수신 도구가 "이 지점에서 이어갑니다" 확인 후 진행
```

> 토큰 한계 신호 (Claude Code 기준):
> - 응답이 이전 결정을 무시하기 시작함
> - 같은 내용을 반복 설명함
> - 파일을 읽었다고 하지만 내용이 틀림
> → 이 중 하나라도 나타나면 즉시 핸드오프 파일 작성 후 /clear

---

## 작성 확인

```
작성자 (발신 도구): Claude Code / Codex
작성일시: 2026-XX-XX HH:MM
다음 수신 도구: Claude Code / Codex
예상 재개 시점: [즉시 / 내일 / 미정]
```

---

## 사용 예시 (참조용)

### Claude Code → Codex 전환 예시

```
# Handoff — 2026-06-04 Claude Code → Codex

## 현재 목표
[프로젝트명] 전체 프로젝트에 거버넌스 규칙을 반영한다.

## 먼저 읽어야 할 파일
1. HANDOFF.md (이 파일)
2. CLAUDE.md
3. SESSION_PROGRESS.md

## 작업 상태
완료:
- [x] 루트 CLAUDE.md 생성
- [x] SECURITY_RULES.md 생성
- [x] ai_anime/CLAUDE.md 확인 (기존 양호)

진행 중:
- [ ] ai_multi_agent 단위 테스트 작성
  - 중단 위치: tests_unit.py 작성 완료, 실행 전
  - 다음: python -m pytest tests_unit.py 실행 후 실패 수정

다음 할 일:
- [ ] ai_story 단위 테스트 작성
- [ ] ai_Scenario 단위 테스트 작성

## 검증 상태
ai_multi_agent tests: PENDING (아직 실행 전)
ai_story tests: 미작성
ai_Scenario tests: 미작성

## Git 상태
브랜치: main
미커밋 변경: 있음 (위 파일들 전부)

## Codex 부팅 프롬프트
HANDOFF.md와 CLAUDE.md를 먼저 읽어줘.
읽은 후 "ai_multi_agent 단위 테스트 실행"부터 이어서 시작해줘.
```

---

*Based on: ai-workspace HANDOFF.md pattern + governance rules*
*Template Version: 1.0 | 2026-06-04*
