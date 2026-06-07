# 3곡 검증 기반 설계 개선 V3

## 1. 문서 지위

이 문서는 `UPGRADE`, `디저트`, `떠나고 싶어` 실제 데이터 검증 결과를
재사용 프로그램 설계에 반영한 V3 보강 규칙이다.

구현 시 문서 우선순위는 다음과 같다.

1. `16_THREE_SONG_DESIGN_IMPROVEMENTS_V3.md`
2. `10_DATA_CONTRACTS_V2.md`
3. `09_REUSABLE_PROGRAM_ARCHITECTURE.md`
4. 기존 배경·사례 문서

이 문서와 기존 문서가 충돌하면 이 문서를 적용한다. 세 곡에서 관찰된
곡명, 패널 번호, 패널 수, 타임코드는 회귀 fixture의 기대값일 뿐 제품
코드의 조건값이 아니다.

## 2. 세 곡에서 확인된 일반 문제

| 관찰 | 일반화해야 할 문제 |
|---|---|
| 곡마다 이미지 수와 음원 길이가 다름 | 패널 수와 컷 길이 동적 계산 |
| 스토리보드 계획 시간이 실제 음원보다 길거나 짧음 | 권장 시간은 가중치로만 사용 |
| 파일명 섹션과 패널 내부 섹션이 다름 | 필드별 출처 우선순위와 충돌 기록 |
| `Verse 1/2`, `Final Chorus`가 파일명에서 축약됨 | canonical type과 원래 의미를 함께 보존 |
| LRC/SRT에 Suno 연주 지시문이 포함됨 | 화면 가사와 분석 metadata 분리 |
| 다음 타임태그까지 수십 초 늘어난 cue가 있음 | 상대 통계 기반 이상 cue 탐지 |
| 정상 자막도 존재함 | WhisperX 선택 실행 |
| LRC/SRT에 Outro 태그가 빠질 수 있음 | 오디오 시작·종료 잔여 구간 복원 |
| 이미지 해상도가 조금씩 다름 | 이미지별 fit/crop 결정 |
| 일부 섹션의 컷이 8초를 조금 넘음 | 반복보다 모션 분할 우선 |

## 3. 하드코딩 금지 계약

### 제품 코드에 넣으면 안 되는 값

- 특정 곡 제목 또는 폴더명
- 특정 패널 수
- 특정 패널 번호 범위
- 특정 cue 번호
- 특정 곡의 시작·종료 밀리초
- 특정 섹션의 고정 반복 횟수
- 특정 파일 UUID
- 특정 이미지 해상도
- 세 곡에서 계산된 평균값

다음 형태는 제품 코드와 기본 설정에서 금지한다.

```python
if title == "sample song":
    ...

if panel_count == 42:
    ...

if cue.index == 44:
    ...

OUTRO_START_MS = 175054
```

샘플 고유 값은 `tests/fixtures/<fixture_id>/expected/` 아래 기대 결과에서만
사용할 수 있다.

### 허용되는 설정

설정에는 곡이 아니라 정책을 넣는다.

```yaml
clips:
  min_seconds: 2.5
  preferred_min_seconds: 4.0
  preferred_max_seconds: 8.0
  hard_max_seconds: 12.0

subtitles:
  long_cue:
    median_multiplier: 2.5
    absolute_floor_seconds: 10.0
  alignment:
    mode: auto
    hold_on_unresolved_long_cue: true

sections:
  synthesize_edge_instrumentals: true
  preserve_original_label: true
```

정책 임계값은 설정 스키마로 관리하고 실행 manifest에 설정 해시를 남긴다.

## 4. 필드별 출처 결정

파일 전체에 하나의 우선순위를 적용하지 않고 필드별로 결정한다.

### 패널 식별

1. `panel_NNN` 번호
2. 패널 문서의 컷 번호
3. 스토리보드 행 번호

번호가 서로 다르면 자동 병합하지 않고 `PANEL_ID_CONFLICT`를 생성한다.

### 섹션 정체성

1. 패널 문서 내부의 명시적 섹션
2. 스토리보드 테이블의 섹션
3. 파일명의 섹션 토큰

파일명은 탐색 힌트일 뿐 의미의 최종 출처가 아니다. 각 선택에는 선택된
값, 후보 값, 출처, 충돌 여부를 기록한다.

### 권장 지속 시간

1. 패널 문서의 유효한 권장 시간
2. 스토리보드 테이블의 유효한 시간
3. 정책 기본 가중치

권장 시간은 타임코드가 아니라 동일 섹션 내부 배분 가중치다.

## 5. 섹션 모델 개선

canonical type만 저장하면 `Verse 1/2`와 `Final Chorus` 의미가 손실된다.
다음 필드를 모두 유지한다.

```json
{
  "label": "Final Chorus",
  "canonical_type": "chorus",
  "variant": "final",
  "ordinal": 2,
  "occurrence": 2,
  "source": "panel_document",
  "confidence": 1.0
}
```

