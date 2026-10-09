# HANDOFF - ai-webtoon_capcut

> **이력**: 2026-08-17에는 Remotion 소스가 없다는 정정이 맞았다. 2026-10-09에 Python CLI `render`와 범용 편집기 `handoff`를 구현해 30초 1080p fixture로 검증했다. `align`과 CapCut 실제 import 검수는 아직 없다.
> 완료 판정은 항상 현재 코드와 검증 결과로 다시 확인한다.

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
- Python 단위 테스트 26개, Remotion typecheck, Python CLI→Remotion 30초 1080p 렌더와 범용 편집기 handoff 생성·무결성 검증 PASS

## 미완료 (설계 범위 밖, 착수 전)

- 실제 곡 1080p 검수: CLI `render` 통합은 PASS지만 실제 음원·전체 패널·라이선스 미디어 입력이 없음
- 범용 편집기 handoff: 생성·SHA-256·구성·경로 검증 완료. CapCut 전용 프로젝트 포맷과 실제 import 사람 검수는 없음
- WhisperX/Demucs 자막 정렬: CLI `align` 명령 없음, `requirements-alignment.txt`는 있으나
  이를 사용하는 소스 코드 없음
- WhisperX/Demucs 정렬과 CapCut 전용 자동화는 구현 시작 전이며, Remotion·범용 handoff는 실제 곡 사람 검수 단계

## 검증 명령

```powershell
.\scripts\test.ps1
.\scripts\validate-project.ps1
.\scripts\webtoon-capcut.ps1 build --song "곡명"
```

## 다음 단계

실제 음원·전체 패널·라이선스 미디어를 준비한 뒤 Python `render`로 1080p 렌더하고, 음악 싱크·크롭·자막·편집을 사람이 검수한다.

## 알려진 판정

- 분석/계획 CLI: PASS
- Python CLI→Remotion 1080p fixture·범용 handoff: PASS / 실제 곡 검수·CapCut import: HOLD
- 공개/배포: HOLD
