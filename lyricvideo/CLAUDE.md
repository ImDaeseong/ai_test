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
npm run render    # 렌더링 출력
```

## 주의사항

- `src/LyricVideo.tsx:165`: 배경 영상은 반드시 `<Video loop>` (HTML5) 사용 — `<OffthreadVideo>`는 `loop` 미지원으로 영상 종료 후 검은 화면 발생
- Remotion v4 API 준수: `<Html5Video>`, `<Html5Audio>`, `trimBefore`/`trimAfter` 사용 (`<Video deprecated>`, `startFrom`/`endAt` deprecated)
- `useCurrentFrame()` + `interpolate()`로만 애니메이션 처리
- 테스트 파일 미작성 (HOLD) — 타입 체크로 기본 검증: `npx tsc --noEmit`
