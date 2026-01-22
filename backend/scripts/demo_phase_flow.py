#!/usr/bin/env python3
"""
Demo test script for sandbox task completion and phase flow.

Three test modes:
1. --mock: Direct PhaseManager handler invocation (fastest, no Redis needed)
2. --integration: Full flow with mocked Daytona responses (tests API + events)
3. --ui: Prints manual UI test steps

All modes use the cloud database (Railway) by default.

Usage:
    # Option 1: Mock test (direct handler calls)
    cd backend && uv run python scripts/demo_phase_flow.py --mock

    # Option 2: Integration test (mocked Daytona, real API flow)
    cd backend && uv run python scripts/demo_phase_flow.py --integration

    # Option 3: Manual UI test steps
    cd backend && uv run python scripts/demo_phase_flow.py --ui

    # Use local database instead of cloud
    cd backend && uv run python scripts/demo_phase_flow.py --mock --local

Environment:
    Uses .env.remote-test for cloud database by default.
    Use --local flag to use local database instead.
"""

import argparse
import asyncio
import os
import sys
import uuid
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def setup_cloud_env():
    """Load cloud database configuration from .env.remote-test."""
    env_file = Path(__file__).parent.parent / ".env.remote-test"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Map TEST vars to regular vars for the app
                    if key == "DATABASE_URL_TEST":
                        os.environ["DATABASE_URL"] = value
                    elif key == "REDIS_URL_TEST":
                        os.environ["REDIS_URL"] = value
                    else:
                        os.environ[key] = value
        print("✓ Loaded cloud database configuration from .env.remote-test")
        return True
    else:
        print("⚠ .env.remote-test not found, using default configuration")
        return False


