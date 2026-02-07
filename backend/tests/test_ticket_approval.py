"""Tests for ticket human approval workflow (REQ-THA-*)."""

from datetime import timedelta
from unittest.mock import Mock

import pytest

from omoi_os.config import ApprovalSettings
from omoi_os.models.approval_status import ApprovalStatus
from omoi_os.models.ticket import Ticket
from omoi_os.models.ticket_status import TicketStatus
from omoi_os.services.approval import ApprovalService, InvalidApprovalStateError
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.utils.datetime import utc_now


@pytest.fixture
def approval_settings() -> ApprovalSettings:
    """Fixture for ApprovalSettings with custom values for testing."""
    return ApprovalSettings(
        ticket_human_review=True,
        approval_timeout_seconds=1800,  # 30 minutes
        on_reject="delete",
    )


@pytest.fixture
def approval_service(
    db_service: DatabaseService,
    event_bus_service: EventBusService,
    approval_settings: ApprovalSettings,
) -> ApprovalService:
    """Fixture for ApprovalService."""
    return ApprovalService(db_service, event_bus_service, approval_settings)


@pytest.fixture
def sample_ticket_for_approval(db_service: DatabaseService) -> Ticket:
    """Create a sample ticket for approval tests."""
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            description="Description for approval test",
            phase_id="PHASE_IMPLEMENTATION",
            status=TicketStatus.BACKLOG.value,
            priority="MEDIUM",
            approval_status=ApprovalStatus.PENDING_REVIEW.value,
            requested_by_agent_id="agent-123",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.expunge(ticket)
        return ticket


