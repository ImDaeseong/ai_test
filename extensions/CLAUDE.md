# Claude Code Instructions — extensions

## 프로젝트 목적

Suno.com 노래 페이지에서 LRC / SRT 형식 동기화 가사를 다운로드하는 Chrome MV3 확장.

## 구조

```
suno-lyric-downloader/
  dist/               # 빌드 결과 (Chrome 로드 대상)
  src/
    contentScript.js  # 페이지 주입 스크립트 (버튼 삽입 + 가사 추출)
    background.js     # 서비스 워커
    popup.*           # 확장 팝업 UI
  package.json
```

## 빌드

```bash
cd suno-lyric-downloader
npm install
npm run build
```

## 설치

Chrome → `chrome://extensions/` → 개발자 모드 ON → `dist/` 폴더 "압축 해제된 확장 프로그램 로드"

## 주의사항

- `contentScript.js:523`: 재주입 대기 시간 800ms — SPA 페이지 전환 후 이전 songId 경쟁 조건 방지. 600ms 이하로 줄이지 말 것
- Chrome MV3 제약: XMLHttpRequest 불가, fetch/ServiceWorker 사용
- 테스트는 실제 Chrome + Suno.com 로그인 환경 필요 — 자동화 테스트 없음 (HOLD)
- `dist/` 는 빌드 산출물 — 직접 편집 금지, 항상 `src/` 수정 후 빌드
