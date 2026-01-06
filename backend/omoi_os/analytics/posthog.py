"""PostHog integration for server-side event tracking.

This module provides:
- Server-side event tracking for billing and critical events
- User identification matching frontend distinct_id
- Revenue tracking with PostHog's revenue properties
- Group analytics for organizations

Important: All user_ids should match the distinct_id used in the frontend
to ensure proper user correlation in PostHog.

Usage:
    from omoi_os.analytics.posthog import track_event, identify_user

    # Track an event
    track_event(
        user_id="user_123",
        event="workflow_completed",
        properties={"workflow_id": "abc"}
    )
"""

from __future__ import annotations

import atexit
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from omoi_os.config import get_app_settings
from omoi_os.logging import get_logger

logger = get_logger(__name__)

# Global PostHog client
_posthog_client = None
_posthog_initialized = False


def get_posthog_client():
    """Get the global PostHog client.

    Returns:
        PostHog client or None if not initialized
    """
    return _posthog_client


def init_posthog() -> bool:
    """Initialize the PostHog client.

    Should be called once at application startup.

    Returns:
        True if PostHog was initialized, False if not configured
    """
    global _posthog_client, _posthog_initialized

    if _posthog_initialized:
        logger.debug("PostHog already initialized")
        return _posthog_client is not None

    settings = get_app_settings().posthog

    if not settings.is_configured:
        logger.info("PostHog not configured (POSTHOG_API_KEY not set)")
        _posthog_initialized = True
        return False

    try:
        from posthog import Posthog

        _posthog_client = Posthog(
            project_api_key=settings.api_key,
            host=settings.host,
            debug=settings.debug,
            sync_mode=False,  # Use async batch sending
        )

        # Register shutdown handler to flush events
        atexit.register(shutdown_posthog)

        _posthog_initialized = True
        logger.info(
            "PostHog initialized",
            host=settings.host,
            debug=settings.debug,
        )
        return True

    except Exception as e:
        logger.error(f"Failed to initialize PostHog: {e}")
        _posthog_initialized = True
        return False


def shutdown_posthog() -> None:
    """Shutdown PostHog client and flush pending events.

    Called automatically at application shutdown via atexit.
    """
    global _posthog_client

    if _posthog_client:
        try:
            _posthog_client.shutdown()
            logger.debug("PostHog client shutdown complete")
        except Exception as e:
            logger.warning(f"Error shutting down PostHog: {e}")


def _ensure_initialized() -> bool:
    """Ensure PostHog is initialized.

    Returns:
        True if PostHog is available, False otherwise
    """
    if not _posthog_initialized:
        init_posthog()
    return _posthog_client is not None


def _normalize_user_id(user_id: Any) -> str:
    """Normalize user_id to string format.

    Args:
        user_id: User ID (can be UUID, str, etc.)

    Returns:
        String representation of user ID
    """
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
        user_id = _normalize_user_id(user_id)

        capture_kwargs = {
            "distinct_id": user_id,
            "event": event,
            "properties": properties or {},
        }

        if timestamp:
            capture_kwargs["timestamp"] = timestamp

        if groups:
            capture_kwargs["groups"] = groups

        _posthog_client.capture(**capture_kwargs)

        logger.debug(
            "PostHog event tracked",
            event=event,
            user_id=user_id,
        )
        return True

    except Exception as e:
        logger.warning(f"Failed to track PostHog event: {e}")
        return False


def identify_user(
    user_id: str,
    properties: Optional[Dict[str, Any]] = None,
) -> bool:
    """Identify a user with properties in PostHog.

    Args:
        user_id: Distinct ID for the user
        properties: User properties to set

    Returns:
        True if identify was queued, False otherwise
    """
    if not _ensure_initialized():
        return False

    try:
        user_id = _normalize_user_id(user_id)

        _posthog_client.identify(
            distinct_id=user_id,
            properties=properties or {},
        )

        logger.debug(
            "PostHog user identified",
            user_id=user_id,
        )
        return True

    except Exception as e:
        logger.warning(f"Failed to identify PostHog user: {e}")
        return False


