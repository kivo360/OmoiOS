# Monitoring & Fault Tolerance Requirements

**Created**: 2025-11-20
**Status**: Draft
**Purpose**: Define heartbeat detection, automatic restart, anomaly detection, escalation, and quarantine protocols for resilient multi‑agent operations.
**Related**: ../multi_agent_orchestration.md, ../agents/lifecycle_management.md, ../workflows/task_queue_management.md, ../integration/mcp_servers.md

---


## Document Overview

This document details heartbeat detection, automatic restart, anomaly detection, escalation, and quarantine protocols for resilient multi-agent operations.

**Parent Document**: [Multi-Agent Orchestration Requirements](../multi_agent_orchestration.md)

---

## 1. Heartbeat Detection

#### REQ-FT-HB-001: Bidirectional Heartbeats
Monitors SHALL process agent heartbeats and send acknowledgments; missing acknowledgments MUST trigger retries and be observable.

#### REQ-FT-HB-002: TTL Thresholds
Default thresholds:
- IDLE TTL: 30s
- RUNNING TTL: 15s
- MONITOR TTL (watchdog layer): 15s (heartbeat every 5s)

#### REQ-FT-HB-003: Gap Detection
Sequence numbers SHALL detect lost heartbeats; 3 consecutive misses → UNRESPONSIVE.

#### REQ-FT-HB-004: Distributed Clock Tolerance
All checks SHALL tolerate clock skew up to 2s; timestamps must be compared using monotonic time where available.

---

## 2. Automatic Restart Protocol

#### REQ-FT-AR-001: Escalation Ladder
1 missed → warn; 2 missed → DEGRADED; 3 missed → UNRESPONSIVE and initiate restart.

#### REQ-FT-AR-002: Restart Steps
1) Graceful stop (10s)  
2) Force terminate  
3) Spawn replacement with same config  
4) Reassign incomplete tasks  
5) Emit AGENT_RESTARTED event with cause chain

#### REQ-FT-AR-003: Cooldown
After restart, apply `RESTART_COOLDOWN` (default 60s) before considering further restarts for the same lineage.

#### REQ-FT-AR-004: Max Attempts
`MAX_RESTART_ATTEMPTS` per `ESCALATION_WINDOW` (default 3 per hour); exceed → escalate to guardian.

---

## 3. Anomaly Detection

#### REQ-FT-AN-001: Composite Anomaly Score
`anomaly_score ∈ [0,1]` computed from:
- Latency deviation (z-score)
- Error rate trend (EMA)
- Resource skew (CPU/Memory vs baseline)
- Queue impact (blocked dependents)

Thresholds configurable (default 0.8).

#### REQ-FT-AN-002: Baseline Learning
Baselines SHALL be learned per agent type and phase; decayed after resurrection.

#### REQ-FT-AN-003: False Positive Guard
Require consecutive `K` anomalous readings (default 3) OR peer-confirmation (watchdog) before quarantine.

---

## 4. Escalation Procedures

#### REQ-FT-ES-001: Severity Mapping
- SEV-1: Multiple CRITICAL tasks blocked or guardian unavailable
- SEV-2: Repeated restarts > threshold
- SEV-3: Single agent chronic anomalies

#### REQ-FT-ES-002: Notification Matrix
Publish to: Guardian, On-call channel, Incident feed; include trace IDs, last N events, config snapshot, and remediation hints.

#### REQ-FT-ES-003: Human-in-the-Loop
For SEV-1, require human acknowledgment within `ACK_SLA` (default 5m); auto-mitigations proceed regardless to contain blast radius.

---

## 5. Quarantine Protocol

#### REQ-FT-QN-001: Isolation
Quarantined agents SHALL receive no new tasks; current task is checkpointed or aborted safely.

#### REQ-FT-QN-002: Forensics
Preserve memory, logs, metrics, and recent event stream; generate immutable case bundle.

#### REQ-FT-QN-003: Clearance
Guardian MAY clear quarantine with evidence; system MUST re-validate upon re-entry (smoke test + short TTL).

