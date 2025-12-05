# Figma Make Prompt 1: Foundation & Design System

Build this following engineering best practices:
- Write all code to WCAG AA accessibility standards
- Create and use reusable components throughout
- Use semantic HTML and proper component architecture
- Avoid absolute positioning; use flexbox/grid layouts
- Build actual code components, not static image SVGs
- Keep code clean, maintainable, and well-structured

You are Figma Make. I need you to build the foundation and design system for a complete, responsive application UI with working React code.

**PROJECT OVERVIEW:**
OmoiOS is a spec-driven autonomous engineering platform that orchestrates multiple AI agents through adaptive, phase-based workflows to build software from requirements to deployment. Target audience: Engineering Managers, Senior Engineers, Technical Leads.

**COMPONENT FRAMEWORK:**
Shadcn UI (https://ui.shadcn.com) with **Tailwind CSS v4**. 

Tailwind v4 uses CSS-first configuration:
- Theme defined via `@theme` directive in CSS (not tailwind.config.js)
- Native CSS variables for all design tokens
- CSS Layers (`@layer base`, `@layer components`, `@layer utilities`)
- Modern CSS features (nesting, container queries, etc.)

Components follow Shadcn's approach: Radix primitives + Tailwind CSS styling.

**DESIGN INSPIRATION:**
Cursor BG Agent - minimal, warm, action-first interface. Cream/off-white backgrounds, low contrast, generous whitespace, centered input focus.

**DESIGN SYSTEM:**

**Layout & Structure:**
- Minimal Header: Height 48px. Right-aligned: "Dashboard" link, Profile avatar. Left: Logo only.
- Left Sidebar: Agent history (220px width). Collapsible. Search, New Agent button, time-grouped list.
- Main Content Area: Centered prompt input (max-width 700px). Large whitespace.
- No right sidebar by default.

**Color Palette (Warm Neutrals):**
- Background: #F5F5F0 (Warm cream/off-white - primary background)
- Surface: #FFFFFF (Cards, inputs, elevated surfaces)
- Sidebar BG: #FAFAF8 (Slightly warmer than main)
- Border: #E8E8E3 (Subtle warm gray borders)
- Text Primary: #1A1A1A (Near black, not pure black)
- Text Secondary: #6B6B6B (Muted gray for timestamps, metadata)
- Text Tertiary: #9B9B9B (Placeholders, disabled)
- Accent: #1A1A1A (Primary actions - dark, not blue)
- Success: #22863A (Git green for additions, completed)
- Danger: #CB2431 (Git red for deletions, errors)
- Warning: #B08800 (Amber for blocked/rate limited)
- Info: #0366D6 (Blue for links, info states)
- Focus Ring: rgba(0,0,0,0.1) (Subtle, not bright blue)

**Dark Mode Colors:**
- Background: #1E1E1E
- Surface: #2D2D2D
- Sidebar BG: #252525
- Border: #3D3D3D
- Text Primary: #E5E5E5
- Text Secondary: #8B8B8B
- Text Tertiary: #5B5B5B

**Typography:**
- UI Font: Inter (Regular 400, Medium 500, Semibold 600)
- Code Font: JetBrains Mono (for line counts, code refs)
- Scale: H1 24px/32px (600), H2 18px/24px (600), H3 16px/22px (500), Body 14px/20px (400), Small 12px/16px (400), Tiny 11px/14px (500)
- Line counts: JetBrains Mono, 12px, Success/Danger colors (+1539 -209)

**Spacing System (Base: 4px):**
- xs: 4px, sm: 8px, md: 12px, lg: 16px, xl: 24px, 2xl: 32px, 3xl: 48px

**Border Radius:**
- sm: 4px, md: 8px, lg: 12px, xl: 16px, full: 9999px

**Shadows (Minimal):**
- sm: 0 1px 2px rgba(0,0,0,0.04)
- md: 0 2px 8px rgba(0,0,0,0.06)
- input-focus: 0 0 0 1px rgba(0,0,0,0.08)

**Shadcn Components to Build (with custom theme):**

1. **Button** (variant: default, secondary, ghost, outline, link, icon)
   - Default: Background hsl(--primary), text hsl(--primary-foreground)
   - Secondary: Background hsl(--secondary), text hsl(--secondary-foreground)
   - Ghost: No border, text hsl(--muted-foreground), hover bg hsl(--accent)
   - Outline: Border hsl(--border), transparent bg
   - Sizes: sm (32px), default (36px), lg (40px), icon (36px square)

2. **Input, Textarea, Select, Checkbox** (Shadcn form components)
   - Use Shadcn Input, Textarea, Select, Checkbox patterns
   - Background: hsl(--background), Border: hsl(--border)
   - Focus: ring-1 ring-ring (dark, not blue)
   - Placeholder: hsl(--muted-foreground)

3. **Card** (Shadcn Card: Card, CardHeader, CardContent, CardFooter)
   - Background: hsl(--card), Border: hsl(--border)
   - Used for: Agent cards, stat cards, form sections

4. **Custom: AgentCard** (extends Card pattern)
   - Compact layout: Status icon (⟳/✓/✗) + Task name + Time
   - Footer: Line changes (+X -Y) in green/red + Repo name muted
   - Hover: bg-accent

5. **Custom: PromptInput** (Textarea + supporting controls)
   - Large Textarea with placeholder "Ask Cursor to build, fix bugs, explore"
   - Below: Model selector (DropdownMenu), Repo selector (Popover)
   - Submit: Button variant="default" with ArrowUp icon

6. **DropdownMenu** (Shadcn DropdownMenu)
   - Trigger: Button or custom trigger
   - Content: bg-popover, shadow-md, rounded-md
   - Items: hover:bg-accent

7. **Select** (Shadcn Select with Radix)
   - SelectTrigger, SelectContent, SelectItem
   - Used for: Model selector, branch selector, filters

8. **Badge** (Shadcn Badge: default, secondary, outline, destructive)
   - Custom variants: repo (folder icon), branch (git-branch icon), status (dot)

9. **Avatar** (Shadcn Avatar with AvatarImage, AvatarFallback)
   - Sizes: sm (24px), default (32px), lg (40px)
   - Fallback: initials on muted background

10. **Sidebar** (Shadcn Sidebar pattern)
    - SidebarProvider, Sidebar, SidebarContent, SidebarGroup, SidebarMenuItem
    - Width: 220px, collapsible to icons (64px) or hidden
    - Background: hsl(--sidebar-background)

11. **Custom: TimeGroupHeader**
    - Text: text-[11px] uppercase tracking-wider text-muted-foreground
    - Used for: TODAY, THIS WEEK, THIS MONTH, ERRORED, EXPIRED

12. **Sheet** (Shadcn Sheet - for mobile sidebar)
    - SheetTrigger, SheetContent (side="left")

13. **Toast** (Shadcn Toast/Sonner)
    - For notifications, success/error feedback

14. **Dialog** (Shadcn Dialog)
    - DialogTrigger, DialogContent, DialogHeader, DialogFooter

15. **Tabs** (Shadcn Tabs)
    - TabsList, TabsTrigger, TabsContent

**Tailwind v4 Theme (CSS-first with @theme):**
```css
@import "tailwindcss";

@theme {
  --color-background: oklch(0.97 0.01 85);
  --color-foreground: oklch(0.15 0 0);
  --color-card: oklch(1 0 0);
  --color-card-foreground: oklch(0.15 0 0);
  --color-primary: oklch(0.15 0 0);
  --color-primary-foreground: oklch(0.97 0.01 85);
  --color-secondary: oklch(0.95 0.01 85);
  --color-secondary-foreground: oklch(0.15 0 0);
  --color-muted: oklch(0.95 0.01 85);
  --color-muted-foreground: oklch(0.5 0 0);
  --color-accent: oklch(0.95 0.01 85);
  --color-accent-foreground: oklch(0.15 0 0);
  --color-destructive: oklch(0.55 0.2 25);
  --color-border: oklch(0.92 0.01 85);
  --color-input: oklch(0.92 0.01 85);
  --color-ring: oklch(0.15 0 0);
  --color-success: oklch(0.55 0.15 145);
  --color-warning: oklch(0.65 0.15 85);
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
}

@layer base {
  :root {
    --radius: 0.5rem;
  }
}
```

Note: Tailwind v4 uses OKLCH color space by default for better perceptual uniformity. The theme values map to the warm cream palette (#F5F5F0, #1A1A1A, etc.).

**Requirements:**
- Build using Shadcn UI component patterns and composition model
- Use Tailwind CSS with CSS variables for theming
- Implement full dark mode support (warm dark tones, not cold grays)
- Make all components responsive (Sidebar → Sheet on mobile)
- Use Lucide React icons (stroke width 1.5, sizes: 14px sm, 16px md, 20px lg)
- Follow Shadcn naming: cn() utility, cva() for variants
- Emphasize whitespace and minimal visual noise

Generate the complete foundation with Shadcn-compatible components, layout system, and theming.

