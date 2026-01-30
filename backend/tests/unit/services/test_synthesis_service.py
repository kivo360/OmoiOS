"""Unit tests for SynthesisService.

Tests the automatic result merging functionality for parallel task coordination.
Uses real database fixtures to properly test SQLAlchemy queries.
"""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.synthesis_service import (
    SynthesisService,
    PendingJoin,
    get_synthesis_service,
    reset_synthesis_service,
)


# =============================================================================
# DATACLASS TESTS (No database needed)
# =============================================================================


class TestPendingJoin:
    """Tests for the PendingJoin dataclass."""

    def test_is_ready_empty(self):
        """Test is_ready returns True when no sources required."""
        join = PendingJoin(
            join_id="join-1",
            source_task_ids=[],
            continuation_task_id="cont-1",
        )
        assert join.is_ready()

    def test_is_ready_none_completed(self):
        """Test is_ready returns False when no sources completed."""
        join = PendingJoin(
            join_id="join-1",
            source_task_ids=["task-1", "task-2"],
            continuation_task_id="cont-1",
        )
        assert not join.is_ready()

    def test_is_ready_partial_completed(self):
        """Test is_ready returns False when only some sources completed."""
        join = PendingJoin(
            join_id="join-1",
            source_task_ids=["task-1", "task-2"],
            continuation_task_id="cont-1",
            completed_source_ids=["task-1"],
        )
        assert not join.is_ready()

    def test_is_ready_all_completed(self):
        """Test is_ready returns True when all sources completed."""
        join = PendingJoin(
            join_id="join-1",
            source_task_ids=["task-1", "task-2"],
            continuation_task_id="cont-1",
            completed_source_ids=["task-1", "task-2"],
        )
        assert join.is_ready()

    def test_is_ready_order_independent(self):
        """Test is_ready doesn't depend on completion order."""
        join = PendingJoin(
            join_id="join-1",
            source_task_ids=["task-1", "task-2", "task-3"],
            continuation_task_id="cont-1",
            completed_source_ids=["task-3", "task-1", "task-2"],
        )
        assert join.is_ready()


# =============================================================================
# MERGE STRATEGY TESTS (No database needed)
# =============================================================================


class TestMergeStrategies:
    """Tests for result merging strategies."""

    @pytest.fixture
    def synthesis_service(self):
        """Create a SynthesisService with mock dependencies for merge tests."""
        reset_synthesis_service()
        mock_db = MagicMock()
        mock_event_bus = MagicMock()
        return SynthesisService(db=mock_db, event_bus=mock_event_bus)

    def test_apply_merge_strategy_combine(self, synthesis_service):
        """Test combine merge strategy preserves all keys."""
        results = [
            {"key1": "value1", "shared": "from1"},
            {"key2": "value2", "shared": "from2"},
        ]

        merged = synthesis_service._apply_merge_strategy(results, "combine")

        assert "_source_results" in merged
        assert "_merge_strategy" in merged
        assert merged["_merge_strategy"] == "combine"
        assert merged["_source_count"] == 2
        assert merged["key1"] == "value1"
        assert merged["key2"] == "value2"
        # First occurrence wins for non-conflicting flatten
        assert merged["shared"] == "from1"

    def test_apply_merge_strategy_union(self, synthesis_service):
        """Test union merge strategy (later values override)."""
        results = [
            {"key1": "value1", "shared": "from1"},
            {"key2": "value2", "shared": "from2"},
        ]

        merged = synthesis_service._apply_merge_strategy(results, "union")

        assert merged["_merge_strategy"] == "union"
        assert merged["shared"] == "from2"  # Later value wins

    def test_apply_merge_strategy_intersection(self, synthesis_service):
        """Test intersection merge strategy (only common keys)."""
        results = [
            {"shared": "from1", "only_in_1": "x"},
            {"shared": "from2", "only_in_2": "y"},
        ]

        merged = synthesis_service._apply_merge_strategy(results, "intersection")

        assert merged["_merge_strategy"] == "intersection"
        assert merged["shared"] == "from2"  # Value from last result
        assert "only_in_1" not in merged
        assert "only_in_2" not in merged

    def test_apply_merge_strategy_empty_results(self, synthesis_service):
        """Test merge with empty results returns empty dict."""
        merged = synthesis_service._apply_merge_strategy([], "combine")
        assert merged == {}

    def test_apply_merge_strategy_unknown_fallback(self, synthesis_service):
        """Test unknown strategy falls back to combine."""
        results = [{"key": "value"}]
        merged = synthesis_service._apply_merge_strategy(results, "unknown_strategy")

        # Should fall back to combine
        assert "_source_results" in merged
        assert merged["key"] == "value"

    def test_apply_merge_strategy_preserves_source_metadata(self, synthesis_service):
        """Test that _source_results preserves original results."""
        results = [
            {"_task_id": "task-1", "data": "first"},
            {"_task_id": "task-2", "data": "second"},
        ]

        merged = synthesis_service._apply_merge_strategy(results, "combine")

        assert len(merged["_source_results"]) == 2
        assert merged["_source_results"][0]["_task_id"] == "task-1"
        assert merged["_source_results"][1]["_task_id"] == "task-2"


