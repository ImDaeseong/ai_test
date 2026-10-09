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

- `npm test`는 파서·타임코드·계획·최종 MP4 계약·공급망 기준선·릴리스 승인 경계 43개를 검증한다.
- 실제 전체 파이프라인은 2026-10-09 로컬 곡으로 FFmpeg 렌더와 H.264/AAC·해상도·길이 검사를 통과했다. 실제 자산은 소스 저장소에 포함하지 않는다.
- `npm run audit:baseline`은 검토된 취약점의 증가·악화를 차단하지만 현재 9건을 해소했다고 주장하지 않는다.
- 창작 품질·저작권·최종 공개는 `release-review.json`의 사람 승인 전까지 HOLD다.
- FFmpeg PATH 미등록 시 렌더 단계에서 실패 — 에러 메시지 `ffmpeg not found` 확인
- `input/` 폴더 내 파일 형식이 지원 목록과 다르면 `validate/` 단계에서 차단됨
