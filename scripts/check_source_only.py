"""Reject tracked media, executables, and local runtime data."""

from pathlib import Path
import subprocess
import sys

BLOCKED = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".mp3", ".wav", ".flac", ".mp4", ".lrc", ".srt",
    ".exe", ".ncb", ".suo", ".aps",
}
ROOT = Path(__file__).resolve().parent.parent
LOCAL_DATA_PREFIXES = ("ai-webtoon/input/", "ai-webtoon/output/")


def _is_local_runtime_data(path: Path) -> bool:
    """Identify private inputs and generated outputs that must stay local."""
    normalized = path.as_posix()
    markers = {"ai-webtoon/input/.gitkeep", "ai-webtoon/output/.gitkeep"}
    return normalized not in markers and normalized.startswith(LOCAL_DATA_PREFIXES)


def main() -> int:
    """Check Git's index for files excluded from the public source release."""
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
    tracked = [Path(raw.decode("utf-8")) for raw in files if raw]
    blocked_media = [path for path in tracked if path.suffix.lower() in BLOCKED]
    blocked_local_data = [path for path in tracked if _is_local_runtime_data(path)]
    if blocked_media:
        print(f"[TRACKED-MEDIA] {len(blocked_media)} media or executable files remain tracked")
    if blocked_local_data:
        print(
            f"[TRACKED-LOCAL-DATA] {len(blocked_local_data)} runtime input/output files remain tracked"
        )
    if blocked_media or blocked_local_data:
        return 1
    print("[SOURCE-ONLY] PASS: 0 tracked media, executables, or runtime data files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
