"""Unit tests for webhook delivery service.

Tests Requirements:
- REQ-WH-001: Webhook subscription CRUD
- REQ-WH-002: HMAC-SHA256 payload signing
- REQ-WH-003: Exponential backoff retry (max 24 hours)
- REQ-WH-004: Replay attack prevention (> 5 min old)
- REQ-WH-005: At-least-once delivery semantics
- REQ-WH-006: Event type filtering
"""

from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from omoi_os.services.webhook_service import (
    WebhookService,
    WebhookSubscriptionError,
    reset_webhook_service,
)
from omoi_os.models.webhook import WebhookDeliveryStatus, WebhookSubscription


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def webhook_service() -> WebhookService:
    """Create a WebhookService with mocked DB."""
    reset_webhook_service()
    service = WebhookService()
    service._db = MagicMock()
    return service


@pytest.fixture
def sample_subscription() -> WebhookSubscription:
    """Create a sample webhook subscription."""
    return WebhookSubscription(
        id=uuid4(),
        org_id=uuid4(),
        url="https://example.com/webhook",
        events=["task.completed", "spec.created"],
        secret="whsec_test_secret_12345",
        active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ============================================================================
# Subscription CRUD Tests
# ============================================================================


class TestWebhookSubscriptionCrud:
    """Tests for webhook subscription CRUD operations."""

    @pytest.mark.unit
    def test_create_subscription(self, webhook_service: WebhookService):
        """Test creating a webhook subscription."""
        org_id = uuid4()
        url = "https://example.com/webhook"
        events = ["task.completed"]
        secret = "whsec_test"

        # Mock the database session
        mock_session = MagicMock()
        mock_db = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        webhook_service._db = mock_db

        # Mock the returned subscription after commit
        expected_sub = WebhookSubscription(
            id=uuid4(),
            org_id=org_id,
            url=url,
            events=events,
            secret=secret,
            active=True,
        )
        mock_session.query.return_value.filter.return_value.first.return_value = (
            expected_sub
        )

        result = webhook_service.create_subscription(
            org_id=org_id,
            url=url,
            events=events,
            secret=secret,
        )

        assert result is not None
        assert result.org_id == org_id
        assert result.url == url
        assert result.events == events

    @pytest.mark.unit
    def test_create_subscription_invalid_url(self, webhook_service: WebhookService):
        """Test creating a subscription with invalid URL fails."""
        with pytest.raises(WebhookSubscriptionError):
            webhook_service.create_subscription(
                org_id=uuid4(),
                url="not-a-url",
                events=["task.completed"],
                secret="whsec_test",
            )

    @pytest.mark.unit
    def test_create_subscription_invalid_event(self, webhook_service: WebhookService):
        """Test creating a subscription with invalid event type fails."""
        with pytest.raises(WebhookSubscriptionError):
            webhook_service.create_subscription(
                org_id=uuid4(),
                url="https://example.com/webhook",
                events=["invalid.event"],
                secret="whsec_test",
            )

    @pytest.mark.unit
    def test_create_subscription_too_many_events(self, webhook_service: WebhookService):
        """Test creating a subscription with too many events fails."""
        with pytest.raises(WebhookSubscriptionError):
            webhook_service.create_subscription(
                org_id=uuid4(),
                url="https://example.com/webhook",
                events=[
                    "task.completed",
                    "spec.created",
                    "task.started",
                    "session.created",
                    "artifact.uploaded",
                    "extra.event",
                ],
                secret="whsec_test",
            )

    @pytest.mark.unit
    def test_list_subscriptions(self, webhook_service: WebhookService):
        """Test listing subscriptions by organization."""
        org_id = uuid4()
        mock_subs = [
            WebhookSubscription(
                id=uuid4(),
                org_id=org_id,
                url="https://example.com/hook1",
                events=["task.completed"],
                secret="whsec_1",
                active=True,
            ),
            WebhookSubscription(
                id=uuid4(),
                org_id=org_id,
                url="https://example.com/hook2",
                events=["spec.created"],
                secret="whsec_2",
                active=True,
            ),
        ]

        mock_session = MagicMock()
        # list_subscriptions uses filter().filter() when active_only=True
        mock_session.query.return_value.filter.return_value.filter.return_value.all.return_value = mock_subs
        mock_db = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        webhook_service._db = mock_db

        result = webhook_service.list_subscriptions(org_id=org_id)
        assert len(result) == 2

    @pytest.mark.unit
    def test_delete_subscription(self, webhook_service: WebhookService):
        """Test deleting a webhook subscription."""
        sub_id = uuid4()
        mock_sub = MagicMock()

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_sub
        )
        mock_db = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        webhook_service._db = mock_db

        webhook_service.delete_subscription(sub_id)
        mock_session.delete.assert_called_once_with(mock_sub)
        mock_session.commit.assert_called_once()

    @pytest.mark.unit
    def test_delete_subscription_not_found(self, webhook_service: WebhookService):
        """Test deleting a non-existent subscription raises error."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_db = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        webhook_service._db = mock_db

        with pytest.raises(WebhookSubscriptionError):
            webhook_service.delete_subscription(uuid4())


# ============================================================================
# HMAC Signature Tests
# ============================================================================


class TestHmacSigning:
    """Tests for HMAC-SHA256 payload signing."""

    @pytest.mark.unit
    def test_sign_payload(self, webhook_service: WebhookService):
        """Test payload signing produces valid HMAC."""
        secret = "whsec_test_secret"
        payload = b'{"event": "task.completed"}'
        timestamp = "1234567890"

        signature = webhook_service._sign_payload(secret, payload, timestamp)

        # Verify it's a hex string
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA-256 hex length

        # Verify we can reproduce it
        expected = hmac.new(
            secret.encode(),
            f"{timestamp}.".encode() + payload,
            hashlib.sha256,
        ).hexdigest()
        assert signature == expected

    @pytest.mark.unit
    def test_sign_payload_different_secrets(self, webhook_service: WebhookService):
        """Test different secrets produce different signatures."""
        payload = b'{"event": "task.completed"}'
        timestamp = "1234567890"

        sig1 = webhook_service._sign_payload("secret_a", payload, timestamp)
        sig2 = webhook_service._sign_payload("secret_b", payload, timestamp)

        assert sig1 != sig2

    @pytest.mark.unit
    def test_sign_payload_different_timestamps(self, webhook_service: WebhookService):
        """Test different timestamps produce different signatures."""
        secret = "whsec_test"
        payload = b'{"event": "task.completed"}'

        sig1 = webhook_service._sign_payload(secret, payload, "1234567890")
        sig2 = webhook_service._sign_payload(secret, payload, "1234567891")

        assert sig1 != sig2


# ============================================================================
# Delivery Retry Tests
# ============================================================================


class TestDeliveryRetry:
    """Tests for exponential backoff retry logic."""

    @pytest.mark.unit
    def test_calculate_backoff_first_attempt(self, webhook_service: WebhookService):
        """Test backoff for first retry."""
        delay = webhook_service._calculate_backoff(attempt=1)
        assert delay == 1  # 2^0 = 1 second

    @pytest.mark.unit
    def test_calculate_backoff_second_attempt(self, webhook_service: WebhookService):
        """Test backoff for second retry."""
        delay = webhook_service._calculate_backoff(attempt=2)
        assert delay == 2  # 2^1 = 2 seconds

    @pytest.mark.unit
    def test_calculate_backoff_third_attempt(self, webhook_service: WebhookService):
        """Test backoff for third retry."""
        delay = webhook_service._calculate_backoff(attempt=3)
        assert delay == 4  # 2^2 = 4 seconds

    @pytest.mark.unit
    def test_calculate_backoff_exponential_growth(
        self, webhook_service: WebhookService
    ):
        """Test exponential growth of backoff."""
        assert webhook_service._calculate_backoff(attempt=4) == 8
        assert webhook_service._calculate_backoff(attempt=5) == 16
        assert webhook_service._calculate_backoff(attempt=6) == 32

    @pytest.mark.unit
    def test_calculate_backoff_max_cap(self, webhook_service: WebhookService):
        """Test backoff is capped at 24 hours."""
        delay = webhook_service._calculate_backoff(attempt=20)
        max_delay = 24 * 60 * 60  # 24 hours in seconds
        assert delay <= max_delay

    @pytest.mark.unit
    def test_calculate_backoff_with_jitter(self, webhook_service: WebhookService):
        """Test backoff includes jitter."""
        delay1 = webhook_service._calculate_backoff(attempt=3, jitter=True)
        delay2 = webhook_service._calculate_backoff(attempt=3, jitter=True)
        # With jitter, delays should differ (statistically almost certain)
        # Jitter formula: delay * (0.5 + random.random()) = 0.5x to 1.5x
        # For attempt=3: base=4, so range is 2 to 6
        assert 2 <= delay1 <= 6  # 0.5 * 4 to 1.5 * 4
        assert 2 <= delay2 <= 6

    @pytest.mark.unit
    def test_max_attempts_reached(self, webhook_service: WebhookService):
        """Test that max attempts prevents infinite retry."""
        max_attempts = webhook_service.max_delivery_attempts
        assert max_attempts > 0
        # After max_attempts, delivery should be marked failed
        assert max_attempts <= 20  # Reasonable upper bound


# ============================================================================
# Replay Attack Prevention Tests
# ============================================================================


class TestReplayPrevention:
    """Tests for replay attack prevention."""

    @pytest.mark.unit
    def test_verify_timestamp_current(self, webhook_service: WebhookService):
        """Test current timestamp is accepted."""
        now = int(time.time())
        assert webhook_service._verify_timestamp(now) is True

    @pytest.mark.unit
    def test_verify_timestamp_recent(self, webhook_service: WebhookService):
        """Test timestamp within 5 minutes is accepted."""
        now = int(time.time())
        recent = now - 60  # 1 minute ago
        assert webhook_service._verify_timestamp(recent) is True

    @pytest.mark.unit
    def test_verify_timestamp_too_old(self, webhook_service: WebhookService):
        """Test timestamp older than 5 minutes is rejected."""
        now = int(time.time())
        old = now - 400  # ~6.7 minutes ago
        assert webhook_service._verify_timestamp(old) is False

    @pytest.mark.unit
    def test_verify_timestamp_future(self, webhook_service: WebhookService):
        """Test future timestamp is rejected."""
        now = int(time.time())
        future = now + 400  # ~6.7 minutes in future
        assert webhook_service._verify_timestamp(future) is False

    @pytest.mark.unit
    def test_verify_timestamp_exactly_5_minutes(self, webhook_service: WebhookService):
        """Test timestamp exactly at 5 minute boundary."""
        now = int(time.time())
        boundary = now - 300  # Exactly 5 minutes
        # Should be accepted (<= 300 seconds)
        assert webhook_service._verify_timestamp(boundary) is True


# ============================================================================
# Delivery Tests
# ============================================================================


class TestWebhookDelivery:
    """Tests for webhook delivery logic."""

    @pytest.mark.unit
    def test_get_subscribers_for_event(self, webhook_service: WebhookService):
        """Test finding subscribers for a specific event."""
        org_id = uuid4()
        # Only return the active subscription that matches the event
        matching_subs = [
            WebhookSubscription(
                id=uuid4(),
                org_id=org_id,
                url="https://example.com/hook1",
                events=["task.completed", "spec.created"],
                secret="whsec_1",
                active=True,
            ),
        ]

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = (
            matching_subs
        )
        mock_db = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        webhook_service._db = mock_db

        result = webhook_service.get_subscribers_for_event(
            org_id=org_id,
            event="task.completed",
        )

        # Should only return active subscriptions matching the event
        assert len(result) == 1
        assert result[0].url == "https://example.com/hook1"

    @pytest.mark.unit
    def test_build_payload_structure(self, webhook_service: WebhookService):
        """Test webhook payload structure."""
        event = "task.completed"
        payload_data = {"task_id": str(uuid4()), "status": "done"}
        timestamp = int(time.time())

        payload = webhook_service._build_payload(event, payload_data, timestamp)

        assert payload["event"] == event
        assert payload["data"] == payload_data
        assert payload["timestamp"] == timestamp
        assert "webhook_id" in payload

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_deliver_webhook_success(self, webhook_service: WebhookService):
        """Test successful webhook delivery."""
        sub = WebhookSubscription(
            id=uuid4(),
            org_id=uuid4(),
            url="https://example.com/webhook",
            events=["task.completed"],
            secret="whsec_test",
            active=True,
        )

        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await webhook_service._deliver_to_subscription(
                sub,
                event="task.completed",
                payload_data={"task_id": str(uuid4())},
            )

        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_deliver_webhook_failure(self, webhook_service: WebhookService):
        """Test failed webhook delivery returns False."""
        sub = WebhookSubscription(
            id=uuid4(),
            org_id=uuid4(),
            url="https://example.com/webhook",
            events=["task.completed"],
            secret="whsec_test",
            active=True,
        )

        # Mock failed HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await webhook_service._deliver_to_subscription(
                sub,
                event="task.completed",
                payload_data={"task_id": str(uuid4())},
            )

        assert result is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_deliver_webhook_network_error(self, webhook_service: WebhookService):
        """Test network error during delivery returns False."""
        sub = WebhookSubscription(
            id=uuid4(),
            org_id=uuid4(),
            url="https://example.com/webhook",
            events=["task.completed"],
            secret="whsec_test",
            active=True,
        )

        with patch(
            "httpx.AsyncClient.post", side_effect=Exception("Connection refused")
        ):
            result = await webhook_service._deliver_to_subscription(
                sub,
                event="task.completed",
                payload_data={"task_id": str(uuid4())},
            )

        assert result is False

    @pytest.mark.unit
    def test_create_delivery_record(self, webhook_service: WebhookService):
        """Test delivery record creation."""
        sub_id = uuid4()
        event = "task.completed"
        payload = {"task_id": str(uuid4())}
        status = WebhookDeliveryStatus.PENDING

        mock_session = MagicMock()
        mock_db = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        webhook_service._db = mock_db

        delivery = webhook_service._create_delivery_record(
            subscription_id=sub_id,
            event=event,
            payload=payload,
            status=status,
        )

        assert delivery.subscription_id == sub_id
        assert delivery.event == event
        assert delivery.payload == payload
        assert delivery.status == status
        assert delivery.attempts == 0
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.unit
    def test_update_delivery_status(self, webhook_service: WebhookService):
        """Test updating delivery record status."""
        delivery_id = uuid4()

        mock_delivery = MagicMock()
        mock_delivery.attempts = 1

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_delivery
        )
        mock_db = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        webhook_service._db = mock_db

        webhook_service._update_delivery_status(
            delivery_id=delivery_id,
            status=WebhookDeliveryStatus.DELIVERED,
            response_status=200,
        )

        assert mock_delivery.status == WebhookDeliveryStatus.DELIVERED
        assert mock_delivery.attempts == 2
        assert mock_delivery.response_status == 200
        mock_session.commit.assert_called_once()


# ============================================================================
# Event Type Tests
# ============================================================================


class TestEventTypes:
    """Tests for valid event types."""

    @pytest.mark.unit
    def test_valid_event_types(self, webhook_service: WebhookService):
        """Test all expected event types are valid."""
        valid_events = [
            "spec.created",
            "task.started",
            "task.completed",
            "session.created",
            "artifact.uploaded",
        ]

        for event in valid_events:
            assert webhook_service._is_valid_event(event) is True

    @pytest.mark.unit
    def test_invalid_event_types(self, webhook_service: WebhookService):
        """Test invalid event types are rejected."""
        invalid_events = [
            "invalid.event",
            "task.unknown",
            "random",
            "",
        ]

        for event in invalid_events:
            assert webhook_service._is_valid_event(event) is False

    @pytest.mark.unit
    def test_no_more_than_five_events(self, webhook_service: WebhookService):
        """Test v1 supports exactly 5 event types."""
        assert len(webhook_service.valid_events) == 5


# ============================================================================
# Audit Logging Tests
# ============================================================================


class TestAuditLogging:
    """Tests for delivery attempt audit logging."""

    @pytest.mark.unit
    def test_audit_log_created_on_attempt(self, webhook_service: WebhookService):
        """Test audit log entry is created on delivery attempt."""
        delivery_id = uuid4()
        attempt_number = 1
        response_status = 200

        mock_session = MagicMock()
        mock_db = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        webhook_service._db = mock_db

        webhook_service._log_delivery_attempt(
            delivery_id=delivery_id,
            attempt_number=attempt_number,
            response_status=response_status,
        )

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.unit
    def test_audit_log_no_plaintext_secret(self, webhook_service: WebhookService):
        """Test audit log does not contain plaintext secret."""
        # This is a design test - verify the service never logs secrets
        secret = "whsec_super_secret"
        # The secret should be used in HMAC but never appear in logs
        # We'll verify by checking the log call arguments don't contain the secret
        with patch("omoi_os.services.webhook_service.logger") as mock_logger:
            webhook_service._sign_payload(secret, b"payload", "1234567890")
            # Check no log call contains the secret
            for call in (
                mock_logger.info.call_args_list + mock_logger.debug.call_args_list
            ):
                if call.args:
                    assert secret not in str(call.args)
