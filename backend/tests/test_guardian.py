"""Tests for Guardian intervention system."""

import pytest

from omoi_os.models.agent import Agent
from omoi_os.models.guardian_action import AuthorityLevel, GuardianAction
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.guardian import GuardianService


@pytest.fixture
def guardian_service(db_service: DatabaseService, event_bus_service: EventBusService):
    """Create a guardian service for testing."""
    return GuardianService(db=db_service, event_bus=event_bus_service)


@pytest.fixture
def running_task(db_service: DatabaseService, sample_task: Task):
    """Create a running task for intervention tests."""
    with db_service.get_session() as session:
        task = session.get(Task, sample_task.id)
        task.status = "running"
        task.assigned_agent_id = "test-agent-1"
        session.commit()
        session.refresh(task)
        session.expunge(task)
        return task


@pytest.fixture
def guardian_agent(db_service: DatabaseService):
    """Create a guardian agent."""
    with db_service.get_session() as session:
        agent = Agent(
            agent_type="guardian",
            phase_id=None,
            status="idle",
            capabilities=["emergency_intervention", "resource_management"],
            capacity=1,
            health_status="healthy",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
        session.expunge(agent)
        return agent


# -------------------------------------------------------------------------
# Emergency Task Cancellation Tests
# -------------------------------------------------------------------------


def test_emergency_cancel_task_success(
    guardian_service: GuardianService,
    db_service: DatabaseService,
    running_task: Task,
    guardian_agent: Agent,
):
    """Test successful emergency task cancellation."""
    action = guardian_service.emergency_cancel_task(
        task_id=running_task.id,
        reason="Agent failure during critical operation",
        initiated_by=guardian_agent.id,
        authority=AuthorityLevel.GUARDIAN,
    )

    assert action is not None
    assert action.action_type == "cancel_task"
    assert action.target_entity == running_task.id
    assert action.authority_level == AuthorityLevel.GUARDIAN
    assert action.initiated_by == guardian_agent.id
    assert action.executed_at is not None

    # Verify task was cancelled
    with db_service.get_session() as session:
        task = session.get(Task, running_task.id)
        assert task.status == "failed"
        assert "EMERGENCY CANCELLATION" in task.error_message


def test_emergency_cancel_task_not_found(
    guardian_service: GuardianService,
    guardian_agent: Agent,
):
    """Test cancelling a non-existent task returns None."""
    action = guardian_service.emergency_cancel_task(
        task_id="non-existent-task",
        reason="Test",
        initiated_by=guardian_agent.id,
        authority=AuthorityLevel.GUARDIAN,
    )

    assert action is None


def test_emergency_cancel_task_insufficient_authority(
    guardian_service: GuardianService,
    running_task: Task,
):
    """Test cancellation with insufficient authority raises PermissionError."""
    with pytest.raises(PermissionError, match="GUARDIAN authority"):
        guardian_service.emergency_cancel_task(
            task_id=running_task.id,
            reason="Test",
            initiated_by="worker-agent",
            authority=AuthorityLevel.WORKER,
        )


def test_emergency_cancel_task_audit_log(
    guardian_service: GuardianService,
    db_service: DatabaseService,
    running_task: Task,
    guardian_agent: Agent,
):
    """Test that cancellation creates proper audit trail."""
    action = guardian_service.emergency_cancel_task(
        task_id=running_task.id,
        reason="System resource exhaustion",
        initiated_by=guardian_agent.id,
        authority=AuthorityLevel.GUARDIAN,
    )

    assert action.audit_log is not None
    assert "before" in action.audit_log
    assert "after" in action.audit_log
    assert action.audit_log["before"]["status"] == "running"
    assert action.audit_log["after"]["status"] == "failed"


# -------------------------------------------------------------------------
# Agent Capacity Reallocation Tests
# -------------------------------------------------------------------------


def test_reallocate_agent_capacity_success(
    guardian_service: GuardianService,
    db_service: DatabaseService,
    sample_agent: Agent,
    guardian_agent: Agent,
):
    """Test successful capacity reallocation between agents."""
    # Create a second agent
    with db_service.get_session() as session:
        target_agent = Agent(
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            status="idle",
            capabilities=["python"],
            capacity=1,
            health_status="healthy",
        )
        session.add(target_agent)
        session.commit()
        session.refresh(target_agent)
        target_agent_id = target_agent.id
        session.expunge(target_agent)

    # Reallocate 1 capacity from sample_agent (has 2) to target_agent (has 1)
    action = guardian_service.reallocate_agent_capacity(
        from_agent_id=sample_agent.id,
        to_agent_id=target_agent_id,
        capacity=1,
        reason="Critical task needs immediate attention",
        initiated_by=guardian_agent.id,
        authority=AuthorityLevel.GUARDIAN,
    )

    assert action is not None
    assert action.action_type == "reallocate_capacity"
    assert action.authority_level == AuthorityLevel.GUARDIAN

    # Verify capacity changes
    with db_service.get_session() as session:
        from_agent = session.get(Agent, sample_agent.id)
        to_agent = session.get(Agent, target_agent_id)
        assert from_agent.capacity == 1  # Was 2, now 1
        assert to_agent.capacity == 2  # Was 1, now 2


def test_reallocate_capacity_insufficient_capacity(
    guardian_service: GuardianService,
    sample_agent: Agent,
    guardian_agent: Agent,
):
    """Test reallocation fails when source agent has insufficient capacity."""
    with pytest.raises(ValueError, match="insufficient capacity"):
        guardian_service.reallocate_agent_capacity(
            from_agent_id=sample_agent.id,
            to_agent_id=guardian_agent.id,
            capacity=10,  # sample_agent only has 2
            reason="Test",
            initiated_by=guardian_agent.id,
            authority=AuthorityLevel.GUARDIAN,
        )


def test_reallocate_capacity_invalid_capacity(
    guardian_service: GuardianService,
    sample_agent: Agent,
    guardian_agent: Agent,
):
    """Test reallocation with invalid capacity value."""
    with pytest.raises(ValueError, match="Capacity must be positive"):
        guardian_service.reallocate_agent_capacity(
            from_agent_id=sample_agent.id,
            to_agent_id=guardian_agent.id,
            capacity=0,
            reason="Test",
            initiated_by=guardian_agent.id,
            authority=AuthorityLevel.GUARDIAN,
        )


def test_reallocate_capacity_agents_not_found(
    guardian_service: GuardianService,
    guardian_agent: Agent,
):
    """Test reallocation with non-existent agents."""
    action = guardian_service.reallocate_agent_capacity(
        from_agent_id="non-existent-1",
        to_agent_id="non-existent-2",
        capacity=1,
        reason="Test",
        initiated_by=guardian_agent.id,
        authority=AuthorityLevel.GUARDIAN,
    )

    assert action is None


# -------------------------------------------------------------------------
# Priority Override Tests
# -------------------------------------------------------------------------


def test_override_task_priority_success(
    guardian_service: GuardianService,
    db_service: DatabaseService,
    sample_task: Task,
    guardian_agent: Agent,
):
    """Test successful priority override."""
    # Task starts with MEDIUM priority
    assert sample_task.priority == "MEDIUM"

    action = guardian_service.override_task_priority(
        task_id=sample_task.id,
        new_priority="CRITICAL",
        reason="Production incident requires immediate attention",
        initiated_by=guardian_agent.id,
        authority=AuthorityLevel.GUARDIAN,
    )

    assert action is not None
    assert action.action_type == "override_priority"
    assert action.audit_log["old_priority"] == "MEDIUM"
    assert action.audit_log["new_priority"] == "CRITICAL"

    # Verify priority was changed
    with db_service.get_session() as session:
        task = session.get(Task, sample_task.id)
        assert task.priority == "CRITICAL"


def test_override_priority_invalid_value(
    guardian_service: GuardianService,
    sample_task: Task,
    guardian_agent: Agent,
):
    """Test priority override with invalid priority value."""
    with pytest.raises(ValueError, match="Invalid priority"):
        guardian_service.override_task_priority(
            task_id=sample_task.id,
            new_priority="SUPER_ULTRA_HIGH",
            reason="Test",
            initiated_by=guardian_agent.id,
            authority=AuthorityLevel.GUARDIAN,
        )


def test_override_priority_insufficient_authority(
    guardian_service: GuardianService,
    sample_task: Task,
):
    """Test priority override with insufficient authority."""
    with pytest.raises(PermissionError, match="GUARDIAN authority"):
        guardian_service.override_task_priority(
            task_id=sample_task.id,
            new_priority="CRITICAL",
            reason="Test",
            initiated_by="watchdog-agent",
            authority=AuthorityLevel.WATCHDOG,
        )


# -------------------------------------------------------------------------
# Rollback and Audit Tests
# -------------------------------------------------------------------------


def test_revert_intervention_success(
    guardian_service: GuardianService,
    db_service: DatabaseService,
    running_task: Task,
    guardian_agent: Agent,
):
    """Test reverting a guardian intervention."""
    # First, create an intervention
    action = guardian_service.emergency_cancel_task(
        task_id=running_task.id,
        reason="Test intervention",
        initiated_by=guardian_agent.id,
        authority=AuthorityLevel.GUARDIAN,
    )

    assert action.reverted_at is None

    # Now revert it
    success = guardian_service.revert_intervention(
        action_id=action.id,
        reason="Crisis resolved, restoring normal operation",
        initiated_by=guardian_agent.id,
    )

    assert success is True

    # Verify reversion was recorded
    with db_service.get_session() as session:
        reverted_action = session.get(GuardianAction, action.id)
        assert reverted_action.reverted_at is not None
        assert "revert_reason" in reverted_action.audit_log


def test_revert_intervention_not_found(
    guardian_service: GuardianService,
    guardian_agent: Agent,
):
    """Test reverting a non-existent intervention."""
    success = guardian_service.revert_intervention(
        action_id="non-existent-action",
        reason="Test",
        initiated_by=guardian_agent.id,
    )

    assert success is False


def test_revert_intervention_already_reverted(
    guardian_service: GuardianService,
    running_task: Task,
    guardian_agent: Agent,
):
    """Test reverting an already-reverted intervention."""
    # Create and revert an intervention
    action = guardian_service.emergency_cancel_task(
        task_id=running_task.id,
        reason="Test",
        initiated_by=guardian_agent.id,
        authority=AuthorityLevel.GUARDIAN,
    )

    guardian_service.revert_intervention(
        action_id=action.id,
        reason="First revert",
        initiated_by=guardian_agent.id,
    )

    # Try to revert again
    success = guardian_service.revert_intervention(
        action_id=action.id,
        reason="Second revert",
        initiated_by=guardian_agent.id,
    )

    assert success is False


def test_get_actions_audit_trail(
    guardian_service: GuardianService,
    running_task: Task,
    sample_task: Task,
    guardian_agent: Agent,
):
    """Test retrieving guardian action audit trail."""
    # Create multiple interventions
    guardian_service.emergency_cancel_task(
        task_id=running_task.id,
        reason="Test 1",
        initiated_by=guardian_agent.id,
        authority=AuthorityLevel.GUARDIAN,
    )

    guardian_service.override_task_priority(
        task_id=sample_task.id,
        new_priority="CRITICAL",
        reason="Test 2",
        initiated_by=guardian_agent.id,
        authority=AuthorityLevel.GUARDIAN,
    )

    # Get all actions
    actions = guardian_service.get_actions(limit=100)

    assert len(actions) == 2
    # Should be sorted by most recent first
    assert actions[0].action_type == "override_priority"
    assert actions[1].action_type == "cancel_task"


def test_get_actions_filtered_by_type(
    guardian_service: GuardianService,
    running_task: Task,
    sample_task: Task,
    guardian_agent: Agent,
):
    """Test filtering action audit trail by type."""
    guardian_service.emergency_cancel_task(
        task_id=running_task.id,
        reason="Test 1",
        initiated_by=guardian_agent.id,
        authority=AuthorityLevel.GUARDIAN,
    )

    guardian_service.override_task_priority(
        task_id=sample_task.id,
        new_priority="CRITICAL",
        reason="Test 2",
        initiated_by=guardian_agent.id,
        authority=AuthorityLevel.GUARDIAN,
    )

    # Filter by action type
    cancel_actions = guardian_service.get_actions(action_type="cancel_task")
    assert len(cancel_actions) == 1
    assert cancel_actions[0].action_type == "cancel_task"

    override_actions = guardian_service.get_actions(action_type="override_priority")
    assert len(override_actions) == 1
    assert override_actions[0].action_type == "override_priority"


def test_get_action_by_id(
    guardian_service: GuardianService,
    running_task: Task,
    guardian_agent: Agent,
):
    """Test retrieving a specific guardian action by ID."""
    action = guardian_service.emergency_cancel_task(
        task_id=running_task.id,
        reason="Test intervention",
        initiated_by=guardian_agent.id,
        authority=AuthorityLevel.GUARDIAN,
    )

    retrieved = guardian_service.get_action(action.id)

    assert retrieved is not None
    assert retrieved.id == action.id
    assert retrieved.action_type == "cancel_task"
    assert retrieved.target_entity == running_task.id
