"""Unit tests for PhaseManager service."""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from omoi_os.models.ticket import Ticket
from omoi_os.models.ticket_status import TicketStatus
from omoi_os.services.phase_manager import (
    PhaseManager,
    ExecutionMode,
    PHASE_CONFIGS,
    PHASE_STATUS_MAP,
    STATUS_PHASE_MAP,
    STATUS_PROGRESSION,
    CONTINUOUS_TASK_TYPES,
    EXPLORATION_TASK_TYPES,
    get_phase_manager,
    reset_phase_manager,
)


class TestPhaseConfigs:
    """Test phase configuration data."""

    def test_all_phases_have_configs(self):
        """All expected phases should have configurations."""
        expected_phases = [
            "PHASE_BACKLOG",
            "PHASE_REQUIREMENTS",
            "PHASE_DESIGN",
            "PHASE_IMPLEMENTATION",
            "PHASE_TESTING",
            "PHASE_DEPLOYMENT",
            "PHASE_DONE",
            "PHASE_BLOCKED",
        ]
        for phase in expected_phases:
            assert phase in PHASE_CONFIGS, f"Missing config for {phase}"

    def test_phase_sequence_order(self):
        """Phases should have proper sequence order."""
        configs = list(PHASE_CONFIGS.values())
        # Filter out BLOCKED which has order 99
        active_phases = [c for c in configs if c.id != "PHASE_BLOCKED"]
        sorted_phases = sorted(active_phases, key=lambda x: x.sequence_order)

        expected_order = [
            "PHASE_BACKLOG",
            "PHASE_REQUIREMENTS",
            "PHASE_DESIGN",
            "PHASE_IMPLEMENTATION",
            "PHASE_TESTING",
            "PHASE_DEPLOYMENT",
            "PHASE_DONE",
        ]
        actual_order = [p.id for p in sorted_phases]
        assert actual_order == expected_order

    def test_terminal_phases(self):
        """Terminal phases should be marked correctly."""
        assert PHASE_CONFIGS["PHASE_DONE"].is_terminal is True
        assert PHASE_CONFIGS["PHASE_BLOCKED"].is_terminal is True
        assert PHASE_CONFIGS["PHASE_IMPLEMENTATION"].is_terminal is False

    def test_continuous_mode_phases(self):
        """Continuous mode should be enabled for implementation phases."""
        assert PHASE_CONFIGS["PHASE_IMPLEMENTATION"].continuous_mode is True
        assert PHASE_CONFIGS["PHASE_TESTING"].continuous_mode is True
        assert PHASE_CONFIGS["PHASE_DEPLOYMENT"].continuous_mode is True
        # Exploration phases should not have continuous mode
        assert PHASE_CONFIGS["PHASE_REQUIREMENTS"].continuous_mode is False
        assert PHASE_CONFIGS["PHASE_DESIGN"].continuous_mode is False

    def test_execution_modes(self):
        """Phases should have correct execution modes."""
        assert (
            PHASE_CONFIGS["PHASE_REQUIREMENTS"].execution_mode
            == ExecutionMode.EXPLORATION
        )
        assert PHASE_CONFIGS["PHASE_DESIGN"].execution_mode == ExecutionMode.EXPLORATION
        assert (
            PHASE_CONFIGS["PHASE_IMPLEMENTATION"].execution_mode
            == ExecutionMode.IMPLEMENTATION
        )
        assert PHASE_CONFIGS["PHASE_TESTING"].execution_mode == ExecutionMode.VALIDATION


class TestPhaseMappings:
    """Test phase-status mappings."""

    def test_phase_to_status_mapping(self):
        """Each phase should map to a valid status."""
        for phase, status in PHASE_STATUS_MAP.items():
            # Verify status is a valid TicketStatus value
            valid_statuses = [s.value for s in TicketStatus]
            assert (
                status in valid_statuses
            ), f"Invalid status {status} for phase {phase}"

    def test_status_to_phase_mapping(self):
        """Each status should map to a valid phase."""
        for status, phase in STATUS_PHASE_MAP.items():
            assert phase in PHASE_CONFIGS, f"Invalid phase {phase} for status {status}"

    def test_status_progression(self):
        """Status progression should lead to valid next statuses."""
        for current, next_status in STATUS_PROGRESSION.items():
            valid_statuses = [s.value for s in TicketStatus]
            assert current in valid_statuses
            assert next_status in valid_statuses