def group_identify(
    group_type: str,
    group_key: str,
    properties: Optional[Dict[str, Any]] = None,
) -> bool:
    """Identify a group with properties in PostHog.

    Use this for organization-level properties.

    Args:
        group_type: Type of group (e.g., "organization", "company")
        group_key: Group identifier
        properties: Group properties to set

    Returns:
        True if group identify was queued, False otherwise
    """
    if not _ensure_initialized():
        return False

    try:
        _posthog_client.group_identify(
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

    except Exception as e:
        logger.warning(f"Failed to identify PostHog group: {e}")
        return False


def capture_revenue(
    user_id: str,
    amount_usd: float,
    event: str = "revenue",
    properties: Optional[Dict[str, Any]] = None,
    groups: Optional[Dict[str, str]] = None,
) -> bool:
    """Capture a revenue event in PostHog.

    Uses PostHog's revenue tracking properties.

    Args:
        user_id: Distinct ID for the user
        amount_usd: Revenue amount in USD
        event: Event name (defaults to "revenue")
        properties: Additional event properties
        groups: Group associations

    Returns:
        True if event was queued, False otherwise
    """
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
    """Track checkout.session.completed event.

    Args:
        user_id: User who completed checkout
        organization_id: Organization associated with checkout
        checkout_type: Type of checkout (subscription, lifetime, credits)
        amount_usd: Amount charged
        tier: Subscription tier if applicable
        stripe_session_id: Stripe checkout session ID

    Returns:
        True if event was tracked
    """
    properties = {
        "checkout_type": checkout_type,
        "amount_usd": amount_usd,
        "organization_id": str(organization_id),
    }

    if tier:
        properties["tier"] = tier
    if stripe_session_id:
        properties["stripe_session_id"] = stripe_session_id

    # Also capture as revenue event
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
    """Track subscription_created event.

    Args:
        user_id: User who created subscription
        organization_id: Organization with new subscription
        tier: Subscription tier (free, pro, team, enterprise)
        amount_usd: Monthly amount
        stripe_subscription_id: Stripe subscription ID
        is_lifetime: Whether this is a lifetime subscription

    Returns:
        True if event was tracked
    """
    properties = {
        "tier": tier,
        "amount_usd": amount_usd,
        "organization_id": str(organization_id),
        "is_lifetime": is_lifetime,
    }

    if stripe_subscription_id:
        properties["stripe_subscription_id"] = stripe_subscription_id

    # Update organization group properties
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
    """Track subscription_canceled event.

    Args:
        user_id: User who canceled
        organization_id: Organization with canceled subscription
        tier: Previous subscription tier
        reason: Cancellation reason if provided
        at_period_end: Whether cancellation is at period end

    Returns:
        True if event was tracked
    """
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
    """Track subscription_updated event (upgrade/downgrade).

    Args:
        user_id: User who made the change
        organization_id: Organization with updated subscription
        old_tier: Previous tier
        new_tier: New tier
        old_amount_usd: Previous monthly amount
        new_amount_usd: New monthly amount

    Returns:
        True if event was tracked
    """
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

    # Update organization group properties
    group_identify(
        group_type="organization",
        group_key=str(organization_id),
        properties={
            "subscription_tier": new_tier,
        },
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
    """Track payment_failed event.

    Args:
        user_id: User associated with failed payment
        organization_id: Organization with failed payment
        amount_usd: Amount that failed to charge
        failure_reason: Reason for failure
        attempt_number: Which payment attempt this was

    Returns:
        True if event was tracked
    """
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
    """Track payment_succeeded event.

    Args:
        user_id: User associated with payment
        organization_id: Organization that made payment
        amount_usd: Amount paid
        payment_type: Type of payment

    Returns:
        True if event was tracked
    """
    properties = {
        "amount_usd": amount_usd,
        "organization_id": str(organization_id),
        "payment_type": payment_type,
    }

    # Capture revenue
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
    """Track workflow_started event.

    Args:
        user_id: User who started the workflow
        organization_id: Organization running the workflow
        workflow_id: Unique workflow/ticket ID
        workflow_type: Type of workflow

    Returns:
        True if event was tracked
    """
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
    """Track workflow_completed event.

    Args:
        user_id: User who ran the workflow
        organization_id: Organization that ran the workflow
        workflow_id: Unique workflow/ticket ID
        duration_seconds: Total workflow duration
        tasks_completed: Number of tasks completed
        cost_usd: Total cost of workflow

    Returns:
        True if event was tracked
    """
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
    """Track workflow_failed event.

    Args:
        user_id: User who ran the workflow
        organization_id: Organization that ran the workflow
        workflow_id: Unique workflow/ticket ID
        error_type: Type of error
        error_message: Error message (will be truncated)
        duration_seconds: Duration before failure

    Returns:
        True if event was tracked
    """
    properties = {
        "workflow_id": str(workflow_id),
        "organization_id": str(organization_id),
    }

    if error_type:
        properties["error_type"] = error_type
    if error_message:
        # Truncate error message to avoid PII in long stack traces
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
    """Track user_created event.

    Args:
        user_id: New user's ID
        organization_id: Organization user belongs to
        signup_method: How user signed up (email, github, google)
        referral_source: Where user came from

    Returns:
        True if event was tracked
    """
    properties = {
        "signup_method": signup_method,
    }

    if organization_id:
        properties["organization_id"] = str(organization_id)
    if referral_source:
        properties["referral_source"] = referral_source

    # Identify the user
    identify_user(
        user_id=user_id,
        properties={
            "signup_method": signup_method,
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    groups = {}
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
    """Track user_signed_in event.

    Args:
        user_id: User who signed in
        organization_id: User's organization
        method: Sign-in method (email, github, google)

    Returns:
        True if event was tracked
    """
    properties = {
        "method": method,
    }

    if organization_id:
        properties["organization_id"] = str(organization_id)

    groups = {}
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
