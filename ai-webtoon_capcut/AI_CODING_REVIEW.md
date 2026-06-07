# AI 코딩 검수

## 이해 가능성

- [x] 입력 → 분석 → 정규화 → 섹션 → 타임라인 → handoff 흐름이 분리됨
- [x] 외부 라이브러리 없이 현재 MVP가 실행됨
- [x] 모듈 역할이 파일명으로 구분됨

## 보안

- [x] API 키·토큰·비밀번호 없음
- [x] 원본 input/output 비수정
- [x] workspace 산출물에 개인 절대 경로 없음
- [x] fixture 곡명 하드코딩 없음
- [ ] Git history secret scan은 공개 직전에 수행

## 입력 처리

- [x] 스토리보드·SRT·LRC 형식 검사
- [x] 이미지 번호 누락·중복 검사
- [x] WAV와 이미지 헤더 검사
- [ ] 파일 크기 상한 미구현
- [ ] MP3/FLAC/M4A는 ffprobe 설치 전 차단

## 유지보수

- [x] 설정과 로직 분리
- [x] 도메인 모델과 CLI 분리
- [x] 곡별 정책 분기 없음
- [x] 동일 입력의 결정론적 run ID
- [ ] `application.py`는 향후 단계별 service로 추가 분리 가능

## 운영

- [x] JSON 구조화 로그
- [x] 오류 코드와 종료 코드
- [x] QA 보고서
- [x] batch 실패 격리
- [x] 실제 렌더 subprocess timeout, 종료 코드, 로그 tail, ffprobe 보고서
- [x] 정렬 subprocess timeout과 오류 격리

## 판정

- 코드 분석/계획 MVP: `PASS WITH LIMITATIONS`
- 영상 제작 전체 시스템: `HOLD`
- 공개/배포: `HOLD`

이유: preview와 정렬 엔진은 구현됐지만 full 렌더, 전체 결합 회귀와 CapCut 사람
검수가 남아 있다.
