# Testing Phase Progression with Local Claude Code

This guide shows how to test the phase progression hooks with a real Claude Code agent running locally.

## The Connection Flow

```
Claude Code Agent (in sandbox or local)
    │
    ├── Calls MCP tool: update_task_status(task_id, "completed", result)
    │
    ▼
FastMCP Server (/mcp/update_task_status)
    │
    ├── Calls TaskQueueService.update_task_status()
    │
    ▼
TaskQueueService
    │
    ├── Updates task.status = "completed" in database
    ├── Publishes TASK_COMPLETED event to Redis
    │
    ▼
PhaseProgressionService (Hook 1)
    │
    ├── Receives TASK_COMPLETED event
    ├── Checks: Are ALL tasks in this phase complete?
    ├── If yes: Advances ticket to next phase
    │
    ▼
PhaseProgressionService (Hook 2)
    │
    ├── Receives ticket.status_transitioned event
    ├── Spawns tasks for the new phase
    │
    ▼
TaskQueueService
    │
    ├── New task is pending
    │
    ▼
Orchestrator Worker
    │
    ├── Picks up the new task
    ├── Assigns to next agent
```

## Local Testing Setup

### Prerequisites
1. PostgreSQL running with database
2. Redis running
3. Backend configured with database URL

### Step 1: Start the Backend API

```bash
cd backend
uv run uvicorn omoi_os.main:app --reload --port 8000
```

### Step 2: Start the Orchestrator Worker

```bash
cd backend
uv run python -m omoi_os.workers.orchestrator_worker
```

### Step 3: Watch Redis Events (Optional but Helpful)

```bash
redis-cli PSUBSCRIBE "events:*"
```

### Step 4: Create a Test Ticket

```bash
# Replace YOUR_PROJECT_ID with an actual project ID
curl -X POST http://localhost:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -H "Cookie: YOUR_AUTH_COOKIE" \
  -d '{
    "title": "Test Phase Progression",
    "description": "Testing automatic phase advancement",
    "project_id": "YOUR_PROJECT_ID",
    "phase_id": "PHASE_REQUIREMENTS",
    "force_create": true
  }'
```

Note the ticket ID from the response.

### Step 5: Check What Tasks Were Spawned

```bash
curl http://localhost:8000/api/v1/debug/tickets/TICKET_ID/tasks-by-phase \
  -H "Cookie: YOUR_AUTH_COOKIE"
```

You should see a `generate_prd` task (or other phase tasks) was created.

### Step 6: Simulate Agent Completing the Task

This is what Claude Code does when it finishes work:

```bash
# Get the task ID from Step 5
curl -X POST http://localhost:8000/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "update_task_status",
    "params": {
      "task_id": "TASK_ID",
      "status": "completed",
      "result": {"summary": "PRD generated successfully"}
    }
  }'
```

### Step 7: Watch What Happens

In your Redis subscriber terminal, you should see:
```
1) "pmessage"
2) "events:*"
3) "events:TASK_COMPLETED"
4) {"task_id": "...", "ticket_id": "...", ...}
```

Then check the ticket:
```bash
curl http://localhost:8000/api/v1/tickets/TICKET_ID \
  -H "Cookie: YOUR_AUTH_COOKIE"
```

If Hook 1 worked, the ticket should have advanced to the next phase.

Check for new tasks:
```bash
curl http://localhost:8000/api/v1/debug/tickets/TICKET_ID/tasks-by-phase \
  -H "Cookie: YOUR_AUTH_COOKIE"
```

If Hook 2 worked, new tasks should exist for the new phase.

## Testing with Actual Claude Code

### Option A: Run Claude Code in Terminal Against Local API

1. Configure Claude Code to use your local MCP server:
   ```
   MCP_URL=http://localhost:8000/mcp/
   ```

2. Start a Claude Code session with a task prompt:
   ```bash
   claude --task "Complete the generate_prd task for ticket TICKET_ID"
   ```

3. Claude Code will:
   - Call `get_task` to understand the task
   - Do the work
   - Call `update_task_status` with "completed"
   - This triggers the hooks!

### Option B: Use the Test Script with MCP Calls

Create a script that mimics what Claude Code does:

```python
#!/usr/bin/env python3
"""Simulate Claude Code completing a task."""

import requests
import sys

MCP_URL = "http://localhost:8000/mcp/"
API_URL = "http://localhost:8000/api/v1"

def call_mcp(method: str, params: dict):
    """Call an MCP method."""
    response = requests.post(
        f"{MCP_URL}call",
        json={"method": method, "params": params}
    )
    return response.json()

def main(task_id: str):
    # 1. Get the task (what Claude Code does first)
    print(f"Getting task {task_id}...")
    result = call_mcp("get_task", {"task_id": task_id})
    print(f"Task: {result}")

    # 2. Simulate doing work (Claude Code would actually do this)
    print("Simulating work...")

    # 3. Mark task complete (this triggers Hook 1!)
    print("Marking task complete...")
    result = call_mcp("update_task_status", {
        "task_id": task_id,
        "status": "completed",
        "result": {"summary": "Work completed by test agent"}
    })
    print(f"Result: {result}")

    # 4. Check if ticket advanced
    # (You'd need auth for this, or use debug endpoints)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_agent_flow.py <task_id>")
        sys.exit(1)
    main(sys.argv[1])
```

## What Success Looks Like

When everything works, you'll see this sequence in the logs:

```
[API] POST /tickets - Ticket created (PHASE_REQUIREMENTS)
[Hook 2] Spawning tasks for PHASE_REQUIREMENTS
[Hook 2] Created generate_prd task

[MCP] update_task_status(task_id, "completed")
[TaskQueue] Publishing TASK_COMPLETED event

[Hook 1] Received TASK_COMPLETED for task X
[Hook 1] Checking if all PHASE_REQUIREMENTS tasks complete...
[Hook 1] All tasks complete, checking phase gate...
[Hook 1] Gate passed, advancing ticket to PHASE_DESIGN

[Hook 2] Received ticket.status_transitioned event
[Hook 2] Spawning tasks for PHASE_DESIGN
[Hook 2] Created create_design_document task
```

## Debugging If It Doesn't Work

### Check 1: Is the Event Bus Connected?
```bash
curl http://localhost:8000/api/v1/debug/event-bus/status
```

### Check 2: Are Events Being Published?
Watch Redis:
```bash
redis-cli PSUBSCRIBE "events:*"
```

Then complete a task and see if the event appears.

### Check 3: Is the Phase Progression Service Active?
```bash
curl http://localhost:8000/api/v1/debug/phase-progression/status
```

Should show `active: true` and `workflow_orchestrator_set: true`.

### Check 4: Are Tasks in the Right Phase?
```bash
curl http://localhost:8000/api/v1/debug/tickets/TICKET_ID/tasks-by-phase
```

### Check 5: Does the Phase Gate Pass?
```bash
curl http://localhost:8000/api/v1/debug/tickets/TICKET_ID/phase-gate-status
```

Shows if the ticket can advance and what's missing.
