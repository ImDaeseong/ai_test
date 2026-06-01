import os
import subprocess
import sys
from pathlib import Path

import streamlit.web.cli as stcli


def resource_path(relative_path: str) -> str:
    """Return a bundled resource path when running from PyInstaller."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


def ensure_chromium() -> None:
    """Install Playwright Chromium beside the executable on first run."""
    exe_dir = Path(sys.executable).parent
    browsers_path = exe_dir / "browsers"
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)

    if browsers_path.exists() and any(browsers_path.glob("chromium*")):
        return

    bundled_driver = Path(resource_path(os.path.join("playwright", "driver", "playwright.cmd")))
    driver = str(bundled_driver) if bundled_driver.exists() else "playwright"

    print("=" * 60)
    print("최초 실행: Chromium 브라우저를 설치합니다. 인터넷 연결이 필요합니다.")
    print(f"설치 경로: {browsers_path}")
    print("=" * 60)

    result = subprocess.run([driver, "install", "chromium"], env=os.environ.copy())
    if result.returncode != 0:
        print("\n[경고] Chromium 자동 설치에 실패했습니다.")
        print("수동으로 `playwright install chromium`을 실행해 주세요.")


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        ensure_chromium()

    sys.argv = [
        "streamlit",
        "run",
        resource_path("app.py"),
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())
