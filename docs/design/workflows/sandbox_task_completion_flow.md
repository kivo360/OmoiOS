# Sandbox Task Completion and Phase Flow Design

**Created**: 2025-01-22
**Status**: In Progress
**Purpose**: Define how sandboxes execute tasks, signal completion, update acceptance criteria, and trigger phase transitions
**Related**: [Phasor System](./phasor_system.md), [PhaseManager Service](../../../backend/omoi_os/services/phase_manager.py)

---

## Overview

This document tracks the design and implementation of the complete flow from task execution in sandboxes to automatic phase transitions and acceptance criteria updates.

**Two Sandbox Systems**:
1. **spec-sandbox** (`subsystems/spec-sandbox/`): Generates specs with phases EXPLORE → PRD → REQUIREMENTS → DESIGN → TASKS → SYNC
2. **Claude Sandbox Worker** (`backend/omoi_os/workers/continuous_sandbox_worker.py`): Executes implementation tasks

Both systems need to communicate task completion back to the backend and update UI state.

---

## Progress Tracker

### Completed

- [x] E2E test script created and passing (`backend/scripts/test_e2e_phase_flow.py`)
- [x] PhaseManager event handlers verified working
- [x] TASK_COMPLETED events correctly trigger phase transitions
- [x] Tickets transition from BACKLOG → IMPLEMENTATION → DONE automatically
- [x] Explored Claude sandbox worker completion signal pattern

### In Progress

- [ ] Design document for task completion and phase flow (this document)
- [ ] Define completion signal patterns for acceptance criteria updates
- [ ] Document API endpoints sandbox needs to call at runtime

### To Do

- [ ] Implement acceptance criteria update endpoint
- [ ] Add acceptance criteria status to spec dashboard UI
- [ ] Create sandbox context pulling mechanism
- [ ] Test end-to-end flow with real sandbox execution

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SPEC CREATION FLOW                                 │
│                        (spec-sandbox subsystem)                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SpecStateMachine executes phases:                                          │
│  EXPLORE → PRD → REQUIREMENTS → DESIGN → TASKS → SYNC                       │
│                                                                              │
│  Outputs:                                                                    │
│  - Requirements (EARS format with acceptance criteria)                       │
│  - Design documents                                                          │
│  - SpecTasks (individual implementation units)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TASK EXECUTION FLOW                                  │
│                    (Claude Sandbox Worker)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Claude Agent in sandbox:                                                    │
│  1. Pulls context from API (requirements, design, task details)              │
│  2. Executes implementation work                                             │
│  3. Signals completion via "TASK_COMPLETE" string (2x consecutive)           │
│  4. Git validation runs (clean, pushed, PR created)                          │
│  5. Reports task-complete to backend API                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE TRANSITION FLOW                                │
│                         (PhaseManager Service)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Backend receives TASK_COMPLETED event:                                      │
│  1. TaskQueueService updates task status                                     │
│  2. EventBusService publishes TASK_COMPLETED                                 │
│  3. PhaseManager._handle_task_completed() receives event                     │
│  4. For implement_feature tasks: move_to_done(ticket_id)                     │
│  5. For other tasks: check_and_advance(ticket_id)                            │
│  6. UI updates automatically via polling/websocket                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Current Completion Signal Pattern (Claude Sandbox Worker)

**File**: `backend/omoi_os/workers/continuous_sandbox_worker.py` (lines 625-720)

```python
# Check for completion signal
output_text = "\n".join(output) if output else ""
if config.completion_signal in output_text:  # Default: "TASK_COMPLETE"
    state.completion_signal_count += 1

    if config.auto_validate:
        await self._run_validation()  # Git validation
else:
    state.completion_signal_count = 0  # Reset on non-signal response
```

**Key Points**:
- Completion signal: `"TASK_COMPLETE"` string in output
- Threshold: 2 consecutive detections (prevents false positives)
- After threshold: runs git validation (`_run_validation()`)
- Git validation checks: clean working directory, code pushed, PR created

**Validation Logic** (lines 692-769):
```python
async def _run_validation(self):
    git_status = check_git_status(config.cwd)

    state.code_committed = git_status["is_clean"]
    state.code_pushed = git_status["is_pushed"]
    state.pr_created = git_status["has_pr"]
    state.tests_passed = git_status["tests_passed"]

    # Research tasks (no code changes) auto-pass
    is_research_task = (
        git_status["is_clean"] and
        git_status["is_pushed"] and
        git_status.get("branch_name") in ("main", "master", None)
    )
```

---

## API Endpoints for Sandbox Communication

