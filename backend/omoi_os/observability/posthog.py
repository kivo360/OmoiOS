"""PostHog error tracking + operational events.

This module is the new home for error tracking, intended to replace
``omoi_os.observability.sentry``. It uses PostHog's v7 module-level *context*
API so exception captures, tags, and identification flow through
``with posthog.new_context():`` blocks (FastAPI middleware, worker
entrypoints, Modal sandbox functions, Celery tasks, etc.).

Two PostHog usages now coexist intentionally:

1. ``omoi_os.analytics.posthog`` — product analytics events using the v3
   client-instance API (``Posthog(...)``, ``client.capture(...)``). Used by
   billing/auth/workflow code. Untouched by the migration.
2. ``omoi_os.observability.posthog`` — *this module*, error tracking using
   the v7 module-level API (``posthog.api_key = ...``, ``posthog.tag(...)``,
   ``posthog.new_context()``, ``posthog.capture_exception(...)``).

Sentry runs in parallel until the cleanup commit removes it. Both error
pipelines fire on the same exception during the dual-write window.

Usage:
    # At application startup (api/main.py)
    from omoi_os.observability.posthog import init_posthog_observability
    init_posthog_observability()

    # Anywhere — wrappers mirror omoi_os.observability.sentry.*
    from omoi_os.observability.posthog import capture_exception, set_tag
    try:
        do_thing()
    except Exception as e:
        capture_exception(e, request_id=rid)
"""

from __future__ import annotations

import atexit
import os
import re
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

from omoi_os.config import get_app_settings
from omoi_os.logging import get_logger
from omoi_os.observability._pii import (
    SENSITIVE_KEYS,
    _is_sensitive_key,
    _redact_value,
    _scrub_dict,
    _scrub_pii_from_string,
)

logger = get_logger(__name__)

# Global flag to track initialization. Mirrors observability.sentry._sentry_initialized.
_posthog_observability_initialized = False
_posthog_module = None  # cached posthog module after init succeeds


def _serverless_environment() -> bool:
    """Detect whether we're running in a context that needs sync_mode flushing.

    Modal sandbox containers exit before async batches drain; same for
    pytest collection. Force sync mode there so events are not silently
    dropped on container exit.
    """
    if os.environ.get("MODAL_TASK_ID"):
        return True
    env = os.environ.get("OMOIOS_ENV", "").lower()
    return env in {"sandbox", "test"}


def init_posthog_observability() -> bool:
    """Configure the posthog module for error tracking.

    Returns True if PostHog observability is now active, False if not
    configured (POSTHOG_API_KEY missing, or POSTHOG_DISABLED set).

    Safe to call multiple times — second call is a no-op.
    """
    global _posthog_observability_initialized, _posthog_module

    if _posthog_observability_initialized:
        return _posthog_module is not None

    settings = get_app_settings().posthog
    if not settings.is_configured:
        logger.info("PostHog observability not configured (POSTHOG_API_KEY not set)")
        _posthog_observability_initialized = True
        return False

    try:
        import posthog
    except ImportError:
        logger.warning("posthog package not installed; observability disabled")
        _posthog_observability_initialized = True
        return False

    posthog.api_key = settings.api_key
    posthog.host = settings.host
    posthog.debug = settings.debug
    # privacy_mode strips IP and similar at the SDK level; we do additional
    # PII scrubbing in our own wrappers below.
    posthog.privacy_mode = True
    posthog.enable_exception_autocapture = settings.capture_exceptions
    posthog.capture_exception_code_variables = settings.capture_code_variables

    # Mask sensitive variable names in any code-variables that do get captured.
    # PostHog's defaults are conservative; we layer our own SENSITIVE_KEYS on top.
    try:
        existing_masks = list(posthog.code_variables_mask_patterns or [])
        for key in SENSITIVE_KEYS:
            existing_masks.append(re.compile(rf"(?i){re.escape(key)}"))
        posthog.code_variables_mask_patterns = existing_masks
    except Exception as e:  # noqa: BLE001 — best-effort hardening
        logger.warning(f"Could not extend code_variables_mask_patterns: {e}")

    # Force sync mode for serverless / test environments so events flush before
    # the container exits. atexit is unreliable in some Modal task lifecycles,
    # so callers running inside Modal should also wrap entrypoints in a
    # try/finally with explicit posthog.shutdown().
    if settings.sync_mode or _serverless_environment():
        posthog.sync_mode = True

    atexit.register(_safe_shutdown)

    _posthog_module = posthog
    _posthog_observability_initialized = True

    logger.info(
        "PostHog observability initialized",
        host=settings.host,
        sync_mode=getattr(posthog, "sync_mode", False),
        capture_exceptions=settings.capture_exceptions,
        capture_code_variables=settings.capture_code_variables,
    )
    return True


