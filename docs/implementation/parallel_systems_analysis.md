# OmoiOS Parallel Systems Analysis Report

**Created**: 2026-02-01  
**Status**: Critical Issues Found  
**Purpose**: Identify conflicts between API Server and Orchestrator Worker running as separate processes

---

## Executive Summary

OmoiOS runs **two parallel processes** that share the same PostgreSQL database and Redis instance:

1. **API Server** (`backend/omoi_os/api/main.py`) - FastAPI application handling HTTP requests
2. **Orchestrator Worker** (`backend/omoi_os/workers/orchestrator_worker.py`) - Background task processor

This analysis found **3 critical issues** that will cause race conditions and unpredictable behavior in production.

---

## Critical Issues

### 🔴 CRITICAL Issue 1: Duplicate Event Handlers for Phase Transitions

**Both systems subscribe to the SAME events and perform the SAME database updates.**

| Event | API Server Handler | Worker Handler |
|-------|-------------------|----------------|
| `TASK_STARTED` | `PhaseManager._handle_task_started()` | `PhaseProgressionService._handle_task_started()` |
| `TASK_COMPLETED` | `PhaseManager._handle_task_completed()` | `PhaseProgressionService._handle_task_completed()` |

#### Evidence

**API Server subscribes at startup** (`api/main.py` line 721):
```python
phase_manager.subscribe_to_events()
```

**Worker subscribes at startup** (`orchestrator_worker.py` line 1326):
```python
phase_progression.subscribe_to_events()
```

**Both handlers move tickets to "done" for `implement_feature` tasks:**

- **API Server** (`phase_manager.py` lines 1096-1117):
  ```python
  async def _handle_task_completed(self, event: SystemEvent):
      task_type = event.payload.get("task_type", "")
      if task_type == "implement_feature":
          await self.move_to_done(ticket_id)  # ← Updates database
  ```

- **Worker** (`phase_progression_service.py` lines 277-341):
  ```python
  async def _handle_task_completed(self, event: SystemEvent):
      task_type = event.payload.get("task_type")
      if task_type == "implement_feature":
          await self._move_ticket_to_done(ticket_id)  # ← Same update!
  ```

#### Impact

When an `implement_feature` task completes:
1. Redis publishes `TASK_COMPLETED` event
2. **Both** API Server and Worker receive the event
3. **Both** try to update `ticket.status = "done"`
4. **RACE CONDITION**: Last write wins, possible database inconsistency

---

### 🔴 CRITICAL Issue 2: Redis Pub/Sub Subscriptions Don't Fire in Worker

**The orchestrator worker subscribes to events but NEVER processes them.**

#### How Redis Pub/Sub Works

Redis pub/sub requires an **active listener** to receive messages:
```python
# Subscription alone does NOT receive messages
pubsub.subscribe(**{channel: handler})

# You MUST call listen() or get_message() to process incoming messages
for message in pubsub.listen():  # Blocking
    pass  # Handlers fire automatically

# Or in a loop:
while True:
    message = pubsub.get_message()  # Non-blocking
```

#### What the Code Does

**EventBusService** (`event_bus.py` lines 122-133):
```python
def listen(self) -> None:
    """Start listening for events (blocking)."""
    for message in self.pubsub.listen():
        pass  # Callbacks invoked via subscribe()
```

**Orchestrator Worker** (`orchestrator_worker.py` lines 333-341):
```python
# Worker subscribes to events...
event_bus.subscribe("TASK_CREATED", handle_task_event)
event_bus.subscribe("TICKET_CREATED", handle_task_event)
# ... etc

# BUT NEVER CALLS:
# event_bus.listen()  ← This is NEVER called!
```

#### Search Results Confirming the Problem

The `listen()` method is only called in:
1. `event_bus.py` (definition)
2. `reasoning_listener.py` line 98 (but ReasoningListenerService is never started)
3. `events.py` line 70 (WebSocket route uses `get_message()`)

**The orchestrator worker has NO call to `listen()` or `get_message()`.**

#### Impact

- All event subscriptions in the worker are **dead code**
- Events registered at lines 333-341 are **never received**
- The worker relies on its 1-second polling fallback (lines 1082-1087) instead of events
- This might be **intentional** (polling-based architecture) but the subscriptions are misleading

---

### 🟡 HIGH Issue 3: No Database Locking on Ticket Status Updates

**Both processes update ticket status without optimistic or pessimistic locking.**

#### Evidence

**PhaseManager** (`phase_manager.py`):
```python
async def move_to_done(self, ticket_id: str):
    with self.db.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        ticket.status = "done"  # Direct assignment, no lock
        session.commit()
```

**PhaseProgressionService** (`phase_progression_service.py`):
```python
async def _move_ticket_to_done(self, ticket_id: str):
    with self.db.get_session() as session:
        ticket = session.query(Ticket).get(ticket_id)
        ticket.status = "done"  # Direct assignment, no lock
        session.commit()
```

