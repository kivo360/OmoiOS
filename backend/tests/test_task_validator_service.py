"""Unit tests for TaskValidatorService.

Tests the core validation service that spawns validators and handles results.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from omoi_os.models.agent import Agent
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.models.project import Project
from omoi_os.models.user import User
from omoi_os.models.validation_review import ValidationReview
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.task_validator import TaskValidatorService, get_task_validator


@pytest.fixture
def task_validator(db_service: DatabaseService, event_bus_service: EventBusService):
    """Create a TaskValidatorService for testing."""
    # Ensure validation is enabled for tests
    os.environ["TASK_VALIDATION_ENABLED"] = "true"
    os.environ["MAX_VALIDATION_ITERATIONS"] = "3"
    return TaskValidatorService(db=db_service, event_bus=event_bus_service)


@pytest.fixture
def task_validator_disabled(db_service: DatabaseService, event_bus_service: EventBusService):
    """Create a TaskValidatorService with validation disabled."""
    os.environ["TASK_VALIDATION_ENABLED"] = "false"
    validator = TaskValidatorService(db=db_service, event_bus=event_bus_service)
    # Reset for other tests
    os.environ["TASK_VALIDATION_ENABLED"] = "true"
    return validator


@pytest.fixture
def sample_project(db_service: DatabaseService, test_user: User) -> Project:
    """Create a sample project with GitHub info."""
    with db_service.get_session() as session:
        # Update user with GitHub token
        user = session.get(User, test_user.id)
        user.attributes = {"github_access_token": "ghp_test_token_12345"}
        session.commit()

        project = Project(
            name="Test Project",
            github_owner="test-owner",
            github_repo="test-repo",
            created_by=test_user.id,
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        session.expunge(project)
        return project


@pytest.fixture
def sample_ticket_with_project(db_service: DatabaseService, sample_project: Project) -> Ticket:
    """Create a sample ticket linked to a project."""
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            description="Test description",
            phase_id="PHASE_IMPLEMENTATION",
            status="in_progress",
            project_id=sample_project.id,
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.expunge(ticket)
        return ticket


@pytest.fixture
def running_task_with_sandbox(db_service: DatabaseService, sample_ticket_with_project: Ticket) -> Task:
    """Create a running task with sandbox_id and branch_name."""
    with db_service.get_session() as session:
        task = Task(
            ticket_id=sample_ticket_with_project.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Test task",
            status="running",
            sandbox_id=f"sandbox-{uuid4().hex[:8]}",
            result={"branch_name": "feature/test-branch"},
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        session.expunge(task)
        return task


# -------------------------------------------------------------------------
# request_validation Tests
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_validation_creates_pending_status(
    task_validator: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
):
    """Test that request_validation sets task status to pending_validation."""
    # Mock the spawner to avoid external calls
    with patch.object(task_validator, '_spawn_validator', new_callable=AsyncMock) as mock_spawn:
        mock_spawn.return_value = {
            "sandbox_id": "validator-sandbox-123",
            "agent_id": str(uuid4()),
        }

        validation_id = await task_validator.request_validation(
            task_id=str(running_task_with_sandbox.id),
            sandbox_id=running_task_with_sandbox.sandbox_id,
            implementation_result={"success": True, "branch_name": "feature/test"},
        )

        assert validation_id  # Non-empty

        # Verify task status updated
        with db_service.get_session() as session:
            task = session.get(Task, running_task_with_sandbox.id)
            assert task.status == "pending_validation"
            assert task.result.get("validation_iteration") == 1
            assert task.result.get("implementation_result") == {
                "success": True,
                "branch_name": "feature/test",
            }


@pytest.mark.asyncio
async def test_request_validation_increments_iteration(
    task_validator: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
):
    """Test that validation_iteration increments on each validation request."""
    task_id = str(running_task_with_sandbox.id)
    sandbox_id = running_task_with_sandbox.sandbox_id

    with patch.object(task_validator, '_spawn_validator', new_callable=AsyncMock) as mock_spawn:
        mock_spawn.return_value = {"sandbox_id": "v-1", "agent_id": str(uuid4())}

        # First validation
        await task_validator.request_validation(
            task_id=task_id,
            sandbox_id=sandbox_id,
            implementation_result={"success": True},
        )

        with db_service.get_session() as session:
            task = session.get(Task, running_task_with_sandbox.id)
            assert task.result.get("validation_iteration") == 1
            # Reset status for next validation
            task.status = "running"
            session.commit()

        # Add a validation review to simulate completed validation
        with db_service.get_session() as session:
            review = ValidationReview(
                task_id=task_id,
                validator_agent_id=str(uuid4()),
                iteration_number=1,
                validation_passed=False,
                feedback="First validation failed",
            )
            session.add(review)
            session.commit()

        # Second validation
        mock_spawn.return_value = {"sandbox_id": "v-2", "agent_id": str(uuid4())}
        await task_validator.request_validation(
            task_id=task_id,
            sandbox_id=sandbox_id,
            implementation_result={"success": True},
        )

        with db_service.get_session() as session:
            task = session.get(Task, running_task_with_sandbox.id)
            assert task.result.get("validation_iteration") == 2


@pytest.mark.asyncio
async def test_request_validation_fails_after_max_iterations(
    db_service: DatabaseService,
    event_bus_service: EventBusService,
    running_task_with_sandbox: Task,
):
    """Test that task fails after exceeding MAX_VALIDATION_ITERATIONS."""
    # Set low max iterations for test
    os.environ["MAX_VALIDATION_ITERATIONS"] = "2"
    task_validator = TaskValidatorService(db=db_service, event_bus=event_bus_service)

    task_id = str(running_task_with_sandbox.id)

    # Add 2 validation reviews (max)
    with db_service.get_session() as session:
        for i in range(2):
            review = ValidationReview(
                task_id=task_id,
                validator_agent_id=str(uuid4()),
                iteration_number=i + 1,
                validation_passed=False,
                feedback=f"Validation {i+1} failed",
            )
            session.add(review)
        session.commit()

    # Third validation request should fail the task
    result = await task_validator.request_validation(
        task_id=task_id,
        sandbox_id=running_task_with_sandbox.sandbox_id,
        implementation_result={"success": True},
    )

    assert result == ""  # Empty string indicates failure

    with db_service.get_session() as session:
        task = session.get(Task, running_task_with_sandbox.id)
        assert task.status == "failed"
        assert "Failed validation after 2 iterations" in task.error_message

    # Reset env
    os.environ["MAX_VALIDATION_ITERATIONS"] = "3"


@pytest.mark.asyncio
async def test_request_validation_disabled_auto_approves(
    task_validator_disabled: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
):
    """Test that validation disabled auto-approves the task."""
    result = await task_validator_disabled.request_validation(
        task_id=str(running_task_with_sandbox.id),
        sandbox_id=running_task_with_sandbox.sandbox_id,
        implementation_result={"success": True, "output": "Done!"},
    )

    assert result == "auto-approved"

    with db_service.get_session() as session:
        task = session.get(Task, running_task_with_sandbox.id)
        assert task.status == "completed"
        assert task.result.get("auto_approved") is True
        assert task.result.get("output") == "Done!"


@pytest.mark.asyncio
async def test_request_validation_stores_validator_info(
    task_validator: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
):
    """Test that validator sandbox_id and agent_id are stored in task.result."""
    validator_sandbox_id = "validator-sandbox-xyz"
    validator_agent_id = str(uuid4())

    with patch.object(task_validator, '_spawn_validator', new_callable=AsyncMock) as mock_spawn:
        mock_spawn.return_value = {
            "sandbox_id": validator_sandbox_id,
            "agent_id": validator_agent_id,
        }

        await task_validator.request_validation(
            task_id=str(running_task_with_sandbox.id),
            sandbox_id=running_task_with_sandbox.sandbox_id,
            implementation_result={"success": True},
        )

        with db_service.get_session() as session:
            task = session.get(Task, running_task_with_sandbox.id)
            assert task.result.get("validator_sandbox_id") == validator_sandbox_id
            assert task.result.get("validator_agent_id") == validator_agent_id


# -------------------------------------------------------------------------
# handle_validation_result Tests
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_validation_result_passed(
    task_validator: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
):
    """Test that passing validation marks task as completed."""
    task_id = str(running_task_with_sandbox.id)
    validator_agent_id = str(uuid4())

    # Set task to pending_validation
    with db_service.get_session() as session:
        task = session.get(Task, running_task_with_sandbox.id)
        task.status = "pending_validation"
        session.commit()

    await task_validator.handle_validation_result(
        task_id=task_id,
        validator_agent_id=validator_agent_id,
        passed=True,
        feedback="All checks passed. Code is production-ready.",
        evidence={"tests": "passed", "build": "success"},
    )

    with db_service.get_session() as session:
        task = session.get(Task, running_task_with_sandbox.id)
        assert task.status == "completed"
        assert task.result.get("validation_passed") is True
        assert task.result.get("validated_at") is not None


@pytest.mark.asyncio
async def test_handle_validation_result_failed(
    task_validator: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
):
    """Test that failing validation marks task as needs_revision."""
    task_id = str(running_task_with_sandbox.id)
    validator_agent_id = str(uuid4())
    feedback = "Tests are failing: 3 unit tests failed"
    recommendations = ["Fix test_foo", "Fix test_bar"]

    # Set task to pending_validation
    with db_service.get_session() as session:
        task = session.get(Task, running_task_with_sandbox.id)
        task.status = "pending_validation"
        session.commit()

    await task_validator.handle_validation_result(
        task_id=task_id,
        validator_agent_id=validator_agent_id,
        passed=False,
        feedback=feedback,
        evidence={"test_output": "FAILED test_foo, test_bar, test_baz"},
        recommendations=recommendations,
    )

    with db_service.get_session() as session:
        task = session.get(Task, running_task_with_sandbox.id)
        assert task.status == "needs_revision"
        assert task.result.get("validation_passed") is False
        assert task.result.get("revision_feedback") == feedback
        assert task.result.get("revision_recommendations") == recommendations


@pytest.mark.asyncio
async def test_handle_validation_result_creates_review_record(
    task_validator: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
):
    """Test that validation result creates a ValidationReview record."""
    task_id = str(running_task_with_sandbox.id)
    validator_agent_id = str(uuid4())
    feedback = "All checks passed!"
    evidence = {"tests": "passed", "build": "success"}

    await task_validator.handle_validation_result(
        task_id=task_id,
        validator_agent_id=validator_agent_id,
        passed=True,
        feedback=feedback,
        evidence=evidence,
    )

    with db_service.get_session() as session:
        reviews = (
            session.query(ValidationReview)
            .filter(ValidationReview.task_id == task_id)
            .all()
        )
        assert len(reviews) == 1
        review = reviews[0]
        assert review.validator_agent_id == validator_agent_id
        assert review.validation_passed is True
        assert review.feedback == feedback
        assert review.evidence == evidence
        assert review.iteration_number == 1


@pytest.mark.asyncio
async def test_handle_validation_result_publishes_passed_event(
    task_validator: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
    event_bus_service: EventBusService,
):
    """Test that passing validation publishes TASK_VALIDATION_PASSED event."""
    task_id = str(running_task_with_sandbox.id)

    with patch.object(event_bus_service, 'publish') as mock_publish:
        await task_validator.handle_validation_result(
            task_id=task_id,
            validator_agent_id=str(uuid4()),
            passed=True,
            feedback="All checks passed!",
        )

        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert event.event_type == "TASK_VALIDATION_PASSED"
        assert event.entity_id == task_id
        assert event.payload["feedback"] == "All checks passed!"


@pytest.mark.asyncio
async def test_handle_validation_result_publishes_failed_event(
    task_validator: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
    event_bus_service: EventBusService,
):
    """Test that failing validation publishes TASK_VALIDATION_FAILED event."""
    task_id = str(running_task_with_sandbox.id)
    recommendations = ["Fix the tests", "Add error handling"]

    with patch.object(event_bus_service, 'publish') as mock_publish:
        await task_validator.handle_validation_result(
            task_id=task_id,
            validator_agent_id=str(uuid4()),
            passed=False,
            feedback="Tests failing",
            recommendations=recommendations,
        )

        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert event.event_type == "TASK_VALIDATION_FAILED"
        assert event.entity_id == task_id
        assert event.payload["feedback"] == "Tests failing"
        assert event.payload["recommendations"] == recommendations


# -------------------------------------------------------------------------
# _spawn_validator Tests
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spawn_validator_gets_repo_info(
    task_validator: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
    sample_project: Project,
):
    """Test that _spawn_validator extracts repo info from project."""
    # Mock the spawner
    with patch('omoi_os.services.task_validator.get_daytona_spawner') as mock_get_spawner:
        mock_spawner = MagicMock()
        mock_spawner.spawn_for_task = AsyncMock(return_value="validator-sandbox-123")
        mock_get_spawner.return_value = mock_spawner

        result = await task_validator._spawn_validator(
            task_id=str(running_task_with_sandbox.id),
            original_sandbox_id=running_task_with_sandbox.sandbox_id,
            iteration=1,
        )

        assert result is not None

        # Verify spawn_for_task was called with correct extra_env
        call_kwargs = mock_spawner.spawn_for_task.call_args[1]
        extra_env = call_kwargs["extra_env"]

        assert extra_env["GITHUB_REPO"] == f"{sample_project.github_owner}/{sample_project.github_repo}"
        assert extra_env["GITHUB_REPO_OWNER"] == sample_project.github_owner
        assert extra_env["GITHUB_REPO_NAME"] == sample_project.github_repo
        assert extra_env["VALIDATION_MODE"] == "true"
        assert extra_env["ORIGINAL_TASK_ID"] == str(running_task_with_sandbox.id)


@pytest.mark.asyncio
async def test_spawn_validator_gets_branch_name(
    task_validator: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
):
    """Test that _spawn_validator extracts branch_name from task.result."""
    with patch('omoi_os.services.task_validator.get_daytona_spawner') as mock_get_spawner:
        mock_spawner = MagicMock()
        mock_spawner.spawn_for_task = AsyncMock(return_value="validator-sandbox-123")
        mock_get_spawner.return_value = mock_spawner

        await task_validator._spawn_validator(
            task_id=str(running_task_with_sandbox.id),
            original_sandbox_id=running_task_with_sandbox.sandbox_id,
            iteration=1,
        )

        call_kwargs = mock_spawner.spawn_for_task.call_args[1]
        extra_env = call_kwargs["extra_env"]

        assert extra_env["BRANCH_NAME"] == "feature/test-branch"


@pytest.mark.asyncio
async def test_spawn_validator_gets_github_token(
    task_validator: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
    sample_project: Project,
    test_user: User,
):
    """Test that _spawn_validator extracts GitHub token from project owner."""
    with patch('omoi_os.services.task_validator.get_daytona_spawner') as mock_get_spawner:
        mock_spawner = MagicMock()
        mock_spawner.spawn_for_task = AsyncMock(return_value="validator-sandbox-123")
        mock_get_spawner.return_value = mock_spawner

        await task_validator._spawn_validator(
            task_id=str(running_task_with_sandbox.id),
            original_sandbox_id=running_task_with_sandbox.sandbox_id,
            iteration=1,
        )

        call_kwargs = mock_spawner.spawn_for_task.call_args[1]
        extra_env = call_kwargs["extra_env"]

        assert extra_env["GITHUB_TOKEN"] == "ghp_test_token_12345"
        assert extra_env["USER_ID"] == str(test_user.id)


@pytest.mark.asyncio
async def test_spawn_validator_creates_agent_record(
    task_validator: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
):
    """Test that _spawn_validator creates a validator Agent record."""
    with patch('omoi_os.services.task_validator.get_daytona_spawner') as mock_get_spawner:
        mock_spawner = MagicMock()
        mock_spawner.spawn_for_task = AsyncMock(return_value="validator-sandbox-123")
        mock_get_spawner.return_value = mock_spawner

        result = await task_validator._spawn_validator(
            task_id=str(running_task_with_sandbox.id),
            original_sandbox_id=running_task_with_sandbox.sandbox_id,
            iteration=1,
        )

        assert result is not None
        agent_id = result["agent_id"]

        with db_service.get_session() as session:
            agent = session.get(Agent, agent_id)
            assert agent is not None
            assert agent.agent_type == "validator"
            assert agent.phase_id == "PHASE_VALIDATION"
            assert "validate" in agent.capabilities
            assert "validator" in agent.tags


@pytest.mark.asyncio
async def test_spawn_validator_handles_failure(
    task_validator: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
):
    """Test that _spawn_validator returns None on failure."""
    with patch('omoi_os.services.task_validator.get_daytona_spawner') as mock_get_spawner:
        mock_get_spawner.side_effect = Exception("Daytona unavailable")

        result = await task_validator._spawn_validator(
            task_id=str(running_task_with_sandbox.id),
            original_sandbox_id=running_task_with_sandbox.sandbox_id,
            iteration=1,
        )

        assert result is None


# -------------------------------------------------------------------------
# _build_validator_prompt Tests
# -------------------------------------------------------------------------


def test_build_validator_prompt_includes_task_id(task_validator: TaskValidatorService):
    """Test that validator prompt includes task_id."""
    task_id = "test-task-123"
    prompt = task_validator._build_validator_prompt(task_id, 1)

    assert task_id in prompt
    assert "Validation Iteration: 1" in prompt


def test_build_validator_prompt_includes_checklist(task_validator: TaskValidatorService):
    """Test that validator prompt includes validation checklist."""
    prompt = task_validator._build_validator_prompt("task-123", 1)

    assert "Tests Pass" in prompt
    assert "Build Passes" in prompt
    assert "Changes Committed" in prompt
    assert "Changes Pushed" in prompt
    assert "PR Created" in prompt
    assert "Code Quality" in prompt


# -------------------------------------------------------------------------
# _auto_approve Tests
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_approve_marks_completed(
    task_validator: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
):
    """Test that _auto_approve marks task as completed."""
    result = await task_validator._auto_approve(
        task_id=str(running_task_with_sandbox.id),
        result={"success": True, "output": "Implementation done!"},
    )

    assert result == "auto-approved"

    with db_service.get_session() as session:
        task = session.get(Task, running_task_with_sandbox.id)
        assert task.status == "completed"
        assert task.result.get("auto_approved") is True
        assert task.result.get("success") is True
        assert task.result.get("output") == "Implementation done!"
        assert task.result.get("completed_at") is not None


# -------------------------------------------------------------------------
# get_task_validator Tests
# -------------------------------------------------------------------------


def test_get_task_validator_factory(db_service: DatabaseService, event_bus_service: EventBusService):
    """Test the get_task_validator factory function."""
    validator = get_task_validator(db=db_service, event_bus=event_bus_service)

    assert isinstance(validator, TaskValidatorService)
    assert validator.db == db_service
    assert validator.event_bus == event_bus_service


# -------------------------------------------------------------------------
# Event Publishing Tests
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_validation_publishes_event(
    task_validator: TaskValidatorService,
    db_service: DatabaseService,
    running_task_with_sandbox: Task,
    event_bus_service: EventBusService,
):
    """Test that request_validation publishes TASK_VALIDATION_REQUESTED event."""
    task_id = str(running_task_with_sandbox.id)
    sandbox_id = running_task_with_sandbox.sandbox_id

    with patch.object(task_validator, '_spawn_validator', new_callable=AsyncMock) as mock_spawn:
        mock_spawn.return_value = {"sandbox_id": "v-1", "agent_id": str(uuid4())}

        with patch.object(event_bus_service, 'publish') as mock_publish:
            await task_validator.request_validation(
                task_id=task_id,
                sandbox_id=sandbox_id,
                implementation_result={"success": True},
            )

            mock_publish.assert_called_once()
            event = mock_publish.call_args[0][0]
            assert event.event_type == "TASK_VALIDATION_REQUESTED"
            assert event.entity_id == task_id
            assert event.payload["sandbox_id"] == sandbox_id
            assert event.payload["iteration"] == 1