def _safe_shutdown() -> None:
    """atexit-safe shutdown that won't raise on import errors."""
    try:
        if _posthog_module is not None:
            _posthog_module.shutdown()
    except Exception as e:  # noqa: BLE001
        logger.debug(f"posthog.shutdown() raised at exit: {e}")


def shutdown() -> None:
    """Explicit shutdown for serverless / Modal entrypoints.

    Call this in a ``finally:`` block at the end of any function whose
    container exits soon (Modal ``@app.function``, Lambda handlers, etc.) —
    atexit may not fire reliably inside those runtimes.
    """
    _safe_shutdown()


# =============================================================================
# Capture wrappers (mirror observability.sentry.* signatures)
# =============================================================================


def capture_exception(exception: BaseException, **context: Any) -> Optional[str]:
    """Capture an exception with optional extra context (tags).

    Mirrors :func:`omoi_os.observability.sentry.capture_exception`. The extra
    context is PII-scrubbed and folded into PostHog tags inside a fresh
    context scope so it doesn't leak into surrounding requests.

    Returns the PostHog event ID if captured, ``None`` otherwise.
    """
    if _posthog_module is None:
        return None

    try:
        with _posthog_module.new_context():
            for key, value in context.items():
                _safe_tag(key, value)
            return _posthog_module.capture_exception(exception)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"posthog.capture_exception failed: {e}")
        return None


def capture_message(message: str, level: str = "info", **context: Any) -> Optional[str]:
    """Capture a message-as-event with optional extra context.

    PostHog has no native ``capture_message``; we route to a custom event
    named ``log_message`` with ``level`` + ``message`` properties. Context
    keys become extra event properties (PII-scrubbed).
    """
    if _posthog_module is None:
        return None

    properties: Dict[str, Any] = {
        "level": level,
        "message": _scrub_pii_from_string(message),
    }
    for key, value in (context or {}).items():
        if _is_sensitive_key(key):
            properties[key] = _redact_value(value)
        elif isinstance(value, str):
            properties[key] = _scrub_pii_from_string(value)
        elif isinstance(value, dict):
            properties[key] = _scrub_dict(value)
        else:
            properties[key] = value

    try:
        return _posthog_module.capture("log_message", properties=properties)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"posthog.capture(log_message) failed: {e}")
        return None


def set_user(
    user_id: str, email: Optional[str] = None, username: Optional[str] = None
) -> None:
    """Identify the current PostHog context with a user.

    PostHog v7's ``identify_context`` takes only a distinct_id. Email and
    username were redacted by Sentry's PII filter anyway, so we don't ship
    them — they'd be ``[REDACTED]`` strings of no analytic value.
    """
    if _posthog_module is None or not user_id:
        return
    try:
        _posthog_module.identify_context(str(user_id))
    except Exception as e:  # noqa: BLE001
        logger.debug(f"posthog.identify_context failed: {e}")


def set_tag(key: str, value: Any) -> None:
    """Add a tag to the current PostHog context."""
    if _posthog_module is None:
        return
    _safe_tag(key, value)


def set_context(name: str, data: Dict[str, Any]) -> None:
    """Flatten a Sentry-style nested context dict into dot-prefixed tags.

    PostHog tags are flat; we mirror Sentry's ``set_context("agent", {...})``
    by emitting ``agent.<key>`` tags for each item.
    """
    if _posthog_module is None or not data:
        return
    for key, value in data.items():
        _safe_tag(f"{name}.{key}", value)


@contextmanager
def push_scope() -> Iterator[Any]:
    """Drop-in replacement for ``with sentry_sdk.push_scope() as scope:``.

    Callers that used ``scope.set_tag(...)`` / ``scope.set_extra(...)`` should
    instead call module-level :func:`set_tag` / :func:`set_context` inside
    the ``with`` block.
    """
    if _posthog_module is None:
        yield None
        return
    with _posthog_module.new_context():
        yield None


