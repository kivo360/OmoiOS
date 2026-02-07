"""MCP Retry Manager with exponential backoff and idempotency support."""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from omoi_os.utils.datetime import utc_now


class TransientError(Exception):
    """Transient error that should be retried."""

    pass


class PermanentError(Exception):
    """Permanent error that should not be retried."""

    pass


class RetryExhaustedError(Exception):
    """All retry attempts exhausted."""

    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception


class MCPRetryManager:
    """
    Manages retry logic with exponential backoff and jitter.

    REQ-MCP-CALL-002: Retry with Backoff
    REQ-MCP-CALL-003: Idempotency
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay_ms: int = 500,
        factor: float = 2.0,
        max_delay_ms: int = 30000,
        jitter: bool = True,
        idempotency_ttl: timedelta = timedelta(hours=1),
    ):
        """
        Initialize retry manager.

        Args:
            max_attempts: Maximum retry attempts
            base_delay_ms: Initial backoff delay in milliseconds
            factor: Exponential backoff factor
            max_delay_ms: Maximum backoff delay in milliseconds
            jitter: Whether to add jitter to backoff
            idempotency_ttl: TTL for idempotency cache entries
        """
        self.max_attempts = max_attempts
        self.base_delay_ms = base_delay_ms
        self.factor = factor
        self.max_delay_ms = max_delay_ms
        self.jitter = jitter
        self.idempotency_ttl = idempotency_ttl
        self.idempotency_keys: Dict[str, tuple[Any, datetime]] = (
            {}
        )  # key -> (result, timestamp)

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        idempotency_key: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Execute function with retry logic.

        Formula: delay = min(base * (factor ^ attempt) + jitter, max_delay)

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            idempotency_key: Optional idempotency key for caching
            **kwargs: Keyword arguments for func

        Returns:
            Function result

        Raises:
            RetryExhaustedError: If all retries exhausted
        """
        # Check idempotency cache
        if idempotency_key and idempotency_key in self.idempotency_keys:
            cached_result, cached_time = self.idempotency_keys[idempotency_key]
            if (utc_now() - cached_time) < self.idempotency_ttl:
                return cached_result
            else:
                # Cache expired
                del self.idempotency_keys[idempotency_key]

        last_exception = None
        attempt = 0

        while attempt < self.max_attempts:
            try:
                result = await func(*args, **kwargs)

                # Cache result for idempotency
                if idempotency_key:
                    self.idempotency_keys[idempotency_key] = (result, utc_now())

                return result

            except TransientError as e:
                last_exception = e
                attempt += 1

                if attempt < self.max_attempts:
                    delay_ms = self._calculate_backoff(attempt)
                    await asyncio.sleep(delay_ms / 1000.0)
                else:
                    break

            except PermanentError:
                # Don't retry permanent errors
                raise

        # All retries exhausted
        raise RetryExhaustedError(
            f"Failed after {self.max_attempts} attempts", last_exception=last_exception
        )

    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay with jitter.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in milliseconds
        """
        # Exponential: base * (factor ^ attempt)
        delay = self.base_delay_ms * (self.factor**attempt)

        # Cap at max delay
        delay = min(delay, self.max_delay_ms)

        # Add jitter (±20%)
        if self.jitter:
            jitter_amount = delay * 0.2
            delay = delay + random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)

    def clear_idempotency_cache(self, older_than: Optional[timedelta] = None) -> None:
        """
        Clear expired idempotency cache entries.

        Args:
            older_than: Optional TTL threshold (defaults to self.idempotency_ttl)
        """
        if older_than is None:
            older_than = self.idempotency_ttl

        cutoff = utc_now() - older_than
        expired_keys = [
            key
            for key, (_, timestamp) in self.idempotency_keys.items()
            if timestamp < cutoff
        ]
        for key in expired_keys:
            del self.idempotency_keys[key]
