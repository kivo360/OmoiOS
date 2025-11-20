# Diagnosis Agent Requirements

**Created**: 2025-11-20
**Status**: Draft
**Purpose**: Specify the capabilities, data contracts, triggers, operation flow, and SLOs for the Diagnosis Agent that triages failures and generates remediation recommendations.
**Related**: docs/requirements/multi_agent_orchestration.md, docs/requirements/workflows/task_queue_management.md, docs/requirements/workflows/validation_system.md, docs/requirements/monitoring/fault_tolerance.md, docs/requirements/workflows/result_submission.md

---


## Document Overview

Defines the capabilities, data contracts, and operation flow for the Diagnosis Agent, which investigates failing tasks, anomalies, or blocked tickets; gathers evidence; proposes hypotheses and remediations; and can open follow-up tasks or recommendations.

**Parent Document**: [Multi-Agent Orchestration Requirements](../multi_agent_orchestration.md)

---

## 1. Goals

- Rapidly triage failures and anomalies with structured analyses.
- Reduce mean time to diagnose (MTTD) and guide remediation.
- Produce auditable diagnosis artifacts and actionable recommendations.

---

## 2. Triggers & Scope

#### REQ-DIAG-001: Triggers
Diagnosis MAY be triggered by:
- Task failure (non-transient),
- Ticket blocked status,
- Monitoring alerts (anomaly/quarantine),
- Validation repeated failures,
- Manual request via API.

#### REQ-DIAG-002: Scope
Diagnosis Agent operates read-mostly with least-privilege; it MUST NOT mutate code or state directly. All fixes route through normal implementation tasks.

---

## 3. Operation Flow

#### REQ-DIAG-003
1) Ingest context (task/ticket, recent logs, metrics, traces, validation feedback).  
2) Build diagnosis dossier (symptoms, environment, reproductions).  
3) Generate hypotheses ranked by likelihood.  
4) Propose remediations with risk/effort estimates.  
5) Emit structured report and optionally create follow-up tasks.

---

## 4. Data Model Requirements

### 4.1 DiagnosisReport
Minimum fields:
- `id`, `subject_id` (task_id or ticket_id), `subject_type`, `status` (open|resolved),
- `symptoms`, `evidence`, `environment_snapshot`,
- `hypotheses` (ordered), `root_cause` (if known),
- `recommendations` (actions, priority), `created_at`, `resolved_at?`.

### 4.2 Follow-up Tasks
If configured, Diagnosis Agent MAY request creation of remediation tasks (phase = IMPLEMENTATION or ANALYSIS) with links back to the report.

---

## 5. Configuration (Normative)

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| diagnosis_enabled | true | bool | Master switch |
| max_hypotheses | 5 | 1–10 | Cap on hypothesis list |
| include_environment | true | bool | Capture env snapshot |
| auto_create_followups | false | bool | Create tasks automatically |
| evidence_window_minutes | 60 | 5–720 | Time range to pull logs/metrics |

---

## 6. API (Normative)

### 6.1 Endpoints Table

| Endpoint | Method | Purpose | Request Body (min) | Success (200) | Failures |
|---------|--------|---------|--------------------|---------------|----------|
| /api/diagnosis/start | POST | Start diagnosis | `{ "subject_type":"task|ticket", "subject_id":"..." }` | `{ "diagnosis_id","status":"started" }` | 404 `{ "error" }` |
| /api/diagnosis/report | GET | Get report | `?diagnosis_id=...` | `DiagnosisReport` | 404 |
| /api/diagnosis/resolve | POST | Mark resolved | `{ "diagnosis_id","root_cause":"...", "resolution_notes":"..." }` | `{ "diagnosis_id","status":"resolved" }` | 404 |

Notes:
- Error schema: `{ "error": "stable_code", "message": "..." }`.
- Authorization required; audit all actions.

---

## 7. WebSocket/Event Contracts

| Event | When Emitted | Payload (min) |
|-------|---------------|---------------|
| diagnosis_started | On start | `{ "diagnosis_id","subject_type","subject_id" }` |
| diagnosis_report_ready | On report completion | `{ "diagnosis_id","subject_id" }` |
| diagnosis_resolved | On resolution | `{ "diagnosis_id","root_cause" }` |

---

## 8. SLOs

#### REQ-DIAG-SLO-001
- Report ready P95 < 60s for standard contexts (bounded evidence window).
- Follow-up task creation P95 < 500ms after report emission (if enabled).

---

## 9. Security & Audit

#### REQ-DIAG-SEC-001
- Read-only access to code/logs/metrics; follow-ups via orchestrated task creation.
- Full audit: triggers, evidence sources, decisions, created tasks.

---

## 11. Memory Integration

#### REQ-DIAG-MEM-001: Store Diagnosis Reports as Memories
Diagnosis reports SHOULD be summarized into one or more memory entries (e.g., `error_fix`, `decision`, `learning`, or `warning`) linked to:
- the associated task/ticket,
- key files involved,
- root cause and recommendation text.

#### REQ-DIAG-MEM-002: Use Memory as Evidence Source
When building a DiagnosisReport, the Diagnosis Agent MAY query the Agent Memory System for:
- prior failures on the same component,
- similar root causes,
- historical remediations and their outcomes,
to reduce time-to-diagnose and improve recommendation quality.

---
## 10. Pydantic Reference Models

```python
from __future__ import annotations
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Hypothesis(BaseModel):
    statement: str
    likelihood: float  # 0.0 - 1.0
    supporting_evidence: List[str] = Field(default_factory=list)
    counterpoints: List[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    description: str
    priority: str  # CRITICAL|HIGH|MEDIUM|LOW
    estimated_effort: str  # e.g., "S", "M", "L"
    creates_followup_task: bool = False


class DiagnosisReport(BaseModel):
    id: str
    subject_type: str  # "task" | "ticket"
    subject_id: str
    status: str  # "open" | "resolved"
    symptoms: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    environment_snapshot: Dict[str, Any] = Field(default_factory=dict)
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    root_cause: Optional[str] = None
    recommendations: List[Recommendation] = Field(default_factory=list)
    created_at: datetime
    resolved_at: Optional[datetime] = None
```

---

## Related Documents

- [Task Queue Management Requirements](./task_queue_management.md)
- [Validation System Requirements](./validation_system.md)
- [Monitoring & Fault Tolerance Requirements](../monitoring/fault_tolerance.md)
- [Enhanced Result Submission Requirements](./result_submission.md)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Spec Agent | Initial draft |


