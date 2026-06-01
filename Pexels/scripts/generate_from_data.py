from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.request import GenerateVideoRequest
from app.services.data_input_service import DataInputService
from app.services.html_report_service import HtmlReportService
from app.services.pipeline_service import VideoPipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an MP4 from files in the data folder.")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--output", default="output/final_shorts.mp4")
    parser.add_argument("--orientation", default="portrait", choices=["portrait", "landscape", "square"])
    parser.add_argument("--style", default="cinematic music video")
    parser.add_argument("--max-lines", type=int, default=12, help="Limit lyric/script lines sent to Gemini. Use 0 for all.")
    parser.add_argument("--no-music", action="store_true")
    parser.add_argument("--no-subtitles", action="store_true")
    parser.add_argument("--report", default="output/index.html")
    parser.add_argument("--open", action="store_true", help="Open the generated HTML report in the default browser.")
    parser.add_argument("--both", action="store_true", help="Generate landscape and shorts outputs.")
    parser.add_argument("--shorts-lines", type=int, default=4, help="Lyric/script lines used for the Shorts version.")
    parser.add_argument("--shorts-duration", type=float, default=45.0, help="Maximum Shorts duration in seconds.")
    args = parser.parse_args()

    max_lines = None if args.max_lines == 0 else args.max_lines
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    gitkeep = Path(args.output).parent / ".gitkeep"
    gitkeep.touch(exist_ok=True)
    assets = DataInputService().discover(Path(args.data_dir), max_lines=max_lines)

    print(f"data_dir: {assets.data_dir}")
    print(f"lyric_file: {assets.lyric_file}")
    print(f"audio_file: {assets.audio_file}")
    print(f"subtitle_file: {assets.subtitle_file}")
    print(f"image_file: {assets.image_file} (not yet used in render)")
    print(f"text_lines: {len([line for line in assets.text.splitlines() if line.strip()])}")
    print(f"output: {args.output}")

    if args.both:
        results = []
        print("generating_landscape: output/final_landscape.mp4")
        results.append(
            VideoPipeline().generate(
                GenerateVideoRequest(
                    text=assets.text,
                    orientation="landscape",
                    style=f"{args.style}, full-length youtube landscape 16:9",
                    with_music=bool(assets.audio_file) and not args.no_music,
                    music_file=str(assets.audio_file) if assets.audio_file else None,
                    with_subtitles=bool(assets.subtitle_file) and not args.no_subtitles,
                    subtitle_file=str(assets.subtitle_file) if assets.subtitle_file else None,
                    output_path="output/final_landscape.mp4",
                )
            )
        )
        shorts_assets = DataInputService().discover(Path(args.data_dir), max_lines=args.shorts_lines)
        print("generating_shorts: output/final_shorts.mp4")
        results.append(
            VideoPipeline().generate(
                GenerateVideoRequest(
                    text=shorts_assets.text,
                    orientation="portrait",
                    style=f"{args.style}, short-form youtube shorts highlight, strongest hook only",
                    with_music=bool(shorts_assets.audio_file) and not args.no_music,
                    music_file=str(shorts_assets.audio_file) if shorts_assets.audio_file else None,
                    with_subtitles=bool(shorts_assets.subtitle_file) and not args.no_subtitles,
                    subtitle_file=str(shorts_assets.subtitle_file) if shorts_assets.subtitle_file else None,
                    output_path="output/final_shorts.mp4",
                    target_duration=args.shorts_duration,
                )
            )
        )
        report = HtmlReportService().write_multi_report(results, assets, Path(args.report))
        print(f"report_file: {report}")
        if args.open:
            webbrowser.open(report.resolve().as_uri())
        return 0

    result = VideoPipeline().generate(
        GenerateVideoRequest(
            text=assets.text,
            orientation=args.orientation,
            style=args.style,
            with_music=bool(assets.audio_file) and not args.no_music,
            music_file=str(assets.audio_file) if assets.audio_file else None,
            with_subtitles=bool(assets.subtitle_file) and not args.no_subtitles,
            subtitle_file=str(assets.subtitle_file) if assets.subtitle_file else None,
            output_path=args.output,
            target_duration=args.shorts_duration if args.orientation == "portrait" else None,
        )
    )

    print(f"status: {result.status}")
    print(f"project_id: {result.project_id}")
    print(f"scenes: {len(result.scenes)}")
    print(f"output_file: {result.output_file}")
    report = HtmlReportService().write_report(result, assets, Path(args.report))
    print(f"report_file: {report}")
    if args.open:
        webbrowser.open(report.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
