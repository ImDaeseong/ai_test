# Architecture

## Pipeline

Text input flows through the following modules:

1. `GeminiService`: converts input text into validated scene JSON.
2. `PexelsService`: searches and ranks stock videos for each scene.
3. `DownloadService`: downloads selected MP4 files and reuses cached files.
4. `FFmpegService`: trims, scales, crops, and concatenates clips.
5. `HtmlReportService`: writes the static browser preview page.
6. `ProjectStore`: persists lightweight project status under `storage/cache/projects/`.

## Module Boundaries

- `app/models/`: Pydantic request, response, and scene schemas.
- `app/services/`: external APIs, file download, rendering, orchestration.
- `app/utils/`: retry, slug, logging, and text helpers.
- `storage/`: generated runtime files only.
- `output/`: final MP4 and static browser report.

## Data Flow

`GenerateVideoRequest` -> `list[Scene]` -> `list[SceneWithVideo]` -> processed clips -> final MP4.

The default `run.bat` flow renders both:

- `output/final_landscape.mp4`: 1920x1080, 16:9
- `output/final_shorts.mp4`: 1080x1920, 9:16

## Failure Strategy

External calls use timeout and retry wrappers. Gemini output is never trusted directly; it is parsed as JSON and validated. FFmpeg is called with argument lists through `subprocess.run` to avoid shell injection.

## Extension Points

Transitions, thumbnails, image-based intro/outro, and burned-in subtitle styling can be added without changing the core scene analysis or Pexels search contracts.
