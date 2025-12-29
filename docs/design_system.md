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

> **NOTE: Theme Direction (Dec 2024)**
> - **Light Mode (Current)**: Clean white/neutral theme - implemented in `globals.css`
> - **Dark Mode (Current)**: Clean dark neutral - implemented in `globals.css`
> - **Dark Mode (Future)**: Golden/amber theme inspired by OG image - warm, luxurious feel
> - Design tokens to be systematized post-launch

---

### Current Implementation (from globals.css)

#### Light Mode CSS Variables
```css
:root {
  /* Core */
  --background: 0 0% 100%;             /* #FFFFFF Pure white */
  --foreground: 0 0% 9%;               /* #171717 Near black */

  /* Card/Surface */
  --card: 0 0% 100%;                   /* #FFFFFF White surfaces */
  --card-foreground: 0 0% 9%;          /* #171717 */

  /* Primary - Dark accent */
  --primary: 0 0% 9%;                  /* #171717 */
  --primary-foreground: 0 0% 100%;     /* #FFFFFF */

  /* Secondary */
  --secondary: 0 0% 96%;               /* #F5F5F5 Light gray */
  --secondary-foreground: 0 0% 9%;     /* #171717 */

  /* Muted */
  --muted: 0 0% 96%;                   /* #F5F5F5 Light gray */
  --muted-foreground: 0 0% 45%;        /* #737373 Secondary text */

  /* Accent */
  --accent: 0 0% 96%;                  /* #F5F5F5 Hover state */
  --accent-foreground: 0 0% 9%;        /* #171717 */

  /* Destructive */
  --destructive: 0 84% 60%;            /* #EF4444 */
  --destructive-foreground: 0 0% 100%;

  /* Borders */
  --border: 0 0% 90%;                  /* #E5E5E5 Light borders */
  --input: 0 0% 90%;                   /* #E5E5E5 */
  --ring: 0 0% 9%;                     /* #171717 Focus ring */

  /* Semantic */
  --success: 142 71% 45%;              /* #22C55E Green */
  --warning: 38 92% 50%;               /* #F59E0B Amber */
  --info: 217 91% 60%;                 /* #3B82F6 Blue */
  --tertiary: 0 0% 64%;                /* #A3A3A3 Placeholder */

  /* Radius */
  --radius: 0.5rem;

  /* Sidebar */
  --sidebar-background: 0 0% 98%;      /* #FAFAFA */
  --sidebar-foreground: 0 0% 9%;       /* #171717 */
  --sidebar-primary: 0 0% 9%;          /* #171717 */
  --sidebar-primary-foreground: 0 0% 100%;
  --sidebar-accent: 0 0% 96%;          /* #F5F5F5 Hover */
  --sidebar-accent-foreground: 0 0% 9%;
  --sidebar-border: 0 0% 90%;          /* #E5E5E5 */
  --sidebar-ring: 0 0% 9%;             /* #171717 */
}
```

#### Landing Page Variables (Light Mode)
```css
:root {
  /* Accent (Neutral dark - professional) */
  --landing-accent: 0 0% 9%;                   /* #171717 - Dark accent */
  --landing-accent-light: 0 0% 20%;            /* #333333 - Lighter */
  --landing-accent-dark: 0 0% 4%;              /* #0A0A0A - Darker */
  --landing-accent-foreground: 0 0% 100%;      /* White text on accent */

  /* Landing Backgrounds */
  --landing-bg: 0 0% 100%;                     /* #FFFFFF - Pure white */
  --landing-bg-muted: 0 0% 98%;                /* #FAFAFA - Very light gray */
  --landing-bg-warm: 0 0% 96%;                 /* #F5F5F5 - Light gray */
  --landing-bg-dark: 0 0% 4%;                  /* #0A0A0A - Near black */

  /* Landing Text */
  --landing-text: 0 0% 9%;                     /* #171717 - Near black */
  --landing-text-muted: 0 0% 45%;              /* #737373 - Gray */
  --landing-text-subtle: 0 0% 64%;             /* #A3A3A3 - Light gray */
  --landing-text-inverse: 0 0% 100%;           /* #FFFFFF */

  /* Landing Borders */
  --landing-border: 0 0% 90%;                  /* #E5E5E5 - Light border */
  --landing-border-accent: 0 0% 9%;            /* Uses accent color */

  /* Landing Gradient Stops */
  --landing-gradient-from: 0 0% 9%;            /* #171717 */
  --landing-gradient-to: 0 0% 4%;              /* #0A0A0A */
}
```

