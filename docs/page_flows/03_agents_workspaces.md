# 3 Sandboxes & Agent Execution

**Part of**: [Page Flow Documentation](./README.md)

**Note**: The UI has shifted from an "agent-based" approach to a "sandbox-based" approach. Users interact with sandboxes (isolated execution environments) rather than directly spawning agents. Sandboxes are created automatically when tasks are launched from the Command Center.

---

## Architecture Overview

The sandbox-based workflow follows this pattern:

```
Command Center (/command)
        │
        │ User describes what they want to build
        ▼
   Create Ticket (API)
        │
        │ Backend orchestrator receives ticket
        ▼
   Spawn Sandbox (Automatic)
        │
        │ Agent runs in isolated sandbox
        ▼
   Sandbox Detail View (/sandbox/:sandboxId)
        │
        │ Real-time events stream via WebSocket
        ▼
   User monitors progress & can send messages
```

---

## UI Components

### IconRail Navigation

The vertical icon navigation includes these sections:

| Icon | Section | Route | Description |
|------|---------|-------|-------------|
| Terminal | Command | `/command` | Primary landing - launch new tasks |
| FolderGit2 | Projects | `/projects` | Project management |
| Workflow | Phases | `/phases` | Phase management |
| Box | Sandboxes | `/sandboxes` | View all sandboxes |
| BarChart3 | Analytics | `/analytics` | Usage analytics |
| Building2 | Organizations | `/organizations` | Organization settings |
| Settings | Settings | `/settings` | User settings |

### ContextualPanel (Sidebar)

The contextual sidebar changes based on the current route:

| Route | Panel | Content |
|-------|-------|---------|
| `/command` | TasksPanel | Running/Pending/Completed/Failed tasks grouped by status |
| `/sandbox/*` | TasksPanel | Same task list with selected sandbox highlighted |
| `/projects` | ProjectsPanel | Project list with favorites/active sections |
| `/phases` | PhasesPanel | Phase configuration |
| `/board/*` | ProjectsPanel | Project context for board view |
| `/health` | HealthPanel | System health metrics |
| `/graph/*` | GraphFiltersPanel | Graph filter options |

---

### Flow 4: Sandbox-Based Execution (Current Implementation)

