"""Retry utilities for Continuous Evaluation resilience.

Wraps azure-ai-evaluation calls with exponential backoff and
graceful degradation for rate limits (429) and transient errors.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# Retryable exception patterns (substring match on str(exception))
_RETRYABLE_PATTERNS = [
    "429",
    "rate limit",
    "too many requests",
    "throttl",
    "timeout",
    "timed out",
    "connection",
    "temporary",
    "server error",
    "502",
    "503",
    "504",
]


def _is_retryable(exc: Exception) -> bool:
    """Check if an exception is retryable based on known patterns.

    Args:
        exc: The exception to check.

    Returns:
        True if the error is transient and worth retrying.
    """
    exc_str = str(exc).lower()
    return any(pattern in exc_str for pattern in _RETRYABLE_PATTERNS)


def retry_with_backoff[T](
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 10.0,
    max_delay: float = 120.0,
    backoff_factor: float = 2.0,
    **kwargs: Any,
) -> T:
    """Execute a function with exponential backoff on retryable errors.

    Args:
        func: The function to call.
        *args: Positional arguments for func.
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds between retries.
        max_delay: Maximum delay cap in seconds.
        backoff_factor: Multiplier for delay after each retry.
        **kwargs: Keyword arguments for func.

    Returns:
        The return value of func.

    Raises:
        Exception: The last exception if all retries are exhausted,
            or immediately if the error is not retryable.
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exception = exc

            if not _is_retryable(exc):
                logger.error("Non-retryable error (attempt %d/%d): %s", attempt + 1, max_retries + 1, exc)
                raise

            if attempt == max_retries:
                logger.error("All %d attempts exhausted. Last error: %s", max_retries + 1, exc)
                raise

            delay = min(base_delay * (backoff_factor**attempt), max_delay)
            logger.warning(
                "Retryable error (attempt %d/%d): %s — retrying in %.0fs",
                attempt + 1,
                max_retries + 1,
                exc,
                delay,
            )
            time.sleep(delay)

    # Should not reach here, but satisfy type checker
    if last_exception:
        raise last_exception
    msg = "retry_with_backoff: unexpected state"
    raise RuntimeError(msg)
