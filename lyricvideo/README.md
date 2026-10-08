# lyricvideo — Remotion 가사 비디오 생성기

Remotion + React 기반 LRC/SRT 가사 비디오 자동 생성.  
16:9 (가로) + 9:16 (세로) 동시 출력 지원.

## 실행

```bash
npm install
npm run dev          # 미리보기
npm run build        # 가로 영상 렌더링
npm run build:vertical
npm run verify:render # 가로·세로 대표 프레임 5장씩 렌더 및 레이아웃 검사
```

## 개선 이력 (2026-06-02)

### 버그 수정
| 파일 | 내용 |
|---|---|
| `src/LyricVideo.tsx:165` | 배경 영상에 `OffthreadVideo` 사용 시 영상 종료 후 루프되지 않고 검은 화면/정지되던 문제 수정 — `OffthreadVideo`(loop 미지원)를 `Video loop`(HTML5, loop 지원)로 교체 |

### 빌드 검증
- `npm test`: 가사 파서와 레이아웃 판정 단위 테스트
- `npm run typecheck`: TypeScript 정적 검사
- `npm run verify:render`: 실제 Chrome 렌더에서 가사 잘림·겹침 검사 및 PNG 증거 생성
- 렌더 전에 최악 조건 텍스트 대비와 줄당 80자·초당 20자 제한을 검사하며, 주관적·의미적 검토는 `RENDER_REVIEW.md`에 기록한다.
