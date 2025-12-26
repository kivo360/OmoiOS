# Sandbox Lifecycle State Machine

**Created**: 2024-12-26
**Updated**: 2024-12-26
**Status**: Implemented
**Purpose**: Define exact rules for sandbox lifecycle management, idle detection, and termination

---

## Overview

This document defines the state machine for sandbox lifecycle management. The goal is to have **perfectly tight** rules that prevent:
1. Premature termination of working sandboxes
2. Runaway diagnostic task spawning
3. Resource waste from truly idle sandboxes

---

## Current State (As Implemented)

### Event Types

#### Work Events (indicate actual progress)
```
agent.file_edited      - Agent edited a file
agent.tool_completed   - Agent finished using a tool
agent.subagent_completed - Subagent finished work
agent.skill_completed  - Skill execution completed
agent.completed        - Agent finished entire task (TERMINAL)
agent.assistant_message - Agent sent a message
agent.tool_use         - Agent started using a tool
agent.tool_result      - Tool returned a result
```

#### Non-Work Events (don't indicate progress)
```
agent.heartbeat        - Agent is alive (has status field)
agent.started          - Agent started execution
agent.thinking         - Agent is processing
agent.error            - Agent encountered an error
```

### Heartbeat Status Values
```
idle      - Agent is not doing anything
running   - Agent is actively working
degraded  - Agent has issues but is alive
failed    - Agent has failed
```

### Constants
```
IDLE_THRESHOLD         = 3 minutes   (no work events = idle)
HEARTBEAT_TIMEOUT      = 90 seconds  (no heartbeat = dead)
STUCK_RUNNING_THRESHOLD = 10 minutes (running status but no work = stuck)
```

---

## Current Decision Logic

### is_alive Determination
```
IF last_heartbeat exists AND (now - last_heartbeat) < 90 seconds:
    is_alive = TRUE
ELSE:
    is_alive = FALSE
```

### is_idle Determination (IMPLEMENTED - FIXED)
```
IF NOT is_alive:
    is_idle = FALSE  # Dead sandboxes are not "idle"

# Check completion with resume detection
completed_at = timestamp of LATEST agent.completed event
IF completed_at exists AND last_work_event > completed_at:
    has_completed = FALSE  # Agent resumed work after completion
ELSE IF completed_at exists:
    has_completed = TRUE   # Agent truly completed

IF has_completed:
    is_idle = FALSE  # Completed sandboxes not marked idle

ELSE IF heartbeat_status == "running":
    # Check for stuck-running condition
    IF last_work_event exists AND (now - last_work_event) > STUCK_RUNNING_THRESHOLD:
        is_idle = TRUE   # STUCK: Claims running but no work for 10+ min
        is_stuck_running = TRUE
    ELSE:
        is_idle = FALSE  # Agent is actively working

ELSE IF no work events ever:
    is_idle = TRUE
    idle_duration = now - first_heartbeat

ELSE IF (now - last_work_event) > IDLE_THRESHOLD:
    is_idle = TRUE
    idle_duration = now - last_work_event

ELSE:
    is_idle = FALSE
```

---

## Problems with Current Implementation (FIXED)

### Problem 1: `has_completed` is checked once, never reset ✅ FIXED
**Scenario:**
1. Agent completes task, sends `agent.completed`
2. Agent is resumed/restarted for more work
3. Agent sends work events (`agent.tool_use`, etc.)
4. Agent stops working, only sends heartbeats
5. ~~Current logic: `has_completed = TRUE` → never marked idle~~
6. ~~**Result**: Sandbox sits forever, never terminated~~

**Fix Applied**: Now checks if work events occurred AFTER the last `agent.completed` timestamp.
If `last_work.created_at > completed_at`, the completion is reset and agent is treated as running.
See `idle_sandbox_monitor.py:check_sandbox_activity()`.

### Problem 2: `heartbeat_status == "running"` trusted indefinitely ✅ FIXED
**Scenario:**
1. Agent sets status to "running"
2. Agent gets stuck in infinite loop or hangs
3. Heartbeats continue with status "running" but no work events
4. ~~**Result**: Sandbox never terminated even though it's stuck~~

**Fix Applied**: Added `STUCK_RUNNING_THRESHOLD = 10 minutes`. If agent reports "running"
but has no work events for 10+ minutes, it's marked as `is_stuck_running = TRUE` and terminated
with reason `"stuck_running"`. See `idle_sandbox_monitor.py:check_sandbox_activity()`.

