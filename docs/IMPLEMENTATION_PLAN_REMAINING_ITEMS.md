# Implementation Plan: Remaining 4 Missing Items

**Date**: 2025-01-30  
**Status**: Planning  
**Priority**: High

## Overview

This document outlines the implementation plan for the final 4 missing/partial requirements to reach 100% compliance:

1. **REQ-ALERT-001**: Alerting Service (MISSING)
2. **REQ-ALM-001**: Agent Registration Enhancements (PARTIAL)
3. **REQ-TQM-ASSIGN-001**: Capability Matching (PARTIAL)
4. **REQ-TKT-PH-001**: Phase Gate Criteria Integration (PARTIAL - likely already working)

---

## 1. REQ-ALERT-001: Alerting Service

### Current Status
- ❌ AlertService not implemented
- ✅ Alert model exists: `omoi_os/models/monitor_anomaly.py::Alert`
- ❌ No rule evaluation engine
- ❌ No routing adapters
- ❌ No alert API routes

### Requirements
From `docs/requirements/monitoring/fault_tolerance.md` and design patterns:
- Rule evaluation engine with YAML rule definitions
- Routing adapters: email, Slack, webhook
- Alert acknowledgment/resolution workflow
- Alert deduplication
- Severity-based routing

### Implementation Steps

#### Step 1: Create AlertService (`omoi_os/services/alerting.py`)
```python
class AlertService:
    """Alerting service with rule evaluation and routing."""
    
    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
        rules_dir: Optional[Path] = None,
    ):
        # Load alert rules from YAML
        # Initialize routing adapters
        # Subscribe to monitoring events
    
    def evaluate_rules(self, metric_name: str, value: float, labels: dict) -> List[Alert]:
        """Evaluate alert rules against metric values."""
    
    def route_alert(self, alert: Alert) -> None:
        """Route alert to configured channels (email/Slack/webhook)."""
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> Alert:
        """Mark alert as acknowledged."""
    
    def resolve_alert(self, alert_id: str, resolved_by: str, note: str) -> Alert:
        """Mark alert as resolved."""
```

#### Step 2: Alert Rule Definitions (YAML)
Create `config/alert_rules/` directory with YAML files:
```yaml
# config/alert_rules/agent_health.yaml
rules:
  - name: agent_heartbeat_missed
    metric: agent.heartbeat.missed
    condition: "value > 2"
    severity: warning
    routing: [slack, email]
    deduplication_window: 300s
    
  - name: agent_anomaly_high
    metric: agent.anomaly_score
    condition: "value >= 0.8"
    severity: critical
    routing: [slack, webhook]
    deduplication_window: 60s
```

#### Step 3: Routing Adapters
```python
# omoi_os/services/alerting/routers.py
class EmailRouter:
    """Email routing adapter."""
    
class SlackRouter:
    """Slack webhook routing adapter."""
    
class WebhookRouter:
    """Generic webhook routing adapter."""
```

#### Step 4: API Routes (`omoi_os/api/routes/alerts.py`)
- `GET /api/v1/alerts` - List active alerts
- `GET /api/v1/alerts/{id}` - Get alert details
- `POST /api/v1/alerts/{id}/acknowledge` - Acknowledge alert
- `POST /api/v1/alerts/{id}/resolve` - Resolve alert
- `GET /api/v1/alert-rules` - List alert rules
- `POST /api/v1/alert-rules` - Create alert rule

#### Step 5: Integration Points
- Subscribe to `monitor.anomaly.detected` events
- Subscribe to `agent.heartbeat.missed` events
- Subscribe to `watchdog.remediation.started` events
- Subscribe to `ticket.blocked` events

### Estimated Effort: 12-15 hours

---

## 2. REQ-ALM-001: Agent Registration Enhancements

### Current Status
- ✅ Basic registration implemented: `omoi_os/services/agent_registry.py::register_agent()`
- ⚠️ Missing: Pre-registration validation
- ⚠️ Missing: Multi-step protocol with explicit steps
- ⚠️ Missing: Cryptographic identity generation
- ⚠️ Missing: Event bus subscription during registration
- ⚠️ Missing: Registration timeout (60s)

