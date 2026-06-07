# Hermes 최종 재검수

검수일: 2026-06-06

## 판정

- Hermes 필수 문서와 자동 품질 게이트: `PASS`
- 분석·정규화·타임라인 생성 MVP: `PASS WITH LIMITATIONS`
- Remotion/CapCut을 포함한 전체 영상 자동 제작: `HOLD`
- 공개·배포: `HOLD`

자동 검사 통과와 영상 제작 완료는 같은 의미가 아니다. 현재 소스는 재사용 가능한
분석·편집 계획을 만들지만, 실제 렌더와 사람 검수는 아직 완료되지 않았다.

## 필수 문서

- [x] `CLAUDE.md`
- [x] `PROJECT_START.md`
- [x] `SECURITY_PLAN.md`
- [x] `.env.example`
- [x] `TESTING_DONE_CRITERIA.md`
- [x] `AI_CODING_REVIEW.md`
- [x] `PRE_DEPLOY.md`
- [x] `HANDOFF.md`
- [x] `docs/ADR/ADR-001-PLANNER-RENDERER-SEPARATION.md`

## 자동 검증

- `scripts/test.ps1`: 30개 테스트 통과
- `scripts/validate-project.ps1`: `HERMES_PROJECT_VALIDATION_PASS`
- 곡명 fixture 하드코딩 검사: 통과
- 공개 JSON의 사용자 절대경로 검사: 통과
- `.env.example` 비밀값 검사: 통과

## 실제 데이터 회귀

| 곡 | 클립 | 음원/종료(ms) | gap | invalid | 최소 클립(ms) | 판정 |
|---|---:|---:|---:|---:|---:|---|
| UPGRADE | 42 | 242952/242952 | 0 | 0 | 4834 | HOLD, ALIGN_REQUIRED |
| 디저트 | 45 | 189360/189360 | 0 | 0 | 3016 | HOLD, ALIGN_REQUIRED |
| 떠나고 싶어 | 30 | 193152/193152 | 0 | 0 | 4487 | WARNINGS, NORMALIZE_ONLY |

전체 output 탐색:

- 총 214곡
- `BUILD_READY`: 3
- `PROMPTS_ONLY`: 210
- `BLOCKED`: 1
- 공개 결과 절대경로 노출: 없음

표준 실행 경로는 `input/{노래명}`을 읽고
`output/{노래명}/{run_id}`에 결과를 생성한다.

현재 `input`에는 검증곡 3개가 준비되어 있으며 기본 `discover`에서 모두
`BUILD_READY`로 확인됐다. `build --song "디저트"`의 실제 output 생성도 통과했다.

## 추가 검수에서 수정한 결함

1. Suno의 같은 시각 `Instrumental/Verse` 태그가 0ms 클립을 만들던 문제
2. `Chorus/Drop`처럼 장르별 섹션 태그가 밀집되어 50ms 클립을 만들던 문제
3. 밀집 태그 연쇄의 마지막 경계가 곡 앞부분 전체를 수백 ms로 압축하던 문제
4. PowerShell 검증 스크립트의 UTF-8 처리 문제
5. inspect/discover 공개 결과의 로컬 절대경로 노출

경계 처리는 특정 곡명이나 장르 조합이 아니라, 패널 수와 최소 실사용 시간을 기준으로
밀집 경계 묶음을 탐지하고 가중 재분배하도록 일반화했다.

## 남은 검증

- [x] Remotion 실제 preview와 음원 종료 프레임 검수
- [x] WhisperX 실제 곡 강제 정렬
- [x] Demucs 짧은 샘플 보컬 분리
- [ ] full 1080p 실제 곡 렌더
- [ ] CapCut 실제 import 및 자막·전환 체감 검수(Q3)
- [ ] 전체 곡 Demucs+WhisperX 결합 실행
- [ ] Suno mix/extend 곡의 정렬 실패 fallback 검증
- [ ] 네 번째·다섯 번째 곡 end-to-end
- [ ] MP3/FLAC/M4A ffprobe 지원
- [ ] 공개 전 사람 보안·성능 검수(Q4), secret history scan, rollback 확인

## 결론

프로그램 설계와 분석·타임라인 생성 소스는 다음 구현 단계에 사용할 수 있다. 다만
영상 자동 제작 완료로 승인할 수는 없으며, 위 사람·렌더·오디오 정렬 검증 전까지
전체 시스템과 배포 상태는 `HOLD`를 유지한다.

## 렌더·정렬 추가 검증

- `떠나고 싶어` preview: H.264/AAC, 960x540, 30fps
- 목표 193.152초, 영상 스트림 193.166667초로 1프레임 이내
- 기본 `burn_subtitles=false`
- 동일 클립 내 두 프레임 해시 차이로 이미지 모션 확인
- `디저트` WhisperX: 30 cue, invalid 0, 중앙 이동 20ms, 최대 이동 4770ms
- Demucs: 8초 샘플에서 `vocals.wav`, `no_vocals.wav` 생성
