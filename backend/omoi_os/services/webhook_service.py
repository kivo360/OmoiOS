"""Webhook delivery service with at-least-once delivery guarantees.

Provides:
- Webhook subscription CRUD
- HMAC-SHA256 payload signing
- Exponential backoff retry (max 24 hours)
- Replay attack prevention via timestamp validation
- Delivery attempt audit logging
"""

from __future__ import annotations

import hashlib
import hmac
import random
import time
import urllib.parse
from datetime import timedelta
from typing import Optional
from uuid import UUID, uuid4

from omoi_os.config import get_app_settings
from omoi_os.logging import get_logger
from omoi_os.models.webhook import (
    WebhookDelivery,
    WebhookDeliveryAttempt,
    WebhookDeliveryStatus,
    WebhookSubscription,
)
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)

MAX_RETRY_ATTEMPTS = 20
MAX_BACKOFF_SECONDS = 24 * 60 * 60  # 24 hours
REPLAY_WINDOW_SECONDS = 300  # 5 minutes
VALID_EVENT_TYPES = frozenset(
    {
        "spec.created",
        "task.started",
        "task.completed",
        "session.created",
        "artifact.uploaded",
    }
)
MAX_EVENTS_PER_SUBSCRIPTION = 5


class WebhookSubscriptionError(Exception):
    """Raised when webhook subscription operations fail."""

    pass


class WebhookDeliveryError(Exception):
    """Raised when webhook delivery operations fail."""

    pass


