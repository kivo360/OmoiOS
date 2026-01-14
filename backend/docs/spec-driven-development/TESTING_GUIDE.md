# Testing Guide for Spec-Driven Development

**Created**: 2025-01-13
**Status**: Active
**Purpose**: Comprehensive guide for testing spec-driven development implementation

---

## Overview

This guide documents **how to test every aspect of spec-driven development** at each phase of implementation. Testing is organized into:

1. **Unit Tests** - Fast, isolated tests for individual components
2. **Integration Tests** - Multi-component tests with real database
3. **API Tests** - Manual/scripted endpoint verification
4. **UI/Browser Tests** - Claude browser extension prompts for verifying frontend
5. **Local Sandbox Tests** - Testing state machine execution locally

---

## Quick Reference

### Run Tests by Type

```bash
# All spec-related unit tests
uv run pytest tests/unit/workers/test_spec_state_machine.py -v

# All spec-related integration tests
uv run pytest tests/integration/test_spec*.py -v

# All spec E2E tests
uv run pytest tests/e2e/test_spec*.py -v

# Full spec test suite (all types)
uv run pytest -k "spec" -v

# With coverage
uv run pytest -k "spec" --cov=omoi_os --cov-report=html
```

### Test File Locations

| Component | Unit Test | Integration Test | E2E Test |
|-----------|-----------|------------------|----------|
| SpecStateMachine | `tests/unit/workers/test_spec_state_machine.py` | `tests/integration/sandbox/test_spec_state_machine_local.py` | `tests/e2e/test_spec_workflow_e2e.py` |
| SpecTaskExecutionService | - | `tests/integration/test_spec_task_execution_integration.py` | `tests/integration/test_spec_task_execution_e2e.py` |
| SpecSyncService | `tests/unit/services/test_spec_dedup.py` | `tests/integration/test_spec_sync_integration.py` | - |
| API Routes | - | `tests/integration/test_spec_acceptance_validator_integration.py` | - |

---

## Phase-by-Phase Testing Checklist

### Phase 1: Wire State Machine to Bridge

**What We're Testing**: After SYNC phase, `SpecTaskExecutionService.execute_spec_tasks()` is called.

#### Unit Tests (Already Exist)

```bash
# Test state machine phase transitions
uv run pytest tests/unit/workers/test_spec_state_machine.py::TestSpecPhase -v

# Test phase order
uv run pytest tests/unit/workers/test_spec_state_machine.py::TestSpecStateMachine::test_phase_order -v

# Test sync phase execution
uv run pytest tests/unit/workers/test_spec_state_machine.py::TestSpecStateMachinePhaseExecution -v
```

#### New Tests Needed for Phase 1

Add to `tests/integration/test_spec_sync_integration.py`:

```python
@pytest.mark.asyncio
async def test_sync_phase_calls_execute_spec_tasks():
    """Test that SYNC phase triggers SpecTaskExecutionService."""
    # This test verifies the wiring in IMPLEMENTATION_ROADMAP.md Task 1.1
    pass
```

#### Manual API Verification

```bash
# 1. Create a spec via API
curl -X POST http://localhost:18000/api/v1/specs \
  -H "Content-Type: application/json" \
  -d '{"project_id": "YOUR_PROJECT_ID", "title": "Test Spec", "description": "Testing the flow"}'

# 2. Trigger execution (after TASKS phase is complete)
curl -X POST http://localhost:18000/api/v1/specs/{spec_id}/execute

# 3. Check if tickets were created
curl http://localhost:18000/api/v1/tickets?project_id=YOUR_PROJECT_ID
```

---

### Phase 2: User Ownership

**What We're Testing**: Tickets created from specs have `user_id` set and appear on board view.

#### Prerequisites

Run migration first:
```bash
uv run alembic upgrade head
```

#### API Tests

```bash
# Test with authenticated user
curl -X POST http://localhost:18000/api/v1/specs \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -d '{"project_id": "YOUR_PROJECT_ID", "title": "Auth Test Spec"}'

# Verify user_id is set
curl http://localhost:18000/api/v1/specs/{spec_id} \
  -H "Cookie: session=YOUR_SESSION_COOKIE"

# Check board view shows tickets
curl http://localhost:18000/api/v1/board/view?project_id=YOUR_PROJECT_ID \
  -H "Cookie: session=YOUR_SESSION_COOKIE"
```

#### New Tests Needed

```python
# tests/integration/test_spec_user_ownership.py
@pytest.mark.asyncio
async def test_spec_has_user_id_when_created_by_authenticated_user():
    """Verify Spec.user_id is populated from authenticated user."""
    pass

@pytest.mark.asyncio
async def test_tickets_from_spec_inherit_user_id():
    """Verify Tickets created from SpecTasks have user_id."""
    pass

@pytest.mark.asyncio
async def test_tickets_visible_on_board_view():
    """Verify tickets with user_id appear on board view API."""
    pass
```

