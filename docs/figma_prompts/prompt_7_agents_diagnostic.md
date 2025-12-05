# Figma Make Prompt 7: Agent Management & Diagnostic Pages

Build this following engineering best practices:
- Write all code to WCAG AA accessibility standards
- Create and use reusable components throughout
- Use semantic HTML and proper component architecture
- Avoid absolute positioning; use flexbox/grid layouts
- Build actual code components, not static image SVGs
- Keep code clean, maintainable, and well-structured

You are Figma Make. Continue building the OmoiOS application. Foundation through Graph, Phases & Statistics are already built. Now build the Agent Management & Diagnostic Pages section.

**PROJECT CONTEXT:**
OmoiOS is a spec-driven autonomous engineering platform. Use Shadcn UI components with the custom warm theme. Note: Reuse AgentCard pattern from Command Center (Prompt 4A) for consistency.

**SHADCN COMPONENTS TO USE:**
- Card (CardHeader, CardContent, CardFooter) - agent cards, detail panels
- Button (default, outline, ghost) - actions, controls
- Badge - status badges, phase badges
- Progress - alignment score, task progress
- Tabs (TabsList, TabsTrigger, TabsContent) - agent detail tabs
- ScrollArea - timeline scroll, workspace files
- Table - commit list, task list
- Avatar - agent icons
- Collapsible - expandable sections
- Sheet (side="right") - agent detail drawer
- Dialog - intervention modal, confirmations
- Textarea - intervention message input
- Code - code blocks (custom or use prose)

**DESIGN NOTES:**
- Background: bg-background, panels: bg-card
- Agent cards: Card with status icon, reuse from Command Center
- Status: text-warning (⟳), text-success (✓), text-destructive (✗)
- Line changes: font-mono text-xs, text-success/text-destructive
- Code blocks: bg-muted rounded-md p-3 font-mono text-sm

**AGENT MANAGEMENT & DIAGNOSTIC PAGES TO BUILD:**

**1. Agents Overview (`/agents`)**
- Layout: Page header with "Spawn Agent" button, agent metrics cards, agent list table/cards, filters
- Components: Page header ("Agents" title, "Spawn Agent" button), Agent metrics cards (Total, Active, Idle, Stuck, Average Alignment), Filter bar (All, Active, Idle, Stuck, By Phase, Search), Agent list (table or cards), Agent card/row (ID, type, status, phase, current task, alignment score, metrics, actions), Empty state
- Content:
  - Metrics cards: Total Agents "5", Active "3", Idle "1", Stuck "1", Average Alignment "78%"
  - Agent cards: Agent ID and type, Status badge (🟢 Active, 🟡 Idle, 🔴 Stuck), Phase assignment "PHASE_IMPLEMENTATION", Current task "Implement JWT" or "None", Alignment score "85%" (if active), Tasks completed "8", Commits "15", Lines changed "+2,450 -120", Actions [View Details] [Intervene] [Assign Task]
- States: Loading (skeleton cards), Empty ("No agents yet"), Populated (agent list with metrics), Filtered (filtered agents), Error
- Navigation: Click "Spawn Agent" → `/agents/spawn`, Filter agents, Search agents, Click agent card → `/agents/:agentId`, Click "Intervene" → intervention modal, Click "Assign Task" → task assignment modal

**2. Spawn Agent (`/agents/spawn`)**
- Layout: Centered form layout with agent configuration options
- Components: Agent creation form, Agent type selector (worker, validator, monitor), Phase assignment dropdown, Capabilities selector (multi-select), Capacity input, Tags input, Create/Cancel buttons
- Content:
  - Form fields: Agent Type [Worker ▼] [Validator] [Monitor], Phase Assignment [PHASE_IMPLEMENTATION ▼], Capabilities [ ] Python [ ] FastAPI [ ] PostgreSQL [ ] Testing, Capacity [1] (number input), Tags [worker] [implementation] (tag input)
  - Create button: "Spawn Agent"
  - Cancel button: "Cancel"
- States: Empty (form with defaults), Validating (real-time), Creating (spinner), Success (redirect to agent detail), Error
- Navigation: Create → `/agents/:agentId`, Cancel → `/agents`

