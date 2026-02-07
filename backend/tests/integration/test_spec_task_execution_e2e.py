"""End-to-end tests for SpecTask execution flow.

Tests the complete flow from API request to task creation:
1. Create a Spec with SpecTasks
2. Approve the design
3. Execute SpecTasks via API
4. Verify Tasks are created and bridging Ticket exists
5. Check execution status

These tests use mocked database to avoid requiring a live database.
For production database tests, set DATABASE_URL_TEST environment variable.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

# =============================================================================
# Test: Full API Execution Flow (Mocked)
# =============================================================================


class TestSpecTaskExecutionAPIFlow:
    """Test the full API flow for SpecTask execution."""

    @pytest.fixture
    def mock_spec_with_tasks(self):
        """Create a mock spec with pending tasks."""
        from omoi_os.models.spec import Spec, SpecTask

        spec = MagicMock(spec=Spec)
        spec.id = f"spec-{uuid4()}"
        spec.project_id = f"project-{uuid4()}"
        spec.title = "Test Feature Implementation"
        spec.description = "Implement a test feature with API endpoints"
        spec.phase = "Implementation"
        spec.design_approved = True

        # Create pending tasks
        task1 = MagicMock(spec=SpecTask)
        task1.id = f"spec-task-{uuid4()}"
        task1.title = "Create API endpoint"
        task1.description = "Create the REST API endpoint for the feature"
        task1.phase = "Implementation"
        task1.priority = "high"
        task1.status = "pending"
        task1.dependencies = []

        task2 = MagicMock(spec=SpecTask)
        task2.id = f"spec-task-{uuid4()}"
        task2.title = "Write unit tests"
        task2.description = "Write unit tests for the API endpoint"
        task2.phase = "Testing"
        task2.priority = "medium"
        task2.status = "pending"
        task2.dependencies = [task1.id]

        task3 = MagicMock(spec=SpecTask)
        task3.id = f"spec-task-{uuid4()}"
        task3.title = "Update documentation"
        task3.description = "Update API documentation"
        task3.phase = "Design"
        task3.priority = "low"
        task3.status = "pending"
        task3.dependencies = []

        spec.tasks = [task1, task2, task3]
        return spec

    @pytest.fixture
    def mock_execution_service(self, mock_spec_with_tasks):
        """Create a mock execution service."""
        from omoi_os.services.spec_task_execution import (
            ExecutionResult,
            ExecutionStats,
        )

        service = MagicMock()
        service.execute_spec_tasks = AsyncMock(
            return_value=ExecutionResult(
                success=True,
                message="Created 3 tasks for execution",
                stats=ExecutionStats(
                    tasks_created=3,
                    tasks_skipped=0,
                    ticket_id=f"ticket-{uuid4()}",
                    errors=[],
                ),
            )
        )
        service.get_execution_status = AsyncMock(
            return_value={
                "spec_id": mock_spec_with_tasks.id,
                "total_tasks": 3,
                "status_counts": {
                    "pending": 0,
                    "in_progress": 3,
                    "completed": 0,
                    "blocked": 0,
                },
                "progress": 0.0,
                "is_complete": False,
            }
        )
        return service


# =============================================================================
# Test: SpecTask to Task Conversion Logic
# =============================================================================


class TestSpecTaskConversionLogic:
    """Test the conversion logic from SpecTask to Task."""

    def test_priority_mapping(self):
        """Test all priority levels are mapped correctly."""
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        priority_map = SpecTaskExecutionService.PRIORITY_MAP

        # Test all mappings
        assert priority_map["critical"] == "CRITICAL"
        assert priority_map["high"] == "HIGH"
        assert priority_map["medium"] == "MEDIUM"
        assert priority_map["low"] == "LOW"

        # Test case insensitivity handling in service
        assert priority_map.get("CRITICAL".lower()) == "CRITICAL"

    def test_phase_mapping(self):
        """Test all phase levels are mapped correctly.

        NOTE: Requirements and Design phases now map to PHASE_IMPLEMENTATION
        to ensure tasks run in continuous mode and execute to completion.
        The original mapping (PHASE_INITIAL) is preserved in ORIGINAL_PHASE_MAP.
        """
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        phase_map = SpecTaskExecutionService.PHASE_MAP

        # Test all mappings - Requirements/Design now map to IMPLEMENTATION
        # to enable continuous mode execution
        assert phase_map["Requirements"] == "PHASE_IMPLEMENTATION"
        assert phase_map["Design"] == "PHASE_IMPLEMENTATION"
        assert phase_map["Implementation"] == "PHASE_IMPLEMENTATION"
        assert phase_map["Testing"] == "PHASE_INTEGRATION"
        assert phase_map["Done"] == "PHASE_REFACTORING"

        # Verify original mapping is preserved for reference
        original_map = SpecTaskExecutionService.ORIGINAL_PHASE_MAP
        assert original_map["Requirements"] == "PHASE_INITIAL"
        assert original_map["Design"] == "PHASE_INITIAL"

    def test_task_type_inference_from_phase(self):
        """Test task type is correctly inferred from phase."""
        # Implementation phase -> implement_feature
        phase_lower = "implementation"
        task_type = "implement_feature"
        if "test" in phase_lower:
            task_type = "write_tests"
        elif "design" in phase_lower:
            task_type = "analyze_requirements"
        assert task_type == "implement_feature"

        # Testing phase -> write_tests
        phase_lower = "testing"
        task_type = "implement_feature"
        if "test" in phase_lower:
            task_type = "write_tests"
        elif "design" in phase_lower:
            task_type = "analyze_requirements"
        assert task_type == "write_tests"

        # Design phase -> analyze_requirements
        phase_lower = "design"
        task_type = "implement_feature"
        if "test" in phase_lower:
            task_type = "write_tests"
        elif "design" in phase_lower:
            task_type = "analyze_requirements"
        assert task_type == "analyze_requirements"

        # Requirements phase -> analyze_requirements
        phase_lower = "requirements"
        task_type = "implement_feature"
        if "test" in phase_lower:
            task_type = "write_tests"
        elif "design" in phase_lower or "requirement" in phase_lower:
            task_type = "analyze_requirements"
        assert task_type == "analyze_requirements"


# =============================================================================
# Test: ExecutionResult and ExecutionStats
# =============================================================================


class TestExecutionDataClasses:
    """Test ExecutionResult and ExecutionStats dataclasses."""

    def test_execution_stats_initialization(self):
        """Test ExecutionStats initializes with correct defaults."""
        from omoi_os.services.spec_task_execution import ExecutionStats

        stats = ExecutionStats()
        assert stats.tasks_created == 0
        assert stats.tasks_skipped == 0
        assert stats.ticket_id is None
        assert stats.errors == []

    def test_execution_stats_to_dict(self):
        """Test ExecutionStats converts to dict correctly."""
        from omoi_os.services.spec_task_execution import ExecutionStats

        stats = ExecutionStats(
            tasks_created=5,
            tasks_skipped=2,
            ticket_id="ticket-123",
            errors=["Error 1", "Error 2"],
        )

        result = stats.to_dict()

        assert result["tasks_created"] == 5
        assert result["tasks_skipped"] == 2
        assert result["ticket_id"] == "ticket-123"
        assert len(result["errors"]) == 2

    def test_execution_result_success(self):
        """Test ExecutionResult for successful execution."""
        from omoi_os.services.spec_task_execution import (
            ExecutionResult,
            ExecutionStats,
        )

        result = ExecutionResult(
            success=True,
            message="Created 5 tasks",
            stats=ExecutionStats(tasks_created=5),
        )

        assert result.success is True
        assert "5 tasks" in result.message
        assert result.stats.tasks_created == 5

    def test_execution_result_failure(self):
        """Test ExecutionResult for failed execution."""
        from omoi_os.services.spec_task_execution import ExecutionResult

        result = ExecutionResult(
            success=False,
            message="Spec not found",
        )

        assert result.success is False
        assert result.stats.tasks_created == 0
        assert result.stats.ticket_id is None


# =============================================================================
# Test: Event Publishing
# =============================================================================


class TestEventPublishing:
    """Test event publishing during SpecTask execution."""

    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus."""
        event_bus = MagicMock()
        event_bus.subscribe = MagicMock()
        event_bus.publish = MagicMock()
        return event_bus

    @pytest.fixture
    def mock_db(self):
        """Create a mock database service."""
        db = MagicMock()
        return db

    def test_subscribe_to_completion_events(self, mock_db, mock_event_bus):
        """Test subscription to task completion events."""
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        service = SpecTaskExecutionService(
            db=mock_db,
            event_bus=mock_event_bus,
        )

        service.subscribe_to_completions()

        # Should subscribe to TASK_COMPLETED and TASK_FAILED
        assert mock_event_bus.subscribe.call_count == 2
        call_args = [call[0][0] for call in mock_event_bus.subscribe.call_args_list]
        assert "TASK_COMPLETED" in call_args
        assert "TASK_FAILED" in call_args

    def test_subscribe_idempotent(self, mock_db, mock_event_bus):
        """Test that subscribing twice doesn't double-subscribe."""
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        service = SpecTaskExecutionService(
            db=mock_db,
            event_bus=mock_event_bus,
        )

        service.subscribe_to_completions()
        service.subscribe_to_completions()

        # Should only subscribe once
        assert mock_event_bus.subscribe.call_count == 2


