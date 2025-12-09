# Diagnostic Reasoning

**Part of**: [Page Flow Documentation](./README.md)

---
### Flow 25: Diagnostic Reasoning View

```
┌─────────────────────────────────────────────────────────────┐
│    PAGE: /board/:projectId/:ticketId (Ticket Detail)        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Ticket: Infrastructure: Redis Cache Setup          │   │
│  │  Status: Backlog | Priority: Critical              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tabs: [Details] [Comments] [Blocking] [Reasoning] │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  [View Reasoning Chain] [View Graph]                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Click "View Reasoning Chain"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /diagnostic/ticket/33cb642c-ebb9-46d3-b021-...      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Diagnostic Reasoning View                          │   │
│  │  Ticket: Infrastructure: Redis Cache Setup          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tabs: [Timeline] [Graph] [Details]                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Timeline View                                       │   │
│  │                                                      │   │
│  │  Oct 30, 10:23 AM  Ticket Created                   │   │
│  │  └─ Reason: "Infrastructure needed for auth system" │   │
│  │  └─ Created by: Agent worker-1                      │   │
│  │                                                      │   │
│  │  Oct 30, 10:25 AM  Discovery Made                   │   │
│  │  └─ Type: bug                                       │   │
│  │  └─ Description: "Found missing Redis dependency"   │   │
│  │  └─ Source Task: task-000 (Phase 2 Implementation) │   │
│  │  └─ Evidence: import redis failed in src/auth/cache.py│ │
│  │                                                      │   │
│  │  Oct 30, 10:26 AM  Task Spawned                    │   │
│  │  └─ Task: task-001 "Setup Redis Infrastructure"    │   │
│  │  └─ Linked to this ticket                           │   │
│  │  └─ Link Reason: "Task addresses infrastructure    │   │
│  │                   requirement"                      │   │
│  │                                                      │   │
│  │  Oct 30, 10:28 AM  Blocking Relationship Added     │   │
│  │  └─ Ticket "Auth System" blocked by this ticket    │   │
│  │  └─ Reason: "Auth requires Redis cache to be       │   │
│  │              operational"                           │   │
│  │  └─ Dependency Type: infrastructure                 │   │
│  │  └─ Agent Reasoning: "Cannot proceed with auth     │   │
│  │                       until cache is ready"         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Discovery Details                                  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Discovery: Bug Found                        │  │   │
│  │  │                                              │  │   │
│  │  │ Source Task: task-000 - "Implement Auth     │  │   │
│  │  │              Cache"                          │  │   │
│  │  │ Type: bug                                    │  │   │
│  │  │ Discovered: Oct 30, 10:25 AM                │  │   │
│  │  │                                              │  │   │
│  │  │ Description:                                │  │   │
│  │  │ Found missing Redis dependency when          │  │   │
│  │  │ attempting to import redis module. The auth  │  │   │
│  │  │ cache implementation requires Redis to be    │  │   │
│  │  │ set up first.                                │  │   │
│  │  │                                              │  │   │
│  │  │ Evidence:                                   │  │   │
│  │  │ • File: src/auth/cache.py:12                │  │   │
│  │  │ • Error: ModuleNotFoundError: No module     │  │   │
│  │  │   named 'redis'                             │  │   │
│  │  │ • Code: import redis                        │  │   │
│  │  │                                              │  │   │
│  │  │ Spawned Tasks:                              │  │   │
│  │  │ • task-001: "Setup Redis Infrastructure"   │  │   │
│  │  │                                              │  │   │
│  │  │ [View Source Task] [View Spawned Tasks]     │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Blocking Relationships                             │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Ticket "Auth System" is blocked by          │  │   │
│  │  │ Ticket "Redis Cache Setup"                  │  │   │
│  │  │                                              │  │   │
│  │  │ Reason:                                     │  │   │
│  │  │ Auth system requires Redis cache to be      │  │   │
│  │  │ operational before authentication can be     │  │   │
│  │  │ implemented. The cache is used for session   │  │   │
│  │  │ storage and token validation.                │  │   │
│  │  │                                              │  │   │
│  │  │ Dependency Type: infrastructure              │  │   │
│  │  │ Required For: ["session_storage",            │  │   │
│  │  │                "token_validation"]           │  │   │
│  │  │                                              │  │   │
│  │  │ Agent Reasoning:                            │  │   │
│  │  │ "Cannot proceed with auth until cache is    │  │   │
│  │  │  ready. Auth endpoints depend on Redis for  │  │   │
│  │  │  session management and token caching."     │  │   │
│  │  │                                              │  │   │
│  │  │ Created: Oct 30, 10:28 AM                  │  │   │
│  │  │ By: Agent worker-1                          │  │   │
│  │  │                                              │  │   │
│  │  │ [View Blocking Ticket] [View Blocked Ticket]│  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Agent Memory & Decisions                           │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ decision - Oct 30, 10:26 AM                 │  │   │
│  │  │ Agent: worker-1                             │  │   │
│  │  │                                              │  │   │
│  │  │ Chose Redis over Memcached for pub/sub      │  │   │
│  │  │ support. Redis provides better integration  │  │   │
│  │  │ with Python and supports pub/sub patterns    │  │   │
│  │  │ needed for real-time updates.               │  │   │
│  │  │                                              │  │   │
│  │  │ Related Files: src/auth/cache.py            │  │   │
│  │  │ Tags: infrastructure, decision              │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## API Integration

### Backend Endpoints

Diagnostic endpoints are prefixed with `/api/v1/diagnostic/`.

---

### GET /api/v1/diagnostic/stuck-workflows
**Description:** List currently stuck workflows

**Response (200):**
```json
{
  "stuck_count": 2,
  "stuck_workflows": [
    {
      "workflow_id": "workflow-uuid",
      "ticket_id": "ticket-uuid",
      "total_tasks": 10,
      "done_tasks": 10,
      "failed_tasks": 0,
      "time_since_last_task_seconds": 300,
      "reason": "All tasks finished but no validated result"
    }
  ]
}
```

---

### GET /api/v1/diagnostic/runs
**Description:** Get diagnostic run history

**Query Params:**
- `limit` (default: 100)
- `workflow_id` (optional): Filter by workflow

**Response (200):**
```json
[
  {
    "run_id": "uuid",
    "workflow_id": "workflow-uuid",
    "diagnostic_agent_id": "diag-agent-uuid",
    "diagnostic_task_id": "task-uuid",
    "triggered_at": "2025-01-15T12:00:00Z",
    "total_tasks_at_trigger": 10,
    "done_tasks_at_trigger": 10,
    "failed_tasks_at_trigger": 0,
    "time_since_last_task_seconds": 300,
    "tasks_created_count": 2,
    "tasks_created_ids": { "task_ids": ["task-1", "task-2"] },
    "workflow_goal": "Complete implementation",
    "phases_analyzed": {},
    "agents_reviewed": {},
    "diagnosis": "Workflow missing result submission",
    "completed_at": "2025-01-15T12:05:00Z",
    "status": "completed",
    "created_at": "2025-01-15T12:00:00Z"
  }
]
```

---

### POST /api/v1/diagnostic/trigger/{workflow_id}
**Description:** Manually trigger diagnostic agent for a stuck workflow

**Path Params:** `workflow_id` (string)

**Response (200):**
```json
{
  "run_id": "uuid",
  "workflow_id": "workflow-uuid",
  "diagnostic_agent_id": null,
  "diagnostic_task_id": null,
  "triggered_at": "2025-01-15T12:00:00Z",
  "status": "pending"
}
```

---

### GET /api/v1/diagnostic/runs/{run_id}
**Description:** Get diagnostic run details

---

**Next**: See [README.md](./README.md) for complete documentation index.
