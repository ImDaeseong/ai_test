"""Audio probing utilities.

Extracts duration and metadata from audio files using ffprobe when available,
falling back to direct WAV header parsing for .wav files.
Only stdlib is used (subprocess, struct, pathlib, json).
"""

from __future__ import annotations

import json
import struct
import subprocess
from pathlib import Path

from webtoon_capcut.domain.models import AudioCandidate
from webtoon_capcut.infrastructure.hashing import sha256_file


def probe_audio(path: str | Path) -> AudioCandidate:
    """Probe an audio file and return an AudioCandidate.

    Duration extraction order:
    1. ffprobe (if available on PATH)
    2. WAV header parsing (for .wav files only)
    3. None (for all other cases)

    Args:
        path: Path to the audio file.

    Returns:
        AudioCandidate with path, extension, duration_ms, and sha256.
    """
    p = Path(path)
    duration_ms = get_audio_duration_ms(p)
    sha256 = sha256_file(p)
    return AudioCandidate(
        path=str(p),
        extension=p.suffix.lower().lstrip("."),
        duration_ms=duration_ms,
        sha256=sha256,
    )


def get_audio_duration_ms(path: str | Path) -> int | None:
    """Return the duration of an audio file in milliseconds.

    Tries ffprobe first; falls back to WAV header parsing for .wav files.

    Args:
        path: Path to the audio file.

    Returns:
        Duration in milliseconds, or None if it cannot be determined.
    """
    p = Path(path)
    seconds = _probe_with_ffprobe(p)
    if seconds is not None:
        return int(round(seconds * 1000))

    if p.suffix.lower() == ".wav":
        return _parse_wav_duration(p)

    return None


def _probe_with_ffprobe(path: Path) -> float | None:
    """Extract duration in seconds using ffprobe.

    Args:
        path: Path to the audio file.

    Returns:
        Duration as a float (seconds), or None if ffprobe is unavailable or fails.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None

    if result.returncode != 0:
        return None

    try:
        data = json.loads(result.stdout)
        duration_str = data.get("format", {}).get("duration")
        if duration_str is None:
            return None
        return float(duration_str)
    except (json.JSONDecodeError, ValueError, KeyError):
        return None


def _parse_wav_duration(path: Path) -> int | None:
    """Parse a WAV file header directly to extract duration in milliseconds.

    WAV RIFF layout:
      Offset  Size  Field
       0       4    ChunkID      "RIFF"
       4       4    ChunkSize    (little-endian uint32)
       8       4    Format       "WAVE"
      12       4    Subchunk1ID  "fmt "
      16       4    Subchunk1Size
      20       2    AudioFormat
      22       2    NumChannels
      24       4    SampleRate
      28       4    ByteRate
      32       2    BlockAlign
      34       2    BitsPerSample
      -- then further subchunks until "data" is found --

    The number of samples = data_chunk_size / (num_channels * bits_per_sample / 8)
    Duration (s) = num_samples / sample_rate

    Args:
        path: Path to the .wav file.

    Returns:
        Duration in milliseconds, or None if parsing fails.
    """
    try:
        with open(path, "rb") as fh:
            header = fh.read(44)  # minimum WAV header size

        if len(header) < 44:
            return None

        # Validate RIFF and WAVE markers
        if header[0:4] != b"RIFF" or header[8:12] != b"WAVE":
            return None

        # fmt subchunk starts at offset 12; verify subchunk1 id
        if header[12:16] != b"fmt ":
            return None

        # Parse fmt subchunk fields (all little-endian)
        (subchunk1_size,) = struct.unpack_from("<I", header, 16)
        (num_channels,) = struct.unpack_from("<H", header, 22)
        (sample_rate,) = struct.unpack_from("<I", header, 24)
        (bits_per_sample,) = struct.unpack_from("<H", header, 34)

        if sample_rate == 0 or num_channels == 0 or bits_per_sample == 0:
            return None

        bytes_per_sample = bits_per_sample // 8
        if bytes_per_sample == 0:
            return None

        # Seek past fmt subchunk to find the "data" chunk.
        # fmt subchunk body starts at offset 20; body length = subchunk1_size
        # Next chunk starts at: 20 + subchunk1_size
        data_chunk_size: int | None = None
        with open(path, "rb") as fh:
            fh.seek(20 + subchunk1_size)
            # Walk subchunks until "data" or EOF
            for _ in range(64):  # guard against malformed files
                chunk_id = fh.read(4)
                if len(chunk_id) < 4:
                    break
                (chunk_size,) = struct.unpack("<I", fh.read(4))
                if chunk_id == b"data":
                    data_chunk_size = chunk_size
                    break
                # Skip this chunk's body
                fh.seek(chunk_size, 1)

        if data_chunk_size is None:
            return None

        num_samples = data_chunk_size // (num_channels * bytes_per_sample)
        duration_ms = int(round(num_samples / sample_rate * 1000))
        return duration_ms

    except (OSError, struct.error, ZeroDivisionError):
        return None
