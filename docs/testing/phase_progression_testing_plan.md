# Phase Progression Testing Plan

This document outlines how to test the phase progression hooks (Hook 1 + Hook 2) and related functionality.

## Overview

The phase progression system consists of:
- **Hook 1**: Auto-advance ticket when all phase tasks complete
- **Hook 2**: Auto-spawn next phase tasks when ticket enters new phase
- **Dynamic PRD**: Generate PRD for tickets without existing requirements

## Testing Approaches

### 1. Unit Tests (Service Layer)

Run the dedicated test script that exercises the core service methods:

```bash
cd backend && uv run python scripts/test_phase_progression_hooks.py
```

This tests:
- Phase completion detection
- Task spawning on phase transition
- Dynamic PRD generation
- Manual trigger methods
- Event subscription

### 2. API Debug Endpoints

The following endpoints are available for manual testing via API:

#### Check Phase Completion (Hook 1 Trigger)
```bash
# Check if a ticket is ready for phase advancement
curl -X POST http://localhost:8000/api/tickets/{ticket_id}/check-phase-completion \
  -H "Content-Type: application/json" \
  -H "Cookie: your-auth-cookie"
```

Response:
```json
{
  "ticket_id": "uuid",
  "current_phase": "PHASE_IMPLEMENTATION",
  "current_status": "building",
  "all_phase_tasks_complete": true,
  "advanced": true
}
```

#### Spawn Phase Tasks (Hook 2 Trigger)
```bash
# Manually spawn tasks for a phase
curl -X POST "http://localhost:8000/api/tickets/{ticket_id}/spawn-phase-tasks?phase_id=PHASE_IMPLEMENTATION" \
  -H "Content-Type: application/json" \
  -H "Cookie: your-auth-cookie"
```

Response:
```json
{
  "ticket_id": "uuid",
  "phase": "PHASE_IMPLEMENTATION",
  "tasks_spawned": 1
}
```

### 3. Local Agent Testing

You can test the full flow locally by running Claude Code against your local API:

#### Setup
1. Start the backend server locally:
   ```bash
   cd backend && uv run uvicorn omoi_os.main:app --reload --port 8000
   ```

2. Start the orchestrator worker:
   ```bash
   cd backend && uv run python -m omoi_os.workers.orchestrator_worker
   ```

3. In another terminal, run Claude Code with test prompts

#### Test Scenarios

**Scenario A: Task Completion → Phase Advance**
1. Create a ticket via API or UI
2. Create a task for the ticket's current phase
3. Complete the task
4. Verify Hook 1 fires and advances the ticket

**Scenario B: Phase Entry → Task Spawn**
1. Create a ticket in PHASE_BACKLOG
2. Advance it to PHASE_REQUIREMENTS
3. Verify Hook 2 spawns the appropriate tasks
4. Check if generate_prd task was created (if no PRD exists)

**Scenario C: Dynamic PRD Generation**
1. Create a ticket WITHOUT a PRD (no context.prd_url)
2. Move it to PHASE_REQUIREMENTS
3. Verify a generate_prd task is created
4. Complete the generate_prd task
5. Verify the ticket can proceed

### 4. Integration Test Script (API Calls)

Run the API-based integration test:

```bash
cd backend && uv run python scripts/test_phase_progression_api.py
```

This script:
- Creates test data via API
- Triggers hooks via debug endpoints
- Verifies expected behavior
- Cleans up test data

### 5. Full End-to-End Testing

#### Local Testing Flow
1. **Start services locally**:
   ```bash
   # Terminal 1: API server
   cd backend && uv run uvicorn omoi_os.main:app --reload

   # Terminal 2: Orchestrator worker
   cd backend && uv run python -m omoi_os.workers.orchestrator_worker

   # Terminal 3: Watch Redis events (optional)
   redis-cli PSUBSCRIBE "*"
   ```

2. **Create test ticket** with no PRD:
   ```bash
   curl -X POST http://localhost:8000/api/tickets \
     -H "Content-Type: application/json" \
     -d '{"title": "Test Feature", "description": "Test description", "project_id": "your-project-id"}'
   ```

