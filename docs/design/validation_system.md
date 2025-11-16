# Validation System Design Document

## Document Overview

The **Validation System** provides a structured workflow for reviewing and validating agent task results before they are considered complete. It extends the core task state machine with explicit validation states, orchestrates validator agents, persists review artifacts, and integrates with Memory and Diagnosis subsystems to create feedback loops and long‑term learning.

- **Purpose and scope**:
  - Define how validation states and transitions are implemented on top of the Task lifecycle.
  - Specify components responsible for spawning validator agents, persisting reviews, delivering feedback, and triggering follow‑up actions.
  - Describe data models, APIs, events, configuration, and integrations required to satisfy all Validation System requirements.
- **Target audience**:
  - AI spec agents defining workflows.
  - Implementation teams building orchestration, API, and storage layers.
  - System architects integrating validation with Memory, Diagnosis, Task Queue, and Workspace Isolation systems.
- **Related documents**:
  - Requirements: `docs/requirements/workflows/validation_system.md`
  - Orchestration Design: `docs/design/multi_agent_orchestration.md`
  - Workspace Isolation: `docs/design/workspace_isolation_system.md`
  - Related requirements:
    - `docs/requirements/workflows/task_queue_management.md`
    - `docs/requirements/monitoring/fault_tolerance.md`
    - `docs/requirements/integration/mcp_servers.md`

---

## Architecture Overview

### High-Level Architecture

```mermaid
flowchart TD
    subgraph WorkflowLayer[Workflow / Task Orchestration Layer]
        TO[Task Orchestrator]
    end

    subgraph ValidationLayer[Validation Layer]
        VO[Validation Orchestrator]
        VR[ValidationReview Store (DB)]
        VT[Feedback Transport]
    end

    subgraph AgentLayer[Agent Execution Layer]
        WA[Worker Agents]
        VA[Validator Agents]
    end

    subgraph IntegrationLayer[Integration Layer]
        MEM[Memory System]
        DIAG[Diagnosis Agent Service]
        WS[WorkspaceManager / Git Adapter]
        EB[Event Bus / WebSocket Gateway]
    end

    TO -->|task enters under_review| VO
    VO -->|spawn_validator| VA
    VA -->|give_review| VO
    VO -->|persist review| VR
    VO -->|notify| EB
    VO -->|send_feedback| VT --> WA

    VO -->|write validation memory| MEM
    VO -->|read past validation memories| MEM

    VO -->|auto-spawn on failures/timeouts| DIAG
    DIAG -->|attach report to ticket| TO

    VO -->|commit_for_validation| WS
```

### Component Responsibilities

| Component | Layer | Responsibilities |
|----------|-------|------------------|
| Validation Orchestrator | Validation | Enforces validation state machine, guards, spawns validator agents, persists reviews, updates Task/Agent extensions, emits events, triggers Memory/Diagnosis actions. |
| Validator Agents | Agent | Perform code/result review, call `give_review`, optionally query Memory System for prior validation context. |
| Worker Agents | Agent | Execute primary task work, transition tasks to `under_review`, receive feedback via transport. |
| ValidationReview Store | Validation | Persist `ValidationReview` records with iteration and FK constraints; expose query primitives. |
| Feedback Transport | Validation | Deliver feedback to originating agents via transport‑agnostic interface (HTTP, IPC, event bus). |
| Task Orchestrator | Workflow | Owns core Task lifecycle; delegates validation transitions to Validation Orchestrator; may create fix tasks or apply retry logic based on validation results. |
| Memory Integration Adapter | Integration | Maps validation outcomes to Memory System entries and retrieves prior validation memories for validator context. |
| Diagnosis Integration Adapter | Integration | Enforces thresholds for repeated failures/timeouts; spawns Diagnosis Agent and attaches reports to tickets. |
| Workspace/Git Adapter | Integration | Creates commits capturing validation artifacts for each iteration, using Workspace Isolation APIs. |
| Event Bus / WebSocket Gateway | Integration | Broadcasts validation lifecycle events (`validation_started`, `validation_review_submitted`, `validation_passed`, `validation_failed`) to clients. |

