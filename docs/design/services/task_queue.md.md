# Task Queue Management Design Document

**Created**: 2025-11-20
**Status**: Draft
**Purpose**: Design specification for the Task Queue Management service handling scheduling, assignment, capacity, branching, and memory system integration.
**Related**: docs/requirements/workflows/task_queue_management.md, docs/design/multi_agent_orchestration.md, docs/requirements/agents/lifecycle_management.md, docs/requirements/workflows/ticket_workflow.md, docs/requirements/monitoring/fault_tolerance.md, docs/requirements/integration/mcp_servers.md, docs/requirements/memory/memory_system.md

---


## Document Overview

This design document specifies the architecture, components, data flows, and implementation patterns for the Task Queue Management subsystem that powers multi-agent workflows. It defines the queue service architecture, task data model, priority scoring algorithm, assignment logic, capacity semantics, discovery-driven branching, validation feedback loops, API surface, WebSocket events, and Memory System integration.

**Target Audience**

- AI spec agents and system architects designing orchestration behavior
- Backend engineers implementing the queue and scheduling services
- Monitoring and fault-tolerance engineers integrating metrics and alerts

**Related Documents**

- Requirements: `docs/requirements/workflows/task_queue_management.md`
- Orchestration Design: `docs/design/multi_agent_orchestration.md`
- Agent Lifecycle Requirements: `docs/requirements/agents/lifecycle_management.md`
- Ticket Workflow Requirements: `docs/requirements/workflows/ticket_workflow.md`
- Fault Tolerance Requirements: `docs/requirements/monitoring/fault_tolerance.md`
- MCP Integration Requirements: `docs/requirements/integration/mcp_servers.md`
- Memory System Requirements: `docs/requirements/memory/memory_system.md` (for REQ-TQM-MEM-001/002)

---

## Architecture Overview

### High-Level Architecture

```mermaid
flowchart LR
    subgraph Clients
        UI[Queue UI / Ticket Board]
        Agents[Worker Agents]
        Guardian[Guardian / Monitoring Agents]
    end

    subgraph QueueService["Task Queue Management Service"]
        Scheduler[Scheduler & Scoring Engine]
        QueueStore[Queue Store & Indexes]
        CapacityMgr[Capacity Manager]
        AssignLogic[Assignment & Eligibility Engine]
        Branching[Discovery & Branching Engine]
        Feedback[Validation Feedback Controller]
        API[HTTP API Layer]
        WS[WebSocket/Event Gateway]
        MemInt[Memory Integration Adapter]
    end

    StateStore[(State Store\n(PostgreSQL))]
    EventBus[[Event Bus]]
    MemorySys[(Memory System)]

    UI <--> API
    Agents <--> API
    Guardian <--> API

    API --> Scheduler
    API --> CapacityMgr
    API --> Feedback
    API --> Branching

    Scheduler <--> QueueStore
    CapacityMgr <--> QueueStore
    AssignLogic <--> QueueStore

    QueueStore <--> StateStore

    Scheduler --> EventBus
    AssignLogic --> EventBus
    Feedback --> EventBus
    Branching --> EventBus
    EventBus --> WS

    MemInt --> MemorySys
    Feedback --> MemInt
    Branching --> MemInt

    Agents <-->|task assignment/results| AssignLogic
```

### Component Responsibilities