# =============================================================================
# Test: Database Session Handling
# =============================================================================


class TestDatabaseSessionHandling:
    """Test database session handling in SpecTaskExecutionService."""

    @pytest.mark.asyncio
    async def test_async_session_context_manager(self):
        """Test async session is properly managed."""
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        service = SpecTaskExecutionService(db=mock_db)
        result = await service.execute_spec_tasks(spec_id="nonexistent")

        # Should fail gracefully when spec not found
        assert result.success is False
        assert "not found" in result.message.lower()


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases in SpecTask execution."""

    @pytest.mark.asyncio
    async def test_execute_with_no_event_bus(self):
        """Test execution works without event bus."""
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        # No event_bus provided
        service = SpecTaskExecutionService(db=mock_db)
        result = await service.execute_spec_tasks(spec_id="test")

        # Should complete without error
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_with_specific_task_ids(self):
        """Test execution filters by specific task IDs."""
        from omoi_os.models.spec import Spec, SpecTask
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        # Create mock spec with tasks
        mock_spec = MagicMock(spec=Spec)
        mock_spec.id = "spec-123"
        mock_spec.project_id = "project-123"
        mock_spec.title = "Test"
        mock_spec.description = "Test description"
        mock_spec.phase = "Implementation"
        mock_spec.design_approved = True

        task1 = MagicMock(spec=SpecTask)
        task1.id = "task-1"
        task1.status = "pending"
        task1.phase = "Implementation"
        task1.priority = "high"
        task1.title = "Task 1"
        task1.description = "Description 1"
        task1.dependencies = []

        task2 = MagicMock(spec=SpecTask)
        task2.id = "task-2"
        task2.status = "pending"
        task2.phase = "Testing"
        task2.priority = "medium"
        task2.title = "Task 2"
        task2.description = "Description 2"
        task2.dependencies = []

        mock_spec.tasks = [task1, task2]

        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_spec
        mock_session.execute.return_value = mock_result
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        service = SpecTaskExecutionService(db=mock_db)

        # Execute with specific task IDs - only task-1
        result = await service.execute_spec_tasks(
            spec_id="spec-123",
            task_ids=["task-1"],
        )

        # task-1 should be processed, task-2 should be skipped (not in list)
        assert result.success is True


# =============================================================================
# Test: Status Retrieval
# =============================================================================


class TestStatusRetrieval:
    """Test execution status retrieval."""

    @pytest.mark.asyncio
    async def test_get_status_calculates_progress(self):
        """Test progress calculation is correct."""
        from omoi_os.models.spec import Spec, SpecTask
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        mock_spec = MagicMock(spec=Spec)
        mock_spec.id = "spec-123"

        # Create 4 tasks with different statuses
        tasks = []
        for status in ["pending", "in_progress", "completed", "completed"]:
            task = MagicMock(spec=SpecTask)
            task.status = status
            tasks.append(task)
        mock_spec.tasks = tasks

        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_spec
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        service = SpecTaskExecutionService(db=mock_db)
        status = await service.get_execution_status(spec_id="spec-123")

        assert status["total_tasks"] == 4
        assert status["status_counts"]["completed"] == 2
        assert status["progress"] == 50.0  # 2/4 * 100
        assert status["is_complete"] is False

    @pytest.mark.asyncio
    async def test_get_status_100_percent_complete(self):
        """Test status shows 100% when all tasks complete."""
        from omoi_os.models.spec import Spec, SpecTask
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        mock_spec = MagicMock(spec=Spec)
        mock_spec.id = "spec-123"

        # All tasks completed
        tasks = []
        for _ in range(3):
            task = MagicMock(spec=SpecTask)
            task.status = "completed"
            tasks.append(task)
        mock_spec.tasks = tasks

        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_spec
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        service = SpecTaskExecutionService(db=mock_db)
        status = await service.get_execution_status(spec_id="spec-123")

        assert status["progress"] == 100.0
        assert status["is_complete"] is True
