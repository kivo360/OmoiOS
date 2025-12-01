# Workspace Architecture & Guardian Intervention Compatibility

## Overview

This document describes how workspace modes interact with the OpenHands SDK Conversation system and Guardian interventions.

## Current Architecture

### Execution Flow

```
Worker (worker.py)
  │
  ▼
AgentExecutor (agent_executor.py)
  │
  ├── self.workspace_dir (string path - LOCAL)
  │
  ▼
Conversation (OpenHands SDK)
  ├── workspace = self.workspace_dir (string path)
  └── persistence_dir = {workspace_dir}/conversation/ (LOCAL)
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `AgentExecutor` | `services/agent_executor.py` | Wraps OpenHands Agent for task execution |
| `OpenHandsWorkspaceFactory` | `services/workspace_manager.py` | Creates workspace instances by mode |
| `ConversationInterventionService` | `services/conversation_intervention.py` | Sends Guardian messages to conversations |
| `WorkspaceSettings` | `config.py:319-343` | Configuration for workspace mode |

---

## Workspace Modes

### Configured Modes (WorkspaceSettings)

```yaml
# config.py:333-342
workspace:
  mode: "local"  # Options: local, docker, remote
  # Note: "daytona" is handled by factory but NOT documented in config
```

### Factory-Supported Modes (OpenHandsWorkspaceFactory)

The factory at `workspace_manager.py:660-722` supports **four** modes:

| Mode | Workspace Class | Description |
|------|----------------|-------------|
| `local` | `LocalWorkspace` | Direct filesystem access |
| `docker` | `DockerWorkspace` | Isolated Docker container |
| `remote` | `RemoteWorkspace` | Connect to OpenHands agent-server |
| `daytona` | `OpenHandsDaytonaWorkspace` | Daytona Cloud sandbox |

**⚠️ INCONSISTENCY #1**: Config documents 3 modes, factory implements 4.

---

## Critical Finding: Workspace Not Used in Conversation

### The Problem

`AgentExecutor.openhands_workspace` property (lines 291-314) creates workspace objects via the factory, but **these objects are NEVER PASSED to the Conversation**.

```python
# agent_executor.py:505-510 - What actually happens
conversation = Conversation(
    agent=self.agent,
    workspace=self.workspace_dir,      # ← STRING path, always local
    persistence_dir=persistence_dir,    # ← Also derived from local path
    conversation_id=conversation_id,
)
```

```python
# agent_executor.py:291-314 - What exists but is UNUSED
@property
def openhands_workspace(self):
    """Lazily create OpenHands workspace based on configuration."""
    if self._openhands_workspace is None:
        if self.project_id:
            factory = get_workspace_factory()
            self._openhands_workspace = factory.create_for_project(...)
    return self._openhands_workspace
# ^^^ This property is NEVER called by execute_task() or prepare_conversation()
```

**⚠️ INCONSISTENCY #2**: Factory creates workspace objects, but they're unused. Conversation always uses local string paths.

### Implication

Currently, regardless of `WORKSPACE_MODE` setting:
- Conversation state (`persistence_dir`) is **always local**
- Workspace execution may not actually use the configured mode

---

## Guardian Intervention Flow

### Current Implementation

```
intelligent_guardian.py:680-738
  │
  ▼
_execute_intervention_action()
  │
  ├── Get task.conversation_id
  ├── Get task.persistence_dir (LOCAL path from DB)
  │
  ▼
ConversationInterventionService.send_intervention()
  │
  ▼
conversation_intervention.py:63-75
  │
  ├── Conversation(persistence_dir=local_path, workspace=workspace_dir)
  └── conversation.send_message("[GUARDIAN INTERVENTION]: ...")
```

### What Gets Stored in Database

From `worker.py:614-624`:
```python
conversation_metadata = executor.prepare_conversation(task_id=str(task.id))
conversation_id = conversation_metadata["conversation_id"]
persistence_dir = conversation_metadata["persistence_dir"]  # LOCAL path