| Component                    | Layer            | Responsibility                                                                                         |
|-----------------------------|------------------|--------------------------------------------------------------------------------------------------------|
| HTTP API Layer              | Interface        | Expose queue_status, bump, cancel, restart, terminate endpoints                                       |
| WebSocket/Event Gateway     | Interface        | Fan-out normative task/agent queue events to UI clients                                               |
| Queue Store & Indexes       | Persistence      | Persist `Task`, `TaskResult`, queue position, priority flags, indexes on status/priority/phase/ticket |
| Scheduler & Scoring Engine  | Core             | Compute composite scores, SLA boosts, starvation floors, and choose next queued task                  |
| Assignment & Eligibility    | Core             | Match tasks to agents (phase & capabilities), enforce dependency barriers and fair-share rules        |
| Capacity Manager            | Core             | Enforce MAX_CONCURRENT_AGENTS, determine under/at capacity, auto-processing triggers                  |
| Discovery & Branching       | Core             | Turn `Discovery` outputs into spawned tasks with parent/child linkage and metadata propagation        |
| Validation Feedback Ctrl    | Core             | Implement auto-fix and re-validation flows, retry budgets, infinite-loop protection                   |
| Memory Integration Adapter  | Integration      | Persist discoveries/errors to Memory System and pre-load context on assignment                        |
| State Store (PostgreSQL)    | Infrastructure   | Durable storage, ACID semantics, and query indexes for low-latency queue operations                   |
| Event Bus                   | Infrastructure   | Publish internal events (`task.created`, `task.queued`, `agent.created`, etc.) for cross-system use   |

### System Boundaries

- **Inside scope**
  - Task lifecycle from `PENDING`/`QUEUED` through assignment to completion/failure.
  - Scheduling and priority/scoring, capacity and auto-processing semantics.
  - Branching tasks based on discoveries and validation feedback loops.
  - Queue-centric APIs and UI-facing WebSocket events.

- **Outside scope**
  - Ticket-level Kanban workflow (covered by Ticket Workflow design).
  - Detailed Agent lifecycle protocols (covered by Agent Lifecycle design).
  - Underlying Memory System implementation.
  - Low-level infrastructure (actual DB deployment, event bus choice).

---

## Component Details

### Queue Store & Indexes

- Persists the `Task` and `TaskResult` models as specified in REQ-TQM-DM-001/002/DM-003.
- Maintains:
  - Primary key on `id`.
  - Composite indexes `(status, priority, phase_id)` and `(ticket_id)`.
  - Additional columns for queue alignment (`queued_at`, `queue_position`, `priority_boosted`).

**Key Responsibilities**

- Provide fast retrieval of:
  - Eligible tasks for scheduling (by status, priority, phase, tenant).
  - Tasks for a given ticket.
  - Parent/child task trees for discovery and validation flows.

### Scheduler & Scoring Engine

Implements REQ-TQM-PRI-002/003/004:

- Computes composite `score`:

  \[
  score = w_p P(priority) + w_a A(age) + w_d D(deadline\_slack) + w_b B(blocker\_count) + w_r R(retry\_penalty)
  \]

- Applies SLA urgency boost and starvation floor:
  - SLA boost when `deadline_at` within `SLA_URGENCY_WINDOW`.
  - Floor score applied when waiting time exceeds `STARVATION_LIMIT`.

Runs in two modes:

- **On-demand**: when an agent requests a task or queue processing is triggered.
- **Scheduled**: periodic re-scoring of a `MAX_QUEUE_SCAN_BATCH` subset for large queues.

### Assignment & Eligibility Engine

Implements REQ-TQM-ASSIGN-001/002/003/004/005:

- Filters tasks by:
  - Phase compatibility (`phase_id` vs agent’s configured phase).
  - Required capabilities vs agent capabilities (from agent type config).
  - Dependency barrier (all `dependencies` are `COMPLETED`).
  - Tenant fair-share constraints.

Supports **pull-first** model:

- Agent calls `assign_task_to_agent(agent_id)` (pull).
- Orchestrator **may** call into assignment engine to push hot-path tasks (e.g., CRITICAL with imminent SLA).

### Capacity Manager

Implements REQ-TQM-CAP-001/002/003:

- Tracks:
  - `active_agents` for task execution.
  - `max_concurrent_agents` (from configuration).
- Decides:
  - Under capacity: tasks started immediately after enrichment (`pending → assigned → in_progress`).
  - At capacity: tasks enriched and set `status=QUEUED` (stored in queue with `queued_at`, `queue_position`).

Auto-processing triggers:

- On `task_completed`, `task_failed`, or `agent_terminated`, or periodic poll:
  - If `active_agents < max_concurrent_agents`, choose next eligible queued task and start it.

### Discovery & Branching Engine

