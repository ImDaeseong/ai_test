# lyricvideo — Remotion 가사 비디오 생성기

Remotion + React 기반 LRC/SRT 가사 비디오 자동 생성.  
16:9 (가로) + 9:16 (세로) 동시 출력 지원.

## 실행

```bash
npm install
npm run dev          # 미리보기
npm run render       # 렌더링
```

## 개선 이력 (2026-06-02)

### 버그 수정
| 파일 | 내용 |
|---|---|
| `src/LyricVideo.tsx:165` | 배경 영상에 `OffthreadVideo` 사용 시 영상 종료 후 루프되지 않고 검은 화면/정지되던 문제 수정 — `OffthreadVideo`(loop 미지원)를 `Video loop`(HTML5, loop 지원)로 교체 |

### 빌드 검증
- `tsc --noEmit` 통과
