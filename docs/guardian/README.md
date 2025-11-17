# Guardian Agent System

**Phase 5 Component** — Emergency intervention and resource reallocation system

---

## Overview

The Guardian Agent System provides emergency intervention capabilities for critical failures and resource constraints. It operates at the highest authority level (GUARDIAN = 4) and can override normal system operations to handle crisis situations.

### Key Features

- **Emergency Task Cancellation** — Immediate termination of stuck or failing tasks
- **Agent Capacity Reallocation** — Steal resources from low-priority work for critical tasks
- **Priority Queue Override** — Boost task priority ahead of normal queue order
- **Automatic Rollback** — Revert interventions after crisis resolution
- **Complete Audit Trail** — Full logging of all guardian actions for compliance

---

## Authority Hierarchy

The system enforces a strict authority hierarchy:

```
5. SYSTEM     — Highest level, automated system actions
4. GUARDIAN   — Emergency intervention authority ✓ (REQUIRED for guardian actions)
3. MONITOR    — Observability and alerting
2. WATCHDOG   — Remediation and recovery
1. WORKER     — Normal task execution
```

Only agents with **GUARDIAN** authority (level 4) or higher can perform interventions.

---

## Core Operations

### 1. Emergency Task Cancellation

Cancel a running task immediately when:
- Agent has failed during execution
- Task has exceeded timeout by 2x or more
- System resources are critically low
- Task is blocking critical work

**API Endpoint:**
```http
POST /api/v1/guardian/intervention/cancel-task
```

**Request:**
```json
{
  "task_id": "task-uuid",
  "reason": "Agent failure during critical operation",
  "initiated_by": "guardian-agent-1",
  "authority": 4
}
```

**Python Example:**
```python
from omoi_os.services.guardian import GuardianService
from omoi_os.models.guardian_action import AuthorityLevel

guardian = GuardianService(db, event_bus)

action = guardian.emergency_cancel_task(
    task_id="task-123",
    reason="Agent failure during critical operation",
    initiated_by="guardian-agent-1",
    authority=AuthorityLevel.GUARDIAN,
)
```

### 2. Agent Capacity Reallocation

Reallocate capacity from agents working on low-priority tasks to handle critical work:

**API Endpoint:**
```http
POST /api/v1/guardian/intervention/reallocate
```

**Request:**
```json
{
  "from_agent_id": "agent-low-priority",
  "to_agent_id": "agent-critical",
  "capacity": 2,
  "reason": "Critical task needs immediate attention",
  "initiated_by": "guardian-agent-1",
  "authority": 4
}
```

**Python Example:**
```python
action = guardian.reallocate_agent_capacity(
    from_agent_id="agent-low-priority",
    to_agent_id="agent-critical",
    capacity=2,
    reason="Critical task needs immediate attention",
    initiated_by="guardian-agent-1",
    authority=AuthorityLevel.GUARDIAN,
)
```

**Validation:**
- Source agent must have sufficient capacity
- Capacity must be positive integer
- Both agents must exist
- Requires GUARDIAN authority

### 3. Priority Queue Override

Boost a task's priority in the queue for immediate execution:

**API Endpoint:**
```http
POST /api/v1/guardian/intervention/override-priority
```

**Request:**
```json
{
  "task_id": "task-uuid",
  "new_priority": "CRITICAL",
  "reason": "Production incident requires immediate attention",
  "initiated_by": "guardian-agent-1",
  "authority": 4
}
```

**Python Example:**
```python
action = guardian.override_task_priority(
    task_id="task-123",
    new_priority="CRITICAL",
    reason="Production incident requires immediate attention",
    initiated_by="guardian-agent-1",
    authority=AuthorityLevel.GUARDIAN,
)
```

**Valid Priorities:**
- `CRITICAL` — Highest priority, handled immediately
- `HIGH` — High priority, ahead of medium/low
- `MEDIUM` — Normal priority
- `LOW` — Lowest priority, may be delayed

---

## Rollback and Audit

### Reverting Interventions

After crisis resolution, interventions can be reverted:

**API Endpoint:**
```http
POST /api/v1/guardian/actions/{action_id}/revert
```

**Request:**
```json
{
  "reason": "Crisis resolved, restoring normal operation",
  "initiated_by": "guardian-agent-1"
}
```

**Python Example:**
```python
success = guardian.revert_intervention(
    action_id="action-123",
    reason="Crisis resolved, restoring normal operation",
    initiated_by="guardian-agent-1",
)
```

**Note:** Reversion marks the action as reverted but does **not** automatically restore previous state. Restoration requires separate actions (e.g., restarting cancelled tasks, reallocating capacity back).

### Audit Trail

All guardian actions are logged with complete audit information:

```python
# Get recent guardian actions
actions = guardian.get_actions(limit=50)

# Get actions for specific task
task_actions = guardian.get_actions(target_entity="task-123")

# Get specific action details
action = guardian.get_action("action-123")
```