Implements REQ-TQM-BR-001/002/003:

- Converts `TaskResult.discoveries` into new tasks using mapping from discovery type to phase/priority.
- Ensures:
  - `parent_task_id` set to originating task (branch linkage).
  - Inherits `ticket_id` for same-ticket discoveries.
  - Cross-ticket creation only allowed when an external guardian/approval signals so.

### Validation Feedback Controller

Implements REQ-TQM-VF-001/002/003:

- On `validation_failed == true`:
  - Creates HIGH priority `PHASE_IMPLEMENTATION` fix task.
  - Creates follow-up `PHASE_VALIDATION` re-check task.
  - Links tasks via `parent_task_id`.
- Tracks `retry_count` vs `max_retries`.
- Uses failure signature tracking to stop infinite loops and escalate to guardian/human when exceeded.

### Memory Integration Adapter

Implements REQ-TQM-MEM-001/002:

- After task completion with discoveries/errors, builds memory payload and calls Memory System:
  - Includes goal/description, result summary, `ticket_id`, file paths, discoveries/issues.
- On assignment, optionally queries Memory System:
  - “Context for task” based on ticket and description; attaches to task metadata or agent context.

---

## Data Models

### Database Schema (PostgreSQL)

This extends the orchestrator’s existing `tasks` table to fully satisfy REQ-TQM-DM-001/002/003 and queue alignment fields.

```sql
CREATE TYPE phase_enum AS ENUM (
  'REQUIREMENTS', 'IMPLEMENTATION', 'VALIDATION', 'ANALYSIS', 'TESTING'
);

CREATE TYPE priority_enum AS ENUM (
  'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
);

CREATE TYPE task_status_enum AS ENUM (
  'PENDING', 'QUEUED', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED'
);

CREATE TABLE tasks (
  id UUID PRIMARY KEY,
  ticket_id UUID NOT NULL REFERENCES tickets(id),
  phase_id phase_enum NOT NULL,
  description TEXT NOT NULL,
  priority priority_enum NOT NULL,
  score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  status task_status_enum NOT NULL DEFAULT 'PENDING',
  assigned_agent_id UUID REFERENCES agents(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  retry_count INTEGER NOT NULL DEFAULT 0,
  max_retries INTEGER NOT NULL DEFAULT 3,
  deadline_at TIMESTAMPTZ,
  dependencies UUID[] NOT NULL DEFAULT '{}',
  parent_task_id UUID REFERENCES tasks(id),
  result JSONB,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  -- Queue alignment fields
  queued_at TIMESTAMPTZ,
  queue_position INTEGER,
  priority_boosted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE task_results (
  task_id UUID PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
  success BOOLEAN NOT NULL,
  output JSONB,
  discoveries JSONB,
  validation_failed BOOLEAN NOT NULL DEFAULT FALSE,
  errors TEXT[] NOT NULL DEFAULT '{}',
  metrics JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Required indexes (REQ-TQM-DM-003)
CREATE INDEX idx_tasks_status_priority_phase
  ON tasks(status, priority, phase_id);

CREATE INDEX idx_tasks_ticket_id
  ON tasks(ticket_id);

-- Queue-related indexes for low-latency scheduling
CREATE INDEX idx_tasks_queued
  ON tasks(status, priority_boosted DESC, priority, queued_at)
  WHERE status = 'QUEUED';

CREATE INDEX idx_tasks_deadline
  ON tasks(deadline_at)
  WHERE status IN ('PENDING', 'QUEUED');
```

### Pydantic Models

The runtime models follow the reference in the requirements with queue alignment fields included.

