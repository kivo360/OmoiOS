"""Tests for diagnostic system - stuck workflow detection and recovery."""

import pytest

from omoi_os.models.agent import Agent
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.models.workflow_result import WorkflowResult
from omoi_os.services.database import DatabaseService
from omoi_os.services.diagnostic import DiagnosticService
from omoi_os.services.discovery import DiscoveryService
from omoi_os.services.embedding import EmbeddingService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.memory import MemoryService
from omoi_os.services.monitor import MonitorService


@pytest.fixture
def diagnostic_service(
    db_service: DatabaseService,
    event_bus_service: EventBusService,
):
    """Create diagnostic service with all dependencies."""
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
def completed_task(db_service: DatabaseService, sample_task: Task):
    """Create a completed task."""
    with db_service.get_session() as session:
        task = session.get(Task, sample_task.id)
        task.status = "completed"
        session.commit()
        session.refresh(task)
        session.expunge(task)
        return task


# -------------------------------------------------------------------------
# Stuck Workflow Detection Tests
# -------------------------------------------------------------------------


def test_find_stuck_workflows(
    diagnostic_service: DiagnosticService,
    db_service: DatabaseService,
    sample_ticket: Ticket,
    completed_task: Task,
):
    """Test detecting stuck workflows."""
    # Make task older than threshold
    with db_service.get_session() as session:
        task = session.get(Task, completed_task.id)
        # Set completed_at to 10 minutes ago
        from datetime import timedelta
        from omoi_os.utils.datetime import utc_now

        task.completed_at = utc_now() - timedelta(minutes=10)
        session.commit()

    # Find stuck workflows
    stuck = diagnostic_service.find_stuck_workflows(
        cooldown_seconds=1,  # Short cooldown for test
        stuck_threshold_seconds=1,  # Short threshold for test
    )

    # Should find the workflow
    assert len(stuck) > 0
    stuck_workflow = next(
        (w for w in stuck if w["workflow_id"] == sample_ticket.id), None
    )
    assert stuck_workflow is not None
    assert stuck_workflow["total_tasks"] >= 1
    assert stuck_workflow["done_tasks"] >= 1


def test_find_stuck_workflows_with_validated_result(
    diagnostic_service: DiagnosticService,
    db_service: DatabaseService,
    sample_ticket: Ticket,
    completed_task: Task,
    sample_agent: Agent,
):
    """Test that workflows with validated results are not considered stuck."""
    # Create validated WorkflowResult
    with db_service.get_session() as session:
        result = WorkflowResult(
            workflow_id=sample_ticket.id,
            agent_id=sample_agent.id,
            markdown_file_path="/tmp/result.md",
            status="validated",
        )
        session.add(result)
        session.commit()

    # Find stuck workflows
    stuck = diagnostic_service.find_stuck_workflows(
        cooldown_seconds=1,
        stuck_threshold_seconds=1,
    )

    # Should NOT find this workflow
    stuck_workflow = next(
        (w for w in stuck if w["workflow_id"] == sample_ticket.id), None
    )
    assert stuck_workflow is None


def test_find_stuck_workflows_with_active_tasks(
    diagnostic_service: DiagnosticService,
    db_service: DatabaseService,
    sample_ticket: Ticket,
    sample_task: Task,
):
    """Test that workflows with active tasks are not stuck."""
    # Make task running (not completed)
    with db_service.get_session() as session:
        task = session.get(Task, sample_task.id)
        task.status = "running"
        session.commit()

    # Find stuck workflows
    stuck = diagnostic_service.find_stuck_workflows()

    # Should NOT find this workflow (has active task)
    stuck_workflow = next(
        (w for w in stuck if w["workflow_id"] == sample_ticket.id), None
    )
    assert stuck_workflow is None


def test_cooldown_enforcement(
    diagnostic_service: DiagnosticService,
    db_service: DatabaseService,
    sample_ticket: Ticket,
    completed_task: Task,
):
    """Test cooldown prevents repeated diagnostics."""
    # Make task old enough
    with db_service.get_session() as session:
        task = session.get(Task, completed_task.id)
        from datetime import timedelta
        from omoi_os.utils.datetime import utc_now

        task.completed_at = utc_now() - timedelta(minutes=10)
        session.commit()

    # First find should succeed
    stuck1 = diagnostic_service.find_stuck_workflows(
        cooldown_seconds=300,  # 5 minute cooldown
        stuck_threshold_seconds=1,
    )
    assert len(stuck1) > 0

    # Manually mark as having run diagnostic
    diagnostic_service._last_diagnostic[sample_ticket.id] = utc_now().timestamp()

    # Second find should not return it (cooldown)
    stuck2 = diagnostic_service.find_stuck_workflows(
        cooldown_seconds=300,
        stuck_threshold_seconds=1,
    )
    stuck_workflow = next(
        (w for w in stuck2 if w["workflow_id"] == sample_ticket.id), None
    )
    assert stuck_workflow is None


