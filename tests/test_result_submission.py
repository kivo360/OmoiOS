"""Tests for result submission system (task-level and workflow-level)."""

import os
import tempfile

import pytest

from omoi_os.models.agent import Agent
from omoi_os.models.agent_result import AgentResult
from omoi_os.models.task import Task
from omoi_os.models.workflow_result import WorkflowResult
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.phase_loader import PhaseLoader
from omoi_os.services.result_submission import ResultSubmissionService


@pytest.fixture
def result_service(db_service: DatabaseService, event_bus_service: EventBusService):
    """Create a result submission service for testing."""
    phase_loader = PhaseLoader()
    return ResultSubmissionService(db=db_service, event_bus=event_bus_service, phase_loader=phase_loader)


@pytest.fixture
def temp_markdown_file():
    """Create a temporary markdown file for testing."""
    content = "# Test Results\n\nThis is a test result file."
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def large_markdown_file():
    """Create a markdown file larger than 100KB."""
    content = "# Large File\n\n" + ("A" * 110 * 1024)  # 110KB
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


# -------------------------------------------------------------------------
# Task-Level Results (AgentResult) Tests
# -------------------------------------------------------------------------


def test_report_task_result_success(
    result_service: ResultSubmissionService,
    db_service: DatabaseService,
    sample_agent: Agent,
    sample_task: Task,
    temp_markdown_file: str,
):
    """Test successful task result submission."""
    # Assign task to agent
    with db_service.get_session() as session:
        task = session.get(Task, sample_task.id)
        task.assigned_agent_id = sample_agent.id
        session.commit()

    # Submit result
    result = result_service.report_task_result(
        agent_id=sample_agent.id,
        task_id=sample_task.id,
        markdown_file_path=temp_markdown_file,
        result_type="implementation",
        summary="Test implementation complete",
    )

    assert result is not None
    assert result.agent_id == sample_agent.id
    assert result.task_id == sample_task.id
    assert result.result_type == "implementation"
    assert result.verification_status == "unverified"
    assert result.markdown_content == "# Test Results\n\nThis is a test result file."


def test_report_task_result_file_not_found(
    result_service: ResultSubmissionService,
    db_service: DatabaseService,
    sample_agent: Agent,
    sample_task: Task,
):
    """Test result submission with non-existent file."""
    # Assign task to agent first
    with db_service.get_session() as session:
        task = session.get(Task, sample_task.id)
        task.assigned_agent_id = sample_agent.id
        session.commit()

    with pytest.raises(FileNotFoundError):
        result_service.report_task_result(
            agent_id=sample_agent.id,
            task_id=sample_task.id,
            markdown_file_path="/nonexistent/file.md",
            result_type="implementation",
            summary="Test",
        )


def test_report_task_result_file_too_large(
    result_service: ResultSubmissionService,
    db_service: DatabaseService,
    sample_agent: Agent,
    sample_task: Task,
    large_markdown_file: str,
):
    """Test result submission with file exceeding 100KB limit."""
    # Assign task to agent
    with db_service.get_session() as session:
        task = session.get(Task, sample_task.id)
        task.assigned_agent_id = sample_agent.id
        session.commit()

    with pytest.raises(ValueError, match="too large"):
        result_service.report_task_result(
            agent_id=sample_agent.id,
            task_id=sample_task.id,
            markdown_file_path=large_markdown_file,
            result_type="implementation",
            summary="Test",
        )


def test_report_task_result_not_markdown(
    result_service: ResultSubmissionService,
    db_service: DatabaseService,
    sample_agent: Agent,
    sample_task: Task,
):
    """Test result submission with non-markdown file."""
    # Create a .txt file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test content")
        txt_path = f.name

    try:
        # Assign task to agent
        with db_service.get_session() as session:
            task = session.get(Task, sample_task.id)
            task.assigned_agent_id = sample_agent.id
            session.commit()

        with pytest.raises(ValueError, match="markdown"):
            result_service.report_task_result(
                agent_id=sample_agent.id,
                task_id=sample_task.id,
                markdown_file_path=txt_path,
                result_type="implementation",
                summary="Test",
            )
    finally:
        if os.path.exists(txt_path):
            os.unlink(txt_path)


