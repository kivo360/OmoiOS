# Agent System Overview

**Created**: 2025-11-21
**Purpose**: Comprehensive guide to understanding the OmoiOS agent system

---

## System Architecture

The OmoiOS agent system is a multi-agent orchestration framework that manages the lifecycle of worker agents that execute tasks in phases.

### Key Components

1. **Worker Process** (`omoi_os/worker.py`)
   - Registers agents in the database
   - Polls for assigned tasks
   - Executes tasks using `AgentExecutor`
   - Manages heartbeats and timeouts

2. **Agent Registry Service** (`omoi_os/services/agent_registry.py`)
   - Handles agent registration/deregistration
   - Manages agent capabilities and discovery
   - Enforces registration protocol (5-step process)

3. **Orchestrator Loop** (`omoi_os/api/main.py`)
   - Assigns tasks to available agents
   - Monitors agent health
   - Handles agent restarts

4. **Heartbeat System** (`omoi_os/services/heartbeat_protocol.py`)
   - Maintains bidirectional heartbeat protocol
   - Tracks missed heartbeats with escalation ladder
   - Triggers restart protocol after 3 missed heartbeats

---

## Agent Lifecycle

### Status Flow

```
SPAWNING → IDLE → RUNNING → (IDLE | DEGRADED | FAILED | QUARANTINED | TERMINATED)
```

**Status Definitions**:

- **SPAWNING**: Agent is being created/registered (initial state)
- **IDLE**: Agent is ready and waiting for tasks
- **RUNNING**: Agent is currently executing a task
- **DEGRADED**: Agent is operational but experiencing issues
- **FAILED**: Agent encountered a fatal error
- **QUARANTINED**: Agent is isolated due to security/health concerns
- **TERMINATED**: Agent is permanently stopped (terminal state)

**Active Statuses** (can receive tasks): `IDLE`, `RUNNING`
**Operational Statuses** (not failed): All except `FAILED`, `TERMINATED`, `QUARANTINED`

### Registration Protocol (REQ-ALM-001)

1. **Pre-Registration Validation**: Verify agent binary, version, configuration
2. **Identity Assignment**: Generate UUID, name, cryptographic identity
3. **Registry Entry Creation**: Create database record with `SPAWNING` status
4. **Event Bus Subscription**: Subscribe to task assignment, system broadcasts, shutdown signals
5. **Initial Heartbeat**: Wait for first heartbeat (60s timeout), then transition to `IDLE`

### Heartbeat Protocol (REQ-ALM-002)

**Frequency**:
- IDLE agents: Every 30 seconds
- RUNNING agents: Every 15 seconds
- Under high load: Every 10 seconds

**Escalation Ladder**:
- 1 missed heartbeat: Log warning
- 2 consecutive missed: Mark as `DEGRADED`, alert monitor
- 3 consecutive missed: Mark as `UNRESPONSIVE`, initiate restart protocol

---

## How Agents Work

### Starting Agents

When you run `just dev-all`:

1. **API Server Starts**: Begins orchestrator loop that assigns tasks
2. **Worker Process Starts**: 
   - Calls `register_agent()` to create agent in database
   - Agent starts in `SPAWNING` status
   - Transitions to `IDLE` status
   - Starts `HeartbeatManager` to send periodic heartbeats
   - Starts polling for assigned tasks

### Task Assignment Flow

1. **Orchestrator Loop** (runs every 10 seconds):
   - Queries for agents with `IDLE` status
   - Queries for pending tasks matching agent's phase
   - Assigns task to agent via `queue.assign_task()`
   - Publishes `TASK_ASSIGNED` event

2. **Worker Loop** (runs continuously):
   - Polls `task_queue.get_assigned_tasks(agent_id)` every 2 seconds
   - When tasks found, submits to thread pool for execution
   - Updates agent status to `RUNNING` during task execution
   - Returns to `IDLE` after completion

3. **Task Execution**:
   - Creates workspace directory for task
   - Initializes `AgentExecutor` with phase context
   - Prepares conversation (for Guardian interventions)
   - Executes task with timeout handling
   - Updates task status to `completed` or `failed`

---

## Current Issues & Debugging

### Issue: "No active agents detected"

**Problem**: Health checks show "No active agents detected" even when worker is running.

