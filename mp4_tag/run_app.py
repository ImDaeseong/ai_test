import streamlit.web.cli as stcli
import os, sys, subprocess
from pathlib import Path


def resource_path(relative_path):
    """PyInstaller가 압축을 푸는 임시 폴더(_MEIPASS)에서 실제 파일 경로를 찾습니다."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def ensure_chromium():
    """exe 옆 browsers 폴더에 Chromium이 없으면 자동 설치합니다."""
    exe_dir = Path(sys.executable).parent
    browsers_path = exe_dir / "browsers"
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)

    # chromium* 폴더가 있으면 이미 설치됨
    if browsers_path.exists() and any(browsers_path.glob("chromium*")):
        return

    # 번들된 playwright driver 경로
    driver = Path(resource_path(os.path.join("playwright", "driver", "playwright.cmd")))
    if not driver.exists():
        # fallback: 시스템 playwright 명령
        driver = "playwright"

    print("=" * 60)
    print(" 최초 실행: Chromium 브라우저를 설치합니다 (인터넷 필요)")
    print(f" 설치 경로: {browsers_path}")
    print("=" * 60)

    result = subprocess.run(
        [str(driver), "install", "chromium"],
        env=os.environ.copy(),
    )

    if result.returncode != 0:
        print("\n[경고] Chromium 자동 설치 실패. 수동으로 실행하세요:")
        print(f"  playwright install chromium")


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        ensure_chromium()

    # 실행 파일 내부의 app.py 경로를 Streamlit 엔진에 전달
    app_path = resource_path("app.py")

    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
    ]

    # Streamlit 메인 함수 실행
    sys.exit(stcli.main())