---

### Phase 3: Event Reporting

**What We're Testing**: Real-time events are emitted during state machine execution.

#### Test EventReporter Integration

```bash
# Run existing EventReporter tests
uv run pytest tests/unit/workers/test_sandbox_worker.py -k "event" -v
```

#### New Tests Needed

```python
# tests/integration/test_spec_events.py
@pytest.mark.asyncio
async def test_spec_phase_started_event_emitted():
    """Verify spec.phase_started event is published."""
    pass

@pytest.mark.asyncio
async def test_spec_phase_completed_event_emitted():
    """Verify spec.phase_completed event is published with eval_score."""
    pass

@pytest.mark.asyncio
async def test_events_visible_via_api():
    """Verify GET /api/v1/specs/{spec_id}/events returns events."""
    pass
```

---

## Local Sandbox Testing

### Running State Machine Locally

Use the isolated worker test script:

```bash
cd backend

# Set environment
set -a && source .env.local && set +a

# Run state machine in isolation (no real sandbox)
uv run python scripts/test_spec_worker_isolated.py --spec-id YOUR_SPEC_ID

# Or with a local workspace directory
uv run python scripts/test_spec_worker_isolated.py \
  --spec-id YOUR_SPEC_ID \
  --workspace /path/to/local/repo
```

### Testing with Real Daytona Sandbox

```bash
# Spawn a sandbox for spec execution
uv run python scripts/test_api_sandbox_spawn.py \
  --mode spec \
  --spec-id YOUR_SPEC_ID \
  --project-id YOUR_PROJECT_ID

# Monitor sandbox events
uv run python scripts/test_websocket_client.py --sandbox-id SANDBOX_ID
```

### Checkpoint Verification

After running state machine locally, verify checkpoints:

```bash
# Check checkpoint files were created
ls -la /path/to/workspace/.omoi_os/checkpoints/
cat /path/to/workspace/.omoi_os/checkpoints/state.json

# Check phase data files
ls -la /path/to/workspace/.omoi_os/phase_data/
cat /path/to/workspace/.omoi_os/phase_data/explore.json
```

---

## UI/Browser Testing Prompts

Use these prompts with **Claude browser extension** to verify frontend functionality.

### Prompt 1: Verify Spec List Page

```
I'm testing the spec-driven development feature. Please help me verify the spec list page works correctly.

1. Navigate to /projects/{project_id}/specs
2. Check if specs are listed with their title, status, and current_phase
3. Verify clicking on a spec navigates to the detail page
4. Check if the "Create Spec" button exists and is clickable

Report any errors in the console or issues with the UI.
```

### Prompt 2: Verify Spec Detail Page Tabs

```
I'm on the spec detail page at /projects/{project_id}/specs/{specId}. Please verify:

1. All tabs are visible: Requirements, Design, Tasks, Execution
2. Click through each tab and confirm content loads without errors
3. On the Execution tab, check if progress metrics are displayed
4. Verify the sidebar shows spec metadata (status, phase, created_at)

Report any loading errors, console errors, or missing UI elements.
```

### Prompt 3: Verify Ticket Visibility After Spec Sync

```
After completing a spec through all phases, I need to verify tickets appear correctly:

1. Navigate to /projects/{project_id}/board
2. Check if tickets from the spec appear in the kanban board
3. Verify each ticket shows: title, priority, phase
4. Check if clicking a ticket opens the ticket detail view
5. Verify the ticket count matches the number of SpecTasks

If tickets are NOT visible, check:
- Does the user have permission to view the board?
- Is user_id set on the tickets? (Check network tab for API response)
```

### Prompt 4: Verify Real-Time Event Updates

```
I want to test real-time updates during spec execution. Please:

1. Navigate to a spec in "executing" status at /projects/{project_id}/specs/{specId}
2. Click the "Execution" tab
3. Monitor if progress updates appear without manual refresh
4. Check the console for WebSocket connections or polling intervals
5. Verify phase transitions are reflected in the UI

Report the polling interval being used and any connection issues.
```

### Prompt 5: Full End-to-End Flow Test

```
Help me test the complete spec-driven workflow:

1. Go to /command and verify the command palette is available
2. Enter a feature request like "Add user authentication to the API"
3. Select spec-driven mode and choose a project
4. Monitor the spec creation and verify redirect to spec detail page
5. Check each phase tab as the spec progresses:
   - EXPLORE tab should show project analysis
   - REQUIREMENTS tab should show EARS-format requirements
   - DESIGN tab should show architecture/data model
   - TASKS tab should show work breakdown
6. After SYNC completes, navigate to the board and verify tickets exist
7. Open one ticket and verify it links back to the spec

Document the complete flow with screenshots and any errors encountered.
```

---