### Requirements
From `docs/requirements/agents/lifecycle_management.md`:
- **Step 1**: Pre-validation (binary integrity, version compatibility, config schema, resource availability)
- **Step 2**: Identity assignment (UUID v4, human-readable name, cryptographic identity)
- **Step 3**: Registry entry creation
- **Step 4**: Event bus subscription (task assignment events, system-wide broadcasts, shutdown signals)
- **Step 5**: Initial heartbeat within 60 seconds

### Implementation Steps

#### Step 1: Add Pre-Validation Module
```python
# omoi_os/services/agent_registry.py

class ValidationResult:
    success: bool
    reason: Optional[str]
    details: Dict[str, Any]

def _pre_validate(
    self,
    agent_type: str,
    capabilities: List[str],
    resource_requirements: Optional[Dict],
    config: Optional[Dict],
) -> ValidationResult:
    """Pre-registration validation per REQ-ALM-001 Step 1."""
    # 1. Binary integrity (if binary_path provided)
    # 2. Version compatibility check
    # 3. Configuration schema validation
    # 4. Resource availability check
```

#### Step 2: Enhance Registration Protocol
Refactor `register_agent()` to explicit multi-step protocol:
```python
def register_agent(...) -> Agent:
    """Multi-step registration protocol per REQ-ALM-001."""
    
    # Step 1: Pre-validation
    validation = self._pre_validate(...)
    if not validation.success:
        raise RegistrationRejectedError(...)
    
    # Step 2: Identity assignment
    agent_id = str(uuid.uuid4())
    agent_name = self._generate_agent_name(agent_type, phase_id)
    crypto_identity = self._generate_crypto_identity(agent_id)
    
    # Step 3: Registry entry creation
    agent = Agent(...)
    session.add(agent)
    session.commit()
    
    # Step 4: Event bus subscription
    if self.event_bus:
        self._subscribe_to_event_bus(agent_id, agent_type, phase_id)
    
    # Step 5: Wait for initial heartbeat (with 60s timeout)
    self._wait_for_initial_heartbeat(agent_id, timeout=60)
    
    return agent
```

#### Step 3: Add Cryptographic Identity
```python
def _generate_crypto_identity(self, agent_id: str) -> Dict[str, str]:
    """Generate cryptographic key pair for agent."""
    # Use cryptography library to generate key pair
    # Store public key in agent metadata
    # Return private key to agent (via secure channel)
```

#### Step 4: Event Bus Subscription
```python
def _subscribe_to_event_bus(
    self, agent_id: str, agent_type: str, phase_id: Optional[str]
) -> None:
    """Subscribe agent to relevant event channels."""
    # Subscribe to task assignment events for phase
    # Subscribe to system-wide broadcasts
    # Subscribe to shutdown signals
    # Confirm subscription acknowledgment
```

#### Step 5: Registration Timeout
```python
def _wait_for_initial_heartbeat(self, agent_id: str, timeout: int = 60) -> None:
    """Wait for initial heartbeat with timeout."""
    # Poll for heartbeat or use event subscription
    # If timeout exceeded, mark registration as failed
    # Clean up agent record
```

### Estimated Effort: 8-10 hours

---

## 3. REQ-TQM-ASSIGN-001: Capability Matching

### Current Status
- ✅ Phase matching works: `get_next_task()` filters by `phase_id`
- ⚠️ Capability matching not explicitly verified
- ✅ Agent model has `capabilities` field (List[str])
- ✅ Task model could have `required_capabilities` field (needs verification)

### Requirements
From `docs/requirements/workflows/task_queue_management.md`:
- Tasks SHALL only be assigned to agents whose `phase_id` matches AND whose capability declarations meet the task's required skills (language, framework, tool)

### Implementation Steps

