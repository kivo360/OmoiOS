# OmoiOS Design System Guide

## Design Philosophy

**Aesthetic**: Linear/Arc-inspired with increased information density. Modern SaaS polish with power-user optimizations.
**Tone**: Professional, precise, autonomous, trustworthy.
**Audience**: Engineering Managers, Senior Engineers, Technical Leads.
**Approach**: Traditional clean layout with progressive enhancement toward high-density "Mission Control" features.

---

## 1. Layout & Structure

### Core Layout: Traditional with Enhancements
Standard SaaS layout with optional high-density features.

- **Global Header**: Height 56px. Logo, project selector, search, notifications, profile.
- **Left Sidebar**: Standard navigation (240px width). Collapsible to icons (64px).
- **Main Content Area**: Primary focus. Single view or tabbed content.
- **Right Sidebar** (Optional/Collapsible): Activity feed or contextual panels.

### Progressive Enhancements (V2+)
- **Agent Status Widget**: Collapsible widget in header or right sidebar showing active agents
- **Intervention Badge**: Notification badge that opens intervention queue when clicked
- **Compact Mode**: Tighter spacing and smaller fonts (user preference)

---

## 2. Color Palette

### Primary Colors (Brand)
High-visibility blue for actions and active states.

| Name | Hex | Usage |
|------|-----|-------|
| **Primary 500** | `#3B82F6` | Primary actions, active tabs, focus rings |
| **Primary 600** | `#2563EB` | Hover state |
| **Primary 900** | `#1E3A8A` | Subtle backgrounds for active items |

### Neutrals (Light & Dark Modes)
Slate-based neutrals for a technical, modern feel.

| Name | Hex (Light) | Hex (Dark) | Usage |
|------|-------------|------------|-------|
| **Slate 900** | `#0F172A` | `#F8FAFC` | Primary text, headings |
| **Slate 700** | `#334155` | `#E2E8F0` | Secondary text, body copy |
| **Slate 500** | `#64748B` | `#94A3B8` | Muted text, icons, placeholders |
| **Slate 400** | `#94A3B8` | `#64748B` | Disabled text, borders |
| **Slate 200** | `#E2E8F0` | `#334155` | Dividers, light borders |
| **Slate 100** | `#F1F5F9` | `#1E293B` | Secondary backgrounds |
| **Slate 50** | `#F8FAFC` | `#0F172A` | App background |
| **White** | `#FFFFFF` | `#1E293B` | Card backgrounds, inputs |

### State Colors (Expanded Vocabulary)
Distinct colors for the comprehensive agent/workflow state machine.

| State Group | State | Color | Hex | Usage |
|-------------|-------|-------|-----|-------|
| **Good** | Active/Executing | Green | `#10B981` | Agents working, tasks running |
| **Good** | Done/Completed | Green | `#10B981` | Finished work |
| **Neutral** | Idle/Available | Slate | `#64748B` | Agents waiting for work |
| **Neutral** | Thinking/Planning | Blue | `#3B82F6` | Agent analyzing (pulse animation) |
| **Neutral** | Learning | Purple | `#A855F7` | Post-task analysis |
| **Warning** | Waiting/Blocked | Orange | `#F59E0B` | Blocked on dependency |
| **Warning** | Rate Limited | Yellow | `#EAB308` | API throttling |
| **Warning** | At Risk | Orange | `#F97316` | Behind schedule/budget |
| **Critical** | Failed/Error | Red | `#EF4444` | Needs intervention |
| **Critical** | Budget Exceeded | Red | `#DC2626` | Cost stop |

---

## 3. Typography

### Font Families
- **UI**: `Inter` (Clean, legible at small sizes)
- **Data/Code**: `JetBrains Mono` (Tabular numbers, logs, IDs, metrics)

### Font Scale
Based on a 1.25 major third scale.

