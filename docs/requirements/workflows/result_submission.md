# Enhanced Result Submission Requirements

**Created**: 2025-11-20
**Status**: Draft
**Purpose**: Specifies the requirements for agents to submit definitive workflow results, including validation, post‑validation actions, configuration, API, events, SLOs, security, and memory integration.
**Related**: ../multi_agent_orchestration.md, ./validation_system.md, ./task_queue_management.md, ./ticket_workflow.md, ../monitoring/fault_tolerance.md

---


## Document Overview

Defines the workflow-level “result found” submission feature: agents submit a definitive solution, the system validates it via validator agents, and performs configured post-validation actions (stop workflow or continue). Includes configuration, API, events, and Pydantic models.

**Parent Document**: [Multi-Agent Orchestration Requirements](../multi_agent_orchestration.md)

---

## 1. Goals

- Allow agents to declare a definitive workflow result.
- Validate result artifacts against explicit criteria.
- Execute a deterministic post-validation action.
- Maintain full auditability and immutability of validated results.

---

## 2. Behavior

#### REQ-ERS-001: Result Declaration
Agents MAY submit a single “result” artifact (markdown file path or payload reference) at any time when `has_result=true`.

#### REQ-ERS-002: Automatic Validation
On submission, THE SYSTEM SHALL:
1) Spawn a validator agent,
2) Evaluate the result against `result_criteria`,
3) Emit a pass/fail decision with feedback and evidence index.

#### REQ-ERS-003: Post-Validation Action
- If PASS and `on_result_found="stop_all"` → terminate active agents/tasks for the workflow and finalize.
- If PASS and `on_result_found="do_nothing"` → record result, allow workflow to continue.
- If FAIL → record decision; allow further submissions.

#### REQ-ERS-004: Immutability
Validated result records SHALL be immutable (append-only with versioning); follow-up submissions create new records.

---

## 3. Configuration (Normative)

YAML (e.g., phases_config.yaml):

```yaml
has_result: true
result_criteria: |
  Detailed validation criteria...
on_result_found: stop_all  # or "do_nothing"
```

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| has_result | bool | false | Enable result submission |
| result_criteria | str | "" | Human-readable spec consumed by validator |
| on_result_found | enum("stop_all","do_nothing") | "stop_all" | Post-validation behavior |

---

## 4. API (Normative)

### 4.1 Endpoints Table

| Endpoint | Method | Purpose | Request Body (min) | Success (200) | Failures |
|---------|--------|---------|--------------------|---------------|----------|
| /api/results/submit | POST | Submit result | `{ "workflow_id","markdown_file_path","agent_id" }` | `{ "submission_id","status":"submitted" }` | 400 `{ "error" }`, 404 `{ "error" }` |
| /api/results/validate | POST | Validator-only validation | `{ "submission_id","passed","feedback" }` | `{ "submission_id","status":"validated","passed":true|false }` | 403 `{ "error" }` (non-validator), 404 |
| /api/workflows/{id}/results | GET | List results for workflow | — | `[ { "submission_id","passed",... } ]` | 404 |

Notes:
- All errors include `{ "error": "stable_code", "message": "..." }`.
- `validate` is restricted to validator agents.

---

## 5. WebSocket/Event Contracts

| Event | When Emitted | Payload (min) |
|-------|---------------|---------------|
| result_submitted | On submission accepted | `{ "workflow_id","submission_id","agent_id" }` |
| result_validated | On pass/fail decision | `{ "workflow_id","submission_id","passed","feedback" }` |
| workflow_termination_requested | On PASS + stop_all | `{ "workflow_id","submission_id" }` |

---

## 6. SLOs

#### REQ-ERS-SLO-001
- Submission ingestion P95 < 200ms,
- Validation decision P95 < validator_timeout_minutes,
- Termination orchestration P95 < 2s after PASS + stop_all.

---

## 7. Security & Audit

#### REQ-ERS-SEC-001
- Authenticate submitter agent; authorize validator role for validation endpoint.
- Append-only audit log for: submissions, validations, termination actions, configuration used.

---

## 9. Memory Integration

#### REQ-ERS-MEM-001: Persist Final Results
When a result submission is validated (pass or fail), THE SYSTEM SHOULD persist a corresponding memory entry capturing:
- workflow_id and ticket/task identifiers,
- link to the result artifact (markdown file path or stored blob),
- validation outcome and feedback,
- result_criteria snapshot used for the decision.

#### REQ-ERS-MEM-002: Use Prior Results as Context
Agents MAY query the Agent Memory System for prior result submissions on the same workflow or component to:
- avoid duplicate work,
- align with previous conclusions,
- reuse successful methodologies and evidence patterns.

---
## 8. Pydantic Reference Models

```python
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ResultSubmission(BaseModel):
    submission_id: str
    workflow_id: str
    agent_id: str
    markdown_file_path: str
    created_at: datetime
    validated_at: Optional[datetime] = None
    passed: Optional[bool] = None
    feedback: Optional[str] = None
    evidence_index: Dict[str, Any] = {}


class SubmitResultRequest(BaseModel):
    workflow_id: str
    markdown_file_path: str
    agent_id: str


class SubmitResultResponse(BaseModel):
    submission_id: str
    status: str  # "submitted"


class ValidateResultRequest(BaseModel):
    submission_id: str
    passed: bool
    feedback: str
```

---

## Related Documents

- [Validation System Requirements](./validation_system.md)
- [Task Queue Management Requirements](./task_queue_management.md)
- [Ticket Workflow Requirements](./ticket_workflow.md)
- [Monitoring & Fault Tolerance Requirements](../monitoring/fault_tolerance.md)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Spec Agent | Initial draft |