#### Step 1: Add Required Capabilities to Task Model
Check if Task model has `required_capabilities` field. If not, add migration:
```python
# Migration: add_required_capabilities_to_tasks.py
required_capabilities: Mapped[Optional[List[str]]] = mapped_column(
    JSONB, nullable=True,
    comment="Required capabilities: ['python', 'fastapi', 'postgres']"
)
```

#### Step 2: Enhance Task Assignment Logic
```python
# omoi_os/services/task_queue.py

def get_next_task(self, phase_id: str, agent_capabilities: List[str]) -> Task | None:
    """Get highest-scored task matching phase AND capabilities."""
    
    # Existing phase filtering...
    available_tasks = []
    for task in tasks:
        if not self._check_dependencies_complete(session, task):
            continue
        
        # NEW: Check capability matching
        if not self._check_capability_match(task, agent_capabilities):
            continue  # Skip tasks that don't match capabilities
        
        task.score = self.scorer.compute_score(task)
        available_tasks.append(task)
    
    # Sort and return...

def _check_capability_match(
    self, task: Task, agent_capabilities: List[str]
) -> bool:
    """Check if agent capabilities match task requirements."""
    if not task.required_capabilities:
        return True  # No requirements = any agent can handle
    
    required = set(task.required_capabilities)
    agent_caps = set(agent_capabilities)
    
    # All required capabilities must be present
    return required.issubset(agent_caps)
```

#### Step 3: Update Orchestrator to Pass Capabilities
```python
# omoi_os/services/orchestrator_coordination.py

# When agent requests task, pass agent capabilities
task = task_queue.get_next_task(
    phase_id=agent.phase_id,
    agent_capabilities=agent.capabilities or []
)
```

#### Step 4: Log Capability Mismatches
```python
def _check_capability_match(...) -> bool:
    """Check capability match and log mismatches."""
    if not required.issubset(agent_caps):
        missing = required - agent_caps
        logger.warning(
            f"Capability mismatch for task {task.id}: "
            f"missing {missing}, agent has {agent_capabilities}"
        )
        return False
    return True
```

### Estimated Effort: 4-6 hours

---

## 4. REQ-TKT-PH-001: Phase Gate Criteria Integration

### Current Status
- ✅ PhaseGateService exists: `omoi_os/services/phase_gate.py`
- ✅ Phase gate criteria defined: `PHASE_GATE_REQUIREMENTS`
- ✅ TicketWorkflowOrchestrator uses PhaseGateService: `check_and_progress_ticket()` calls `phase_gate.check_gate_requirements()`
- ⚠️ Need to verify integration is complete and working

### Requirements
From `docs/requirements/workflows/ticket_workflow.md`:
- Each phase MUST define completion criteria and artifacts
- Phase completion events SHALL advance ticket automatically when acceptance criteria are met

### Verification Steps

#### Step 1: Verify Integration
✅ Already integrated in `TicketWorkflowOrchestrator.check_and_progress_ticket()`:
```python
# Line 216-221: omoi_os/services/ticket_workflow.py
gate_result = self.phase_gate.check_gate_requirements(
    ticket_id, ticket.phase_id
)

if not gate_result["requirements_met"]:
    return None  # Gate criteria not met, cannot progress
```

#### Step 2: Verify Phase Gate Criteria Match Requirements
Check that `PHASE_GATE_REQUIREMENTS` matches REQ-TKT-PH-001:
- ✅ `analyzing` → requirements doc/diffs, clarified scope
- ✅ `building` → merged edits, CI green build  
- ⚠️ `building-done` → packaging + handoff bundle (may need verification)
- ✅ `testing` → successful unit/integration/E2E evidence

#### Step 3: Add Missing Phase Definitions
If `building-done` phase criteria missing, add to `PHASE_GATE_REQUIREMENTS`:
```python
"PHASE_BUILDING_DONE": {
    "required_artifacts": ["packaging_bundle", "handoff_documentation"],
    "required_tasks_completed": True,
    "validation_criteria": {
        "packaging_bundle": {"must_exist": True},
    },
}
```

