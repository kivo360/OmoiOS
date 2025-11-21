# OmoiOS Frontend Package - Complete Index

**Created**: 2025-11-21
**Status**: Package Index
**Purpose**: Master index of all frontend code, scaffolds, and documentation ready for assembly

---

## What You Have: Complete Frontend Infrastructure

**Total Code**: ~15,000 lines of ready-to-copy implementations
**Total Specs**: ~15,000 lines of detailed specifications
**Total Pages**: 40+ pages fully designed and scaffolded
**Estimated Assembly Time**: 1-2 weeks (not months)

---

## 📦 Package Contents

### 1. Product Specifications (Copy to Figma/Dev Team)

| Document | Lines | Purpose | Status |
|----------|-------|---------|--------|
| `docs/app_overview.md` | 145 | Product concept, features, user flow | ✅ Complete |
| `docs/page_architecture.md` | 1,000+ | Detailed specs for all 40 pages | ✅ Complete |
| `docs/design_system.md` | 284 | Colors, typography, components | ✅ Complete |
| `docs/user_journey.md` | 1,858 | Complete user flows | ✅ Complete |
| `docs/page_flow.md` | 3,491 | Page-by-page navigation | ✅ Complete |
| `docs/user_flows_summary.md` | 494 | Flow summary | ✅ Complete |

---

### 2. Technical Architecture (Copy to Project)

| Document | Lines | Purpose | Copy To |
|----------|-------|---------|---------|
| `docs/design/frontend/frontend_architecture_shadcn_nextjs.md` | 348 | Next.js 15 architecture | Reference doc |
| `docs/design/frontend/react_query_websocket.md` | 2,958 | React Query hooks + WebSocket | `src/hooks/*` |
| `docs/design/frontend/zustand_middleware_reference.md` | 754 | Custom Zustand middleware | `src/middleware/*` |
| `docs/design/frontend/component_scaffold_guide.md` | 5,374 | 80+ component scaffolds | `src/components/*` |
| `docs/design/auth/frontend_auth_scaffold.md` | 1,974 | Complete auth pages | `src/app/(auth)/*` |
| `docs/design/services/dependency_graph_service.md` | 773 | Graph visualization logic | `src/components/graph/*` |

---

### 3. Ready-to-Copy Code Scaffolds

#### Authentication Pages (6 pages)
**Source**: `docs/design/auth/frontend_auth_scaffold.md`

| Page | Lines | Copy To | Features |
|------|-------|---------|----------|
| Auth Layout | 11-31 | `app/(auth)/layout.tsx` | Centered card design |
| Login | 33-162 | `app/(auth)/login/page.tsx` | Email/password, OAuth, validation |
| Register | 164-308 | `app/(auth)/register/page.tsx` | Email/password, validation, terms |
| Verify Email | 310-383 | `app/(auth)/verify-email/page.tsx` | Resend email, change email |
| Forgot Password | 385-488 | `app/(auth)/forgot-password/page.tsx` | Email reset request |
| Reset Password | 490-593 | `app/(auth)/reset-password/page.tsx` | Password reset form |

#### Dashboard Pages (10+ pages)
**Source**: `docs/design/auth/frontend_auth_scaffold.md`

| Page | Lines | Copy To | Features |
|------|-------|---------|----------|
| Dashboard Layout | 595-670 | `app/(dashboard)/layout.tsx` | Header + Sidebar + Providers |
| Root Layout | 672-750 | `app/layout.tsx` | All providers (Query, WS, Theme) |
| Projects List | 752-850 | `app/(dashboard)/projects/page.tsx` | Grid view, filters, search |
| Project Detail | 852-962 | `app/(dashboard)/projects/[id]/page.tsx` | Overview cards, quick nav |
| Kanban Board | 1030-1200 | `app/(dashboard)/board/[projectId]/page.tsx` | Drag-and-drop, real-time |
| Ticket Detail | 1202-1382 | `app/(dashboard)/board/[projectId]/[ticketId]/page.tsx` | Tabs, comments, commits |
| Agents List | 1387-1485 | `app/(dashboard)/agents/page.tsx` | Agent cards, filters |
| Agent Detail | 1489-1624 | `app/(dashboard)/agents/[agentId]/page.tsx` | Trajectory, interventions |
| Statistics | 1629-1740 | `app/(dashboard)/projects/[id]/stats/page.tsx` | Charts, metrics |
| Phase Overview | Check component guide | `app/(dashboard)/projects/[id]/phases/page.tsx` | Phase cards |

