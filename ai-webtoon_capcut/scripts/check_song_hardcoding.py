"""Detect fixture song names embedded in executable Python source."""
from __future__ import annotations

import argparse
import ast
from pathlib import Path

DEFAULT_NAMES = ("UPGRADE", "디저트", "떠나고")

def _docstring_nodes(tree: ast.AST) -> set[int]:
    ignored: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                ignored.add(id(body[0].value))
    return ignored

def find_hardcoded_song_names(source_root: Path, names: tuple[str, ...] = DEFAULT_NAMES) -> list[str]:
    """Return executable string literals containing fixture-only song names."""
    findings: list[str] = []
    for path in sorted(source_root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as error:
            findings.append(f"{path}:INVALID:{error}")
            continue
        ignored = _docstring_nodes(tree)
        for node in ast.walk(tree):
            if id(node) in ignored or not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            for name in names:
                if name.casefold() in node.value.casefold():
                    findings.append(f"{path}:{getattr(node, 'lineno', 0)}:{name}")
    return findings

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1] / "src")
    args = parser.parse_args()
    findings = find_hardcoded_song_names(args.root.resolve())
    if findings:
        print("\n".join(findings))
        return 1
    print("PASS: executable Python source contains no fixture song names")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
