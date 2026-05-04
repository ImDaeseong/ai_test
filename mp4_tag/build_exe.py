import shutil
import subprocess
import time
from pathlib import Path

import PyInstaller.__main__


APP_NAME = "VideoDownloader"
EXE_NAME = f"{APP_NAME}.exe"


def stop_running_app() -> None:
    subprocess.run(["taskkill", "/F", "/IM", EXE_NAME], capture_output=True, text=True)
    time.sleep(1)


def clean_build_dirs() -> None:
    for folder in ("build", "dist"):
        path = Path(folder)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)


def build() -> None:
    stop_running_app()
    clean_build_dirs()

    opts = [
        "run_app.py",
        f"--name={APP_NAME}",
        "--onefile",
        "--noconfirm",
        "--clean",
        "--add-data=app.py;.",
        "--add-data=downloader_core.py;.",
        "--add-data=job_manager.py;.",
        "--add-data=server_limits.py;.",
        "--collect-all=streamlit",
        "--collect-all=playwright",
        "--collect-all=yt_dlp",
        "--collect-all=httpx",
        "--collect-all=httpcore",
        "--additional-hooks-dir=.",
    ]

    if Path("ffmpeg.exe").exists():
        opts.append("--add-data=ffmpeg.exe;.")
    else:
        print("[경고] ffmpeg.exe가 프로젝트 폴더에 없습니다. exe 실행 환경에 별도로 설치되어 있어야 합니다.")

    PyInstaller.__main__.run(opts)


if __name__ == "__main__":
    build()
