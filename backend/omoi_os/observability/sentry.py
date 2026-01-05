"""Sentry integration for error tracking and performance monitoring.

This module provides:
- Exception tracking (sync and async)
- Performance monitoring with distributed tracing
- PII filtering to protect user data
- Environment-specific configuration

Usage:
    # At application startup (main.py)
    from omoi_os.observability.sentry import init_sentry
    init_sentry()

    # In any module - errors are automatically captured
    # For manual capture:
    import sentry_sdk
    sentry_sdk.capture_exception(error)
    sentry_sdk.capture_message("Something happened")
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from omoi_os.config import get_app_settings
from omoi_os.logging import get_logger

logger = get_logger(__name__)

# Patterns for PII detection and redaction
PII_PATTERNS = {
    # Email addresses
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    # Credit card numbers (basic pattern)
    "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
    # Phone numbers (various formats)
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    # SSN
    "ssn": re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"),
    # API keys / tokens (generic pattern for long hex/base64 strings)
    "api_key": re.compile(r"\b[a-zA-Z0-9_-]{32,}\b"),
}

# Keys that should always be redacted
SENSITIVE_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "api-key",
    "authorization",
    "auth",
    "bearer",
    "access_token",
    "refresh_token",
    "private_key",
    "privatekey",
    "private-key",
    "credentials",
    "credit_card",
    "creditcard",
    "card_number",
    "cvv",
    "ssn",
    "social_security",
    "stripe_key",
    "stripe_secret",
    "webhook_secret",
    "session_id",
    "sessionid",
    "cookie",
    "x-api-key",
    "x-auth-token",
}

# Global flag to track initialization
_sentry_initialized = False


def _is_sensitive_key(key: str) -> bool:
    """Check if a key name indicates sensitive data."""
    key_lower = key.lower()
    return any(sensitive in key_lower for sensitive in SENSITIVE_KEYS)


def _redact_value(value: Any) -> Any:
    """Redact a value, preserving its type information."""
    if value is None:
        return None
    if isinstance(value, str):
        return "[REDACTED]"
    if isinstance(value, (int, float)):
        return 0
    if isinstance(value, bool):
        return value  # Booleans don't contain PII
    if isinstance(value, (list, tuple)):
        return [_redact_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    return "[REDACTED]"


def _scrub_pii_from_string(value: str) -> str:
    """Scrub PII patterns from a string value."""
    result = value
    for pattern_name, pattern in PII_PATTERNS.items():
        result = pattern.sub(f"[{pattern_name.upper()}_REDACTED]", result)
    return result


def _scrub_dict(data: Dict[str, Any], depth: int = 0, max_depth: int = 10) -> Dict[str, Any]:
    """Recursively scrub PII from a dictionary."""
    if depth > max_depth:
        return {"_truncated": True}

    result = {}
    for key, value in data.items():
        # Check if key indicates sensitive data
        if _is_sensitive_key(key):
            result[key] = _redact_value(value)
        elif isinstance(value, dict):
            result[key] = _scrub_dict(value, depth + 1, max_depth)
        elif isinstance(value, (list, tuple)):
            result[key] = [
                _scrub_dict(v, depth + 1, max_depth) if isinstance(v, dict)
                else _scrub_pii_from_string(v) if isinstance(v, str) else v
                for v in value
            ]
        elif isinstance(value, str):
            result[key] = _scrub_pii_from_string(value)
        else:
            result[key] = value

    return result


def filter_pii(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Filter PII from Sentry events before sending.

    This is the before_send hook for Sentry SDK.

    Args:
        event: The Sentry event to be sent
        hint: Additional information about the event (e.g., original exception)

    Returns:
        Modified event with PII filtered, or None to drop the event
    """
    # Don't filter if send_default_pii is explicitly enabled (dev mode)
    settings = get_app_settings().sentry
    if settings.send_default_pii:
        return event

    try:
        # Scrub request data
        if "request" in event:
            request = event["request"]
            if "headers" in request:
                request["headers"] = _scrub_dict(request["headers"])
            if "data" in request:
                if isinstance(request["data"], dict):
                    request["data"] = _scrub_dict(request["data"])
                elif isinstance(request["data"], str):
                    request["data"] = _scrub_pii_from_string(request["data"])
            if "query_string" in request:
                request["query_string"] = _scrub_pii_from_string(
                    request.get("query_string", "")
                )
            if "cookies" in request:
                request["cookies"] = "[REDACTED]"

        # Scrub user data
        if "user" in event:
            user = event["user"]
            # Keep user ID for correlation, redact everything else
            event["user"] = {
                "id": user.get("id"),
                "username": "[REDACTED]" if user.get("username") else None,
                "email": "[REDACTED]" if user.get("email") else None,
                "ip_address": user.get("ip_address"),  # Keep for geo but scrub if needed
            }

        # Scrub exception values for PII patterns
        if "exception" in event and "values" in event["exception"]:
            for exc in event["exception"]["values"]:
                if "value" in exc and isinstance(exc["value"], str):
                    exc["value"] = _scrub_pii_from_string(exc["value"])
                # Scrub local variables in stack frames
                if "stacktrace" in exc and "frames" in exc["stacktrace"]:
                    for frame in exc["stacktrace"]["frames"]:
                        if "vars" in frame:
                            frame["vars"] = _scrub_dict(frame["vars"])

        # Scrub breadcrumbs
        if "breadcrumbs" in event and "values" in event["breadcrumbs"]:
            for breadcrumb in event["breadcrumbs"]["values"]:
                if "data" in breadcrumb:
                    breadcrumb["data"] = _scrub_dict(breadcrumb["data"])
                if "message" in breadcrumb:
                    breadcrumb["message"] = _scrub_pii_from_string(
                        breadcrumb.get("message", "")
                    )

        # Scrub extra context
        if "extra" in event:
            event["extra"] = _scrub_dict(event["extra"])

        # Scrub contexts
        if "contexts" in event:
            event["contexts"] = _scrub_dict(event["contexts"])

        # Scrub tags (less aggressive, just check sensitive keys)
        if "tags" in event:
            event["tags"] = {
                k: "[REDACTED]" if _is_sensitive_key(k) else v
                for k, v in event["tags"].items()
            }

    except Exception as e:
        # If scrubbing fails, log and return original event
        # This prevents crashes in the error handler
        logger.warning(f"PII scrubbing failed: {e}")

    return event


