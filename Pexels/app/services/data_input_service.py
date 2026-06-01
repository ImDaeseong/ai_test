from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataAssets:
    data_dir: Path
    lyric_file: Path
    text: str
    audio_file: Path | None = None
    subtitle_file: Path | None = None
    image_file: Path | None = None


class DataInputService:
    def discover(self, data_dir: Path, max_lines: int | None = None) -> DataAssets:
        if not data_dir.exists():
            raise RuntimeError(f"Data directory does not exist: {data_dir}")
        lyric_file = self._first(data_dir, ["*.lrc", "*.srt", "*.txt"])
        if not lyric_file:
            raise RuntimeError("No .lrc, .srt, or .txt lyric/script file found in data directory.")

        text = self.extract_text(lyric_file, max_lines=max_lines)
        if not text.strip():
            raise RuntimeError(f"No usable text extracted from {lyric_file}")

        return DataAssets(
            data_dir=data_dir,
            lyric_file=lyric_file,
            text=text,
            audio_file=self._first(data_dir, ["*.mp3", "*.wav", "*.m4a", "*.aac"]),
            subtitle_file=self._first(data_dir, ["*.srt"]),
            image_file=self._first(data_dir, ["*.png", "*.jpg", "*.jpeg", "*.webp"]),
        )

    def extract_text(self, path: Path, max_lines: int | None = None) -> str:
        suffix = path.suffix.lower()
        raw = path.read_text(encoding="utf-8-sig", errors="replace")
        if suffix == ".lrc":
            lines = self._extract_lrc_lines(raw)
        elif suffix == ".srt":
            lines = self._extract_srt_lines(raw)
        else:
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if max_lines and max_lines > 0:
            lines = lines[:max_lines]
        return "\n".join(lines)

    def _extract_lrc_lines(self, raw: str) -> list[str]:
        lines: list[str] = []
        for line in raw.splitlines():
            clean = re.sub(r"\[[^\]]*\]", "", line).strip()
            if clean and not clean.lower().startswith("instrumental"):
                lines.append(clean)
        return lines

    def _extract_srt_lines(self, raw: str) -> list[str]:
        lines: list[str] = []
        for line in raw.splitlines():
            clean = line.strip()
            if not clean or clean.isdigit() or "-->" in clean:
                continue
            lines.append(clean)
        return lines

    def _first(self, data_dir: Path, patterns: list[str]) -> Path | None:
        for pattern in patterns:
            matches = sorted(data_dir.glob(pattern))
            if matches:
                return matches[0]
        return None