#### Current Dark Mode CSS Variables
```css
.dark {
  /* Core */
  --background: 0 0% 4%;               /* #0A0A0A */
  --foreground: 0 0% 98%;              /* #FAFAFA */

  /* Card/Surface */
  --card: 0 0% 9%;                     /* #171717 */
  --card-foreground: 0 0% 98%;         /* #FAFAFA */

  /* Primary */
  --primary: 0 0% 98%;                 /* #FAFAFA */
  --primary-foreground: 0 0% 9%;       /* #171717 */

  /* Secondary */
  --secondary: 0 0% 15%;               /* #262626 */
  --secondary-foreground: 0 0% 98%;    /* #FAFAFA */

  /* Muted */
  --muted: 0 0% 15%;                   /* #262626 */
  --muted-foreground: 0 0% 64%;        /* #A3A3A3 */

  /* Accent */
  --accent: 0 0% 15%;                  /* #262626 Hover */
  --accent-foreground: 0 0% 98%;       /* #FAFAFA */

  /* Borders */
  --border: 0 0% 18%;                  /* #2E2E2E */
  --input: 0 0% 18%;                   /* #2E2E2E */
  --ring: 0 0% 98%;                    /* #FAFAFA */

  /* Sidebar */
  --sidebar-background: 0 0% 7%;       /* #121212 */
  --sidebar-foreground: 0 0% 98%;      /* #FAFAFA */
  --sidebar-primary: 0 0% 98%;         /* #FAFAFA */
  --sidebar-primary-foreground: 0 0% 9%;
  --sidebar-accent: 0 0% 15%;          /* #262626 */
  --sidebar-accent-foreground: 0 0% 98%;
  --sidebar-border: 0 0% 18%;          /* #2E2E2E */
  --sidebar-ring: 0 0% 98%;
}
```

---

### Tailwind Color Mappings (from tailwind.config.ts)

```typescript
colors: {
  border: 'hsl(var(--border))',
  input: 'hsl(var(--input))',
  ring: 'hsl(var(--ring))',
  background: 'hsl(var(--background))',
  foreground: 'hsl(var(--foreground))',
  success: 'hsl(var(--success))',
  warning: 'hsl(var(--warning))',
  info: 'hsl(var(--info))',
  tertiary: 'hsl(var(--tertiary))',
  primary: {
    DEFAULT: 'hsl(var(--primary))',
    foreground: 'hsl(var(--primary-foreground))'
  },
  secondary: {
    DEFAULT: 'hsl(var(--secondary))',
    foreground: 'hsl(var(--secondary-foreground))'
  },
  destructive: {
    DEFAULT: 'hsl(var(--destructive))',
    foreground: 'hsl(var(--destructive-foreground))'
  },
  muted: {
    DEFAULT: 'hsl(var(--muted))',
    foreground: 'hsl(var(--muted-foreground))'
  },
  accent: {
    DEFAULT: 'hsl(var(--accent))',
    foreground: 'hsl(var(--accent-foreground))'
  },
  popover: {
    DEFAULT: 'hsl(var(--popover))',
    foreground: 'hsl(var(--popover-foreground))'
  },
  card: {
    DEFAULT: 'hsl(var(--card))',
    foreground: 'hsl(var(--card-foreground))'
  },
  sidebar: {
    DEFAULT: 'hsl(var(--sidebar-background))',
    foreground: 'hsl(var(--sidebar-foreground))',
    primary: 'hsl(var(--sidebar-primary))',
    'primary-foreground': 'hsl(var(--sidebar-primary-foreground))',
    accent: 'hsl(var(--sidebar-accent))',
    'accent-foreground': 'hsl(var(--sidebar-accent-foreground))',
    border: 'hsl(var(--sidebar-border))',
    ring: 'hsl(var(--sidebar-ring))'
  },
  landing: {
    accent: {
      DEFAULT: 'hsl(var(--landing-accent))',
      light: 'hsl(var(--landing-accent-light))',
      dark: 'hsl(var(--landing-accent-dark))',
      foreground: 'hsl(var(--landing-accent-foreground))'
    },
    bg: {
      DEFAULT: 'hsl(var(--landing-bg))',
      muted: 'hsl(var(--landing-bg-muted))',
      warm: 'hsl(var(--landing-bg-warm))',
      dark: 'hsl(var(--landing-bg-dark))'
    },
    text: {
      DEFAULT: 'hsl(var(--landing-text))',
      muted: 'hsl(var(--landing-text-muted))',
      subtle: 'hsl(var(--landing-text-subtle))',
      inverse: 'hsl(var(--landing-text-inverse))'
    },
    border: {
      DEFAULT: 'hsl(var(--landing-border))',
      accent: 'hsl(var(--landing-border-accent) / 0.3)'
    }
  }
}
```