**Root Cause**: Status mismatch in `agent_output_collector.py`
- Looking for: `["working", "pending", "assigned", "idle"]` (lowercase, task-like statuses)
- Actual agent statuses: `["SPAWNING", "IDLE", "RUNNING", ...]` (uppercase enum values)

**Fix**: Update `get_active_agents()` to use correct enum values:
```python
active_statuses = [AgentStatus.IDLE.value, AgentStatus.RUNNING.value]
```

### Issue: Registration Timeout

**Problem**: New agent `c123dae6-4e45-4cfc-9566-00887eecf6ee` failed registration - no initial heartbeat within 60s.

**Possible Causes**:
1. Worker's `HeartbeatManager` not started before registration completes
2. Worker process crashes during registration
3. Network/database connectivity issues
4. Status manager not properly transitioning from `SPAWNING` to `IDLE`

**Current Worker Registration Flow**:
- Worker calls `register_agent()` (direct DB insert, not via `AgentRegistryService`)
- Sets status to `IDLE` immediately (skips registration protocol)
- Starts `HeartbeatManager` after registration

**Note**: Worker bypasses full registration protocol - this may cause issues if monitoring expects full protocol.

---

## Monitoring & Health Checks

### Health Check Components

1. **Intelligent Monitoring Loop** (`omoi_os/services/monitoring_loop.py`)
   - Runs Guardian trajectory analysis
   - Checks agent health
   - Generates alerts

2. **Heartbeat Monitoring Loop** (`omoi_os/api/main.py`)
   - Checks for missed heartbeats
   - Applies escalation ladder
   - Triggers restart protocol

3. **Health Service** (`omoi_os/services/agent_health.py`)
   - Provides health check API endpoint
   - Returns active agent count, alignment scores, alerts

### Health Check Alerts

- "No active agents detected": No agents with active status found
- "Average agent alignment is very low": Trajectory analysis shows agents off-track

---

## API Endpoints

- `GET /health`: System health check (returns agent count, alerts)
- `GET /api/agents`: List all agents
- `GET /api/agents/{agent_id}/health`: Get specific agent health
- `POST /api/agents/{agent_id}/heartbeat`: Emit heartbeat (used by worker)

---

## Configuration

### Agent Configuration

- **Concurrency**: Number of concurrent tasks (default: 2)
- **Phase ID**: Agent specialization (e.g., `PHASE_IMPLEMENTATION`)
- **Capabilities**: Tools agent can use (e.g., `["bash", "file_editor"]`)

### Heartbeat Configuration

- **IDLE_INTERVAL**: 30 seconds
- **RUNNING_INTERVAL**: 15 seconds
- **Registration Timeout**: 60 seconds
- **Missed Heartbeat Threshold**: 3 consecutive

---

## Troubleshooting

### Agent Not Receiving Tasks

1. Check agent status is `IDLE` (not `SPAWNING` or `DEGRADED`)
2. Verify orchestrator loop is running (check API logs)
3. Check for pending tasks matching agent's phase
4. Verify agent's phase matches task phase

### Agent Not Sending Heartbeats

1. Check `HeartbeatManager` is started (`Heartbeat manager started for agent...`)
2. Verify `HeartbeatProtocolService` is initialized
3. Check database connectivity
4. Look for exceptions in worker logs

### Agent Marked Unresponsive

1. Check last heartbeat timestamp in database
2. Verify worker process is still running
3. Check for thread deadlocks (heartbeat thread blocked)
4. Review restart protocol logs

---

## Best Practices

1. **Always use `AgentRegistryService` for registration** (not direct DB inserts)
2. **Wait for initial heartbeat before considering agent active**
3. **Monitor agent status transitions** (should follow valid state machine)
4. **Use status manager for state transitions** (ensures validation)
5. **Handle cleanup on shutdown** (deregister agent, stop managers)

---

## Related Documentation

- `docs/requirements/agents/agent_lifecycle.md`: Full requirements specification
- `docs/design/agents/agent_lifecycle_management.md`: Design documentation
- `backend/omoi_os/models/agent_status.py`: Status enum definitions
- `backend/CLAUDE.md`: SQLAlchemy model rules (avoid `metadata` attribute!)

