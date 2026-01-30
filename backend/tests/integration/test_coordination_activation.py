"""Integration tests for coordination activation in spec task execution.

Tests the end-to-end flow where:
1. SpecTaskExecutionService parses parallel_opportunities from spec.phase_data
2. CoordinationService.register_join() is called for each parallel group
3. coordination.join.created events are published
4. SynthesisService receives events and tracks pending joins
5. When parallel tasks complete, synthesis_context is populated on continuation task

These tests verify the "wiring" between:
- SpecTaskExecutionService (parses parallel opportunities, calls register_join)
- CoordinationService (publishes coordination.join.created events)
- SynthesisService (handles events, triggers synthesis when ready)
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from omoi_os.models.spec import Spec, SpecTask
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.coordination import CoordinationService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.spec_task_execution import (
    SpecTaskExecutionService,
    ParallelGroup,
)
from omoi_os.services.synthesis_service import (
    SynthesisService,
    reset_synthesis_service,
)
from omoi_os.services.task_queue import TaskQueueService


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def spec_with_parallel_opportunities(db_service: DatabaseService) -> Spec:
    """Create a spec with phase_data containing parallel opportunities."""
    with db_service.get_session() as session:
        # Create project first
        from omoi_os.models.project import Project
        project = Project(
            id=f"proj-{uuid4().hex[:8]}",
            name="Test Project",
            description="For testing parallel coordination",
        )
        session.add(project)
        session.flush()

        spec = Spec(
            id=f"spec-{uuid4().hex[:8]}",
            project_id=project.id,
            title="Test Spec with Parallel Tasks",
            description="Testing parallel task coordination",
            status="executing",
            design_approved=True,  # Required for execution
            phase_data={
                "sync": {
                    "dependency_analysis": {
                        "task_dependency_graph": {
                            "TSK-001": [],
                            "TSK-002": ["TSK-001"],
                            "TSK-003": ["TSK-001", "TSK-002"],
                            "TSK-004": ["TSK-001", "TSK-002"],
                            "TSK-005": ["TSK-003", "TSK-004"],  # Continuation
                        },
                        "parallel_opportunities": [
                            "TSK-003 and TSK-004 can run in parallel after TSK-002"
                        ],
                    }
                }
            },
        )
        session.add(spec)
        session.flush()

        # Create SpecTasks that match the dependency graph
        for i in range(1, 6):
            spec_task = SpecTask(
                id=f"TSK-00{i}",
                spec_id=spec.id,
                title=f"Task {i}",
                description=f"Description for task {i}",
                phase="implementation",
                priority="medium",
                status="pending",
            )
            session.add(spec_task)

        session.commit()

        # Refresh to get relationships
        session.refresh(spec)
        session.expunge(spec)
        return spec


@pytest.fixture
def task_queue_service(
    db_service: DatabaseService, event_bus_service: EventBusService
) -> TaskQueueService:
    """Create a TaskQueueService."""
    return TaskQueueService(db_service, event_bus=event_bus_service)


@pytest.fixture
def coordination_service(
    db_service: DatabaseService,
    task_queue_service: TaskQueueService,
    event_bus_service: EventBusService,
) -> CoordinationService:
    """Create a CoordinationService."""
    return CoordinationService(db_service, task_queue_service, event_bus_service)


@pytest.fixture
def synthesis_service(
    db_service: DatabaseService, event_bus_service: EventBusService
) -> SynthesisService:
    """Create a SynthesisService."""
    reset_synthesis_service()
    service = SynthesisService(db=db_service, event_bus=event_bus_service)
    service.subscribe_to_events()
    return service


@pytest.fixture
def spec_task_execution_service(
    db_service: DatabaseService,
    event_bus_service: EventBusService,
    coordination_service: CoordinationService,
) -> SpecTaskExecutionService:
    """Create a SpecTaskExecutionService with coordination enabled."""
    return SpecTaskExecutionService(
        db=db_service,
        event_bus=event_bus_service,
        coordination=coordination_service,
    )


# =============================================================================
# PARALLEL OPPORTUNITY PARSING TESTS
# =============================================================================


class TestOwnedFilesExtraction:
    """Tests for extracting owned_files from spec.phase_data."""

    def test_extract_owned_files_from_phase_data(
        self, db_service: DatabaseService
    ):
        """Test extracting files_to_create and files_to_modify from phase_data."""
        service = SpecTaskExecutionService(db=db_service)

        spec = MagicMock()
        spec.id = "test-spec"
        spec.phase_data = {
            "tasks": {
                "tasks": [
                    {
                        "id": "TSK-001",
                        "title": "Implement user service",
                        "files_to_create": ["src/services/user.py", "src/models/user.py"],
                        "files_to_modify": ["src/api/routes.py"],
                    },
                    {
                        "id": "TSK-002",
                        "title": "Add tests",
                        "files_to_create": ["tests/test_user.py"],
                        "files_to_modify": [],
                    },
                ]
            }
        }

        # Test task with both create and modify
        owned_files = service._extract_owned_files(spec, "TSK-001")
        assert owned_files is not None
        assert len(owned_files) == 3
        assert "src/services/user.py" in owned_files
        assert "src/models/user.py" in owned_files
        assert "src/api/routes.py" in owned_files

        # Test task with only create
        owned_files_2 = service._extract_owned_files(spec, "TSK-002")
        assert owned_files_2 is not None
        assert len(owned_files_2) == 1
        assert "tests/test_user.py" in owned_files_2

    def test_extract_owned_files_missing_task(
        self, db_service: DatabaseService
    ):
        """Test that missing task returns None."""
        service = SpecTaskExecutionService(db=db_service)

        spec = MagicMock()
        spec.id = "test-spec"
        spec.phase_data = {
            "tasks": {
                "tasks": [{"id": "TSK-001", "title": "Task 1"}]
            }
        }

        result = service._extract_owned_files(spec, "TSK-999")
        assert result is None

    def test_extract_owned_files_empty_phase_data(
        self, db_service: DatabaseService
    ):
        """Test that empty phase_data returns None."""
        service = SpecTaskExecutionService(db=db_service)

        spec = MagicMock()
        spec.id = "test-spec"
        spec.phase_data = {}

        result = service._extract_owned_files(spec, "TSK-001")
        assert result is None

    def test_extract_owned_files_directory_glob_conversion(
        self, db_service: DatabaseService
    ):
        """Test that directory paths are converted to glob patterns."""
        service = SpecTaskExecutionService(db=db_service)

        spec = MagicMock()
        spec.id = "test-spec"
        spec.phase_data = {
            "tasks": {
                "tasks": [
                    {
                        "id": "TSK-001",
                        "title": "Task 1",
                        "files_to_create": ["src/services/"],
                        "files_to_modify": ["src/api/routes/"],
                    }
                ]
            }
        }

        owned_files = service._extract_owned_files(spec, "TSK-001")
        assert owned_files is not None
        assert "src/services/**" in owned_files
        assert "src/api/routes/**" in owned_files

    def test_extract_owned_files_deduplication(
        self, db_service: DatabaseService
    ):
        """Test that duplicate file paths are deduplicated."""
        service = SpecTaskExecutionService(db=db_service)

        spec = MagicMock()
        spec.id = "test-spec"
        spec.phase_data = {
            "tasks": {
                "tasks": [
                    {
                        "id": "TSK-001",
                        "title": "Task 1",
                        "files_to_create": ["src/user.py"],
                        "files_to_modify": ["src/user.py"],  # Same file
                    }
                ]
            }
        }

        owned_files = service._extract_owned_files(spec, "TSK-001")
        assert owned_files is not None
        assert len(owned_files) == 1
        assert "src/user.py" in owned_files


class TestParallelOpportunityParsing:
    """Tests for parsing parallel opportunities from spec.phase_data."""

    def test_parse_simple_parallel_opportunity(
        self, db_service: DatabaseService
    ):
        """Test parsing a simple parallel opportunity string."""
        service = SpecTaskExecutionService(db=db_service)

        # Create a mock spec with phase_data
        spec = MagicMock()
        spec.id = "test-spec"
        spec.phase_data = {
            "sync": {
                "dependency_analysis": {
                    "task_dependency_graph": {
                        "TSK-001": [],
                        "TSK-002": ["TSK-001"],
                        "TSK-003": ["TSK-002"],
                    },
                    "parallel_opportunities": [
                        "TSK-001 and TSK-002 can run in parallel"
                    ],
                }
            }
        }

        # Mapping from spec_task_id to created task_id
        task_mapping = {
            "TSK-001": "task-uuid-001",
            "TSK-002": "task-uuid-002",
            "TSK-003": "task-uuid-003",
        }

        groups = service._parse_parallel_opportunities(spec, task_mapping)

        assert len(groups) == 1
        assert set(groups[0].source_task_ids) == {"task-uuid-001", "task-uuid-002"}

    def test_parse_multiple_parallel_opportunities(
        self, db_service: DatabaseService
    ):
        """Test parsing multiple parallel opportunities."""
        service = SpecTaskExecutionService(db=db_service)

        spec = MagicMock()
        spec.id = "test-spec"
        spec.phase_data = {
            "sync": {
                "dependency_analysis": {
                    "task_dependency_graph": {
                        "TSK-001": [],
                        "TSK-002": [],
                        "TSK-003": [],
                        "TSK-004": ["TSK-001", "TSK-002"],
                        "TSK-005": ["TSK-001", "TSK-002", "TSK-003"],
                    },
                    "parallel_opportunities": [
                        "TSK-001 and TSK-002 can run in parallel",
                        "TSK-001, TSK-002, and TSK-003 are independent",
                    ],
                }
            }
        }

        task_mapping = {
            f"TSK-00{i}": f"task-uuid-00{i}" for i in range(1, 6)
        }

        groups = service._parse_parallel_opportunities(spec, task_mapping)

        assert len(groups) == 2

    def test_parse_finds_continuation_task(
        self, db_service: DatabaseService
    ):
        """Test that continuation task is found from dependency graph."""
        service = SpecTaskExecutionService(db=db_service)

        spec = MagicMock()
        spec.id = "test-spec"
        spec.phase_data = {
            "sync": {
                "dependency_analysis": {
                    "task_dependency_graph": {
                        "TSK-001": [],
                        "TSK-002": [],
                        "TSK-003": ["TSK-001", "TSK-002"],  # Depends on both
                    },
                    "parallel_opportunities": [
                        "TSK-001 and TSK-002 can run in parallel"
                    ],
                }
            }
        }

        task_mapping = {
            "TSK-001": "task-uuid-001",
            "TSK-002": "task-uuid-002",
            "TSK-003": "task-uuid-003",
        }

        groups = service._parse_parallel_opportunities(spec, task_mapping)

        assert len(groups) == 1
        assert groups[0].continuation_task_id == "task-uuid-003"

    def test_parse_empty_phase_data(self, db_service: DatabaseService):
        """Test parsing with empty phase_data."""
        service = SpecTaskExecutionService(db=db_service)

        spec = MagicMock()
        spec.id = "test-spec"
        spec.phase_data = {}

        groups = service._parse_parallel_opportunities(spec, {})

        assert len(groups) == 0

    def test_parse_no_parallel_opportunities(self, db_service: DatabaseService):
        """Test parsing when no parallel opportunities exist."""
        service = SpecTaskExecutionService(db=db_service)

        spec = MagicMock()
        spec.id = "test-spec"
        spec.phase_data = {
            "sync": {
                "dependency_analysis": {
                    "task_dependency_graph": {"TSK-001": []},
                    "parallel_opportunities": [],
                }
            }
        }

        groups = service._parse_parallel_opportunities(spec, {"TSK-001": "task-1"})

        assert len(groups) == 0


# =============================================================================
# COORDINATION REGISTRATION TESTS
# =============================================================================


class TestCoordinationRegistration:
    """Tests for CoordinationService.register_join() method."""

    def test_register_join_publishes_event(
        self,
        db_service: DatabaseService,
        task_queue_service: TaskQueueService,
        event_bus_service: EventBusService,
    ):
        """Test that register_join publishes coordination.join.created event.

        Note: Since EventBus requires Redis which may not be available in tests,
        we mock the event_bus.publish method to capture published events.
        """
        # Create ticket and tasks
        with db_service.get_session() as session:
            ticket = Ticket(
                title="Test Ticket",
                description="Testing coordination",
                phase_id="PHASE_IMPLEMENTATION",
                status="in_progress",
                priority="MEDIUM",
            )
            session.add(ticket)
            session.commit()
            ticket_id = ticket.id

        # Create tasks
        task1 = task_queue_service.enqueue_task(
            ticket_id=ticket_id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="parallel_1",
            description="Parallel task 1",
            priority="MEDIUM",
        )
        task2 = task_queue_service.enqueue_task(
            ticket_id=ticket_id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="parallel_2",
            description="Parallel task 2",
            priority="MEDIUM",
        )
        continuation = task_queue_service.enqueue_task(
            ticket_id=ticket_id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="continuation",
            description="Continuation task",
            priority="MEDIUM",
        )

        # Track published events by mocking publish
        published_events = []
        original_publish = event_bus_service.publish

        def mock_publish(event):
            published_events.append(event)
            original_publish(event)

        event_bus_service.publish = mock_publish

        try:
            # Create coordination service and register join
            coordination = CoordinationService(
                db_service, task_queue_service, event_bus_service
            )
            coordination.register_join(
                join_id="test-join",
                source_task_ids=[task1.id, task2.id],
                continuation_task_id=continuation.id,
                merge_strategy="combine",
            )

            # Verify event was published
            coord_events = [e for e in published_events if e.event_type == "coordination.join.created"]
            assert len(coord_events) == 1
            event = coord_events[0]
            assert event.payload["join_id"] == "test-join"
            assert set(event.payload["source_task_ids"]) == {task1.id, task2.id}
            assert event.payload["continuation_task_id"] == continuation.id
            assert event.payload["merge_strategy"] == "combine"
        finally:
            event_bus_service.publish = original_publish

    def test_register_join_updates_continuation_dependencies(
        self,
        db_service: DatabaseService,
        task_queue_service: TaskQueueService,
        event_bus_service: EventBusService,
    ):
        """Test that register_join updates continuation task dependencies."""
        # Create ticket and tasks
        with db_service.get_session() as session:
            ticket = Ticket(
                title="Test Ticket",
                description="Testing coordination",
                phase_id="PHASE_IMPLEMENTATION",
                status="in_progress",
                priority="MEDIUM",
            )
            session.add(ticket)
            session.commit()
            ticket_id = ticket.id

        task1 = task_queue_service.enqueue_task(
            ticket_id=ticket_id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="parallel_1",
            description="Parallel task 1",
            priority="MEDIUM",
        )
        task2 = task_queue_service.enqueue_task(
            ticket_id=ticket_id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="parallel_2",
            description="Parallel task 2",
            priority="MEDIUM",
        )
        continuation = task_queue_service.enqueue_task(
            ticket_id=ticket_id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="continuation",
            description="Continuation task",
            priority="MEDIUM",
        )

        coordination = CoordinationService(
            db_service, task_queue_service, event_bus_service
        )
        coordination.register_join(
            join_id="test-join",
            source_task_ids=[task1.id, task2.id],
            continuation_task_id=continuation.id,
            merge_strategy="combine",
        )

        # Verify continuation task dependencies were updated
        with db_service.get_session() as session:
            updated_cont = session.query(Task).filter(Task.id == continuation.id).first()
            assert updated_cont.dependencies is not None
            depends_on = updated_cont.dependencies.get("depends_on", [])
            assert task1.id in depends_on
            assert task2.id in depends_on


# =============================================================================
# END-TO-END SYNTHESIS TESTS
# =============================================================================


class TestEndToEndSynthesis:
    """End-to-end tests for the full coordination → synthesis flow.

    Note: Since EventBus requires Redis which may not be available in tests,
    these tests directly call the handlers that would normally be triggered
    by Redis pub/sub events.
    """

    def test_synthesis_triggers_when_parallel_tasks_complete(
        self,
        db_service: DatabaseService,
        event_bus_service: EventBusService,
    ):
        """Test that synthesis is triggered when all parallel tasks complete."""
        reset_synthesis_service()

        # Create ticket
        with db_service.get_session() as session:
            ticket = Ticket(
                title="E2E Synthesis Test",
                description="Testing end-to-end synthesis flow",
                phase_id="PHASE_IMPLEMENTATION",
                status="in_progress",
                priority="MEDIUM",
            )
            session.add(ticket)
            session.commit()
            ticket_id = ticket.id

        # Create parallel source tasks (already completed with results)
        task_ids = []
        with db_service.get_session() as session:
            for i in range(2):
                task = Task(
                    ticket_id=ticket_id,
                    phase_id="PHASE_IMPLEMENTATION",
                    task_type=f"parallel_{i}",
                    description=f"Parallel task {i}",
                    priority="MEDIUM",
                    status="completed",
                    result={"output": f"result_{i}", "data": {"key": f"value{i}"}},
                )
                session.add(task)
                session.commit()
                task_ids.append(task.id)

        # Create continuation task (pending)
        with db_service.get_session() as session:
            continuation = Task(
                ticket_id=ticket_id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="continuation",
                description="Continuation task",
                priority="MEDIUM",
                status="pending",
            )
            session.add(continuation)
            session.commit()
            continuation_id = continuation.id

        # Create services
        task_queue = TaskQueueService(db_service, event_bus=event_bus_service)
        synthesis = SynthesisService(db=db_service, event_bus=event_bus_service)

        # Capture published events and forward to synthesis service handlers
        def mock_publish(event):
            if event.event_type == "coordination.join.created":
                synthesis._handle_join_created(event)

        original_publish = event_bus_service.publish
        event_bus_service.publish = mock_publish

        try:
            coordination = CoordinationService(db_service, task_queue, event_bus_service)

            # Register join - since tasks are already completed, synthesis should trigger immediately
            coordination.register_join(
                join_id="e2e-join",
                source_task_ids=task_ids,
                continuation_task_id=continuation_id,
                merge_strategy="combine",
            )
        finally:
            event_bus_service.publish = original_publish

        # Verify synthesis_context was injected into continuation task
        with db_service.get_session() as session:
            updated_cont = session.query(Task).filter(Task.id == continuation_id).first()
            assert updated_cont.synthesis_context is not None
            assert "_source_results" in updated_cont.synthesis_context
            assert updated_cont.synthesis_context["_source_count"] == 2
            assert updated_cont.synthesis_context["_merge_strategy"] == "combine"

    def test_synthesis_waits_for_pending_tasks(
        self,
        db_service: DatabaseService,
        event_bus_service: EventBusService,
    ):
        """Test that synthesis waits until all parallel tasks complete."""
        reset_synthesis_service()

        # Create ticket
        with db_service.get_session() as session:
            ticket = Ticket(
                title="Pending Tasks Test",
                description="Testing synthesis waiting for pending tasks",
                phase_id="PHASE_IMPLEMENTATION",
                status="in_progress",
                priority="MEDIUM",
            )
            session.add(ticket)
            session.commit()
            ticket_id = ticket.id

        # Create parallel source tasks (PENDING)
        task_ids = []
        with db_service.get_session() as session:
            for i in range(2):
                task = Task(
                    ticket_id=ticket_id,
                    phase_id="PHASE_IMPLEMENTATION",
                    task_type=f"parallel_{i}",
                    description=f"Parallel task {i}",
                    priority="MEDIUM",
                    status="pending",  # Not completed yet
                )
                session.add(task)
                session.commit()
                task_ids.append(task.id)

        # Create continuation task
        with db_service.get_session() as session:
            continuation = Task(
                ticket_id=ticket_id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="continuation",
                description="Continuation task",
                priority="MEDIUM",
                status="pending",
            )
            session.add(continuation)
            session.commit()
            continuation_id = continuation.id

        # Create services
        task_queue = TaskQueueService(db_service, event_bus=event_bus_service)
        synthesis = SynthesisService(db=db_service, event_bus=event_bus_service)

        # Capture published events and forward to synthesis service handlers
        def mock_publish(event):
            if event.event_type == "coordination.join.created":
                synthesis._handle_join_created(event)

        original_publish = event_bus_service.publish
        event_bus_service.publish = mock_publish

        try:
            coordination = CoordinationService(db_service, task_queue, event_bus_service)

            # Register join - tasks are pending, so synthesis should NOT trigger yet
            coordination.register_join(
                join_id="pending-join",
                source_task_ids=task_ids,
                continuation_task_id=continuation_id,
                merge_strategy="combine",
            )
        finally:
            event_bus_service.publish = original_publish

        # Join should be registered but pending
        pending = synthesis.get_pending_join("pending-join")
        assert pending is not None
        assert len(pending.completed_source_ids) == 0

        # Continuation should NOT have synthesis_context yet
        with db_service.get_session() as session:
            cont = session.query(Task).filter(Task.id == continuation_id).first()
            assert cont.synthesis_context is None

        # Complete first task
        with db_service.get_session() as session:
            task = session.query(Task).filter(Task.id == task_ids[0]).first()
            task.status = "completed"
            task.result = {"output": "result_0"}
            session.commit()

        # Send TASK_COMPLETED event directly to handler
        synthesis._handle_task_completed(
            SystemEvent(
                event_type="TASK_COMPLETED",
                entity_type="task",
                entity_id=task_ids[0],
                payload={},
            )
        )

        # Still pending (need both tasks)
        pending = synthesis.get_pending_join("pending-join")
        assert pending is not None
        assert len(pending.completed_source_ids) == 1

        # Complete second task
        with db_service.get_session() as session:
            task = session.query(Task).filter(Task.id == task_ids[1]).first()
            task.status = "completed"
            task.result = {"output": "result_1"}
            session.commit()

        synthesis._handle_task_completed(
            SystemEvent(
                event_type="TASK_COMPLETED",
                entity_type="task",
                entity_id=task_ids[1],
                payload={},
            )
        )

        # Now synthesis should have triggered
        assert synthesis.get_pending_join("pending-join") is None

        # Continuation should have synthesis_context
        with db_service.get_session() as session:
            cont = session.query(Task).filter(Task.id == continuation_id).first()
            assert cont.synthesis_context is not None
            assert cont.synthesis_context["_source_count"] == 2