### Problem 3: No distinction between "finished" and "truly idle" ✅ ADDRESSED
**Scenario:**
1. Agent completes work successfully
2. Agent is now idle (waiting for next task or shutdown)
3. Should we terminate? Depends on whether more work is expected

**Resolution**: After `agent.completed`, sandbox is NOT marked idle. It will eventually
be cleaned up by a separate post-completion timeout (suggested: 5 minutes) or when the
task status is marked as completed. The diagnostic system now also recognizes workflows
where all tasks completed successfully without needing a formal WorkflowResult.

---

## Proposed State Machine

### Sandbox States

```
┌─────────────┐
│   CREATED   │  Initial state when sandbox is spawned
└──────┬──────┘
       │ agent.started
       ▼
┌─────────────┐
│   RUNNING   │  Agent is actively working
└──────┬──────┘
       │
       ├─── agent.completed ──────────────────┐
       │                                      ▼
       │                              ┌─────────────┐
       │                              │  COMPLETED  │  Agent finished successfully
       │                              └──────┬──────┘
       │                                     │
       │                                     │ work event after completed
       │                                     ▼
       │                              ┌─────────────┐
       │                              │   RESUMED   │  Agent restarted work
       │                              └──────┬──────┘
       │                                     │
       │                                     │ (loops back)
       │◄────────────────────────────────────┘
       │
       ├─── no work for IDLE_THRESHOLD ───┐
       │    AND status != "running"       │
       │                                  ▼
       │                          ┌─────────────┐
       │                          │    IDLE     │  No progress, should terminate
       │                          └──────┬──────┘
       │                                 │
       │                                 │ terminate_idle_sandbox()
       │                                 ▼
       │                          ┌─────────────┐
       │                          │ TERMINATED  │  Sandbox stopped
       │                          └─────────────┘
       │
       ├─── no heartbeat for HEARTBEAT_TIMEOUT
       │
       ▼
┌─────────────┐
│    DEAD     │  Sandbox stopped responding
└─────────────┘
```

### State Transition Rules

#### RUNNING → COMPLETED
```
WHEN: agent.completed event received
THEN:
  - Mark state as COMPLETED
  - Record completion timestamp
  - Start post-completion timer (e.g., 5 minutes)
```

#### COMPLETED → TERMINATED (auto-cleanup)
```
WHEN: Post-completion timer expires AND no new work events
THEN:
  - Terminate sandbox gracefully
  - Mark task as completed (not failed!)
```

#### COMPLETED → RESUMED
```
WHEN: Work event received after agent.completed
THEN:
  - Mark state as RESUMED (effectively RUNNING)
  - Clear completion timestamp
  - Restart idle monitoring
```

#### RUNNING → IDLE
```
WHEN: ALL of:
  - is_alive = TRUE
  - heartbeat_status != "running"
  - (now - last_work_event) > IDLE_THRESHOLD
  - NOT in COMPLETED state
THEN:
  - Mark as IDLE
  - Terminate sandbox
  - Mark task as FAILED with "idle_timeout"
```

#### RUNNING → DEAD
```
WHEN: (now - last_heartbeat) > HEARTBEAT_TIMEOUT
THEN:
  - Mark as DEAD
  - Terminate sandbox
  - Mark task as FAILED with "heartbeat_timeout"
```

### Special Rules

#### Rule: "Running" Status with No Work
```
IF heartbeat_status == "running"
   AND (now - last_work_event) > STUCK_THRESHOLD (e.g., 10 minutes)
THEN:
   Consider agent STUCK, not just idle
   Log warning but still terminate
```

#### Rule: Completed Then Resumed
```
IF agent.completed seen
   AND work events exist AFTER agent.completed timestamp
THEN:
   has_completed = FALSE (reset it)
   Treat as normal RUNNING state
```

#### Rule: Never Terminate Completed Tasks as Failed
```
IF agent.completed seen
   AND no work events after completion
   AND terminating for cleanup
THEN:
   Task status should remain "completed" (not "failed")
```

---

## Required Code Changes

### 1. Track completion timestamp, not just boolean
```python
# Instead of:
has_completed = session.query(SandboxEvent).filter(...).first() is not None

# Do:
completed_event = session.query(SandboxEvent).filter(
    SandboxEvent.sandbox_id == sandbox_id,
    SandboxEvent.event_type == "agent.completed",
).order_by(SandboxEvent.created_at.desc()).first()

completed_at = completed_event.created_at if completed_event else None
```

### 2. Check if work happened after completion
```python
if completed_at and last_work:
    work_after_completion = last_work.created_at > completed_at
    if work_after_completion:
        # Agent resumed - treat as running, not completed
        has_completed = False
```

