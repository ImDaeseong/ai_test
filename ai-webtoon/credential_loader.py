"""Load the shared OpenAI credential without exposing its value."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_KEYS_FILE = Path(__file__).resolve().parents[2] / "ai_agent" / "keyinfo" / "keys.env"


def load_openai_api_key(path: Path = DEFAULT_KEYS_FILE) -> bool:
    """Set OPENAI_API_KEY from the shared key file and return only its presence."""
    if os.getenv("OPENAI_API_KEY"):
        return True
    if not path.is_file():
        return False
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == "OPENAI_API_KEY":
            value = value.strip().strip('"').strip("'")
            if value:
                os.environ["OPENAI_API_KEY"] = value
                return True
    return False
