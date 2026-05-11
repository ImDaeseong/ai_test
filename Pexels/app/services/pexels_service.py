from __future__ import annotations

import json
from pathlib import Path

import httpx

from app.config import settings
from app.models.scene import Scene
from app.utils.file_utils import safe_slug
from app.utils.retry import retry


class PexelsService:
    base_url = "https://api.pexels.com/videos/search"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.pexels_api_key

    def search_best_video(self, scene: Scene) -> dict:
        if not self.api_key:
            raise RuntimeError("PEXELS_API_KEY is missing.")

        cache_file = self._cache_file(scene)
        if cache_file.exists():
            results = json.loads(cache_file.read_text(encoding="utf-8"))
        else:
            results = self._search(scene.search_keywords, scene.orientation)
            cache_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

        videos = results.get("videos", [])
        if not videos:
            fallback = " ".join(scene.search_keywords.split()[:2]) or scene.scene
            results = self._search(fallback, scene.orientation)
            videos = results.get("videos", [])
        if not videos:
            raise RuntimeError(f"No Pexels videos found for '{scene.search_keywords}'.")
        return max(videos, key=lambda item: score_video(item, scene))

    @retry()
    def _search(self, query: str, orientation: str) -> dict:
        headers = {"Authorization": self.api_key or ""}
        params = {"query": query, "orientation": orientation, "per_page": 10}
        with httpx.Client(timeout=settings.request_timeout) as client:
            response = client.get(self.base_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

    def _cache_file(self, scene: Scene) -> Path:
        settings.ensure_storage()
        name = safe_slug(f"{scene.orientation}_{scene.search_keywords}")[:120]
        return settings.cache_dir / f"pexels_{name}.json"


def select_best_file(video: dict) -> dict:
    files = video.get("video_files") or []
    mp4s = [item for item in files if item.get("file_type") == "video/mp4" and item.get("link")]
    if not mp4s:
        raise RuntimeError("Selected Pexels video has no downloadable MP4 file.")
    return max(mp4s, key=lambda item: (item.get("width") or 0) * (item.get("height") or 0))


def score_video(video: dict, scene: Scene) -> float:
    width = video.get("width") or 0
    height = video.get("height") or 0
    duration = video.get("duration") or 0
    resolution = width * height / 1_000_000
    duration_score = max(0, 10 - abs(duration - scene.duration))
    orientation_score = 0
    if scene.orientation == "portrait" and height >= width:
        orientation_score = 8
    elif scene.orientation == "landscape" and width >= height:
        orientation_score = 8
    elif scene.orientation == "square" and abs(width - height) < max(width, height) * 0.2:
        orientation_score = 8
    return resolution + duration_score + orientation_score