class WebhookService:
    """Service for managing webhook subscriptions and deliveries.

    Provides at-least-once delivery with:
    - HMAC-SHA256 payload signing
    - Exponential backoff retry
    - Replay attack prevention
    - Delivery audit logging
    """

    def __init__(self, db: Optional[DatabaseService] = None):
        """Initialize webhook service.

        Args:
            db: Database service (optional, for testing)
        """
        self._db = db
        self.max_delivery_attempts = MAX_RETRY_ATTEMPTS
        self.max_backoff_seconds = MAX_BACKOFF_SECONDS
        self.replay_window_seconds = REPLAY_WINDOW_SECONDS
        self.valid_events = VALID_EVENT_TYPES

    def _get_db(self) -> DatabaseService:
        """Get database service, initializing if needed."""
        if self._db is None:
            from omoi_os.services.database import DatabaseService

            settings = get_app_settings()
            self._db = DatabaseService(connection_string=settings.database.url)
        return self._db

    # ========================================================================
    # Subscription CRUD
    # ========================================================================

    def create_subscription(
        self,
        org_id: UUID,
        url: str,
        events: list[str],
        secret: str,
    ) -> WebhookSubscription:
        """Create a new webhook subscription.

        Args:
            org_id: Organization ID
            url: Webhook delivery URL
            events: List of event types to subscribe to
            secret: HMAC-SHA256 signing secret

        Returns:
            Created subscription

        Raises:
            WebhookSubscriptionError: If validation fails
        """
        self._validate_url(url)
        self._validate_events(events)

        db = self._get_db()
        with db.get_session() as session:
            subscription = WebhookSubscription(
                id=uuid4(),
                org_id=org_id,
                url=url,
                events=events,
                secret=secret,
                active=True,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(subscription)
            session.commit()
            session.refresh(subscription)
            session.expunge(subscription)

            logger.info(
                "Webhook subscription created",
                subscription_id=str(subscription.id),
                org_id=str(org_id),
                url=url,
                events=events,
            )

            return subscription

    def list_subscriptions(
        self,
        org_id: UUID,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WebhookSubscription]:
        """List webhook subscriptions for an organization.

        Args:
            org_id: Organization ID
            active_only: If True, only return active subscriptions
            limit: Maximum results to return (1..1000)
            offset: Number of results to skip

        Returns:
            List of subscriptions
        """
        db = self._get_db()
        with db.get_session() as session:
            query = session.query(WebhookSubscription).filter(
                WebhookSubscription.org_id == org_id
            )
            if active_only:
                query = query.filter(WebhookSubscription.active.is_(True))

            subs = (
                query.order_by(WebhookSubscription.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            for sub in subs:
                session.expunge(sub)
            return subs

    def get_subscription(self, subscription_id: UUID) -> Optional[WebhookSubscription]:
        """Get a subscription by ID.

        Args:
            subscription_id: Subscription ID

        Returns:
            Subscription or None if not found
        """
        db = self._get_db()
        with db.get_session() as session:
            sub = (
                session.query(WebhookSubscription)
                .filter(WebhookSubscription.id == subscription_id)
                .first()
            )
            if sub is not None:
                session.expunge(sub)
            return sub

    def delete_subscription(self, subscription_id: UUID) -> None:
        """Delete a webhook subscription.

        Args:
            subscription_id: Subscription ID to delete

        Raises:
            WebhookSubscriptionError: If subscription not found
        """
        db = self._get_db()
        with db.get_session() as session:
            sub = (
                session.query(WebhookSubscription)
                .filter(WebhookSubscription.id == subscription_id)
                .first()
            )
            if sub is None:
                raise WebhookSubscriptionError(
                    f"Subscription not found: {subscription_id}"
                )

            session.delete(sub)
            session.commit()

            logger.info(
                "Webhook subscription deleted",
                subscription_id=str(subscription_id),
            )

    def update_subscription(
        self,
        subscription_id: UUID,
        url: Optional[str] = None,
        events: Optional[list[str]] = None,
        secret: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> Optional[WebhookSubscription]:
        """Update a webhook subscription.

        Args:
            subscription_id: Subscription ID
            url: New URL (optional)
            events: New event types (optional)
            secret: New secret (optional)
            active: New active status (optional)

        Returns:
            Updated subscription or None if not found
        """
        db = self._get_db()
        with db.get_session() as session:
            sub = (
                session.query(WebhookSubscription)
                .filter(WebhookSubscription.id == subscription_id)
                .first()
            )
            if sub is None:
                return None

            if url is not None:
                self._validate_url(url)
                sub.url = url
            if events is not None:
                self._validate_events(events)
                sub.events = events
            if secret is not None:
                sub.secret = secret
            if active is not None:
                sub.active = active

            sub.updated_at = utc_now()
            session.commit()
            session.refresh(sub)
            session.expunge(sub)

            logger.info(
                "Webhook subscription updated",
                subscription_id=str(subscription_id),
            )

            return sub

    # ========================================================================
    # Validation
    # ========================================================================

    def _validate_url(self, url: str) -> None:
        """Validate webhook URL.

        Args:
            url: URL to validate

        Raises:
            WebhookSubscriptionError: If URL is invalid
        """
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise WebhookSubscriptionError(f"Invalid webhook URL: {url}")
        if parsed.scheme not in ("http", "https"):
            raise WebhookSubscriptionError(f"Webhook URL must use http or https: {url}")

    def _validate_events(self, events: list[str]) -> None:
        """Validate event types.

        Args:
            events: List of event types

        Raises:
            WebhookSubscriptionError: If events are invalid
        """
        if not events:
            raise WebhookSubscriptionError("At least one event type is required")
        if len(events) > MAX_EVENTS_PER_SUBSCRIPTION:
            raise WebhookSubscriptionError(
                f"Maximum {MAX_EVENTS_PER_SUBSCRIPTION} event types allowed, got {len(events)}"
            )
        for event in events:
            if not self._is_valid_event(event):
                raise WebhookSubscriptionError(f"Invalid event type: {event}")

    def _is_valid_event(self, event: str) -> bool:
        """Check if an event type is valid.

        Args:
            event: Event type string

        Returns:
            True if valid
        """
        return event in self.valid_events

    # ========================================================================
    # HMAC Signing
    # ========================================================================

    def _sign_payload(self, secret: str, payload: bytes, timestamp: str) -> str:
        """Sign payload with HMAC-SHA256.

        Args:
            secret: Signing secret
            payload: JSON payload bytes
            timestamp: Unix timestamp string

        Returns:
            Hex-encoded HMAC-SHA256 signature
        """
        signed_payload = f"{timestamp}.".encode() + payload
        return hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()

    def _verify_signature(
        self, secret: str, payload: bytes, timestamp: str, signature: str
    ) -> bool:
        """Verify HMAC-SHA256 signature.

        Args:
            secret: Signing secret
            payload: JSON payload bytes
            timestamp: Unix timestamp string
            signature: Expected signature

        Returns:
            True if signature is valid
        """
        expected = self._sign_payload(secret, payload, timestamp)
        return hmac.compare_digest(expected, signature)

    # ========================================================================
    # Replay Prevention
    # ========================================================================

    def _verify_timestamp(self, timestamp: int) -> bool:
        """Verify timestamp is within acceptable window.

        Args:
            timestamp: Unix timestamp

        Returns:
            True if timestamp is within 5 minutes of now
        """
        now = int(time.time())
        delta = abs(now - timestamp)
        return delta <= self.replay_window_seconds

    # ========================================================================
    # Retry Logic
    # ========================================================================

    def _calculate_backoff(self, attempt: int, jitter: bool = False) -> int:
        """Calculate exponential backoff delay.

        Args:
            attempt: Attempt number (1-indexed)
            jitter: If True, add random jitter

        Returns:
            Delay in seconds
        """
        delay = min(2 ** (attempt - 1), self.max_backoff_seconds)
        if jitter:
            delay = int(delay * (0.5 + random.random()))
        return delay

    def _schedule_retry(self, delivery_id: UUID, attempt: int) -> None:
        """Schedule next retry for a delivery.

        Args:
            delivery_id: Delivery ID
            attempt: Current attempt number
        """
        delay = self._calculate_backoff(attempt, jitter=True)
        next_retry = utc_now() + timedelta(seconds=delay)

        db = self._get_db()
        with db.get_session() as session:
            delivery = (
                session.query(WebhookDelivery)
                .filter(WebhookDelivery.id == delivery_id)
                .first()
            )
            if delivery is not None:
                delivery.next_retry_at = next_retry
                delivery.status = WebhookDeliveryStatus.RETRYING
                session.commit()

                logger.info(
                    "Webhook retry scheduled",
                    delivery_id=str(delivery_id),
                    attempt=attempt,
                    delay=delay,
                    next_retry=next_retry.isoformat(),
                )

    # ========================================================================
    # Delivery
    # ========================================================================

    def get_subscribers_for_event(
        self,
        org_id: UUID,
        event: str,
    ) -> list[WebhookSubscription]:
        """Get active subscriptions for an event type.

        Args:
            org_id: Organization ID
            event: Event type

        Returns:
            List of matching active subscriptions
        """
        db = self._get_db()
        with db.get_session() as session:
            subs = (
                session.query(WebhookSubscription)
                .filter(
                    WebhookSubscription.org_id == org_id,
                    WebhookSubscription.active.is_(True),
                    WebhookSubscription.events.contains([event]),
                )
                .all()
            )
            for sub in subs:
                session.expunge(sub)
            return subs

    def _build_payload(
        self,
        event: str,
        data: dict,
        timestamp: int,
    ) -> dict:
        """Build webhook payload.

        Args:
            event: Event type
            data: Event data
            timestamp: Unix timestamp

        Returns:
            Payload dictionary
        """
        return {
            "webhook_id": str(uuid4()),
            "event": event,
            "timestamp": timestamp,
            "data": data,
        }

    async def _deliver_to_subscription(
        self,
        subscription: WebhookSubscription,
        event: str,
        payload_data: dict,
    ) -> bool:
        """Deliver webhook to a subscription.

        Args:
            subscription: Webhook subscription
            event: Event type
            payload_data: Event payload data

        Returns:
            True if delivery succeeded
        """
        import json

        import httpx

        timestamp = int(time.time())
        payload = self._build_payload(event, payload_data, timestamp)
        # Serialize the exact bytes we'll put on the wire so the HMAC covers
        # the same content the subscriber will verify.
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode()

        signature = self._sign_payload(
            subscription.secret, payload_bytes, str(timestamp)
        )

        # Stripe-style header: receivers reconstruct `<timestamp>.<body>` and
        # verify HMAC over that. Both X-Webhook-Signature and X-Signature are
        # sent so naive consumers that grep for "signature" can find it.
        stripe_sig = f"t={timestamp},v1={signature}"
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": stripe_sig,
            "X-Signature": stripe_sig,
            "X-Webhook-Timestamp": str(timestamp),
            "X-Webhook-Event": event,
            "User-Agent": "OmoiOS-Webhook/1.0",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    subscription.url,
                    content=payload_bytes,
                    headers=headers,
                )

            success = 200 <= response.status_code < 300

            if success:
                logger.info(
                    "Webhook delivered",
                    subscription_id=str(subscription.id),
                    event_type=event,
                    status=response.status_code,
                )
            else:
                logger.warning(
                    "Webhook delivery failed",
                    subscription_id=str(subscription.id),
                    event_type=event,
                    status=response.status_code,
                    response=response.text[:200],
                )

            return success

        except Exception as e:
            logger.error(
                "Webhook delivery error",
                subscription_id=str(subscription.id),
                event_type=event,
                error=str(e),
            )
            return False

    async def trigger_event(
        self,
        org_id: UUID,
        event: str,
        payload_data: dict,
    ) -> list[UUID]:
        """Trigger a webhook event for all matching subscriptions.

        Args:
            org_id: Organization ID
            event: Event type
            payload_data: Event payload data

        Returns:
            List of created delivery IDs
        """
        if not self._is_valid_event(event):
            raise WebhookDeliveryError(f"Invalid event type: {event}")

        subscribers = self.get_subscribers_for_event(org_id, event)
        delivery_ids = []

        for sub in subscribers:
            delivery = self._create_delivery_record(
                subscription_id=sub.id,
                event=event,
                payload=payload_data,
                status=WebhookDeliveryStatus.PENDING,
            )
            delivery_ids.append(delivery.id)

            # Attempt immediate delivery
            success = await self._deliver_to_subscription(sub, event, payload_data)

            if success:
                self._update_delivery_status(
                    delivery.id,
                    WebhookDeliveryStatus.DELIVERED,
                    response_status=200,
                )
            else:
                self._update_delivery_status(
                    delivery.id,
                    WebhookDeliveryStatus.FAILED,
                    response_status=None,
                )
                self._schedule_retry(delivery.id, attempt=1)

        return delivery_ids

    # ========================================================================
    # Delivery Records
    # ========================================================================

    def _create_delivery_record(
        self,
        subscription_id: UUID,
        event: str,
        payload: dict,
        status: str,
    ) -> WebhookDelivery:
        """Create a delivery record.

        Args:
            subscription_id: Subscription ID
            event: Event type
            payload: Payload data
            status: Initial status

        Returns:
            Created delivery record
        """
        db = self._get_db()
        with db.get_session() as session:
            delivery = WebhookDelivery(
                id=uuid4(),
                subscription_id=subscription_id,
                event=event,
                payload=payload,
                status=status,
                attempts=0,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(delivery)
            session.commit()
            session.refresh(delivery)
            session.expunge(delivery)
            return delivery

    def _update_delivery_status(
        self,
        delivery_id: UUID,
        status: str,
        response_status: Optional[int] = None,
        response_body: Optional[str] = None,
    ) -> None:
        """Update delivery status.

        Args:
            delivery_id: Delivery ID
            status: New status
            response_status: HTTP response status
            response_body: HTTP response body
        """
        db = self._get_db()
        with db.get_session() as session:
            delivery = (
                session.query(WebhookDelivery)
                .filter(WebhookDelivery.id == delivery_id)
                .first()
            )
            if delivery is not None:
                delivery.status = status
                delivery.attempts += 1
                delivery.response_status = response_status
                if response_body:
                    delivery.response_body = response_body[:4096]
                if status == WebhookDeliveryStatus.DELIVERED:
                    delivery.delivered_at = utc_now()
                    delivery.next_retry_at = None
                session.commit()

    def get_deliveries(
        self,
        subscription_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WebhookDelivery]:
        """Get delivery records for a subscription.

        Args:
            subscription_id: Subscription ID
            limit: Maximum results
            offset: Results to skip

        Returns:
            List of delivery records
        """
        db = self._get_db()
        with db.get_session() as session:
            deliveries = (
                session.query(WebhookDelivery)
                .filter(WebhookDelivery.subscription_id == subscription_id)
                .order_by(WebhookDelivery.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            for d in deliveries:
                session.expunge(d)
            return deliveries

    # ========================================================================
    # Audit Logging
    # ========================================================================

    def _log_delivery_attempt(
        self,
        delivery_id: UUID,
        attempt_number: int,
        response_status: Optional[int] = None,
        response_body: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Log a delivery attempt.

        Args:
            delivery_id: Delivery ID
            attempt_number: Attempt number
            response_status: HTTP response status
            response_body: HTTP response body
            error_message: Error message if failed
        """
        db = self._get_db()
        with db.get_session() as session:
            attempt = WebhookDeliveryAttempt(
                id=uuid4(),
                delivery_id=delivery_id,
                attempt_number=attempt_number,
                response_status=response_status,
                response_body=response_body[:4096] if response_body else None,
                error_message=error_message[:1024] if error_message else None,
                created_at=utc_now(),
            )
            session.add(attempt)
            session.commit()

            logger.info(
                "Webhook delivery attempt logged",
                delivery_id=str(delivery_id),
                attempt=attempt_number,
                status=response_status,
            )


# Global singleton instance
_webhook_service: Optional[WebhookService] = None


def get_webhook_service() -> WebhookService:
    """Get the global webhook service instance.

    Returns:
        WebhookService instance
    """
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService()
    return _webhook_service


def reset_webhook_service() -> None:
    """Reset the global webhook service instance.

    Useful for testing to ensure clean state.
    """
    global _webhook_service
    _webhook_service = None
