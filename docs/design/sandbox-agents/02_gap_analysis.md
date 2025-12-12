# Sandbox System Gap Analysis

**Created**: 2025-12-12  
**Updated**: 2025-12-12 (major revision after discovering existing WebSocket system)  
**Status**: Planning Document  
**Purpose**: Comprehensive analysis of existing infrastructure vs. requirements for real-time sandbox agent communication

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
│  │   ├─ Supports runtime: "openhands" | "claude"                           │
│  │   ├─ Injects env vars (AGENT_ID, TASK_ID, MCP_SERVER_URL)               │
│  │   ├─ Uploads worker script (openhands or claude)                        │
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
│  OpenHands Worker (embedded in daytona_spawner._get_worker_script)          │
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
│  ├─ conversation_id (OpenHands conversation reference)                     │
│  ├─ persistence_dir (OpenHands state directory)                            │
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

### Gap 1 (Actual): Sandbox Event Callback Endpoint ❌

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   NEEDED: Sandbox Event Callback Endpoint                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Endpoint: POST /api/v1/sandboxes/{sandbox_id}/events                      │
│                                                                             │
│  Purpose:                                                                   │
│  ├─ Workers POST events to this endpoint                                   │
│  ├─ Server validates and persists event                                    │
│  └─ Server publishes to EventBusService                                    │
│                                                                             │
│  Request Body:                                                              │
│  {                                                                          │
│    "event_type": "agent.tool_use",                                         │
│    "event_data": { "tool": "bash", "command": "npm install" },             │
│    "source": "agent"                                                       │
│  }                                                                          │
│                                                                             │
│  What Happens:                                                              │
│  1. Validate event schema                                                  │
│  2. (Optional) Persist to sandbox_events table                             │
│  3. Publish via event_bus.publish(SystemEvent(                             │
│       event_type="SANDBOX_EVENT",                                          │
│       entity_type="sandbox",                                               │
│       entity_id=sandbox_id,                                                │
│       payload=event_data                                                   │
│     ))                                                                     │
│  4. WebSocketEventManager automatically broadcasts to subscribers          │
│                                                                             │
│  Effort: ~2-3 hours                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Gap 2: Sandbox Session Persistence ❌

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     NEEDED: Database Persistence                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  New Tables (optional but recommended):                                     │
│  ├─ sandbox_sessions - tracks sandbox instances                            │
│  └─ sandbox_events - event audit log for replay                            │
│                                                                             │
│  Current State:                                                             │
│  ├─ SandboxInfo stored in memory only (DaytonaSpawnerService)              │
│  └─ Lost on server restart                                                 │
│                                                                             │
│  Note: This is optional for MVP. Events flow through Redis pub/sub         │
│  regardless. DB persistence is for:                                         │
│  ├─ Audit trail                                                            │
│  ├─ Event replay on reconnection                                           │
│  └─ Query sandbox history                                                  │
│                                                                             │
│  Effort: ~4-6 hours (migration + models + service updates)                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Gap 3: Message Injection ❌

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NEEDED: Message Injection                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Purpose: User/Guardian sends message to running agent                      │
│                                                                             │
│  Recommended: HTTP Polling (Simple & Reliable)                              │
│  ────────────────────────────────────────────────────────────────           │
│                                                                             │
│  Endpoint: GET /api/v1/sandboxes/{sandbox_id}/messages                     │
│  ├─ Worker polls every 2-5 seconds                                         │
│  ├─ Returns pending messages for the sandbox                               │
│  └─ Server marks messages as delivered                                     │
│                                                                             │
│  Endpoint: POST /api/v1/sandboxes/{sandbox_id}/messages                    │
│  ├─ User/Guardian posts message                                            │
│  └─ Stored in memory or DB until worker polls                              │
│                                                                             │
│  Worker Integration:                                                        │
│  1. After each agent turn, poll for messages                               │
│  2. If message exists, inject into agent conversation                      │
│  3. Handle "interrupt" command to stop current operation                   │
│                                                                             │
│  Effort: ~4-6 hours (endpoint + worker modification)                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Gap 4: Worker Script Updates ❌

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      NEEDED: Worker Script Updates                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Update OpenHands Worker (_get_worker_script):                              │
│  ├─ POST events to /api/v1/sandboxes/{id}/events (not tasks endpoint)      │
│  ├─ Report more granular events (tool_use, thinking, etc.)                 │
│  ├─ Poll for messages after each agent turn                                │
│  └─ Handle interrupt commands                                              │
│                                                                             │
│  Update Claude Worker (claude_agent_worker.py):                             │
│  ├─ Same changes as OpenHands worker                                       │
│  └─ Use PreToolUse/PostToolUse hooks for real-time reporting               │
│                                                                             │
│  Effort: ~4 hours                                                          │
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

### Files to Create/Modify (Reduced!)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     REVISED FILES TO CREATE/MODIFY                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  NEW FILES (minimal):                                                       │
│  ├─ backend/omoi_os/api/routes/sandboxes.py    (event + message endpoints) │
│  └─ backend/omoi_os/api/schemas/sandbox.py     (request/response DTOs)     │
│                                                                             │
│  MODIFIED FILES:                                                            │
│  ├─ backend/omoi_os/services/daytona_spawner.py (worker script updates)    │
│  └─ backend/omoi_os/api/main.py                 (route registration)       │
│                                                                             │
│  OPTIONAL (for persistence):                                                │
│  ├─ backend/alembic/versions/XXX_sandbox_sessions.py                       │
│  └─ backend/omoi_os/models/sandbox.py                                      │
│                                                                             │
│  NO LONGER NEEDED:                                                          │
│  ├─ ❌ backend/omoi_os/api/websockets/sandbox_ws.py (use existing!)        │
│  ├─ ❌ backend/omoi_os/services/ws_manager.py (use existing!)              │
│  └─ ❌ EventBusService modifications (already works!)                      │
│                                                                             │
│  Total: 2 new files, 2 modified files (MVP)                                │
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
- ✅ Worker scripts (openhands + claude)
- ✅ Task queue with full DAG support
- ✅ Monitoring infrastructure

### What We Need (Minimal!)
- ❌ Sandbox event callback endpoint (~2-3 hours)
- ❌ Message injection endpoints (~4-6 hours)
- ❌ Worker script updates (~4 hours)
- ❌ (Optional) Database persistence for audit trail

### Revised Effort
**Original estimate**: 36-52 hours  
**Revised estimate**: 14-19 hours  
**Savings**: 60-70% reduction!

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
