# Figma Make Prompt 6B: Statistics & Activity Pages

Build this following engineering best practices:
- Write all code to WCAG AA accessibility standards
- Create and use reusable components throughout
- Use semantic HTML and proper component architecture
- Avoid absolute positioning; use flexbox/grid layouts
- Build actual code components, not static image SVGs
- Keep code clean, maintainable, and well-structured

You are Figma Make. Continue building the OmoiOS application. Foundation through Graph & Phase Management (Prompt 6A) are already built. Now build the Statistics & Activity Pages section.

**PROJECT CONTEXT:**
OmoiOS is a spec-driven autonomous engineering platform. Use Shadcn UI components with the custom warm theme.

**SHADCN COMPONENTS TO USE:**
- Card (CardHeader, CardContent) - stat cards, chart containers
- Tabs (TabsList, TabsTrigger, TabsContent) - statistics tabs
- Button (outline, ghost) - export, date range
- Badge - event type badges
- ScrollArea - activity timeline scroll
- Select - date range selector, filters
- Popover - date picker (with Calendar)
- Calendar - date range selection
- Avatar - user avatars in activity
- Separator - timeline markers
- Skeleton - loading states for charts

**CHARTS:**
- Use Recharts library with custom theme colors
- Chart colors from CSS variables: --chart-1 through --chart-5
- Muted palette, consistent with warm design

**DESIGN NOTES:**
- Background: bg-background, chart containers: bg-card
- Timeline: vertical ScrollArea with Separator between groups
- Event cards: compact, icon + text + timestamp (text-muted-foreground)
- Export: Button variant="outline" with download icon

**PAGES TO BUILD:**

**1. Statistics Dashboard (`/projects/:projectId/stats`)**
- Layout: Page header, tab navigation, main content with metrics sections, charts
- Components: Header ("Statistics" title, date range selector), Tabs (Overview, Tickets, Agents, Code, Cost, Phases), Overview tab (metrics cards, summary charts), Tickets tab (statistics, completion rates, cycle times), Agents tab (performance metrics, alignment scores), Code tab (change statistics, test coverage, commits), Cost tab (LLM costs, resource usage), Phases tab (performance metrics, efficiency, bottlenecks), Charts (line, bar, pie - use recharts), Export button
- Content:
  - **Overview**: Total Tickets, Tasks, Agents, Completion Rate, Average Cycle Time, Summary charts
  - **Tickets**: Tickets by phase chart, Completion rates by type, Cycle time distribution
  - **Agents**: Performance table, Alignment scores, Tasks completed per agent
  - **Code**: Lines changed chart, Test coverage trend, Commits over time
  - **Cost**: LLM costs by phase, Resource usage graphs, Budget status
  - **Phases**: Performance overview, Efficiency metrics, Bottlenecks, Discovery activity
- States: Loading (skeleton charts), Loaded, No Data ("No data available"), Error
- Navigation: Switch tabs, Select date range, Filter metrics, Hover charts, Export (PDF, CSV), Drill down

**2. Activity Timeline (`/projects/:projectId/activity`)**
- Layout: Page header with filters, timeline feed (vertical), event cards, infinite scroll
- Components: Header ("Activity Timeline", filters), Filter bar (All Events, Discoveries, Phase Transitions, Agent Actions, Memory Operations, Commits, Test Results), Date range selector, Timeline feed (vertical, chronological), Event cards (icon, event type, description, timestamp, related links), Load more / infinite scroll, Empty state
- Content: Event cards show icon (color-coded), Event type badge "Discovery", "Phase Transition", "Memory Saved", Description "Agent worker-1 discovered optimization opportunity", Timestamp "2 hours ago", Links [View Ticket] [View Task] [View Discovery]
- States: Loading (skeleton), Empty ("No activity yet"), Filtered (with count), Loading More, Error
- Navigation: Filter by type, Select date range, Click event → related page, Scroll to load more, Search timeline

**Requirements:**
- Create reusable chart components (line, bar, pie - use recharts or similar)
- Implement date range selector component
- Create timeline feed component (reusable, vertical layout)
- Add infinite scroll functionality
- Implement export functionality (PDF, CSV)
- Create filter bars (reusable)
- Include loading skeletons, empty states, error handling
- Make all pages responsive
- Include toast notifications
- Add hover interactions for charts (show details on hover)

Generate both pages as separate React components with full functionality, proper state management, and navigation.

