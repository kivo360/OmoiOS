"""PII detection and redaction helpers.

Shared by ``observability.posthog`` for scrubbing properties before they hit
the wire. Lives in its own module so neither ``observability.posthog`` nor
the legacy ``observability.sentry`` re-export shim has to import the other.

Patterns and keyword list mirror what the original Sentry ``before_send``
hook scrubbed; preserving them keeps PII coverage identical across the
migration.
"""

from __future__ import annotations

import re
from typing import Any, Dict

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


def _is_sensitive_key(key: str) -> bool:
    """Return True if the given key name indicates sensitive data."""
    key_lower = key.lower()
    return any(sensitive in key_lower for sensitive in SENSITIVE_KEYS)


def _redact_value(value: Any) -> Any:
    """Redact a value, preserving its type information."""
    if value is None:
        return None
    if isinstance(value, str):
        return "[REDACTED]"
    if isinstance(value, bool):
        return value  # Booleans don't contain PII
    if isinstance(value, (int, float)):
        return 0
    if isinstance(value, (list, tuple)):
        return [_redact_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    return "[REDACTED]"


def _scrub_pii_from_string(value: str | None) -> str:
    """Scrub PII patterns from a string value.

    Returns an empty string if ``None`` is passed.
    """
    if value is None:
        return ""
    result = value
    for pattern_name, pattern in PII_PATTERNS.items():
        result = pattern.sub(f"[{pattern_name.upper()}_REDACTED]", result)
    return result


def _scrub_dict(
    data: Dict[str, Any], depth: int = 0, max_depth: int = 10
) -> Dict[str, Any]:
    """Recursively scrub PII from a dictionary."""
    if depth > max_depth:
        return {"_truncated": True}

    result: Dict[str, Any] = {}
    for key, value in data.items():
        if _is_sensitive_key(key):
            result[key] = _redact_value(value)
        elif isinstance(value, dict):
            result[key] = _scrub_dict(value, depth + 1, max_depth)
        elif isinstance(value, (list, tuple)):
            result[key] = [
                (
                    _scrub_dict(v, depth + 1, max_depth)
                    if isinstance(v, dict)
                    else _scrub_pii_from_string(v)
                    if isinstance(v, str)
                    else v
                )
                for v in value
            ]
        elif isinstance(value, str):
            result[key] = _scrub_pii_from_string(value)
        else:
            result[key] = value

    return result


__all__ = [
    "PII_PATTERNS",
    "SENSITIVE_KEYS",
    "_is_sensitive_key",
    "_redact_value",
    "_scrub_pii_from_string",
    "_scrub_dict",
]
