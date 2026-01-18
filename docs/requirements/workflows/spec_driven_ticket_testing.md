# Spec-Driven Ticket Testing Requirements

**Created**: 2026-01-18
**Status**: Draft
**Purpose**: Define the functional requirements for testing the spec-driven ticket workflow, ensuring end-to-end validation of specifications through ticket creation, requirement tracking, and workflow execution.
**Related**: docs/requirements/workflows/ticket_workflow.md, docs/requirements/workflows/task_queue.md

---

## Document Overview

This document specifies requirements for testing the spec-driven ticket workflow in OmoiOS. It covers the validation of specifications through their complete lifecycle, from creation through requirements gathering, design approval, implementation, and completion. These requirements ensure that the spec-driven development process functions correctly and produces reliable, traceable outcomes.

**Parent Document**: [Ticket Workflow Requirements](./ticket_workflow.md)

---

## 1. Spec Lifecycle Testing

### 1.1 Spec Creation and Initialization

#### REQ-SDT-LC-001: Spec Creation Validation
WHEN a new specification is created through the API,
THE SYSTEM SHALL validate that:
- The spec has a unique identifier following the pattern `spec-{uuid}`
- The title and description are non-empty strings
- The initial status is set to `draft`
- The initial phase is set to `Requirements`
- Progress metrics are initialized to zero
- Timestamps (`created_at`, `updated_at`) are set to current UTC time

#### REQ-SDT-LC-002: Project Association
WHEN a specification is created,
THE SYSTEM SHALL verify that:
- The spec is associated with a valid project_id
- The project exists in the database
- The spec appears in the project's specs relationship

#### REQ-SDT-LC-003: Spec Retrieval
WHEN a specification is requested by ID,
THE SYSTEM SHALL return the complete spec including:
- All basic fields (id, title, description, status, phase)
- Associated requirements with their acceptance criteria
- Associated tasks with their statuses
- Design artifacts if present
- Execution metrics if available

---

## 2. Requirements Phase Testing

### 2.1 EARS-Style Requirements

#### REQ-SDT-RQ-001: Requirement Creation Format
WHEN a requirement is added to a specification,
THE SYSTEM SHALL enforce the EARS format:
- A `title` field for brief identification
- A `condition` field representing the "WHEN" clause
- An `action` field representing the "THE SYSTEM SHALL" clause
- Initial status set to `pending`

#### REQ-SDT-RQ-002: Requirement Uniqueness
WHEN multiple requirements are added to a spec,
THE SYSTEM SHALL ensure each requirement has a unique ID following the pattern `req-{uuid}`.

#### REQ-SDT-RQ-003: Requirement Ordering
WHEN requirements are retrieved for a specification,
THE SYSTEM SHALL return them ordered by `created_at` timestamp.

### 2.2 Acceptance Criteria

#### REQ-SDT-AC-001: Acceptance Criterion Creation
WHEN an acceptance criterion is added to a requirement,
THE SYSTEM SHALL:
- Generate a unique ID following the pattern `crit-{uuid}`
- Associate it with the correct requirement_id
- Initialize `completed` status to false

#### REQ-SDT-AC-002: Acceptance Criterion Completeness
WHEN all acceptance criteria for a requirement are marked as completed,
THE SYSTEM SHALL allow the requirement status to transition to `completed`.

#### REQ-SDT-AC-003: Cascade Deletion
WHEN a requirement is deleted,
THE SYSTEM SHALL cascade delete all associated acceptance criteria.

### 2.3 Requirements Approval

#### REQ-SDT-RA-001: Requirements Approval Gate
WHEN requirements are approved for a specification,
THE SYSTEM SHALL:
- Set `requirements_approved` to true
- Record `requirements_approved_at` timestamp
- Transition the spec status from `draft` to `requirements`
- Advance the phase to `Design`

#### REQ-SDT-RA-002: Approval Preconditions
WHEN requirements approval is requested,
THE SYSTEM SHALL verify that:
- At least one requirement exists for the spec
- Each requirement has at least one acceptance criterion
- The spec is currently in `draft` status

---

## 3. Design Phase Testing

### 3.1 Design Artifacts

#### REQ-SDT-DS-001: Design Artifact Storage
WHEN design artifacts are updated for a specification,
THE SYSTEM SHALL store them as JSONB with the following structure:
- `architecture`: System architecture documentation
- `data_model`: Data model specifications
- `api_spec`: API specifications

#### REQ-SDT-DS-002: Design Artifact Retrieval
WHEN a specification is retrieved after design update,
THE SYSTEM SHALL return the complete design artifact structure.

#### REQ-SDT-DS-003: Partial Design Updates
WHEN a partial design update is submitted (some fields null),
THE SYSTEM SHALL merge updates without overwriting existing non-null fields.

### 3.2 Design Approval

#### REQ-SDT-DA-001: Design Approval Gate
WHEN design is approved for a specification,
THE SYSTEM SHALL:
- Set `design_approved` to true
- Record `design_approved_at` timestamp
- Transition the spec status from `requirements` to `design`
- Advance the phase to `Implementation`

