# 테스트 반복 계획

## 1. 테스트 계층

### 단위 테스트

- 곡명과 경로 해석
- 스토리보드 표 파싱
- LRC/SRT 파싱
- 시간 형식 변환
- 섹션별 시간 배분
- 프레임 반올림
- 이미지 부족·과다 정책
- 신뢰도 상태 변환
- 보고서 직렬화

### 통합 테스트

- 실제 `01_storyboard.md` + 이미지 fixture + 짧은 오디오
- Python timeline JSON → TypeScript schema 검증
- Remotion 10~30초 렌더
- SRT와 handoff 패키지 생성
- 외부 도구 실패와 timeout 처리

### 회귀 테스트

최소 샘플군:

| 유형 | 목적 |
|---|---|
| 느린 발라드 | 적은 이미지와 긴 컷 |
| 빠른 곡 | 많은 이미지와 짧은 컷 |
| 한글 곡명 | Windows 경로와 인코딩 |
| 영문/공백 곡명 | 경로 quoting |
| Suno Remix | 기존 LRC/SRT 불일치 |
| Extend 곡 | 접합부와 반복 가사 |
| 가사 없는 구간이 긴 곡 | instrumental 처리 |
| 자막 없는 곡 | 자막 선택 기능 |

사용자 음악과 이미지는 저장소에 커밋하지 않는다. 공개 가능한 짧은 합성 fixture 또는 사용자가 로컬에서 지정한 fixture를 사용한다.

### 수동 테스트

- 전체 영상 감상
- 자막 싱크 샘플링
- 이미지 모션과 크롭 품질
- 코러스 전환 품질
- CapCut 가져오기
- 최종 출력 해상도, 음량, 검은 프레임 확인

## 2. 변경별 필수 재실행

| 변경 영역 | 반드시 다시 실행할 테스트 |
|---|---|
| storyboard parser | 파서 단위 + 실제 3곡 회귀 |
| subtitle parser | LRC/SRT 정상·오류 fixture |
| timeline 계산 | 모든 경계값 + 전체 회귀 |
| frame 계산 | fps별 속성 테스트 |
| Remotion 컴포넌트 | 30초 렌더 + 시각 스냅샷 |
| 모션 프리셋 | 패널 타입별 수동 영상 확인 |
| 자막 정렬 | 라벨링 샘플 비교 + 저신뢰 검수 |
| package builder | 폴더 스냅샷 + CapCut 가져오기 |
| 의존성 업데이트 | 전체 테스트 + 실제 렌더 |

## 3. 테스트 명령 초안

```powershell
# Python
python -m pytest -q
python -m pytest tests\test_timeline.py -q
python -m pytest tests\integration -q

# TypeScript / Remotion
npm test
npm run typecheck
npm run lint
npm run render:fixture

# 전체 검증
python -m webtoon_capcut validate --fixture fixtures\manifest.json
```

이 명령은 구현 후 실제 스크립트명과 일치하도록 수정한다. 존재하지 않는 명령을 README에 완료된 것처럼 기록하지 않는다.

## 4. 속성 기반 핵심 테스트

임의의 음악 길이와 이미지 수에 대해 다음을 반복 검증한다.

- 모든 clip duration > 0
- start가 단조 증가
- 최종 종료가 음악 길이와 허용 오차 이내
- 이미지 수 변화에도 예외 없는 정상 정책 적용
- 동일 seed와 입력은 동일 결과
- 어떠한 입력에서도 작업 루트 밖 경로를 생성하지 않음

## 5. 실패 기록

```text
테스트 ID:
커밋/버전:
입력 fixture:
실행 명령:
실패 메시지:
재현 횟수:
예상 영향:
원인:
수정:
재검증 명령:
재검증 결과:
```

같은 원인으로 3회 실패하면 같은 방식의 재시도를 중단하고 설계 또는 접근을 다시 검토한다.

## 6. 통과 기준

- 테스트 개수 자체를 품질 목표로 삼지 않는다.
- 핵심 계산, 파일 경계, 오류 처리가 반복 가능하게 검증되어야 한다.
- 회귀 샘플 결과가 이전 승인 결과와 비교 가능해야 한다.
- 테스트가 통과해도 자막과 영상 품질의 사람 검수는 별도로 필요하다.