### System Boundaries

- **Within scope of Validation System**:
  - Managing Task validation states (`under_review`, `validation_in_progress`, `needs_work`, `done`, `failed`) and guards.
  - Spawning and tracking validator agents for specific tasks.
  - Persisting `ValidationReview` artifacts and exposing status.
  - Delivering validator feedback to originating agents.
  - Writing/reading validation‑related memories.
  - Triggering Diagnosis Agents when validation failures or timeouts exceed thresholds.
  - Creating validation‑related Git commits via Workspace Isolation.

- **Out of scope (delegated)**:
  - Underlying Task Queue implementation and general task assignment.
  - Generic agent lifecycle management and health monitoring.
  - Memory System internal storage and retrieval algorithms.
  - Diagnosis Agent internal analysis workflow.
  - Workspace creation/teardown and low‑level Git operations.

---

## Component Details

### Validation Orchestrator

The **Validation Orchestrator** is a logical service responsible for applying the validation state machine to tasks and coordinating validator agents.

#### State Machine Enforcement (REQ-VAL-SM-001, REQ-VAL-SM-002)

The orchestrator enforces the following transitions:

- `pending → assigned → in_progress` (owned by Task Orchestrator, but visible to Validation Orchestrator).
- `in_progress → under_review`:
  - Preconditions:
    - Worker agent has published a completion signal.
    - If the task is associated with a Git‑backed workspace, a `commit_sha` must be provided (via Workspace/Git adapter).
  - Side effects:
    - Increment `task.validation_iteration` by 1.
    - Optionally call `commit_for_validation(agent_id, iteration)` on WorkspaceManager.
- `under_review → validation_in_progress`:
  - Preconditions:
    - Validator agent successfully spawned for the task.
  - Side effects:
    - Emit `validation_started` event.
- `validation_in_progress → done`:
  - Preconditions:
    - Received `give_review` with `validation_passed == true`.
  - Side effects:
    - Persist `ValidationReview` record.
    - Set `task.review_done = true`.
    - Update Task status to `done`.
    - Emit `validation_review_submitted` and `validation_passed` events.
    - Write Memory entry (REQ-VAL-MEM-001).
- `validation_in_progress → needs_work`:
  - Preconditions:
    - Received `give_review` with `validation_passed == false` and non‑empty `feedback`.
  - Side effects:
    - Persist `ValidationReview` record.
    - Set `task.last_validation_feedback`.
    - Emit `validation_review_submitted` and `validation_failed` events.
    - Optionally create fix tasks and/or requeue work (coordinated with Task Queue).
    - Write Memory entry (REQ-VAL-MEM-001).
- `needs_work → in_progress`:
  - Preconditions:
    - Original worker agent resumes work on the same session.
- `in_progress → failed`:
  - Preconditions:
    - Worker agent explicitly gives up or system terminates the attempt.

Guards are implemented centrally in the orchestrator to keep the Task store logically consistent.

#### Reactions to Task State Changes

The Validation Orchestrator subscribes to Task lifecycle events (e.g., `TASK_STATUS_CHANGED`) from the Event Bus:

- When it observes `status=UNDER_REVIEW` and `task.validation_enabled == true`, it:
  - Validates that a `commit_sha` is present (for Git‑backed tasks).
  - Calls `spawn_validator(task_id, commit_sha)` (internal call or via public API).
- When it receives `give_review`:
  - Validates caller identity (`agent_type=validator`).
  - Applies the appropriate transition (`validation_in_progress → done` or `validation_in_progress → needs_work`).
  - Updates Task and ValidationReview tables accordingly.

### Validator Agent Lifecycle (REQ-VAL-LC-001, REQ-VAL-LC-002)

Validator agents are regular agents specialized for review:

- **Spawn**:
  - Triggered when a task enters `under_review` with `validation_enabled=true`.
  - Implemented via `/api/validation/spawn_validator` or an internal orchestration call.
  - The spawn logic:
    - Selects an available agent template with `agent_type=validator`.
    - Binds it to the task and relevant workspace (read‑only or read/write, depending on policy).
    - Sets `agent.kept_alive_for_validation` for the originating worker if we need it to remain available for fix iterations.