#### REQ-SDT-DA-002: Design Approval Preconditions
WHEN design approval is requested,
THE SYSTEM SHALL verify that:
- Requirements have been approved (`requirements_approved` is true)
- At least one design artifact field is populated
- The spec is currently in `requirements` status

---

## 4. Task Generation Testing

### 4.1 Spec Task Creation

#### REQ-SDT-TK-001: Task Creation from Spec
WHEN a task is added to a specification,
THE SYSTEM SHALL:
- Generate a unique ID following the pattern `spec-task-{uuid}`
- Associate it with the correct spec_id
- Require title, description, phase, and priority fields
- Initialize status to `pending`

#### REQ-SDT-TK-002: Task Dependencies
WHEN task dependencies are specified,
THE SYSTEM SHALL:
- Store dependencies as a JSONB array of task IDs
- Validate that dependency IDs reference existing tasks
- Detect and reject circular dependencies

#### REQ-SDT-TK-003: Task Ordering
WHEN tasks are retrieved for a specification,
THE SYSTEM SHALL return them ordered by `created_at` timestamp.

### 4.2 Task Status Transitions

#### REQ-SDT-TS-001: Valid Task Transitions
THE SYSTEM SHALL enforce valid task status transitions:
- `pending` -> `in_progress`
- `in_progress` -> `completed` | `blocked`
- `blocked` -> `in_progress`
- `completed` (terminal state)

#### REQ-SDT-TS-002: Task Progress Tracking
WHEN a task status changes to `completed`,
THE SYSTEM SHALL update the spec's progress percentage based on:
`progress = (completed_tasks / total_tasks) * 100`

---

## 5. End-to-End Workflow Testing

### 5.1 Complete Lifecycle

#### REQ-SDT-E2E-001: Full Spec Lifecycle
THE SYSTEM SHALL support the complete spec lifecycle:
1. Create spec in `draft` status
2. Add requirements with acceptance criteria
3. Approve requirements -> transition to `requirements` status
4. Add design artifacts
5. Approve design -> transition to `design` status
6. Add tasks for implementation
7. Complete tasks -> update progress
8. Mark spec as `completed` when all tasks done

#### REQ-SDT-E2E-002: Status Consistency
WHEN a spec transitions between phases,
THE SYSTEM SHALL maintain consistency between `status` and `phase` fields:
| Status | Phase |
|--------|-------|
| draft | Requirements |
| requirements | Design |
| design | Implementation |
| executing | Implementation/Testing |
| completed | Done |

### 5.2 Ticket Integration

#### REQ-SDT-TI-001: Spec-Ticket Linkage
WHEN a ticket is created from a specification,
THE SYSTEM SHALL:
- Link the ticket to the spec via spec_id reference
- Increment the spec's `linked_tickets` counter
- Copy relevant requirements as ticket acceptance criteria

#### REQ-SDT-TI-002: Ticket Progress Reflection
WHEN tickets linked to a spec change status,
THE SYSTEM SHALL update the spec's execution metrics accordingly.

---

## 6. Error Handling and Validation

### 6.1 Input Validation

#### REQ-SDT-VL-001: Required Field Validation
WHEN creating or updating spec entities,
THE SYSTEM SHALL reject requests with missing required fields and return appropriate error messages.

#### REQ-SDT-VL-002: Foreign Key Validation
WHEN creating entities with foreign key references (spec_id, requirement_id),
THE SYSTEM SHALL verify the referenced entity exists before creation.

### 6.2 State Validation

#### REQ-SDT-ST-001: Invalid Transition Rejection
WHEN an invalid status transition is attempted,
THE SYSTEM SHALL reject the request with a clear error message indicating:
- Current status
- Requested status
- Valid transition options

#### REQ-SDT-ST-002: Approval Order Enforcement
THE SYSTEM SHALL enforce that design approval cannot occur before requirements approval.

---

## 7. Performance Requirements

#### REQ-SDT-PF-001: Spec Retrieval Latency
WHEN retrieving a specification with all relationships,
THE SYSTEM SHALL respond within 200ms (P95) for specs with up to 50 requirements and 100 tasks.

#### REQ-SDT-PF-002: Bulk Operations
WHEN performing bulk operations (adding multiple requirements or tasks),
THE SYSTEM SHALL complete within 500ms (P95) for batches of up to 20 items.

---

## 8. API Endpoint Testing

### 8.1 Spec Endpoints

| Endpoint | Method | Test Cases |
|----------|--------|------------|
| /api/specs | POST | Create spec, validation errors, duplicate handling |
| /api/specs/{id} | GET | Retrieve spec, 404 handling, relationship loading |
| /api/specs/{id} | PUT | Update spec, status transitions, partial updates |
| /api/specs/{id} | DELETE | Delete spec, cascade behavior |

### 8.2 Requirement Endpoints

| Endpoint | Method | Test Cases |
|----------|--------|------------|
| /api/specs/{id}/requirements | POST | Create requirement, EARS validation |
| /api/specs/{id}/requirements/{req_id} | PUT | Update requirement, status transitions |
| /api/specs/{id}/requirements/{req_id}/criteria | POST | Add acceptance criterion |
| /api/specs/{id}/approve-requirements | POST | Approval gate validation |

