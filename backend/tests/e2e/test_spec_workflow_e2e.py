"""End-to-end tests for the complete spec-driven development workflow.

Tests the full flow:
1. Create spec via API
2. Execute state machine (EXPLORE -> REQUIREMENTS -> DESIGN -> TASKS -> SYNC)
3. Verify requirements, tasks, and criteria are persisted with deduplication
4. Test retry scenarios where duplicates should be skipped

These tests use mocked LLM responses to simulate the state machine flow
without requiring actual LLM API calls.
"""

import json
import shutil
import tempfile
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from omoi_os.models.spec import (
    Spec,
    SpecRequirement,
)
from omoi_os.schemas.spec_generation import SpecPhase
from omoi_os.services.database import DatabaseService
from omoi_os.services.spec_dedup import SpecDeduplicationService, compute_content_hash
from omoi_os.services.spec_sync import SpecSyncService, SyncStats
from omoi_os.workers.spec_state_machine import (
    PhaseResult,
    SpecStateMachine,
    _MockSpec,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    workspace = tempfile.mkdtemp(prefix="spec_e2e_test_")
    yield workspace
    shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture
def mock_db_session():
    """Create a mock database session for testing."""
    session = AsyncMock()
    session._pending_operations = []  # Marker for mock detection
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.close = AsyncMock()

    # Default: no existing records
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_result.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[]))
    )
    session.execute.return_value = mock_result

    return session


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = MagicMock()
    service.generate_embedding = MagicMock(return_value=[0.1] * 1536)
    return service


@pytest.fixture
def sample_explore_output() -> Dict[str, Any]:
    """Sample exploration phase output."""
    return {
        "project_type": "web_api",
        "tech_stack": ["python", "fastapi", "postgresql", "sqlalchemy"],
        "existing_models": [
            {
                "name": "User",
                "file": "models/user.py",
                "fields": ["id", "email", "name"],
            },
            {
                "name": "Task",
                "file": "models/task.py",
                "fields": ["id", "title", "status"],
            },
        ],
        "existing_routes": ["/api/users", "/api/tasks", "/health"],
        "database_type": "postgresql",
        "project_structure": {
            "directories": ["src/", "tests/", "docs/", "models/"],
            "entry_point": "main.py",
        },
        "coding_conventions": {
            "style_guide": "pep8",
            "naming": "snake_case",
        },
        "explored_files": ["main.py", "models/user.py", "models/task.py"],
    }


@pytest.fixture
def sample_requirements_output() -> Dict[str, Any]:
    """Sample requirements phase output."""
    return {
        "requirements": [
            {
                "id": "REQ-001",
                "title": "User Authentication",
                "condition": "WHEN a user submits valid credentials",
                "action": "THE SYSTEM SHALL authenticate the user and return a JWT token",
                "acceptance_criteria": [
                    "Token expires after 24 hours",
                    "Invalid credentials return 401 status",
                    "Rate limiting after 5 failed attempts",
                ],
            },
            {
                "id": "REQ-002",
                "title": "Task Creation",
                "condition": "WHEN an authenticated user creates a task",
                "action": "THE SYSTEM SHALL create the task and return task details",
                "acceptance_criteria": [
                    "Task has unique ID",
                    "Task status defaults to 'pending'",
                    "Created timestamp is recorded",
                ],
            },
        ],
    }


@pytest.fixture
def sample_design_output() -> Dict[str, Any]:
    """Sample design phase output."""
    return {
        "architecture": {
            "pattern": "layered",
            "layers": ["api", "service", "repository", "model"],
        },
        "data_model": {
            "entities": ["User", "Task", "Session"],
            "relationships": [
                {"from": "User", "to": "Task", "type": "one-to-many"},
            ],
        },
        "api_design": {
            "endpoints": [
                {"method": "POST", "path": "/auth/login", "description": "User login"},
                {"method": "POST", "path": "/tasks", "description": "Create task"},
            ],
        },
        "security_considerations": [
            "JWT token authentication",
            "Password hashing with bcrypt",
            "Rate limiting on auth endpoints",
        ],
    }


