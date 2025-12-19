# Sandbox Monitoring System Testing Plan

**Created**: 2025-12-19
**Status**: Draft
**Purpose**: Test plan for validating sandbox spawning and the guardian/conductor/monitoring systems after the sandbox migration fixes.

---

## Overview

This testing plan validates that the sandbox migration fixes work correctly with the Guardian, Conductor, and MonitoringLoop systems. The fixes ensure these monitoring services can properly detect and interact with sandbox tasks (which use `sandbox_id`) rather than only legacy tasks (which use `assigned_agent_id`).

## Prerequisites

### Database Configuration

The config files are already configured to use remote Railway databases:

- **Database URL**: `postgresql+psycopg://postgres:***@REDACTED_DB_HOST:5432/REDACTED_DB`
- **Redis URL**: `redis://default:***@crossover.proxy.rlwy.net:23902`

Verify configuration by checking:
```bash
# View current config (from backend directory)
cat config/local.yaml | grep -A2 "database:"
cat config/local.yaml | grep -A2 "redis:"
```

### Environment Variables

Ensure `.env.local` has the required variables:
```bash
# Required for sandbox spawning
DAYTONA_API_KEY=dtn_...
ORCHESTRATOR_ENABLED=true
DAYTONA_SANDBOX_EXECUTION=true

# For callback URLs (point to Railway production)
CALLBACK_URL=https://omoi-api-production.up.railway.app/sandbox/events
MESSAGE_POLL_URL=https://omoi-api-production.up.railway.app/sandbox/messages
```

---

## Test Categories

### 1. E2E Sandbox Spawn Test (Existing)

**Script**: `backend/scripts/test_api_sandbox_spawn.py`

This is the primary E2E test that validates:
- Project creation/linking
- Ticket creation with task
- Task dispatch to orchestrator
- Sandbox spawning via Daytona
- Event callbacks (SandboxEvent creation)
- Task completion

**Usage**:
```bash
cd backend
uv run python scripts/test_api_sandbox_spawn.py
```

**What it validates**:
- [x] Task creation from ticket
- [x] Orchestrator picks up task
- [x] Daytona sandbox spawns
- [x] Sandbox events are recorded
- [x] Worker completes task

---

### 2. Guardian Sandbox Integration Tests

**Script**: `backend/tests/integration/sandbox/test_guardian_sandbox_integration.py`

**Run with**:
```bash
cd backend
uv run pytest tests/integration/sandbox/test_guardian_sandbox_integration.py -v
```

**What it validates**:
- [x] Guardian detects sandbox tasks (`_is_sandbox_task()`)
- [x] Guardian routes interventions to message injection API
- [x] Message injection endpoint works for guardian_nudge
- [x] Worker scripts handle guardian messages

---

### 3. Monitoring Loop Sandbox Detection Test

**Purpose**: Verify `_get_active_sandbox_agent_ids()` in monitoring services returns sandbox IDs correctly.

**Key Methods Fixed**:
- `MonitoringLoop._get_active_sandbox_agent_ids()`
- `Conductor._get_active_sandbox_agent_ids()`
- `IntelligentGuardian._get_active_sandbox_agent_ids()`

**Manual Test**:
```python
# Run from backend directory
cd backend
uv run python -c "
from omoi_os.config import get_app_settings
from omoi_os.services.database import DatabaseService
from omoi_os.services.monitoring_loop import MonitoringLoop
from omoi_os.services.event_bus import EventBusService

settings = get_app_settings()
db = DatabaseService(settings.database.url)
event_bus = EventBusService(settings.redis.url)

loop = MonitoringLoop(db, event_bus)
sandbox_ids = loop._get_active_sandbox_agent_ids()
print(f'Active sandbox IDs: {sandbox_ids}')
"
```

---

### 4. Trajectory Context Sandbox Test

**Purpose**: Verify `get_sandbox_id_for_agent()` correctly identifies sandbox agents.

**Key Fix**: The method now checks if the passed ID is itself a sandbox_id first, before falling back to legacy agent lookup.

**Manual Test**:
```python
cd backend
uv run python -c "
from omoi_os.config import get_app_settings
from omoi_os.services.database import DatabaseService
from omoi_os.services.trajectory_context import TrajectoryContext

settings = get_app_settings()
db = DatabaseService(settings.database.url)
trajectory = TrajectoryContext(db)

# Test with a known sandbox_id (get one from running sandbox task)
# sandbox_id = 'your-sandbox-id-here'
# result = trajectory.get_sandbox_id_for_agent(sandbox_id)
# print(f'Result: {result}')
"
```

---

### 5. Agent Output Collector Sandbox Test

