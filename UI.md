# UI.md — OmoiOS Frontend Architecture

This document helps contributors understand the frontend codebase quickly. For detailed page-by-page flows, see the deep-dive documentation linked throughout.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Next.js 15 (App Router) |
| UI Components | ShadCN UI (Radix primitives + Tailwind CSS v4) |
| Server State | React Query (TanStack Query) — 60s stale time, 1 retry |
| Client State | Zustand with persist middleware |
| Graphs | React Flow v12 (@xyflow/react) |
| Terminal | xterm.js |
| Analytics | PostHog |
| Error Tracking | Sentry |
| Fonts | Inter (sans), JetBrains Mono (mono) |

## Route Structure

The frontend uses Next.js route groups to separate concerns:

```
frontend/app/
├── (app)/              # Authenticated application — main product
│   ├── command/        # Command Center (primary landing after login)
│   ├── projects/       # Project management
│   │   └── [id]/
│   │       ├── specs/[specId]/  # Spec workflow viewer (most complex page)
│   │       ├── settings/        # Project config (board, GitHub, phases)
│   │       ├── explore/         # Project exploration
│   │       └── stats/           # Project statistics
│   ├── board/[projectId]/       # Kanban ticket board
│   ├── graph/[projectId]/       # Dependency graph visualization
│   ├── sandboxes/               # Sandbox list
│   │   └── sandbox/[sandboxId]/ # Sandbox execution detail (events, preview, chat)
│   ├── agents/                  # Agent management and monitoring
│   │   └── [agentId]/workspace/ # Agent terminal
│   ├── organizations/           # Org management, members, billing, settings
│   ├── settings/                # User settings (profile, security, API keys, appearance)
│   ├── health/                  # Agent health, trajectories, interventions
│   ├── activity/                # Real-time activity feed
│   ├── phases/                  # Workflow phase management
│   ├── prototype/               # Live prototype workspace
│   ├── diagnostic/[entityType]/[entityId]/  # Diagnostic reasoning
│   └── commits/[commitSha]/     # Commit detail
│
├── (auth)/             # Authentication — centered layout, no sidebar
│   ├── login/
│   ├── register/
│   ├── forgot-password/
│   ├── reset-password/
│   ├── verify-email/
│   └── callback/       # OAuth callback
│
├── (dashboard)/        # Root dashboard — redirects to /command
├── onboarding/         # Onboarding wizard (6-step flow)
├── try/                # (Planned) Public prototype workspace
├── blog/               # Blog listing and posts
├── docs/               # Documentation (Fumadocs)
├── pricing/            # Pricing page
└── showcase/[token]/   # Public showcase/demo page
```

## Application Shell

The authenticated app uses a three-column layout:

```
┌──────────────────────────────────────────────────────┐
│ MinimalHeader (breadcrumbs, context, user menu)       │
├─────────┬──────────────────┬─────────────────────────┤
│ IconRail│ ContextualPanel  │ Main Content             │
│  (14w)  │   (16rem)        │   (flex-1)               │
│         │                  │                           │
│ Terminal│ Changes based on │ Route page content        │
│ Folder  │ active section:  │                           │
│ Box     │ - ProjectsPanel  │                           │
│ Building│ - TasksPanel     │                           │
│         │ - SettingsPanel  │                           │
│ ─────── │ - HealthPanel    │                           │
│ Settings│ - GraphFilters   │                           │
│         │ - etc.           │                           │
└─────────┴──────────────────┴─────────────────────────┘
```

**Key files:**
- `components/layout/MainLayout.tsx` — Three-column shell
- `components/layout/IconRail.tsx` — Left icon navigation (4 main + settings)
- `components/layout/ContextualPanel.tsx` — Route-aware sidebar that swaps panels
- `components/layout/MinimalHeader.tsx` — Top bar with breadcrumbs

**Keyboard shortcuts:** `Cmd+1-4` navigate sections, `Cmd+B` collapses the panel.

## Component Organization

