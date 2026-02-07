"""Tests for validation system (Enhanced Validation - Squad C)."""

import pytest
from unittest.mock import patch

from omoi_os.models.agent import Agent
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.models.validation_review import ValidationReview
from omoi_os.services.agent_registry import AgentRegistryService
from omoi_os.services.database import DatabaseService
from omoi_os.services.diagnostic import DiagnosticService
from omoi_os.services.embedding import EmbeddingService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.memory import MemoryService
from omoi_os.services.monitor import MonitorService
from omoi_os.services.discovery import DiscoveryService
from omoi_os.services.validation_orchestrator import (
    ValidationOrchestrator,
    ValidationState,
)
from omoi_os.utils.datetime import utc_now


@pytest.fixture
def embedding_service():
    """Embedding service for validation tests."""
    return EmbeddingService()


@pytest.fixture
def memory_service(embedding_service):
    """Memory service for validation tests."""
    return MemoryService(embedding_service=embedding_service, event_bus=None)


@pytest.fixture
def diagnostic_service(
    db_service: DatabaseService,
    event_bus_service: EventBusService,
):
    """Diagnostic service with dependencies."""
    embedding = EmbeddingService()
    memory = MemoryService(embedding_service=embedding, event_bus=event_bus_service)
    discovery = DiscoveryService(event_bus=event_bus_service)
    monitor = MonitorService(db=db_service, event_bus=event_bus_service)

    return DiagnosticService(
        db=db_service,
        discovery=discovery,
        memory=memory,
        monitor=monitor,
        event_bus=event_bus_service,
    )


@pytest.fixture
def validation_orchestrator(
    db_service: DatabaseService,
    event_bus_service: EventBusService,
    memory_service: MemoryService,
    diagnostic_service: DiagnosticService,
):
    """Validation orchestrator service."""
    registry_service = AgentRegistryService(db_service, event_bus_service)
    return ValidationOrchestrator(
        db=db_service,
        agent_registry=registry_service,
        memory=memory_service,
        diagnostic=diagnostic_service,
        event_bus=event_bus_service,
    )


@pytest.fixture
def validation_enabled_task(db_service: DatabaseService, sample_task: Task):
    """Create a task with validation enabled."""
    with db_service.get_session() as session:
        task = session.get(Task, sample_task.id)
        task.validation_enabled = True
        task.validation_iteration = 0
        task.status = "running"
        session.commit()
        session.refresh(task)
        session.expunge(task)
        return task


