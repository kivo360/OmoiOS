# Task Queue Management Requirements

## Document Overview

This document defines requirements for the end-to-end task queue subsystem that powers multi-agent workflows. It specifies the task data model, priority scoring, assignment logic, discovery-driven branching, and validation feedback loops.

**Parent Document**: [Multi-Agent Orchestration Requirements](../multi_agent_orchestration.md)

---

## 1. Task Data Model

### 1.1 Core Entities

#### REQ-TQM-DM-001: Task Schema
THE SYSTEM SHALL persist tasks with the following minimum schema:
```python
Task = {
    "id": "uuid",                        # unique task identifier
    "ticket_id": "uuid",                 # parent ticket
    "phase_id": "PhaseEnum",             # REQUIREMENTS | IMPLEMENTATION | VALIDATION | ANALYSIS | TESTING
    "description": "str",                # human-readable description
    "priority": "PriorityEnum",          # CRITICAL | HIGH | MEDIUM | LOW
    "score": "float",                    # dynamic scheduling score (see §2)
    "status": "TaskStatusEnum",          # PENDING | IN_PROGRESS | COMPLETED | FAILED | CANCELLED
    "assigned_agent_id": "uuid|null",
    "created_at": "datetime",
    "started_at": "datetime|null",
    "completed_at": "datetime|null",
    "retry_count": "int",                # default 0
    "max_retries": "int",                # default 3 (configurable)
    "deadline_at": "datetime|null",      # optional SLA
    "dependencies": ["uuid", "..."],     # prerequisite task ids
    "parent_task_id": "uuid|null",       # for branching & sub-tasks
    "result": "TaskResult|null",         # see §1.2
    "metadata": {"k": "v"}               # arbitrary structured context
}
```

#### REQ-TQM-DM-002: Result Schema
```python
TaskResult = {
    "success": "bool",
    "output": "Any",
    "discoveries": ["Discovery", "..."],  # see §4
    "validation_failed": "bool",
    "errors": ["str", "..."],
    "metrics": {"duration_ms": 0, "..."}
}
```

#### REQ-TQM-DM-003: Indexing
THE SYSTEM SHALL index tasks by `(status, priority, phase_id)` and `(ticket_id)` to enable low-latency fetch and fan-out operations (P95 < 100ms).

---

## 2. Priority and Scoring

### 2.1 Static Priority
#### REQ-TQM-PRI-001: Priority Order
Static priority ordering SHALL be enforced: `CRITICAL > HIGH > MEDIUM > LOW`.

### 2.2 Dynamic Score
#### REQ-TQM-PRI-002: Composite Score
Each task SHALL have a dynamic `score` computed as:
```
score = w_p * P(priority) 
      + w_a * A(age_seconds) 
      + w_d * D(deadline_slack) 
      + w_b * B(blocker_count) 
      + w_r * R(retry_penalty)
```
Where:
- `P(priority)`: discrete mapping (CRITICAL=1.0, HIGH=0.75, MEDIUM=0.5, LOW=0.25)
- `A(age_seconds)`: normalized 0.0–1.0 with cap at `AGE_CEILING`
- `D(deadline_slack)`: higher when closer to deadline (0.0–1.0)
- `B(blocker_count)`: increases urgency when this task unblocks others (0.0–1.0)
- `R(retry_penalty)`: reduces score as retries accumulate (0.0–1.0)
- `w_*`: weights, configurable; defaults: `w_p=0.45, w_a=0.2, w_d=0.15, w_b=0.15, w_r=0.05`

#### REQ-TQM-PRI-003: SLA Boost
Tasks with `deadline_at` within `SLA_URGENCY_WINDOW` SHALL receive an additional multiplicative boost (default 1.25x).

#### REQ-TQM-PRI-004: Starvation Guard
No task SHALL wait longer than `STARVATION_LIMIT` (default 2h). The scheduler MUST apply a minimum floor score to starved tasks.

---

## 3. Assignment Logic

### 3.1 Eligibility
#### REQ-TQM-ASSIGN-001: Capability Match
Tasks SHALL only be assigned to agents whose `phase_id` matches and whose capability declarations meet the task’s required skills (language, framework, tool).