- `label`: 원문 라벨
- `canonical_type`: 렌더 정책에 사용하는 일반 유형
- `variant`: `final`, `pre`, `post` 등 의미 보조값
- `ordinal`: 라벨에 명시된 번호
- `occurrence`: 실제 등장 순서

`Verse`, `Verse 1`, `Verse 2`는 같은 canonical family에 속하지만 서로 다른
section instance다. `Final Chorus`도 일반 Chorus와 자동 합치지 않는다.

## 6. 가장자리 구간 복원

첫 자막이 0초보다 늦거나 마지막 자막이 음원 종료보다 빠를 수 있다.
고정 시간값 없이 다음과 같이 처리한다.

```text
leading_gap = first_timed_event_start - audio_start
trailing_gap = audio_end - last_lyric_or_section_end
```

### 선행 구간

- 원문 또는 스토리보드에 Intro/Instrumental이 있으면 해당 구간으로 생성
- 둘 다 없으면 `synthetic_intro` 후보를 생성
- 음성 활동 분석에서 보컬이 감지되면 단순 Instrumental로 확정하지 않음

### 후행 구간

- 원문 또는 스토리보드에 Outro가 있으면 누락된 timed section을 복원
- 근거가 없으면 `synthetic_tail`로 보존하고 `REVIEW` 표시
- 마지막 가사 문장을 오디오 끝까지 자동 연장하지 않음

생성된 섹션은 반드시 다음 정보를 가진다.

```json
{
  "boundary_source": "audio_edge_gap",
  "synthetic": true,
  "evidence": ["song_source:outro", "audio_end"],
  "review_required": false
}
```

## 7. 자막 품질 평가와 정렬 라우팅

WhisperX를 모든 곡에 실행하지 않는다. 먼저 LRC/SRT 품질을 계산하고
필요한 경로로 보낸다.

### cue 이상 점수

다음 특징을 조합한다.

- cue 길이와 해당 곡 가사 cue 중앙값의 비율
- 설정된 절대 최소 장기 cue 기준
- 글자 수 대비 표시 시간
- 다음 섹션 이벤트까지의 비정상 공백
- LRC와 SRT 시간 차이
- 원문 가사 시퀀스 일치도
- 음성 활동 구간과 cue의 겹침

특정 cue 번호나 특정 초를 검사하지 않는다.

### 라우팅 상태

| 상태 | 조건 | 처리 |
|---|---|---|
| `NORMALIZE_ONLY` | 가사 순서와 시간 품질이 정상 | metadata 제거 후 사용 |
| `ALIGN_RECOMMENDED` | 경미한 장기 cue 또는 경계 불확실 | preview 허용, 검수 표시 |
| `ALIGN_REQUIRED` | 심각한 장기 cue, Remix/Extend 불일치 | WhisperX/Demucs 경로 |
| `HOLD` | 정렬 후에도 신뢰도 부족 | 사람 승인 전 최종 렌더 금지 |

Demucs 사용 여부도 곡명으로 결정하지 않는다. 혼합 음원에서 보컬 정렬
신뢰도가 기준 이하일 때만 분리 어댑터를 호출한다.

## 8. 패널 시간 배분

### 1단계: 섹션 길이 결정

명시 sidecar, timed section, 가사 정렬, 스토리보드 가중치 순으로 구한다.

### 2단계: 섹션 내부 가중 배분

```text
panel_duration =
  section_duration * panel_weight / sum(section_panel_weights)
```

계산 결과를 정책 범위와 비교한다.

### 3단계: 너무 긴 컷

1. `preferred_max` 이하지만 그대로 사용
2. `preferred_max` 초과, `hard_max` 이하면 모션 phase로 분할
3. `hard_max` 초과면 같은 섹션 패널 재사용 또는 추가 이미지 필요 경고

모션 phase 분할은 동일 이미지를 파일상 반복하지 않고 하나의 clip 안에서
zoom/pan 방향을 바꾸는 방식이다.

### 4단계: 너무 짧은 컷

1. 섹션 첫·마지막 패널 보존
2. 패널 타입 다양성 보존
3. 인접 유사 패널 제외 후보 생성
4. 자동 제외 정책이 꺼져 있으면 `REVIEW_REQUIRED`

섹션의 이미지를 다른 섹션으로 임의 이동하지 않는다.

## 9. 이미지 정규화

곡 단위의 대표 해상도를 가정하지 않고 이미지별로 probe한다.

각 이미지에 다음 값을 계산한다.

```json
{
  "source_width": 1662,
  "source_height": 946,
  "source_ratio": 1.7569,
  "target_ratio": 1.7778,
  "fit": "cover",
  "crop_risk": "low"
}
```

허용 fit 정책:

- `cover`
- `contain_blur`
- `contain_color`
- `smart_crop`

원본 이미지는 리사이즈하거나 덮어쓰지 않는다.

## 10. 상태 모델 정리

자산 준비 상태와 검수 상태를 한 enum에 섞지 않는다.

```json
{
  "readiness": "BUILD_READY",
  "review_state": "WARNINGS",
  "alignment_state": "NORMALIZE_ONLY"
}
```

### readiness