---

## 6. Observability & SLOs

#### REQ-FT-OB-001: Time-to-Detect (TTD)
P95 TTD for missed heartbeats < 20s (worker), < 10s (monitor by watchdog).

#### REQ-FT-OB-002: MTTR
Mean time to recover from single agent failure < 60s.

#### REQ-FT-OB-003: Auditability
All escalations, quarantines, and restarts MUST be audited with actor and reason.

---

## 7. Configuration Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| RESTART_COOLDOWN | 60s | Per lineage |
| MAX_RESTART_ATTEMPTS | 3 | Per hour |
| ESCALATION_WINDOW | 1h | Rolling window |
| ANOMALY_THRESHOLD | 0.8 | Composite score |
| ANOMALY_CONSECUTIVE | 3 | Readings before action |
| ACK_SLA | 5m | For SEV-1 |

---

## 8. Diagnosis Integration

#### REQ-FT-DIAG-001: Auto-Spawn on Anomaly
If `anomaly_score >= ANOMALY_THRESHOLD` for `ANOMALY_CONSECUTIVE` readings AND `DIAG_ON_ANOMALY=true`, THE SYSTEM SHALL start a Diagnosis Agent for the affected agent to collect evidence and recommendations.

#### REQ-FT-DIAG-002: Auto-Spawn on Restart Escalation
If restart attempts exceed `MAX_RESTART_ATTEMPTS` within `ESCALATION_WINDOW` AND `DIAG_ON_RESTART_ESCALATION=true`, THE SYSTEM SHALL start a Diagnosis Agent focusing on systemic failure causes.

### 8.1 Configuration

| Parameter | Default | Notes |
|-----------|---------|-------|
| DIAG_ON_ANOMALY | true | Enable diagnosis when anomalies persist |
| DIAG_ON_RESTART_ESCALATION | true | Enable diagnosis after restart escalation |

---

## 8. Pydantic Reference Models

```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    UNRESPONSIVE = "UNRESPONSIVE"
    QUARANTINED = "QUARANTINED"
    TERMINATED = "TERMINATED"


class SeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class HeartbeatMessage(BaseModel):
    agent_id: str
    timestamp: datetime
    sequence_number: int
    status: AgentStatus
    current_task_id: Optional[str] = None
    health_metrics: Dict[str, Any] = Field(default_factory=dict)
    checksum: str


class RestartEvent(BaseModel):
    agent_id: str
    reason: str
    graceful_attempt_ms: int = 10000
    forced: bool = False
    spawned_agent_id: Optional[str] = None
    reassigned_tasks: List[str] = Field(default_factory=list)
    occurred_at: datetime


class AnomalyReading(BaseModel):
    agent_id: str
    timestamp: datetime
    latency_z: float = 0.0
    error_rate_ema: float = 0.0
    resource_skew: float = 0.0
    queue_impact: float = 0.0

    @property
    def composite_score(self) -> float:
        # Example non-binding reference implementation
        return min(
            1.0,
            0.35 * abs(self.latency_z)
            + 0.30 * self.error_rate_ema
            + 0.20 * self.resource_skew
            + 0.15 * self.queue_impact,
        )


class EscalationNotice(BaseModel):
    severity: SeverityEnum
    agent_ids: List[str] = Field(default_factory=list)
    summary: str
    trace_ids: List[str] = Field(default_factory=list)
    recent_events: List[Dict[str, Any]] = Field(default_factory=list)
    config_snapshot: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class QuarantineRecord(BaseModel):
    agent_id: str
    initiated_at: datetime
    reason: str
    evidence_bundle_uri: str
    cleared_at: Optional[datetime] = None
    cleared_by: Optional[str] = None
```

---

## Related Documents

- [Agent Lifecycle Management Requirements](../agents/lifecycle_management.md)
- [Task Queue Management Requirements](../workflows/task_queue_management.md)
- [MCP Integration Requirements](../integration/mcp_servers.md)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Spec Agent | Initial draft |


