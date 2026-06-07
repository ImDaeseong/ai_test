# ADR-001: 분석 계획 엔진과 렌더러 분리

- 상태: 확정
- 날짜: 2026-06-06

## 상황

곡 분석과 자막 정규화는 Python에서 안정적으로 검증할 수 있지만 실제 영상
렌더는 Remotion과 ffmpeg 설치 상태에 영향을 받는다.

## 결정

Python은 manifest, normalized subtitle, section, timeline을 생성한다.
Remotion은 검증된 timeline 계약만 소비한다.

## 이유

- 렌더 도구 없이 분석 테스트 가능
- CapCut과 다른 렌더러로 교체 가능
- 자막 HOLD와 영상 렌더 성공을 혼동하지 않음

## 포기한 대안

- Node/Remotion 단일 애플리케이션
- CapCut 비공개 draft JSON 직접 생성

## 결과

두 런타임 관리 비용이 생기지만 분석 결정론과 테스트 가능성이 높아진다.
