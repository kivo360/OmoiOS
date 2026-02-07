# Part 5: Frontend Architecture

> Summary doc — see linked design docs for full details.

## Overview

OmoiOS uses a **Next.js 15 App Router** frontend with ShadCN UI (Radix + Tailwind), dual state management (Zustand + React Query), and real-time WebSocket integration for live agent monitoring.

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | Next.js 15 (App Router) | SSR, routing, layouts |
| **UI Components** | ShadCN UI (Radix + Tailwind) | Base component library |
| **Client State** | Zustand (with middleware) | UI state, preferences |
| **Server State** | React Query | API data caching, mutations |
| **Graphs** | React Flow v12 (@xyflow/react) | Dependency visualization |
| **Terminal** | xterm.js | Agent output streaming |

## Route Groups

The app uses Next.js route groups for layout separation:

| Group | Layout | Purpose |
|-------|--------|---------|
| `(auth)` | Centered card | Login, register, OAuth, email verification, password reset |
| `(dashboard)` | Sidebar shell | All protected routes, project-scoped paths |

### Key Page Categories

- **Organization Pages** — list, create, detail, settings, member management
- **Dashboard** — overview with stats cards, project list (grid/list views), AI-assisted exploration
- **Spec Workspace** — multi-tab workspace (Requirements, Design, Tasks, Execution) with Notion-style structured blocks
- **Kanban Board** — horizontal scrolling columns with drag-and-drop tickets, inline detail drawer, WIP limits
- **Graph Views** — full project dependency graph and per-ticket focused graphs via React Flow
- **Statistics** — six analytics tabs for project metrics
- **Agent Management** — agent list, workspace views, diagnostic reasoning

## Component Organization

```
frontend/components/
├── ui/              # ShadCN base components (Button, Dialog, Card, etc.)
├── kanban/          # Kanban board feature components
├── graph/           # React Flow graph components
├── project/         # Project-scoped feature components
├── exploration/     # AI exploration wizard components
└── layout/          # Shell, sidebar, navigation
```

## State Management

Zustand stores use a rich middleware stack:

```
devtools → persist → websocketSync → reactQueryBridge → timeTravel → subscribeWithSelector → immer
```

- **Zustand**: UI state (sidebar open, selected tab, user preferences)
- **React Query**: Server data (projects, tickets, tasks, agents) with automatic cache invalidation
- **WebSocket Bridge**: Incoming events trigger both React Query invalidation and Zustand updates

## Real-Time Integration

WebSocket events bridge to both state layers:

1. **React Query**: `queryClient.invalidateQueries()` for entity-specific cache busting
2. **Zustand**: `websocketSync` middleware transforms events to state mutations with configurable merge strategies
3. **Optimistic Updates**: UI updates immediately, confirms/rolls back on WebSocket response

### Event Types

| Event | Triggers |
|-------|----------|
| `monitoring_update` | Guardian/Conductor analysis refresh |
| `steering_issued` | Agent intervention notification |
| `task_updated` | Task status change |
| `ticket_updated` | Ticket status change |
| `agent_status_changed` | Agent health change |

## Detailed Documentation

| Document | Content |
|----------|---------|
| [Frontend Architecture (ShadCN + Next.js)](../design/frontend/frontend_architecture_shadcn_nextjs.md) | Full component system, route architecture, middleware stack |
| [Page Architecture](../page_architecture.md) | All ~94 pages with layouts, data requirements, interactions |
| [React Query + WebSocket Integration](../design/frontend/react_query_websocket.md) | Detailed real-time data flow, cache strategies |
