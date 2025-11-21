#!/usr/bin/env python3
"""Simulation script for multi-agent parallel workflow coordination.

This script demonstrates coordination patterns in action by simulating
a multi-agent workflow with parallel execution, synchronization points,
and result merging.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from omoi_os.config import get_app_settings
from omoi_os.models.ticket import Ticket
from omoi_os.services.coordination import CoordinationService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.task_queue import TaskQueueService


def simulate_parallel_implementation():
    """Simulate a parallel implementation workflow."""
    print("=" * 80)
    print("Simulating Parallel Implementation Workflow")
    print("=" * 80)

    # Initialize services
    app_settings = get_app_settings()
    db_url = app_settings.database.url
    redis_url = app_settings.redis.url

    db = DatabaseService(connection_string=db_url)
    queue = TaskQueueService(db)
    event_bus = EventBusService(redis_url=redis_url)
    coordination = CoordinationService(db, queue, event_bus)

    # Create ticket
    with db.get_session() as session:
        ticket = Ticket(
            title="Parallel Feature Implementation",
            description="Implement feature with parallel modules",
            phase_id="PHASE_INITIAL",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        ticket_id = str(ticket.id)

    print(f"\n✓ Created ticket: {ticket_id}")

    # Create initial design task
    design_task = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_INITIAL",
        task_type="design_architecture",
        description="Design feature architecture",
        priority="HIGH",
    )
    print(f"✓ Created design task: {design_task.id}")

    # Simulate design completion
    queue.update_task_status(design_task.id, "completed", result={"design": "complete"})
    print(f"✓ Design task completed")

    # Split into parallel implementation tasks
    print("\n--- Splitting into parallel implementation tasks ---")
    parallel_tasks = coordination.split_task(
        split_id="parallel_impl_split",
        source_task_id=design_task.id,
        target_tasks=[
            {
                "phase_id": "PHASE_IMPLEMENTATION",
                "task_type": "implement_module_a",
                "description": "Implement module A (frontend)",
                "priority": "HIGH",
            },
            {
                "phase_id": "PHASE_IMPLEMENTATION",
                "task_type": "implement_module_b",
                "description": "Implement module B (backend)",
                "priority": "HIGH",
            },
            {
                "phase_id": "PHASE_IMPLEMENTATION",
                "task_type": "implement_module_c",
                "description": "Implement module C (database)",
                "priority": "HIGH",
            },
        ],
    )

    print(f"✓ Created {len(parallel_tasks)} parallel tasks:")
    for i, task in enumerate(parallel_tasks, 1):
        print(f"  {i}. {task.task_type}: {task.id}")

    # Create sync point
    print("\n--- Creating synchronization point ---")
    sync_point = coordination.create_sync_point(
        sync_id="implementation_sync",
        waiting_task_ids=[t.id for t in parallel_tasks],
        required_count=3,
    )
    print(f"✓ Created sync point: {sync_point.sync_id}")
    print(f"  Waiting for {sync_point.required_count} tasks to complete")

    # Simulate parallel execution (tasks complete in different order)
    print("\n--- Simulating parallel execution ---")
    completion_order = [parallel_tasks[1], parallel_tasks[0], parallel_tasks[2]]
    for i, task in enumerate(completion_order, 1):
        queue.update_task_status(
            task.id,
            "completed",
            result={"module": task.task_type, "status": "done"},
        )
        print(f"✓ Task {i} completed: {task.task_type}")

        # Check sync point status
        is_ready = coordination.check_sync_point_ready(
            "implementation_sync", sync_point
        )
        print(f"  Sync point ready: {is_ready} ({i}/{sync_point.required_count})")

    # Join tasks for integration
    print("\n--- Joining tasks for integration ---")
    continuation = coordination.join_tasks(
        join_id="integration_join",
        source_task_ids=[t.id for t in parallel_tasks],
        continuation_task={
            "phase_id": "PHASE_INTEGRATION",
            "task_type": "integrate_modules",
            "description": "Integrate all modules together",
            "priority": "HIGH",
        },
    )
    print(f"✓ Created continuation task: {continuation.id}")
    print(f"  Task type: {continuation.task_type}")
    print(f"  Depends on: {len(continuation.dependencies.get('depends_on', []))} tasks")

    # Merge results
    print("\n--- Merging task results ---")
    merged = coordination.merge_task_results(
        merge_id="result_merge",
        source_task_ids=[t.id for t in parallel_tasks],
        merge_strategy="combine",
    )
    print(f"✓ Merged results from {len(parallel_tasks)} tasks")
    print(f"  Result keys: {list(merged.keys())}")

    print("\n" + "=" * 80)
    print("Simulation completed successfully!")
    print("=" * 80)


def simulate_review_feedback_loop():
    """Simulate a review-feedback loop workflow."""
    print("\n" + "=" * 80)
    print("Simulating Review-Feedback Loop Workflow")
    print("=" * 80)

    # Initialize services
    app_settings = get_app_settings()
    db_url = app_settings.database.url
    redis_url = app_settings.redis.url

    db = DatabaseService(connection_string=db_url)
    queue = TaskQueueService(db)
    event_bus = EventBusService(redis_url=redis_url)
    coordination = CoordinationService(db, queue, event_bus)

    # Create ticket
    with db.get_session() as session:
        ticket = Ticket(
            title="Feature with Review Process",
            description="Implement feature with review and feedback",
            phase_id="PHASE_INITIAL",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        ticket_id = str(ticket.id)

    print(f"\n✓ Created ticket: {ticket_id}")

    # Create implementation task
    impl_task = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="implement_feature",
        description="Implement feature",
        priority="HIGH",
    )
    print(f"✓ Created implementation task: {impl_task.id}")

    # Split into parallel implementation components
    print("\n--- Splitting into parallel components ---")
    impl_tasks = coordination.split_task(
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
    print(f"✓ Created {len(impl_tasks)} implementation components")

    # Simulate implementation completion
    for task in impl_tasks:
        queue.update_task_status(
            task.id, "completed", result={"implementation": "complete"}
        )
    print("✓ All implementation components completed")

    # Create review tasks
    print("\n--- Creating review tasks ---")
    review_tasks = []
    for impl_task_item in impl_tasks:
        review_task = queue.enqueue_task(
            ticket_id=ticket_id,
            phase_id="PHASE_INTEGRATION",
            task_type="review_implementation",
            description=f"Review {impl_task_item.task_type}",
            priority="HIGH",
            dependencies={"depends_on": [impl_task_item.id]},
        )
        review_tasks.append(review_task)
    print(f"✓ Created {len(review_tasks)} review tasks")

    # Simulate reviews
    print("\n--- Simulating reviews ---")
    for review_task in review_tasks:
        queue.update_task_status(
            review_task.id,
            "completed",
            result={"review_status": "approved", "feedback": "Looks good"},
        )
    print("✓ All reviews completed")

    # Merge feedback
    print("\n--- Merging review feedback ---")
    feedback = coordination.merge_task_results(
        merge_id="feedback_merge",
        source_task_ids=[t.id for t in review_tasks],
        merge_strategy="combine",
    )
    print(f"✓ Merged feedback from {len(review_tasks)} reviews")

    print("\n" + "=" * 80)
    print("Review-Feedback Loop simulation completed!")
    print("=" * 80)


if __name__ == "__main__":
    print("Multi-Agent Parallel Workflow Simulation")
    print("=" * 80)

    try:
        simulate_parallel_implementation()
        simulate_review_feedback_loop()
    except Exception as e:
        print(f"\n❌ Simulation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

