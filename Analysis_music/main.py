#!/usr/bin/env python3
"""
AI Music & Visual Content Executive Producer
============================================
Analyzes Suno AI prompts (+ optional audio) and generates:
  1. LilyPond sheet music  (.ly)
  2. Music analysis report (report.md)
  3. AI improvement advice (inside report.md)
  4. Visual content prompts (visual_prompts.md)

Usage:
  python main.py --prompt sample_prompt.txt
  python main.py --prompt sample_prompt.txt --audio song.mp3
  python main.py --prompt sample_prompt.txt --audio song.mp3 --out my_outputs
  python main.py --text "[Genre: K-Pop]\n[BPM: 128]\n..."
"""

from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

# Force UTF-8 output on Windows to avoid cp949 encode errors
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    from colorama import Fore, Style, init as colorama_init  # type: ignore[import-untyped]
    colorama_init()
except ImportError:
    class Fore:  # type: ignore[no-redef]
        GREEN = RED = CYAN = YELLOW = MAGENTA = ""
    class Style:  # type: ignore[no-redef]
        RESET_ALL = ""

# ── Banner ──────────────────────────────────────────────────────────────────

BANNER = """
+--------------------------------------------------------------+
|      AI Music & Visual Content Executive Producer           |
|      Powered by Claude Sonnet 4.6 / LilyPond / librosa      |
+--------------------------------------------------------------+
"""


def _ok(msg: str):
    print(f"{Fore.GREEN}  [OK]  {msg}{Style.RESET_ALL}")


def _info(msg: str):
    print(f"{Fore.CYAN}  [>>]  {msg}{Style.RESET_ALL}")


def _warn(msg: str):
    print(f"{Fore.YELLOW}  [!!]  {msg}{Style.RESET_ALL}")


def _err(msg: str):
    print(f"{Fore.RED}  [XX]  {msg}{Style.RESET_ALL}")


def _step(n: int, total: int, msg: str):
    print(f"\n{Fore.MAGENTA}[{n}/{total}]{Style.RESET_ALL} {msg}")


# ── Argument parsing ─────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="AI Music & Visual Content Executive Producer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    input_group = p.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--prompt", "-p",
        metavar="FILE",
        help="Path to a .txt file containing the Suno AI prompt",
    )
    input_group.add_argument(
        "--text", "-t",
        metavar="TEXT",
        help="Inline Suno AI prompt text (use \\n for newlines)",
    )
    p.add_argument(
        "--audio", "-a",
        metavar="FILE",
        help="Optional audio file (.mp3/.wav/.flac/.ogg/.m4a) for deeper analysis",
    )
    p.add_argument(
        "--out", "-o",
        metavar="DIR",
        default="outputs",
        help="Output directory (default: outputs/)",
    )
    p.add_argument(
        "--no-lilypond",
        action="store_true",
        help="Skip LilyPond sheet music generation",
    )
    p.add_argument(
        "--no-visual",
        action="store_true",
        help="Skip visual prompt generation",
    )
    p.add_argument(
        "--render-pdf",
        action="store_true",
        help="Render LilyPond .ly to PDF (requires LilyPond installed)",
    )
    return p


# ── LilyPond PDF rendering ───────────────────────────────────────────────────