```
┌─────────────────────────────────────────────────────────────┐
│          PAGE: /command (Command Center)                     │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ IconRail │ ContextualPanel (TasksPanel)  │ Main Content │ │
│  ├──────────┼───────────────────────────────┼──────────────┤ │
│  │          │                               │              │ │
│  │  [Logo]  │ [Search tasks...]             │ "What would  │ │
│  │          │ [Filter] [Sort]               │  you like    │ │
│  │ Terminal │ [+ New Task]                  │  to build?"  │ │
│  │ (active) │                               │              │ │
│  │          │ RUNNING                       │ ┌──────────┐ │ │
│  │ Projects │ ┌────────────────────────┐   │ │[Prompt   ]│ │ │
│  │          │ │⟳ Fix authentication    │   │ │[input... ]│ │ │
│  │ Phases   │ │  running • 5m          │   │ └──────────┘ │ │
│  │          │ └────────────────────────┘   │              │ │
│  │ Sandbox  │                               │ [Model ▼]   │ │
│  │          │ COMPLETED                     │              │ │
│  │ Analytics│ ┌────────────────────────┐   │ ┌──────────┐ │ │
│  │          │ │✓ Add user dashboard    │   │ │📁 repo ▼ │ │ │
│  │ Orgs     │ │  completed • 1h        │   │ │⎇ main ▼  │ │ │
│  │          │ └────────────────────────┘   │ └──────────┘ │ │
│  │ Settings │                               │              │ │
│  │          │ FAILED                        │              │ │
│  │          │ ┌────────────────────────┐   │              │ │
│  │          │ │✗ DB migration          │   │              │ │
│  │          │ │  failed • 2h           │   │              │ │
│  │          │ └────────────────────────┘   │              │ │
│  └──────────┴───────────────────────────────┴──────────────┘ │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ User types prompt and submits
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│          PAGE: /command (Launching State)                    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                                                      │   │
│  │  ┌─────────────────────────────────────────────────┐│   │
│  │  │ ⟳ Creating task...                              ││   │
│  │  │ ⟳ Launching sandbox environment...               ││   │
│  │  └─────────────────────────────────────────────────┘│   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Steps:                                                     │
│  1. Create ticket via API                                   │
│  2. Wait for SANDBOX_SPAWNED event via WebSocket           │
│  3. Redirect to /sandbox/:sandboxId                        │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Sandbox created, redirect triggered
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│      PAGE: /sandbox/:sandboxId (Sandbox Detail View)         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ IconRail │ ContextualPanel (TasksPanel)  │ Main Content │ │
│  ├──────────┼───────────────────────────────┼──────────────┤ │
│  │          │                               │              │ │
│  │  [Logo]  │ [Search tasks...]             │ ← Back to    │ │
│  │          │                               │   Command    │ │
│  │ Terminal │ RUNNING                       │              │ │
│  │          │ ┌────────────────────────┐   │ 🤖 Task Name │ │
│  │ Projects │ │⟳ Fix authentication    │←──│ [Running]    │ │
│  │          │ │  selected • running    │   │              │ │
│  │ Phases   │ └────────────────────────┘   │ sandbox-id   │ │
│  │          │                               │              │ │
│  │ Sandbox  │ COMPLETED                     │ [🟢 Live]    │ │
│  │ (active) │ ...                           │ [Refresh]    │ │
│  │          │                               │              │ │
│  │ Analytics│                               │ [Events]     │ │
│  │          │                               │ [Details]    │ │
│  │ Orgs     │                               │              │ │
│  │          │                               │ ┌──────────┐ │ │
│  │ Settings │                               │ │ agent.   │ │ │
│  │          │                               │ │ thinking │ │ │
│  │          │                               │ │ ...      │ │ │
│  │          │                               │ │          │ │ │
│  │          │                               │ │ agent.   │ │ │
│  │          │                               │ │ tool_use │ │ │
│  │          │                               │ │ Read()   │ │ │
│  │          │                               │ └──────────┘ │ │
│  │          │                               │              │ │
│  │          │                               │ ┌──────────┐ │ │
│  │          │                               │ │[Message ]│ │ │
│  │          │                               │ │[to agent]│ │ │
│  │          │                               │ └──────────┘ │ │
│  └──────────┴───────────────────────────────┴──────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### Flow 5: Sandbox Detail View Features

```
┌─────────────────────────────────────────────────────────────┐
│      PAGE: /sandbox/:sandboxId - Events Tab                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ← Back to Command                                   │   │
│  │                                                      │   │
│  │  🤖 Build Authentication System                      │   │
│  │  [Running] sandbox-abc123                           │   │
│  │                                   [🟢 Live] [⟳]     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  [Events]  [Details]                                 │   │
│  │  ^^^^^^^^ (active)                                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Events Stream (real-time via WebSocket)            │   │
│  │                                                      │   │
│  │  ┌────────────────────────────────────────────────┐│   │
│  │  │ 💭 agent.thinking                              ││   │
│  │  │ "I'll analyze the codebase structure..."       ││   │
│  │  └────────────────────────────────────────────────┘│   │
│  │                                                      │   │
│  │  ┌────────────────────────────────────────────────┐│   │
│  │  │ 🔧 agent.tool_completed - Read                 ││   │
│  │  │ src/auth/login.ts                             ││   │
│  │  │ ▼ Show content                                 ││   │
│  │  └────────────────────────────────────────────────┘│   │
│  │                                                      │   │
│  │  ┌────────────────────────────────────────────────┐│   │
│  │  │ ✏️ agent.tool_completed - Write                ││   │
│  │  │ src/auth/jwt.ts (new file)                    ││   │
│  │  │ ▼ Show diff                                    ││   │
│  │  └────────────────────────────────────────────────┘│   │
│  │                                                      │   │
│  │  ┌────────────────────────────────────────────────┐│   │
│  │  │ 💻 agent.tool_completed - Bash                 ││   │
│  │  │ $ npm install jsonwebtoken                     ││   │
│  │  │ ▼ Show output                                  ││   │
│  │  └────────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  [Send a message to the agent...]                   │   │
│  │  [____________________________________] [Send]      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────┐
│      PAGE: /sandbox/:sandboxId - Details Tab                 │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  [Events]  [Details]                                 │   │
│  │            ^^^^^^^^^ (active)                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Task Information                                   │   │
│  │                                                      │   │
│  │  Task ID:     task-xyz789                           │   │
│  │  Sandbox ID:  sandbox-abc123                        │   │
│  │  Status:      [Running]                             │   │
│  │  Priority:    Medium                                │   │
│  │  Task Type:   implementation                        │   │
│  │  Phase:       PHASE_IMPLEMENTATION                  │   │
│  │  Created:     Dec 30, 2025 10:30 AM                │   │
│  │  Started:     Dec 30, 2025 10:31 AM                │   │
│  │                                                      │   │
│  │  Description:                                       │   │
│  │  Build an authentication system with OAuth2...     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Event Summary                                      │   │
│  │                                                      │   │
│  │  Total Events:  47                                  │   │
│  │  Tool Uses:     23                                  │   │
│  │  File Edits:    8                                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## API Integration

