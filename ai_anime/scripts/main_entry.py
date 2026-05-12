from __future__ import annotations

import argparse
import sys
import threading
import time
import webbrowser


def _open_browser(url: str, delay: float = 1.5) -> None:
    time.sleep(delay)
    webbrowser.open(url)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Anime MV Builder")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true", help="서버 시작 시 브라우저를 자동으로 열지 않습니다.")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    if not args.no_browser:
        threading.Thread(target=_open_browser, args=(url,), daemon=True).start()

    # web_app.main()은 argparse를 사용하므로 argv를 직접 전달
    sys.argv = ["web_app.py", "--host", args.host, "--port", str(args.port)]
    from web_app import main as web_main
    web_main()


if __name__ == "__main__":
    main()