def render_lilypond_pdf(ly_path: Path, lilypond_cmd: str = "lilypond") -> bool:
    import subprocess
    try:
        result = subprocess.run(
            [lilypond_cmd, "--output", str(ly_path.parent), str(ly_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ── Main pipeline ────────────────────────────────────────────────────────────

def run(args: argparse.Namespace):
    from config import AUDIO_FORMATS
    from analyzer.suno_parser import SunoParser
    from analyzer.audio_analyzer import AudioAnalyzer
    from generators.lilypond_gen import LilyPondGenerator
    from generators.report_gen import ReportGenerator
    from generators.visual_gen import VisualGenerator

    print(BANNER)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    total_steps = 4 - int(args.no_lilypond) - int(args.no_visual)
    step = 0

    # ── Step: Parse prompt ──────────────────────────────────────────────────
    step += 1
    _step(step, total_steps, "Parsing Suno AI prompt...")
    parser = SunoParser()
    if args.prompt:
        prompt_path = Path(args.prompt)
        if not prompt_path.exists():
            _err(f"Prompt file not found: {prompt_path}")
            sys.exit(1)
        data = parser.parse_file(str(prompt_path))
    else:
        text = args.text.replace("\\n", "\n")
        data = parser.parse(text)

    _ok(f"Title: {data.title}")
    _ok(f"Genre: {', '.join(data.genre)}")
    _ok(f"BPM: {data.bpm}  |  Key: {data.key}  |  Language: {data.language}")
    _ok(f"Sections: {', '.join(s.name for s in data.sections)}")
    _ok(f"Total lyric lines: {data.total_lines}")

    # ── Step: Audio analysis (optional) ────────────────────────────────────
    audio_result = None
    if args.audio:
        step += 1
        _step(step, total_steps, f"Analyzing audio: {args.audio}")
        audio_path = Path(args.audio)
        if not audio_path.exists():
            _warn(f"Audio file not found: {audio_path} — skipping audio analysis")
        elif audio_path.suffix.lower() not in AUDIO_FORMATS:
            _warn(f"Unsupported audio format: {audio_path.suffix} — skipping")
        else:
            analyzer = AudioAnalyzer()
            section_names = [s.name for s in data.sections]
            audio_result = analyzer.analyze(str(audio_path), section_names)
            if audio_result.available:
                _ok(f"Duration: {audio_result.duration_str}")
                _ok(f"Detected BPM: {audio_result.bpm:.1f}")
                _ok(f"Detected Key: {audio_result.estimated_key}")
                _ok(f"Dynamic Range: {audio_result.dynamic_range_db:.1f} dB")
            else:
                _warn(f"Audio analysis failed: {audio_result.error}")
                audio_result = None

    # ── Step: Generate report.md ────────────────────────────────────────────
    step += 1
    _step(step, total_steps, "Generating music analysis report...")
    t0 = time.time()
    report_gen = ReportGenerator()
    report_path = report_gen.generate(data, audio_result, out_dir)
    _ok(f"Report saved → {report_path}  ({time.time()-t0:.1f}s)")

    # ── Step: LilyPond sheet music ──────────────────────────────────────────
    if not args.no_lilypond:
        step += 1
        _step(step, total_steps, "Generating LilyPond sheet music...")
        ly_gen = LilyPondGenerator()
        ly_path = ly_gen.generate(data, out_dir)
        _ok(f"Sheet music saved → {ly_path}")

        if args.render_pdf:
            _info("Rendering PDF with LilyPond...")
            from config import LILYPOND_PATH
            ok = render_lilypond_pdf(ly_path, LILYPOND_PATH)
            if ok:
                pdf = ly_path.with_suffix(".pdf")
                _ok(f"PDF rendered → {pdf}")
            else:
                _warn("LilyPond not found or render failed — .ly file still generated")

    # ── Step: Visual prompts ────────────────────────────────────────────────
    if not args.no_visual:
        step += 1
        _step(step, total_steps, "Generating visual content prompts...")
        t0 = time.time()
        vis_gen = VisualGenerator()
        visual, vp_path = vis_gen.generate(data, out_dir)
        _ok(f"Theme: {visual.theme}")
        _ok(f"Palette: {' · '.join(visual.color_palette[:4])}")
        _ok(f"Video scenes generated: {len(visual.video_scenes)}")
        _ok(f"Visual prompts saved → {vp_path}  ({time.time()-t0:.1f}s)")

    # ── Summary ─────────────────────────────────────────────────────────────
    print(f"\n{Fore.GREEN}{'─'*60}")
    print(f"  All outputs saved to: {out_dir.resolve()}")
    print(f"  Files generated:")
    for f in sorted(out_dir.iterdir()):
        print(f"    {Fore.CYAN}{f.name}{Style.RESET_ALL}  ({f.stat().st_size:,} bytes)")
    print(f"{'─'*60}{Style.RESET_ALL}\n")


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        run(args)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Interrupted.{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as exc:
        _err(f"Unexpected error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
