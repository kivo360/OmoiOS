"""Tests for coordination patterns service."""

import pytest

from omoi_os.services.coordination import (
    CoordinationPattern,
    CoordinationService,
)
from tests.test_helpers import create_test_ticket


@pytest.fixture
def coordination_service(db_service, task_queue_service, event_bus_service):
    """Create coordination service instance."""
    return CoordinationService(db_service, task_queue_service, event_bus_service)


@pytest.fixture
def test_ticket(db_service):
    """Create a test ticket for coordination tests."""
    return create_test_ticket(db_service, ticket_id="test_ticket")


class TestSyncPoint:
    """Tests for synchronization point operations."""

    def test_create_sync_point(self, coordination_service):
        """Test creating a sync point."""
        sync_point = coordination_service.create_sync_point(
            sync_id="test_sync_1",
            waiting_task_ids=["task_1", "task_2", "task_3"],
            required_count=2,
            timeout_seconds=3600,
        )

        assert sync_point.sync_id == "test_sync_1"
        assert sync_point.waiting_task_ids == ["task_1", "task_2", "task_3"]
        assert sync_point.required_count == 2
        assert sync_point.timeout_seconds == 3600

    def test_create_sync_point_defaults(self, coordination_service):
        """Test creating sync point with default values."""
        sync_point = coordination_service.create_sync_point(
            sync_id="test_sync_2",
            waiting_task_ids=["task_1", "task_2"],
        )

        assert sync_point.required_count == 2  # Should default to len(waiting_task_ids)
        assert sync_point.timeout_seconds is None

    def test_check_sync_point_ready(self, coordination_service, db_service, test_ticket):
        """Test checking if sync point is ready."""
        # Create tasks
        task1 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test_task",
            description="Test task 1",
            priority="HIGH",
        )
        task2 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test_task",
            description="Test task 2",
            priority="HIGH",
        )

        # Create sync point
        sync_point = coordination_service.create_sync_point(
            sync_id="test_sync",
            waiting_task_ids=[task1.id, task2.id],
            required_count=2,
        )

        # Initially not ready
        assert not coordination_service.check_sync_point_ready("test_sync", sync_point)

        # Complete one task
        coordination_service.queue.update_task_status(task1.id, "completed")

        # Still not ready (need 2)
        assert not coordination_service.check_sync_point_ready("test_sync", sync_point)

        # Complete second task
        coordination_service.queue.update_task_status(task2.id, "completed")

        # Now ready
        assert coordination_service.check_sync_point_ready("test_sync", sync_point)

    def test_check_sync_point_partial(self, coordination_service, test_ticket):
        """Test sync point with partial completion requirement."""
        task1 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test_task",
            description="Test task 1",
            priority="HIGH",
        )
        task2 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test_task",
            description="Test task 2",
            priority="HIGH",
        )
        task3 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test_task",
            description="Test task 3",
            priority="HIGH",
        )

        sync_point = coordination_service.create_sync_point(
            sync_id="test_sync_partial",
            waiting_task_ids=[task1.id, task2.id, task3.id],
            required_count=2,  # Only need 2 of 3
        )

        # Complete 2 tasks
        coordination_service.queue.update_task_status(task1.id, "completed")
        coordination_service.queue.update_task_status(task2.id, "completed")

        # Should be ready even though task3 is not complete
        assert coordination_service.check_sync_point_ready(
            "test_sync_partial", sync_point
        )


class TestSplitOperations:
    """Tests for split operations."""

    def test_split_task(self, coordination_service, test_ticket):
        """Test splitting a task into multiple parallel tasks."""
        source_task = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Implement feature",
            priority="HIGH",
        )

        target_tasks = [
            {
                "phase_id": "PHASE_IMPLEMENTATION",
                "task_type": "implement_module_a",
                "description": "Implement module A",
                "priority": "HIGH",
            },
            {
                "phase_id": "PHASE_IMPLEMENTATION",
                "task_type": "implement_module_b",
                "description": "Implement module B",
                "priority": "HIGH",
            },
        ]

        created_tasks = coordination_service.split_task(
            split_id="test_split",
            source_task_id=source_task.id,
            target_tasks=target_tasks,
        )

        assert len(created_tasks) == 2
        assert all(
            task.dependencies.get("depends_on") == [source_task.id]
            for task in created_tasks
        )
        assert created_tasks[0].task_type == "implement_module_a"
        assert created_tasks[1].task_type == "implement_module_b"

    def test_split_task_invalid_source(self, coordination_service):
        """Test splitting with invalid source task."""
        with pytest.raises(ValueError, match="Source task.*not found"):
            coordination_service.split_task(
                split_id="test_split",
                source_task_id="invalid_task_id",
                target_tasks=[],
            )


class TestJoinOperations:
    """Tests for join operations."""

    def test_join_tasks(self, coordination_service, test_ticket):
        """Test joining multiple tasks."""
        # Create source tasks
        task1 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_module_a",
            description="Implement module A",
            priority="HIGH",
        )
        task2 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_module_b",
            description="Implement module B",
            priority="HIGH",
        )

        continuation_task = {
            "phase_id": "PHASE_INTEGRATION",
            "task_type": "integrate_modules",
            "description": "Integrate modules",
            "priority": "HIGH",
        }

        continuation = coordination_service.join_tasks(
            join_id="test_join",
            source_task_ids=[task1.id, task2.id],
            continuation_task=continuation_task,
        )

        assert continuation.task_type == "integrate_modules"
        assert continuation.phase_id == "PHASE_INTEGRATION"
        assert continuation.dependencies.get("depends_on") == [task1.id, task2.id]

    def test_join_tasks_invalid_source(self, coordination_service):
        """Test joining with invalid source tasks."""
        with pytest.raises(ValueError, match="Some source tasks not found"):
            coordination_service.join_tasks(
                join_id="test_join",
                source_task_ids=["invalid_task_1", "invalid_task_2"],
                continuation_task={},
            )


