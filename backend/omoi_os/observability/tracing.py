"""Tracing wrapper layer (Sentry-free shim).

Originally this module wrapped Sentry's APM tracing API. As part of the
Sentry → PostHog migration, the underlying Sentry calls were removed and
the wrappers became thin no-ops that preserve the existing public surface
so any future caller continues to compile.

Distributed tracing in this codebase is provided by Pydantic Logfire /
OpenTelemetry — see :mod:`omoi_os.observability` (``LogfireTracer``,
``instrument_fastapi``, ``instrument_sqlalchemy``, ``instrument_httpx``,
``instrument_redis``). Those auto-instrumentations already capture spans
for HTTP requests, DB queries, outbound calls, and cache operations, so
manual ``traced_span(...)`` decoration would duplicate work.

PostHog has no native backend Python tracing API. The few breadcrumb-style
calls route to PostHog as ``breadcrumb.<category>`` events (Phase 6
strategy A) so the *intent* of breadcrumbs is preserved if anything
re-wires those calls in the future.

Usage (kept for shape compatibility — these are no-ops for span data):

    from omoi_os.observability.tracing import trace_external_api, traced_span

    @trace_external_api("stripe")
    async def charge(...): ...

    with traced_span("db", "complex_query"):
        ...
"""

from __future__ import annotations

import functools
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, Optional, TypeVar

from omoi_os.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def _get_request_id() -> Optional[str]:
    """Get the current request ID from context, if available."""
    try:
        from omoi_os.logging import get_request_id

        return get_request_id()
    except Exception:  # noqa: BLE001
        return None


@contextmanager
def traced_span(
    op: str,
    description: str,
    tags: Optional[Dict[str, str]] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Iterator[None]:
    """No-op span context manager.

    Span tracking is now handled by Logfire's auto-instrumentation. Any
    tags/data passed here are dropped silently so callers don't crash.
    """
    yield None


def trace_external_api(provider: str) -> Callable[[F], F]:
    """No-op decorator for external API calls (Logfire instruments httpx)."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        import asyncio

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper  # type: ignore[return-value]

    return decorator


def trace_operation(category: str, name: str) -> Callable[[F], F]:
    """No-op decorator for application-level operations."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        import asyncio

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper  # type: ignore[return-value]

    return decorator


def trace_db_operation(query_type: str, table: str) -> Callable[[F], F]:
    """No-op decorator for DB operations (Logfire instruments SQLAlchemy)."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        import asyncio

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper  # type: ignore[return-value]

    return decorator


def set_transaction_name(name: str) -> None:
    """No-op (transactions are owned by Logfire)."""
    return None


def set_span_tag(key: str, value: Any) -> None:
    """No-op (Logfire auto-spans don't accept post-hoc tags from here)."""
    return None


def set_span_data(key: str, value: Any) -> None:
    """No-op (Logfire auto-spans don't accept post-hoc data from here)."""
    return None


def add_breadcrumb(
    category: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    level: str = "info",
) -> None:
    """Convert Sentry-style breadcrumb to a PostHog ``breadcrumb.<category>`` event.

    PostHog has no native breadcrumb concept. Per the migration plan
    (Phase 6, strategy A) we ship the breadcrumb as a regular event so
    its intent is preserved. Falls through to a no-op if PostHog
    observability isn't initialized.
    """
    try:
        from omoi_os.observability import posthog as _ph_obs
    except Exception:  # noqa: BLE001
        return

    if getattr(_ph_obs, "_posthog_module", None) is None:
        return

    try:
        properties: Dict[str, Any] = {
            "message": message,
            "level": level,
        }
        if data:
            properties.update(data)
        _ph_obs._posthog_module.capture(f"breadcrumb.{category}", properties=properties)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"breadcrumb capture failed: {e}")


def get_trace_headers() -> Dict[str, str]:
    """Return W3C ``traceparent``/``tracestate`` headers if available.

    Logfire/OpenTelemetry handles distributed trace propagation natively
    on instrumented httpx clients. This helper used to return Sentry's
    ``sentry-trace`` + ``baggage`` headers for the Sentry distributed
    tracing protocol; we don't need that anymore. Returns an empty dict
    so any caller still calling this gets a safe fallback.
    """
    return {}


def extract_trace_context(headers: Dict[str, str]) -> None:
    """No-op extraction (Logfire's OTel handles upstream-context propagation)."""
    return None


__all__ = [
    "traced_span",
    "trace_external_api",
    "trace_operation",
    "trace_db_operation",
    "set_transaction_name",
    "set_span_tag",
    "set_span_data",
    "add_breadcrumb",
    "get_trace_headers",
    "extract_trace_context",
]
