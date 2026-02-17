# Activity Timeline

**Part of**: [Page Flow Documentation](./README.md)

---

## Overview

The Activity Timeline is a real-time event feed that aggregates all system activity across agents, tasks, tickets, commits, PRs, and sandbox executions. It connects via WebSocket to display events as they happen, with filtering and search capabilities. It can also be scoped to a specific sandbox via query parameter.

---

## Flow 67: Activity Timeline (Global)

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /activity                                            │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Activity Timeline               🟢 Connected          │ │
│  │  Real-time feed of all system    [42 events] [● Live]  │ │
│  │  activity                                     [↻]      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Filters                                               │ │
│  │  🔍 [Search activity...]                               │ │
│  │  Type: [All Types ▼]                                   │ │
│  │  Actor: [All] [🤖 Agents] [👤 You] [⚡ System]         │ │
│  │  Project: [All Projects ▼]                             │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  Today                                                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  🤖 agent_a5c2  [Agent]                                │ │
│  │  Modified stripe.ts (+45 -3)           📝 File Edit 2m│ │
│  │  ┌──────────────────────────────────────────────────┐ │ │
│  │  │  FileChangeCard: stripe.ts modified +45 -3       │ │ │
│  │  │  [View Diff]                                     │ │ │
│  │  └──────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  🤖 agent_b7d1  [Agent]                                │ │
│  │  TASK_COMPLETED on task task_123     ✓ Complete    5m  │ │
│  │  [Complete] [acme-project] Task: task_123              │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ⚡ System                                              │ │
│  │  AGENT_REGISTERED on agent agent_c9  ⚡ Spawned   8m  │ │
│  │  [Spawned] Type: code_generator                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  Yesterday                                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ...more events                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  [Listening for events... Activities appear as they happen] │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Route
`/activity` (global) or `/activity?sandbox_id=:sandboxId` (sandbox-scoped)

### Purpose
Real-time event feed showing all system activity. Useful for monitoring agent operations, debugging issues, and tracking progress across projects.

### User Actions
- **Search**: Filter events by title or description text
- **Filter by type**: All Types, Commits, Decisions, Comments, Completions, Errors, Pull Requests, Discoveries, Blocking, Status Changes, File Edits
- **Filter by actor**: All, Agents, You, System
- **Filter by project**: All Projects, System Events, or specific project
- **Toggle live mode**: Enable/disable real-time WebSocket updates
- **Refresh**: Clear events and restart the feed
- **Navigate to source**: Click event link to jump to the related ticket, agent, or task

### Sandbox-Scoped Mode
When `?sandbox_id=:sandboxId` is present:
- Title changes to "Sandbox Activity"
- Badge shows sandbox ID with "X" to clear filter
- WebSocket filters to only events for that sandbox entity

### Event Types
| Event Type | Icon | Category |
|------------|------|----------|
| `COMMIT_LINKED` / `commit` | Git commit | Code |
| `TASK_COMPLETED` / `task_complete` | Checkmark | Tasks |
| `TASK_ASSIGNED` | Arrow right | Tasks |
| `TASK_CREATED` | Plus | Tasks |
| `TICKET_TRANSITION` / `ticket_status` | Arrow right | Tickets |
| `TICKET_BLOCKED` | Warning | Tickets |
| `TICKET_UNBLOCKED` | Checkmark | Tickets |
| `AGENT_REGISTERED` / `agent_spawned` | Zap | Agents |
| `AGENT_HEARTBEAT` | Wifi | Agents |
| `decision` | Brain | Decisions |
| `comment` | Message | Comments |
| `ERROR` / `error` | Alert circle | Errors |
| `pr_opened` | Git PR | PRs |
| `discovery` | Lightbulb | Discoveries |
| `blocking_added` | Warning | Blocking |
| `tasks_generated` | Zap | Tasks |
| `spec_approved` | File text | Specs |
| `SANDBOX_agent.file_edited` | File code | Sandbox |
| `SANDBOX_agent.started` | Zap | Sandbox |
| `SANDBOX_agent.completed` | Checkmark | Sandbox |
| `SANDBOX_agent.error` | Alert | Sandbox |
| `SANDBOX_agent.tool_use` | Wrench | Sandbox |
| `SANDBOX_agent.tool_result` | Terminal | Sandbox |
| `SANDBOX_agent.thinking` | Brain | Sandbox |
| `SANDBOX_agent.assistant_message` | Message | Sandbox |
| `SANDBOX_agent.heartbeat` | Wifi | Sandbox |
| `SANDBOX_agent.message_injected` | Message | Sandbox |
| `SANDBOX_agent.subagent_invoked` | Bot | Sandbox |
| `SANDBOX_agent.subagent_completed` | Checkmark | Sandbox |

### Connection States
| State | Indicator |
|-------|-----------|
| Connecting | Yellow badge + pulsing wifi icon + "Connecting..." |
| Connected | Green badge + wifi icon + "Connected" |
| Disconnected | Red badge + wifi-off icon + "Disconnected" |
| Error | Red badge with error details |

### Grouping
Events are grouped by date: Today, Yesterday, Earlier.

### Components
- `ActivityPageContent` — Main activity feed with filters
- `FileChangeCard` — Renders file edit diffs inline (shared with sandbox detail)
- `useEvents` — Custom hook for WebSocket event subscription

### API Endpoints
- `WS /api/v1/events/ws` — WebSocket for real-time system events (via `useEvents`)

### State Management
- `useEvents` (custom WebSocket hook) — Manages connection, event buffering (max 100), filtering
- Local state for search query, type/actor/project filters, live toggle
- `useMemo` for filtered and grouped event lists
- Event-to-activity transformation with actor inference from entity type/payload

---

## Activity System Architecture

```
Backend Event Sources                    Frontend
┌───────────────────┐
│  Agent Service    │──┐
│  Task Service     │──┤                 ┌──────────────────┐
│  Ticket Service   │──┼── Redis ───────►│  WebSocket       │
│  Sandbox Service  │──┤    Pub/Sub      │  /api/v1/events  │
│  GitHub Service   │──┤                 │                  │
│  Commit Tracker   │──┘                 │  useEvents hook  │
└───────────────────┘                    │     │            │
                                         │     ▼            │
                                         │  Activity Page   │
                                         │  /activity       │
                                         │                  │
                                         │  Sandbox Page    │
                                         │  /sandbox/:id    │
                                         └──────────────────┘
```

---

**Previous**: See [16_public_pages.md](./16_public_pages.md) for public-facing pages.
