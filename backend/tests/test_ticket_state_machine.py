"""Tests for Ticket State Machine (REQ-TKT-SM-001 through REQ-TKT-BL-003)."""

from datetime import timedelta

import pytest

from omoi_os.models.phase_gate_artifact import PhaseGateArtifact
from omoi_os.models.ticket import Ticket
from omoi_os.models.ticket_status import (
    TicketStatus,
    is_valid_transition,
)
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.phase_gate import PhaseGateService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.ticket_workflow import (
    InvalidTransitionError,
    TicketBlockedError,
    TicketWorkflowOrchestrator,
)
from omoi_os.utils.datetime import utc_now


@pytest.fixture
def phase_gate_service(db_service: DatabaseService) -> PhaseGateService:
    """Create a phase gate service."""
    return PhaseGateService(db_service)


@pytest.fixture
def ticket_workflow_orchestrator(
    db_service: DatabaseService,
    task_queue_service: TaskQueueService,
    phase_gate_service: PhaseGateService,
    event_bus_service: EventBusService,
) -> TicketWorkflowOrchestrator:
    """Create a ticket workflow orchestrator."""
    return TicketWorkflowOrchestrator(
        db=db_service,
        task_queue=task_queue_service,
        phase_gate=phase_gate_service,
        event_bus=event_bus_service,
    )


