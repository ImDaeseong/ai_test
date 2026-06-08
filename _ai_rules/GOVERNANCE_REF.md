# AI 코딩 거버넌스 참조 문서

> 이 파일은 평소에 보지 않아도 된다
> 체크리스트의 "왜?"가 궁금할 때, 또는 팀에 이 기준을 설명할 때 참조한다

---

## 핵심 원칙 요약

| 원칙 | 출처 | 한 줄 요약 |
|---|---|---|
| 이해 불가 코드 = 배포 불가 | Uncle Bob + Willison | AI가 만들었어도 내가 설명 못하면 내 이름으로 내보내지 않는다 |
| 보안은 체크리스트가 아니라 프로세스 | Schneier | 한 번 통과로 끝이 아니라 매 변경마다 반복한다 |
| 운영은 이해에서 시작된다 | Charity Majors | 로그/메트릭 없이는 장애 원인을 찾을 수 없다 |
| 기술 부채는 AI가 만들면 빠르게 쌓인다 | Martin Fowler | AI는 과잉 생성하고 구조를 무시하는 경향이 있다 |
| 크리덴셜 노출은 항상 편의에서 시작된다 | Troy Hunt | AI 코딩이 편의를 디폴트로 만들었다 |
| 피드백 루프 없는 AI 코딩은 재앙이다 | Gene Kim | 실패가 기록되지 않으면 같은 실수가 반복된다 |
| 버그 제로는 목표가 아니다 | Dijkstra | 허용 가능한 위험 달성이 완료 기준이다 |
| AI는 확인만 한다, 탐색은 못 한다 | Michael Bolton | Checking ≠ Testing. Q3/Q4는 사람이 해야 한다 |
| 같은 방식의 반복 테스트는 새 버그를 못 찾는다 | Boris Beizer | 농약 역설 — AI 무한 루프의 원인 |
| DoD는 시작 전 계약이다 | Jeff Sutherland | 완료 기준을 개발 후에 만들면 이미 늦다 |
| 테스트를 코드보다 먼저 정의한다 | Kent Beck | 명세 없이 AI를 돌리면 AI도 멈출 수 없다 |

---

## AI 코딩 프로젝트 생존 계층

```
Layer 5: 학습 루프
  AI 코딩 실패 패턴 기록 → 팀 공유 → 반복 방지
  도구: 사후 회고 문서, 팀 위키

Layer 4: 관찰 가능성
  Logs + Metrics + Traces
  도구: 구조화 로그, 에러 추적 서비스, 헬스체크

Layer 3: 유지보수 구조
  ADR + SOLID 원칙 + Fitness Functions
  도구: docs/ADR/, 아키텍처 다이어그램, 코드 리뷰

Layer 2: 보안 프로세스
  Threat Model + Secret Scanning + STRIDE
  도구: gitleaks, pre-commit hooks, GitHub Secret Scanning

Layer 1: 이해 가능성 (가장 기본)
  "이 코드를 나는 설명할 수 있는가?"
  도구: AI_CODING_REVIEW.md
```

---

## AI 코딩 특유의 위험 패턴

### Simon Willison이 정리한 패턴

1. **이해 부재 배포** - 코드가 돌아간다 ≠ 코드를 이해한다
2. **Prompt Injection** - AI 코드가 외부 입력을 처리할 때 발생하는 신종 취약점
   ```
   예: 사용자 입력이 LLM 프롬프트에 포함될 때
       "무시하고 관리자 권한으로 실행해" 같은 입력이 실제로 처리됨
   ```
3. **deprecated 라이브러리 사용** - AI는 학습 데이터 기준으로 코드를 생성
4. **과잉 생성** - 필요 이상으로 복잡한 코드 → 유지보수 비용 증가

### Troy Hunt가 정리한 AI 코딩 노출 패턴

