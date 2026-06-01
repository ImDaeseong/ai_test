from __future__ import annotations

from pathlib import Path

import httpx

from app.config import settings
from app.services.pexels_service import select_best_file
from app.utils.file_utils import safe_slug
from app.utils.retry import retry


class DownloadService:
    def download_pexels_video(self, video: dict) -> Path:
        settings.ensure_storage()
        video_id = video.get("id")
        best_file = select_best_file(video)
        filename = f"pexels_{video_id}_{safe_slug(str(best_file.get('quality', 'video')))}.mp4"
        target = settings.raw_video_dir / filename
        if target.exists() and target.stat().st_size > 0:
            return target
        return self._download(best_file["link"], target)

    @retry()
    def _download(self, url: str, target: Path) -> Path:
        max_bytes = settings.max_download_mb * 1024 * 1024
        bytes_written = 0
        temp_target = target.with_suffix(target.suffix + ".part")
        temp_target.unlink(missing_ok=True)
        with httpx.Client(timeout=settings.request_timeout, follow_redirects=True) as client:
            try:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with temp_target.open("wb") as file:
                        for chunk in response.iter_bytes():
                            bytes_written += len(chunk)
                            if bytes_written > max_bytes:
                                raise RuntimeError("Download exceeded MAX_DOWNLOAD_MB.")
                            file.write(chunk)
            except Exception:
                temp_target.unlink(missing_ok=True)
                raise
        temp_target.replace(target)
        return target