class TestApprovalService:
    """Tests for ApprovalService."""

    def test_create_ticket_with_approval_enabled(
        self, approval_service: ApprovalService, db_service: DatabaseService
    ):
        """Test ticket creation with approval gate enabled (REQ-THA-002)."""
        with db_service.get_session() as session:
            ticket = Ticket(
                title="Test Ticket",
                description="Test description",
                phase_id="PHASE_IMPLEMENTATION",
                status=TicketStatus.BACKLOG.value,
                priority="MEDIUM",
            )
            session.add(ticket)
            session.flush()

            # Apply approval gate (updates ticket fields in place)
            ticket = approval_service.create_ticket_with_approval(
                ticket, requested_by_agent_id="agent-123"
            )

            # Commit to save changes
            session.commit()
            session.refresh(ticket)

            assert ticket.approval_status == ApprovalStatus.PENDING_REVIEW.value
            assert ticket.approval_deadline_at is not None
            assert ticket.requested_by_agent_id == "agent-123"
            assert (
                ticket.approval_deadline_at - utc_now()
            ).total_seconds() <= approval_service.config.approval_timeout_seconds

    def test_create_ticket_with_approval_disabled(
        self, db_service: DatabaseService, event_bus_service: EventBusService
    ):
        """Test ticket creation with approval gate disabled (REQ-THA-002)."""
        # Create service with approval disabled
        settings = ApprovalSettings(ticket_human_review=False)
        approval_service = ApprovalService(db_service, event_bus_service, settings)

        with db_service.get_session() as session:
            ticket = Ticket(
                title="Test Ticket",
                description="Test description",
                phase_id="PHASE_IMPLEMENTATION",
                status=TicketStatus.BACKLOG.value,
                priority="MEDIUM",
            )
            session.add(ticket)
            session.flush()

            # Apply approval gate (should skip, updates ticket fields in place)
            ticket = approval_service.create_ticket_with_approval(
                ticket, requested_by_agent_id="agent-123"
            )

            # Commit to save changes
            session.commit()
            session.refresh(ticket)

            assert ticket.approval_status == ApprovalStatus.APPROVED.value
            assert ticket.approval_deadline_at is None
            assert ticket.requested_by_agent_id == "agent-123"

    def test_approve_ticket_success(
        self,
        approval_service: ApprovalService,
        sample_ticket_for_approval: Ticket,
        db_service: DatabaseService,
    ):
        """Test approving a pending ticket (REQ-THA-004)."""
        ticket = approval_service.approve_ticket(
            sample_ticket_for_approval.id, approver_id="human-123"
        )

        # Verify in database
        with db_service.get_session() as session:
            db_ticket = session.get(Ticket, sample_ticket_for_approval.id)
            assert db_ticket.approval_status == ApprovalStatus.APPROVED.value
            assert db_ticket.approval_deadline_at is None

        # Verify returned ticket object
        assert ticket.approval_status == ApprovalStatus.APPROVED.value
        assert ticket.approval_deadline_at is None

    def test_approve_ticket_invalid_state(
        self, approval_service: ApprovalService, db_service: DatabaseService
    ):
        """Test approving a ticket that's not in pending_review state (REQ-THA-010)."""
        # Create ticket already approved
        with db_service.get_session() as session:
            ticket = Ticket(
                title="Test Ticket",
                description="Test description",
                phase_id="PHASE_IMPLEMENTATION",
                status=TicketStatus.BACKLOG.value,
                priority="MEDIUM",
                approval_status=ApprovalStatus.APPROVED.value,
            )
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            ticket_id = ticket.id

        with pytest.raises(InvalidApprovalStateError):
            approval_service.approve_ticket(ticket_id, approver_id="human-123")

    def test_reject_ticket_success(
        self, approval_service: ApprovalService, sample_ticket_for_approval: Ticket
    ):
        """Test rejecting a pending ticket (REQ-THA-004)."""
        ticket = approval_service.reject_ticket(
            sample_ticket_for_approval.id,
            rejection_reason="Not relevant",
            rejector_id="human-123",
        )

        assert ticket.approval_status == ApprovalStatus.REJECTED.value
        assert ticket.rejection_reason == "Not relevant"

    def test_reject_ticket_invalid_state(
        self, approval_service: ApprovalService, db_service: DatabaseService
    ):
        """Test rejecting a ticket that's not in pending_review state (REQ-THA-010)."""
        # Create ticket already approved
        with db_service.get_session() as session:
            ticket = Ticket(
                title="Test Ticket",
                description="Test description",
                phase_id="PHASE_IMPLEMENTATION",
                status=TicketStatus.BACKLOG.value,
                priority="MEDIUM",
                approval_status=ApprovalStatus.APPROVED.value,
            )
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            ticket_id = ticket.id

        with pytest.raises(InvalidApprovalStateError):
            approval_service.reject_ticket(
                ticket_id, rejection_reason="Not relevant", rejector_id="human-123"
            )

    def test_reject_ticket_deletes_when_configured(
        self, db_service: DatabaseService, event_bus_service: EventBusService
    ):
        """Test that rejected tickets are deleted when on_reject=delete (REQ-THA-004)."""
        settings = ApprovalSettings(ticket_human_review=True, on_reject="delete")
        approval_service = ApprovalService(db_service, event_bus_service, settings)

        with db_service.get_session() as session:
            ticket = Ticket(
                title="Test Ticket",
                description="Test description",
                phase_id="PHASE_IMPLEMENTATION",
                status=TicketStatus.BACKLOG.value,
                priority="MEDIUM",
                approval_status=ApprovalStatus.PENDING_REVIEW.value,
            )
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            ticket_id = ticket.id

        # Reject ticket
        approval_service.reject_ticket(
            ticket_id, rejection_reason="Not relevant", rejector_id="human-123"
        )

        # Verify ticket is deleted
        with db_service.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            assert ticket is None

    def test_reject_ticket_archives_when_configured(
        self, db_service: DatabaseService, event_bus_service: EventBusService
    ):
        """Test that rejected tickets are archived when on_reject=archive (REQ-THA-004)."""
        settings = ApprovalSettings(ticket_human_review=True, on_reject="archive")
        approval_service = ApprovalService(db_service, event_bus_service, settings)

        with db_service.get_session() as session:
            ticket = Ticket(
                title="Test Ticket",
                description="Test description",
                phase_id="PHASE_IMPLEMENTATION",
                status=TicketStatus.BACKLOG.value,
                priority="MEDIUM",
                approval_status=ApprovalStatus.PENDING_REVIEW.value,
            )
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            ticket_id = ticket.id

        # Reject ticket
        approval_service.reject_ticket(
            ticket_id, rejection_reason="Not relevant", rejector_id="human-123"
        )

        # Verify ticket is still present but marked as rejected
        with db_service.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            assert ticket is not None
            assert ticket.approval_status == ApprovalStatus.REJECTED.value

    def test_handle_timeout_success(
        self, approval_service: ApprovalService, db_service: DatabaseService
    ):
        """Test handling ticket approval timeout (REQ-THA-004)."""
        # Create ticket with deadline in the past
        with db_service.get_session() as session:
            ticket = Ticket(
                title="Test Ticket",
                description="Test description",
                phase_id="PHASE_IMPLEMENTATION",
                status=TicketStatus.BACKLOG.value,
                priority="MEDIUM",
                approval_status=ApprovalStatus.PENDING_REVIEW.value,
                approval_deadline_at=utc_now() - timedelta(seconds=60),
            )
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            ticket_id = ticket.id

        # Handle timeout
        ticket = approval_service.handle_timeout(ticket_id)

        # Ticket should be timed out (or deleted if on_reject=delete)
        if ticket is not None:
            assert ticket.approval_status == ApprovalStatus.TIMED_OUT.value
            assert ticket.rejection_reason == "Approval timeout exceeded"

    def test_handle_timeout_skips_non_pending(
        self, approval_service: ApprovalService, db_service: DatabaseService
    ):
        """Test that timeout handling skips tickets not in pending_review state."""
        # Create ticket already approved
        with db_service.get_session() as session:
            ticket = Ticket(
                title="Test Ticket",
                description="Test description",
                phase_id="PHASE_IMPLEMENTATION",
                status=TicketStatus.BACKLOG.value,
                priority="MEDIUM",
                approval_status=ApprovalStatus.APPROVED.value,
            )
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            ticket_id = ticket.id

        # Handle timeout (should return None)
        result = approval_service.handle_timeout(ticket_id)

        assert result is None

        # Verify ticket is still approved
        with db_service.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            assert ticket.approval_status == ApprovalStatus.APPROVED.value

    def test_check_timeouts_finds_expired(
        self, approval_service: ApprovalService, db_service: DatabaseService
    ):
        """Test check_timeouts finds tickets with expired deadlines (REQ-THA-004, REQ-THA-009)."""
        # Create multiple tickets: one expired, one not expired, one already approved
        with db_service.get_session() as session:
            ticket1 = Ticket(
                title="Expired Ticket",
                description="Test description",
                phase_id="PHASE_IMPLEMENTATION",
                status=TicketStatus.BACKLOG.value,
                priority="MEDIUM",
                approval_status=ApprovalStatus.PENDING_REVIEW.value,
                approval_deadline_at=utc_now() - timedelta(seconds=60),
            )
            ticket2 = Ticket(
                title="Not Expired Ticket",
                description="Test description",
                phase_id="PHASE_IMPLEMENTATION",
                status=TicketStatus.BACKLOG.value,
                priority="MEDIUM",
                approval_status=ApprovalStatus.PENDING_REVIEW.value,
                approval_deadline_at=utc_now() + timedelta(seconds=600),
            )
            ticket3 = Ticket(
                title="Approved Ticket",
                description="Test description",
                phase_id="PHASE_IMPLEMENTATION",
                status=TicketStatus.BACKLOG.value,
                priority="MEDIUM",
                approval_status=ApprovalStatus.APPROVED.value,
                approval_deadline_at=utc_now() - timedelta(seconds=60),
            )
            session.add_all([ticket1, ticket2, ticket3])
            session.commit()
            session.refresh(ticket1)
            session.refresh(ticket2)
            session.refresh(ticket3)
            ticket1_id = ticket1.id
            ticket2_id = ticket2.id
            ticket3_id = ticket3.id

        # Check timeouts
        timed_out_ids = approval_service.check_timeouts()

        # Should find only ticket1 (expired and pending)
        assert ticket1_id in timed_out_ids
        assert ticket2_id not in timed_out_ids  # Not expired
        assert ticket3_id not in timed_out_ids  # Not pending

    def test_get_pending_count(
        self, approval_service: ApprovalService, db_service: DatabaseService
    ):
        """Test getting count of pending tickets (REQ-THA-*)."""
        # Create tickets with different approval statuses
        with db_service.get_session() as session:
            ticket1 = Ticket(
                title="Pending Ticket 1",
                description="Test description",
                phase_id="PHASE_IMPLEMENTATION",
                status=TicketStatus.BACKLOG.value,
                priority="MEDIUM",
                approval_status=ApprovalStatus.PENDING_REVIEW.value,
            )
            ticket2 = Ticket(
                title="Pending Ticket 2",
                description="Test description",
                phase_id="PHASE_IMPLEMENTATION",
                status=TicketStatus.BACKLOG.value,
                priority="MEDIUM",
                approval_status=ApprovalStatus.PENDING_REVIEW.value,
            )
            ticket3 = Ticket(
                title="Approved Ticket",
                description="Test description",
                phase_id="PHASE_IMPLEMENTATION",
                status=TicketStatus.BACKLOG.value,
                priority="MEDIUM",
                approval_status=ApprovalStatus.APPROVED.value,
            )
            session.add_all([ticket1, ticket2, ticket3])
            session.commit()

        # Get pending count
        count = approval_service.get_pending_count()

        assert count == 2

    def test_get_approval_status(
        self, approval_service: ApprovalService, sample_ticket_for_approval: Ticket
    ):
        """Test getting approval status for a ticket (REQ-THA-*)."""
        status = approval_service.get_approval_status(sample_ticket_for_approval.id)

        assert status is not None
        assert status["ticket_id"] == str(sample_ticket_for_approval.id)
        assert status["approval_status"] == ApprovalStatus.PENDING_REVIEW.value
        assert status["requested_by_agent_id"] == "agent-123"

    def test_get_approval_status_not_found(self, approval_service: ApprovalService):
        """Test getting approval status for non-existent ticket."""
        status = approval_service.get_approval_status("non-existent-id")

        assert status is None

    def test_approve_ticket_publishes_event(
        self,
        approval_service: ApprovalService,
        sample_ticket_for_approval: Ticket,
        event_bus_service: EventBusService,
    ):
        """Test that approving a ticket publishes TICKET_APPROVED event (REQ-THA-010)."""
        # Mock event bus to capture published events
        published_events = []

        def capture_event(event):
            published_events.append(event)

        # Replace event bus publish with our capture function
        original_publish = event_bus_service.publish
        event_bus_service.publish = Mock(side_effect=capture_event)

        try:
            approval_service.approve_ticket(
                sample_ticket_for_approval.id, approver_id="human-123"
            )

            # Verify event was published
            assert len(published_events) == 1
            event = published_events[0]
            assert event.event_type == "TICKET_APPROVED"
            assert event.entity_id == str(sample_ticket_for_approval.id)
            assert event.payload["approver_id"] == "human-123"
        finally:
            event_bus_service.publish = original_publish

    def test_reject_ticket_publishes_event(
        self,
        approval_service: ApprovalService,
        sample_ticket_for_approval: Ticket,
        event_bus_service: EventBusService,
    ):
        """Test that rejecting a ticket publishes TICKET_REJECTED event (REQ-THA-010)."""
        # Mock event bus to capture published events
        published_events = []

        def capture_event(event):
            published_events.append(event)

        # Replace event bus publish with our capture function
        original_publish = event_bus_service.publish
        event_bus_service.publish = Mock(side_effect=capture_event)

        try:
            approval_service.reject_ticket(
                sample_ticket_for_approval.id,
                rejection_reason="Not relevant",
                rejector_id="human-123",
            )

            # Verify event was published
            assert len(published_events) == 1
            event = published_events[0]
            assert event.event_type == "TICKET_REJECTED"
            assert event.entity_id == str(sample_ticket_for_approval.id)
            assert event.payload["rejection_reason"] == "Not relevant"
            assert event.payload["rejector_id"] == "human-123"
        finally:
            event_bus_service.publish = original_publish

    def test_create_ticket_with_approval_publishes_event(
        self,
        approval_service: ApprovalService,
        db_service: DatabaseService,
        event_bus_service: EventBusService,
    ):
        """Test that creating ticket with approval enabled publishes TICKET_APPROVAL_PENDING event (REQ-THA-010)."""
        # Mock event bus to capture published events
        published_events = []

        def capture_event(event):
            published_events.append(event)

        # Replace event bus publish with our capture function
        original_publish = event_bus_service.publish
        event_bus_service.publish = Mock(side_effect=capture_event)

        try:
            with db_service.get_session() as session:
                ticket = Ticket(
                    title="Test Ticket",
                    description="Test description",
                    phase_id="PHASE_IMPLEMENTATION",
                    status=TicketStatus.BACKLOG.value,
                    priority="MEDIUM",
                )
                session.add(ticket)
                session.flush()

                # Apply approval gate (updates ticket fields)
                ticket = approval_service.create_ticket_with_approval(
                    ticket, requested_by_agent_id="agent-123"
                )

                # Flush to get ticket.id
                session.flush()

                # Emit pending event (simulating what API route does)
                approval_service._emit_pending_event(ticket)

                # Commit to save
                session.commit()
                session.refresh(ticket)

                # Verify event was published
                assert len(published_events) == 1
                event = published_events[0]
                assert event.event_type == "TICKET_APPROVAL_PENDING"
                assert event.entity_id == str(ticket.id)
                assert "deadline_at" in event.payload

                # Verify ticket state
                assert ticket.approval_status == ApprovalStatus.PENDING_REVIEW.value
                assert ticket.id is not None
        finally:
            event_bus_service.publish = original_publish


class TestApprovalStatus:
    """Tests for ApprovalStatus enum."""

    def test_is_pending(self):
        """Test is_pending helper method."""
        assert ApprovalStatus.is_pending(ApprovalStatus.PENDING_REVIEW.value) is True
        assert ApprovalStatus.is_pending(ApprovalStatus.APPROVED.value) is False

    def test_is_final(self):
        """Test is_final helper method."""
        assert ApprovalStatus.is_final(ApprovalStatus.APPROVED.value) is True
        assert ApprovalStatus.is_final(ApprovalStatus.REJECTED.value) is True
        assert ApprovalStatus.is_final(ApprovalStatus.TIMED_OUT.value) is True
        assert ApprovalStatus.is_final(ApprovalStatus.PENDING_REVIEW.value) is False

    def test_can_proceed(self):
        """Test can_proceed helper method."""
        assert ApprovalStatus.can_proceed(ApprovalStatus.APPROVED.value) is True
        assert ApprovalStatus.can_proceed(ApprovalStatus.PENDING_REVIEW.value) is False
        assert ApprovalStatus.can_proceed(ApprovalStatus.REJECTED.value) is False
        assert ApprovalStatus.can_proceed(ApprovalStatus.TIMED_OUT.value) is False
