# Figma Make Prompt 4: Analytics Dashboard & Project Pages

Build this following engineering best practices:
- Write all code to WCAG AA accessibility standards
- Create and use reusable components throughout
- Use semantic HTML and proper component architecture
- Avoid absolute positioning; use flexbox/grid layouts
- Build actual code components, not static image SVGs
- Keep code clean, maintainable, and well-structured

You are Figma Make. Continue building the OmoiOS application. Foundation, design system, authentication, organization pages, and Command Center are already built. Now build the Analytics Dashboard & Project Pages section.

**PROJECT CONTEXT:**
OmoiOS is a spec-driven autonomous engineering platform. The Command Center (`/`) is the primary landing page. The Analytics Dashboard is a SECONDARY page accessed via deliberate navigation. Use Shadcn UI components.

**SHADCN COMPONENTS TO USE:**
- Card (CardHeader, CardContent) - stat cards, spec cards, project cards
- Button - CTAs, quick actions
- Badge - status badges (Draft, Active, Completed)
- Progress - spec progress bars
- Avatar - user avatars in activity feed
- Sidebar - left navigation (reuse from foundation)
- DropdownMenu - project filter, action menus
- Command (cmdk) - Command Palette (Cmd+K)
- ScrollArea - activity feed scrolling
- Skeleton - loading states

**DESIGN NOTES:**
- Background: bg-background, cards: bg-card
- Stats cards: minimal, large numbers, small labels
- Spec cards: Progress component (thin), Badge for status
- Activity feed: ScrollArea with timestamped items
- Navigation: Sidebar with active state on "Analytics"
- Command Palette: Command component with search + recent actions

**ANALYTICS DASHBOARD & PROJECT PAGES TO BUILD:**

**1. Analytics Dashboard (`/analytics`) - Secondary Page**
- Layout: Top navigation bar, left sidebar with main nav, main content area (2-column: overview + activity feed), right sidebar (collapsible activity feed)
- Components: Top nav bar (Logo, Command, Projects, Agents, [Analytics] active, Search, Profile menu), Left sidebar navigation (Home, Projects, Board, Graph, Specs, Stats, Agents, Cost, Audit), Overview section (stats cards: Total Specs, Active Agents, Tickets in Progress, Recent Commits), Active Specs grid (spec cards with progress bars), Quick Actions section (New Spec, New Project buttons), Recent Activity sidebar (collapsible chronological feed), Project Filter dropdown, Command Palette (Cmd+K)
- Content:
  - Page title: "Analytics Dashboard"
  - Project filter: [All Projects ▼]
  - Stats cards: Total Specs "5", Active Agents "3", Tickets in Progress "12", Recent Commits "8"
  - Spec cards: Spec name, description, progress bar (0-100%), status badge (Draft, Requirements, Design, Tasks, Executing, Completed), last updated timestamp, quick actions ([View] [Board])
  - Activity feed: "Spec 'Auth System' requirements approved", "Agent worker-1 completed task 'Setup JWT'", "Discovery: Bug found in login flow", "Guardian intervention sent to worker-2"
- States: Loading (skeleton cards and stats), Empty ("No activity yet" - redirect CTA to Command Center), Populated (overview with specs and activity), Error (error message with retry)
- Navigation: Click spec card → spec workspace, Click "New Spec" → create spec modal/page, Click "New Project" → `/projects/new`, Click activity item → related page, Cmd+K → Command Palette, Click Logo or "Command" → `/` (Command Center)

**2. Projects List (`/projects`)**
- Layout: Header with "Create Project" button, filter/search bar, projects grid/list view toggle
- Components: Page header ("Create Project" button), Filter bar (All, Active, Archived, By Organization), Search input, View toggle (Grid/List), Project cards grid (3 columns desktop, 1 mobile), Project card (thumbnail, name, description, org badge, stats, actions), Empty state
- Content:
  - Page title: "Projects"
  - Project cards: Thumbnail/icon, Project name, Description (truncated), Organization badge, Stats ("X tickets, Y agents active"), Last active ("Updated 2 hours ago")
  - Empty state: "No projects yet. Create your first project to get started."
