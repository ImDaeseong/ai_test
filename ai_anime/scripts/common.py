from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


if getattr(sys, "frozen", False):
    # PyInstaller로 빌드된 exe: 실행 파일 옆 디렉터리를 루트로 사용
    PROJECT_ROOT = Path(sys.executable).parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(name: str) -> Any:
    path = PROJECT_ROOT / "configs" / f"{name}.json"
    if not path.exists():
        return {}
    return read_json(path)


_sections_config = load_config("song_sections")
DEFAULT_SECTIONS: list[str] = _sections_config.get(
    "default_sections",
    ["Intro", "Verse", "Pre-Chorus", "Chorus", "Bridge", "Outro"],
)
_SECTION_ALIASES: dict[str, str] = _sections_config.get("aliases", {})


def ensure_directories() -> None:
    for folder in [
        "input",
        "analysis",
        "character/character_reference",
        "storyboard",
        "prompts/image_prompts",
        "prompts/video_prompts",
        "output/images",
        "output/storyboard",
        "output/videos",
    ]:
        (PROJECT_ROOT / folder).mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp949", "euc-kr"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "song"


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def versioned_run_dir(base: Path, song_slug: str) -> Path:
    run_dir = base / f"{song_slug}-{timestamp()}"
    counter = 2
    while run_dir.exists():
        run_dir = base / f"{song_slug}-{timestamp()}-{counter}"
        counter += 1
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,;/]", value) if item.strip()]


def normalize_section_name(name: str) -> str:
    compact = re.sub(r"\s+", " ", name.strip()).lower()
    return _SECTION_ALIASES.get(compact, name.strip().title())
