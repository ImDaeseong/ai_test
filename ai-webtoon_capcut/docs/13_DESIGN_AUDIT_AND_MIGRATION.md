# 설계 감사와 마이그레이션

## 1. 감사 목적

UPGRADE 한 곡을 준비한 경험을 재사용 프로그램 설계에 반영하고, 샘플 전용 결정을 제품 코드로 가져가지 않도록 경계를 정한다.

## 2. 유지할 설계

- 원본 읽기 전용
- 별도 workspace
- manifest와 파일 해시
- Python 계획 엔진과 Remotion 렌더 분리
- CapCut은 최종 검수
- Suno 자막 메타데이터 분류
- 사람 검수 상태
- timeline JSON 경계

## 3. 폐기할 샘플 전용 방식

| 샘플 방식 | 폐기 이유 | 일반화 방식 |
|---|---|---|
| UPGRADE 절대 경로 | 다른 곡 불가 | CLI/manifest 입력 |
| 패널 42개 검사 | 실제 20~63장 | storyboard 기반 동적 수 |
| panel_001~042 고정 | 곡별 상이 | 연속성 검증 |
| 섹션 패널 번호 수동 범위 | 구조 다양 | storyboard label grouping |
| 섹션 시각 수동 입력 | 곡마다 다름 | boundary resolver 전략 |
| Bridge 3회 반복 | 샘플 전용 | 섹션 길이 기반 자동 계산 |
| cue 89 고정 보정 | 파일마다 다름 | 장기 cue 탐지 규칙 |
| 242.952초 상수 | 샘플 전용 | audio probe |
| 0~9.9초 제거 | 다른 곡 오탐 | 고밀도+반복 시퀀스 복합 탐지 |

## 4. 기존 문서 정리 원칙

문서 역할:

- `01~08`: 배경, 원칙, 사례, 초기 설계
- `09`: 재사용 프로그램의 canonical architecture
- `10`: 구현 데이터 계약
- `11`: 구현 순서와 CLI
- `12`: 재사용성 검증
- `13`: 샘플 설계에서 일반 설계로의 변경 기록

UPGRADE의 숫자는 회귀 fixture에서만 사용한다.

## 5. UPGRADE video_project 취급

현재 `ai-webtoon/output/UPGRADE/video_project`는 다음 용도로만 사용한다.

- 예상 출력 구조 참고
- JSON/CSV fixture 후보
- 자막 정규화 회귀 근거
- 타임라인 불변조건 검증

정식 프로그램의 출력으로 간주하지 않는다.

향후 구현 후:

1. 기존 `video_project`를 보관하거나 이름을 `video_project_manual_fixture`로 변경
2. 정식 CLI로 새 workspace에 UPGRADE 재생성
3. 두 결과를 비교
4. 차이를 검수 보고서에 기록

사용자 승인 없이 기존 폴더를 이동하거나 이름 변경하지 않는다.

## 6. 구현 시작 전 체크리스트

- [ ] V2 문서 우선순위를 README에 명시
- [ ] CLI MVP 범위 확정
- [ ] Python/Node 지원 버전 확인
- [ ] JSON schema 구현
- [ ] 214곡 storyboard parser 테스트 준비
- [ ] UPGRADE fixture의 민감·저작권 데이터 저장소 포함 여부 결정
- [ ] 추가 4곡의 실제 미디어 준비
- [ ] Remotion 설치 및 라이선스 확인
- [ ] ffmpeg/ffprobe 설치 방식 결정
- [ ] Demucs 대체 가능 인터페이스 유지

## 7. 최종 판정

```text
설계 상태: IMPLEMENTATION_READY_WITH_VALIDATION_GATES
재사용 프로그램 상태: NOT IMPLEMENTED
다곡 검증 상태: HOLD
```

프로그램 구현은 시작할 수 있다. 그러나 “재사용 가능” 판정은 V2 검증 매트릭스의 최소 5곡 end-to-end 통과 후에만 가능하다.