- States: Loading (skeleton cards), Empty (empty state with CTA), Filtered (filtered results with count), Error
- Navigation: Click project card → `/projects/:id`, Click "Create Project" → `/projects/new`, Filter/search projects

**3. Create Project (`/projects/new`)**
- Layout: Centered form layout with multi-step wizard or single form
- Components: Project creation form, Form sections (Basic Info, Initial Setup, Configuration), Organization selector dropdown, AI-assisted exploration toggle, Form validation, Cancel and Submit buttons
- Content:
  - Page title: "Create New Project"
  - Form fields: Project Name (required), Description (textarea), Organization (dropdown, required), Initial Setup ("Use AI-assisted exploration" checkbox, "Create initial spec" checkbox), Configuration (optional advanced settings)
  - Submit button: "Create Project"
  - Cancel button: "Cancel"
- States: Empty, Validating (real-time), Loading (spinner), Success (redirect to `/projects/:id` or `/projects/:id/explore`), Error
- Navigation: Submit → `/projects/:id` or `/projects/:id/explore` (if AI exploration enabled), Cancel → `/projects`

**4. Project Overview (`/projects/:id`)**
- Layout: Project header with name and settings, main content area with overview cards and quick links, right sidebar with recent activity
- Components: Project header (name, description, settings button, GitHub connection status), Overview stats cards (Tickets, Tasks, Agents, Completion Rate), Quick navigation cards (Board, Graph, Specs, Stats, Agents, Phases), Recent activity feed, Active tickets preview, Active agents preview
- Content:
  - Project name and description
  - Stats cards: Total Tickets "24", Active Tasks "8", Active Agents "3", Completion Rate "65%"
  - Quick nav cards: Kanban Board, Dependency Graph, Spec Workspace, Statistics, Agents, Phases
  - Recent activity: Last 10 events
  - Active tickets: Top 5 tickets by priority
- States: Loading (skeleton content), Loaded (overview with stats), Empty ("Create Your First Ticket" CTA), Error
- Navigation: Click navigation cards → respective pages, Click "Settings" → project settings, Click ticket preview → ticket detail, Click agent preview → agent detail

**5. AI-Assisted Exploration (`/projects/:id/explore`)**
- Layout: Full-page wizard with progress indicator, step-by-step generation, preview panels
- Components: Progress indicator (Step 1: Analyzing, Step 2: Generating Requirements, Step 3: Creating Design), Project analysis panel, Generated requirements preview, Generated design preview, Accept/Edit/Reject buttons per step, Final review panel
- Content:
  - Step 1: "Analyzing project structure...", File tree analysis, Technology stack detection
  - Step 2: Generated EARS-style requirements, Preview panel with edit capability
  - Step 3: Architecture diagrams, Sequence diagrams, Data models
  - Final Review: Combined spec preview
- States: Analyzing (progress spinner), Generating (step progress), Review (generated content with edit options), Saving (save progress), Complete (redirect to spec workspace), Error (error with retry)
- Navigation: Start exploration, Accept step → next step, Reject step → regenerate, Finalize → `/projects/:id/specs/:specId`, Cancel → `/projects/:id`

**Requirements:**
- Use existing layout structure with sidebar navigation
- Implement Command Palette component (Cmd+K keyboard shortcut)
- Create reusable SpecCard and ProjectCard components
- Implement progress bars for spec progress
- Add status badges with appropriate colors (use design system state colors)
- Implement activity feed component (reusable for multiple pages)
- Create stats card component (reusable)
- Implement grid/list view toggle
- Add filter and search functionality
- Include empty states with clear CTAs
- Implement loading skeletons
- Make all pages responsive
- Add toast notifications for success/error states
- Implement multi-step wizard for AI exploration with progress indicator
- Include preview panels with edit capability for generated content

Generate all 5 pages as separate React components with full functionality, proper state management, and navigation.