| Style | Size | Line Height | Weight | Usage |
|-------|------|-------------|--------|-------|
| **H1** | 32px (2rem) | 40px | Bold (700) | Page titles, Hero text |
| **H2** | 24px (1.5rem) | 32px | Semibold (600) | Section headers, Card titles |
| **H3** | 20px (1.25rem) | 28px | Semibold (600) | Sub-sections, Modal titles |
| **H4** | 16px (1rem) | 24px | Semibold (600) | Component headers |
| **Body** | 14px (0.875rem) | 20px | Regular (400) | Main content, descriptions |
| **Small** | 12px (0.75rem) | 16px | Regular (400) | Metadata, labels, captions |
| **Tiny** | 10px (0.625rem) | 12px | Medium (500) | Badges, tiny indicators |

### Font Weights
- **Regular (400)**: Body text, descriptions
- **Medium (500)**: Button text, navigation links, labels
- **Semibold (600)**: Headings, emphasized text
- **Bold (700)**: Main page titles, highly emphasized numbers

---

## 4. Spacing System

**Base Unit**: 4px (0.25rem)

| Token | Value | Pixels | Usage |
|-------|-------|--------|-------|
| **none** | 0 | 0px | No spacing |
| **xs** | 1 | 4px | Tight grouping (icon + text) |
| **sm** | 2 | 8px | Related elements (inputs in form) |
| **md** | 4 | 16px | Component padding, standard gap |
| **lg** | 6 | 24px | Section spacing, card padding |
| **xl** | 8 | 32px | Container padding |
| **2xl** | 12 | 48px | Major section breaks |
| **3xl** | 16 | 64px | Page layout spacing |

**Guidance**:
- Use `md` (16px) for standard component padding
- Use `sm` (8px) for spacing between related items
- Use `lg` (24px) for separating distinct logical groups

### Compact Mode (Optional)
For users who prefer higher density:
- Card padding: `sm` (8px) instead of `lg` (24px)
- List item height: 32px instead of 40px
- Font sizes: -1px across the board

---

## 5. Border Radius & Shadows

### Border Radius
Soft, modern curves.

| Token | Value | Usage |
|-------|-------|-------|
| **none** | 0px | Square elements |
| **sm** | 4px | Inputs, small buttons, checkboxes |
| **md** | 6px | Standard buttons, dropdowns, cards |
| **lg** | 8px | Modals, large cards, toast notifications |
| **full** | 9999px | Pills, badges, avatars, icon buttons |

### Shadows
Subtle, diffuse shadows for depth.

| Token | CSS Value | Usage |
|-------|-----------|-------|
| **sm** | `0 1px 2px 0 rgb(0 0 0 / 0.05)` | Buttons, inputs (hover) |
| **md** | `0 4px 6px -1px rgb(0 0 0 / 0.1)` | Cards, dropdown menus |
| **lg** | `0 10px 15px -3px rgb(0 0 0 / 0.1)` | Modals, popovers |
| **focus** | `0 0 0 2px #3B82F6` | Focus states (accessibility) |

---

## 6. Core Components

### Buttons
**Height**: 36px (sm), 40px (md), 48px (lg)
**Radius**: `md` (6px)
**Typography**: Medium weight

- **Primary**: Solid Primary 500 background, White text. Hover: Primary 600.
- **Secondary**: White background, Slate 300 border, Slate 700 text. Hover: Slate 50 bg.
- **Ghost**: Transparent background, Slate 600 text. Hover: Slate 100 bg.
- **Destructive**: Red 50 background, Red 600 text. Hover: Red 100 bg.
- **Icon Button**: Square/Circle, ghost style usually.

### Inputs
**Height**: 36px (sm), 40px (md)
**Radius**: `md` (6px)
**Border**: 1px solid Slate 300

- **Text Field**: White background, Slate 900 text. Focus: Primary 500 ring.
- **Textarea**: Same style, resizable vertical.
- **Select/Dropdown**: Chevron icon right, same style as text field.
- **Checkbox/Radio**: Accent color Primary 500.

### Cards
**Background**: White (Light), Slate 900 (Dark)
**Border**: 1px solid Slate 200 (Light), Slate 700 (Dark)
**Radius**: `md` (6px) or `lg` (8px)
**Shadow**: `sm` or `none` (border-heavy style preferred)
**Padding**: `lg` (24px)

