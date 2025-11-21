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

**DESIGN SYSTEM:**

**Layout & Structure:**
- Global Header: Height 56px. Logo, project selector, search, notifications, profile.
- Left Sidebar: Standard navigation (240px width). Collapsible to icons (64px).
- Main Content Area: Primary focus. Single view or tabbed content.
- Right Sidebar (Optional/Collapsible): Activity feed or contextual panels.

**Color Palette:**
- Primary 500: #3B82F6 (Primary actions, active tabs, focus rings)
- Primary 600: #2563EB (Hover state)
- Neutrals (Light/Dark): Slate 900 (#0F172A/#F8FAFC), Slate 700 (#334155/#E2E8F0), Slate 500 (#64748B/#94A3B8), Slate 200 (#E2E8F0/#334155), Slate 100 (#F1F5F9/#1E293B), Slate 50 (#F8FAFC/#0F172A), White (#FFFFFF/#1E293B)
- State Colors: Green #10B981 (Active/Completed), Blue #3B82F6 (Thinking), Purple #A855F7 (Learning), Orange #F59E0B (Blocked), Yellow #EAB308 (Rate Limited), Red #EF4444 (Failed)

**Typography:**
- UI Font: Inter (Regular 400, Medium 500, Semibold 600, Bold 700)
- Code Font: JetBrains Mono
- Scale: H1 32px/40px (700), H2 24px/32px (600), H3 20px/28px (600), H4 16px/24px (600), Body 14px/20px (400), Small 12px/16px (400), Tiny 10px/12px (500)

**Spacing System (Base: 4px):**
- xs: 4px, sm: 8px, md: 16px, lg: 24px, xl: 32px, 2xl: 48px, 3xl: 64px

**Border Radius:**
- sm: 4px, md: 6px, lg: 8px, full: 9999px

**Shadows:**
- sm: 0 1px 2px 0 rgb(0 0 0 / 0.05)
- md: 0 4px 6px -1px rgb(0 0 0 / 0.1)
- lg: 0 10px 15px -3px rgb(0 0 0 / 0.1)
- focus: 0 0 0 2px #3B82F6

**Core Components to Build:**

1. **Button Component** (Primary, Secondary, Ghost, Destructive, Icon variants)
   - Heights: 36px (sm), 40px (md), 48px (lg)
   - Radius: md (6px)
   - Typography: Medium weight
   - States: Default, Hover, Active, Disabled, Loading

2. **Input Components** (Text, Textarea, Select, Checkbox, Radio)
   - Heights: 36px (sm), 40px (md)
   - Border: 1px solid Slate 300
   - Focus: Primary 500 ring
   - States: Default, Focus, Error, Disabled

3. **Card Component**
   - Background: White (Light) / Slate 900 (Dark)
   - Border: 1px solid Slate 200 (Light) / Slate 700 (Dark)
   - Radius: md (6px) or lg (8px)
   - Padding: lg (24px)
   - Shadow: sm or none

4. **Badge/Tag Component**
   - Height: 20-24px
   - Radius: full (pill) or sm (rounded rect)
   - Variants: Phase badges, Status badges, Status dots (6px circle with pulse animation for Active/Thinking)

5. **Avatar Component**
   - Shape: Circle (rounded-full)
   - Sizes: 24px (xs), 32px (sm), 40px (md), 48px (lg)
   - Content: Image or Initials

6. **Modal/Dialog Component**
   - Overlay: Black 50% opacity with backdrop blur
   - Container: White, centered, Shadow lg, Radius lg
   - Header: Title H3, Close icon button
   - Footer: Right-aligned action buttons

7. **Toast/Notification Component**
   - Position: Bottom-right or Top-right
   - Style: Small card, shadow lg, slide-in animation
   - Variants: Success (Green), Error (Red), Info (Blue)

8. **Layout Components:**
   - GlobalHeader (56px height)
   - Sidebar (240px width, collapsible to 64px)
   - MainContentArea
   - RightSidebar (collapsible)

9. **Navigation Components:**
   - SidebarNav (active/inactive states)
   - Tabs (horizontal, active has bottom border 2px Primary 500)

10. **Dark Mode Toggle** (functional light/dark mode switch)

**Requirements:**
- Build all components as reusable React components with TypeScript
- Implement full dark mode support
- Use CSS variables for theming
- Make all components responsive (mobile, tablet, desktop)
- Include proper ARIA labels and keyboard navigation
- Export components in a clean structure ready for Next.js integration
- Use Lucide React for icons (stroke width 1.5px or 2px, sizes: 16px sm, 20px md, 24px lg)

Generate the complete foundation with all core components, layout system, and theming infrastructure.