#### Contrast with Task Queue (Done Correctly)

The `TaskQueueService` correctly uses atomic updates (`task_queue.py` lines 277-308):
```python
# Correct: Atomic UPDATE with WHERE clause
result = session.execute(
    update(Task)
    .where(Task.id == task_id)
    .where(Task.status == TaskStatus.PENDING)  # Only if still pending
    .values(status=TaskStatus.ASSIGNED, assigned_to=agent_id)
)
if result.rowcount == 0:
    return None  # Another process claimed it
```

#### Impact

When both processes try to update ticket status:
- No `SELECT ... FOR UPDATE` (pessimistic locking)
- No version column check (optimistic locking)
- Last write wins → potential state inconsistency

---

## Additional Observations

### Singleton Pattern - Process Safe ✅

The singleton pattern used (`get_*_service()` functions) is **process-safe** because:
- Each process has its own memory space
- Global variables are not shared between processes
- Each process initializes its own service instances

This is correct behavior for multi-process architecture.

### Redis Key Usage - No Conflicts ✅

Redis is used for:
1. **Pub/Sub channels**: `events.{event_type}` - Read-only, no conflicts
2. **OAuth state**: `oauth_state:{state}` - Per-request, TTL-based, no conflicts

No Redis key conflicts were found between processes.

### Task Queue - Correctly Implemented ✅

Task claiming uses atomic database updates (lines 277-308 in `task_queue.py`):
- `UPDATE ... WHERE status = pending` ensures only one process claims a task
- This is the correct pattern

---

## Recommended Fixes

### Option A: Single Event Handler (Recommended)

Remove event subscriptions from one system. Since the Worker is the task executor:

**Keep**: Worker's PhaseProgressionService subscriptions  
**Remove**: API Server's PhaseManager subscriptions

```python
# api/main.py - Remove this call
# phase_manager.subscribe_to_events()  ← DELETE
```

**Pros**: Simple, clear ownership  
**Cons**: API Server can't react to events directly

### Option B: Distributed Lock for Ticket Updates

Add Redis-based distributed locking:

```python
import redis

async def move_to_done(self, ticket_id: str):
    lock_key = f"ticket_lock:{ticket_id}"
    lock = self.redis.lock(lock_key, timeout=10)
    
    if lock.acquire(blocking=True, blocking_timeout=5):
        try:
            with self.db.get_session() as session:
                ticket = session.get(Ticket, ticket_id)
                if ticket.status != "done":  # Idempotency check
                    ticket.status = "done"
                    session.commit()
        finally:
            lock.release()
```

**Pros**: Both systems can coexist  
**Cons**: Added complexity, Redis dependency for correctness

### Option C: Optimistic Locking with Version Column

Add a `version` column to Ticket model:

```python
class Ticket(Base):
    version: Mapped[int] = mapped_column(default=0)

async def move_to_done(self, ticket_id: str, expected_version: int):
    result = session.execute(
        update(Ticket)
        .where(Ticket.id == ticket_id)
        .where(Ticket.version == expected_version)
        .values(status="done", version=expected_version + 1)
    )
    if result.rowcount == 0:
        raise ConcurrentModificationError()
```

**Pros**: Database-native, no Redis dependency  
**Cons**: Requires schema migration, retry logic

### Option D: Clean Up Dead Code

If the worker is polling-based by design, remove the misleading event subscriptions:

```python
# orchestrator_worker.py - Remove lines 333-341
# These subscriptions never fire anyway
```

---

## File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `api/main.py` | 656-944 | API Server lifespan initialization |
| `workers/orchestrator_worker.py` | 1263-1417 | Worker initialization |
| `services/event_bus.py` | 1-157 | Redis pub/sub service |
| `services/phase_manager.py` | 1038-1128 | API's phase transition handler |
| `services/phase_progression_service.py` | 123-420 | Worker's phase transition handler |
| `services/task_queue.py` | 260-310 | Task claiming (correct implementation) |

---

## Action Items

| Priority | Issue | Recommended Fix | Effort |
|----------|-------|-----------------|--------|
| 🔴 P0 | Duplicate TASK_COMPLETED handlers | Option A: Remove from API Server | 1 hour |
| 🔴 P0 | Dead event subscriptions in worker | Option D: Remove or implement listen() | 30 min |
| 🟡 P1 | No ticket update locking | Option C: Add version column | 4 hours |

---

## Conclusion

The parallel systems have **critical race conditions** that will cause unpredictable behavior when:
1. Tasks complete (both systems try to move tickets to "done")
2. Multiple tickets are processed simultaneously

**Immediate action required** before production use:
1. Choose ONE system to handle phase transitions
2. Remove dead code (subscriptions that never fire)
3. Add proper locking for ticket status updates