### Existing Endpoints (Sandbox → Backend)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/sandboxes/{sandbox_id}/events` | POST | Report events (EventReporter) |
| `/api/v1/sandboxes/{sandbox_id}/task-complete` | POST | Signal task completion |
| `/api/v1/sandboxes/{sandbox_id}/messages` | GET | Poll for messages (MessagePoller) |
| `/api/v1/sandboxes/{sandbox_id}/heartbeat` | POST | Keep-alive heartbeat |

### Proposed Endpoints (Context Pulling)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/tasks/{task_id}/context` | GET | Pull full task context for sandbox |
| `/api/v1/specs/{spec_id}/requirements` | GET | Get requirements with acceptance criteria |
| `/api/v1/specs/{spec_id}/design` | GET | Get design documents |
| `/api/v1/requirements/{req_id}/criteria/{criteria_id}` | PATCH | Update acceptance criteria status |

---

## Acceptance Criteria Update Flow

### Current State

- Requirements with acceptance criteria are stored in the spec
- Spec dashboard shows requirements with checkboxes
- No mechanism for sandbox to update individual criteria as "met"

### Proposed Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. Sandbox pulls task context at start                                      │
│     GET /api/v1/tasks/{task_id}/context                                      │
│                                                                              │
│     Response includes:                                                       │
│     - Task description                                                       │
│     - Linked requirements with acceptance criteria                           │
│     - Design references                                                      │
│     - Ticket context                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. Sandbox executes task, marking criteria as met                           │
│                                                                              │
│     As work progresses, sandbox calls:                                       │
│     PATCH /api/v1/requirements/{req_id}/criteria/{criteria_id}               │
│     Body: { "status": "met", "evidence": "..." }                             │
│                                                                              │
│     UI updates in real-time (checkbox checked)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. Task completion signal sent                                              │
│                                                                              │
│     Agent outputs "TASK_COMPLETE" (2x consecutive)                           │
│     Git validation passes                                                    │
│     POST /api/v1/sandboxes/{sandbox_id}/task-complete                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. Phase transition triggered                                               │
│                                                                              │
│     PhaseManager handles TASK_COMPLETED event                                │
│     If all tasks complete: ticket moves to PHASE_DONE                        │
│     UI shows all requirements/criteria as complete                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Task Context Endpoint Design

### GET /api/v1/tasks/{task_id}/context

**Purpose**: Provide sandbox with all context needed to execute task

**Response Schema**:
```json
{
  "task": {
    "id": "uuid",
    "description": "Implement user authentication",
    "task_type": "implement_feature",
    "phase_id": "PHASE_IMPLEMENTATION",
    "ticket_id": "uuid"
  },
  "ticket": {
    "id": "uuid",
    "title": "User Authentication Feature",
    "description": "..."
  },
  "spec": {
    "id": "uuid",
    "title": "Authentication Spec"
  },
  "requirements": [
    {
      "id": "REQ-001",
      "description": "WHEN user submits login form THEN system validates credentials",
      "acceptance_criteria": [
        {
          "id": "AC-001-1",
          "description": "Valid credentials return JWT token",
          "status": "pending"
        },
        {
          "id": "AC-001-2",
          "description": "Invalid credentials return 401 error",
          "status": "pending"
        }
      ]
    }
  ],
  "design": {
    "architecture": "...",
    "interfaces": "...",
    "data_models": "..."
  },
  "files_to_modify": ["src/auth/login.py", "tests/test_auth.py"]
}
```

---

## Acceptance Criteria Status Update

### PATCH /api/v1/requirements/{req_id}/criteria/{criteria_id}

**Purpose**: Allow sandbox to mark acceptance criteria as met during execution

**Request Body**:
```json
{
  "status": "met",
  "evidence": "Test test_login_valid_credentials passes with JWT token validation",
  "verified_by": "sandbox-abc123",
  "verified_at": "2025-01-22T10:30:00Z"
}
```

**Response**:
```json
{
  "id": "AC-001-1",
  "status": "met",
  "evidence": "...",
  "requirement_id": "REQ-001",
  "requirement_complete": false  // True when all criteria met
}
```

---

## Phase Transition Logic

### PhaseManager._handle_task_completed()

**File**: `backend/omoi_os/services/phase_manager.py` (lines 1096-1127)

```python
def _handle_task_completed(self, event_data: dict) -> None:
    payload = event_data.get("payload", {})
    ticket_id = payload.get("ticket_id")
    task_type = payload.get("task_type")

    if not ticket_id:
        return

    # For implement_feature tasks, go directly to DONE
    if task_type == "implement_feature":
        self.move_to_done(
            ticket_id=ticket_id,
            initiated_by="phase-manager-task-completed",
            reason=f"Implementation task completed",
        )
    else:
        # For other tasks, check if we can advance
        self.check_and_advance(ticket_id)
```

