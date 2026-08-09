import time
from collections.abc import Callable
from typing import TypeVar

from stock_ai.exceptions import MissingDependencyError


T = TypeVar("T")


def retry_call(
    operation: Callable[[], T],
    attempts: int = 3,
    initial_delay_seconds: float = 0.8,
) -> T:
    """Retry transient provider errors with a small exponential backoff."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return operation()
        except MissingDependencyError:
            raise
        except Exception as error:
            last_error = error
            if attempt == attempts - 1:
                break
            time.sleep(initial_delay_seconds * (2**attempt))
    assert last_error is not None
    raise last_error
