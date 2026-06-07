# 시스템 설계 보충: 출처 기반 자막 정렬 원칙

이 문서는 `01_SYSTEM_DESIGN.md`의 LRC/SRT 재정렬 부분에 적용할 보충 기준이다.

## 기술 근거

- WhisperX의 VAD와 강제 음소 정렬 구조를 시간 추정의 참고 모델로 사용한다.
- Demucs의 보컬 분리 기능을 선택적 전처리로 사용한다.
- Suno Extend/Whole Song 특성상 최종 음원과 기존 자막의 버전 불일치를 정상적인 실패 조건으로 취급한다.

## 필수 설계 변경

1. `VocalSeparator`는 교체 가능한 인터페이스로 둔다.
2. `AlignmentEngine`은 `original_mix`와 `vocal_stem` 결과 비교를 지원한다.
3. 프로젝트 manifest에 최종 음원 해시와 자막 원본 해시를 기록한다.
4. Extend 접합부 추정 시간이 있으면 검수 우선순위를 높인다.
5. WhisperX 계열 결과는 텍스트 원본이 아니라 시간 후보로 사용한다.
6. 가창 정확도는 자동 테스트만으로 승인하지 않고 사람 검수를 통과해야 한다.

상세 출처와 한계는 `07_REFERENCES.md`를 참조한다.