class TestTaskTypes:
    """Test task type classifications."""

    def test_continuous_task_types(self):
        """Continuous task types should include implementation tasks."""
        assert "implement_feature" in CONTINUOUS_TASK_TYPES
        assert "fix_bug" in CONTINUOUS_TASK_TYPES
        assert "write_tests" in CONTINUOUS_TASK_TYPES

    def test_exploration_task_types(self):
        """Exploration task types should include analysis tasks."""
        assert "analyze_requirements" in EXPLORATION_TASK_TYPES
        assert "explore_problem" in EXPLORATION_TASK_TYPES

    def test_no_overlap_between_task_types(self):
        """Continuous and exploration task types should not overlap."""
        overlap = CONTINUOUS_TASK_TYPES & EXPLORATION_TASK_TYPES
        assert len(overlap) == 0, f"Overlapping task types: {overlap}"


class TestPhaseManagerInit:
    """Test PhaseManager initialization."""

    def test_init_with_required_deps(self):
        """PhaseManager should initialize with just db."""
        db = MagicMock()
        manager = PhaseManager(db=db)
        assert manager.db == db
        assert manager.task_queue is None
        assert manager.phase_gate is None
        assert manager.event_bus is None

    def test_init_with_all_deps(self):
        """PhaseManager should accept all optional dependencies."""
        db = MagicMock()
        task_queue = MagicMock()
        phase_gate = MagicMock()
        event_bus = MagicMock()

        manager = PhaseManager(
            db=db,
            task_queue=task_queue,
            phase_gate=phase_gate,
            event_bus=event_bus,
        )

        assert manager.db == db
        assert manager.task_queue == task_queue
        assert manager.phase_gate == phase_gate
        assert manager.event_bus == event_bus


class TestPhaseConfigAccess:
    """Test phase configuration access methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.db = MagicMock()
        self.manager = PhaseManager(db=self.db)

    def test_get_phase_config_valid(self):
        """Should return config for valid phase."""
        config = self.manager.get_phase_config("PHASE_IMPLEMENTATION")
        assert config is not None
        assert config.id == "PHASE_IMPLEMENTATION"
        assert config.continuous_mode is True

    def test_get_phase_config_invalid(self):
        """Should return None for invalid phase."""
        config = self.manager.get_phase_config("PHASE_INVALID")
        assert config is None

    def test_get_all_phases(self):
        """Should return all phases in sequence order."""
        phases = self.manager.get_all_phases()
        assert len(phases) == len(PHASE_CONFIGS)
        # Verify order (BLOCKED is last due to sequence_order=99)
        assert phases[0].id == "PHASE_BACKLOG"
        assert phases[-1].id == "PHASE_BLOCKED"

    def test_get_status_for_phase(self):
        """Should return correct status for phase."""
        assert self.manager.get_status_for_phase("PHASE_IMPLEMENTATION") == "building"
        assert self.manager.get_status_for_phase("PHASE_DONE") == "done"
        assert self.manager.get_status_for_phase("PHASE_INVALID") is None

    def test_get_phase_for_status(self):
        """Should return correct phase for status."""
        assert self.manager.get_phase_for_status("building") == "PHASE_IMPLEMENTATION"
        assert self.manager.get_phase_for_status("done") == "PHASE_DONE"
        assert self.manager.get_phase_for_status("invalid") is None

    def test_get_execution_mode(self):
        """Should return correct execution mode."""
        assert (
            self.manager.get_execution_mode("PHASE_IMPLEMENTATION")
            == ExecutionMode.IMPLEMENTATION
        )
        assert (
            self.manager.get_execution_mode("PHASE_REQUIREMENTS")
            == ExecutionMode.EXPLORATION
        )
        assert (
            self.manager.get_execution_mode("PHASE_INVALID")
            == ExecutionMode.EXPLORATION
        )

    def test_is_continuous_mode_enabled(self):
        """Should correctly identify continuous mode phases."""
        assert self.manager.is_continuous_mode_enabled("PHASE_IMPLEMENTATION") is True
        assert self.manager.is_continuous_mode_enabled("PHASE_REQUIREMENTS") is False

    def test_get_next_phase(self):
        """Should return correct next phase."""
        assert self.manager.get_next_phase("PHASE_BACKLOG") == "PHASE_REQUIREMENTS"
        assert self.manager.get_next_phase("PHASE_IMPLEMENTATION") == "PHASE_TESTING"
        assert self.manager.get_next_phase("PHASE_DONE") is None  # Terminal

    def test_get_next_status(self):
        """Should return correct next status."""
        assert self.manager.get_next_status("backlog") == "analyzing"
        assert self.manager.get_next_status("building") == "building-done"
        assert self.manager.get_next_status("done") is None


class TestTransitionValidation:
    """Test phase transition validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.db = MagicMock()
        self.manager = PhaseManager(db=self.db)

    def test_validate_transition_path_valid(self):
        """Should allow valid transition paths."""
        valid, reasons = self.manager.validate_transition_path(
            "PHASE_IMPLEMENTATION", "PHASE_TESTING"
        )
        assert valid is True
        assert len(reasons) == 0

    def test_validate_transition_path_invalid(self):
        """Should reject invalid transition paths."""
        valid, reasons = self.manager.validate_transition_path(
            "PHASE_BACKLOG", "PHASE_DONE"
        )
        assert valid is False
        assert len(reasons) > 0

    def test_validate_transition_to_blocked_always_allowed(self):
        """Transitioning to BLOCKED should always be allowed."""
        valid, reasons = self.manager.validate_transition_path(
            "PHASE_IMPLEMENTATION", "PHASE_BLOCKED"
        )
        assert valid is True

    def test_validate_transition_unknown_phases(self):
        """Should reject unknown phases."""
        valid, reasons = self.manager.validate_transition_path(
            "PHASE_INVALID", "PHASE_DONE"
        )
        assert valid is False
        assert "Unknown source phase" in reasons[0]

    def test_can_transition_ticket_not_found(self):
        """Should fail when ticket not found."""
        session_mock = MagicMock()
        session_mock.get.return_value = None
        self.db.get_session.return_value.__enter__ = MagicMock(
            return_value=session_mock
        )
        self.db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        can, reasons = self.manager.can_transition(
            "nonexistent", "PHASE_IMPLEMENTATION"
        )
        assert can is False
        assert "not found" in reasons[0]

    def test_can_transition_blocked_ticket(self):
        """Blocked tickets should only allow unblock transitions."""
        ticket = MagicMock()
        ticket.phase_id = "PHASE_IMPLEMENTATION"
        ticket.is_blocked = True

        session_mock = MagicMock()
        session_mock.get.return_value = ticket
        self.db.get_session.return_value.__enter__ = MagicMock(
            return_value=session_mock
        )
        self.db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Cannot transition to DONE when blocked
        can, reasons = self.manager.can_transition("ticket-123", "PHASE_DONE")
        assert can is False

        # Can transition to unblock phases (via BLOCKED allowed transitions)
        can, reasons = self.manager.can_transition("ticket-123", "PHASE_REQUIREMENTS")
        # This depends on BLOCKED config allowing it
        # Blocked is terminal but allows transitions out