```python
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PhaseEnum(str, Enum):
    REQUIREMENTS = "REQUIREMENTS"
    IMPLEMENTATION = "IMPLEMENTATION"
    VALIDATION = "VALIDATION"
    ANALYSIS = "ANALYSIS"
    TESTING = "TESTING"


class PriorityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TaskStatusEnum(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class DiscoveryType(str, Enum):
    SECURITY_ISSUE = "security_issue"
    REQUIRES_CLARIFICATION = "requires_clarification"
    OPTIMIZATION_OPPORTUNITY = "optimization_opportunity"


class Discovery(BaseModel):
    type: DiscoveryType
    details: str
    severity: PriorityEnum = Field(default=PriorityEnum.MEDIUM)
    suggested_action: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    success: bool
    output: Any | None = None
    discoveries: List[Discovery] = Field(default_factory=list)
    validation_failed: bool = False
    errors: List[str] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(default_factory=dict)


class Task(BaseModel):
    id: str
    ticket_id: str
    phase_id: PhaseEnum
    description: str
    priority: PriorityEnum
    score: float = 0.0
    status: TaskStatusEnum = TaskStatusEnum.PENDING
    assigned_agent_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    deadline_at: Optional[datetime] = None
    dependencies: List[str] = Field(default_factory=list)
    parent_task_id: Optional[str] = None
    result: Optional[TaskResult] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    queued_at: Optional[datetime] = None
    queue_position: Optional[int] = None
    priority_boosted: bool = False


class QueueStatus(BaseModel):
    active_agents: int
    max_concurrent_agents: int
    at_capacity: bool
    queued_tasks: List[str] = Field(default_factory=list)
```

---

## API Specifications

### Overview

All Task Queue Management APIs are scoped under `/api/` and are consistent with REQ-TQM-PROC-* and REQ-TQM endpoints list.

#### Endpoint Table

| Endpoint                 | Method | Purpose                               | Bypass Limit | Auth Required |
|--------------------------|--------|---------------------------------------|--------------|--------------|
| `/api/queue_status`      | GET    | Return queue state & capacity info    | N/A          | Yes          |
| `/api/bump_task_priority`| POST   | Bump & Start queued task immediately  | Yes          | Yes (admin)  |
| `/api/cancel_queued_task`| POST   | Remove task from queue                | N/A          | Yes          |
| `/api/restart_task`      | POST   | Restart done/failed task (no bypass)  | No           | Yes          |
| `/api/terminate_agent`   | POST   | Terminate running agent               | N/A          | Yes (admin)  |

All requests MUST include:

- `X-Correlation-Id` header for tracing.
- Auth context (e.g., `Authorization` header) for RBAC.

### `/api/queue_status` (GET)

**Purpose**: Returns current queue and capacity snapshot.

**Response 200**

```json
{
  "active_agents": 7,
  "max_concurrent_agents": 10,
  "at_capacity": false,
  "queued_depth": 12,
  "queued_by_priority": {
    "CRITICAL": 1,
    "HIGH": 5,
    "MEDIUM": 4,
    "LOW": 2
  },
  "oldest_wait_seconds": 320,
  "critical_backlog_seconds": 0
}
```

### `/api/bump_task_priority` (POST)

Implements REQ-TQM-BUMP-001/002/003 (manual priority bypass).

**Request**

```json
{
  "task_id": "uuid",
  "reason": "Pager alert for critical production outage"
}
```

**Behavior**

- Validates `BUMP_AND_START_ENABLED` and that over-capacity will not exceed `MAX_CONCURRENT_AGENTS + OVERCAP_LIMIT`.
- Updates:
  - `priority_boosted = true`
  - Moves task to `queue_position = 1` if still queued.
- If task is `QUEUED`, immediately:
  - Starts agent even if at capacity (temporary over-commit).
  - Publishes `task_priority_bumped`, `agent_created`, and `task_started` events.

**Response 200**

```json
{
  "task_id": "uuid",
  "agent_id": "agent-123",
  "over_capacity": true,
  "active_agents": 11,
  "max_concurrent_agents": 10
}
```

### `/api/cancel_queued_task` (POST)

**Request**

```json
{
  "task_id": "uuid"
}
```

**Behavior**

- Only tasks in `QUEUED` or `PENDING` can be cancelled.
- Sets status to `CANCELLED`, removes from queue, logs audit event.

**Response 200**

```json
{
  "task_id": "uuid",
  "status": "CANCELLED"
}
```

