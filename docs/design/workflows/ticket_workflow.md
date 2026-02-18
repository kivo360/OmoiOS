# Ticket Workflow Design Document

**Created**: 2025-11-20
**Status**: Draft
**Purpose**: Define the Kanban-style ticket workflow system, its state machine, phase orchestration, blocking detection, and integration points.
**Related**: docs/requirements/workflows/ticket_workflow.md, docs/design/multi_agent_orchestration.md, docs/design/task_queue_management.md, docs/design/validation_system.md, docs/requirements/workflows/task_queue_management.md, docs/requirements/workflows/validation_system.md, docs/requirements/monitoring/monitoring_architecture.md

---


## Document Overview

The **Ticket Workflow System** provides a Kanban-style state machine for orchestrating ticket lifecycle across multiple phases (analyzing, building, testing), with automatic progression, blocking detection, and parallel processing capabilities. It coordinates phase gates, manages ticket-to-task mapping, and integrates with the Task Queue and Validation systems to provide end-to-end workflow orchestration.

- **Purpose and scope**:
  - Define the Kanban state machine implementation (backlog → analyzing → building → building-done → testing → done) with blocked states.
  - Specify phase orchestration mechanisms including gate criteria, task seeding, and rollback support.
  - Describe blocking detection algorithms with threshold-based triggers and alert generation.
  - Define parallel processing rules with dependency checking and concurrency limits.
  - Specify data models, APIs, and integration points with Task Queue and Validation systems.
- **Target audience**:
  - AI spec agents defining workflow orchestration.
  - Implementation teams building ticket lifecycle management, phase gates, and blocking detection.
  - System architects integrating ticket workflow with Task Queue, Validation, and Monitoring systems.
- **Related documents**:
  - Requirements: `docs/requirements/workflows/ticket_workflow.md`
  - Orchestration Design: `docs/design/multi_agent_orchestration.md`
  - Task Queue Management: `docs/design/task_queue_management.md`
  - Validation System: `docs/design/validation_system.md`
  - Related requirements:
    - `docs/requirements/workflows/task_queue_management.md`
    - `docs/requirements/workflows/validation_system.md`
    - `docs/requirements/monitoring/monitoring_architecture.md`

---

## Architecture Overview

### High-Level Architecture

```mermaid
flowchart TD
    subgraph TicketWorkflowLayer[Ticket Workflow Layer]
        TW[Ticket Workflow Orchestrator]
        BD[Blocking Detector]
        PG[Phase Gate Manager]
        TA[Ticket Store (DB)]
    end

    subgraph TaskQueueLayer[Task Queue Layer]
        TQ[Task Queue Service]
        TS[Task Store]
    end

    subgraph ValidationLayer[Validation Layer]
        VO[Validation Orchestrator]
        VS[Validation Store]
    end

    subgraph AgentLayer[Agent Execution Layer]
        WA[Worker Agents]
    end

    subgraph IntegrationLayer[Integration Layer]
        EB[Event Bus / WebSocket Gateway]
        MON[Monitoring Service]
    end

    TW -->|create ticket| TA
    TW -->|seed phase tasks| TQ
    TQ -->|assign tasks| WA
    WA -->|complete tasks| TQ
    TQ -->|phase complete| PG
    PG -->|check gate criteria| VO
    VO -->|validation result| PG
    PG -->|advance phase| TW
    TW -->|update status| TA

    BD -->|monitor tickets| TA
    BD -->|detect blocking| TW
    TW -->|emit alerts| EB
    TW -->|create unblock tasks| TQ

    TW -->|query parallel tickets| TA
    TW -->|enforce concurrency| MON
```

### Component Responsibilities

| Component | Layer | Responsibilities |
|-----------|-------|------------------|
| Ticket Workflow Orchestrator | Workflow | Enforces Kanban state machine, orchestrates phase transitions, manages ticket-to-task mapping, coordinates with Task Queue for task seeding, handles phase rollbacks, emits lifecycle events. |
| Phase Gate Manager | Workflow | Validates phase completion criteria, coordinates with Validation System for gate validation, manages phase artifacts, triggers phase transitions. |
| Blocking Detector | Workflow | Monitors ticket state duration, detects blocking conditions based on thresholds, classifies blocker types (dependency, waiting_on_clarification, failing_checks, environment), generates alerts and remediation tasks. |
| Ticket Store | Workflow | Persists Ticket records with state tracking, phase artifacts, blocking metadata; exposes query primitives for state machine transitions and parallel processing analysis. |
| Task Queue Service | Task Queue | Receives task seeding requests from Ticket Workflow, manages task assignment to agents, reports task completion to Phase Gate Manager, enforces task dependencies. |
| Validation Orchestrator | Validation | Validates phase gate artifacts (e.g., building-done artifacts, testing evidence), returns validation results to Phase Gate Manager. |
| Worker Agents | Agent | Execute tasks seeded by Ticket Workflow phases, update task status, provide phase completion artifacts. |
| Event Bus / WebSocket Gateway | Integration | Broadcasts ticket lifecycle events (`ticket_created`, `phase_transitioned`, `ticket_blocked`, `ticket_unblocked`, `ticket_done`) to clients. |
| Monitoring Service | Integration | Provides system-wide resource utilization metrics, enforces concurrency limits, tracks ticket metrics (lead time, blocked time ratio, reopen rate). |

### System Boundaries

