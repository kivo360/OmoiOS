# Figma Make Prompts Usage Guide

## Quick Start

1. **Start with Prompt 1** and work sequentially through all 11 prompts
2. **Copy each prompt** entirely (including the engineering best practices header)
3. **Paste into Figma Make** - each prompt is designed to be self-contained
4. **Build incrementally** - each prompt builds upon previous work

## Component Framework: Shadcn UI + Tailwind v4

All prompts are built on **Shadcn UI** with **Tailwind CSS v4**:

**Tailwind v4 (CSS-First):**
- No `tailwind.config.js` - configure via `@theme` in CSS
- OKLCH color space for perceptual uniformity
- Native CSS variables, layers, nesting
- Import: `@import "tailwindcss";`

**Shadcn Patterns:**
- Radix UI primitives for accessibility
- `cn()` for class merging, `cva()` for variants
- Composable, copy-paste components

**Most Used Components:**
- `Button` (variants: default, secondary, outline, ghost, destructive)
- `Card` (CardHeader, CardContent, CardFooter)
- `Input`, `Textarea`, `Select`, `Checkbox`, `Switch`
- `Dialog`, `Sheet`, `Popover`, `DropdownMenu`
- `Tabs`, `Table`, `Badge`, `Avatar`, `Progress`
- `Sidebar`, `ScrollArea`, `Separator`
- `Toast/Sonner`, `Command` (cmdk)

**Tailwind v4 Theme Format:**
```css
@import "tailwindcss";

@theme {
  --color-background: oklch(0.97 0.01 85);
  --color-foreground: oklch(0.15 0 0);
  --color-primary: oklch(0.15 0 0);
  --radius-md: 0.5rem;
}
```

## Design Inspiration: Cursor BG Agent

The design system is inspired by the Cursor BG Agent interface:

**Key Visual Characteristics:**
- **Warm cream background** (#F5F5F0) - not cold white/gray
- **Minimal visual noise** - no heavy shadows, bright accents
- **Low contrast** - easy on the eyes, muted secondary text
- **Generous whitespace** - centered content, breathing room
- **Git-style line changes** - green for additions (+), red for deletions (-)
- **Time grouping** - Today, This Week, This Month sections
- **Action-first** - prominent input area, sidebar shows agent history

**Color Usage:**
- Primary actions: Dark (#1A1A1A), not blue
- Success/additions: Git green (#22863A)
- Errors/deletions: Git red (#CB2431)
- Secondary text: Muted gray (#6B6B6B)

## Important: Navigation Hierarchy

- **Command Center (`/`)** is the PRIMARY authenticated landing page
- **Analytics Dashboard (`/analytics`)** is SECONDARY, accessed via deliberate navigation
- Users land on Command Center first, then navigate to Analytics if needed

## Character Count Summary

| Prompt | Pages | Characters | Status |
|--------|-------|------------|--------|
| Prompt 1: Foundation | 0 (foundation) | 4,646 | ✅ Good |
| Prompt 2: Authentication | 7 | 6,184 | ⚠️ Over 5k - may need trimming |
| Prompt 3: Organizations | 4 | 5,738 | ⚠️ Over 5k - may need trimming |
| Prompt 4A: Command Center | 1 + 3 components | ~4,200 | ✅ Good |
| Prompt 4: Analytics & Projects | 5 | 7,172 | ⚠️ Over 5k - needs trimming |
| Prompt 5: Specs & Kanban | 4 | 7,387 | ⚠️ Over 5k - needs trimming |
| Prompt 6A: Graph & Phases | 7 | 6,009 | ⚠️ Over 5k - may need trimming |
| Prompt 6B: Statistics & Activity | 2 | 3,658 | ✅ Good |
| Prompt 7: Agents & Diagnostic | 5 | 7,841 | ⚠️ Over 5k - needs trimming |
| Prompt 8A: User Settings | 6 | 5,011 | ⚠️ Over 5k - slight trim |
| Prompt 8B: Project Settings | 4 | 4,860 | ✅ Good |

## Trimming Strategy

If a prompt exceeds 5,000 characters when pasted into Figma Make:

1. **Keep the engineering best practices header** (essential)
2. **Keep the PROJECT CONTEXT section** (essential)
3. **Condense page descriptions** by:
   - Removing redundant "States" descriptions (keep only unique ones)
   - Shortening "Content" sections (keep key items only)
   - Combining similar navigation patterns
   - Removing verbose explanations in "Requirements" section

4. **Priority order for content**:
   - Layout Structure (most important)
   - Key Components (essential)
   - Navigation patterns (important)
   - Content examples (can be shortened)
   - Requirements (can be condensed)

## Example Trimming

**Before (verbose):**
```
- States: Loading (skeleton cards), Empty ("No projects yet. Create your first project to get started."), Populated (project cards grid), Error (error message with retry button)
```

**After (condensed):**
```
- States: Loading, Empty, Populated, Error
```

## Tips for Success

1. **Build sequentially** - Don't skip prompts as they build on each other
2. **Reference previous prompts** - Components from earlier prompts are reused
3. **Test incrementally** - Build and test each section before moving on
4. **Keep components reusable** - Export components properly for reuse
5. **Follow design system** - All prompts reference the same design tokens

## What Each Prompt Delivers

- **Prompt 1**: Foundation components (Buttons, Inputs, Cards, Layout, Dark Mode)
- **Prompt 4A**: Command Center - PRIMARY landing with unified project/repo selector, recent agents sidebar
- **Prompt 4**: Analytics Dashboard (SECONDARY) + Project management pages
- **Prompts 2-8B**: Complete page implementations with full functionality
- **Total**: ~42+ pages covering the entire OmoiOS application

## Key Components from Command Center (Prompt 4A)

These components are reused across the application:

1. **UnifiedProjectSelector** - Dropdown showing projects + available repos (1:1 constraint)
2. **RecentAgentsSidebar** - Collapsible sidebar with time-grouped agent history
3. **AgentCard (compact)** - Small card for sidebar display
4. **TaskSubmissionFlow** - Progress overlay for task processing

## Troubleshooting

**Issue**: Prompt too long for Figma Make
- **Solution**: Use trimming strategy above, focus on Layout/Components/Navigation

**Issue**: Missing components from previous prompts
- **Solution**: Ensure you've completed all previous prompts in order

**Issue**: Design system tokens not working
- **Solution**: Verify Prompt 1 foundation is complete and components are exported

**Issue**: Navigation not working
- **Solution**: Use React Router or similar, implement routes as specified in each prompt

## Next Steps After Completion

Once all prompts are built:

1. **Integration**: Convert to Next.js structure (if needed)
2. **API Integration**: Connect to backend APIs
3. **State Management**: Add global state (Redux, Zustand, etc.)
4. **Testing**: Add unit and integration tests
5. **Performance**: Optimize bundle size and loading
6. **Documentation**: Document component usage