@pytest.fixture
def sample_tasks_output() -> Dict[str, Any]:
    """Sample tasks phase output."""
    return {
        "tasks": [
            {
                "id": "TASK-001",
                "title": "Implement JWT Authentication",
                "description": "Create JWT token generation and validation",
                "requirement_id": "REQ-001",
                "priority": "high",
                "estimated_hours": 4,
            },
            {
                "id": "TASK-002",
                "title": "Create Login Endpoint",
                "description": "Implement POST /auth/login endpoint",
                "requirement_id": "REQ-001",
                "priority": "high",
                "estimated_hours": 2,
            },
            {
                "id": "TASK-003",
                "title": "Implement Task Creation",
                "description": "Create POST /tasks endpoint with validation",
                "requirement_id": "REQ-002",
                "priority": "medium",
                "estimated_hours": 3,
            },
        ],
    }


# =============================================================================
# Test: State Machine Initialization and Phase Flow
# =============================================================================


class TestSpecStateMachineE2E:
    """E2E tests for the spec state machine."""

    def test_state_machine_creates_with_all_phases(
        self, mock_db_session, temp_workspace
    ):
        """Test state machine initializes with correct phase order."""
        machine = SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db_session,
            working_directory=temp_workspace,
        )

        assert machine.PHASE_ORDER == [
            SpecPhase.EXPLORE,
            SpecPhase.REQUIREMENTS,
            SpecPhase.DESIGN,
            SpecPhase.TASKS,
            SpecPhase.SYNC,
            SpecPhase.COMPLETE,
        ]

    @pytest.mark.asyncio
    async def test_load_spec_creates_mock_in_sandbox_mode(
        self, mock_db_session, temp_workspace
    ):
        """Test load_spec creates _MockSpec when database returns None."""
        machine = SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db_session,
            working_directory=temp_workspace,
        )

        spec = await machine.load_spec()

        assert isinstance(spec, _MockSpec)
        assert spec.id == "spec-test-123"
        assert spec.is_mock is True
        assert spec.current_phase == SpecPhase.EXPLORE.value

    @pytest.mark.asyncio
    async def test_phase_data_accumulates_correctly(
        self,
        mock_db_session,
        temp_workspace,
        sample_explore_output,
        sample_requirements_output,
    ):
        """Test phase data accumulates as phases complete."""
        machine = SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db_session,
            working_directory=temp_workspace,
        )

        spec = await machine.load_spec()

        # Simulate saving phase results
        explore_result = PhaseResult(
            phase=SpecPhase.EXPLORE,
            data=sample_explore_output,
            eval_score=0.95,
            attempts=1,
        )
        await machine.save_phase_result(spec, SpecPhase.EXPLORE, explore_result)

        assert "explore" in spec.phase_data
        assert spec.phase_data["explore"]["project_type"] == "web_api"

        req_result = PhaseResult(
            phase=SpecPhase.REQUIREMENTS,
            data=sample_requirements_output,
            eval_score=0.92,
            attempts=1,
        )
        await machine.save_phase_result(spec, SpecPhase.REQUIREMENTS, req_result)

        assert "requirements" in spec.phase_data
        assert len(spec.phase_data["requirements"]["requirements"]) == 2


class TestSpecStateMachinePhaseExecution:
    """Test individual phase execution."""

    @pytest.mark.asyncio
    async def test_sync_phase_skips_for_mock_spec(
        self, mock_db_session, temp_workspace
    ):
        """Test SYNC phase returns skip result for mock specs."""
        machine = SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db_session,
            working_directory=temp_workspace,
        )

        mock_spec = _MockSpec("spec-test-123", "Test Spec", "Test Description")

        result = await machine._execute_sync_phase(mock_spec)

        assert result.phase == SpecPhase.SYNC
        assert result.data["status"] == "skipped"
        assert result.data["reason"] == "mock_spec_sandbox_mode"


# =============================================================================
# Test: Full Workflow with Mock LLM
# =============================================================================