def test_report_task_result_path_traversal(
    result_service: ResultSubmissionService,
    db_service: DatabaseService,
    sample_agent: Agent,
    sample_task: Task,
):
    """Test result submission blocks path traversal."""
    # Assign task to agent first
    with db_service.get_session() as session:
        task = session.get(Task, sample_task.id)
        task.assigned_agent_id = sample_agent.id
        session.commit()

    with pytest.raises(ValueError, match="traversal"):
        result_service.report_task_result(
            agent_id=sample_agent.id,
            task_id=sample_task.id,
            markdown_file_path="../../../etc/passwd.md",
            result_type="implementation",
            summary="Test",
        )


def test_report_task_result_wrong_agent(
    result_service: ResultSubmissionService,
    db_service: DatabaseService,
    sample_agent: Agent,
    sample_task: Task,
    temp_markdown_file: str,
):
    """Test result submission by agent that doesn't own the task."""
    # Create another agent
    with db_service.get_session() as session:
        other_agent = Agent(
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            status="idle",
            capabilities=["python"],
            capacity=1,
            health_status="healthy",
        )
        session.add(other_agent)
        session.commit()
        other_agent_id = other_agent.id

        # Assign task to sample_agent
        task = session.get(Task, sample_task.id)
        task.assigned_agent_id = sample_agent.id
        session.commit()

    # Try to submit result as other_agent
    with pytest.raises(ValueError, match="not assigned"):
        result_service.report_task_result(
            agent_id=other_agent_id,
            task_id=sample_task.id,
            markdown_file_path=temp_markdown_file,
            result_type="implementation",
            summary="Test",
        )


def test_multiple_results_per_task(
    result_service: ResultSubmissionService,
    db_service: DatabaseService,
    sample_agent: Agent,
    sample_task: Task,
):
    """Test submitting multiple results for the same task."""
    # Assign task to agent
    with db_service.get_session() as session:
        task = session.get(Task, sample_task.id)
        task.assigned_agent_id = sample_agent.id
        session.commit()

    # Create two temp files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Result 1")
        file1 = f.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Result 2")
        file2 = f.name

    try:
        # Submit first result
        result1 = result_service.report_task_result(
            agent_id=sample_agent.id,
            task_id=sample_task.id,
            markdown_file_path=file1,
            result_type="implementation",
            summary="First result",
        )

        # Submit second result
        result2 = result_service.report_task_result(
            agent_id=sample_agent.id,
            task_id=sample_task.id,
            markdown_file_path=file2,
            result_type="analysis",
            summary="Second result",
        )

        # Both should exist
        assert result1 is not None
        assert result2 is not None
        assert result1.id != result2.id

        # Get all results
        results = result_service.get_task_results(sample_task.id)
        assert len(results) == 2

    finally:
        os.unlink(file1)
        os.unlink(file2)


def test_verify_task_result(
    result_service: ResultSubmissionService,
    db_service: DatabaseService,
    sample_agent: Agent,
    sample_task: Task,
    temp_markdown_file: str,
):
    """Test verifying a task result."""
    # Assign and submit result
    with db_service.get_session() as session:
        task = session.get(Task, sample_task.id)
        task.assigned_agent_id = sample_agent.id
        session.commit()

    result = result_service.report_task_result(
        agent_id=sample_agent.id,
        task_id=sample_task.id,
        markdown_file_path=temp_markdown_file,
        result_type="implementation",
        summary="Test",
    )

    assert result.verification_status == "unverified"

    # Verify result
    verified_result = result_service.verify_task_result(
        result_id=result.id,
        validation_review_id="review-123",
        verified=True,
    )

    assert verified_result is not None
    assert verified_result.verification_status == "verified"
    assert verified_result.verified_at is not None
    assert verified_result.verified_by_validation_id == "review-123"


# -------------------------------------------------------------------------
# Workflow-Level Results (WorkflowResult) Tests
# -------------------------------------------------------------------------


