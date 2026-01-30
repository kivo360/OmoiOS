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
