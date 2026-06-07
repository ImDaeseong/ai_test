from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from common import PROJECT_ROOT
from policy_safety import policy_risk_hits


SKIP_OUTPUT_DIRS = {
    "images",
    "storyboard",
    "videos",
    "web_inputs",
}
IMAGE_SHOT_SUFFIXES = ("_wide", "_action", "_emotion", "_detail")
REQUIRED_OUTPUT_DOCS = (
    "00_output_folder_guide.md",
    "00_image_generation_guide.md",
    "00_prompt_to_video_workflow.md",
    "00_production_guide.md",
)


@dataclass
class SongReport:
    title: str
    scenes: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def song_output_dirs(output_root: Path) -> list[Path]:
    if not output_root.exists():
        return []
    result = []
    for path in sorted(output_root.iterdir(), key=lambda p: p.name.casefold()):
        if not path.is_dir() or path.name in SKIP_OUTPUT_DIRS:
            continue
        if (path / "image_prompts").is_dir() or (path / "video_prompts").is_dir():
            result.append(path)
    return result


def scene_key(path: Path, collapse_image_variants: bool = False) -> str:
    stem = path.stem
    if collapse_image_variants:
        for suffix in IMAGE_SHOT_SUFFIXES:
            if stem.endswith(suffix):
                return stem[: -len(suffix)]
    return stem


def image_shot_label(path: Path) -> str:
    for suffix in IMAGE_SHOT_SUFFIXES:
        if path.stem.endswith(suffix):
            return suffix.lstrip("_")
    return "action"


def scene_files(folder: Path, collapse_image_variants: bool = False) -> dict[str, Path]:
    if not folder.is_dir():
        return {}
    files = {}
    for path in sorted(folder.glob("scene_*.md")):
        files.setdefault(scene_key(path, collapse_image_variants), path)
    return files


