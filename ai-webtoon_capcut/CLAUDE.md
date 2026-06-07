# CLAUDE.md - ai-webtoon_capcut

## 프로젝트 목적

Suno 기반 웹툰 이미지, 음악, LRC/SRT를 분석해 곡 길이와 일치하는 편집
타임라인과 CapCut 전달 패키지를 반복 생성하는 개인 로컬 CLI다.

## 절대 규칙

- `../ai-webtoon/input`과 `../ai-webtoon/output` 원본을 수정·삭제하지 않는다.
- API 키, 토큰, 비밀번호, 개인 절대 경로를 코드와 산출물에 저장하지 않는다.
- 곡명, 패널 수, cue 번호, 특정 타임코드를 제품 코드에 하드코딩하지 않는다.
- 파일명만으로 섹션 의미를 확정하지 않는다.
- `HOLD` 자막을 사람 승인 없이 최종 완료로 표시하지 않는다.
- Remotion/WhisperX/Demucs 미구현 상태를 구현 완료라고 표현하지 않는다.

## 파일 역할

| 파일/폴더 | 역할 | 수정 시 주의사항 |
|---|---|---|
| `src/webtoon_capcut/` | 분석·정규화·타임라인 CLI | fixture 곡명 금지 |
| `config/default.json` | 곡 독립 정책 | 특정 곡 값 금지 |
| `tests/` | 단위·통합·거버넌스 검사 | 실제 원본 변경 금지 |
| `input/` | 노래별 원본 입력 | 읽기 전용, Git 추적 금지 |
| `output/` | 노래별 실행 산출물 | Git 추적 금지 |
| `workspace/` | 이전 버전 산출물 | 신규 실행에서 사용하지 않음 |
| `docs/` | 설계·검증 근거 | V3 우선순위 유지 |

## 검증 명령

```powershell
.\scripts\test.ps1
.\scripts\webtoon-capcut.ps1 discover
.\scripts\webtoon-capcut.ps1 build --song "곡명"
.\scripts\validate-project.ps1
```

## 완료 기준

- 자동 테스트가 모두 통과한다.
- 세 검증 곡의 타임라인 시작은 0이고 gap은 0이다.
- 마지막 clip은 음원 종료와 1프레임 이내 일치한다.
- 제품 소스에 fixture 곡명과 샘플 시간값이 없다.
- 산출물에 개인 절대 경로와 비밀값이 없다.
- 사람 Q3/Q4 검수 전 상태는 `HOLD` 또는 `CONDITIONAL`로 남긴다.