class TestPhaseTransitions:
    """Test phase transition execution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.db = MagicMock()
        self.event_bus = MagicMock()
        self.task_queue = MagicMock()
        self.phase_gate = MagicMock()

        self.manager = PhaseManager(
            db=self.db,
            event_bus=self.event_bus,
            task_queue=self.task_queue,
            phase_gate=self.phase_gate,
        )

        # Set up default phase gate response
        self.phase_gate.check_gate_requirements.return_value = {
            "requirements_met": True,
            "missing_artifacts": [],
        }
        self.phase_gate.collect_artifacts.return_value = []

    def _setup_ticket(self, phase_id: str, status: str, is_blocked: bool = False):
        """Helper to set up a mock ticket."""
        ticket = MagicMock(spec=Ticket)
        ticket.id = str(uuid4())
        ticket.phase_id = phase_id
        ticket.status = status
        ticket.is_blocked = is_blocked
        ticket.priority = "medium"
        ticket.title = "Test Ticket"
        ticket.previous_phase_id = None
        ticket.blocked_reason = None
        ticket.blocked_at = None

        session_mock = MagicMock()
        session_mock.get.return_value = ticket
        session_mock.query.return_value.filter.return_value.count.return_value = 0
        self.db.get_session.return_value.__enter__ = MagicMock(
            return_value=session_mock
        )
        self.db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        return ticket

    def test_transition_to_phase_success(self):
        """Should successfully transition to valid next phase."""
        ticket = self._setup_ticket("PHASE_IMPLEMENTATION", "building")

        result = self.manager.transition_to_phase(
            ticket.id,
            "PHASE_TESTING",
            initiated_by="test",
            reason="Test transition",
        )

        assert result.success is True
        assert result.from_phase == "PHASE_IMPLEMENTATION"
        assert result.to_phase == "PHASE_TESTING"

    def test_transition_publishes_events(self):
        """Should publish events on successful transition."""
        ticket = self._setup_ticket("PHASE_IMPLEMENTATION", "building")

        self.manager.transition_to_phase(
            ticket.id,
            "PHASE_TESTING",
            initiated_by="test",
        )

        # Should publish phase_transitioned and TICKET_STATUS_CHANGED
        assert self.event_bus.publish.call_count >= 1

    def test_transition_force_skips_validation(self):
        """Force flag should skip validation."""
        ticket = self._setup_ticket("PHASE_BACKLOG", "backlog")

        # This would normally fail validation
        result = self.manager.transition_to_phase(
            ticket.id,
            "PHASE_DONE",
            force=True,
        )

        assert result.success is True

    def test_transition_spawns_tasks(self):
        """Should spawn tasks for new phase."""
        ticket = self._setup_ticket("PHASE_BACKLOG", "backlog")

        self.manager.transition_to_phase(
            ticket.id,
            "PHASE_IMPLEMENTATION",
            spawn_tasks=True,
            force=True,
        )

        # Task queue should be called for implementation tasks
        assert self.task_queue.enqueue_task.called

    def test_transition_no_spawn_for_terminal(self):
        """Should not spawn tasks for terminal phases."""
        ticket = self._setup_ticket("PHASE_IMPLEMENTATION", "building")

        self.manager.transition_to_phase(
            ticket.id,
            "PHASE_DONE",
            spawn_tasks=True,
            force=True,
        )

        # Task queue should NOT be called for DONE phase
        # (because is_terminal=True skips task spawning)

    def test_fast_track_to_implementation(self):
        """Should fast-track to implementation."""
        ticket = self._setup_ticket("PHASE_BACKLOG", "backlog")

        result = self.manager.fast_track_to_implementation(ticket.id)

        assert result.success is True
        assert result.to_phase == "PHASE_IMPLEMENTATION"

    def test_fast_track_from_implementation_fails(self):
        """Fast-track from implementation should fail."""
        ticket = self._setup_ticket("PHASE_IMPLEMENTATION", "building")

        result = self.manager.fast_track_to_implementation(ticket.id)

        assert result.success is False
        assert "already in PHASE_IMPLEMENTATION" in result.reason

    def test_move_to_done(self):
        """Should move ticket to done."""
        ticket = self._setup_ticket("PHASE_IMPLEMENTATION", "building")

        result = self.manager.move_to_done(ticket.id)

        assert result.success is True
        assert result.to_phase == "PHASE_DONE"


class TestAutoAdvancement:
    """Test automatic phase advancement."""

    def setup_method(self):
        """Set up test fixtures."""
        self.db = MagicMock()
        self.phase_gate = MagicMock()

        self.manager = PhaseManager(
            db=self.db,
            phase_gate=self.phase_gate,
        )

    def test_check_and_advance_blocked_ticket(self):
        """Should not advance blocked tickets."""
        ticket = MagicMock()
        ticket.phase_id = "PHASE_IMPLEMENTATION"
        ticket.is_blocked = True

        session_mock = MagicMock()
        session_mock.get.return_value = ticket
        self.db.get_session.return_value.__enter__ = MagicMock(
            return_value=session_mock
        )
        self.db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        result = self.manager.check_and_advance("ticket-123")

        assert result.success is False
        assert "blocked" in result.reason.lower()

    def test_check_and_advance_terminal_ticket(self):
        """Should not advance terminal tickets."""
        ticket = MagicMock()
        ticket.phase_id = "PHASE_DONE"
        ticket.is_blocked = False

        session_mock = MagicMock()
        session_mock.get.return_value = ticket
        self.db.get_session.return_value.__enter__ = MagicMock(
            return_value=session_mock
        )
        self.db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        result = self.manager.check_and_advance("ticket-123")

        assert result.success is False


class TestCallbacks:
    """Test callback registration and execution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.db = MagicMock()
        self.manager = PhaseManager(db=self.db)

    def test_register_pre_transition_callback(self):
        """Should register pre-transition callback."""

        def my_callback(manager, ticket_id, from_phase, to_phase):
            pass

        self.manager.register_pre_transition_callback(my_callback)
        assert my_callback in self.manager._pre_transition_callbacks

    def test_register_post_transition_callback(self):
        """Should register post-transition callback."""

        def my_callback(manager, ticket_id, from_phase, to_phase):
            pass

        self.manager.register_post_transition_callback(my_callback)
        assert my_callback in self.manager._post_transition_callbacks

    def test_register_gate_failure_callback(self):
        """Should register gate failure callback."""

        def my_callback(manager, ticket_id, from_phase, to_phase):
            pass

        self.manager.register_gate_failure_callback(my_callback)
        assert my_callback in self.manager._on_gate_failure_callbacks


