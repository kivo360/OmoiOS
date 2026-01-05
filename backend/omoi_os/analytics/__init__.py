"""Analytics infrastructure for server-side event tracking.

This module provides:
- PostHog integration for product analytics
- Event tracking for billing and critical backend events
- User identification and property tracking

Usage:
    from omoi_os.analytics import track_event, identify_user

    # Track an event
    track_event(
        user_id="user_123",
        event="workflow_completed",
        properties={"workflow_id": "abc", "duration_seconds": 120}
    )

    # Identify a user with properties
    identify_user(
        user_id="user_123",
        properties={"plan": "pro", "company": "Acme Inc"}
    )
"""

from omoi_os.analytics.posthog import (
    init_posthog,
    shutdown_posthog,
    track_event,
    identify_user,
    group_identify,
    capture_revenue,
    get_posthog_client,
    # Billing events
    track_checkout_completed,
    track_subscription_created,
    track_subscription_canceled,
    track_subscription_updated,
    track_payment_failed,
    track_payment_succeeded,
    # Workflow events
    track_workflow_started,
    track_workflow_completed,
    track_workflow_failed,
    # User events
    track_user_created,
    track_user_signed_in,
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
