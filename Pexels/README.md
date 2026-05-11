# AI Pexels Video Generator

Local automation tool that turns files in `data/` into stock-footage music videos using Gemini, Pexels, and FFmpeg.

## Quick Start

Double-click:

```bat
run.bat
```

It creates both final videos and opens a browser report:

- `output/final_landscape.mp4`: regular YouTube landscape video, 1920x1080, 16:9
- `output/final_shorts.mp4`: YouTube Shorts portrait video, 1080x1920, 9:16
- `output/index.html`: preview page for both videos and scene-level clips

## Data

Put files in `data/`:

- Lyrics/script: `.lrc`, `.srt`, `.txt`
- Audio: `.wav`, `.mp3`, `.m4a`, `.aac`
- Subtitle track: `.srt`

The final video duration is matched to the music duration.

## Environment

Copy `.env.example` to `.env` and set:

```env
GEMINI_API_KEY=...
PEXELS_API_KEY=...
```

FFmpeg must be installed and available in `PATH`.

## Developer Tools

```bat
dev_tools.bat
```

Use it to run tests, validate data, generate without opening the browser, or clean generated cache files.