**Enhanced Workflow Card** (V2 Progressive Enhancement):
- Add metadata row: Last action, Next action, ETA
- Add progress details: "13/20 tasks (65%)"
- Add risk indicators: "Blocked: 0 | At risk: 2"
- Optional sparkline: Tiny velocity graph (24h trend)

### Navigation
- **Sidebar**: Slate 50 (Light) or Slate 900 (Dark) vertical bar. Width ~240px.
  - Active Item: Primary 50/900 background, Primary 600/400 text.
  - Inactive Item: Slate 500 text. Hover: Slate 700 text.
- **Tabs**: Horizontal list.
  - Active: Bottom border 2px Primary 500, Primary 700 text.
  - Inactive: No border, Slate 500 text.

### Modals/Dialogs
**Overlay**: Black with 50% opacity (`bg-black/50`) backdrop blur.
**Container**: White, centered, Shadow `lg`, Radius `lg`.
**Header**: Title H3, Close icon button.
**Footer**: Right-aligned action buttons.

### Toasts/Notifications
**Position**: Bottom-right or Top-right.
**Style**: Small card, shadow `lg`, slide-in animation.
**Variants**: Success (Green icon), Error (Red icon), Info (Blue icon).

### Badges/Tags
**Size**: Height 20-24px.
**Radius**: `full` (pill shape) or `sm` (rounded rect).
**Style**: Subtle background (Color 50) + Strong text (Color 700).
- **Phase Badges**: Purple/Blue/Orange/Green backgrounds.
- **Status Badges**: Green/Red/Gray backgrounds.
- **Status Dots**: 6px circle. Pulsing animation for `Active`/`Thinking`. Static for others.

### Avatars
**Shape**: Circle (`rounded-full`).
**Size**: 24px (xs), 32px (sm), 40px (md), 48px (lg).
**Content**: Image or Initials.
**Border**: Optional 1-2px white border for overlapping avatars.

---

---

## 7. Elevations & Surfaces

The interface uses subtle borders and background contrast (Linear-style).

### Layer 0: Application Background
- **Light**: Slate 50 (`#F8FAFC`)
- **Dark**: Slate 950 (`#020617`)

### Layer 1: Content Containers (Cards, Sidebar)
- **Light**: White (`#FFFFFF`), Border Slate 200
- **Dark**: Slate 900 (`#0F172A`), Border Slate 800

### Layer 2: Interactive Elements (Dropdowns, Popovers)
- **Light**: White, Shadow `md`, Border Slate 200
- **Dark**: Slate 800, Shadow `md`, Border Slate 700

### Layer 3: Modals & Floating Elements
- **Light**: White, Shadow `lg`, Border Slate 200
- **Dark**: Slate 800, Shadow `lg`, Border Slate 700

---

## 8. Icons
**Set**: Lucide React or Phosphor Icons (Outlined/Stroke style).
**Stroke Width**: 1.5px or 2px.
**Size**: 16px (sm), 20px (md), 24px (lg).

---

## 9. Progressive Enhancements (V2+)

### High-Density Features (Gradual Integration)

**Phase 1 (V1)**: Traditional Linear-style design
- Clean layout, spacious cards
- Standard navigation
- Activity feed in collapsible sidebar

**Phase 2 (V1.5)**: Add density options
- **Compact Mode Toggle**: Tighter spacing, smaller fonts
- **Enhanced Cards**: Add "Last action", "Next action", ETA
- **Real-Time Metrics**: Show burn rate, budget % on cards

**Phase 3 (V2)**: Add Mission Control widgets
- **Agent Status Widget**: Collapsible widget showing active agents
- **Intervention Badge**: Notification count that opens queue
- **Sparklines**: Tiny velocity/trend graphs on workflow cards

**Phase 4 (V2.5)**: Full Mission Control Mode
- **Persistent Agent Panel**: Optional right panel (toggle on/off)
- **Intervention Drawer**: Bottom drawer for decisions
- **Multi-pane Layout**: Power user layout option

### Micro-Interactions
- **Optimistic UI**: State changes reflect immediately
- **Status Pulse**: Active agents/tasks have subtle opacity pulse (1s loop)
- **New Item Flash**: Newly added items flash highlight then fade
- **Hover-to-Reveal**: Additional metadata appears on hover