@pytest.fixture
def validator_agent(db_service: DatabaseService):
    """Create a validator agent."""
    with db_service.get_session() as session:
        agent = Agent(
            agent_type="validator",
            phase_id="PHASE_IMPLEMENTATION",
            status="idle",
            capabilities=["validation", "code_review", "testing"],
            capacity=1,
            health_status="healthy",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
        session.expunge(agent)
        return agent


@pytest.fixture
def worker_agent(db_service: DatabaseService):
    """Create a worker agent."""
    with db_service.get_session() as session:
        agent = Agent(
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            status="idle",
            capabilities=["implementation"],
            capacity=1,
            health_status="healthy",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
        session.expunge(agent)
        return agent


# -------------------------------------------------------------------------
# State Machine Transition Tests (REQ-VAL-SM-001, REQ-VAL-SM-002)
# -------------------------------------------------------------------------


def test_transition_to_under_review_success(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
):
    """Test successful transition to under_review state.

    Note: When validation_enabled=True, the transition_to_under_review method
    auto-spawns a validator which immediately transitions to validation_in_progress.
    """
    commit_sha = "abc123def456"

    success = validation_orchestrator.transition_to_under_review(
        task_id=validation_enabled_task.id,
        commit_sha=commit_sha,
    )

    assert success is True

    # Verify task state (should be validation_in_progress due to auto-spawn)
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        # When validation enabled, auto-spawn transitions to validation_in_progress
        assert task.status == ValidationState.VALIDATION_IN_PROGRESS
        assert task.validation_iteration == 1  # Incremented
        assert task.review_done is False
        assert task.result["validation_commit_sha"] == commit_sha
        # Verify validator was spawned
        assert validation_enabled_task.id in validation_orchestrator._active_validators


def test_transition_to_under_review_increments_iteration(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
):
    """Test that validation_iteration increments on each transition."""
    commit_sha = "abc123def456"

    # First transition
    validation_orchestrator.transition_to_under_review(
        task_id=validation_enabled_task.id,
        commit_sha=commit_sha,
    )

    # Verify iteration incremented
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        assert task.validation_iteration == 1

    # Reset status for second transition
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = "running"
        task.review_done = False
        session.commit()

    # Second transition
    validation_orchestrator.transition_to_under_review(
        task_id=validation_enabled_task.id,
        commit_sha=commit_sha,
    )

    # Verify iteration incremented again
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        assert task.validation_iteration == 2


def test_transition_to_under_review_requires_commit_sha(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
):
    """Test that commit_sha is required for validation-enabled tasks (REQ-VAL-SM-002)."""
    with pytest.raises(ValueError, match="commit_sha required"):
        validation_orchestrator.transition_to_under_review(
            task_id=validation_enabled_task.id,
            commit_sha=None,
        )


def test_transition_to_under_review_auto_spawns_validator(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
):
    """Test that validator is auto-spawned when task enters under_review (REQ-VAL-LC-001)."""
    commit_sha = "abc123def456"

    validation_orchestrator.transition_to_under_review(
        task_id=validation_enabled_task.id,
        commit_sha=commit_sha,
    )

    # Verify validator was spawned (check active validators)
    assert validation_enabled_task.id in validation_orchestrator._active_validators


# -------------------------------------------------------------------------
# Validator Spawning Tests (REQ-VAL-LC-001)
# -------------------------------------------------------------------------


def test_spawn_validator_success(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
):
    """Test successful validator spawning."""
    commit_sha = "abc123def456"

    # Set task to under_review state
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = ValidationState.UNDER_REVIEW
        session.commit()

    validator_id = validation_orchestrator.spawn_validator(
        task_id=validation_enabled_task.id,
        commit_sha=commit_sha,
    )

    assert validator_id is not None

    # Verify validator agent was created
    with db_service.get_session() as session:
        validator = session.get(Agent, validator_id)
        assert validator is not None
        assert validator.agent_type == "validator"
        assert validator.phase_id == validation_enabled_task.phase_id

    # Verify task transitioned to validation_in_progress
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        assert task.status == ValidationState.VALIDATION_IN_PROGRESS


def test_spawn_validator_prevents_duplicate(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
):
    """Test that spawning validator twice returns None if already active."""
    commit_sha = "abc123def456"

    # Set task to under_review state
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = ValidationState.UNDER_REVIEW
        session.commit()

    # First spawn
    validator_id1 = validation_orchestrator.spawn_validator(
        task_id=validation_enabled_task.id,
        commit_sha=commit_sha,
    )
    assert validator_id1 is not None

    # Second spawn should return None (already active)
    validator_id2 = validation_orchestrator.spawn_validator(
        task_id=validation_enabled_task.id,
        commit_sha=commit_sha,
    )
    assert validator_id2 is None


def test_spawn_validator_only_if_validation_enabled(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    sample_task: Task,
):
    """Test that validator is not spawned if validation_enabled=False."""
    commit_sha = "abc123def456"

    # Set task to under_review but validation disabled
    with db_service.get_session() as session:
        task = session.get(Task, sample_task.id)
        task.status = ValidationState.UNDER_REVIEW
        task.validation_enabled = False
        session.commit()

    validator_id = validation_orchestrator.spawn_validator(
        task_id=sample_task.id,
        commit_sha=commit_sha,
    )

    assert validator_id is None


# -------------------------------------------------------------------------
# Review Handling Tests (REQ-VAL-SM-002, REQ-VAL-SEC-001)
# -------------------------------------------------------------------------


def test_give_review_success_validation_passed(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
    validator_agent: Agent,
):
    """Test successful review submission with validation_passed=True."""
    # Set task to validation_in_progress
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = ValidationState.VALIDATION_IN_PROGRESS
        task.validation_iteration = 1
        session.commit()

    # Track validator
    validation_orchestrator._active_validators[validation_enabled_task.id] = (
        validator_agent.id
    )

    # Submit review
    result = validation_orchestrator.give_review(
        task_id=validation_enabled_task.id,
        validator_agent_id=validator_agent.id,
        validation_passed=True,
        feedback="All checks passed. Code looks good.",
    )

    assert result["status"] == "completed"
    assert result["message"] == "Validation passed"
    assert result["iteration"] == 1

    # Verify task transitioned to done
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        assert task.status == ValidationState.DONE
        assert task.review_done is True

    # Verify ValidationReview was created
    with db_service.get_session() as session:
        reviews = (
            session.query(ValidationReview)
            .filter(ValidationReview.task_id == validation_enabled_task.id)
            .all()
        )
        assert len(reviews) == 1
        assert reviews[0].validation_passed is True
        assert reviews[0].validator_agent_id == validator_agent.id


def test_give_review_success_validation_failed(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
    validator_agent: Agent,
):
    """Test successful review submission with validation_passed=False."""
    # Set task to validation_in_progress
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = ValidationState.VALIDATION_IN_PROGRESS
        task.validation_iteration = 1
        session.commit()

    # Track validator
    validation_orchestrator._active_validators[validation_enabled_task.id] = (
        validator_agent.id
    )

    feedback_text = "Missing error handling in function X."

    # Submit review
    result = validation_orchestrator.give_review(
        task_id=validation_enabled_task.id,
        validator_agent_id=validator_agent.id,
        validation_passed=False,
        feedback=feedback_text,
        evidence={"error_count": 3, "critical_issues": ["missing_error_handling"]},
        recommendations=["Add try-catch blocks", "Add input validation"],
    )

    assert result["status"] == "needs_work"
    assert result["message"] == "Validation failed; feedback recorded"
    assert result["iteration"] == 1

    # Verify task transitioned to needs_work
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        assert task.status == ValidationState.NEEDS_WORK
        assert task.last_validation_feedback == feedback_text

    # Verify ValidationReview was created with evidence and recommendations
    with db_service.get_session() as session:
        reviews = (
            session.query(ValidationReview)
            .filter(ValidationReview.task_id == validation_enabled_task.id)
            .all()
        )
        assert len(reviews) == 1
        assert reviews[0].validation_passed is False
        assert reviews[0].feedback == feedback_text
        assert reviews[0].evidence == {
            "error_count": 3,
            "critical_issues": ["missing_error_handling"],
        }
        assert reviews[0].recommendations == [
            "Add try-catch blocks",
            "Add input validation",
        ]


def test_give_review_only_validator_agent(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
    worker_agent: Agent,
):
    """Test that only validator agents can submit reviews (REQ-VAL-SEC-001)."""
    # Set task to validation_in_progress
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = ValidationState.VALIDATION_IN_PROGRESS
        task.validation_iteration = 1
        session.commit()

    # Try to submit review with worker agent (should fail)
    with pytest.raises(
        PermissionError, match="Only validator agents may call give_review"
    ):
        validation_orchestrator.give_review(
            task_id=validation_enabled_task.id,
            validator_agent_id=worker_agent.id,
            validation_passed=True,
            feedback="This should fail",
        )


def test_give_review_requires_validation_in_progress_state(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
    validator_agent: Agent,
):
    """Test that give_review requires task to be in validation_in_progress state."""
    # Set task to running (wrong state)
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = "running"
        task.validation_iteration = 1
        session.commit()

    # Try to submit review (should fail)
    with pytest.raises(ValueError, match="must be in validation_in_progress state"):
        validation_orchestrator.give_review(
            task_id=validation_enabled_task.id,
            validator_agent_id=validator_agent.id,
            validation_passed=True,
            feedback="This should fail",
        )


def test_give_review_requires_feedback_on_failure(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
    validator_agent: Agent,
):
    """Test that feedback is required when validation_passed=False (REQ-VAL-SM-002)."""
    # Set task to validation_in_progress
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = ValidationState.VALIDATION_IN_PROGRESS
        task.validation_iteration = 1
        session.commit()

    # Track validator
    validation_orchestrator._active_validators[validation_enabled_task.id] = (
        validator_agent.id
    )

    # Try to submit review without feedback (should fail)
    with pytest.raises(
        ValueError, match="feedback required when validation_passed=False"
    ):
        validation_orchestrator.give_review(
            task_id=validation_enabled_task.id,
            validator_agent_id=validator_agent.id,
            validation_passed=False,
            feedback="",  # Empty feedback
        )


# -------------------------------------------------------------------------
# Feedback Delivery Tests (REQ-VAL-LC-002)
# -------------------------------------------------------------------------


def test_send_feedback_success(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    worker_agent: Agent,
    event_bus_service: EventBusService,
):
    """Test successful feedback delivery to agent."""
    feedback_text = "Please add error handling to function X."

    # Mock event publishing to verify it's called
    with patch.object(event_bus_service, "publish") as mock_publish:
        delivered = validation_orchestrator.send_feedback(
            agent_id=worker_agent.id,
            feedback=feedback_text,
        )

        assert delivered is True
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args[0][0]
        assert call_args.event_type == "agent.validation_feedback"
        assert call_args.entity_type == "agent"
        assert call_args.entity_id == worker_agent.id
        assert call_args.payload["feedback"] == feedback_text


def test_send_feedback_agent_not_found(
    validation_orchestrator: ValidationOrchestrator,
):
    """Test that send_feedback returns False for non-existent agent."""
    delivered = validation_orchestrator.send_feedback(
        agent_id="non-existent-agent-id",
        feedback="Some feedback",
    )

    assert delivered is False


# -------------------------------------------------------------------------
# Status Query Tests (REQ-VAL-API)
# -------------------------------------------------------------------------


def test_get_validation_status_success(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
):
    """Test successful validation status query."""
    # Set task state
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = ValidationState.UNDER_REVIEW
        task.validation_iteration = 2
        task.review_done = False
        task.last_validation_feedback = "Previous feedback"
        session.commit()

    status = validation_orchestrator.get_validation_status(validation_enabled_task.id)

    assert status is not None
    assert status["task_id"] == validation_enabled_task.id
    assert status["state"] == ValidationState.UNDER_REVIEW
    assert status["iteration"] == 2
    assert status["review_done"] is False
    assert status["last_feedback"] == "Previous feedback"


def test_get_validation_status_task_not_found(
    validation_orchestrator: ValidationOrchestrator,
):
    """Test that get_validation_status returns None for non-existent task."""
    status = validation_orchestrator.get_validation_status("non-existent-task-id")
    assert status is None


# -------------------------------------------------------------------------
# Memory Integration Tests (REQ-VAL-MEM-001)
# -------------------------------------------------------------------------


def test_validation_review_records_memory(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    memory_service: MemoryService,
    validation_enabled_task: Task,
    validator_agent: Agent,
    sample_ticket: Ticket,
):
    """Test that validation review records memory entry (REQ-VAL-MEM-001)."""
    # Set task to validation_in_progress
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = ValidationState.VALIDATION_IN_PROGRESS
        task.validation_iteration = 1
        task.ticket_id = sample_ticket.id
        session.commit()

    # Track validator
    validation_orchestrator._active_validators[validation_enabled_task.id] = (
        validator_agent.id
    )

    # Mock memory service to verify it's called
    with patch.object(memory_service, "store_execution") as mock_store:
        validation_orchestrator.give_review(
            task_id=validation_enabled_task.id,
            validator_agent_id=validator_agent.id,
            validation_passed=True,
            feedback="All checks passed.",
        )

        # Verify memory was recorded
        mock_store.assert_called_once()
        call_args = mock_store.call_args[1]
        assert call_args["task_id"] == validation_enabled_task.id
        assert "All checks passed" in call_args["execution_summary"]
        assert call_args["success"] is True
        assert call_args["session"] is not None  # Verify session is passed


# -------------------------------------------------------------------------
# Diagnosis Integration Tests (REQ-VAL-DIAG-001, REQ-VAL-DIAG-002)
# -------------------------------------------------------------------------


def test_repeated_failures_spawn_diagnosis(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    diagnostic_service: DiagnosticService,
    validation_enabled_task: Task,
    validator_agent: Agent,
    sample_ticket: Ticket,
):
    """Test that repeated validation failures spawn Diagnosis Agent (REQ-VAL-DIAG-001)."""
    # Set task to validation_in_progress
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = ValidationState.VALIDATION_IN_PROGRESS
        task.validation_iteration = 1
        task.ticket_id = sample_ticket.id
        session.commit()

    # Track validator
    validation_orchestrator._active_validators[validation_enabled_task.id] = (
        validator_agent.id
    )

    # First failure
    validation_orchestrator.give_review(
        task_id=validation_enabled_task.id,
        validator_agent_id=validator_agent.id,
        validation_passed=False,
        feedback="First failure feedback.",
    )

    # Reset to validation_in_progress for second failure
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = ValidationState.VALIDATION_IN_PROGRESS
        task.validation_iteration = 2
        session.commit()

    validation_orchestrator._active_validators[validation_enabled_task.id] = (
        validator_agent.id
    )

    # Mock diagnostic service to verify it's called on second failure
    with patch.object(diagnostic_service, "spawn_diagnostic_agent") as mock_spawn:
        # Second failure (should trigger diagnosis)
        validation_orchestrator.give_review(
            task_id=validation_enabled_task.id,
            validator_agent_id=validator_agent.id,
            validation_passed=False,
            feedback="Second failure feedback.",
        )

        # Verify diagnostic agent was spawned
        mock_spawn.assert_called_once()
        call_args = mock_spawn.call_args[1]
        assert call_args["workflow_id"] == sample_ticket.id
        assert call_args["context"]["trigger"] == "repeated_validation_failures"
        assert call_args["context"]["consecutive_failures"] >= 2


def test_check_validator_timeouts(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    diagnostic_service: DiagnosticService,
    validation_enabled_task: Task,
    validator_agent: Agent,
    sample_ticket: Ticket,
):
    """Test that validator timeouts are detected and handled (REQ-VAL-DIAG-002)."""
    # Set task to validation_in_progress
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = ValidationState.VALIDATION_IN_PROGRESS
        task.ticket_id = sample_ticket.id
        session.commit()

    # Track validator
    validation_orchestrator._active_validators[validation_enabled_task.id] = (
        validator_agent.id
    )

    # Set validator heartbeat to old timestamp (simulating timeout)
    from datetime import timedelta

    with db_service.get_session() as session:
        validator = session.get(Agent, validator_agent.id)
        validator.last_heartbeat = utc_now() - timedelta(minutes=15)  # 15 minutes ago
        session.commit()

    # Mock diagnostic service to verify it's called on timeout
    with patch.object(diagnostic_service, "spawn_diagnostic_agent") as mock_spawn:
        validation_orchestrator.check_validator_timeouts(timeout_minutes=10)

        # Verify diagnostic agent was spawned for timeout
        mock_spawn.assert_called_once()
        call_args = mock_spawn.call_args[1]
        assert call_args["context"]["trigger"] == "validation_timeout"
        assert call_args["context"]["validator_agent_id"] == validator_agent.id

    # Verify task was marked as failed
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        assert task.status == ValidationState.FAILED
        assert "timeout" in task.error_message.lower()


# -------------------------------------------------------------------------
# Event Publishing Tests (REQ-VAL-Events)
# -------------------------------------------------------------------------


def test_validation_started_event_published(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
    validator_agent: Agent,
    event_bus_service: EventBusService,
):
    """Test that validation_started event is published (REQ-VAL-Events)."""
    # Set task to under_review
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = ValidationState.UNDER_REVIEW
        task.validation_iteration = 1
        session.commit()

    # Mock event publishing
    with patch.object(event_bus_service, "publish") as mock_publish:
        validation_orchestrator.transition_to_validation_in_progress(
            task_id=validation_enabled_task.id,
            validator_agent_id=validator_agent.id,
        )

        # Verify validation_started event was published
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args[0][0]
        assert call_args.event_type == "validation_started"
        assert call_args.entity_type == "task"
        assert call_args.entity_id == validation_enabled_task.id
        assert call_args.payload["iteration"] == 1


def test_validation_passed_event_published(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
    validator_agent: Agent,
    event_bus_service: EventBusService,
):
    """Test that validation_passed event is published (REQ-VAL-Events)."""
    # Set task to validation_in_progress
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = ValidationState.VALIDATION_IN_PROGRESS
        task.validation_iteration = 1
        session.commit()

    # Track validator
    validation_orchestrator._active_validators[validation_enabled_task.id] = (
        validator_agent.id
    )

    # Mock event publishing
    with patch.object(event_bus_service, "publish") as mock_publish:
        validation_orchestrator.give_review(
            task_id=validation_enabled_task.id,
            validator_agent_id=validator_agent.id,
            validation_passed=True,
            feedback="All checks passed.",
        )

        # Verify validation_passed event was published
        calls = [call[0][0] for call in mock_publish.call_args_list]
        event_types = [call.event_type for call in calls]
        assert "validation_passed" in event_types

        # Find validation_passed event
        passed_event = next(c for c in calls if c.event_type == "validation_passed")
        assert passed_event.entity_id == validation_enabled_task.id
        assert passed_event.payload["iteration"] == 1


def test_validation_failed_event_published(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
    validator_agent: Agent,
    event_bus_service: EventBusService,
):
    """Test that validation_failed event is published (REQ-VAL-Events)."""
    # Set task to validation_in_progress
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = ValidationState.VALIDATION_IN_PROGRESS
        task.validation_iteration = 1
        session.commit()

    # Track validator
    validation_orchestrator._active_validators[validation_enabled_task.id] = (
        validator_agent.id
    )

    feedback_text = "Missing error handling."

    # Mock event publishing
    with patch.object(event_bus_service, "publish") as mock_publish:
        validation_orchestrator.give_review(
            task_id=validation_enabled_task.id,
            validator_agent_id=validator_agent.id,
            validation_passed=False,
            feedback=feedback_text,
        )

        # Verify validation_failed event was published
        calls = [call[0][0] for call in mock_publish.call_args_list]
        event_types = [call.event_type for call in calls]
        assert "validation_failed" in event_types

        # Find validation_failed event
        failed_event = next(c for c in calls if c.event_type == "validation_failed")
        assert failed_event.entity_id == validation_enabled_task.id
        assert failed_event.payload["iteration"] == 1
        assert failed_event.payload["feedback"] == feedback_text


# -------------------------------------------------------------------------
# Integration Tests
# -------------------------------------------------------------------------


def test_complete_validation_workflow(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
    validator_agent: Agent,
):
    """Test complete validation workflow: under_review -> validation_in_progress -> done."""
    commit_sha = "abc123def456"

    # Step 1: Transition to under_review
    validation_orchestrator.transition_to_under_review(
        task_id=validation_enabled_task.id,
        commit_sha=commit_sha,
    )

    # Verify validator spawned
    validator_id = validation_orchestrator._active_validators.get(
        validation_enabled_task.id
    )
    assert validator_id is not None

    # Step 2: Submit review with validation_passed=True
    result = validation_orchestrator.give_review(
        task_id=validation_enabled_task.id,
        validator_agent_id=validator_id,
        validation_passed=True,
        feedback="All checks passed. Code is production-ready.",
    )

    assert result["status"] == "completed"

    # Step 3: Verify final state
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        assert task.status == ValidationState.DONE
        assert task.review_done is True
        assert task.validation_iteration == 1

        # Verify ValidationReview exists
        reviews = (
            session.query(ValidationReview)
            .filter(ValidationReview.task_id == validation_enabled_task.id)
            .all()
        )
        assert len(reviews) == 1
        assert reviews[0].validation_passed is True


def test_validation_workflow_with_feedback_loop(
    validation_orchestrator: ValidationOrchestrator,
    db_service: DatabaseService,
    validation_enabled_task: Task,
    validator_agent: Agent,
    worker_agent: Agent,
):
    """Test validation workflow with feedback loop: failed -> needs_work -> in_progress -> done."""
    commit_sha = "abc123def456"

    # Step 1: Transition to under_review and spawn validator
    validation_orchestrator.transition_to_under_review(
        task_id=validation_enabled_task.id,
        commit_sha=commit_sha,
    )

    validator_id = validation_orchestrator._active_validators.get(
        validation_enabled_task.id
    )

    # Step 2: First review fails
    result1 = validation_orchestrator.give_review(
        task_id=validation_enabled_task.id,
        validator_agent_id=validator_id,
        validation_passed=False,
        feedback="Missing error handling. Please add try-catch blocks.",
    )

    assert result1["status"] == "needs_work"

    # Verify task in needs_work state
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        assert task.status == ValidationState.NEEDS_WORK
        assert (
            task.last_validation_feedback
            == "Missing error handling. Please add try-catch blocks."
        )

    # Step 3: Worker resumes (manually set status for test)
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        task.status = "running"
        session.commit()

    # Step 4: Transition to under_review again (second iteration)
    validation_orchestrator.transition_to_under_review(
        task_id=validation_enabled_task.id,
        commit_sha=commit_sha,
    )

    # Verify iteration incremented
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        assert task.validation_iteration == 2

    # Get new validator
    validator_id2 = validation_orchestrator._active_validators.get(
        validation_enabled_task.id
    )

    # Step 5: Second review passes
    result2 = validation_orchestrator.give_review(
        task_id=validation_enabled_task.id,
        validator_agent_id=validator_id2,
        validation_passed=True,
        feedback="All issues resolved. Code is ready.",
    )

    assert result2["status"] == "completed"

    # Verify final state
    with db_service.get_session() as session:
        task = session.get(Task, validation_enabled_task.id)
        assert task.status == ValidationState.DONE
        assert task.review_done is True
        assert task.validation_iteration == 2

        # Verify both reviews exist
        reviews = (
            session.query(ValidationReview)
            .filter(ValidationReview.task_id == validation_enabled_task.id)
            .order_by(ValidationReview.iteration_number)
            .all()
        )
        assert len(reviews) == 2
        assert reviews[0].validation_passed is False  # First review failed
        assert reviews[1].validation_passed is True  # Second review passed
