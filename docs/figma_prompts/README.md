# Figma Make Prompts for OmoiOS Application

This directory contains 11 sequential prompts designed to build the complete OmoiOS application UI using Figma Make. Each prompt is approximately 4,000 characters and builds upon the previous one.

## Prompt Structure

Each prompt includes:
- Engineering best practices (WCAG AA, reusable components, semantic HTML, flexbox/grid, etc.)
- Project context and design system references
- Detailed page specifications with components, content, states, and navigation
- Requirements for implementation

## Component Framework

All prompts use **Shadcn UI** (https://ui.shadcn.com) with **Tailwind CSS v4**:

**Tailwind v4 Key Features:**
- CSS-first configuration via `@theme` directive (no tailwind.config.js)
- Native CSS variables and OKLCH color space
- CSS Layers (`@layer base`, `@layer components`, `@layer utilities`)
- Modern CSS: native nesting, container queries, `:has()`, etc.
- Import via `@import "tailwindcss";`

**Shadcn Patterns:**
- Radix UI primitives for accessibility
- `cn()` utility for class merging, `cva()` for variants
- Composable component patterns

**Key Shadcn Components Used**:
- Layout: Sidebar, Sheet, ScrollArea, Separator
- Forms: Input, Textarea, Select, Checkbox, RadioGroup, Switch, Label, Form
- Feedback: Toast/Sonner, Dialog, AlertDialog, Popover, Tooltip
- Data Display: Card, Badge, Avatar, Table, Progress
- Navigation: Tabs, DropdownMenu, Command (cmdk)

## Usage Instructions

1. **Start with Prompt 1**: Foundation & Design System
   - This establishes the base components, layout system, and theming
   - Builds all reusable UI components (Buttons, Inputs, Cards, Badges, etc.)
   - Sets up dark mode and responsive layout structure

2. **Continue Sequentially**: Prompts 2-8 build upon previous work
   - Each prompt references components and patterns from earlier prompts
   - Build pages in the order specified for best results

3. **Copy Each Prompt**: 
   - Open the prompt file
   - Copy the entire contents (including the header with engineering practices)
   - Paste into Figma Make
   - Each prompt should be ~4,000 characters

## Prompt Breakdown

### Prompt 1: Foundation & Design System
**Pages**: None (foundation only)
**Components**: All core UI components, layout system, theming
**Key Deliverables**: 
- Button, Input, Card, Badge, Avatar, Modal, Toast components
- Layout components (Header, Sidebar, MainContentArea)
- Navigation components
- Dark mode toggle
- Complete design system implementation

### Prompt 2: Authentication Pages
**Pages**: 7 pages
- Landing Page, Register, Login, Login OAuth, Verify Email, Forgot Password, Reset Password
**Dependencies**: Uses foundation components from Prompt 1

### Prompt 3: Organization Pages
**Pages**: 4 pages
- Organizations List, Create Organization, Organization Detail, Organization Settings
**Dependencies**: Uses foundation + authentication patterns

### Prompt 4A: Command Center (Primary Landing)
**Pages**: 1 page + 3 major components
- Command Center (`/` - authenticated landing), Unified Project/Repo Selector, Recent Agents Sidebar, Task Submission Flow
**Dependencies**: Uses foundation + previous patterns
**Special Features**: Primary landing page, unified project/repo dropdown (1:1 constraint), collapsible agent sidebar, action-first design

### Prompt 4: Analytics Dashboard & Project Pages
**Pages**: 5 pages
- Analytics Dashboard (`/analytics` - secondary), Projects List, Create Project, Project Overview, AI-Assisted Exploration
**Dependencies**: Uses foundation + previous patterns + Command Center components

### Prompt 5: Spec Workspace & Kanban Board Pages
**Pages**: 4 pages
- Specs List, Spec Workspace, Kanban Board, Ticket Detail
**Dependencies**: Uses foundation + previous patterns
**Special Features**: Drag-and-drop, Notion-style editor, diagram viewer

### Prompt 6A: Graph & Phase Management Pages
**Pages**: 7 pages
- Dependency Graph, Ticket Graph, Phase Overview, Phase Detail, Create Custom Phase, Task Phase Management, Phase Gate Approvals
**Dependencies**: Uses foundation + previous patterns
**Special Features**: Graph visualization (React Flow), phase management

### Prompt 6B: Statistics & Activity Pages
**Pages**: 2 pages
- Statistics Dashboard, Activity Timeline
**Dependencies**: Uses foundation + previous patterns (including 6A)
**Special Features**: Charts (recharts), timeline feeds, export functionality

### Prompt 7: Agent Management & Diagnostic Pages
**Pages**: 5 pages
- Agents Overview, Spawn Agent, Agent Detail, Workspace Detail, Diagnostic Reasoning View
**Dependencies**: Uses foundation + previous patterns
**Special Features**: Agent status indicators, alignment scores, diagnostic reasoning

### Prompt 8A: User Settings Pages
**Pages**: 6 pages
- User Settings, Profile Settings, API Keys, Create API Key, API Key Detail, Active Sessions
**Dependencies**: Uses foundation + previous patterns
**Special Features**: Settings navigation, API key management

### Prompt 8B: Project Settings Pages
**Pages**: 4 pages
- Project Settings, Board Configuration, Phase Configuration, GitHub Integration
**Dependencies**: Uses foundation + previous patterns (including 8A)
**Special Features**: Settings navigation, OAuth integration UI, board/phase configuration

## Total Application Coverage

- **Total Pages**: ~42+ pages
- **Total Prompts**: 11 prompts (optimized to ~4,000 characters each)
- **Character Range**: ~3,500-4,500 characters per prompt
- **Primary Landing**: Command Center (`/`) - action-first entry point
- **Secondary Dashboard**: Analytics Dashboard (`/analytics`) - deliberate navigation

## Important Notes

1. **Sequential Building**: Each prompt builds on the previous one. Don't skip prompts.

2. **Component Reuse**: Later prompts reference components built in earlier prompts. Ensure components are properly exported and reusable.

3. **Responsive Design**: All pages should be responsive (mobile, tablet, desktop) as specified in requirements.

4. **State Management**: Each prompt includes state specifications (Loading, Empty, Error, Success). Implement these consistently.

5. **Navigation**: Navigation patterns are specified in each prompt. Use React Router or similar for routing.

6. **Accessibility**: All components must meet WCAG AA standards with proper ARIA labels, keyboard navigation, and semantic HTML.

7. **Dark Mode**: The design system includes full dark mode support. Ensure all components work in both light and dark modes.

## Design System Reference

**Design Inspiration**: Cursor BG Agent - minimal, warm, action-first interface.

All prompts reference the updated design system (Prompt 1):

**Color Palette (Warm Neutrals)**:
- Background: #F5F5F0 (Warm cream - primary)
- Surface: #FFFFFF (Cards, inputs)
- Border: #E8E8E3 (Subtle warm gray)
- Text: #1A1A1A (primary), #6B6B6B (secondary), #9B9B9B (tertiary)
- Accent: #1A1A1A (dark, not blue)
- Git colors: #22863A (additions), #CB2431 (deletions)
- State: #B08800 (warning), #0366D6 (info)

**Typography**: Inter (UI), JetBrains Mono (code/line counts)
**Spacing**: 4px base (xs: 4px, sm: 8px, md: 12px, lg: 16px, xl: 24px)
**Border Radius**: sm: 4px, md: 8px, lg: 12px, xl: 16px
**Shadows**: Minimal - sm, md only (subtle, not heavy)

**Key Principles**:
- Warm, not cold (cream backgrounds, not pure white/gray)
- Minimal visual noise (no heavy shadows, bright accents)
- Generous whitespace
- Action-first centered input
- Low contrast, easy on the eyes

## Next Steps After Building

Once all prompts are completed:

1. **Integration**: Convert to Next.js app structure (if needed)
2. **API Integration**: Connect to backend APIs
3. **State Management**: Add global state management (Redux, Zustand, etc.)
4. **Testing**: Add unit and integration tests
5. **Performance**: Optimize bundle size and loading performance
6. **Documentation**: Document component usage and patterns

## File Structure

```
docs/figma_prompts/
├── README.md (this file)
├── USAGE_GUIDE.md
│
├── prompt_1_foundation.md           ← Design system (Cursor-inspired)
├── prompt_2_authentication.md       ← Auth pages (7 pages)
├── prompt_3_organizations.md        ← Organization pages (4 pages)
├── prompt_4a_command_center.md      ← PRIMARY landing page (1 page + components)
├── prompt_4_dashboard_projects.md   ← Analytics Dashboard + Projects (5 pages)
├── prompt_5_specs_kanban.md         ← Specs & Kanban (4 pages)
├── prompt_6a_graph_phases.md        ← Graph & Phases (7 pages)
├── prompt_6b_statistics_activity.md ← Statistics & Activity (2 pages)
├── prompt_7_agents_diagnostic.md    ← Agents & Diagnostic (5 pages)
├── prompt_8a_user_settings.md       ← User Settings (6 pages)
├── prompt_8b_project_settings.md    ← Project Settings (4 pages)
│
├── prompt_6_graph_phases_stats.md   ← DEPRECATED (see 6a + 6b)
└── prompt_8_settings.md             ← DEPRECATED (see 8a + 8b)
```

## Questions or Issues?

If you encounter issues with any prompt:
1. Ensure you've completed all previous prompts
2. Check that components from earlier prompts are properly exported
3. Verify design system tokens are correctly implemented
4. Review the page architecture document for additional context

