# Suno Lyric Downloader — 크롬 확장 프로그램 재현 프롬프트

> **대상 모델:** Claude Sonnet 4.6 이상  
> **목적:** Suno.com 노래 페이지에서 동기화 가사를 LRC/SRT 파일로 다운로드하는 크롬 확장 프로그램을 처음부터 구현한다.

---

## 1. 프로젝트 개요

### 기능 요약
- Suno.com 노래 상세 페이지(`/song/{id}`) 진입 시 커버 이미지 위에 **LRC** · **SRT** 다운로드 버튼을 자동 주입
- Suno Studio API에서 타이밍 데이터를 가져와 LRC/SRT 파일로 변환 후 브라우저 다운로드
- 팝업 UI에서 현재 탭 상태 표시 및 수동 버튼 탐색 기능 제공
- 13개 언어 지원(i18n)

### 기술 스택
| 역할 | 기술 |
|------|------|
| 확장 UI | React 18 + Tailwind CSS v4 |
| 빌드 | Vite (또는 webpack) |
| 크롬 API | `tabs`, `runtime.sendMessage`, `runtime.onMessage` |
| 스타일링 | Tailwind CSS (popup) + 인라인 CSS (content script) |
| 국제화 | Chrome i18n `_locales` |

---

## 2. 파일 구조

```
suno-lyric-downloader/
├── manifest.json
├── background.js
├── contentScript.js
├── popup.html
├── popup.js            ← React 빌드 결과물
├── popup.css           ← Tailwind 빌드 결과물
├── show.gif            ← 버튼 위치 안내 이미지
├── public/
│   ├── icon16.png
│   ├── icon32.png
│   ├── icon48.png
│   └── icon128.png
└── _locales/
    ├── en/messages.json
    ├── ko/messages.json
    ├── ja/messages.json
    ├── zh_CN/messages.json
    ├── ar/messages.json
    ├── de/messages.json
    ├── es/messages.json
    ├── fr/messages.json
    ├── hi/messages.json
    ├── it/messages.json
    ├── pt/messages.json
    └── ru/messages.json
```

---

## 3. manifest.json

```json
{
  "manifest_version": 3,
  "name": "__MSG_extension_name__",
  "description": "__MSG_extension_description__",
  "version": "2.0.5",
  "default_locale": "en",
  "minimum_chrome_version": "114",
  "permissions": ["tabs"],
  "host_permissions": ["https://suno.com/*"],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["https://suno.com/*"],
      "js": ["contentScript.js"]
    }
  ],
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "public/icon16.png",
      "32": "public/icon32.png",
      "48": "public/icon48.png",
      "128": "public/icon128.png"
    }
  },
  "icons": {
    "16": "public/icon16.png",
    "32": "public/icon32.png",
    "48": "public/icon48.png",
    "128": "public/icon128.png"
  }
}
```

---

## 4. background.js — Service Worker

### 역할
- 탭 URL 변경 감지 → `/song/{id}` 패턴이면 content script에 메시지 전송

### 구현 요구사항

```javascript
// background.js

chrome.action.setPopup({ popup: "popup.html" });

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url) {
    const url = new URL(changeInfo.url);
    // /song/{songId} 경로인 경우만 처리
    const match = url.pathname.match(/^\/song\/([^/]+)/);
    if (match) {
      const songId = match[1];
      chrome.tabs.sendMessage(tabId, {
        action: "URL_CHANGED",
        url: changeInfo.url,
        songId,
      }).catch(() => {}); // content script 미준비 상태 무시
    }
  }
});
```

---

## 5. contentScript.js — 핵심 로직

### 5-1. 전체 흐름

```
페이지 로드 / URL 변경
    ↓
MutationObserver로 커버 이미지 감지
    ↓
이미 버튼 있으면 skip
    ↓
Suno API에서 aligned_lyrics + clip 메타데이터 fetch
    ↓
타이밍 품질 평가 (words vs lines 선택)
    ↓
누락 가사 보완 (Prompt Repair)
    ↓
LRC / SRT 포맷 변환
    ↓
버튼 클릭 시 파일 다운로드
```

### 5-2. API 호출

#### 인증
- `document.cookie`에서 `__session` 쿠키 값을 추출해 Bearer 토큰으로 사용

```javascript
function getSessionToken() {
  const match = document.cookie.match(/(?:^|;\s*)__session=([^;]+)/);
  return match ? match[1] : null;
}
```