# =============================================================================
# REGISTRATION TESTS (Mock event bus)
# =============================================================================


class TestSynthesisServiceRegistration:
    """Tests for join registration functionality."""

    @pytest.fixture
    def synthesis_service(self):
        """Create a SynthesisService with mock dependencies."""
        reset_synthesis_service()
        mock_db = MagicMock()
        # Make get_session return a context manager that returns a mock session
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=None)
        mock_event_bus = MagicMock()
        return SynthesisService(db=mock_db, event_bus=mock_event_bus)

    def test_register_join(self, synthesis_service):
        """Test registering a join operation."""
        synthesis_service.register_join(
            join_id="join-1",
            source_task_ids=["task-1", "task-2"],
            continuation_task_id="cont-1",
            merge_strategy="combine",
        )

        pending = synthesis_service.get_pending_join("join-1")
        assert pending is not None
        assert pending.join_id == "join-1"
        assert pending.source_task_ids == ["task-1", "task-2"]
        assert pending.continuation_task_id == "cont-1"
        assert pending.merge_strategy == "combine"

    def test_register_join_creates_reverse_lookup(self, synthesis_service):
        """Test that registering creates reverse lookup for source tasks."""
        synthesis_service.register_join(
            join_id="join-1",
            source_task_ids=["task-1", "task-2"],
            continuation_task_id="cont-1",
        )

        # Verify reverse lookup is created
        assert "task-1" in synthesis_service._task_to_joins
        assert "task-2" in synthesis_service._task_to_joins
        assert "join-1" in synthesis_service._task_to_joins["task-1"]
        assert "join-1" in synthesis_service._task_to_joins["task-2"]

    def test_handle_join_created_event(self, synthesis_service):
        """Test handling coordination.join.created event."""
        event_data = {
            "payload": {
                "join_id": "join-2",
                "source_task_ids": ["task-a", "task-b"],
                "continuation_task_id": "cont-2",
                "merge_strategy": "union",
            }
        }

        synthesis_service._handle_join_created(event_data)

        pending = synthesis_service.get_pending_join("join-2")
        assert pending is not None
        assert pending.merge_strategy == "union"

    def test_handle_join_created_ignores_invalid_event(self, synthesis_service):
        """Test that invalid events are ignored."""
        # Missing join_id
        synthesis_service._handle_join_created({"payload": {}})
        assert len(synthesis_service._pending_joins) == 0

        # Missing source_task_ids
        synthesis_service._handle_join_created({
            "payload": {"join_id": "j1", "continuation_task_id": "c1"}
        })
        assert len(synthesis_service._pending_joins) == 0

    def test_get_pending_joins_returns_copy(self, synthesis_service):
        """Test that get_pending_joins returns a copy, not the internal dict."""
        synthesis_service.register_join(
            join_id="join-1",
            source_task_ids=["task-1"],
            continuation_task_id="cont-1",
        )

        pending_copy = synthesis_service.get_pending_joins()
        pending_copy["new_key"] = "bad"

        # Internal state should not be modified
        assert "new_key" not in synthesis_service._pending_joins


# =============================================================================
# DATABASE INTEGRATION TESTS
# =============================================================================


