"""
HLS / MP4 Video Downloader (Path Optimized)
- 모든 결과물은 실행 파일 위치의 'downloads' 폴더에 저장
- Pylance 경고 및 미사용 임포트 완전 정리

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 실행 방법
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[최초 1회] 환경 설치
  setup.bat 더블클릭
  → Python(임베디드), pip, 패키지, Chromium 자동 설치
  → ffmpeg.exe 가 프로젝트 폴더에 있어야 함 (없으면 경고)

──────────────────────────────────────────────────
방법 A. GUI (웹 브라우저, 권장)
──────────────────────────────────────────────────
  run.bat 더블클릭
  → 브라우저에서 http://localhost:8501 자동 오픈
  → URL 입력 후 🔍 분석 버튼 클릭

  또는 시스템 Python 사용 시:
    streamlit run app.py

──────────────────────────────────────────────────
방법 B. CLI (터미널, 이 파일 직접 실행)
──────────────────────────────────────────────────
  python main.py <URL>
  예) python main.py https://example.com/video

  URL 생략 시 실행 후 입력 프롬프트가 표시됨:
    python main.py

──────────────────────────────────────────────────
다운로드 결과물 저장 위치
  ./downloads/  (프로젝트 폴더 내 자동 생성)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sys
import re
import subprocess
import asyncio
import shutil
from urllib.parse import urljoin
from pathlib import Path

# 실행 파일(.exe) 위치 기준 경로 계산 (PyInstaller 환경 대응)
_EXE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
_LOCAL_FFMPEG = _EXE_DIR / "ffmpeg.exe"
FFMPEG_BIN = str(_LOCAL_FFMPEG) if _LOCAL_FFMPEG.exists() else (shutil.which("ffmpeg") or "ffmpeg")

import httpx
import yt_dlp
from playwright.async_api import async_playwright

# ──────────────────────────────────────────────
# 0. 경로 설정 및 의존성 체크
# ──────────────────────────────────────────────
# 실행 파일 기준의 downloads 폴더 설정
DOWNLOAD_DIR = _EXE_DIR / "downloads"

def prepare_env():
    """환경 준비: 폴더 생성 및 ffmpeg 체크"""
    if not DOWNLOAD_DIR.exists():
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        print(f"📁 저장 폴더 생성됨: {DOWNLOAD_DIR.resolve()}")
        
    if not (_LOCAL_FFMPEG.exists() or shutil.which("ffmpeg")):
        print("\n❌ ffmpeg 미설치: 프로젝트 폴더에 ffmpeg.exe를 복사하거나 winget install ffmpeg 실행 필요")
        sys.exit(1)

# ──────────────────────────────────────────────
# 1단계: yt-dlp (유튜브 우선 순위)
# ──────────────────────────────────────────────
def try_ytdlp(url: str) -> bool:
    print(f"\n[1/4] yt-dlp 분석 시도 중...")
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        # 다운로드 폴더 경로 반영
        'outtmpl': str(DOWNLOAD_DIR / '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            print(f"✅ yt-dlp 완료: {info.get('title')}")
            return True
    except:
        return False

# ──────────────────────────────────────────────
# 2단계: Playwright (동적 스니핑)
# ──────────────────────────────────────────────
async def collect_media_urls(page_url: str) -> list[dict]:
    found_streams = []
    seen_urls = set()

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
        except:
            print("\n❌ 브라우저 미설치: playwright install chromium")
            sys.exit(1)

        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        page = await context.new_page()

        async def handle_request(request):
            url = request.url
            if url in seen_urls: return
            if re.search(r"\.(m3u8|mp4|ts)(\?|$)", url, re.I) or "googlevideo.com/videoplayback" in url:
                seen_urls.add(url)
                headers = dict(request.headers)
                headers.setdefault("referer", page_url)
                stype = "YouTube" if "googlevideo" in url else "HLS" if ".m3u8" in url.lower() else "MP4"
                found_streams.append({"url": url, "type": stype, "headers": headers})
                print(f"  ✨ 발견 [{len(found_streams)}]: {stype}")

        page.on("request", handle_request)
        print(f"[2/4] 동적 수집 시작 (8초 대기): {page_url}")
        
        try:
            await page.goto(page_url, wait_until="domcontentloaded", timeout=60_000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(8) 
        except: pass
        await browser.close()
    return found_streams

# ──────────────────────────────────────────────
# 3단계: 화질 선택 및 다운로드
# ──────────────────────────────────────────────
def pick_best_stream(master_m3u8: str, base_url: str) -> str:
    lines = master_m3u8.splitlines()
    streams = []
    for i, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF"):
            bw = int(re.search(r"BANDWIDTH=(\d+)", line).group(1)) if "BANDWIDTH" in line else 0
            for j in range(i + 1, len(lines)):
                uri = lines[j].strip()
                if uri and not uri.startswith("#"):
                    streams.append((bw, uri))
                    break
    if not streams: return ""
    best_bw, best_uri = max(streams, key=lambda x: x[0])
    print(f"  📊 최적 화질 선택됨 (Bandwidth: {best_bw:,} bps)")
    return best_uri if best_uri.startswith("http") else urljoin(base_url, best_uri)

def ffmpeg_download(media_url: str, headers: dict, output_path: Path):
    allowed = ["user-agent", "referer", "cookie", "origin"]
    header_str = "\r\n".join([f"{k}: {v}" for k, v in headers.items() if k.lower() in allowed]) + "\r\n"

    cmd = [FFMPEG_BIN, "-y", "-headers", header_str, "-i", media_url, "-c", "copy", "-bsf:a", "aac_adtstoasc", str(output_path)]
    print(f"\n🚀 저장 프로세스 시작 → {output_path.name}")
    subprocess.run(cmd, shell=False)

# ──────────────────────────────────────────────
# 메인 제어
# ──────────────────────────────────────────────
async def main(page_url: str):
    prepare_env()
    if try_ytdlp(page_url): return

    streams = await collect_media_urls(page_url)
    if not streams: 
        print("❌ 추출 가능한 미디어가 없습니다.")
        return

    print("\n" + "="*60)
    for i, s in enumerate(streams, 1):
        print(f"{i:<4} | {s['type']:<10} | {s['url'][:40]}...")
    print("="*60)

    choice = input("\n📥 다운로드할 번호 (취소: Enter): ").strip()
    if not choice: return
    
    try:
        idx = int(choice) - 1
        selected = streams[idx]
        
        if "googlevideo" in selected['url']:
            print("⚠️ 유튜브 조각 감지: 안전 모드(yt-dlp) 전환...")
            with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': str(DOWNLOAD_DIR / 'yt_video.%(ext)s')}) as ydl:
                ydl.download([page_url])
            return

        final_url = selected['url']
        if ".m3u8" in final_url.lower():
            async with httpx.AsyncClient() as client:
                r = await client.get(final_url, headers={k:v for k,v in selected['headers'].items() if k.lower() in ('referer', 'cookie')})
                if "#EXT-X-STREAM-INF" in r.text:
                    best = pick_best_stream(r.text, final_url.rsplit("/", 1)[0] + "/")
                    if best: final_url = best

        # 최종 출력 경로 조합
        final_output = DOWNLOAD_DIR / f"output_{idx+1}.mp4"
        ffmpeg_download(final_url, selected['headers'], final_output)
        print(f"\n✅ 저장 완료: {final_output.resolve()}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else input("\n🚀 [Usage] python main.py <URL>\n🔗 URL 입력: ").strip()
    if target:
        asyncio.run(main(target))