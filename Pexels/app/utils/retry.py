from __future__ import annotations

import time
from collections.abc import Callable
from functools import wraps
from typing import TypeVar


T = TypeVar("T")


def retry(
    attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry only the caller-selected transient exception classes."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_error: Exception | None = None
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_error = exc
                    if attempt == attempts - 1:
                        break
                    time.sleep(current_delay)
                    current_delay *= backoff
            if last_error:
                raise last_error
            raise RuntimeError("Retry failed without an exception.")

        return wrapper

    return decorator
