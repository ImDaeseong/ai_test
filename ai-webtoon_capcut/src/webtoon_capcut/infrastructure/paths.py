"""Path safety and naming utilities.

Provides:
- safe_relative   — resolves a path relative to a root, blocking traversal outside
- slugify         — human-readable slug from a song title (Korean/ASCII safe)
- make_song_id    — stable song identifier
- make_run_id     — per-run unique identifier
- ensure_dir      — create a directory tree if it does not exist
- project_root    — absolute path to the project root
- config_path     — absolute path to config/default.json

Only stdlib is used (pathlib, re, unicodedata, hashlib via hashing module).
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from webtoon_capcut.domain.errors import ErrorCode, WCBlockedError
from webtoon_capcut.infrastructure.hashing import sha256_str


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------


def safe_relative(base: Path, target: Path) -> str:
    """Return *target* as a forward-slash string relative to *base*.

    Both paths are fully resolved before comparison so that symlinks and ``..``
    components do not bypass the check.

    Args:
        base: Trusted root directory.
        target: Path that must be inside *base*.

    Returns:
        Relative path string using forward slashes (POSIX style).

    Raises:
        WCBlockedError: With :attr:`ErrorCode.PATH_OUTSIDE_ROOT` if *target*
            resolves to a location outside *base*.
    """
    resolved_base = base.resolve()
    resolved_target = target.resolve()

    try:
        relative = resolved_target.relative_to(resolved_base)
    except ValueError:
        raise WCBlockedError(
            ErrorCode.PATH_OUTSIDE_ROOT,
            f"Path '{target}' is outside root '{base}'.",
        )

    return relative.as_posix()


# ---------------------------------------------------------------------------
# Slug and ID generation
# ---------------------------------------------------------------------------


def slugify(title: str) -> str:
    """Convert *title* to a URL/filename-safe slug.

    Rules:
    - Korean (Hangul), ASCII letters, and digits are preserved.
    - Whitespace sequences are replaced with a single hyphen.
    - All other characters (punctuation, symbols, etc.) are removed.
    - The result is lowercased and truncated to 60 characters.
    - Leading and trailing hyphens are stripped.

    Args:
        title: Raw song or folder title.

    Returns:
        Slug string of at most 60 characters.
    """
    # Normalise Unicode to NFC so composed Hangul is handled consistently.
    text = unicodedata.normalize("NFC", title)

    # Lowercase before filtering.
    text = text.lower()

    # Replace whitespace runs with a hyphen placeholder.
    text = re.sub(r"\s+", "-", text)

    # Keep only Hangul syllables/jamo, ASCII letters, digits, and hyphens.
    text = re.sub(r"[^가-힣ᄀ-ᇿ㄰-㆏a-z0-9\-]", "", text)

    # Collapse consecutive hyphens.
    text = re.sub(r"-{2,}", "-", text)

    # Strip leading/trailing hyphens and truncate.
    text = text.strip("-")[:60]

    return text


def make_song_id(title: str, song_dir: str) -> str:
    """Create a stable, human-readable song identifier.

    Format: ``{slug}-{hash8}`` where *slug* is :func:`slugify` applied to
    *title* and *hash8* is the first 8 hex characters of the SHA-256 of
    *song_dir*.

    Args:
        title: Song title (used for the readable part).
        song_dir: Canonical song directory path (used for the hash part so
            that two songs with the same title but different directories get
            different IDs).

    Returns:
        Song ID string, e.g. ``"upgrade-a1b2c3d4"``.
    """
    slug = slugify(title)
    hash_suffix = sha256_str(song_dir)[:8]
    return f"{slug}-{hash_suffix}"


def make_run_id() -> str:
    """Create a unique run identifier for the current process invocation.

    The ID is not required to be deterministic across runs — it only needs
    to be unique enough to avoid workspace collisions when the same song is
    processed multiple times.

    Format: ``"run-{hash12}"`` where the hash is derived from the current
    working directory and the memory address of a freshly created object.

    Returns:
        Run ID string, e.g. ``"run-3f9a1c2b4e87"``.
    """
    seed = str(Path.cwd()) + str(id(object()))
    hash_suffix = sha256_str(seed)[:12]
    return f"run-{hash_suffix}"


# ---------------------------------------------------------------------------
# Directory helpers
# ---------------------------------------------------------------------------


def ensure_dir(path: Path) -> Path:
    """Create *path* and all intermediate parents if they do not already exist.

    Args:
        path: Directory path to create.

    Returns:
        The same *path* object (for chaining convenience).
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Project layout
# ---------------------------------------------------------------------------


def project_root() -> Path:
    """Return the absolute path to the project root directory.

    Traversal from this file's location:
        ``src/webtoon_capcut/infrastructure/paths.py``
        -> ``src/webtoon_capcut/infrastructure/``   (.parent, step 1)
        -> ``src/webtoon_capcut/``                  (.parent, step 2)
        -> ``src/``                                 (.parent, step 3)
        -> ``<project_root>/``                      (.parent, step 4)

    Returns:
        Resolved absolute :class:`pathlib.Path` of the project root
        (the directory that contains ``config/``, ``src/``, ``docs/``, etc.).
    """
    return Path(__file__).parent.parent.parent.parent.resolve()


def config_path() -> Path:
    """Return the absolute path to ``config/default.json``.

    Returns:
        Resolved path: ``<project_root>/config/default.json``.
    """
    return project_root() / "config" / "default.json"
