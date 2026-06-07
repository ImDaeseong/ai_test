# ai-webtoon_capcut 설계 문서

## 프로젝트 목적

`ai-webtoon`의 스토리보드, 이미지, 음악, LRC/SRT를 읽어 음악 길이에 맞는
편집 타임라인을 만들고 Remotion 초벌 영상과 CapCut 전달 패키지를 생성한다.

## 현재 상태

- 설계: `IMPLEMENTATION READY`
- 분석·계획 MVP: `IMPLEMENTED`
- 전체 영상 자동화: `HOLD`
- 실제 분석: 3곡
- end-to-end 렌더 검증: 미실행
- 최종 재사용성 판정: `HOLD`
- 출시 기준: 서로 다른 실제 곡 최소 5개를 동일 코드와 명령으로 처리

현재 3곡으로 구현을 시작할 수 있다. 추가 곡은 구현을 미루는 조건이 아니라
회귀 범위와 출시 검증을 확대하는 입력으로 사용한다.

## Hermes 작업 시작 순서

새 설계, 계획, 구현 또는 큰 변경 전에는 다음 문서를 먼저 확인한다.

```text
CLAUDE.md
-> PROJECT_START.md
-> SECURITY_PLAN.md
-> TESTING_DONE_CRITERIA.md
-> AI_CODING_REVIEW.md
-> HANDOFF.md
```

검증 없이 완료라고 표시하지 않는다. 자동 테스트는 checking이며, CapCut
체감 싱크와 공개 품질은 사람이 testing해야 한다.

## 구현 문서 우선순위

```text
16_THREE_SONG_DESIGN_IMPROVEMENTS_V3
-> 10_DATA_CONTRACTS_V2
-> 09_REUSABLE_PROGRAM_ARCHITECTURE
-> 11_IMPLEMENTATION_BLUEPRINT_V2
-> 12_REUSABILITY_VALIDATION_MATRIX
-> 17_MULTI_SONG_VALIDATION_REGISTRY
-> 01~08 배경·원칙·사례 문서
```

V3와 기존 문서가 충돌하면 V3를 적용한다. 샘플 곡의 패널 수, cue 번호,
타임코드, 파일 UUID는 회귀 fixture 값이며 제품 코드의 상수가 아니다.

## 주요 문서

| 문서 | 역할 |
|---|---|
| `09_REUSABLE_PROGRAM_ARCHITECTURE.md` | 다곡 탐색, 섹션 추론, 동적 타임라인 |
| `10_DATA_CONTRACTS_V2.md` | manifest, inventory, subtitle, section, timeline 계약 |
| `11_IMPLEMENTATION_BLUEPRINT_V2.md` | CLI, 모듈, 구현 순서 |
| `12_REUSABILITY_VALIDATION_MATRIX.md` | 자동·수동·출시 검증 |
| `13_DESIGN_AUDIT_AND_MIGRATION.md` | 단일 곡 방식에서 일반 설계로의 변경 |
| `14_DESSERT_DATASET_ANALYSIS.md` | 두 번째 실제 곡 분석 |
| `15_LEAVE_DATASET_ANALYSIS.md` | 세 번째 실제 곡 분석 |
| `16_THREE_SONG_DESIGN_IMPROVEMENTS_V3.md` | **최우선:** 3곡 기반 일반화와 하드코딩 방지 |
| `17_MULTI_SONG_VALIDATION_REGISTRY.md` | 추가 곡 누적 검증 현황과 절차 |
| `08_SUNO_SUBTITLE_NORMALIZATION.md` | Suno 가사·연주 지시 분류 |
| `07_REFERENCES.md` | WhisperX, Demucs, Suno Extend 근거 |

프로젝트 루트의 Hermes 문서:

- `PROJECT_START.md`: 목적, 보안 경계, 아키텍처 결정
- `SECURITY_PLAN.md`: 위협과 원본 보호
- `TESTING_DONE_CRITERIA.md`: 인수 조건과 중단 기준
- `AI_CODING_REVIEW.md`: AI 생성 코드 검수
- `PRE_DEPLOY.md`: 배포 게이트와 롤백
- `HANDOFF.md`: 다음 세션 재개 정보

## 3곡 검증에서 반영된 개선

- 이미지 수와 음원 길이는 실행 시 탐색·계산
- 스토리보드 권장 시간은 절대 타임코드가 아니라 배분 가중치
- 패널 내부 섹션, 스토리보드, 파일명 후보를 비교하고 출처 기록
- `Verse 1/2`, `Final Chorus`의 원래 의미 보존
- 누락된 Intro/Outro를 오디오 가장자리와 원문 구조로 복원
- Suno 대괄호 지시문과 화면 가사 분리
- 장기 cue를 cue 번호가 아닌 곡 내부 통계로 탐지
- 정상 자막은 정규화만 하고 문제가 있는 곡만 WhisperX로 라우팅
- Remotion MP4는 기본적으로 자막을 굽지 않고 CapCut용 SRT를 별도 제공
- 이미지마다 해상도와 종횡비를 검사해 fit 결정
- 긴 컷은 반복보다 모션 phase 분할 우선
- 준비 상태, 검수 상태, 자막 정렬 상태를 별도 필드로 관리
- 곡명 변경, cue 이동, 패널 수 변경을 이용한 하드코딩 방지 테스트

