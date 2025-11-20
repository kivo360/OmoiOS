# Ticket Human Approval Requirements

**Created**: 2025-11-20
**Status**: Draft
**Purpose**: Define the human-in-the-loop approval gate for ticket creation/activation, including lifecycle, data model, API, events, and guardrails.
**Related**: ../multi_agent_orchestration.md, ./ticket_workflow.md, ./task_queue_management.md, ./validation_system.md, ../monitoring/fault_tolerance.md

---


## Document Overview

This document defines the human-in-the-loop approval gate for ticket creation/activation. When enabled, agent-initiated ticket creation is placed in a pending review state until explicitly approved or rejected by a human. The gate prevents unnecessary workspace/branch/sandbox spin-up before approval.

**Parent Document**: [Multi-Agent Orchestration Requirements](../multi_agent_orchestration.md)

---

## 1. Goals

- Ensure high-quality, relevant tickets before allocating compute.
- Prevent unnecessary workspace/branch proliferation and sandbox expense.
- Provide clear APIs, events, and states for approval workflows.

---

## 2. Ticket Approval Lifecycle

#### REQ-THA-001: Approval Statuses
Tickets SHALL include an `approval_status` with values:
- `pending_review` | `approved` | `rejected` | `timed_out`

#### REQ-THA-002: Default Behavior
- When `ticket_human_review=false` (default), tickets skip the approval gate.
- When `ticket_human_review=true`, agent-created tickets MUST start as `pending_review`.

#### REQ-THA-003: Blocking Semantics
While `approval_status=pending_review`, the originating agent MUST block on ticket activation (no downstream tasks, no workspace/branch/sandbox provisioning).

#### REQ-THA-004: Resolution Paths
- `approved`: ticket is activated; downstream processing may begin.
- `rejected`: ticket is deleted (or archived per config) and agent receives rejection reason.
- `timed_out`: if `approval_timeout_seconds` elapses without decision, treat as rejection and notify agent.

---

## 3. Data Model Requirements

#### REQ-THA-005: Ticket Fields (Min)
- `approval_status: ApprovalStatusEnum`
- `approval_deadline_at: datetime|null`
- `requested_by_agent_id: str`
- `rejection_reason: str|null`

#### REQ-THA-006: Audit Fields
Record approval/rejection actor and timestamp in the audit log with correlation id.

---

## 4. Configuration (Normative)

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| ticket_human_review | false | bool | Enable approval gate |
| approval_timeout_seconds | 1800 | 60–86400 | Time to wait before timeout |
| on_reject | "delete" | "delete"|"archive" | Behavior for rejected tickets |

Example (board/phase):
```json
{
  "board_config": {
    "ticket_human_review": true,
    "approval_timeout_seconds": 1800
  }
}
```

---

## 5. Guardrails (Workspaces/Branches/Sandboxes)

#### REQ-THA-007
Systems that incur cost (workspace creation, branch creation, sandbox provisioning) MUST NOT execute until `approval_status=approved`.

#### REQ-THA-008
If approval is granted, provisioning MAY start immediately; otherwise MUST NOT execute.

---

## 6. API (Normative)

### 6.1 Endpoints Table

| Endpoint | Method | Purpose | Request Body (min) | Success (200) | Failures |
|---------|--------|---------|--------------------|---------------|----------|
| /api/tickets/approve | POST | Approve ticket | `{ "ticket_id": "string" }` | `{ "ticket_id":"...", "status":"approved" }` | 400 `{ "error":"..." }`, 404 `{ "error":"not_found" }` |
| /api/tickets/reject | POST | Reject ticket | `{ "ticket_id":"string", "rejection_reason":"string" }` | `{ "ticket_id":"...", "status":"rejected" }` | 400, 404 |
| /api/tickets/pending-review-count | GET | Count pending | queryless | `{ "pending_count": 3 }` | 200 only |
| /api/tickets/approval-status | GET | Get status | `?ticket_id=...` | `{ "ticket_id":"...", "approval_status":"...", "deadline_at": "ISO8601|null" }` | 404 |

Notes:
- All error responses MUST include `{ "error": "stable_code", "message": "human readable" }`.
- Authorization is required; only approved roles can change approval status.

---

## 7. WebSocket/Event Contracts

| Event | When Emitted | Payload (min) |
|-------|---------------|---------------|
| ticket_approval_pending | Ticket enters pending state | `{ "ticket_id", "deadline_at" }` |
| ticket_approved | Approved | `{ "ticket_id" }` |
| ticket_rejected | Rejected | `{ "ticket_id", "reason" }` |
| ticket_timed_out | Timed out | `{ "ticket_id" }` |

---

## 8. SLOs & Behavior

#### REQ-THA-009
- Approval decision propagation P95 < 500ms (event emission).
- Timeout processing P95 < 2s from deadline.

---

## 9. Security & Audit

#### REQ-THA-010
- Only authorized human roles MAY approve/reject.
- All actions MUST be audited: actor, ticket_id, decision, reason, timestamps.

---

## 10. Pydantic Reference Models

```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class ApprovalStatusEnum(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"


class TicketApprovalState(BaseModel):
    ticket_id: str
    approval_status: ApprovalStatusEnum
    approval_deadline_at: Optional[datetime] = None
    requested_by_agent_id: str
    rejection_reason: Optional[str] = None


class ApproveTicketRequest(BaseModel):
    ticket_id: str


class ApproveTicketResponse(BaseModel):
    ticket_id: str
    status: ApprovalStatusEnum  # "approved"


class RejectTicketRequest(BaseModel):
    ticket_id: str
    rejection_reason: str


class RejectTicketResponse(BaseModel):
    ticket_id: str
    status: ApprovalStatusEnum  # "rejected"
```

---

## Related Documents

- [Ticket Workflow Requirements](./ticket_workflow.md)
- [Task Queue Management Requirements](./task_queue_management.md)
- [Validation System Requirements](./validation_system.md)
- [Monitoring & Fault Tolerance Requirements](../monitoring/fault_tolerance.md)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Spec Agent | Initial draft |