### 3. Add "stuck running" detection
```python
STUCK_THRESHOLD = timedelta(minutes=10)

if heartbeat_status == "running" and last_work:
    running_without_work = (now - last_work.created_at) > STUCK_THRESHOLD
    if running_without_work:
        logger.warning("agent_stuck_running", sandbox_id=sandbox_id)
        is_idle = True  # Force termination
```

### 4. Don't mark completed tasks as failed
```python
# In terminate_idle_sandbox:
if task.status in ("pending", "claiming", "assigned", "running"):
    # Only mark as failed if task wasn't completed
    if not has_completed:
        task.status = "failed"
        task.error_message = f"Sandbox terminated: {reason}..."
    else:
        # Completed task being cleaned up - leave status as completed
        logger.info("cleanup_completed_sandbox", task_id=task_id)
```

---

## Summary of States

| State | Description | Next States |
|-------|-------------|-------------|
| CREATED | Sandbox spawned, agent not started | RUNNING |
| RUNNING | Agent actively working | COMPLETED, IDLE, DEAD |
| COMPLETED | Agent finished task successfully | RESUMED, TERMINATED |
| RESUMED | Agent restarted after completion | COMPLETED, IDLE, DEAD |
| IDLE | No work progress, should terminate | TERMINATED |
| DEAD | No heartbeats, unresponsive | TERMINATED |
| TERMINATED | Sandbox stopped | (terminal) |

## Summary of Conditions (IMPLEMENTED)

| Condition | Old Behavior | New Behavior (Implemented) |
|-----------|---------|----------|
| is_alive | heartbeat < 90s ago | Same |
| is_completed | ANY agent.completed exists | ✅ LATEST agent.completed, no work after |
| is_running | heartbeat.status == "running" | ✅ Same, BUT with stuck detection |
| is_idle | no work for 3min + not running + not completed | ✅ Completed resets if resumed |
| is_stuck_running | N/A | ✅ NEW: running status but no work for 10min |
| workflow_success | Requires WorkflowResult | ✅ NEW: All tasks completed + none failed |

---

---

## Diagnostic Task Spawning Logic

The diagnostic system (`diagnostic.py`) spawns recovery tasks when it detects "stuck" workflows. This is a MAJOR source of runaway tasks when the logic is wrong.

### Updated Logic: `find_stuck_workflows()` (IMPLEMENTED)

```
FOR each ticket WHERE status != "done":

    # Condition 1: Has tasks
    IF no tasks exist for ticket:
        SKIP (nothing to diagnose)

    # Condition 2: All tasks finished
    IF any task has status IN (pending, claiming, assigned, running,
                               under_review, validation_in_progress):
        SKIP (work still in progress)

    # Condition 3: Has validated WorkflowResult
    IF WorkflowResult exists with status="validated":
        SKIP (workflow completed successfully)

    # ✅ Condition 4: All tasks completed without failures
    IF completed_tasks > 0 AND failed_tasks == 0:
        SKIP (simple workflow succeeded - no WorkflowResult needed)

    # ✅ Condition 5: Diagnostics already attempted for failed task
    # This prevents infinite loops where:
    #   - Original task fails
    #   - Diagnostic task spawned and completes
    #   - Original task still failed
    #   - System spawns ANOTHER diagnostic → LOOP!
    IF completed_diagnostic_tasks > 0 AND failed_original_tasks > 0:
        SKIP (needs human review, not more diagnostics)

    # Safeguards
    IF pending diagnostic tasks exist: SKIP
    IF consecutive_failures >= max_consecutive_failures: SKIP
    IF total_diagnostic_runs >= max_diagnostics_per_workflow: SKIP
    IF not clone_ready: SKIP
    IF cooldown not passed: SKIP

    # Stuck time check
    IF time_since_last_task_completion >= stuck_threshold (60s):
        → WORKFLOW IS STUCK → SPAWN DIAGNOSTIC TASK
```

### THE PROBLEM: WorkflowResult Dependency ✅ FIXED

**The diagnostic system required a `WorkflowResult` with `status="validated"` to know work is done.**

But `WorkflowResult` is only created when:
1. Agent explicitly calls `submit_result` API
2. Result goes through validation process
3. Validator marks it as `validated`

**For simple tasks (like creating a Python script):**
- Agent completes task ✓
- Task marked as `completed` ✓
- But NO WorkflowResult is created! ✗
- ~~Diagnostic system thinks: "All tasks done, no validated result = STUCK"~~
- ~~→ Spawns diagnostic task~~
- ~~→ Diagnostic task completes~~
- ~~→ Still no WorkflowResult~~
- ~~→ Spawns ANOTHER diagnostic task~~
- ~~→ RUNAWAY LOOP~~

