# Sandbox Migration: Fix Legacy `assigned_agent_id` References

## Context

We've migrated from a legacy agent execution model to a new sandbox-based execution model using Daytona. The key difference:

- **Legacy**: Tasks have `assigned_agent_id` pointing to a persistent agent, use `AgentLog` for events, and store `conversation_id`/`persistence_dir` for OpenHands conversation persistence
- **Sandbox**: Tasks have `sandbox_id` pointing to an ephemeral Daytona sandbox, use `SandboxEvent` for events, and don't use conversation persistence (use message injection instead)

Many services still query/filter on `assigned_agent_id` which breaks sandbox execution. This document lists all required changes.

---

## Task Model Reference

```python
# backend/omoi_os/models/task.py
class Task(Base):
    assigned_agent_id: Optional[str]  # Legacy - NULL for sandbox tasks
    sandbox_id: Optional[str]         # New - set for sandbox tasks
    conversation_id: Optional[str]    # Legacy OpenHands persistence
    persistence_dir: Optional[str]    # Legacy OpenHands persistence
```

**Rule**: A task is a sandbox task if `sandbox_id IS NOT NULL`. Legacy tasks have `assigned_agent_id IS NOT NULL`.

---

## Critical Fixes (Will Break Execution)

### 1. Result Submission Validation

**File**: `backend/omoi_os/services/result_submission.py`
**Line**: 76-79

**Current Code**:
```python
if task.assigned_agent_id != agent_id:
    raise ValueError(
        f"Task {task_id} is not assigned to agent {agent_id}"
    )
```

**Problem**: Sandbox tasks have `assigned_agent_id = None`, so this always raises ValueError.

**Fix**: Check `sandbox_id` for sandbox tasks:
```python
# Validate task ownership based on execution mode
if task.sandbox_id:
    # Sandbox mode - verify via sandbox_id passed from worker
    # The sandbox worker should pass its sandbox_id for validation
    pass  # Sandbox validation handled differently
elif task.assigned_agent_id != agent_id:
    raise ValueError(
        f"Task {task_id} is not assigned to agent {agent_id}"
    )
```

---

### 2. Guardian Intervention Delivery

**File**: `backend/omoi_os/services/intelligent_guardian.py`
**Lines**: 814-830, 942-960

**Current Code** (line 819):
```python
if not task.conversation_id or not task.persistence_dir:
    logger.warning(f"Task {task.id} missing conversation info...")
    return False
```

**Problem**: Sandbox tasks never have `conversation_id` or `persistence_dir`, so Guardian can never intervene.

**Fix**: Add sandbox intervention path using message injection:
```python
if task.sandbox_id:
    # Sandbox mode - use message injection API
    return await self._send_sandbox_intervention(task.sandbox_id, intervention)
elif not task.conversation_id or not task.persistence_dir:
    logger.warning(f"Task {task.id} missing conversation info for legacy intervention")
    return False
# ... existing legacy intervention code
```

**Note**: You'll need to implement `_send_sandbox_intervention()` that calls the sandbox message injection endpoint at `POST /api/sandbox/{sandbox_id}/inject-message`.

---

### 3. Agent Collaboration Messaging

**File**: `backend/omoi_os/services/collaboration.py`
**Lines**: 619, 627, 654-656

**Current Code** (line 619):
```python
Task.assigned_agent_id == recipient_id,
```

**Current Code** (line 627):
```python
if active_task and active_task.conversation_id and active_task.persistence_dir:
```

**Problem**: Can't find or message agents running in sandboxes.

**Fix** (line 619):
```python
or_(
    Task.assigned_agent_id == recipient_id,
    and_(Task.sandbox_id.isnot(None), Task.status == "running")
),
```

**Fix** (line 627):
```python
if active_task:
    if active_task.sandbox_id:
        # Use sandbox message injection
        await self._inject_sandbox_message(active_task.sandbox_id, message)
        return True
    elif active_task.conversation_id and active_task.persistence_dir:
        # Legacy conversation injection
        # ... existing code
```

