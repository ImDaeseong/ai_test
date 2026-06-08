"""Structured JSON Lines logging utilities.

All log output uses JSON Lines format:
    {"ts": "<ISO8601>", "level": "<LEVEL>", "logger": "<name>", "msg": "<text>", ...extra}

Only stdlib is used (logging, json, datetime, sys).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class _JsonLinesFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        base: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Include any extra fields attached to the record, skipping internal ones.
        _stdlib_keys = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in _stdlib_keys and not key.startswith("_"):
                base[key] = value

        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)

        return json.dumps(base, ensure_ascii=False, default=str)


def get_logger(name: str) -> logging.Logger:
    """Return a logger that writes JSON Lines to stdout.

    If the logger already has handlers attached (e.g. called twice with the
    same name) the existing instance is returned unchanged so that log records
    are not duplicated.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` configured with a :class:`_JsonLinesFormatter`
        StreamHandler pointing at ``sys.stdout``.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonLinesFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    # Do not propagate to the root logger to avoid duplicate output.
    logger.propagate = False
    return logger


def log_issue(
    logger: logging.Logger,
    issue_id: str,
    severity: str,
    code: str,
    message: str,
    evidence: dict[str, Any] | None = None,
) -> None:
    """Log a structured review issue at the appropriate log level.

    Severity mapping:
        - ``BLOCKER`` / ``HOLD``  -> ERROR
        - ``REVIEW`` / ``WARNING`` -> WARNING
        - ``INFO`` (and anything else) -> INFO

    Args:
        logger: Logger instance obtained from :func:`get_logger`.
        issue_id: Unique identifier for this issue (e.g. ``"SUBTITLE_LONG_CUE_001"``).
        severity: One of ``INFO``, ``WARNING``, ``REVIEW``, ``HOLD``, ``BLOCKER``.
        code: Short machine-readable code (e.g. ``"LONG_LYRIC_CUE"``).
        message: Human-readable description of the issue.
        evidence: Optional dict with supporting data (cue IDs, durations, etc.).
    """
    extra: dict[str, Any] = {
        "issue_id": issue_id,
        "severity": severity,
        "code": code,
    }
    if evidence is not None:
        extra["evidence"] = evidence

    level_upper = severity.upper()
    if level_upper in ("BLOCKER", "HOLD"):
        logger.error(message, extra=extra)
    elif level_upper in ("REVIEW", "WARNING"):
        logger.warning(message, extra=extra)
    else:
        logger.info(message, extra=extra)