```
frontend/components/
├── ui/                  # ShadCN primitives (40+ components)
│                        # Button, Card, Dialog, Tabs, Badge, Skeleton, Toast, etc.
│                        # DO NOT modify these unless updating ShadCN itself.
│
├── layout/              # Application shell (MainLayout, IconRail, ContextualPanel)
├── panels/              # Sidebar panels (ProjectsPanel, TasksPanel, HealthPanel, etc.)
│
├── command/             # Command Center — PromptInput, ModelSelector, WorkflowModeSelector
├── spec/                # Spec workflow — EventTimeline, PhaseProgress, ShareButtons
├── sandbox/             # Sandbox execution — EventRenderer, FileEditCard, ToolUseCard
├── board/               # Kanban board — AgentPanel
├── billing/             # Billing — PricingTable, SubscriptionCard, UpgradeDialog
├── onboarding/          # Onboarding wizard — OnboardingWizard + step components
├── github/              # GitHub integration — RepositoryBrowser, FileBrowser
├── preview/             # Live preview — PreviewPanel (iframe to dev server)
├── prototype/           # Prototype workspace — PrototypeWorkspace (split-view)
├── custom/              # App-specific — AgentCard, TaskCard, FileChangeCard
│
├── landing/             # Marketing landing page components
│   └── TicketJourney, CLIDemo, AgentTerminal, etc.
├── marketing/           # Marketing sections
│   ├── FloatingNavbar
│   └── sections/ (HeroSection, ProductShowcaseSection, NightShiftSection, etc.)
│
├── settings/            # Settings — ConnectedAccounts
├── docs/                # Documentation — mermaid diagram support
└── error-boundary.tsx   # Global error boundary
```

## State Management

### React Query (server state)

All data fetching uses React Query hooks in `frontend/hooks/`. Each hook file covers one domain:

| Hook file | Key hooks | Domain |
|-----------|-----------|--------|
| `useProjects.ts` | `useProjects()`, `useProject(id)`, `useCreateProject()` | Project CRUD |
| `useSpecs.ts` | `useProjectSpecs()`, `useSpec()`, `useApproveRequirements()`, `useExecuteSpecTasks()` | Spec workflow (largest hook file) |
| `useAgents.ts` | `useAgents()`, `useAgentStatistics()` | Agent management |
| `useSandbox.ts` | `useSandboxMonitor()`, `useSandboxTask()` | Sandbox execution |
| `useTickets.ts` | `useTickets()`, `useCreateTicket()` | Ticket CRUD |
| `useBoard.ts` | `useBoard()` | Kanban board state |
| `useGitHub.ts` | `useGitHub()`, `useConnectedRepositories()` | GitHub integration |
| `useOrganizations.ts` | `useOrganizations()` | Org management |
| `useBilling.ts` | — | Billing/subscriptions |
| `useOnboarding.ts` | `useOnboarding()` | Onboarding wizard state (Zustand + server sync) |
| `usePrototype.ts` | — | Prototype workspace sessions |
| `useEvents.ts` | `useEvents()` | Real-time system events |
| `useMonitor.ts` | — | Health monitoring |

### Zustand (client state)

- `useOnboarding.ts` — Onboarding wizard state with `persist` middleware and server sync
- Infrastructure exists for `useKanbanStore`, `useAgentStore`, `useUIStore` but React Query is the primary source

### API Client

`frontend/lib/api/client.ts` — Centralized HTTP client with:
- JWT token management (localStorage, auto-refresh 2 min before expiry)
- Auth cookie for middleware (`omoios_auth_state`)
- `ApiError` class with status, message, details
- Sentry breadcrumbs on errors

Domain-specific files in `lib/api/` (one per domain: `projects.ts`, `specs.ts`, `agents.ts`, etc.)

## Providers (Context)

Wrapped in `app/layout.tsx`:

```
RootProvider (Fumadocs)
  └── QueryProvider (React Query + devtools)
       └── StoreProvider (Zustand)
            └── ThemeProvider (dark/light mode)
                 └── AuthProvider (JWT tokens)
                      └── PostHogProvider (analytics)
                           └── ErrorBoundary
                                └── Toaster (Sonner)
```

## Design System

### Colors (CSS variables)

Semantic tokens defined in CSS with light/dark variants:

- `--color-primary`, `--color-secondary`, `--color-destructive` — Actions
- `--color-muted`, `--color-accent` — UI accents
- `--color-background`, `--color-foreground`, `--color-border` — Layout
- `--color-success`, `--color-warning`, `--color-info` — Status
- `--color-sidebar`, `--color-sidebar-*` — Sidebar theming
- `--color-landing-*` — Marketing page colors
- `--color-chart-1` through `--color-chart-5` — Data visualization

### Spacing and radius

- `--radius-lg: 0.5rem` (cards, large buttons)
- `--radius-md: 6px` (medium elements)
- `--radius-sm: 4px` (small elements)

### ShadCN components (40+)

Before creating new UI primitives, check `components/ui/`. Available: Button, Card, Dialog, Tabs, Badge, Skeleton, Toast (Sonner), Progress, Dropdown, Select, Input, Textarea, Form (react-hook-form), Popover, Tooltip, Sheet, Accordion, Collapsible, ScrollArea, Resizable, Calendar, Breadcrumb, Pagination, Alert, and more.

## Key Pages

### Command Center (`/command`)

The primary landing page after login. Three-step workflow: select project/repo, select mode (quick/full/sandbox), enter prompt. Includes model selector, branch selection, and recent agents sidebar.

**Components**: `command/PromptInput`, `command/ModelSelector`, `command/WorkflowModeSelector`, `command/RecentAgentsSidebar`

### Spec Viewer (`/projects/[id]/specs/[specId]`)

The most complex page — multi-phase workflow viewer with tabs per phase (EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC). Includes real-time event streaming, approval buttons, task cards, and sharing.

**Components**: `spec/EventTimeline`, `spec/PhaseProgress`, `spec/ShareButtons`, `spec/SpecCompletionModal`

### Sandbox Detail (`/sandbox/[sandboxId]`)

Real-time execution viewer showing agent events (file edits, bash commands, test runs), live preview iframe, and agent chat. Uses `EventRenderer` to display events with syntax highlighting.

**Components**: `sandbox/EventRenderer`, `sandbox/FileEditCard`, `sandbox/ToolUseCard`, `preview/PreviewPanel`

### Onboarding (`/onboarding`)

6-step wizard: Welcome → GitHub → Repo → First Spec → Plan → Complete. State managed by `useOnboarding.ts` (Zustand + server sync). Step components in `components/onboarding/steps/`.

## Detailed Documentation

For comprehensive page-by-page flows and user journeys, see:

### Page Flows (`docs/page_flows/`)

Detailed page-by-page navigation documentation covering 67 flows across the entire application. Each document describes the exact UI elements, API calls, state transitions, and error handling for a set of related pages.

| Document | Coverage |
|----------|----------|
| [README.md](docs/page_flows/README.md) | Index of all 67 flows with quick navigation |
| [01_authentication.md](docs/page_flows/01_authentication.md) | Registration, login, OAuth, email verification |
| [02_projects_specs.md](docs/page_flows/02_projects_specs.md) | Project creation, spec-driven workflow |
| [03_agents_workspaces.md](docs/page_flows/03_agents_workspaces.md) | Agent management, spawning, workspace isolation |
| [04_kanban_tickets.md](docs/page_flows/04_kanban_tickets.md) | Kanban board, ticket operations, search |
| [05_organizations_api.md](docs/page_flows/05_organizations_api.md) | Org management, API key management |
| [06_visualizations.md](docs/page_flows/06_visualizations.md) | Dependency graph, statistics, activity timeline |
| [07_phases.md](docs/page_flows/07_phases.md) | Phase management, gates, custom phases |
| [08a_comments_collaboration.md](docs/page_flows/08a_comments_collaboration.md) | Comments and collaboration |
| [08b_ticket_operations.md](docs/page_flows/08b_ticket_operations.md) | Ticket search, creation, status transitions |
| [08c_github_integration.md](docs/page_flows/08c_github_integration.md) | GitHub OAuth, repository connection |
| [09a_diagnostic_reasoning.md](docs/page_flows/09a_diagnostic_reasoning.md) | Diagnostic reasoning view |
| [10_command_center.md](docs/page_flows/10_command_center.md) | Command center, project selection, recent agents |
| [10a_monitoring_system.md](docs/page_flows/10a_monitoring_system.md) | Health dashboard, trajectories, interventions |
| [11_cost_management.md](docs/page_flows/11_cost_management.md) | Cost dashboard, budgets, forecasting |
| [12_agent_memory.md](docs/page_flows/12_agent_memory.md) | Memory search, learned patterns, ACE workflow |
| [13_sandbox_system.md](docs/page_flows/13_sandbox_system.md) | Sandbox list and detail (real-time events, preview) |
| [14_billing.md](docs/page_flows/14_billing.md) | Billing dashboard, Stripe checkout, subscriptions |
| [15_settings_expanded.md](docs/page_flows/15_settings_expanded.md) | Appearance, integrations, notifications, security |
| [16_public_pages.md](docs/page_flows/16_public_pages.md) | Landing page, pricing, blog, docs, showcase |
| [17_activity_timeline.md](docs/page_flows/17_activity_timeline.md) | Real-time activity feed |

