# Monitoring Architecture Requirements

## Document Overview

Normative requirements for the monitoring stack: loop cadence, Guardian and Conductor behaviors, data contracts, APIs, events, configuration (with generic vector search and PGVector as a preferred implementation), SLOs, and Pydantic reference models.

**Parent Document**: [Multi-Agent Orchestration Requirements](../multi_agent_orchestration.md)

---

## 1. Monitoring Loop

#### REQ-MON-LOOP-001: Cadence
THE SYSTEM SHALL execute a monitoring cycle every `interval_seconds` (default 60s).

#### REQ-MON-LOOP-002: Phases
Each cycle SHALL perform:
1) GuardianPhase: per-agent analyses (parallelizable).
2) ConductorPhase: system-wide aggregation and decisioning.
3) Persistence: store analyses and interventions.

#### REQ-MON-LOOP-003: Failure Handling
If any phase fails, the cycle MUST log, emit an alert, and proceed with partial results without blocking the next cycle.

---

## 2. Guardian (Per-Agent)

#### REQ-MON-GRD-001: Inputs
Guardian SHALL consume recent agent logs, prior summaries, status, and resource metrics.

#### REQ-MON-GRD-002: Outputs
Guardian SHALL produce structured analysis including:
- alignment_score (0–1),
- trajectory_summary,
- needs_steering (bool) and suggested steering type (if any).

#### REQ-MON-GRD-003: Grace Period
New agents shall have a grace period `guardian.min_agent_age` (default: 60s) before scoring impacts actions.

---

## 3. Conductor (System-Wide)

#### REQ-MON-CND-001: Coherence Scoring
Conductor SHALL compute a system coherence score (0–1) using recent Guardian outputs.

#### REQ-MON-CND-002: Duplicate Detection
Conductor SHALL detect duplicates by comparing agent work descriptions and touched resources; detected duplicates MUST be persisted.

#### REQ-MON-CND-003: Actions
Based on thresholds, Conductor MAY suggest or trigger task termination, work redistribution, or escalation. All actions MUST be auditable.

---

## 4. Data Persistence & Vector Search

#### REQ-MON-DATA-001: Storage
All analyses, interventions, duplicates, and coherence results MUST be persisted in the data store with ACID guarantees.

#### REQ-MON-DATA-002: Vector Search
The system SHALL support a generic vector search capability for semantic similarity. PGVector is the preferred implementation, but the requirement MUST remain provider-agnostic.

---

## 5. APIs (Normative)

### 5.1 Endpoints Table

| Endpoint | Method | Purpose | Request | Success (200) | Failures |
|---------|--------|---------|---------|---------------|----------|
| /api/agent_trajectories | GET | List agents with latest Guardian metrics | — | `[ { agent_id, alignment_score, trajectory_summary } ]` | 200 only |
| /api/system_coherence | GET | Get Conductor results | — | `{ coherence_score, duplicates, system_status }` | 200 only |
| /api/steer_agent | POST | Manual steering | `{ agent_id, steering_type, message }` | `{ delivered: true }` | 404 `{ error }` |

Notes:
- All error bodies MUST include `{ "error": "stable_code", "message": "..." }`.
- Authorization is required for steering.

---

## 6. WebSocket / Events

| Event | When Emitted | Payload (min) |
|-------|---------------|---------------|
| monitoring_update | End of cycle | `{ agents, systemCoherence, duplicates, interventions }` |
| steering_issued | Upon steering | `{ agent_id, steering_type }` |

---

## 7. Configuration (Normative)

```yaml
monitoring:
  interval_seconds: 60
  parallel_analysis: true
  max_concurrent: 10
guardian:
  min_agent_age: 60
  past_summaries_limit: 10
  context_history_lines: 200
conductor:
  min_agents_for_analysis: 2
  duplicate_threshold: 0.8
  coherence_thresholds:
    healthy: 0.7
    warning: 0.5
    critical: 0.3
vector_search:
  provider: "pgvector"   # generic interface, PGVector preferred
  index_name: "agent-summaries"
```

All keys MUST have sane defaults and be overridable per environment.

---

## 8. SLOs

#### REQ-MON-SLO-001
- Cycle time P95 < 5s (excluding model latency when batched).
- Model (LLM) latency P95 < 3s per call (target; may vary by provider).
- DB operations P95 < 500ms per write batch.

---

## 9. Security & Audit

#### REQ-MON-SEC-001
- All steering and termination decisions MUST be audited with actor, reason, and affected agents.
- APIs MUST require authenticated access with role-based authorization.

---

## 10. Pydantic Reference Models

```python
from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AgentTrajectory(BaseModel):
    agent_id: str
    alignment_score: float
    trajectory_summary: str


class DuplicatePair(BaseModel):
    agent1_id: str
    agent2_id: str
    similarity_score: float
    work_description: Optional[str] = None


class MonitoringData(BaseModel):
    agents: List[AgentTrajectory] = Field(default_factory=list)
    systemCoherence: float
    duplicates: List[DuplicatePair] = Field(default_factory=list)
    interventions: List[Dict[str, Any]] = Field(default_factory=list)
```

---

## 11. Memory Integration

#### REQ-MON-MEM-001: Persist Significant Analyses
Significant Guardian and Conductor findings (e.g., chronic misalignment, high-impact duplicates, critical interventions) SHOULD be summarized into memory entries (typically `warning`, `decision`, or `codebase_knowledge`) to:
- document systemic issues,
- capture successful remediation patterns,
- enrich future context for agents.

#### REQ-MON-MEM-002: Monitoring-Aware Context
Agents MAY read monitoring-derived memories (e.g., high-risk components, recurring failures) when selecting strategies or planning work, via the Agent Memory System search/context APIs.

---
## Related Documents

- [Fault Tolerance Requirements](./fault_tolerance.md)
- [Validation System Requirements](../workflows/validation_system.md)
- [Diagnosis Agent Requirements](../workflows/diagnosis_agent.md)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Spec Agent | Initial draft |


