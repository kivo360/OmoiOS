# Existing Systems Integration Guide

**Status**: Draft  
**Last Updated**: 2024-12-12  
**Purpose**: Document how existing systems work and how they need to change to support sandbox agents

---

## Overview

This document provides context on existing systems in the codebase that interact with agents and explains how they need to be modified to support the new sandbox-based agent execution model.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SYSTEMS INTEGRATION MAP                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  EXISTING SYSTEMS              SANDBOX CHANGES NEEDED          PHASE        │
│  ────────────────              ───────────────────────         ─────        │
│                                                                             │
│  IntelligentGuardian           Add sandbox-aware routing        Phase 6     │
│  ConversationInterventionSvc   Keep for legacy, bypass          Phase 6     │
│  AgentRegistryService          Minor awareness                  Optional    │
│  TaskQueueService              Works as-is ✅                   -           │
│  EventBusService               Works as-is ✅                   -           │
│  DaytonaSpawnerService         Already sandbox-native ✅        -           │
│  Worker (worker.py)            Legacy only, not for sandbox     -           │
│                                                                             │
│  FAULT TOLERANCE SYSTEMS       SANDBOX CHANGES NEEDED          PHASE        │
│  ───────────────────────       ───────────────────────         ─────        │
│                                                                             │
│  HeartbeatAnalyzer             Check sandbox event timestamps   Phase 7     │
│  RestartOrchestrator           Call DaytonaSpawner for restart  Phase 7     │
│  TrajectoryContextBuilder      Read from event store            Phase 7     │
│  ForensicsCollector            Pull from sandbox before term.   Phase 7     │
│  CooldownManager               Works as-is ✅                   -           │
│                                                                             │
│  DATABASE MODELS               CHANGES NEEDED                   PHASE        │
│  ────────────────              ──────────────                   ─────        │
│                                                                             │
│  Task                          Add sandbox_id field             Phase 6     │
│  Agent                         Works as-is ✅                   -           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. IntelligentGuardian

### Current Behavior

**Location**: `backend/omoi_os/services/intelligent_guardian.py`

The IntelligentGuardian provides LLM-powered monitoring of agent trajectories. It detects when agents are:
- **Drifting** from task objectives
- **Stuck** in repetitive loops
- **Making mistakes** that could be costly

When intervention is needed, it creates a `SteeringIntervention` and calls `execute_steering_intervention()`.

### How It Works Today

```python
# Current flow in execute_steering_intervention()

async def execute_steering_intervention(self, intervention, task=None):
    if not task or not task.conversation_id or not task.persistence_dir:
        return False  # Can't intervene without conversation info
    
    workspace_dir = f"/workspace/{task.ticket_id}"
    
    intervention_service = ConversationInterventionService()
    success = intervention_service.send_intervention(
        conversation_id=task.conversation_id,
        persistence_dir=task.persistence_dir,  # LOCAL PATH!
        workspace_dir=workspace_dir,
        message=intervention.message,
    )
```

**Key Dependency**: Requires `persistence_dir` to be a **local filesystem path** where OpenHands conversation state is stored.

### Problem with Sandbox Agents

Sandbox agents run inside Daytona containers. Their conversation state (`persistence_dir`) is at `/tmp/openhands/` **inside the sandbox**, not on the local filesystem.

```
LOCAL SERVER FILESYSTEM          DAYTONA SANDBOX
─────────────────────────        ────────────────
                                 ┌─────────────────────────┐
/tmp/openhands/ ← EMPTY!         │ /tmp/openhands/         │
                                 │   ├── conv-abc123/      │
                                 │   │   ├── state.json    │
                                 │   │   └── history/      │
                                 │   └── ...               │
                                 └─────────────────────────┘
```

### Required Changes

1. **Add `_is_sandbox_task()` method** to detect sandbox execution mode
2. **Add `_sandbox_intervention()` method** that uses HTTP message injection
3. **Update `execute_steering_intervention()`** to route appropriately

