"""PostHog product analytics — server-side event tracking.

Routes business events (billing, subscriptions, workflows, user lifecycle)
through PostHog's *module-level* v7 API:

    posthog.capture(event=..., distinct_id=..., properties=..., groups=...)
    posthog.set(distinct_id=..., properties=...)
    posthog.group_identify(group_type=..., group_key=..., properties=...)

This mirrors the same module-level API used by
``omoi_os.observability.posthog`` for error tracking, so a single
``posthog.api_key`` global drives both pipelines. Initialization is
delegated to ``init_posthog_observability()`` — calling
:func:`init_posthog` here is a thin wrapper that returns its result.

All ``user_id`` arguments must match the ``distinct_id`` used by the
frontend so events land on the same person record.

Usage:
    from omoi_os.analytics.posthog import track_event, identify_user

    track_event(
        user_id="user_123",
        event="workflow_completed",
        properties={"workflow_id": "abc"},
    )
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from warnings import warn

from omoi_os.logging import get_logger
from omoi_os.observability.posthog import init_posthog_observability

logger = get_logger(__name__)


def init_posthog() -> bool:
    """Initialize PostHog product analytics.

    Delegates to :func:`init_posthog_observability` which configures the
    same module-level posthog state (api_key, host, sync_mode,
    privacy_mode, exception autocapture). Safe to call multiple times.

    Returns True if PostHog is now usable, False otherwise.
    """
    return init_posthog_observability()


def shutdown_posthog() -> None:
    """Flush any buffered analytics events.

    The observability module already registers an atexit handler, so
    calling this manually is only needed in serverless / Modal entrypoints
    where atexit may not fire.
    """
    try:
        import posthog

        posthog.shutdown()
    except Exception as e:  # noqa: BLE001
        logger.debug(f"posthog.shutdown raised: {e}")


def get_posthog_client():
    """Deprecated — return the posthog module itself.

    Kept for any out-of-tree caller that still imports this. The v7 module
    surface is the canonical entry point; new code should ``import
    posthog`` directly.
    """
    warn(
        "get_posthog_client() is deprecated; import the `posthog` module "
        "directly. The v7 API surface lives at module level.",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        import posthog

        return posthog if getattr(posthog, "api_key", None) else None
    except ImportError:
        return None


def _ensure_initialized() -> bool:
    """Return True if PostHog is configured (api_key set) and importable."""
    try:
        import posthog
    except ImportError:
        return False
    return bool(getattr(posthog, "api_key", None))


def _normalize_user_id(user_id: Any) -> str:
    """Normalize user_id to string format."""
    if isinstance(user_id, UUID):
        return str(user_id)
    return str(user_id)


def track_event(
    user_id: str,
    event: str,
    properties: Optional[Dict[str, Any]] = None,
    timestamp: Optional[datetime] = None,
    groups: Optional[Dict[str, str]] = None,
) -> bool:
    """Track an event in PostHog.

    Args:
        user_id: Distinct ID for the user (should match frontend)
        event: Event name
        properties: Event properties
        timestamp: Event timestamp (defaults to now)
        groups: Group associations (e.g., {"organization": "org_123"})

    Returns:
        True if event was queued, False otherwise
    """
    if not _ensure_initialized():
        return False

    try:
        import posthog

        user_id = _normalize_user_id(user_id)
        capture_kwargs: Dict[str, Any] = {
            "distinct_id": user_id,
            "properties": properties or {},
        }
        if timestamp:
            capture_kwargs["timestamp"] = timestamp
        if groups:
            capture_kwargs["groups"] = groups

        posthog.capture(event, **capture_kwargs)
        logger.debug(
            "PostHog event tracked",
            event_name=event,
            user_id=user_id,
        )
        return True

    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to track PostHog event: {e}")
        return False


def identify_user(
    user_id: str,
    properties: Optional[Dict[str, Any]] = None,
) -> bool:
    """Set person properties on a user record.

    PostHog v7's module API replaces the old ``identify(distinct_id,
    properties)`` with ``set(distinct_id=..., properties=...)``. The
    semantics are the same: properties are merged into the user record.
    """
    if not _ensure_initialized():
        return False

    try:
        import posthog

        user_id = _normalize_user_id(user_id)
        posthog.set(distinct_id=user_id, properties=properties or {})
        logger.debug("PostHog user identified", user_id=user_id)
        return True

    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to identify PostHog user: {e}")
        return False


def group_identify(
    group_type: str,
    group_key: str,
    properties: Optional[Dict[str, Any]] = None,
) -> bool:
    """Set group-level properties (e.g. organization-level)."""
    if not _ensure_initialized():
        return False

    try:
        import posthog

        posthog.group_identify(
            group_type=group_type,
            group_key=str(group_key),
            properties=properties or {},
        )
        logger.debug(
            "PostHog group identified",
            group_type=group_type,
            group_key=group_key,
        )
        return True

    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to identify PostHog group: {e}")
        return False


def capture_revenue(
    user_id: str,
    amount_usd: float,
    event: str = "revenue",
    properties: Optional[Dict[str, Any]] = None,
    groups: Optional[Dict[str, str]] = None,
) -> bool:
    """Capture a revenue event using PostHog's revenue properties."""
    revenue_properties = {
        "$revenue": amount_usd,
        "revenue": amount_usd,
        "currency": "USD",
        **(properties or {}),
    }
    return track_event(
        user_id=user_id,
        event=event,
        properties=revenue_properties,
        groups=groups,
    )