**Key Insight**: `implement_feature` task completion directly triggers `move_to_done()`. Other task types use `check_and_advance()` which validates phase gates.

---

## Integration Points

### 1. Claude Sandbox Worker Changes

**File**: `backend/omoi_os/workers/continuous_sandbox_worker.py`

Add context pulling at task start:
```python
async def _start_task(self):
    # Pull full context before starting
    context = await self._fetch_task_context(self.task_id)

    # Inject context into Claude prompt
    self.system_prompt = self._build_prompt_with_context(context)
```

Add acceptance criteria updates during execution:
```python
async def _report_criteria_met(self, criteria_id: str, evidence: str):
    await self.reporter.report(
        "criteria.met",
        {
            "criteria_id": criteria_id,
            "evidence": evidence,
            "task_id": self.task_id,
        }
    )
```

### 2. Backend API Changes

**New Route**: `backend/omoi_os/api/routes/specs.py`

```python
@router.get("/{spec_id}/requirements")
async def get_spec_requirements(spec_id: UUID):
    """Get requirements with acceptance criteria for a spec."""
    # Return requirements with nested criteria

@router.patch("/requirements/{req_id}/criteria/{criteria_id}")
async def update_acceptance_criteria(
    req_id: str,
    criteria_id: str,
    update: CriteriaUpdate,
):
    """Update acceptance criteria status."""
    # Update criteria, emit event for UI update
```

### 3. Frontend Updates

**Component**: Spec dashboard requirements tab

- Listen for criteria status events via websocket/polling
- Update checkboxes in real-time as sandbox marks criteria met
- Show progress percentage based on criteria completion

---

## Testing Strategy

### Unit Tests

1. **PhaseManager event handlers**
   - Test `_handle_task_completed` with different task types
   - Test phase transitions with mock events

2. **Criteria update endpoints**
   - Test PATCH endpoint updates status correctly
   - Test requirement completion calculation

### Integration Tests

1. **E2E phase flow** (existing: `scripts/test_e2e_phase_flow.py`)
   - Ticket creation → Task execution → Phase transition

2. **Criteria update flow** (to create)
   - Task starts → Pulls context → Updates criteria → Completes → Phase transition

### Manual Testing

1. Create spec via UI
2. Execute spec tasks
3. Watch sandbox logs for completion signals
4. Verify phase transitions in dashboard
5. Check acceptance criteria checkboxes update

---

## Open Questions

1. **Criteria Update Frequency**: Should sandbox update criteria after each test pass, or batch at end?
   - Recommendation: Update as tests pass for real-time UI feedback

2. **Evidence Storage**: How much evidence detail to store per criteria?
   - Recommendation: Store test output excerpt, file paths, timestamps

3. **Rollback Handling**: What happens if criteria needs to be unmarked?
   - Recommendation: Allow status reversal with audit trail

4. **Multi-Task Requirements**: If multiple tasks touch same requirement, how to coordinate?
   - Recommendation: Criteria marked met when ANY task provides evidence

---

## Next Steps

1. **Immediate** (for demo):
   - Verify E2E flow works with manual task execution
   - Ensure phase transitions happen automatically

2. **Short-term**:
   - Implement task context endpoint
   - Add criteria update mechanism
   - Wire up UI updates

3. **Medium-term**:
   - Add evidence storage
   - Implement requirement completion aggregation
   - Add progress tracking metrics

---

## Related Files

| File | Purpose |
|------|---------|
| `backend/scripts/test_e2e_phase_flow.py` | E2E test for phase transitions |
| `backend/omoi_os/services/phase_manager.py` | Phase transition logic |
| `backend/omoi_os/services/task_queue.py` | Task status and event publishing |
| `backend/omoi_os/workers/continuous_sandbox_worker.py` | Claude sandbox execution |
| `backend/omoi_os/api/routes/sandbox.py` | Sandbox API endpoints |
| `subsystems/spec-sandbox/src/spec_sandbox/worker/state_machine.py` | Spec generation |
| `subsystems/spec-sandbox/src/spec_sandbox/prompts/phases.py` | Spec phase prompts |

---

## Session Continuation Context

**Last Updated**: 2025-01-22

### What Was Accomplished This Session

1. **Verified PhaseManager Integration Works**
   - Created `backend/scripts/test_e2e_phase_flow.py` - a mock mode E2E test
   - Test passes: Ticket transitions BACKLOG → IMPLEMENTATION → DONE automatically
   - PhaseManager._handle_task_completed() correctly triggers move_to_done()

2. **Explored Completion Signal Pattern**
   - Claude sandbox worker uses "TASK_COMPLETE" string detection
   - Requires 2 consecutive detections to prevent false positives
   - After threshold: runs git validation (clean, pushed, PR created)
   - File: `continuous_sandbox_worker.py` lines 625-720

