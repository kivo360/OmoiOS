"""Observability infrastructure using Pydantic Logfire and OpenTelemetry.

This module provides:
- Distributed tracing via Logfire (OpenTelemetry compatible)
- Structured logging with correlation IDs
- Performance profiling
- LLM call tracking via Laminar integration
"""

import os
from contextlib import contextmanager
from typing import Optional

from omoi_os.config import get_app_settings

# Lazy import to avoid hard dependency during tests
try:
    import logfire

    LOGFIRE_AVAILABLE = True
except ImportError:
    LOGFIRE_AVAILABLE = False


class LogfireTracer:
    """Wrapper around Pydantic Logfire for distributed tracing."""

    def __init__(self, service_name: str = "omoi-os", enabled: bool = True):
        """
        Initialize Logfire tracer.

        Args:
            service_name: Service identifier for traces
            enabled: Enable/disable tracing (default: True, respects LOGFIRE_TOKEN env)
        """
        self.service_name = service_name
        self.enabled = enabled and LOGFIRE_AVAILABLE
        self._configured = False

        if self.enabled and not self._configured:
            try:
                # Configure Logfire with service name
                logfire.configure(
                    service_name=service_name,
                    # Logfire auto-detects LOGFIRE_TOKEN from environment
                )
                self._configured = True
            except Exception as e:
                print(f"Warning: Logfire configuration failed: {e}")
                self.enabled = False

    @contextmanager
    def span(self, operation_name: str, **attributes):
        """
        Create a tracing span.

        Args:
            operation_name: Name of the operation being traced
            **attributes: Additional span attributes

        Usage:
            with tracer.span("database.query", table="users"):
                # Database operation
                pass
        """
        if not self.enabled:
            yield None
            return

        with logfire.span(operation_name, **attributes) as span:
            yield span

    def log_info(self, message: str, **extra):
        """Log info level message with trace context."""
        if self.enabled:
            logfire.info(message, **extra)

    def log_error(self, message: str, **extra):
        """Log error level message with trace context."""
        if self.enabled:
            logfire.error(message, **extra)

    def log_warning(self, message: str, **extra):
        """Log warning level message with trace context."""
        if self.enabled:
            logfire.warn(message, **extra)


# Global tracer instance
_tracer: Optional[LogfireTracer] = None


def get_tracer(service_name: str = "omoi-os") -> LogfireTracer:
    """
    Get global tracer instance.

    Args:
        service_name: Service name for tracing

    Returns:
        LogfireTracer instance
    """
    global _tracer
    if _tracer is None:
        observability_settings = get_app_settings().observability
        if observability_settings.logfire_token:
            os.environ.setdefault("LOGFIRE_TOKEN", observability_settings.logfire_token)
        enabled = observability_settings.enable_tracing or bool(
            observability_settings.logfire_token
        )
        _tracer = LogfireTracer(service_name=service_name, enabled=enabled)
    return _tracer


def instrument_fastapi(app):
    """
    Instrument FastAPI app with Logfire auto-tracing.

    Args:
        app: FastAPI application instance

    Usage:
        from fastapi import FastAPI
        from omoi_os.observability import instrument_fastapi

        app = FastAPI()
        instrument_fastapi(app)
    """
    if LOGFIRE_AVAILABLE:
        logfire.instrument_fastapi(app)


def instrument_sqlalchemy(engine):
    """
    Instrument SQLAlchemy engine with Logfire.

    Args:
        engine: SQLAlchemy engine instance
    """
    if LOGFIRE_AVAILABLE:
        logfire.instrument_sqlalchemy(engine=engine)


def instrument_httpx():
    """Instrument HTTPX client for outbound HTTP tracing."""
    if LOGFIRE_AVAILABLE:
        logfire.instrument_httpx()


def instrument_redis():
    """Instrument Redis client for cache operation tracing."""
    if LOGFIRE_AVAILABLE:
        logfire.instrument_redis()


__all__ = [
    "LogfireTracer",
    "get_tracer",
    "instrument_fastapi",
    "instrument_httpx",
    "instrument_redis",
    "instrument_sqlalchemy",
]
