# Figma Make Prompt 6A: Graph & Phase Management Pages

Build this following engineering best practices:
- Write all code to WCAG AA accessibility standards
- Create and use reusable components throughout
- Use semantic HTML and proper component architecture
- Avoid absolute positioning; use flexbox/grid layouts
- Build actual code components, not static image SVGs
- Keep code clean, maintainable, and well-structured

You are Figma Make. Continue building the OmoiOS application. Foundation through Specs & Kanban are already built. Now build the Graph & Phase Management Pages section.

**PROJECT CONTEXT:**
OmoiOS is a spec-driven autonomous engineering platform. Use Shadcn UI components with the custom warm theme.

**SHADCN COMPONENTS TO USE:**
- Card (CardHeader, CardContent) - phase cards, node detail panels
- Button (default, outline, ghost) - actions, navigation
- Badge - status badges, phase badges
- Tabs (TabsList, TabsTrigger, TabsContent) - phase detail tabs
- Input, Textarea, Label - phase forms
- Checkbox - transition checkboxes, terminal phase toggle
- Slider - timeout, WIP limit configuration
- ScrollArea - sidebar filters, long content
- Sheet (side="right") - node detail drawer on graph
- Dialog - create phase modal, confirmations
- Collapsible - expandable phase sections
- Table - task lists, approval lists
- Select - filter dropdowns

**DESIGN NOTES:**
- Background: bg-background, graph canvas: bg-card
- Graph: use @xyflow/react (React Flow), warm node colors
- Phase cards: Card with subtle border, hover:shadow-sm
- Status colors: text-success, text-destructive, text-warning (muted versions)

**PAGES TO BUILD:**

**1. Dependency Graph (`/graph/:projectId`)**
- Layout: Full-page graph canvas, left sidebar filters, right sidebar node details
- Components: Graph canvas (React Flow), Zoom/pan controls, Filter sidebar (Phase, Status, Type, Agent), Node details panel, Legend, Search bar
- Content: Ticket nodes (rectangles, color by status), Task nodes (circles, color by phase), Discovery nodes (diamonds, purple), Dependency edges (blocking), Discovery edges (spawning), Normal flow edges (phase progression)
- States: Loading, Rendering, Empty ("No dependencies yet"), Error
- Navigation: Click node → detail, Pan/zoom, Filter nodes

**2. Ticket Graph (`/graph/:projectId/:ticketId`)**
- Layout: Same as full graph, centered on selected ticket
- Components: Graph canvas (focused), Ticket detail panel, Related tickets highlighted, Path highlighting
- Content: Centered ticket node (highlighted), Blocker tickets (above, red), Blocked tickets (below, orange)
- States: Same as full graph, Focused
- Navigation: Click related ticket → detail, Highlight paths

**3. Phase Overview (`/projects/:projectId/phases`)**
- Layout: Page header, phase cards grid (2-3 columns)
- Components: Header ("Phases" title, "Create Custom Phase" button), Phase cards grid, Phase card (number, name, description, task stats, agent count, discovery indicator, "View Tasks" button), Empty state
- Content: Phase cards show "Phase 1: Requirements Analysis", Description, Task stats "28 total, 22 done, 2 active", Active agents "2 agents working", Discovery "3 new branches spawned", Status badge, "View Tasks →" button
- States: Loading (skeleton), Empty ("No phases configured"), Populated, Error
- Navigation: Click card → `/projects/:projectId/phases/:phaseId`, "View Tasks" → task list, "Create Custom Phase" → `/projects/:projectId/phases/new`

**4. Phase Detail (`/projects/:projectId/phases/:phaseId`)**
- Layout: Phase header, tab navigation, form sections, save/cancel buttons
- Components: Header (phase ID, name, description, edit/save buttons), Tabs (Basic Info, Done Definitions, Expected Outputs, Phase Prompt, Transitions, Configuration), Save/Cancel buttons
- Content: Basic Info (Phase ID read-only, Name, Description, Sequence Order, Terminal checkbox), Done Definitions (criteria list, "+ Add Criterion"), Phase Prompt (large text editor, Markdown, Preview toggle), Transitions (checklist of phase IDs), Configuration (Timeout, Max Retries, Retry Strategy, WIP Limit)
- States: Viewing (read-only), Editing (form enabled), Saving (spinner), Saved, Error
- Navigation: Switch tabs, Save → overview, Cancel → overview

**5. Create Custom Phase (`/projects/:projectId/phases/new`)**
- Layout: Same as Phase Detail, creation mode with phase ID input
- Components: Phase creation form (same tabs), Phase ID input (must start with "PHASE_"), Form validation, Create/Cancel buttons
- Content: Same as Phase Detail + Phase ID input (required, starts with "PHASE_")
- States: Empty, Validating, Creating, Success (redirect), Error
- Navigation: Create → `/projects/:projectId/phases/:phaseId`, Cancel → `/projects/:projectId/phases`

**6. Task Phase Management (`/projects/:projectId/tasks/phases`)**
- Layout: Page header, expandable phase sections, task cards, bulk actions bar
- Components: Header ("Tasks by Phase", filters, search), Filter bar (All Phases, All Status, All Priorities, Search), Expandable phase sections, Task cards, Bulk actions (Select All, Move Selected, Bulk Edit), Empty states
- Content: Phase sections "PHASE_IMPLEMENTATION (28 tasks)", Expand/collapse, Task count "Total: 28, Done: 22, Active: 2", Task cards (description, status badge, agent, priority, timestamp, "Move to Phase ▼")
- States: Loading, Empty, Populated, Filtered, Error
- Navigation: Expand/collapse, Filter/search, Select tasks, "Move to Phase" → modal, Bulk move, Click card → detail

**7. Phase Gate Approvals (`/projects/:projectId/phase-gates`)**
- Layout: Page header, pending approvals list, approval detail modal
- Components: Header ("Phase Gate Approvals", filters), Filter bar (All Phases, Pending, Approved, Rejected), Approval cards, Approval detail modal, Recent approvals
- Content: Approval cards (ticket name/ID, current → requested phase, requested by agent, timestamp, gate criteria ✓/✗, artifacts "code_changes: ✓", "test_coverage: 85% ✓", actions [Review] [Approve] [Reject]), Detail (full request, gate criteria, artifact review, comments, decision buttons)
- States: Loading, Empty ("No pending approvals"), Pending, Reviewing (modal open), Approving, Error
- Navigation: Filter, Click card → detail, Review criteria/artifacts, Approve/Reject, Request info

**Requirements:**
- Use React Flow for graph visualization with zoom/pan
- Create reusable phase card component
- Implement large text editor (Markdown support) for Phase Prompt
- Add JSONB editor for Configuration tab
- Implement expandable/collapsible sections
- Create approval card and detail modal
- Add filter bars (reusable)
- Include loading skeletons, empty states, error handling
- Make all pages responsive
- Include toast notifications

Generate all 7 pages as separate React components with full functionality, proper state management, and navigation.