3. **Created This Design Document**
   - Tracks progress, defines architecture, proposes new endpoints
   - Located at: `docs/design/workflows/sandbox_task_completion_flow.md`

### Key Files to Read First in Next Session

```bash
# 1. This design document (you're reading it)
docs/design/workflows/sandbox_task_completion_flow.md

# 2. The E2E test script (shows working phase transition flow)
backend/scripts/test_e2e_phase_flow.py

# 3. PhaseManager event handlers (core logic)
backend/omoi_os/services/phase_manager.py  # lines 1096-1127 for _handle_task_completed

# 4. Claude sandbox worker completion detection
backend/omoi_os/workers/continuous_sandbox_worker.py  # lines 625-720

# 5. Task completion endpoint (sandbox calls this)
backend/omoi_os/api/routes/sandbox.py  # search for "task-complete"
```

### Commands to Run E2E Test

```bash
cd backend
uv run python scripts/test_e2e_phase_flow.py --mock
# Should output: "✓ SUCCESS: Ticket transitioned to PHASE_DONE automatically!"
```

### What Needs to Be Done Next

**Priority 1 - For Demo Today:**
- [ ] Run the E2E test to verify it still passes
- [ ] Manually test with a real spec execution if time permits

**Priority 2 - Acceptance Criteria Updates:**
- [ ] Implement `GET /api/v1/tasks/{task_id}/context` endpoint
- [ ] Implement `PATCH /api/v1/requirements/{req_id}/criteria/{criteria_id}` endpoint
- [ ] Wire sandbox to call these endpoints during execution

**Priority 3 - UI Updates:**
- [ ] Add real-time criteria status updates to spec dashboard
- [ ] Show checkboxes updating as sandbox marks criteria met

### Key Decisions Made

1. **Two Sandbox Systems Stay Separate**
   - spec-sandbox: Generates specs (EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC)
   - Claude sandbox worker: Executes implementation tasks
   - Do NOT remove phases from spec-sandbox - requirements need to show in UI

2. **Completion Signal Pattern**
   - "TASK_COMPLETE" string detected 2x consecutive
   - Git validation after signal detection
   - Research tasks (no code changes) auto-pass validation

3. **Phase Transition Trigger**
   - `implement_feature` task type → direct move_to_done()
   - Other task types → check_and_advance() (validates gates)

### User's Primary Goal

User has a demo video to finish today. Needs to verify:
1. Tasks execute in sandboxes properly
2. Phase transitions happen automatically when tasks complete
3. Requirements/acceptance criteria are visible in spec dashboard UI

### Prompt to Resume Work

```
Continue working on the sandbox task completion and phase flow.
Read the design document at docs/design/workflows/sandbox_task_completion_flow.md
for full context. The E2E test at backend/scripts/test_e2e_phase_flow.py
already passes. Focus on implementing the acceptance criteria update endpoints
so the UI can show criteria being checked off in real-time.
```

### Code Snippets Ready to Use

**PhaseManager Event Handler Location** (for reference):
```python
# backend/omoi_os/services/phase_manager.py lines 1096-1127
def _handle_task_completed(self, event_data: dict) -> None:
    payload = event_data.get("payload", {})
    ticket_id = payload.get("ticket_id")
    task_type = payload.get("task_type")

    if task_type == "implement_feature":
        self.move_to_done(ticket_id=ticket_id, ...)
    else:
        self.check_and_advance(ticket_id)
```

**Completion Signal Detection** (for reference):
```python
# backend/omoi_os/workers/continuous_sandbox_worker.py lines 625-650
if config.completion_signal in output_text:  # "TASK_COMPLETE"
    state.completion_signal_count += 1
    if config.auto_validate:
        await self._run_validation()
else:
    state.completion_signal_count = 0  # Reset
```

### Architecture Summary

```
Spec Dashboard UI ◄───────────────────────────────────────────┐
       │                                                       │
       ▼                                                       │
spec-sandbox ──► Requirements/Design/Tasks ──► Database ──────┤
                                                               │
Claude Sandbox Worker ──► TASK_COMPLETE signal                 │
       │                                                       │
       ▼                                                       │
POST /sandboxes/{id}/task-complete                             │
       │                                                       │
       ▼                                                       │
TaskQueueService.update_task_status()                          │
       │                                                       │
       ▼                                                       │
EventBusService publishes TASK_COMPLETED                       │
       │                                                       │
       ▼                                                       │
PhaseManager._handle_task_completed()                          │
       │                                                       │
       ▼                                                       │
move_to_done() or check_and_advance() ─────────────────────────┘
```