```text
PROMPTS_ONLY
IMAGES_READY
MEDIA_READY
BUILD_READY
BLOCKED
```

### review_state

```text
CLEAN
WARNINGS
REVIEW_REQUIRED
HOLD
HUMAN_APPROVED
```

`BUILD_READY_WITH_WARNINGS` 같은 합성 문자열은 저장하지 않는다.

## 11. 데이터 계약 추가

### Panel Resolution

```json
{
  "panel_id": "panel_020",
  "section": {
    "selected": "Drop",
    "source": "panel_document",
    "candidates": [
      {"value": "Drop", "source": "panel_document"},
      {"value": "Drop", "source": "storyboard"},
      {"value": "Chorus", "source": "filename"}
    ],
    "conflict": true
  }
}
```

### Subtitle Quality

```json
{
  "lyric_cue_count": 30,
  "median_duration_ms": 3630,
  "long_cue_count": 1,
  "sequence_match_score": 0.94,
  "alignment_route": "ALIGN_REQUIRED",
  "reasons": ["duration_outlier", "section_gap_overlap"]
}
```

### Clip Motion Phases

```json
{
  "clip_id": "clip_001",
  "duration_ms": 8900,
  "motion_phases": [
    {"start_ratio": 0.0, "end_ratio": 0.55, "preset": "slow_zoom_in"},
    {"start_ratio": 0.55, "end_ratio": 1.0, "preset": "subtle_pan_right"}
  ]
}
```

예시 숫자는 스키마 형식 설명용이며 정책 조건이 아니다.

## 12. 오류 코드 추가

| 코드 | 심각도 | 의미 |
|---|---|---|
| `PANEL_ID_CONFLICT` | HOLD | 번호 출처 간 불일치 |
| `PANEL_SECTION_CONFLICT` | WARNING | 파일명과 내부 섹션 불일치 |
| `SECTION_LABEL_LOSS` | WARNING | 축약 파일명으로 세부 의미 손실 |
| `SYNTHETIC_EDGE_SECTION` | INFO/REVIEW | 전주·후주 섹션 복원 |
| `LONG_CUE_OUTLIER` | REVIEW/HOLD | 곡 내부 분포 대비 비정상 cue |
| `ALIGNMENT_REQUIRED` | HOLD | 강제 정렬 필요 |
| `IMAGE_RATIO_VARIANCE` | INFO/WARNING | 이미지별 비율 차이 |
| `PREFERRED_CLIP_DURATION_EXCEEDED` | INFO | 모션 phase 적용 |
| `HARD_CLIP_DURATION_EXCEEDED` | REVIEW | 반복 또는 이미지 추가 필요 |

## 13. 결정론과 캐시

결과 캐시 키:

```text
input file hashes
+ normalized configuration hash
+ schema version
+ application version
+ optional alignment model version
```

절대 경로, 실행 시각, 곡 표시 제목은 타임라인 결정 키에서 제외한다.
같은 내용을 다른 폴더명으로 복사해도 상대 자산 구조가 같으면 동일한
계획 결과를 만들어야 한다.

## 14. 하드코딩 방지 자동 검증

### 소스 정적 검사

- fixture 곡 제목이 `src/`와 `remotion/src/`에 나타나면 실패
- fixture UUID가 제품 코드에 나타나면 실패
- 샘플 패널 수와 음원 길이가 조건문 상수로 나타나면 검토 실패
- 절대 사용자 경로가 코드·설정·산출물에 나타나면 실패

### 변형 테스트

1. 곡 폴더명과 title을 임의 문자열로 변경
2. 모든 cue를 같은 양만큼 이동
3. 패널 수를 늘리거나 줄인 합성 fixture 생성
4. 이미지 해상도를 일부 변경
5. LRC만 또는 SRT만 남김
6. 섹션 라벨을 alias로 변경

기대 결과:

- 제목 변경은 타임라인 구조에 영향을 주지 않는다.
- cue 이동은 경계도 같은 양만큼 이동시킨다.
- 패널 수 변경은 duration allocator만 변경한다.
- 이미지 해상도 변경은 fit 결정만 변경한다.
- 자막 형식 변경은 동일한 정규화 모델로 수렴한다.

## 15. 구현 반영 순서

1. readiness/review/alignment 상태 분리
2. panel field provenance와 conflict 모델 구현
3. section identity 확장
4. edge gap 기반 Intro/Outro 복원
5. subtitle quality scorer와 alignment router
6. motion phase를 포함한 duration allocator
7. 이미지별 fit 결정
8. 하드코딩 정적 검사와 변형 테스트
9. 세 곡 fixture 회귀 테스트
10. 추가 곡을 같은 registry에 누적

## 16. 구현 시작 판정

```text
설계 개선 상태: READY
프로그램 구현 상태: NOT IMPLEMENTED
현재 실제 검증 곡: 3
최종 재사용성 출시 게이트: 최소 5곡 end-to-end
```

세 곡으로 구현을 시작하기에는 충분하다. 추가 곡은 구현을 미루는 조건이
아니라 회귀 범위를 넓히고 출시 게이트를 충족하는 입력으로 사용한다.
