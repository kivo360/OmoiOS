"""End-to-end tests for parallel multi-agent coordination patterns."""

import pytest

from omoi_os.services.coordination import CoordinationService
from tests.test_helpers import create_test_ticket


@pytest.fixture
def coordination_service(db_service, task_queue_service, event_bus_service):
    """Create coordination service instance."""
    return CoordinationService(db_service, task_queue_service, event_bus_service)


class TestE2EParallelWorkflow:
    """End-to-end tests for parallel workflow scenarios."""

    def test_parallel_implementation_workflow(self, coordination_service, db_service):
        """Test complete parallel implementation workflow."""
        # Create test ticket
        ticket = create_test_ticket(db_service, ticket_id="test_ticket_parallel")
        
        # Create initial ticket task
        source_task = coordination_service.queue.enqueue_task(
            ticket_id=ticket.id,
            phase_id="PHASE_INITIAL",
            task_type="design_feature",
            description="Design feature architecture",
            priority="HIGH",
        )

        # Split into parallel implementation tasks
        parallel_tasks = coordination_service.split_task(
            split_id="parallel_impl_split",
            source_task_id=source_task.id,
            target_tasks=[
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
                {
                    "phase_id": "PHASE_IMPLEMENTATION",
                    "task_type": "implement_module_c",
                    "description": "Implement module C",
                    "priority": "HIGH",
                },
            ],
        )

        assert len(parallel_tasks) == 3

        # Create sync point
        sync_point = coordination_service.create_sync_point(
            sync_id="implementation_sync",
            waiting_task_ids=[t.id for t in parallel_tasks],
            required_count=3,
        )

        # Initially not ready
        assert not coordination_service.check_sync_point_ready(
            "implementation_sync", sync_point
        )

        # Complete all parallel tasks
        for i, task in enumerate(parallel_tasks):
            coordination_service.queue.update_task_status(
                task.id, "completed", result={f"module_{i}": task.task_type}
            )

        # Sync point should be ready
        assert coordination_service.check_sync_point_ready(
            "implementation_sync", sync_point
        )

        # Join tasks for integration
        continuation = coordination_service.join_tasks(
            join_id="integration_join",
            source_task_ids=[t.id for t in parallel_tasks],
            continuation_task={
                "phase_id": "PHASE_INTEGRATION",
                "task_type": "integrate_modules",
                "description": "Integrate all modules",
                "priority": "HIGH",
            },
        )

        assert continuation.task_type == "integrate_modules"
        assert continuation.phase_id == "PHASE_INTEGRATION"
        assert len(continuation.dependencies.get("depends_on", [])) == 3

        # Merge results
        merged = coordination_service.merge_task_results(
            merge_id="result_merge",
            source_task_ids=[t.id for t in parallel_tasks],
            merge_strategy="combine",
        )

        assert len(merged) == 3
        assert all(k.startswith("module_") for k in merged.keys())

    def test_review_feedback_loop_workflow(self, coordination_service, db_service):
        """Test review-feedback loop workflow."""
        # Create test ticket
        ticket = create_test_ticket(db_service, ticket_id="test_ticket_review")
        
        # Create initial implementation task
        impl_task = coordination_service.queue.enqueue_task(
            ticket_id=ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Implement feature",
            priority="HIGH",
        )

        # Split into parallel implementation tasks
        impl_tasks = coordination_service.split_task(
            split_id="impl_split",
            source_task_id=impl_task.id,
            target_tasks=[
                {
                    "phase_id": "PHASE_IMPLEMENTATION",
                    "task_type": "implement_component_a",
                    "description": "Implement component A",
                    "priority": "HIGH",
                },
                {
                    "phase_id": "PHASE_IMPLEMENTATION",
                    "task_type": "implement_component_b",
                    "description": "Implement component B",
                    "priority": "HIGH",
                },
            ],
        )

        # Create review tasks (depend on implementation tasks)
        review_tasks = []
        for impl_task_item in impl_tasks:
            review_task = coordination_service.queue.enqueue_task(
                ticket_id="test_ticket_review",
                phase_id="PHASE_INTEGRATION",
                task_type="review_implementation",
                description=f"Review {impl_task_item.task_type}",
                priority="HIGH",
                dependencies={"depends_on": [impl_task_item.id]},
            )
            review_tasks.append(review_task)

        # Sync point for reviews
        review_sync = coordination_service.create_sync_point(
            sync_id="review_sync",
            waiting_task_ids=[t.id for t in review_tasks],
            required_count=2,
        )

        # Complete reviews
        for review_task in review_tasks:
            coordination_service.queue.update_task_status(
                review_task.id,
                "completed",
                result={"review_status": "approved", "feedback": "Looks good"},
            )

        assert coordination_service.check_sync_point_ready("review_sync", review_sync)

        # Merge review feedback
        feedback = coordination_service.merge_task_results(
            merge_id="feedback_merge",
            source_task_ids=[t.id for t in review_tasks],
            merge_strategy="combine",
        )

        assert "review_status" in str(feedback)

    def test_majority_vote_workflow(self, coordination_service, db_service):
        """Test majority vote decision workflow."""
        # Create test ticket
        ticket = create_test_ticket(db_service, ticket_id="test_ticket_vote")
        
        # Create decision task
        decision_task = coordination_service.queue.enqueue_task(
            ticket_id=ticket.id,
            phase_id="PHASE_INITIAL",
            task_type="make_decision",
            description="Make architectural decision",
            priority="HIGH",
        )

        # Split into parallel evaluation tasks
        eval_tasks = coordination_service.split_task(
            split_id="vote_split",
            source_task_id=decision_task.id,
            target_tasks=[
                {
                    "phase_id": "PHASE_INITIAL",
                    "task_type": "evaluate_option_a",
                    "description": "Evaluate option A",
                    "priority": "MEDIUM",
                },
                {
                    "phase_id": "PHASE_INITIAL",
                    "task_type": "evaluate_option_b",
                    "description": "Evaluate option B",
                    "priority": "MEDIUM",
                },
                {
                    "phase_id": "PHASE_INITIAL",
                    "task_type": "evaluate_option_c",
                    "description": "Evaluate option C",
                    "priority": "MEDIUM",
                },
            ],
        )

        # Sync point with majority requirement (2 of 3)
        vote_sync = coordination_service.create_sync_point(
            sync_id="vote_sync",
            waiting_task_ids=[t.id for t in eval_tasks],
            required_count=2,  # Majority
        )

        # Complete 2 evaluations (majority)
        coordination_service.queue.update_task_status(
            eval_tasks[0].id, "completed", result={"vote": "option_a", "score": 8}
        )
        coordination_service.queue.update_task_status(
            eval_tasks[1].id, "completed", result={"vote": "option_a", "score": 7}
        )

        # Sync point should be ready with majority
        assert coordination_service.check_sync_point_ready("vote_sync", vote_sync)

        # Merge votes
        votes = coordination_service.merge_task_results(
            merge_id="vote_merge",
            source_task_ids=[eval_tasks[0].id, eval_tasks[1].id],
            merge_strategy="combine",
        )

        assert "vote" in str(votes)

        # Create continuation task based on majority decision
        continuation = coordination_service.join_tasks(
            join_id="decision_join",
            source_task_ids=[eval_tasks[0].id, eval_tasks[1].id],
            continuation_task={
                "phase_id": "PHASE_INITIAL",
                "task_type": "implement_decision",
                "description": "Implement majority decision",
                "priority": "HIGH",
            },
            merge_strategy="majority",
        )

        assert continuation.task_type == "implement_decision"

    def test_deadlock_avoidance(self, coordination_service, db_service):
        """Test that coordination patterns avoid deadlocks."""
        # Create test ticket
        ticket = create_test_ticket(db_service, ticket_id="test_ticket_deadlock")
        
        # Create tasks that would form a cycle without proper dependency management
        task1 = coordination_service.queue.enqueue_task(
            ticket_id=ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="task_1",
            description="Task 1",
            priority="HIGH",
        )
        task2 = coordination_service.queue.enqueue_task(
            ticket_id=ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="task_2",
            description="Task 2",
            priority="HIGH",
            dependencies={"depends_on": [task1.id]},
        )

        # Try to create a join that depends on both
        # This should work without creating a cycle
        continuation = coordination_service.join_tasks(
            join_id="deadlock_test_join",
            source_task_ids=[task1.id, task2.id],
            continuation_task={
                "phase_id": "PHASE_INTEGRATION",
                "task_type": "continuation",
                "description": "Continuation task",
                "priority": "HIGH",
            },
        )

        # Verify continuation depends on both tasks
        assert task1.id in continuation.dependencies.get("depends_on", [])
        assert task2.id in continuation.dependencies.get("depends_on", [])

        # Verify no circular dependency
        # task1 -> task2 -> continuation (valid DAG)
        assert coordination_service.queue.detect_circular_dependencies(
            continuation.id, continuation.dependencies.get("depends_on", [])
        ) is None