class TestMergeOperations:
    """Tests for merge operations."""

    def test_merge_task_results_combine(self, coordination_service, test_ticket):
        """Test merging task results with combine strategy."""
        # Create and complete tasks with results
        task1 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test_task",
            description="Test task 1",
            priority="HIGH",
        )
        task2 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test_task",
            description="Test task 2",
            priority="HIGH",
        )

        coordination_service.queue.update_task_status(
            task1.id, "completed", result={"key1": "value1", "key2": "value2"}
        )
        coordination_service.queue.update_task_status(
            task2.id, "completed", result={"key3": "value3", "key4": "value4"}
        )

        merged = coordination_service.merge_task_results(
            merge_id="test_merge",
            source_task_ids=[task1.id, task2.id],
            merge_strategy="combine",
        )

        assert merged == {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
            "key4": "value4",
        }

    def test_merge_task_results_intersection(self, coordination_service, test_ticket):
        """Test merging with intersection strategy."""
        task1 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test_task",
            description="Test task 1",
            priority="HIGH",
        )
        task2 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test_task",
            description="Test task 2",
            priority="HIGH",
        )

        coordination_service.queue.update_task_status(
            task1.id, "completed", result={"common": "value1", "unique1": "value1"}
        )
        coordination_service.queue.update_task_status(
            task2.id, "completed", result={"common": "value2", "unique2": "value2"}
        )

        merged = coordination_service.merge_task_results(
            merge_id="test_merge",
            source_task_ids=[task1.id, task2.id],
            merge_strategy="intersection",
        )

        # Should only include common keys
        assert "common" in merged
        assert "unique1" not in merged
        assert "unique2" not in merged

    def test_merge_task_results_incomplete(self, coordination_service, test_ticket):
        """Test merging with incomplete tasks."""
        task1 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test_task",
            description="Test task 1",
            priority="HIGH",
        )
        task2 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test_task",
            description="Test task 2",
            priority="HIGH",
        )

        # Only complete one task
        coordination_service.queue.update_task_status(
            task1.id, "completed", result={"key": "value"}
        )

        with pytest.raises(ValueError, match="is not completed"):
            coordination_service.merge_task_results(
                merge_id="test_merge",
                source_task_ids=[task1.id, task2.id],
            )


class TestPatternExecution:
    """Tests for pattern execution."""

    def test_execute_sync_pattern(self, coordination_service):
        """Test executing a sync pattern."""
        pattern_config = {
            "type": CoordinationPattern.SYNC,
            "id": "test_sync_pattern",
            "waiting_task_ids": ["task_1", "task_2"],
            "required_count": 2,
        }

        result = coordination_service.execute_pattern(pattern_config)

        assert "sync_point" in result
        assert result["sync_id"] == "test_sync_pattern"

    def test_execute_split_pattern(self, coordination_service, test_ticket):
        """Test executing a split pattern."""
        source_task = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Implement feature",
            priority="HIGH",
        )

        pattern_config = {
            "type": CoordinationPattern.SPLIT,
            "id": "test_split_pattern",
            "source_task_id": source_task.id,
            "target_tasks": [
                {
                    "phase_id": "PHASE_IMPLEMENTATION",
                    "task_type": "implement_module_a",
                    "description": "Implement module A",
                    "priority": "HIGH",
                }
            ],
        }

        result = coordination_service.execute_pattern(pattern_config)

        assert "tasks" in result
        assert len(result["tasks"]) == 1

    def test_execute_join_pattern(self, coordination_service, test_ticket):
        """Test executing a join pattern."""
        task1 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_module_a",
            description="Implement module A",
            priority="HIGH",
        )
        task2 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_module_b",
            description="Implement module B",
            priority="HIGH",
        )

        pattern_config = {
            "type": CoordinationPattern.JOIN,
            "id": "test_join_pattern",
            "source_task_ids": [task1.id, task2.id],
            "continuation_task": {
                "phase_id": "PHASE_INTEGRATION",
                "task_type": "integrate_modules",
                "description": "Integrate modules",
                "priority": "HIGH",
            },
        }

        result = coordination_service.execute_pattern(pattern_config)

        assert "continuation_task" in result
        assert result["task_id"] is not None

    def test_execute_merge_pattern(self, coordination_service, test_ticket):
        """Test executing a merge pattern."""
        task1 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test_task",
            description="Test task 1",
            priority="HIGH",
        )
        task2 = coordination_service.queue.enqueue_task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test_task",
            description="Test task 2",
            priority="HIGH",
        )

        coordination_service.queue.update_task_status(
            task1.id, "completed", result={"key1": "value1"}
        )
        coordination_service.queue.update_task_status(
            task2.id, "completed", result={"key2": "value2"}
        )

        pattern_config = {
            "type": CoordinationPattern.MERGE,
            "id": "test_merge_pattern",
            "source_task_ids": [task1.id, task2.id],
            "merge_strategy": "combine",
        }

        result = coordination_service.execute_pattern(pattern_config)

        assert "merged_result" in result
        assert result["merged_result"]["key1"] == "value1"
        assert result["merged_result"]["key2"] == "value2"

    def test_execute_unknown_pattern(self, coordination_service):
        """Test executing an unknown pattern type."""
        pattern_config = {
            "type": "unknown_pattern",
            "id": "test_pattern",
        }

        with pytest.raises(ValueError, match="Unknown pattern type"):
            coordination_service.execute_pattern(pattern_config)

