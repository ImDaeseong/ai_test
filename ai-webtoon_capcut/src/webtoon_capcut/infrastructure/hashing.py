"""Cryptographic hashing utilities.

All functions produce lowercase hex SHA-256 digests.
Only stdlib is used (hashlib, json, pathlib).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 hex digest of a file's contents.

    Reads the file in 64 KiB chunks to keep memory usage constant regardless
    of file size.

    Args:
        path: Path to the file. Accepts both :class:`str` and :class:`pathlib.Path`.

    Returns:
        Lowercase hexadecimal SHA-256 digest string (64 characters).

    Raises:
        FileNotFoundError: If *path* does not exist.
        IsADirectoryError: If *path* is a directory.
    """
    digest = hashlib.sha256()
    chunk_size = 65536  # 64 KiB
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def sha256_str(s: str) -> str:
    """Return the SHA-256 hex digest of a UTF-8 encoded string.

    Args:
        s: Input string.

    Returns:
        Lowercase hexadecimal SHA-256 digest string (64 characters).
    """
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def hash_config(config_dict: dict) -> str:  # type: ignore[type-arg]
    """Return the SHA-256 hex digest of a config dictionary.

    The dictionary is serialised to JSON with sorted keys and no extra
    whitespace before hashing so that equivalent configs always produce the
    same hash regardless of key insertion order.

    Args:
        config_dict: Arbitrary JSON-serialisable dictionary.

    Returns:
        Lowercase hexadecimal SHA-256 digest string (64 characters).
    """
    canonical = json.dumps(config_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_str(canonical)
