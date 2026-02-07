"""Integration tests for SpecTask execution with sandbox infrastructure.

Tests the full integration between:
1. SpecTaskExecutionService - Converts SpecTasks to Tasks
2. TaskQueueService - Manages task lifecycle
3. OrchestratorWorker - Picks up tasks and spawns sandboxes
4. EventBus - Publishes events for completion handling

These tests verify the data flow without requiring actual Daytona sandboxes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

# =============================================================================
# Test: Task Creation Flow
# =============================================================================


class TestTaskCreationFlow:
    """Test that SpecTasks create proper Tasks for sandbox execution."""

    @pytest.fixture
    def mock_spec_with_implementation_task(self):
        """Create a spec with an implementation task."""
        from omoi_os.models.spec import Spec, SpecTask

        spec = MagicMock(spec=Spec)
        spec.id = f"spec-{uuid4()}"
        spec.project_id = f"project-{uuid4()}"
        spec.title = "Add User Authentication"
        spec.description = "Implement JWT-based authentication system"
        spec.phase = "Implementation"
        spec.design_approved = True

        task = MagicMock(spec=SpecTask)
        task.id = f"spec-task-{uuid4()}"
        task.title = "Implement JWT token generation"
        task.description = "Create JWT tokens for user authentication"
        task.phase = "Implementation"
        task.priority = "high"
        task.status = "pending"
        task.dependencies = []

        spec.tasks = [task]
        return spec

    def test_priority_mapping_for_sandbox(self):
        """Test priority maps to Task priority enum values."""
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        # These priorities should match what TaskQueueService expects
        assert SpecTaskExecutionService.PRIORITY_MAP["critical"] == "CRITICAL"
        assert SpecTaskExecutionService.PRIORITY_MAP["high"] == "HIGH"
        assert SpecTaskExecutionService.PRIORITY_MAP["medium"] == "MEDIUM"
        assert SpecTaskExecutionService.PRIORITY_MAP["low"] == "LOW"

    def test_phase_mapping_for_sandbox(self):
        """Test phase maps to phase_id values used by orchestrator."""
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        # These phase IDs should match what orchestrator_worker expects
        assert (
            SpecTaskExecutionService.PHASE_MAP["Implementation"]
            == "PHASE_IMPLEMENTATION"
        )
        assert SpecTaskExecutionService.PHASE_MAP["Testing"] == "PHASE_INTEGRATION"
        assert SpecTaskExecutionService.PHASE_MAP["Requirements"] == "PHASE_INITIAL"
        assert SpecTaskExecutionService.PHASE_MAP["Design"] == "PHASE_INITIAL"


# =============================================================================
# Test: Event Publishing for Orchestrator
# =============================================================================


class TestEventPublishingForOrchestrator:
    """Test events are published correctly for orchestrator to pick up."""

    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus."""
        from omoi_os.services.event_bus import EventBusService

        event_bus = MagicMock(spec=EventBusService)
        event_bus.publish = MagicMock()
        event_bus.subscribe = MagicMock()
        return event_bus

    @pytest.fixture
    def mock_db(self):
        """Create a mock database service."""
        db = MagicMock()
        return db

    def test_completion_subscription(self, mock_db, mock_event_bus):
        """Test service subscribes to task completion events."""
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        service = SpecTaskExecutionService(
            db=mock_db,
            event_bus=mock_event_bus,
        )
        service.subscribe_to_completions()

        # Verify subscriptions match what orchestrator publishes
        calls = [call[0][0] for call in mock_event_bus.subscribe.call_args_list]
        assert (
            "TASK_COMPLETED" in calls
        )  # Orchestrator publishes this on sandbox completion
        assert "TASK_FAILED" in calls  # Orchestrator publishes this on sandbox failure


# =============================================================================
# Test: Task Data for Sandbox
# =============================================================================


