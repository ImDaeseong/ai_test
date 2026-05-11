from __future__ import annotations

import argparse
from pathlib import Path

from app.config import settings
from app.models.request import GenerateVideoRequest
from app.services.pipeline_service import VideoPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate stock-footage videos from text.")
    parser.add_argument("--input", help="Input text file path")
    parser.add_argument("--text", help="Raw input text")
    parser.add_argument("--orientation", default=settings.default_orientation)
    parser.add_argument("--output", help="Output MP4 path")
    parser.add_argument("--style", default="cinematic")
    return parser.parse_args()


def run_cli() -> None:
    args = parse_args()
    if args.input:
        text = Path(args.input).read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        raise SystemExit("Provide --input path or --text.")

    request = GenerateVideoRequest(
        text=text,
        orientation=args.orientation,
        style=args.style,
        output_path=args.output,
    )
    result = VideoPipeline().generate(request)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    run_cli()