#### 가사 API
```
GET https://studio-api.prod.suno.com/api/gen/{songId}/aligned_lyrics/v2/
Authorization: Bearer {session_token}

응답 형태:
{
  aligned_lyrics: [
    {
      text: string,        // 가사 라인
      start_s: number,     // 시작 시간 (초)
      end_s: number,       // 종료 시간 (초)
      words: [             // 단어별 타이밍 (선택적)
        { text: string, start_s: number, end_s: number }
      ]
    }
  ],
  waveform_data: number[]  // 파형 데이터 (타이밍 보정용)
}
```

#### 클립 메타데이터 API
```
GET https://studio-api.prod.suno.com/api/clip/{songId}
Authorization: Bearer {session_token}

응답 형태:
{
  duration_s: number,
  metadata: {
    prompt: string,         // 원본 가사 (누락 보정용)
    duration_formatted: string
  }
}
```

### 5-3. 타이밍 품질 평가 알고리즘

타이밍 품질 점수를 계산해 `words` 레벨과 `lines` 레벨 중 더 신뢰할 수 있는 소스를 선택한다.

```javascript
function calcTimingQuality(lines, useWords = false) {
  let validCount = 0;
  let monotonicBreaks = 0;
  let prev = -1;

  for (const line of lines) {
    const items = useWords ? (line.words ?? []) : [line];
    for (const item of items) {
      const t = item.start_s;
      if (t != null && t >= 0) {
        validCount++;
        if (t < prev) monotonicBreaks++;
        prev = t;
      }
    }
  }

  const total = lines.length || 1;
  const score = validCount / total - monotonicBreaks * 0.5;
  return { score, validCount, monotonicBreaks };
}

// 70% 이상 유효 타이밍이면 해당 소스 사용
function chooseBestSource(aligned_lyrics) {
  const wordsQuality = calcTimingQuality(aligned_lyrics, true);
  const linesQuality = calcTimingQuality(aligned_lyrics, false);

  if (wordsQuality.score >= 0.7) return "words";
  if (linesQuality.score >= 0.7) return "lines";
  return "lines"; // 기본값
}
```

### 5-4. 누락 타이밍 처리

타이밍이 없는 라인은 두 가지 방법으로 보정한다:

**방법 1: 선형 배분 (waveform 없을 때)**
```javascript
function distributeLinear(lines, totalDuration) {
  const step = totalDuration / lines.length;
  return lines.map((line, i) => ({
    ...line,
    start_s: i * step,
    end_s: (i + 1) * step,
  }));
}
```

**방법 2: 파형 기반 상대적 확장 (waveform 있을 때)**
```javascript
function expandByWaveform(lines, waveformData, totalDuration) {
  // 1. 파형 피크 감지 (에너지 기반 threshold 계산)
  const threshold = calcWaveformThreshold(waveformData);
  // 2. 기존 타이밍이 있는 앵커 포인트와 파형 에너지 분포를 이용해
  //    타이밍 없는 구간을 비례적으로 분배
  // 3. 앵커 간격 내에서 에너지 누적량에 비례해 각 라인 시작 시간 결정
  return repairTimings(lines, waveformData, threshold, totalDuration);
}
```

### 5-5. 프롬프트 보완 (Prompt Repair)

API 응답 가사가 원본 프롬프트보다 짧은 경우, 메타데이터의 `prompt` 필드에서 누락 라인을 복원한다.

```javascript
function repairMissingLyrics(alignedLines, originalPrompt) {
  // 1. 원본 프롬프트를 라인 단위로 분리
  // 2. 각 라인을 정규화 (소문자, 특수문자 제거)
  // 3. aligned_lyrics에 없는 라인 탐지
  // 4. 앞뒤 라인의 타이밍을 기반으로 선형 보간해 타이밍 할당
  // 5. 올바른 순서로 삽입
}
```

### 5-6. LRC 포맷 변환

```javascript
function toTimestampLRC(seconds) {
  const m = Math.floor(seconds / 60).toString().padStart(2, "0");
  const s = (seconds % 60).toFixed(2).padStart(5, "0");
  return `${m}:${s}`;
}

function toLRC(lines) {
  return lines
    .map(line => `[${toTimestampLRC(line.start_s)}]${line.text}`)
    .join("\n");
}
```

### 5-7. SRT 포맷 변환

```javascript
function toTimestampSRT(seconds) {
  const h = Math.floor(seconds / 3600).toString().padStart(2, "0");
  const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, "0");
  const s = Math.floor(seconds % 60).toString().padStart(2, "0");
  const ms = Math.round((seconds % 1) * 1000).toString().padStart(3, "0");
  return `${h}:${m}:${s},${ms}`;
}

function toSRT(lines) {
  return lines
    .map((line, i) => {
      const start = toTimestampSRT(line.start_s);
      const end = toTimestampSRT(line.end_s ?? lines[i + 1]?.start_s ?? line.start_s + 3);
      return `${i + 1}\n${start} --> ${end}\n${line.text}`;
    })
    .join("\n\n");
}
```

