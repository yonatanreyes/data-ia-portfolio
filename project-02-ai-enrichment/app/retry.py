"""Generic retry helper with exponential backoff.

This module is intentionally independent of any specific AI SDK: it
only knows how to retry a zero-argument function a limited number of
times when a caller-specified set of exception types is raised. Each
provider passes in its own SDK's transient exception types.
"""

import logging
import time
from collections.abc import Callable
from typing import TypeVar


logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(
    callback: Callable[[], T],
    max_retries: int,
    retry_on: tuple[type[Exception], ...],
) -> T:
    """Execute a callback, retrying on specific transient exceptions.

    Args:
        callback: Zero-argument function to execute (e.g. a lambda
            wrapping an API call).
        max_retries: Maximum number of retries after the first attempt.
        retry_on: Exception types considered transient/retryable
            (e.g. rate limits, timeouts, connection drops).

    Returns:
        Whatever `callback` returns on success.

    Raises:
        Exception: The original exception, once retries are exhausted,
            or immediately if it is not one of `retry_on`.
    """
    for attempt in range(max_retries + 1):

        try:
            return callback()

        except retry_on as error:

            if attempt >= max_retries:
                logger.error(
                    "Giving up after %d attempt(s): %s",
                    attempt + 1,
                    error,
                )
                raise

            wait_seconds = 2**attempt

            logger.warning(
                "Transient error (%s). Retrying in %ds (attempt %d/%d).",
                error,
                wait_seconds,
                attempt + 1,
                max_retries,
            )

            time.sleep(wait_seconds)

    raise RuntimeError("Retry loop exited unexpectedly.")