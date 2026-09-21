"""Monthly call-count guard for paid webtoon image generation."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

DEFAULT_MONTHLY_CALL_LIMIT = 100
LOGS_DIR = Path(__file__).resolve().parent / "logs"


class BudgetExceededError(RuntimeError):
    """Signal that another paid generation would exceed the local limit."""


def _log_path(logs_dir: Path) -> Path:
    return logs_dir / f"{dt.datetime.now():%Y-%m}.jsonl"


def count_calls(logs_dir: Path = LOGS_DIR) -> int:
    """Count successful calls recorded for the current month."""
    path = _log_path(logs_dir)
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def check_limit(*, logs_dir: Path = LOGS_DIR, limit: int = DEFAULT_MONTHLY_CALL_LIMIT) -> None:
    """Reject a paid call when the current-month limit is reached."""
    used = count_calls(logs_dir)
    if used >= limit:
        raise BudgetExceededError(f"monthly image limit reached ({used}/{limit})")


def record_call(usage: dict[str, Any], *, logs_dir: Path = LOGS_DIR) -> None:
    """Record one successful call without prompts, responses, or credentials."""
    safe_usage = {
        key: value for key, value in usage.items()
        if key in {"input_tokens", "output_tokens", "total_tokens"}
        and isinstance(value, (int, float))
    }
    entry = {
        "timestamp": dt.datetime.now().isoformat(), "provider": "openai",
        "model": "gpt-image-2", "mode": "webtoon_panel", "usage": safe_usage,
    }
    logs_dir.mkdir(exist_ok=True)
    with _log_path(logs_dir).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
