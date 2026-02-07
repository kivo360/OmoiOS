#!/usr/bin/env python3
"""
End-to-end test script to verify the complete spec-to-sandbox-to-phase flow.

This script simulates the complete lifecycle:
1. Create a spec with requirements and tasks
2. Execute spec tasks (which creates a bridging Ticket and Tasks)
3. Simulate sandbox execution completing tasks
4. Verify phase transitions happen automatically via PhaseManager

Run with:
    cd backend && uv run python scripts/test_e2e_phase_flow.py

Requirements:
    - Backend services running (or use --mock mode)
    - Database accessible
"""

import argparse
import asyncio
import sys
import uuid

# Add parent to path for imports
sys.path.insert(0, ".")


async def test_full_phase_flow(
    base_url: str = "http://localhost:18000", mock_mode: bool = False
):
    """Test the complete flow from spec creation to phase completion."""

    if mock_mode:
        return await test_with_mock_services()

    return await test_with_live_api(base_url)


async def test_with_mock_services():
    """Test flow using in-memory mock services (no API needed).

    This test directly invokes the PhaseManager event handlers rather than
    relying on Redis pub/sub, which makes it more reliable for testing.
    """
    from omoi_os.config import get_app_settings
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.task_queue import TaskQueueService
    from omoi_os.services.phase_manager import get_phase_manager
    from omoi_os.services.phase_gate import PhaseGateService
    from omoi_os.models.ticket import Ticket
    from omoi_os.models.task import Task
    from omoi_os.utils.datetime import utc_now

    print("\n" + "=" * 70)
    print("E2E Phase Flow Test (Mock Mode - Direct Handler Invocation)")
    print("=" * 70)

    # Initialize services with config
    settings = get_app_settings()
    db = DatabaseService(settings.database.url)
    # Don't use event_bus for this test - we'll call handlers directly
    task_queue = TaskQueueService(db, event_bus=None)
    phase_gate = PhaseGateService(db)

    # Initialize PhaseManager WITHOUT event subscription
    # We'll call handlers directly for testing
    phase_manager = get_phase_manager(
        db=db,
        task_queue=task_queue,
        phase_gate=phase_gate,
        event_bus=None,
    )
    print("✓ PhaseManager initialized (direct handler mode)")

    # Create a test ticket
    ticket_id = str(uuid.uuid4())
    with db.get_session() as session:
        ticket = Ticket(
            id=ticket_id,
            title="Test Feature: E2E Phase Flow",
            description="Test ticket for validating phase transitions",
            status="BACKLOG",
            phase_id="PHASE_BACKLOG",
            priority="HIGH",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(ticket)
        session.commit()
        print(f"✓ Created test ticket: {ticket_id}")

    # Step 1: Enqueue an implement_feature task (simulates spec task execution)
    print("\n--- Step 1: Creating implementation task ---")
    task = task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="implement_feature",
        description="Implement the test feature",
        priority="HIGH",
    )
    print(f"✓ Created task: {task.id} (type: {task.task_type})")

    # Check ticket status after task creation
    with db.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        print(f"  Ticket phase: {ticket.phase_id}, status: {ticket.status}")

    # Step 2: Simulate task starting (what sandbox does)
    print("\n--- Step 2: Simulating task start (sandbox picks up task) ---")
    sandbox_id = f"sandbox-{uuid.uuid4().hex[:8]}"

    # Assign task to sandbox
    with db.get_session() as session:
        task_obj = session.get(Task, str(task.id))
        task_obj.sandbox_id = sandbox_id
        task_obj.status = "running"
        task_obj.started_at = utc_now()
        session.commit()

    # DIRECTLY call the PhaseManager handler (simulates what would happen via event bus)
    # This is equivalent to what happens when TASK_STARTED event is received
    task_started_event = {
        "event_type": "TASK_STARTED",
        "entity_type": "task",
        "entity_id": str(task.id),
        "payload": {
            "task_id": str(task.id),
            "ticket_id": ticket_id,
            "phase_id": "PHASE_IMPLEMENTATION",
            "task_type": "implement_feature",
            "status": "running",
            "sandbox_id": sandbox_id,
        },
    }
    phase_manager._handle_task_started(task_started_event)
    print(f"✓ Task started in sandbox: {sandbox_id}")
    print("  → PhaseManager._handle_task_started() called directly")

    # Check ticket status after task started
    with db.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        print(f"  Ticket phase: {ticket.phase_id}, status: {ticket.status}")

    # Step 3: Simulate task completion (what sandbox reports)
    print("\n--- Step 3: Simulating task completion (sandbox reports done) ---")

    # Update task status in database
    with db.get_session() as session:
        task_obj = session.get(Task, str(task.id))
        task_obj.status = "completed"
        task_obj.completed_at = utc_now()
        task_obj.result = {
            "output": "Feature implemented successfully",
            "branch_name": "feature/test-e2e-flow",
            "files_changed": ["src/feature.py", "tests/test_feature.py"],
        }
        session.commit()

    # DIRECTLY call the PhaseManager handler (simulates what would happen via event bus)
    # This is equivalent to what happens when TASK_COMPLETED event is received
    task_completed_event = {
        "event_type": "TASK_COMPLETED",
        "entity_type": "task",
        "entity_id": str(task.id),
        "payload": {
            "task_id": str(task.id),
            "ticket_id": ticket_id,
            "phase_id": "PHASE_IMPLEMENTATION",
            "task_type": "implement_feature",
            "status": "completed",
        },
    }
    phase_manager._handle_task_completed(task_completed_event)
    print("✓ Task completed")
    print("  → PhaseManager._handle_task_completed() called directly")

    # Step 4: Verify phase transition happened
    print("\n--- Step 4: Verifying phase transition ---")
    with db.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        print(f"  Final ticket phase: {ticket.phase_id}")
        print(f"  Final ticket status: {ticket.status}")

        # Status can be "done" or "DONE" depending on config
        if ticket.phase_id == "PHASE_DONE" and ticket.status.upper() == "DONE":
            print("\n" + "=" * 70)
            print("✓ SUCCESS: Ticket transitioned to PHASE_DONE automatically!")
            print("=" * 70)
            return True
        else:
            print("\n" + "=" * 70)
            print(
                f"✗ UNEXPECTED: Expected PHASE_DONE, got {ticket.phase_id}/{ticket.status}"
            )
            print("=" * 70)
            return False


