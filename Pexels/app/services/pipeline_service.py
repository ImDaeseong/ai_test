from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.config import settings
from app.models.request import GenerateVideoRequest
from app.models.response import GenerateVideoResponse, ProjectStatusResponse
from app.models.scene import SceneWithVideo
from app.services.download_service import DownloadService
from app.services.ffmpeg_service import FFmpegService
from app.services.gemini_service import GeminiService
from app.services.pexels_service import PexelsService
from app.services.project_store import ProjectStore


class VideoPipeline:
    def __init__(self) -> None:
        self.gemini = GeminiService()
        self.pexels = PexelsService()
        self.downloader = DownloadService()
        self.ffmpeg = FFmpegService()
        self.project_store = ProjectStore()

    def generate(self, request: GenerateVideoRequest) -> GenerateVideoResponse:
        settings.ensure_storage()
        project_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.project_store.save(ProjectStatusResponse(status="running", project_id=project_id))

        try:
            scenes = self.gemini.analyze_text(request.text, request.orientation, request.style)
            hydrated: list[SceneWithVideo] = []
            for scene in scenes:
                selected = self.pexels.search_best_video(scene)
                downloaded = self.downloader.download_pexels_video(selected)
                hydrated.append(
                    SceneWithVideo(
                        **scene.model_dump(),
                        video_id=selected.get("id"),
                        video_file=str(downloaded),
                    )
                )

            output = Path(request.output_path) if request.output_path else settings.output_dir / f"final_{project_id}.mp4"
            output_file = str(
                self.ffmpeg.render(
                    hydrated,
                    output,
                    music_file=Path(request.music_file) if request.with_music and request.music_file else None,
                    subtitle_file=Path(request.subtitle_file) if request.with_subtitles and request.subtitle_file else None,
                    target_duration=request.target_duration,
                )
            )
            response = GenerateVideoResponse(
                status="success",
                project_id=project_id,
                scenes=hydrated,
                output_file=output_file,
            )
            self.project_store.save(ProjectStatusResponse(**response.model_dump()))
            return response
        except Exception as exc:
            self.project_store.save(ProjectStatusResponse(status="failed", project_id=project_id, error=str(exc)))
            raise
