# Suno LRC/SRT 정규화 설계

## 1. 목적

Suno에서 생성하거나 다운로드한 LRC/SRT에는 다음 내용이 한 파일에 섞일 수 있다.

- 실제로 노래한 가사
- `[Intro]`, `[Verse]`, `[Chorus]` 같은 곡 구조 태그
- `[Guitar Solo]` 같은 연주 구간 태그
- `[Loud high-gain tube-amp feedback]` 같은 생성·연출 지시
- 드럼 카운트, 호흡, 함성처럼 실제 소리일 수도 있는 비가사 이벤트
- 정상 타임코드 가사 앞에 압축 삽입된 원본 Suno 프롬프트 블록

이 문서는 다른 Suno 곡에도 적용할 수 있는 분류와 정규화 규칙을 정의한다.

## 2. 확인된 UPGRADE 샘플

검사 파일:

- `UPGRADE.wav`
- Suno 가사 다운로더 LRC
- Suno 가사 다운로더 SRT

확인 결과:

| 항목 | 값 |
|---|---|
| WAV 형식 | 48 kHz, 16-bit PCM, 스테레오 |
| WAV 전체 길이 | 242.952초 |
| LRC/SRT cue 수 | 102개 |
| 대괄호 메타데이터 | 17개 |
| 실제 가사 형태 | 85개 |
| 압축 프롬프트 블록 | 0~9.9초, 57개 cue |
| 정상 동기화 가사 시작 | 24.335초 |
| 마지막 가사 종료 | 228.450초 |
| 자막 없는 아웃트로 후보 | 약 14.5초 |

### 핵심 이상 패턴

1. `0~9.9초`에 원본 프롬프트 전체가 약 `0.18초` 간격으로 삽입되었다.
2. 같은 가사가 `24.335초`부터 정상적인 길이로 다시 등장한다.
3. `[End]` cue가 `9.9~24.335초`를 차지한다.
4. `135~192.048초`의 한 가사 cue가 57.048초로 비정상적으로 늘어났다.
5. `192.048초`에 연주 지시, 섹션 태그, 실제 코러스 가사가 동시에 중복된다.

이 샘플에서 `0~9.9초` 블록은 실제 동기화 자막이 아니라 Suno 프롬프트 메타데이터로 판정할 수 있다.

## 3. 분류 모델

모든 cue는 원문을 보존하면서 다음 중 하나로 분류한다.

| 분류 | 예시 | 기본 자막 표시 |
|---|---|---|
| `lyric` | `어제의 껍질을 찢어 발겨` | 표시 |
| `section` | `[Intro]`, `[Verse 1]`, `[Chorus]` | 제외 |
| `instrumental` | `[Guitar Solo]`, `[Instrumental Break]` | 제외 |
| `production_direction` | `[Fast aggressive down-stroke riffing]` | 제외 |
| `sound_event` | `[Loud high-gain tube-amp feedback]` | 제외 |
| `spoken_event_candidate` | `[Drummer counts: One! Two! Three! Four!]` | 음원 확인 후 선택 |
| `end_marker` | `[End]`, `[Outro]` | 제외 |
| `unknown_bracketed` | 사전에 없는 대괄호 문장 | 검수 필요 |

내부 모델 예:

```json
{
  "cue_id": "cue_090",
  "start_ms": 192048,
  "end_ms": 192068,
  "raw_text": "[Raw high-gain solo with feedback and noise]",
  "normalized_text": "",
  "type": "production_direction",
  "display_as_subtitle": false,
  "confidence": 0.98,
  "review_required": false
}
```

## 4. 대괄호 처리 원칙

대괄호 항목을 무조건 삭제하지 않는다.

### 자동 분류 가능한 항목

- 표준 섹션 이름: Intro, Verse, Pre-Chorus, Chorus, Bridge, Breakdown, Drop, Outro, End
- 연주 이름: Guitar Solo, Drum Solo, Instrumental, Interlude
- 악기·음향·카메라가 아닌 음악 생성 지시 형태의 문장

### 음원 확인이 필요한 항목

- count, shout, whisper, spoken, breathing, scream, laugh 등 실제 발화 가능 표현
- 인물의 대사처럼 보이는 문장
- 대괄호 안에 실제 가사 문장이 들어간 경우

`spoken_event_candidate`는 기본적으로 화면 자막에서 제외하지만, 보컬 stem 또는 사람 검수에서 실제 발화로 확인되면 자막으로 승격할 수 있다.

## 5. 압축 프롬프트 블록 탐지

다음 특징을 조합해 파일 앞부분의 가짜 타임라인 블록을 탐지한다.

1. 짧은 시간 안에 비정상적으로 많은 cue가 존재한다.
2. cue 지속 시간이 거의 동일하고 지나치게 짧다.
3. 전체 가사와 섹션 태그가 순서대로 한 번 빠르게 등장한다.
4. 같은 가사 시퀀스가 뒤에서 정상적인 시간 간격으로 반복된다.
5. 첫 블록의 총 길이가 실제 가창으로 불가능할 정도로 짧다.

