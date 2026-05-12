# AI Anime Monochrome Cinematic MV System

A reusable Python pipeline for turning raw song information into an anime-style monochrome cinematic music video package.

The system creates:

- `input/song_master.json`
- `analysis/emotion_analysis.json`
- `analysis/visual_world.json`
- `analysis/cinematic_style.json`
- `character/protagonist_bible.json`
- `character/character_prompt.md`
- `storyboard/scene_list.json`
- `storyboard/story_arc.json`
- `storyboard/story_summary.md`
- `storyboard/storyboard_prompts.md`
- `storyboard/camera_directions.md`
- per-scene image prompts
- per-scene video prompts for Runway, Kling, Pika, and Luma
- optional versioned snapshots under `output/storyboard/`

## Concept

Each song becomes its own emotional cinematic world. Characters may change between songs, but within one song the protagonist identity, hairstyle, outfit, color rules, atmosphere, and visual tone stay consistent.

The default visual identity is:

- anime cinematic style
- monochrome black and white base
- one accent color only
- emotional composition
- soft cinematic lighting
- atmospheric environments
- strong silhouettes
- film-like framing
- non-photorealistic stylized visuals

## Requirements

Python 3.10 or newer is recommended.

No third-party dependencies are required for the current local pipeline.

## Folder Structure

```text
ai-anime-mv-system/
├─ input/
│  ├─ raw_song.txt
│  ├─ lyrics.lrc
│  └─ song_master.json
├─ analysis/
│  ├─ emotion_analysis.json
│  ├─ visual_world.json
│  └─ cinematic_style.json
├─ character/
│  ├─ protagonist_bible.json
│  ├─ character_prompt.md
│  └─ character_reference/
├─ storyboard/
│  ├─ scene_list.json
│  ├─ storyboard_prompts.md
│  └─ camera_directions.md
├─ prompts/
│  ├─ image_prompts/
│  ├─ video_prompts/
│  └─ style_rules.md
├─ output/
│  ├─ images/
│  ├─ storyboard/
│  └─ videos/
└─ scripts/
   ├─ parser.py
   ├─ emotion_engine.py
   ├─ scene_generator.py
   ├─ image_prompt_generator.py
   ├─ video_prompt_generator.py
   └─ run_pipeline.py
```

## Input Format

Copy the base files for a song into `input/`. The parser scans the folder and builds `input/song_master.json` from the available files.

Supported input files:

- `.txt` for style, metadata, and section lyrics
- `.lrc` for timestamped lyrics
- `.srt` for subtitle-style timestamped lyrics
- Optional audio files (`.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`, `.ogg`) for reference metadata such as duration

If multiple files are present, `raw_song.txt` is used as the primary metadata/section source when available, `.lrc` or `.srt` is used for timed lyrics, and audio files are stored as optional reference metadata.

Audio files are analyzed when present. By default, the analysis is saved in `song_master.json` as reference data only. Enable audio analysis application when you want the generated storyboard metadata to use audio-derived energy and pacing hints.

Supported metadata fields:

```text
Genre:
BPM:
Mood:
Energy:
Instruments:
Music style tags:
Negative tags:
Visual cues:
Atmosphere:
Pacing:
```

Supported section labels:

```text
[Intro]
[Verse]
[Pre-Chorus]
[Chorus]
[Bridge]
[Outro]
```

LRC timestamped lyrics are also recognized when present.

## Run the Full Pipeline

From this folder:

```powershell
python scripts/run_pipeline.py
```

Run with a versioned snapshot:

```powershell
python scripts/run_pipeline.py --snapshot
```

Run with a custom input file or folder:

```powershell
python scripts/run_pipeline.py --input input/my_song.txt --snapshot
python scripts/run_pipeline.py --input input --snapshot
```

Apply optional audio analysis hints during generation:

```powershell
python scripts/run_pipeline.py --input input --apply-audio-analysis --snapshot
```

## Run the Web UI

Start the local web page:

```powershell
python scripts/web_app.py
```

Or double-click:

```text
run_web.bat
```

Then open:

```text
http://127.0.0.1:8000
```

The page lets you paste lyrics and metadata, optionally attach `.lrc`, `.srt`, `.mp3`, or `.wav` files, choose whether audio analysis should affect generation, run the pipeline, and review the generated scenes, image prompts, video prompts, and JSON outputs.

For stronger visual consistency, generate `character/character_reference_prompt.md` first as a master character reference image. Then attach that same reference image when creating each scene image, and attach each finished scene image when running its matching video prompt.

The completed result also includes `storyboard/story_arc.json` and `storyboard/story_summary.md`, which describe the overall story in Korean and add scene-by-scene continuity beats.

## Run Individual Steps

```powershell
python scripts/parser.py --input input
python scripts/emotion_engine.py
python scripts/scene_generator.py
python scripts/image_prompt_generator.py
python scripts/video_prompt_generator.py
```

## Pipeline

```text
RAW MUSIC INPUT
↓
Music Parser
↓
song_master.json
↓
Emotion Analysis Engine
↓
Visual World Generator
↓
Anime MV Scene Generator
↓
Storyboard Generator
↓
GPT Image Prompt Generator
↓
Video Prompt Generator
```

## Output Notes

The generated prompt files are intended as creative-direction prompts for image and video tools. The current scripts do not call external AI services. This keeps the pipeline deterministic, local, and easy to automate later.

The `--snapshot` flag never overwrites previous storyboard packages. Each run creates a timestamped folder in `output/storyboard/`.

## Extension Points

Good next modules to add:

- shot duration estimation from BPM and song structure
- OpenAI API integration for richer lyric interpretation
- image generation adapter
- Runway, Kling, Pika, or Luma export adapters
- reference image management
- prompt scoring and consistency checks
- final edit decision list generation