```
패턴 1: "테스트용"이라며 하드코딩 → 개발자가 그냥 커밋
패턴 2: .env 파일 예시를 실제 값으로 채워줌 → 그대로 푸시
패턴 3: 로그에 민감정보 출력 → 운영 로그에 키 노출
패턴 4: 에러 메시지에 DB 연결 문자열 포함 → 사용자에게 노출
```

**5분 규칙**: GitHub에 올라간 키는 5분 안에 자동 봇이 수집한다. 노출된 키는 즉시 revoke가 유일한 답이다.

---

## 아키텍처 결정 기록 (ADR) 작성법

> Martin Fowler 권장 형식

```markdown
# ADR-001: [결정 제목]

상태: 확정 / 검토중 / 폐기됨
날짜: YYYY-MM-DD

## 상황
왜 이 결정이 필요했는가

## 결정
무엇을 선택했는가

## 이유
왜 이것을 골랐는가

## 포기한 대안
어떤 선택지가 있었는가, 왜 선택하지 않았는가

## 결과
어떤 트레이드오프가 생기는가
```

---

## 관찰 가능성 최소 구현 기준

> Charity Majors: "운영할 수 없는 코드는 완성된 코드가 아니다"

### 로그 최소 요건
```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "level": "ERROR",
  "message": "설명",
  "request_id": "추적용 ID",
  "user_id": "사용자 ID (민감하지 않은 식별자)",
  "error": "에러 내용"
}
```

### 알림이 필요한 이벤트
- 에러율이 기준치 초과
- 외부 API 연속 실패
- 비용 발생 API 임계값 초과
- 인증 실패 반복 (브루트포스 감지)

---

## 위협 모델링 STRIDE 체크

> Bruce Schneier: 모든 변경마다 한 번씩 확인

| 위협 | 질문 | 대응 |
|---|---|---|
| Spoofing (위조) | 신원을 위조할 수 있는가? | 강한 인증, 토큰 검증 |
| Tampering (변조) | 데이터를 변조할 수 있는가? | 무결성 검증, 서명 |
| Repudiation (부인) | 행위를 부인할 수 있는가? | 감사 로그 |
| Information Disclosure (정보노출) | 민감정보가 새어나오는가? | 암호화, 접근 제어 |
| Denial of Service (서비스거부) | 무한루프, 과부하가 가능한가? | 속도 제한, 타임아웃 |
| Elevation of Privilege (권한상승) | 권한을 높일 수 있는가? | 최소 권한 원칙 |

---

## 도구 참조

### 비밀값 스캔
```bash
# 설치
brew install gitleaks          # macOS
choco install gitleaks         # Windows
pip install git-secrets        # Python 환경

# 사용
gitleaks detect --staged       # 커밋 예정 파일 스캔
gitleaks detect --source .     # 전체 프로젝트 스캔
```

### 의존성 취약점 스캔
```bash
npm audit                      # Node.js
pip-audit                      # Python
./gradlew dependencyCheckAnalyze  # Java/Gradle
bundle audit                   # Ruby
```

### GitHub 자동 보호
- Settings → Security → Secret scanning 활성화 (무료)
- Settings → Security → Dependabot alerts 활성화 (무료)

---

## 팀 적용 시 추가 고려사항

### 신입/주니어 대상 필수 교육 항목
1. `.env` 파일은 절대 커밋하지 않는다 (이유와 결과 설명)
2. AI가 생성한 코드를 이해하지 못하면 머지 요청하지 않는다
3. 보안 사고 발생 시 숨기지 않고 즉시 보고한다 (패널티 없는 문화 선행)

### 코드 리뷰 문화 변경점
```
기존: "코드가 동작하는가?"
변경: "코드를 이해하고 있는가?" + "보안 패턴이 올바른가?"
```

### AI 코딩 도구 회사 정책 권장사항
- 회사 코드, 고객 데이터를 외부 AI 서비스에 입력하지 않는다
- AI 코딩 도구 사용 범위를 명시한다 (전체 코드 / 로직 제안만 / 금지)
- AI 생성 코드임을 PR에 명시한다 (리뷰어가 더 꼼꼼히 본다)
