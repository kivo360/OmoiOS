# Frontend Implementation Guide: From Docs to Next.js App

**Created**: 2025-11-21
**Updated**: 2025-11-21
**Status**: Implementation Roadmap
**Purpose**: Step-by-step guide to build the OmoiOS Next.js frontend using existing infrastructure

---

## Overview

You already have **extensive frontend infrastructure** documented (~10,000+ lines). This guide shows you how to assemble it into a working Next.js app.

### API integration targets (keep mocks until final wiring)
When replacing mocks, use these endpoints/contracts to stay aligned with backend:
- Health: `GET /api/health/overview` (alignment, active_agents, alerts, interventions_24h), `GET /api/health/trajectories` (agent_id, project_id, alignment_score, status, last_event, note), `GET /api/health/interventions` (id, agent_id, type, result, summary, timestamp), `GET/PUT /api/health/settings` (alignment_min, idle_minutes, poll_seconds, notify_email, notify_slack).
- Graph/Discovery: `GET /api/projects/{projectId}/graph` (tickets with status/priority/blocked_by/assignee), `GET /api/projects/{projectId}/discoveries` (id, ticket_id, branch, type, summary, impact), `GET /api/tickets/{ticketId}/thread` (phases[], current_phase, thread_label).
- Phase Gates: `GET /api/projects/{projectId}/phase-gates/pending`, `POST /api/phase-gates/{gateId}/decision` (approve/reject, comment, artifacts[]).
- Analytics: `GET /api/analytics/overview` (per-project stats), `GET /api/analytics/activity` (event feed).
- Workspaces/Agents: `GET /api/workspaces` (id, agent_id, project_id, repo, status, last_sync), `GET /api/agents/{agentId}` (status, current_ticket, heartbeat).
- Command Center: `GET /api/projects` (id, name, repo, ticket_count), `GET /api/repos` (full_name, private), `POST /api/agents` (prompt, project_id|repo_full_name, model) → returns agent_id.

Use React Query hooks to replace mock arrays; keep identical shapes to avoid UI churn.

**✅ You Already Have:**

### Product & Design Documentation
- `docs/app_overview.md` - Product overview, features, user flow (complete)
- `docs/page_architecture.md` - Detailed specs for all 40+ pages (complete)
- `docs/design_system.md` - Colors, typography, components, spacing (complete)
- `docs/user_journey.md` - User flows and scenarios (complete)
- `docs/page_flow.md` - Page-by-page navigation flows (complete)

### Technical Architecture Documentation
- `docs/design/frontend/frontend_architecture_shadcn_nextjs.md` - **Complete Next.js 15 + ShadCN architecture**
- `docs/design/frontend/react_query_websocket.md` - **React Query hooks + WebSocket integration** (2,958 lines!)
- `docs/design/frontend/zustand_middleware_reference.md` - **Custom Zustand middleware** (websocketSync, reactQueryBridge, timeTravel)
- `docs/design/frontend/component_scaffold_guide.md` - **Ready-to-use component scaffolds** (5,000+ lines)
- `docs/design/auth/frontend_auth_scaffold.md` - **Complete auth pages with code** (1,974 lines)
- `docs/design/frontend/project_management_dashboard.md` - Detailed UI/UX specs (4,549 lines)

### Working Prototype
- `examples/frontend/` - Working Vite + React prototype with ticket panel

**Total Documentation**: ~20,000+ lines of frontend specifications, architecture, and code scaffolds.

---

## Quick Start: 5 Commands to Create the Project

```bash
# 1. Create Next.js 15 app with TypeScript and App Router
npx create-next-app@latest omoios-ui --typescript --tailwind --app --use-npm

# 2. Navigate into project
cd omoios-ui

# 3. Install ShadCN UI (based on Radix UI + Tailwind)
npx shadcn@latest init

# 4. Install additional dependencies
npm install zustand @tanstack/react-query react-flow-renderer lucide-react date-fns

# 5. Start dev server
npm run dev
```

**Result**: You now have a Next.js 15 app running at `http://localhost:3000`.

---

## Project Structure (Already Defined)

**Reference**: `docs/design/frontend/frontend_architecture_shadcn_nextjs.md` (lines 92-209)

You already have the complete directory structure defined. Use it as-is:

