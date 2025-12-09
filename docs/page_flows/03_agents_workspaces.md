# 3 Agents Workspaces

**Part of**: [Page Flow Documentation](./README.md)

---
### Flow 4: Agent Management & Spawning

```
┌─────────────────────────────────────────────────────────────┐
│          PAGE: /agents (Agent List)                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Agents                                               │   │
│  │                                                       │   │
│  │  [Spawn Agent] [View Health]                         │   │
│  │                                                       │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Agent: worker-1                                │  │   │
│  │  │ Status: 🟢 Active                               │  │   │
│  │  │ Phase: IMPLEMENTATION                          │  │   │
│  │  │ Current Task: "Implement JWT"                  │  │   │
│  │  │ Heartbeat: 5s ago ✓                            │  │   │
│  │  │ [View Details] [Intervene]                     │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Agent: worker-2                                │  │   │
│  │  │ Status: 🟡 Idle                                 │  │   │
│  │  │ Phase: INTEGRATION                             │  │   │
│  │  │ Current Task: None                             │  │   │
│  │  │ Heartbeat: 2s ago ✓                            │  │   │
│  │  │ [View Details] [Assign Task]                   │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Agent: worker-3                                │  │   │
│  │  │ Status: 🔴 Stuck                                │  │   │
│  │  │ Phase: IMPLEMENTATION                          │  │   │
│  │  │ Current Task: "Setup OAuth2"                   │  │   │
│  │  │ Heartbeat: 95s ago ⚠️                          │  │   │
│  │  │ Guardian: Intervention sent 30s ago            │  │   │
│  │  │ [View Details] [Force Intervene]              │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Click "Spawn Agent"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│        PAGE: /agents/spawn (Spawn Agent Modal)             │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Spawn New Agent                                     │   │
│  │                                                      │   │
│  │  Agent Type:                                        │   │
│  │  ○ Worker (Execution)                               │   │
│  │  ○ Planner (Planning)                               │   │
│  │  ○ Validator (Testing)                             │   │
│  │                                                      │   │
│  │  Phase Assignment:                                  │   │
│  │  [Select Phase ▼]                                    │   │
│  │  • PHASE_INITIAL                                     │   │
│  │  • PHASE_IMPLEMENTATION                              │   │
│  │  • PHASE_INTEGRATION                                 │   │
│  │  • PHASE_REFACTORING                                 │   │
│  │                                                      │   │
│  │  Capabilities:                                      │   │
│  │  ☑ File Editing                                     │   │
│  │  ☑ Terminal Access                                  │   │
│  │  ☑ Code Generation                                  │   │
│  │  ☐ Testing                                          │   │
│  │                                                      │   │
│  │  Project:                                           │   │
│  │  [Select Project ▼]                                 │   │
│  │                                                      │   │
│  │  [Cancel] [Spawn Agent]                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Click "Spawn Agent"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│      PAGE: /agents/:agentId (Agent Detail View)            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Agent: worker-1                                      │   │
│  │  Status: 🟢 Active                                    │   │
│  │  Phase: IMPLEMENTATION                                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tabs: [Overview] [Trajectory] [Tasks] [Logs]       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Overview Tab                                        │   │
│  │                                                      │   │
│  │  Current Task: "Implement JWT"                      │   │
│  │  Progress: 60%                                      │   │
│  │  Heartbeat: 5s ago ✓                                │   │
│  │                                                      │   │
│  │  Recent Activity:                                   │   │
│  │  • Started task "Implement JWT" 10m ago             │   │
│  │  • Committed changes 5m ago                         │   │
│  │  • Guardian intervention 2m ago                      │   │
│  │                                                      │   │
│  │  [View Trajectory] [Send Intervention]             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Trajectory Tab                                      │   │
│  │                                                      │   │
│  │  Alignment Score: 78%                               │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Timeline:                                     │  │   │
│  │  │                                              │  │   │
│  │  │  [10m] Started task                          │  │   │
│  │  │  [8m]  Analyzing requirements                │  │   │
│  │  │  [6m]  Writing code                          │  │   │
│  │  │  [4m]  Guardian: "Focus on core flow"       │  │   │
│  │  │  [2m]  Adjusted approach                     │  │   │
│  │  │  [now] Testing implementation               │  │   │
│  │  │                                              │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  [View Full Trajectory]                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## API Integration

### Backend Endpoints

All agent endpoints are prefixed with `/api/v1/`.

---

### GET /api/v1/agents
**Description:** List all registered agents

**Response (200):**
```json
[
  {
    "agent_id": "uuid",
    "agent_type": "worker",
    "phase_id": "PHASE_IMPLEMENTATION",
    "status": "idle",
    "capabilities": ["python", "analysis"],
    "capacity": 2,
    "health_status": "healthy",
    "tags": ["python"],
    "last_heartbeat": "2025-01-15T10:00:00Z",
    "created_at": "2025-01-15T09:00:00Z"
  }
]
```

---

### POST /api/v1/agents/register
**Description:** Register a new agent

**Request Body:**
```json
{
  "agent_type": "worker",
  "phase_id": "PHASE_IMPLEMENTATION",
  "capabilities": ["python", "javascript", "analysis"],
  "capacity": 2,
  "status": "idle",
  "tags": ["frontend", "backend"]
}
```

**Response (201):**
```json
{
  "agent_id": "uuid",
  "agent_type": "worker",
  "phase_id": "PHASE_IMPLEMENTATION",
  "status": "idle",
  "capabilities": ["python", "javascript", "analysis"],
  "capacity": 2,
  "health_status": "healthy",
  "tags": ["frontend", "backend"],
  "last_heartbeat": null,
  "created_at": "2025-01-15T10:00:00Z"
}
```

---

### GET /api/v1/agents/{agent_id}
**Description:** Get specific agent details

**Path Params:** `agent_id` (string)

---

### PATCH /api/v1/agents/{agent_id}
**Description:** Update agent properties

**Request Body (all fields optional):**
```json
{
  "capabilities": ["python", "go"],
  "capacity": 3,
  "status": "busy",
  "tags": ["high-priority"],
  "health_status": "degraded"
}
```

---

### GET /api/v1/agents/health
**Description:** Get health status for all agents

**Query Params:**
- `timeout_seconds` (optional): Custom timeout for stale detection (default: 90)

**Response (200):**
```json
[
  {
    "agent_id": "uuid",
    "health_status": "healthy",
    "last_heartbeat": "2025-01-15T10:00:00Z",
    "seconds_since_heartbeat": 15,
    "is_stale": false
  }
]
```

---

### GET /api/v1/agents/{agent_id}/health
**Description:** Get health for specific agent

---

### GET /api/v1/agents/statistics
**Description:** Get comprehensive agent statistics

**Response (200):**
```json
{
  "total_agents": 10,
  "by_status": { "idle": 5, "busy": 3, "maintenance": 2 },
  "by_type": { "worker": 8, "monitor": 2 },
  "by_health": { "healthy": 8, "degraded": 1, "stale": 1 }
}
```

---

### POST /api/v1/agents/{agent_id}/heartbeat
**Description:** Send heartbeat from agent

**Request Body:**
```json
{
  "agent_id": "uuid",
  "sequence_number": 42,
  "health_metrics": {
    "cpu_percent": 45.5,
    "memory_percent": 60.2,
    "disk_percent": 35.0
  },
  "current_task_id": "task-uuid",
  "checksum": "sha256-hash"
}
```

**Response (200):**
```json
{
  "received": true,
  "acknowledged_sequence": 42,
  "server_timestamp": "2025-01-15T10:00:00Z",
  "message": "Heartbeat acknowledged"
}
```

---

### GET /api/v1/agents/search
**Description:** Search for agents by capabilities

**Query Params:**
- `capabilities`: List of required capabilities
- `phase_id` (optional): Limit to specific phase
- `agent_type` (optional): Filter by agent type
- `limit` (default: 5, max: 20)

**Response (200):**
```json
[
  {
    "agent": { "agent_id": "uuid", "...": "..." },
    "match_score": 0.85,
    "matched_capabilities": ["python", "analysis"]
  }
]
```

---

### GET /api/v1/agents/stale
**Description:** Get list of stale agents

---

### POST /api/v1/agents/cleanup-stale
**Description:** Mark stale agents for cleanup

**Query Params:**
- `timeout_seconds` (optional): Custom timeout
- `mark_as` (default: "timeout"): Status to mark stale agents

---

**Next**: See [README.md](./README.md) for complete documentation index.
