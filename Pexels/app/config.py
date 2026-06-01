from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    pexels_api_key: str | None = os.getenv("PEXELS_API_KEY")
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "storage/output"))
    raw_video_dir: Path = Path(os.getenv("RAW_VIDEO_DIR", "storage/raw_videos"))
    processed_dir: Path = Path(os.getenv("PROCESSED_DIR", "storage/processed"))
    cache_dir: Path = Path(os.getenv("CACHE_DIR", "storage/cache"))
    default_orientation: str = os.getenv("DEFAULT_ORIENTATION", "landscape")
    default_scene_duration: float = float(os.getenv("DEFAULT_SCENE_DURATION", "5"))
    request_timeout: float = float(os.getenv("REQUEST_TIMEOUT", "30"))
    max_download_mb: int = int(os.getenv("MAX_DOWNLOAD_MB", "250"))

    def ensure_storage(self) -> None:
        for directory in [self.output_dir, self.raw_video_dir, self.processed_dir, self.cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)


settings = Settings()
