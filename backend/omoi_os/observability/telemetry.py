"""Unified telemetry facade — single public surface for the codebase.

Routes the four signals (errors, traces, metrics, events) to the right
sinks based on the routing matrix in :mod:`omoi_os.observability._taxonomy`:

    Errors      → Sentry SDK (BetterStack Errors) + PostHog (mirror)
    Traces      → OTel SDK (BetterStack Telemetry) + Sentry (via SentrySpanProcessor)
    Metrics     → OTel SDK (BetterStack Telemetry) + PostHog (counters)
    Events      → PostHog (primary) + OTel counters (revenue/feature)
    Heartbeats  → BetterStack Uptime

The current ``omoi_os.observability.posthog`` and
``omoi_os.observability.betterstack`` modules are the implementation details;
no caller should import them directly. Callers use this module:

    from omoi_os.observability.telemetry import (
        capture_exception, metric_increment, track_event, identify_user,
    )
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Optional

from omoi_os.config import get_app_settings
from omoi_os.logging import get_logger
from omoi_os.observability._taxonomy import (
    Domain,
    EVENT_TASK_COMPLETED,
    EVENT_TASK_FAILED,
    EVENT_TASK_RETRIED,
    Sink,
    domain_for,
    sinks_for,
)

# Re-export taxonomy so callers can `from telemetry import EVENT_USER_SIGNUP`.
from omoi_os.observability._taxonomy import *  # noqa: F401,F403

# Re-export PII helpers for legacy callers.
from omoi_os.observability._pii import (  # noqa: F401
    PII_PATTERNS,
    SENSITIVE_KEYS,
    _is_sensitive_key,
    _redact_value,
    _scrub_dict,
    _scrub_pii_from_string,
)

# Bind to the existing PostHog implementation as the secondary sink.
from omoi_os.observability import posthog as _ph

# BetterStack module — primary sink for errors/traces/metrics.
from omoi_os.observability import betterstack as _bs

logger = get_logger(__name__)

_initialized = False


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def init_telemetry() -> None:
    """Initialize all configured sinks. Idempotent."""
    global _initialized
    if _initialized:
        return

    # PostHog (errors + product analytics)
    try:
        _ph.init_posthog_observability()
    except Exception as exc:  # noqa: BLE001
        logger.warning("PostHog init failed: %s", exc)

    # PostHog logs bridge (existing module)
    try:
        from omoi_os.observability import posthog_logs

        posthog_logs.init_posthog_logs()
    except Exception as exc:  # noqa: BLE001
        logger.debug("PostHog logs bridge skipped: %s", exc)

    # BetterStack (Sentry SDK + OTel + Uptime)
    settings = get_app_settings().betterstack
    if settings.is_errors_configured or settings.is_otlp_configured:
        try:
            _bs.init_betterstack()
        except Exception as exc:  # noqa: BLE001
            logger.warning("BetterStack init failed: %s", exc)

    _initialized = True


def shutdown() -> None:
    """Flush every buffered sink. Call from atexit / serverless entrypoints."""
    try:
        _ph.shutdown()
    except Exception as exc:  # noqa: BLE001
        logger.debug("PostHog shutdown raised: %s", exc)
    try:
        _bs.shutdown()
    except Exception as exc:  # noqa: BLE001
        logger.debug("BetterStack shutdown raised: %s", exc)


# Backwards-compatible name; some callers still import init_sentry.
def init_sentry() -> bool:
    """Deprecated alias for :func:`init_telemetry`."""
    init_telemetry()
    return True


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


def capture_exception(exception: BaseException, **context: Any) -> Optional[str]:
    """Capture an exception to BetterStack Errors (Sentry) + PostHog.

    Returns the BetterStack event id if available, else the PostHog one.
    """
    bs_id = _capture_to_sentry(exception, context)
    ph_id = _ph.capture_exception(exception, **context)
    return bs_id or ph_id


def capture_message(message: str, level: str = "info", **context: Any) -> Optional[str]:
    bs_id = _capture_message_to_sentry(message, level, context)
    ph_id = _ph.capture_message(message, level=level, **context)
    return bs_id or ph_id


def _capture_to_sentry(
    exception: BaseException, context: dict[str, Any]
) -> Optional[str]:
    handle = _bs.get_handle()
    if handle is None or not handle.sentry_initialized:
        return None
    try:
        import sentry_sdk

        with sentry_sdk.new_scope() as scope:
            for k, v in context.items():
                scope.set_extra(k, v)
            return sentry_sdk.capture_exception(exception)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Sentry capture_exception failed: %s", exc)
        return None


def _capture_message_to_sentry(
    message: str, level: str, context: dict[str, Any]
) -> Optional[str]:
    handle = _bs.get_handle()
    if handle is None or not handle.sentry_initialized:
        return None
    try:
        import sentry_sdk

        with sentry_sdk.new_scope() as scope:
            for k, v in context.items():
                scope.set_extra(k, v)
            return sentry_sdk.capture_message(message, level=level)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Sentry capture_message failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


def set_user(
    user_id: Optional[str] = None,
    *,
    email: Optional[str] = None,
    username: Optional[str] = None,
    **traits: Any,
) -> None:
    _ph.set_user(user_id, email=email, username=username, **traits)
    handle = _bs.get_handle()
    if handle and handle.sentry_initialized:
        try:
            import sentry_sdk

            sentry_sdk.set_user(
                {
                    "id": user_id,
                    "email": email,
                    "username": username,
                    **traits,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Sentry set_user failed: %s", exc)


def set_tag(key: str, value: Any) -> None:
    _ph.set_tag(key, value)
    handle = _bs.get_handle()
    if handle and handle.sentry_initialized:
        try:
            import sentry_sdk

            sentry_sdk.set_tag(key, value)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Sentry set_tag failed: %s", exc)


def set_context(name: str, data: dict[str, Any]) -> None:
    _ph.set_context(name, data)
    handle = _bs.get_handle()
    if handle and handle.sentry_initialized:
        try:
            import sentry_sdk

            sentry_sdk.set_context(name, data)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Sentry set_context failed: %s", exc)


@contextmanager
def push_scope() -> Iterator[Any]:
    with _ph.push_scope() as scope:
        yield scope


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def metric_increment(
    name: str, value: float = 1.0, tags: Optional[dict[str, str]] = None
) -> None:
    """Counter increment. Routes to OTel + PostHog."""
    _ph.metric_increment(name, value=value, tags=tags)
    _otel_counter(name, value, tags or {})


def metric_gauge(
    name: str, value: float, tags: Optional[dict[str, str]] = None
) -> None:
    _ph.metric_gauge(name, value=value, tags=tags)
    _otel_gauge(name, value, tags or {})


def metric_histogram(
    name: str, value: float, tags: Optional[dict[str, str]] = None
) -> None:
    """Histogram observation — equivalent to PostHog distribution."""
    _ph.metric_distribution(name, value=value, tags=tags)
    _otel_histogram(name, value, tags or {})


# Legacy alias.
metric_distribution = metric_histogram


def metric_set(name: str, value: str, tags: Optional[dict[str, str]] = None) -> None:
    """Unique-cardinality counter (PostHog only — OTel has no equivalent)."""
    _ph.metric_set(name, value=value, tags=tags)


def _otel_counter(name: str, value: float, attributes: dict[str, str]) -> None:
    handle = _bs.get_handle()
    if handle is None or handle.meter_provider is None:
        return
    try:
        from opentelemetry import metrics as otel_metrics

        meter = otel_metrics.get_meter("omoi_os")
        counter = _meter_get_or_create(meter, name, "counter")
        counter.add(value, attributes)
    except Exception as exc:  # noqa: BLE001
        logger.debug("OTel counter failed: %s", exc)


def _otel_gauge(name: str, value: float, attributes: dict[str, str]) -> None:
    handle = _bs.get_handle()
    if handle is None or handle.meter_provider is None:
        return
    try:
        from opentelemetry import metrics as otel_metrics

        meter = otel_metrics.get_meter("omoi_os")
        gauge = _meter_get_or_create(meter, name, "gauge")
        gauge.set(value, attributes)
    except Exception as exc:  # noqa: BLE001
        logger.debug("OTel gauge failed: %s", exc)


def _otel_histogram(name: str, value: float, attributes: dict[str, str]) -> None:
    handle = _bs.get_handle()
    if handle is None or handle.meter_provider is None:
        return
    try:
        from opentelemetry import metrics as otel_metrics

        meter = otel_metrics.get_meter("omoi_os")
        hist = _meter_get_or_create(meter, name, "histogram")
        hist.record(value, attributes)
    except Exception as exc:  # noqa: BLE001
        logger.debug("OTel histogram failed: %s", exc)


_INSTRUMENT_CACHE: dict[tuple[str, str], Any] = {}


def _meter_get_or_create(meter, name: str, kind: str):
    """Cache OTel instruments — re-creating on every call wastes memory."""
    cache_key = (name, kind)
    inst = _INSTRUMENT_CACHE.get(cache_key)
    if inst is not None:
        return inst
    if kind == "counter":
        inst = meter.create_counter(name)
    elif kind == "gauge":
        inst = meter.create_gauge(name)
    elif kind == "histogram":
        inst = meter.create_histogram(name)
    else:  # pragma: no cover
        raise ValueError(f"unknown instrument kind: {kind}")
    _INSTRUMENT_CACHE[cache_key] = inst
    return inst


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


def track_event(
    name: str,
    *,
    distinct_id: Optional[str] = None,
    domain: Optional[Domain] = None,
    properties: Optional[dict[str, Any]] = None,
) -> None:
    """Domain-aware event dispatch.

    Looks up the event in ``_taxonomy.EVENT_TO_DOMAIN`` to decide which
    sinks to fire. Falls back to PRODUCT if the event isn't registered.
    """
    domain = domain or domain_for(name)
    sinks = sinks_for(name)
    props = dict(properties or {})

    if Sink.POSTHOG in sinks:
        _track_posthog_event(name, distinct_id=distinct_id, properties=props)

    if Sink.BETTERSTACK_TELEMETRY in sinks:
        # Most events are also useful as a counter (e.g. checkout_completed).
        metric_increment(f"event_{name}_total", tags=_string_tags(props))


def identify_user(
    distinct_id: str,
    *,
    email: Optional[str] = None,
    properties: Optional[dict[str, Any]] = None,
) -> None:
    """Identify a user in PostHog and tag the Sentry scope."""
    props = dict(properties or {})
    if email:
        props.setdefault("email", email)
    _identify_posthog(distinct_id, props)
    set_user(distinct_id, email=email, **props)


def track_conversion(
    name: str,
    *,
    distinct_id: Optional[str] = None,
    value: Optional[float] = None,
    currency: str = "USD",
    properties: Optional[dict[str, Any]] = None,
) -> None:
    """Marketing-style conversion event (revenue + counter)."""
    props = dict(properties or {})
    if value is not None:
        props.setdefault("$revenue", value)
        props.setdefault("currency", currency)
        metric_histogram(
            f"revenue_{currency.lower()}",
            value,
            tags={"event": name, **_string_tags(props)},
        )
    track_event(name, distinct_id=distinct_id, properties=props)


def _track_posthog_event(
    name: str, *, distinct_id: Optional[str], properties: dict[str, Any]
) -> None:
    if distinct_id is None:
        # PostHog requires a distinct_id; use a server placeholder for
        # system-level events that aren't user-attributable.
        distinct_id = properties.get("user_id") or "server"
    try:
        from omoi_os.analytics import posthog as ph_analytics

        ph_analytics.track_event(user_id=distinct_id, event=name, properties=properties)
    except Exception as exc:  # noqa: BLE001
        logger.debug("PostHog track_event failed: %s", exc)


def _identify_posthog(distinct_id: str, properties: dict[str, Any]) -> None:
    try:
        from omoi_os.analytics import posthog as ph_analytics

        ph_analytics.identify_user(user_id=distinct_id, properties=properties)
    except Exception as exc:  # noqa: BLE001
        logger.debug("PostHog identify failed: %s", exc)


def _string_tags(props: dict[str, Any]) -> dict[str, str]:
    """OTel attribute values must be string/bool/number; coerce defensively."""
    out: dict[str, str] = {}
    for k, v in props.items():
        if isinstance(v, (str, int, float, bool)):
            out[k] = str(v)
    return out


# ---------------------------------------------------------------------------
# Pre-built operational metrics — same names as the legacy shim
# ---------------------------------------------------------------------------


def track_task_completed(task_id: str, phase: str, duration_ms: float) -> None:
    metric_histogram(
        "task_duration_ms", duration_ms, tags={"phase": phase, "outcome": "ok"}
    )
    metric_increment("tasks_completed_total", tags={"phase": phase})
    track_event(
        EVENT_TASK_COMPLETED,
        distinct_id=task_id,
        properties={"phase": phase, "duration_ms": duration_ms},
    )


def track_task_failed(task_id: str, phase: str, error_type: str) -> None:
    metric_increment(
        "tasks_failed_total", tags={"phase": phase, "error_type": error_type}
    )
    track_event(
        EVENT_TASK_FAILED,
        distinct_id=task_id,
        properties={"phase": phase, "error_type": error_type},
    )


def track_task_retried(task_id: str, phase: str, retry_count: int) -> None:
    metric_increment("tasks_retried_total", tags={"phase": phase})
    track_event(
        EVENT_TASK_RETRIED,
        distinct_id=task_id,
        properties={"phase": phase, "retry_count": retry_count},
    )


def track_queue_depth(queue: str, depth: int, **tags: str) -> None:
    metric_gauge("queue_depth_total", depth, tags={"queue": queue, **tags})


def track_agent_health(agent_id: str, status: str) -> None:
    metric_gauge(
        "agent_health_status",
        1 if status == "healthy" else 0,
        tags={"agent_id": agent_id, "status": status},
    )


def track_llm_usage(
    *,
    model: str,
    tokens_input: int,
    tokens_output: int,
    cost_usd: Optional[float] = None,
) -> None:
    metric_histogram("llm_tokens_input", tokens_input, tags={"model": model})
    metric_histogram("llm_tokens_output", tokens_output, tags={"model": model})
    if cost_usd is not None:
        metric_histogram("llm_cost_usd", cost_usd, tags={"model": model})


# ---------------------------------------------------------------------------
# Heartbeats
# ---------------------------------------------------------------------------


def deploy_marker(
    *,
    release: str,
    environment: str,
    git_sha: Optional[str] = None,
    actor: Optional[str] = None,
) -> None:
    """Mark a deploy in BetterStack + PostHog.

    Call from your CI/CD pipeline at the moment a new release goes live.
    Adds:
      * a counter in BetterStack Telemetry (chart deploy frequency)
      * a Sentry event (groups exceptions by release for "release health")
      * a PostHog event (cross-reference with product metrics)
    """
    metric_increment(
        "deploys_total",
        tags={"environment": environment, "release": release},
    )
    track_event(
        "deploy_completed",
        properties={
            "release": release,
            "environment": environment,
            "git_sha": git_sha,
            "actor": actor,
        },
    )

    handle = _bs.get_handle()
    if handle and handle.sentry_initialized:
        try:
            import sentry_sdk

            sentry_sdk.capture_message(
                f"Deploy {release} → {environment}",
                level="info",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Sentry deploy_marker capture_message failed: %s", exc)


def heartbeat() -> None:
    """Manually fire a heartbeat ping (synchronous, best-effort).

    The async background loop in :mod:`betterstack` already pings on a
    schedule; this is for one-off cron-like heartbeats from worker tick
    loops.
    """
    settings = get_app_settings().betterstack
    if not settings.heartbeat_token:
        return
    try:
        import httpx

        httpx.get(
            f"{_bs.UPTIME_HEARTBEAT_URL}/{settings.heartbeat_token}",
            timeout=5.0,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("heartbeat ping failed: %s", exc)


# ---------------------------------------------------------------------------
# Tracing decorators (delegate to the existing tracing module)
# ---------------------------------------------------------------------------


# These are imported lazily so the heavy tracing module isn't loaded
# unless someone actually uses tracing.
def __getattr__(name: str) -> Any:  # PEP 562
    if name in _TRACING_NAMES:
        from omoi_os.observability import tracing as _tracing

        return getattr(_tracing, name)
    raise AttributeError(name)


_TRACING_NAMES = {
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
}


__all__ = [
    # Lifecycle
    "init_telemetry",
    "init_sentry",  # legacy alias
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
    # Heartbeats / deploys
    "heartbeat",
    "deploy_marker",
    # Tracing (lazy-loaded via __getattr__)
    *sorted(_TRACING_NAMES),
    # PII helpers
    "PII_PATTERNS",
    "SENSITIVE_KEYS",
]