## Database State Verification

### Check Spec Records

```sql
-- Get spec with all related data
SELECT
    s.id, s.title, s.status, s.current_phase,
    s.user_id,
    COUNT(DISTINCT sr.id) as requirement_count,
    COUNT(DISTINCT st.id) as task_count
FROM specs s
LEFT JOIN spec_requirements sr ON sr.spec_id = s.id
LEFT JOIN spec_tasks st ON st.spec_id = s.id
WHERE s.id = 'YOUR_SPEC_ID'
GROUP BY s.id;

-- Check SpecTask -> Ticket linkage
SELECT
    st.id as spec_task_id,
    st.title as spec_task_title,
    t.id as ticket_id,
    t.title as ticket_title,
    t.user_id
FROM spec_tasks st
LEFT JOIN tickets t ON t.spec_task_id = st.id
WHERE st.spec_id = 'YOUR_SPEC_ID';

-- Verify tickets have user_id
SELECT id, title, user_id, spec_id, spec_task_id
FROM tickets
WHERE spec_id = 'YOUR_SPEC_ID';
```

### Check Events

```sql
-- Get spec-related events
SELECT
    event_type,
    event_data->>'phase' as phase,
    event_data->>'eval_score' as eval_score,
    created_at
FROM sandbox_events
WHERE spec_id = 'YOUR_SPEC_ID'
ORDER BY created_at DESC
LIMIT 20;
```

---

## Test Data Setup

### Create Test Project

```bash
# Via API
curl -X POST http://localhost:18000/api/v1/projects \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -d '{"name": "Test Project for Specs", "description": "Testing spec workflow"}'
```

### Create Test Spec with Phase Data

```python
# scripts/setup_test_spec.py
"""Create a test spec with phase data for testing sync."""

import asyncio
from omoi_os.services.database import DatabaseService
from omoi_os.models.spec import Spec

async def create_test_spec():
    db = DatabaseService()

    async with db.get_async_session() as session:
        spec = Spec(
            project_id="YOUR_PROJECT_ID",
            user_id="YOUR_USER_ID",  # Important for Phase 2!
            title="Test Spec for Sync",
            description="Testing SpecTask -> Ticket flow",
            status="executing",
            current_phase="sync",
            phase_data={
                "explore": {"project_type": "web_api"},
                "requirements": {
                    "requirements": [
                        {
                            "id": "REQ-001",
                            "title": "User Login",
                            "condition": "WHEN user submits credentials",
                            "action": "THE SYSTEM SHALL authenticate",
                            "acceptance_criteria": ["Returns JWT", "Logs attempt"]
                        }
                    ]
                },
                "design": {"architecture": "Layered"},
                "tasks": {
                    "tasks": [
                        {
                            "id": "TASK-001",
                            "title": "Implement JWT Auth",
                            "description": "Create JWT token generation",
                            "requirement_id": "REQ-001",
                            "priority": "high"
                        }
                    ]
                }
            }
        )
        session.add(spec)
        await session.commit()
        print(f"Created spec: {spec.id}")

if __name__ == "__main__":
    asyncio.run(create_test_spec())
```

---

## Troubleshooting

### Tests Fail with "Spec not found"

1. Check database connection: `uv run python -c "from omoi_os.services.database import DatabaseService; print('OK')"`
2. Verify migrations ran: `uv run alembic current`
3. Check spec exists: Query database directly

### Tickets Not Appearing on Board

1. Check `user_id` on ticket: `SELECT user_id FROM tickets WHERE spec_id = ?`
2. Verify board API filters: Board view filters by `project_id` AND `user_id`
3. Check user permissions

### Events Not Being Emitted

1. Verify EventReporter is passed to state machine
2. Check `CALLBACK_URL` env var in sandbox
3. Verify sandbox_events table exists
4. Check for errors in sandbox logs

### Phase Evaluator Failing

1. Check evaluator output: Evaluators log their scoring
2. Verify JSON extraction: State machine logs extracted JSON
3. Review retry prompt: Retry prompts include failure reasons

---

## Test Coverage Goals

| Component | Current Coverage | Target |
|-----------|-----------------|--------|
| SpecStateMachine | ~70% | 85% |
| SpecTaskExecutionService | ~60% | 80% |
| SpecSyncService | ~50% | 75% |
| SpecDeduplicationService | ~80% | 90% |
| API Routes | ~30% | 70% |

Run coverage report:
```bash
uv run pytest -k "spec" --cov=omoi_os --cov-report=html
open htmlcov/index.html
```

---

## Related Documentation

- [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) - Step-by-step implementation tasks
- [architecture.md](./architecture.md) - System architecture overview
- [data-flow-gap.md](./data-flow-gap.md) - SpecTask → Ticket data flow
- [ui-and-events.md](./ui-and-events.md) - Event reporting and UI updates