```python
# Updated flow

async def execute_steering_intervention(self, intervention, task=None):
    if not task:
        task = self._get_task_for_agent(intervention.agent_id)
    
    if self._is_sandbox_task(task):
        # Sandbox mode: use HTTP message injection
        return await self._sandbox_intervention(
            sandbox_id=task.sandbox_id,
            message=intervention.message,
        )
    else:
        # Legacy mode: use local filesystem
        return await self._legacy_intervention(task, intervention.message)
```

---

## 2. ConversationInterventionService

### Current Behavior

**Location**: `backend/omoi_os/services/conversation_intervention.py`

This service is specifically designed to inject messages into running OpenHands conversations by:
1. Loading conversation state from local `persistence_dir`
2. Creating a `Conversation` object
3. Calling `conversation.send_message()`

### How It Works Today

```python
class ConversationInterventionService:
    def send_intervention(
        self,
        conversation_id: str,
        persistence_dir: str,  # Must be local path!
        workspace_dir: str,
        message: str,
    ) -> bool:
        intervention_agent = Agent(...)
        intervention_message = Message(...)
        
        conversation = Conversation(
            conversation_id=conversation_id,
            persistence_dir=persistence_dir,  # Loads from local FS
            agent=intervention_agent,
            workspace=workspace_dir,
        )
        
        conversation.send_message(intervention_message)
```

### Impact on Sandbox Agents

This service **cannot be used for sandbox agents** because:
- It requires local filesystem access
- Sandbox conversation state is remote

### Required Changes

**No changes needed to this service.** It will continue to serve legacy agents.

The Guardian will bypass this service for sandbox agents and use HTTP message injection directly.

---

## 3. AgentRegistryService

### Current Behavior

**Location**: `backend/omoi_os/services/agent_registry.py`

Provides capability-aware agent registration and discovery:
- CRUD operations for agents
- Capability matching
- Pre-registration validation

### How It Works Today

```python
class AgentRegistryService:
    def register_agent(self, agent_type, phase_id, capabilities=None) -> str:
        # Creates agent record
        # Returns agent_id
    
    def find_capable_agent(self, required_capabilities) -> Optional[Agent]:
        # Finds agent with matching capabilities
    
    def get_available_agent(self) -> Optional[Agent]:
        # Gets first available agent
```

### Impact on Sandbox Agents

The registry doesn't need to know about sandbox execution mode at the registration level. The execution mode is determined at task assignment time by the orchestrator.

### Required Changes

**Minor or no changes needed.**

Optionally, could add an `execution_mode` field to track whether an agent is currently running in sandbox mode, but this isn't strictly necessary since the Task model tracks `sandbox_id`.

---

## 4. TaskQueueService

### Current Behavior

**Location**: `backend/omoi_os/services/task_queue.py`

Manages task queue operations:
- Enqueueing tasks with dependencies
- Retrieving next executable tasks
- Assigning tasks to agents
- Updating task status
- Publishing task events

### How It Works Today

```python
class TaskQueueService:
    def enqueue_task(self, task: Task) -> bool:
        # Adds task to queue
        # Publishes TASK_QUEUED event
    
    def get_next_task(self) -> Optional[Task]:
        # Gets highest priority task with resolved dependencies
    
    def assign_task(self, task_id, agent_id) -> bool:
        # Marks task as assigned
        # Publishes TASK_ASSIGNED event
```

### Impact on Sandbox Agents

**No changes needed.** The queue service is execution-mode agnostic. It manages task lifecycle regardless of how the task is executed.

---

## 5. EventBusService

### Current Behavior

**Location**: `backend/omoi_os/services/event_bus.py`

Provides system-wide event publishing using Redis Pub/Sub:
- Publishes `SystemEvent` objects
- Broadcasts to all subscribers
- WebSocket manager subscribes to relay to frontend