def extract_identity_anchors(reference: str) -> list[str]:
    anchors: list[str] = []

    patterns = [
        r"face structure:\s*([^,]+,\s*[^,]+,\s*[^,]+,\s*[^,]+)",
        r"song-specific face detail:\s*([^,]+)",
        r"signature gesture:\s*([^,]+(?:,\s*then [^,]+)?)",
        r"Signature prop:\s*([^.]+)",
        r"Accent detail:\s*([^.]+)",
        r"Primary recurring subject:\s*([^.]+)",
        r"Subject design:\s*([^,]+,\s*[^,]+,\s*[^,]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, reference)
        if match:
            anchors.append(match.group(1).strip())

    design_match = re.search(
        r"Character design:\s*(.*?)(?:\. Signature prop:|\. Accent detail:)",
        reference,
        flags=re.DOTALL,
    )
    if design_match:
        clauses = [c.strip() for c in design_match.group(1).split(",")]
        keywords = (
            "hair",
            "bob",
            "jacket",
            "coat",
            "shirt",
            "dress",
            "uniform",
            "suit",
            "sweater",
            "glove",
            "hairpin",
            "accessory",
        )
        for clause in clauses:
            if any(keyword in clause.lower() for keyword in keywords):
                anchors.append(clause)

    unique: list[str] = []
    seen = set()
    for anchor in anchors:
        cleaned = re.sub(r"\s+", " ", anchor).strip(" .")
        if len(cleaned) < 8:
            continue
        key = cleaned.casefold()
        if key not in seen:
            unique.append(cleaned)
            seen.add(key)
    return unique


def extract_palette_sentence(reference: str) -> str | None:
    match = re.search(r"limited-color anime palette:\s*([^.]+)\.", reference)
    if not match:
        return None
    return "limited-color anime palette: " + re.sub(r"\s+", " ", match.group(1)).strip()


def contains_text(content: str, needle: str) -> bool:
    return needle.casefold() in content.casefold()


def missing_anchors(content: str, anchors: list[str]) -> list[str]:
    return [anchor for anchor in anchors if not contains_text(content, anchor)]


def check_other_title_leaks(content: str, own_title: str, all_titles: list[str]) -> list[str]:
    leaked = []
    for title in all_titles:
        if title == own_title or len(title.strip()) < 3:
            continue
        if title in own_title or own_title in title:
            continue
        if title in content:
            leaked.append(title)
    return leaked


def is_non_human_subject(reference: str) -> bool:
    match = re.search(r"Primary subject type:\s*([^)]+)\)", reference)
    if not match:
        return "environment-led" in reference or "non-human" in reference
    subject_type = match.group(1).casefold()
    return "environment_only" in subject_type or "object_symbol" in subject_type


def validate_song(song_dir: Path, all_titles: list[str]) -> SongReport:
    title = song_dir.name
    report = SongReport(title=title)
    ref_path = song_dir / "character_reference_prompt.md"
    image_dir = song_dir / "image_prompts"
    video_dir = song_dir / "video_prompts"
    clip_dir = song_dir / "video_clip_prompts"

    if not ref_path.exists():
        report.errors.append("character_reference_prompt.md missing")
        return report
    if not image_dir.is_dir():
        report.errors.append("image_prompts folder missing")
        return report
    if not video_dir.is_dir():
        report.errors.append("video_prompts folder missing")
        return report
    if not clip_dir.is_dir():
        report.errors.append("video_clip_prompts folder missing")
        return report

    reference = read_text(ref_path)
    ref_hits = policy_risk_hits(reference)
    if ref_hits:
        report.errors.append(
            "character_reference_prompt.md contains policy-sensitive term(s): " + ", ".join(ref_hits[:8])
        )
    anchors = extract_identity_anchors(reference)
    palette = extract_palette_sentence(reference)
    title_lock = f"belong only to '{title}'"
    non_human_subject = is_non_human_subject(reference)
    min_reference_anchors = 3 if non_human_subject else 5
    min_video_anchors = 2 if non_human_subject else max(3, len(anchors) // 2)

    if len(anchors) < min_reference_anchors:
        report.errors.append(f"identity anchors too weak in character reference ({len(anchors)} found)")
    if not palette:
        report.errors.append("limited-color anime palette missing in character reference")
    if not contains_text(reference, title_lock):
        report.errors.append("song-specific title lock missing or mismatched in character reference")

    image_prompt_files = sorted(image_dir.glob("scene_*.md"))
    image_scenes = scene_files(image_dir, collapse_image_variants=True)
    video_scenes = scene_files(video_dir)
    clip_files = sorted(clip_dir.glob("scene_*_clip_*.md"))
    report.scenes = max(len(image_scenes), len(video_scenes))
    if not image_scenes:
        report.errors.append("no image scene prompts found")
    if not video_scenes:
        report.errors.append("no video scene prompts found")

    image_only = sorted(set(image_scenes) - set(video_scenes))
    video_only = sorted(set(video_scenes) - set(image_scenes))
    if image_only:
        report.errors.append("image scenes without matching video prompts: " + ", ".join(image_only))
    if video_only:
        report.errors.append("video scenes without matching image prompts: " + ", ".join(video_only))
    if not clip_files:
        report.errors.append("no video clip prompts found")

    for doc_name in REQUIRED_OUTPUT_DOCS:
        if not (song_dir / doc_name).exists():
            report.errors.append(f"{doc_name} missing")

    timeline_plan = clip_dir / "timeline_plan.md"
    if not timeline_plan.exists():
        report.errors.append("video_clip_prompts/timeline_plan.md missing")

    for path in image_prompt_files:
        content = read_text(path)
        risk_hits = policy_risk_hits(content)
        if risk_hits:
            report.errors.append(
                f"{path.relative_to(song_dir)} contains policy-sensitive term(s): "
                + ", ".join(risk_hits[:8])
            )
        leaks = check_other_title_leaks(content, title, all_titles)
        if leaks:
            report.errors.append(f"{path.relative_to(song_dir)} leaks other song title(s): {', '.join(leaks[:5])}")
        if not contains_text(content, title_lock):
            report.errors.append(f"{path.relative_to(song_dir)} missing song title identity lock")
        if palette and not contains_text(content, palette):
            report.errors.append(f"{path.relative_to(song_dir)} missing reference palette")
        missing = missing_anchors(content, anchors)
        present_count = len(anchors) - len(missing)
        shot_label = image_shot_label(path)
        if shot_label == "action" and missing and not non_human_subject:
            report.errors.append(
                f"{path.relative_to(song_dir)} missing identity anchor(s): "
                + "; ".join(missing[:4])
            )
        elif shot_label == "emotion" and anchors and present_count < 2:
            report.errors.append(
                f"{path.relative_to(song_dir)} has weak emotion identity carryover "
                f"({present_count}/{len(anchors)} anchors present)"
            )
        elif shot_label in {"wide", "detail"} and anchors and present_count == 0:
            report.warnings.append(
                f"{path.relative_to(song_dir)} has no direct character anchors "
                f"({shot_label} shot should still keep title lock, palette, motif, and reference image)"
            )

    for stem, path in video_scenes.items():
        content = read_text(path)
        risk_hits = policy_risk_hits(content)
        if risk_hits:
            report.errors.append(
                f"{path.relative_to(song_dir)} contains policy-sensitive term(s): "
                + ", ".join(risk_hits[:8])
            )
        leaks = check_other_title_leaks(content, title, all_titles)
        if leaks:
            report.errors.append(f"{path.relative_to(song_dir)} leaks other song title(s): {', '.join(leaks[:5])}")
        if "Preserve the character design:" not in content and "Preserve the primary visual subject:" not in content:
            report.errors.append(f"{path.relative_to(song_dir)} missing video character preservation instruction")
        if palette and not contains_text(content, palette):
            report.errors.append(f"{path.relative_to(song_dir)} missing reference palette")

        missing = missing_anchors(content, anchors)
        present_count = len(anchors) - len(missing)
        if anchors and present_count < min_video_anchors:
            report.errors.append(
                f"{path.relative_to(song_dir)} has weak video identity carryover "
                f"({present_count}/{len(anchors)} anchors present)"
            )
        elif missing:
            report.warnings.append(
                f"{path.relative_to(song_dir)} omits some reference anchors "
                f"({present_count}/{len(anchors)} present)"
            )

    clip_prefixes = {re.sub(r"_clip_\d+$", "", path.stem) for path in clip_files}
    missing_clip_scenes = sorted(set(video_scenes) - clip_prefixes)
    if missing_clip_scenes:
        report.errors.append("video scenes without clip prompts: " + ", ".join(missing_clip_scenes))

    for path in clip_files:
        content = read_text(path)
        risk_hits = policy_risk_hits(content)
        if risk_hits:
            report.errors.append(
                f"{path.relative_to(song_dir)} contains policy-sensitive term(s): "
                + ", ".join(risk_hits[:8])
            )
        leaks = check_other_title_leaks(content, title, all_titles)
        if leaks:
            report.errors.append(f"{path.relative_to(song_dir)} leaks other song title(s): {', '.join(leaks[:5])}")
        if "Reference flow:" not in content:
            report.errors.append(f"{path.relative_to(song_dir)} missing reference flow")
        if "Clip role:" not in content:
            report.errors.append(f"{path.relative_to(song_dir)} missing clip role")
        if "Identity lock:" not in content:
            report.errors.append(f"{path.relative_to(song_dir)} missing identity lock")
        if palette and not contains_text(content, palette):
            report.errors.append(f"{path.relative_to(song_dir)} missing reference palette")
        missing = missing_anchors(content, anchors)
        present_count = len(anchors) - len(missing)
        if anchors and present_count < min_video_anchors:
            report.errors.append(
                f"{path.relative_to(song_dir)} has weak clip identity carryover "
                f"({present_count}/{len(anchors)} anchors present)"
            )

    model_sheet = image_dir / "00_character_turnaround_model_sheet.md"
    if not model_sheet.exists():
        report.errors.append("00_character_turnaround_model_sheet.md missing")
    else:
        model_content = read_text(model_sheet)
        risk_hits = policy_risk_hits(model_content)
        if risk_hits:
            report.errors.append(
                "00_character_turnaround_model_sheet.md contains policy-sensitive term(s): "
                + ", ".join(risk_hits[:8])
            )
        if palette and not contains_text(model_content, palette):
            report.errors.append("00_character_turnaround_model_sheet.md missing reference palette")
        missing = missing_anchors(model_content, anchors)
        if missing:
            report.errors.append(
                "00_character_turnaround_model_sheet.md missing identity anchor(s): "
                + "; ".join(missing[:4])
            )

    return report


def format_report(reports: list[SongReport]) -> str:
    passed = sum(1 for report in reports if report.passed)
    failed = len(reports) - passed
    warning_count = sum(len(report.warnings) for report in reports)
    lines = [
        "# Output Prompt Consistency Report",
        "",
        f"Songs checked: {len(reports)}",
        f"PASS: {passed}",
        f"FAIL: {failed}",
        f"Warnings: {warning_count}",
        "",
    ]
    for report in reports:
        status = "PASS" if report.passed else "FAIL"
        lines.append(f"## [{status}] {report.title} ({report.scenes} scenes)")
        if report.errors:
            lines.append("Errors:")
            lines.extend(f"- {issue}" for issue in report.errors)
        if report.warnings:
            lines.append("Warnings:")
            lines.append(f"- {len(report.warnings)} video prompt(s) omit non-critical reference anchor details.")
            lines.append(f"- Example: {report.warnings[0]}")
        if not report.errors and not report.warnings:
            lines.append("- No consistency issues found.")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate per-song consistency across generated output image/video prompts."
    )
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "output"))
    parser.add_argument("--report", default=str(PROJECT_ROOT / "output" / "consistency_report.md"))
    args = parser.parse_args()

    output_root = Path(args.output_root)
    song_dirs = song_output_dirs(output_root)
    all_titles = [path.name for path in song_dirs]
    reports = [validate_song(path, all_titles) for path in song_dirs]
    report_text = format_report(reports)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    print(report_text)
    return 1 if any(not report.passed for report in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
