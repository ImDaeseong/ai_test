"""Reject tracked media and compiled files in the source-only release."""

from pathlib import Path
import subprocess
import sys

BLOCKED = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".wav", ".mp4", ".exe"}
ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    """Check Git's index for files excluded from the public source release."""
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
    blocked = [
        path for raw in files if raw
        if (path := Path(raw.decode("utf-8"))).suffix.lower() in BLOCKED
    ]
    if blocked:
        print(f"[TRACKED-MEDIA] {len(blocked)} media or executable files remain tracked")
        return 1
    print("[TRACKED-MEDIA] PASS: 0 tracked media or executable files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
