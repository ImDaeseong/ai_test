from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean generated caches and temporary video files.")
    parser.add_argument("--all", action="store_true", help="Also remove downloaded raw Pexels videos and API caches.")
    args = parser.parse_args()

    targets = [settings.processed_dir, settings.output_dir]
    if args.all:
        targets.extend([settings.raw_video_dir, settings.cache_dir])

    for directory in targets:
        clean_directory(directory)
        print(f"cleaned: {directory}")

    Path("output").mkdir(parents=True, exist_ok=True)
    Path("output/.gitkeep").touch(exist_ok=True)
    print("output folder ready")
    return 0


def clean_directory(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for path in directory.iterdir():
        if path.name == ".gitkeep":
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    (directory / ".gitkeep").touch(exist_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
