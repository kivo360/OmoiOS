# Server-Side Event Tracking

This document describes the PostHog server-side analytics integration for tracking billing and critical backend events.

## Overview

PostHog is integrated for server-side event tracking to ensure critical events are accurately captured even if the frontend fails to track them. This is especially important for:

- **Billing Events**: Stripe webhook events that affect revenue
- **Subscription Lifecycle**: Creation, updates, cancellation
- **Payment Events**: Successful payments and failures
- **Workflow Events**: Backend job completion tracking

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTHOG_API_KEY` | PostHog project API key (required) | None |
| `POSTHOG_HOST` | PostHog host URL | https://app.posthog.com |
| `POSTHOG_DEBUG` | Enable debug logging | false |
| `POSTHOG_DISABLED` | Disable all tracking | false |

### Example Configuration

```bash
# Production
export POSTHOG_API_KEY="phc_xxx"
export POSTHOG_HOST="https://app.posthog.com"

# Self-hosted PostHog
export POSTHOG_API_KEY="phc_xxx"
export POSTHOG_HOST="https://posthog.yourdomain.com"

# Development (with debug)
export POSTHOG_API_KEY="phc_xxx"
export POSTHOG_DEBUG="true"
```

## Event Schema

### Billing Events

#### checkout_completed

Fired when a Stripe checkout session completes successfully.

```json
{
  "event": "checkout_completed",
  "distinct_id": "user_123",
  "properties": {
    "checkout_type": "subscription",  // subscription, lifetime, credits
    "amount_usd": 50.00,
    "organization_id": "org_456",
    "tier": "pro",
    "stripe_session_id": "cs_xxx"
  },
  "groups": {
    "organization": "org_456"
  }
}
```

#### subscription_created

Fired when a new subscription is created via Stripe webhook.

```json
{
  "event": "subscription_created",
  "distinct_id": "user_123",
  "properties": {
    "tier": "pro",
    "amount_usd": 50.00,
    "organization_id": "org_456",
    "stripe_subscription_id": "sub_xxx",
    "is_lifetime": false
  }
}
```

#### subscription_updated

Fired when a subscription tier changes (upgrade/downgrade).

```json
{
  "event": "subscription_updated",
  "distinct_id": "user_123",
  "properties": {
    "old_tier": "pro",
    "new_tier": "team",
    "old_amount_usd": 50.00,
    "new_amount_usd": 150.00,
    "organization_id": "org_456",
    "change_type": "upgrade",
    "mrr_change": 100.00
  }
}
```

#### subscription_canceled

Fired when a subscription is canceled.

```json
{
  "event": "subscription_canceled",
  "distinct_id": "user_123",
  "properties": {
    "tier": "pro",
    "organization_id": "org_456",
    "at_period_end": true,
    "reason": "user_requested"  // optional
  }
}
```

#### payment_succeeded

Fired when a payment succeeds.

```json
{
  "event": "payment_succeeded",
  "distinct_id": "user_123",
  "properties": {
    "amount_usd": 50.00,
    "organization_id": "org_456",
    "payment_type": "subscription",  // subscription, one_time, credits
    "$revenue": 50.00,
    "currency": "USD"
  }
}
```

#### payment_failed

Fired when a payment fails.

```json
{
  "event": "payment_failed",
  "distinct_id": "user_123",
  "properties": {
    "amount_usd": 50.00,
    "organization_id": "org_456",
    "failure_reason": "card_declined",
    "attempt_number": 1
  }
}
```

### Workflow Events

#### workflow_started

Fired when a workflow/sandbox begins execution.

```json
{
  "event": "workflow_started",
  "distinct_id": "user_123",
  "properties": {
    "workflow_id": "wf_789",
    "organization_id": "org_456",
    "workflow_type": "code_review"
  }
}
```

#### workflow_completed

Fired when a workflow completes successfully.

```json
{
  "event": "workflow_completed",
  "distinct_id": "user_123",
  "properties": {
    "workflow_id": "wf_789",
    "organization_id": "org_456",
    "duration_seconds": 120.5,
    "tasks_completed": 5,
    "cost_usd": 0.25
  }
}
```

#### workflow_failed

Fired when a workflow fails.

```json
{
  "event": "workflow_failed",
  "distinct_id": "user_123",
  "properties": {
    "workflow_id": "wf_789",
    "organization_id": "org_456",
    "error_type": "TimeoutError",
    "error_message": "Operation timed out after 300s",
    "duration_seconds": 300.0
  }
}
```

### User Events

#### user_created

Fired when a new user account is created.

```json
{
  "event": "user_created",
  "distinct_id": "user_123",
  "properties": {
    "signup_method": "github",
    "organization_id": "org_456",
    "referral_source": "product_hunt"
  }
}
```

#### user_signed_in

Fired when a user signs in.

```json
{
  "event": "user_signed_in",
  "distinct_id": "user_123",
  "properties": {
    "method": "github",
    "organization_id": "org_456"
  }
}
```

## Usage

### Basic Event Tracking

```python
from omoi_os.analytics import track_event, identify_user