# =============================================================================
# Billing Events
# =============================================================================


def track_checkout_completed(
    user_id: str,
    organization_id: str,
    checkout_type: str,  # "subscription", "lifetime", "credits"
    amount_usd: float,
    tier: Optional[str] = None,
    stripe_session_id: Optional[str] = None,
) -> bool:
    """Track checkout.session.completed event."""
    properties = {
        "checkout_type": checkout_type,
        "amount_usd": amount_usd,
        "organization_id": str(organization_id),
    }
    if tier:
        properties["tier"] = tier
    if stripe_session_id:
        properties["stripe_session_id"] = stripe_session_id

    capture_revenue(
        user_id=user_id,
        amount_usd=amount_usd,
        event="checkout_completed",
        properties=properties,
        groups={"organization": str(organization_id)},
    )

    return track_event(
        user_id=user_id,
        event="checkout_completed",
        properties=properties,
        groups={"organization": str(organization_id)},
    )


def track_subscription_created(
    user_id: str,
    organization_id: str,
    tier: str,
    amount_usd: float,
    stripe_subscription_id: Optional[str] = None,
    is_lifetime: bool = False,
) -> bool:
    """Track subscription_created event."""
    properties = {
        "tier": tier,
        "amount_usd": amount_usd,
        "organization_id": str(organization_id),
        "is_lifetime": is_lifetime,
    }
    if stripe_subscription_id:
        properties["stripe_subscription_id"] = stripe_subscription_id

    group_identify(
        group_type="organization",
        group_key=str(organization_id),
        properties={
            "subscription_tier": tier,
            "is_lifetime": is_lifetime,
        },
    )

    return track_event(
        user_id=user_id,
        event="subscription_created",
        properties=properties,
        groups={"organization": str(organization_id)},
    )


def track_subscription_canceled(
    user_id: str,
    organization_id: str,
    tier: str,
    reason: Optional[str] = None,
    at_period_end: bool = True,
) -> bool:
    """Track subscription_canceled event."""
    properties = {
        "tier": tier,
        "organization_id": str(organization_id),
        "at_period_end": at_period_end,
    }
    if reason:
        properties["reason"] = reason

    return track_event(
        user_id=user_id,
        event="subscription_canceled",
        properties=properties,
        groups={"organization": str(organization_id)},
    )


def track_subscription_updated(
    user_id: str,
    organization_id: str,
    old_tier: str,
    new_tier: str,
    old_amount_usd: float,
    new_amount_usd: float,
) -> bool:
    """Track subscription_updated event (upgrade/downgrade)."""
    is_upgrade = new_amount_usd > old_amount_usd
    properties = {
        "old_tier": old_tier,
        "new_tier": new_tier,
        "old_amount_usd": old_amount_usd,
        "new_amount_usd": new_amount_usd,
        "organization_id": str(organization_id),
        "change_type": "upgrade" if is_upgrade else "downgrade",
        "mrr_change": new_amount_usd - old_amount_usd,
    }

    group_identify(
        group_type="organization",
        group_key=str(organization_id),
        properties={"subscription_tier": new_tier},
    )

    return track_event(
        user_id=user_id,
        event="subscription_updated",
        properties=properties,
        groups={"organization": str(organization_id)},
    )


def track_payment_failed(
    user_id: str,
    organization_id: str,
    amount_usd: float,
    failure_reason: Optional[str] = None,
    attempt_number: int = 1,
) -> bool:
    """Track payment_failed event."""
    properties = {
        "amount_usd": amount_usd,
        "organization_id": str(organization_id),
        "attempt_number": attempt_number,
    }
    if failure_reason:
        properties["failure_reason"] = failure_reason

    return track_event(
        user_id=user_id,
        event="payment_failed",
        properties=properties,
        groups={"organization": str(organization_id)},
    )