### Backend Endpoints (Sandbox-Based)

#### Task Creation (via Command Center)
```
POST /api/v1/tickets
```
Creates a ticket which triggers the orchestrator to spawn a sandbox.

**Request Body:**
```json
{
  "title": "Build authentication system",
  "description": "Full prompt text...",
  "phase_id": "PHASE_IMPLEMENTATION",
  "priority": "MEDIUM",
  "check_duplicates": false,
  "force_create": true
}
```

**Response (201):**
```json
{
  "id": "ticket-uuid",
  "title": "Build authentication system",
  "status": "OPEN",
  "phase_id": "PHASE_IMPLEMENTATION"
}
```

---

#### WebSocket Events (Real-Time Updates)

The frontend subscribes to events via WebSocket at `/api/v1/events/stream`.

**Sandbox Events:**
- `SANDBOX_CREATED` / `SANDBOX_SPAWNED` / `sandbox.spawned` - Sandbox is ready
- `TASK_STARTED` - Task execution began
- `TASK_SANDBOX_ASSIGNED` - Sandbox assigned to task

**Agent Events (streamed to sandbox detail page):**
- `agent.thinking` - Agent reasoning
- `agent.tool_use` - Tool invocation started
- `agent.tool_completed` - Tool finished with result
- `agent.file_edited` - File modification
- `agent.message` - Agent text output

---

#### GET /api/v1/tasks
**Description:** List tasks (used by TasksPanel)

**Query Params:**
- `limit` (optional): Max tasks to return
- `status` (optional): Filter by status

**Response (200):**
```json
[
  {
    "id": "task-uuid",
    "title": "Build authentication system",
    "task_type": "implementation",
    "status": "running",
    "sandbox_id": "sandbox-uuid",
    "ticket_id": "ticket-uuid",
    "created_at": "2025-12-30T10:30:00Z",
    "started_at": "2025-12-30T10:31:00Z"
  }
]
```

---

#### GET /api/v1/tasks/by-sandbox/:sandboxId
**Description:** Get task associated with a sandbox

**Response (200):**
```json
{
  "id": "task-uuid",
  "title": "Build authentication system",
  "description": "Full prompt...",
  "task_type": "implementation",
  "status": "running",
  "sandbox_id": "sandbox-uuid",
  "priority": "MEDIUM",
  "phase_id": "PHASE_IMPLEMENTATION",
  "created_at": "2025-12-30T10:30:00Z",
  "started_at": "2025-12-30T10:31:00Z"
}
```

---

#### GET /api/v1/sandboxes/:sandboxId/events
**Description:** Get historical events for a sandbox (WebSocket provides real-time)

**Response (200):**
```json
[
  {
    "id": "event-uuid",
    "sandbox_id": "sandbox-uuid",
    "event_type": "agent.thinking",
    "event_data": {
      "content": "I'll analyze the codebase..."
    },
    "created_at": "2025-12-30T10:31:05Z"
  }
]
```

---

#### POST /api/v1/sandboxes/:sandboxId/message
**Description:** Send a message to the agent in a sandbox

**Request Body:**
```json
{
  "content": "Can you also add password validation?"
}
```

**Response (200):**
```json
{
  "success": true,
  "message_id": "msg-uuid"
}
```

---

## Component Summary

### TasksPanel (`/components/panels/TasksPanel.tsx`)
- Displays tasks grouped by status (Running, Pending, Completed, Failed)
- Search/filter functionality
- Highlights selected sandbox when on `/sandbox/:sandboxId` route
- "New Task" button links to `/command`

### Command Page (`/app/(app)/command/page.tsx`)
- Primary prompt input for describing tasks
- Repository/branch selector
- Model selector
- Shows launch progress states
- Automatically redirects to sandbox when ready

### Sandbox Detail Page (`/app/(app)/sandbox/[sandboxId]/page.tsx`)
- Real-time event streaming via WebSocket
- Events tab: Shows agent activity (thinking, tool use, file edits)
- Details tab: Task metadata and event summary
- Message input: Send messages to agent
- Connection status indicator (Live/Disconnected)

---

**Next**: See [README.md](./README.md) for complete documentation index.