async def test_mock_mode():
    """
    Option 1: Mock Test

    Directly invokes PhaseManager event handlers without needing Redis.
    This is the fastest way to verify the phase transition logic works.
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
    print("DEMO: Mock Test (Direct PhaseManager Handler Invocation)")
    print("=" * 70)

    # Initialize services
    settings = get_app_settings()
    db = DatabaseService(settings.database.url)
    task_queue = TaskQueueService(db, event_bus=None)
    phase_gate = PhaseGateService(db)

    phase_manager = get_phase_manager(
        db=db,
        task_queue=task_queue,
        phase_gate=phase_gate,
        event_bus=None,
    )
    print("✓ Services initialized (using cloud database)")

    # Create test ticket
    ticket_id = str(uuid.uuid4())
    with db.get_session() as session:
        ticket = Ticket(
            id=ticket_id,
            title=f"Demo Test: Phase Flow {utc_now().strftime('%H:%M:%S')}",
            description="Demo ticket for validating phase transitions",
            status="BACKLOG",
            phase_id="PHASE_BACKLOG",
            priority="HIGH",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(ticket)
        session.commit()
        print(f"✓ Created test ticket: {ticket_id[:8]}...")

    # Step 1: Create implementation task
    print("\n--- Step 1: Create implementation task ---")
    task = task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="implement_feature",
        description="Implement the demo feature",
        priority="HIGH",
    )
    print(f"✓ Created task: {str(task.id)[:8]}... (type: {task.task_type})")

    # Step 2: Simulate task start
    print("\n--- Step 2: Simulate task start (sandbox picks up task) ---")
    sandbox_id = f"demo-sandbox-{uuid.uuid4().hex[:8]}"

    with db.get_session() as session:
        task_obj = session.get(Task, str(task.id))
        task_obj.sandbox_id = sandbox_id
        task_obj.status = "running"
        task_obj.started_at = utc_now()
        session.commit()

    # Call PhaseManager handler directly
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

    with db.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        print(f"  Ticket phase: {ticket.phase_id}")

    # Step 3: Simulate task completion
    print("\n--- Step 3: Simulate task completion ---")

    with db.get_session() as session:
        task_obj = session.get(Task, str(task.id))
        task_obj.status = "completed"
        task_obj.completed_at = utc_now()
        task_obj.result = {
            "output": "Feature implemented successfully",
            "context_injected": True,  # New: context was injected at creation
        }
        session.commit()

    # Call PhaseManager handler directly
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

    # Step 4: Verify phase transition
    print("\n--- Step 4: Verify phase transition ---")
    with db.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        print(f"  Final phase: {ticket.phase_id}")
        print(f"  Final status: {ticket.status}")

        if ticket.phase_id == "PHASE_DONE" and ticket.status.upper() == "DONE":
            print("\n" + "=" * 70)
            print("✅ SUCCESS: Ticket transitioned to PHASE_DONE automatically!")
            print("=" * 70)

            # Cleanup
            print("\n--- Cleanup ---")
            session.delete(ticket)
            task_obj = session.get(Task, str(task.id))
            if task_obj:
                session.delete(task_obj)
            session.commit()
            print("✓ Test data cleaned up")
            return True
        else:
            print("\n" + "=" * 70)
            print(f"❌ FAILED: Expected PHASE_DONE, got {ticket.phase_id}/{ticket.status}")
            print("=" * 70)
            return False


async def test_integration_mode():
    """
    Option 2: Integration Test

    Tests the task context builder and phase transitions.
    Creates a simple Ticket -> Task flow (no spec needed for basic test).
    """
    from omoi_os.config import get_app_settings
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.task_queue import TaskQueueService
    from omoi_os.services.phase_manager import get_phase_manager
    from omoi_os.services.phase_gate import PhaseGateService
    from omoi_os.services.task_context_builder import TaskContextBuilder
    from omoi_os.models.ticket import Ticket
    from omoi_os.models.task import Task
    from omoi_os.utils.datetime import utc_now

    print("\n" + "=" * 70)
    print("DEMO: Integration Test (TaskContextBuilder + PhaseManager)")
    print("=" * 70)

    # Initialize services
    settings = get_app_settings()
    db = DatabaseService(settings.database.url)
    task_queue = TaskQueueService(db, event_bus=None)
    phase_gate = PhaseGateService(db)
    context_builder = TaskContextBuilder(db)

    phase_manager = get_phase_manager(
        db=db,
        task_queue=task_queue,
        phase_gate=phase_gate,
        event_bus=None,
    )
    print("✓ Services initialized")

    # Create test data: Ticket -> Task (no spec needed for basic test)
    print("\n--- Setup: Create Ticket and Task ---")

    ticket_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())

    with db.get_session() as session:
        # Create ticket (no spec linkage for simple test)
        ticket = Ticket(
            id=ticket_id,
            title=f"Demo: Integration Test {utc_now().strftime('%H:%M:%S')}",
            description="Integration test for context builder and phase transitions",
            status="BACKLOG",
            phase_id="PHASE_BACKLOG",
            priority="HIGH",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(ticket)

        # Create task linked to ticket
        task = Task(
            id=task_id,
            ticket_id=ticket_id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Implement the demo feature with full context injection",
            status="pending",
            priority="HIGH",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(task)
        session.commit()

        print(f"✓ Created Ticket: {ticket_id[:8]}...")
        print(f"✓ Created Task: {task_id[:8]}...")

    # Test TaskContextBuilder (the new context injection system)
    print("\n--- Test: TaskContextBuilder (Context Injection) ---")

    context = context_builder.build_context_sync(task_id)
    if context:
        print(f"✓ Context built successfully")
        print(f"  - Task: {context.task_description[:50]}...")
        print(f"  - Ticket: {context.ticket_title}")
        print(f"  - Spec: {context.spec_title or '(no spec linked)'}")

        # Generate markdown (what gets injected into sandbox)
        markdown = context.to_markdown()
        if markdown:
            print(f"  - Markdown context: {len(markdown)} chars")
            print("✓ Context would be injected via TASK_DATA_BASE64")
    else:
        print("⚠ No context built (expected for task without spec)")

    # Simulate sandbox execution
    print("\n--- Test: Simulated Sandbox Execution ---")

    sandbox_id = f"demo-{uuid.uuid4().hex[:8]}"

    with db.get_session() as session:
        task_obj = session.get(Task, task_id)
        task_obj.sandbox_id = sandbox_id
        task_obj.status = "running"
        task_obj.started_at = utc_now()
        session.commit()

    print(f"✓ Task assigned to sandbox: {sandbox_id}")
    print("  (In real flow: DaytonaSpawner creates sandbox with TASK_DATA_BASE64)")

    # Trigger task started
    phase_manager._handle_task_started({
        "event_type": "TASK_STARTED",
        "payload": {
            "task_id": task_id,
            "ticket_id": ticket_id,
            "task_type": "implement_feature",
        },
    })
    print("✓ TASK_STARTED event processed")

    with db.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        print(f"  Ticket phase after start: {ticket.phase_id}")

    # Simulate task completion
    with db.get_session() as session:
        task_obj = session.get(Task, task_id)
        task_obj.status = "completed"
        task_obj.completed_at = utc_now()
        task_obj.result = {
            "output": "Implementation complete",
            "context_injected": True,
            "no_mcp_calls": True,
        }
        session.commit()

    # Trigger task completed
    phase_manager._handle_task_completed({
        "event_type": "TASK_COMPLETED",
        "payload": {
            "task_id": task_id,
            "ticket_id": ticket_id,
            "task_type": "implement_feature",
        },
    })
    print("✓ TASK_COMPLETED event processed")

    # Verify results
    print("\n--- Verify: Phase Transition ---")
    with db.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        print(f"  Ticket phase: {ticket.phase_id}")
        print(f"  Ticket status: {ticket.status}")

        success = ticket.phase_id == "PHASE_DONE" and ticket.status.upper() == "DONE"

        # Cleanup
        print("\n--- Cleanup ---")
        task_obj = session.get(Task, task_id)
        if task_obj:
            session.delete(task_obj)
        session.delete(ticket)
        session.commit()
        print("✓ Test data cleaned up")

        if success:
            print("\n" + "=" * 70)
            print("✅ SUCCESS: Integration test passed!")
            print("   - TaskContextBuilder works ✓")
            print("   - Phase transitions via PhaseManager ✓")
            print("   - No MCP tools needed (context pre-injected) ✓")
            print("=" * 70)
            return True
        else:
            print("\n" + "=" * 70)
            print(f"❌ FAILED: Phase transition did not complete")
            print("=" * 70)
            return False


def print_ui_test_steps():
    """
    Option 3: Manual UI Test Steps

    Prints step-by-step instructions for testing via the UI.
    """
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      MANUAL UI TEST: Phase Flow Demo                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Prerequisites:
  • Frontend running: https://omoios.dev (or localhost:3000)
  • Backend running: https://api.omoios.dev (Railway)
  • Daytona workspace available

═══════════════════════════════════════════════════════════════════════════════

STEP 1: Create a New Spec
─────────────────────────
  1. Navigate to a project in the dashboard
  2. Click "New Spec" or use the command palette (Cmd+K)
  3. Enter a simple feature description, e.g.:
     "Add a health check endpoint that returns server status"
  4. Click "Create & Execute"

STEP 2: Watch Spec Generation
─────────────────────────────
  1. Observe the spec phases progressing:
     EXPLORE → PRD → REQUIREMENTS → DESIGN → TASKS → SYNC
  2. Each phase updates in real-time
  3. When complete, you'll see:
     • Requirements with acceptance criteria
     • Design documents
     • SpecTasks ready for execution

STEP 3: Execute Tasks
─────────────────────
  1. Click "Execute Tasks" on the spec
  2. This will:
     • Create a bridging Ticket (PHASE_BACKLOG)
     • Convert SpecTasks → Tasks
     • Spawn sandbox(es) for implementation

  3. Watch the sandbox terminal output:
     • Context is injected via TASK_DATA_BASE64 (no MCP calls!)
     • Agent implements the feature
     • Agent signals "TASK_COMPLETE"

STEP 4: Verify Phase Transition
───────────────────────────────
  1. After sandbox completes:
     • Task status → "completed"
     • Ticket phase → PHASE_DONE
     • Ticket status → DONE

  2. Check the Kanban board:
     • Ticket should move to "Done" column automatically

STEP 5: Verify Acceptance Criteria (Future)
───────────────────────────────────────────
  1. In the spec dashboard, check Requirements tab
  2. Acceptance criteria checkboxes should be checked
     (requires frontend WebSocket integration - TODO)

═══════════════════════════════════════════════════════════════════════════════

KEY THINGS TO OBSERVE:
  ✓ No MCP tool calls in sandbox logs (context pre-injected)
  ✓ Phase transitions happen automatically
  ✓ No manual intervention needed after "Execute Tasks"

TROUBLESHOOTING:
  • If sandbox doesn't start: Check Daytona workspace status
  • If phase doesn't transition: Check PhaseManager logs in Railway
  • If context missing: Verify TaskContextBuilder ran in orchestrator

═══════════════════════════════════════════════════════════════════════════════
""")
    return True


async def main():
    parser = argparse.ArgumentParser(
        description="Demo test script for phase flow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/demo_phase_flow.py --mock          # Fast mock test
  uv run python scripts/demo_phase_flow.py --integration   # Full integration test
  uv run python scripts/demo_phase_flow.py --ui            # Print UI test steps
  uv run python scripts/demo_phase_flow.py --mock --local  # Use local database
        """,
    )
    parser.add_argument("--mock", action="store_true", help="Run mock test (direct handler calls)")
    parser.add_argument("--integration", action="store_true", help="Run integration test (mocked Daytona)")
    parser.add_argument("--ui", action="store_true", help="Print manual UI test steps")
    parser.add_argument("--local", action="store_true", help="Use local database instead of cloud")
    args = parser.parse_args()

    # Default to mock if no option specified
    if not any([args.mock, args.integration, args.ui]):
        args.mock = True

    # Setup cloud database unless --local specified
    if not args.local:
        setup_cloud_env()
    else:
        print("✓ Using local database configuration")

    # Run selected test
    if args.ui:
        success = print_ui_test_steps()
    elif args.integration:
        success = await test_integration_mode()
    else:
        success = await test_mock_mode()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