- **Within scope of Ticket Workflow System**:
  - Managing Kanban state machine (backlog → analyzing → building → building-done → testing → done) with blocked states.
  - Orchestrating phase transitions based on gate criteria and task completion.
  - Detecting blocking conditions and generating remediation actions.
  - Enforcing parallel processing rules with dependency checking and concurrency limits.
  - Managing ticket-to-task mapping and phase task seeding.
  - Persisting ticket state and phase artifacts.
  - Emitting ticket lifecycle events.

- **Out of scope (delegated)**:
  - Task Queue internal implementation (task priority scoring, assignment logic).
  - Validation System internal validation workflows (validator agent spawning, review persistence).
  - Agent lifecycle management (agent spawning, health monitoring, resource allocation).
  - Workspace Isolation (workspace provisioning, Git operations, sandbox management).
  - Memory System internal storage and retrieval.

---

## Component Details

### Ticket Workflow Orchestrator

The **Ticket Workflow Orchestrator** is the core service responsible for enforcing the Kanban state machine, orchestrating phase transitions, managing ticket-to-task relationships, and coordinating with Task Queue and Validation systems.

#### State Machine Enforcement (REQ-TKT-SM-001, REQ-TKT-SM-002)

The orchestrator enforces the following state transitions:

- **States** (REQ-TKT-SM-001):
  - `backlog`: Initial state for newly created tickets.
  - `analyzing`: Requirements analysis and scope clarification phase.
  - `building`: Implementation and code editing phase.
  - `building-done`: Building phase complete, awaiting gate validation.
  - `testing`: Testing and validation phase.
  - `done`: Ticket completed successfully.
  - `blocked`: Overlay state indicating ticket is blocked (used alongside current phase).

- **Valid Transitions** (REQ-TKT-SM-002):
  ```
  backlog → analyzing
  analyzing → building | blocked
  building → building-done | blocked
  building-done → testing | blocked
  testing → done | building (on fix needed) | blocked
  blocked → analyzing | building | building-done | testing
  ```

- **Automatic Progression** (REQ-TKT-SM-003):
  - When a phase completes (all tasks done and gate criteria met), automatically advance to the next phase.
  - Progression triggers:
    - Phase gate validation passes.
    - All phase tasks are marked complete.
    - No blocking conditions detected.

- **Regressions** (REQ-TKT-SM-004):
  - Failed validation/testing regresses ticket to the previous actionable phase (e.g., `testing → building` on fix needed).
  - Regression preserves context: phase artifacts, validation feedback, and blocking reasons are attached to the ticket.

#### Phase Task Seeding (REQ-TKT-PH-002)

When a ticket enters a phase, the orchestrator seeds initial tasks via Task Queue Service:

- **Analyzing Phase**:
  - Task: "Analyze requirements and clarify scope"
  - Capability: `analysis`
  - Dependencies: None
  - Artifacts expected: Requirements doc/diffs, clarified scope

- **Building Phase**:
  - Task: "Implement code changes"
  - Capability: `implementation`
  - Dependencies: Analyzing phase tasks (if applicable)
  - Artifacts expected: Merged edits, CI green build

- **Building-Done Phase**:
  - Task: "Package and prepare handoff bundle"
  - Capability: `packaging`
  - Dependencies: Building phase tasks
  - Artifacts expected: Packaging bundle, handoff documentation

- **Testing Phase**:
  - Task: "Execute unit/integration/E2E tests"
  - Capability: `testing`
  - Dependencies: Building-done phase tasks
  - Artifacts expected: Test results, test evidence

#### Phase Rollback Support (REQ-TKT-PH-003)

On phase failure or regression:

- Preserve all artifacts from the current phase in `PhaseGateArtifacts`.
- Store rollback context: validation feedback, blocking reasons, failed task IDs.
- Maintain ticket state history for audit trail.
- Enable deterministic re-entry to the previous phase with preserved context.

### Phase Gate Manager

The **Phase Gate Manager** validates phase completion criteria and coordinates gate validation with the Validation System.

#### Phase Gate Criteria (REQ-TKT-PH-001)

Each phase defines completion criteria and required artifacts:

| Phase | Completion Criteria | Required Artifacts |
|-------|-------------------|-------------------|
| `analyzing` | Requirements document generated, scope clarified | Requirements doc/diffs, clarified scope document |
| `building` | All code changes merged, CI build green | Merged edits (commit SHAs), CI build status |
| `building-done` | Packaging complete, handoff bundle ready | Packaging bundle URI, handoff documentation |
| `testing` | All tests passing, evidence provided | Test results (unit/integration/E2E), test evidence URIs |

#### Gate Validation Flow

1. **Phase Completion Detection**:
   - Monitor task completion for all tasks in current phase.
   - When all tasks complete, collect phase artifacts.

2. **Artifact Validation**:
   - Coordinate with Validation Orchestrator to validate artifacts against gate criteria.
   - Validation Orchestrator returns pass/fail with feedback.

3. **Gate Decision**:
   - If validation passes: trigger phase transition to next phase.
   - If validation fails: regress to previous actionable phase with feedback.

4. **Artifact Persistence**:
   - Store validated artifacts in `PhaseGateArtifacts` table.
   - Link artifacts to ticket and phase for audit trail.

### Blocking Detector

The **Blocking Detector** monitors ticket state duration and detects blocking conditions based on thresholds and task progress.

#### Blocking Threshold (REQ-TKT-BL-001)

- Monitor tickets in non-terminal states (`backlog`, `analyzing`, `building`, `building-done`, `testing`).
- If a ticket remains in the same state longer than `BLOCKING_THRESHOLD` (default: 30 minutes) with no task progress, mark as `blocked`.
- Task progress indicators:
  - New tasks completed.
  - Task status updates (in_progress → done).
  - Agent activity (heartbeats, log events).