#### Step 4: Verify Automatic Progression Triggers
Ensure `check_and_progress_ticket()` is called:
- ✅ After task completion (verify in orchestrator)
- ✅ After phase gate validation (verify in validation orchestrator)
- ✅ In background monitoring loop (verify in main.py)

### Estimated Effort: 2-3 hours (mostly verification)

---

## Implementation Priority & Order

### Recommended Order:

1. **REQ-TQM-ASSIGN-001: Capability Matching** (4-6 hours)
   - Smallest scope, clear requirements
   - High impact on task assignment quality
   - Low risk

2. **REQ-TKT-PH-001: Phase Gate Integration** (2-3 hours)
   - Mostly verification
   - Likely already working, just needs confirmation
   - Quick win

3. **REQ-ALM-001: Agent Registration Enhancements** (8-10 hours)
   - Medium complexity
   - Foundation for security and reliability
   - Can be done incrementally

4. **REQ-ALERT-001: Alerting Service** (12-15 hours)
   - Largest scope
   - Most complex (rule engine, routing adapters)
   - Can be done last as it's not blocking core functionality

### Total Estimated Effort: 26-34 hours

---

## Testing Strategy

### For Each Item:

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test component interactions
3. **E2E Tests**: Test full workflows
4. **Regression Tests**: Ensure existing functionality still works

### Test Files to Create/Update:

- `tests/test_alerting.py` - Alert rule evaluation, routing, acknowledgment
- `tests/test_agent_registration_enhanced.py` - Pre-validation, multi-step protocol
- `tests/test_capability_matching.py` - Capability verification during assignment
- `tests/test_phase_gate_integration.py` - Phase gate integration with ticket workflow

---

## Migration Requirements

### Database Migrations Needed:

1. **Alert Rules Table** (for REQ-ALERT-001):
   ```sql
   CREATE TABLE alert_rules (
       id UUID PRIMARY KEY,
       name VARCHAR(255) NOT NULL,
       metric_name VARCHAR(255) NOT NULL,
       condition TEXT NOT NULL,
       severity VARCHAR(20) NOT NULL,
       routing JSONB NOT NULL,
       enabled BOOLEAN DEFAULT TRUE,
       created_at TIMESTAMPTZ NOT NULL
   );
   ```

2. **Agent Cryptographic Identity** (for REQ-ALM-001):
   ```sql
   ALTER TABLE agents ADD COLUMN crypto_public_key TEXT;
   ALTER TABLE agents ADD COLUMN crypto_identity_metadata JSONB;
   ```

3. **Task Required Capabilities** (for REQ-TQM-ASSIGN-001):
   ```sql
   ALTER TABLE tasks ADD COLUMN required_capabilities JSONB;
   CREATE INDEX idx_tasks_required_capabilities ON tasks USING GIN (required_capabilities);
   ```

---

## Success Criteria

### REQ-ALERT-001:
- ✅ AlertService evaluates rules from YAML configs
- ✅ Alerts routed to email/Slack/webhook based on configuration
- ✅ Alert acknowledgment and resolution workflow works
- ✅ API routes functional
- ✅ Integration with monitoring events verified

### REQ-ALM-001:
- ✅ Pre-validation rejects invalid agents
- ✅ Multi-step registration protocol executed
- ✅ Cryptographic identity generated and stored
- ✅ Event bus subscription during registration
- ✅ Registration timeout enforced (60s)

### REQ-TQM-ASSIGN-001:
- ✅ Tasks only assigned to agents with matching capabilities
- ✅ Capability mismatches logged with alternatives
- ✅ Phase matching still works (backward compatible)

### REQ-TKT-PH-001:
- ✅ Phase gate criteria verified for all phases
- ✅ Automatic progression uses phase gate validation
- ✅ Integration with ticket workflow confirmed working

---

## Next Steps

1. Review this plan with team
2. Prioritize based on business needs
3. Start with quick wins (Capability Matching, Phase Gate verification)
4. Implement incrementally with tests
5. Update REQUIREMENTS_COMPLIANCE_ANALYSIS.md as items complete