### Fix Applied

**Now checks task completion status BEFORE checking for WorkflowResult.**

Added this safeguard to `diagnostic.py:find_stuck_workflows()`:

```python
# ===== SAFEGUARD: All tasks completed successfully without failures =====
# Simple tasks (like creating a Python script) don't always produce
# a WorkflowResult, but if all tasks completed and none failed,
# the workflow succeeded - don't spawn diagnostics!
completed_tasks = session.query(Task).filter(
    Task.ticket_id == ticket.id,
    Task.status == "completed",
).count()
failed_tasks = session.query(Task).filter(
    Task.ticket_id == ticket.id,
    Task.status == "failed",
).count()

# If we have completed tasks and NO failed tasks, workflow succeeded
if completed_tasks > 0 and failed_tasks == 0:
    logger.debug(
        f"Skipping workflow {ticket.id}: all {completed_tasks} tasks completed successfully"
    )
    continue
```

**Result**: Simple successful workflows no longer trigger runaway diagnostics.

### Diagnostic Spawning Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   DIAGNOSTIC MONITORING LOOP                     │
│                  (runs every 60 seconds)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. find_stuck_workflows()                                       │
│     └─ Query all tickets where status != "done"                  │
│     └─ Check each for "stuck" conditions                         │
│                                                                  │
│  2. For each stuck workflow:                                     │
│     └─ build_diagnostic_context()                                │
│     └─ spawn_diagnostic_agent()                                  │
│         └─ Create DiagnosticRun record                           │
│         └─ Generate hypotheses via LLM                           │
│         └─ discovery.spawn_diagnostic_recovery()                 │
│             └─ Create Task with type="discovery_diagnostic_*"    │
│                                                                  │
│  3. New diagnostic task enters queue                             │
│     └─ Gets picked up by worker                                  │
│     └─ Runs in sandbox                                           │
│     └─ Completes (or fails)                                      │
│                                                                  │
│  4. Loop repeats...                                              │
│     └─ If still no WorkflowResult → SPAWNS AGAIN!                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Connection to Idle Sandbox Monitor

The idle sandbox monitor can TRIGGER diagnostic spawning indirectly:

```
1. Sandbox is terminated for idle_timeout
2. Task marked as "failed"
3. Diagnostic monitor sees: "task failed, no WorkflowResult"
4. Diagnostic thinks workflow is stuck
5. Spawns diagnostic task
6. New sandbox created
7. If new sandbox also goes idle → cycle repeats
```

---

## Termination Procedure

When a sandbox is terminated (idle, dead, or cleanup), the following steps MUST happen in order:

```
┌─────────────────────────────────────────────────────────┐
│                  TERMINATION SEQUENCE                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. EXTRACT TRANSCRIPT                                   │
│     └─ Pull session transcript from sandbox              │
│     └─ Contains full conversation/work history           │
│                                                          │
│  2. SAVE TRANSCRIPT                                      │
│     └─ Persist to database (claude_session_transcripts)  │
│     └─ Enables later resumption or debugging             │
│                                                          │
│  3. STOP SANDBOX                                         │
│     └─ Call daytona_spawner.terminate_sandbox()          │
│     └─ Releases Daytona resources                        │
│                                                          │
│  4. UPDATE TASK STATUS                                   │
│     └─ Only if task is in active state:                  │
│        pending, claiming, assigned, running              │
│     └─ Mark as "failed" with reason                      │
│     └─ DO NOT overwrite completed/cancelled tasks        │
│                                                          │
│  5. EMIT EVENT                                           │
│     └─ Publish SANDBOX_TERMINATED_IDLE event             │
│     └─ Includes: reason, duration, task_id, transcript   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Critical**: Transcript MUST be saved BEFORE stopping the sandbox. Once the sandbox is stopped, the transcript is lost.

**Implementation**: See `idle_sandbox_monitor.py:terminate_idle_sandbox()`

---

## Open Questions

1. **Post-completion timeout**: How long should we wait after `agent.completed` before auto-terminating?
   - Suggestion: 5 minutes

2. **Stuck running threshold**: How long with "running" status but no work before considering stuck?
   - Suggestion: 10 minutes

3. **Should completed sandboxes auto-terminate?**
   - Suggestion: Yes, after post-completion timeout

4. **What about user-initiated tasks?**
   - Should we wait indefinitely for user input?
   - Suggestion: No, same idle rules apply
