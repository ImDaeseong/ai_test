# Security Rules

> 복사 위치: 프로젝트 루트 `/SECURITY_RULES.md`
> 사용 시점: 커밋/푸시 전, 유료 API 도입 전
> 원칙: API 키·비밀값·내부 정보는 코드가 아니라 사람이 지킨다 — 체크리스트로 강제한다

---

## Never Store (절대 저장 금지)

- API 키, 토큰, 비밀번호
- DB 접속 정보, 서버 주소, 내부망 정보
- 회사 소스코드, 회사 내부 문서, 고객 정보
- 개인 주민등록번호, 결제 정보, 민감한 건강 정보

---

## API Key 관리 규칙

```
✅ 올바른 방법:
  .env 파일에만 저장 (gitignore 처리됨)
  API_KEY_NAME=값

❌ 금지:
  설정 파일에 직접 작성
  소스 코드에 하드코딩
  README.md에 예시로 실제 값 포함
  output/ 폴더 결과물에 포함
```

### `.env.example` 관리 원칙

`.env.example`은 이 프로젝트에서 실제로 쓰는 키 이름만, 값 없이 포함한다.

```
# .env.example
API_KEY_NAME=
```

---

## Allowed (저장 가능)

- 개인 AI 실험/작업 기록
- 개인 학습 메모
- 일반화된 개발 패턴
- 공개 자료 기반 정리
- 회사 정보가 제거된 추상화된 회고

---

## Commit 전 체크리스트

```text
변경 파일 목록:
API 키/비밀값 포함 여부:
.env 파일이 변경 목록에 포함 여부:
회사/고객 정보 포함 여부:
공개 저장소로 공개되어도 안전한 수준인지:
추가 확인이 필요한 파일:
```

### 확인 명령어

```bash
# API 키 패턴 검색 (커밋 전 반드시 실행)
git diff --staged | grep -iE "api_key|password|secret|token"

# .env 파일이 staged에 없는지 확인
git diff --staged --name-only | grep ".env$"
```

---

## Cost Boundary (비용 관리)

유료 AI 도구 사용 전 기록:

```text
도구 이름:
월 비용:
필요한 이유:
무료 대안:
이번 달 비용 한도 안에 있는가:
결정: 보류 / 1회 테스트 / 결제
```