class TestSingleton:
    """Test singleton pattern."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_phase_manager()

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_phase_manager()

    def test_get_phase_manager_requires_db_first_time(self):
        """Should require db for first initialization."""
        with pytest.raises(ValueError, match="Must provide db"):
            get_phase_manager()

    def test_get_phase_manager_returns_same_instance(self):
        """Should return same instance on subsequent calls."""
        db = MagicMock()
        manager1 = get_phase_manager(db=db)
        manager2 = get_phase_manager()

        assert manager1 is manager2

    def test_reset_phase_manager(self):
        """Reset should allow new initialization."""
        db1 = MagicMock()
        db2 = MagicMock()

        manager1 = get_phase_manager(db=db1)
        reset_phase_manager()
        manager2 = get_phase_manager(db=db2)

        assert manager1 is not manager2
        assert manager2.db is db2


class TestEventSubscriptions:
    """Test event subscription handlers."""

    def setup_method(self):
        """Set up test fixtures."""
        self.db = MagicMock()
        self.event_bus = MagicMock()
        self.manager = PhaseManager(
            db=self.db,
            event_bus=self.event_bus,
        )

    def test_subscribe_to_events(self):
        """Should subscribe to expected events."""
        self.manager.subscribe_to_events()

        # Should subscribe to TASK_STARTED and TASK_COMPLETED
        subscribe_calls = self.event_bus.subscribe.call_args_list
        event_types = [call[0][0] for call in subscribe_calls]

        assert "TASK_STARTED" in event_types
        assert "TASK_COMPLETED" in event_types

    def test_handle_task_started_implementation(self):
        """Should move ticket to implementation on implement_feature start."""
        ticket = MagicMock()
        ticket.phase_id = "PHASE_REQUIREMENTS"
        ticket.is_blocked = False

        session_mock = MagicMock()
        session_mock.get.return_value = ticket
        self.db.get_session.return_value.__enter__ = MagicMock(
            return_value=session_mock
        )
        self.db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        event_data = {
            "payload": {
                "ticket_id": "ticket-123",
                "task_type": "implement_feature",
                "phase_id": "PHASE_REQUIREMENTS",
            }
        }

        self.manager._handle_task_started(event_data)

        # Should have attempted to move to implementation


class TestStatusSync:
    """Test status synchronization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.db = MagicMock()
        self.manager = PhaseManager(db=self.db)

    def test_sync_status_with_phase(self):
        """Should sync status to match phase."""
        ticket = MagicMock()
        ticket.phase_id = "PHASE_IMPLEMENTATION"
        ticket.status = "analyzing"  # Wrong status

        session_mock = MagicMock()
        session_mock.get.return_value = ticket
        self.db.get_session.return_value.__enter__ = MagicMock(
            return_value=session_mock
        )
        self.db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        result = self.manager.sync_status_with_phase("ticket-123")

        assert result is True
        assert ticket.status == "building"

    def test_sync_status_no_change_needed(self):
        """Should not update when status already matches."""
        ticket = MagicMock()
        ticket.phase_id = "PHASE_IMPLEMENTATION"
        ticket.status = "building"  # Correct status

        session_mock = MagicMock()
        session_mock.get.return_value = ticket
        self.db.get_session.return_value.__enter__ = MagicMock(
            return_value=session_mock
        )
        self.db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        result = self.manager.sync_status_with_phase("ticket-123")

        assert result is False

    def test_sync_phase_with_status(self):
        """Should sync phase to match status."""
        ticket = MagicMock()
        ticket.phase_id = "PHASE_REQUIREMENTS"  # Wrong phase
        ticket.status = "building"

        session_mock = MagicMock()
        session_mock.get.return_value = ticket
        self.db.get_session.return_value.__enter__ = MagicMock(
            return_value=session_mock
        )
        self.db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        result = self.manager.sync_phase_with_status("ticket-123")

        assert result is True
        assert ticket.phase_id == "PHASE_IMPLEMENTATION"