#### Blocker Classification (REQ-TKT-BL-002)

Blockers are classified into categories that influence remediation:

| Blocker Type | Description | Remediation Tasks |
|--------------|-------------|-------------------|
| `dependency` | Waiting on another ticket or external dependency | Create dependency tracking task, notify dependent ticket |
| `waiting_on_clarification` | Waiting for user/clarification input | Create clarification request task, notify stakeholders |
| `failing_checks` | Tests or validation failing | Create fix task, attach validation feedback |
| `environment` | Environment or resource issues | Create environment remediation task, escalate to Monitoring |

#### Alert Generation (REQ-TKT-BL-003)

When blocking is detected:

1. **Mark Ticket as Blocked**:
   - Set `ticket.blocked = true`.
   - Set `ticket.blocked_reason` to classified blocker type.
   - Record `ticket.blocked_at` timestamp.

2. **Emit Alert Event**:
   - Event: `ticket_blocked`
   - Payload: ticket_id, blocker_type, suggested_remediation, timestamp
   - Broadcast via Event Bus / WebSocket Gateway.

3. **Auto-Create Remediation Tasks**:
   - Based on blocker classification, create unblocking tasks via Task Queue:
     - For `dependency`: Create "Resolve dependency" task.
     - For `waiting_on_clarification`: Create "Request clarification" task.
     - For `failing_checks`: Create "Fix failing checks" task (attach validation feedback).
     - For `environment`: Create "Fix environment" task.

### Ticket Store

The **Ticket Store** provides persistence for ticket records, phase artifacts, and state history.

#### Core Responsibilities

- Persist `Ticket` records with state, phase, and blocking metadata.
- Store `PhaseGateArtifacts` linked to tickets and phases.
- Maintain ticket state history for audit trail.
- Expose query primitives for:
  - State machine transitions (find tickets by state, phase).
  - Parallel processing analysis (find independent tickets, check dependencies).
  - Blocking analysis (find blocked tickets, aggregate blocker types).
  - Metrics queries (lead time, blocked time ratio, reopen rate).

---

## Kanban State Machine

### State Machine Diagram

```mermaid
stateDiagram-v2
    [*] --> backlog
    backlog --> analyzing

    analyzing --> building : Phase tasks complete\nGate criteria met
    analyzing --> blocked : Threshold exceeded\nNo task progress

    building --> building-done : Phase tasks complete\nGate criteria met
    building --> blocked : Threshold exceeded\nNo task progress

    building-done --> testing : Phase tasks complete\nGate criteria met
    building-done --> blocked : Threshold exceeded\nNo task progress

    testing --> done : Phase tasks complete\nGate criteria met\nAll tests passing
    testing --> building : Fix needed\nValidation fails
    testing --> blocked : Threshold exceeded\nNo task progress

    blocked --> analyzing : Unblocked
    blocked --> building : Unblocked
    blocked --> building-done : Unblocked
    blocked --> testing : Unblocked

    done --> [*]
```

### State Transition Logic

#### Normal Progression

1. **backlog → analyzing**:
   - Trigger: Manual assignment or automatic queue processing.
   - Action: Seed analyzing phase tasks, set `current_phase = "analyzing"`.

2. **analyzing → building**:
   - Precondition: All analyzing tasks complete, gate criteria met (requirements doc present).
   - Action: Seed building phase tasks, set `current_phase = "building"`.

3. **building → building-done**:
   - Precondition: All building tasks complete, gate criteria met (CI green).
   - Action: Seed building-done phase tasks, set `current_phase = "building-done"`.

4. **building-done → testing**:
   - Precondition: All building-done tasks complete, gate criteria met (packaging bundle ready).
   - Action: Seed testing phase tasks, set `current_phase = "testing"`.

5. **testing → done**:
   - Precondition: All testing tasks complete, gate criteria met (all tests passing).
   - Action: Mark ticket as done, emit `ticket_done` event.

#### Blocking Transitions

- **Any phase → blocked**:
  - Trigger: Blocking Detector detects threshold exceeded with no task progress.
  - Action: Set `blocked = true`, set `blocked_reason`, emit `ticket_blocked` event.

- **blocked → previous phase**:
  - Trigger: Remediation task completes or blocking condition resolved.
  - Action: Clear `blocked = false`, clear `blocked_reason`, emit `ticket_unblocked` event.

#### Regression Transitions

- **testing → building**:
  - Trigger: Validation fails or tests fail, fix needed.
  - Precondition: Received validation feedback indicating fix required.
  - Action: Regress to building phase, attach validation feedback to ticket, seed fix tasks.

---

## Phase Orchestration

### Phase Sequence

The ticket workflow follows a strict phase sequence:

```
backlog → analyzing → building → building-done → testing → done
```

Each phase must complete before the next begins, with the exception of regressions (testing → building).

### Phase Handoff

Phase handoffs occur when:

1. **All phase tasks complete**: Task Queue Service reports all tasks in the current phase are done.
2. **Gate criteria validated**: Phase Gate Manager validates artifacts against gate criteria via Validation System.
3. **No blocking conditions**: Blocking Detector confirms no blocking conditions exist.
4. **Next phase ready**: Ticket Workflow Orchestrator seeds tasks for the next phase and updates ticket state.

### Phase Artifacts Management

Each phase produces artifacts that are:

- **Collected**: Phase Gate Manager collects artifacts from completed tasks.
- **Validated**: Validation Orchestrator validates artifacts against gate criteria.
- **Persisted**: Artifacts stored in `PhaseGateArtifacts` table with links to ticket and phase.
- **Preserved**: Artifacts preserved during rollbacks for context restoration.

### Rollback Handling

When a phase fails validation or testing fails:

1. **Preserve Context**:
   - Store current phase artifacts in `PhaseGateArtifacts`.
   - Record validation feedback and failure reasons in ticket metadata.
   - Maintain state history for audit trail.

2. **Regress Phase**:
   - Update ticket state to previous actionable phase (e.g., `testing → building`).
   - Set `ticket.regression_count` += 1.

3. **Seed Fix Tasks**:
   - Create tasks with validation feedback attached.
   - Mark tasks as fix-related to distinguish from initial implementation.

4. **Restore Context**:
   - Attach previous phase artifacts to new phase tasks for context.
   - Enable deterministic re-entry to previous phase.

---

## Blocking Detection

### Detection Algorithm

The Blocking Detector runs periodically (default: every 5 minutes) to monitor tickets:

```python
def detect_blocking(ticket: Ticket, threshold: timedelta) -> Optional[BlockingCondition]:
    """Detect if ticket is blocked based on state duration and task progress."""

    # Check if ticket is in a non-terminal state
    if ticket.status in [TicketStatusEnum.DONE]:
        return None

    # Calculate time in current state
    time_in_state = now() - ticket.state_entered_at

    # Check threshold
    if time_in_state < threshold:
        return None

    # Check task progress
    recent_progress = check_recent_task_progress(ticket.id, threshold)
    if recent_progress:
        return None  # Task progress detected, not blocked

    # Classify blocker type
    blocker_type = classify_blocker(ticket)

    return BlockingCondition(
        ticket_id=ticket.id,
        blocker_type=blocker_type,
        detected_at=now(),
        time_in_state=time_in_state
    )
```

### Blocker Classification Logic

```python
def classify_blocker(ticket: Ticket) -> BlockerType:
    """Classify blocker type based on ticket context and task analysis."""

    # Check for dependency blockers
    if has_unresolved_dependencies(ticket):
        return BlockerType.DEPENDENCY

    # Check for clarification blockers
    if has_pending_clarifications(ticket):
        return BlockerType.WAITING_ON_CLARIFICATION

    # Check for failing checks
    if has_failing_checks(ticket):
        return BlockerType.FAILING_CHECKS

    # Check for environment issues
    if has_environment_issues(ticket):
        return BlockerType.ENVIRONMENT

    # Default to dependency if unknown
    return BlockerType.DEPENDENCY
```

### Remediation Task Generation

When blocking is detected, remediation tasks are auto-created:

```python
def create_remediation_tasks(ticket: Ticket, blocker_type: BlockerType) -> List[Task]:
    """Create remediation tasks based on blocker classification."""

    tasks = []

    if blocker_type == BlockerType.DEPENDENCY:
        tasks.append(Task(
            ticket_id=ticket.id,
            title="Resolve dependency",
            description=f"Resolve blocking dependency for ticket {ticket.id}",
            capability="dependency_resolution",
            priority="HIGH"
        ))

    elif blocker_type == BlockerType.WAITING_ON_CLARIFICATION:
        tasks.append(Task(
            ticket_id=ticket.id,
            title="Request clarification",
            description=f"Request clarification for ticket {ticket.id}",
            capability="communication",
            priority="HIGH"
        ))

    elif blocker_type == BlockerType.FAILING_CHECKS:
        tasks.append(Task(
            ticket_id=ticket.id,
            title="Fix failing checks",
            description=f"Fix failing checks for ticket {ticket.id}",
            capability="testing",
            priority="HIGH",
            metadata={"validation_feedback": ticket.last_validation_feedback}
        ))

    elif blocker_type == BlockerType.ENVIRONMENT:
        tasks.append(Task(
            ticket_id=ticket.id,
            title="Fix environment",
            description=f"Fix environment issues for ticket {ticket.id}",
            capability="infrastructure",
            priority="CRITICAL"
        ))

    return tasks
```

---

## Parallel Processing Rules

### Independence Analysis (REQ-TKT-PL-001)

Tickets without inter-ticket dependencies may run in parallel up to `MAX_CONCURRENT_TICKETS` (default: 50).

#### Dependency Detection

```python
def check_ticket_dependencies(ticket: Ticket) -> List[str]:
    """Check for inter-ticket dependencies."""

    dependencies = []

    # Check explicit dependencies in metadata
    if "depends_on" in ticket.metadata:
        dependencies.extend(ticket.metadata["depends_on"])

    # Check for implicit dependencies (same workspace, conflicting files)
    if "workspace_id" in ticket.metadata:
        conflicting_tickets = find_conflicting_tickets(
            workspace_id=ticket.metadata["workspace_id"],
            files=ticket.metadata.get("files", [])
        )
        dependencies.extend(conflicting_tickets)

    return dependencies
```

#### Parallel Eligibility

A ticket is eligible for parallel processing if:

1. **No inter-ticket dependencies**: `check_ticket_dependencies(ticket) == []`.
2. **Within concurrency limit**: Current active tickets < `MAX_CONCURRENT_TICKETS`.
3. **Resources available**: Monitoring Service confirms resource availability.

### Resource Guardrails (REQ-TKT-PL-002)

Parallelism must respect resource budgets; Monitoring Service may throttle globally.

#### Resource Budget Enforcement

