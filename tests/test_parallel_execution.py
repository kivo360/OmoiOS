"""Tests for parallel task execution and DAG batching."""


class TestDAGBatching:
    """Tests for DAG-based parallel task batching."""

    def test_get_ready_tasks_empty(self, task_queue_service):
        """Test getting ready tasks when none exist."""
        tasks = task_queue_service.get_ready_tasks("PHASE_IMPLEMENTATION")
        assert tasks == []

    def test_get_ready_tasks_single(self, task_queue_service, sample_ticket):
        """Test getting a single ready task."""
        task = task_queue_service.enqueue_task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Feature A",
            priority="HIGH",
        )

        ready_tasks = task_queue_service.get_ready_tasks("PHASE_IMPLEMENTATION")
        assert len(ready_tasks) == 1
        assert ready_tasks[0].id == task.id

    def test_get_ready_tasks_multiple(self, task_queue_service, sample_ticket):
        """Test getting multiple ready tasks for parallel execution."""
        # Create 5 independent tasks
        tasks = []
        for i in range(5):
            task = task_queue_service.enqueue_task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type=f"task_{i}",
                description=f"Task {i}",
                priority="MEDIUM",
            )
            tasks.append(task)

        ready_tasks = task_queue_service.get_ready_tasks(
            "PHASE_IMPLEMENTATION", limit=3
        )
        assert len(ready_tasks) == 3
        assert all(t.status == "pending" for t in ready_tasks)

    def test_get_ready_tasks_respects_dependencies(
        self, task_queue_service, sample_ticket
    ):
        """Test that get_ready_tasks only returns tasks with satisfied dependencies."""
        # Create task chain: A -> B -> C
        task_a = task_queue_service.enqueue_task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="task_a",
            description="Task A",
            priority="HIGH",
        )
        task_b = task_queue_service.enqueue_task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="task_b",
            description="Task B",
            priority="HIGH",
            dependencies={"depends_on": [task_a.id]},
        )
        task_queue_service.enqueue_task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="task_c",
            description="Task C",
            priority="HIGH",
            dependencies={"depends_on": [task_b.id]},
        )

        # Only A should be ready
        ready_tasks = task_queue_service.get_ready_tasks("PHASE_IMPLEMENTATION")
        assert len(ready_tasks) == 1
        assert ready_tasks[0].id == task_a.id

        # Complete A
        task_queue_service.update_task_status(task_a.id, "completed")

        # Now only B should be ready
        ready_tasks = task_queue_service.get_ready_tasks("PHASE_IMPLEMENTATION")
        assert len(ready_tasks) == 1
        assert ready_tasks[0].id == task_b.id

    def test_get_ready_tasks_parallel_branches(self, task_queue_service, sample_ticket):
        """Test that parallel branches are batched correctly."""
        # Create diamond dependency: A -> B,C,D -> E
        task_a = task_queue_service.enqueue_task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="task_a",
            description="Root task",
            priority="HIGH",
        )

        task_b = task_queue_service.enqueue_task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="task_b",
            description="Branch B",
            priority="HIGH",
            dependencies={"depends_on": [task_a.id]},
        )
        task_c = task_queue_service.enqueue_task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="task_c",
            description="Branch C",
            priority="HIGH",
            dependencies={"depends_on": [task_a.id]},
        )
        task_d = task_queue_service.enqueue_task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="task_d",
            description="Branch D",
            priority="HIGH",
            dependencies={"depends_on": [task_a.id]},
        )

        # Only A is ready initially
        ready_tasks = task_queue_service.get_ready_tasks("PHASE_IMPLEMENTATION")
        assert len(ready_tasks) == 1

        # Complete A
        task_queue_service.update_task_status(task_a.id, "completed")

        # Now B, C, D should all be ready (parallel branches)
        ready_tasks = task_queue_service.get_ready_tasks("PHASE_IMPLEMENTATION")
        assert len(ready_tasks) == 3
        task_ids = {t.id for t in ready_tasks}
        assert task_ids == {task_b.id, task_c.id, task_d.id}

    def test_get_ready_tasks_priority_order(self, task_queue_service, sample_ticket):
        """Test that ready tasks are returned in priority order."""
        # Create tasks with different priorities
        task_low = task_queue_service.enqueue_task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="low_priority",
            description="Low priority task",
            priority="LOW",
        )
        task_critical = task_queue_service.enqueue_task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="critical",
            description="Critical task",
            priority="CRITICAL",
        )
        task_medium = task_queue_service.enqueue_task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="medium",
            description="Medium task",
            priority="MEDIUM",
        )

        ready_tasks = task_queue_service.get_ready_tasks(
            "PHASE_IMPLEMENTATION", limit=10
        )
        assert len(ready_tasks) == 3
        # Should be in priority order: CRITICAL, MEDIUM, LOW
        assert ready_tasks[0].id == task_critical.id
        assert ready_tasks[1].id == task_medium.id
        assert ready_tasks[2].id == task_low.id