### `/api/restart_task` (POST)

**Request**

```json
{
  "task_id": "uuid",
  "reason": "Manual re-run after config fix"
}
```

**Behavior**

- Only `COMPLETED` or `FAILED` tasks are eligible.
- Creates a new task instance or resets original task based on configuration:
  - Recommended: create new task with `parent_task_id` = original; copy metadata and increase `retry_count`.
- Does **not** bypass capacity; task is treated as normal queued or pending.

**Response 200**

```json
{
  "original_task_id": "uuid",
  "new_task_id": "uuid2",
  "queued": true
}
```

### `/api/terminate_agent` (POST)

**Request**

```json
{
  "agent_id": "agent-123",
  "reason": "Stuck in loop / runaway behavior"
}
```

**Behavior**

- Terminates running agent (with Agent Lifecycle system), marks associated task `FAILED`.
- Triggers queue processing (REQ-TQM-CAP-003/PROC-001).

**Response 202**

```json
{
  "agent_id": "agent-123",
  "terminated": true,
  "reassigned_tasks": ["task-1", "task-2"]
}
```

---

## WebSocket Events

Implements REQ-TQM WebSocket events.

### Event Table

| Event                 | When Emitted                        | Payload (min)                                                                 |
|-----------------------|-------------------------------------|-------------------------------------------------------------------------------|
| `task_queued`         | Task added to queue                 | `task_id`, `description`, `queue_position`, `slots_available`                |
| `task_created`        | New task created                    | `task_id`, `description`, `agent_id?`                                        |
| `task_completed`      | Task finished                       | `task_id`, `agent_id`, `status`, `summary`                                   |
| `task_priority_bumped`| Task started via bump & start       | `task_id`, `agent_id`                                                        |
| `agent_created`       | New agent spawned for a task        | `agent_id`, `task_id`                                                        |
| `agent_status_changed`| Agent status updated                | `agent_id`, `status`                                                         |

Example payload for `task_queued`:

```json
{
  "event": "task_queued",
  "timestamp": "2025-11-16T12:00:00Z",
  "payload": {
    "task_id": "uuid",
    "description": "Implement fix for validation failures",
    "queue_position": 3,
    "slots_available": 2
  }
}
```

---

## Implementation Details

### Priority Scoring Algorithm

**Inputs**

- Static priority enum.
- `age_seconds` since `created_at`.
- Deadline slack \(= deadline\_at - now\).
- `blocker_count` (number of tasks unblocked by this task completing).
- `retry_penalty` (derived from `retry_count` vs `max_retries`).

**Pseudocode**

```python
def compute_task_score(task: Task, now: datetime, config: SchedulerConfig) -> float:
    age_seconds = (now - task.created_at).total_seconds()
    age_norm = min(age_seconds / config.AGE_CEILING, 1.0)

    if task.deadline_at:
        slack_seconds = (task.deadline_at - now).total_seconds()
        if slack_seconds <= 0:
            deadline_norm = 1.0
        else:
            deadline_norm = max(0.0, 1.0 - slack_seconds / config.SLA_URGENCY_WINDOW)
    else:
        deadline_norm = 0.0

    blocker_count = get_blocker_count(task.id)
    blocker_norm = min(blocker_count / config.BLOCKER_CEILING, 1.0)

    retry_ratio = task.retry_count / max(task.max_retries, 1)
    retry_penalty = max(0.0, 1.0 - retry_ratio)

    priority_map = {
        PriorityEnum.CRITICAL: 1.0,
        PriorityEnum.HIGH: 0.75,
        PriorityEnum.MEDIUM: 0.5,
        PriorityEnum.LOW: 0.25,
    }

    base_score = (
        config.w_p * priority_map[task.priority]
        + config.w_a * age_norm
        + config.w_d * deadline_norm
        + config.w_b * blocker_norm
        + config.w_r * retry_penalty
    )

    if task.deadline_at and 0 <= (task.deadline_at - now).total_seconds() <= config.SLA_URGENCY_WINDOW:
        base_score *= config.SLA_BOOST_MULTIPLIER

    wait_seconds = (now - task.created_at).total_seconds()
    if wait_seconds >= config.STARVATION_LIMIT:
        base_score = max(base_score, config.STARVATION_FLOOR_SCORE)

    return base_score
```

