# 설계문서 03 — 미디어 다운로더

> 프로젝트: mp4_tag

---

## 1. 프로젝트 정의

**mp4_tag**: Streamlit UI + yt-dlp + Playwright 기반 웹 미디어 다운로더
- yt-dlp 지원 사이트 → 직접 다운로드
- 그 외 사이트 → Playwright 브라우저 분석으로 미디어 URL 추출

---

## 2. 기술 스택

| 기술 | 용도 |
|------|------|
| **Python** 3.12 | 핵심 언어 (3.14 NotImplementedError 있음 → 3.12 명시) |
| **Streamlit** | 웹 UI (빠른 프로토타이핑) |
| **yt-dlp** | YouTube 등 직접 다운로드 |
| **Playwright** | 브라우저 기반 URL 추출 |
| **Pandas** | 다운로드 이력 관리 |
| **Pillow** | 썸네일 처리 |

---

## 3. 아키텍처

### 다운로드 결정 흐름
```
URL 입력
  ↓
is_ytdlp_supported_site(url)
  ├── True → yt-dlp 직접 다운로드 (빠름)
  └── False → Playwright 브라우저 분석
               → 미디어 URL 추출
               → yt-dlp or requests 다운로드
```

### yt-dlp 지원 사이트 (직접 처리)
```python
YTDLP_DOMAINS = {
    'youtube.com', 'youtu.be',
    'twitter.com', 'x.com',
    'instagram.com',
    'tiktok.com',
    'vimeo.com',
    'soundcloud.com',
    'twitch.tv',
    'dailymotion.com',
    'nicovideo.jp',
    'bilibili.com',
}
```

### 모듈 구조
```
main.py              → Streamlit 진입점
app.py               → UI 컴포넌트
downloader_core.py   → yt-dlp·Playwright 핵심 로직
job_manager.py       → 비동기 작업 관리
server_limits.py     → 서버 제한 설정
```

---

## 4. 핵심 환경 변수

```
MAX_YTDLP_ATTEMPTS=12   # 기본값, 최악 48회 재시도
MAX_ANALYZE_WORKERS=2   # 동시 URL 분석 수
```

---

## 5. run.bat 자동화 패턴

```batch
@echo off
:: Python 3.12 venv 자동 생성
IF NOT EXIST ".venv" (
    py -3.12 -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
    .venv\Scripts\playwright install chromium
)
.venv\Scripts\streamlit run main.py
```

### 핵심: `py -3.12` 명시
- Python 3.14에서 NotImplementedError 발생 → 3.12 고정
- venv 내 패키지 + Playwright 브라우저 자동 설치

---

## 6. yt-dlp 사용 패턴

```python
import yt_dlp

def download_with_ytdlp(url, output_dir, max_attempts=12):
    ydl_opts = {
        'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'retries': max_attempts,
        'quiet': False,
        'no_warnings': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return info
```

---

## 7. Playwright 분석 패턴

```python
from playwright.sync_api import sync_playwright

def extract_media_urls(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        media_urls = []
        page.on('response', lambda r: media_urls.append(r.url)
                if r.headers.get('content-type', '').startswith('video/')
                else None)

        page.goto(url, wait_until='networkidle')
        browser.close()
    return media_urls
```

---

## 8. Streamlit UI 버튼 구조

```python
col1, col2 = st.columns(2)
with col1:
    if st.button("yt-dlp ▶"):        # 직접 yt-dlp 다운로드
        submit_ytdlp_download(url)
with col2:
    if st.button("분석 후 다운로드"):  # Playwright 분석
        submit_fallback_download(url)
```

---

## 9. 테스트 (50개)

범위: URL 파싱, 사이트 감지, yt-dlp 옵션, Playwright mock, 작업 관리, 서버 제한

---

## 10. 주의사항 및 한계

| 항목 | 내용 |
|------|------|
| **저작권** | 개인 용도만 사용, 저작권 컨텐츠 무단 배포 금지 |
| **Python 버전** | 반드시 `py -3.12` 사용 (3.14 불가) |
| **Playwright** | 첫 실행 시 Chromium 자동 설치 (~150MB) |
| **속도 제한** | 일부 사이트 IP 차단 → `MAX_YTDLP_ATTEMPTS` 조정 |
| **로그인 필요 사이트** | Playwright 쿠키 주입 필요 (미구현) |