#### Providers (3 essential)
**Source**: `docs/design/auth/frontend_auth_scaffold.md`

| Provider | Lines | Copy To | Purpose |
|----------|-------|---------|---------|
| QueryProvider | 1789-1813 | `src/providers/QueryProvider.tsx` | React Query setup |
| WebSocketProvider | 1815-1895 | `src/providers/WebSocketProvider.tsx` | WebSocket + Query integration |
| StoreProvider | 1897-1973 | `src/providers/StoreProvider.tsx` | Zustand hydration |

---

### 4. Zustand Stores with Advanced Middleware

**Source**: `docs/design/frontend/zustand_middleware_reference.md`

| Store | Lines (Middleware) | Lines (Store) | Copy To | Features |
|-------|-------------------|---------------|---------|----------|
| websocketSync | 20-137 | - | `src/middleware/websocket-sync.ts` | Real-time sync |
| reactQueryBridge | 171-330 | - | `src/middleware/react-query-bridge.ts` | Zustand ↔ RQ sync |
| uiStore | - | component_scaffold: 4884-4970 | `src/stores/uiStore.ts` | Theme, sidebar, modals, toasts |
| kanbanStore | - | react_query_websocket: 2652-2750 | `src/stores/kanbanStore.ts` | Full middleware stack |
| agentStore | - | react_query_websocket: 276-342 | `src/stores/agentStore.ts` | Agent monitoring |
| searchStore | - | Check component guide | `src/stores/searchStore.ts` | Search with history |

**Middleware Stack (Already Defined)**:
```typescript
devtools(persist(websocketSync(reactQueryBridge(temporal(subscribeWithSelector(immer(
  (set, get) => ({ /* your store */ })
)))))))
```

---

### 5. React Query Hooks (All Entities)

**Source**: `docs/design/frontend/react_query_websocket.md`

| Hook Category | Lines | Copy To | Hooks Included |
|---------------|-------|---------|----------------|
| Query Keys | 9-47 | `src/lib/query-keys.ts` | projectKeys, ticketKeys, agentKeys, etc. |
| Project Hooks | 52-95 | `src/hooks/useProjects.ts` | useProjects, useProject, useCreateProject |
| Ticket Hooks | 96-167 | `src/hooks/useTickets.ts` | useTickets, useTicket, useCreateTicket, useMoveTicket |
| Task Hooks | 168-215 | `src/hooks/useTasks.ts` | useTasks, useTask, useCreateTask |
| Graph Hooks | 216-275 | `src/hooks/useGraph.ts` | useDependencyGraph |
| Agent Hooks | 485-830 | `src/hooks/useAgents.ts` | useAgents, useAgent, useSpawnAgent, useTrajectory |
| Search Hooks | 1200-1350 | `src/hooks/useSearch.ts` | useTicketSearch, useFilters |
| Pagination Hooks | 1351-1550 | `src/hooks/usePagination.ts` | useInfiniteTickets |

---

### 6. Component Scaffolds (80+ Components)

**Source**: `docs/design/frontend/component_scaffold_guide.md`

| Component Category | Lines | Components Included |
|--------------------|-------|---------------------|
| Kanban | 464-1115 | KanbanBoard, BoardColumn, TicketCard, CreateTicketDialog, DroppableBoardColumn |
| Graph | 1122-1455 | DependencyGraph, GraphToolbar, NodeDetailPanel, GraphLegend |
| Search | 1867-2053 | SearchCommand (CMDK), SearchResults, SearchFilters |
| Agents | 2246-2519 | AgentCard, AgentStatusWidget, AgentMetrics, AgentInterventionPanel |
| Statistics | 2526-2885 | StatsOverview, StatsChart, MetricCard, TrendSparkline |
| Activity Feed | 2892-3200 | ActivityTimeline, EventCard, EventFilters |
| Comments | 3207-3434 | CommentThread, CommentEditor, MentionInput |
| Terminal | 4558-4879 | TerminalStream (Xterm.js), TerminalToolbar |
| Code Highlight | 4283-4557 | CodeHighlighter, SyntaxHighlight, DiffViewer |

**Total**: 80+ production-ready components with full TypeScript, Tailwind, and ShadCN integration.

---

## 🚀 Assembly Instructions

### Quick Assembly (1-2 Days for MVP)