---

## Query Filter Fixes (Return Wrong/Empty Data)

### 4. Trajectory Context Queries

**File**: `backend/omoi_os/services/trajectory_context.py`
**Lines**: 101, 714

**Current Code** (line 101):
```python
.filter_by(assigned_agent_id=str(agent.id), status="running")
```

**Fix**:
```python
.filter(
    or_(
        Task.assigned_agent_id == str(agent.id),
        and_(
            Task.sandbox_id.isnot(None),
            # Need to join through sandbox to get agent_id
        )
    ),
    Task.status == "running"
)
```

**Alternative simpler fix** - if agent has sandbox tag, query by sandbox_id:
```python
if "sandbox" in (agent.tags or []):
    task = session.query(Task).filter(
        Task.sandbox_id.isnot(None),
        Task.status == "running"
    ).first()
else:
    task = session.query(Task).filter_by(
        assigned_agent_id=str(agent.id),
        status="running"
    ).first()
```

---

### 5. Monitor Service Queries

**File**: `backend/omoi_os/services/monitor.py`
**Lines**: 522, 534, 546

**Current Code**:
```python
Task.assigned_agent_id == agent_id,
```

**Fix** - Add sandbox_id to filter:
```python
or_(
    Task.assigned_agent_id == agent_id,
    Task.sandbox_id == sandbox_id  # Need to pass sandbox_id to these methods
),
```

---

### 6. Agent Output Collector - Wrong Event Table

**File**: `backend/omoi_os/services/agent_output_collector.py`
**Lines**: 98-107, 204, 403

**Current Code** (line 98-107):
```python
logs = (
    session.query(AgentLog)
    .filter_by(agent_id=agent_id)
    .filter(AgentLog.log_type.in_([...]))
    .order_by(AgentLog.created_at.desc())
    .limit(limit)
    .all()
)
```

**Problem**: Sandbox agents log to `SandboxEvent`, not `AgentLog`.

**Fix**:
```python
from omoi_os.models.sandbox_event import SandboxEvent

# Check if this is a sandbox agent
agent = session.query(Agent).get(agent_id)
if agent and agent.tags and "sandbox" in agent.tags:
    # Query SandboxEvent for sandbox agents
    events = (
        session.query(SandboxEvent)
        .filter_by(sandbox_id=sandbox_id)
        .filter(SandboxEvent.event_type.in_([...]))
        .order_by(SandboxEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    # Transform to common format
    logs = [self._sandbox_event_to_log(e) for e in events]
else:
    # Legacy AgentLog query
    logs = (
        session.query(AgentLog)
        .filter_by(agent_id=agent_id)
        ...
    )
```

---

### 7. Composite Anomaly Scorer Queries

**File**: `backend/omoi_os/services/composite_anomaly_scorer.py`
**Lines**: 269, 327, 348, 361

**Current Code**:
```python
Task.assigned_agent_id == agent_id,
```

**Fix** - Same pattern as monitor.py:
```python
or_(
    Task.assigned_agent_id == agent_id,
    Task.sandbox_id == sandbox_id
),
```

---

### 8. Diagnostic Service Filter

**File**: `backend/omoi_os/services/diagnostic.py`
**Lines**: 569, 583

**Current Code** (line 569):
```python
Task.assigned_agent_id.isnot(None),
```

**Current Code** (line 583):
```python
agent_id = task.assigned_agent_id
```

**Fix** (line 569):
```python
or_(
    Task.assigned_agent_id.isnot(None),
    Task.sandbox_id.isnot(None)
),
```

**Fix** (line 583):
```python
agent_id = task.assigned_agent_id
if not agent_id and task.sandbox_id:
    # Resolve sandbox_id to agent_id if needed
    # Or handle sandbox notification differently
    agent_id = self._get_agent_for_sandbox(task.sandbox_id)
```

---

### 9. Task Queue Assignment Logic

**File**: `backend/omoi_os/services/task_queue.py`
**Lines**: 279, 366, 561, 796

These need conditional logic based on execution mode. Key changes:

**Line 279** (task assignment):
```python
# Only set assigned_agent_id for legacy mode
if not use_sandbox:
    task.assigned_agent_id = agent_id
```

**Line 561** (retry logic):
```python
# Clear appropriate field based on mode
if task.sandbox_id:
    task.sandbox_id = None  # Clear sandbox for retry
else:
    task.assigned_agent_id = None  # Clear legacy assignment
```

**Line 796** (query filter):
```python
if sandbox_id:
    query = query.filter(Task.sandbox_id == sandbox_id)
elif agent_id:
    query = query.filter(Task.assigned_agent_id == agent_id)
```

---

## Sandbox Detection Fixes (Using Wrong Field)

### 10. Monitoring Loop - Wrong Sandbox Detection

**File**: `backend/omoi_os/services/monitoring_loop.py`
**Lines**: 427-435

**Current Code**:
```python
Task.assigned_agent_id.isnot(None),  # WRONG - sandbox tasks don't have this
```

**Fix**:
```python
Task.sandbox_id.isnot(None),  # Correct - sandbox tasks have sandbox_id
```

Also fix lines 433-435:
```python
# Current (wrong):
str(task.assigned_agent_id) if task.assigned_agent_id else None

# Fix:
task.sandbox_id  # Use sandbox_id directly
```

---

### 11. Conductor Service - Wrong Sandbox Detection

**File**: `backend/omoi_os/services/conductor.py`
**Lines**: 298-306

**Current Code**:
```python
Task.assigned_agent_id.isnot(None),
```

**Fix**:
```python
Task.sandbox_id.isnot(None),
```

---

### 12. Intelligent Guardian - Wrong Sandbox Detection

**File**: `backend/omoi_os/services/intelligent_guardian.py`
**Lines**: 277-285

**Current Code**:
```python
Task.assigned_agent_id.isnot(None),
```

**Fix**:
```python
Task.sandbox_id.isnot(None),
```

---

## Import Requirements

When adding `or_` and `and_` filters, ensure these imports:

```python
from sqlalchemy import or_, and_
```

When querying `SandboxEvent`:

```python
from omoi_os.models.sandbox_event import SandboxEvent
```

---

## Testing Checklist

After making changes, verify:

- [ ] Sandbox task can submit results without ValueError
- [ ] Guardian can detect sandbox tasks in monitoring loop
- [ ] Guardian can send interventions to sandbox tasks
- [ ] Trajectory analysis finds sandbox agent's current task
- [ ] Monitor metrics include sandbox task completions
- [ ] Agent output collector returns events for sandbox agents
- [ ] Collaboration messages reach sandbox agents
- [ ] Task retry works for sandbox tasks
- [ ] Diagnostic recovery notifications include sandbox tasks

---

## Files Summary

| Priority | File | Lines to Change |
|----------|------|-----------------|
| CRITICAL | `services/result_submission.py` | 76-79 |
| CRITICAL | `services/intelligent_guardian.py` | 277-285, 814-830, 942-960 |
| CRITICAL | `services/collaboration.py` | 619, 627, 654-656 |
| HIGH | `services/trajectory_context.py` | 101, 714 |
| HIGH | `services/monitor.py` | 522, 534, 546 |
| HIGH | `services/agent_output_collector.py` | 98-107, 204, 403 |
| HIGH | `services/composite_anomaly_scorer.py` | 269, 327, 348, 361 |
| MEDIUM | `services/diagnostic.py` | 569, 583 |
| MEDIUM | `services/task_queue.py` | 279, 366, 561, 796 |
| MEDIUM | `services/monitoring_loop.py` | 427-435 |
| MEDIUM | `services/conductor.py` | 298-306 |

---

## Notes

1. All files are in `backend/omoi_os/`
2. The sandbox message injection endpoint already exists at `POST /api/sandbox/{sandbox_id}/inject-message`
3. `SandboxEvent` model is in `backend/omoi_os/models/sandbox_event.py`
4. After changes, run tests: `pytest backend/tests/ -v`