def test_stuck_threshold(
    diagnostic_service: DiagnosticService,
    db_service: DatabaseService,
    sample_ticket: Ticket,
    sample_task: Task,
):
    """Test stuck threshold prevents premature detection."""
    # Task completed recently
    with db_service.get_session() as session:
        task = session.get(Task, sample_task.id)
        task.status = "completed"
        from omoi_os.utils.datetime import utc_now

        task.completed_at = utc_now()  # Just now
        session.commit()

    # Find with high threshold
    stuck = diagnostic_service.find_stuck_workflows(
        cooldown_seconds=1,
        stuck_threshold_seconds=3600,  # 1 hour threshold
    )

    # Should NOT find (not stuck long enough)
    stuck_workflow = next(
        (w for w in stuck if w["workflow_id"] == sample_ticket.id), None
    )
    assert stuck_workflow is None


def test_spawn_diagnostic_agent(
    diagnostic_service: DiagnosticService,
    sample_ticket: Ticket,
):
    """Test spawning a diagnostic agent."""
    context = {
        "workflow_id": sample_ticket.id,
        "total_tasks": 5,
        "done_tasks": 5,
        "failed_tasks": 0,
        "time_stuck_seconds": 300,
        "workflow_goal": "Complete implementation",
    }

    diagnostic_run = diagnostic_service.spawn_diagnostic_agent(
        workflow_id=sample_ticket.id,
        context=context,
    )

    assert diagnostic_run is not None
    assert diagnostic_run.workflow_id == sample_ticket.id
    assert diagnostic_run.total_tasks_at_trigger == 5
    assert diagnostic_run.done_tasks_at_trigger == 5
    assert diagnostic_run.status == "created"


def test_build_diagnostic_context(
    diagnostic_service: DiagnosticService,
    db_service: DatabaseService,
    sample_ticket: Ticket,
    completed_task: Task,
):
    """Test building diagnostic context."""
    context = diagnostic_service.build_diagnostic_context(
        workflow_id=sample_ticket.id,
        max_agents=15,
        max_analyses=5,
    )

    assert context is not None
    assert context["workflow_id"] == sample_ticket.id
    assert "workflow_goal" in context
    assert "total_tasks" in context
    assert "done_tasks" in context
    assert "recent_tasks" in context
    assert "agents_reviewed" in context
    assert "phases_analyzed" in context


def test_complete_diagnostic_run(
    diagnostic_service: DiagnosticService,
    sample_ticket: Ticket,
):
    """Test completing a diagnostic run."""
    # Create diagnostic run
    context = {
        "total_tasks": 5,
        "done_tasks": 5,
        "failed_tasks": 0,
        "time_stuck_seconds": 300,
    }

    diagnostic_run = diagnostic_service.spawn_diagnostic_agent(
        workflow_id=sample_ticket.id,
        context=context,
    )

    # Complete it
    completed = diagnostic_service.complete_diagnostic_run(
        run_id=diagnostic_run.id,
        tasks_created=["task-1", "task-2"],
        diagnosis="Workflow missing result submission",
    )

    assert completed is not None
    assert completed.tasks_created_count == 2
    assert completed.status == "completed"
    assert completed.diagnosis == "Workflow missing result submission"
    assert completed.completed_at is not None


def test_diagnostic_run_tracking(
    diagnostic_service: DiagnosticService,
    sample_ticket: Ticket,
):
    """Test tracking multiple diagnostic runs."""
    # Create two diagnostic runs
    context1 = {
        "total_tasks": 5,
        "done_tasks": 5,
        "failed_tasks": 0,
        "time_stuck_seconds": 300,
    }
    context2 = {
        "total_tasks": 6,
        "done_tasks": 6,
        "failed_tasks": 0,
        "time_stuck_seconds": 600,
    }

    run1 = diagnostic_service.spawn_diagnostic_agent(sample_ticket.id, context1)
    run2 = diagnostic_service.spawn_diagnostic_agent(sample_ticket.id, context2)

    # Get all runs
    runs = diagnostic_service.get_diagnostic_runs(
        workflow_id=sample_ticket.id, limit=100
    )

    assert len(runs) == 2
    # Should be sorted by most recent first
    assert runs[0].id == run2.id
    assert runs[1].id == run1.id


def test_diagnostic_integration_with_discovery(
    diagnostic_service: DiagnosticService,
    db_service: DatabaseService,
    sample_ticket: Ticket,
    completed_task: Task,
):
    """Test diagnostic uses Discovery to spawn recovery tasks."""
    # Spawn diagnostic with recovery task
    with db_service.get_session() as session:
        # Use spawn_diagnostic_recovery from discovery service
        recovery_task = diagnostic_service.discovery.spawn_diagnostic_recovery(
            session=session,
            ticket_id=sample_ticket.id,
            diagnostic_run_id="test-run-123",
            reason="Workflow stuck - missing result",
            suggested_phase="PHASE_FINAL",
            suggested_priority="HIGH",
        )

        session.commit()
        session.refresh(recovery_task)
        session.expunge(recovery_task)

    # Verify task was created
    assert recovery_task is not None
    assert recovery_task.ticket_id == sample_ticket.id
    assert recovery_task.priority == "HIGH"
    assert "Diagnostic recovery" in recovery_task.description