### 5-8. UI 주입

커버 이미지 감지 후 오버레이 버튼을 DOM에 삽입한다.

```javascript
// 커버 이미지 선택자
const COVER_SELECTOR = 'img[alt="Song Cover Image"].w-full.h-full';

// MutationObserver로 커버 이미지 감지
const observer = new MutationObserver(() => {
  const covers = document.querySelectorAll(COVER_SELECTOR);
  covers.forEach(injectButtons);
});
observer.observe(document.body, { childList: true, subtree: true });

function injectButtons(coverImg) {
  if (coverImg.dataset.sunoLyricInjected) return;
  coverImg.dataset.sunoLyricInjected = "1";

  // 부모를 relative positioning으로 설정
  const wrapper = coverImg.parentElement;
  wrapper.style.position = "relative";

  // 오버레이 컨테이너 생성
  const overlay = document.createElement("div");
  overlay.className = "suno-lyric-downloader-overlay";

  // LRC 버튼
  const lrcBtn = createButton("LRC", () => download("lrc", songId));
  // SRT 버튼
  const srtBtn = createButton("SRT", () => download("srt", songId));

  overlay.appendChild(lrcBtn);
  overlay.appendChild(srtBtn);
  wrapper.appendChild(overlay);
}
```

### 5-9. 버튼 CSS (인라인 주입)

```javascript
const BUTTON_STYLES = `
.suno-lyric-downloader-overlay {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
  z-index: 9999;
}

.suno-lyric-downloader-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 2rem;
  padding: 0 12px;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  font-family: ui-sans-serif, "Segoe UI", sans-serif;
  font-size: 0.875rem;
  font-weight: 500;
  color: #fff;
  background: rgba(12, 12, 14, 0.72);
  backdrop-filter: blur(10px);
  transition: opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.suno-lyric-downloader-btn:hover {
  opacity: 0.85;
  transform: scale(1.04);
}

.suno-lyric-downloader-btn:active {
  transform: scale(0.97);
}

.suno-lyric-downloader-btn svg {
  width: 0.875rem;
  height: 0.875rem;
  flex-shrink: 0;
}
`;
```

SVG 아이콘은 다운로드 화살표 아이콘 사용 (Heroicons `arrow-down-tray`).

---

## 6. popup.html / popup.js — 팝업 UI

### 6-1. popup.html 기본 구조

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Suno Lyric Downloader</title>
  <link rel="stylesheet" href="popup.css" />
</head>
<body>
  <div id="root"></div>
  <script type="module" src="popup.js"></script>
</body>
</html>
```

### 6-2. React 컴포넌트 구조

```
<App>
  ├── <StatusSection>       ← 현재 탭 상태 표시
  ├── <GuideSection>        ← 사용 방법 3단계 안내
  ├── <ActionButtons>       ← "Suno 열기" / "다운로드 버튼 찾기"
  ├── <DemoImage>           ← show.gif 안내 이미지
  └── <TroubleshootingSection> ← 문제 해결 안내