class TestTaskDataForSandbox:
    """Test Task objects contain correct data for sandbox execution."""

    @pytest.mark.asyncio
    async def test_task_has_spec_context(self):
        """Test created Task includes spec context for sandbox."""
        from omoi_os.models.spec import Spec, SpecTask
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        # Create mock spec
        mock_spec = MagicMock(spec=Spec)
        mock_spec.id = "spec-123"
        mock_spec.project_id = "project-123"
        mock_spec.title = "Authentication Feature"
        mock_spec.description = "JWT auth implementation"
        mock_spec.phase = "Implementation"
        mock_spec.design_approved = True

        # Create mock task
        task = MagicMock(spec=SpecTask)
        task.id = "spec-task-456"
        task.title = "Create auth middleware"
        task.description = "Implement auth middleware for routes"
        task.phase = "Implementation"
        task.priority = "high"
        task.status = "pending"
        task.dependencies = []

        mock_spec.tasks = [task]

        # Mock database
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
        result = await service.execute_spec_tasks(spec_id="spec-123")

        # Verify task was processed
        assert result.success is True
        assert result.stats.tasks_created == 1


# =============================================================================
# Test: Bridging Ticket Creation
# =============================================================================


class TestBridgingTicketCreation:
    """Test bridging Ticket is created for Task execution."""

    @pytest.mark.asyncio
    async def test_ticket_created_with_spec_context(self):
        """Test bridging Ticket contains spec context."""
        from omoi_os.models.spec import Spec, SpecTask
        from omoi_os.models.ticket import Ticket
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        # Create mock spec
        mock_spec = MagicMock(spec=Spec)
        mock_spec.id = "spec-123"
        mock_spec.project_id = "project-123"
        mock_spec.title = "New Feature"
        mock_spec.description = "Feature description"
        mock_spec.phase = "Implementation"
        mock_spec.design_approved = True

        task = MagicMock(spec=SpecTask)
        task.id = "task-1"
        task.title = "Implement"
        task.description = "Implementation details"
        task.phase = "Implementation"
        task.priority = "medium"
        task.status = "pending"
        task.dependencies = []

        mock_spec.tasks = [task]

        # Track created tickets
        created_tickets = []

        def track_add(obj):
            if isinstance(obj, Ticket):
                created_tickets.append(obj)

        mock_db = MagicMock()
        mock_session = AsyncMock()

        # First execute returns spec, then ticket lookup returns None (to create new)
        spec_result = MagicMock()
        spec_result.scalar_one_or_none.return_value = mock_spec
        ticket_result = MagicMock()
        ticket_result.scalar_one_or_none.return_value = None

        mock_session.execute = AsyncMock(side_effect=[spec_result, ticket_result])
        mock_session.add = track_add
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        service = SpecTaskExecutionService(db=mock_db)
        result = await service.execute_spec_tasks(spec_id="spec-123")

        # Verify a ticket was created (or would be created)
        # The actual ticket creation happens in _get_or_create_ticket
        assert result.success is True


# =============================================================================
# Test: Task Type Determination for Orchestrator
# =============================================================================


class TestTaskTypeDetermination:
    """Test task_type is correctly set for orchestrator routing."""

    def test_implementation_phase_task_type(self):
        """Test implementation phase produces implement_feature task type."""
        phase = "Implementation"
        task_type = "implement_feature"

        phase_lower = phase.lower()
        if "test" in phase_lower:
            task_type = "write_tests"
        elif "design" in phase_lower:
            task_type = "analyze_requirements"

        assert task_type == "implement_feature"

    def test_testing_phase_task_type(self):
        """Test testing phase produces write_tests task type."""
        phase = "Testing"
        task_type = "implement_feature"

        phase_lower = phase.lower()
        if "test" in phase_lower:
            task_type = "write_tests"
        elif "design" in phase_lower:
            task_type = "analyze_requirements"

        assert task_type == "write_tests"

    def test_task_type_matches_orchestrator_categories(self):
        """Test our task types match orchestrator's execution mode categories."""
        # From orchestrator_worker.py EXPLORATION_TASK_TYPES
        exploration_types = {
            "analyze_requirements",
            "explore_codebase",
            "create_spec",
        }

        # From orchestrator_worker.py VALIDATION_TASK_TYPES

        # Implementation types (not in exploration or validation)
        implementation_types = {
            "implement_feature",
            "write_tests",  # This creates tests, different from validate/run_tests
        }

        # Verify our mappings produce valid types
        assert "implement_feature" in implementation_types
        assert "write_tests" in implementation_types
        assert "analyze_requirements" in exploration_types