def track_payment_succeeded(
    user_id: str,
    organization_id: str,
    amount_usd: float,
    payment_type: str = "subscription",  # subscription, one_time, credits
) -> bool:
    """Track payment_succeeded event."""
    properties = {
        "amount_usd": amount_usd,
        "organization_id": str(organization_id),
        "payment_type": payment_type,
    }

    capture_revenue(
        user_id=user_id,
        amount_usd=amount_usd,
        event="payment_succeeded",
        properties=properties,
        groups={"organization": str(organization_id)},
    )

    return track_event(
        user_id=user_id,
        event="payment_succeeded",
        properties=properties,
        groups={"organization": str(organization_id)},
    )


# =============================================================================
# Workflow Events
# =============================================================================


def track_workflow_started(
    user_id: str,
    organization_id: str,
    workflow_id: str,
    workflow_type: Optional[str] = None,
) -> bool:
    """Track workflow_started event."""
    properties = {
        "workflow_id": str(workflow_id),
        "organization_id": str(organization_id),
    }
    if workflow_type:
        properties["workflow_type"] = workflow_type

    return track_event(
        user_id=user_id,
        event="workflow_started",
        properties=properties,
        groups={"organization": str(organization_id)},
    )


def track_workflow_completed(
    user_id: str,
    organization_id: str,
    workflow_id: str,
    duration_seconds: Optional[float] = None,
    tasks_completed: Optional[int] = None,
    cost_usd: Optional[float] = None,
) -> bool:
    """Track workflow_completed event."""
    properties = {
        "workflow_id": str(workflow_id),
        "organization_id": str(organization_id),
    }
    if duration_seconds is not None:
        properties["duration_seconds"] = duration_seconds
    if tasks_completed is not None:
        properties["tasks_completed"] = tasks_completed
    if cost_usd is not None:
        properties["cost_usd"] = cost_usd

    return track_event(
        user_id=user_id,
        event="workflow_completed",
        properties=properties,
        groups={"organization": str(organization_id)},
    )


def track_workflow_failed(
    user_id: str,
    organization_id: str,
    workflow_id: str,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    duration_seconds: Optional[float] = None,
) -> bool:
    """Track workflow_failed event."""
    properties = {
        "workflow_id": str(workflow_id),
        "organization_id": str(organization_id),
    }
    if error_type:
        properties["error_type"] = error_type
    if error_message:
        properties["error_message"] = error_message[:500]
    if duration_seconds is not None:
        properties["duration_seconds"] = duration_seconds

    return track_event(
        user_id=user_id,
        event="workflow_failed",
        properties=properties,
        groups={"organization": str(organization_id)},
    )


# =============================================================================
# User Events
# =============================================================================


def track_user_created(
    user_id: str,
    organization_id: Optional[str] = None,
    signup_method: str = "email",
    referral_source: Optional[str] = None,
) -> bool:
    """Track user_created event."""
    properties: Dict[str, Any] = {"signup_method": signup_method}
    if organization_id:
        properties["organization_id"] = str(organization_id)
    if referral_source:
        properties["referral_source"] = referral_source

    identify_user(
        user_id=user_id,
        properties={
            "signup_method": signup_method,
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    groups: Dict[str, str] = {}
    if organization_id:
        groups["organization"] = str(organization_id)

    return track_event(
        user_id=user_id,
        event="user_created",
        properties=properties,
        groups=groups if groups else None,
    )


def track_user_signed_in(
    user_id: str,
    organization_id: Optional[str] = None,
    method: str = "email",
) -> bool:
    """Track user_signed_in event."""
    properties: Dict[str, Any] = {"method": method}
    if organization_id:
        properties["organization_id"] = str(organization_id)

    groups: Dict[str, str] = {}
    if organization_id:
        groups["organization"] = str(organization_id)

    return track_event(
        user_id=user_id,
        event="user_signed_in",
        properties=properties,
        groups=groups if groups else None,
    )


__all__ = [
    # Core functions
    "init_posthog",
    "shutdown_posthog",
    "track_event",
    "identify_user",
    "group_identify",
    "capture_revenue",
    "get_posthog_client",
    # Billing events
    "track_checkout_completed",
    "track_subscription_created",
    "track_subscription_canceled",
    "track_subscription_updated",
    "track_payment_failed",
    "track_payment_succeeded",
    # Workflow events
    "track_workflow_started",
    "track_workflow_completed",
    "track_workflow_failed",
    # User events
    "track_user_created",
    "track_user_signed_in",
]