### How It Works Today

```python
@dataclass
class SystemEvent:
    event_type: str
    entity_type: str
    entity_id: str
    payload: dict
    timestamp: datetime

class EventBusService:
    def publish(self, event: SystemEvent):
        # Serializes and publishes to Redis channel
    
    def subscribe(self, callback):
        # Registers callback for incoming events
```

### Impact on Sandbox Agents

**No changes needed.** The event bus is transport-agnostic. Sandbox workers will publish events via HTTP callbacks, which then get relayed to the event bus.

---

## 6. DaytonaSpawnerService

### Current Behavior

**Location**: `backend/omoi_os/services/daytona_spawner.py`

Manages Daytona sandbox lifecycle:
- Creates sandboxes for tasks
- Injects environment variables
- Uploads worker scripts
- Terminates sandboxes

### How It Works Today

```python
class DaytonaSpawnerService:
    async def spawn_for_task(
        self,
        task_id: str,
        agent_id: str,
        phase_id: str,
        agent_type: str,
    ) -> str:
        # Creates Daytona sandbox
        # Injects env vars (OMOI_TASK_ID, API_BASE_URL, etc.)
        # Uploads worker script
        # Starts execution
        # Returns sandbox_id
```

### Impact on Sandbox Agents

**This is already sandbox-native.** It's the core of the new execution model.

### Required Changes

**Minor**: Update the spawner to:
1. Set `task.sandbox_id` after creating sandbox
2. Use the new event callback endpoints instead of legacy ones

---

## 7. Worker Service (Legacy)

### Current Behavior

**Location**: `backend/omoi_os/worker.py`

The legacy worker service that runs on the local server:
- Heartbeat management
- Task execution loop
- Direct database access

### How It Works Today

```python
class HeartbeatManager:
    def start(self):
        # Starts heartbeat thread
        # Adaptive frequency based on server load

def main():
    agent_id = register_agent(...)
    heartbeat_manager = HeartbeatManager(agent_id, health_service)
    heartbeat_manager.start()
    
    while True:
        task = get_next_task()
        execute_task(task)
```

### Impact on Sandbox Agents

**Not used for sandbox agents.** This is the legacy execution path.

The orchestrator in `main.py` chooses between:
- **Legacy mode**: Assigns task to local worker
- **Sandbox mode**: Spawns Daytona sandbox

---

## 8. Task Model

### Current State

**Location**: `backend/omoi_os/models/task.py`

```python
class Task(Base):
    __tablename__ = "tasks"
    
    id: Mapped[str] = mapped_column(...)
    ticket_id: Mapped[str] = mapped_column(...)
    phase_id: Mapped[str] = mapped_column(...)
    status: Mapped[str] = mapped_column(...)
    assigned_agent_id: Mapped[Optional[str]] = mapped_column(...)
    conversation_id: Mapped[Optional[str]] = mapped_column(...)  # OpenHands conv ID
    persistence_dir: Mapped[Optional[str]] = mapped_column(...)  # Local path (legacy)
    # sandbox_id is MISSING!
```

### Required Changes

**ADD `sandbox_id` field**:

```python
sandbox_id: Mapped[Optional[str]] = mapped_column(
    String(255),
    nullable=True,
    index=True,
    comment="Daytona sandbox ID if task is running in sandbox mode"
)
```

This field is critical for:
- Guardian mode detection (`task.sandbox_id` presence = sandbox mode)
- Task-to-sandbox association for monitoring
- HTTP endpoint routing for interventions

---

## 9. Orchestrator Loop

### Current Behavior

**Location**: `backend/omoi_os/api/main.py` (in `orchestrator_loop()`)

The orchestrator determines execution mode and routes tasks:

```python
async def orchestrator_loop():
    while True:
        task = queue.get_next_task()
        if not task:
            await asyncio.sleep(1)
            continue
        
        settings = get_app_settings()
        sandbox_execution = settings.daytona.sandbox_execution
        
        if sandbox_execution and daytona_spawner:
            # Sandbox mode
            sandbox_id = await daytona_spawner.spawn_for_task(
                task_id=task.id,
                agent_id=agent_id,
                phase_id=phase_id,
                agent_type=agent_type,
            )
            queue.assign_task(task.id, agent_id)
        else:
            # Legacy mode
            queue.assign_task(task.id, available_agent_id)
```

### Required Changes

**Update to set `task.sandbox_id`**:

```python
if sandbox_execution and daytona_spawner:
    sandbox_id = await daytona_spawner.spawn_for_task(...)
    
    # SET THE SANDBOX_ID ON THE TASK!
    with db.get_session() as session:
        task = session.query(Task).get(task.id)
        task.sandbox_id = sandbox_id
        session.commit()
    
    queue.assign_task(task.id, agent_id)
```

---

## 10. Fault Tolerance Systems (Phase 7 - Full Integration)

> **Note**: This section is for the Full Integration track (Phase 7). MVP can skip this.

### Overview

**Location**: `docs/design/monitoring/fault_tolerance.md`

The fault tolerance system provides automatic detection and recovery for agent failures:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FAULT TOLERANCE COMPONENTS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  HeartbeatAnalyzer                                                          │
│  ├─ Receives heartbeats from agents                                        │
│  ├─ TTL: IDLE=30s, RUNNING=15s                                             │
│  └─ 3 misses → UNRESPONSIVE → restart                                      │
│                                                                             │
│  RestartOrchestrator                                                        │
│  ├─ Step 1: Graceful stop (10s timeout)                                    │
│  ├─ Step 2: Force terminate if needed                                      │
│  ├─ Step 3: Spawn replacement                                              │
│  └─ Step 4: Reassign tasks                                                 │
│                                                                             │
│  TrajectoryContextBuilder                                                   │
│  ├─ Builds context for Guardian analysis                                   │
│  └─ Reads logs, summaries, metrics                                         │
│                                                                             │
│  ForensicsCollector                                                         │
│  ├─ Collects evidence for quarantine                                       │
│  └─ Preserves memory, logs, metrics                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Impact on Sandbox Agents

**Problem**: These systems assume direct access to agent processes/filesystems, which doesn't exist for Daytona sandboxes.

### 10.1 HeartbeatAnalyzer Changes

**Current Behavior**:
- Expects agents to POST heartbeats directly
- Checks last heartbeat timestamp against TTL

**Required Changes for Sandbox**:
```python
# HeartbeatAnalyzer needs to check sandbox events instead

async def check_agent_health(self, agent_id: str) -> bool:
    task = await self._get_task_for_agent(agent_id)
    
    if task.sandbox_id:
        # Sandbox mode: check latest event timestamp
        last_event = await self._get_latest_sandbox_event(task.sandbox_id)
        if last_event:
            elapsed = datetime.utcnow() - last_event.created_at
            return elapsed < self.ttl_thresholds[task.status]
        return False  # No events = unhealthy
    else:
        # Legacy mode: existing heartbeat check
        return await self._legacy_heartbeat_check(agent_id)
```

### 10.2 RestartOrchestrator Changes

**Current Behavior**:
- Calls `graceful_stop()` on agent process
- Spawns new agent via AgentRegistry

**Required Changes for Sandbox**:
```python
async def initiate_restart(self, agent_id: str, reason: str) -> RestartEvent:
    task = await self._get_task_for_agent(agent_id)
    
    if task and task.sandbox_id:
        # Sandbox mode: use DaytonaSpawnerService
        await self.daytona_spawner.terminate_sandbox(task.sandbox_id)
        new_sandbox_id = await self.daytona_spawner.spawn_for_task(
            task_id=str(task.id),
            agent_id=agent_id,
            phase_id=task.phase_id,
            agent_type=task.agent_type,
        )
        task.sandbox_id = new_sandbox_id
        # ...
    else:
        # Legacy mode: existing restart logic
        # ...
```

