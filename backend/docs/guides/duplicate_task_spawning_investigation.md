# Duplicate Task Spawning Investigation

**Created**: 2025-12-23
**Status**: Investigation Complete - Fix Pending
**Purpose**: Document root cause analysis of duplicate sandbox task spawning and recommended solutions

## Executive Summary

The orchestrator continuously spawns duplicate tasks (particularly diagnostic tasks like `discovery_diagnostic_no_result`) despite tasks already being completed. This investigation identified **the root cause as an in-memory cooldown dictionary** in `DiagnosticService` that loses state on process restart or across multiple process instances.

### Key Findings

| Issue | Status | Impact |
|-------|--------|--------|
| In-memory cooldown dictionary | **ROOT CAUSE** | Cooldown lost on restart |
| Race condition in task claiming | Fixed | Minor contributor |
| Completed tasks marked as failed | Fixed | UI confusion |
| Missing `claiming` status in checks | Fixed | Task state inconsistency |

---

## Symptoms Observed

1. **Duplicate task spawning**: Same task (e.g., binomial distribution calculation) keeps reappearing
2. **Task intervals**: 2-12 minutes between duplicate runs (tends toward extremes)
3. **Completed tasks showing as "Failed"**: Tasks that successfully completed were marked failed in UI
4. **Daytona credit consumption**: Unnecessary sandboxes being spawned

---

## Root Cause Analysis

### The Real Problem: In-Memory Cooldown State

**Location**: `omoi_os/services/diagnostic.py`

```python
class DiagnosticService:
    def __init__(...):
        # THIS IS THE ROOT CAUSE
        self._last_diagnostic: Dict[str, float] = {}  # In-memory only!
```

**Why This Fails**:

1. **Process Restart**: Any restart of `orchestrator_worker.py` or `monitoring_worker.py` creates a new `DiagnosticService` instance with an empty `_last_diagnostic` dictionary

2. **Multiple Processes**: Each worker process has its own `DiagnosticService` instance with independent cooldown state - they don't share memory

3. **Cooldown Check Fails**:
```python
def find_stuck_workflows(self, cooldown_seconds: int = 60, ...):
    now_timestamp = utc_now().timestamp()
    if ticket.id in self._last_diagnostic:  # Empty after restart!
        time_since_last = now_timestamp - self._last_diagnostic[ticket.id]
        if time_since_last < cooldown_seconds:
            continue  # Skip - but this never triggers after restart
```

### Why 2-12 Minute Intervals?

The timing pattern (2-12 minutes, tending toward extremes) correlates with:

- **60-second diagnostic monitoring loop** + processing time
- **Process lifecycle events** (restarts, new instances)
- **Event-driven feedback loop**: Diagnostic tasks emit `TASK_CREATED` events which wake the orchestrator

### The Cascade Effect

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DUPLICATE SPAWNING CASCADE                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. DiagnosticService detects "stuck" workflow                      │
│     └─ Cooldown check passes (dictionary empty or stale)            │
│                                                                      │
│  2. Spawns diagnostic task (discovery_diagnostic_no_result)         │
│     └─ Task inserted with status='pending'                          │
│                                                                      │
│  3. EventBus emits TASK_CREATED                                     │
│     └─ Orchestrator receives wakeup signal                          │
│                                                                      │
│  4. Orchestrator picks up task                                      │
│     └─ Spawns Daytona sandbox                                       │
│                                                                      │
│  5. Meanwhile: Another DiagnosticService check runs                 │
│     └─ Different process OR process restarted                       │
│     └─ Empty _last_diagnostic dictionary                            │
│     └─ Same "stuck" workflow detected again!                        │
│                                                                      │
│  6. GOTO step 2 (another diagnostic task spawned)                   │
│                                                                      │
│  Result: Multiple sandboxes for same problem                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Contributing Factors (Already Fixed)

### 1. Race Condition in Task Claiming

**File**: `omoi_os/services/task_queue.py`

**Problem**: `get_next_task()` returned tasks without atomically claiming them, allowing multiple poll cycles to grab the same task.

**Fix Applied**:
```python
# ATOMIC CLAIM: Use raw SQL UPDATE with WHERE clause
result = session.execute(
    text("""
        UPDATE tasks
        SET status = 'claiming', score = :score
        WHERE id = :task_id
        AND status = 'pending'
        AND sandbox_id IS NULL
        RETURNING id
    """),
    {"task_id": str(task.id), "score": task.score}
)
claimed_row = result.fetchone()
session.commit()

if not claimed_row:
    logger.debug(f"Task {task.id} was claimed by another process, skipping")
    return None
```

### 2. Completed Tasks Marked as Failed

**File**: `omoi_os/services/idle_sandbox_monitor.py`

**Problem**: `terminate_idle_sandbox()` blindly set `task.status = "failed"` without checking if task was already completed.

**Fix Applied**:
```python
# Only mark as failed if task is still in an active state
if task.status in ("pending", "claiming", "assigned", "running"):
    task.status = "failed"
    task.error_message = f"Sandbox terminated: {reason}..."
else:
    log.info("task_status_preserved", existing_status=task.status)
```

### 3. Missing `claiming` Status in Active Task Checks

**Files**: `diagnostic.py`, `task_queue.py`, `sandbox.py`, `restart_orchestrator.py`

**Problem**: The new `claiming` status wasn't included in active task status checks, causing services to think tasks were finished when they were being claimed.

