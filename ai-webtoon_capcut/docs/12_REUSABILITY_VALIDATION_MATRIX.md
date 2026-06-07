# 재사용성 검증 매트릭스

## 1. 현재 감사 판정

| 영역 | 판정 | 근거 |
|---|---|---|
| 상위 아키텍처 | PASS | 파서, 정렬, 타임라인, 렌더 경계가 정의됨 |
| 데이터 계약 | NEEDS FIX | V1 예시는 있었으나 다곡 충돌·신뢰도 계약이 부족했음 |
| UPGRADE 준비 데이터 | PASS WITH REVIEW | 42개 이미지와 242.952초 타임라인 검증 |
| 재사용 구현 | HOLD | 정식 프로그램 없음 |
| 다곡 실제 미디어 검증 | HOLD | 현재 UPGRADE만 미디어 준비 완료 |
| 자막 강제 정렬 | HOLD | Demucs 실행 의존성 문제, WhisperX 미설치 |
| Remotion 렌더 | HOLD | 실제 MP4 미생성 |

## 2. 핵심 회귀 축

### 패널 수

```text
20, 27, 34, 42, 50, 63
```

실제 분포의 최소, 중앙, 최대를 포함한다.

### 음악 길이

```text
90초 이하
90~180초
180~300초
300초 초과
```

### 섹션 구조

- 기본 Intro/Verse/Chorus/Outro
- Final Chorus와 Post-Chorus
- Hook, Drop, Build
- Breakdown과 Interlude
- Verse 3 이상, Chorus 3 이상
- Instrumental 중심

### 자막 형태

- LRC만
- SRT만
- LRC/SRT 둘 다 정상
- 둘 중 하나만 정상
- Suno 프롬프트 블록 포함
- 대괄호 실제 발화 후보 포함
- 반복 가사
- 생략 가사
- 장기 cue
- 자막 없음

### 이미지 상태

- 모든 이미지 동일 해상도
- 해상도 혼합
- PNG/JPG/WebP 혼합
- 이미지 1개 누락
- 같은 패널 이미지 중복
- 종횡비 혼합
- 손상 이미지

## 3. 자동 테스트

| ID | 테스트 | 기대 결과 |
|---|---|---|
| R-DISC-01 | 214곡 discover | 예외 없이 상태 분류 |
| R-DISC-02 | 현재 데이터 | UPGRADE만 BUILD_READY로 판정 |
| R-PARSE-01 | 214개 storyboard | 모든 패널과 섹션 라벨 파싱 |
| R-PARSE-02 | 패널 수 20~63 | 고정 개수 가정 없음 |
| R-ASSET-01 | panel 번호 매칭 | 정확히 1:1 |
| R-ASSET-02 | 중복 후보 | 자동 선택하지 않고 BLOCKED |
| R-SUB-01 | UPGRADE prompt block | 0~9.9초 블록 격리 |
| R-SUB-02 | bracket metadata | lyric SRT에서 제외, metadata 보존 |
| R-SUB-03 | 긴 cue | HOLD 이슈 생성 |
| R-SEC-01 | TXT 가사 정렬 | section boundary source 기록 |
| R-SEC-02 | 정렬 불가 | storyboard weight 폴백 |
| R-TIME-01 | 임의 길이/이미지 수 | 마지막 프레임 일치 |
| R-TIME-02 | 이미지 부족 | 반복 정책과 경고 |
| R-TIME-03 | 이미지 과다 | 다양성 유지 제외 정책 |
| R-PATH-01 | 한글·공백 경로 | 정상 처리 |
| R-PATH-02 | 루트 탈출 | 거부 |
| R-BATCH-01 | 한 곡 실패 | 나머지 곡 계속 처리 |
| R-DETERM-01 | 동일 입력 재실행 | 동일 timeline hash |

## 4. 속성 기반 테스트

임의 생성:

- 음악 길이: 30,000~600,000ms
- 패널 수: 1~100
- 섹션 수: 1~30
- 패널 권장 시간: 1~15초

불변조건:

- 모든 clip duration > 0
- clip start가 단조 증가
- gap과 허용되지 않은 overlap 없음
- 마지막 end가 audio duration과 1프레임 이내
- panel 없는 section을 조용히 생성하지 않음
- 최대 재사용 정책 초과 시 경고 또는 중단
- 같은 입력은 같은 결과

## 5. 수동 검수용 5곡 기준

실제 구현 후 다음 특성이 겹치지 않도록 5곡을 고른다.

| 샘플 | 필수 특성 |
|---|---|
| A | UPGRADE, 빠른 곡, 42장, 긴 솔로, 혼합 LRC/SRT |
| B | 느린 발라드, 20~30장, 긴 컷 |
| C | 50장 이상, 빠른 컷, 반복 코러스 |
| D | Remix/Extend, 기존 자막 불일치 |
| E | Instrumental/Interlude/Hook 등 비표준 섹션 |

각 곡에서 검수:

- 첫 보컬
- 첫 Chorus
- 반복 Chorus
- 연주 구간 경계
- 마지막 가사
- 영상 종료
- 이미지 반복 품질
- CapCut SRT import

## 6. 성능과 운영 검증

- inspect 214곡 처리 시간
- 곡당 plan 메모리와 시간
- preview 렌더 시간
- full 렌더 임시 공간
- batch 동시 실행 제한
- CPU 전용 환경
- GPU 환경
- 실패 후 재실행과 캐시 무효화

## 7. 보안과 원본 보호

처리 전후 원본 해시를 비교한다.

```text
storyboard
images
audio
lrc
srt
```

검증:

- 원본 해시 변경 0건
- workspace 밖 생성 파일 0건
- `.env` 변경 0건
- 로그 비밀값 0건
- 절대 개인 경로를 handoff 패키지에 포함하지 않음

## 8. 출시 게이트

### Prototype PASS

- UPGRADE plan과 정리 SRT 재생성
- 하드코딩 곡명 없음
- timeline 검증 PASS

### MVP PASS

- 5곡 end-to-end
- preview MP4 5개
- CapCut import 5개
- P0/P1 미해결 없음
- 문서와 실제 명령 일치

### Batch PASS

- 준비된 곡 전체 자동 탐색
- 실패 격리
- 요약 보고서
- 결정론적 재실행

검증 전 상태는 완료가 아니라 `HOLD`다.

