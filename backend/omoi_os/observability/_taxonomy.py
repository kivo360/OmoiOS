"""Event name constants grouped by product domain.

Five domains, each with a routing table that the facade reads to decide
which sinks an event fans out to. Adding a new event:

    1. Pick the right ``Domain``.
    2. Add a constant: ``EVENT_FOO_BAR = "foo_bar"``.
    3. Append to the matching domain's tuple in ``EVENTS_BY_DOMAIN``.

Reference: docs/architecture/observability_unified.md (§ Five-domain event taxonomy)
"""

from __future__ import annotations

import enum


class Domain(str, enum.Enum):
    DEVELOPMENT = "development"
    INFRASTRUCTURE = "infrastructure"
    PRODUCT = "product"
    USERS = "users"
    MARKETING = "marketing"


class Sink(str, enum.Enum):
    POSTHOG = "posthog"
    BETTERSTACK_TELEMETRY = "betterstack_telemetry"
    BETTERSTACK_ERRORS = "betterstack_errors"
    BETTERSTACK_UPTIME = "betterstack_uptime"


# ---------------------------------------------------------------------------
# Domain → sink routing
# ---------------------------------------------------------------------------

DOMAIN_SINKS: dict[Domain, tuple[Sink, ...]] = {
    Domain.DEVELOPMENT: (Sink.BETTERSTACK_ERRORS, Sink.BETTERSTACK_TELEMETRY),
    Domain.INFRASTRUCTURE: (Sink.BETTERSTACK_TELEMETRY, Sink.BETTERSTACK_UPTIME),
    Domain.PRODUCT: (Sink.POSTHOG, Sink.BETTERSTACK_TELEMETRY),
    Domain.USERS: (Sink.POSTHOG,),
    Domain.MARKETING: (Sink.POSTHOG, Sink.BETTERSTACK_TELEMETRY),
}


# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

EVENT_UNHANDLED_EXCEPTION = "unhandled_exception"
EVENT_DEPLOY_STARTED = "deploy_started"
EVENT_DEPLOY_COMPLETED = "deploy_completed"
EVENT_RELEASE_HEALTH = "release_health"
EVENT_SLOW_QUERY = "slow_query"


# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

EVENT_QUEUE_DEPTH = "queue_depth"
EVENT_AGENT_HEARTBEAT = "agent_heartbeat"
EVENT_AGENT_HEALTH = "agent_health"
EVENT_DB_POOL_EXHAUSTED = "db_pool_exhausted"
EVENT_CRON_COMPLETED = "cron_completed"
EVENT_CRON_FAILED = "cron_failed"
EVENT_LLM_TOKEN_USAGE = "llm_token_usage"


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

EVENT_FEATURE_USED = "feature_used"
EVENT_SPEC_PHASE_ADVANCED = "spec_phase_advanced"
EVENT_SPEC_CREATED = "spec_created"
EVENT_AGENT_INTERVENTION = "agent_intervention"
EVENT_TASK_COMPLETED = "task_completed"
EVENT_TASK_FAILED = "task_failed"
EVENT_TASK_RETRIED = "task_retried"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

EVENT_USER_SIGNUP = "user_signup"
EVENT_USER_LOGIN = "user_login"
EVENT_USER_LOGOUT = "user_logout"
EVENT_USER_IDENTIFIED = "user_identified"
EVENT_SESSION_STARTED = "session_started"


# ---------------------------------------------------------------------------
# Marketing
# ---------------------------------------------------------------------------

EVENT_SIGNUP_COMPLETED = "signup_completed"
EVENT_CHECKOUT_STARTED = "checkout_started"
EVENT_CHECKOUT_COMPLETED = "checkout_completed"
EVENT_SUBSCRIPTION_CREATED = "subscription_created"
EVENT_SUBSCRIPTION_UPDATED = "subscription_updated"
EVENT_SUBSCRIPTION_CANCELED = "subscription_canceled"
EVENT_PAYMENT_SUCCEEDED = "payment_succeeded"
EVENT_PAYMENT_FAILED = "payment_failed"


EVENTS_BY_DOMAIN: dict[Domain, tuple[str, ...]] = {
    Domain.DEVELOPMENT: (
        EVENT_UNHANDLED_EXCEPTION,
        EVENT_DEPLOY_STARTED,
        EVENT_DEPLOY_COMPLETED,
        EVENT_RELEASE_HEALTH,
        EVENT_SLOW_QUERY,
    ),
    Domain.INFRASTRUCTURE: (
        EVENT_QUEUE_DEPTH,
        EVENT_AGENT_HEARTBEAT,
        EVENT_AGENT_HEALTH,
        EVENT_DB_POOL_EXHAUSTED,
        EVENT_CRON_COMPLETED,
        EVENT_CRON_FAILED,
        EVENT_LLM_TOKEN_USAGE,
    ),
    Domain.PRODUCT: (
        EVENT_FEATURE_USED,
        EVENT_SPEC_PHASE_ADVANCED,
        EVENT_SPEC_CREATED,
        EVENT_AGENT_INTERVENTION,
        EVENT_TASK_COMPLETED,
        EVENT_TASK_FAILED,
        EVENT_TASK_RETRIED,
    ),
    Domain.USERS: (
        EVENT_USER_SIGNUP,
        EVENT_USER_LOGIN,
        EVENT_USER_LOGOUT,
        EVENT_USER_IDENTIFIED,
        EVENT_SESSION_STARTED,
    ),
    Domain.MARKETING: (
        EVENT_SIGNUP_COMPLETED,
        EVENT_CHECKOUT_STARTED,
        EVENT_CHECKOUT_COMPLETED,
        EVENT_SUBSCRIPTION_CREATED,
        EVENT_SUBSCRIPTION_UPDATED,
        EVENT_SUBSCRIPTION_CANCELED,
        EVENT_PAYMENT_SUCCEEDED,
        EVENT_PAYMENT_FAILED,
    ),
}


# Reverse lookup: event name → domain
EVENT_TO_DOMAIN: dict[str, Domain] = {
    name: domain for domain, names in EVENTS_BY_DOMAIN.items() for name in names
}


def domain_for(event_name: str) -> Domain:
    """Return the domain owning ``event_name``. Defaults to PRODUCT."""
    return EVENT_TO_DOMAIN.get(event_name, Domain.PRODUCT)


def sinks_for(event_name: str) -> tuple[Sink, ...]:
    """Return the sinks that ``event_name`` should fan out to."""
    return DOMAIN_SINKS[domain_for(event_name)]
