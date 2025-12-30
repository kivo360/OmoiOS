"""Integration tests for the complete validation flow.

Tests the full validation workflow from task completion to validation result.
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
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.task_validator import TaskValidatorService


@pytest.fixture
def integration_db(db_service: DatabaseService) -> DatabaseService:
    """Database service for integration tests."""
    return db_service


@pytest.fixture
def integration_event_bus(event_bus_service: EventBusService) -> EventBusService:
    """Event bus service for integration tests."""
    return event_bus_service


@pytest.fixture
def test_project(integration_db: DatabaseService, test_user: User) -> Project:
    """Create a test project with full GitHub configuration."""
    with integration_db.get_session() as session:
        # Update user with GitHub token
        user = session.get(User, test_user.id)
        user.attributes = {"github_access_token": "ghp_integration_test_token"}
        session.commit()

        project = Project(
            name="Integration Test Project",
            github_owner="integration-owner",
            github_repo="integration-repo",
            created_by=test_user.id,
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        session.expunge(project)
        return project


@pytest.fixture
def test_ticket(integration_db: DatabaseService, test_project: Project) -> Ticket:
    """Create a test ticket linked to the project."""
    with integration_db.get_session() as session:
        ticket = Ticket(
            title="Integration Test Ticket",
            description="Full validation flow test",
            phase_id="PHASE_IMPLEMENTATION",
            status="in_progress",
            project_id=test_project.id,
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.expunge(ticket)
        return ticket


@pytest.fixture
def implementer_task(integration_db: DatabaseService, test_ticket: Ticket) -> Task:
    """Create a task simulating an implementer's work."""
    with integration_db.get_session() as session:
        task = Task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Implement user authentication",
            status="running",
            sandbox_id=f"impl-sandbox-{uuid4().hex[:8]}",
            result={"branch_name": "feature/auth-implementation"},
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        session.expunge(task)
        return task


@pytest.fixture
def task_validator(
    integration_db: DatabaseService, integration_event_bus: EventBusService
) -> TaskValidatorService:
    """Create TaskValidatorService with validation enabled."""
    os.environ["TASK_VALIDATION_ENABLED"] = "true"
    os.environ["MAX_VALIDATION_ITERATIONS"] = "3"
    return TaskValidatorService(db=integration_db, event_bus=integration_event_bus)


# -------------------------------------------------------------------------
# Complete Validation Flow Tests
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_validation_flow_pass(
    task_validator: TaskValidatorService,
    integration_db: DatabaseService,
    implementer_task: Task,
):
    """Test complete flow: completion -> validation request -> pass -> completed."""
    task_id = str(implementer_task.id)
    sandbox_id = implementer_task.sandbox_id

    # Mock spawner to avoid external calls
    with patch.object(task_validator, '_spawn_validator', new_callable=AsyncMock) as mock_spawn:
        validator_agent_id = str(uuid4())
        mock_spawn.return_value = {
            "sandbox_id": "validator-sandbox-123",
            "agent_id": validator_agent_id,
        }

        # Step 1: Request validation (simulating agent.completed event)
        validation_id = await task_validator.request_validation(
            task_id=task_id,
            sandbox_id=sandbox_id,
            implementation_result={
                "success": True,
                "branch_name": "feature/auth-implementation",
                "commit_sha": "abc123def",
            },
        )

        assert validation_id

        # Verify task is pending_validation
        with integration_db.get_session() as session:
            task = session.get(Task, implementer_task.id)
            assert task.status == "pending_validation"
            assert task.result.get("validation_iteration") == 1
            assert task.result.get("validator_sandbox_id") == "validator-sandbox-123"

        # Step 2: Handle validation result (simulating validator completion)
        await task_validator.handle_validation_result(
            task_id=task_id,
            validator_agent_id=validator_agent_id,
            passed=True,
            feedback="All checks passed. Tests pass, build succeeds, PR created.",
            evidence={
                "tests": {"passed": 42, "failed": 0},
                "build": "success",
                "pr_url": "https://github.com/owner/repo/pull/123",
            },
        )

        # Verify final state
        with integration_db.get_session() as session:
            task = session.get(Task, implementer_task.id)
            assert task.status == "completed"
            assert task.result.get("validation_passed") is True
            assert task.result.get("validated_at") is not None

            # Verify review record
            reviews = session.query(ValidationReview).filter(
                ValidationReview.task_id == task_id
            ).all()
            assert len(reviews) == 1
            assert reviews[0].validation_passed is True


