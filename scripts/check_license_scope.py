"""Verify the root MIT license and third-party boundary stay explicit."""

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LICENSE = Path("LICENSE")
NOTICES = Path("THIRD_PARTY_NOTICES.md")
README = Path("README.md")
LICENSE_SHA256 = "f6ed8a10c522896b3ea0e61ca0588857009561a2b1032e2c0756843facf4803d"
NOTICE_SNIPPETS = (
    "run_game/run_game/json/LICENSE",
    "https://github.com/open-source-parsers/jsoncpp/tree/1.7.2",
    "https://github.com/remotion-dev/remotion/blob/main/LICENSE.md",
    "not covered by the root MIT license",
)
README_SNIPPETS = ("[MIT License](LICENSE)", "[Third-party notices](THIRD_PARTY_NOTICES.md)")


def _tracked_files(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=False,
    )
    if result.returncode != 0:
        return set()
    return {item.decode("utf-8") for item in result.stdout.split(b"\0") if item}


def check(root: Path = ROOT, tracked_files: set[str] | None = None) -> list[str]:
    """Return stable error codes for incomplete or changed license scope files."""
    tracked = _tracked_files(root) if tracked_files is None else tracked_files
    errors = []
    for path in (LICENSE, NOTICES, README):
        if path.as_posix() not in tracked:
            errors.append(f"{path.name.upper().replace('.', '_')}_UNTRACKED")

    license_file = root / LICENSE
    if not license_file.is_file():
        errors.append("ROOT_LICENSE_MISSING")
    elif hashlib.sha256(
        license_file.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    ).hexdigest() != LICENSE_SHA256:
        errors.append("ROOT_LICENSE_CHANGED")

    notice_file = root / NOTICES
    if not notice_file.is_file():
        errors.append("THIRD_PARTY_NOTICES_MISSING")
    else:
        notice = notice_file.read_text(encoding="utf-8")
        if any(snippet not in notice for snippet in NOTICE_SNIPPETS):
            errors.append("THIRD_PARTY_NOTICES_INCOMPLETE")

    readme_file = root / README
    if not readme_file.is_file():
        errors.append("README_MISSING")
    else:
        readme = readme_file.read_text(encoding="utf-8")
        if any(snippet not in readme for snippet in README_SNIPPETS):
            errors.append("README_LICENSE_LINKS_MISSING")
    return errors


def main(root: Path = ROOT, tracked_files: set[str] | None = None) -> int:
    """Report whether the public license boundary is complete and intact."""
    errors = check(root, tracked_files)
    if errors:
        print("[LICENSE-SCOPE] FAIL: " + ",".join(errors))
        return 1
    print("[LICENSE-SCOPE] PASS: MIT root license and third-party boundary intact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
