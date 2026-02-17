# Sandbox System

**Part of**: [Page Flow Documentation](./README.md)

---

## Overview

The Sandbox System is the core execution environment for OmoiOS. When a user submits a task from the Command Center, the system spawns an isolated sandbox with an AI agent. Users can monitor real-time events, send messages to the agent, preview running applications, and manage sandbox lifecycle.

---

## Flow 52: Sandbox List

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /sandboxes                                           │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Header                                                │ │
│  │  📦 Sandboxes              [Refresh] [+ New Sandbox]   │ │
│  │  42 sandboxes total                                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Filters                                               │ │
│  │  🔍 [Search sandboxes...]                              │ │
│  │                                                        │ │
│  │  [All] [Running] [Validating] [Awaiting] [Pending]     │ │
│  │  [Completed] [Failed]                                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ ▶ Running    │ │ ✓ Completed  │ │ ✗ Failed     │       │
│  │ sandbox_task │ │ sandbox_task │ │ sandbox_task │       │
│  │ "Add auth"  │ │ "Fix bug"   │ │ "Refactor"  │       │
│  │ abc123...   │ │ def456...   │ │ ghi789...   │       │
│  │ ──────────  │ │ ──────────  │ │ ──────────  │       │
│  │ Running 5m  │ │ Completed   │ │ Failed      │       │
│  └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Route
`/sandboxes`

### Purpose
List all sandbox tasks with filtering and search. Entry point for monitoring sandbox executions.

### User Actions
- **Search**: Filter sandboxes by title, task type, ID, or sandbox ID
- **Filter by status**: All, Running, Validating, Awaiting Validation, Pending, Completed, Failed
- **Navigate**: Click a sandbox card to open its detail view
- **Create new**: Click "New Sandbox" to go to Command Center
- **Refresh**: Manually refresh sandbox list
- **Mark as failed**: Right-click running/pending tasks to force-fail

### Components
- `SandboxesPage` — Main list page
- Status filter buttons with count badges
- Sandbox cards in responsive grid (2-3 columns)
- Dropdown menu for task actions (mark failed)

### API Endpoints
- `GET /api/v1/tasks?task_type=sandbox` — List sandbox tasks (via `useSandboxTasks` hook)
- `POST /api/v1/tasks/:id/fail` — Mark task as failed (via `useFailTask` hook)

### State Management
- `useSandboxTasks` (React Query) — Fetches sandbox task list
- `useFailTask` (React Query mutation) — Marks tasks as failed
- Local state for search query and status filter

---

## Flow 53: Sandbox Detail — Event Monitoring

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /sandbox/:sandboxId                                  │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ← Back to Command                                    │ │
│  │  🤖 Add Stripe payments           [Running]           │ │
│  │  sandbox_abc123def456                  🟢 Live [↻]    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Tabs: [Events] [Preview] [Details]                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Events Feed (real-time via WebSocket)                 │ │
│  │                                                        │ │
│  │  ↑ Scroll up for older events                          │ │
│  │                                                        │ │
│  │  ┌──────────────────────────────────────────────────┐ │ │
│  │  │ 🔧 agent.tool_completed — Write                  │ │ │
│  │  │ File: src/payments/stripe.ts                     │ │ │
│  │  │ +45 lines added                                  │ │ │
│  │  └──────────────────────────────────────────────────┘ │ │
│  │                                                        │ │
│  │  ┌──────────────────────────────────────────────────┐ │ │
│  │  │ 💬 agent.assistant_message                       │ │ │
│  │  │ "I've created the Stripe integration module..."  │ │ │
│  │  └──────────────────────────────────────────────────┘ │ │
│  │                                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  [Type a message to the agent...              ] [Send] │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Route
`/sandbox/[sandboxId]`

### Purpose
Real-time monitoring of a sandbox execution. Watch agent events as they happen, send messages to the agent, and preview running applications.

