# Figma Make Prompt 4A: Command Center (Primary Landing)

Build this following engineering best practices:
- Write all code to WCAG AA accessibility standards
- Create and use reusable components throughout
- Use semantic HTML and proper component architecture
- Avoid absolute positioning; use flexbox/grid layouts
- Build actual code components, not static image SVGs
- Keep code clean, maintainable, and well-structured

You are Figma Make. Continue building the OmoiOS application. Foundation, design system, authentication, and organization pages are already built. Now build the Command Center - the PRIMARY landing page for authenticated users.

**PROJECT CONTEXT:**
OmoiOS is a spec-driven autonomous engineering platform. The Command Center is the action-first entry point where users quickly start tasks. Use Shadcn UI components with the custom warm theme.

**SHADCN COMPONENTS TO USE:**
- Sidebar (SidebarProvider, Sidebar, SidebarContent, SidebarGroup) - agent history
- Button (default, outline, ghost, icon) - New Agent, Submit, actions
- Input - search agents, prompt input
- Textarea - main prompt input (custom styling)
- Avatar (AvatarImage, AvatarFallback) - profile avatar
- DropdownMenu - model selector
- Popover - repo/branch selector
- ScrollArea - sidebar agent list
- Badge - repo badge, branch badge
- Separator - between time groups
- Sheet (side="left") - mobile sidebar
- Tooltip - icon button hints

**DESIGN REFERENCE:**
Match Cursor BG Agent aesthetic - warm cream bg-background (#F5F5F0), minimal header, prominent left Sidebar with agent history, centered prompt input.

**COMMAND CENTER PAGES TO BUILD:**

**1. Command Center (`/` - Authenticated Primary Landing)**
- Layout: Minimal top bar (right-aligned), left sidebar (Recent Agents - collapsible 220px), main content area (centered prompt input max-width 700px)
- Background: Warm cream #F5F5F0, generous whitespace
- Components: 
  - Minimal top bar: Right side only - "Dashboard" text link, Profile avatar (32px circle)
  - Logo: Left side, small icon (20px)
  - Recent Agents sidebar: 
    - Search input at top ("Search agents...")
    - Filter/sort icons (subtle, right of search)
    - "New Agent" button (primary, full-width, icon + text)
    - Time group headers (Today, This Week, This Month - uppercase, tiny, muted)
    - Agent cards (status icon ⟳/✓/✗ + task name + time, below: +X -Y line changes in green/red + repo name muted)
    - Bottom sections: "Errored", "Expired" filters
    - Settings gear + Help question mark icons at very bottom
  - Centered prompt area:
    - Large textarea input (placeholder: "Ask Cursor to build, fix bugs, explore")
    - Below input left: Model selector dropdown ("Opus 4.5" with chevron)
    - Below input right: Attach file icon, Submit arrow-up button (accent bg)
    - Below that: Project/repo selector (folder icon + "kivo360/sensei-games" + branch icon + "main")
- Content:
  - Input placeholder: "Ask Cursor to build, fix bugs, explore"
  - Model selector shows current model
  - Repo selector shows owner/repo-name format
  - Agent cards show: task name (truncated), time ago (2h, 1d, 3d, 1w), line changes (+1539 -209 in green/red), repo name
- States: Ready (default), Loading (subtle spinner in submit button), Success (redirect), Error (toast)
- Navigation: Submit → `/agents/:agentId`, Click agent → `/agents/:agentId`, Dashboard → `/analytics`

**2. Unified Project/Repo Selector (Component)**
- Style: Subtle text button with folder icon, not heavy dropdown
- Layout: Click to open popover/dropdown, search at top, grouped sections
- Components:
  - Trigger: Folder icon + "owner/repo-name" + chevron (muted text style)
  - Branch indicator: Branch icon + "main" (separate, also muted)
  - Dropdown panel: White surface, shadow md, radius lg
  - Search input at top of panel
  - PROJECTS section header (uppercase, tiny, muted)
  - Project items (name + repo + ticket count)
  - REPOSITORIES section header
  - Repo items (+ prefix, name, Public/Private subtle badge)
  - Connect action at bottom
- States: Closed, Open, Searching, Loading
- Behavior: Select project → updates selector display, Select repo → creates project

**3. Recent Agents Sidebar (Component)**
- Style: Matches Cursor sidebar exactly - warm bg, minimal cards
- Layout: 220px width, full height, collapsible
- Components:
  - Search input ("Search agents..." placeholder, subtle border)
  - Filter/sort icon buttons (right of search, ghost style)
  - "New Agent" button (full-width, primary style with edit icon)
  - Time group headers (TODAY, THIS WEEK, THIS MONTH - 11px uppercase #9B9B9B)
  - Agent cards:
    - Row 1: Status icon (⟳ yellow for in-progress, ✓ for complete) + Task name (14px, truncated) + Time (12px, muted, right-aligned)
    - Row 2: Line changes (+1539 -209 in JetBrains Mono, green/red) + dot separator + repo name (muted)
  - Section dividers (subtle 1px line)
  - Bottom filters: "Errored", "Expired" (text links, muted)
  - Footer: Settings gear icon + Help ? icon (ghost buttons, bottom-left)
- States: Expanded (220px), Collapsed (icon strip ~48px), Loading (skeleton cards)
- Hover: Agent cards get subtle bg #F0F0EC

**4. Task Submission Flow**
- Style: No heavy overlay - just subtle loading state in submit button
- Submit button: Transforms to spinner while processing
- On success: Smooth redirect to agent detail page
- On error: Toast notification (bottom-right, subtle)

**Requirements:**
- Match Cursor BG Agent aesthetic exactly (warm cream, minimal, low contrast)
- Command Center is PRIMARY landing (not dashboard)
- Sidebar: 220px, warm background, clean agent cards with line change stats
- Prompt area: Centered (max-width 700px), large textarea, subtle controls below
- Use JetBrains Mono for line counts (+X -Y)
- Status icons: ⟳ (in-progress), ✓ (complete), ✗ (failed)
- Colors: Use design system warm neutrals, git green/red for line changes
- No heavy shadows or bright accent colors
- Generous whitespace throughout
- Responsive: Sidebar collapses to icons on tablet, hides on mobile
- Keyboard: Enter to submit, Cmd+K for command palette
- Smooth transitions (150ms ease) for hover states and sidebar collapse

Generate all components with full functionality matching the Cursor design reference.