#### REQ-TQM-ASSIGN-002: Dependency Barrier
A task SHALL NOT start until all `dependencies` are `COMPLETED`. The queue MUST efficiently check dependency satisfaction.

### 3.2 Pull vs Push
#### REQ-TQM-ASSIGN-003: Pull-First Model
IDLE agents SHOULD prefer pulling the highest-score eligible task to minimize contention; orchestrator MAY push for hot-path tasks (e.g., CRITICAL with imminent SLA).

### 3.3 Concurrency and Fairness
#### REQ-TQM-ASSIGN-004: Tenant Fair-Share
When operating multi-tenant tickets, the scheduler SHALL enforce fair-share limits to prevent one tenant from starving others.

#### REQ-TQM-ASSIGN-005: Backoff on Failure
After a task failure, the same agent SHALL be deprioritized for reassignment of the same task within a `AGENT_TASK_BACKOFF_WINDOW`.

---

## 3A. Capacity & Queue Semantics (Alignment)

#### REQ-TQM-CAP-001: Max Concurrent Agents
The system SHALL enforce a hard capacity limit `max_concurrent_agents`. When active agents ≥ limit, new tasks SHALL be queued rather than started.

#### REQ-TQM-CAP-002: Under vs At Capacity Behavior
- Under capacity: task is enriched and started immediately; status transitions `pending → assigned → in_progress`.
- At capacity: task is enriched and added to queue; status transitions `pending → queued`.

#### REQ-TQM-CAP-003: Auto-Processing
The queue MUST auto-process on these triggers:
- Task completes (status → done)
- Task fails (status → failed)
- Agent terminates (voluntary or forced)
Upon trigger, the system dequeues the next eligible task and starts it if capacity exists.

---

## 4. Discovery-Driven Branching

### 4.1 Discovery Types
#### REQ-TQM-BR-001: Standard Types
Supported discovery types include:
- `security_issue` → spawn CRITICAL `PHASE_ANALYSIS` task
- `requires_clarification` → spawn `PHASE_REQUIREMENTS` task
- `optimization_opportunity` → spawn MEDIUM `PHASE_ANALYSIS` task

### 4.2 Branch Creation
#### REQ-TQM-BR-002: Parent-Child Linkage
Spawned tasks MUST reference `parent_task_id` and inherit relevant `metadata` with redaction of secrets.

#### REQ-TQM-BR-003: Ticket Propagation
If discovery pertains to the same ticket, spawned tasks SHALL inherit `ticket_id`; cross-ticket spawning REQUIRES explicit guardian approval.

---

## 5. Validation Feedback Loops

### 5.1 Auto-Fix Flow
#### REQ-TQM-VF-001: Fix-and-Revalidate
If `validation_failed == true`, the system SHALL:
1) Create a HIGH priority `PHASE_IMPLEMENTATION` fix task
2) Queue an automatic `PHASE_VALIDATION` re-check task
3) Link both tasks via `parent_task_id`

#### REQ-TQM-VF-002: Retry Budget
The queue SHALL enforce `max_retries` and maintain `retry_count`. Upon exhaustion, escalate to guardian with full context.

### 5.2 Loop Breakers
#### REQ-TQM-VF-003: Infinite Loop Protection
The system SHALL track repeated failure signatures and halt loops after `REPEAT_SIGNATURE_LIMIT` occurrences, requiring human or guardian review.

---

## 6. Metrics & SLAs

#### REQ-TQM-OBS-001: Scheduler Latency
Task fetch + assign P95 latency < 100ms under nominal load.

#### REQ-TQM-OBS-002: Queue Depth
Expose queue depth and depth-by-priority; alert when CRITICAL depth > 0 for > 60s.

#### REQ-TQM-OBS-003: Retry Rates
Track retries per phase and per discovery type; anomaly alerts on spikes.

---

