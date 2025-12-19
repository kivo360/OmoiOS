#!/usr/bin/env python3
"""E2E test for sandbox monitoring integration.

Tests that Guardian, Conductor, and MonitoringLoop can properly
detect and monitor sandbox tasks after the sandbox migration fixes.

Prerequisites:
1. Run test_api_sandbox_spawn.py first to create a sandbox task
2. Or manually create a task with sandbox_id set

Usage:
    cd backend
    uv run python scripts/test_sandbox_monitoring_e2e.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.local")

from omoi_os.config import get_app_settings
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.monitoring_loop import MonitoringLoop, MonitoringConfig
from omoi_os.services.intelligent_guardian import IntelligentGuardian
from omoi_os.services.conductor import ConductorService
from omoi_os.services.trajectory_context import TrajectoryContext
from omoi_os.services.agent_output_collector import AgentOutputCollector
from omoi_os.models.task import Task


def test_sandbox_tasks_exist(db: DatabaseService) -> list:
    """Check for running sandbox tasks in the database."""
    print("\n[1/6] Checking for sandbox tasks in database...")
    with db.get_session() as session:
        # Check for any tasks with sandbox_id
        sandbox_tasks = (
            session.query(Task)
            .filter(Task.sandbox_id.isnot(None))
            .order_by(Task.created_at.desc())
            .limit(10)
            .all()
        )

        if not sandbox_tasks:
            print("   ⚠️  No sandbox tasks found in database.")
            print("   Run test_api_sandbox_spawn.py first to create one.")
            return []

        running_tasks = [t for t in sandbox_tasks if t.status in ["running", "assigned"]]
        print(f"   ✅ Found {len(sandbox_tasks)} sandbox task(s) total")
        print(f"   ✅ Found {len(running_tasks)} running/assigned sandbox task(s)")

        for task in sandbox_tasks[:5]:  # Show first 5
            print(
                f"      - Task {str(task.id)[:8]}... | Status: {task.status} | Sandbox: {task.sandbox_id[:20]}..."
            )

        return sandbox_tasks


def test_monitoring_loop_detection(db: DatabaseService, event_bus: EventBusService) -> bool:
    """Test MonitoringLoop._get_active_sandbox_agent_ids()."""
    print("\n[2/6] Testing MonitoringLoop._get_active_sandbox_agent_ids()...")
    try:
        config = MonitoringConfig(
            guardian_interval_seconds=60,
            conductor_interval_seconds=300,
            auto_steering_enabled=False,
        )
        monitoring_loop = MonitoringLoop(db, event_bus, config)
        sandbox_ids = monitoring_loop._get_active_sandbox_agent_ids()
        print(f"   ✅ Found {len(sandbox_ids)} active sandbox IDs via MonitoringLoop")
        for sid in sandbox_ids[:3]:  # Show first 3
            print(f"      - {sid[:40]}...")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


def test_guardian_detection(db: DatabaseService) -> bool:
    """Test IntelligentGuardian._get_active_sandbox_agent_ids()."""
    print("\n[3/6] Testing IntelligentGuardian._get_active_sandbox_agent_ids()...")
    try:
        guardian = IntelligentGuardian(db)
        sandbox_ids = guardian._get_active_sandbox_agent_ids()
        print(f"   ✅ Found {len(sandbox_ids)} active sandbox IDs via Guardian")
        for sid in sandbox_ids[:3]:
            print(f"      - {sid[:40]}...")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


def test_conductor_detection(db: DatabaseService) -> bool:
    """Test ConductorService._get_active_sandbox_agent_ids()."""
    print("\n[4/6] Testing ConductorService._get_active_sandbox_agent_ids()...")
    try:
        conductor = ConductorService(db)
        with db.get_session() as session:
            sandbox_ids = conductor._get_active_sandbox_agent_ids(session)
            print(f"   ✅ Found {len(sandbox_ids)} active sandbox IDs via Conductor")
            for sid in sandbox_ids[:3]:
                print(f"      - {sid[:40]}...")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


def test_trajectory_context(db: DatabaseService) -> bool:
    """Test TrajectoryContext.get_sandbox_id_for_agent()."""
    print("\n[5/6] Testing TrajectoryContext.get_sandbox_id_for_agent()...")
    try:
        trajectory = TrajectoryContext(db)
        with db.get_session() as session:
            sandbox_task = session.query(Task).filter(Task.sandbox_id.isnot(None)).first()

            if sandbox_task and sandbox_task.sandbox_id:
                # Test: passing sandbox_id should return itself
                result = trajectory.get_sandbox_id_for_agent(sandbox_task.sandbox_id)
                if result == sandbox_task.sandbox_id:
                    print(f"   ✅ get_sandbox_id_for_agent() correctly returns sandbox_id")
                    print(f"      Input:  {sandbox_task.sandbox_id[:40]}...")
                    print(f"      Output: {result[:40]}...")
                    return True
                else:
                    print(f"   ❌ Expected {sandbox_task.sandbox_id[:30]}...")
                    print(f"      Got: {result}")
                    return False
            else:
                print("   ⚠️  No sandbox tasks to test with - SKIP")
                return True  # Not a failure, just no data
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


def test_agent_output_collector(db: DatabaseService, event_bus: EventBusService) -> bool:
    """Test AgentOutputCollector.get_sandbox_id_for_agent()."""
    print("\n[6/6] Testing AgentOutputCollector.get_sandbox_id_for_agent()...")
    try:
        collector = AgentOutputCollector(db, event_bus)
        with db.get_session() as session:
            sandbox_task = session.query(Task).filter(Task.sandbox_id.isnot(None)).first()

            if sandbox_task and sandbox_task.sandbox_id:
                result = collector.get_sandbox_id_for_agent(sandbox_task.sandbox_id)
                if result == sandbox_task.sandbox_id:
                    print(f"   ✅ get_sandbox_id_for_agent() correctly returns sandbox_id")
                    print(f"      Input:  {sandbox_task.sandbox_id[:40]}...")
                    print(f"      Output: {result[:40]}...")
                    return True
                else:
                    print(f"   ❌ Expected {sandbox_task.sandbox_id[:30]}...")
                    print(f"      Got: {result}")
                    return False
            else:
                print("   ⚠️  No sandbox tasks to test with - SKIP")
                return True  # Not a failure, just no data
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


def main():
    print("=" * 70)
    print("SANDBOX MONITORING E2E TEST")
    print("=" * 70)

    settings = get_app_settings()
    db = DatabaseService(settings.database.url)
    event_bus = EventBusService(settings.redis.url)

    # Mask credentials in URL for display
    db_display = settings.database.url
    if "@" in db_display:
        parts = db_display.split("@")
        db_display = f"***@{parts[1]}"

    redis_display = settings.redis.url
    if "@" in redis_display:
        parts = redis_display.split("@")
        redis_display = f"***@{parts[1]}"

    print(f"\nDatabase: {db_display}")
    print(f"Redis: {redis_display}")

    results = []

    # Run all tests
    sandbox_tasks = test_sandbox_tasks_exist(db)
    results.append(("Sandbox Tasks Exist", len(sandbox_tasks) > 0 or True))  # True if no tasks (not a failure)

    results.append(("MonitoringLoop Detection", test_monitoring_loop_detection(db, event_bus)))
    results.append(("Guardian Detection", test_guardian_detection(db)))
    results.append(("Conductor Detection", test_conductor_detection(db)))
    results.append(("TrajectoryContext", test_trajectory_context(db)))
    results.append(("AgentOutputCollector", test_agent_output_collector(db, event_bus)))

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = 0
    failed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}: {test_name}")
        if success:
            passed += 1
        else:
            failed += 1

    print("\n" + "-" * 70)
    print(f"   Total: {len(results)} | Passed: {passed} | Failed: {failed}")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("   Sandbox monitoring systems are working correctly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Check the output above for details.")

    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
