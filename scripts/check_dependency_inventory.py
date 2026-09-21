"""Verify that every dependency manifest is covered by the release inventory."""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INVENTORY = Path("DEPENDENCY_INVENTORY.md")
HASH_LINE = re.compile(r"^- `([^`]+)` — `sha256:([0-9a-f]{64})`$", re.MULTILINE)


def _tracked_files(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=False,
    )
    if result.returncode != 0:
        return set()
    return {item.decode("utf-8") for item in result.stdout.split(b"\0") if item}


def _is_manifest(path: str) -> bool:
    name = Path(path).name
    return (
        name.startswith("requirements") and name.endswith(".txt")
        or name in {"pyproject.toml", "package.json", "package-lock.json", "go.mod", "go.sum"}
        or name.endswith(".vcxproj")
    )


def manifest_hash(path: Path) -> str:
    """Return a line-ending-independent SHA-256 for a text manifest."""
    normalized = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def check(root: Path = ROOT, tracked_files: set[str] | None = None) -> list[str]:
    """Return stable errors for uncovered, stale, or unlocked manifests."""
    tracked = _tracked_files(root) if tracked_files is None else tracked_files
    manifests = {path for path in tracked if _is_manifest(path)}
    errors: list[str] = []

    if INVENTORY.as_posix() not in tracked:
        errors.append("INVENTORY_UNTRACKED")
    inventory_path = root / INVENTORY
    if not inventory_path.is_file():
        return errors + ["INVENTORY_MISSING"]

    recorded = dict(HASH_LINE.findall(inventory_path.read_text(encoding="utf-8")))
    missing = sorted(manifests - recorded.keys())
    extra = sorted(recorded.keys() - manifests)
    if missing:
        errors.append("MANIFESTS_UNDOCUMENTED:" + ",".join(missing))
    if extra:
        errors.append("MANIFESTS_STALE:" + ",".join(extra))

    changed = sorted(
        path for path in manifests & recorded.keys()
        if manifest_hash(root / path) != recorded[path]
    )
    if changed:
        errors.append("MANIFEST_HASH_CHANGED:" + ",".join(changed))

    for package_json in sorted(path for path in manifests if path.endswith("package.json")):
        lock = (Path(package_json).parent / "package-lock.json").as_posix()
        if lock not in manifests:
            errors.append("NPM_LOCK_MISSING:" + package_json)
    for lock in sorted(path for path in manifests if path.endswith("package-lock.json")):
        try:
            data = json.loads((root / lock).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            errors.append("NPM_LOCK_INVALID:" + lock)
            continue
        if data.get("lockfileVersion") != 3 or not isinstance(data.get("packages"), dict):
            errors.append("NPM_LOCK_UNSUPPORTED:" + lock)
    return errors


def main(root: Path = ROOT, tracked_files: set[str] | None = None) -> int:
    """Report whether dependency evidence is complete and reproducible."""
    errors = check(root, tracked_files)
    if errors:
        print("[DEPENDENCY-INVENTORY] FAIL: " + ";".join(errors))
        return 1
    print("[DEPENDENCY-INVENTORY] PASS: all tracked manifests covered and npm locks valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
