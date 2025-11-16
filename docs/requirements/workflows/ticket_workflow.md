# Ticket Workflow Requirements

## Document Overview

This document specifies the Kanban-style ticket state machine, phase orchestration across tickets, blocking detection, and parallel processing rules.

**Parent Document**: [Multi-Agent Orchestration Requirements](../multi_agent_orchestration.md)

---

## 1. Kanban State Machine

#### REQ-TKT-SM-001: States
Tickets SHALL use the following states:
`backlog → analyzing → building → building-done → testing → done` with optional `blocked` overlay.

#### REQ-TKT-SM-002: Transitions
Valid transitions:
```
backlog → analyzing
analyzing → building | blocked
building → building-done | blocked
building-done → testing | blocked
testing → done | building (on fix needed) | blocked
blocked → analyzing | building | building-done | testing
```

#### REQ-TKT-SM-003: Automatic Progression
Phase completion events SHALL advance the ticket automatically when acceptance criteria are met.

#### REQ-TKT-SM-004: Regressions
Failed validation/testing SHALL regress to the previous actionable phase with context attached.

---

## 2. Phase Orchestration

#### REQ-TKT-PH-001: Phase Gate Criteria
Each phase MUST define completion criteria and artifacts:
- analyzing → requirements doc/diffs, clarified scope
- building → merged edits, CI green build
- building-done → packaging + handoff bundle
- testing → successful unit/integration/E2E evidence

#### REQ-TKT-PH-002: Phase Task Seeding
At entry to a phase, the system SHALL seed initial tasks (see Task Queue Management) with correct capabilities and dependencies.

#### REQ-TKT-PH-003: Rollback Support
On failure, the system MUST preserve artifacts and context for deterministic re-entry to the previous phase.

---

## 3. Blocking Detection

#### REQ-TKT-BL-001: Threshold
If a ticket remains in the same non-terminal state longer than `BLOCKING_THRESHOLD` (default 30m) with no task progress, mark as `blocked`.

#### REQ-TKT-BL-002: Blocker Classification
Blockers SHALL be classified: dependency, waiting_on_clarification, failing_checks, environment; classification MUST influence remediation tasks.

#### REQ-TKT-BL-003: Alerts
Emit alerts with suggested remediation and auto-create unblocking tasks where possible.

---

## 4. Parallel Processing Rules

#### REQ-TKT-PL-001: Independence
Tickets without inter-ticket dependencies MAY run in parallel up to `MAX_CONCURRENT_TICKETS`.

#### REQ-TKT-PL-002: Resource Guardrails
Parallelism MUST respect resource budgets; guardian MAY throttle globally.

#### REQ-TKT-PL-003: Affinity/Anti-Affinity
Prefer agent affinity for continuity but apply anti-affinity to avoid hotspots when utilization > 80%.

---

## 5. SLAs & Metrics

#### REQ-TKT-OBS-001: Lead Time
Track ticket lead time (backlog → done) and phase cycle times; alert on outliers.

#### REQ-TKT-OBS-002: Blocked Time Ratio
Track ratio of time blocked vs active; surface top blocker classes weekly.

#### REQ-TKT-OBS-003: Reopen Rate
Testing→building regressions per ticket; investigate if above threshold.

---

## 6. Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| BLOCKING_THRESHOLD | 30m | Time in-state before blocked |
| MAX_CONCURRENT_TICKETS | 50 | Parallel tickets cap |
| PHASE_SEED_BATCH | 10 | Initial tasks created per phase |

---

## 7. Pydantic Reference Models

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
    BLOCKED = "blocked"  # overlay/flag, used alongside current status


class Ticket(BaseModel):
    id: str
    title: str
    description: str
    status: TicketStatusEnum
    priority: str  # CRITICAL | HIGH | MEDIUM | LOW (reuse PriorityEnum if imported)
    created_at: datetime
    updated_at: datetime
    assigned_agents: List[str] = Field(default_factory=list)
    tasks: List[str] = Field(default_factory=list)
    current_phase: str  # REQUIREMENTS | IMPLEMENTATION | VALIDATION | ANALYSIS | TESTING
    metadata: Dict[str, str] = Field(default_factory=dict)
    blocked_reason: Optional[str] = None


class PhaseGateArtifacts(BaseModel):
    ticket_id: str
    analyzing_artifacts: List[str] = Field(default_factory=list)
    building_artifacts: List[str] = Field(default_factory=list)
    packaging_bundle_uri: Optional[str] = None
    testing_evidence: List[str] = Field(default_factory=list)
    last_phase_passed_at: Optional[datetime] = None
```

---

## Related Documents

- [Task Queue Management Requirements](./task_queue_management.md)
- [Monitoring & Fault Tolerance Requirements](../monitoring/fault_tolerance.md)
- [MCP Integration Requirements](../integration/mcp_servers.md)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Spec Agent | Initial draft |