@pytest.mark.asyncio
async def test_complete_validation_flow_fail_and_retry(
    task_validator: TaskValidatorService,
    integration_db: DatabaseService,
    implementer_task: Task,
):
    """Test flow: completion -> validation -> fail -> needs_revision -> retry -> pass."""
    task_id = str(implementer_task.id)
    sandbox_id = implementer_task.sandbox_id

    with patch.object(task_validator, '_spawn_validator', new_callable=AsyncMock) as mock_spawn:
        # First validation attempt
        validator_agent_id_1 = str(uuid4())
        mock_spawn.return_value = {
            "sandbox_id": "validator-1",
            "agent_id": validator_agent_id_1,
        }

        await task_validator.request_validation(
            task_id=task_id,
            sandbox_id=sandbox_id,
            implementation_result={"success": True, "branch_name": "feature/auth"},
        )

        # First validation FAILS
        await task_validator.handle_validation_result(
            task_id=task_id,
            validator_agent_id=validator_agent_id_1,
            passed=False,
            feedback="Tests failing: 3 unit tests failed",
            recommendations=["Fix test_login", "Fix test_logout", "Fix test_session"],
        )

        # Verify needs_revision state
        with integration_db.get_session() as session:
            task = session.get(Task, implementer_task.id)
            assert task.status == "needs_revision"
            assert task.result.get("revision_feedback") == "Tests failing: 3 unit tests failed"
            assert len(task.result.get("revision_recommendations", [])) == 3

        # Simulate implementer fixing and re-requesting validation
        with integration_db.get_session() as session:
            task = session.get(Task, implementer_task.id)
            task.status = "running"  # Back to running for re-implementation
            session.commit()

        # Second validation attempt
        validator_agent_id_2 = str(uuid4())
        mock_spawn.return_value = {
            "sandbox_id": "validator-2",
            "agent_id": validator_agent_id_2,
        }

        await task_validator.request_validation(
            task_id=task_id,
            sandbox_id=sandbox_id,
            implementation_result={"success": True, "branch_name": "feature/auth", "fixed_tests": True},
        )

        # Verify iteration incremented
        with integration_db.get_session() as session:
            task = session.get(Task, implementer_task.id)
            assert task.result.get("validation_iteration") == 2

        # Second validation PASSES
        await task_validator.handle_validation_result(
            task_id=task_id,
            validator_agent_id=validator_agent_id_2,
            passed=True,
            feedback="All issues resolved. All 42 tests pass.",
        )

        # Verify completed state
        with integration_db.get_session() as session:
            task = session.get(Task, implementer_task.id)
            assert task.status == "completed"
            assert task.result.get("validation_passed") is True

            # Verify both reviews exist
            reviews = session.query(ValidationReview).filter(
                ValidationReview.task_id == task_id
            ).order_by(ValidationReview.iteration_number).all()
            assert len(reviews) == 2
            assert reviews[0].validation_passed is False
            assert reviews[1].validation_passed is True


@pytest.mark.asyncio
async def test_validation_max_iterations_exceeded(
    integration_db: DatabaseService,
    integration_event_bus: EventBusService,
    implementer_task: Task,
):
    """Test that task fails after exceeding max validation iterations."""
    os.environ["MAX_VALIDATION_ITERATIONS"] = "2"
    task_validator = TaskValidatorService(
        db=integration_db, event_bus=integration_event_bus
    )

    task_id = str(implementer_task.id)
    sandbox_id = implementer_task.sandbox_id

    with patch.object(task_validator, '_spawn_validator', new_callable=AsyncMock) as mock_spawn:
        # First validation
        mock_spawn.return_value = {"sandbox_id": "v1", "agent_id": str(uuid4())}
        await task_validator.request_validation(
            task_id=task_id,
            sandbox_id=sandbox_id,
            implementation_result={"success": True},
        )
        await task_validator.handle_validation_result(
            task_id=task_id,
            validator_agent_id=str(uuid4()),
            passed=False,
            feedback="First failure",
        )

        # Reset to running
        with integration_db.get_session() as session:
            task = session.get(Task, implementer_task.id)
            task.status = "running"
            session.commit()

        # Second validation
        mock_spawn.return_value = {"sandbox_id": "v2", "agent_id": str(uuid4())}
        await task_validator.request_validation(
            task_id=task_id,
            sandbox_id=sandbox_id,
            implementation_result={"success": True},
        )
        await task_validator.handle_validation_result(
            task_id=task_id,
            validator_agent_id=str(uuid4()),
            passed=False,
            feedback="Second failure",
        )

        # Reset to running
        with integration_db.get_session() as session:
            task = session.get(Task, implementer_task.id)
            task.status = "running"
            session.commit()

        # Third validation request should fail the task
        result = await task_validator.request_validation(
            task_id=task_id,
            sandbox_id=sandbox_id,
            implementation_result={"success": True},
        )

        assert result == ""  # Empty = failed

        with integration_db.get_session() as session:
            task = session.get(Task, implementer_task.id)
            assert task.status == "failed"
            assert "Failed validation after 2 iterations" in task.error_message

    # Reset env
    os.environ["MAX_VALIDATION_ITERATIONS"] = "3"


