from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator


MAX_ANALYZE_WORKERS = 2

_analyze_slots = threading.BoundedSemaphore(MAX_ANALYZE_WORKERS)


@contextmanager
def analysis_slot() -> Iterator[bool]:
    acquired = _analyze_slots.acquire(blocking=False)
    try:
        yield acquired
    finally:
        if acquired:
            _analyze_slots.release()
