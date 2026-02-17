# 15 Prototype Workspace & Diagnostic Reasoning

**Part of**: [User Journey Documentation](./README.md)

---

## Overview

OmoiOS provides two advanced tools for rapid development and debugging: a Prototype Workspace for iterating on frontend UI via natural language, and a Diagnostic Reasoning view for inspecting the full decision chain behind any ticket or spec.

---

## 15.1 Prototype Workspace (/prototype)

```
User navigates to /prototype (from sidebar):
   ↓
No active session — framework selection screen:
   ↓
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│                    Start Prototyping                          │
│                                                              │
│  Framework:                                                  │
│  [React + Vite + TypeScript       ▼]                        │
│                                                              │
│  Options:                                                    │
│  - React + Vite + TypeScript                                │
│  - Next.js + TypeScript + Tailwind                          │
│  - Vue + Vite + TypeScript                                  │
│                                                              │
│                    [▶ Start Session]                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
   ↓
User clicks "Start Session":
   ↓
System creates sandbox → Status: "Creating..."
   ↓
Sandbox ready → Split view activated:
   ↓
┌───────────────────────┬─────────────────────────────────────┐
│  Prototype  [Ready]   │                        [End Session]│
│  react-vite           │                                     │
├───────────────────────┤                                     │
│                       │                                     │
│  [Describe what you   │        Live Preview Panel           │
│   want to build...]   │                                     │
│                       │     (iframe rendering the running   │
│  [Send Prompt]        │      prototype in real time)        │
│                       │                                     │
├───────────────────────┤                                     │
│  Prompt History:      │                                     │
│                       │                                     │
│  ┌─────────────────┐ │                                     │
│  │ "Add a login    │ │                                     │
│  │  form with..."  │ │                                     │
│  │ Response summary │ │                                     │
│  │ 10:23 AM        │ │                                     │
│  └─────────────────┘ │                                     │
│                       │                                     │
│  ┌─────────────────┐ │                                     │
│  │ "Change the     │ │                                     │
│  │  button color"  │ │                                     │
│  │ Response summary │ │                                     │
│  │ 10:25 AM        │ │                                     │
│  └─────────────────┘ │                                     │
│                       │                                     │
├───────────────────────┤                                     │
│  Export:              │                                     │
│  [github.com/user/repo]  [↓]                               │
└───────────────────────┴─────────────────────────────────────┘
```

### Session States

| Status | Description |
|--------|-------------|
| Creating | Sandbox being provisioned |
| Ready | Sandbox active, accepts prompts |
| Generating | Processing a prompt, preview updating |
| Exporting | Pushing code to a GitHub repository |
| Stopped | Session ended by user |
| Failed | Sandbox or prompt failed (error message shown) |

### Key Interactions

| Action | Behavior |
|--------|----------|
| Send Prompt | Describe UI changes in natural language → agent modifies code → preview updates live |
| Enter key | Sends prompt (Shift+Enter for newline) |
| Prompt History | Scrollable list of past prompts with response summaries and timestamps |
| Export to Repo | Enter a GitHub repo URL → code pushed to repository |
| End Session | Stops sandbox, returns to framework selection |
| PreviewPanel | Same component used in sandbox detail — renders live iframe of running app |

### Integration with Sandbox System

- Uses `usePrototype` hook backed by `PrototypeSession` API type
- Session has `preview_id` and `sandbox_id` linking to the sandbox infrastructure
- `PreviewPanel` component is shared with the main sandbox detail view
- Framework selection determines the scaffold (React+Vite, Next.js, or Vue+Vite)

---

## 15.2 Diagnostic Reasoning (/diagnostic/[entityType]/[entityId])