```bash
# === STEP 1: Create Project (5 minutes) ===
npx create-next-app@latest omoios-ui --typescript --tailwind --app --use-npm
cd omoios-ui

# === STEP 2: Install Dependencies (10 minutes) ===
# Copy complete dependency list from docs/design/frontend/frontend_architecture_shadcn_nextjs.md
npm install @tanstack/react-query@^5.0.0 @tanstack/react-query-devtools@^5.0.0 \
  zustand@^4.5.0 immer@^10.0.3 zundo@^2.0.0 zustand-pub@^1.0.0 lz-string@^1.5.0 \
  @dnd-kit/core@^6.1.0 @dnd-kit/sortable@^8.0.0 reactflow@^11.10.0 \
  framer-motion@^11.0.0 date-fns@^2.30.0 recharts@^2.9.0 \
  react-syntax-highlighter@^15.5.0 xterm@^5.3.0 xterm-addon-fit@^0.8.0 \
  xterm-addon-web-links@^0.9.0 next-themes@^0.2.1

# === STEP 3: Initialize ShadCN (5 minutes) ===
npx shadcn@latest init
# Install all components
npx shadcn@latest add button card input badge avatar dropdown-menu dialog \
  tabs toast table sheet scroll-area separator navigation-menu breadcrumb \
  label select checkbox radio-group switch textarea form progress accordion \
  alert-dialog popover tooltip calendar alert command

# === STEP 4: Create Folder Structure (1 minute) ===
mkdir -p src/{components,lib,hooks,stores,types,providers,middleware}
mkdir -p src/components/{ui,shared,layout,kanban,graph,agents,phases,project}
mkdir -p docs

# === STEP 5: Copy Documentation (2 minutes) ===
# Copy all docs from senior_sandbox to omoios-ui
cp -r ../senior_sandbox/docs/{app_overview,page_architecture,design_system}.md docs/
cp -r ../senior_sandbox/docs/design docs/

# === STEP 6: Copy Environment Variables (1 minute) ===
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:18000
NEXT_PUBLIC_WS_URL=ws://localhost:18000/ws
EOF

# === STEP 7: Start Copying Code (Day 1-2) ===
# See "File Copy Checklist" below
```

---

## 📋 File Copy Checklist

### Phase 1: Providers & Infrastructure (30 minutes)

```bash
# 1. Copy Query Provider
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 1789-1813)
# TO: src/providers/QueryProvider.tsx

# 2. Copy WebSocket Provider  
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 1815-1895)
# TO: src/providers/WebSocketProvider.tsx

# 3. Copy Store Provider
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 1897-1973)
# TO: src/providers/StoreProvider.tsx

# 4. Copy Root Layout with Providers
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 672-750)
# TO: src/app/layout.tsx

# 5. Copy Query Keys Factory
# FROM: docs/design/frontend/react_query_websocket.md (lines 9-47)
# TO: src/lib/query-keys.ts

# 6. Copy WebSocket Middleware
# FROM: docs/design/frontend/zustand_middleware_reference.md (lines 20-137)
# TO: src/middleware/websocket-sync.ts

# 7. Copy React Query Bridge
# FROM: docs/design/frontend/zustand_middleware_reference.md (lines 171-330)
# TO: src/middleware/react-query-bridge.ts
```

### Phase 2: Auth Pages (1 hour)

```bash
# 8. Copy Auth Layout
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 11-31)
# TO: src/app/(auth)/layout.tsx

# 9. Copy Login Page
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 33-162)
# TO: src/app/(auth)/login/page.tsx

# 10. Copy Register Page
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 164-308)
# TO: src/app/(auth)/register/page.tsx

# 11. Copy Verify Email
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 310-383)
# TO: src/app/(auth)/verify-email/page.tsx

# 12. Copy Forgot Password
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 385-488)
# TO: src/app/(auth)/forgot-password/page.tsx

# 13. Copy Reset Password
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 490-593)
# TO: src/app/(auth)/reset-password/page.tsx
```

### Phase 3: Dashboard & Kanban (4 hours)

```bash
# 14. Copy Dashboard Layout
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 595-670)
# TO: src/app/(dashboard)/layout.tsx

# 15. Copy UI Store
# FROM: docs/design/frontend/component_scaffold_guide.md (lines 4884-4970)
# TO: src/stores/uiStore.ts

# 16. Copy Kanban Store (with full middleware stack)
# FROM: docs/design/frontend/react_query_websocket.md (lines 2652-2750)
# TO: src/stores/kanbanStore.ts

# 17. Copy Kanban Board Page
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 1030-1200)
# TO: src/app/(dashboard)/board/[projectId]/page.tsx

# 18. Copy Kanban Components
# FROM: docs/design/frontend/component_scaffold_guide.md (lines 464-1115)
# TO: src/components/kanban/*
#   - KanbanBoard.tsx
#   - BoardColumn.tsx
#   - TicketCard.tsx
#   - CreateTicketDialog.tsx
```