# Track a custom event
track_event(
    user_id="user_123",
    event="feature_used",
    properties={"feature": "code_review", "language": "python"}
)

# Identify a user with properties
identify_user(
    user_id="user_123",
    properties={"plan": "pro", "company_size": "small"}
)
```

### Billing Event Helpers

```python
from omoi_os.analytics import (
    track_checkout_completed,
    track_subscription_created,
    track_payment_failed,
)

# After Stripe checkout.session.completed
track_checkout_completed(
    user_id=customer_email,
    organization_id=org_id,
    checkout_type="subscription",
    amount_usd=50.00,
    tier="pro",
    stripe_session_id=session_id,
)

# After subscription creation
track_subscription_created(
    user_id=user_id,
    organization_id=org_id,
    tier="pro",
    amount_usd=50.00,
    stripe_subscription_id=sub_id,
)

# After payment failure
track_payment_failed(
    user_id=user_id,
    organization_id=org_id,
    amount_usd=50.00,
    failure_reason="insufficient_funds",
)
```

### Revenue Tracking

PostHog supports revenue tracking with special properties:

```python
from omoi_os.analytics import capture_revenue

capture_revenue(
    user_id=user_id,
    amount_usd=50.00,
    event="subscription_payment",
    properties={"tier": "pro"}
)
```

### Group Analytics

Track events at the organization level:

```python
from omoi_os.analytics import group_identify, track_event

# Set organization properties
group_identify(
    group_type="organization",
    group_key=org_id,
    properties={
        "subscription_tier": "pro",
        "employee_count": 50,
        "industry": "technology"
    }
)

# Track event with organization group
track_event(
    user_id=user_id,
    event="workflow_completed",
    properties={...},
    groups={"organization": org_id}
)
```

## User ID Consistency

**Important**: The `user_id` (distinct_id) should match between frontend and backend tracking to ensure proper user correlation in PostHog.

Recommended approach:
1. Use the same user ID format: `user_<uuid>` or just the UUID
2. Frontend: Set `posthog.identify(userId)` on login
3. Backend: Use the same ID in `track_event(user_id=...)`

## Adding New Events

When adding new server-side events:

1. Define the event schema in this document
2. Create a helper function in `omoi_os/analytics/posthog.py`
3. Add the function to `__init__.py` exports
4. Document when/where the event should be fired
5. Ensure user_id consistency with frontend

Example helper function:

```python
def track_my_new_event(
    user_id: str,
    organization_id: str,
    custom_property: str,
) -> bool:
    """Track my_new_event event.

    Args:
        user_id: User who triggered the event
        organization_id: Organization context
        custom_property: Description of property

    Returns:
        True if event was tracked
    """
    properties = {
        "custom_property": custom_property,
        "organization_id": str(organization_id),
    }

    return track_event(
        user_id=user_id,
        event="my_new_event",
        properties=properties,
        groups={"organization": str(organization_id)},
    )
```

## Deduplication

Server-side events are designed to complement, not duplicate, frontend tracking:

- **Server-side only**: Billing webhooks, background jobs, API-only actions
- **Frontend preferred**: UI interactions, page views, feature usage
- **Both (for reliability)**: Critical conversions, signup completion

PostHog handles deduplication based on event name + distinct_id + timestamp within a small window.

## Troubleshooting

### Events Not Appearing in PostHog

1. Verify `POSTHOG_API_KEY` is set correctly
2. Enable debug mode with `POSTHOG_DEBUG=true`
3. Check for initialization errors in logs
4. Ensure events are being flushed (happens on shutdown)

### User Correlation Issues

1. Verify distinct_id matches between frontend/backend
2. Check PostHog identify calls on frontend
3. Use PostHog's person merge feature if needed

### Missing Revenue Data

1. Ensure `$revenue` property is set (note the $ prefix)
2. Verify currency is included
3. Check PostHog revenue reports configuration