## 핵심 원칙

```text
생성됨 != 검증됨
자동 정렬됨 != 정확함
렌더링 성공 != 편집 품질 PASS
```

1. 원본 input/output은 읽기 전용이다.
2. 음악 길이가 최종 타임라인의 절대 종료 기준이다.
3. 곡명, 패널 수, 섹션 범위, cue 번호, 시간 경계를 하드코딩하지 않는다.
4. 모든 추론값에 source, confidence, evidence를 기록한다.
5. 파일명은 의미의 최종 출처가 아니라 탐색 힌트다.
6. 강제 정렬은 품질 점수에 따라 선택 실행한다.
7. 낮은 신뢰도의 자막과 섹션은 자동 승인하지 않는다.
8. Remotion은 합성·렌더 엔진, CapCut은 최종 검수 도구로 사용한다.
9. pyCapCut과 CapCut 비공개 포맷은 MVP 필수 의존성으로 두지 않는다.
10. 같은 입력 해시와 설정은 같은 타임라인을 생성해야 한다.

## 목표 사용 흐름

```text
input/{노래명} 곡 탐색
-> 자산 inventory와 원본 해시
-> 패널·섹션 provenance 해결
-> LRC/SRT 품질 평가와 Suno metadata 분리
-> 필요 시 WhisperX/Demucs 정렬
-> 오디오 가장자리 Intro/Outro 복원
-> 동적 timeline.json 생성
-> Remotion 미리보기
-> QA 보고서와 CapCut 전달 패키지
-> 사람 최종 검수
```

## 표준 입출력 구조

```text
ai-webtoon_capcut/
├─ input/
│  └─ {노래명}/
│     ├─ 01_storyboard.md
│     ├─ img/
│     ├─ panels/
│     ├─ {음악}.wav
│     └─ {자막}.srt 또는 {자막}.lrc
└─ output/
   └─ {노래명}/
      └─ {run_id}/
         ├─ manifest.json
         ├─ timeline/
         ├─ subtitles/
         ├─ reports/
         ├─ render/
         │  └─ preview.mp4
         └─ handoff/
            ├─ subtitles-original.srt
            ├─ subtitles-aligned.srt
            └─ timeline.json
```

기본 실행:

```powershell
.\scripts\install-renderer.ps1
.\scripts\webtoon-capcut.ps1 inspect --song "UPGRADE"
.\scripts\webtoon-capcut.ps1 build --song "UPGRADE"
.\scripts\webtoon-capcut.ps1 render --song "UPGRADE" --profile preview
.\scripts\webtoon-capcut.ps1 build-all --ready-only
```

자막 시간이 불안정한 곡은 먼저 자동 보정한다. 기본값은 Demucs 보컬 분리 후
WhisperX 정렬이며 CPU에서는 오래 걸릴 수 있다.

```powershell
.\scripts\install-alignment.ps1
.\scripts\webtoon-capcut.ps1 align --song "UPGRADE"
```

CapCut에서는 `subtitles-aligned.srt`를 먼저 가져온 뒤 귀로 들으며 최종
조정한다. Remotion에 자막을 굽는 검토 영상이 필요한 경우에만 다음을 사용한다.

```powershell
.\scripts\webtoon-capcut.ps1 render --song "UPGRADE" --burn-subtitles
```

Windows에서는 프로젝트 루트의 `webtoon-capcut.bat`을 더블클릭해 메뉴를
사용할 수 있다. 콘솔에서는 인자를 직접 전달할 수 있다.

```bat
webtoon-capcut.bat build --song "UPGRADE"
webtoon-capcut.bat render --song "UPGRADE"
webtoon-capcut.bat build-all --ready-only
webtoon-capcut.bat discover
```

`--song-dir`, `--input-root`, `--output-root`로 다른 위치도 지정할 수 있다.
원본 `input/`은 읽기 전용으로 취급하고 생성 결과는 `output/`에만 기록한다.

## 검증 현황

| fixture | 주요 검증 특성 |
|---|---|
| `fixture_upgrade` | 긴 연주 구간, 프롬프트 블록, 장기 cue |
| `fixture_dessert` | 45장, 섹션 충돌, 장기 cue, 혼합 해상도 |
| `fixture_leave` | 30장, 긴 전주·후주, 누락 Outro, 축약 섹션 |

남은 최소 2곡은 가능하면 LRC만/SRT만, 50장 이상, Remix/Extend,
비표준 섹션, 혼합 이미지 포맷 같은 아직 검증되지 않은 특성을 포함한다.

## 비목표

- 이미지 또는 AI 영상 생성
- CapCut 비공개 초안 포맷 직접 수정
- 자동 정렬 결과를 사람 확인 없이 최종 승인
- 모든 자막을 무조건 자동 승인
- 원본 폴더 대량 재작성
- 곡별 예외 코드를 제품 소스에 추가
- 유료 API를 기본 실행 경로로 강제
