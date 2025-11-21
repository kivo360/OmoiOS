# Figma Make Prompt 5: Spec Workspace & Kanban Board Pages

Build this following engineering best practices:
- Write all code to WCAG AA accessibility standards
- Create and use reusable components throughout
- Use semantic HTML and proper component architecture
- Avoid absolute positioning; use flexbox/grid layouts
- Build actual code components, not static image SVGs
- Keep code clean, maintainable, and well-structured

You are Figma Make. Continue building the OmoiOS application. Foundation through Dashboard & Projects are already built. Now build the Spec Workspace & Kanban Board Pages section.

**PROJECT CONTEXT:**
OmoiOS is a spec-driven autonomous engineering platform. Use existing design system components and layout structure.

**SPEC WORKSPACE & KANBAN PAGES TO BUILD:**

**1. Specs List (`/projects/:id/specs`)**
- Layout: Header with "Create Spec" button, filter/search bar, specs grid/list
- Components: Page header ("Create Spec" button), Filter bar (All, Draft, Requirements, Design, Tasks, Executing, Completed), Search input, Spec cards grid (2 columns desktop, 1 mobile), Spec card (name, description, status badge, progress bar, last updated, actions), Empty state
- Content:
  - Page title: "Specs"
  - Spec cards: Spec name, Description (truncated), Status badge (color-coded), Progress bar (0-100%), Last updated timestamp, Quick actions ([View] [Edit] [Export])
  - Empty state: "No specs yet. Create your first spec to get started."
- States: Loading (skeleton cards), Empty (empty state with CTA), Filtered (filtered results), Error
- Navigation: Click spec card → `/projects/:id/specs/:specId`, Click "Create Spec" → create spec modal/page, Click actions menu → Export, Archive, Delete

**2. Spec Workspace (`/projects/:id/specs/:specId`)**
- Layout: Spec header with name and actions, left sidebar with spec switcher, main content area with tabs, right sidebar (collapsible) with spec metadata
- Components: Spec header (name, status badge, export button, settings menu), Left sidebar (spec switcher dropdown, spec list), Tab navigation (Requirements, Design, Tasks, Execution), Requirements tab (structured blocks editor - Notion-style), Design tab (diagram viewer/editor, architecture diagrams), Tasks tab (task breakdown table with dependencies), Execution tab (progress dashboard, running tasks, PRs), Right sidebar (spec metadata, version history, linked tickets)
- Content:
  - **Requirements Tab**: EARS-style requirements blocks, Structured format: "WHEN [condition] THE SYSTEM SHALL [action]", Acceptance criteria blocks
  - **Design Tab**: Architecture diagrams (Mermaid or image), Sequence diagrams, Data models, API specifications
  - **Tasks Tab**: Task breakdown table, Dependencies visualization, Task status indicators
  - **Execution Tab**: Overall progress bar, Test coverage percentage, Running tasks section, Pull Requests section
- States: Loading (skeleton content), Editing (edit mode with save button), Saving (save progress), Saved (success indicator), Error
- Navigation: Switch tabs, Switch specs (via sidebar dropdown), Export spec (Markdown, YAML, PDF), Link/unlink tickets

**3. Kanban Board (`/board/:projectId`)**
- Layout: Board header with filters and view options, horizontal scrolling board with columns, ticket cards in columns, ticket detail drawer (slides from right)
- Components: Board header (project name, filters, view switcher, "Create Ticket" button), Filter bar (Type, Phase, Status, Priority, Search), Board columns (Backlog, Requirements, Implementation, Testing, Done, Blocked), Ticket cards (title, phase badge, priority indicator, assignee, commit stats, blocking indicator), WIP limit indicators per column, Ticket detail drawer (slides from right on click), View switcher (Kanban, List, Graph)
- Content:
  - Board columns: Column name, Ticket count, WIP limit indicator (if exceeded)
  - Ticket cards: Ticket title, Phase badge (color-coded), Priority indicator (CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=gray), Assigned agent name, Commit stats: "+X -Y", Blocking indicator (if blocked)
  - Empty columns: "Drop tickets here"
- States: Loading (skeleton columns), Empty ("Create First Ticket" CTA), Dragging (drag preview and drop zones), Filtered (filtered tickets with count), Error
- Navigation: Drag and drop tickets between columns, Click ticket card → open detail drawer, Click "Create Ticket" → create ticket modal, Toggle view (Kanban/List/Graph), Click column header → column settings

**4. Ticket Detail (`/board/:projectId/:ticketId`)**
- Layout: Ticket header with title and actions, tab navigation, main content area with tab content, right sidebar with ticket metadata
- Components: Ticket header (title, status badge, phase badge, priority indicator, actions menu), Tab navigation (Details, Comments, Tasks, Commits, Blocking, Reasoning), Details tab (description, metadata, history), Comments tab (comment thread, comment editor, mention autocomplete), Tasks tab (task list with status, agent assignment), Commits tab (commit list with diffs), Blocking tab (dependency graph, blocker list, blocked-by list), Reasoning tab (diagnostic reasoning chain, discovery events), Right sidebar (ticket metadata, linked spec, related tickets)
- Content:
  - **Details Tab**: Ticket title and description, Status and phase badges, Priority indicator, Created/updated timestamps, Assigned agent, Linked spec (if any)
  - **Comments Tab**: Comment thread (chronological), Comment editor with @mention support, File attachments
  - **Tasks Tab**: Task list with status, agent, progress
  - **Commits Tab**: Commit list with messages, authors, diffs
  - **Blocking Tab**: Dependency graph visualization, Blocker tickets list, Blocked-by tickets list
  - **Reasoning Tab**: Discovery events timeline, Task spawning reasoning, Ticket linking reasoning
- States: Loading (skeleton content), Loaded (ticket with tabs), Editing (edit mode), Saving (save progress), Error
- Navigation: Switch tabs, Edit ticket, Add comment, View task details, View commit diffs, Add/remove blocking relationships, View diagnostic reasoning, Transition ticket status, Link/unlink related tickets

**Requirements:**
- Implement drag-and-drop functionality for Kanban board (use react-beautiful-dnd or dnd-kit)
- Create reusable TicketCard component
- Implement tab navigation component (reusable)
- Create structured blocks editor for Requirements tab (Notion-style, use contenteditable or rich text editor)
- Implement diagram viewer/editor for Design tab (support Mermaid diagrams)
- Create task breakdown table with dependency visualization
- Implement ticket detail drawer (slide-in from right, overlay)
- Add keyboard navigation for Kanban board (j/k up/down, h/l left/right, Enter to open)
- Implement WIP limit indicators with visual warnings
- Create dependency graph visualization component (for Blocking tab)
- Add comment thread with @mention autocomplete
- Implement commit diff viewer
- Include diagnostic reasoning timeline component
- Make all pages responsive (mobile: single column, tablet/desktop: multi-column)
- Add loading states and skeletons
- Implement proper error handling
- Include empty states with CTAs
- Add toast notifications for actions

Generate all 4 pages as separate React components with full functionality, proper state management, drag-and-drop, and navigation.

