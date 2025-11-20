# Frontend Architecture: Next.js 15 + ShadCN UI

**Created**: 2025-05-19
**Status**: Design Document
**Purpose**: Defines the frontend architecture, component mapping to ShadCN UI, and Next.js 15 App Router directory structure.

## 1. Technology Stack

- **Framework**: Next.js 15 (App Router)
- **UI Library**: ShadCN UI (Radix UI + Tailwind CSS)
- **Styling**: Tailwind CSS
- **State Management**: 
  - **Zustand** (client state) with middleware:
    - `zustand/middleware/persist` - Persistent state
    - `zustand/middleware/devtools` - Redux DevTools integration
    - `zustand/middleware/immer` - Immutable state updates
    - `zustand/middleware/subscribeWithSelector` - Selective subscriptions
    - Custom `websocketSync` middleware - Real-time synchronization
    - Custom `reactQueryBridge` middleware - React Query integration
    - `zundo` - Advanced undo/redo with time-travel
    - `zustand-pub` - Cross-tab synchronization (optional)
  - **React Query** (server state) with WebSocket integration
- **Animations**: Framer Motion
- **Icons**: Lucide React
- **Graphs**: React Flow
- **Drag & Drop**: dnd-kit (accessible drag and drop)
- **Terminal**: Xterm.js with addons (fit, web-links, search, unicode11, serialize)
- **Code Highlighting**: react-syntax-highlighter with Prism
- **Date Utilities**: date-fns

## 2. ShadCN Component Mapping

This section maps the functional components identified in the Project Management Dashboard design to specific ShadCN UI components to ensure consistency and speed up development.

### Core Layout & Navigation
| Functional Component | ShadCN Component(s) | Notes |
|----------------------|---------------------|-------|
| **Sidebar** | `Sheet` (mobile), `Sidebar` (custom w/ `Button` + `ScrollArea`) | Sidebar navigation with collapsible sections. |
| **Top Navigation** | `NavigationMenu`, `Avatar`, `DropdownMenu` | User profile, settings, global project switcher. |
| **Breadcrumbs** | `Breadcrumb` | Navigation path tracking. |
| **Theme Toggle** | `Button` (icon), `DropdownMenu` | Light/Dark mode switcher. |
| **Notifications** | `Popover`, `ScrollArea`, `Card` | Notification center dropdown. |

### Kanban Board
| Functional Component | ShadCN Component(s) | Notes |
|----------------------|---------------------|-------|
| **Kanban Board Container** | `ScrollArea` | Horizontal scrolling for columns. |
| **Kanban Column** | `Card` (container), `Badge` (count) | Column layout. |
| **Ticket Card** | `Card`, `Badge` (priority/phase), `Avatar` (assignee), `Separator` | The main unit of work. |
| **WIP Indicator** | `Progress` | Visual indicator of column capacity. |
| **Add Ticket Button** | `Button` (ghost/outline) | Quick add action at bottom of column. |
| **Column Menu** | `DropdownMenu` | Column actions (edit, delete, sort). |

### Dependency Graph
| Functional Component | ShadCN Component(s) | Notes |
|----------------------|---------------------|-------|
| **Graph Container** | `Card` (wrapper) | Wraps the React Flow canvas. |
| **Graph Controls** | `Tooltip`, `Button` | Zoom in/out, fit view controls. |
| **Node Details Panel** | `Sheet` (side drawer) | Slide-out panel when clicking a node. |
| **Filter Toolbar** | `ToggleGroup` or `Select` | Filter nodes by status/type. |

### Project Management
| Functional Component | ShadCN Component(s) | Notes |
|----------------------|---------------------|-------|
| **Project List** | `Table` (list view) or `Card` (grid view) | Display projects. |
| **Project Card** | `Card`, `Progress` (completion), `Badge` (status) | Grid item for project. |
| **Create Project Modal** | `Dialog`, `Form`, `Input`, `Textarea`, `Select` | Form to create new project. |
| **Project Settings** | `Tabs`, `Form`, `Switch`, `Input` | Tabbed settings page. |

### AI & Exploration
| Functional Component | ShadCN Component(s) | Notes |
|----------------------|---------------------|-------|
| **Chat Interface** | `ScrollArea` (messages), `Textarea`, `Button` | Chat window for AI interactions. |
| **Message Bubble** | `Card` (styled) | Individual chat messages. |
| **Document Viewer** | `Card`, `ScrollArea` | Markdown rendering area. |
| **Approval Controls** | `Alert`, `Button` | Approve/Reject/Feedback actions. |
| **Exploration Progress** | `Progress` or `Steps` (custom using `Separator` + icons) | Visual progress tracker. |