```
User clicks "Diagnostic" link on a ticket or spec:
   ↓
Navigates to /diagnostic/ticket/:id or /diagnostic/spec/:id:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Ticket                                            │
│  Diagnostic Reasoning           TICKET-abc123                │
│  Complete timeline of agent decisions and reasoning           │
│                                                              │
│  [42 events] [12 decisions] [2 errors]                       │
├─────────────────────────────────────────────────────────────┤
│  [Search events...] [Event type ▼]  [Expand All] [Collapse] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Timeline:                                                   │
│                                                              │
│  ● Ticket Created                               2h ago      │
│  │ ┌─────────────────────────────────────────────────────┐  │
│  │ │ > "Build authentication system"                     │  │
│  │ │   Created with HIGH priority                        │  │
│  │ └─────────────────────────────────────────────────────┘  │
│  │                                                           │
│  ⚡ Tasks Spawned                               1h 55m ago  │
│  │ ┌─────────────────────────────────────────────────────┐  │
│  │ │ > "Spawned 3 sub-tasks for auth implementation"     │  │
│  │ │   🤖 worker-1                                       │  │
│  │ │   ▸ Details (click to expand)                       │  │
│  │ └─────────────────────────────────────────────────────┘  │
│  │                                                           │
│  💡 Discovery                                    1h 30m ago  │
│  │ ┌─────────────────────────────────────────────────────┐  │
│  │ │ > "Found existing JWT utilities in shared/auth"     │  │
│  │ │   🤖 worker-1                                       │  │
│  │ │   ▸ Evidence: code, requirement                     │  │
│  │ └─────────────────────────────────────────────────────┘  │
│  │                                                           │
│  🧠 Agent Decision                               1h 15m ago │
│  │ ┌─────────────────────────────────────────────────────┐  │
│  │ │ > "Chose JWT over session-based auth"               │  │
│  │ │   🤖 worker-1                    Confidence: 89%    │  │
│  │ │                                                      │  │
│  │ │   Reasoning: "JWT aligns with existing API..."      │  │
│  │ │                                                      │  │
│  │ │   Alternatives considered:                           │  │
│  │ │   ✗ Session-based: "Doesn't scale for API clients" │  │
│  │ │   ✗ OAuth only: "Over-engineered for MVP"           │  │
│  │ │                                                      │  │
│  │ │   Decision: [IMPLEMENT]                              │  │
│  │ │   "Implement JWT with refresh token rotation"        │  │
│  │ └─────────────────────────────────────────────────────┘  │
│  │                                                           │
│  ...                                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Event Types

| Event Type | Icon | Color | Description |
|------------|------|-------|-------------|
| ticket_created | Plus | Blue | Ticket or spec was created |
| task_spawned | Zap | Purple | Sub-tasks spawned from parent |
| discovery | Lightbulb | Yellow | Agent found something noteworthy |
| agent_decision | Brain | Green | Agent made a deliberate choice |
| blocking_added | Warning | Orange | Blocking dependency identified |
| code_change | GitBranch | Cyan | Code was modified |
| error | AlertCircle | Red | Error or failure occurred |

### Event Card Details (Expanded)

Each event card is collapsible. When expanded, it shows:

| Section | Content |
|---------|---------|
| Details | Context text, reasoning explanation, tasks created list, alternatives considered with rejection reasons, confidence percentage, lines added/removed/files changed/tests |
| Evidence | Typed evidence items (error, log, code, doc, requirement, test, coverage, stats) with content and optional external link |
| Decision | Decision type badge (COMPLETE, BLOCK, IMPLEMENT), action description, reasoning explanation. Color-coded: green for complete, orange for block, blue for implement |

### Filters & Controls

| Control | Behavior |
|---------|----------|
| Search | Filter events by title or description text |
| Type filter | Dropdown: All Events, Ticket Created, Tasks Spawned, Discovery, Agent Decision, Blocking Added, Code Change, Error |
| Expand All | Opens all event cards simultaneously |
| Collapse All | Closes all event cards |

### Navigation

- Back link navigates to source: `/board/project/[ticketId]` for tickets, `/projects/project/specs/[specId]` for specs
- Header shows entity type badge (TICKET or SPEC) with entity ID
- Stats badges show total events, decisions count, and error count

### API Integration

- Uses `useReasoningChain(entityType, entityId, filters)` hook
- Server-side type filtering via `event_type` query parameter
- Returns `{ events, stats: { total, decisions, discoveries, errors } }`

---

**Related**: See [06a_monitoring_system.md](./06a_monitoring_system.md) for Guardian monitoring and [03_execution_monitoring.md](./03_execution_monitoring.md) for sandbox execution monitoring.
