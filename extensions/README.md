# extensions — Suno Lyric Downloader

Suno.com 노래 페이지에서 LRC / SRT 형식 동기화 가사를 다운로드하는 Chrome MV3 확장.

## 설치

1. Chrome → `chrome://extensions/` → 개발자 모드 ON
2. `suno-lyric-downloader/dist/` 폴더를 "압축 해제된 확장 프로그램 로드"

## 빌드

```bash
cd suno-lyric-downloader
npm install
npm run build
```

## 개선 이력 (2026-06-02)

### 버그 수정
| 파일 | 내용 |
|---|---|
| `src/contentScript.js:523` | SPA 페이지 전환 후 이전 songId로 버튼이 잘못 주입되던 경쟁 조건 완화 — 재주입 대기 시간 600ms → 800ms로 증가 |

### 알려진 제한사항
- Suno 사이트가 `HttpOnly` 쿠키로 변경 시 인증 불가 (외부 사이트 의존)
- 탭 새로고침 시 가사 캐시 초기화 (메모리 캐시만 사용)
