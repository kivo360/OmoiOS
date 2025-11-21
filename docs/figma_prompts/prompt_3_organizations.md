# Figma Make Prompt 3: Organization Pages

Build this following engineering best practices:
- Write all code to WCAG AA accessibility standards
- Create and use reusable components throughout
- Use semantic HTML and proper component architecture
- Avoid absolute positioning; use flexbox/grid layouts
- Build actual code components, not static image SVGs
- Keep code clean, maintainable, and well-structured

You are Figma Make. Continue building the OmoiOS application. Foundation, design system, and authentication pages are already built. Now build the Organization Management Pages section.

**PROJECT CONTEXT:**
OmoiOS is a spec-driven autonomous engineering platform. Use existing design system components and layout structure (Header, Sidebar, MainContentArea).

**ORGANIZATION PAGES TO BUILD:**

**1. Organizations List (`/organizations`)**
- Layout: Header with "Create Organization" button, grid/list of organization cards, sidebar with user profile
- Components: Page header (title + "Create Organization" button), Organization cards grid (3 columns desktop, 1 mobile), Organization card (logo, name, member count, role badge, "View" button), Empty state illustration, User profile sidebar
- Content:
  - Page title: "Organizations"
  - Organization cards show: Logo/avatar, Organization name, Member count ("X members"), User's role badge ("Owner", "Admin", "Member"), Last active ("Active 2 hours ago")
  - Empty state: "You're not a member of any organizations yet"
- States: Loading (skeleton cards), Empty (empty state with CTA), Populated (organization cards grid), Error (error message with retry)
- Navigation: Click card → `/organizations/:id`, Click "Create Organization" → `/organizations/new`

**2. Create Organization (`/organizations/new`)**
- Layout: Centered form layout with multi-step wizard (optional) or single form
- Components: Organization creation form, Form sections (Basic Info, Resource Limits, Settings), Form validation messages, Cancel and Submit buttons, Resource limit sliders/inputs
- Content:
  - Page title: "Create Organization"
  - Form fields:
    - Organization Name (required)
    - Organization Slug (auto-generated, editable)
    - Resource Limits:
      - Max Concurrent Agents (slider: 1-100)
      - Max Runtime Hours/Month (slider: 10-10000)
    - Billing Email (optional)
    - Settings (JSONB editor for advanced config)
  - Submit button: "Create Organization"
  - Cancel button: "Cancel"
- States: Empty, Validating (real-time feedback), Loading (spinner, form disabled), Success (redirect to `/organizations/:id`), Error (slug taken, validation errors)
- Navigation: Submit → `/organizations/:id`, Cancel → `/organizations`

**3. Organization Detail (`/organizations/:id`)**
- Layout: Header with organization name and settings button, main content area with tabs, sidebar with quick stats
- Components: Organization header (logo, name, settings button), Tab navigation (Overview, Members, Projects, Activity), Overview tab (stats cards, recent activity feed), Members tab (member list table), Projects tab (projects grid), Activity tab (activity timeline), Quick stats sidebar
- Content:
  - Organization name and logo
  - Stats cards: Total Members, Active Projects, Total Agents, Resource Usage (X/Y hours this month)
  - Recent activity feed
  - Member list: Name, Email, Role, Joined Date, Actions
  - Projects grid with project cards
- States: Loading (skeleton content), Loaded (tabs with content), Empty Members ("Invite Members" CTA), Empty Projects ("Create Project" CTA), Error
- Navigation: Click "Settings" → `/organizations/:id/settings`, Click project → `/projects/:id`, Switch tabs (Overview, Members, Projects, Activity)

**4. Organization Settings (`/organizations/:id/settings`)**
- Layout: Header with organization name, left sidebar with settings tabs, main content area with form sections
- Components: Settings sidebar navigation (General, Resources, Members, Billing tabs), General tab (organization info form, logo upload), Resources tab (resource limit sliders, usage graphs), Members tab (member management table, invite member button), Billing tab (billing email, usage summary, payment method - future), Save/Cancel buttons per tab
- Content:
  - **General Tab**: Organization Name input, Organization Slug input, Logo upload area, Description textarea
  - **Resources Tab**: Max Concurrent Agents slider, Max Runtime Hours/Month slider, Current Usage graphs, Usage alerts configuration
  - **Members Tab**: Member list table, "Invite Member" button, Role management (Owner, Admin, Member)
  - **Billing Tab**: Billing Email input, Usage Summary (current month), Payment Method (future)
- States: Loading (skeleton forms), Editing (form fields enabled), Saving (save button spinner), Saved (success toast, form disabled), Error
- Navigation: Save → stay on page with success, Cancel → `/organizations/:id`, Switch tabs (General, Resources, Members, Billing)

**Requirements:**
- Use existing layout structure (Header, Sidebar, MainContentArea)
- Implement tab navigation component
- Create reusable OrganizationCard component
- Implement slider components for resource limits
- Add empty states with clear CTAs
- Include loading skeletons for better UX
- Make all pages responsive (mobile: 1 column, tablet: 2 columns, desktop: 3 columns for grids)
- Implement proper form validation
- Add success/error toast notifications
- Use table components for member lists
- Include role badges with appropriate colors
- Implement search/filter functionality for organizations list (optional but recommended)

Generate all 4 organization pages as separate React components with full functionality, proper state management, and navigation.

