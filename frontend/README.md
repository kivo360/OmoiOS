# OmoiOS Frontend

Next.js 15 frontend for OmoiOS autonomous engineering platform.

## Status

✅ **Foundation Complete** - Fresh Next.js project set up with all providers and basic auth structure.

### What's Been Set Up

1. ✅ Fresh Next.js 15 project with TypeScript and Tailwind CSS
2. ✅ All dependencies installed (React Query, Zustand, ShadCN, etc.)
3. ✅ ShadCN UI initialized with 32 components
4. ✅ Providers created:
   - QueryProvider (React Query)
   - WebSocketProvider (WebSocket connection)
   - StoreProvider (Zustand hydration)
   - ThemeProvider (next-themes)
5. ✅ Root layout with all providers integrated
6. ✅ Auth layout created
7. ✅ Login page created

### Next Steps (From FRONTEND_PACKAGE.md)

#### Remaining Auth Pages
- [ ] Register page (`app/(auth)/register/page.tsx`)
- [ ] Verify Email page (`app/(auth)/verify-email/page.tsx`)
- [ ] Forgot Password page (`app/(auth)/forgot-password/page.tsx`)
- [ ] Reset Password page (`app/(auth)/reset-password/page.tsx`)

**Source**: `docs/design/auth/frontend_auth_scaffold.md`

#### Middleware & Stores
- [ ] WebSocket sync middleware (`middleware/websocket-sync.ts`)
- [ ] React Query bridge middleware (`middleware/react-query-bridge.ts`)
- [ ] UI Store (`stores/uiStore.ts`)
- [ ] Kanban Store (`stores/kanbanStore.ts`)
- [ ] Agent Store (`stores/agentStore.ts`)

**Sources**:
- `docs/design/frontend/zustand_middleware_reference.md`
- `docs/design/frontend/react_query_websocket.md`

#### React Query Hooks
- [ ] Query keys factory (`lib/query-keys.ts`)
- [ ] Project hooks (`hooks/useProjects.ts`)
- [ ] Ticket hooks (`hooks/useTickets.ts`)
- [ ] Task hooks (`hooks/useTasks.ts`)
- [ ] Graph hooks (`hooks/useGraph.ts`)
- [ ] Agent hooks (`hooks/useAgents.ts`)

**Source**: `docs/design/frontend/react_query_websocket.md`

#### Dashboard Pages
- [ ] Dashboard layout (`app/(dashboard)/layout.tsx`)
- [ ] Projects list (`app/(dashboard)/projects/page.tsx`)
- [ ] Project detail (`app/(dashboard)/projects/[id]/page.tsx`)
- [ ] Kanban board (`app/(dashboard)/board/[projectId]/page.tsx`)
- [ ] Ticket detail (`app/(dashboard)/board/[projectId]/[ticketId]/page.tsx`)
- [ ] Agents list (`app/(dashboard)/agents/page.tsx`)
- [ ] Agent detail (`app/(dashboard)/agents/[agentId]/page.tsx`)

**Source**: `docs/design/auth/frontend_auth_scaffold.md`

#### Components
- [ ] Kanban components (`components/kanban/*`)
- [ ] Graph components (`components/graph/*`)
- [ ] Agent components (`components/agents/*`)
- [ ] Layout components (`components/layout/*`)

**Source**: `docs/design/frontend/component_scaffold_guide.md`

## Quick Start

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Visit: http://localhost:3000
```

## Environment Variables

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:18000
NEXT_PUBLIC_WS_URL=ws://localhost:18000/ws
```

## Documentation

See `../docs/FRONTEND_PACKAGE.md` for complete code index with line numbers.

## Project Structure

```
frontend/
├── app/                  # Next.js App Router pages
│   ├── (auth)/          # Authentication routes
│   │   ├── login/
│   │   └── ...
│   └── layout.tsx       # Root layout with providers
├── components/           # React components
│   ├── ui/              # ShadCN UI components
│   └── ...
├── providers/           # React providers
│   ├── QueryProvider.tsx
│   ├── WebSocketProvider.tsx
│   ├── StoreProvider.tsx
│   └── ThemeProvider.tsx
├── hooks/               # React Query hooks (TODO)
├── stores/              # Zustand stores (TODO)
├── middleware/          # Zustand middleware (TODO)
└── lib/                 # Utilities
```

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **UI Library**: ShadCN UI (Radix UI + Tailwind CSS)
- **State**: Zustand + React Query
- **Real-Time**: WebSocket integration
- **Graph**: React Flow
- **Animations**: Framer Motion