```
omoios-ui/
├── src/
│   ├── app/                          # App Router pages
│   │   ├── (auth)/                   # Auth layout group
│   │   │   ├── login/
│   │   │   │   └── page.tsx          # /login
│   │   │   ├── register/
│   │   │   │   └── page.tsx          # /register
│   │   │   ├── verify-email/
│   │   │   │   └── page.tsx          # /verify-email
│   │   │   └── layout.tsx            # Auth layout (centered card)
│   │   │
│   │   ├── (dashboard)/              # Dashboard layout group
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx          # /dashboard
│   │   │   ├── projects/
│   │   │   │   ├── page.tsx          # /projects
│   │   │   │   ├── new/
│   │   │   │   │   └── page.tsx      # /projects/new
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx      # /projects/:id
│   │   │   │       ├── phases/
│   │   │   │       │   ├── page.tsx  # /projects/:id/phases
│   │   │   │       │   └── [phaseId]/
│   │   │   │       │       └── page.tsx # /projects/:id/phases/:phaseId
│   │   │   │       ├── specs/
│   │   │   │       │   └── [specId]/
│   │   │   │       │       └── page.tsx # /projects/:id/specs/:specId
│   │   │   │       └── stats/
│   │   │   │           └── page.tsx  # /projects/:id/stats
│   │   │   ├── board/
│   │   │   │   └── [projectId]/
│   │   │   │       ├── page.tsx      # /board/:projectId
│   │   │   │       └── [ticketId]/
│   │   │   │           └── page.tsx  # /board/:projectId/:ticketId
│   │   │   ├── graph/
│   │   │   │   └── [projectId]/
│   │   │   │       └── page.tsx      # /graph/:projectId
│   │   │   ├── agents/
│   │   │   │   ├── page.tsx          # /agents
│   │   │   │   └── [agentId]/
│   │   │   │       └── page.tsx      # /agents/:agentId
│   │   │   └── layout.tsx            # Dashboard layout (header + sidebar)
│   │   │
│   │   └── page.tsx                  # Landing page (/)
│   │
│   ├── components/                   # Reusable components
│   │   ├── ui/                       # ShadCN components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── avatar.tsx
│   │   │   └── ...
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── ActivityFeed.tsx
│   │   │   └── CommandPalette.tsx
│   │   ├── board/
│   │   │   ├── KanbanBoard.tsx
│   │   │   ├── TicketCard.tsx
│   │   │   └── TicketDetailDrawer.tsx
│   │   ├── graph/
│   │   │   ├── DependencyGraph.tsx
│   │   │   └── GraphControls.tsx
│   │   ├── agents/
│   │   │   ├── AgentStatusWidget.tsx
│   │   │   └── AgentCard.tsx
│   │   └── phases/
│   │       ├── PhaseCard.tsx
│   │       └── PhaseOverview.tsx
│   │
│   ├── lib/                          # Utilities
│   │   ├── api.ts                    # API client (fetch wrapper)
│   │   ├── websocket.ts              # WebSocket client
│   │   └── utils.ts                  # Helper functions
│   │
│   ├── store/                        # State management
│   │   ├── useProjectStore.ts        # Zustand store for projects
│   │   ├── useAgentStore.ts          # Zustand store for agents
│   │   └── useWebSocketStore.ts      # WebSocket connection state
│   │
│   ├── hooks/                        # Custom hooks
│   │   ├── useTickets.ts             # React Query for tickets
│   │   ├── useTasks.ts               # React Query for tasks
│   │   ├── useAgents.ts              # React Query for agents
│   │   └── useWebSocket.ts           # WebSocket hook
│   │
│   └── types/                        # TypeScript types
│       ├── ticket.ts
│       ├── task.ts
│       ├── agent.ts
│       └── phase.ts
│
├── public/                           # Static assets
├── tailwind.config.ts                # Design system colors/spacing
└── package.json
```

---

## Step-by-Step Implementation

### Step 1: Set Up Design System in Tailwind

**✅ Already Defined**: `docs/design_system.md`

Copy the Tailwind config directly into your project:

**File**: `tailwind.config.ts`

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // From docs/design_system.md - Primary Colors
        primary: {
          100: '#DBEAFE',
          500: '#3B82F6',
          600: '#2563EB',
        },
        // Status Colors
        success: '#10B981',
        error: '#EF4444',
        warning: '#F59E0B',
        info: '#3B82F6',
        // Workflow Phase Colors
        phase: {
          requirements: '#8B5CF6',
          implementation: '#3B82F6',
          testing: '#F97316',
          deployment: '#10B981',
          blocked: '#EF4444',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      spacing: {
        // From docs/design_system.md - Spacing System
        'xs': '4px',
        'sm': '8px',
        'md': '16px',
        'lg': '24px',
        'xl': '32px',
        '2xl': '48px',
        '3xl': '64px',
      }
    },
  },
  plugins: [],
};
export default config;
```

---

### Step 2: Copy Documentation to Frontend Project

Create a `docs/` folder in your Next.js project and copy key docs:

```bash
# Inside omoios-ui/
mkdir -p docs

# Copy essential docs
cp ../senior_sandbox/docs/app_overview.md docs/
cp ../senior_sandbox/docs/page_architecture.md docs/
cp ../senior_sandbox/docs/design_system.md docs/
cp ../senior_sandbox/docs/user_journey.md docs/
```

These become your **implementation reference** as you build each page.

---

### Step 3: Install ShadCN Components (Complete List)

**✅ Already Defined**: `docs/design/frontend/frontend_architecture_shadcn_nextjs.md` (Component Mapping section, lines 32-89)

Install all ShadCN components you'll need:

```bash
# Core Components
npx shadcn@latest add button card input badge avatar dropdown-menu dialog tabs toast table