### 10.3 TrajectoryContextBuilder Changes

**Current Behavior**:
- Reads agent logs from local filesystem
- Tails log files for context

**Required Changes for Sandbox**:
```python
async def build_for_task(self, task: Task) -> AgentTrajectoryContext:
    if task.sandbox_id:
        # Sandbox mode: read from event store (events POSTed by worker)
        events = await self._get_sandbox_events(task.sandbox_id, limit=200)
        logs_snippet = "\n".join(
            f"[{e.event_type}] {e.payload.get('message', '')}"
            for e in events
        )
        return AgentTrajectoryContext(logs_snippet=logs_snippet, ...)
    else:
        # Legacy mode: read from filesystem
        return await self._build_from_filesystem(task)
```

### 10.4 ForensicsCollector Changes (Optional)

**Current Behavior**:
- Preserves memory, logs, metrics from local agent

**Required Changes for Sandbox**:
```python
async def collect_forensics(self, agent_id: str) -> str:
    task = await self._get_task_for_agent(agent_id)
    
    if task.sandbox_id:
        # Sandbox mode: pull data from sandbox before termination
        bundle = {
            'events': await self._get_all_sandbox_events(task.sandbox_id),
            'logs': await self.daytona_spawner.download_file(
                task.sandbox_id, "/tmp/openhands/agent.log"
            ),
            # Note: Some data may not be accessible
        }
    else:
        # Legacy mode: existing collection
        # ...
```

---

## Summary: Changes by System

### Phase 6 (Guardian Integration)

| System | Changes Needed | Effort |
|--------|----------------|--------|
| **IntelligentGuardian** | Add sandbox mode detection & HTTP intervention | 3-4 hrs |
| ConversationInterventionService | None (keep for legacy) | 0 |
| AgentRegistryService | None or minimal | 0-1 hrs |
| TaskQueueService | None | 0 |
| EventBusService | None | 0 |
| DaytonaSpawnerService | Minor updates to use new endpoints | 1 hr |
| **Task Model** | Add `sandbox_id` field + migration | 1 hr |
| **Orchestrator** | Set `task.sandbox_id` after spawn | 0.5 hr |

**Phase 6 Effort**: 5.5-6.5 hours

### Phase 7 (Fault Tolerance Integration)

| System | Changes Needed | Effort |
|--------|----------------|--------|
| **HeartbeatAnalyzer** | Check sandbox event timestamps | 2-3 hrs |
| **RestartOrchestrator** | Call DaytonaSpawner for sandbox restart | 3-4 hrs |
| **TrajectoryContextBuilder** | Read from event store for sandbox | 2-3 hrs |
| ForensicsCollector | Pull from sandbox (optional) | 1-2 hrs |
| Worker Script | Add heartbeat thread | 1 hr |

**Phase 7 Effort**: 8-12 hours

**Total Full Integration Effort**: 13.5-18.5 hours (after MVP)

---

## Integration Testing Checklist

### Phase 6 Tests

- [ ] `task.sandbox_id` is correctly set after sandbox spawn
- [ ] Guardian correctly detects sandbox mode via `_is_sandbox_task()`
- [ ] Guardian interventions reach sandbox agents via message injection
- [ ] Guardian interventions still work for legacy agents
- [ ] No regressions in task assignment flow
- [ ] No regressions in event publishing

### Phase 7 Tests (Full Integration)

- [ ] Sandbox workers send heartbeat events every 15 seconds
- [ ] HeartbeatAnalyzer detects missed sandbox heartbeats
- [ ] RestartOrchestrator correctly terminates and respawns sandbox
- [ ] TrajectoryContextBuilder reads from event store for sandbox tasks
- [ ] End-to-end: heartbeat miss → detection → restart → new sandbox working
