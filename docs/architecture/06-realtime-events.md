# Part 6: Real-Time Event System

> Summary doc — see linked design docs for full details.

## Overview

OmoiOS uses a **Redis pub/sub EventBus** as the backbone for all inter-service communication, with WebSocket forwarding to the frontend for live monitoring dashboards.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌──────────────┐
│  Backend Service │ ──pub──→│  Redis EventBus  │ ──sub──→│  Subscribers │
│  (any service)   │         │  (pub/sub)       │         │  (services)  │
└─────────────────┘         └────────┬─────────┘         └──────────────┘
                                     │
                                     │ forward
                                     ▼
                            ┌──────────────────┐         ┌──────────────┐
                            │  WebSocket Server │ ──ws──→ │   Frontend   │
                            │  (events route)   │         │  (React)     │
                            └──────────────────┘         └──────────────┘
```

## EventBusService

The `EventBusService` wraps Redis pub/sub with typed event handling:

```python
# Publishing
event_bus.publish("TASK_COMPLETED", {
    "entity_type": "task",
    "entity_id": str(task.id),
    "payload": {"status": "done", "result": result_data}
})

# Subscribing
event_bus.subscribe("TASK_COMPLETED", handler_function)
```

**Channel naming**: `events.{EVENT_TYPE}` (e.g., `events.TASK_COMPLETED`)

## Event Categories

### Agent & Sandbox Events

| Event | Source | Description |
|-------|--------|-------------|
| `agent.started` | ClaudeSandboxWorker | Agent begins execution |
| `agent.thinking` | ClaudeSandboxWorker | Agent reasoning step |
| `agent.message` | ClaudeSandboxWorker | Agent text output |
| `agent.completed` | ClaudeSandboxWorker | Agent finished task |
| `agent.error` | ClaudeSandboxWorker | Agent encountered error |
| `agent.tool_use` | ClaudeSandboxWorker | Tool invocation |
| `sandbox.heartbeat` | ClaudeSandboxWorker | Health check (every 30s) |

### Task Lifecycle Events

| Event | Source | Subscribers |
|-------|--------|-------------|
| `TASK_CREATED` | TaskQueueService | orchestrator_worker |
| `TASK_STARTED` | TaskQueueService | phase_manager, phase_progression |
| `TASK_COMPLETED` | TaskQueueService | synthesis_service, spec_task_execution, phase_manager, phase_progression |
| `TASK_FAILED` | TaskQueueService | spec_task_execution |
| `TASK_VALIDATION_PASSED` | ValidationOrchestrator | orchestrator_worker |
| `TASK_VALIDATION_FAILED` | ValidationOrchestrator | orchestrator_worker |

### Coordination Events

| Event | Source | Subscribers |
|-------|--------|-------------|
| `TICKET_CREATED` | TicketWorkflowOrchestrator | orchestrator_worker |
| `PHASE_TRANSITION` | PhaseManager | phase_progression |
| `coordination.join.created` | CoordinationService | synthesis_service |
| `synthesis.completed` | SynthesisService | convergence_merge_service |

### Monitoring Events (Frontend-Bound)

| Event | Destination | Purpose |
|-------|-------------|---------|
| `monitoring_update` | WebSocket → Frontend | Guardian/Conductor analysis results |
| `steering_issued` | WebSocket → Frontend | Agent intervention notifications |
| `task_updated` | WebSocket → Frontend | Task status changes |
| `ticket_updated` | WebSocket → Frontend | Ticket status changes |
| `agent_status_changed` | WebSocket → Frontend | Agent health changes |

## Frontend WebSocket Integration

The frontend uses a hybrid approach:

1. **React Query**: WebSocket events trigger `queryClient.invalidateQueries()` for entity-specific cache busting
2. **Zustand**: `websocketSync` middleware transforms events into state mutations
3. **Optimistic Updates**: UI changes immediately, confirms/rolls back on server response

## Known Issues

See [Integration Gaps](14-integration-gaps.md#gap-2-event-system-gaps) for the full list of events published with no subscribers (153 published vs 18 subscribed).

## Detailed Documentation

| Document | Content |
|----------|---------|
| [React Query + WebSocket Integration](../design/frontend/react_query_websocket.md) | Full real-time data flow, cache invalidation strategies |
| [Frontend Architecture](../design/frontend/frontend_architecture_shadcn_nextjs.md) | WebSocket middleware stack, Zustand sync patterns |
