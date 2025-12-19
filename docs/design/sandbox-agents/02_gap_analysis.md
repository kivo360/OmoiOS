# Sandbox System Gap Analysis

**Created**: 2025-12-12
**Updated**: 2025-12-18 (major revision - most gaps have been implemented!)
**Validated**: 2025-12-18 ✅ (systematically verified against actual codebase)
**Status**: ~~Planning Document~~ → **MOSTLY IMPLEMENTED**
**Purpose**: Comprehensive analysis of existing infrastructure vs. requirements for real-time sandbox agent communication

---

## 🎉 Implementation Status Update (2025-12-18)

**Most gaps identified in this document have been implemented!** This section summarizes the current state:

### ✅ Fully Implemented (No Work Needed)
| Gap | Original Status | Implementation Location |
|-----|----------------|------------------------|
| `sandbox_id` in Task model | 🔴 Missing | `backend/omoi_os/models/task.py:63` |
| GitHub Token handling | 🔴 Missing | `daytona_spawner.py:546,599-606` (uses Daytona SDK's `git.clone()`) |
| Sandbox event callback endpoint | ❌ Missing | `sandbox.py:365` - `POST /{sandbox_id}/events` |
| Message injection endpoints | ❌ Missing | `sandbox.py:758,803` - `POST/GET /{sandbox_id}/messages` |
| Database event persistence | ❌ Optional | `sandbox.py:212-269` - persists to `sandbox_events` table |
| Guardian sandbox intervention | 🔴 Missing | `intelligent_guardian.py:693-887` - `_is_sandbox_task()` + `_sandbox_intervention()` |
| GitHub API methods | 🟡 Missing | `github_api.py:804,852,923,956` - `get_pull_request`, `merge_pull_request`, `delete_branch`, `compare_branches` |
| Branch workflow service | ❌ Missing | `branch_workflow.py` + `api/routes/branch_workflow.py` |
| Worker script updates | ❌ Missing | Embedded in `daytona_spawner.py` - workers POST to sandbox endpoints |
| Session transcript saving | ❌ Not planned | `sandbox.py:272-332` - cross-sandbox resumption support |

### ❌ Still Outstanding
| Gap | Status | Notes |
|-----|--------|-------|
| RestartOrchestrator sandbox handling | 🔴 Not started | `restart_orchestrator.py` has no sandbox/daytona awareness |
| Heartbeat-based sandbox health | 🟡 Partial | Workers can POST heartbeat events, but RestartOrchestrator doesn't consume them |
| Idle sandbox detection | ✅ Implemented | `idle_sandbox_monitor.py` + `orchestrator_worker.py:411-492` |

### Effort Remaining
- **RestartOrchestrator integration**: ~4-6 hours
- **Full fault tolerance for sandboxes**: ~8-12 hours
- ~~**Idle sandbox detection**: ~2-4 hours~~ ✅ **DONE**

---

## Idle Sandbox Detection Design (2025-12-18) ✅ IMPLEMENTED

### Problem Statement

Current monitoring can detect **dead sandboxes** (missed heartbeats via RestartOrchestrator), but cannot detect **idle sandboxes** that:
- ✅ Send heartbeats (appear alive)
- ❌ Show no actual work progress
- ❌ Have no user input for extended periods

These idle sandboxes waste Daytona resources and should be terminated.

### Work Events vs Non-Work Events

The worker script (`claude_sandbox_worker.py`) reports various event types. Only some indicate actual progress:

**Work Events** (indicate progress - last activity timestamp should update):
- `agent.file_edited` - Modified files
- `agent.tool_completed` - Completed a tool call
- `agent.subagent_completed` - Subagent finished work
- `agent.skill_completed` - Skill execution done
- `agent.completed` - Task completed
- `agent.assistant_message` - Generated output
- `agent.tool_use` - Tool invocation
- `agent.tool_result` - Tool execution result

**Non-Work Events** (don't indicate progress):
- `agent.heartbeat` - Just alive signal
- `agent.started` - Initial startup
- `agent.thinking` - Processing without output
- `agent.error` - Failure state (but track these separately)

### Architecture Decision: New Service, Not RestartOrchestrator

**RestartOrchestrator** handles **dead agent detection** (no heartbeats). Idle detection is fundamentally different:
- Different detection logic (event analysis vs heartbeat timeout)
- Different termination approach (Daytona SDK vs local process kill)
- Different recovery patterns (no replacement needed for idle sandboxes)

**Solution**: Create `IdleSandboxMonitor` service integrated into `orchestrator_worker.py`.

### Implementation Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     IDLE SANDBOX MONITORING FLOW                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  orchestrator_worker.py                                                     │
│  ├─ orchestrator_loop() - existing task spawn loop                         │
│  ├─ heartbeat_task() - existing heartbeat logging                          │
│  └─ idle_sandbox_check_loop() - NEW                                        │
│         │                                                                   │
│         ├─ Every 60 seconds:                                               │
│         │   └─ Query sandbox_events for all active sandboxes               │
│         │                                                                   │
│         ├─ For each sandbox:                                               │
│         │   ├─ Last heartbeat < 90s ago? → Alive                           │
│         │   ├─ Last work event < IDLE_THRESHOLD ago? → Active              │
│         │   ├─ Last user message < IDLE_THRESHOLD ago? → Has input         │
│         │   └─ Otherwise → IDLE                                            │
│         │                                                                   │
│         └─ For IDLE sandboxes:                                             │
│             ├─ Terminate via DaytonaSpawnerService.stop_sandbox()          │
│             ├─ Update task.status = "failed" with reason                   │
│             └─ Emit SANDBOX_TERMINATED_IDLE event                          │
│                                                                             │
│  Configuration (via YAML or env):                                          │
│  ├─ IDLE_THRESHOLD_MINUTES: 30 (default)                                   │
│  ├─ IDLE_CHECK_INTERVAL_SECONDS: 60 (default)                              │
│  └─ IDLE_DETECTION_ENABLED: true (default)                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Database Queries

```python
# Get last work event for a sandbox
last_work = session.query(SandboxEvent).filter(
    SandboxEvent.sandbox_id == sandbox_id,
    SandboxEvent.event_type.in_(WORK_EVENT_TYPES)
).order_by(SandboxEvent.created_at.desc()).first()

# Get last heartbeat
last_heartbeat = session.query(SandboxEvent).filter(
    SandboxEvent.sandbox_id == sandbox_id,
    SandboxEvent.event_type == "agent.heartbeat"
).order_by(SandboxEvent.created_at.desc()).first()

# Get active sandboxes (have recent heartbeats)
cutoff = utc_now() - timedelta(seconds=90)
active_sandboxes = session.query(SandboxEvent.sandbox_id).filter(
    SandboxEvent.event_type == "agent.heartbeat",
    SandboxEvent.created_at >= cutoff
).distinct().all()
```

### Termination Flow

1. **Stop sandbox** via Daytona SDK
2. **Update task** status to "failed" with error_message explaining idle termination
3. **Emit event** `SANDBOX_TERMINATED_IDLE` for monitoring/alerting
4. **Log** for debugging (sandbox_id, last_work_at, idle_duration)

### Files Created/Modified ✅

| File | Action | Description |
|------|--------|-------------|
| `backend/omoi_os/services/idle_sandbox_monitor.py` | ✅ CREATED | Core idle detection service |
| `backend/omoi_os/workers/orchestrator_worker.py` | ✅ MODIFIED | Added `idle_sandbox_check_loop()` (lines 411-492) |

### Integration with Existing Systems

- **Uses existing**: `SandboxEvent` model, `DaytonaSpawnerService`, `EventBusService`
- **Runs in**: `orchestrator_worker.py` alongside existing loops
- **Configurable**: Via environment variables:
  - `IDLE_DETECTION_ENABLED`: Enable/disable (default: true)
  - `IDLE_THRESHOLD_MINUTES`: Time without work before considered idle (default: 30)
  - `IDLE_CHECK_INTERVAL_SECONDS`: How often to check (default: 60)

---

---

## 🔍 Validation Status

> **This document has been validated against the actual codebase on 2025-12-12.**

### Validation Summary

| Category | Documented | Verified | Status |
|----------|------------|----------|--------|
| WebSocket endpoint exists | `/api/v1/ws/events` | `backend/omoi_os/api/routes/events.py` | ✅ Confirmed |
| WebSocketEventManager | Redis pub/sub bridge | Lines 23-161 in `events.py` | ✅ Confirmed |
| Frontend useEvents hook | Filters, reconnection | `frontend/hooks/useEvents.ts` (242 lines) | ✅ Confirmed |
| WebSocketProvider | Auto-connect, query invalidation | `frontend/providers/WebSocketProvider.tsx` | ✅ Confirmed |
| EventBusService | Redis pub/sub | `backend/omoi_os/services/event_bus.py` (83 lines) | ✅ Confirmed |
| DaytonaSpawnerService | Claude Agent SDK workers | `backend/omoi_os/services/daytona_spawner.py` (821 lines) | ✅ Confirmed |
| TaskQueueService | DAG-aware, events | `backend/omoi_os/services/task_queue.py` (~860 lines) | ✅ Confirmed |
| GitHubAPIService | Full API wrapper | `backend/omoi_os/services/github_api.py` (~765 lines) | ✅ Confirmed |

### ⚠️ Risks Identified During Validation

1. **In-Memory Sandbox Tracking** (Medium Risk)
   - Location: `daytona_spawner.py` lines 99-101
   - Issue: `_sandboxes` and `_task_to_sandbox` are in-memory dicts
   - Impact: Server restart = lose all active sandbox state
   - Mitigation: Phase 4 (optional) adds database persistence

2. **Embedded Worker Scripts** (Low Risk)
   - Location: `daytona_spawner.py` lines 344-662
   - Issue: 100+ line scripts embedded as string returns
   - Impact: Hard to test, hard to maintain
   - Recommendation: Consider extracting to files that get uploaded

8. **✅ SDK API Correctness** (RESOLVED 2025-12-12)
   - Location: `daytona_spawner.py` - `_get_worker_script()` and `_get_claude_worker_script()`
   - Issues Fixed:
     - **Claude Agent SDK**: Worker implementation verified against SDK documentation
     - **Claude SDK**: Model name was malformed (`claude-sonnet-4-5` → `claude-sonnet-4-20250514`)
   - SDK References:
     - Claude: `docs/libraries/claude-agent-sdk-python-clean.md`
     - Claude Agent SDK: `docs/libraries/claude-agent-sdk-python-clean.md`
   - Status: **Fixed** - Worker scripts now match official SDK documentation

9. **⚠️ Polling-Based Intervention Latency** (Medium Risk - Performance)
   - Location: Worker scripts in `daytona_spawner.py`
   - Issue: Current design uses polling for message injection (worker polls after each turn)
   - Impact: Interventions may be delayed by seconds to minutes (full agent turn cycle)
   - Solution: **Hook-based injection** - check for pending messages BEFORE each tool call
   - SDK Support:
     - **Claude SDK**: Native `PreToolUse` hooks ✅
     - **Claude Agent SDK**: PreToolUse hooks for intervention injection ✅
   - Benefits:
     - Sub-second intervention injection (< 100ms vs seconds)
     - Guardian steering is immediate
     - User nudges take effect on next tool call
   - Implementation: Phase 2 enhancement (hook registration in worker scripts)
   - References:
     - Claude hooks: `docs/libraries/claude-agent-sdk-python-clean.md` (Lifecycle Hooks section)
     - Claude hooks: `docs/libraries/claude-agent-sdk-python-clean.md` (Lifecycle Hooks section)

3. **Event Endpoint Overlap** (Low Risk)
   - Current: `/tasks/{id}/events` and `/agent-events` endpoints exist
   - Planned: `/sandboxes/{id}/events` endpoint
   - Recommendation: Consolidate to sandbox-centric model per this design

4. **~~🔴 Missing `sandbox_id` Field in Task Model~~** ✅ **RESOLVED**
   - Location: `backend/omoi_os/models/task.py` line 63
   - **Status**: Field exists! `sandbox_id: Mapped[Optional[str]] = mapped_column(...)`
   - Also present in: `sandbox_event.py:41`, `claude_session_transcript.py:61`
   - ~~Impact: Sandbox-task association is broken; Guardian can't identify sandbox tasks~~
   - **No action needed** - this was implemented

5. **~~🔴 Guardian Cannot Intervene with Sandbox Agents~~** ✅ **RESOLVED**
   - Location: `backend/omoi_os/services/intelligent_guardian.py` lines 693-887
   - **Status**: IMPLEMENTED with sandbox-aware routing!
   - Implementation:
     - `_is_sandbox_task(task)` - detects sandbox mode via `task.sandbox_id`
     - `_sandbox_intervention(intervention, task)` - POSTs to `/api/v1/sandboxes/{id}/messages`
   - The "REQUIRED FLOW" diagram below is now the ACTUAL implementation:

   ```
   IMPLEMENTED FLOW (Sandbox-aware) ✅:
   ┌─────────────────────────────────────────────────────────────────┐
   │  Guardian.execute_steering_intervention()                       │
   │       │                                                         │
   │       ├─► IF self._is_sandbox_task(task):  # Line 825          │
   │       │       await self._sandbox_intervention(...)  # Line 827 │
   │       │       → POST /api/v1/sandboxes/{id}/messages            │
   │       │                                                         │
   │       └─► ELSE:                                                 │
   │               ConversationInterventionService (legacy path)     │
   └─────────────────────────────────────────────────────────────────┘
   ```

6. **Dual Monitoring Paths Complexity** (Medium Risk - Architecture Complexity)
   - Issue: System now has TWO agent execution modes with different intervention mechanisms
   - Legacy Path: Direct filesystem access via `persistence_dir`
   - Sandbox Path: HTTP API via message injection endpoints
   - Impact: Guardian and monitoring code must detect mode and route correctly
   - Recommendation: Clear mode detection via `task.sandbox_id` presence

7. **~~🔴 GitHub Token Not Passed to Sandbox~~** ✅ **RESOLVED**
   - Location: `backend/omoi_os/services/daytona_spawner.py` lines 543-634
   - **Status**: IMPLEMENTED using Daytona SDK's native git.clone()!
   - Implementation:
     - Line 546: `github_token = env_vars.pop("GITHUB_TOKEN", None)`
     - Lines 599-606: Uses Daytona SDK's `sandbox.git.clone()` with token:
       ```python
       sandbox.git.clone(
           url=repo_url,
           path=workspace_path,
           username="x-access-token",
           password=github_token,
       )
       ```
   - Also in worker scripts (lines 822, 1307): Workers can clone using token from env
   - ~~Impact: Agents cannot clone repos, work on files directly, or create commits~~
   - **No action needed** - this was implemented

9. **🟡 Fault Tolerance System Not Designed for Sandbox** (Medium Risk - Future Integration)
   - Location: `docs/design/monitoring/fault_tolerance.md`
   - Issue: Existing fault tolerance system assumes direct agent access
   - Components affected:
     - **Heartbeat Detection**: Expects bidirectional heartbeats from agents
     - **Restart Orchestrator**: Doesn't know how to restart Daytona sandboxes
     - **Trajectory Context Builder**: Reads logs from local filesystem
     - **Forensics Collector**: Collects data from local agent process
   - Impact: MVP can work without fault tolerance, but Full Integration needs it
   - **MVP Strategy**: Use task timeouts, simple restart (terminate + spawn new)
   - **Full Integration**: Connect RestartOrchestrator to DaytonaSpawnerService
   - See "MVP vs Full Integration" section below

10. **~~🟡 GitHub API Missing Methods for Branch Workflow~~** ✅ **RESOLVED**
    - Location: `backend/omoi_os/services/github_api.py`
    - **Status**: ALL methods now exist!
    - **Existing** (ready to use):
      - `create_branch()` ✅
      - `create_pull_request()` ✅
      - `list_branches()`, `list_commits()`, `list_pull_requests()` ✅
    - **~~Missing~~ Now Implemented**:
      - `get_pull_request()` ✅ Line 804
      - `merge_pull_request()` ✅ Line 852
      - `delete_branch()` ✅ Line 923
      - `compare_branches()` ✅ Line 956
    - ~~Impact: BranchWorkflowService cannot complete PR lifecycle~~
    - **No action needed** - all methods implemented

11. **🔴 RestartOrchestrator Spawns Local Agents, Not Sandboxes** (HIGH Risk - Phase 7 Blocker)
    - Location: `backend/omoi_os/services/restart_orchestrator.py` line 246-265
    - Issue: `_spawn_replacement()` uses `AgentRegistryService.register_agent()` which creates local agents
    - Current code:
      ```python
      def _spawn_replacement(self, original_agent: Agent) -> str:
          replacement = self.agent_registry.register_agent(...)  # LOCAL ONLY!
          return replacement.id
      ```
    - Problem: For sandbox tasks, we need `DaytonaSpawnerService.spawn_for_task()` instead
    - Impact: Restarted sandbox agents become local agents, breaking sandbox isolation
    - **Required Fix (Phase 7)**:
      ```python
      if task.sandbox_id:  # Was a sandbox task
          new_sandbox_id = await self.daytona_spawner.spawn_for_task(...)
      else:
          replacement = self.agent_registry.register_agent(...)
      ```
    - Status: Documented in `07_existing_systems_integration.md` Phase 7 changes

### File Path Reference

For implementers, here are the exact file locations:

**Backend (confirmed to exist):**
- `backend/omoi_os/api/routes/events.py` - WebSocket endpoint + manager
- `backend/omoi_os/services/event_bus.py` - EventBusService
- `backend/omoi_os/services/daytona_spawner.py` - Sandbox spawner
- `backend/omoi_os/services/task_queue.py` - Task queue
- `backend/omoi_os/services/github_api.py` - GitHub API wrapper
- `backend/omoi_os/services/intelligent_guardian.py` - Guardian monitoring

**Frontend (confirmed to exist):**
- `frontend/hooks/useEvents.ts` - Event subscription hooks
- `frontend/providers/WebSocketProvider.tsx` - WebSocket context

**To Be Created:**
- `backend/omoi_os/api/routes/sandboxes.py` - NEW (Phase 1-2)
- `backend/omoi_os/services/branch_workflow.py` - NEW (Phase 5)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [What We Already Have](#what-we-already-have)
3. [What We Need](#what-we-need)
4. [Architecture Decision: Standalone vs. Integration](#architecture-decision)
5. [Recommended Approach](#recommended-approach)
6. [Implementation Breakdown](#implementation-breakdown)
7. [Code Examples](#code-examples)

---

## Executive Summary

**🎉 Key Finding**: The existing codebase has **~85% of the infrastructure** needed for real-time sandbox agent communication. **We already have a complete WebSocket event system!**

### ✅ Already Built (No Work Needed)
1. **WebSocket endpoint**: `/api/v1/ws/events` with filters
2. **WebSocket manager**: `WebSocketEventManager` with Redis pub/sub bridge
3. **Frontend hooks**: `useEvents()`, `useEntityEvents()`, `WebSocketProvider`
4. **Event bus**: `EventBusService` with Redis pub/sub

### ❌ Actual Gaps (Minimal Work)
1. **Sandbox event callback endpoint** - for workers to POST events (~2 hours)
2. **Database persistence** for sandbox sessions (~4 hours)
3. **Message injection** into running agents (~4-6 hours)
4. **Worker script updates** to report events more frequently (~4 hours)

**Revised Effort Estimate**: ~14-20 hours total (down from original ~36-52 hours)

---

## What We Already Have

### 1. 🎉 WebSocket Event System ✅ (COMPLETE!)

**This is the key discovery - we already have a full WebSocket system!**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  EXISTING WEBSOCKET SYSTEM (events.py)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  BACKEND: /api/v1/ws/events                                                 │
│  ────────────────────────────────────────────────────────────────           │
│                                                                             │
│  WebSocketEventManager (routes/events.py)                                   │
│  ├─ active_connections: Set[WebSocket]                                     │
│  ├─ connection_filters: dict[WebSocket, dict]                              │
│  ├─ Redis pub/sub listener (pattern: events.*)                             │
│  ├─ _broadcast_event() - sends to matching clients                         │
│  └─ _matches_filters() - filters by event_type, entity_type, entity_id     │
│                                                                             │
│  Endpoint: ws://localhost:18000/api/v1/ws/events                            │
│  ├─ Query params: ?event_types=X&entity_types=Y&entity_ids=Z               │
│  ├─ Dynamic subscription via WebSocket messages                            │
│  ├─ Ping/keepalive every 30s                                               │
│  └─ Full test coverage (test_websocket_events.py)                          │
│                                                                             │
│  ────────────────────────────────────────────────────────────────           │
│                                                                             │
│  FRONTEND:                                                                  │
│  ────────────────────────────────────────────────────────────────           │
│                                                                             │
│  WebSocketProvider (providers/WebSocketProvider.tsx)                        │
│  ├─ Auto-connects on mount                                                 │
│  ├─ Reconnection with backoff (5 attempts)                                 │
│  ├─ Invalidates React Query cache on ticket/agent events                   │
│  └─ Provides useWebSocket() hook                                           │
│                                                                             │
│  useEvents() Hook (hooks/useEvents.ts)                                      │
│  ├─ filters: { event_types, entity_types, entity_ids }                     │
│  ├─ onEvent callback                                                       │
│  ├─ events buffer (max 100)                                                │
│  ├─ updateFilters() - dynamic subscription                                 │
│  ├─ clearEvents()                                                          │
│  └─ Auto-reconnect on disconnect                                           │
│                                                                             │
│  useEntityEvents(entityType, entityId) Hook                                 │
│  └─ PERFECT for subscribing to sandbox events!                             │
│                                                                             │
│  useEventTypes(eventTypes) Hook                                             │
│  └─ Subscribe to specific event types                                      │
│                                                                             │
│  ────────────────────────────────────────────────────────────────           │
│                                                                             │
│  HOW TO USE FOR SANDBOX:                                                    │
│  ────────────────────────────────────────────────────────────────           │
│                                                                             │
│  Backend: Publish events with entity_type="sandbox", entity_id=sandbox_id  │
│                                                                             │
│    event_bus.publish(SystemEvent(                                          │
│        event_type="SANDBOX_AGENT_TOOL_USE",                                │
│        entity_type="sandbox",                                              │
│        entity_id=sandbox_id,                                               │
│        payload={"tool": "bash", "command": "npm install"}                  │
│    ))                                                                      │
│                                                                             │
│  Frontend: Subscribe with useEntityEvents                                   │
│                                                                             │
│    const { events } = useEntityEvents("sandbox", sandboxId)                │
│                                                                             │
│  VERDICT: NO NEW WEBSOCKET CODE NEEDED!                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Background Task Infrastructure ✅

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EXISTING BACKGROUND LOOPS (main.py)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  orchestrator_loop()                                                        │
│  ├─ Polls TaskQueueService every 10s                                       │
│  ├─ Spawns Daytona sandboxes when DAYTONA_SANDBOX_EXECUTION=true           │
│  └─ Falls back to legacy agent assignment otherwise                        │
│                                                                             │
│  heartbeat_monitoring_loop()                                                │
│  ├─ Checks missed heartbeats every 10s                                     │
│  ├─ Applies 3-miss escalation ladder                                       │
│  └─ Triggers RestartOrchestrator on unresponsive agents                    │
│                                                                             │
│  diagnostic_monitoring_loop()                                               │
│  ├─ Checks for stuck workflows every 60s                                   │
│  ├─ Spawns diagnostic agents                                               │
│  └─ Builds context from recent tasks/analyses                              │
│                                                                             │
│  approval_timeout_loop()                                                    │
│  └─ Processes ticket approval timeouts                                     │
│                                                                             │
│  VERDICT: No need for Celery/taskiq - asyncio loops are working well       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3. Event Bus Infrastructure ✅

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     EXISTING EVENT BUS (event_bus.py)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  EventBusService                                                            │
│  ├─ Redis pub/sub (redis://localhost:16379)                                │
│  ├─ Channel pattern: events.{event_type}                                   │
│  └─ SystemEvent model with entity_type, entity_id, payload                 │
│                                                                             │
│  Current Event Types Published:                                             │
│  ├─ TASK_ASSIGNED, TASK_COMPLETED, TASK_FAILED                             │
│  ├─ SANDBOX_SPAWNED (from orchestrator_loop)                               │
│  ├─ monitoring.* events (health checks, analyses)                          │
│  └─ agent.* events (heartbeat acknowledgments)                             │
│                                                                             │
│  WebSocket Bridge: ALREADY INTEGRATED!                                      │
│  ├─ WebSocketEventManager listens to Redis pub/sub                         │
│  └─ Broadcasts matching events to connected clients                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3. Daytona Sandbox Management ✅

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  EXISTING DAYTONA SPAWNER (daytona_spawner.py)               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DaytonaSpawnerService                                                      │
│  ├─ spawn_for_task() - creates Daytona sandbox                             │
│  │   ├─ Supports runtime: "claude"                                          │
│  │   ├─ Injects env vars (AGENT_ID, TASK_ID, MCP_SERVER_URL)               │
│  │   ├─ Uploads worker script (claude)                                      │
│  │   └─ Returns sandbox_id                                                 │
│  │                                                                         │
│  ├─ terminate_sandbox() - destroys sandbox                                 │
│  ├─ get_sandbox_info() - returns SandboxInfo                               │
│  └─ list_active_sandboxes() - all tracked sandboxes                        │
│                                                                             │
│  In-Memory Tracking:                                                        │
│  ├─ _sandboxes: Dict[sandbox_id, SandboxInfo]                              │
│  └─ _task_to_sandbox: Dict[task_id, sandbox_id]                            │
│                                                                             │
│  Missing:                                                                   │
│  ├─ Database persistence (sandboxes lost on restart)                       │
│  ├─ WebSocket subscriptions per sandbox                                    │
│  └─ Event callback endpoint for workers                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4. Worker Scripts ✅

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       EXISTING WORKER SCRIPTS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Claude Agent SDK Worker (embedded in daytona_spawner._get_worker_script)    │
│  ├─ Fetches task from MCP_SERVER_URL                                       │
│  ├─ Creates LocalConversation                                              │
│  ├─ Runs agent loop                                                        │
│  └─ Reports status back via HTTP POST                                      │
│                                                                             │
│  Claude Worker (claude_agent_worker.py)                                     │
│  ├─ Fetches task from MCP_SERVER_URL                                       │
│  ├─ Creates ClaudeSDKClient                                                │
│  ├─ Custom tools: read_file, write_file, run_command, etc.                 │
│  └─ Reports events back via HTTP POST                                      │
│                                                                             │
│  Current Event Reporting:                                                   │
│  ├─ POST {MCP_SERVER_URL}/tasks/{task_id}/events                           │
│  └─ Events: started, thinking, tool_use, completed, error                  │
│                                                                             │
│  Missing:                                                                   │
│  ├─ Streaming events (currently batched)                                   │
│  ├─ File change detection                                                  │
│  ├─ Command output streaming                                               │
│  └─ Message injection endpoint (receive user messages)                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5. Task Queue ✅

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      EXISTING TASK QUEUE (task_queue.py)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TaskQueueService (~860 lines)                                              │
│  ├─ enqueue_task() - create task with dependencies                         │
│  ├─ get_next_task() - DAG-aware priority selection                         │
│  ├─ get_ready_tasks() - batch tasks for parallel execution                 │
│  ├─ assign_task() - assign to agent                                        │
│  ├─ update_task_status() - status + result + conversation_id               │
│  ├─ check_task_timeout() - timeout detection                               │
│  ├─ cancel_task() - cancellation                                           │
│  └─ retry logic - exponential backoff, error classification                │
│                                                                             │
│  Key Fields Tracked:                                                        │
│  ├─ conversation_id (Claude Agent SDK conversation reference)              │
│  ├─ persistence_dir (Claude Agent SDK state directory)                     │
│  └─ result (task output as JSONB)                                          │
│                                                                             │
│  VERDICT: Fully functional, no changes needed                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6. Monitoring Infrastructure ✅

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EXISTING MONITORING (monitoring_loop.py)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MonitoringLoop                                                             │
│  ├─ _guardian_loop() - trajectory analysis every 60s                       │
│  ├─ _conductor_loop() - system coherence every 5 min                       │
│  └─ _health_check_loop() - health alerts every 30s                         │
│                                                                             │
│  IntelligentGuardian                                                        │
│  ├─ analyze_agent_trajectory() - LLM-powered analysis                      │
│  ├─ detect_steering_interventions() - identifies drift                     │
│  └─ execute_steering_intervention() - sends guidance                       │
│                                                                             │
│  Integration Point for Sandbox Monitoring:                                  │
│  ├─ Guardian can analyze sandbox agent conversations                       │
│  └─ Steering interventions can be routed to sandboxes                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## What We Need

### ~~Gap 1: WebSocket Endpoint~~ ✅ ALREADY EXISTS!

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ✅ ALREADY EXISTS: WebSocket System                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Endpoint: ws://localhost:18000/api/v1/ws/events                           │
│                                                                             │
│  What's Already There:                                                      │
│  ├─ ✅ WebSocket endpoint with query param filters                         │
│  ├─ ✅ WebSocketEventManager with Redis pub/sub listener                   │
│  ├─ ✅ Filter by event_types, entity_types, entity_ids                     │
│  ├─ ✅ Dynamic subscription updates via messages                           │
│  ├─ ✅ Ping/keepalive handling                                             │
│  ├─ ✅ Frontend: WebSocketProvider, useEvents(), useEntityEvents()         │
│  └─ ✅ Full test coverage                                                  │
│                                                                             │
│  For Sandbox Events:                                                        │
│  ├─ Backend: event_bus.publish() with entity_type="sandbox"                │
│  └─ Frontend: useEntityEvents("sandbox", sandboxId)                        │
│                                                                             │
│  Effort: 0 hours (NOTHING TO BUILD)                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### ~~Gap 1 (Actual): Sandbox Event Callback Endpoint~~ ✅ IMPLEMENTED

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   ✅ IMPLEMENTED: Sandbox Event Callback Endpoint            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Location: backend/omoi_os/api/routes/sandbox.py:365                       │
│  Endpoint: POST /api/v1/sandboxes/{sandbox_id}/events                      │
│                                                                             │
│  Features Implemented:                                                      │
│  ├─ Workers POST events to this endpoint ✅                                │
│  ├─ Server validates and persists event to sandbox_events table ✅         │
│  ├─ Server publishes to EventBusService ✅                                 │
│  ├─ Task finalization on agent.completed/failed events ✅                  │
│  └─ Session transcript saving for cross-sandbox resumption ✅              │
│                                                                             │
│  Request Body:                                                              │
│  {                                                                          │
│    "event_type": "agent.tool_use",                                         │
│    "event_data": { "tool": "bash", "command": "npm install" },             │
│    "source": "agent"                                                       │
│  }                                                                          │
│                                                                             │
│  Also includes GET endpoint for querying events:                           │
│  GET /api/v1/sandboxes/{sandbox_id}/events?limit=100&event_type=...       │
│                                                                             │
│  Effort: ~~2-3 hours~~ DONE                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### ~~Gap 2: Sandbox Session Persistence~~ ✅ IMPLEMENTED

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  ✅ IMPLEMENTED: Database Persistence                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Tables Created:                                                            │
│  ├─ sandbox_events - event audit log (sandbox.py:212-269)                  │
│  └─ claude_session_transcripts - session transcript storage                │
│                                                                             │
│  Models:                                                                    │
│  ├─ backend/omoi_os/models/sandbox_event.py ✅                             │
│  └─ backend/omoi_os/models/claude_session_transcript.py ✅                 │
│                                                                             │
│  Features:                                                                  │
│  ├─ Event persistence on POST /sandboxes/{id}/events ✅                    │
│  ├─ Event querying via GET /sandboxes/{id}/events ✅                       │
│  ├─ Session transcript saving for cross-sandbox resumption ✅              │
│  └─ Audit trail with timestamps ✅                                         │
│                                                                             │
│  Note: Sandbox tracking is still in-memory in DaytonaSpawnerService        │
│  (Medium Risk item #1). Full session persistence would require more work.  │
│                                                                             │
│  Effort: ~~4-6 hours~~ DONE                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### ~~Gap 3: Message Injection~~ ✅ IMPLEMENTED

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ✅ IMPLEMENTED: Message Injection                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Location: backend/omoi_os/api/routes/sandbox.py:758-831                   │
│                                                                             │
│  POST /api/v1/sandboxes/{sandbox_id}/messages ✅ (line 758)                │
│  ├─ User/Guardian posts message                                            │
│  ├─ Stored in Redis (RedisMessageQueue) or in-memory for tests            │
│  ├─ Broadcasts SANDBOX_MESSAGE_QUEUED event                                │
│  └─ Returns message_id for tracking                                        │
│                                                                             │
│  GET /api/v1/sandboxes/{sandbox_id}/messages ✅ (line 803)                 │
│  ├─ Worker polls for pending messages                                      │
│  ├─ Returns and clears pending messages (FIFO order)                       │
│  └─ Returns empty list if no messages                                      │
│                                                                             │
│  Message Types Supported:                                                   │
│  ├─ user_message - Guidance from user                                      │
│  ├─ interrupt - High-priority stop signal                                  │
│  ├─ guardian_nudge - Guardian intervention                                 │
│  └─ system - System-level notification                                     │
│                                                                             │
│  Backend: message_queue.py (Redis + InMemory implementations)              │
│                                                                             │
│  Effort: ~~4-6 hours~~ DONE                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### ~~Gap 4: Worker Script Updates~~ ✅ IMPLEMENTED

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   ✅ IMPLEMENTED: Worker Script Updates                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Location: daytona_spawner.py worker scripts                               │
│                                                                             │
│  Claude Worker Features:                                                    │
│  ├─ POST events to /api/v1/sandboxes/{id}/events ✅                        │
│  ├─ Report granular events (tool_use, thinking, progress) ✅               │
│  ├─ Poll for messages after each agent turn ✅                             │
│  ├─ Handle interrupt/user_message/guardian_nudge types ✅                  │
│  ├─ Git repo cloning with GITHUB_TOKEN ✅                                  │
│  ├─ Session transcript extraction for resumption ✅                        │
│  └─ Heartbeat reporting ✅                                                 │
│                                                                             │
│  Worker script also:                                                        │
│  ├─ Loads from backend/omoi_os/workers/claude_sandbox_worker.py           │
│  └─ Supports resume_session_id for continuing previous sessions            │
│                                                                             │
│  Effort: ~~4 hours~~ DONE                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### ~~Gap 5: Guardian & Monitoring Integration~~ ✅ IMPLEMENTED

```
┌─────────────────────────────────────────────────────────────────────────────┐
│           ✅ IMPLEMENTED: Guardian & Existing Systems Integration            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ~~PROBLEM: Guardian CANNOT intervene with sandbox agents!~~                │
│  SOLVED: Guardian now fully supports sandbox interventions!                 │
│                                                                             │
│  All Changes Implemented:                                                   │
│                                                                             │
│  1. sandbox_id in Task Model ✅                                            │
│     Location: backend/omoi_os/models/task.py:63                            │
│     sandbox_id: Mapped[Optional[str]] = mapped_column(...)                 │
│                                                                             │
│  2. Guardian Sandbox Mode Detection ✅                                      │
│     Location: intelligent_guardian.py:693-702                              │
│     def _is_sandbox_task(self, task: Task) -> bool:                        │
│         return bool(task.sandbox_id) if task else False                    │
│                                                                             │
│  3. Sandbox Intervention Path ✅                                           │
│     Location: intelligent_guardian.py:704-749                              │
│     async def _sandbox_intervention(self, intervention, task):             │
│         → POST /api/v1/sandboxes/{task.sandbox_id}/messages                │
│         → message_type: "guardian_nudge"                                   │
│                                                                             │
│  4. Intervention Routing ✅                                                 │
│     Location: intelligent_guardian.py:825-887                              │
│     if self._is_sandbox_task(task):                                        │
│         return await self._sandbox_intervention(intervention, task)        │
│                                                                             │
│  5. Worker Handles Guardian Messages ✅                                     │
│     Worker polls and processes guardian_nudge message type                 │
│                                                                             │
│  Effort: ~~6-8 hours~~ DONE                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Decision

### ✅ Decision: Use Existing WebSocket System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               ARCHITECTURE: Leverage Existing Infrastructure                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  We DON'T need to build new WebSocket infrastructure!                       │
│                                                                             │
│  Current Flow (already working):                                            │
│                                                                             │
│     EventBusService.publish()                                               │
│            │                                                                │
│            ▼                                                                │
│     Redis Pub/Sub (events.{event_type})                                    │
│            │                                                                │
│            ▼                                                                │
│     WebSocketEventManager._listen_to_redis()                               │
│            │                                                                │
│            ▼                                                                │
│     WebSocketEventManager._broadcast_event()                               │
│            │                                                                │
│            ▼                                                                │
│     Frontend WebSocket clients (filtered by entity_id)                     │
│                                                                             │
│  ────────────────────────────────────────────────────────────────           │
│                                                                             │
│  What We Need to Add:                                                       │
│                                                                             │
│     Sandbox Worker                                                          │
│            │                                                                │
│            │ POST /api/v1/sandboxes/{id}/events                            │
│            ▼                                                                │
│     New Endpoint (2-3 hours work)                                          │
│            │                                                                │
│            │ event_bus.publish(entity_type="sandbox", entity_id=id)        │
│            ▼                                                                │
│     ... existing flow handles the rest ...                                 │
│                                                                             │
│  ────────────────────────────────────────────────────────────────           │
│                                                                             │
│  Frontend Usage:                                                            │
│                                                                             │
│     // Subscribe to all events for a specific sandbox                       │
│     const { events } = useEntityEvents("sandbox", sandboxId)               │
│                                                                             │
│     // Or filter by specific event types                                    │
│     const { events } = useEvents({                                          │
│       filters: {                                                            │
│         entity_types: ["sandbox"],                                         │
│         entity_ids: [sandboxId],                                           │
│         event_types: ["SANDBOX_AGENT_TOOL_USE", "SANDBOX_AGENT_MESSAGE"]   │
│       }                                                                    │
│     })                                                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### No Need for Celery/taskiq/DBOS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   WHY NO SEPARATE TASK SYSTEM NEEDED                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ❌ NOT NEEDED: Celery, taskiq, DBOS, separate process                     │
│                                                                             │
│  Reasons:                                                                   │
│                                                                             │
│  1. Asyncio loops are working well:                                         │
│     ├─ orchestrator_loop (spawns sandboxes)                                │
│     ├─ heartbeat_monitoring_loop                                           │
│     ├─ diagnostic_monitoring_loop                                          │
│     └─ All running in main.py as asyncio tasks                             │
│                                                                             │
│  2. WebSocket already integrated:                                           │
│     ├─ WebSocketEventManager listens to Redis                              │
│     └─ Broadcasts to filtered clients                                      │
│                                                                             │
│  3. Event bus handles pub/sub:                                              │
│     ├─ EventBusService.publish() → Redis                                   │
│     └─ Multiple consumers can subscribe                                    │
│                                                                             │
│  4. Single deployment unit:                                                 │
│     ├─ Simpler ops                                                         │
│     ├─ Shared database connections                                         │
│     └─ Less infrastructure to manage                                       │
│                                                                             │
│  If scaling becomes an issue later, THEN consider extraction.              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Recommended Approach

### Revised Implementation Plan (Much Simpler!)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     REVISED IMPLEMENTATION PLAN                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1: Sandbox Event Callback (~2-3 hours)                               │
│  ─────────────────────────────────────────────────────────────              │
│                                                                             │
│  Just ONE new endpoint:                                                     │
│                                                                             │
│  POST /api/v1/sandboxes/{sandbox_id}/events                                │
│                                                                             │
│  @router.post("/sandboxes/{sandbox_id}/events")                            │
│  async def report_sandbox_event(                                            │
│      sandbox_id: str,                                                       │
│      event: SandboxEventCreate,                                             │
│      event_bus: EventBusService = Depends(get_event_bus_service)           │
│  ):                                                                         │
│      # Publish to existing event bus                                        │
│      event_bus.publish(SystemEvent(                                         │
│          event_type=f"SANDBOX_{event.event_type.upper()}",                 │
│          entity_type="sandbox",                                             │
│          entity_id=sandbox_id,                                              │
│          payload=event.event_data                                           │
│      ))                                                                     │
│      return {"status": "ok"}                                                │
│                                                                             │
│  That's it! The existing WebSocketEventManager handles the rest.            │
│                                                                             │
│  ─────────────────────────────────────────────────────────────              │
│                                                                             │
│  Phase 2: Message Injection (~4-6 hours)                                    │
│  ─────────────────────────────────────────────────────────────              │
│                                                                             │
│  Two endpoints:                                                             │
│                                                                             │
│  POST /api/v1/sandboxes/{sandbox_id}/messages                              │
│  ├─ Stores message in Redis or in-memory                                   │
│  └─ Sets a flag that sandbox has pending messages                          │
│                                                                             │
│  GET /api/v1/sandboxes/{sandbox_id}/messages                               │
│  ├─ Worker polls this after each agent turn                                │
│  └─ Returns and clears pending messages                                    │
│                                                                             │
│  ─────────────────────────────────────────────────────────────              │
│                                                                             │
│  Phase 3: Worker Script Updates (~4 hours)                                  │
│  ─────────────────────────────────────────────────────────────              │
│                                                                             │
│  Update workers to:                                                         │
│  ├─ POST events to /sandboxes/{id}/events                                  │
│  ├─ Poll GET /sandboxes/{id}/messages after agent turns                    │
│  └─ Handle interrupt commands                                              │
│                                                                             │
│  ─────────────────────────────────────────────────────────────              │
│                                                                             │
│  Phase 4 (Optional): Database Persistence (~4-6 hours)                      │
│  ─────────────────────────────────────────────────────────────              │
│                                                                             │
│  Only if you want event history/audit trail:                                │
│  ├─ sandbox_sessions table                                                 │
│  ├─ sandbox_events table                                                   │
│  └─ Can be done later, not blocking MVP                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Breakdown

### Revised Effort Estimate

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   REVISED IMPLEMENTATION EFFORT                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase          │ Effort (hours) │ Components                              │
│  ───────────────┼────────────────┼─────────────────────────────────────────│
│  Phase 1        │  2-3           │ Sandbox event callback endpoint         │
│  Phase 2        │  4-6           │ Message injection (2 endpoints)         │
│  Phase 3        │  4             │ Worker script updates                   │
│  Phase 4 (opt)  │  4-6           │ Database persistence (if needed)        │
│  ───────────────┼────────────────┼─────────────────────────────────────────│
│  MVP TOTAL      │  10-13 hours   │ ~1-2 days of focused work               │
│  Full TOTAL     │  14-19 hours   │ ~2-3 days with DB persistence           │
│                                                                             │
│  SAVINGS: 60-70% reduction from original estimate!                          │
│  (Original: 36-52 hours → Revised: 14-19 hours)                            │
│                                                                             │
│  Risk Factors:                                                              │
│  ├─ Worker script testing in Daytona                                       │
│  └─ Agent SDK message injection complexity                                 │
│                                                                             │
│  NO LONGER RISKS (already solved):                                          │
│  ├─ ✅ WebSocket authentication (existing system)                          │
│  ├─ ✅ Reconnection/buffering (existing useEvents hook)                    │
│  └─ ✅ Redis pub/sub bridge (existing WebSocketEventManager)               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Files Created/Modified (2025-12-18 Status)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FILES CREATED/MODIFIED                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ✅ CREATED FILES:                                                          │
│  ├─ backend/omoi_os/api/routes/sandbox.py    (event + message endpoints)   │
│  ├─ backend/omoi_os/api/routes/branch_workflow.py (branch workflow API)    │
│  ├─ backend/omoi_os/services/branch_workflow.py (branch workflow service)  │
│  ├─ backend/omoi_os/services/message_queue.py (Redis + InMemory queues)    │
│  ├─ backend/omoi_os/models/sandbox_event.py (event persistence model)      │
│  ├─ backend/omoi_os/models/claude_session_transcript.py (session storage)  │
│  └─ backend/omoi_os/workers/claude_sandbox_worker.py (worker script)       │
│                                                                             │
│  ✅ MODIFIED FILES:                                                         │
│  ├─ backend/omoi_os/models/task.py (added sandbox_id field)                │
│  ├─ backend/omoi_os/services/daytona_spawner.py (worker scripts, git)      │
│  ├─ backend/omoi_os/services/intelligent_guardian.py (sandbox routing)     │
│  ├─ backend/omoi_os/services/github_api.py (added 4 methods)               │
│  └─ backend/omoi_os/api/main.py (route registration)                       │
│                                                                             │
│  ❌ STILL NEEDS MODIFICATION:                                               │
│  └─ backend/omoi_os/services/restart_orchestrator.py (sandbox awareness)   │
│                                                                             │
│  Total: 7 new files, 5 modified files (DONE!)                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Code Examples

### Example 1: Sandbox Event Callback Endpoint (NEW)

```python
# backend/omoi_os/api/routes/sandboxes.py

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from omoi_os.api.dependencies import get_event_bus_service
from omoi_os.services.event_bus import EventBusService, SystemEvent

router = APIRouter(prefix="/sandboxes", tags=["sandboxes"])


class SandboxEventCreate(BaseModel):
    """Event from a sandbox worker."""
    event_type: str  # e.g., "agent.tool_use", "agent.message", "agent.thinking"
    event_data: dict
    source: str = "agent"  # agent | user | guardian | system


@router.post("/{sandbox_id}/events")
async def report_sandbox_event(
    sandbox_id: str,
    event: SandboxEventCreate,
    event_bus: EventBusService = Depends(get_event_bus_service)
):
    """
    Receive events from sandbox workers and broadcast via WebSocket.
    
    The existing WebSocketEventManager will automatically pick this up
    and broadcast to any clients subscribed with entity_type="sandbox".
    """
    # Publish to existing event bus - NO NEW CODE NEEDED!
    event_bus.publish(SystemEvent(
        event_type=f"SANDBOX_{event.event_type.upper().replace('.', '_')}",
        entity_type="sandbox",
        entity_id=sandbox_id,
        payload={
            "event_type": event.event_type,
            "source": event.source,
            **event.event_data
        }
    ))
    
    return {"status": "ok", "sandbox_id": sandbox_id}
```

### Example 2: Message Injection Endpoints (NEW)

```python
# Continued in backend/omoi_os/api/routes/sandboxes.py

from typing import List, Optional
import redis

# In-memory message queue (or use Redis)
_pending_messages: dict[str, list[dict]] = {}


class SandboxMessage(BaseModel):
    """Message to send to a sandbox agent."""
    content: str
    message_type: str = "user_message"  # user_message | interrupt | guidance


@router.post("/{sandbox_id}/messages")
async def send_message_to_sandbox(
    sandbox_id: str,
    message: SandboxMessage,
    event_bus: EventBusService = Depends(get_event_bus_service)
):
    """
    Queue a message to be injected into the sandbox agent.
    The worker polls GET /messages to retrieve pending messages.
    """
    if sandbox_id not in _pending_messages:
        _pending_messages[sandbox_id] = []
    
    _pending_messages[sandbox_id].append({
        "content": message.content,
        "message_type": message.message_type,
        "timestamp": utc_now().isoformat()
    })
    
    # Also broadcast that a message was sent (for UI feedback)
    event_bus.publish(SystemEvent(
        event_type="SANDBOX_MESSAGE_QUEUED",
        entity_type="sandbox",
        entity_id=sandbox_id,
        payload={"message_type": message.message_type}
    ))
    
    return {"status": "queued", "queue_size": len(_pending_messages[sandbox_id])}


@router.get("/{sandbox_id}/messages")
async def get_pending_messages(sandbox_id: str) -> List[dict]:
    """
    Worker polls this endpoint to get pending messages.
    Messages are cleared after retrieval.
    """
    messages = _pending_messages.pop(sandbox_id, [])
    return messages
```

### Example 3: Frontend Usage (EXISTING HOOKS!)

```tsx
// No new frontend code needed! Just use existing hooks:

import { useEntityEvents } from "@/hooks/useEvents"

function SandboxMonitor({ sandboxId }: { sandboxId: string }) {
  // Subscribe to all events for this sandbox
  const { events, isConnected } = useEntityEvents("sandbox", sandboxId)
  
  return (
    <div>
      <div>Status: {isConnected ? "Connected" : "Disconnected"}</div>
      
      {events.map((event, i) => (
        <div key={i}>
          <strong>{event.event_type}</strong>
          <pre>{JSON.stringify(event.payload, null, 2)}</pre>
        </div>
      ))}
    </div>
  )
}

// Or with specific event type filtering:
import { useEvents } from "@/hooks/useEvents"

function ToolUseMonitor({ sandboxId }: { sandboxId: string }) {
  const { events } = useEvents({
    filters: {
      entity_types: ["sandbox"],
      entity_ids: [sandboxId],
      event_types: ["SANDBOX_AGENT_TOOL_USE"]
    }
  })
  
  return <div>{/* ... */}</div>
}
```

### Example 4: Worker Script Update (MODIFIED)

```python
# Update to worker script in daytona_spawner.py

# Change from posting to tasks endpoint:
#   requests.post(f"{MCP_SERVER_URL}/tasks/{TASK_ID}/events", ...)

# To posting to sandbox endpoint:
def report_event(event_type: str, event_data: dict):
    """Report event to server for WebSocket broadcast."""
    requests.post(
        f"{MCP_SERVER_URL}/api/v1/sandboxes/{SANDBOX_ID}/events",
        json={
            "event_type": event_type,
            "event_data": event_data,
            "source": "agent"
        }
    )

def poll_for_messages() -> list:
    """Check for pending user/guardian messages."""
    response = requests.get(
        f"{MCP_SERVER_URL}/api/v1/sandboxes/{SANDBOX_ID}/messages"
    )
    return response.json() if response.ok else []

# In agent loop:
while agent_running:
    # Run agent turn
    result = agent.step()
    
    # Report events
    report_event("agent.tool_use", {"tool": result.tool, "input": result.input})
    
    # Check for messages
    messages = poll_for_messages()
    for msg in messages:
        if msg["message_type"] == "interrupt":
            agent.stop()
        elif msg["message_type"] == "user_message":
            agent.inject_message(msg["content"])
```

---

## Summary

### 🎉 What We Already Have (Complete!)
- ✅ **WebSocket endpoint**: `/api/v1/ws/events` with filters
- ✅ **WebSocket manager**: `WebSocketEventManager` with Redis bridge
- ✅ **Frontend hooks**: `useEvents()`, `useEntityEvents()`, `WebSocketProvider`
- ✅ **Event bus**: `EventBusService` with Redis pub/sub
- ✅ Background task loops (asyncio)
- ✅ Daytona sandbox spawner
- ✅ Worker scripts (claude)
- ✅ Task queue with full DAG support
- ✅ Monitoring infrastructure

### What's Been Built Since Original Analysis (2025-12-18 Update!)
- ✅ **Sandbox event callback endpoint** - `sandbox.py:365` with DB persistence
- ✅ **Message injection endpoints** - `sandbox.py:758,803` with Redis queue
- ✅ **Worker script updates** - POST to sandbox endpoints, message polling, heartbeats
- ✅ **Guardian sandbox integration** - `intelligent_guardian.py:693-887`
- ✅ **Database persistence** - `sandbox_events` and `claude_session_transcripts` tables
- ✅ **GitHub API methods** - `merge_pull_request`, `delete_branch`, `get_pull_request`, `compare_branches`
- ✅ **Branch workflow service** - `branch_workflow.py` + routes
- ✅ **Session transcript saving** - Cross-sandbox resumption support

### ❌ What Still Needs Work
- ❌ **RestartOrchestrator sandbox handling** (~4-6 hours) - No daytona/sandbox awareness
- ❌ **Full fault tolerance for sandboxes** (~8-12 hours) - Heartbeat consumption, escalation ladder

### Revised Effort
**Original estimate**: 36-52 hours
**~~MVP estimate~~**: ~~14-19 hours~~ → **DONE!** 🎉
**~~Full estimate with Guardian~~**: ~~20-27 hours~~ → **DONE!** 🎉
**Remaining (fault tolerance)**: 12-18 hours
**Total completed**: ~90% of original scope!

---

## MVP vs Full Integration Strategy

This section clarifies the two-track approach to implementation:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                MVP vs FULL INTEGRATION ROADMAP                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MVP TRACK (Phases 0-3)                  FULL INTEGRATION (Phases 4-7)     │
│  ─────────────────────                   ─────────────────────────────     │
│  Goal: Get sandbox agents working        Goal: Production-ready system     │
│  Timeframe: 1-2 days                     Timeframe: +3-5 days              │
│                                                                             │
│  ✅ Event streaming to frontend          ✅ Database persistence            │
│  ✅ Message injection for interventions  ✅ Branch workflow automation      │
│  ✅ Guardian can steer sandbox agents    ✅ Guardian integrated properly    │
│  ✅ Basic task timeout handling          ✅ Heartbeat-based health          │
│                                          ✅ RestartOrchestrator integration │
│  ⚠️ No heartbeat system                  ✅ Full fault tolerance            │
│  ⚠️ Simple restart (kill + respawn)     ✅ Forensics & quarantine          │
│  ⚠️ In-memory sandbox tracking                                             │
│                                                                             │
│  WHY THIS ORDER:                                                            │
│  ───────────────                                                            │
│  1. MVP validates core assumptions FAST                                    │
│  2. Full Integration builds ON TOP of MVP (not parallel)                   │
│  3. Each phase adds to existing code, doesn't replace                      │
│  4. Tests at each gate prevent regressions                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### MVP Simplifications

The MVP intentionally skips some sophistication to get working faster:

| Feature | MVP Approach | Full Integration |
|---------|-------------|------------------|
| **Health Monitoring** | Task timeout (no heartbeats) | Bidirectional heartbeats to `/sandboxes/{id}/heartbeat` |
| **Agent Restart** | Simple: terminate sandbox + spawn new | Full escalation ladder (1→2→3 misses) via RestartOrchestrator |
| **Sandbox Tracking** | In-memory dict in DaytonaSpawner | Database table + foreign key to Task |
| **Log Collection** | Event streaming only | Pull logs from sandbox for forensics |
| **Guardian** | Message injection works | Full trajectory analysis with sandbox context |
| **Anomaly Detection** | None | Sandbox-specific baselines |

### Why MVP First is Safe

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MVP → FULL INTEGRATION UPGRADE PATH                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MVP creates EXTENSION POINTS for Full Integration:                        │
│                                                                             │
│  1. Event Callback Endpoint (Phase 1)                                       │
│     MVP: Workers POST events                                               │
│     Full: SAME endpoint, add heartbeat event type                          │
│     └─ No breaking change, just new event type                             │
│                                                                             │
│  2. Message Injection (Phase 2)                                             │
│     MVP: Guardian uses it for interventions                                │
│     Full: SAME endpoint, Fault Tolerance uses it too                       │
│     └─ No breaking change, just more consumers                             │
│                                                                             │
│  3. sandbox_id on Task (Phase 6)                                           │
│     MVP: Guardian uses for mode detection                                  │
│     Full: RestartOrchestrator uses for sandbox restart                     │
│     └─ Field is there, more code uses it                                   │
│                                                                             │
│  4. DaytonaSpawnerService                                                   │
│     MVP: spawn_for_task() and terminate_sandbox()                          │
│     Full: RestartOrchestrator calls these same methods                     │
│     └─ No new methods needed, just integration                             │
│                                                                             │
│  KEY INSIGHT: MVP is a SUBSET of Full Integration, not separate system     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Fault Tolerance Integration Details (Full Integration)

When ready for Full Integration, these are the specific changes needed:

**Phase 7A: Heartbeat for Sandbox Agents**
```python
# Worker script addition (in _get_worker_script)
# Every 15 seconds, POST heartbeat:
requests.post(
    f"{API_BASE}/api/v1/sandboxes/{sandbox_id}/events",
    json={
        "event_type": "heartbeat",
        "event_data": {
            "status": "running",
            "current_action": agent.current_action,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
)
```

**Phase 7B: RestartOrchestrator Integration**
```python
# In RestartOrchestrator.initiate_restart()
task = get_task_for_agent(agent_id)

if task.sandbox_id:
    # Sandbox mode: use DaytonaSpawner
    await daytona_spawner.terminate_sandbox(task.sandbox_id)
    new_sandbox_id = await daytona_spawner.spawn_for_task(
        task_id=task.id,
        agent_id=agent_id,
        phase_id=task.phase_id,
        agent_type=task.agent_type,
    )
    task.sandbox_id = new_sandbox_id
    session.commit()
else:
    # Legacy mode: existing logic
    ...
```

**Phase 7C: Trajectory Context for Sandbox**
```python
# In TrajectoryContextBuilder
if task.sandbox_id:
    # Get context from event store (events were POSTed by worker)
    recent_events = await db.query(SandboxEvent).filter(
        SandboxEvent.sandbox_id == task.sandbox_id
    ).order_by(SandboxEvent.created_at.desc()).limit(100).all()
    
    context.logs_snippet = "\n".join(e.payload.get("message", "") for e in recent_events)
else:
    # Legacy mode: read from local filesystem
    context.logs_snippet = tail_file(task.persistence_dir + "/agent.log")
```

### Why the Reduction?
The existing WebSocket system already handles:
- Redis pub/sub → WebSocket bridge
- Client filter subscriptions
- Reconnection handling
- Ping/keepalive
- Dynamic subscription updates

We just need to:
1. Add one endpoint for workers to POST events
2. Add two endpoints for message injection
3. Update worker scripts to use new endpoints

### Next Steps
1. Add `POST /api/v1/sandboxes/{id}/events` endpoint
2. Add message injection endpoints
3. Update worker scripts in `daytona_spawner.py`
4. (Optional) Add database persistence for event history

---

## Related Documents

- [Sandbox Agent Architecture](./sandbox_agent_architecture.md)
- [System Inventory Summary](../system_inventory_summary.md)
- [Product Vision](../product_vision.md)

---

## Existing WebSocket Code References

Backend:
- `backend/omoi_os/api/routes/events.py` - WebSocket endpoint & manager
- `backend/tests/test_websocket_events.py` - Full test coverage
- `backend/scripts/test_websocket_client.py` - Manual test client

Frontend:
- `frontend/providers/WebSocketProvider.tsx` - Context provider
- `frontend/hooks/useEvents.ts` - Event subscription hooks
