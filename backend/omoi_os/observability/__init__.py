"""Observability — single facade for the four-sink pipeline.

Public entrypoint: :mod:`omoi_os.observability.telemetry`.

This package owns the Sentry SDK + OpenTelemetry + BetterStack + PostHog
integration. Callers should import names from this package directly:

    from omoi_os.observability import (
        capture_exception, metric_increment, track_event, identify_user,
    )

Set ``OBS_LEGACY_LOGFIRE=1`` to fall back to the older Logfire wrapper —
useful as an emergency rollback while the new stack is being validated.

Reference: docs/architecture/observability_unified.md
"""

from __future__ import annotations

import os
import warnings
from contextlib import contextmanager
from typing import Optional

from omoi_os.config import get_app_settings

# Re-export the new facade.
from omoi_os.observability.telemetry import (  # noqa: F401
    PII_PATTERNS,
    SENSITIVE_KEYS,
    capture_exception,
    capture_message,
    deploy_marker,
    heartbeat,
    identify_user,
    init_sentry,
    init_telemetry,
    metric_distribution,
    metric_gauge,
    metric_histogram,
    metric_increment,
    metric_set,
    push_scope,
    set_context,
    set_tag,
    set_user,
    shutdown,
    track_agent_health,
    track_conversion,
    track_event,
    track_llm_usage,
    track_queue_depth,
    track_task_completed,
    track_task_failed,
    track_task_retried,
)

from omoi_os.observability.tracing import (  # noqa: F401
    add_breadcrumb,
    extract_trace_context,
    get_trace_headers,
    set_span_data,
    set_span_tag,
    set_transaction_name,
    trace_db_operation,
    trace_external_api,
    trace_operation,
    traced_span,
)


# ---------------------------------------------------------------------------
# Legacy Logfire path — gated behind OBS_LEGACY_LOGFIRE=1 for emergency rollback
# ---------------------------------------------------------------------------

_LEGACY_LOGFIRE = os.environ.get("OBS_LEGACY_LOGFIRE", "").lower() in (
    "1",
    "true",
    "yes",
)

try:
    import logfire as _logfire  # noqa: F401

    LOGFIRE_AVAILABLE = True
except ImportError:
    LOGFIRE_AVAILABLE = False


class LogfireTracer:
    """Legacy Logfire wrapper retained for backward compat (Phase D rollback)."""

    def __init__(self, service_name: str = "omoi-os", enabled: bool = True):
        self.service_name = service_name
        self.enabled = enabled and LOGFIRE_AVAILABLE and _LEGACY_LOGFIRE
        self._configured = False
        if self.enabled and not self._configured:
            try:
                import logfire

                logfire.configure(service_name=service_name)
                self._configured = True
            except Exception as e:  # noqa: BLE001
                warnings.warn(
                    f"Logfire configuration failed: {e}", RuntimeWarning, stacklevel=2
                )
                self.enabled = False

    @contextmanager
    def span(self, operation_name: str, **attributes):
        if not self.enabled:
            yield None
            return
        import logfire

        with logfire.span(operation_name, **attributes) as span:
            yield span

    def log_info(self, message: str, **extra):
        if self.enabled:
            import logfire

            logfire.info(message, **extra)

    def log_error(self, message: str, **extra):
        if self.enabled:
            import logfire

            logfire.error(message, **extra)

    def log_warning(self, message: str, **extra):
        if self.enabled:
            import logfire

            logfire.warn(message, **extra)


_tracer: Optional[LogfireTracer] = None


def get_tracer(service_name: str = "omoi-os") -> LogfireTracer:
    """Return the legacy Logfire tracer when ``OBS_LEGACY_LOGFIRE=1``.

    New code should use the OTel TracerProvider via
    ``opentelemetry.trace.get_tracer(...)`` instead.
    """
    global _tracer
    if _tracer is None:
        observability_settings = get_app_settings().observability
        if observability_settings.logfire_token:
            os.environ.setdefault("LOGFIRE_TOKEN", observability_settings.logfire_token)
        enabled = _LEGACY_LOGFIRE and (
            observability_settings.enable_tracing
            or bool(observability_settings.logfire_token)
        )
        _tracer = LogfireTracer(service_name=service_name, enabled=enabled)
    return _tracer


def instrument_fastapi(app):
    """Instrument FastAPI with OTel + (optionally) Logfire."""
    # OTel auto-instrumentation always works once a TracerProvider exists.
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception as e:  # noqa: BLE001
        warnings.warn(f"OTel FastAPI instrumentation failed: {e}", RuntimeWarning)
    if _LEGACY_LOGFIRE and LOGFIRE_AVAILABLE:
        import logfire

        logfire.instrument_fastapi(app)


def instrument_sqlalchemy(engine):
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument(engine=engine)
    except Exception as e:  # noqa: BLE001
        warnings.warn(f"OTel SQLAlchemy instrumentation failed: {e}", RuntimeWarning)
    if _LEGACY_LOGFIRE and LOGFIRE_AVAILABLE:
        import logfire

        logfire.instrument_sqlalchemy(engine=engine)


def instrument_httpx():
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except Exception as e:  # noqa: BLE001
        warnings.warn(f"OTel HTTPX instrumentation failed: {e}", RuntimeWarning)
    if _LEGACY_LOGFIRE and LOGFIRE_AVAILABLE:
        import logfire

        logfire.instrument_httpx()


def instrument_redis():
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()
    except Exception as e:  # noqa: BLE001
        warnings.warn(f"OTel Redis instrumentation failed: {e}", RuntimeWarning)
    if _LEGACY_LOGFIRE and LOGFIRE_AVAILABLE:
        import logfire

        logfire.instrument_redis()


__all__ = [
    # Lifecycle
    "init_telemetry",
    "init_sentry",
    "shutdown",
    # Errors
    "capture_exception",
    "capture_message",
    # Context
    "set_user",
    "set_tag",
    "set_context",
    "push_scope",
    # Metrics
    "metric_increment",
    "metric_gauge",
    "metric_histogram",
    "metric_distribution",
    "metric_set",
    # Events
    "track_event",
    "identify_user",
    "track_conversion",
    # Pre-built operational metrics
    "track_task_completed",
    "track_task_failed",
    "track_task_retried",
    "track_queue_depth",
    "track_agent_health",
    "track_llm_usage",
    # Heartbeat / deploys
    "heartbeat",
    "deploy_marker",
    # Tracing
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
    # Instrumentation
    "instrument_fastapi",
    "instrument_sqlalchemy",
    "instrument_httpx",
    "instrument_redis",
    # Legacy (gated)
    "LogfireTracer",
    "get_tracer",
    # PII
    "PII_PATTERNS",
    "SENSITIVE_KEYS",
]