### Assignment Logic (Pull-First)

```python
async def assign_task_to_agent(agent_id: str) -> Optional[Task]:
    agent = await state_store.get_agent(agent_id)
    eligible_tasks = await queue_store.fetch_eligible_tasks(
        phase_id=agent.phase_id,
        capabilities=agent.capabilities,
        tenant_id=agent.tenant_id,
        limit=config.MAX_QUEUE_SCAN_BATCH,
    )
    scored = [(compute_task_score(t), t) for t in eligible_tasks]
    scored.sort(key=lambda x: x[0], reverse=True)

    for score, task in scored:
        if not dependencies_satisfied(task):
            continue
        if not fair_share_allows(task, agent.tenant_id):
            continue
        await state_store.assign_task(task.id, agent_id, score)
        await capacity_manager.on_task_started()
        event_bus.publish(EventType.TASK_ASSIGNED, {"task_id": task.id, "agent_id": agent_id})
        return task

    return None
```

### Capacity & Auto-Processing Flow

Implements REQ-TQM-CAP-003 and REQ-TQM-PROC-001/002.

```python
async def process_queue_trigger(reason: str) -> None:
    if capacity_manager.is_at_capacity():
        return

    next_task = await queue_store.get_next_queued_task()
    if not next_task:
        return

    await queue_store.dequeue_task(next_task.id)
    agent_id = await agent_pool.spawn_agent_for_phase(next_task.phase_id)
    await state_store.assign_task(next_task.id, agent_id)
    await capacity_manager.on_task_started()
    event_bus.publish(EventType.AGENT_CREATED, {"agent_id": agent_id, "task_id": next_task.id})
```

Queue ordering is:

1. `priority_boosted = TRUE` tasks (Bump & Start).
2. Higher `priority`.
3. Earlier `queued_at` (FIFO).

### Discovery-Driven Branching

```python
async def process_discoveries(task: Task, result: TaskResult) -> None:
    for discovery in result.discoveries:
        new_task = build_task_from_discovery(task, discovery)
        await state_store.create_task(new_task)
        await queue_store.enqueue(new_task)
        event_bus.publish(EventType.TASK_CREATED, {"task_id": new_task.id})
        ws_gateway.broadcast("task_created", {"task_id": new_task.id, "description": new_task.description})
```

`build_task_from_discovery` maps `DiscoveryType` to target phase and priority per REQ-TQM-BR-001 and sets `parent_task_id` and metadata.

### Validation Feedback Loop & Loop Breakers

```python
async def handle_validation_feedback(task: Task, result: TaskResult) -> None:
    if not result.validation_failed:
        clear_failure_signature(task.id)
        return

    signature = compute_failure_signature(task, result)
    count = increment_failure_signature(signature)

    if count >= config.REPEAT_SIGNATURE_LIMIT:
        await guardian_escalate(task, result, signature)
        return

    if task.retry_count >= task.max_retries:
        await guardian_escalate(task, result, signature)
        return

    fix_task = Task(
        id=uuid4_str(),
        ticket_id=task.ticket_id,
        phase_id=PhaseEnum.IMPLEMENTATION,
        description=f"Fix issues for: {task.description}",
        priority=PriorityEnum.HIGH,
        parent_task_id=task.id,
        retry_count=task.retry_count + 1,
        metadata={"original_task_id": task.id},
        created_at=now(),
    )
    revalidate_task = Task(
        id=uuid4_str(),
        ticket_id=task.ticket_id,
        phase_id=PhaseEnum.VALIDATION,
        description=f"Re-validate: {task.description}",
        priority=PriorityEnum.HIGH,
        parent_task_id=fix_task.id,
        created_at=now(),
    )

    await state_store.create_task(fix_task)
    await queue_store.enqueue(fix_task)
    await state_store.create_task(revalidate_task)
    await queue_store.enqueue(revalidate_task)
```

