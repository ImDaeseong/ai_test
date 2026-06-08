# AI 코딩 프로젝트 템플릿 사용 가이드

## 파일 구성

| 파일 | 사용 시점 | 소요 시간 |
|---|---|---|
| `PROJECT_START.md` | 프로젝트 생성 직후 | 30분 |
| `TESTING_DONE_CRITERIA.md` | 개발 시작 전 (완료 기준 정의) | 20분 |
| `VSCODE_AI_RULES.md` | Claude Code 세션마다 상시 적용 | 상시 |
| `CODEX_RULES.md` | Codex 세션마다 상시 적용 | 상시 |
| `TOOL_GUIDE.md` | Claude Code vs Codex 선택 시 | 참조용 |
| `AI_CODING_REVIEW.md` | AI 코드 커밋/머지 전 | 15~30분 |
| `PRE_DEPLOY.md` | 모든 배포 직전 | 5~10분 |
| `HANDOFF_TEMPLATE.md` | AI 도구 전환 직전 (Claude Code ↔ Codex) | 5분 |
| `GOVERNANCE_REF.md` | "왜?"가 궁금할 때, 팀 교육 시 | 참조용 |

---

## 새 프로젝트 시작 시

```
1. 이 _templates 폴더에서 파일 4개를 복사한다
   (GOVERNANCE_REF.md는 선택)

2. 프로젝트 루트에 붙여넣는다

3. PROJECT_START.md를 작성한다 (30분)

4. .gitignore에 .env 포함 여부 즉시 확인한다

5. 개발 시작 전 TESTING_DONE_CRITERIA.md의 완료 기준을 먼저 작성한다
```

---

## 개인 프로젝트 vs 회사 프로젝트

| 항목 | 개인 | 회사 |
|---|---|---|
| PROJECT_START.md 작성 | 본인만 | 팀장/동료 검토 포함 |
| AI_CODING_REVIEW.md | 본인 자가 검토 | PR 리뷰 시 함께 확인 |
| PRE_DEPLOY.md | 본인 확인 | 배포 담당자 + 검토자 서명 |
| GOVERNANCE_REF.md | 참조용 | 팀 온보딩 자료로 활용 |

---

## 개인 프로젝트 vs 회사 프로젝트 (TESTING_DONE_CRITERIA 적용)

| 항목 | 개인 | 회사 |
|---|---|---|
| 완료 기준 작성 | 본인이 개발 전 작성 | 기획자/팀장 검토 후 확정 |
| 버그 심각도 분류 | 본인 판단 | 팀 기준으로 사전 합의 |
| 구조적 문제 판단 | 3회 규칙 적용 | 3회 규칙 + 팀장 보고 |
| 인간 검증 항목 | 본인 직접 확인 | 담당자 분리 검증 |
| 테스트 종료 선언 | 본인 | 검토자 서명 필요 |

---

## 이 템플릿이 막는 것

- API 키, 비밀번호 GitHub 노출
- AI가 만든 코드를 이해 못한 채 배포
- VS Code AI 세션 무한 루프 · 토큰 낭비
- 테스트 완료 기준 없이 무한 수정 루프
- 구조적 문제를 패치로만 덮다가 더 큰 장애 발생
- 장애 발생 시 원인 파악 불가
- 신규 기능 추가 시 기존 기능 회귀
- 운영 이후 유지보수 불능 상태
