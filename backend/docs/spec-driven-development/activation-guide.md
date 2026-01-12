# Activation Guide - Spec-Driven Development

**Created**: 2025-01-11
**Status**: Reference
**Purpose**: How to activate each workflow path (current state)

---

## Path 1: Prompt Injection (Agent-Driven)

### How to Activate

**Via Command Page (Frontend)**:
1. Go to Command page
2. Select "spec_driven" workflow mode
3. Enter title and description
4. Submit

**What Happens**:
- Ticket created with `workflow_mode: "spec_driven"`
- Task created with `execution_config: { require_spec_skill: true }`
- Sandbox spawned with `REQUIRE_SPEC_SKILL=true` env var
- Agent receives `spec_driven_dev_prompt` in system prompt
- Agent manually creates specs by following prompt instructions

**Direct API**:
```bash
# Create ticket with spec_driven mode
curl -X POST http://localhost:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My feature idea",
    "description": "Detailed description...",
    "project_id": "<project-uuid>",
    "workflow_mode": "spec_driven",
    "phase_id": "PHASE_INITIAL",
    "priority": "MEDIUM"
  }'
```

### Verification

Check that prompt injection happened:
```python
# In claude_sandbox_worker.py logs, look for:
# "EXPLORATION MODE: Injecting spec-driven development prompt"
```

---

## Path 2: SpecStateMachine (System-Driven)

### How to Activate

**Via API (Recommended)**:

```bash
# Step 1: Create a spec
curl -X POST http://localhost:8000/api/v1/specs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My feature spec",
    "description": "What I want to build...",
    "project_id": "<project-uuid>"
  }'
# Response: { "id": "<spec-uuid>", ... }

# Step 2: Execute the spec
curl -X POST http://localhost:8000/api/v1/specs/<spec-uuid>/execute \
  -H "Content-Type: application/json" \
  -d '{
    "working_directory": "/path/to/project"
  }'
# Response: { "status": "started", "current_phase": "explore" }
```

**What Happens**:
- Spec status updated to "executing"
- `run_spec_state_machine()` called in background
- State machine runs phases: EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC
- Each phase has evaluator (quality gate)
- Progress saved to database

### Monitoring Progress

```bash
# Get spec details (includes current_phase, progress)
curl http://localhost:8000/api/v1/specs/<spec-uuid>

# Get execution status
curl http://localhost:8000/api/v1/specs/<spec-uuid>/execution-status

# Get phase data (outputs from each phase)
curl http://localhost:8000/api/v1/specs/<spec-uuid>/phase-data
```

### Via Sandbox Environment (Manual/Testing)

Set environment variables before starting sandbox:
```bash
export SPEC_ID="<spec-uuid>"
export SPEC_PHASE="explore"  # or requirements/design/tasks/sync
export PROJECT_ID="<project-uuid>"
export EXECUTION_MODE="exploration"
export REQUIRE_SPEC_SKILL="true"

# Run sandbox worker
python -m omoi_os.workers.claude_sandbox_worker
```

Worker will detect `SPEC_ID` + `SPEC_PHASE` and call `_run_spec_state_machine()`.

---

## Comparison: Which to Use?

| Scenario | Recommended Path |
|----------|------------------|
| New project, exploring from scratch | Prompt Injection |
| Have clear requirements already | SpecStateMachine |
| Want checkpoints/recovery | SpecStateMachine |
| Want automatic phase progression | SpecStateMachine |
| Want agent to discover requirements | Prompt Injection |
| Testing state machine | SpecStateMachine via API |

---

## Current Limitations

### Prompt Injection Path
- No automatic spec creation
- No phase tracking in database
- No checkpoint/recovery
- Agent may drift from spec format

### SpecStateMachine Path
- Requires pre-existing spec_id
- No UI to create and execute in one step
- Must use API directly (no command page integration)

### Both Paths
- No approval gates in UI (phases auto-progress)
- No real-time progress in frontend
- No WebSocket updates for phase changes

---

## Testing Commands

### Test Prompt Injection Works

```bash
# 1. Create spec_driven ticket
curl -X POST http://localhost:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test spec driven",
    "description": "Testing prompt injection",
    "project_id": "<project-uuid>",
    "workflow_mode": "spec_driven",
    "phase_id": "PHASE_INITIAL",
    "priority": "LOW"
  }'

# 2. Check task was created with execution_config
curl http://localhost:8000/api/v1/tasks?ticket_id=<ticket-uuid>
# Look for: "execution_config": { "require_spec_skill": true }

# 3. Check sandbox logs for prompt injection
# Look for: "Injecting spec-driven development prompt"
```

### Test State Machine Works

```bash
# 1. Create spec directly
SPEC_ID=$(curl -s -X POST http://localhost:8000/api/v1/specs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "State machine test",
    "description": "Testing state machine execution",
    "project_id": "<project-uuid>"
  }' | jq -r '.id')

echo "Created spec: $SPEC_ID"

# 2. Execute spec
curl -X POST "http://localhost:8000/api/v1/specs/$SPEC_ID/execute" \
  -H "Content-Type: application/json" \
  -d '{}'

# 3. Monitor progress
watch -n 5 "curl -s http://localhost:8000/api/v1/specs/$SPEC_ID | jq '.status, .current_phase, .progress'"
```

---

## Debugging

### Logs to Watch

```bash
# Prompt injection
grep "spec-driven" /var/log/omoios/sandbox.log
grep "EXPLORATION MODE" /var/log/omoios/sandbox.log

# State machine
grep "SPEC STATE MACHINE" /var/log/omoios/sandbox.log
grep "SpecStateMachine" /var/log/omoios/worker.log
```

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| No prompt injection | `REQUIRE_SPEC_SKILL` not set | Check `workflow_mode: "spec_driven"` in ticket |
| State machine not starting | No `SPEC_ID` env var | Create spec first, use API |
| Phase stuck | Evaluator rejection | Check phase data for errors |
| Sandbox crash | Missing DATABASE_URL | Ensure env vars passed to sandbox |
