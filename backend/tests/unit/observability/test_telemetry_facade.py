"""Test the unified telemetry facade.

Confirms the facade exports the superset of symbols that the legacy
``observability.sentry`` shim used to expose, and that the metrics /
event / context functions are no-ops when no sinks are configured.

Reference: docs/architecture/observability_unified.md
"""

from __future__ import annotations

import pytest

from omoi_os.observability import telemetry
from omoi_os.observability._taxonomy import (
    EVENT_CHECKOUT_COMPLETED,
    EVENT_TASK_COMPLETED,
    EVENT_USER_SIGNUP,
    Domain,
    Sink,
    domain_for,
    sinks_for,
)


# ---------------------------------------------------------------------------
# Public surface — facade must export everything the legacy shim did.
# ---------------------------------------------------------------------------

# These are the names the legacy shim ``observability.sentry`` re-exported.
# Future-proofs the migration: if anything is removed from the facade, the
# corresponding caller will break, and this test catches it first.
LEGACY_EXPECTED_SYMBOLS = (
    "init_sentry",
    "capture_exception",
    "capture_message",
    "set_user",
    "set_tag",
    "set_context",
    "metric_increment",
    "metric_gauge",
    "metric_distribution",
    "metric_set",
    "track_task_completed",
    "track_task_failed",
    "track_task_retried",
    "track_queue_depth",
    "track_agent_health",
    "track_llm_usage",
    "PII_PATTERNS",
    "SENSITIVE_KEYS",
)


@pytest.mark.unit
@pytest.mark.parametrize("name", LEGACY_EXPECTED_SYMBOLS)
def test_facade_exports_legacy_symbol(name: str) -> None:
    """Every legacy symbol from observability.sentry is present on the facade."""
    assert hasattr(telemetry, name), f"telemetry.{name} missing"


@pytest.mark.unit
def test_facade_exports_new_symbols() -> None:
    """New symbols introduced by the unified facade are present."""
    for name in ("track_event", "identify_user", "track_conversion", "heartbeat"):
        assert hasattr(telemetry, name), f"telemetry.{name} missing"


# ---------------------------------------------------------------------------
# Taxonomy — domain routing is deterministic and complete.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_domain_lookup_known_event() -> None:
    assert domain_for(EVENT_USER_SIGNUP) == Domain.USERS
    assert domain_for(EVENT_CHECKOUT_COMPLETED) == Domain.MARKETING
    assert domain_for(EVENT_TASK_COMPLETED) == Domain.PRODUCT


@pytest.mark.unit
def test_domain_lookup_unknown_event_defaults_to_product() -> None:
    assert domain_for("totally_made_up_event") == Domain.PRODUCT


@pytest.mark.unit
def test_sinks_for_event() -> None:
    assert Sink.POSTHOG in sinks_for(EVENT_USER_SIGNUP)
    assert Sink.BETTERSTACK_TELEMETRY in sinks_for(EVENT_CHECKOUT_COMPLETED)


# ---------------------------------------------------------------------------
# No-sink behavior — every facade function must be safe to call when nothing
# is configured. Boot order, test runs, and dev environments depend on this.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_metric_increment_no_sink_is_safe() -> None:
    # Should not raise even if no sink is configured.
    telemetry.metric_increment("test_metric", value=1.0, tags={"k": "v"})


@pytest.mark.unit
def test_metric_gauge_no_sink_is_safe() -> None:
    telemetry.metric_gauge("test_gauge", 42.0, tags={"k": "v"})


@pytest.mark.unit
def test_metric_histogram_no_sink_is_safe() -> None:
    telemetry.metric_histogram("test_hist", 1.5, tags={"k": "v"})


@pytest.mark.unit
def test_capture_exception_no_sink_is_safe() -> None:
    try:
        raise RuntimeError("synthetic")
    except RuntimeError as e:
        result = telemetry.capture_exception(e)
    # Returns either an event id or None — never raises.
    assert result is None or isinstance(result, str)


@pytest.mark.unit
def test_track_event_no_sink_is_safe() -> None:
    telemetry.track_event(
        EVENT_USER_SIGNUP, distinct_id="user-123", properties={"plan": "free"}
    )


@pytest.mark.unit
def test_track_task_completed_no_sink_is_safe() -> None:
    telemetry.track_task_completed("task-1", "PHASE_IMPLEMENTATION", 1234.5)


@pytest.mark.unit
def test_heartbeat_no_token_is_safe() -> None:
    # No BETTERSTACK_HEARTBEAT_TOKEN set in tests — must not raise.
    telemetry.heartbeat()


# ---------------------------------------------------------------------------
# Idempotence — init_telemetry must be re-callable without side effects.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_init_telemetry_idempotent() -> None:
    telemetry.init_telemetry()
    telemetry.init_telemetry()
    telemetry.init_telemetry()