```python
def check_resource_availability() -> bool:
    """Check if system has capacity for additional parallel tickets."""

    # Check resource utilization
    cpu_utilization = monitoring_service.get_cpu_utilization()
    memory_utilization = monitoring_service.get_memory_utilization()
    agent_count = monitoring_service.get_active_agent_count()

    # Enforce resource limits
    if cpu_utilization > 0.8:
        return False  # CPU threshold exceeded

    if memory_utilization > 0.85:
        return False  # Memory threshold exceeded

    if agent_count >= MAX_AGENTS:
        return False  # Agent capacity reached

    return True
```

### Affinity/Anti-Affinity (REQ-TKT-PL-003)

Prefer agent affinity for continuity but apply anti-affinity to avoid hotspots when utilization > 80%.

#### Agent Affinity Rules

```python
def assign_ticket_to_agent(ticket: Ticket, agents: List[Agent]) -> Optional[Agent]:
    """Assign ticket to agent with preference for continuity."""

    # Prefer agents that previously worked on this ticket
    previous_agents = get_previous_agents(ticket.id)
    if previous_agents:
        available_previous = [a for a in previous_agents if a.is_available() and a.utilization < 0.8]
        if available_previous:
            return available_previous[0]

    # Apply anti-affinity if utilization high
    utilization = monitoring_service.get_system_utilization()
    if utilization > 0.8:
        # Avoid hot agents (utilization > 80%)
        available_agents = [a for a in agents if a.utilization < 0.8 and a.is_available()]
        if available_agents:
            return min(available_agents, key=lambda a: a.utilization)

    # Default: assign to least utilized available agent
    available_agents = [a for a in agents if a.is_available()]
    if available_agents:
        return min(available_agents, key=lambda a: a.utilization)

    return None
```

---

## Data Models

### Database Schema

#### Tickets Table

```sql
CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('backlog', 'analyzing', 'building', 'building-done', 'testing', 'done')),
    priority VARCHAR(20) NOT NULL CHECK (priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    current_phase VARCHAR(50) NOT NULL CHECK (current_phase IN ('REQUIREMENTS', 'IMPLEMENTATION', 'VALIDATION', 'ANALYSIS', 'TESTING')),
    blocked BOOLEAN NOT NULL DEFAULT FALSE,
    blocked_reason VARCHAR(100),
    blocked_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    state_entered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    regression_count INTEGER NOT NULL DEFAULT 0,
    assigned_agents UUID[] DEFAULT ARRAY[]::UUID[],
    tasks UUID[] DEFAULT ARRAY[]::UUID[],
    metadata JSONB DEFAULT '{}'::JSONB,

    CONSTRAINT tickets_status_check CHECK (
        (status = 'done' AND blocked = FALSE) OR
        (status != 'done')
    )
);

CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_blocked ON tickets(blocked) WHERE blocked = TRUE;
CREATE INDEX idx_tickets_current_phase ON tickets(current_phase);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_tickets_created_at ON tickets(created_at);
CREATE INDEX idx_tickets_state_entered_at ON tickets(state_entered_at) WHERE status != 'done';
```

#### Phase Gate Artifacts Table

```sql
CREATE TABLE phase_gate_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    phase VARCHAR(50) NOT NULL CHECK (phase IN ('analyzing', 'building', 'building-done', 'testing')),
    analyzing_artifacts TEXT[] DEFAULT ARRAY[]::TEXT[],
    building_artifacts TEXT[] DEFAULT ARRAY[]::TEXT[],
    packaging_bundle_uri VARCHAR(500),
    testing_evidence TEXT[] DEFAULT ARRAY[]::TEXT[],
    last_phase_passed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT phase_gate_artifacts_ticket_phase_unique UNIQUE (ticket_id, phase)
);

CREATE INDEX idx_phase_gate_artifacts_ticket_id ON phase_gate_artifacts(ticket_id);
CREATE INDEX idx_phase_gate_artifacts_phase ON phase_gate_artifacts(phase);
```

#### Ticket State History Table

```sql
CREATE TABLE ticket_state_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    from_status VARCHAR(50),
    to_status VARCHAR(50) NOT NULL,
    from_phase VARCHAR(50),
    to_phase VARCHAR(50) NOT NULL,
    transition_reason TEXT,
    blocked BOOLEAN NOT NULL DEFAULT FALSE,
    blocked_reason VARCHAR(100),
    metadata JSONB DEFAULT '{}'::JSONB,
    transitioned_at TIMESTAMP NOT NULL DEFAULT NOW(),
    transitioned_by UUID, -- Agent ID if automated

    CONSTRAINT ticket_state_history_status_check CHECK (
        to_status IN ('backlog', 'analyzing', 'building', 'building-done', 'testing', 'done')
    )
);

CREATE INDEX idx_ticket_state_history_ticket_id ON ticket_state_history(ticket_id);
CREATE INDEX idx_ticket_state_history_transitioned_at ON ticket_state_history(transitioned_at);
CREATE INDEX idx_ticket_state_history_to_status ON ticket_state_history(to_status);
```

### Pydantic Models