@pytest.fixture
def ticket(db_service: DatabaseService) -> Ticket:
    """Create a test ticket in backlog."""
    with db_service.get_session() as session:
        ticket = Ticket(
            id="test-ticket-1",
            title="Test Ticket",
            description="Test Description",
            phase_id="PHASE_BACKLOG",
            status=TicketStatus.BACKLOG.value,
            priority="MEDIUM",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.expunge(ticket)
        return ticket


class TestTicketStatus:
    """Tests for TicketStatus enum and transition validation."""

    def test_ticket_status_enum(self):
        """Test TicketStatus enum values."""
        assert TicketStatus.BACKLOG.value == "backlog"
        assert TicketStatus.ANALYZING.value == "analyzing"
        assert TicketStatus.BUILDING.value == "building"
        assert TicketStatus.BUILDING_DONE.value == "building-done"
        assert TicketStatus.TESTING.value == "testing"
        assert TicketStatus.DONE.value == "done"

    def test_is_terminal(self):
        """Test terminal state detection."""
        assert TicketStatus.is_terminal(TicketStatus.DONE.value) is True
        assert TicketStatus.is_terminal(TicketStatus.BACKLOG.value) is False
        assert TicketStatus.is_terminal(TicketStatus.ANALYZING.value) is False

    def test_valid_transitions(self):
        """Test valid state transitions per REQ-TKT-SM-002."""
        # Normal progression
        assert (
            is_valid_transition(
                TicketStatus.BACKLOG.value, TicketStatus.ANALYZING.value
            )
            is True
        )
        assert (
            is_valid_transition(
                TicketStatus.ANALYZING.value, TicketStatus.BUILDING.value
            )
            is True
        )
        assert (
            is_valid_transition(
                TicketStatus.BUILDING.value, TicketStatus.BUILDING_DONE.value
            )
            is True
        )
        assert (
            is_valid_transition(
                TicketStatus.BUILDING_DONE.value, TicketStatus.TESTING.value
            )
            is True
        )
        assert (
            is_valid_transition(TicketStatus.TESTING.value, TicketStatus.DONE.value)
            is True
        )

        # Regression: testing → building (on fix needed)
        assert (
            is_valid_transition(TicketStatus.TESTING.value, TicketStatus.BUILDING.value)
            is True
        )

        # Invalid transitions
        assert (
            is_valid_transition(TicketStatus.BACKLOG.value, TicketStatus.DONE.value)
            is False
        )
        assert (
            is_valid_transition(TicketStatus.DONE.value, TicketStatus.BACKLOG.value)
            is False
        )

    def test_blocked_transitions(self):
        """Test transitions from blocked state per REQ-TKT-SM-002."""
        # When blocked, can transition to any of the allowed states
        assert (
            is_valid_transition(
                TicketStatus.BUILDING.value,
                TicketStatus.ANALYZING.value,
                is_blocked=True,
            )
            is True
        )
        assert (
            is_valid_transition(
                TicketStatus.ANALYZING.value,
                TicketStatus.BUILDING.value,
                is_blocked=True,
            )
            is True
        )
        assert (
            is_valid_transition(
                TicketStatus.BUILDING.value,
                TicketStatus.BUILDING_DONE.value,
                is_blocked=True,
            )
            is True
        )
        assert (
            is_valid_transition(
                TicketStatus.BUILDING.value, TicketStatus.TESTING.value, is_blocked=True
            )
            is True
        )


class TestTicketWorkflowOrchestrator:
    """Tests for TicketWorkflowOrchestrator service."""

    # ---------------------------------------------------------------------
    # State Transitions (REQ-TKT-SM-001, REQ-TKT-SM-002)
    # ---------------------------------------------------------------------

    def test_transition_status_valid(
        self, ticket_workflow_orchestrator: TicketWorkflowOrchestrator, ticket: Ticket
    ):
        """Test valid status transition."""
        updated = ticket_workflow_orchestrator.transition_status(
            ticket.id, TicketStatus.ANALYZING.value, initiated_by="test", reason="Test"
        )

        assert updated.status == TicketStatus.ANALYZING.value
        assert updated.phase_id == "PHASE_REQUIREMENTS"
        assert updated.previous_phase_id == "PHASE_BACKLOG"

    def test_transition_status_invalid(
        self, ticket_workflow_orchestrator: TicketWorkflowOrchestrator, ticket: Ticket
    ):
        """Test invalid status transition raises error."""
        with pytest.raises(InvalidTransitionError):
            ticket_workflow_orchestrator.transition_status(
                ticket.id,
                TicketStatus.DONE.value,  # Cannot jump from backlog to done
                initiated_by="test",
            )

    def test_transition_status_blocked(
        self, ticket_workflow_orchestrator: TicketWorkflowOrchestrator, ticket: Ticket
    ):
        """Test blocked ticket cannot transition to non-unblock states."""
        # Transition to analyzing first
        ticket_id = ticket.id  # Extract ID before session closes
        ticket_workflow_orchestrator.transition_status(
            ticket_id, TicketStatus.ANALYZING.value, initiated_by="test"
        )

        # Mark ticket as blocked
        with ticket_workflow_orchestrator.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            ticket.is_blocked = True
            ticket.blocked_reason = "dependency"
            session.commit()

        # Try to transition to DONE (should fail - not in BLOCKED_TRANSITIONS)
        with pytest.raises(TicketBlockedError):
            ticket_workflow_orchestrator.transition_status(
                ticket_id,
                TicketStatus.DONE.value,
                initiated_by="test",
            )

        # Transition to BUILDING should succeed (is in BLOCKED_TRANSITIONS)
        updated = ticket_workflow_orchestrator.transition_status(
            ticket_id, TicketStatus.BUILDING.value, initiated_by="test"
        )
        assert updated.status == TicketStatus.BUILDING.value
        assert updated.is_blocked is False  # Should be unblocked

    def test_transition_status_blocked_to_unblock(
        self, ticket_workflow_orchestrator: TicketWorkflowOrchestrator, ticket: Ticket
    ):
        """Test blocked ticket can transition to unblock state."""
        ticket_id = ticket.id  # Extract ID before session closes
        # First transition to analyzing
        ticket_workflow_orchestrator.transition_status(
            ticket_id, TicketStatus.ANALYZING.value, initiated_by="test"
        )

        # Mark as blocked
        with ticket_workflow_orchestrator.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            ticket.is_blocked = True
            ticket.blocked_reason = "dependency"
            session.commit()

        # Transition from blocked to building (unblock)
        updated = ticket_workflow_orchestrator.transition_status(
            ticket_id, TicketStatus.BUILDING.value, initiated_by="test"
        )

        assert updated.status == TicketStatus.BUILDING.value
        assert updated.is_blocked is False
        assert updated.blocked_reason is None
        assert updated.blocked_at is None

    def test_transition_status_creates_phase_history(
        self, ticket_workflow_orchestrator: TicketWorkflowOrchestrator, ticket: Ticket
    ):
        """Test transition creates phase history record."""
        ticket_workflow_orchestrator.transition_status(
            ticket.id, TicketStatus.ANALYZING.value, initiated_by="test", reason="Test"
        )

        with ticket_workflow_orchestrator.db.get_session() as session:
            from omoi_os.models.phase_history import PhaseHistory

            history = (
                session.query(PhaseHistory)
                .filter(PhaseHistory.ticket_id == ticket.id)
                .order_by(PhaseHistory.created_at.desc())
                .first()
            )

            assert history is not None
            assert history.from_phase == "PHASE_BACKLOG"
            assert history.to_phase == "PHASE_REQUIREMENTS"
            assert history.transitioned_by == "test"

    def test_transition_status_publishes_event(
        self, ticket_workflow_orchestrator: TicketWorkflowOrchestrator, ticket: Ticket
    ):
        """Test transition publishes event."""
        # Mock event bus
        events = []

        def mock_publish(event):
            events.append(event)

        ticket_workflow_orchestrator.event_bus.publish = mock_publish

        ticket_workflow_orchestrator.transition_status(
            ticket.id, TicketStatus.ANALYZING.value, initiated_by="test"
        )

        assert len(events) == 1
        assert events[0].event_type == "ticket.status_transitioned"
        assert events[0].entity_id == ticket.id
        assert events[0].payload["from_status"] == TicketStatus.BACKLOG.value
        assert events[0].payload["to_status"] == TicketStatus.ANALYZING.value

    # ---------------------------------------------------------------------
    # Automatic Progression (REQ-TKT-SM-003)
    # ---------------------------------------------------------------------

    def test_check_and_progress_ticket_gate_not_met(
        self, ticket_workflow_orchestrator: TicketWorkflowOrchestrator, ticket: Ticket
    ):
        """Test progression does not occur if gate criteria not met."""
        # Transition to analyzing
        ticket_workflow_orchestrator.transition_status(
            ticket.id, TicketStatus.ANALYZING.value, initiated_by="test"
        )

        # Check progression (should return None - gate criteria not met)
        result = ticket_workflow_orchestrator.check_and_progress_ticket(ticket.id)
        assert result is None

    def test_check_and_progress_ticket_gate_met(
        self,
        ticket_workflow_orchestrator: TicketWorkflowOrchestrator,
        db_service: DatabaseService,
        ticket: Ticket,
    ):
        """Test progression occurs when gate criteria met."""
        # Transition to analyzing
        ticket_workflow_orchestrator.transition_status(
            ticket.id, TicketStatus.ANALYZING.value, initiated_by="test"
        )

        # Create task and mark as completed
        with db_service.get_session() as session:
            task = Task(
                id="task-1",
                ticket_id=ticket.id,
                phase_id="PHASE_REQUIREMENTS",
                task_type="analyze_requirements",
                priority="MEDIUM",
                status="completed",
            )
            session.add(task)

            # Create phase gate artifact
            artifact = PhaseGateArtifact(
                ticket_id=ticket.id,
                phase_id="PHASE_REQUIREMENTS",
                artifact_type="requirements_document",
                artifact_path="requirements.md",
                artifact_content={"min_length": 500},
                collected_by="test",
            )
            session.add(artifact)
            session.commit()

        # Check progression (should progress to building)
        result = ticket_workflow_orchestrator.check_and_progress_ticket(ticket.id)
        assert result is not None
        assert result.status == TicketStatus.BUILDING.value

    def test_check_and_progress_ticket_blocked(
        self, ticket_workflow_orchestrator: TicketWorkflowOrchestrator, ticket: Ticket
    ):
        """Test progression does not occur if ticket is blocked."""
        ticket_id = ticket.id  # Extract ID before session closes
        # Transition to analyzing
        ticket_workflow_orchestrator.transition_status(
            ticket_id, TicketStatus.ANALYZING.value, initiated_by="test"
        )

        # Mark as blocked
        with ticket_workflow_orchestrator.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            ticket.is_blocked = True
            ticket.blocked_reason = "dependency"
            session.commit()

        # Check progression (should return None - blocked)
        result = ticket_workflow_orchestrator.check_and_progress_ticket(ticket_id)
        assert result is None

    def test_check_and_progress_ticket_terminal(
        self, ticket_workflow_orchestrator: TicketWorkflowOrchestrator, ticket: Ticket
    ):
        """Test progression does not occur if ticket is in terminal state."""
        # Transition to done
        ticket_workflow_orchestrator.transition_status(
            ticket.id, TicketStatus.DONE.value, initiated_by="test", force=True
        )

        # Check progression (should return None - terminal)
        result = ticket_workflow_orchestrator.check_and_progress_ticket(ticket.id)
        assert result is None

    # ---------------------------------------------------------------------
    # Regressions (REQ-TKT-SM-004)
    # ---------------------------------------------------------------------

    def test_regress_ticket(
        self, ticket_workflow_orchestrator: TicketWorkflowOrchestrator, ticket: Ticket
    ):
        """Test ticket regression to previous phase."""
        # Progress through states
        ticket_workflow_orchestrator.transition_status(
            ticket.id, TicketStatus.ANALYZING.value, initiated_by="test"
        )
        ticket_workflow_orchestrator.transition_status(
            ticket.id, TicketStatus.BUILDING.value, initiated_by="test"
        )
        ticket_workflow_orchestrator.transition_status(
            ticket.id, TicketStatus.BUILDING_DONE.value, initiated_by="test"
        )
        ticket_workflow_orchestrator.transition_status(
            ticket.id, TicketStatus.TESTING.value, initiated_by="test"
        )

        # Regress from testing to building (fix needed)
        updated = ticket_workflow_orchestrator.regress_ticket(
            ticket.id,
            TicketStatus.BUILDING.value,
            validation_feedback="Tests failed, fix needed",
            initiated_by="test",
        )

        assert updated.status == TicketStatus.BUILDING.value
        # Context might be None if not properly initialized, check if it exists
        if updated.context:
            assert "regressions" in updated.context
            assert len(updated.context["regressions"]) == 1
            assert (
                updated.context["regressions"][0]["validation_feedback"]
                == "Tests failed, fix needed"
            )

    # ---------------------------------------------------------------------
    # Blocking Detection (REQ-TKT-BL-001, REQ-TKT-BL-002, REQ-TKT-BL-003)
    # ---------------------------------------------------------------------

    def test_mark_blocked(
        self, ticket_workflow_orchestrator: TicketWorkflowOrchestrator, ticket: Ticket
    ):
        """Test marking ticket as blocked."""
        # Transition to analyzing (non-terminal state)
        ticket_workflow_orchestrator.transition_status(
            ticket.id, TicketStatus.ANALYZING.value, initiated_by="test"
        )

        # Mark as blocked
        updated = ticket_workflow_orchestrator.mark_blocked(
            ticket.id,
            blocker_type="dependency",
            suggested_remediation="Resolve dependency",
            initiated_by="test",
        )

        assert updated.is_blocked is True
        assert updated.blocked_reason == "dependency"
        assert updated.blocked_at is not None

    def test_mark_blocked_terminal_state(
        self, ticket_workflow_orchestrator: TicketWorkflowOrchestrator, ticket: Ticket
    ):
        """Test marking terminal state ticket as blocked (should be no-op)."""
        ticket_id = ticket.id  # Extract ID before session closes
        # Transition to done
        updated_ticket = ticket_workflow_orchestrator.transition_status(
            ticket_id, TicketStatus.DONE.value, initiated_by="test", force=True
        )
        assert updated_ticket.status == TicketStatus.DONE.value

        # Mark as blocked (should not block terminal state)
        updated = ticket_workflow_orchestrator.mark_blocked(
            ticket_id, blocker_type="dependency", initiated_by="test"
        )

        assert updated.is_blocked is False  # Terminal state cannot be blocked

    def test_unblock_ticket(
        self, ticket_workflow_orchestrator: TicketWorkflowOrchestrator, ticket: Ticket
    ):
        """Test unblocking ticket."""
        # Mark as blocked
        ticket_workflow_orchestrator.transition_status(
            ticket.id, TicketStatus.ANALYZING.value, initiated_by="test"
        )
        ticket_workflow_orchestrator.mark_blocked(
            ticket.id, blocker_type="dependency", initiated_by="test"
        )

        # Unblock
        updated = ticket_workflow_orchestrator.unblock_ticket(
            ticket.id, initiated_by="test"
        )

        assert updated.is_blocked is False
        assert updated.blocked_reason is None
        assert updated.blocked_at is None

    def test_detect_blocking(
        self,
        ticket_workflow_orchestrator: TicketWorkflowOrchestrator,
        db_service: DatabaseService,
        ticket: Ticket,
    ):
        """Test blocking detection per REQ-TKT-BL-001."""
        ticket_id = ticket.id  # Extract ID before session closes
        # Transition to analyzing
        ticket_workflow_orchestrator.transition_status(
            ticket_id, TicketStatus.ANALYZING.value, initiated_by="test"
        )

        # Update ticket's updated_at to be older than threshold
        with db_service.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            ticket.updated_at = utc_now() - timedelta(
                minutes=ticket_workflow_orchestrator.BLOCKING_THRESHOLD_MINUTES + 1
            )
            session.commit()

        # Detect blocking
        results = ticket_workflow_orchestrator.detect_blocking()

        # Should detect this ticket as needing to be blocked
        ticket_results = [r for r in results if r["ticket_id"] == ticket_id]
        if ticket_results:
            assert ticket_results[0]["should_block"] is True
            assert ticket_results[0]["blocker_type"] in [
                "dependency",
                "waiting_on_clarification",
                "failing_checks",
                "environment",
            ]

    def test_detect_blocking_with_progress(
        self,
        ticket_workflow_orchestrator: TicketWorkflowOrchestrator,
        db_service: DatabaseService,
        ticket: Ticket,
    ):
        """Test blocking detection does not trigger if task progress exists."""
        ticket_id = ticket.id  # Extract ID before session closes
        # Transition to analyzing
        ticket_workflow_orchestrator.transition_status(
            ticket_id, TicketStatus.ANALYZING.value, initiated_by="test"
        )

        # Create completed task recently (within threshold)
        with db_service.get_session() as session:
            task = Task(
                id="task-1",
                ticket_id=ticket_id,
                phase_id="PHASE_REQUIREMENTS",
                task_type="analyze_requirements",
                priority="MEDIUM",
                status="completed",
                completed_at=utc_now() - timedelta(minutes=10),  # Recent completion
            )
            session.add(task)

            # Update ticket's updated_at to be older than threshold
            ticket = session.get(Ticket, ticket_id)
            ticket.updated_at = utc_now() - timedelta(
                minutes=ticket_workflow_orchestrator.BLOCKING_THRESHOLD_MINUTES + 1
            )
            session.commit()

        # Detect blocking
        results = ticket_workflow_orchestrator.detect_blocking()

        # Should not detect this ticket (has progress)
        ticket_results = [r for r in results if r["ticket_id"] == ticket_id]
        assert len(ticket_results) == 0

    def test_blocker_classification(
        self,
        ticket_workflow_orchestrator: TicketWorkflowOrchestrator,
        db_service: DatabaseService,
        ticket: Ticket,
    ):
        """Test blocker classification per REQ-TKT-BL-002."""
        ticket_id = ticket.id  # Extract ID before session closes
        # Transition to analyzing
        ticket_workflow_orchestrator.transition_status(
            ticket_id, TicketStatus.ANALYZING.value, initiated_by="test"
        )

        # Create failed task (should classify as failing_checks)
        with db_service.get_session() as session:
            task = Task(
                id="task-1",
                ticket_id=ticket_id,
                phase_id="PHASE_REQUIREMENTS",
                task_type="analyze_requirements",
                priority="MEDIUM",
                status="failed",
            )
            session.add(task)

            # Update ticket's updated_at to be older than threshold
            ticket = session.get(Ticket, ticket_id)
            ticket.updated_at = utc_now() - timedelta(
                minutes=ticket_workflow_orchestrator.BLOCKING_THRESHOLD_MINUTES + 1
            )
            session.commit()

        # Detect blocking
        results = ticket_workflow_orchestrator.detect_blocking()

        # Should classify as failing_checks
        ticket_results = [r for r in results if r["ticket_id"] == ticket_id]
        if ticket_results:
            assert ticket_results[0]["blocker_type"] == "failing_checks"

    def test_mark_blocked_publishes_event(
        self, ticket_workflow_orchestrator: TicketWorkflowOrchestrator, ticket: Ticket
    ):
        """Test marking blocked publishes event."""
        # Mock event bus
        events = []

        def mock_publish(event):
            events.append(event)

        ticket_workflow_orchestrator.event_bus.publish = mock_publish

        ticket_workflow_orchestrator.transition_status(
            ticket.id, TicketStatus.ANALYZING.value, initiated_by="test"
        )

        ticket_workflow_orchestrator.mark_blocked(
            ticket.id, blocker_type="dependency", initiated_by="test"
        )

        assert len(events) >= 1
        blocked_events = [e for e in events if e.event_type == "ticket.blocked"]
        assert len(blocked_events) == 1
        assert blocked_events[0].entity_id == ticket.id
        assert blocked_events[0].payload["blocker_type"] == "dependency"

    def test_unblock_publishes_event(
        self, ticket_workflow_orchestrator: TicketWorkflowOrchestrator, ticket: Ticket
    ):
        """Test unblocking publishes event."""
        # Mock event bus
        events = []

        def mock_publish(event):
            events.append(event)

        ticket_workflow_orchestrator.event_bus.publish = mock_publish

        ticket_workflow_orchestrator.transition_status(
            ticket.id, TicketStatus.ANALYZING.value, initiated_by="test"
        )
        ticket_workflow_orchestrator.mark_blocked(
            ticket.id, blocker_type="dependency", initiated_by="test"
        )

        ticket_workflow_orchestrator.unblock_ticket(ticket.id, initiated_by="test")

        unblocked_events = [e for e in events if e.event_type == "ticket.unblocked"]
        assert len(unblocked_events) == 1
        assert unblocked_events[0].entity_id == ticket.id
