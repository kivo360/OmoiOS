"""Webhook API routes for subscription management and delivery tracking.

Provides endpoints for:
- Creating webhook subscriptions
- Listing subscriptions by organization
- Updating/deleting subscriptions
- Triggering test deliveries
- Listing delivery status

All routes are guarded by the webhooks_enabled feature flag.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from omoi_os.config import is_feature_enabled
from omoi_os.logging import get_logger
from omoi_os.services.webhook_service import (
    WebhookService,
    get_webhook_service,
    VALID_EVENT_TYPES,
)

logger = get_logger(__name__)
router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class WebhookSubscriptionCreate(BaseModel):
    """Request model for creating a webhook subscription."""

    url: str = Field(
        ..., min_length=1, max_length=2048, description="Webhook delivery URL"
    )
    events: list[str] = Field(..., description="Event types to subscribe to")
    secret: str = Field(
        ..., min_length=16, max_length=256, description="HMAC-SHA256 signing secret"
    )
    active: bool = Field(default=True, description="Whether subscription is active")

    @field_validator("events")
    @classmethod
    def validate_events(cls, events: list[str]) -> list[str]:
        """Validate that all event types are supported."""
        invalid = [e for e in events if e not in VALID_EVENT_TYPES]
        if invalid:
            raise ValueError(
                f"Invalid event types: {invalid}. Valid: {list(VALID_EVENT_TYPES)}"
            )
        return events


class WebhookSubscriptionUpdate(BaseModel):
    """Request model for updating a webhook subscription."""

    url: Optional[str] = Field(default=None, max_length=2048)
    events: Optional[list[str]] = Field(default=None)
    secret: Optional[str] = Field(default=None, min_length=16, max_length=256)
    active: Optional[bool] = None

    @field_validator("events")
    @classmethod
    def validate_events(cls, events: Optional[list[str]]) -> Optional[list[str]]:
        """Validate that all event types are supported."""
        if events is None:
            return events
        invalid = [e for e in events if e not in VALID_EVENT_TYPES]
        if invalid:
            raise ValueError(
                f"Invalid event types: {invalid}. Valid: {list(VALID_EVENT_TYPES)}"
            )
        return events


class WebhookSubscriptionResponse(BaseModel):
    """Response model for webhook subscription."""

    id: UUID
    org_id: UUID
    url: str
    events: list[str]
    active: bool
    created_at: str
    updated_at: str


class WebhookDeliveryResponse(BaseModel):
    """Response model for webhook delivery."""

    id: UUID
    subscription_id: UUID
    event: str
    status: str
    attempts: int
    next_retry_at: Optional[str]
    response_status: Optional[int]
    delivered_at: Optional[str]
    created_at: str
    updated_at: str


class WebhookTestRequest(BaseModel):
    """Request model for triggering a test webhook delivery."""

    event: str = Field(..., description="Event type to test")
    payload: dict = Field(default_factory=dict, description="Test payload")

    @field_validator("event")
    @classmethod
    def validate_event(cls, event: str) -> str:
        """Validate that event type is supported."""
        if event not in VALID_EVENT_TYPES:
            raise ValueError(
                f"Invalid event type: {event}. Valid: {list(VALID_EVENT_TYPES)}"
            )
        return event


# ============================================================================
# Helpers
# ============================================================================


def check_feature_flag() -> None:
    """Check if webhooks feature is enabled.

    Raises:
        HTTPException: 404 if feature flag is disabled
    """
    if not is_feature_enabled("webhooks_enabled"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhooks API not available",
        )


def get_service() -> WebhookService:
    """Get webhook service instance."""
    return get_webhook_service()


def _subscription_to_dict(sub) -> dict:
    """Convert subscription model to dict."""
    return {
        "id": sub.id,
        "org_id": sub.org_id,
        "url": sub.url,
        "events": sub.events,
        "active": sub.active,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
        "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
    }


def _delivery_to_dict(delivery) -> dict:
    """Convert delivery model to dict."""
    return {
        "id": delivery.id,
        "subscription_id": delivery.subscription_id,
        "event": delivery.event,
        "status": delivery.status,
        "attempts": delivery.attempts,
        "next_retry_at": delivery.next_retry_at.isoformat()
        if delivery.next_retry_at
        else None,
        "response_status": delivery.response_status,
        "delivered_at": delivery.delivered_at.isoformat()
        if delivery.delivered_at
        else None,
        "created_at": delivery.created_at.isoformat() if delivery.created_at else None,
        "updated_at": delivery.updated_at.isoformat() if delivery.updated_at else None,
    }


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/subscriptions", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    org_id: UUID = Query(..., description="Organization ID"),
    request: WebhookSubscriptionCreate = ...,
) -> dict:
    """Create a new webhook subscription.

    Args:
        org_id: Organization that owns the subscription
        request: Subscription configuration

    Returns:
        Created subscription metadata with 201 status

    Raises:
        HTTPException: 404 if feature disabled, 400 if creation fails
    """
    check_feature_flag()

    try:
        service = get_service()
        subscription = service.create_subscription(
            org_id=org_id,
            url=request.url,
            events=request.events,
            secret=request.secret,
        )

        logger.info(
            "Webhook subscription created",
            subscription_id=str(subscription.id),
            org_id=str(org_id),
            url=request.url,
            events=request.events,
        )

        return _subscription_to_dict(subscription)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create webhook subscription", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create subscription: {str(e)}",
        )


@router.get("/subscriptions")
async def list_subscriptions(
    org_id: UUID = Query(..., description="Organization ID"),
    active_only: bool = Query(True, description="Only return active subscriptions"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    """List webhook subscriptions for an organization.

    Args:
        org_id: Organization to filter by
        active_only: Whether to filter to active subscriptions only
        limit: Maximum results
        offset: Results to skip

    Returns:
        List of subscription metadata
    """
    check_feature_flag()

    try:
        service = get_service()
        subscriptions = service.list_subscriptions(
            org_id=org_id,
            active_only=active_only,
            limit=limit,
            offset=offset,
        )

        return [_subscription_to_dict(sub) for sub in subscriptions]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to list webhook subscriptions", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to list subscriptions: {str(e)}",
        )


@router.get("/subscriptions/{subscription_id}")
async def get_subscription(
    subscription_id: UUID,
) -> dict:
    """Get a webhook subscription by ID.

    Args:
        subscription_id: Subscription ID

    Returns:
        Subscription metadata

    Raises:
        HTTPException: 404 if not found
    """
    check_feature_flag()

    try:
        service = get_service()
        subscription = service.get_subscription(subscription_id)

        if subscription is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )

        return _subscription_to_dict(subscription)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get webhook subscription", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get subscription: {str(e)}",
        )


@router.patch("/subscriptions/{subscription_id}")
async def update_subscription(
    subscription_id: UUID,
    request: WebhookSubscriptionUpdate = ...,
) -> dict:
    """Update a webhook subscription.

    Args:
        subscription_id: Subscription ID
        request: Fields to update

    Returns:
        Updated subscription metadata

    Raises:
        HTTPException: 404 if not found
    """
    check_feature_flag()

    try:
        service = get_service()

        # Build update dict with only provided fields
        updates = {}
        if request.url is not None:
            updates["url"] = request.url
        if request.events is not None:
            updates["events"] = request.events
        if request.secret is not None:
            updates["secret"] = request.secret
        if request.active is not None:
            updates["active"] = request.active

        subscription = service.update_subscription(subscription_id, **updates)

        if subscription is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )

        logger.info(
            "Webhook subscription updated",
            subscription_id=str(subscription_id),
            updates=list(updates.keys()),
        )

        return _subscription_to_dict(subscription)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update webhook subscription", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update subscription: {str(e)}",
        )


@router.delete(
    "/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_subscription(
    subscription_id: UUID,
) -> None:
    """Delete a webhook subscription.

    Args:
        subscription_id: Subscription ID

    Raises:
        HTTPException: 404 if not found
    """
    check_feature_flag()

    try:
        service = get_service()
        deleted = service.delete_subscription(subscription_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )

        logger.info(
            "Webhook subscription deleted",
            subscription_id=str(subscription_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete webhook subscription", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete subscription: {str(e)}",
        )


@router.post("/subscriptions/{subscription_id}/test")
async def test_subscription(
    subscription_id: UUID,
    request: WebhookTestRequest = ...,
) -> dict:
    """Trigger a test webhook delivery.

    Args:
        subscription_id: Subscription ID
        request: Test event and payload

    Returns:
        Delivery result
    """
    check_feature_flag()

    try:
        service = get_service()
        success = await service.deliver_to_subscription(
            subscription_id=subscription_id,
            event=request.event,
            payload_data=request.payload,
        )

        return {
            "subscription_id": str(subscription_id),
            "event": request.event,
            "success": success,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to test webhook delivery", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Test delivery failed: {str(e)}",
        )


@router.get("/subscriptions/{subscription_id}/deliveries")
async def list_deliveries(
    subscription_id: UUID,
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    """List deliveries for a subscription.

    Args:
        subscription_id: Subscription ID
        status_filter: Optional status filter
        limit: Maximum results
        offset: Results to skip

    Returns:
        List of delivery metadata
    """
    check_feature_flag()

    try:
        service = get_service()
        deliveries = service.list_deliveries(
            subscription_id=subscription_id,
            status=status_filter,
            limit=limit,
            offset=offset,
        )

        return [_delivery_to_dict(d) for d in deliveries]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list webhook deliveries", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to list deliveries: {str(e)}",
        )