**Fix Applied**: Added `"claiming"` to all `.in_(["pending", "assigned", "running"])` filters.

---

## Recommended Solutions

### Quick Fix: Persist Cooldown to Database

Create a new model and persist cooldown state:

```python
# omoi_os/models/diagnostic_cooldown.py
class DiagnosticCooldown(Base):
    __tablename__ = "diagnostic_cooldowns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id"), unique=True)
    last_diagnostic_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

    __table_args__ = (
        Index("ix_diagnostic_cooldowns_ticket_id", "ticket_id"),
    )
```

Update `DiagnosticService`:
```python
def _check_cooldown(self, ticket_id: uuid.UUID, cooldown_seconds: int) -> bool:
    """Check if cooldown period has passed (database-backed)."""
    with self.db.get_session() as session:
        cooldown = session.query(DiagnosticCooldown).filter(
            DiagnosticCooldown.ticket_id == ticket_id
        ).first()

        if cooldown:
            elapsed = (utc_now() - cooldown.last_diagnostic_at).total_seconds()
            return elapsed >= cooldown_seconds
        return True  # No record = never ran

def _update_cooldown(self, ticket_id: uuid.UUID):
    """Update cooldown timestamp in database."""
    with self.db.get_session() as session:
        cooldown = session.query(DiagnosticCooldown).filter(
            DiagnosticCooldown.ticket_id == ticket_id
        ).first()

        if cooldown:
            cooldown.last_diagnostic_at = utc_now()
        else:
            cooldown = DiagnosticCooldown(
                ticket_id=ticket_id,
                last_diagnostic_at=utc_now()
            )
            session.add(cooldown)
        session.commit()
```

### Medium-Term: Add Deduplication Check Before Spawning

Before creating any diagnostic task, check if one already exists:

```python
def _has_pending_diagnostic(self, ticket_id: uuid.UUID, task_type: str) -> bool:
    """Check if a diagnostic task is already pending/running for this ticket."""
    with self.db.get_session() as session:
        existing = session.query(Task).filter(
            Task.ticket_id == ticket_id,
            Task.task_type == task_type,
            Task.status.in_(["pending", "claiming", "assigned", "running"])
        ).first()
        return existing is not None
```

### Long-Term: Event-Driven Architecture with TaskIQ

Migrate from polling-based orchestration to event-driven task execution:

**Key Benefits**:
- Immediate task execution (no 5-second polling delay)
- Built-in deduplication via Redis locks
- Proper async/await support
- Retry mechanisms with exponential backoff

**Architecture**:
```
┌────────────────────────────────────────────────────────────────┐
│                   EVENT-DRIVEN ARCHITECTURE                     │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Task Created ──► Redis Queue ──► TaskIQ Worker ──► Sandbox    │
│       │                              │                          │
│       │                              ├── Dedup Middleware       │
│       │                              │   (Redis Lock)           │
│       │                              │                          │
│       │                              └── Retry Middleware       │
│       │                                  (Exponential Backoff)  │
│       │                                                         │
│       └──► Periodic Cleanup Worker (catch missed tasks)         │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Example TaskIQ Implementation**:
```python
from taskiq import TaskiqMiddleware
from taskiq_redis import RedisAsyncLock

class DeduplicationMiddleware(TaskiqMiddleware):
    def __init__(self, redis_url: str, lock_ttl: int = 300):
        self.redis_url = redis_url
        self.lock_ttl = lock_ttl

    async def pre_execute(self, message):
        task_key = f"dedup:{message.task_name}:{message.kwargs.get('task_id')}"
        lock = RedisAsyncLock(self.redis_url, task_key, ttl=self.lock_ttl)

        if not await lock.acquire():
            raise TaskiqDuplicateError(f"Task {task_key} already running")

        message.labels["dedup_lock"] = lock
        return message
```

---

## Files Modified During Investigation

| File | Changes | Commit |
|------|---------|--------|
| `omoi_os/services/task_queue.py` | Atomic claiming, stale cleanup | `ba4c3a3` |
| `omoi_os/services/diagnostic.py` | Added `claiming` to status checks | `ba4c3a3` |
| `omoi_os/services/idle_sandbox_monitor.py` | Preserve completed task status | `8699c1d` |
| `omoi_os/api/routes/sandbox.py` | Added `claiming` to task lookup | `ba4c3a3` |
| `omoi_os/services/restart_orchestrator.py` | Clear `sandbox_id` on reassign | `ba4c3a3` |

---

## Implementation Priority

1. **Immediate** (30 min): Persist cooldown to database
2. **Short-term** (1 hour): Add deduplication check before spawning diagnostics
3. **Medium-term** (4-8 hours): Implement TaskIQ for event-driven execution
4. **Long-term**: Full migration to event-driven architecture

---

## Verification Steps

After implementing fixes:

1. **Restart orchestrator** and verify no immediate duplicate spawning
2. **Monitor task creation** logs for duplicate `discovery_diagnostic_*` tasks
3. **Check Daytona usage** for unexpected sandbox creation
4. **Verify completed tasks** remain marked as completed (not failed)

---

## Related Documentation

- [Async Python Patterns](./async_python_patterns.md) - Background on async worker patterns
- [Sandbox Architecture](../WORKSPACE_ARCHITECTURE.md) - Sandbox lifecycle documentation
- [Distributed Agent Architecture](../DISTRIBUTED_AGENT_ARCHITECTURE.md) - Multi-agent coordination
