"""Tracing decorators backed by OpenTelemetry.

These decorators create real OTel spans now that
:mod:`omoi_os.observability.betterstack` wires a TracerProvider with both
the OTLP exporter (BetterStack Telemetry) and the SentrySpanProcessor
(BetterStack Errors). When neither is configured, OTel falls back to a
no-op tracer so the decorators stay zero-cost.

Usage:

    from omoi_os.observability.tracing import trace_external_api, traced_span

    @trace_external_api("stripe")
    async def charge(...): ...

    with traced_span("db", "complex_query", tags={"table": "users"}):
        ...
"""

from __future__ import annotations

import asyncio
import functools
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, Optional, TypeVar

from omoi_os.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def _get_request_id() -> Optional[str]:
    try:
        from omoi_os.logging import get_request_id

        return get_request_id()
    except Exception:  # noqa: BLE001
        return None


def _tracer():
    """Lazy-import OTel API. Returns None if OTel isn't installed."""
    try:
        from opentelemetry import trace

        return trace.get_tracer("omoi_os")
    except Exception:  # noqa: BLE001
        return None


def _apply_attributes(
    span,
    *,
    op: Optional[str],
    description: Optional[str],
    tags: Optional[Dict[str, str]],
    data: Optional[Dict[str, Any]],
) -> None:
    if span is None:
        return
    if op is not None:
        span.set_attribute("op", op)
    if description is not None:
        span.set_attribute("description", description)
    rid = _get_request_id()
    if rid:
        span.set_attribute("request_id", rid)
    for key, value in (tags or {}).items():
        if isinstance(value, (str, bool, int, float)):
            span.set_attribute(f"tag.{key}", value)
    for key, value in (data or {}).items():
        if isinstance(value, (str, bool, int, float)):
            span.set_attribute(f"data.{key}", value)


@contextmanager
def traced_span(
    op: str,
    description: str,
    tags: Optional[Dict[str, str]] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Iterator[None]:
    """Open an OTel span scoped to the ``with`` block."""
    tracer = _tracer()
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_span(f"{op}.{description}") as span:
        _apply_attributes(span, op=op, description=description, tags=tags, data=data)
        yield span


def _decorate(span_name_fn: Callable[[], str]) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        tracer = _tracer()

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                if tracer is None:
                    return await func(*args, **kwargs)
                with tracer.start_as_current_span(span_name_fn()):
                    return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if tracer is None:
                return func(*args, **kwargs)
            with tracer.start_as_current_span(span_name_fn()):
                return func(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    return decorator


def trace_external_api(provider: str) -> Callable[[F], F]:
    """Wrap an outbound API call in an OTel span.

    Note: ``opentelemetry-instrumentation-httpx`` already creates spans
    around HTTPX requests. This decorator is for cases where you want a
    parent span over a multi-step external interaction (e.g. Stripe
    customer + subscription creation).
    """
    return _decorate(lambda: f"external_api.{provider}")


def trace_operation(category: str, name: str) -> Callable[[F], F]:
    return _decorate(lambda: f"{category}.{name}")


def trace_db_operation(query_type: str, table: str) -> Callable[[F], F]:
    """Wrap a DB operation in a span. SQLAlchemy auto-instrumentation already
    creates spans for raw queries; use this when you want a logical-operation
    name (e.g. ``find_active_users``)."""
    return _decorate(lambda: f"db.{query_type}.{table}")


def set_transaction_name(name: str) -> None:
    """Update the current span's name. No-op outside an active span."""
    tracer = _tracer()
    if tracer is None:
        return
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.is_recording():
            span.update_name(name)
    except Exception:  # noqa: BLE001
        return


def set_span_tag(key: str, value: Any) -> None:
    tracer = _tracer()
    if tracer is None or not isinstance(value, (str, int, float, bool)):
        return
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.is_recording():
            span.set_attribute(key, value)
    except Exception:  # noqa: BLE001
        return


def set_span_data(key: str, value: Any) -> None:
    set_span_tag(f"data.{key}", value)


def add_breadcrumb(
    category: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    level: str = "info",
) -> None:
    """Add an OTel span event (the OTel equivalent of a Sentry breadcrumb).

    Falls back to a PostHog ``breadcrumb.<category>`` event if no active
    OTel span is present, preserving the legacy behaviour.
    """
    tracer = _tracer()
    span = None
    if tracer is not None:
        try:
            from opentelemetry import trace

            span = trace.get_current_span()
            if span and span.is_recording():
                attrs: Dict[str, Any] = {"message": message, "level": level}
                if data:
                    for k, v in data.items():
                        if isinstance(v, (str, int, float, bool)):
                            attrs[k] = v
                span.add_event(f"breadcrumb.{category}", attributes=attrs)
                return
        except Exception:  # noqa: BLE001
            pass

    # Fallback: legacy PostHog breadcrumb event
    try:
        from omoi_os.observability import posthog as _ph_obs
    except Exception:  # noqa: BLE001
        return

    if getattr(_ph_obs, "_posthog_module", None) is None:
        return

    try:
        properties: Dict[str, Any] = {"message": message, "level": level}
        if data:
            properties.update(data)
        _ph_obs._posthog_module.capture(f"breadcrumb.{category}", properties=properties)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"breadcrumb capture failed: {e}")


def get_trace_headers() -> Dict[str, str]:
    """Return W3C ``traceparent``/``tracestate`` headers for the active span."""
    try:
        from opentelemetry import propagate

        carrier: Dict[str, str] = {}
        propagate.inject(carrier)
        return carrier
    except Exception:  # noqa: BLE001
        return {}


def extract_trace_context(headers: Dict[str, str]) -> None:
    """Extract upstream W3C trace context. Result is auto-attached as the
    parent of the next span created on this thread/task."""
    try:
        from opentelemetry import context, propagate

        ctx = propagate.extract(headers)
        context.attach(ctx)
    except Exception:  # noqa: BLE001
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