---

## Integration Points

### Memory System Integration (REQ-TQM-MEM-001/002)

- **On completion**:
  - When `TaskResult.discoveries` or `errors` non-empty:
    - Build memory:

      ```json
      {
        "type": "task_discovery",
        "ticket_id": "uuid",
        "task_id": "uuid",
        "goal": "Task description",
        "result_summary": "Short outcome summary",
        "discoveries": [...],
        "errors": [...],
        "affected_files": [...]
      }
      ```

    - Call Memory System `create_memory` / ACE API.
- **On assignment**:
  - Optional pre-fetch:

    ```python
    context_memories = memory_client.get_context_for_task(
        ticket_id=task.ticket_id,
        description=task.description,
        limit=config.MEM_CONTEXT_LIMIT,
    )
    task.metadata["memory_context"] = context_memories
    ```

### Agent Lifecycle Integration

- Uses Agent Lifecycle service to:
  - Spawn worker agents for tasks based on phase and capabilities.
  - Track `active_agents` count.
  - Handle agent termination events, which trigger queue processing.

### Ticket Workflow Integration

- Each `Task.ticket_id` links to the Ticket system.
- Ticket phases (Kanban) control which `phase_id` tasks are generated.
- Task queue feeds progress into Ticket Workflow for phase transitions.

### Monitoring & Fault Tolerance Integration

- Exposes metrics:

  - `task_queue_depth{priority,phase}`
  - `task_fetch_latency`
  - `task_retry_count`
  - `task_starvation_count`

- Fault Tolerance uses these metrics and internal events to detect backlog, starvation, or excessive retries.

---

## Configuration Parameters

Aligned with §7 of the requirements.

```python
class TaskQueueConfig(BaseSettings):
    AGE_CEILING: int = 3600
    SLA_URGENCY_WINDOW: int = 900
    STARVATION_LIMIT: int = 7200
    AGENT_TASK_BACKOFF_WINDOW: int = 1800
    MAX_QUEUE_SCAN_BATCH: int = 200
    MAX_CONCURRENT_AGENTS: int = 10
    BUMP_AND_START_ENABLED: bool = True
    OVERCAP_LIMIT: int = 1

    # Scoring weights
    w_p: float = 0.45
    w_a: float = 0.20
    w_d: float = 0.15
    w_b: float = 0.15
    w_r: float = 0.05

    SLA_BOOST_MULTIPLIER: float = 1.25
    STARVATION_FLOOR_SCORE: float = 0.6
    BLOCKER_CEILING: int = 10

    class Config:
        env_prefix = "TQ_"
```

---

## Related Documents

- Requirements: `docs/requirements/workflows/task_queue_management.md`
- Multi-Agent Orchestration Design: `docs/design/multi_agent_orchestration.md`
- Ticket Workflow Requirements: `docs/requirements/workflows/ticket_workflow.md`
- Agent Lifecycle Requirements: `docs/requirements/agents/lifecycle_management.md`
- Monitoring & Fault Tolerance Requirements: `docs/requirements/monitoring/fault_tolerance.md`
- Memory System Requirements: `docs/requirements/memory/memory_system.md`

---

## Quality Checklist (Job 6)

- [x] All requirements from `task_queue_management.md` addressed:
  - Task data model, results, indexing
  - Composite scoring, SLA boost, starvation guard
  - Assignment, dependency barrier, fair-share & backoff
  - Capacity semantics and auto-processing triggers
  - Bump & Start implementation with guardrails
  - Discovery-driven branching and parent-child linkage
  - Validation feedback loops, retry budget, loop breakers
  - Normative API endpoints and WebSocket events
  - Memory integration (REQ-TQM-MEM-001/002)
  - Metrics and configuration parameters
- [x] Architecture and flow diagrams included (Mermaid).
- [x] API specifications match normative endpoints.
- [x] Database schemas and Pydantic models match requirements.
- [x] Integration points documented with related subsystems.
- [x] Configuration parameters aligned with requirements.