한 조건만으로 삭제하지 않는다. 여러 조건이 충족될 때 `prompt_block_candidate`로 표시하고 뒤쪽 정상 시퀀스와 비교한다.

권장 알고리즘:

```text
초반 cue 밀도 계산
-> 중앙 지속 시간 계산
-> 대괄호 비율과 가사 반복 시퀀스 탐지
-> 뒤쪽 cue와 텍스트 순서 유사도 비교
-> 높은 신뢰도이면 프롬프트 블록으로 격리
-> 애매하면 사람 검수
```

## 6. 비정상 cue 탐지와 복구

### 긴 cue

다음 경우 비정상 후보로 본다.

- 한 줄 가사가 일반적인 줄 길이보다 현저히 길게 지속
- 다음 가사까지 연주 태그가 누락되어 한 cue가 늘어남
- 섹션 경계를 가로질러 cue가 유지됨

복구 순서:

1. 보컬 활동 종료 시점을 찾는다.
2. 원래 가사 cue의 종료를 보컬 종료 근처로 줄인다.
3. 남은 구간을 `instrumental` 또는 `unknown_gap`으로 기록한다.
4. 다음 섹션 시작을 기존 cue 또는 음원 분석으로 유지한다.
5. 신뢰도가 낮으면 자동 수정하지 않고 검수 대상으로 둔다.

### 동일 타임스탬프 중복

같은 시작 시각에 여러 항목이 있으면 우선순위를 적용한다.

```text
실제 lyric
> spoken_event_candidate
> section
> instrumental
> production_direction
> end_marker
```

실제 가사는 자막 트랙에 남기고 나머지는 메타데이터 트랙으로 이동한다.

### End/Outro 처리

- `[End]`가 실제 음악 종료 전에 나타나도 음악을 자르지 않는다.
- 최종 WAV 길이를 절대 기준으로 사용한다.
- 마지막 가사 이후 음악이 계속되면 `instrumental_outro`로 기록한다.

## 7. 처리 파이프라인

```text
LRC/SRT 원문 로드
-> 형식·인코딩 검증
-> cue 공통 모델 변환
-> 대괄호 의미 분류
-> 압축 프롬프트 블록 탐지
-> 텍스트 반복 시퀀스 비교
-> 비정상 길이·중복 cue 탐지
-> WAV 길이와 범위 검증
-> 선택적 보컬 분리/강제 정렬
-> lyric 자막과 metadata 트랙 분리
-> cleaned.srt + metadata.json + review.csv 출력
```

## 8. 출력 파일

```text
subtitles/
├── source_original.lrc
├── source_original.srt
├── lyrics_cleaned.srt
├── song_structure.json
├── subtitle_metadata.json
└── subtitle_review.csv
```

`song_structure.json`에는 섹션과 연주 구간을 저장한다.

```json
{
  "sections": [
    {
      "type": "instrumental",
      "label": "Guitar Solo",
      "start_ms": null,
      "end_ms": 192048,
      "source": "metadata_and_audio",
      "review_required": true
    }
  ]
}
```

`start_ms=null`은 음원 분석 또는 사람 검수 전에는 시작 시각을 확정하지 않았다는 뜻이다. 실제 timeline으로 승격할 때는 `start_ms`를 확정하고 `end_ms > start_ms` 스키마 검증을 통과해야 한다.

## 9. 다른 Suno 곡 적용 원칙

- 모든 Suno 곡에 압축 프롬프트 블록이 있다고 가정하지 않는다.
- 대괄호가 있다고 모두 메타데이터라고 가정하지 않는다.
- LRC와 SRT 중 하나만 정상일 수 있으므로 양쪽을 비교한다.
- 파일명이나 다운로더 이름만으로 정상 여부를 확정하지 않는다.
- 최종 음악 파일의 길이와 해시를 기준으로 자막 버전을 연결한다.
- Remix, Extend, Replace Section 결과는 재정렬 우선순위를 높인다.
- 자동 정리 후에도 첫 보컬, 첫 코러스, 솔로 전후, 마지막 가사를 사람이 확인한다.

## 10. UPGRADE 샘플의 예상 정리

```text
0.000~9.900       압축 Suno 프롬프트 블록 -> 자막 제외
9.900~24.335      Intro/연주 구간 후보
24.335~135.000    실제 Verse~Bridge 가사
135.000~192.048   마지막 Bridge 가사 종료 + Guitar Solo로 분리 필요
192.048~228.450   Final Chorus/Outro 실제 가사
228.450~242.952   자막 없는 instrumental outro
```

`135~192.048초`의 정확한 가사 종료와 기타 솔로 시작은 보컬 분리 또는 사람 청취로 확정해야 한다.

## 11. 완료 기준

- 원본 LRC/SRT를 변경하지 않는다.
- 실제 가사와 메타데이터가 별도 출력된다.
- 프롬프트 블록 제거 근거가 보고서에 남는다.
- 비정상 cue와 중복 cue가 검수 목록에 기록된다.
- 음악 길이를 벗어난 cue가 없다.
- 저신뢰 구간은 자동 확정되지 않는다.
- 최소 5개 이상의 서로 다른 Suno 곡으로 회귀 검증한다.
