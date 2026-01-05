"""Performance tracing utilities for distributed tracing.

This module provides:
- Decorators for tracing external API calls
- Context managers for custom spans
- Request ID propagation for frontend → backend correlation
- Custom tags and attributes for filtering

Uses Sentry's distributed tracing which is built on OpenTelemetry compatible
concepts and can propagate trace context to other services.

Usage:
    from omoi_os.observability.tracing import trace_external_api, trace_operation

    @trace_external_api("github")
    async def fetch_github_repo(repo: str):
        ...

    @trace_operation("db", "custom_query")
    async def complex_query():
        ...

    # Context manager style
    with traced_span("http.client", "stripe_api"):
        stripe.charges.create(...)
"""

from __future__ import annotations

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional, TypeVar

from omoi_os.logging import get_logger

logger = get_logger(__name__)

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


def _get_request_id() -> Optional[str]:
    """Get the current request ID from context.

    Returns:
        Request ID if available, None otherwise
    """
    from omoi_os.logging import get_request_id
    return get_request_id()


@contextmanager
def traced_span(
    op: str,
    description: str,
    tags: Optional[Dict[str, str]] = None,
    data: Optional[Dict[str, Any]] = None,
):
    """Context manager for creating a traced span.

    This wraps Sentry's start_span for manual instrumentation.

    Args:
        op: Operation type (e.g., "http.client", "db", "serialize")
        description: Human-readable description
        tags: Key-value tags for filtering
        data: Additional data to attach to the span

    Yields:
        The created span object

    Example:
        with traced_span("http.client", "stripe_create_customer") as span:
            span.set_data("customer_email", email)
            result = stripe.customers.create(email=email)
    """
    try:
        import sentry_sdk
    except ImportError:
        # Sentry not available - just yield None
        yield None
        return

    with sentry_sdk.start_span(op=op, description=description) as span:
        # Set tags if provided
        if tags:
            for key, value in tags.items():
                span.set_tag(key, value)

        # Set data if provided
        if data:
            for key, value in data.items():
                span.set_data(key, value)

        # Add request ID for correlation
        request_id = _get_request_id()
        if request_id:
            span.set_tag("request_id", request_id)

        yield span