# -------------------------------------------------------------------------
# Branch/Repo Info Propagation Tests
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_branch_name_propagates_to_validator(
    task_validator: TaskValidatorService,
    integration_db: DatabaseService,
    implementer_task: Task,
    test_project: Project,
):
    """Test that branch_name from task.result is passed to validator."""
    with patch('omoi_os.services.task_validator.get_daytona_spawner') as mock_get_spawner:
        mock_spawner = MagicMock()
        mock_spawner.spawn_for_task = AsyncMock(return_value="validator-sandbox-xyz")
        mock_get_spawner.return_value = mock_spawner

        await task_validator._spawn_validator(
            task_id=str(implementer_task.id),
            original_sandbox_id=implementer_task.sandbox_id,
            iteration=1,
        )

        # Verify branch name passed in extra_env
        call_kwargs = mock_spawner.spawn_for_task.call_args[1]
        extra_env = call_kwargs["extra_env"]

        assert extra_env["BRANCH_NAME"] == "feature/auth-implementation"


@pytest.mark.asyncio
async def test_repo_info_propagates_to_validator(
    task_validator: TaskValidatorService,
    integration_db: DatabaseService,
    implementer_task: Task,
    test_project: Project,
):
    """Test that GitHub repo info from project is passed to validator."""
    with patch('omoi_os.services.task_validator.get_daytona_spawner') as mock_get_spawner:
        mock_spawner = MagicMock()
        mock_spawner.spawn_for_task = AsyncMock(return_value="validator-sandbox-xyz")
        mock_get_spawner.return_value = mock_spawner

        await task_validator._spawn_validator(
            task_id=str(implementer_task.id),
            original_sandbox_id=implementer_task.sandbox_id,
            iteration=1,
        )

        call_kwargs = mock_spawner.spawn_for_task.call_args[1]
        extra_env = call_kwargs["extra_env"]

        assert extra_env["GITHUB_REPO"] == f"{test_project.github_owner}/{test_project.github_repo}"
        assert extra_env["GITHUB_REPO_OWNER"] == test_project.github_owner
        assert extra_env["GITHUB_REPO_NAME"] == test_project.github_repo


@pytest.mark.asyncio
async def test_github_token_propagates_to_validator(
    task_validator: TaskValidatorService,
    integration_db: DatabaseService,
    implementer_task: Task,
    test_project: Project,
    test_user: User,
):
    """Test that GitHub token from project owner is passed to validator."""
    with patch('omoi_os.services.task_validator.get_daytona_spawner') as mock_get_spawner:
        mock_spawner = MagicMock()
        mock_spawner.spawn_for_task = AsyncMock(return_value="validator-sandbox-xyz")
        mock_get_spawner.return_value = mock_spawner

        await task_validator._spawn_validator(
            task_id=str(implementer_task.id),
            original_sandbox_id=implementer_task.sandbox_id,
            iteration=1,
        )

        call_kwargs = mock_spawner.spawn_for_task.call_args[1]
        extra_env = call_kwargs["extra_env"]

        assert extra_env["GITHUB_TOKEN"] == "ghp_integration_test_token"
        assert extra_env["USER_ID"] == str(test_user.id)


