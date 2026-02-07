#!/usr/bin/env python3
"""Smoke test script to verify the minimal E2E flow works."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from omoi_os.config import get_app_settings
from omoi_os.models.agent import Agent
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.task_queue import TaskQueueService


def main():
    """Run smoke test."""
    print("=" * 60)
    print("OmoiOS Smoke Test")
    print("=" * 60)

    # Initialize services
    app_settings = get_app_settings()
    database_url = app_settings.database.url
    redis_url = app_settings.redis.url

    print("\n1. Initializing services...")
    print(f"   Database: {database_url}")
    print(f"   Redis: {redis_url}")

    db = DatabaseService(database_url)
    event_bus = EventBusService(redis_url)
    task_queue = TaskQueueService(db)

    # Create tables
    print("\n2. Creating database tables...")
    db.create_tables()
    print("   ✓ Tables created")

    # Create ticket
    print("\n3. Creating test ticket...")
    with db.get_session() as session:
        ticket = Ticket(
            title="Smoke Test Ticket",
            description="This is a smoke test to verify the system works",
            phase_id="PHASE_REQUIREMENTS",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        ticket_id = ticket.id
    print(f"   ✓ Ticket created: {ticket_id}")

    # Enqueue task
    print("\n4. Enqueueing task...")
    task = task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="smoke_test_task",
        description="Smoke test task",
        priority="HIGH",
    )
    task_id = task.id
    print(f"   ✓ Task enqueued: {task_id}")

    # Register agent
    print("\n5. Registering agent...")
    with db.get_session() as session:
        agent = Agent(
            agent_type="worker",
            phase_id="PHASE_REQUIREMENTS",
            status="idle",
            capabilities=["bash", "file_editor"],
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
        agent_id = agent.id
    print(f"   ✓ Agent registered: {agent_id}")

    # Assign task
    print("\n6. Assigning task to agent...")
    task_queue.assign_task(task_id, agent_id)
    print("   ✓ Task assigned")

    # Publish event
    print("\n7. Publishing TASK_ASSIGNED event...")
    event = SystemEvent(
        event_type="TASK_ASSIGNED",
        entity_type="task",
        entity_id=task_id,
        payload={"agent_id": agent_id},
    )
    event_bus.publish(event)
    print("   ✓ Event published")

    # Update task status
    print("\n8. Updating task status to completed...")
    task_queue.update_task_status(
        task_id,
        "completed",
        result={"status": "success", "message": "Smoke test passed"},
    )
    print("   ✓ Task completed")

    # Verify final state
    print("\n9. Verifying final state...")
    with db.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        task = session.get(Task, task_id)
        agent = session.get(Agent, agent_id)

        assert ticket is not None, "Ticket should exist"
        assert task is not None, "Task should exist"
        assert task.status == "completed", "Task should be completed"
        assert agent is not None, "Agent should exist"

    print("   ✓ All checks passed")

    # Cleanup
    print("\n10. Cleaning up...")
    db.drop_tables()
    event_bus.close()
    print("   ✓ Cleanup complete")

    print("\n" + "=" * 60)
    print("✓ Smoke test PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