# Layout Components
npx shadcn@latest add sheet scroll-area separator navigation-menu breadcrumb

# Form Components
npx shadcn@latest add label select checkbox radio-group switch textarea form

# Data Display
npx shadcn@latest add progress accordion alert-dialog popover tooltip calendar

# Feedback
npx shadcn@latest add alert toast sonner

# Utilities
npx shadcn@latest add command
```

These auto-generate components in `src/components/ui/` styled with your Tailwind theme.

---

### Step 4: Use Existing React Query Hooks

**✅ Already Implemented**: `docs/design/frontend/react_query_websocket.md` (lines 1-500)

You have **complete React Query hooks already defined** for all entities. Copy them directly:

**Reference Document Sections:**
- Lines 9-47: Query Key Factory (projectKeys, boardKeys, ticketKeys, agentKeys, graphKeys)
- Lines 52-167: Custom Hooks (useProjects, useTickets, useAgents, useTasks, useBoard)
- Lines 485-830: Agent Hooks with full mutations
- Lines 1200-1900: Advanced hooks (search, filters, pagination)

**File**: `src/lib/query-keys.ts` (Copy from docs)

```typescript
// This is already fully defined in docs/design/frontend/react_query_websocket.md
export const projectKeys = {
  all: ['projects'] as const,
  lists: () => [...projectKeys.all, 'list'] as const,
  detail: (id: string) => [...projectKeys.all, 'detail', id] as const,
  stats: (id: string) => [...projectKeys.all, 'stats', id] as const,
}

export const ticketKeys = {
  all: ['tickets'] as const,
  lists: (filters?: Record<string, any>) => [...ticketKeys.all, 'list', { ...filters }] as const,
  detail: (id: string) => [...ticketKeys.all, 'detail', id] as const,
  comments: (id: string) => [...ticketKeys.all, 'comments', id] as const,
}

// ... (copy all keys from docs)
```

**File**: `src/hooks/useTickets.ts` (Copy from docs)

```typescript
// Already fully implemented in docs/design/frontend/react_query_websocket.md lines 96-167
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ticketKeys } from '@/lib/query-keys'
import { api } from '@/lib/api'

export function useTickets(projectId: string) {
  return useQuery({
    queryKey: ticketKeys.lists({ projectId }),
    queryFn: () => api.getTickets(projectId),
    enabled: !!projectId,
  })
}

export function useCreateTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.createTicket,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.all })
    },
  })
}

// ... (copy all hooks from docs)
```

---

### Step 5: Use Existing WebSocket Provider

**✅ Already Implemented**: `docs/design/auth/frontend_auth_scaffold.md` (lines 1815-1900)

You have a **complete WebSocket Provider with React Query integration** already defined.

**File**: `src/providers/WebSocketProvider.tsx` (Copy from docs)

```typescript
// Already fully implemented in docs/design/auth/frontend_auth_scaffold.md
"use client"

import { createContext, useContext, useEffect, useRef } from "react"
import { useQueryClient } from "@tanstack/react-query"

const WebSocketContext = createContext<{
  socket: WebSocket | null
  isConnected: boolean
  send: (type: string, payload: any) => void
}>({ socket: null, isConnected: false, send: () => {} })

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const socket = useRef<WebSocket | null>(null)
  const queryClient = useQueryClient()
  
  useEffect(() => {
    const ws = new WebSocket(process.env.NEXT_PUBLIC_WS_URL!)
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      // Invalidate React Query cache based on event type
      if (data.event_type === 'TICKET_UPDATED') {
        queryClient.invalidateQueries({ queryKey: ['tickets'] })
      }
      // ... (full implementation in docs)
    }
    
    socket.current = ws
    return () => ws.close()
  }, [])
  
  return (
    <WebSocketContext.Provider value={{ socket: socket.current, ... }}>
      {children}
    </WebSocketContext.Provider>
  )
}

