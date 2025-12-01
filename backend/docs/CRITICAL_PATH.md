# Critical Path Analysis

**Date**: 2025-11-30
**Purpose**: Identify the minimum components that MUST work for core functionality

---

## Executive Summary

The critical path has **6 mandatory stages**. If any stage fails, the system cannot function:

```
USER REQUEST → TICKET → TASK → AGENT → LLM → RESULT
```

**Estimated minimum viable services**: 12 out of 64+ total services

---

## Critical Path Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CRITICAL EXECUTION PATH                            │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────┐
    │   USER   │
    └────┬─────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────────────────────────────────┐
│  1. API LAYER   │────▶│ FastAPI routes: /tickets, /tasks, /agents       │
│    (Entry)      │     │ Auth middleware (JWT/API key validation)         │
└────────┬────────┘     └──────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────────────────────────────────┐
│  2. TICKET      │────▶│ TicketWorkflowOrchestrator                       │
│    CREATION     │     │  └─ Creates ticket in DB                         │
│                 │     │  └─ Sets phase_id (PHASE_REQUIREMENTS)           │
│                 │     │  └─ (Optional) ApprovalService gate              │
└────────┬────────┘     └──────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────────────────────────────────┐
│  3. TASK        │────▶│ TaskQueueService                                 │
│    CREATION     │     │  └─ Creates initial task for ticket              │
│                 │     │  └─ Sets priority, phase, dependencies           │
│                 │     │  └─ Publishes TASK_CREATED event                 │
└────────┬────────┘     └──────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────────────────────────────────┐
│  4. ORCHESTRATOR│────▶│ orchestrator_loop() in api/main.py               │
│    ASSIGNMENT   │     │  └─ Polls TaskQueueService for pending tasks     │
│                 │     │  └─ Finds IDLE agent via AgentRegistryService    │
│                 │     │  └─ Assigns task to agent                        │
│                 │     │  └─ Publishes TASK_ASSIGNED event                │
└────────┬────────┘     └──────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────────────────────────────────┐
│  5. AGENT       │────▶│ AgentExecutor                                    │
│    EXECUTION    │     │  └─ Loads phase context (PHASE_REQUIREMENTS)     │
│                 │     │  └─ Creates OpenHands Agent with tools           │
│                 │     │  └─ Opens Conversation in workspace              │
│                 │     │  └─ Sends task prompt to LLM                     │
│                 │     │  └─ Executes tool calls (bash, file, tasks)      │
└────────┬────────┘     └──────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────────────────────────────────┐
│  6. LLM         │────▶│ LLM (via z.ai or Fireworks)                      │
│    INFERENCE    │     │  └─ Model: openai/glm-4.6 (main agents)          │
│                 │     │  └─ Model: kimi-k2-thinking (diagnostics)        │
│                 │     │  └─ Returns tool calls or text response          │
└────────┬────────┘     └──────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────────────────────────────────┐
│  7. RESULT      │────▶│ ResultSubmissionService                          │
│    SUBMISSION   │     │  └─ Agent submits work via give_result tool      │
│                 │     │  └─ ValidationOrchestrator spawns validator      │
│                 │     │  └─ Task marked completed or needs_work          │
└─────────────────┘     └──────────────────────────────────────────────────┘
```

---

## Mandatory Services (Critical Path)

These 12 services MUST work for the system to function:

| # | Service | File | Why Critical |
|---|---------|------|--------------|
| 1 | **DatabaseService** | `services/database.py` | All state persistence |
| 2 | **EventBusService** | `services/event_bus.py` | All service coordination |
| 3 | **TicketWorkflowOrchestrator** | `services/ticket_workflow.py` | Creates/manages tickets |
| 4 | **TaskQueueService** | `services/task_queue.py` | Creates/prioritizes tasks |
| 5 | **AgentRegistryService** | `services/agent_registry.py` | Registers/finds agents |
| 6 | **AgentStatusManager** | `services/agent_status_manager.py` | Agent state machine |
| 7 | **AgentExecutor** | `services/agent_executor.py` | Runs OpenHands agent |
| 8 | **LLMSettings** | `config.py` | LLM configuration |
| 9 | **PhaseGateService** | `services/phase_gate.py` | Phase transition rules |
| 10 | **ResultSubmissionService** | `services/result_submission.py` | Result handling |
| 11 | **ValidationOrchestrator** | `services/validation_orchestrator.py` | Quality gate |
| 12 | **AuthService** | `services/auth_service.py` | Access control |

---

## Service Dependency Graph

```
                    ┌─────────────────┐
                    │ DatabaseService │ ◀──────────────────────────┐
                    └────────┬────────┘                            │
                             │                                     │
              ┌──────────────┼──────────────┐                      │
              ▼              ▼              ▼                      │
     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
     │ EventBus    │  │ TaskQueue   │  │ AgentReg.   │            │
     └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
            │                │                │                    │
            │                ▼                ▼                    │
            │         ┌─────────────────────────────┐              │
            │         │    TicketWorkflowOrch.      │──────────────┤
            │         └──────────────┬──────────────┘              │
            │                        │                             │
            ▼                        ▼                             │
     ┌─────────────┐         ┌─────────────────┐                   │
     │ orchestrator│◀────────│   PhaseGate     │                   │
     │    _loop    │         └─────────────────┘                   │
     └──────┬──────┘                                               │
            │                                                      │
            ▼                                                      │
     ┌─────────────────┐                                           │
     │  AgentExecutor  │───▶ OpenHands SDK ───▶ LLM API           │
     └────────┬────────┘                                           │
              │                                                    │
              ▼                                                    │
     ┌─────────────────────┐                                       │
     │ ResultSubmission    │───────────────────────────────────────┘
     └────────┬────────────┘
              │
              ▼
     ┌─────────────────────┐
     │ ValidationOrch.     │
     └─────────────────────┘