### Phase 4: Hooks & API (2 hours)

```bash
# 19. Copy Ticket Hooks
# FROM: docs/design/frontend/react_query_websocket.md (lines 96-167)
# TO: src/hooks/useTickets.ts

# 20. Copy Agent Hooks
# FROM: docs/design/frontend/react_query_websocket.md (lines 485-830)
# TO: src/hooks/useAgents.ts

# 21. Copy Project Hooks
# FROM: docs/design/frontend/react_query_websocket.md (lines 52-95)
# TO: src/hooks/useProjects.ts

# 22. Copy Task Hooks
# FROM: docs/design/frontend/react_query_websocket.md (lines 168-215)
# TO: src/hooks/useTasks.ts

# 23. Copy Graph Hooks
# FROM: docs/design/frontend/react_query_websocket.md (lines 216-275)
# TO: src/hooks/useGraph.ts
```

### Phase 5: Remaining Pages (1 week)

```bash
# 24. Copy Projects List
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 752-850)
# TO: src/app/(dashboard)/projects/page.tsx

# 25. Copy Project Detail
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 852-962)
# TO: src/app/(dashboard)/projects/[id]/page.tsx

# 26. Copy Ticket Detail
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 1202-1382)
# TO: src/app/(dashboard)/board/[projectId]/[ticketId]/page.tsx

# 27. Copy Agents List
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 1387-1485)
# TO: src/app/(dashboard)/agents/page.tsx

# 28. Copy Agent Detail
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 1489-1624)
# TO: src/app/(dashboard)/agents/[agentId]/page.tsx

# 29. Copy Statistics Page
# FROM: docs/design/auth/frontend_auth_scaffold.md (lines 1629-1740)
# TO: src/app/(dashboard)/projects/[id]/stats/page.tsx

# 30-40. Copy remaining pages from component_scaffold_guide.md
# (Dependency Graph, Search, Phase Management, etc.)
```

---

## 🎯 Fastest Path to Working App

### Day 1: Foundation (4 hours)
1. ✅ Run setup script (create project, install deps)
2. ✅ Copy Tailwind config with design system
3. ✅ Copy 3 providers (Query, WebSocket, Store)
4. ✅ Copy root layout with providers
5. ✅ Copy query keys factory
6. ✅ Test providers working

### Day 2: Auth Flow (4 hours)
1. ✅ Copy auth layout
2. ✅ Copy all 6 auth pages
3. ✅ Create API client (basic fetch wrapper)
4. ✅ Test login/register flow (with mock API if backend not ready)

### Day 3: Dashboard (4 hours)
1. ✅ Copy dashboard layout (header + sidebar)
2. ✅ Copy UI store
3. ✅ Create navigation links
4. ✅ Test navigation

### Day 4-5: Kanban Board (8 hours)
1. ✅ Copy kanban store with full middleware
2. ✅ Copy kanban board page
3. ✅ Copy ticket hooks
4. ✅ Test drag-and-drop
5. ✅ Wire up WebSocket
6. ✅ Test real-time updates

### Week 2: Remaining Features (20 hours)
1. ✅ Copy all remaining pages (projects, agents, stats, graph, phases)
2. ✅ Copy all hooks
3. ✅ Copy remaining components
4. ✅ Test all flows
5. ✅ Polish and fix bugs

**Total Time: 1-2 weeks** for complete working app.

---

## 📚 Documentation Organization

### Specifications (For Product/Design Team)
```
docs/
├── app_overview.md              # Product vision (2 sentences)
├── page_architecture.md         # All 40 pages detailed
├── design_system.md             # Visual design system
├── user_journey.md              # User flows
├── page_flow.md                 # Navigation flows
└── user_flows_summary.md        # Flow summary
```

### Technical Implementation (For Dev Team)
```
docs/design/frontend/
├── frontend_architecture_shadcn_nextjs.md    # Architecture master plan
├── react_query_websocket.md                  # Hooks + WebSocket
├── zustand_middleware_reference.md           # Custom middleware
├── component_scaffold_guide.md               # 80+ components
└── frontend_auth_scaffold.md                 # Auth pages

docs/design/auth/
└── frontend_auth_scaffold.md                 # Complete auth flow
```

### Implementation Guides
```
docs/
├── frontend_implementation_guide.md          # This guide (updated)
├── FRONTEND_PACKAGE.md                       # This file (package index)
└── design/frontend/
    ├── mission_control_exploration.md        # Mission Control design
    ├── density_roadmap.md                    # Progressive enhancement
    └── workflow_interconnection_validation.md # Hephaestus pattern validation
```