task_queue.update_task_status(
    task.id, "running",
    conversation_id=conversation_id,
    persistence_dir=persistence_dir,  # Stored in DB as LOCAL path
)
```

---

## Compatibility Matrix

Given current implementation where `persistence_dir` is always local:

| Workspace Mode | Conversation State | Command Execution | Guardian Works? |
|----------------|-------------------|-------------------|-----------------|
| `local` | Local disk | Local disk | ✅ Yes |
| `docker` | Local disk | Docker (if properly integrated) | ✅ Yes |
| `daytona` | Local disk | Daytona (if properly integrated) | ✅ Yes |
| `remote` (agent-server) | Local disk* | Remote server | ⚠️ Partial* |

*With `remote` mode pointing to an agent-server, the current implementation stores `persistence_dir` locally, but the agent-server manages its own conversation state. This creates a **state mismatch**.

---

## OpenHands SDK Conversation Parameters

From OpenHands SDK documentation:

```python
Conversation(
    agent: Agent,                    # Required
    workspace: str | BaseWorkspace,  # String path OR workspace object
    persistence_dir: str,            # Local directory for conversation state
    conversation_id: UUID | None,    # For resumption
)
```

The `workspace` parameter can be:
- **String path**: Interpreted as local filesystem path
- **Workspace object**: `LocalWorkspace`, `DockerWorkspace`, `RemoteWorkspace`, or custom implementation

Currently we always pass a string, never a workspace object.

---

## Required Fixes

### Fix #1: Update WorkspaceSettings Documentation

Add `daytona` to documented modes in `config.py`:
```python
# Workspace mode: "local", "docker", "remote", "daytona"
mode: str = "local"
```

### Fix #2: Use Workspace Objects in Conversation

Modify `AgentExecutor.prepare_conversation()` and `execute_task()` to pass the workspace object:

```python
# Proposed change
conversation = Conversation(
    agent=self.agent,
    workspace=self.openhands_workspace,  # ← Use workspace object
    persistence_dir=persistence_dir,
    conversation_id=conversation_id,
)
```

### Fix #3: Handle Remote/Agent-Server Mode

For `remote` mode (agent-server), Guardian interventions would need to use HTTP API instead of local filesystem:

```
POST /api/conversations/{conversation_id}/events
{
  "role": "user",
  "content": [{"type": "text", "text": "[GUARDIAN INTERVENTION]: ..."}],
  "run": true
}
```

This requires a new `AgentServerInterventionService` that uses HTTP instead of local filesystem access.

---

## Summary of Inconsistencies

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 1 | Config documents 3 modes, factory implements 4 | `config.py` vs `workspace_manager.py` | Documentation mismatch |
| 2 | `openhands_workspace` property exists but unused | `agent_executor.py:291-314` | Workspace mode not applied to Conversation |
| 3 | `remote` mode stores local persistence_dir | `agent_executor.py:495` | State mismatch with agent-server |

---

---

## Monitoring System Architecture

The monitoring system consists of **five** interconnected services:

### Monitoring Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                     MONITORING LOOP                             │
│                  (services/monitoring_loop.py)                  │
│                                                                 │
│  Orchestrates all monitoring - runs background loops for:       │
│  - Guardian analysis (every 60s)                                │
│  - Conductor analysis (every 300s)                              │
│  - Health checks (every 30s)                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    GUARDIAN     │  │   CONDUCTOR     │  │    MONITOR      │
│  (intelligent_  │  │  (conductor.py) │  │  (monitor.py)   │
│   guardian.py)  │  │                 │  │                 │
│                 │  │  System-wide    │  │  Metrics        │
│  Agent-level    │  │  coherence      │  │  collection &   │
│  trajectory     │  │  analysis       │  │  anomaly        │
│  analysis &     │  │  Duplicate      │  │  detection      │
│  steering       │  │  detection      │  │                 │
└────────┬────────┘  └─────────────────┘  └─────────────────┘
         │
         │ Sends interventions to
         ▼
┌─────────────────────────────────────────────────────────────────┐
│              CONVERSATION INTERVENTION SERVICE                   │
│               (conversation_intervention.py)                     │
│                                                                 │
│  Injects "[GUARDIAN INTERVENTION]: ..." into OpenHands convo   │
└─────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                        WATCHDOG                                  │
│                    (services/watchdog.py)                        │
│                                                                 │
│  META-MONITOR: Watches the watchers                             │
│  - Monitors monitor agents (15s heartbeat TTL)                  │
│  - Executes remediation policies (restart, failover)            │
│  - Escalates to Guardian when remediation fails                 │
└─────────────────────────────────────────────────────────────────┘
```

