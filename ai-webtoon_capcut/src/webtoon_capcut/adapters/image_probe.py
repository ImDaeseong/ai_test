"""Image probing utilities.

Extracts dimensions and metadata from image files using direct header parsing
where possible, with ffprobe as a fallback for unsupported formats.
Only stdlib is used (subprocess, struct, pathlib, json).
"""

from __future__ import annotations

import json
import struct
import subprocess
from pathlib import Path

from webtoon_capcut.domain.models import ImageCandidate
from webtoon_capcut.infrastructure.hashing import sha256_file


def probe_image(path: str | Path, panel_id: str) -> ImageCandidate:
    """Probe an image file and return an ImageCandidate.

    Dimension extraction order per format:
    - PNG  : direct header parsing (_read_png_dimensions)
    - JPEG : SOF marker scanning   (_read_jpeg_dimensions)
    - WEBP / others : ffprobe fallback (_ffprobe_dimensions)

    Args:
        path: Path to the image file.
        panel_id: Panel identifier to embed in the returned candidate.

    Returns:
        ImageCandidate with panel_id, path, extension, width, height, and sha256.
    """
    p = Path(path)
    dims = get_image_dimensions(p)
    width, height = dims if dims is not None else (None, None)
    sha256 = sha256_file(p)
    return ImageCandidate(
        panel_id=panel_id,
        path=str(p),
        extension=p.suffix.lower().lstrip("."),
        width=width,
        height=height,
        sha256=sha256,
    )


def get_image_dimensions(path: str | Path) -> tuple[int, int] | None:
    """Return the (width, height) of an image file in pixels.

    Dispatches to format-specific parsers based on file extension, then falls
    back to ffprobe for unsupported extensions.

    Args:
        path: Path to the image file.

    Returns:
        (width, height) tuple, or None if dimensions cannot be determined.
    """
    p = Path(path)
    ext = p.suffix.lower()

    try:
        with open(p, "rb") as fh:
            # Read enough bytes to cover PNG header (24 B) and JPEG scan (up to 64 KiB)
            header = fh.read(65536)
    except OSError:
        return None

    if ext == ".png":
        if len(header) >= 24:
            try:
                return _read_png_dimensions(header)
            except (struct.error, ValueError):
                pass

    elif ext in (".jpg", ".jpeg"):
        try:
            result = _read_jpeg_dimensions(header)
            if result is not None:
                return result
        except (struct.error, ValueError):
            pass

    # Fallback for WEBP, AVIF, HEIC, TIFF and any other formats
    return _ffprobe_dimensions(p)


def _read_png_dimensions(data: bytes) -> tuple[int, int]:
    """Extract width and height from a PNG file's binary header.

    PNG layout:
      Bytes 0-7  : PNG signature (\\x89PNG\\r\\n\\x1a\\n)
      Bytes 8-11 : IHDR chunk length (4 B big-endian)
      Bytes 12-15: IHDR chunk type  ("IHDR")
      Bytes 16-19: width  (4 B big-endian uint32)
      Bytes 20-23: height (4 B big-endian uint32)

    Args:
        data: Raw file bytes (must be at least 24 bytes).

    Returns:
        (width, height) in pixels.

    Raises:
        ValueError: If the PNG signature or IHDR marker is missing.
        struct.error: If the byte slice is too short to unpack.
    """
    PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
    if data[:8] != PNG_SIGNATURE:
        raise ValueError("Not a valid PNG file")
    if data[12:16] != b"IHDR":
        raise ValueError("PNG IHDR chunk not found at expected offset")
    (width,) = struct.unpack_from(">I", data, 16)
    (height,) = struct.unpack_from(">I", data, 20)
    return width, height


def _read_jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    """Scan a JPEG byte stream for an SOF0 marker and extract dimensions.

    JPEG SOF0 (Start of Frame) marker layout:
      0xFF 0xC0 : marker
      2 B       : segment length (big-endian, includes length field itself)
      1 B       : precision (bits per sample)
      2 B       : height (big-endian uint16)
      2 B       : width  (big-endian uint16)

    The function walks all JPEG markers until SOF0 (0xFFC0) is found.
    SOF1-SOF3 (0xFFC1-0xFFC3) are also accepted as equivalent progressive/lossless frames.

    Args:
        data: Raw file bytes.

    Returns:
        (width, height) in pixels, or None if the SOF0 marker is not found.

    Raises:
        struct.error: On a truncated segment.
    """
    if len(data) < 2 or data[:2] != b"\xff\xd8":
        return None  # Not a JPEG

    SOF_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3}
    pos = 2  # skip SOI marker
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            break
        marker_byte = data[pos + 1]

        # Standalone markers (no length field): SOI, EOI, RST0-RST7
        if marker_byte in (0xD8, 0xD9) or 0xD0 <= marker_byte <= 0xD7:
            pos += 2
            continue

        if pos + 4 > len(data):
            break
        (seg_len,) = struct.unpack_from(">H", data, pos + 2)
        # seg_len includes the 2-byte length field itself
        if seg_len < 2:
            break

        if marker_byte in SOF_MARKERS:
            # SOF segment: FF Cx LL LL PP HH HH WW WW ...
            if pos + 9 > len(data):
                break
            (height,) = struct.unpack_from(">H", data, pos + 5)
            (width,) = struct.unpack_from(">H", data, pos + 7)
            return width, height

        pos += 2 + seg_len  # advance past this segment

    return None


def _ffprobe_dimensions(path: Path) -> tuple[int, int] | None:
    """Extract image dimensions using ffprobe.

    Runs:
        ffprobe -v error -select_streams v:0
                -show_entries stream=width,height -of json <path>

    Args:
        path: Path to the image file.

    Returns:
        (width, height) in pixels, or None if ffprobe is unavailable or fails.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
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
        streams = data.get("streams", [])
        if not streams:
            return None
        stream = streams[0]
        width = stream.get("width")
        height = stream.get("height")
        if width is None or height is None:
            return None
        return int(width), int(height)
    except (json.JSONDecodeError, ValueError, KeyError, IndexError):
        return None