---

## 🎁 What You Can Do With This Package

### Option 1: Build Next.js App Yourself
1. Follow the assembly instructions above
2. Copy code from scaffolds
3. Customize as needed
4. Deploy to Vercel

**Time**: 1-2 weeks
**Control**: Full customization

---

### Option 2: Give to Another Developer
1. Zip the entire `docs/` folder
2. Include `FRONTEND_PACKAGE.md` (this file)
3. Include `frontend_implementation_guide.md`
4. Developer follows assembly instructions

**Time**: 1-2 weeks for them
**Benefits**: Complete handoff package

---

### Option 3: Use AI to Generate
1. Give AI the complete documentation package
2. Prompt: "Build Next.js app from these scaffolds"
3. AI copies code from scaffolds into project structure
4. You review and customize

**Time**: 2-3 days (with validation)
**Benefits**: Fastest path

---

### Option 4: Use Figma Make to Generate (Your Plan)
1. Copy design system → Figma Make
2. Copy page architecture → Figma Make
3. Copy user flows → Figma Make
4. Figma Make generates Next.js code
5. Merge generated code with your scaffolds

**Time**: Variable (depends on Figma Make output quality)
**Benefits**: Visual-first design process

---

## 💡 Recommendations

### For Fastest Results:
1. **Use scaffolds directly** (don't rebuild what's done)
2. **Start with auth pages** (6 pages, 1 hour to copy)
3. **Add kanban board** (already has full middleware stack)
4. **Wire up WebSocket** (provider is ready)
5. **Copy remaining pages** as needed

### Key Files That Unlock Everything:
1. ✅ `providers/QueryProvider.tsx` - Enables all React Query hooks
2. ✅ `providers/WebSocketProvider.tsx` - Enables real-time updates
3. ✅ `middleware/websocket-sync.ts` - Enables Zustand WebSocket sync
4. ✅ `middleware/react-query-bridge.ts` - Enables Zustand ↔ React Query sync
5. ✅ `stores/kanbanStore.ts` - Example of full middleware stack working together

Copy these 5 files first, and everything else builds on top.

---

## 📦 Creating a Distribution Package

### Option: Create Documentation Zip

```bash
# From senior_sandbox directory
cd docs
zip -r ../omoios-frontend-package.zip \
  app_overview.md \
  page_architecture.md \
  design_system.md \
  user_journey.md \
  page_flow.md \
  user_flows_summary.md \
  design/frontend/ \
  design/auth/ \
  design/services/dependency_graph_service.md \
  frontend_implementation_guide.md \
  FRONTEND_PACKAGE.md

# Result: omoios-frontend-package.zip (all docs + scaffolds)
```

**Contents**:
- All specifications
- All scaffolds
- All architecture docs
- Implementation guide
- This package index

**Usage**: Unzip, read FRONTEND_PACKAGE.md, follow instructions.

---

## ✅ Validation Checklist

Before starting development, verify you have:

- [ ] `docs/app_overview.md` - Product overview
- [ ] `docs/page_architecture.md` - All 40 page specs
- [ ] `docs/design_system.md` - Design system
- [ ] `docs/design/frontend/frontend_architecture_shadcn_nextjs.md` - Architecture
- [ ] `docs/design/frontend/react_query_websocket.md` - Hooks (2,958 lines)
- [ ] `docs/design/frontend/zustand_middleware_reference.md` - Middleware (754 lines)
- [ ] `docs/design/frontend/component_scaffold_guide.md` - Components (5,374 lines)
- [ ] `docs/design/auth/frontend_auth_scaffold.md` - Auth pages (1,974 lines)

**If you have all 8 documents, you have everything you need.**

---

## Summary

**What You Have:**
- ✅ Complete product specifications
- ✅ Detailed page architecture for 40+ pages
- ✅ Full design system
- ✅ User flows and journeys
- ✅ **15,000+ lines of ready-to-copy code**
- ✅ Custom Zustand middleware
- ✅ Complete React Query setup
- ✅ WebSocket integration
- ✅ 80+ component scaffolds
- ✅ 6 complete auth pages
- ✅ Kanban board with full features

**What You Need to Do:**
1. Create Next.js project
2. Copy code from scaffolds
3. Customize branding/API endpoints
4. Test and deploy

**Time Estimate**: 1-2 weeks (not months).

**You're not building from scratch—you're assembling a pre-fabricated system.**

