from pathlib import Path

import pytest

from scripts.validate_data import validate_env


def test_validate_env_allows_missing_keys_without_smoke(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "GEMINI_API_KEY=\nPEXELS_API_KEY=your_pexels_api_key_here\n",
        encoding="utf-8",
    )

    validate_env(require_api_keys=False)


def test_validate_env_requires_keys_for_smoke(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "GEMINI_API_KEY=\nPEXELS_API_KEY=your_pexels_api_key_here\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY, PEXELS_API_KEY"):
        validate_env(require_api_keys=True)