## 7. Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| AGE_CEILING | 3600s | Cap for age normalization |
| SLA_URGENCY_WINDOW | 900s | Time window for deadline boost |
| STARVATION_LIMIT | 7200s | Max wait before floor score |
| AGENT_TASK_BACKOFF_WINDOW | 1800s | Cooldown for reassigning failed tasks to same agent |
| MAX_QUEUE_SCAN_BATCH | 200 | Max tasks scanned per scheduling cycle |
| MAX_CONCURRENT_AGENTS | 10 | Hard capacity limit |
| BUMP_AND_START_ENABLED | true | Allow priority bypass |

---

## 8. Pydantic Reference Models

```python
from __future__ import annotations
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
    # Queue alignment fields
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

## 9. Bump & Start (Priority Bypass)

#### REQ-TQM-BUMP-001: Manual Priority Bypass
The system SHALL support “Bump & Start” to start a queued task immediately, bypassing the capacity limit.

#### REQ-TQM-BUMP-002: Effects
- Move task to queue position #1.
- Start agent immediately even if `active_agents ≥ max_concurrent_agents` (temporary over-capacity).
- System naturally returns to configured limit as agents complete; no further over-commit occurs.

#### REQ-TQM-BUMP-003: Guardrails
- Feature flag `BUMP_AND_START_ENABLED` must be true.
- Audit log MUST record actor, reason, and resulting capacity.
- Over-capacity MUST NOT exceed `max_concurrent_agents + OVERCAP_LIMIT` (default: +1).

---

## 10. Queue Processing Triggers and Flow

#### REQ-TQM-PROC-001: Triggers
Queue processing MUST run on:
- task completion, task failure, agent termination, and on schedule (poll).

#### REQ-TQM-PROC-002: Reference Flow
```python
async def process_queue():
    if active_agents >= max_concurrent_agents:
        return
    next_task = get_next_queued_task()  # priority_boosted > priority > queued_at (FIFO)
    if not next_task:
        return
    dequeue_task(next_task.id)
    create_agent_for_task(next_task)
```

---

## 11. API Endpoints (Normative)

| Endpoint | Method | Purpose | Bypass Limit |
|---------|--------|---------|--------------|
| /api/queue_status | GET | Return queue state | N/A |
| /api/bump_task_priority | POST | Start queued task immediately | Yes |
| /api/cancel_queued_task | POST | Remove task from queue | N/A |
| /api/restart_task | POST | Restart done/failed task | No |
| /api/terminate_agent | POST | Terminate running agent | N/A |

Payload references SHALL include: `task_id` or `agent_id`, correlation id, and auth context.

---

## 12. WebSocket Events (Normative)

| Event | When Emitted | Payload (min) |
|-------|---------------|---------------|
| task_queued | Task added to queue | task_id, description, queue_position, slots_available |
| task_created | New task created | task_id, description, agent_id? |
| task_completed | Task finished | task_id, agent_id, status, summary |
| task_priority_bumped | Task started via bump | task_id, agent_id |
| agent_created | New agent spawned | agent_id, task_id |
| agent_status_changed | Agent status updated | agent_id, status |

Clients (QueueSection, TasksPage, AgentList) SHALL subscribe as appropriate.

---

## 13. Memory Integration

#### REQ-TQM-MEM-001: Discovery Persistence
When a task completes with non-empty `discoveries` or `errors` in `TaskResult`, THE SYSTEM SHOULD invoke the Agent Memory System (ACE workflow or equivalent API) to persist a corresponding memory, including:
- task `goal`/`description`,
- `result` summary,
- linked `ticket_id` and affected file paths (when available),
- discovered issues or opportunities.

#### REQ-TQM-MEM-002: Context Retrieval on Assignment
When assigning a task to an agent, THE SYSTEM MAY request contextual memories for the `ticket_id` and/or `description` from the Agent Memory System to pre-load relevant knowledge (e.g., via a “get context for task” API).

---
## Related Documents

- [Agent Lifecycle Management Requirements](../agents/lifecycle_management.md)
- [Monitoring & Fault Tolerance Requirements](../monitoring/fault_tolerance.md)
- [Ticket Workflow Requirements](./ticket_workflow.md)
- [MCP Integration Requirements](../integration/mcp_servers.md)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Spec Agent | Initial draft |