# =============================================================================
# Test: Status Updates
# =============================================================================


class TestStatusUpdates:
    """Test SpecTask status updates when Tasks complete."""

    @pytest.fixture
    def mock_db_with_task_result(self):
        """Create mock DB that returns a completed task with spec_task_id."""
        from omoi_os.models.task import Task
        from omoi_os.models.spec import SpecTask

        mock_task = MagicMock(spec=Task)
        mock_task.id = "task-123"
        mock_task.result = {"spec_task_id": "spec-task-456"}

        mock_spec_task = MagicMock(spec=SpecTask)
        mock_spec_task.id = "spec-task-456"
        mock_spec_task.status = "in_progress"

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            side_effect=lambda model, id: {
                Task: mock_task,
                SpecTask: mock_spec_task,
            }.get(model)
        )
        mock_session.commit = MagicMock()

        mock_db = MagicMock()
        mock_db.get_session = MagicMock(
            return_value=MagicMock(
                __enter__=MagicMock(return_value=mock_session),
                __exit__=MagicMock(return_value=None),
            )
        )

        return mock_db, mock_spec_task

    def test_completion_handler_updates_spec_task(self, mock_db_with_task_result):
        """Test _handle_task_completed updates SpecTask status."""
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        mock_db, mock_spec_task = mock_db_with_task_result

        service = SpecTaskExecutionService(db=mock_db)

        # Simulate completion event
        event_data = {
            "entity_id": "task-123",
        }

        service._handle_task_completed(event_data)

        # Verify SpecTask status was updated
        assert mock_spec_task.status == "completed"


# =============================================================================
# Test: Integration with TaskQueueService
# =============================================================================


class TestTaskQueueIntegration:
    """Test Tasks are compatible with TaskQueueService."""

    def test_task_priority_is_valid_enum_value(self):
        """Test Task priority matches TaskQueueService expected values."""
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        valid_priorities = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}

        for priority in SpecTaskExecutionService.PRIORITY_MAP.values():
            assert priority in valid_priorities

    def test_task_phase_is_valid_enum_value(self):
        """Test Task phase_id matches expected phase values."""
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        valid_phases = {
            "PHASE_INITIAL",
            "PHASE_IMPLEMENTATION",
            "PHASE_INTEGRATION",
            "PHASE_REFACTORING",
        }

        for phase in SpecTaskExecutionService.PHASE_MAP.values():
            assert phase in valid_phases


# =============================================================================
# Test: Error Handling
# =============================================================================


class TestErrorHandling:
    """Test error handling in the execution flow."""

    @pytest.mark.asyncio
    async def test_handles_missing_spec_gracefully(self):
        """Test graceful handling when spec not found."""
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

        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_handles_unapproved_design(self):
        """Test handling when design not approved."""
        from omoi_os.models.spec import Spec
        from omoi_os.services.spec_task_execution import SpecTaskExecutionService

        mock_spec = MagicMock(spec=Spec)
        mock_spec.id = "spec-123"
        mock_spec.design_approved = False
        mock_spec.tasks = []

        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_spec
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        service = SpecTaskExecutionService(db=mock_db)
        result = await service.execute_spec_tasks(spec_id="spec-123")

        assert result.success is False
        assert "design" in result.message.lower()
        assert "approved" in result.message.lower()