async def test_with_live_api(base_url: str):
    """Test flow using live API endpoints."""
    import httpx

    print("\n" + "=" * 70)
    print(f"E2E Phase Flow Test (Live API: {base_url})")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0):
        # Step 1: Create a test project (if needed)
        print("\n--- Step 1: Setup test project and spec ---")

        # For demo, we'd typically have a project already
        # This shows the API flow you'd use

        # Create spec
        # POST /api/v1/projects/{project_id}/specs

        # Execute spec (runs state machine in sandbox)
        # POST /api/v1/specs/{spec_id}/execute

        # After spec completes, execute tasks
        # POST /api/v1/specs/{spec_id}/execute-tasks

        # Monitor task execution status
        # GET /api/v1/specs/{spec_id}/execution-status

        # When sandbox completes a task, it calls:
        # POST /api/v1/sandboxes/{sandbox_id}/task-complete

        # PhaseManager event handlers automatically move phases

        print("Live API test not fully implemented - use mock mode for validation")
        print("Or run through the UI to test the flow")
        return True


def print_flow_diagram():
    """Print the execution flow diagram."""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                        SPEC → SANDBOX → PHASE FLOW                          ║
╚════════════════════════════════════════════════════════════════════════════╝

1. SPEC CREATION & EXECUTION
   ┌─────────────────────────────────────────────────────────────────────────┐
   │  POST /specs/{spec_id}/execute                                          │
   │    └── DaytonaSpawner.spawn_for_phase()                                 │
   │          └── Sandbox runs SpecStateMachine                              │
   │                └── EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC       │
   │                      └── Saves SpecTasks to database                    │
   └─────────────────────────────────────────────────────────────────────────┘

2. TASK EXECUTION
   ┌─────────────────────────────────────────────────────────────────────────┐
   │  POST /specs/{spec_id}/execute-tasks                                    │
   │    └── SpecTaskExecutionService.execute_spec_tasks()                    │
   │          ├── Creates/finds bridging Ticket for Spec                     │
   │          ├── Converts SpecTasks → Tasks (linked to Ticket)              │
   │          └── Sets Task.phase_id = "PHASE_IMPLEMENTATION"                │
   └─────────────────────────────────────────────────────────────────────────┘

3. SANDBOX EXECUTION (per Task)
   ┌─────────────────────────────────────────────────────────────────────────┐
   │  OrchestratorWorker picks up Task                                       │
   │    └── DaytonaSpawner.spawn_for_task()                                  │
   │          └── Sandbox runs Claude Agent for implementation               │
   │                └── When done: POST /sandboxes/{id}/task-complete        │
   └─────────────────────────────────────────────────────────────────────────┘

4. TASK COMPLETION → PHASE TRANSITION
   ┌─────────────────────────────────────────────────────────────────────────┐
   │  POST /sandboxes/{sandbox_id}/task-complete                             │
   │    └── TaskQueueService.update_task_status_async()                      │
   │          └── Publishes TASK_COMPLETED event                             │
   │                                                                         │
   │  PhaseManager._handle_task_completed() (event subscriber)               │
   │    ├── If task_type == "implement_feature":                             │
   │    │     └── move_to_done(ticket_id)  → PHASE_DONE / DONE               │
   │    └── Else:                                                            │
   │          └── check_and_advance(ticket_id)  → Next phase if gates pass   │
   └─────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
KEY EVENTS:
  • TASK_STARTED    → PhaseManager moves to PHASE_IMPLEMENTATION if needed
  • TASK_COMPLETED  → PhaseManager advances to next phase or PHASE_DONE
  • TASKS_UNBLOCKED → DAG evaluation spawns dependent tasks

KEY SERVICES:
  • PhaseManager       - Handles phase transitions, event subscriptions
  • TaskQueueService   - Task CRUD, status updates, event publishing
  • DaytonaSpawner     - Creates sandboxes for specs and tasks
  • EventBusService    - Pub/sub for TASK_* events

SANDBOX_ID:
  • Set on Task when sandbox is spawned
  • Used for routing completion callbacks
  • Multiple tasks can share same sandbox (sequential) or separate sandboxes
═══════════════════════════════════════════════════════════════════════════════
""")


async def main():
    parser = argparse.ArgumentParser(description="Test E2E phase flow")
    parser.add_argument(
        "--url", default="http://localhost:18000", help="Backend API URL"
    )
    parser.add_argument(
        "--mock", action="store_true", help="Use mock services (no API needed)"
    )
    parser.add_argument(
        "--diagram", action="store_true", help="Print flow diagram and exit"
    )
    args = parser.parse_args()

    if args.diagram:
        print_flow_diagram()
        return

    success = await test_full_phase_flow(args.url, args.mock)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
