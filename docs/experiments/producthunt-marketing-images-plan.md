# Product Hunt Marketing Images Plan

**Created**: 2026-01-20
**Purpose**: Plan for marketing gallery images for OmoiOS Product Hunt launch
**Reference**: Inspired by daily.dev Recruiter's Product Hunt gallery style

---

## Overview

Create a set of 5-7 marketing images showcasing OmoiOS key features with SVG-style UI mockups. These will be used in the Product Hunt gallery alongside the demo video.

### Image Specifications
- **Dimensions**: 1200 x 900 or 1200 x 800 (Product Hunt gallery)
- **Style**: Consistent with existing OG images (dark gold/amber theme OR light cream variant)
- **Format**: SVG-rendered via `@vercel/og` ImageResponse
- **Location**: `frontend/app/og/marketing/` directory

---

## Image 1: Command Center - Natural Language Input

**Headline**: "Describe What You Want Built"
**Subheadline**: "Type a feature request → OmoiOS plans and executes"

**UI Mockup Elements**:
- Clean input field with placeholder: "Add payment processing with Stripe..."
- Model selector dropdown (opus-4.5)
- Repository selector (github.com/acme/webapp)
- Mode toggle (Quick / Spec-Driven)
- Launch button with glow effect

**Key Message**: The starting point - just describe what you need

---

## Image 2: Kanban Board - Real-Time Task Visibility

**Headline**: "Watch Agents Work in Real-Time"
**Subheadline**: "Full visibility into every task, ticket, and agent"

**UI Mockup Elements**:
- 4-column kanban: Backlog | In Progress | Review | Done
- Task cards with:
  - Title (e.g., "Implement Stripe webhook handler")
  - Agent avatar with status indicator (active/idle)
  - Phase badge (Planning/Building/Testing)
  - Priority indicator
- Side panel preview showing agent activity

**Key Message**: Never wonder what your agents are doing

---

## Image 3: Spec Workspace - Structured Requirements

**Headline**: "Specs, Not Vibes"
**Subheadline**: "Structured requirements before a single line of code"

**UI Mockup Elements**:
- Multi-tab interface: Requirements | Design | Tasks | Execution
- Requirements tab active showing:
  - EARS-style requirement blocks
  - Acceptance criteria checklist
  - Phase transition approval button
- Sidebar with spec navigation

**Key Message**: Spec-driven > vibe-driven development

---

## Image 4: Phase Gates - Strategic Approval Points

**Headline**: "Autonomy With Oversight"
**Subheadline**: "Approve at phase transitions, not every keystroke"

**UI Mockup Elements**:
- Visual flow: Requirements → Design → Tasks → Execution
- Gate indicators between phases with checkmarks/pending status
- Approval dialog showing:
  - Phase summary
  - Changes preview
  - Approve/Request Changes buttons
- Activity feed showing recent approvals

**Key Message**: Control where it matters, automation everywhere else

---

## Image 5: Agent Health Dashboard - Self-Healing System

**Headline**: "Agents That Fix Themselves"
**Subheadline**: "Guardian monitors, detects drift, and intervenes automatically"

**UI Mockup Elements**:
- Agent grid showing health status (green/yellow/red)
- Intervention timeline showing:
  - "Agent stuck on test failure → Steering sent"
  - "Constraint violation detected → Corrected"
- Metrics cards: Active Agents | Interventions Today | Avg. Resolve Time

**Key Message**: Self-healing workflows that don't need babysitting

---

## Image 6: Dependency Graph - Interconnected Workflows

**Headline**: "Workflows That Build Themselves"
**Subheadline**: "Tasks discover dependencies and adapt in real-time"

**UI Mockup Elements**:
- Node graph visualization showing:
  - Task nodes with status colors
  - Dependency arrows connecting related tasks
  - Discovery branches spawning from main flow
- Legend: Completed | In Progress | Blocked | Discovered

**Key Message**: Structure emerges from the problem, not predefined plans

---

## Image 7: Terminal + Code View - Agent Workspace

**Headline**: "Full Dev Environment Access"
**Subheadline**: "Watch agents code, test, and debug in isolated sandboxes"

**UI Mockup Elements**:
- Split view:
  - Left: Terminal with real-time output
  - Right: Code editor showing file being modified
- File tree showing changed files
- Sandbox status indicator (Daytona)

**Key Message**: Complete transparency into agent execution

---

## Implementation Priority

1. **Image 2: Kanban Board** - Most visually impactful, shows core value prop
2. **Image 1: Command Center** - Shows the entry point/simplicity
3. **Image 4: Phase Gates** - Key differentiator from competitors
4. **Image 5: Agent Health** - Unique self-healing feature
5. **Image 3: Spec Workspace** - Reinforces spec-driven approach
6. **Image 6: Dependency Graph** - Advanced feature for power users
7. **Image 7: Terminal View** - Technical credibility

---

## Design Notes

### Color Palette (Dark Theme)
- Background: `#1a150d` to `#0f0c08` gradient
- Primary accent: `#FFD04A` (gold)
- Secondary accent: `#FFE78A` (light gold)
- Success: `#50C878` (green)
- Text: `rgba(255, 248, 235, 0.92)`
- Muted: `rgba(255, 236, 205, 0.70)`

### Color Palette (Light Theme)
- Background: `#FFFCF5` to `#FFF8EB` gradient
- Primary accent: `#E8A317` (amber)
- Shadow: `rgba(0, 0, 0, 0.06)`
- Text: `#2d2618`
- Muted: `rgba(45, 38, 24, 0.60)`

### Typography
- Headlines: Montserrat Regular (400), 28-32px
- Subheadlines: Montserrat Light (300), 16-18px
- UI labels: Montserrat Light (300), 12-14px

### Common Elements
- OmoiOS logo in corner (consistent placement)
- Subtle dot pattern background texture
- Soft glow effects on interactive elements
- Rounded corners (14-18px radius)
- Card shadows for depth

---

## File Structure

```
frontend/app/og/marketing/
├── command-center/route.tsx      # Image 1
├── kanban-board/route.tsx        # Image 2
├── spec-workspace/route.tsx      # Image 3
├── phase-gates/route.tsx         # Image 4
├── agent-health/route.tsx        # Image 5
├── dependency-graph/route.tsx    # Image 6
└── agent-workspace/route.tsx     # Image 7
```

---

## Next Steps

1. Start with Image 2 (Kanban Board) as the flagship marketing image
2. Create reusable component patterns (card styles, badges, etc.)
3. Generate dark and light variants for each
4. Review with Playwright screenshots before finalizing
5. Export final images for Product Hunt upload
