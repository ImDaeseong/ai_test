# HANDOFF - ai-webtoon_capcut

> **2026-08-17 정정**: 이 문서의 이전 버전은 Remotion 렌더, WhisperX/Demucs 정렬, CapCut
> handoff 자동 검증 스크립트, 테스트 45개 통과를 "완료"로 기록했으나, 실제 저장소 코드로
> 확인한 결과 해당 기능은 존재하지 않는다 — `remotion/`에는 `package.json`뿐이고 렌더
> 컴포지션 소스가 없고, CLI에 `render`/`align` 명령이 없고, `scripts/validate-capcut-handoff.ps1`
> 파일이 없고, 테스트는 14개다(`git log`상 이 문서와 `remotion/`은 2026-06-07 단일 import
> 커밋 이후 변경 이력이 없음 — 다른 환경의 작업 기록이 코드 없이 문서만 넘어온 것으로 보임).
> 아래는 코드 기준으로 정정한 내용이다. 향후 이 문서를 실제 진행 상황의 근거로 쓰지 말고,
> 항상 코드·테스트 실행 결과로 재확인한다.

## 현재 목표

곡별 하드코딩 없이 웹툰 이미지·음악·Suno 자막을 분석하고 편집 타임라인을
생성하는 재사용 CLI를 완성한다.

## 먼저 읽을 파일

1. `CLAUDE.md`
2. `README.md`
3. `IMPLEMENTATION.md`
4. `docs/16_THREE_SONG_DESIGN_IMPROVEMENTS_V3.md`
5. `TESTING_DONE_CRITERIA.md`
6. `AI_CODING_REVIEW.md`
7. `HERMES_REVIEW.md`

## 완료 (코드로 확인됨)

- Python 분석/계획 CLI: `discover / inspect / normalize / plan / build / build-all`
- WAV·이미지·스토리보드·LRC/SRT 분석
- 자막 품질 라우팅
- 동적 섹션·타임라인
- 3곡 회귀와 214곡 discover
- Hermes 필수 문서와 자동 검증 (`scripts/validate-project.ps1`)
- Suno 밀집 섹션 태그 연쇄의 일반화된 경계 재분배
- 기본 경로 `input/{노래명}` → `output/{노래명}/{run_id}`
- 더블클릭 메뉴와 명령 전달을 지원하는 `webtoon-capcut.bat`
- 단위 테스트 14개 (`tests/unit/`) 전량 PASS

## 미완료 (설계 범위 밖, 착수 전)

- Remotion 렌더러: `remotion/`에 `package.json`만 있고 컴포지션 소스·CLI `render` 명령 없음
- CapCut 패키징/handoff 자동화: 관련 코드·검증 스크립트 없음
- WhisperX/Demucs 자막 정렬: CLI `align` 명령 없음, `requirements-alignment.txt`는 있으나
  이를 사용하는 소스 코드 없음
- 위 셋 모두 사람 Q3/Q4 검수 이전 단계가 아니라 **구현 자체가 시작 전**

## 검증 명령

```powershell
.\scripts\test.ps1
.\scripts\validate-project.ps1
.\scripts\webtoon-capcut.ps1 build --song "곡명"
```

## 다음 단계

착수 순서는 정해진 바 없음. Remotion 렌더러/CapCut 패키징을 시작하려면 먼저 스펙(입출력
계약, 실패 처리, 검증 기준)을 잡고 `docs/`에 설계 문서를 추가한 뒤 진행한다.

## 알려진 판정

- 분석/계획 CLI: PASS
- Remotion 렌더러·CapCut 패키징: 착수 전 (HOLD)
- 공개/배포: HOLD