### Service Details

| Service | File | Interval | Purpose |
|---------|------|----------|--------|
| **MonitoringLoop** | `monitoring_loop.py` | Orchestrator | Coordinates all monitoring background tasks |
| **IntelligentGuardian** | `intelligent_guardian.py` | 60s | Agent trajectory analysis, steering interventions |
| **ConductorService** | `conductor.py` | 300s | System coherence, duplicate detection, coordination |
| **MonitorService** | `monitor.py` | On-demand | Metrics collection (tasks, agents, locks), anomaly detection |
| **WatchdogService** | `watchdog.py` | 5s | Meta-monitoring of monitors, remediation policies |

### Guardian vs Conductor

| Aspect | Guardian | Conductor |
|--------|----------|----------|
| **Scope** | Individual agents | System-wide |
| **Frequency** | Every 60 seconds | Every 5 minutes |
| **Analysis** | Trajectory alignment, focus | Coherence score, duplicates |
| **Action** | Steering interventions | Recommendations |
| **Data Source** | Agent conversation history | Guardian analyses from DB |

### Watchdog Authority Levels

From `models/guardian_action.py`:

```python
class AuthorityLevel:
    WATCHDOG = 2      # Can remediate monitors
    GUARDIAN = 4      # Can steer any agent
    CONDUCTOR = 3     # System-wide coordination
```

Watchdog escalates to Guardian when remediation fails.

### Monitoring Loop Configuration

From `config.py:345-361`:

```yaml
monitoring:
  guardian_interval_seconds: 60     # Agent analysis frequency
  conductor_interval_seconds: 300   # System coherence frequency  
  health_check_interval_seconds: 30 # Health check frequency
  auto_steering_enabled: false      # Auto-execute steering
  max_concurrent_analyses: 5        # Parallel analysis limit
```

### Intervention Execution Flow

```
Guardian.analyze_agent_trajectory(agent_id)
  │
  ├── Builds trajectory context from conversation history
  ├── Sends to LLM for analysis
  ├── Returns: alignment_score, needs_steering, steering_recommendation
  │
  ▼
Guardian.detect_steering_interventions()
  │
  ├── Finds agents where needs_steering=True
  ├── Creates SteeringIntervention objects
  │
  ▼
Guardian.execute_steering_intervention(intervention)
  │
  ├── Stores in database
  ├── Calls _execute_intervention_action()
  │       │
  │       ▼
  │   ConversationInterventionService.send_intervention()
  │       │
  │       ├── Gets task.conversation_id and task.persistence_dir from DB
  │       ├── Creates Conversation(persistence_dir=..., workspace=...)
  │       └── conversation.send_message("[GUARDIAN INTERVENTION]: ...")
  │
  └── Publishes event to EventBus
```

---

## Recommended Reading Order

### Workspace & Execution
1. `omoi_os/config.py:319-343` - WorkspaceSettings
2. `omoi_os/services/workspace_manager.py:660-828` - OpenHandsWorkspaceFactory
3. `omoi_os/services/agent_executor.py:477-594` - prepare_conversation & execute_task
4. `omoi_os/services/conversation_intervention.py` - Guardian intervention injection
5. `omoi_os/workspace/daytona.py:605-873` - OpenHandsDaytonaWorkspace adapter

### Monitoring System
6. `omoi_os/services/monitoring_loop.py` - Orchestration of all monitoring
7. `omoi_os/services/intelligent_guardian.py` - Agent trajectory analysis
8. `omoi_os/services/conductor.py` - System coherence analysis
9. `omoi_os/services/monitor.py` - Metrics and anomaly detection
10. `omoi_os/services/watchdog.py` - Meta-monitoring of monitors