export const useWebSocket = () => useContext(WebSocketContext)
```

**Reference**: `docs/design/frontend/react_query_websocket.md` (lines 1839-2100) for complete WebSocket event handling.

---

### Step 6: Use Existing Page Scaffolds

**✅ Already Implemented**: `docs/design/auth/frontend_auth_scaffold.md` - **Complete auth pages with code**

You have **ready-to-use page scaffolds**. Just copy and customize:

**MVP Page Priority** (Copy in this order):

#### Phase 1: Authentication (Week 1)
- [ ] Landing page (`/`)
- [ ] Login page (`/login`)
- [ ] Register page (`/register`)

**✅ Already Implemented**: `docs/design/auth/frontend_auth_scaffold.md`

**Copy These Files Directly:**
1. **Auth Layout**: Lines 11-31 → `app/(auth)/layout.tsx`
2. **Login Page**: Lines 33-162 → `app/(auth)/login/page.tsx`
3. **Register Page**: Lines 164-308 → `app/(auth)/register/page.tsx`
4. **Verify Email Page**: Lines 310-383 → `app/(auth)/verify-email/page.tsx`
5. **Forgot Password**: Lines 385-488 → `app/(auth)/forgot-password/page.tsx`
6. **Reset Password**: Lines 490-593 → `app/(auth)/reset-password/page.tsx`

**These are complete, production-ready pages.** Just copy the code.

#### Phase 2: Dashboard Shell (Week 1)
- [ ] Dashboard layout (`/dashboard`)
- [ ] Header component
- [ ] Sidebar navigation component

**✅ Already Implemented**: `docs/design/auth/frontend_auth_scaffold.md`

**Copy These Files Directly:**
1. **Dashboard Layout**: Lines 595-670 → `app/(dashboard)/layout.tsx`
2. **Root Layout with Providers**: Lines 672-750 → `app/layout.tsx`
3. **Query Provider**: Lines 1789-1813 → `src/providers/QueryProvider.tsx`
4. **WebSocket Provider**: Lines 1815-1895 → `src/providers/WebSocketProvider.tsx`

**These include:**
- Header with navigation
- Sidebar with collapsible sections
- React Query provider setup
- WebSocket provider with auto-reconnect
- Theme provider (light/dark mode)

#### Phase 3: Projects (Week 2)
- [ ] Projects list (`/projects`)
- [ ] Project overview (`/projects/:id`)

**Implementation Guide:**
1. Read `docs/page_architecture.md` → "Projects List" and "Project Overview"
2. Create API hooks with React Query
3. Build project cards using ShadCN `Card` component

#### Phase 4: Kanban Board (Week 2-3)
- [ ] Kanban board (`/board/:projectId`)
- [ ] Ticket cards
- [ ] Ticket detail drawer

**✅ Already Implemented**: `docs/design/auth/frontend_auth_scaffold.md` (lines 1030-1385)

**Copy These Files Directly:**
1. **Kanban Board Page**: Lines 1030-1200 → `app/(dashboard)/board/[projectId]/page.tsx`
   - Includes drag-and-drop with @dnd-kit
   - Zustand store integration
   - React Query + WebSocket sync
   - Optimistic updates

2. **Kanban Store**: `docs/design/frontend/react_query_websocket.md` (lines 2652-2750) → `src/stores/kanbanStore.ts`
   - Complete Zustand store with all middleware
   - WebSocket sync
   - React Query bridge
   - Time-travel (undo/redo)

**This is production-ready code with all features.**

#### Phase 5: Real-Time Features (Week 3)
- [ ] WebSocket integration
- [ ] Real-time board updates
- [ ] Activity feed component

**Implementation Guide:**
1. Set up WebSocket hook
2. Subscribe to events: `TICKET_CREATED`, `TICKET_UPDATED`, `TASK_COMPLETED`
3. Update UI optimistically

---

## Practical Workflow: Using Your Existing Scaffolds

### You Don't Need to Write Pages from Scratch

**You already have complete page implementations.** Here's the workflow:

**Step 1: Identify the Page**
Look up the page in `docs/page_architecture.md`

**Step 2: Find the Scaffold**
Check if it exists in:
- `docs/design/auth/frontend_auth_scaffold.md` (Auth pages - lines 11-1974)
- `docs/design/frontend/component_scaffold_guide.md` (Components - lines 1-5374)
- `docs/design/frontend/react_query_websocket.md` (Hooks - lines 1-2958)

**Step 3: Copy the Code**
Literally copy-paste the implementation into your project.

**Step 4: Customize**
Adjust branding, text, API endpoints.

### Example: Adding Login Page (1 Minute)

**Step 1**: Open `docs/design/auth/frontend_auth_scaffold.md` → Lines 33-162

**Step 2**: Copy entire code block

**Step 3**: Paste into `app/(auth)/login/page.tsx`

**Step 4**: Update API endpoint if needed:
```typescript
// Change this line:
const res = await fetch("/api/v1/auth/login", ...)
// To match your backend:
const res = await fetch("/api/auth/login", ...)
```

**Done.** The page is complete with:
- Form validation
- Loading states
- Error handling
- OAuth button
- Responsive design
- Tailwind styling matching design system

---

## Document-to-Code Mapping (Copy-Paste Workflow)

### For Each Page You Build:

**Option A: Use Existing Scaffolds (Fastest)**
1. Check if page exists in scaffold docs:
   - Auth pages → `docs/design/auth/frontend_auth_scaffold.md`
   - Dashboard pages → `docs/design/frontend/component_scaffold_guide.md`
2. Copy the entire page implementation
3. Paste into `src/app/[path]/page.tsx`
4. Adjust API endpoints to match your backend
5. Done.

**Option B: Build from Spec (If No Scaffold)**
1. **Open `docs/page_architecture.md`** → Find your page
2. **Read these sections**:
   - Purpose (why the page exists)
   - Layout Structure (header, sidebar, content areas)
   - Key Components (which UI elements to use - ShadCN mapping provided)
   - Interactive Elements (what users can do)
   - Content (specific text and data)
   - States (loading, empty, error states)

3. **Use existing hooks** from `docs/design/frontend/react_query_websocket.md`
4. **Use existing stores** (if needed) from `docs/design/frontend/zustand_middleware_reference.md`
5. **Reference similar page** in scaffold docs for patterns
6. **Build page** using ShadCN components
7. **Wire up WebSocket** using WebSocketProvider

**Estimated Time per Page:**
- With scaffold: **5-15 minutes** (copy-paste + customize)
- Without scaffold: **1-3 hours** (build from spec)

---

## MVP Feature Set (Ship First)

**Week 1-2: Core Auth & Shell**
- [ ] Landing page
- [ ] Login/Register
- [ ] Dashboard shell (header + sidebar)
- [ ] Projects list

**Week 3-4: Kanban Board**
- [ ] Board view with columns
- [ ] Ticket cards
- [ ] Ticket detail view
- [ ] Real-time updates (WebSocket)

**Week 5-6: Agents & Monitoring**
- [ ] Agents list
- [ ] Agent detail view
- [ ] Activity timeline
- [ ] Basic statistics

**Week 7-8: Phases & Advanced**
- [ ] Phase overview dashboard
- [ ] Dependency graph (basic)
- [ ] Spec workspace (read-only first)

**Week 9-10: Polish & Enhancements**
- [ ] Search functionality
- [ ] Intervention queue
- [ ] Comments system
- [ ] Export features

---

## Pre-Built Infrastructure You Have

### Zustand Stores (Custom Middleware)

**✅ Already Implemented**: `docs/design/frontend/zustand_middleware_reference.md`

**Custom Middleware Included:**
1. **websocketSync** - Real-time WebSocket synchronization (lines 20-137)
2. **reactQueryBridge** - Bidirectional Zustand ↔ React Query sync (lines 171-330)
3. **timeTravel** - Undo/redo with state history (dev mode)
4. **compressedStorage** - LZ-string compression for large state
5. **encryptedStorage** - Client-side encryption
6. **robustStorage** - Multi-fallback (localStorage → sessionStorage → memory)

**Example Stores Ready to Copy:**
- `uiStore.ts` - Global UI state (lines 4884-4970 in component_scaffold_guide.md)
- `kanbanStore.ts` - Kanban with full middleware stack (lines 2652-2750 in react_query_websocket.md)
- `agentStore.ts` - Agent selection and monitoring (lines 276-342 in react_query_websocket.md)
- `searchStore.ts` - Search with history persistence
- `terminalStore.ts` - Multi-session terminal management

**To Use:**
1. Create `src/stores/` directory
2. Copy store implementations from docs
3. Import in your components:
   ```typescript
   import { useKanbanStore } from '@/stores/kanbanStore'
   
   const { tickets, moveTicket } = useKanbanStore()
   ```

---

### React Query Hooks (Complete Set)

**✅ Already Implemented**: `docs/design/frontend/react_query_websocket.md`

**Hooks Ready to Copy:**
- **Project Hooks**: useProjects, useProject, useCreateProject (lines 52-95)
- **Ticket Hooks**: useTickets, useTicket, useCreateTicket, useMoveTicket (lines 96-167)
- **Agent Hooks**: useAgents, useAgent, useAgentTrajectory, useSpawnAgent (lines 485-830)
- **Task Hooks**: useTasks, useTask, useCreateTask (lines 168-215)
- **Graph Hooks**: useDependencyGraph (lines 216-275)
- **Search Hooks**: useTicketSearch with filters (lines 1200-1350)

**To Use:**
1. Create `src/hooks/` directory
2. Copy hook implementations from docs
3. Use in components:
   ```typescript
   import { useTickets } from '@/hooks/useTickets'
   
   const { data: tickets, isLoading } = useTickets(projectId)
   ```

---

### Component Scaffolds (80+ Components)

**✅ Already Implemented**: `docs/design/frontend/component_scaffold_guide.md` (5,374 lines)

**Complete Components Ready to Copy:**
- KanbanBoard, BoardColumn, TicketCard (lines 464-1115)
- DependencyGraph with React Flow (lines 1122-1455)
- SearchCommand with history (lines 1867-2053)
- AgentCard, AgentStatusWidget (lines 2246-2519)
- TerminalStream with Xterm.js (lines 4558-4879)
- CodeHighlighter with syntax highlighting (lines 4283-4557)
- And 70+ more components...

**To Use:**
1. Create component directory structure
2. Copy component code from docs
3. Import and use:
   ```typescript
   import { KanbanBoard } from '@/components/kanban/KanbanBoard'
   
   <KanbanBoard projectId={projectId} />
   ```

---

## Integration with Backend

### Environment Variables

**File**: `.env.local`

```bash
NEXT_PUBLIC_API_URL=http://localhost:18000
NEXT_PUBLIC_WS_URL=ws://localhost:18000/ws
```

### API Routes to Implement

Map backend FastAPI routes to frontend API client:

**Backend** (`omoi_os/api/routes/tickets.py`):
```python
@router.post("", response_model=TicketResponse)
async def create_ticket(ticket_data: TicketCreate):
    ...