```

### 6-3. 팝업 상태 (4가지)

| 상태 | 조건 | 메시지 |
|------|------|--------|
| `loading` | 탭 정보 확인 중 | "현재 탭 확인 중..." |
| `not_suno` | Suno가 아닌 탭 | "Suno를 열고 노래 상세 페이지를 선택하세요." |
| `suno_non_song` | Suno이지만 /song/ 아님 | "Suno에 있습니다. /song/으로 시작하는 URL의 노래 페이지를 여세요." |
| `suno_song` | /song/{id} 페이지 | "노래 페이지 감지됨. 다운로드 버튼을 찾을 수 있습니다." |

### 6-4. 탭 URL 감지 로직

```javascript
useEffect(() => {
  chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
    if (!tab?.url) { setStatus("not_suno"); return; }
    const url = new URL(tab.url);
    if (!url.hostname.includes("suno.com")) {
      setStatus("not_suno");
    } else if (url.pathname.startsWith("/song/")) {
      setStatus("suno_song");
      setSongId(url.pathname.split("/")[2]);
    } else {
      setStatus("suno_non_song");
    }
  });
}, []);
```

### 6-5. "다운로드 버튼 찾기" 동작

```javascript
function handleFindButtons() {
  chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
    chrome.tabs.sendMessage(tab.id, { action: "FIND_BUTTONS" });
  });
}
```

### 6-6. 팝업 크기 및 스타일

- 최소 너비: 360px, 최소 높이: 520px
- Tailwind 색상 팔레트: neutral 950/900/500 (배경), emerald 50/100/300/400 (액센트)
- 다크 그라디언트 배경
- 안내 단계: 번호 뱃지 + 텍스트 카드

---

## 7. 국제화 (i18n)

### 7-1. 메시지 키 목록

```json
{
  "extension_name": { "message": "Suno Lyric Downloader" },
  "extension_description": { "message": "..." },
  "download_lyric": { "message": "가사 다운로드" },
  "toggle_type": { "message": "형식 변경" },
  "popup_status_loading": { "message": "현재 탭 확인 중..." },
  "popup_status_not_suno": { "message": "Suno를 열고 노래 페이지를 선택하세요." },
  "popup_status_suno_non_song": { "message": "Suno에 있습니다. /song/ URL을 여세요." },
  "popup_status_suno_song": { "message": "노래 페이지 감지됨." },
  "popup_step_1": { "message": "Suno에 로그인" },
  "popup_step_2": { "message": "노래 상세 페이지 열기 (https://suno.com/song/...)" },
  "popup_step_3": { "message": "LRC 또는 SRT 버튼 클릭" },
  "popup_button_open_suno": { "message": "Suno 열기" },
  "popup_button_find_buttons": { "message": "다운로드 버튼 찾기" },
  "popup_troubleshooting_title": { "message": "문제 해결" },
  "popup_troubleshooting_no_timing": { "message": "일부 노래는 동기화 타이밍이 없습니다." },
  "popup_troubleshooting_wait_cover": { "message": "커버 로딩 후 새로고침 해보세요." },
  "popup_troubleshooting_login": { "message": "Suno에 로그인했는지 확인하세요." },
  "popup_troubleshooting_song_page": { "message": "홈/만들기/플레이리스트가 아닌 노래 상세 페이지를 이용하세요." },
  "popup_footer_tip": { "message": "팁: 노래 커버 위에 버튼이 나타납니다." }
}
```

### 7-2. 사용법

```javascript
// manifest.json에서
"name": "__MSG_extension_name__"