### User Journeys (`docs/user_journey/`)

End-to-end user flows from onboarding through feature completion, organized by journey phase rather than individual pages.

| Document | Coverage |
|----------|----------|
| [README.md](docs/user_journey/README.md) | Index with quick navigation by topic |
| [00_overview.md](docs/user_journey/00_overview.md) | 60-second story, core promise, dashboard layout |
| [00a_demo_flow.md](docs/user_journey/00a_demo_flow.md) | 90-second video demo script |
| [01_onboarding.md](docs/user_journey/01_onboarding.md) | Onboarding and first project setup |
| [01a_onboarding_conversion.md](docs/user_journey/01a_onboarding_conversion.md) | Onboarding conversion funnel analysis |
| [02_feature_planning.md](docs/user_journey/02_feature_planning.md) | Feature request and planning flow |
| [03_execution_monitoring.md](docs/user_journey/03_execution_monitoring.md) | Autonomous execution and monitoring |
| [04_approvals_completion.md](docs/user_journey/04_approvals_completion.md) | Approval gates and phase transitions |
| [05_optimization.md](docs/user_journey/05_optimization.md) | Ongoing monitoring and optimization |
| [06_key_interactions.md](docs/user_journey/06_key_interactions.md) | Command palette, real-time updates, interventions |
| [06a_monitoring_system.md](docs/user_journey/06a_monitoring_system.md) | Guardian and monitoring system |
| [07_phase_system.md](docs/user_journey/07_phase_system.md) | Phase system, custom phases, discovery branching |
| [08_user_personas.md](docs/user_journey/08_user_personas.md) | Personas: engineering manager, senior IC, CTO |
| [09_design_principles.md](docs/user_journey/09_design_principles.md) | Visual design principles and success metrics |
| [10_additional_flows.md](docs/user_journey/10_additional_flows.md) | Error handling, notifications, collaboration, mobile |
| [11_cost_memory_management.md](docs/user_journey/11_cost_memory_management.md) | Cost dashboard, budgets, memory insights |
| [12_billing_subscription.md](docs/user_journey/12_billing_subscription.md) | Subscription tiers, credits, invoices |
| [13_public_marketing_pages.md](docs/user_journey/13_public_marketing_pages.md) | Landing page, pricing, blog, docs, showcase |
| [14_settings_personalization.md](docs/user_journey/14_settings_personalization.md) | Appearance, notifications, security, integrations |
| [15_prototype_diagnostic.md](docs/user_journey/15_prototype_diagnostic.md) | Prototype workspace and diagnostic reasoning |

### How these relate

- **Page flows** = "What does each page do?" — API calls, state, UI elements, error handling
- **User journeys** = "How does a user accomplish a goal?" — Cross-page flows, decision points, personas
- **This document (UI.md)** = "How is the frontend built?" — Architecture, components, patterns, conventions

## Adding New Pages

1. Determine the route group: `(app)` for authenticated, `(auth)` for auth flows, root for public
2. Create `page.tsx` in the appropriate `app/` subdirectory
3. If the page needs a sidebar panel, add it to `components/panels/` and register in `ContextualPanel.tsx`
4. Create domain hooks in `hooks/` and API functions in `lib/api/`
5. Use existing ShadCN components from `components/ui/` — don't create new primitives
6. Document the page flow in `docs/page_flows/` if it's a significant new feature