### Common UI Elements
| Functional Component | ShadCN Component(s) | Notes |
|----------------------|---------------------|-------|
| **Search Bar** | `Command` (CMDK) | Global search modal/input. |
| **Status Badge** | `Badge` | Colored badges for status/priority. |
| **User Avatar** | `Avatar` | User profile images/initials. |
| **Toast Notifications** | `Sonner` or `Toast` | Success/error feedback. |
| **Confirmation Dialog** | `AlertDialog` | Destructive action confirmation. |
| **Date Picker** | `Calendar`, `Popover` | Due date selection. |
| **Tabs** | `Tabs` | Switching views (Board/Graph/List). |
| **Filters** | `Select`, `Popover`, `Checkbox` | Data filtering controls. |

## 3. Next.js 15 Directory Structure (App Router)

We follow a feature-based organization where possible, leveraging Next.js 15's `app` directory conventions.

```
app/
├── (auth)/                     # Authentication routes group
│   ├── login/
│   │   └── page.tsx            # Login page
│   ├── layout.tsx              # Auth layout (centered card)
│   └── loading.tsx             # Auth loading state
│
├── (dashboard)/                # Protected dashboard routes group
│   ├── layout.tsx              # Dashboard shell (Sidebar, Header, AuthCheck)
│   ├── loading.tsx             # Global dashboard loading
│   ├── error.tsx               # Global dashboard error boundary
│   │
│   ├── page.tsx                # / -> redirects to /projects or /overview
│   ├── overview/               # System Overview
│   │   └── page.tsx
│   │
│   ├── projects/               # Project Management
│   │   ├── page.tsx            # Project list
│   │   ├── new/                # New project wizard
│   │   │   └── page.tsx
│   │   ├── [projectId]/        # Specific project context
│   │   │   ├── page.tsx        # Project overview (redirects to board or overview)
│   │   │   ├── layout.tsx      # Project-specific layout (ProjectHeader, Tabs)
│   │   │   ├── board/          # Kanban Board
│   │   │   │   └── page.tsx
│   │   │   ├── graph/          # Dependency Graph
│   │   │   │   └── page.tsx
│   │   │   ├── specs/          # Specifications & Docs
│   │   │   │   ├── page.tsx    # List of specs
│   │   │   │   └── [specId]/   # Spec viewer/editor
│   │   │   │       └── page.tsx
│   │   │   ├── stats/          # Project Statistics
│   │   │   │   └── page.tsx
│   │   │   ├── agents/         # Project-specific Agents
│   │   │   │   └── page.tsx
│   │   │   ├── explore/        # AI Exploration Mode
│   │   │   │   └── page.tsx
│   │   │   └── settings/       # Project Settings
│   │   │       └── page.tsx
│   │
│   ├── tickets/                # Global Ticket View (optional/admin)
│   │   └── [ticketId]/         # Ticket Detail (often accessed via modal, but needs page)
│   │       └── page.tsx
│   │
│   ├── agents/                 # Global Agent Management
│   │   ├── page.tsx            # All agents list
│   │   └── [agentId]/
│   │       └── page.tsx        # Agent detail & trajectory
│   │
│   ├── search/                 # Global Search Results
│   │   └── page.tsx
│   │
│   └── settings/               # User/App Settings
│       ├── page.tsx            # Redirect to profile
│       ├── profile/
│       │   └── page.tsx
│       └── notifications/
│           └── page.tsx
│
├── api/                        # Next.js Route Handlers (Proxy/BFF if needed)
│   └── ...
│
├── layout.tsx                  # Root layout (Providers: Theme, Query, etc.)
└── global.css                  # Tailwind imports
```

## 4. Component Directory Structure (`src/components`)

We organize components by "scope": `ui` (ShadCN base), `shared` (app-wide reuse), and feature-specific folders.

```
src/
├── components/
│   ├── ui/                     # ShadCN Base Components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── sheet.tsx
│   │   ├── scroll-area.tsx
│   │   └── ... (all shadcn components)
│   │
│   ├── shared/                 # Shared Application Components
│   │   ├── UserAvatar.tsx
│   │   ├── StatusBadge.tsx
│   │   ├── PriorityIcon.tsx
│   │   ├── SearchCommand.tsx
│   │   └── ThemeToggle.tsx
│   │
│   ├── layout/                 # Shell Components
│   │   ├── AppSidebar.tsx
│   │   ├── TopHeader.tsx
│   │   └── PageHeader.tsx
│   │
│   ├── kanban/                 # Kanban Feature Components
│   │   ├── BoardContainer.tsx
│   │   ├── BoardColumn.tsx
│   │   ├── TicketCard.tsx
│   │   └── CreateTicketDialog.tsx
│   │
│   ├── graph/                  # Graph Feature Components
│   │   ├── GraphView.tsx
│   │   ├── NodeTypes.tsx
│   │   └── GraphToolbar.tsx
│   │
│   ├── project/                # Project Feature Components
│   │   ├── ProjectCard.tsx
│   │   ├── CreateProjectForm.tsx
│   │   └── ProjectStats.tsx
│   │
│   └── exploration/            # AI Exploration Components
│       ├── ChatInterface.tsx
│       ├── DocumentPreview.tsx
│       └── ProgressSteps.tsx
```

