# MCP Server Integration Requirements

## Document Overview

This document specifies requirements for integrating external tools via MCP servers, including tool registration, authorization, failure handling, and retry logic.

**Parent Document**: [Multi-Agent Orchestration Requirements](../multi_agent_orchestration.md)

---

## 1. Tool Registration

#### REQ-MCP-REG-001: Server Discovery
Upon connection, MCP servers SHALL advertise metadata (server_id, version, capabilities) and list tools with JSON schemas.

#### REQ-MCP-REG-002: Schema Validation
The orchestrator SHALL validate tool schemas; invalid tools MUST be rejected with diagnostics.

#### REQ-MCP-REG-003: Version Compatibility
Server and tool versions MUST satisfy a negotiated compatibility matrix; incompatible endpoints are disabled with warning.

---

## 2. Authorization

#### REQ-MCP-AUTH-001: Agent-Scoped Permissions
Tool invocation SHALL be authorized per-agent and per-tool action. Default-deny; explicit grants via policy.

#### REQ-MCP-AUTH-002: Capability Binding
Agents SHALL declare tool capabilities during registration; orchestrator binds those capabilities to authorization checks.

#### REQ-MCP-AUTH-003: Least Privilege
Policies MUST be least-privilege; time-bounded tokens SHOULD be used for high-risk tools.

---

## 3. Invocation & Failure Handling

#### REQ-MCP-CALL-001: Structured Request
Requests MUST include correlation id, agent id, ticket/task context, and validated params; all calls MUST be traced.

#### REQ-MCP-CALL-002: Retry with Backoff
Transient failures SHALL use exponential backoff with jitter: `base=500ms, factor=2.0, max=3 attempts`.

#### REQ-MCP-CALL-003: Idempotency
Where feasible, calls MUST be idempotent with `Idempotency-Key` to prevent duplicate side-effects.

#### REQ-MCP-CALL-004: Fallbacks
If retries exhaust, orchestrator SHOULD attempt configured fallbacks (alternate server/tool) or escalate.

#### REQ-MCP-CALL-005: Circuit Breaker
Repeated failures SHALL open a circuit per server+tool to protect the system; half-open probes after `COOLDOWN`.

---

## 4. Telemetry & Audit

#### REQ-MCP-OBS-001: Metrics
Collect call count, error rates, P50/P95 latency, retry counts, and open circuits. Export Prometheus metrics.

#### REQ-MCP-OBS-002: Audit Trail
Log all invocations with actor (agent), policy decision, parameters hash, and results (redacted).

---

## 5. Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| RETRY_MAX_ATTEMPTS | 3 | Max retries for transient errors |
| RETRY_BASE_MS | 500 | Initial backoff |
| CIRCUIT_FAILURE_THRESHOLD | 5 | Errors before opening |
| CIRCUIT_COOLDOWN | 60s | Wait before half-open |
| TOKEN_TTL | 15m | Authorization token lifetime |

---

## 6. Pydantic Reference Models

```python
from __future__ import annotations
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class MCPServerMeta(BaseModel):
    server_id: str
    version: str
    capabilities: List[str] = Field(default_factory=list)
    connected_at: datetime


class MCPTool(BaseModel):
    server_id: str
    tool_name: str
    schema: Dict[str, Any]  # JSON Schema
    version: Optional[str] = None
    enabled: bool = True


class PolicyGrant(BaseModel):
    agent_id: str
    tool_name: str
    actions: List[str] = Field(default_factory=list)
    token_ttl: timedelta = Field(default=timedelta(minutes=15))


class MCPInvocationRequest(BaseModel):
    correlation_id: str
    agent_id: str
    server_id: str
    tool_name: str
    params: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None
    ticket_id: Optional[str] = None
    task_id: Optional[str] = None
    requested_at: datetime


class MCPInvocationResult(BaseModel):
    correlation_id: str
    success: bool
    result: Any | None = None
    error: Optional[str] = None
    attempts: int = 1
    latency_ms: float = 0.0
    completed_at: datetime
```

---

## Related Documents

- [Agent Lifecycle Management Requirements](../agents/lifecycle_management.md)
- [Task Queue Management Requirements](../workflows/task_queue_management.md)
- [Monitoring & Fault Tolerance Requirements](../monitoring/fault_tolerance.md)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Spec Agent | Initial draft |