```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class TicketStatusEnum(str, Enum):
    BACKLOG = "backlog"
    ANALYZING = "analyzing"
    BUILDING = "building"
    BUILDING_DONE = "building-done"
    TESTING = "testing"
    DONE = "done"


class BlockerType(str, Enum):
    DEPENDENCY = "dependency"
    WAITING_ON_CLARIFICATION = "waiting_on_clarification"
    FAILING_CHECKS = "failing_checks"
    ENVIRONMENT = "environment"


class Ticket(BaseModel):
    id: str
    title: str
    description: str
    status: TicketStatusEnum
    priority: str  # CRITICAL | HIGH | MEDIUM | LOW
    current_phase: str  # REQUIREMENTS | IMPLEMENTATION | VALIDATION | ANALYSIS | TESTING
    blocked: bool = False
    blocked_reason: Optional[BlockerType] = None
    blocked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    state_entered_at: datetime
    regression_count: int = 0
    assigned_agents: List[str] = Field(default_factory=list)
    tasks: List[str] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)


class PhaseGateArtifacts(BaseModel):
    ticket_id: str
    phase: str  # analyzing | building | building-done | testing
    analyzing_artifacts: List[str] = Field(default_factory=list)
    building_artifacts: List[str] = Field(default_factory=list)
    packaging_bundle_uri: Optional[str] = None
    testing_evidence: List[str] = Field(default_factory=list)
    last_phase_passed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class BlockingCondition(BaseModel):
    ticket_id: str
    blocker_type: BlockerType
    detected_at: datetime
    time_in_state: timedelta
    suggested_remediation: Optional[str] = None
```

---

## API Specifications

### Ticket CRUD Operations

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| POST | `/api/tickets` | Create new ticket | `{title, description, priority, metadata?}` | `{ticket_id, status, created_at}` |
| GET | `/api/tickets/{ticket_id}` | Get ticket details | - | `{ticket details}` |
| PUT | `/api/tickets/{ticket_id}` | Update ticket | `{title?, description?, priority?, metadata?}` | `{ticket details}` |
| DELETE | `/api/tickets/{ticket_id}` | Delete ticket | - | `{success}` |
| GET | `/api/tickets` | List tickets | `{status?, phase?, blocked?, limit?, offset?}` | `{tickets[], total}` |

### Phase Transition Operations

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| POST | `/api/tickets/{ticket_id}/transition` | Transition ticket phase | `{to_status, to_phase, reason?}` | `{ticket details}` |
| POST | `/api/tickets/{ticket_id}/regress` | Regress ticket phase | `{to_phase, reason, validation_feedback?}` | `{ticket details}` |
| POST | `/api/tickets/{ticket_id}/unblock` | Unblock ticket | `{reason?}` | `{ticket details}` |

### Blocking Detection Operations

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| GET | `/api/tickets/blocked` | List blocked tickets | `{blocker_type?, limit?, offset?}` | `{tickets[], total}` |
| POST | `/api/tickets/{ticket_id}/block` | Manually block ticket | `{blocker_type, reason}` | `{ticket details}` |
| POST | `/api/tickets/{ticket_id}/remediation-tasks` | Get remediation tasks | - | `{tasks[]}` |

### Phase Gate Operations

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| GET | `/api/tickets/{ticket_id}/artifacts` | Get phase artifacts | `{phase?}` | `{artifacts}` |
| POST | `/api/tickets/{ticket_id}/artifacts` | Store phase artifacts | `{phase, artifacts}` | `{artifacts}` |
| POST | `/api/tickets/{ticket_id}/validate-gate` | Validate phase gate | `{phase}` | `{valid, feedback?}` |

### Request/Response Models

#### Create Ticket Request

```python
class CreateTicketRequest(BaseModel):
    title: str
    description: str
    priority: str  # CRITICAL | HIGH | MEDIUM | LOW
    metadata: Optional[Dict[str, str]] = None
```

#### Transition Ticket Request

```python
class TransitionTicketRequest(BaseModel):
    to_status: TicketStatusEnum
    to_phase: str
    reason: Optional[str] = None
```

#### Block Ticket Request

```python
class BlockTicketRequest(BaseModel):
    blocker_type: BlockerType
    reason: str
```

### Error Handling

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | `INVALID_TRANSITION` | Invalid state transition attempted |
| 400 | `MISSING_ARTIFACTS` | Phase gate validation failed, artifacts missing |
| 400 | `GATE_CRITERIA_NOT_MET` | Phase gate criteria not met |
| 404 | `TICKET_NOT_FOUND` | Ticket not found |
| 409 | `TICKET_BLOCKED` | Ticket is blocked, transition not allowed |
| 500 | `INTERNAL_ERROR` | Internal server error |

---

## Integration Points

### Task Queue Integration

The Ticket Workflow System integrates with the Task Queue Service for task seeding and management.

#### Ticket-to-Task Mapping

- **Task Seeding**: When a ticket enters a phase, the orchestrator seeds initial tasks via Task Queue Service API:
  ```python
  task_queue_service.create_tasks(
      ticket_id=ticket.id,
      phase=ticket.current_phase,
      tasks=phase_task_templates[ticket.current_phase],
      dependencies=previous_phase_tasks
  )
  ```

- **Task Completion Tracking**: Task Queue Service reports task completion to Ticket Workflow Orchestrator:
  ```python
  task_queue_service.on_task_complete(
      callback=lambda task_id, result: handle_task_completion(ticket_id, task_id, result)
  )
  ```

- **Phase Completion Detection**: When all phase tasks complete, Task Queue Service notifies Phase Gate Manager:
  ```python
  if all_phase_tasks_complete(ticket.current_phase):
      phase_gate_manager.validate_phase_gate(ticket.id, ticket.current_phase)
  ```

### Validation System Integration

The Ticket Workflow System integrates with the Validation System for phase gate validation.

#### Phase Gate Validation

- **Gate Criteria Validation**: Phase Gate Manager coordinates with Validation Orchestrator to validate artifacts:
  ```python
  validation_result = validation_orchestrator.validate_artifacts(
      ticket_id=ticket.id,
      phase=ticket.current_phase,
      artifacts=phase_artifacts
  )
  ```

