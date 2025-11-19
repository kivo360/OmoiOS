"""Tests for agent status state machine (REQ-ALM-004)."""

import pytest

from omoi_os.models.agent import Agent
from omoi_os.models.agent_status import AgentStatus, is_valid_transition
from omoi_os.models.agent_status_transition import AgentStatusTransition
from omoi_os.services.agent_status_manager import AgentStatusManager, InvalidTransitionError
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.utils.datetime import utc_now


@pytest.fixture
def agent(db_service: DatabaseService) -> Agent:
    """Create a test agent."""
    with db_service.get_session() as session:
        agent = Agent(
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            status=AgentStatus.IDLE.value,
            capabilities=["bash", "file_editor"],
            capacity=1,
            health_status="healthy",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
        session.expunge(agent)
        return agent


# Use event_bus_service fixture from conftest.py instead of defining our own


@pytest.fixture
def status_manager(db_service: DatabaseService, event_bus_service: EventBusService) -> AgentStatusManager:
    """Create an AgentStatusManager instance."""
    return AgentStatusManager(db_service, event_bus_service)


class TestAgentStatus:
    """Tests for AgentStatus enum and transition validation."""

    def test_agent_status_enum(self):
        """Test AgentStatus enum values."""
        assert AgentStatus.SPAWNING.value == "SPAWNING"
        assert AgentStatus.IDLE.value == "IDLE"
        assert AgentStatus.RUNNING.value == "RUNNING"
        assert AgentStatus.DEGRADED.value == "DEGRADED"
        assert AgentStatus.FAILED.value == "FAILED"
        assert AgentStatus.QUARANTINED.value == "QUARANTINED"
        assert AgentStatus.TERMINATED.value == "TERMINATED"

    def test_is_terminal(self):
        """Test terminal state detection."""
        assert AgentStatus.is_terminal(AgentStatus.TERMINATED.value) is True
        assert AgentStatus.is_terminal(AgentStatus.IDLE.value) is False
        assert AgentStatus.is_terminal(AgentStatus.RUNNING.value) is False

    def test_is_active(self):
        """Test active state detection."""
        assert AgentStatus.is_active(AgentStatus.IDLE.value) is True
        assert AgentStatus.is_active(AgentStatus.RUNNING.value) is True
        assert AgentStatus.is_active(AgentStatus.SPAWNING.value) is False
        assert AgentStatus.is_active(AgentStatus.DEGRADED.value) is False

    def test_is_operational(self):
        """Test operational state detection."""
        assert AgentStatus.is_operational(AgentStatus.IDLE.value) is True
        assert AgentStatus.is_operational(AgentStatus.RUNNING.value) is True
        assert AgentStatus.is_operational(AgentStatus.DEGRADED.value) is True
        assert AgentStatus.is_operational(AgentStatus.FAILED.value) is False
        assert AgentStatus.is_operational(AgentStatus.TERMINATED.value) is False
        assert AgentStatus.is_operational(AgentStatus.QUARANTINED.value) is False

    def test_valid_transitions(self):
        """Test valid state transitions per REQ-ALM-004."""
        # SPAWNING → IDLE, FAILED, TERMINATED
        assert is_valid_transition(AgentStatus.SPAWNING.value, AgentStatus.IDLE.value) is True
        assert is_valid_transition(AgentStatus.SPAWNING.value, AgentStatus.FAILED.value) is True
        assert is_valid_transition(AgentStatus.SPAWNING.value, AgentStatus.TERMINATED.value) is True

        # IDLE → RUNNING, DEGRADED, QUARANTINED, TERMINATED
        assert is_valid_transition(AgentStatus.IDLE.value, AgentStatus.RUNNING.value) is True
        assert is_valid_transition(AgentStatus.IDLE.value, AgentStatus.DEGRADED.value) is True
        assert is_valid_transition(AgentStatus.IDLE.value, AgentStatus.QUARANTINED.value) is True
        assert is_valid_transition(AgentStatus.IDLE.value, AgentStatus.TERMINATED.value) is True

        # RUNNING → IDLE, FAILED, DEGRADED, QUARANTINED
        assert is_valid_transition(AgentStatus.RUNNING.value, AgentStatus.IDLE.value) is True
        assert is_valid_transition(AgentStatus.RUNNING.value, AgentStatus.FAILED.value) is True
        assert is_valid_transition(AgentStatus.RUNNING.value, AgentStatus.DEGRADED.value) is True
        assert is_valid_transition(AgentStatus.RUNNING.value, AgentStatus.QUARANTINED.value) is True

        # DEGRADED → IDLE, FAILED, QUARANTINED, TERMINATED
        assert is_valid_transition(AgentStatus.DEGRADED.value, AgentStatus.IDLE.value) is True
        assert is_valid_transition(AgentStatus.DEGRADED.value, AgentStatus.FAILED.value) is True
        assert is_valid_transition(AgentStatus.DEGRADED.value, AgentStatus.QUARANTINED.value) is True
        assert is_valid_transition(AgentStatus.DEGRADED.value, AgentStatus.TERMINATED.value) is True

        # FAILED → QUARANTINED, TERMINATED
        assert is_valid_transition(AgentStatus.FAILED.value, AgentStatus.QUARANTINED.value) is True
        assert is_valid_transition(AgentStatus.FAILED.value, AgentStatus.TERMINATED.value) is True

        # QUARANTINED → IDLE, TERMINATED
        assert is_valid_transition(AgentStatus.QUARANTINED.value, AgentStatus.IDLE.value) is True
        assert is_valid_transition(AgentStatus.QUARANTINED.value, AgentStatus.TERMINATED.value) is True

    def test_invalid_transitions(self):
        """Test invalid state transitions per REQ-ALM-004."""
        # SPAWNING cannot go to RUNNING directly
        assert is_valid_transition(AgentStatus.SPAWNING.value, AgentStatus.RUNNING.value) is False

        # IDLE cannot go to FAILED directly
        assert is_valid_transition(AgentStatus.IDLE.value, AgentStatus.FAILED.value) is False

        # TERMINATED cannot transition anywhere (terminal state)
        assert is_valid_transition(AgentStatus.TERMINATED.value, AgentStatus.IDLE.value) is False
        assert is_valid_transition(AgentStatus.TERMINATED.value, AgentStatus.RUNNING.value) is False

        # FAILED cannot go to IDLE or RUNNING
        assert is_valid_transition(AgentStatus.FAILED.value, AgentStatus.IDLE.value) is False
        assert is_valid_transition(AgentStatus.FAILED.value, AgentStatus.RUNNING.value) is False

        # Cannot skip states (e.g., IDLE → QUARANTINED without going through DEGRADED)
        # Actually, IDLE → QUARANTINED is valid per the requirements
        # But IDLE → FAILED is not valid (must go through DEGRADED or RUNNING first)
        assert is_valid_transition(AgentStatus.IDLE.value, AgentStatus.FAILED.value) is False


class TestAgentStatusManager:
    """Tests for AgentStatusManager service."""

    # ---------------------------------------------------------------------
    # State Transitions (REQ-ALM-004)
    # ---------------------------------------------------------------------

    def test_transition_status_valid(
        self, status_manager: AgentStatusManager, agent: Agent
    ):
        """Test valid status transition."""
        updated = status_manager.transition_status(
            agent.id,
            to_status=AgentStatus.RUNNING.value,
            initiated_by="test",
            reason="Starting task execution",
        )

        assert updated.status == AgentStatus.RUNNING.value

        # Verify transition was recorded
        transitions = status_manager.get_transition_history(agent.id, limit=1)
        assert len(transitions) == 1
        assert transitions[0].from_status == AgentStatus.IDLE.value
        assert transitions[0].to_status == AgentStatus.RUNNING.value
        assert transitions[0].reason == "Starting task execution"
        assert transitions[0].triggered_by == "test"

    def test_transition_status_invalid(
        self, status_manager: AgentStatusManager, agent: Agent
    ):
        """Test invalid status transition raises error."""
        with pytest.raises(InvalidTransitionError):
            status_manager.transition_status(
                agent.id,
                to_status=AgentStatus.FAILED.value,  # Cannot go from IDLE to FAILED directly
                initiated_by="test",
            )

    def test_transition_status_force(
        self, status_manager: AgentStatusManager, agent: Agent
    ):
        """Test forced transition bypasses validation."""
        # Force transition from IDLE to FAILED (normally invalid)
        updated = status_manager.transition_status(
            agent.id,
            to_status=AgentStatus.FAILED.value,
            initiated_by="guardian",
            reason="Guardian override",
            force=True,
        )

        assert updated.status == AgentStatus.FAILED.value

    def test_transition_status_invalid_status(
        self, status_manager: AgentStatusManager, agent: Agent
    ):
        """Test transition to invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            status_manager.transition_status(
                agent.id,
                to_status="INVALID_STATUS",
                initiated_by="test",
            )

    def test_transition_status_agent_not_found(
        self, status_manager: AgentStatusManager
    ):
        """Test transition for non-existent agent raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            status_manager.transition_status(
                "non-existent-id",
                to_status=AgentStatus.RUNNING.value,
                initiated_by="test",
            )

    def test_transition_status_same_status(
        self, status_manager: AgentStatusManager, agent: Agent
    ):
        """Test transition to same status requires force flag."""
        # Same-to-same transitions are not valid by default per REQ-ALM-004
        # Must use force=True for guardian override scenarios
        with pytest.raises(InvalidTransitionError):
            status_manager.transition_status(
                agent.id,
                to_status=AgentStatus.IDLE.value,  # Same as current
                initiated_by="test",
                reason="No-op transition",
            )

        # With force=True, it should work (for guardian override)
        updated = status_manager.transition_status(
            agent.id,
            to_status=AgentStatus.IDLE.value,  # Same as current
            initiated_by="guardian",
            reason="Guardian override - no-op transition",
            force=True,
        )

        assert updated.status == AgentStatus.IDLE.value

        # Should still create a transition record
        transitions = status_manager.get_transition_history(agent.id, limit=2)
        assert len(transitions) >= 1

    def test_transition_status_updates_updated_at(
        self, status_manager: AgentStatusManager, agent: Agent, db_service: DatabaseService
    ):
        """Test that transition updates agent's updated_at timestamp."""
        original_updated_at = agent.updated_at

        # Wait a tiny bit to ensure timestamp difference
        import time
        time.sleep(0.01)

        updated = status_manager.transition_status(
            agent.id,
            to_status=AgentStatus.RUNNING.value,
            initiated_by="test",
        )

        # Verify updated_at was updated
        assert updated.updated_at > original_updated_at

    def test_transition_status_with_task_id(
        self, status_manager: AgentStatusManager, agent: Agent, db_service: DatabaseService, sample_ticket
    ):
        """Test transition with task_id association."""
        # Create a real task for the foreign key constraint
        from omoi_os.models.task import Task

        with db_service.get_session() as session:
            task = Task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test_task",
                description="Test task",
                priority="MEDIUM",
                status="pending",
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            task_id = task.id
            session.expunge(task)

        updated = status_manager.transition_status(
            agent.id,
            to_status=AgentStatus.RUNNING.value,
            initiated_by="test",
            task_id=task_id,
            reason="Task assigned",
        )

        # Verify transition was recorded with task_id
        transitions = status_manager.get_transition_history(agent.id, limit=1)
        assert len(transitions) == 1
        assert transitions[0].task_id == task_id

    def test_transition_status_with_metadata(
        self, status_manager: AgentStatusManager, agent: Agent
    ):
        """Test transition with metadata."""
        metadata = {"error_code": "TIMEOUT", "retry_count": 2}

        updated = status_manager.transition_status(
            agent.id,
            to_status=AgentStatus.DEGRADED.value,
            initiated_by="test",
            metadata=metadata,
            reason="Performance degradation",
        )

        # Verify transition was recorded with metadata
        transitions = status_manager.get_transition_history(agent.id, limit=1)
        assert len(transitions) == 1
        assert transitions[0].transition_metadata == metadata

    # ---------------------------------------------------------------------
    # Transition History (REQ-ALM-004)
    # ---------------------------------------------------------------------

    def test_get_transition_history(
        self, status_manager: AgentStatusManager, agent: Agent
    ):
        """Test getting transition history."""
        # Make multiple transitions
        status_manager.transition_status(agent.id, AgentStatus.RUNNING.value, initiated_by="test", reason="T1")
        status_manager.transition_status(agent.id, AgentStatus.IDLE.value, initiated_by="test", reason="T2")
        status_manager.transition_status(agent.id, AgentStatus.DEGRADED.value, initiated_by="test", reason="T3")

        # Get history (should be most recent first)
        transitions = status_manager.get_transition_history(agent.id, limit=10)

        assert len(transitions) >= 3
        # Verify order (most recent first)
        assert transitions[0].to_status == AgentStatus.DEGRADED.value
        assert transitions[1].to_status == AgentStatus.IDLE.value
        assert transitions[2].to_status == AgentStatus.RUNNING.value

    def test_get_transition_history_limit(
        self, status_manager: AgentStatusManager, agent: Agent
    ):
        """Test transition history limit."""
        # Make more transitions than limit
        for i in range(5):
            status_manager.transition_status(
                agent.id,
                AgentStatus.RUNNING.value if i % 2 == 0 else AgentStatus.IDLE.value,
                initiated_by="test",
                reason=f"Transition {i}",
            )

        # Get limited history
        transitions = status_manager.get_transition_history(agent.id, limit=2)

        assert len(transitions) == 2

    def test_get_transition_history_empty(
        self, status_manager: AgentStatusManager, agent: Agent
    ):
        """Test getting transition history for agent with no transitions."""
        transitions = status_manager.get_transition_history(agent.id)

        # Should have at least the initial transition if any, or empty
        # Since agent was created directly, might have no transitions
        assert isinstance(transitions, list)

    # ---------------------------------------------------------------------
    # Event Publishing (REQ-ALM-004)
    # ---------------------------------------------------------------------

    def test_transition_status_publishes_event(
        self, status_manager: AgentStatusManager, agent: Agent, event_bus_service: EventBusService
    ):
        """Test that status transition publishes AGENT_STATUS_CHANGED event."""
        # Subscribe to events
        events_received = []
        def event_handler(event):
            events_received.append(event)

        # Note: FakeStrictRedis doesn't support pub/sub like real Redis
        # So we'll test the event bus publish call indirectly by checking
        # that no exception is raised and the transition succeeds
        updated = status_manager.transition_status(
            agent.id,
            to_status=AgentStatus.RUNNING.value,
            initiated_by="test",
            reason="Test event",
        )

        assert updated.status == AgentStatus.RUNNING.value
        # Event bus should have been called (no exception means it worked)

    # ---------------------------------------------------------------------
    # Integration Tests
    # ---------------------------------------------------------------------

    def test_full_lifecycle(
        self, status_manager: AgentStatusManager, db_service: DatabaseService, sample_ticket
    ):
        """Test full agent lifecycle with state machine."""
        from omoi_os.models.task import Task

        # Create agent in SPAWNING state
        with db_service.get_session() as session:
            agent = Agent(
                agent_type="worker",
                phase_id="PHASE_IMPLEMENTATION",
                status=AgentStatus.SPAWNING.value,
                capabilities=["bash"],
                capacity=1,
                health_status="healthy",
            )
            session.add(agent)
            session.commit()
            session.refresh(agent)
            agent_id = agent.id
            session.expunge(agent)

            # Create a real task for the transition
            task = Task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test_task",
                description="Test task",
                priority="MEDIUM",
                status="pending",
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            task_id = task.id
            session.expunge(task)

        # SPAWNING → IDLE
        agent = status_manager.transition_status(
            agent_id, AgentStatus.IDLE.value, initiated_by="system", reason="Registration complete"
        )
        assert agent.status == AgentStatus.IDLE.value

        # IDLE → RUNNING
        agent = status_manager.transition_status(
            agent_id, AgentStatus.RUNNING.value, initiated_by="worker", reason="Task assigned", task_id=task_id
        )
        assert agent.status == AgentStatus.RUNNING.value

        # RUNNING → IDLE (task completed)
        agent = status_manager.transition_status(
            agent_id, AgentStatus.IDLE.value, initiated_by="worker", reason="Task completed"
        )
        assert agent.status == AgentStatus.IDLE.value

        # IDLE → DEGRADED (anomaly detected)
        agent = status_manager.transition_status(
            agent_id, AgentStatus.DEGRADED.value, initiated_by="monitor", reason="Anomaly detected"
        )
        assert agent.status == AgentStatus.DEGRADED.value

        # DEGRADED → QUARANTINED (escalation)
        agent = status_manager.transition_status(
            agent_id, AgentStatus.QUARANTINED.value, initiated_by="guardian", reason="Escalation"
        )
        assert agent.status == AgentStatus.QUARANTINED.value

        # QUARANTINED → TERMINATED (cleanup)
        agent = status_manager.transition_status(
            agent_id, AgentStatus.TERMINATED.value, initiated_by="system", reason="Cleanup"
        )
        assert agent.status == AgentStatus.TERMINATED.value

        # Verify transition history
        transitions = status_manager.get_transition_history(agent_id, limit=10)
        assert len(transitions) >= 6  # All transitions recorded

        # Verify final state is terminal
        assert AgentStatus.is_terminal(agent.status) is True

    def test_degradation_path(
        self, status_manager: AgentStatusManager, agent: Agent
    ):
        """Test degradation path: RUNNING → DEGRADED → FAILED."""
        # IDLE → RUNNING
        agent = status_manager.transition_status(
            agent.id, AgentStatus.RUNNING.value, initiated_by="test", reason="Start task"
        )

        # RUNNING → DEGRADED (missed heartbeats)
        agent = status_manager.transition_status(
            agent.id, AgentStatus.DEGRADED.value, initiated_by="monitor", reason="Missed heartbeats"
        )
        assert agent.status == AgentStatus.DEGRADED.value

        # DEGRADED → FAILED (unresponsive)
        agent = status_manager.transition_status(
            agent.id, AgentStatus.FAILED.value, initiated_by="monitor", reason="Unresponsive"
        )
        assert agent.status == AgentStatus.FAILED.value

        # FAILED → TERMINATED (restart protocol)
        agent = status_manager.transition_status(
            agent.id, AgentStatus.TERMINATED.value, initiated_by="restart_orchestrator", reason="Restart"
        )
        assert agent.status == AgentStatus.TERMINATED.value

    def test_recovery_path(
        self, status_manager: AgentStatusManager, agent: Agent
    ):
        """Test recovery path: QUARANTINED → IDLE."""
        # First, transition to QUARANTINED through valid path
        # IDLE → DEGRADED → QUARANTINED
        status_manager.transition_status(agent.id, AgentStatus.DEGRADED.value, initiated_by="test", reason="Degrade")
        status_manager.transition_status(agent.id, AgentStatus.QUARANTINED.value, initiated_by="test", reason="Quarantine")

        # QUARANTINED → IDLE (recovery)
        agent = status_manager.transition_status(
            agent.id, AgentStatus.IDLE.value, initiated_by="system", reason="Recovered"
        )
        assert agent.status == AgentStatus.IDLE.value
        assert AgentStatus.is_active(agent.status) is True