3. **Move to PHASE_REQUIREMENTS**:
   ```bash
   curl -X PATCH http://localhost:8000/api/tickets/{ticket_id} \
     -H "Content-Type: application/json" \
     -d '{"phase_id": "PHASE_REQUIREMENTS", "status": "analyzing"}'
   ```

4. **Verify generate_prd task created**:
   ```bash
   curl http://localhost:8000/api/tasks?ticket_id={ticket_id}
   ```

5. **Simulate task completion**:
   ```bash
   curl -X PATCH http://localhost:8000/api/tasks/{task_id}/status \
     -H "Content-Type: application/json" \
     -d '{"status": "completed"}'
   ```

6. **Verify phase advancement**:
   ```bash
   curl http://localhost:8000/api/tickets/{ticket_id}
   ```

### 6. Sandbox Testing

Before sandbox deployment, verify locally that:
- [ ] All unit tests pass
- [ ] API endpoints respond correctly
- [ ] Event subscriptions are active
- [ ] Task spawning creates correct task types
- [ ] Phase advancement logic works

## Debugging Tips

### Check Event Bus Activity
```bash
# Subscribe to all Redis events
redis-cli PSUBSCRIBE "events:*"
```

### Check Task Queue
```bash
# View pending tasks
curl http://localhost:8000/api/v1/debug/tasks/pending

# View running tasks by org
curl http://localhost:8000/api/v1/debug/tasks/running/{org_id}

# Get task queue stats
curl http://localhost:8000/api/v1/debug/tasks/stats
```

### View Phase Gate Status
```bash
curl http://localhost:8000/api/v1/debug/tickets/{ticket_id}/phase-gate-status

# View tasks by phase for a ticket
curl http://localhost:8000/api/v1/debug/tickets/{ticket_id}/tasks-by-phase
```

### Agent Limit Status
```bash
# Get agent stats for an organization
curl http://localhost:8000/api/v1/debug/agents/{org_id}/stats
```

### Phase Progression Status
```bash
# Check phase progression service status
curl http://localhost:8000/api/v1/debug/phase-progression/status

# View initial tasks configuration
curl http://localhost:8000/api/v1/debug/phase-progression/initial-tasks
```

### System Health
```bash
# Full system health check
curl http://localhost:8000/api/v1/debug/health
```

### Event Bus Testing
```bash
# Get event bus status
curl http://localhost:8000/api/v1/debug/event-bus/status

# Publish test event
curl -X POST "http://localhost:8000/api/v1/debug/event-bus/test-publish?event_type=TEST_EVENT"
```

### Manual Hook Invocation
```bash
# Force check phase completion
curl -X POST http://localhost:8000/api/tickets/{ticket_id}/check-phase-completion

# Force spawn phase tasks
curl -X POST http://localhost:8000/api/tickets/{ticket_id}/spawn-phase-tasks
```

## Common Issues

### Hook 1 Not Firing
- Verify all tasks for the phase are marked "completed"
- Check phase gate requirements are met
- Ensure event bus subscription is active

### Hook 2 Not Spawning Tasks
- Verify phase has defined initial tasks in PHASE_INITIAL_TASKS
- Check ticket context for spec-defined tasks
- Ensure event bus is properly connected

### PRD Task Not Created
- Verify ticket has no prd_url, requirements_document, or spec_id in context
- Check phase gate artifacts for existing requirements

## Test Data Cleanup

The test scripts clean up after themselves, but if needed:

```sql
-- Delete test tasks
DELETE FROM tasks WHERE ticket_id IN (
  SELECT id FROM tickets WHERE title LIKE 'Test%'
);

-- Delete test tickets
DELETE FROM tickets WHERE title LIKE 'Test%';
```

## Next Steps

1. Run unit tests: `cd backend && uv run python scripts/test_phase_progression_hooks.py`
2. Run API tests: `cd backend && uv run python scripts/test_phase_progression_api.py`
3. Manual testing via API endpoints
4. Full local agent testing
5. Sandbox deployment and verification