### User Actions
- **Watch events**: Real-time scrolling feed of agent actions (tool use, file edits, messages, errors)
- **Send messages**: Type and send messages to the running agent (Enter to send, Shift+Enter for newline)
- **View preview**: When agent starts a dev server, Preview tab auto-activates showing the live app
- **View details**: Task metadata (ID, sandbox ID, status, priority, type, phase, timestamps, description)
- **Refresh**: Manually refresh event stream connection
- **Infinite scroll**: Scroll up to load older events

### Tabs
| Tab | Content |
|-----|---------|
| Events | Real-time event feed with auto-scroll, infinite scroll for history |
| Preview | Live preview panel (appears when agent starts a dev server) |
| Details | Task info card (metadata) + Event summary card (counts) |

### Event Types Displayed
- `agent.tool_use` / `agent.tool_completed` — Tool invocations (Read, Write, Edit, Bash)
- `agent.file_edited` — File change diffs with line counts
- `agent.assistant_message` — Agent text responses (rendered as Markdown)
- `agent.user_message` — User-sent messages
- `agent.subagent_invoked` / `agent.subagent_completed` — Subagent delegation
- `agent.started` / `agent.completed` / `agent.error` — Lifecycle events

### Event Deduplication
The page applies intelligent deduplication:
- `tool_use` events are hidden when a matching `tool_completed` exists
- `file_edited` events are hidden when a `tool_completed` covers the same file
- Duplicate file writes to the same path with same content are collapsed
- Subagent prompts shown in SubagentCard suppress duplicate user messages
- Heartbeat events are always hidden

### Components
- `SandboxDetailPage` — Main detail page
- `EventRenderer` — Renders individual events by type
- `PreviewPanel` — Live application preview (iframe-based)
- `Markdown` — Renders agent messages
- `useInfiniteScrollTop` — Custom hook for upward infinite scroll

### API Endpoints
- `GET /api/v1/tasks?sandbox_id=:sandboxId` — Fetch task info (via `useSandboxTask`)
- `GET /api/v1/sandbox/:sandboxId/events` — Fetch event history
- `WS /api/v1/sandbox/:sandboxId/ws` — WebSocket for real-time events (via `useSandboxMonitor`)
- `POST /api/v1/sandbox/:sandboxId/message` — Send message to agent (via `sendMessage`)
- `GET /api/v1/sandbox/:sandboxId/preview` — Preview session info (via `usePreview`)

### State Management
- `useSandboxTask` (React Query) — Task metadata
- `useSandboxMonitor` (custom hook) — WebSocket connection + event history + message sending
- `usePreview` (custom hook) — Preview session lifecycle (start, stop, refresh, status)
- `useInfiniteScrollTop` (custom hook) — Upward infinite scroll with cooldown

### Connection States
| State | Indicator |
|-------|-----------|
| Connecting | Spinner + "Connecting..." |
| Connected | Green wifi icon + "Live" |
| Disconnected | Gray wifi-off icon + "Disconnected" |

---

## Sandbox Workflow Summary

```
Command Center (/command)
    │
    │ User types task + selects repo + submits
    │
    ▼
POST /api/v1/tickets → Creates ticket
    │
    │ Frontend waits for SANDBOX_SPAWNED event
    │ (WebSocket + 3s polling fallback)
    │
    ▼
Redirect to /sandbox/:sandboxId
    │
    │ Real-time event monitoring begins
    │ Agent works autonomously
    │
    ├── Events Tab: Watch tool calls, file edits, messages
    ├── Preview Tab: Live app preview when dev server starts
    ├── Details Tab: Task metadata and event counts
    │
    │ User can send messages to agent at any time
    │
    ▼
Task completes/fails → Status badge updates
    │
    │ User navigates back or to /sandboxes
    │
    ▼
Sandbox List (/sandboxes) — Browse all past/active sandboxes
```

---

**Next**: See [14_billing.md](./14_billing.md) for billing and subscription workflows.