class TestSynthesisServiceWithDatabase:
    """Tests that use real database fixtures to test SQLAlchemy queries."""

    @pytest.fixture
    def ticket(self, db_service: DatabaseService) -> Ticket:
        """Create a test ticket."""
        with db_service.get_session() as session:
            ticket = Ticket(
                title="Test Parallel Ticket",
                description="Testing parallel task synthesis",
                phase_id="PHASE_IMPLEMENTATION",
                status="in_progress",
                priority="MEDIUM",
            )
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            session.expunge(ticket)
            return ticket

    @pytest.fixture
    def source_tasks(self, db_service: DatabaseService, ticket: Ticket) -> list[Task]:
        """Create two source tasks that will be merged."""
        tasks = []
        with db_service.get_session() as session:
            for i in range(2):
                task = Task(
                    ticket_id=ticket.id,
                    phase_id="PHASE_IMPLEMENTATION",
                    task_type=f"parallel_task_{i}",
                    description=f"Parallel task {i}",
                    priority="MEDIUM",
                    status="completed",
                    result={"output": f"result_{i}", "files_changed": [f"file{i}.py"]},
                )
                session.add(task)
                session.commit()
                session.refresh(task)
                session.expunge(task)
                tasks.append(task)
        return tasks

    @pytest.fixture
    def continuation_task(self, db_service: DatabaseService, ticket: Ticket) -> Task:
        """Create a continuation task that will receive merged results."""
        with db_service.get_session() as session:
            task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="continuation_task",
                description="Task that continues after parallel tasks",
                priority="MEDIUM",
                status="pending",
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            session.expunge(task)
            return task

    @pytest.fixture
    def synthesis_service(
        self, db_service: DatabaseService, event_bus_service: EventBusService
    ) -> SynthesisService:
        """Create a SynthesisService with real database."""
        reset_synthesis_service()
        return SynthesisService(db=db_service, event_bus=event_bus_service)

    def test_merge_task_results_from_database(
        self, synthesis_service, source_tasks, db_service
    ):
        """Test merging results actually queries the database."""
        source_ids = [task.id for task in source_tasks]

        merged = synthesis_service._merge_task_results(
            source_task_ids=source_ids,
            merge_strategy="combine",
        )

        # Should have both results
        assert "_source_results" in merged
        assert len(merged["_source_results"]) == 2

        # Check that task metadata was added
        source_result = merged["_source_results"][0]
        assert "_task_id" in source_result
        assert "_task_type" in source_result

    def test_inject_synthesis_context_writes_to_database(
        self, synthesis_service, continuation_task, source_tasks, db_service
    ):
        """Test that synthesis context is actually written to the database."""
        source_ids = [task.id for task in source_tasks]
        test_context = {
            "merged_data": "test",
            "_source_count": 2,
        }

        synthesis_service._inject_synthesis_context(
            task_id=continuation_task.id,
            synthesis_context=test_context,
            source_task_ids=source_ids,
            join_id="test-join",
        )

        # Verify it was written to database
        with db_service.get_session() as session:
            updated_task = session.query(Task).filter(Task.id == continuation_task.id).first()
            assert updated_task is not None
            assert updated_task.synthesis_context is not None
            assert updated_task.synthesis_context["merged_data"] == "test"
            assert updated_task.synthesis_context["_join_id"] == "test-join"
            assert updated_task.synthesis_context["_source_task_ids"] == source_ids

    def test_full_synthesis_flow(
        self, synthesis_service, source_tasks, continuation_task, db_service, event_bus_service
    ):
        """Test the complete synthesis flow: register → complete tasks → merge → inject."""
        source_ids = [task.id for task in source_tasks]

        # Register the join
        synthesis_service.register_join(
            join_id="full-flow-join",
            source_task_ids=source_ids,
            continuation_task_id=continuation_task.id,
            merge_strategy="combine",
        )

        # Since tasks are already completed, check_already_completed_sources should trigger
        # Let's manually trigger task completion events
        for task in source_tasks:
            synthesis_service._handle_task_completed({"entity_id": task.id})

        # Verify the join was cleaned up (synthesis completed)
        assert synthesis_service.get_pending_join("full-flow-join") is None

        # Verify context was injected into continuation task
        with db_service.get_session() as session:
            updated_task = session.query(Task).filter(Task.id == continuation_task.id).first()
            assert updated_task.synthesis_context is not None
            assert "_source_results" in updated_task.synthesis_context

    def test_merge_handles_missing_task(self, synthesis_service, source_tasks):
        """Test that merging handles missing tasks gracefully."""
        # Include a non-existent task ID
        source_ids = [source_tasks[0].id, "non-existent-task-id"]

        merged = synthesis_service._merge_task_results(
            source_task_ids=source_ids,
            merge_strategy="combine",
        )

        # Should still have one result
        assert len(merged.get("_source_results", [])) == 1

    def test_merge_handles_incomplete_task(self, synthesis_service, db_service, ticket):
        """Test that merging skips tasks that aren't completed."""
        with db_service.get_session() as session:
            incomplete_task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="incomplete_task",
                description="Still running",
                priority="MEDIUM",
                status="running",  # Not completed
                result={"should_be": "skipped"},
            )
            session.add(incomplete_task)
            session.commit()
            task_id = incomplete_task.id

        merged = synthesis_service._merge_task_results(
            source_task_ids=[task_id],
            merge_strategy="combine",
        )

        # Should be empty since task is not completed
        assert merged.get("_source_results", []) == []