def trace_external_api(service_name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator to trace external API calls.

    Creates a span around the decorated function with the service name.

    Args:
        service_name: Name of the external service (e.g., "github", "stripe", "openai")
        tags: Additional tags to add to the span

    Returns:
        Decorated function

    Example:
        @trace_external_api("github")
        async def fetch_repo_info(repo: str) -> dict:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://api.github.com/repos/{repo}")
                return response.json()
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                import sentry_sdk

                with sentry_sdk.start_span(
                    op="http.client",
                    description=f"{service_name}: {func.__name__}",
                ) as span:
                    span.set_tag("service", service_name)
                    span.set_tag("function", func.__name__)

                    if tags:
                        for key, value in tags.items():
                            span.set_tag(key, value)

                    request_id = _get_request_id()
                    if request_id:
                        span.set_tag("request_id", request_id)

                    start_time = time.perf_counter()
                    try:
                        result = await func(*args, **kwargs)
                        span.set_data("success", True)
                        return result
                    except Exception as e:
                        span.set_data("success", False)
                        span.set_data("error_type", type(e).__name__)
                        span.set_data("error_message", str(e)[:500])  # Truncate
                        raise
                    finally:
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        span.set_data("duration_ms", duration_ms)

            except ImportError:
                # Sentry not available
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                import sentry_sdk

                with sentry_sdk.start_span(
                    op="http.client",
                    description=f"{service_name}: {func.__name__}",
                ) as span:
                    span.set_tag("service", service_name)
                    span.set_tag("function", func.__name__)

                    if tags:
                        for key, value in tags.items():
                            span.set_tag(key, value)

                    request_id = _get_request_id()
                    if request_id:
                        span.set_tag("request_id", request_id)

                    start_time = time.perf_counter()
                    try:
                        result = func(*args, **kwargs)
                        span.set_data("success", True)
                        return result
                    except Exception as e:
                        span.set_data("success", False)
                        span.set_data("error_type", type(e).__name__)
                        span.set_data("error_message", str(e)[:500])
                        raise
                    finally:
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        span.set_data("duration_ms", duration_ms)

            except ImportError:
                return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def trace_operation(op: str, description: Optional[str] = None, tags: Optional[Dict[str, str]] = None):
    """Decorator to trace any operation with a custom span.

    Similar to trace_external_api but for general operations like
    database queries, serialization, or business logic.

    Args:
        op: Operation type (e.g., "db", "serialize", "validate")
        description: Human-readable description (defaults to function name)
        tags: Additional tags to add to the span

    Returns:
        Decorated function

    Example:
        @trace_operation("db", "complex_aggregation")
        async def get_monthly_stats(org_id: str) -> dict:
            ...

        @trace_operation("serialize")
        def serialize_response(data: dict) -> bytes:
            ...
    """
    def decorator(func: F) -> F:
        span_description = description or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                import sentry_sdk

                with sentry_sdk.start_span(op=op, description=span_description) as span:
                    span.set_tag("function", func.__name__)

                    if tags:
                        for key, value in tags.items():
                            span.set_tag(key, value)

                    request_id = _get_request_id()
                    if request_id:
                        span.set_tag("request_id", request_id)

                    start_time = time.perf_counter()
                    try:
                        result = await func(*args, **kwargs)
                        span.set_data("success", True)
                        return result
                    except Exception as e:
                        span.set_data("success", False)
                        span.set_data("error_type", type(e).__name__)
                        raise
                    finally:
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        span.set_data("duration_ms", duration_ms)

            except ImportError:
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                import sentry_sdk

                with sentry_sdk.start_span(op=op, description=span_description) as span:
                    span.set_tag("function", func.__name__)

                    if tags:
                        for key, value in tags.items():
                            span.set_tag(key, value)

                    request_id = _get_request_id()
                    if request_id:
                        span.set_tag("request_id", request_id)

                    start_time = time.perf_counter()
                    try:
                        result = func(*args, **kwargs)
                        span.set_data("success", True)
                        return result
                    except Exception as e:
                        span.set_data("success", False)
                        span.set_data("error_type", type(e).__name__)
                        raise
                    finally:
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        span.set_data("duration_ms", duration_ms)

            except ImportError:
                return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def trace_db_operation(description: Optional[str] = None):
    """Specialized decorator for database operations.

    Convenience wrapper around trace_operation for database calls.

    Args:
        description: Operation description (defaults to function name)

    Example:
        @trace_db_operation("get_user_by_email")
        async def get_user_by_email(email: str) -> Optional[User]:
            ...
    """
    return trace_operation(op="db.query", description=description, tags={"category": "database"})


def set_transaction_name(name: str) -> None:
    """Set the transaction name for the current trace.

    Useful for custom naming when the automatic naming isn't descriptive enough.

    Args:
        name: Transaction name
    """
    try:
        import sentry_sdk
        scope = sentry_sdk.get_current_scope()
        if scope.transaction:
            scope.transaction.name = name
    except Exception:
        pass


def set_span_tag(key: str, value: str) -> None:
    """Set a tag on the current span.

    Tags are searchable and can be used for filtering in Sentry.

    Args:
        key: Tag name
        value: Tag value
    """
    try:
        import sentry_sdk
        span = sentry_sdk.get_current_span()
        if span:
            span.set_tag(key, value)
    except Exception:
        pass


def set_span_data(key: str, value: Any) -> None:
    """Set data on the current span.

    Data is attached to the span for debugging but not searchable.

    Args:
        key: Data key
        value: Data value
    """
    try:
        import sentry_sdk
        span = sentry_sdk.get_current_span()
        if span:
            span.set_data(key, value)
    except Exception:
        pass


def add_breadcrumb(
    message: str,
    category: str = "custom",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """Add a breadcrumb to the current trace.

    Breadcrumbs are a trail of events leading up to an error.

    Args:
        message: Breadcrumb message
        category: Category for grouping
        level: Severity level (debug, info, warning, error)
        data: Additional data
    """
    try:
        import sentry_sdk
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {},
        )
    except Exception:
        pass


def get_trace_headers() -> Dict[str, str]:
    """Get trace context headers for propagating to downstream services.

    Use this when making HTTP calls to other instrumented services to
    enable distributed tracing.

    Returns:
        Dictionary of headers to include in outgoing requests

    Example:
        headers = get_trace_headers()
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
    """
    try:
        import sentry_sdk
        from sentry_sdk.integrations.httpx import _get_headers

        # Get the propagation headers from the current scope
        scope = sentry_sdk.get_current_scope()
        if scope.span:
            return {
                "sentry-trace": scope.span.to_traceparent(),
                "baggage": scope.span.to_baggage(),
            }
    except Exception:
        pass

    return {}


def extract_trace_context(headers: Dict[str, str]) -> None:
    """Extract trace context from incoming request headers.

    Called automatically by FastAPI integration, but useful for
    custom scenarios like background jobs or message queues.

    Args:
        headers: Incoming request headers
    """
    try:
        import sentry_sdk
        from sentry_sdk.tracing import Transaction

        sentry_trace = headers.get("sentry-trace")
        baggage = headers.get("baggage")

        if sentry_trace:
            # Continue the existing trace
            transaction = Transaction.continue_from_headers(
                {"sentry-trace": sentry_trace, "baggage": baggage}
            )
            sentry_sdk.get_current_scope().set_transaction(transaction)
    except Exception:
        pass


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