# -------------------------------------------------------------------------
# Event Integration Tests
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validation_events_published_correctly(
    task_validator: TaskValidatorService,
    integration_db: DatabaseService,
    integration_event_bus: EventBusService,
    implementer_task: Task,
):
    """Test that all validation events are published in correct order."""
    task_id = str(implementer_task.id)
    events_published = []

    def capture_event(event):
        events_published.append(event.event_type)

    with patch.object(task_validator, '_spawn_validator', new_callable=AsyncMock) as mock_spawn:
        validator_agent_id = str(uuid4())
        mock_spawn.return_value = {
            "sandbox_id": "v-1",
            "agent_id": validator_agent_id,
        }

        with patch.object(integration_event_bus, 'publish', side_effect=capture_event):
            # Request validation
            await task_validator.request_validation(
                task_id=task_id,
                sandbox_id=implementer_task.sandbox_id,
                implementation_result={"success": True},
            )

            assert "TASK_VALIDATION_REQUESTED" in events_published

            # Pass validation
            await task_validator.handle_validation_result(
                task_id=task_id,
                validator_agent_id=validator_agent_id,
                passed=True,
                feedback="All good!",
            )

            assert "TASK_VALIDATION_PASSED" in events_published


@pytest.mark.asyncio
async def test_validation_failed_event_contains_feedback(
    task_validator: TaskValidatorService,
    integration_db: DatabaseService,
    integration_event_bus: EventBusService,
    implementer_task: Task,
):
    """Test that TASK_VALIDATION_FAILED event contains feedback and recommendations."""
    task_id = str(implementer_task.id)
    captured_event = None

    def capture_event(event):
        nonlocal captured_event
        if event.event_type == "TASK_VALIDATION_FAILED":
            captured_event = event

    with patch.object(task_validator, '_spawn_validator', new_callable=AsyncMock) as mock_spawn:
        validator_agent_id = str(uuid4())
        mock_spawn.return_value = {"sandbox_id": "v-1", "agent_id": validator_agent_id}

        await task_validator.request_validation(
            task_id=task_id,
            sandbox_id=implementer_task.sandbox_id,
            implementation_result={"success": True},
        )

        with patch.object(integration_event_bus, 'publish', side_effect=capture_event):
            await task_validator.handle_validation_result(
                task_id=task_id,
                validator_agent_id=validator_agent_id,
                passed=False,
                feedback="Tests failing",
                recommendations=["Fix test_foo", "Fix test_bar"],
            )

        assert captured_event is not None
        assert captured_event.payload["feedback"] == "Tests failing"
        assert captured_event.payload["recommendations"] == ["Fix test_foo", "Fix test_bar"]


# -------------------------------------------------------------------------
# Edge Cases
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validation_with_missing_task(
    task_validator: TaskValidatorService,
):
    """Test validation request for non-existent task."""
    result = await task_validator.request_validation(
        task_id="non-existent-task-id",
        sandbox_id="sandbox-123",
        implementation_result={"success": True},
    )

    assert result == ""  # Empty string indicates failure


@pytest.mark.asyncio
async def test_validation_result_for_missing_task(
    task_validator: TaskValidatorService,
):
    """Test handling validation result for non-existent task."""
    # Should not raise, just log error
    await task_validator.handle_validation_result(
        task_id="non-existent-task-id",
        validator_agent_id=str(uuid4()),
        passed=True,
        feedback="This should be ignored",
    )
    # No assertion - just ensure no exception


@pytest.mark.asyncio
async def test_spawn_validator_failure_continues_gracefully(
    task_validator: TaskValidatorService,
    integration_db: DatabaseService,
    implementer_task: Task,
):
    """Test that spawner failure doesn't crash the validation flow."""
    with patch.object(task_validator, '_spawn_validator', new_callable=AsyncMock) as mock_spawn:
        mock_spawn.return_value = None  # Simulate failure

        validation_id = await task_validator.request_validation(
            task_id=str(implementer_task.id),
            sandbox_id=implementer_task.sandbox_id,
            implementation_result={"success": True},
        )

        # Validation ID still returned, task still marked pending_validation
        assert validation_id

        with integration_db.get_session() as session:
            task = session.get(Task, implementer_task.id)
            assert task.status == "pending_validation"
            # But no validator info stored
            assert task.result.get("validator_sandbox_id") is None