- **Work**:
  - Validator agents:
    - Access the task workspace at a Git commit corresponding to the iteration.
    - Optionally query Memory System for prior validation memories for the same ticket/component.
    - Run tests, linters, and other tools as needed.
    - Call `/api/validation/give_review` exactly once per iteration with pass/fail, feedback, and optional evidence/recommendations.
- **Feedback Delivery**:
  - The orchestrator uses `Feedback Transport` to deliver feedback to the originating agent:
    - HTTP callback to a per‑agent endpoint.
    - Event Bus message consumed by the agent process.
    - Any other transport as long as it respects REQ-VAL-LC-002 (tmux is not assumed).

### Workspace/Git Integration Component (REQ-VAL-LC-003)

The Validation System reuses the **Workspace Isolation System**:

- Before entering `under_review`, the worker agent (through Task Orchestrator) requests:

```python
commit_info = workspace_manager.commit_for_validation(
    agent_id=agent.id,
    iteration=task.validation_iteration + 1,
)
```

- The resulting `commit_sha` is attached to the task and passed to `spawn_validator`.
- Each validation attempt therefore has:
  - A dedicated Git commit capturing state of the workspace.
  - A standard commit message following the Workspace design (e.g., `[Workspace {id}] Iteration {n} - Ready for validation`).
- Validators operate over that commit, ensuring reproducible review and traceability.

### ValidationReview Store (REQ-VAL-DM-003)

The **ValidationReview Store** is responsible for:

- Enforcing FK constraints between `validation_reviews.task_id` and `tasks.id`, and between `validator_agent_id` and `agents.id`.
- Ensuring `iteration_number` matches the Task’s current `validation_iteration` at the time of review.
- Providing query methods to:
  - Fetch all reviews for a given task.
  - Fetch the last review for a task (for status endpoint).
  - Aggregate statistics (e.g., consecutive failures).

### Security & Audit Subcomponent (REQ-VAL-SEC-001)

The Validation System integrates with the orchestration audit log:

- Authorization:
  - For `/api/validation/give_review`, the caller’s `agent_id` is resolved and `agent_type` checked to be `validator`.
  - For `/api/validation/spawn_validator`, the caller must be an internal system component (e.g., Task Orchestrator) or have appropriate privileges.
- Audit logging:
  - On every review submission, an audit record is written capturing:
    - `actor_id` (validator agent ID).
    - `target_type="task"`, `target_id=task_id`.
    - Iteration number and result (`validation_passed`).
    - Timestamp and optional metadata (evidence, recommendations).
  - Audit log schema aligns with the general `audit_log` table from the orchestration design.

---

## Data Models

### Task Model Extensions (REQ-VAL-DM-001)

The `tasks` table and corresponding Task domain model are extended with validation fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `validation_enabled` | bool | `false` | Enables validation for this task. |
| `validation_iteration` | int | `0` | Current validation iteration counter. |
| `last_validation_feedback` | text \| null | `null` | Last feedback text provided by validator. |
| `review_done` | bool | `false` | Whether the latest validation cycle has completed successfully. |

**Update rules**:

- On entering `under_review`: `validation_iteration += 1`.
- On `validation_in_progress → done`: `review_done = true`.
- On `validation_in_progress → needs_work`: `last_validation_feedback = feedback` from `give_review`.

Example SQL (fragment):

```sql
ALTER TABLE tasks
    ADD COLUMN validation_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN validation_iteration INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN last_validation_feedback TEXT,
    ADD COLUMN review_done BOOLEAN NOT NULL DEFAULT FALSE;
```

### Agent Model Extensions (REQ-VAL-DM-002)

The `agents` table and Agent model are extended as follows:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent_type` | enum(`phase`, `validator`, `monitor`) | - | Logical role of the agent. |
| `kept_alive_for_validation` | bool | `false` | Whether the agent should be retained across iterations for further validation‑driven work. |

Example SQL:

```sql
CREATE TYPE agent_type_enum AS ENUM ('phase', 'validator', 'monitor');

