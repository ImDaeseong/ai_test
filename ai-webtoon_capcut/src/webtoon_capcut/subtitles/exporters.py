from __future__ import annotations

import csv
from pathlib import Path

from ..domain.enums import CueType
from ..domain.models import SubtitleDocument


def _ms_to_srt_timestamp(ms: int) -> str:
    """밀리초를 SRT 타임스탬프 문자열(HH:MM:SS,mmm)로 변환한다."""
    total_seconds, millis = divmod(ms, 1000)
    total_minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def export_srt(doc: SubtitleDocument, output_path: str | Path) -> None:
    """SubtitleDocument의 lyric cue를 SRT 파일로 저장한다.

    형식:
        <순번>
        HH:MM:SS,mmm --> HH:MM:SS,mmm
        <텍스트>
        <빈 줄>
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lyric_cues = [c for c in doc.cues if c.cue_type == CueType.lyric]

    lines: list[str] = []
    for seq, cue in enumerate(lyric_cues, start=1):
        start_ts = _ms_to_srt_timestamp(cue.start_ms)
        end_ts = _ms_to_srt_timestamp(cue.end_ms)
        lines.append(str(seq))
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(cue.text)
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def export_review_csv(doc: SubtitleDocument, output_path: str | Path) -> None:
    """SubtitleDocument의 issues를 CSV 파일로 저장한다.

    컬럼: code, severity, cue_id, message, (추가 필드는 extra_info로 직렬화)
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fixed_fields = ["code", "severity", "cue_id", "message"]

    # 모든 issue에서 추가 키를 수집하여 컬럼 순서를 결정한다
    extra_keys: list[str] = []
    for issue in doc.issues:
        for key in issue:
            if key not in fixed_fields and key not in extra_keys:
                extra_keys.append(key)

    fieldnames = fixed_fields + extra_keys

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for issue in doc.issues:
            row: dict = {field: issue.get(field, "") for field in fieldnames}
            writer.writerow(row)