```

**Frontend** (`src/lib/api.ts`):
```typescript
async createTicket(data: TicketCreate): Promise<TicketResponse> {
  return this.request('/api/tickets', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
```

---

## Reference Documents at Each Stage

### When Building Auth Pages
**Read:**
- `docs/page_architecture.md` → Authentication Pages section
- `docs/user_journey.md` → Phase 1: Onboarding & First Project Setup
- `docs/page_flow.md` → Flow 1: Registration & First Login

### When Building Kanban Board
**Read:**
- `docs/page_architecture.md` → Kanban Board Pages section
- `docs/user_journey.md` → Phase 3: Autonomous Execution & Monitoring
- `docs/design/frontend/project_management_dashboard.md` → Kanban Board section
- `docs/page_flow.md` → Flow 10: Kanban Board & Ticket Management

### When Building Dependency Graph
**Read:**
- `docs/page_architecture.md` → Graph & Visualization Pages
- `docs/design/services/dependency_graph_service.md` → Graph data structure
- `docs/design/frontend/workflow_interconnection_validation.md` → Discovery branching visualization

### When Building Phase Management
**Read:**
- `docs/page_architecture.md` → Phase Management Pages
- `docs/design/workflows/omoios_phase_system_comparison.md` → Phase system details
- `docs/user_journey.md` → Phase System Overview section

---

## TypeScript Types from Backend

Generate TypeScript types from your Python models:

**Option 1: Manual (Quick Start)**

**File**: `src/types/ticket.ts`

```typescript
export type TicketStatus = 
  | 'backlog'
  | 'analyzing'
  | 'building'
  | 'building-done'
  | 'testing'
  | 'done'
  | 'blocked';

export type Ticket = {
  id: string;
  title: string;
  description: string;
  status: TicketStatus;
  phase_id: string;
  priority: string;
  created_at: string;
  updated_at: string;
  blocked_by_ticket_ids?: Record<string, string>;
};
```

**Option 2: Auto-Generate (Better)**

Use `openapi-typescript` to generate types from FastAPI's OpenAPI schema:

```bash
# Install
npm install --save-dev openapi-typescript

# Generate types from backend
npx openapi-typescript http://localhost:18000/openapi.json -o src/types/api.d.ts
```

---

## Recommended Development Sequence

### Week 1: Foundation
```bash
# Day 1-2: Project setup
- Create Next.js project
- Set up Tailwind with design system
- Install ShadCN components
- Create folder structure

# Day 3-4: Auth pages
- Build landing page
- Build login page
- Build register page
- Wire up backend API

# Day 5: Dashboard shell
- Create layout with header + sidebar
- Build navigation
- Add activity feed (right sidebar)
```

### Week 2: Core Features
```bash
# Day 1-3: Projects
- Projects list page
- Create project page
- Project overview page

# Day 4-5: Kanban Board (basic)
- Board layout with columns
- Ticket cards (static)
- Ticket detail drawer
```

### Week 3: Real-Time & Agents
```bash
# Day 1-2: WebSocket integration
- Set up WebSocket client
- Add real-time board updates
- Add activity feed updates

# Day 3-5: Agents
- Agents list page
- Agent detail page
- Agent status widget (header)
```

### Week 4: Phases & Graph
```bash
# Day 1-2: Phase management
- Phase overview page
- Phase detail page

# Day 3-5: Dependency graph
- Basic graph visualization
- Graph controls
- Node detail panel
```

---

## Streamlined Setup: Use Your Infrastructure

### Complete Setup Script

**Reference**: `docs/design/frontend/frontend_architecture_shadcn_nextjs.md` (lines 220-275)

```bash
# 1. Create Next.js project
npx create-next-app@latest omoios-ui --typescript --tailwind --app --use-npm
cd omoios-ui

# 2. Initialize ShadCN
npx shadcn@latest init

# 3. Install COMPLETE dependency list (from your architecture doc)
npm install \
  @tanstack/react-query@^5.0.0 \
  @tanstack/react-query-devtools@^5.0.0 \
  zustand@^4.5.0 \
  immer@^10.0.3 \
  zundo@^2.0.0 \
  zustand-pub@^1.0.0 \
  lz-string@^1.5.0 \
  @dnd-kit/core@^6.1.0 \
  @dnd-kit/sortable@^8.0.0 \
  reactflow@^11.10.0 \
  framer-motion@^11.0.0 \
  date-fns@^2.30.0 \
  recharts@^2.9.0 \
  react-syntax-highlighter@^15.5.0 \
  xterm@^5.3.0 \
  xterm-addon-fit@^0.8.0 \
  xterm-addon-web-links@^0.9.0 \
  next-themes@^0.2.1

# 4. Install ShadCN components (complete list)
npx shadcn@latest add button card input badge avatar dropdown-menu \
  dialog tabs toast table sheet scroll-area separator navigation-menu \
  breadcrumb label select checkbox radio-group switch textarea form \
  progress accordion alert-dialog popover tooltip calendar alert command

# 5. Create folder structure
mkdir -p src/{components,lib,hooks,stores,types,providers,middleware}
mkdir -p src/components/{ui,shared,layout,kanban,graph,agents,phases,project,exploration}

# 6. Copy documentation to project
mkdir -p docs
cp ../senior_sandbox/docs/{app_overview,page_architecture,design_system}.md docs/
cp -r ../senior_sandbox/docs/design/frontend docs/design/

# 7. Set up environment variables
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:18000
NEXT_PUBLIC_WS_URL=ws://localhost:18000/ws
EOF

# 8. Start development
npm run dev
```

**Result**: Complete Next.js project with all dependencies and documentation ready.

---

## Complete Documentation Reference Chart

| Building... | Scaffold Document (Copy-Paste) | Spec Document (Reference) | Lines |
|-------------|-------------------------------|---------------------------|-------|
| **Landing Page** | - | `page_architecture.md` | "Landing Page" |
| **Login** | `frontend_auth_scaffold.md` | `page_architecture.md` | 33-162 |
| **Register** | `frontend_auth_scaffold.md` | `page_architecture.md` | 164-308 |
| **Verify Email** | `frontend_auth_scaffold.md` | `page_architecture.md` | 310-383 |
| **Dashboard Layout** | `frontend_auth_scaffold.md` | `page_architecture.md` | 595-670 |
| **Kanban Board** | `frontend_auth_scaffold.md` | `page_architecture.md` | 1030-1385 |
| **Dependency Graph** | `component_scaffold_guide.md` | `dependency_graph_service.md` | Check doc |
| **Search Command** | `component_scaffold_guide.md` | `page_architecture.md` | 1867-2053 |
| **Agent Card** | `component_scaffold_guide.md` | `page_architecture.md` | 2246-2519 |
| **Zustand Stores** | `zustand_middleware_reference.md` | `frontend_architecture.md` | All |
| **React Query Hooks** | `react_query_websocket.md` | `frontend_architecture.md` | 52-1900 |
| **WebSocket Provider** | `frontend_auth_scaffold.md` | `react_query_websocket.md` | 1815-1895 |
| **Query Provider** | `frontend_auth_scaffold.md` | `react_query_websocket.md` | 1789-1813 |
| **Custom Middleware** | `zustand_middleware_reference.md` | - | 20-560 |
| **Component Patterns** | `component_scaffold_guide.md` | - | 1-5374 |
| **Design Tokens** | - | `design_system.md` | All |
| **User Flows** | - | `user_journey.md` | All |

---

## Tips for Success

### 1. Start Small
Don't try to build all 40 pages at once. Build MVP pages first, then expand.

### 2. Use the Documentation as Spec
Treat `page_architecture.md` like a Figma design file:
- Layout Structure = Component hierarchy
- Key Components = Which ShadCN components to use
- Content = Actual text to display
- States = Loading, error, empty state logic

### 3. Build Components Bottom-Up
1. Build atomic components (Button, Input) - ShadCN handles this
2. Build molecules (TicketCard, AgentCard) - Combine ShadCN components
3. Build organisms (KanbanBoard, DependencyGraph) - Compose molecules
4. Build pages - Compose organisms

### 4. Test with Mock Data First
Before wiring up real backend:
```typescript
// Mock data for development
const mockTickets = [
  { id: '1', title: 'Build Auth', status: 'building', phase_id: 'PHASE_IMPLEMENTATION' },
  { id: '2', title: 'Build API', status: 'testing', phase_id: 'PHASE_TESTING' },
];
```

Once UI works, swap for real API calls.

### 5. Use AI to Scaffold Pages
Since you have detailed specs, you can use AI to generate initial page scaffolds:

**Prompt:**
```
I have a detailed page specification. Generate a Next.js page component.

Page: Kanban Board
Reference: [paste "Kanban Board" section from page_architecture.md]
Design System: [paste relevant colors/spacing from design_system.md]

Generate:
- Next.js App Router page.tsx
- TypeScript
- ShadCN components
- Tailwind styling
```

AI will scaffold ~80% of the page structure. You just wire up logic.

---

## Deployment

### Vercel (Recommended for Next.js)
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel

# Set environment variables in Vercel dashboard
NEXT_PUBLIC_API_URL=https://api.omoios.com
NEXT_PUBLIC_WS_URL=wss://api.omoios.com/ws
```

### Docker (Alternative)
```dockerfile
FROM node:20-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
```

---

## Revised Timeline (With Your Scaffolds)

**Using Your Pre-Built Scaffolds:**

**Solo Developer (Copy-Paste Workflow):**
- **MVP (Auth + Dashboard + Board)**: **3-5 days** (was 3-4 weeks)
- **Full Feature Set (All 40 pages)**: **2-3 weeks** (was 10-12 weeks)
- **Polish & Enhancements**: +1 week

**With AI Assistance (Cursor/Claude):**
- **MVP**: **1-2 days** (was 1-2 weeks)
- **Full Feature Set**: **1-2 weeks** (was 4-6 weeks)
- **Polish**: +3-5 days

**Team of 2-3:**
- **MVP**: **1-2 days** (was 1 week)
- **Full Feature Set**: **1 week** (was 3-4 weeks)
- **Polish**: +2-3 days

**Why So Much Faster:**
- ✅ Auth pages: Complete code ready to copy (6 pages)
- ✅ Providers: QueryProvider, WebSocketProvider ready
- ✅ Stores: Zustand stores with middleware ready
- ✅ Hooks: All React Query hooks defined
- ✅ Components: 80+ component scaffolds ready
- ✅ Middleware: Custom websocketSync, reactQueryBridge ready
- ✅ You're **assembling**, not building from scratch

---

## Next Steps: Rapid Assembly

### Day 1: Project Setup (2 hours)
1. ✅ Run setup script (creates project, installs all deps)
2. ✅ Copy documentation to `docs/` folder in project
3. ✅ Update Tailwind config with design system
4. ✅ Copy providers (Query, WebSocket, Theme) from docs
5. ✅ Update `app/layout.tsx` with providers

### Day 2: Auth Pages (3 hours)
1. ✅ Copy auth layout from `frontend_auth_scaffold.md` (lines 11-31)
2. ✅ Copy login page (lines 33-162)
3. ✅ Copy register page (lines 164-308)
4. ✅ Copy verify-email (lines 310-383)
5. ✅ Update API endpoints to match backend
6. ✅ Test auth flow

### Day 3: Dashboard Shell (4 hours)
1. ✅ Copy dashboard layout (lines 595-670)
2. ✅ Create sidebar navigation
3. ✅ Create header component
4. ✅ Wire up navigation links
5. ✅ Test navigation

### Day 4-5: Kanban Board (8 hours)
1. ✅ Copy Kanban board page (lines 1030-1200)
2. ✅ Copy kanbanStore from `react_query_websocket.md` (lines 2652-2750)
3. ✅ Copy useTickets hooks
4. ✅ Test drag-and-drop
5. ✅ Wire up WebSocket for real-time updates
6. ✅ Test optimistic updates

### Week 2: Remaining Pages
1. ✅ Copy agent pages from component scaffolds
2. ✅ Copy graph component
3. ✅ Copy phase overview pages
4. ✅ Copy statistics pages
5. ✅ Wire up remaining WebSocket events

**Total Time**: **1-2 weeks** (not 10-12 weeks)

**You're not building from scratch—you're assembling pre-built components.**

---

## Pro Tips

### 1. Copy Smart, Not Blind
When copying scaffolds:
- Update API endpoints to match your backend URLs
- Update event types to match your WebSocket events
- Customize text/branding
- Adjust colors if needed (though design system matches)

### 2. Use the Architecture as Reference
`docs/design/frontend/frontend_architecture_shadcn_nextjs.md` is your master plan:
- Directory structure (lines 92-209)
- Middleware stack order (lines 283-299)
- Store architecture (lines 330-348)
- Component mapping (lines 32-89)

### 3. Start with Proven Code
Don't write new implementations of:
- WebSocket integration (already done)
- Zustand middleware (already done)
- React Query setup (already done)
- Auth flow (already done)

Just copy and customize.

### 4. Reference Documents by Line Number
All scaffolds include line numbers. Use them:
- "Copy lines 33-162 from frontend_auth_scaffold.md"
- Much faster than reading the whole doc

---

## Your Documentation Assets (Summary)

**Ready-to-Copy Code (~15,000 lines):**
- ✅ `frontend_auth_scaffold.md` - 6 complete auth pages (1,974 lines)
- ✅ `component_scaffold_guide.md` - 80+ components (5,374 lines)
- ✅ `react_query_websocket.md` - All hooks + providers (2,958 lines)
- ✅ `zustand_middleware_reference.md` - Custom middleware (754 lines)
- ✅ `frontend_architecture_shadcn_nextjs.md` - Architecture guide (348 lines)

**Specifications (~15,000 lines):**
- ✅ `page_architecture.md` - All page specs
- ✅ `user_journey.md` - User flows
- ✅ `page_flow.md` - Navigation flows
- ✅ `design_system.md` - Visual design
- ✅ `project_management_dashboard.md` - Detailed UI/UX

**You have both the spec AND the implementation.** Just copy and assemble.