## 5. Client-Side Data Fetching Strategy

We will use **React Query (TanStack Query)** for all client-side data fetching, caching, and optimistic updates. This maps directly to the API hooks defined in the implementation plan.

- **Queries**: Fetch data (Board, Projects, Tickets).
- **Mutations**: Create/Update actions (Move Ticket, Create Project).
- **Optimistic Updates**: Immediately update UI before server confirmation (essential for Kanban drag-and-drop).
- **WebSocket Integration**: `useWebSocket` hook will subscribe to events and invalidate/update React Query cache.

## 6. Key Dependencies

```json
{
  "dependencies": {
    "next": "15.x",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "lucide-react": "^0.292.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0",
    "tailwindcss-animate": "^1.0.7",
    "@radix-ui/react-avatar": "^1.0.4",
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-dropdown-menu": "^2.0.6",
    "@radix-ui/react-scroll-area": "^1.0.5",
    "@radix-ui/react-slot": "^1.0.2",
    "@radix-ui/react-tooltip": "^1.0.7",
    "@tanstack/react-query": "^5.0.0",
    "@tanstack/react-query-devtools": "^5.0.0",
    "@dnd-kit/core": "^6.1.0",
    "@dnd-kit/sortable": "^8.0.0",
    "@dnd-kit/utilities": "^3.2.0",
    "reactflow": "^11.10.0",
    "zustand": "^4.5.0",
    "immer": "^10.0.3",
    "zundo": "^2.0.0",
    "zustand-pub": "^1.0.0",
    "lz-string": "^1.5.0",
    "date-fns": "^2.30.0",
    "recharts": "^2.9.0",
    "framer-motion": "^11.0.0",
    "react-syntax-highlighter": "^15.5.0",
    "@types/react-syntax-highlighter": "^15.5.11",
    "xterm": "^5.3.0",
    "xterm-addon-fit": "^0.8.0",
    "xterm-addon-web-links": "^0.9.0",
    "xterm-addon-search": "^0.13.0",
    "xterm-addon-unicode11": "^0.6.0",
    "xterm-addon-serialize": "^0.11.0",
    "xterm-addon-image": "^0.6.0",
    "xterm-addon-ligatures": "^0.7.0",
    "next-themes": "^0.2.1"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.3.0"
  }
}
```

## 7. Zustand Middleware Architecture

### 7.1 Middleware Stack

The application uses a layered middleware approach for Zustand stores:

```typescript
// Middleware order (outermost to innermost):
devtools(           // 1. Redux DevTools integration
  persist(          // 2. localStorage/sessionStorage persistence
    websocketSync(  // 3. Real-time WebSocket synchronization
      reactQueryBridge(  // 4. React Query cache integration
        timeTravel(      // 5. Time-travel debugging (dev only)
          subscribeWithSelector(  // 6. Performance optimization
            immer(               // 7. Immutable updates (innermost)
              (set, get) => ({ /* store implementation */ })
            )
          )
        )
      )
    )
  )
)
```

### 7.2 Available Custom Middleware

#### `websocketSync` Middleware
Synchronizes Zustand state with WebSocket events in real-time:
- Listens to specific WebSocket event types
- Transforms incoming messages to state updates
- Optionally syncs local state changes back to server
- Supports both object merge and immer-style updates

#### `reactQueryBridge` Middleware
Bidirectional sync between Zustand and React Query:
- Triggers React Query invalidations on state changes
- Syncs React Query cache data to Zustand store
- Supports optimistic updates
- Configurable invalidation rules

#### `timeTravel` Middleware (Development)
Undo/redo support with state history:
- Maintains state history (configurable max)
- Provides `undo()`, `redo()`, `reset()` actions
- Only enabled in development mode
- Can navigate to specific historical state

#### Advanced Persistence Options
- `compressedStorage` - LZ-string compression for large state
- `encryptedStorage` - Client-side encryption (requires key)
- `robustStorage` - Multi-fallback (localStorage → sessionStorage → memory)

### 7.3 Store Architecture

**Core Stores**:
- `uiStore` - Global UI state (theme, sidebar, modals, toasts)
- `kanbanStore` - Kanban board state with drag-and-drop
- `agentStore` - Agent selection, filters, health monitoring
- `searchStore` - Search state with history persistence
- `terminalStore` - Multi-session terminal management
- `monitoringStore` - System-wide metrics and coherence

**Store Features**:
- Type-safe throughout with TypeScript
- SSR-compatible with manual hydration
- Selective subscriptions for performance
- Cross-tab synchronization (optional)
- Automatic React Query integration
- Real-time WebSocket updates