def init_sentry() -> bool:
    """Initialize Sentry SDK with application configuration.

    Should be called once at application startup.

    Returns:
        True if Sentry was initialized, False if not configured
    """
    global _sentry_initialized

    if _sentry_initialized:
        logger.debug("Sentry already initialized")
        return True

    settings = get_app_settings().sentry

    if not settings.is_configured:
        logger.info("Sentry not configured (SENTRY_DSN not set)")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.httpx import HttpxIntegration

        # Configure logging integration - capture errors and warnings
        logging_integration = LoggingIntegration(
            level=None,  # Don't capture logs at any level as breadcrumbs
            event_level=None,  # Don't send logs as events (we use structlog)
        )

        sentry_sdk.init(
            dsn=settings.dsn,
            environment=settings.environment,
            release=settings.release,
            debug=settings.debug,
            # Sampling
            traces_sample_rate=settings.traces_sample_rate if settings.enable_tracing else 0.0,
            profiles_sample_rate=settings.profiles_sample_rate if settings.enable_tracing else 0.0,
            # PII
            send_default_pii=settings.send_default_pii,
            before_send=filter_pii,
            # Additional settings
            attach_stacktrace=settings.attach_stacktrace,
            max_breadcrumbs=settings.max_breadcrumbs,
            # Integrations
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                RedisIntegration(),
                HttpxIntegration(),
                logging_integration,
            ],
            # Filter out health check transactions
            traces_sampler=_traces_sampler,
        )

        _sentry_initialized = True
        logger.info(
            "Sentry initialized",
            environment=settings.environment,
            tracing_enabled=settings.enable_tracing,
            traces_sample_rate=settings.traces_sample_rate,
        )
        return True

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def _traces_sampler(sampling_context: Dict[str, Any]) -> float:
    """Custom sampler to filter out noisy transactions.

    Args:
        sampling_context: Context about the transaction being sampled

    Returns:
        Sample rate for this transaction (0.0 to 1.0)
    """
    settings = get_app_settings().sentry

    # Get transaction name
    transaction_name = sampling_context.get("transaction_context", {}).get("name", "")

    # Always skip health check endpoints
    if any(
        path in transaction_name.lower()
        for path in ["/health", "/healthz", "/ready", "/readiness", "/liveness", "/metrics"]
    ):
        return 0.0

    # Skip static file requests
    if "/static/" in transaction_name or "/favicon" in transaction_name:
        return 0.0

    # Skip internal endpoints
    if "/_" in transaction_name:
        return 0.0

    # Sample API requests at configured rate
    if "/api/" in transaction_name:
        return settings.traces_sample_rate

    # Sample webhook requests at higher rate (important for debugging)
    if "/webhook" in transaction_name.lower():
        return min(settings.traces_sample_rate * 2, 1.0)

    # Default sample rate
    return settings.traces_sample_rate


def capture_exception(exception: Exception, **context: Any) -> Optional[str]:
    """Capture an exception to Sentry with additional context.

    Args:
        exception: The exception to capture
        **context: Additional context to attach to the event

    Returns:
        Event ID if captured, None otherwise
    """
    if not _sentry_initialized:
        return None

    import sentry_sdk

    with sentry_sdk.push_scope() as scope:
        for key, value in context.items():
            scope.set_extra(key, value)
        return sentry_sdk.capture_exception(exception)


def capture_message(message: str, level: str = "info", **context: Any) -> Optional[str]:
    """Capture a message to Sentry with additional context.

    Args:
        message: The message to capture
        level: Log level (debug, info, warning, error, fatal)
        **context: Additional context to attach to the event

    Returns:
        Event ID if captured, None otherwise
    """
    if not _sentry_initialized:
        return None

    import sentry_sdk

    with sentry_sdk.push_scope() as scope:
        for key, value in context.items():
            scope.set_extra(key, value)
        return sentry_sdk.capture_message(message, level=level)


def set_user(user_id: str, email: Optional[str] = None, username: Optional[str] = None) -> None:
    """Set the current user context for Sentry.

    Args:
        user_id: Unique user identifier
        email: User's email (will be redacted by PII filter)
        username: User's username (will be redacted by PII filter)
    """
    if not _sentry_initialized:
        return

    import sentry_sdk

    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
        "username": username,
    })


def set_tag(key: str, value: str) -> None:
    """Set a tag on the current scope.

    Tags are searchable in Sentry and can be used for filtering.

    Args:
        key: Tag name
        value: Tag value
    """
    if not _sentry_initialized:
        return

    import sentry_sdk

    sentry_sdk.set_tag(key, value)


def set_context(name: str, data: Dict[str, Any]) -> None:
    """Set additional context data on the current scope.

    Args:
        name: Context name
        data: Context data dictionary
    """
    if not _sentry_initialized:
        return

    import sentry_sdk

    sentry_sdk.set_context(name, data)


__all__ = [
    "init_sentry",
    "filter_pii",
    "capture_exception",
    "capture_message",
    "set_user",
    "set_tag",
    "set_context",
]