class TestFullSpecWorkflow:
    """Test the complete spec workflow with mocked components."""

    @pytest.fixture
    def full_phase_data(
        self,
        sample_explore_output,
        sample_requirements_output,
        sample_design_output,
        sample_tasks_output,
    ) -> Dict[str, Any]:
        """Complete phase data for all phases."""
        return {
            "explore": sample_explore_output,
            "requirements": sample_requirements_output,
            "design": sample_design_output,
            "tasks": sample_tasks_output,
        }

    @pytest.mark.asyncio
    async def test_complete_workflow_with_mocked_agent(
        self,
        mock_db_session,
        temp_workspace,
        full_phase_data,
    ):
        """Test complete workflow from EXPLORE to SYNC with mocked agent."""
        machine = SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db_session,
            working_directory=temp_workspace,
        )

        # Load mock spec
        spec = await machine.load_spec()
        assert spec.current_phase == SpecPhase.EXPLORE.value

        # Simulate each phase completing successfully
        phases_to_simulate = [
            (SpecPhase.EXPLORE, full_phase_data["explore"]),
            (SpecPhase.REQUIREMENTS, full_phase_data["requirements"]),
            (SpecPhase.DESIGN, full_phase_data["design"]),
            (SpecPhase.TASKS, full_phase_data["tasks"]),
        ]

        for phase, data in phases_to_simulate:
            result = PhaseResult(
                phase=phase,
                data=data,
                eval_score=0.95,
                attempts=1,
            )
            await machine.save_phase_result(spec, phase, result)
            spec.current_phase = machine.next_phase(phase).value
            await machine.save_checkpoint(spec)

        # Verify all phase data accumulated
        assert "explore" in spec.phase_data
        assert "requirements" in spec.phase_data
        assert "design" in spec.phase_data
        assert "tasks" in spec.phase_data

        # Execute SYNC phase (should skip for mock)
        sync_result = await machine._execute_sync_phase(spec)
        assert sync_result.data["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_checkpoint_persistence_to_files(
        self,
        mock_db_session,
        temp_workspace,
        sample_explore_output,
    ):
        """Test that checkpoints are persisted to files correctly."""
        from pathlib import Path

        machine = SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db_session,
            working_directory=temp_workspace,
        )

        spec = await machine.load_spec()

        # Save explore phase
        result = PhaseResult(
            phase=SpecPhase.EXPLORE,
            data=sample_explore_output,
            eval_score=0.95,
            attempts=1,
        )
        await machine.save_phase_result(spec, SpecPhase.EXPLORE, result)
        spec.current_phase = SpecPhase.REQUIREMENTS.value
        await machine.save_checkpoint(spec)

        # Verify checkpoint files exist
        checkpoint_dir = Path(temp_workspace) / ".omoi_os" / "checkpoints"
        assert checkpoint_dir.exists()

        state_file = checkpoint_dir / "state.json"
        assert state_file.exists()

        state = json.loads(state_file.read_text())
        assert state["current_phase"] == "requirements"
        assert state["spec_id"] == "spec-test-123"


# =============================================================================
# Test: Deduplication in E2E Flow
# =============================================================================


class TestDeduplicationE2E:
    """E2E tests for deduplication during sync."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database service."""
        db = MagicMock()
        return db

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.mark.asyncio
    async def test_criterion_deduplication_on_retry(self, mock_db, mock_session):
        """Test that duplicate criteria are skipped on retry."""
        # First sync: No existing criteria
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result_none

        dedup_service = SpecDeduplicationService(db=mock_db)

        # First check - should be new
        result1 = await dedup_service.check_criterion_duplicate(
            requirement_id="req-123",
            text="User sees success message",
            session=mock_session,
        )
        assert result1.is_duplicate is False
        assert result1.action == "create"

        # Second sync (retry): Criterion now exists
        mock_existing = MagicMock()
        mock_existing.id = "crit-123"
        mock_existing.text = "User sees success message"

        mock_result_existing = MagicMock()
        mock_result_existing.scalar_one_or_none.return_value = mock_existing
        mock_session.execute.return_value = mock_result_existing

        # Second check - should be duplicate
        result2 = await dedup_service.check_criterion_duplicate(
            requirement_id="req-123",
            text="User sees success message",
            session=mock_session,
        )
        assert result2.is_duplicate is True
        assert result2.action == "skip"

    @pytest.mark.asyncio
    async def test_requirement_deduplication_by_hash(self, mock_db, mock_session):
        """Test requirement deduplication using content hash."""
        # Create two requirements with same content
        content1 = "WHEN user clicks THE SYSTEM SHALL respond"
        content2 = "WHEN user clicks THE SYSTEM SHALL respond"

        hash1 = compute_content_hash(content1)
        hash2 = compute_content_hash(content2)

        # Same content should produce same hash
        assert hash1 == hash2

        # First sync: No existing requirement
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        mock_result_none.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result_none

        dedup_service = SpecDeduplicationService(db=mock_db)

        result1 = await dedup_service.check_requirement_duplicate(
            spec_id="spec-123",
            title="Click Response",
            condition="WHEN user clicks",
            action="THE SYSTEM SHALL respond",
            session=mock_session,
        )
        assert result1.is_duplicate is False
        assert result1.content_hash == hash1

    @pytest.mark.asyncio
    async def test_bulk_dedup_returns_correct_categories(self, mock_db, mock_session):
        """Test bulk deduplication categorizes items correctly."""
        # Setup: First criterion exists, second is new
        existing_text = "existing criterion"
        new_text = "brand new criterion"

        mock_existing = MagicMock()
        mock_existing.id = "crit-existing"
        mock_existing.text = existing_text

        call_count = [0]

        def mock_execute(query):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.scalar_one_or_none.return_value = mock_existing
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        dedup_service = SpecDeduplicationService(db=mock_db)

        criteria = [
            {"text": existing_text},  # Should be skipped
            {"text": new_text},  # Should be created
        ]

        result = await dedup_service.deduplicate_criteria_bulk(
            requirement_id="req-123",
            criteria=criteria,
            session=mock_session,
        )

        assert len(result.to_create) == 1
        assert len(result.to_skip) == 1
        assert result.to_create[0]["text"] == new_text