// JavaScript에서
const msg = chrome.i18n.getMessage("popup_status_loading");
```

---

## 8. 파일 다운로드 구현

```javascript
function triggerDownload(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

async function download(format, songId) {
  const token = getSessionToken();
  if (!token) { alert("Suno 로그인이 필요합니다."); return; }

  // API 호출
  const [lyricsRes, clipRes] = await Promise.all([
    fetch(`https://studio-api.prod.suno.com/api/gen/${songId}/aligned_lyrics/v2/`, {
      headers: { Authorization: `Bearer ${token}` }
    }),
    fetch(`https://studio-api.prod.suno.com/api/clip/${songId}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
  ]);

  const { aligned_lyrics, waveform_data } = await lyricsRes.json();
  const clip = await clipRes.json();

  // 품질 평가 → 타이밍 선택 → 누락 보완
  const source = chooseBestSource(aligned_lyrics);
  let lines = extractLines(aligned_lyrics, source);
  lines = repairMissingLyrics(lines, clip.metadata?.prompt ?? "");
  lines = fillMissingTimings(lines, waveform_data, clip.duration_s);

  // 포맷 변환 및 다운로드
  const content = format === "lrc" ? toLRC(lines) : toSRT(lines);
  const ext = format === "lrc" ? "lrc" : "srt";
  const title = clip.title ?? songId;
  triggerDownload(content, `${title}.${ext}`, "text/plain;charset=utf-8");
}
```

---

## 9. 캐싱 전략

동일 songId에 대한 중복 API 호출을 방지한다.

```javascript
const lyricsCache = new Map(); // songId → 가공된 lyrics 데이터

async function getLyrics(songId) {
  if (lyricsCache.has(songId)) return lyricsCache.get(songId);
  const data = await fetchAndProcess(songId);
  lyricsCache.set(songId, data);
  return data;
}
```

---

## 10. 메시지 통신 흐름

```
background.js                contentScript.js              popup.js
     |                              |                          |
     | URL_CHANGED (songId)         |                          |
     |----------------------------->|                          |
     |                    inject buttons                       |
     |                              |                          |
     |                              |    FIND_BUTTONS          |
     |                              |<-------------------------|
     |                    re-scan DOM                          |
```

---

## 11. 개발 환경 설정

### 의존성 설치

```bash
npm create vite@latest suno-lyric-downloader -- --template react
cd suno-lyric-downloader
npm install
npm install -D tailwindcss @tailwindcss/vite
```

### vite.config.js (확장 프로그램 빌드용)

```javascript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "dist",
    rollupOptions: {
      input: {
        popup: resolve(__dirname, "popup.html"),
        background: resolve(__dirname, "src/background.js"),
        contentScript: resolve(__dirname, "src/contentScript.js"),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "[name].js",
        assetFileNames: "[name].[ext]",
      },
    },
  },
});
```

### 개발 → 로드 순서

1. `npm run build` 실행
2. Chrome `chrome://extensions/` 접속
3. "개발자 모드" 활성화
4. "압축해제된 확장 프로그램 로드" → `dist` 폴더 선택
5. `https://suno.com/song/{임의ID}` 접속해서 테스트

---

## 12. 구현 시 주의사항

1. **세션 토큰 보안:** `__session` 쿠키는 HttpOnly가 아니므로 JS에서 읽을 수 있지만, 외부 서버로 전송하지 말 것
2. **MutationObserver 정리:** URL 변경 시 이전 observer를 disconnect하고 새로 등록
3. **중복 버튼 방지:** `data-suno-lyric-injected` 속성으로 이미 처리된 이미지 확인
4. **SRT end time:** 마지막 라인의 end_s가 없으면 `start_s + 3초`를 기본값으로 사용
5. **LRC 소수점:** `.toFixed(2)` 사용 (MM:SS.mm 형식 유지)
6. **SRT 소수점:** 밀리초는 콤마(`,`)로 구분 (`HH:MM:SS,mmm`)
7. **타이밍 단조성:** start_s가 이전보다 작은 역전 케이스는 이전 값 + 최소간격으로 보정
8. **Content Script CSS 격리:** 클래스 prefix `suno-lyric-downloader-`를 일관되게 사용해 기존 스타일 충돌 방지

---

## 13. 테스트 시나리오

| 시나리오 | 기대 결과 |
|----------|-----------|
| 동기화 가사 있는 노래 | LRC/SRT 다운로드 정상 |
| 동기화 타이밍 없는 노래 | 선형 배분으로 파일 생성 |
| 미로그인 상태 | 알림 메시지 표시 |
| 팝업: Suno 외 탭 | "Suno를 여세요" 상태 표시 |
| 팝업: 노래 페이지 | "노래 페이지 감지됨" 상태 표시 |
| 팝업: 버튼 찾기 클릭 | content script에 메시지 전송 |
| 다국어: 브라우저 언어 변경 | 해당 언어로 UI 표시 |

---

## 14. 빠른 시작 프롬프트 (AI에게 전달용)

아래 프롬프트를 그대로 AI 코딩 도구에 붙여넣어 전체 구현을 요청할 수 있다.

```
Suno.com 노래 상세 페이지에서 LRC/SRT 가사 파일을 다운로드하는 크롬 확장 프로그램을 구현해 주세요.

요구사항:
- Manifest V3 사용
- content script에서 MutationObserver로 img[alt="Song Cover Image"].w-full.h-full 감지
- 커버 이미지 위에 LRC/SRT 다운로드 버튼 오버레이 주입 (glassmorphism 스타일)
- https://studio-api.prod.suno.com/api/gen/{songId}/aligned_lyrics/v2/ 에서 타이밍 포함 가사 fetch
- https://studio-api.prod.suno.com/api/clip/{songId} 에서 곡 메타데이터 fetch
- __session 쿠키로 Bearer 인증
- words 레벨 / lines 레벨 타이밍 품질 평가 후 신뢰도 높은 소스 선택 (70% threshold)
- 타이밍 없는 라인은 선형 배분 또는 waveform 기반 보정
- [MM:SS.mm]text 형식 LRC 변환
- HH:MM:SS,mmm --> HH:MM:SS,mmm + 번호 형식 SRT 변환
- React + Tailwind CSS v4 팝업 UI (360×520px, 다크 테마, emerald 액센트)
- 팝업 4가지 상태: loading / not_suno / suno_non_song / suno_song
- 13개 언어 _locales i18n
- background service worker에서 tabs.onUpdated로 /song/{id} URL 감지 후 content script에 메시지
- songId별 가사 캐싱 (Map)
- Vite 빌드 설정 (popup + background + contentScript 멀티 엔트리)

위 사양을 모두 충족하는 완전한 소스코드를 작성해 주세요.
```

---

*분석 기준 버전: 2.0.5 | 분석일: 2026-05-08*