- **Validation Feedback**: When validation fails, Validation System provides feedback for regression:
  ```python
  if not validation_result.passed:
      ticket_workflow_orchestrator.regress_phase(
          ticket_id=ticket.id,
          to_phase=previous_actionable_phase,
          validation_feedback=validation_result.feedback
      )
  ```

### Monitoring Service Integration

The Ticket Workflow System integrates with Monitoring Service for resource management and metrics.

#### Resource Availability

- **Concurrency Limits**: Monitoring Service enforces resource budgets:
  ```python
  if monitoring_service.check_resource_availability():
      ticket_workflow_orchestrator.process_parallel_tickets()
  else:
      ticket_workflow_orchestrator.throttle_parallel_processing()
  ```

#### Metrics Tracking

- **Lead Time**: Track ticket lead time (backlog → done) and phase cycle times:
  ```python
  metrics = {
      "lead_time": ticket.done_at - ticket.created_at,
      "phase_cycle_times": calculate_phase_cycle_times(ticket),
      "blocked_time_ratio": calculate_blocked_time_ratio(ticket)
  }
  monitoring_service.record_ticket_metrics(ticket.id, metrics)
  ```

### Event Bus / WebSocket Gateway Integration

The Ticket Workflow System emits lifecycle events via Event Bus for real-time updates.

#### Event Types

- `ticket_created`: Ticket created in backlog.
- `phase_transitioned`: Ticket transitioned to new phase.
- `ticket_blocked`: Ticket marked as blocked.
- `ticket_unblocked`: Ticket unblocked.
- `ticket_done`: Ticket completed successfully.

#### Event Payload

```python
{
    "event_type": "ticket_blocked",
    "ticket_id": "uuid",
    "blocker_type": "dependency",
    "suggested_remediation": "Resolve dependency",
    "timestamp": "2025-11-16T10:00:00Z"
}
```

---

## Implementation Details

### Phase Transition Algorithm

```python
def transition_phase(ticket: Ticket, to_phase: str) -> Ticket:
    """Transition ticket to new phase with validation and task seeding."""

    # Validate transition
    if not is_valid_transition(ticket.current_phase, to_phase):
        raise InvalidTransitionError(f"Cannot transition from {ticket.current_phase} to {to_phase}")

    # Check blocking conditions
    if ticket.blocked:
        raise TicketBlockedError("Ticket is blocked, cannot transition")

    # Validate phase gate criteria
    if ticket.current_phase != "backlog":
        validation_result = phase_gate_manager.validate_phase_gate(ticket.id, ticket.current_phase)
        if not validation_result.passed:
            raise GateCriteriaNotMetError(validation_result.feedback)

    # Collect phase artifacts
    artifacts = collect_phase_artifacts(ticket.id, ticket.current_phase)

    # Store artifacts in PhaseGateArtifacts
    phase_gate_artifacts = store_phase_artifacts(ticket.id, ticket.current_phase, artifacts)

    # Update ticket state
    previous_phase = ticket.current_phase
    ticket.current_phase = to_phase
    ticket.status = map_phase_to_status(to_phase)
    ticket.state_entered_at = now()
    ticket.updated_at = now()

    # Persist ticket
    ticket = ticket_store.update_ticket(ticket)

    # Record state history
    record_state_transition(ticket.id, previous_phase, to_phase)

    # Seed tasks for new phase
    tasks = seed_phase_tasks(ticket.id, to_phase, previous_phase)
    ticket.tasks.extend([task.id for task in tasks])

    # Emit event
    event_bus.publish(TicketPhaseTransitionedEvent(
        ticket_id=ticket.id,
        from_phase=previous_phase,
        to_phase=to_phase,
        timestamp=now()
    ))

    return ticket
```

### Blocking Detection Implementation

```python
def run_blocking_detection():
    """Periodic blocking detection job."""

    # Find tickets in non-terminal states
    tickets = ticket_store.find_tickets_by_status([
        TicketStatusEnum.BACKLOG,
        TicketStatusEnum.ANALYZING,
        TicketStatusEnum.BUILDING,
        TicketStatusEnum.BUILDING_DONE,
        TicketStatusEnum.TESTING
    ])

    threshold = timedelta(minutes=config.BLOCKING_THRESHOLD)

    for ticket in tickets:
        # Skip if already blocked
        if ticket.blocked:
            continue

        # Check blocking condition
        blocking_condition = detect_blocking(ticket, threshold)

        if blocking_condition:
            # Mark ticket as blocked
            ticket.blocked = True
            ticket.blocked_reason = blocking_condition.blocker_type
            ticket.blocked_at = blocking_condition.detected_at
            ticket_store.update_ticket(ticket)

            # Create remediation tasks
            remediation_tasks = create_remediation_tasks(ticket, blocking_condition.blocker_type)
            for task in remediation_tasks:
                task_queue_service.create_task(task)

            # Emit alert event
            event_bus.publish(TicketBlockedEvent(
                ticket_id=ticket.id,
                blocker_type=blocking_condition.blocker_type,
                suggested_remediation=blocking_condition.suggested_remediation,
                timestamp=now()
            ))
```

### Performance Considerations

#### Database Indexing

- **Status Indexes**: Index on `tickets.status` for fast queries by state.
- **Blocked Indexes**: Partial index on `tickets.blocked` for blocked ticket queries.
- **Phase Indexes**: Index on `tickets.current_phase` for phase-based queries.
- **State History Indexes**: Index on `ticket_state_history.transitioned_at` for time-based queries.