---

### Future Golden Dark Theme (Planned)

#### Golden Palette (Primary Brand - Used in OG Images)
The signature OmoiOS golden theme - warm amber tones that evoke "overnight automation" and premium feel.

| Name | Hex | HSL (approx) | Usage |
|------|-----|--------------|-------|
| **Gold Light** | `#FFE78A` | `46 100% 77%` | Gradient start, highlights |
| **Gold Primary** | `#FFD04A` | `44 100% 64%` | Primary accent, gradient mid |
| **Gold Warm** | `#FF8A2A` | `24 100% 58%` | Gradient end, emphasis |
| **Amber Glow** | `rgba(255,200,50,0.15)` | - | Subtle backgrounds, pills |
| **Amber Border** | `rgba(255,200,50,0.2)` | - | Subtle borders |

#### Future Dark Theme Backgrounds (Golden/Brown)
```css
/* Future .dark-golden or enhanced .dark theme */
Background gradient: linear-gradient(145deg, #2d2618 0%, #1a150d 50%, #0f0c08 100%)
Warm overlay: radial-gradient(ellipse at 30% 30%, rgba(255,200,50,0.12), transparent)
```

| Name | Hex | HSL (approx) | Usage |
|------|-----|--------------|-------|
| **Dark Warm 100** | `#2d2618` | `36 30% 13%` | Lightest dark background |
| **Dark Warm 200** | `#1a150d` | `37 33% 8%` | Mid dark background |
| **Dark Warm 300** | `#0f0c08` | `34 30% 4%` | Deepest dark background |
| **Text on Dark** | `rgba(255,230,180,0.9)` | - | Primary text on dark |
| **Muted on Dark** | `rgba(255,230,200,0.6)` | - | Secondary text on dark |

---

### Semantic State Colors

| State Group | State | Color | Hex | CSS Variable |
|-------------|-------|-------|-----|--------------|
| **Good** | Success/Done | Green | `#22C55E` | `--success: 142 71% 45%` |
| **Neutral** | Info/Thinking | Blue | `#3B82F6` | `--info: 217 91% 60%` |
| **Warning** | Warning/Blocked | Amber | `#F59E0B` | `--warning: 38 92% 50%` |
| **Critical** | Error/Failed | Red | `#EF4444` | `--destructive: 0 84% 60%` |

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

---

## 10. Design Tokens (Future)

> **Status**: Planned for post-launch implementation
> **Priority**: Low (launch first, systematize later)

### Token Architecture (Planned)
When implemented, design tokens will follow this structure:

```
tokens/
├── colors/
│   ├── brand.json       # Golden theme colors
│   ├── semantic.json    # success, error, warning, info
│   └── neutral.json     # Grays/slates
├── typography/
│   ├── fonts.json
│   └── scale.json
├── spacing.json
├── radii.json
├── shadows.json
└── themes/
    ├── light.json       # Current clean theme
    └── dark.json        # Golden/amber theme
```

### Dark Theme Vision
The dark theme should feel like the OG image - warm, premium, "nighttime productivity":

- **Background**: Rich warm browns (`#2d2618` → `#1a150d` → `#0f0c08`)
- **Accent**: Golden gradients (`#FFE78A` → `#FFD04A` → `#FF8A2A`)
- **Text**: Warm off-white (`rgba(255,230,180,0.9)`)
- **Glow effects**: Subtle amber radial gradients for depth
- **Feel**: Like working in a warm, luxurious command center at night

### Implementation Notes
- Use CSS custom properties for easy theming
- Consider `next-themes` for theme switching
- Tailwind CSS can consume tokens via `tailwind.config.js`
- shadcn/ui components already support dark mode via CSS variables