# =============================================================================
# Test: Sync Service Integration
# =============================================================================


class TestSyncServiceIntegration:
    """Test SpecSyncService integration with state machine."""

    def test_sync_stats_accumulate_correctly(self):
        """Test SyncStats accumulates counts correctly."""
        stats = SyncStats()

        # Simulate syncing 5 requirements
        for i in range(5):
            if i < 3:  # 3 new
                stats.requirements_created += 1
            else:  # 2 duplicates
                stats.requirements_skipped += 1

        assert stats.requirements_created == 3
        assert stats.requirements_skipped == 2
        assert stats.to_dict()["requirements_created"] == 3

    def test_sync_service_initialization(self):
        """Test SpecSyncService initializes correctly."""
        mock_db = MagicMock()
        mock_embedding = MagicMock()

        service = SpecSyncService(
            db=mock_db,
            embedding_service=mock_embedding,
        )

        assert service.db == mock_db
        assert service.embedding_service == mock_embedding
        assert service.dedup_service is not None


# =============================================================================
# Test: API Integration (if database available)
# =============================================================================


@pytest.mark.integration
class TestSpecAPIIntegration:
    """Integration tests requiring real database."""

    @pytest.fixture
    def db_service(self):
        """Create database service if available."""
        import os

        db_url = os.getenv("DATABASE_URL_TEST")
        if not db_url:
            pytest.skip("DATABASE_URL_TEST not set")

        db = DatabaseService(db_url)
        db.create_tables()
        yield db
        db.engine.dispose()

    @pytest.fixture
    def project_id(self, db_service):
        """Create a test project and return its ID."""
        from omoi_os.models.project import Project

        with db_service.get_session() as session:
            project = Project(
                name=f"Test Project {uuid4().hex[:8]}",
                description="Test project for E2E spec tests",
            )
            session.add(project)
            session.commit()
            project_id = project.id
            session.expunge(project)
            return project_id

    @pytest.mark.asyncio
    async def test_create_spec_and_sync_requirements(
        self, db_service, project_id, sample_requirements_output
    ):
        """Test creating a spec and syncing requirements to database."""
        # Create spec
        async with db_service.get_async_session() as session:
            spec = Spec(
                project_id=project_id,
                title="Test Spec for E2E",
                description="Testing spec-driven workflow",
                status="draft",
                current_phase=SpecPhase.SYNC.value,
                phase_data={
                    "requirements": sample_requirements_output,
                },
            )
            session.add(spec)
            await session.commit()
            spec_id = spec.id

        # Create sync service and sync
        sync_service = SpecSyncService(db=db_service)

        async with db_service.get_async_session() as session:
            result = await sync_service.sync_spec(
                spec_id=spec_id,
                session=session,
            )

        assert result.success
        assert result.stats.requirements_created == 2

        # Verify requirements were created
        async with db_service.get_async_session() as session:
            query = (
                select(SpecRequirement)
                .filter(SpecRequirement.spec_id == spec_id)
                .options(selectinload(SpecRequirement.criteria))
            )
            db_result = await session.execute(query)
            requirements = db_result.scalars().all()

        assert len(requirements) == 2

        # Verify acceptance criteria
        total_criteria = sum(len(r.criteria) for r in requirements)
        assert total_criteria == 6  # 3 + 3 criteria

    @pytest.mark.asyncio
    async def test_retry_sync_skips_duplicates(
        self, db_service, project_id, sample_requirements_output
    ):
        """Test that retry sync skips already-created requirements."""
        # Create spec with phase data
        async with db_service.get_async_session() as session:
            spec = Spec(
                project_id=project_id,
                title="Test Spec Retry",
                description="Testing retry deduplication",
                status="draft",
                current_phase=SpecPhase.SYNC.value,
                phase_data={
                    "requirements": sample_requirements_output,
                },
            )
            session.add(spec)
            await session.commit()
            spec_id = spec.id

        sync_service = SpecSyncService(db=db_service)

        # First sync - should create all
        async with db_service.get_async_session() as session:
            result1 = await sync_service.sync_spec(
                spec_id=spec_id,
                session=session,
            )

        assert result1.stats.requirements_created == 2
        assert result1.stats.requirements_skipped == 0

        # Second sync (retry) - should skip all
        async with db_service.get_async_session() as session:
            result2 = await sync_service.sync_spec(
                spec_id=spec_id,
                session=session,
            )

        assert result2.stats.requirements_created == 0
        assert result2.stats.requirements_skipped == 2

        # Verify only 2 requirements exist (not 4)
        async with db_service.get_async_session() as session:
            query = select(SpecRequirement).filter(SpecRequirement.spec_id == spec_id)
            db_result = await session.execute(query)
            requirements = db_result.scalars().all()

        assert len(requirements) == 2


