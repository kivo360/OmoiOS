#!/usr/bin/env python3
"""
Create test data for dependency graph visualization.

This script creates:
- Multiple tickets
- Tasks with dependencies
- Task discoveries that spawn new tasks
- Parent-child task relationships

Run with: uv run python scripts/create_test_dependency_graph.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.event_bus import EventBusService
from omoi_os.models.ticket import Ticket
from omoi_os.models.task_discovery import TaskDiscovery
from omoi_os.utils.datetime import utc_now


def create_test_dependency_graph():
    """Create test tickets and tasks with dependencies."""

    # Initialize services with connection strings from environment
    database_url = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:15432/app_db"
    )
    redis_url = os.getenv("REDIS_URL", "redis://localhost:16379")

    db = DatabaseService(connection_string=database_url)
    event_bus = EventBusService(redis_url=redis_url)
    queue = TaskQueueService(db)

    print("Creating test dependency graph data...")

    with db.get_session() as session:
        # Create Ticket 1: Authentication System
        ticket1 = Ticket(
            title="Implement Authentication System",
            description="Build a complete authentication system with OAuth2 support",
            phase_id="PHASE_IMPLEMENTATION",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket1)
        session.flush()
        print(f"✓ Created ticket: {ticket1.title} (ID: {ticket1.id[:8]}...)")

        # Create tasks for Ticket 1 with dependencies
        # Use session parameter to ensure all tasks are in the same transaction
        task1_1 = queue.enqueue_task(
            ticket_id=ticket1.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="design_architecture",
            description="Design authentication architecture",
            priority="HIGH",
            session=session,
        )
        print(f"  ✓ Created task: {task1_1.description} (ID: {task1_1.id[:8]}...)")

        task1_2 = queue.enqueue_task(
            ticket_id=ticket1.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_jwt",
            description="Implement JWT token generation",
            priority="HIGH",
            dependencies={"depends_on": [task1_1.id]},  # Depends on design
            session=session,
        )
        print(f"  ✓ Created task: {task1_2.description} (depends on task1_1)")

        task1_3 = queue.enqueue_task(
            ticket_id=ticket1.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_oauth2",
            description="Implement OAuth2 provider integration",
            priority="CRITICAL",
            dependencies={"depends_on": [task1_1.id]},  # Also depends on design
            session=session,
        )
        print(f"  ✓ Created task: {task1_3.description} (depends on task1_1)")

        # Create a discovery that spawns a new task
        discovery1 = TaskDiscovery(
            source_task_id=task1_2.id,
            discovery_type="bug",
            description="Found security issue: JWT tokens need refresh mechanism",
            spawned_task_ids=[],
            priority_boost=True,
            resolution_status="open",
        )
        session.add(discovery1)
        session.flush()

        # Create task spawned from discovery
        task1_4 = queue.enqueue_task(
            ticket_id=ticket1.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_refresh_tokens",
            description="Implement JWT refresh token mechanism",
            priority="CRITICAL",
            dependencies={"depends_on": [task1_2.id]},  # Depends on JWT implementation
            session=session,
        )
        discovery1.add_spawned_task(task1_4.id)
        print(f"  ✓ Created discovery: {discovery1.description}")
        print(f"  ✓ Created task from discovery: {task1_4.description}")

        # Create final task that depends on multiple tasks
        task1_5 = queue.enqueue_task(
            ticket_id=ticket1.id,
            phase_id="PHASE_TESTING",
            task_type="write_tests",
            description="Write integration tests for authentication",
            priority="MEDIUM",
            dependencies={
                "depends_on": [task1_2.id, task1_3.id, task1_4.id]
            },  # Depends on all implementations
            session=session,
        )
        print(
            f"  ✓ Created task: {task1_5.description} (depends on task1_2, task1_3, task1_4)"
        )

        # Create Ticket 2: Database Migrations
        ticket2 = Ticket(
            title="Add Database Migrations",
            description="Set up Alembic migrations and initial schema",
            phase_id="PHASE_IMPLEMENTATION",
            status="pending",
            priority="MEDIUM",
        )
        session.add(ticket2)
        session.flush()
        print(f"\n✓ Created ticket: {ticket2.title} (ID: {ticket2.id[:8]}...)")

        task2_1 = queue.enqueue_task(
            ticket_id=ticket2.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="setup_alembic",
            description="Set up Alembic migration framework",
            priority="MEDIUM",
            session=session,
        )
        print(f"  ✓ Created task: {task2_1.description}")

        task2_2 = queue.enqueue_task(
            ticket_id=ticket2.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="create_initial_schema",
            description="Create initial database schema",
            priority="MEDIUM",
            dependencies={"depends_on": [task2_1.id]},
            session=session,
        )
        print(f"  ✓ Created task: {task2_2.description} (depends on task2_1)")

        # Create Ticket 3: API Endpoints (with parent-child relationships)
        ticket3 = Ticket(
            title="Develop REST API Endpoints",
            description="Create REST API endpoints for user management",
            phase_id="PHASE_IMPLEMENTATION",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket3)
        session.flush()
        print(f"\n✓ Created ticket: {ticket3.title} (ID: {ticket3.id[:8]}...)")

        task3_1 = queue.enqueue_task(
            ticket_id=ticket3.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="design_api",
            description="Design API endpoint structure",
            priority="HIGH",
            session=session,
        )
        print(f"  ✓ Created task: {task3_1.description}")

        # Create parent task
        task3_2 = queue.enqueue_task(
            ticket_id=ticket3.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_endpoints",
            description="Implement user management endpoints",
            priority="HIGH",
            dependencies={"depends_on": [task3_1.id]},
            session=session,
        )
        # Set parent_task_id after creation
        task3_2.parent_task_id = None  # This is the parent, not a child
        print(f"  ✓ Created task: {task3_2.description} (depends on task3_1)")

        # Create child tasks (sub-tasks)
        task3_3 = queue.enqueue_task(
            ticket_id=ticket3.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_get_user",
            description="Implement GET /users/{id} endpoint",
            priority="MEDIUM",
            dependencies={"depends_on": [task3_2.id]},
            session=session,
        )
        # Set parent_task_id after creation
        task3_3.parent_task_id = task3_2.id
        print(f"  ✓ Created sub-task: {task3_3.description} (child of task3_2)")

        task3_4 = queue.enqueue_task(
            ticket_id=ticket3.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_create_user",
            description="Implement POST /users endpoint",
            priority="MEDIUM",
            dependencies={"depends_on": [task3_2.id]},
            session=session,
        )
        # Set parent_task_id after creation
        task3_4.parent_task_id = task3_2.id
        print(f"  ✓ Created sub-task: {task3_4.description} (child of task3_2)")

        # Mark some tasks as completed to test different statuses
        task1_1.status = "completed"
        task1_1.completed_at = utc_now()
        print("\n  ✓ Marked task1_1 as completed")

        task2_1.status = "completed"
        task2_1.completed_at = utc_now()
        print("  ✓ Marked task2_1 as completed")

        task3_1.status = "running"
        task3_1.started_at = utc_now()
        task3_1.assigned_agent_id = "test-agent-123"
        print("  ✓ Marked task3_1 as running (assigned to agent)")

        session.commit()

        print("\n" + "=" * 60)
        print("Test Data Summary:")
        print("=" * 60)
        print("\nTickets created: 3")
        print(f"  - Ticket 1: {ticket1.title} ({ticket1.id})")
        print(f"  - Ticket 2: {ticket2.title} ({ticket2.id})")
        print(f"  - Ticket 3: {ticket3.title} ({ticket3.id})")
        print("\nTasks created: 10")
        print("  - Ticket 1: 5 tasks (with dependencies and discovery)")
        print("  - Ticket 2: 2 tasks (simple dependency chain)")
        print("  - Ticket 3: 3 tasks (with parent-child relationships)")
        print("\nDiscoveries created: 1")
        print("  - Discovery from task1_2 that spawned task1_4")
        print("\n" + "=" * 60)
        print("\nTest the API with:")
        print(f"  GET /api/v1/graph/dependency-graph/ticket/{ticket1.id}")
        print(f"  GET /api/v1/graph/dependency-graph/ticket/{ticket2.id}")
        print(f"  GET /api/v1/graph/dependency-graph/ticket/{ticket3.id}")
        print(f"  GET /api/v1/graph/dependency-graph/task/{task1_2.id}/blocked")
        print(f"  GET /api/v1/graph/dependency-graph/task/{task1_5.id}/blocking")
        print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        create_test_dependency_graph()
        print("\n✓ Test data created successfully!")
    except Exception as e:
        print(f"\n✗ Error creating test data: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
