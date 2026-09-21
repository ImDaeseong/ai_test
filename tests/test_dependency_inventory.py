"""Regression tests for dependency inventory coverage and lock integrity."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_dependency_inventory as guard


def _write_inventory(root: Path, manifests: list[str]) -> None:
    lines = ["# Inventory", ""]
    for path in manifests:
        lines.append(f"- `{path}` — `sha256:{guard.manifest_hash(root / path)}`")
    (root / guard.INVENTORY).write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_inventory_accepts_covered_locked_manifests(tmp_path: Path) -> None:
    """A documented npm manifest and version-3 lock pass together."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app/package.json").write_text('{"dependencies":{}}\n', encoding="utf-8")
    (tmp_path / "app/package-lock.json").write_text(
        json.dumps({"lockfileVersion": 3, "packages": {}}), encoding="utf-8"
    )
    manifests = ["app/package.json", "app/package-lock.json"]
    _write_inventory(tmp_path, manifests)
    tracked = set(manifests) | {guard.INVENTORY.as_posix()}
    assert guard.check(tmp_path, tracked) == []


def test_inventory_rejects_new_manifest_and_missing_lock(tmp_path: Path) -> None:
    """An undocumented package manifest cannot bypass inventory or lock review."""
    (tmp_path / "package.json").write_text('{"dependencies":{}}\n', encoding="utf-8")
    (tmp_path / guard.INVENTORY).write_text("# Inventory\n", encoding="utf-8")
    tracked = {"package.json", guard.INVENTORY.as_posix()}
    errors = guard.check(tmp_path, tracked)
    assert "MANIFESTS_UNDOCUMENTED:package.json" in errors
    assert "NPM_LOCK_MISSING:package.json" in errors


def test_inventory_rejects_changed_manifest(tmp_path: Path) -> None:
    """A manifest edit requires the reviewed inventory hash to be refreshed."""
    (tmp_path / "requirements.txt").write_text("example==1.0\n", encoding="utf-8")
    _write_inventory(tmp_path, ["requirements.txt"])
    (tmp_path / "requirements.txt").write_text("example==2.0\n", encoding="utf-8")
    tracked = {"requirements.txt", guard.INVENTORY.as_posix()}
    assert guard.check(tmp_path, tracked) == ["MANIFEST_HASH_CHANGED:requirements.txt"]


def test_inventory_rejects_stale_entry(tmp_path: Path) -> None:
    """A removed manifest cannot leave stale release evidence behind."""
    (tmp_path / "requirements.txt").write_text("example==1.0\n", encoding="utf-8")
    _write_inventory(tmp_path, ["requirements.txt"])
    tracked = {guard.INVENTORY.as_posix()}
    assert guard.check(tmp_path, tracked) == ["MANIFESTS_STALE:requirements.txt"]


def test_inventory_rejects_invalid_or_unsupported_npm_lock(tmp_path: Path) -> None:
    """Malformed and unsupported npm lockfiles fail deterministically."""
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad/package-lock.json").write_text("not json\n", encoding="utf-8")
    (tmp_path / "old").mkdir()
    (tmp_path / "old/package-lock.json").write_text(
        json.dumps({"lockfileVersion": 2, "packages": {}}), encoding="utf-8"
    )
    manifests = ["bad/package-lock.json", "old/package-lock.json"]
    _write_inventory(tmp_path, manifests)
    tracked = set(manifests) | {guard.INVENTORY.as_posix()}
    assert guard.check(tmp_path, tracked) == [
        "NPM_LOCK_INVALID:bad/package-lock.json",
        "NPM_LOCK_UNSUPPORTED:old/package-lock.json",
    ]