def _safe_tag(key: str, value: Any) -> None:
    """Tag with PII redaction for sensitive keys / strings."""
    if _posthog_module is None:
        return
    try:
        if _is_sensitive_key(key):
            value = _redact_value(value)
        elif isinstance(value, str):
            value = _scrub_pii_from_string(value)
        _posthog_module.tag(key, value)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"posthog.tag({key!r}) failed: {e}")


# =============================================================================
# Metrics API — route Sentry's metrics surface through PostHog events
# =============================================================================
# Sentry SDK v2 already removed the metrics API and the existing wrappers
# are no-ops. We replace them with lightweight PostHog ``capture`` calls so
# operational telemetry (queue depth, agent health, llm token usage) survives
# the Sentry removal. These are not high-cardinality; PostHog handles them as
# regular events.


def metric_increment(
    name: str, value: int = 1, tags: Optional[Dict[str, str]] = None
) -> None:
    """Counter metric → ``metric.increment`` event."""
    if _posthog_module is None:
        return
    try:
        _posthog_module.capture(
            "metric.increment",
            properties={"metric": name, "value": value, **(tags or {})},
        )
    except Exception:  # noqa: BLE001
        return


def metric_gauge(
    name: str, value: float, tags: Optional[Dict[str, str]] = None
) -> None:
    """Gauge metric → ``metric.gauge`` event."""
    if _posthog_module is None:
        return
    try:
        _posthog_module.capture(
            "metric.gauge",
            properties={"metric": name, "value": value, **(tags or {})},
        )
    except Exception:  # noqa: BLE001
        return


def metric_distribution(
    name: str, value: float, tags: Optional[Dict[str, str]] = None
) -> None:
    """Distribution metric → ``metric.distribution`` event."""
    if _posthog_module is None:
        return
    try:
        _posthog_module.capture(
            "metric.distribution",
            properties={"metric": name, "value": value, **(tags or {})},
        )
    except Exception:  # noqa: BLE001
        return


def metric_set(name: str, value: str, tags: Optional[Dict[str, str]] = None) -> None:
    """Set metric (count of unique values) → ``metric.set`` event."""
    if _posthog_module is None:
        return
    try:
        _posthog_module.capture(
            "metric.set",
            properties={"metric": name, "value": value, **(tags or {})},
        )
    except Exception:  # noqa: BLE001
        return


# =============================================================================
# Pre-built metrics for common OmoiOS operations
# =============================================================================
# These mirror observability.sentry.track_* so the same callers work
# unchanged once we swap their import path in Phase 5.


def track_task_completed(task_id: str, phase: str, duration_ms: float) -> None:
    metric_increment("omoios.task.completed", tags={"phase": phase})
    metric_distribution("omoios.task.duration_ms", duration_ms, tags={"phase": phase})


def track_task_failed(task_id: str, phase: str, error_type: str) -> None:
    metric_increment(
        "omoios.task.failed", tags={"phase": phase, "error_type": error_type}
    )


def track_task_retried(task_id: str, phase: str, retry_count: int) -> None:
    metric_increment("omoios.task.retried", tags={"phase": phase})
    metric_gauge("omoios.task.retry_count", retry_count, tags={"task_id": task_id})


def track_queue_depth(
    queue_name: str, depth: int, priority: Optional[str] = None
) -> None:
    tags: Dict[str, str] = {"queue": queue_name}
    if priority:
        tags["priority"] = priority
    metric_gauge("omoios.queue.depth", depth, tags=tags)


def track_agent_health(agent_id: str, status: str) -> None:
    metric_increment(f"omoios.agent.{status}", tags={"agent_id": agent_id})
    metric_set("omoios.agents.active", agent_id)


def track_llm_usage(
    model: str, tokens_in: int, tokens_out: int, duration_ms: float
) -> None:
    tags = {"model": model}
    metric_increment("omoios.llm.requests", tags=tags)
    metric_distribution("omoios.llm.tokens_in", tokens_in, tags=tags)
    metric_distribution("omoios.llm.tokens_out", tokens_out, tags=tags)
    metric_distribution("omoios.llm.duration_ms", duration_ms, tags=tags)


__all__ = [
    "init_posthog_observability",
    "shutdown",
    "capture_exception",
    "capture_message",
    "set_user",
    "set_tag",
    "set_context",
    "push_scope",
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
]