# =============================================================================
# SINGLETON TESTS
# =============================================================================


class TestSynthesisServiceSingleton:
    """Tests for singleton management."""

    def test_get_synthesis_service_requires_args_first_call(self):
        """Test that first call requires db and event_bus."""
        reset_synthesis_service()
        with pytest.raises(ValueError, match="db and event_bus are required"):
            get_synthesis_service()

    def test_get_synthesis_service_returns_same_instance(self):
        """Test that subsequent calls return the same instance."""
        reset_synthesis_service()

        mock_db = MagicMock()
        mock_event_bus = MagicMock()

        service1 = get_synthesis_service(db=mock_db, event_bus=mock_event_bus)
        service2 = get_synthesis_service()  # No args needed

        assert service1 is service2

    def test_reset_synthesis_service(self):
        """Test that reset clears the singleton."""
        reset_synthesis_service()

        mock_db = MagicMock()
        mock_event_bus = MagicMock()

        get_synthesis_service(db=mock_db, event_bus=mock_event_bus)
        reset_synthesis_service()

        # Need to provide args again
        with pytest.raises(ValueError):
            get_synthesis_service()


# =============================================================================
# COORDINATION INTEGRATION TESTS
# =============================================================================


class TestSynthesisCoordinationIntegration:
    """Tests that verify SynthesisService integrates with CoordinationService.

    These tests verify the event-driven flow works correctly when
    CoordinationService.join_tasks() publishes events. Since tests may not
    have Redis available, we use direct method calls to simulate events.
    """

    @pytest.fixture
    def ticket(self, db_service: DatabaseService) -> Ticket:
        """Create a test ticket."""
        with db_service.get_session() as session:
            ticket = Ticket(
                title="Test Coordination Ticket",
                description="Testing coordination-to-synthesis integration",
                phase_id="PHASE_IMPLEMENTATION",
                status="in_progress",
                priority="MEDIUM",
            )
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            session.expunge(ticket)
            return ticket

    @pytest.fixture
    def source_tasks(self, db_service: DatabaseService, ticket: Ticket) -> list[Task]:
        """Create source tasks for coordination."""
        tasks = []
        with db_service.get_session() as session:
            for i in range(2):
                task = Task(
                    ticket_id=ticket.id,
                    phase_id="PHASE_IMPLEMENTATION",
                    task_type=f"parallel_task_{i}",
                    description=f"Parallel task {i}",
                    priority="MEDIUM",
                    status="completed",
                    result={"output": f"result_{i}", "data": {"key": f"value{i}"}},
                )
                session.add(task)
                session.commit()
                session.refresh(task)
                session.expunge(task)
                tasks.append(task)
        return tasks

    @pytest.fixture
    def continuation_task(self, db_service: DatabaseService, ticket: Ticket) -> Task:
        """Create continuation task."""
        with db_service.get_session() as session:
            task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="continuation_task",
                description="Continuation after parallel tasks",
                priority="MEDIUM",
                status="pending",
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            session.expunge(task)
            return task

    @pytest.fixture
    def synthesis_service(
        self, db_service: DatabaseService, event_bus_service: EventBusService
    ) -> SynthesisService:
        """Create SynthesisService with real database."""
        reset_synthesis_service()
        service = SynthesisService(db=db_service, event_bus=event_bus_service)
        service.subscribe_to_events()
        return service

    def test_handle_join_created_event_format(self, synthesis_service, source_tasks, continuation_task, db_service):
        """Test that SynthesisService correctly handles join.created events.

        When source tasks are already completed (as in this test), synthesis triggers
        immediately during join registration. This verifies the complete flow works.
        """
        from omoi_os.services.event_bus import SystemEvent

        source_ids = [str(task.id) for task in source_tasks]

        # Simulate the event that CoordinationService.join_tasks() would publish
        event = SystemEvent(
            event_type="coordination.join.created",
            entity_type="join",
            entity_id="test-join-1",
            payload={
                "join_id": "test-join-1",
                "source_task_ids": source_ids,
                "continuation_task_id": str(continuation_task.id),
                "merge_strategy": "combine",
            },
        )

        # Directly call the handler (simulating what EventBus would do)
        synthesis_service._handle_join_created(event)

        # Since source tasks are already completed, synthesis should have triggered
        # immediately, so the pending join is already cleaned up
        pending = synthesis_service.get_pending_join("test-join-1")
        assert pending is None  # Join completed and cleaned up

        # Verify synthesis_context was injected into continuation task
        with db_service.get_session() as session:
            updated_task = session.query(Task).filter(
                Task.id == continuation_task.id
            ).first()
            assert updated_task.synthesis_context is not None
            assert "_source_results" in updated_task.synthesis_context
            assert updated_task.synthesis_context["_merge_strategy"] == "combine"

    def test_handle_task_completed_event_format(
        self, synthesis_service, source_tasks, continuation_task, db_service
    ):
        """Test that SynthesisService correctly handles TASK_COMPLETED events."""
        from omoi_os.services.event_bus import SystemEvent

        source_ids = [str(task.id) for task in source_tasks]

        # First register a join
        synthesis_service.register_join(
            join_id="event-format-test",
            source_task_ids=source_ids,
            continuation_task_id=str(continuation_task.id),
            merge_strategy="combine",
        )

        # Simulate TASK_COMPLETED events (the format EventBus would send)
        for task in source_tasks:
            event = SystemEvent(
                event_type="TASK_COMPLETED",
                entity_type="task",
                entity_id=str(task.id),
                payload={"result": task.result},
            )
            synthesis_service._handle_task_completed(event)

        # Verify synthesis completed and context was injected
        assert synthesis_service.get_pending_join("event-format-test") is None

        with db_service.get_session() as session:
            updated_task = session.query(Task).filter(
                Task.id == continuation_task.id
            ).first()
            assert updated_task.synthesis_context is not None
            assert "_source_results" in updated_task.synthesis_context
            assert updated_task.synthesis_context["_merge_strategy"] == "combine"
            assert updated_task.synthesis_context["_source_count"] == 2

    def test_full_event_driven_synthesis_flow(
        self,
        synthesis_service,
        source_tasks,
        continuation_task,
        db_service,
    ):
        """Test complete flow: join.created event → immediate synthesis when tasks already complete.

        This test demonstrates the real-world scenario where source tasks may complete
        before the join is registered, and synthesis triggers immediately on registration.
        """
        from omoi_os.services.event_bus import SystemEvent

        source_ids = [str(task.id) for task in source_tasks]

        # Step 1: Simulate coordination.join.created event
        # Since source tasks are already completed, synthesis will trigger immediately
        join_event = SystemEvent(
            event_type="coordination.join.created",
            entity_type="join",
            entity_id="full-flow-test",
            payload={
                "join_id": "full-flow-test",
                "source_task_ids": source_ids,
                "continuation_task_id": str(continuation_task.id),
                "merge_strategy": "union",
            },
        )
        synthesis_service._handle_join_created(join_event)

        # Step 2: Join should be cleaned up (synthesis already completed)
        assert synthesis_service.get_pending_join("full-flow-test") is None

        # Step 3: Verify synthesis_context was injected into continuation task
        with db_service.get_session() as session:
            updated_task = session.query(Task).filter(
                Task.id == continuation_task.id
            ).first()
            assert updated_task.synthesis_context is not None
            assert "_source_results" in updated_task.synthesis_context
            assert updated_task.synthesis_context["_merge_strategy"] == "union"
            assert "_join_id" in updated_task.synthesis_context
            assert updated_task.synthesis_context["_join_id"] == "full-flow-test"

    def test_synthesis_flow_with_pending_tasks(
        self,
        db_service,
        event_bus_service,
    ):
        """Test synthesis when tasks complete AFTER join is registered.

        This tests the normal flow where:
        1. Join is registered with pending source tasks
        2. Tasks complete one by one
        3. Synthesis triggers when all complete
        """
        from omoi_os.services.event_bus import SystemEvent

        reset_synthesis_service()

        # Create a ticket
        with db_service.get_session() as session:
            ticket = Ticket(
                title="Pending Tasks Test",
                description="Testing synthesis with pending tasks",
                phase_id="PHASE_IMPLEMENTATION",
                status="in_progress",
                priority="MEDIUM",
            )
            session.add(ticket)
            session.commit()
            ticket_id = ticket.id

        # Create source tasks in PENDING state (not completed)
        source_task_ids = []
        with db_service.get_session() as session:
            for i in range(2):
                task = Task(
                    ticket_id=ticket_id,
                    phase_id="PHASE_IMPLEMENTATION",
                    task_type=f"pending_task_{i}",
                    description=f"Pending task {i}",
                    priority="MEDIUM",
                    status="pending",  # Not completed yet!
                )
                session.add(task)
                session.commit()
                source_task_ids.append(str(task.id))

        # Create continuation task
        with db_service.get_session() as session:
            continuation_task = Task(
                ticket_id=ticket_id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="continuation_pending",
                description="Continuation for pending test",
                priority="MEDIUM",
                status="pending",
            )
            session.add(continuation_task)
            session.commit()
            continuation_task_id = str(continuation_task.id)

        # Create synthesis service
        synthesis_service = SynthesisService(db=db_service, event_bus=event_bus_service)

        # Step 1: Register join - tasks are pending, so join stays pending
        join_event = SystemEvent(
            event_type="coordination.join.created",
            entity_type="join",
            entity_id="pending-test-join",
            payload={
                "join_id": "pending-test-join",
                "source_task_ids": source_task_ids,
                "continuation_task_id": continuation_task_id,
                "merge_strategy": "combine",
            },
        )
        synthesis_service._handle_join_created(join_event)

        # Join should still be pending (tasks not complete)
        pending = synthesis_service.get_pending_join("pending-test-join")
        assert pending is not None
        assert len(pending.completed_source_ids) == 0

        # Step 2: Complete first task
        with db_service.get_session() as session:
            task = session.query(Task).filter(Task.id == source_task_ids[0]).first()
            task.status = "completed"
            task.result = {"output": "first_result"}
            session.commit()

        complete_event1 = SystemEvent(
            event_type="TASK_COMPLETED",
            entity_type="task",
            entity_id=source_task_ids[0],
            payload={"status": "completed"},
        )
        synthesis_service._handle_task_completed(complete_event1)

        # Join still pending (one task remaining)
        pending = synthesis_service.get_pending_join("pending-test-join")
        assert pending is not None
        assert len(pending.completed_source_ids) == 1

        # Step 3: Complete second task
        with db_service.get_session() as session:
            task = session.query(Task).filter(Task.id == source_task_ids[1]).first()
            task.status = "completed"
            task.result = {"output": "second_result"}
            session.commit()

        complete_event2 = SystemEvent(
            event_type="TASK_COMPLETED",
            entity_type="task",
            entity_id=source_task_ids[1],
            payload={"status": "completed"},
        )
        synthesis_service._handle_task_completed(complete_event2)

        # Step 4: Join should be completed and cleaned up
        assert synthesis_service.get_pending_join("pending-test-join") is None

        # Step 5: Verify synthesis_context was injected
        with db_service.get_session() as session:
            updated_task = session.query(Task).filter(
                Task.id == continuation_task_id
            ).first()
            assert updated_task.synthesis_context is not None
            assert "_source_results" in updated_task.synthesis_context
            assert updated_task.synthesis_context["_source_count"] == 2