**3. Agent Detail (`/agents/:agentId`)**
- Layout: Agent header with status, tab navigation, main content area, right sidebar with quick stats
- Components: Agent header (ID, type, status badge, phase badge, actions menu), Tab navigation (Overview, Tasks, Interventions, Workspace, Logs), Overview tab (current task, alignment score, performance metrics), Tasks tab (task history table), Interventions tab (Guardian intervention history), Workspace tab (workspace details, commits, merge conflicts), Logs tab (agent execution logs), Right sidebar (quick stats, health indicators)
- Content:
  - **Overview Tab**: Current task card, Alignment score gauge, Performance metrics (tasks completed, commits, lines changed), Health indicators
  - **Tasks Tab**: Task history table (task, status, completed at)
  - **Interventions Tab**: Intervention history (type, message, timestamp, result)
  - **Workspace Tab**: Workspace path, Git branch name, Commits list, Merge conflicts (if any)
  - **Logs Tab**: Execution logs (searchable, filterable)
- States: Loading (skeleton content), Loaded (agent details), Active (current task and alignment), Idle ("No current task"), Error
- Navigation: Switch tabs, View task details, View intervention details, View workspace commits, View logs, Intervene agent, Assign task

**4. Workspace Detail (`/agents/:agentId/workspace`)**
- Layout: Workspace header, tab navigation (Commits, Merge Conflicts, Settings), main content area
- Components: Workspace header (workspace path, git branch, workspace type), Tab navigation (Commits, Merge Conflicts, Settings), Commits tab (commit list with messages, diffs, timestamps), Merge Conflicts tab (conflict list with resolution status), Settings tab (workspace configuration, retention policies), Commit diff viewer
- Content:
  - **Commits Tab**: Commit list (SHA, message, author, timestamp, files changed), Commit diff viewer
  - **Merge Conflicts Tab**: Conflict list (file, status, resolution method), Resolution details
  - **Settings Tab**: Workspace path (read-only), Git branch (read-only), Workspace type (local/docker/kubernetes/remote), Parent agent (if inherited), Retention policy settings
- States: Loading (skeleton content), Loaded (workspace details), No Conflicts ("No merge conflicts"), Error
- Navigation: Switch tabs, View commit diffs, Resolve merge conflicts, Configure workspace settings, Browse workspace files (future)

**5. Diagnostic Reasoning View (`/diagnostic/ticket/:ticketId`)**
- Layout: Diagnostic header, tab navigation (Timeline, Graph, Details), main content area with reasoning chain
- Components: Diagnostic header (ticket name, "Diagnostic Reasoning" title), Tab navigation (Timeline, Graph, Details), Timeline tab (chronological reasoning chain with events), Graph tab (visual graph showing relationships and reasoning), Details tab (detailed reasoning explanations), Reasoning event cards (discovery, linking, spawning events), Evidence panels (code snippets, logs, agent decisions)
- Content:
  - **Timeline Tab**: Reasoning events in chronological order: "Ticket Created - Reason: Infrastructure needed for auth system", "Task Spawned - Reason: Discovery: Bug found in login flow", "Ticket Linked - Reason: Dependency detected: Auth depends on Database", Each event shows: Timestamp, Event type icon, Reasoning description, Evidence (if available), Related links
  - **Graph Tab**: Visual graph with reasoning annotations, Hover to see reasoning
  - **Details Tab**: Detailed explanations, Agent decision logs, Discovery evidence
- States: Loading (skeleton content), Loaded (reasoning chain), Empty ("No diagnostic data available"), Error
- Navigation: Switch tabs, Expand/collapse reasoning events, View evidence (code, logs), Navigate to related tickets/tasks, Filter by event type, Search reasoning chain

**Requirements:**
- Create reusable AgentCard component
- Implement status badges with pulse animation for Active/Thinking states (use design system state colors)
- Create alignment score gauge component (circular or linear progress)
- Implement agent metrics cards (reusable)
- Create intervention history component
- Implement workspace detail tabs
- Add commit diff viewer component (syntax highlighting)
- Create merge conflict resolution UI
- Implement diagnostic reasoning timeline component
- Add evidence panels for code snippets and logs
- Create reasoning event cards (reusable)
- Implement searchable/filterable logs component
- Add health indicators (visual status indicators)
- Include loading skeletons for all pages
- Make all pages responsive
- Implement proper error handling
- Add empty states with CTAs
- Include toast notifications for actions
- Implement intervention modal (for sending messages, pausing, refocusing agents)
- Add task assignment modal
- Create capabilities multi-select component
- Implement tag input component

Generate all 5 pages as separate React components with full functionality, proper state management, and navigation.