```

---

## What Happens at Each Stage

### Stage 1: API Layer
```python
# POST /api/tickets
@router.post("/")
async def create_ticket(ticket_data: TicketCreate):
    # Auth check happens in middleware
    ticket = ticket_workflow.create_ticket(ticket_data)
    return ticket
```

### Stage 2: Ticket Creation
```python
# TicketWorkflowOrchestrator.create_ticket()
ticket = Ticket(
    title=data.title,
    description=data.description,
    phase_id="PHASE_REQUIREMENTS",  # Start here
    status=TicketStatus.BACKLOG.value,
)
session.add(ticket)
# Optional: ApprovalService.create_ticket_with_approval()
```

### Stage 3: Task Creation
```python
# TaskQueueService.enqueue_task()
task = Task(
    ticket_id=ticket_id,
    phase_id="PHASE_REQUIREMENTS",
    description="Analyze requirements and create implementation plan",
    priority=priority,
    status="pending",
)
session.add(task)
event_bus.publish(SystemEvent("TASK_CREATED", ...))
```

### Stage 4: Orchestrator Assignment
```python
# orchestrator_loop() in api/main.py
while True:
    available_agent = session.query(Agent).filter(
        Agent.status == AgentStatus.IDLE.value
    ).first()
    
    task = queue.get_next_task(phase_id, agent_capabilities)
    queue.assign_task(task.id, agent.id)
    
    event_bus.publish(SystemEvent("TASK_ASSIGNED", ...))
```

### Stage 5: Agent Execution
```python
# AgentExecutor.execute_task()
llm = LLM(model=settings.model, api_key=settings.api_key)
agent = Agent(llm=llm, tools=[...], ...)

conversation = Conversation(
    agent=agent,
    workspace=workspace_dir,
    prompt=task_prompt,
)
conversation.run()
```

### Stage 6: LLM Inference
```
Agent → LLM API (z.ai or Fireworks)
  Request: {messages: [...], tools: [...]}
  Response: {tool_calls: [...]} or {content: "..."}
```

### Stage 7: Result Submission
```python
# Agent calls give_result tool
result_service.submit_result(task_id, result_data)

# Triggers validation
validation_orchestrator.transition_to_under_review(task_id)
# Spawns validator agent
```

---

## Failure Points

| Stage | Failure Mode | System Impact |
|-------|--------------|---------------|
| 1 | Database down | **FATAL** - Nothing works |
| 2 | Ticket creation fails | **FATAL** - No work enters system |
| 3 | Task queue fails | **BLOCKED** - No work assigned |
| 4 | No idle agents | **STALLED** - Work waits indefinitely |
| 5 | LLM API down | **FATAL** - Agents can't think |
| 6 | LLM returns error | **RETRY** - Task marked failed |
| 7 | Validation fails | **LOOP** - Task returns to needs_work |

---

## Critical Environment Variables

Without these, the system won't start:

```bash
# Database (REQUIRED)
DATABASE_URL=postgresql+psycopg://...

# LLM - Main Agents (REQUIRED)
LLM_API_KEY=<z.ai-key>
LLM_MODEL=openai/glm-4.6
LLM_BASE_URL=https://api.z.ai/api/coding/paas/v4

# LLM - Diagnostics (REQUIRED for self-healing)
LLM_FIREWORKS_API_KEY=<fireworks-key>

# Auth (REQUIRED for multi-tenant)
AUTH_SECRET_KEY=<random-32-bytes>
```

---

## Critical Path Tests

These tests MUST pass before any deployment:

```bash
# 1. Database connectivity
pytest tests/test_e2e_database.py -v

# 2. LLM connectivity
pytest tests/test_llm_service_simple.py -v

# 3. Ticket → Task flow
pytest tests/test_e2e_ticket_lifecycle.py -v

