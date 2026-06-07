# 테스트 완료 기준

## 작업 정의

- 유형: 신규 프로젝트
- 내용: 다곡 웹툰 MV 편집 타임라인 생성 CLI
- 작성일: 2026-06-06

## 인수 조건

조건 1:

```text
Given 이미지, WAV, 스토리보드가 준비된 곡
When build 명령을 실행하면
Then 첫 clip은 0에서 시작하고 마지막 clip은 음원 종료와 1프레임 이내 일치한다
```

조건 2:

```text
Given Suno metadata와 장시간 cue가 포함된 SRT
When 자막 품질을 평가하면
Then metadata는 화면 가사에서 제외되고 필요한 정렬 상태가 기록된다
```

조건 3:

```text
Given 곡명, 이미지 수, 섹션 구성이 서로 다른 입력
When 동일 CLI를 실행하면
Then 소스 수정 없이 각각 독립된 output/{노래명}/{run_id} 산출물을 만든다
```

조건 4:

```text
Given 이미지나 음원이 없는 프롬프트 전용 폴더
When discover를 실행하면
Then 실패하지 않고 PROMPTS_ONLY로 분류한다
```

## 테스트 전략

- 단위: 섹션 정규화, 시간 배분, SRT/LRC, 이미지/WAV probe
- 통합: 임시 곡 fixture의 inspect/build
- 회귀: 실제 3곡과 전체 214곡 탐색
- Q3 사람 테스트: CapCut import와 체감 자막 싱크
- Q4 사람 테스트: 공개 전 보안·성능 검토

## 버그 심각도

- P0: 원본 손상, 비밀값 노출
- P1: 타임라인 gap, 음원 종료 불일치, 잘못된 파일 선택
- P2: 과도한 경고, 모션 품질 저하
- P3: 문구와 표시 형식

## DoD

- [x] 자동 테스트 30개
- [x] 세 곡 타임라인 연속성 확인
- [x] 214곡 discover 예외 없음
- [x] 하드코딩·절대 경로·비밀값 검사
- [x] Remotion 실제 preview 렌더
- [x] WhisperX 실제 곡 정렬
- [x] Demucs 짧은 샘플 보컬 분리
- [ ] full 1080p 실제 곡 렌더
- [ ] 전체 곡 Demucs+WhisperX 결합 검증
- [ ] Q3 CapCut 탐색 검수
- [ ] Q4 사람 보안 검수
- [ ] 실제 5곡 end-to-end

현재 테스트 종료 판정: `HOLD`

자동 checking은 완료됐지만 사람 testing과 렌더 검증이 남아 있다.

최종 자동 검수 결과와 실제 3곡 수치는 `HERMES_REVIEW.md`를 기준으로 한다.