**Audit Record Includes:**
- Action type and target entity
- Authority level used
- Reason for intervention
- Who initiated and approved (if applicable)
- Execution and reversion timestamps
- Complete before/after state in `audit_log` JSONB field

**API Endpoint:**
```http
GET /api/v1/guardian/actions?limit=100&action_type=cancel_task
```

---

## Guardian Policies

The system uses YAML-based policies to define intervention rules. Policies are stored in:

```
omoi_os/config/guardian_policies/
├── emergency.yaml                # Emergency cancellation rules
├── resource_reallocation.yaml    # Capacity reallocation rules
└── priority_override.yaml        # Priority escalation rules
```

### Policy Structure

Each policy defines:
- **Triggers** — Conditions that activate the policy
- **Actions** — Steps to take when triggered
- **Rollback** — How to revert after crisis resolution
- **Authority** — Minimum authority level required

**Example (Emergency Policy):**
```yaml
policy:
  name: "emergency_cancellation"
  min_authority: 4  # GUARDIAN
  
  triggers:
    - type: "task_timeout"
      condition: "task.running_duration > task.timeout_seconds * 2"
      
    - type: "agent_failure"
      condition: "agent.health_status == 'failed' AND task.status == 'running'"
  
  actions:
    - type: "cancel_task"
      auto_approve: true
      
    - type: "notify"
      channels: ["slack", "pagerduty"]
  
  rollback:
    enabled: true
    auto_rollback_after_minutes: 60
```

---

## Events

Guardian actions publish events for monitoring and automation:

### Event Types

| Event | Description | Payload |
|-------|-------------|---------|
| `guardian.intervention.started` | Intervention initiated | `{action_type, task_id, reason, authority}` |
| `guardian.intervention.completed` | Intervention executed successfully | `{action_type, target_entity, result}` |
| `guardian.intervention.reverted` | Intervention rolled back | `{action_id, reason, reverted_by}` |
| `guardian.resource.reallocated` | Capacity moved between agents | `{from_agent_id, to_agent_id, capacity}` |

**Subscribing to Events:**
```python
from omoi_os.services.event_bus import EventBusService

event_bus = EventBusService(redis_url="redis://localhost:16379")

def handle_guardian_event(event):
    print(f"Guardian action: {event['event_type']}")
    print(f"Reason: {event['payload']['reason']}")

event_bus.subscribe("guardian.*", handle_guardian_event)
```

---

## Integration Points

### Phase 4 Watchdog Integration

If Phase 4 Monitoring is complete, Guardian receives escalations from Watchdog:

```python
# Watchdog escalates to Guardian when remediation fails
if remediation_failed:
    watchdog.escalate_to_guardian(
        alert_id=alert.id,
        reason="Automated remediation failed 3 times",
    )
```

Guardian can then take stronger action (capacity reallocation, task cancellation).

### Task Queue Integration

Guardian uses `TaskQueueService` for:
- Cancelling running tasks
- Overriding task priorities
- Checking task status and dependencies

```python
from omoi_os.services.task_queue import TaskQueueService

queue = TaskQueueService(db)
task = queue.get_task(task_id)

if task.status == "running" and task_stuck:
    guardian.emergency_cancel_task(
        task_id=task.id,
        reason="Task stuck for 2x timeout duration",
        initiated_by=guardian_agent_id,
    )
```

### Agent Registry Integration

Guardian uses `AgentRegistryService` for:
- Finding available agents
- Checking agent capacity
- Reallocating resources

```python
from omoi_os.services.agent_registry import AgentRegistryService

registry = AgentRegistryService(db, event_bus)

# Find agents with low-priority work
low_priority_agents = registry.find_agents_by_criteria(
    current_task_priority="LOW",
    capacity__gt=1,
)

# Reallocate capacity to critical work
for agent in low_priority_agents:
    guardian.reallocate_agent_capacity(
        from_agent_id=agent.id,
        to_agent_id=critical_agent_id,
        capacity=1,
        reason="Critical task requires immediate attention",
        initiated_by=guardian_agent_id,
    )
```

---

## Database Schema

### `guardian_actions` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | String (PK) | UUID |
| `action_type` | String | cancel_task, reallocate_capacity, override_priority |
| `target_entity` | String | Task ID, agent ID, or other entity |
| `authority_level` | Integer | AuthorityLevel enum value (1-5) |
| `reason` | Text | Explanation for intervention |
| `initiated_by` | String | Agent/user ID who initiated |
| `approved_by` | String (nullable) | If approval required |
| `executed_at` | Timestamp | When intervention executed |
| `reverted_at` | Timestamp (nullable) | When rolled back |
| `audit_log` | JSONB | Before/after state, parameters, results |
| `created_at` | Timestamp | Record creation time |