# 4. Agent execution
pytest tests/test_e2e_agent_executor.py -v

# 5. Full workflow
pytest tests/test_e2e_full_workflow.py::test_ticket_to_completion -v
```

---

## Non-Critical (Can Fail Gracefully)

These services can fail without stopping core functionality:

| Service | Impact if Down |
|---------|----------------|
| ACE Memory | No learning, but execution works |
| GitHub Integration | No commit linking |
| Alerting | No notifications |
| Cost Tracking | No cost visibility |
| Watchdog | No meta-monitoring |
| Dependency Graph | No visualization |

---

## Summary: What MUST Work

1. **PostgreSQL** - Running and accessible
2. **LLM API** - At least one provider responding
3. **EventBus** - In-memory or Redis
4. **orchestrator_loop** - Background task running
5. **At least 1 Agent** - Registered and IDLE
6. **Workspace** - Writable directory

**Minimum viable system**: Database + 1 LLM + 1 Agent + Workspace = Working autonomous pipeline

---

## Vertical Slice Strategy

### Philosophy

> "Get the circuit closed first, then expand vertically."

Instead of testing 394 things at once, verify **one complete loop** works:

```
Ticket → Task → Agent → LLM → Result → Validation → Done
```

Once this circuit is proven, add features incrementally and test them in isolation.

---

### The Minimal Circuit

**Goal**: Prove a ticket can go from creation to completion autonomously.

```
┌─────────────────────────────────────────────────────────────────┐
│                    MINIMAL VERTICAL SLICE                       │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────┐
  │  Create  │  POST /api/tickets {title: "Add hello.txt"}
  │  Ticket  │
  └────┬─────┘
       │
       ▼
  ┌──────────┐
  │  Task    │  Auto-created with phase_id=PHASE_IMPLEMENTATION
  │  Queued  │  Status: pending
  └────┬─────┘
       │
       ▼
  ┌──────────┐
  │  Agent   │  orchestrator_loop assigns to IDLE agent
  │  Assigned│  Status: assigned → running
  └────┬─────┘
       │
       ▼
  ┌──────────┐
  │  LLM     │  Agent sends prompt, gets tool calls
  │  Thinks  │  Creates hello.txt in workspace
  └────┬─────┘
       │
       ▼
  ┌──────────┐
  │  Result  │  Agent calls give_result tool
  │  Submitted│ Task status: under_review
  └────┬─────┘
       │
       ▼
  ┌──────────┐
  │  Validate│  (Optional) Validator agent checks work
  │  Pass    │  Task status: completed
  └────┬─────┘
       │
       ▼
  ┌──────────┐
  │  DONE    │  Ticket status: done
  │  ✓       │  File exists in workspace
  └──────────┘
```

---

### Circuit Verification Script

```bash
#!/bin/bash
# verify_circuit.sh - Prove the minimal loop works

set -e
cd /Users/kevinhill/Coding/Experiments/senior-sandbox/senior_sandbox/backend

echo "=== CIRCUIT VERIFICATION ==="
echo ""

# 1. Check database
echo "[1/6] Database connection..."
python -c "from omoi_os.services.database import DatabaseService; db = DatabaseService(); print('✓ DB connected')" || exit 1

# 2. Check LLM
echo "[2/6] LLM connectivity..."
uv run python tests/test_llm_service_simple.py || exit 1

# 3. Check agent can be registered
echo "[3/6] Agent registration..."
python -c "
from omoi_os.services.database import DatabaseService
from omoi_os.services.agent_registry import AgentRegistryService
db = DatabaseService()
reg = AgentRegistryService(db)
print('✓ Agent registry works')
" || exit 1

# 4. Check ticket creation
echo "[4/6] Ticket creation..."
python -c "
from omoi_os.services.database import DatabaseService
from omoi_os.services.ticket_workflow import TicketWorkflowOrchestrator
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.phase_gate import PhaseGateService
db = DatabaseService()
queue = TaskQueueService(db)
phase = PhaseGateService(db)
workflow = TicketWorkflowOrchestrator(db, queue, phase)
print('✓ Ticket workflow initialized')
" || exit 1

# 5. Check orchestrator loop can run
echo "[5/6] Orchestrator loop..."
python -c "
import asyncio
from omoi_os.api.main import orchestrator_loop
print('✓ Orchestrator loop importable')
" || exit 1

# 6. Check agent executor
echo "[6/6] Agent executor..."
python -c "
from omoi_os.services.agent_executor import AgentExecutor
print('✓ AgentExecutor importable')
" || exit 1