### 8.3 Design Endpoints

| Endpoint | Method | Test Cases |
|----------|--------|------------|
| /api/specs/{id}/design | PUT | Update design artifacts |
| /api/specs/{id}/approve-design | POST | Design approval gate validation |

### 8.4 Task Endpoints

| Endpoint | Method | Test Cases |
|----------|--------|------------|
| /api/specs/{id}/tasks | POST | Create task, dependency validation |
| /api/specs/{id}/tasks/{task_id} | PUT | Update task, status transitions |

---

## 9. Pydantic Reference Models

```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SpecStatusEnum(str, Enum):
    DRAFT = "draft"
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    EXECUTING = "executing"
    COMPLETED = "completed"


class SpecPhaseEnum(str, Enum):
    REQUIREMENTS = "Requirements"
    DESIGN = "Design"
    IMPLEMENTATION = "Implementation"
    TESTING = "Testing"
    DONE = "Done"


class RequirementStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class AcceptanceCriterion(BaseModel):
    id: str
    requirement_id: str
    text: str
    completed: bool = False
    created_at: datetime
    updated_at: datetime


class SpecRequirement(BaseModel):
    id: str
    spec_id: str
    title: str
    condition: str  # EARS "WHEN" clause
    action: str     # EARS "THE SYSTEM SHALL" clause
    status: RequirementStatusEnum = RequirementStatusEnum.PENDING
    linked_design: Optional[str] = None
    criteria: List[AcceptanceCriterion] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SpecTask(BaseModel):
    id: str
    spec_id: str
    title: str
    description: Optional[str] = None
    phase: str
    priority: str = "medium"
    status: TaskStatusEnum = TaskStatusEnum.PENDING
    assigned_agent: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class DesignArtifact(BaseModel):
    architecture: Optional[str] = None
    data_model: Optional[str] = None
    api_spec: Optional[str] = None


class ExecutionMetrics(BaseModel):
    overall_progress: float = 0.0
    test_coverage: float = 0.0
    tests_total: int = 0
    tests_passed: int = 0
    tests_failed: int = 0


class Spec(BaseModel):
    id: str
    project_id: str
    title: str
    description: Optional[str] = None
    status: SpecStatusEnum = SpecStatusEnum.DRAFT
    phase: SpecPhaseEnum = SpecPhaseEnum.REQUIREMENTS
    progress: float = 0.0
    test_coverage: float = 0.0
    active_agents: int = 0
    linked_tickets: int = 0
    design: Optional[DesignArtifact] = None
    execution: Optional[ExecutionMetrics] = None
    requirements_approved: bool = False
    requirements_approved_at: Optional[datetime] = None
    design_approved: bool = False
    design_approved_at: Optional[datetime] = None
    requirements: List[SpecRequirement] = Field(default_factory=list)
    tasks: List[SpecTask] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SpecTestScenario(BaseModel):
    """Test scenario for spec-driven ticket workflow."""
    name: str
    description: str
    preconditions: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    expected_results: List[str] = Field(default_factory=list)
    priority: str = "medium"
```

---

## 10. Test Scenarios

### Scenario 1: Happy Path - Complete Lifecycle
**Preconditions**: Empty project exists
**Steps**:
1. Create a new spec with title and description
2. Add 3 requirements with EARS format
3. Add acceptance criteria to each requirement
4. Approve requirements
5. Add design artifacts (architecture, data_model, api_spec)
6. Approve design
7. Create 5 tasks for implementation
8. Complete all tasks sequentially
9. Verify spec marked as completed

**Expected Results**:
- Spec progresses through all statuses
- Progress updates after each task completion
- Final progress is 100%
- All timestamps are recorded correctly

### Scenario 2: Validation Failure - Missing Requirements
**Preconditions**: Spec exists in draft status with no requirements
**Steps**:
1. Attempt to approve requirements

**Expected Results**:
- Request is rejected with error message
- Spec remains in draft status

### Scenario 3: Design Before Requirements
**Preconditions**: Spec exists with requirements not approved
**Steps**:
1. Attempt to approve design

**Expected Results**:
- Request is rejected with error indicating requirements must be approved first
- Spec status unchanged

### Scenario 4: Task Dependency Chain
**Preconditions**: Spec in design status
**Steps**:
1. Create Task A (no dependencies)
2. Create Task B (depends on A)
3. Create Task C (depends on B)
4. Attempt to complete Task C before Task A

**Expected Results**:
- Task C cannot be started until dependencies completed
- Completing Task A allows Task B to start
- Completing Task B allows Task C to start

---

## Related Documents

- [Ticket Workflow Requirements](./ticket_workflow.md)
- [Task Queue Management Requirements](./task_queue.md)
- [Agent Lifecycle Management Requirements](../agents/agent_lifecycle.md)
- [Monitoring & Fault Tolerance Requirements](../monitoring/fault_tolerance.md)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-18 | AI Spec Agent | Initial draft |
