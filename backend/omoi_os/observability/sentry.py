"""Backward-compatibility shim for the legacy Sentry surface.

Sentry was removed as part of the Sentry → PostHog migration; the actual
implementation now lives in :mod:`omoi_os.observability.posthog`. This
module re-exports the same names so any caller still doing
``from omoi_os.observability.sentry import capture_exception`` keeps
working without an import-path churn.

The name "sentry" is preserved purely for backward compat — there is no
Sentry SDK in this codebase anymore. New code should prefer importing
directly from :mod:`omoi_os.observability.posthog`, or via the package
re-exports in :mod:`omoi_os.observability`.

PII helpers are re-exported from :mod:`omoi_os.observability._pii`.
"""

from __future__ import annotations

from typing import Any, Dict

from omoi_os.logging import get_logger
from omoi_os.observability._pii import (
    PII_PATTERNS,
    SENSITIVE_KEYS,
    _is_sensitive_key,
    _redact_value,
    _scrub_dict,
    _scrub_pii_from_string,
)
from omoi_os.observability.posthog import (
    capture_exception,
    capture_message,
    init_posthog_observability,
    metric_distribution,
    metric_gauge,
    metric_increment,
    metric_set,
    set_context,
    set_tag,
    set_user,
    track_agent_health,
    track_llm_usage,
    track_queue_depth,
    track_task_completed,
    track_task_failed,
    track_task_retried,
)

logger = get_logger(__name__)


def init_sentry() -> bool:
    """Deprecated no-op kept for backward compatibility.

    Sentry was removed in favor of PostHog. Callers should switch to
    :func:`omoi_os.observability.posthog.init_posthog_observability` —
    this stub forwards to it so existing boot sequences keep working
    until they're updated.
    """
    logger.debug(
        "init_sentry() is a deprecated no-op; forwarding to "
        "init_posthog_observability()"
    )
    return init_posthog_observability()


def filter_pii(
    event: Dict[str, Any], hint: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Apply the codebase's PII scrubbing rules to an event-shaped dict.

    Originally a Sentry ``before_send`` hook; kept here in stub form so any
    out-of-tree caller still importing ``filter_pii`` doesn't break. We no
    longer have a Sentry event pipeline to feed it into, so this just
    returns a scrubbed copy of the input dict.
    """
    if not isinstance(event, dict):
        return event
    return _scrub_dict(event)


__all__ = [
    # Init shim
    "init_sentry",
    # Capture wrappers (route to PostHog)
    "capture_exception",
    "capture_message",
    "set_user",
    "set_tag",
    "set_context",
    # Metrics
    "metric_increment",
    "metric_gauge",
    "metric_distribution",
    "metric_set",
    # Pre-built metrics
    "track_task_completed",
    "track_task_failed",
    "track_task_retried",
    "track_queue_depth",
    "track_agent_health",
    "track_llm_usage",
    # PII helpers (re-exported for any out-of-tree caller)
    "PII_PATTERNS",
    "SENSITIVE_KEYS",
    "filter_pii",
    "_is_sensitive_key",
    "_redact_value",
    "_scrub_pii_from_string",
    "_scrub_dict",
]