**Purpose**: Verify `get_sandbox_id_for_agent()` works correctly for collecting sandbox agent outputs.

**Key Fix**: Same as trajectory context - checks if ID is itself a sandbox_id.

---

## Full Integration Test Sequence

### Step-by-Step E2E Test

1. **Start the API server** (if testing locally):
   ```bash
   cd backend
   uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 18000 --reload
   ```

2. **Start the orchestrator worker** (separate terminal):
   ```bash
   cd backend
   ORCHESTRATOR_ENABLED=true DAYTONA_SANDBOX_EXECUTION=true uv run python -m omoi_os.workers.orchestrator_worker
   ```

3. **Run the E2E sandbox spawn test**:
   ```bash
   cd backend
   uv run python scripts/test_api_sandbox_spawn.py
   ```

4. **Monitor sandbox events in database**:
   ```sql
   -- Connect to Railway PostgreSQL and check
   SELECT id, sandbox_id, event_type, created_at
   FROM sandbox_events
   ORDER BY created_at DESC
   LIMIT 20;
   ```

5. **Check task has sandbox_id set**:
   ```sql
   SELECT id, status, sandbox_id, assigned_agent_id
   FROM tasks
   WHERE sandbox_id IS NOT NULL
   ORDER BY created_at DESC
   LIMIT 5;
   ```

---

## Testing Checklist (From SANDBOX_MIGRATION_TASK.md)

After running the tests, verify:

- [ ] **Sandbox task can submit results without ValueError**
  - Test: E2E spawn test completes with task status = "completed"

- [ ] **Guardian can detect sandbox tasks in monitoring loop**
  - Test: `_get_active_sandbox_agent_ids()` returns sandbox IDs

- [ ] **Guardian can send interventions to sandbox tasks**
  - Test: Guardian integration test passes

- [ ] **Trajectory analysis finds sandbox agent's current task**
  - Test: `get_sandbox_id_for_agent()` returns correct sandbox_id

- [ ] **Monitor metrics include sandbox task completions**
  - Test: Task completion events recorded in sandbox_events table

- [ ] **Agent output collector returns events for sandbox agents**
  - Test: Events can be retrieved via `/api/v1/sandboxes/{id}/events`

- [ ] **Collaboration messages reach sandbox agents**
  - Test: Messages can be POSTed and retrieved via sandbox message API

- [ ] **Task retry works for sandbox tasks**
  - Test: Retry clears `sandbox_id` (not `assigned_agent_id`)

- [ ] **Diagnostic recovery notifications include sandbox tasks**
  - Test: Diagnostic service can find and notify sandbox tasks

---

## New Test Script: Sandbox Monitoring E2E

Create this test to verify monitoring systems work with active sandbox tasks:

**File**: `backend/scripts/test_sandbox_monitoring_e2e.py`