ALTER TABLE agents
    ADD COLUMN agent_type agent_type_enum NOT NULL,
    ADD COLUMN kept_alive_for_validation BOOLEAN NOT NULL DEFAULT FALSE;
```

### ValidationReview Table (REQ-VAL-DM-003)

```sql
CREATE TABLE validation_reviews (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    validator_agent_id TEXT NOT NULL REFERENCES agents(id),
    iteration_number INT NOT NULL,
    validation_passed BOOLEAN NOT NULL,
    feedback TEXT NOT NULL,
    evidence JSONB,
    recommendations JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT validation_reviews_iteration_match
        CHECK (iteration_number > 0)
);

CREATE INDEX idx_validation_reviews_task_iteration
    ON validation_reviews(task_id, iteration_number);
```

At write time, the Validation Orchestrator ensures `iteration_number == task.validation_iteration` to satisfy the requirement that the iteration matches the Task’s current iteration.

### Pydantic Models

The following Pydantic models align with the reference definitions from the requirements.

```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ValidationState(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    VALIDATION_IN_PROGRESS = "validation_in_progress"
    NEEDS_WORK = "needs_work"
    DONE = "done"
    FAILED = "failed"


class ValidationReview(BaseModel):
    id: str
    task_id: str
    validator_agent_id: str
    iteration_number: int
    validation_passed: bool
    feedback: str
    evidence: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    created_at: datetime


class ValidationReviewRequest(BaseModel):
    task_id: str
    validator_agent_id: str
    validation_passed: bool
    feedback: str
    evidence: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None


class ValidationReviewResponse(BaseModel):
    status: str  # "completed" | "needs_work"
    message: str
    iteration: int
```

These models are reused in API request/response definitions below.

---

## API Specifications

### REST Endpoints (REQ-VAL-API)

The Validation System exposes four primary endpoints, mirroring the normative requirements.

#### Endpoint Summary Table (matches requirements 5.1)

| Endpoint | Method | Purpose | Minimal Request Body | Responses |
|----------|--------|---------|----------------------|-----------|
| `/api/validation/give_review` | POST | Submit validation review for a task | `{ task_id, validator_agent_id, validation_passed, feedback, evidence?, recommendations? }` | **200 OK**: `{ status: "completed" \| "needs_work", message, iteration }`; **400**: `{ error }`; **403**: `{ error }` (non‑validator); **404**: `{ error }` |
| `/api/validation/spawn_validator` | POST | Spawn validator for task | `{ task_id, commit_sha? }` | **200 OK**: `{ validator_agent_id }`; **409**: `{ error }` (already running); **404**: `{ error }` |
| `/api/validation/send_feedback` | POST | Deliver feedback to agent | `{ agent_id, feedback }` | **200 OK**: `{ delivered: true }`; **404**: `{ error }` |
| `/api/validation/status` | GET | Fetch validation status for task | Query: `?task_id=...` | **200 OK**: `{ task_id, state, iteration, review_done, last_feedback }`; **404**: `{ error }` |

All error responses MUST include a stable `error` field.

#### `/api/validation/give_review` – Submit Review

Request model:

```python
class GiveReviewRequest(ValidationReviewRequest):
    """Alias for clarity; same fields as ValidationReviewRequest."""
    pass
```

Response model:

```python
class GiveReviewResponse(ValidationReviewResponse):
    ...
```

Behavior:

- Validate that:
  - `validator_agent_id` exists and `agent_type == "validator"`. Otherwise return `403 { "error": "forbidden" }`.
  - `task_id` exists. Otherwise return `404 { "error": "task_not_found" }`.
- On success:
  - Persist `ValidationReview`.
  - Apply transition (`validation_in_progress → done` if `validation_passed`, else `validation_in_progress → needs_work`).
  - Emit `validation_review_submitted` plus either `validation_passed` or `validation_failed`.
  - Return:

```json
{
  "status": "completed",
  "message": "Validation passed",
  "iteration": 2
}
```

or

```json
{
  "status": "needs_work",
  "message": "Validation failed; feedback recorded",
  "iteration": 2
}
```

#### `/api/validation/spawn_validator` – Spawn Validator

Request model:

```python
class SpawnValidatorRequest(BaseModel):
    task_id: str
    commit_sha: Optional[str] = None
```

Response model:

```python
class SpawnValidatorResponse(BaseModel):
    validator_agent_id: str
```

Behavior:

- If there is already an active validator for the task’s current iteration, return `409 { "error": "validator_already_running" }`.
- If `task_id` does not exist, return `404 { "error": "task_not_found" }`.
- Otherwise:
  - Select a validator agent template.
  - Spawn the validator agent bound to the task and workspace at `commit_sha` (if provided).
  - Set Task state to `validation_in_progress`.
  - Emit `validation_started` event.
  - Return `{ "validator_agent_id": "<id>" }`.

#### `/api/validation/send_feedback` – Deliver Feedback to Agent

Request model:

```python
class SendFeedbackRequest(BaseModel):
    agent_id: str
    feedback: str
```

Response model:

```python
class SendFeedbackResponse(BaseModel):
    delivered: bool
```

Behavior:

- If `agent_id` does not exist, return `404 { "error": "agent_not_found" }`.
- Use Feedback Transport to deliver the feedback (e.g., HTTP callback, event bus message).
- Return `{ "delivered": true }` on success.

#### `/api/validation/status` – Fetch Validation Status

Query parameter:

- `task_id` (required).

Response model:

```python
class ValidationStatusResponse(BaseModel):
    task_id: str
    state: ValidationState
    iteration: int
    review_done: bool
    last_feedback: Optional[str]
```

Behavior:

- If no such task exists, return `404 { "error": "task_not_found" }`.
- Otherwise:
  - Compute the current validation state derived from Task status and `validation_enabled`.
  - Return the latest iteration and last feedback, using the Task fields and the latest `ValidationReview` if needed.

### WebSocket/Event Contracts (REQ-VAL-Events)

The Validation System emits domain events via the Event Bus and WebSocket gateway.

| Event | When Emitted | Payload (min) |
|-------|--------------|---------------|
| `validation_started` | Task enters `validation_in_progress` | `{ "task_id": str, "iteration": int }` |
| `validation_review_submitted` | A `ValidationReview` record is saved | `{ "task_id": str, "iteration": int, "passed": bool, "validator_agent_id": str }` |
| `validation_passed` | Task marked `done` after validation | `{ "task_id": str, "iteration": int }` |
| `validation_failed` | Task marked `needs_work` after validation | `{ "task_id": str, "iteration": int, "feedback": str }` |

These events are used by UI clients, monitoring dashboards, and higher‑level workflow components.

---

## Integration Points

### Memory System Integration (REQ-VAL-MEM-001, REQ-VAL-MEM-002)

For each validation iteration, the Validation Orchestrator writes a memory record via the Memory System API:

```python
async def record_validation_memory(review: ValidationReview, ticket_id: str) -> None:
    payload = {
        "type": "validation_outcome",
        "task_id": review.task_id,
        "ticket_id": ticket_id,
        "iteration": review.iteration_number,
        "validation_passed": review.validation_passed,
        "feedback": review.feedback,
        "evidence": review.evidence,
        "recommendations": review.recommendations,
    }
    await memory_client.create_memory(payload)
```

Validator agents may then query prior memories:

```python
async def load_prior_validation_context(ticket_id: str) -> list[dict]:
    return await memory_client.search_memories(
        filters={"ticket_id": ticket_id, "type": "validation_outcome"},
        limit=50,
    )
```

Use cases:

- Avoid repeating approaches that previously failed.
- Reuse successful patterns and evidence.
- Improve or clarify `result_criteria` when gaps are consistently observed.

### Diagnosis Agent Integration (REQ-VAL-DIAG-001, REQ-VAL-DIAG-002)

The Validation System tracks **consecutive validation failures** and timeouts per task.

- **Repeated failures**:

```python
if result.validation_failed:
    task.consecutive_validation_failures += 1
    if (
        config.DIAG_ON_VALIDATION_FAILURES
        and task.consecutive_validation_failures
        >= config.DIAG_VALIDATION_FAILURES_THRESHOLD
    ):
        await diagnosis_client.start_diagnosis(task_id=task.id)
```

- **Timeouts**:

When a validator exceeds `validator_timeout_minutes` for a given iteration:

```python
if (
    elapsed_minutes > config.validator_timeout_minutes
    and config.DIAG_ON_VALIDATION_TIMEOUT
):
    await diagnosis_client.start_diagnosis(
        task_id=task.id,
        focus="validation_timeout",
    )
```

The Diagnosis Agent’s report is attached to the ticket via the Task Orchestrator, and referenced in subsequent validation iterations as input context.

### Task Queue and Workflow Integration

The Validation System is tightly coupled to the task lifecycle but does not implement the queue itself:

- On `validation_failed`:
  - A fix task may be created (e.g., by the Task Queue based on `auto_create_followups`), pointing back to the original task and including validator feedback.
- On `validation_passed`:
  - The Ticket’s phase can advance, and dependent tasks can be unblocked.
- The Validation Orchestrator provides hooks for:
  - Incrementing retry counts.
  - Applying backoff or escalation logic as defined in the Task Queue Management design.

### Workspace Isolation and Git Integration

Integration with the Workspace Isolation System ensures repeatable validation artifacts:

- On entering `under_review`, the Task Orchestrator:

```python
commit_info = workspace_manager.commit_for_validation(
    agent_id=worker_agent.id,
    iteration=task.validation_iteration + 1,
)

task.metadata["validation_commit_sha"] = commit_info["commit_sha"]
```

- Commit messages follow the existing convention:
  - `[Workspace {id}] Iteration {n} - Ready for validation`.
- Validator agents are launched with:
  - Read access to the workspace at the given commit.
  - Paths for validation artifacts (logs, diff files, reports) to be included in subsequent commits if needed.

---

## Implementation Details

### State Machine Implementation

Pseudocode for enforcing validation transitions:

```python
async def transition_to_under_review(task: Task, agent: Agent, commit_sha: Optional[str]) -> None:
    if not commit_sha:
        raise ValidationError("commit_sha required for under_review")

    task.validation_iteration += 1
    task.status = ValidationState.UNDER_REVIEW.value
    task.review_done = False
    await state_store.save_task(task)

    await spawn_validator_for_task(task.id, commit_sha)


async def handle_give_review(req: GiveReviewRequest) -> GiveReviewResponse:
    validator = await state_store.get_agent(req.validator_agent_id)
    if validator.agent_type != "validator":
        raise ForbiddenError("validator agent required")

    task = await state_store.get_task(req.task_id)
    if task.status != ValidationState.VALIDATION_IN_PROGRESS.value:
        raise ValidationError("task not in validation_in_progress")

    review = ValidationReview(
        id=generate_id(),
        task_id=task.id,
        validator_agent_id=validator.id,
        iteration_number=task.validation_iteration,
        validation_passed=req.validation_passed,
        feedback=req.feedback,
        evidence=req.evidence,
        recommendations=req.recommendations,
        created_at=datetime.utcnow(),
    )
    await validation_review_repo.save(review)

    if req.validation_passed:
        task.status = ValidationState.DONE.value
        task.review_done = True
        event_type = "validation_passed"
        status = "completed"
        message = "Validation passed"
    else:
        task.status = ValidationState.NEEDS_WORK.value
        task.last_validation_feedback = req.feedback
        event_type = "validation_failed"
        status = "needs_work"
        message = "Validation failed"

    await state_store.save_task(task)
    await event_bus.publish_event(event_type, {...})
    await record_validation_memory(review, ticket_id=task.ticket_id)

    return GiveReviewResponse(status=status, message=message, iteration=task.validation_iteration)
```

### Validator Spawn and Timeout Handling

Pseudocode for spawning validator agents and monitoring timeouts:

```python
async def spawn_validator_for_task(task_id: str, commit_sha: Optional[str]) -> str:
    task = await state_store.get_task(task_id)

    if await validator_registry.has_active_validator(task_id, task.validation_iteration):
        raise ConflictError("validator already running")

    validator_agent_id = await agent_lifecycle.spawn_validator_agent(task_id, commit_sha)
    await validator_registry.register(task_id, task.validation_iteration, validator_agent_id)

    task.status = ValidationState.VALIDATION_IN_PROGRESS.value
    await state_store.save_task(task)

    await event_bus.publish_event("validation_started", {"task_id": task.id, "iteration": task.validation_iteration})
    return validator_agent_id


async def monitor_validator_timeouts() -> None:
    while True:
        for assignment in await validator_registry.list_active():
            elapsed = (datetime.utcnow() - assignment.started_at).total_seconds() / 60
            if elapsed > config.validator_timeout_minutes:
                await handle_validator_timeout(assignment.task_id)
        await asyncio.sleep(30)
```

Timeout handlers invoke Diagnosis Agent when configured, as described in the integration section.

### Feedback Delivery Mechanism

An abstract interface decouples the orchestrator from specific transports:

```python
class FeedbackTransport(Protocol):
    async def send_feedback(self, agent_id: str, feedback: str) -> bool:
        ...


class EventBusFeedbackTransport:
    async def send_feedback(self, agent_id: str, feedback: str) -> bool:
        await event_bus.publish_event("agent.validation_feedback", {"agent_id": agent_id, "feedback": feedback})
        return True


class HttpFeedbackTransport:
    async def send_feedback(self, agent_id: str, feedback: str) -> bool:
        endpoint = await agent_directory.get_callback_url(agent_id)
        # POST feedback to agent's callback URL
        ...
        return True
```

`/api/validation/send_feedback` is implemented by calling the currently configured `FeedbackTransport`.

### Performance and SLO Mapping (REQ-VAL-SLO-001, REQ-VAL-SLO-002)

- **Iteration time**:
  - `iteration_timeout_minutes` bounds each validation iteration duration.
  - Combined with `validator_timeout_minutes`, the system ensures validation cycles add approximately 2–10 minutes under normal conditions.
- **Startup latency**:
  - Validator agents share the same lifecycle framework as other agents; startup P95 < 30s is achieved by:
    - Keeping a warm pool of idle validator agents.
    - Minimizing workspace checkout overhead by reusing existing worktrees when possible.
- **Persistence latency**:
  - Validation review writes are single‑row inserts with indexed lookups, targeting P95 < 200ms.

### Configuration Reference

The Validation System configuration is typically represented as a Pydantic settings class:

```python
from pydantic_settings import BaseSettings


class ValidationConfig(BaseSettings):
    enabled_by_default: bool = False
    max_iterations: int = 10
    iteration_timeout_minutes: int = 30
    validator_timeout_minutes: int = 10
    keep_failed_iterations: bool = True
    auto_create_followups: bool = True

    DIAG_ON_VALIDATION_FAILURES: bool = True
    DIAG_VALIDATION_FAILURES_THRESHOLD: int = 2
    DIAG_ON_VALIDATION_TIMEOUT: bool = True

    class Config:
        env_prefix = "VALIDATION_"
        env_file = ".env"
```

Configuration parameters map directly to the normative tables in the requirements.

---

## Related Documents

- **Requirements**:
  - `docs/requirements/workflows/validation_system.md`
- **Core design references**:
  - `docs/design/multi_agent_orchestration.md`
  - `docs/design/workspace_isolation_system.md`
- **Other related requirement specs**:
  - `docs/requirements/workflows/task_queue_management.md`
  - `docs/requirements/monitoring/fault_tolerance.md`
  - `docs/requirements/integration/mcp_servers.md`

---

## Quality Checklist Alignment

- All validation states, transitions, and guards from the requirements are mapped to orchestration behavior.
- Task and Agent data model extensions are explicitly defined, including update rules and SQL.
- The `ValidationReview` artifact is fully specified with constraints and indexing.
- REST APIs and WebSocket/event contracts match the normative definitions and enforce security requirements.
- Memory and Diagnosis integrations are documented with concrete call patterns.
- Workspace/Git integration leverages the Workspace Isolation System commit semantics for each validation iteration.
- Configuration parameters and SLOs are connected to concrete implementation patterns.