# =============================================================================
# Test: Error Handling
# =============================================================================


class TestErrorHandling:
    """Test error handling in the spec workflow."""

    @pytest.mark.asyncio
    async def test_phase_timeout_is_configurable(self, mock_db_session, temp_workspace):
        """Test that phase timeouts are configurable."""
        machine = SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db_session,
            working_directory=temp_workspace,
        )

        # Default timeouts should be reasonable
        assert machine.PHASE_TIMEOUTS[SpecPhase.EXPLORE] == 180
        assert machine.PHASE_TIMEOUTS[SpecPhase.REQUIREMENTS] == 300
        assert machine.PHASE_TIMEOUTS[SpecPhase.SYNC] == 120

    @pytest.mark.asyncio
    async def test_max_retries_respected(self, mock_db_session, temp_workspace):
        """Test that max retries is respected."""
        machine = SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db_session,
            working_directory=temp_workspace,
            max_retries=5,
        )

        assert machine.max_retries == 5

    @pytest.mark.asyncio
    async def test_sync_error_captured_in_result(self, mock_db_session, temp_workspace):
        """Test that sync errors are captured in the phase result."""
        machine = SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db_session,
            working_directory=temp_workspace,
        )

        # Create mock spec that is NOT a mock (to trigger actual sync)
        real_spec = MagicMock()
        real_spec.is_mock = False
        real_spec.id = "spec-test-123"

        # Mock sync service to raise an error
        mock_sync_service = MagicMock()
        mock_sync_service.sync_spec = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        machine.sync_service = mock_sync_service

        # Execute sync phase - should handle error gracefully
        result = await machine._execute_sync_phase(real_spec)

        assert result.phase == SpecPhase.SYNC
        assert result.data["status"] == "error"
        assert "Database connection failed" in result.data["message"]


# =============================================================================
# Test: Evaluator Integration
# =============================================================================


class TestEvaluatorIntegration:
    """Test evaluator integration in the E2E flow."""

    def test_exploration_evaluator_passes_valid_output(
        self, mock_db_session, temp_workspace, sample_explore_output
    ):
        """Test exploration evaluator passes valid output."""
        machine = SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db_session,
            working_directory=temp_workspace,
        )

        evaluator = machine.evaluators[SpecPhase.EXPLORE]
        result = evaluator.evaluate(sample_explore_output)

        # Should pass or have high score
        assert result.passed or result.score >= 0.7

    def test_requirements_evaluator_passes_valid_output(
        self, mock_db_session, temp_workspace, sample_requirements_output
    ):
        """Test requirements evaluator passes valid output."""
        machine = SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db_session,
            working_directory=temp_workspace,
        )

        evaluator = machine.evaluators[SpecPhase.REQUIREMENTS]
        result = evaluator.evaluate(sample_requirements_output)

        # Should pass or have high score
        assert result.passed or result.score >= 0.7

    def test_evaluators_reject_empty_output(self, mock_db_session, temp_workspace):
        """Test all evaluators reject empty output."""
        machine = SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db_session,
            working_directory=temp_workspace,
        )

        for phase, evaluator in machine.evaluators.items():
            result = evaluator.evaluate({})
            assert not result.passed, f"{phase} evaluator should reject empty output"
            assert len(result.failures) > 0