#### Caching Strategy

- **Ticket Cache**: Cache frequently accessed tickets in-memory with TTL (default: 5 minutes).
- **Phase Gate Cache**: Cache phase gate validation results for recently validated phases.
- **Blocking Detection Cache**: Cache blocking detection results to avoid redundant checks.

#### Batch Processing

- **Phase Transition Batching**: Batch phase transitions when multiple tickets complete simultaneously.
- **Blocking Detection Batching**: Batch blocking detection checks to reduce database queries.
- **Metrics Batching**: Batch metrics updates to reduce monitoring service load.

---

## SLAs & Metrics

### Lead Time (REQ-TKT-OBS-001)

Track ticket lead time (backlog → done) and phase cycle times; alert on outliers.

#### Metrics

- **Lead Time**: Time from ticket creation to completion.
- **Phase Cycle Times**: Time spent in each phase (analyzing, building, building-done, testing).
- **Outlier Detection**: Alert when lead time exceeds P95 threshold (default: 4 hours).

#### Implementation

```python
def calculate_lead_time(ticket: Ticket) -> timedelta:
    """Calculate ticket lead time."""
    return ticket.done_at - ticket.created_at

def calculate_phase_cycle_time(ticket: Ticket, phase: str) -> timedelta:
    """Calculate time spent in specific phase."""
    phase_transitions = ticket_state_history.filter(
        ticket_id=ticket.id,
        to_phase=phase
    )
    if not phase_transitions:
        return timedelta(0)

    entry_time = phase_transitions[0].transitioned_at
    exit_transitions = ticket_state_history.filter(
        ticket_id=ticket.id,
        from_phase=phase
    )
    if exit_transitions:
        exit_time = exit_transitions[0].transitioned_at
        return exit_time - entry_time

    # Phase still in progress
    return now() - entry_time
```

### Blocked Time Ratio (REQ-TKT-OBS-002)

Track ratio of time blocked vs active; surface top blocker classes weekly.

#### Metrics

- **Blocked Time Ratio**: Percentage of ticket lifetime spent blocked.
- **Blocker Classification**: Aggregate blocker types (dependency, waiting_on_clarification, failing_checks, environment).
- **Weekly Reports**: Generate weekly reports with top blocker classes.

#### Implementation

```python
def calculate_blocked_time_ratio(ticket: Ticket) -> float:
    """Calculate blocked time ratio."""
    total_time = (ticket.updated_at or now()) - ticket.created_at
    blocked_time = calculate_total_blocked_time(ticket)

    if total_time == timedelta(0):
        return 0.0

    return (blocked_time.total_seconds() / total_time.total_seconds()) * 100

def aggregate_blocker_types(start_date: datetime, end_date: datetime) -> Dict[str, int]:
    """Aggregate blocker types for date range."""
    blocked_tickets = ticket_store.find_blocked_tickets(start_date, end_date)

    blocker_counts = {}
    for ticket in blocked_tickets:
        blocker_type = ticket.blocked_reason or "unknown"
        blocker_counts[blocker_type] = blocker_counts.get(blocker_type, 0) + 1

    return blocker_counts
```

### Reopen Rate (REQ-TKT-OBS-003)

Track testing→building regressions per ticket; investigate if above threshold.

#### Metrics

- **Reopen Rate**: Number of regressions (testing → building) per ticket.
- **Threshold Alert**: Alert when reopen rate exceeds threshold (default: 2 regressions per ticket).
- **Investigation Triggers**: Trigger investigation for tickets with high reopen rates.

#### Implementation

```python
def calculate_reopen_rate(ticket: Ticket) -> int:
    """Calculate number of regressions for ticket."""
    regressions = ticket_state_history.filter(
        ticket_id=ticket.id,
        from_phase="testing",
        to_phase="building"
    )
    return len(regressions)

def check_reopen_rate_threshold(ticket: Ticket, threshold: int = 2) -> bool:
    """Check if reopen rate exceeds threshold."""
    reopen_rate = calculate_reopen_rate(ticket)
    if reopen_rate > threshold:
        # Trigger investigation
        trigger_investigation(ticket.id, reopen_rate)
        return True
    return False
```

---

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `BLOCKING_THRESHOLD` | 30m | Time in-state before ticket marked as blocked |
| `MAX_CONCURRENT_TICKETS` | 50 | Maximum number of parallel tickets |
| `PHASE_SEED_BATCH` | 10 | Initial tasks created per phase |
| `BLOCKING_DETECTION_INTERVAL` | 5m | Interval for blocking detection job |
| `LEAD_TIME_P95_THRESHOLD` | 4h | P95 lead time threshold for alerts |
| `REOPEN_RATE_THRESHOLD` | 2 | Reopen rate threshold per ticket |
| `TICKET_CACHE_TTL` | 5m | Ticket cache TTL |
| `PHASE_GATE_CACHE_TTL` | 10m | Phase gate validation cache TTL |

---

## Related Documents

- **Requirements**: `docs/requirements/workflows/ticket_workflow.md`
- **Orchestration Design**: `docs/design/multi_agent_orchestration.md`
- **Task Queue Management**: `docs/design/task_queue_management.md`
- **Validation System**: `docs/design/validation_system.md`
- **Related Requirements**:
  - `docs/requirements/workflows/task_queue_management.md`
  - `docs/requirements/workflows/validation_system.md`
  - `docs/requirements/monitoring/monitoring_architecture.md`

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Design Agent | Initial design document for Ticket Workflow System |

---