**Indexes:**
- `ix_guardian_actions_action_type` — Filter by action type
- `ix_guardian_actions_target_entity` — Find actions for specific entity
- `ix_guardian_actions_initiated_by` — Audit trail by initiator
- `ix_guardian_actions_entity_type` — Composite index for efficient queries

---

## Testing

### Run Guardian Tests

```bash
# Run all guardian tests
uv run pytest tests/test_guardian.py tests/test_guardian_policies.py -v

# Run specific test
uv run pytest tests/test_guardian.py::test_emergency_cancel_task_success -v

# Run with coverage
uv run pytest tests/test_guardian.py --cov=omoi_os.services.guardian --cov-report=html
```

### Test Coverage

- **15 tests** in `test_guardian.py` — Core functionality
- **8 tests** in `test_guardian_policies.py` — Policy validation
- **23 total tests** — 100% coverage target

**Test Categories:**
- Emergency task cancellation (4 tests)
- Agent capacity reallocation (4 tests)
- Priority override (3 tests)
- Rollback and audit (4 tests)
- Policy loading and evaluation (8 tests)

---

## Security Considerations

### Authority Validation

All guardian operations **strictly enforce** authority checks:

```python
if authority < AuthorityLevel.GUARDIAN:
    raise PermissionError(
        f"Emergency cancellation requires GUARDIAN authority (level 4), "
        f"but got {authority.name} (level {authority})"
    )
```

### Audit Logging

Every intervention is logged with:
- **Who** initiated the action
- **When** it was executed and reverted
- **Why** (reason field required)
- **What** changed (before/after state in audit_log)

This ensures full accountability and compliance.

### Event Publishing

All guardian actions publish events for:
- Real-time monitoring and alerting
- Security audit trails
- Automated response workflows

---

## Troubleshooting

### Common Issues

**1. PermissionError: Insufficient authority**
- **Cause:** Attempting intervention with authority < GUARDIAN (4)
- **Solution:** Ensure guardian agent is registered with correct authority level

**2. ValueError: Agent has insufficient capacity**
- **Cause:** Trying to reallocate more capacity than agent has
- **Solution:** Check agent capacity before reallocation, or reduce amount

**3. ValueError: Invalid priority**
- **Cause:** Priority override with invalid value
- **Solution:** Use one of: CRITICAL, HIGH, MEDIUM, LOW

**4. Action not found (404)**
- **Cause:** Task/agent doesn't exist or action_id invalid
- **Solution:** Verify entity exists before intervention

### Debug Mode

Enable debug logging for guardian operations:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("omoi_os.services.guardian")
logger.setLevel(logging.DEBUG)
```

---

## Best Practices

### When to Use Guardian

✅ **Use Guardian for:**
- Production incidents (P0/P1)
- Agent failures during critical tasks
- System resource exhaustion
- Tasks stuck beyond 2x timeout
- Critical work blocked by low-priority tasks

❌ **Don't use Guardian for:**
- Normal task failures (use retry logic)
- Non-critical priority changes
- Routine capacity adjustments
- Minor delays or slowness

### Rollback Strategy

1. **Monitor** — Track when crisis is resolved
2. **Revert** — Mark intervention as reverted
3. **Restore** — Manually restore previous state if needed
4. **Document** — Update audit trail with resolution notes

### Policy Guidelines

When creating custom policies:
- Set `min_authority: 4` for guardian actions
- Define clear, measurable triggers
- Enable rollback with reasonable timeouts
- Include notification channels
- Document expected vs. actual behavior

---

## Migration

The guardian system requires migration **006_guardian**:

```bash
# Run migration
uv run alembic upgrade head

# Verify migration
uv run alembic history
```

**Migration creates:**
- `guardian_actions` table
- Indexes for efficient audit queries
- Constraints for data integrity

---

## API Reference

See OpenAPI documentation at `/docs` when API server is running:

```bash
uv run uvicorn omoi_os.api.main:app --reload
# Visit http://localhost:8000/docs
```

**Guardian Endpoints:**
- `POST /api/v1/guardian/intervention/cancel-task`
- `POST /api/v1/guardian/intervention/reallocate`
- `POST /api/v1/guardian/intervention/override-priority`
- `GET /api/v1/guardian/actions`
- `GET /api/v1/guardian/actions/{action_id}`
- `POST /api/v1/guardian/actions/{action_id}/revert`

---

## Contributing

When adding new guardian features:
1. Add method to `GuardianService`
2. Create corresponding API route
3. Write comprehensive tests (aim for 100% coverage)
4. Update this documentation
5. Create policy YAML if applicable
6. Publish appropriate events

---

## Version History

- **v1.0** (Phase 5) — Initial release
  - Emergency task cancellation
  - Agent capacity reallocation
  - Priority queue override
  - Complete audit trail
  - Policy-based intervention rules