echo ""
echo "=== CIRCUIT VERIFIED ==="
echo "All critical path components are functional."
echo "Ready for vertical expansion."
```

---

### Vertical Expansion Order

Once the circuit works, add features in this order:

| Phase | Feature | Test First |
|-------|---------|------------|
| V1 | Basic circuit (above) | Manual verification |
| V2 | Multi-phase transitions | `test_e2e_phases.py` |
| V3 | Validation loop | `test_e2e_validation.py` |
| V4 | Discovery/branching | `test_e2e_discovery.py` |
| V5 | Diagnostic self-healing | `test_e2e_diagnostic_spawn.py` |
| V6 | Multi-agent coordination | `test_e2e_collaboration.py` |
| V7 | Cost tracking | `test_e2e_cost_tracking.py` |
| V8 | ACE memory learning | `test_e2e_ace_workflow.py` |

**Rule**: Don't move to V(n+1) until V(n) tests pass.

---

### What You Can Skip Initially

| Feature | Skip Until... |
|---------|---------------|
| GitHub integration | You need commit linking |
| Alerting | You need notifications |
| Watchdog | You have multiple monitors |
| Daytona sandbox | You need cloud isolation |
| MCP server | You need external tool access |
| Approval workflow | You need human-in-loop |

---

### Testing Strategy: Build Vertically

```
         V8: ACE Memory
            │
         V7: Cost Tracking
            │
         V6: Multi-Agent
            │
         V5: Diagnostics
            │
         V4: Discovery
            │
         V3: Validation
            │
         V2: Phases
            │
  ┌─────────────────────┐
  │   V1: BASIC CIRCUIT │  ← YOU ARE HERE
  │   Ticket→Task→Done  │
  └─────────────────────┘
```

Each vertical layer adds capability without breaking the layer below.

---

## Frontend Readiness Checklist

### API Surface: 176 Routes Across 23 Routers

| Router | Prefix | Critical Path? |
|--------|--------|----------------|
| `tickets` | `/api/v1/tickets` | **YES** |
| `tasks` | `/api/v1/tasks` | **YES** |
| `agents` | `/api/v1/agents` | **YES** |
| `auth` | `/api/v1/auth` | **YES** |
| `phases` | `/api/v1/phases` | **YES** |
| `results` | `/api/v1/results` | **YES** |
| `validation` | `/api/validation` | **YES** |
| `board` | `/api/v1/board` | Kanban UI |
| `graph` | `/api/v1/graph` | Visualization |
| `collaboration` | `/api/v1/collaboration` | Multi-agent |
| `diagnostic` | `/api/v1/diagnostic` | Self-healing |
| `guardian` | `/api/v1/guardian` | Monitoring |
| `costs` | `/api/v1/costs` | Billing |
| `alerts` | `/api/v1/alerts` | Notifications |
| `events` | `/api/v1/events` | SSE/WebSocket |
| `memory` | `/api/v1/memory` | ACE system |
| `quality` | `/api/v1/quality` | Predictions |
| `commits` | `/api/v1/commits` | GitHub |
| `github` | `/api/v1/github` | Webhooks |
| `projects` | `/api/v1/projects` | Multi-tenant |
| `watchdog` | `/api/v1/watchdog` | Meta-monitor |
| `mcp` | `/mcp` | External tools |
| `monitoring` | `/api/v1/monitoring` | Health |

### Quick Server Test

```bash
# Start the server
cd /Users/kevinhill/Coding/Experiments/senior-sandbox/senior_sandbox/backend
uv run uvicorn omoi_os.api.main:app --reload --port 8000

# In another terminal, test critical endpoints:
curl http://localhost:8000/api/v1/tickets        # Should return []
curl http://localhost:8000/api/v1/agents         # Should return []
curl http://localhost:8000/docs                  # Swagger UI
```

### Critical Path API Flow (for frontend)

```
1. POST /api/v1/auth/login          → Get JWT token
2. POST /api/v1/tickets             → Create ticket
3. GET  /api/v1/tickets/{id}        → Watch status
4. GET  /api/v1/tasks?ticket_id=X   → See tasks
5. GET  /api/v1/board/view          → Kanban board
6. GET  /api/v1/graph/{ticket_id}   → Dependency graph
```

### What Frontend Needs From Backend

| Frontend Feature | Backend Endpoint | Status |
|------------------|------------------|--------|
| Login/Register | `/api/v1/auth/*` | ✓ Ready |
| Create ticket | `POST /api/v1/tickets` | ✓ Ready |
| View tickets | `GET /api/v1/tickets` | ✓ Ready |
| Kanban board | `GET /api/v1/board/view` | ✓ Ready |
| Task list | `GET /api/v1/tasks` | ✓ Ready |
| Agent status | `GET /api/v1/agents` | ✓ Ready |
| Dep graph | `GET /api/v1/graph/*` | ✓ Ready |
| Real-time events | `GET /api/v1/events/stream` | ✓ Ready (SSE) |
| Cost dashboard | `GET /api/v1/costs/*` | ✓ Ready |
