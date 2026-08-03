# Claude Code Instructions — imagevideo

## 프로젝트 목적

가사 파일(.srt/.lrc/lyrics.json)과 음악 파일로 완성된 뮤직비디오를 자동 생성하는
Node.js + FFmpeg 파이프라인.

## 구조

```
src/
  pipeline/    # 파이프라인 오케스트레이터
  planner/     # 씬 계획 로직
  render/      # FFmpeg 렌더링
  motion/      # 모션 효과
  subtitles/   # 자막 처리
  ffmpeg/      # FFmpeg 래퍼
  utils/       # 공통 유틸
  validate/    # 입력 검증
input/         # 입력 파일 (가사, 음악, 배경 이미지/영상)
```

## 실행

```bash
npm install
# input/ 에 파일 준비 후
npm start
```

## 요구사항

- Node.js 20+
- FFmpeg (PATH 등록 필수)

## 주의사항

- 파이프라인 전체 통합 테스트는 없음 (HOLD) — 신규 기능 추가 시 `src/validate/` 검증 로직 우선 확인
- `src/utils/`의 순수함수(lyricParsers/timecode/validation)는 33개 단위 테스트로 자동 검증됨(2026-06-28 작성 완료): `node src/utils/lyricParsers.test.js && node src/utils/timecode.test.js && node src/utils/validation.test.js`
- FFmpeg PATH 미등록 시 렌더 단계에서 실패 — 에러 메시지 `ffmpeg not found` 확인
- `input/` 폴더 내 파일 형식이 지원 목록과 다르면 `validate/` 단계에서 차단됨