def test_submit_workflow_result(
    result_service: ResultSubmissionService,
    sample_ticket,
    sample_agent: Agent,
    temp_markdown_file: str,
):
    """Test successful workflow result submission."""
    result = result_service.submit_workflow_result(
        workflow_id=sample_ticket.id,
        agent_id=sample_agent.id,
        markdown_file_path=temp_markdown_file,
        explanation="Found the solution",
        evidence=["Evidence 1", "Evidence 2"],
    )

    assert result is not None
    assert result.workflow_id == sample_ticket.id
    assert result.agent_id == sample_agent.id
    assert result.status == "pending_validation"
    assert result.explanation == "Found the solution"
    assert result.evidence == {"items": ["Evidence 1", "Evidence 2"]}


def test_validate_workflow_result_pass(
    result_service: ResultSubmissionService,
    sample_ticket,
    sample_agent: Agent,
    temp_markdown_file: str,
):
    """Test validating a workflow result as passed."""
    # Submit result
    result = result_service.submit_workflow_result(
        workflow_id=sample_ticket.id,
        agent_id=sample_agent.id,
        markdown_file_path=temp_markdown_file,
    )

    # Validate as passed
    validation_result = result_service.validate_workflow_result(
        result_id=result.id,
        passed=True,
        feedback="All criteria met",
        evidence=[{"criterion": "test", "passed": True}],
        validator_agent_id="validator-123",
    )

    assert validation_result["passed"] is True
    assert validation_result["validation_status"] == "validated"
    assert "action_taken" in validation_result


def test_validate_workflow_result_fail(
    result_service: ResultSubmissionService,
    sample_ticket,
    sample_agent: Agent,
    temp_markdown_file: str,
):
    """Test validating a workflow result as failed."""
    # Submit result
    result = result_service.submit_workflow_result(
        workflow_id=sample_ticket.id,
        agent_id=sample_agent.id,
        markdown_file_path=temp_markdown_file,
    )

    # Validate as failed
    validation_result = result_service.validate_workflow_result(
        result_id=result.id,
        passed=False,
        feedback="Missing evidence",
        evidence=[{"criterion": "test", "passed": False}],
        validator_agent_id="validator-123",
    )

    assert validation_result["passed"] is False
    assert validation_result["validation_status"] == "rejected"


def test_list_workflow_results(
    result_service: ResultSubmissionService,
    sample_ticket,
    sample_agent: Agent,
):
    """Test listing all results for a workflow."""
    # Create two temp files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Result 1")
        file1 = f.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Result 2")
        file2 = f.name

    try:
        # Submit two results
        result_service.submit_workflow_result(
            workflow_id=sample_ticket.id,
            agent_id=sample_agent.id,
            markdown_file_path=file1,
        )

        result_service.submit_workflow_result(
            workflow_id=sample_ticket.id,
            agent_id=sample_agent.id,
            markdown_file_path=file2,
        )

        # List results
        results = result_service.list_workflow_results(sample_ticket.id)
        assert len(results) == 2

    finally:
        os.unlink(file1)
        os.unlink(file2)


def test_workflow_result_immutability(
    result_service: ResultSubmissionService,
    sample_ticket,
    sample_agent: Agent,
    temp_markdown_file: str,
):
    """Test that workflow results are immutable after creation."""
    # Submit result
    result = result_service.submit_workflow_result(
        workflow_id=sample_ticket.id,
        agent_id=sample_agent.id,
        markdown_file_path=temp_markdown_file,
    )

    # Verify we can't update (would need a new submission)
    # Results are append-only - new submissions create new records
    
    # Submit another result (version 2)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Updated Result")
        updated_file = f.name

    try:
        result2 = result_service.submit_workflow_result(
            workflow_id=sample_ticket.id,
            agent_id=sample_agent.id,
            markdown_file_path=updated_file,
        )

        # Should be a separate record
        assert result2.id != result.id

        # Both should exist
        results = result_service.list_workflow_results(sample_ticket.id)
        assert len(results) == 2

    finally:
        os.unlink(updated_file)

