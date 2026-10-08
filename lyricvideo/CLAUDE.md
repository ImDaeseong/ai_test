# Claude Code Instructions — lyricvideo

## 프로젝트 목적

Remotion + React 기반 LRC/SRT 가사 비디오 자동 생성.
16:9 (가로) + 9:16 (세로) 동시 출력 지원.

## 구조

```
src/
  LyricVideo.tsx    # 메인 Remotion 컴포지션 (가사 싱크 + 배경 처리)
  compositions/     # 추가 컴포지션
scripts/            # 렌더 스크립트
remotion.config.ts  # Remotion 설정
```

## 실행

```bash
npm install
npm run dev       # 미리보기 (Remotion Studio)
npm run build     # 가로 영상 렌더링 출력
npm run build:vertical
npm run verify:render  # 가로·세로 대표 프레임 5장씩 렌더 및 레이아웃 검사
```

## 주의사항

- `src/LyricVideo.tsx:165`: 배경 영상은 반드시 `<Video loop>` (HTML5) 사용 — `<OffthreadVideo>`는 `loop` 미지원으로 영상 종료 후 검은 화면 발생
- Remotion v4 API 준수: `<Html5Video>`, `<Html5Audio>`, `trimBefore`/`trimAfter` 사용 (`<Video deprecated>`, `startFrom`/`endAt` deprecated)
- `useCurrentFrame()` + `interpolate()`로만 애니메이션 처리
- `npm run verify:render`는 실제 브라우저 레이아웃에서 가사 박스의 캔버스 이탈·상호 겹침을 검사하고 가로·세로 대표 프레임을 `out/verification/`에 남긴다. 입력 미디어나 Chrome이 없으면 HOLD다.
- 대비와 읽기 속도는 자동 검사하며, 의미·번역·배경과의 정서적 적합성은 `RENDER_REVIEW.md`의 인간 검토 항목으로 확인한다.
- `src/parsers.ts`와 레이아웃 판정 순수함수는 `npm test`로 자동 검증한다.