```python
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

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from omoi_os.config import get_app_settings
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.monitoring_loop import MonitoringLoop, MonitoringConfig
from omoi_os.services.intelligent_guardian import IntelligentGuardian
from omoi_os.services.conductor import ConductorService
from omoi_os.services.trajectory_context import TrajectoryContext
from omoi_os.services.agent_output_collector import AgentOutputCollector
from omoi_os.models.task import Task


def main():
    print("=" * 70)
    print("SANDBOX MONITORING E2E TEST")
    print("=" * 70)

    settings = get_app_settings()
    db = DatabaseService(settings.database.url)
    event_bus = EventBusService(settings.redis.url)

    print(f"\nDatabase: {settings.database.url[:50]}...")
    print(f"Redis: {settings.redis.url[:30]}...")

    # Step 1: Check for running sandbox tasks
    print("\n[1/6] Checking for running sandbox tasks...")
    with db.get_session() as session:
        sandbox_tasks = session.query(Task).filter(
            Task.sandbox_id.isnot(None),
            Task.status.in_(["running", "assigned"])
        ).all()

        if not sandbox_tasks:
            print("   ⚠️  No running sandbox tasks found.")
            print("   Run test_api_sandbox_spawn.py first to create one.")
            # Continue anyway to test other functionality
        else:
            print(f"   ✅ Found {len(sandbox_tasks)} sandbox task(s)")
            for task in sandbox_tasks:
                print(f"      - Task {str(task.id)[:8]}... | Sandbox: {task.sandbox_id[:20]}...")

    # Step 2: Test MonitoringLoop sandbox detection
    print("\n[2/6] Testing MonitoringLoop._get_active_sandbox_agent_ids()...")
    try:
        config = MonitoringConfig(
            guardian_interval_seconds=60,
            conductor_interval_seconds=300,
            auto_steering_enabled=False
        )
        monitoring_loop = MonitoringLoop(db, event_bus, config)
        sandbox_ids = monitoring_loop._get_active_sandbox_agent_ids()
        print(f"   ✅ Found {len(sandbox_ids)} active sandbox IDs")
        for sid in sandbox_ids[:3]:  # Show first 3
            print(f"      - {sid[:30]}...")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Step 3: Test Guardian sandbox detection
    print("\n[3/6] Testing IntelligentGuardian._get_active_sandbox_agent_ids()...")
    try:
        guardian = IntelligentGuardian(db)
        sandbox_ids = guardian._get_active_sandbox_agent_ids()
        print(f"   ✅ Found {len(sandbox_ids)} active sandbox IDs via Guardian")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Step 4: Test Conductor sandbox detection
    print("\n[4/6] Testing ConductorService._get_active_sandbox_agent_ids()...")
    try:
        conductor = ConductorService(db)
        sandbox_ids = conductor._get_active_sandbox_agent_ids()
        print(f"   ✅ Found {len(sandbox_ids)} active sandbox IDs via Conductor")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Step 5: Test TrajectoryContext.get_sandbox_id_for_agent()
    print("\n[5/6] Testing TrajectoryContext.get_sandbox_id_for_agent()...")
    try:
        trajectory = TrajectoryContext(db)
        with db.get_session() as session:
            sandbox_task = session.query(Task).filter(
                Task.sandbox_id.isnot(None)
            ).first()

            if sandbox_task and sandbox_task.sandbox_id:
                # Test: passing sandbox_id should return itself
                result = trajectory.get_sandbox_id_for_agent(sandbox_task.sandbox_id)
                if result == sandbox_task.sandbox_id:
                    print(f"   ✅ get_sandbox_id_for_agent() correctly returns sandbox_id")
                else:
                    print(f"   ❌ Expected {sandbox_task.sandbox_id}, got {result}")
            else:
                print("   ⚠️  No sandbox tasks to test with")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Step 6: Test AgentOutputCollector.get_sandbox_id_for_agent()
    print("\n[6/6] Testing AgentOutputCollector.get_sandbox_id_for_agent()...")
    try:
        collector = AgentOutputCollector(db, event_bus)
        with db.get_session() as session:
            sandbox_task = session.query(Task).filter(
                Task.sandbox_id.isnot(None)
            ).first()

            if sandbox_task and sandbox_task.sandbox_id:
                result = collector.get_sandbox_id_for_agent(sandbox_task.sandbox_id)
                if result == sandbox_task.sandbox_id:
                    print(f"   ✅ get_sandbox_id_for_agent() correctly returns sandbox_id")
                else:
                    print(f"   ❌ Expected {sandbox_task.sandbox_id}, got {result}")
            else:
                print("   ⚠️  No sandbox tasks to test with")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    print("\n" + "=" * 70)
    print("SANDBOX MONITORING E2E TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
```

---

## Running All Tests

### Quick Validation
```bash
cd backend

# 1. Unit tests for sandbox integration
uv run pytest tests/integration/sandbox/ -v

# 2. Guardian unit tests
uv run pytest tests/test_guardian.py -v

# 3. Monitoring smoke test
uv run python scripts/test_intelligent_monitoring.py
```

### Full E2E Validation
```bash
cd backend

# 1. E2E sandbox spawn (creates real sandbox)
uv run python scripts/test_api_sandbox_spawn.py

# 2. Monitoring E2E (validates monitoring detects sandbox)
uv run python scripts/test_sandbox_monitoring_e2e.py
```

---

## Troubleshooting

### Task Not Picked Up
- Check `ORCHESTRATOR_ENABLED=true` in environment
- Check `DAYTONA_SANDBOX_EXECUTION=true` in environment
- Verify orchestrator worker is running

### Sandbox Events Not Appearing
- Check `CALLBACK_URL` points to correct API endpoint
- Verify API is accessible from Daytona sandboxes (use Railway URL, not localhost)

### Guardian Can't Find Sandbox Tasks
- Verify the fix in `_get_active_sandbox_agent_ids()` is deployed
- Check that tasks have `sandbox_id` set (not `assigned_agent_id`)

### TrajectoryContext Returns None
- Verify the fix in `get_sandbox_id_for_agent()` checks sandbox_id first
- Ensure task status is "running" or "assigned"

---

## Related Documentation

- [SANDBOX_MIGRATION_TASK.md](../implementation/sandbox/SANDBOX_MIGRATION_TASK.md) - Full list of migration fixes
- [test_api_sandbox_spawn.py](../../backend/scripts/test_api_sandbox_spawn.py) - E2E spawn test
- [test_guardian_sandbox_integration.py](../../backend/tests/integration/sandbox/test_guardian_sandbox_integration.py) - Guardian tests
