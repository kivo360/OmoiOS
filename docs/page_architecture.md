# OmoiOS Complete Page Architecture

## Authentication Pages

### Landing Page (`/`)

**Purpose**: Entry point for new and returning users; provides clear value proposition and access to login/registration.

**Layout Structure**: Full-width hero section with centered content, navigation bar at top, footer at bottom.

**Key Components**:
- Top navigation bar (Logo, "Login", "Sign Up" buttons)
- Hero section with headline, value proposition, CTA buttons
- Feature highlights section (3-4 cards)
- Social proof/testimonials section
- Footer with links

**Interactive Elements**:
- Click "Login" → Navigate to `/login`
- Click "Sign Up" → Navigate to `/register`
- Click "Login with GitHub" → OAuth flow
- Scroll to reveal features

**Navigation**:
- **From**: Direct URL, external links, marketing pages
- **To**: `/login`, `/register`, `/login/oauth`

**Content**:
- Headline: "Scale Development Without Scaling Headcount"
- Subheadline: "Autonomous engineering platform that orchestrates AI agents through adaptive workflows"
- Primary CTA: "Get Started Free"
- Secondary CTA: "Login with GitHub"
- Feature cards: "Spec-Driven Workflows", "Multi-Agent Coordination", "Real-Time Visibility", "Adaptive Discovery"

**States**:
- **Default**: Hero with CTAs visible
- **Loading**: Show loading spinner on CTA click
- **Error**: Display error message if OAuth fails

---

### Register (`/register`)

**Purpose**: Allow new users to create accounts via email/password registration.

**Layout Structure**: Centered card layout on full-width background, minimal navigation.

**Key Components**:
- Registration form (email, password, confirm password, terms checkbox)
- Form validation messages
- "Already have an account? Login" link
- "Sign up with GitHub" button
- Password strength indicator

**Interactive Elements**:
- Fill form fields
- Toggle password visibility
- Check terms checkbox
- Submit form
- Click "Login" link
- Click "Sign up with GitHub"

**Navigation**:
- **From**: Landing page, `/login` page
- **To**: `/verify-email` (after successful registration), `/login` (via link), `/login/oauth` (GitHub)

**Content**:
- Page title: "Create Your Account"
- Form fields: Email, Password, Confirm Password
- Terms checkbox: "I agree to terms and conditions"
- Submit button: "Create Account"
- Footer link: "Already have an account? Login"

**States**:
- **Empty**: Form with placeholder text
- **Validating**: Real-time validation feedback
- **Loading**: Submit button shows spinner, form disabled
- **Success**: Redirect to `/verify-email`
- **Error**: Display error message above form (email exists, weak password, etc.)

---

### Login (`/login`)

**Purpose**: Authenticate existing users via email/password or OAuth.

**Layout Structure**: Centered card layout on full-width background, minimal navigation.

**Key Components**:
- Login form (email, password, remember me checkbox)
- "Forgot password?" link
- "Login with GitHub" button
- "Don't have an account? Register" link
- Form validation messages

**Interactive Elements**:
- Fill email and password fields
- Toggle password visibility
- Check "Remember me" checkbox
- Submit form
- Click "Forgot password?" link
- Click "Login with GitHub" button
- Click "Register" link

**Navigation**:
- **From**: Landing page, `/register` page
- **To**: `/dashboard` (after successful login), `/forgot-password` (via link), `/login/oauth` (GitHub), `/register` (via link)

**Content**:
- Page title: "Welcome Back"
- Form fields: Email, Password
- Remember me checkbox: "Keep me signed in"
- Submit button: "Login"
- Footer links: "Forgot password?", "Don't have an account? Register"

**States**:
- **Empty**: Form with placeholder text
- **Loading**: Submit button shows spinner, form disabled
- **Success**: Redirect to `/dashboard` or return URL
- **Error**: Display error message above form (invalid credentials, account locked, etc.)

---

### Login OAuth (`/login/oauth`)

**Purpose**: Handle OAuth redirect flow for GitHub/GitLab authentication.

**Layout Structure**: Full-page loading state, minimal UI.

**Key Components**:
- Loading spinner
- Status message
- "Cancel" button (optional)

**Interactive Elements**:
- Automatic redirect to OAuth provider
- Click "Cancel" to abort flow

**Navigation**:
- **From**: `/login`, `/register`, landing page
- **To**: External OAuth provider → Callback → `/dashboard`

**Content**:
- Loading message: "Redirecting to GitHub..."
- Status updates: "Authorizing...", "Completing login..."

**States**:
- **Loading**: Show spinner and status message
- **Success**: Redirect to callback handler then dashboard
- **Error**: Display error message with "Try Again" button
- **Cancelled**: Redirect back to `/login`

---

### Verify Email (`/verify-email`)

**Purpose**: Confirm user email address after registration.

**Layout Structure**: Centered card layout with icon and message.

**Key Components**:
- Email icon/illustration
- Verification message
- "Resend email" button
- "Change email" link

**Interactive Elements**:
- Click "Resend email" button
- Click "Change email" link
- Click verification link from email (handled separately)

**Navigation**:
- **From**: `/register` (after registration)
- **To**: `/dashboard` (after email verification), `/register` (change email)

**Content**:
- Icon: Email/envelope illustration
- Title: "Verify Your Email"
- Message: "We've sent a verification link to [email]. Click the link in the email to activate your account."
- Resend button: "Resend Verification Email"
- Change email link: "Wrong email address?"

**States**:
- **Pending**: Show verification message
- **Resending**: Button shows spinner
- **Resent**: Show success message "Email sent!"
- **Verified**: Auto-redirect to dashboard (if link clicked)

---

### Forgot Password (`/forgot-password`)

**Purpose**: Initiate password reset flow by sending reset email.

**Layout Structure**: Centered card layout, minimal navigation.

**Key Components**:
- Email input form
- Submit button
- "Back to login" link
- Success message area

**Interactive Elements**:
- Enter email address
- Submit form
- Click "Back to login" link

**Navigation**:
- **From**: `/login` page
- **To**: `/login` (via back link), `/reset-password` (after email sent, via email link)

**Content**:
- Title: "Reset Your Password"
- Message: "Enter your email address and we'll send you a link to reset your password."
- Email input field
- Submit button: "Send Reset Link"
- Footer link: "Back to login"

**States**:
- **Empty**: Form with placeholder
- **Loading**: Submit button shows spinner
- **Success**: Show success message "Check your email for reset instructions"
- **Error**: Display error message (email not found, etc.)

---

### Reset Password (`/reset-password`)

**Purpose**: Allow users to set new password after clicking reset link.

**Layout Structure**: Centered card layout with form.

**Key Components**:
- Password input fields (new password, confirm)
- Password strength indicator
- Submit button
- Token validation (hidden)

**Interactive Elements**:
- Enter new password
- Confirm password
- Toggle password visibility
- Submit form

**Navigation**:
- **From**: Email reset link (with token)
- **To**: `/login` (after successful reset)

**Content**:
- Title: "Set New Password"
- Form fields: New Password, Confirm Password
- Password strength indicator
- Submit button: "Reset Password"

**States**:
- **Invalid Token**: Show error "Reset link expired or invalid"
- **Loading**: Submit button shows spinner
- **Success**: Show success message, redirect to login
- **Error**: Display validation errors

---

## Organization Pages

### Organizations List (`/organizations`)

**Purpose**: Display all organizations the user belongs to, enable switching context and creating new organizations.

**Layout Structure**: Header with "Create Organization" button, grid/list of organization cards, sidebar with user profile.

**Key Components**:
- Page header with title and "Create Organization" button
- Organization cards grid (3 columns on desktop, 1 on mobile)
- Organization card (logo, name, member count, role badge, "View" button)
- Empty state illustration
- User profile sidebar

**Interactive Elements**:
- Click organization card → Navigate to organization detail
- Click "Create Organization" button → Navigate to create page
- Click "View" button on card
- Search/filter organizations (optional)

**Navigation**:
- **From**: Dashboard, user menu
- **To**: `/organizations/new` (create), `/organizations/:id` (view detail)

**Content**:
- Page title: "Organizations"
- Organization cards show:
  - Organization logo/avatar
  - Organization name
  - Member count: "X members"
  - User's role badge: "Owner", "Admin", "Member"
  - Last active: "Active 2 hours ago"
- Empty state: "You're not a member of any organizations yet"

**States**:
- **Loading**: Show skeleton cards
- **Empty**: Show empty state with "Create Organization" CTA
- **Populated**: Show organization cards grid
- **Error**: Show error message with retry button

---

### Create Organization (`/organizations/new`)

**Purpose**: Create a new organization with initial configuration.

**Layout Structure**: Centered form layout with multi-step wizard (optional) or single form.

**Key Components**:
- Organization creation form
- Form sections: Basic Info, Resource Limits, Settings
- Form validation messages
- Cancel and Submit buttons
- Resource limit sliders/inputs

**Interactive Elements**:
- Fill organization name
- Enter organization slug (auto-generated from name)
- Set resource limits (max agents, max runtime hours)
- Configure settings (JSONB editor or form fields)
- Submit form
- Cancel creation

**Navigation**:
- **From**: `/organizations` list page
- **To**: `/organizations/:id` (after creation), `/organizations` (cancel)

**Content**:
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

**States**:
- **Empty**: Form with placeholders
- **Validating**: Real-time validation feedback
- **Loading**: Submit button shows spinner, form disabled
- **Success**: Redirect to new organization detail page
- **Error**: Display error message (slug taken, validation errors)

---

### Organization Detail (`/organizations/:id`)

**Purpose**: View organization overview, members, and quick access to settings.

**Layout Structure**: Header with organization name and settings button, main content area with tabs, sidebar with quick stats.

**Key Components**:
- Organization header (logo, name, settings button)
- Tab navigation (Overview, Members, Projects, Activity)
- Overview tab: Stats cards, recent activity feed
- Members tab: Member list table
- Projects tab: Projects grid
- Activity tab: Activity timeline
- Quick stats sidebar

**Interactive Elements**:
- Switch tabs
- Click "Settings" button
- Click member → View member details (future)
- Click project → Navigate to project
- Filter/sort members and projects

**Navigation**:
- **From**: `/organizations` list, user menu (switch org)
- **To**: `/organizations/:id/settings` (settings), `/projects/:id` (project detail)

**Content**:
- Organization name and logo
- Stats cards:
  - Total Members
  - Active Projects
  - Total Agents
  - Resource Usage (X/Y hours this month)
- Recent activity feed
- Member list with: Name, Email, Role, Joined Date, Actions
- Projects grid with project cards

**States**:
- **Loading**: Show skeleton content
- **Loaded**: Show tabs with content
- **Empty Members**: Show "Invite Members" CTA
- **Empty Projects**: Show "Create Project" CTA
- **Error**: Show error message

---

### Organization Settings (`/organizations/:id/settings`)

**Purpose**: Configure organization settings, resource limits, members, and billing.

**Layout Structure**: Header with organization name, left sidebar with settings tabs, main content area with form sections.

**Key Components**:
- Settings sidebar navigation (General, Resources, Members, Billing tabs)
- General tab: Organization info form, logo upload
- Resources tab: Resource limit sliders, usage graphs
- Members tab: Member management table, invite member button
- Billing tab: Billing email, usage summary, payment method (future)
- Save/Cancel buttons per tab

**Interactive Elements**:
- Switch settings tabs
- Edit organization name, slug
- Upload organization logo
- Adjust resource limits
- Invite members
- Remove members
- Update billing email
- Save changes per tab

**Navigation**:
- **From**: `/organizations/:id` detail page
- **To**: `/organizations/:id` (after save), `/organizations` (cancel)

**Content**:
- **General Tab**:
  - Organization Name input
  - Organization Slug input
  - Logo upload area
  - Description textarea
- **Resources Tab**:
  - Max Concurrent Agents slider
  - Max Runtime Hours/Month slider
  - Current Usage graphs
  - Usage alerts configuration
- **Members Tab**:
  - Member list table
  - "Invite Member" button
  - Role management (Owner, Admin, Member)
- **Billing Tab**:
  - Billing Email input
  - Usage Summary (current month)
  - Payment Method (future)

**States**:
- **Loading**: Show skeleton forms
- **Editing**: Form fields enabled
- **Saving**: Save button shows spinner
- **Saved**: Show success toast, form disabled
- **Error**: Show error message

---

## Dashboard & Project Pages

### Dashboard (`/dashboard`)

**Purpose**: Provide overview of all projects, active specs, quick actions, and recent activity.

**Layout Structure**: Top navigation bar, left sidebar with main nav, main content area (2-column: overview + activity feed), right sidebar (collapsible activity feed).

**Key Components**:
- Top navigation bar (Logo, Projects, Search, Notifications, Profile menu)
- Left sidebar navigation (Home, Projects, Board, Graph, Specs, Stats, Agents, Cost, Audit)
- Overview section (stats cards: Total Specs, Active Agents, Tickets in Progress, Recent Commits)
- Active Specs grid (spec cards with progress bars)
- Quick Actions section (New Spec, New Project buttons)
- Recent Activity sidebar (collapsible chronological feed)
- Command Palette (Cmd+K)

**Interactive Elements**:
- Click spec card → Navigate to spec workspace
- Click "New Spec" button → Create spec modal/page
- Click "New Project" button → Navigate to create project
- Click activity item → Navigate to related page
- Use Command Palette (Cmd+K) → Quick navigation/search
- Click notifications → View notification panel
- Click profile menu → User menu

**Navigation**:
- **From**: `/login` (after login), any page (via logo/home)
- **To**: All project pages, spec pages, settings pages

**Content**:
- Stats cards:
  - Total Specs: "5"
  - Active Agents: "3"
  - Tickets in Progress: "12"
  - Recent Commits: "8"
- Spec cards show:
  - Spec name and description
  - Progress bar (0-100%)
  - Status badge (Draft, Requirements, Design, Tasks, Executing, Completed)
  - Last updated timestamp
  - Quick actions ([View] [Edit] [Export])
- Activity feed items:
  - "Spec 'Auth System' requirements approved"
  - "Agent worker-1 completed task 'Setup JWT'"
  - "Discovery: Bug found in login flow"
  - "Guardian intervention sent to worker-2"

**States**:
- **Loading**: Show skeleton cards and stats
- **Empty**: Show empty state with "Create Your First Project" CTA
- **Populated**: Show overview with specs and activity
- **Error**: Show error message with retry

---

### Projects List (`/projects`)

**Purpose**: Display all projects user has access to, enable filtering and creation.

**Layout Structure**: Header with "Create Project" button, filter/search bar, projects grid/list view toggle.

**Key Components**:
- Page header with "Create Project" button
- Filter bar (All, Active, Archived, By Organization)
- Search input
- View toggle (Grid/List)
- Project cards grid (3 columns desktop, 1 mobile)
- Project card (thumbnail, name, description, org badge, stats, actions)
- Empty state

**Interactive Elements**:
- Click project card → Navigate to project overview
- Click "Create Project" button → Navigate to create page
- Filter projects (All, Active, Archived)
- Search projects by name
- Toggle grid/list view
- Click project actions menu → Quick actions

**Navigation**:
- **From**: Dashboard, sidebar navigation
- **To**: `/projects/new` (create), `/projects/:id` (view project)

**Content**:
- Page title: "Projects"
- Project cards show:
  - Project thumbnail/icon
  - Project name
  - Description (truncated)
  - Organization badge
  - Stats: "X tickets, Y agents active"
  - Last active: "Updated 2 hours ago"
- Empty state: "No projects yet. Create your first project to get started."

**States**:
- **Loading**: Show skeleton cards
- **Empty**: Show empty state with CTA
- **Filtered**: Show filtered results with count
- **Error**: Show error message

---

### Create Project (`/projects/new`)

**Purpose**: Create new project with initial configuration.

**Layout Structure**: Centered form layout with multi-step wizard or single form.

**Key Components**:
- Project creation form
- Form sections: Basic Info, Initial Setup, Configuration
- Organization selector dropdown
- AI-assisted exploration toggle
- Form validation
- Cancel and Submit buttons

**Interactive Elements**:
- Fill project name and description
- Select organization
- Toggle AI-assisted exploration
- Configure initial settings
- Submit form
- Cancel creation

**Navigation**:
- **From**: `/projects` list, dashboard "New Project" button
- **To**: `/projects/:id` (after creation), `/projects/:id/explore` (if AI exploration enabled), `/projects` (cancel)

**Content**:
- Page title: "Create New Project"
- Form fields:
  - Project Name (required)
  - Description (textarea)
  - Organization (dropdown, required)
  - Initial Setup:
    - "Use AI-assisted exploration" checkbox
    - "Create initial spec" checkbox
  - Configuration (optional advanced settings)
- Submit button: "Create Project"
- Cancel button: "Cancel"

**States**:
- **Empty**: Form with placeholders
- **Validating**: Real-time validation
- **Loading**: Submit button spinner
- **Success**: Redirect to project overview or exploration
- **Error**: Show error message

---

### Project Overview (`/projects/:id`)

**Purpose**: Main project dashboard showing overview metrics and quick navigation to all project features.

**Layout Structure**: Project header with name and settings, main content area with overview cards and quick links, right sidebar with recent activity.

**Key Components**:
- Project header (name, description, settings button, GitHub connection status)
- Overview stats cards (Tickets, Tasks, Agents, Completion Rate)
- Quick navigation cards (Board, Graph, Specs, Stats, Agents, Phases)
- Recent activity feed
- Active tickets preview
- Active agents preview

**Interactive Elements**:
- Click navigation cards → Navigate to respective pages
- Click "Settings" button → Project settings
- Click ticket preview → Navigate to ticket detail
- Click agent preview → Navigate to agent detail
- Click activity item → Navigate to related page

**Navigation**:
- **From**: `/projects` list, dashboard
- **To**: All project sub-pages (Board, Graph, Specs, Stats, Agents, Settings, etc.)

**Content**:
- Project name and description
- Stats cards:
  - Total Tickets: "24"
  - Active Tasks: "8"
  - Active Agents: "3"
  - Completion Rate: "65%"
- Quick nav cards:
  - Kanban Board
  - Dependency Graph
  - Spec Workspace
  - Statistics
  - Agents
  - Phases
- Recent activity: Last 10 events
- Active tickets: Top 5 tickets by priority

**States**:
- **Loading**: Show skeleton content
- **Loaded**: Show overview with stats
- **Empty**: Show "Create Your First Ticket" CTA
- **Error**: Show error message

---

### AI-Assisted Exploration (`/projects/:id/explore`)

**Purpose**: AI analyzes project and generates initial requirements and design documents.

**Layout Structure**: Full-page wizard with progress indicator, step-by-step generation, preview panels.

**Key Components**:
- Progress indicator (Step 1: Analyzing, Step 2: Generating Requirements, Step 3: Creating Design)
- Project analysis panel
- Generated requirements preview
- Generated design preview
- Accept/Edit/Reject buttons per step
- Final review panel

**Interactive Elements**:
- Start exploration
- Review generated content
- Edit generated requirements/design
- Accept step → Move to next
- Reject step → Regenerate
- Finalize → Create spec

**Navigation**:
- **From**: `/projects/new` (if AI exploration enabled), `/projects/:id` (manual trigger)
- **To**: `/projects/:id/specs/:specId` (after creation), `/projects/:id` (cancel)

**Content**:
- Step 1: Project Analysis
  - "Analyzing project structure..."
  - File tree analysis
  - Technology stack detection
- Step 2: Requirements Generation
  - Generated EARS-style requirements
  - Preview panel with edit capability
- Step 3: Design Generation
  - Architecture diagrams
  - Sequence diagrams
  - Data models
- Final Review: Combined spec preview

**States**:
- **Analyzing**: Show progress spinner
- **Generating**: Show step progress
- **Review**: Show generated content with edit options
- **Saving**: Show save progress
- **Complete**: Redirect to spec workspace
- **Error**: Show error with retry option

---

## Spec Workspace Pages

### Specs List (`/projects/:id/specs`)

**Purpose**: Display all specs for project, enable filtering and creation.

**Layout Structure**: Header with "Create Spec" button, filter/search bar, specs grid/list.

**Key Components**:
- Page header with "Create Spec" button
- Filter bar (All, Draft, Requirements, Design, Tasks, Executing, Completed)
- Search input
- Spec cards grid (2 columns desktop, 1 mobile)
- Spec card (name, description, status badge, progress bar, last updated, actions)
- Empty state

**Interactive Elements**:
- Click spec card → Navigate to spec workspace
- Click "Create Spec" button → Create spec modal/page
- Filter specs by status
- Search specs by name
- Click spec actions menu → Export, Archive, Delete

**Navigation**:
- **From**: Project overview, sidebar navigation
- **To**: `/projects/:id/specs/:specId` (view spec), create spec modal/page

**Content**:
- Page title: "Specs"
- Spec cards show:
  - Spec name
  - Description (truncated)
  - Status badge with color coding
  - Progress bar (0-100%)
  - Last updated timestamp
  - Quick actions ([View] [Edit] [Export])
- Empty state: "No specs yet. Create your first spec to get started."

**States**:
- **Loading**: Skeleton cards
- **Empty**: Empty state with CTA
- **Filtered**: Filtered results
- **Error**: Error message

---

### Spec Workspace (`/projects/:id/specs/:specId`)

**Purpose**: Multi-tab workspace for viewing and editing spec content (Requirements, Design, Tasks, Execution).

**Layout Structure**: Spec header with name and actions, left sidebar with spec switcher, main content area with tabs, right sidebar (collapsible) with spec metadata.

**Key Components**:
- Spec header (name, status badge, export button, settings menu)
- Left sidebar (spec switcher dropdown, spec list)
- Tab navigation (Requirements, Design, Tasks, Execution)
- Requirements tab: Structured blocks editor (Notion-style)
- Design tab: Diagram viewer/editor, architecture diagrams
- Tasks tab: Task breakdown table with dependencies
- Execution tab: Progress dashboard, running tasks, PRs
- Right sidebar: Spec metadata, version history, linked tickets

**Interactive Elements**:
- Switch tabs
- Switch specs (via sidebar dropdown)
- Edit requirements blocks (add, edit, delete blocks)
- View/edit design diagrams
- Edit task breakdown
- View execution progress
- Export spec (Markdown, YAML, PDF)
- Link/unlink tickets

**Navigation**:
- **From**: `/projects/:id/specs` list, project overview
- **To**: All tabs within spec, export modal, ticket detail (via links)

**Content**:
- **Requirements Tab**:
  - EARS-style requirements blocks
  - Structured format: "WHEN [condition] THE SYSTEM SHALL [action]"
  - Acceptance criteria blocks
- **Design Tab**:
  - Architecture diagrams (Mermaid or image)
  - Sequence diagrams
  - Data models
  - API specifications
- **Tasks Tab**:
  - Task breakdown table
  - Dependencies visualization
  - Task status indicators
- **Execution Tab**:
  - Overall progress bar
  - Test coverage percentage
  - Running tasks section
  - Pull Requests section

**States**:
- **Loading**: Show skeleton content
- **Editing**: Show edit mode with save button
- **Saving**: Show save progress
- **Saved**: Show success indicator
- **Error**: Show error message

---

## Kanban Board Pages

### Kanban Board (`/board/:projectId`)

**Purpose**: Visual Kanban board for managing tickets through workflow phases with drag-and-drop.

**Layout Structure**: Board header with filters and view options, horizontal scrolling board with columns, ticket cards in columns, ticket detail drawer (slides from right).

**Key Components**:
- Board header (project name, filters, view switcher, "Create Ticket" button)
- Filter bar (Type, Phase, Status, Priority, Search)
- Board columns (Backlog, Requirements, Implementation, Testing, Done, Blocked)
- Ticket cards (title, phase badge, priority indicator, assignee, commit stats, blocking indicator)
- WIP limit indicators per column
- Ticket detail drawer (slides from right on click)
- View switcher (Kanban, List, Graph)

**Interactive Elements**:
- Drag and drop tickets between columns
- Click ticket card → Open detail drawer
- Click "Create Ticket" button → Create ticket modal
- Filter tickets (type, phase, status, priority)
- Search tickets
- Keyboard navigation (j/k up/down, h/l left/right, Enter to open)
- Toggle view (Kanban/List/Graph)
- Click column header → Column settings

**Navigation**:
- **From**: Project overview, sidebar navigation
- **To**: Ticket detail drawer (inline), `/board/:projectId/:ticketId` (full page), create ticket modal

**Content**:
- Board columns show:
  - Column name
  - Ticket count
  - WIP limit indicator (if exceeded)
- Ticket cards show:
  - Ticket title
  - Phase badge (color-coded)
  - Priority indicator (CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=gray)
  - Assigned agent name
  - Commit stats: "+X -Y"
  - Blocking indicator (if blocked)
- Empty columns: "Drop tickets here"

**States**:
- **Loading**: Show skeleton columns
- **Empty**: Show empty board with "Create First Ticket" CTA
- **Dragging**: Show drag preview and drop zones
- **Filtered**: Show filtered tickets with count
- **Error**: Show error message

---

### Ticket Detail (`/board/:projectId/:ticketId`)

**Purpose**: Full ticket details with tabs for comments, tasks, commits, blocking relationships, and diagnostic reasoning.

**Layout Structure**: Ticket header with title and actions, tab navigation, main content area with tab content, right sidebar with ticket metadata.

**Key Components**:
- Ticket header (title, status badge, phase badge, priority indicator, actions menu)
- Tab navigation (Details, Comments, Tasks, Commits, Blocking, Reasoning)
- Details tab: Description, metadata, history
- Comments tab: Comment thread, comment editor, mention autocomplete
- Tasks tab: Task list with status, agent assignment
- Commits tab: Commit list with diffs
- Blocking tab: Dependency graph, blocker list, blocked-by list
- Reasoning tab: Diagnostic reasoning chain, discovery events
- Right sidebar: Ticket metadata, linked spec, related tickets

**Interactive Elements**:
- Switch tabs
- Edit ticket (title, description, status, priority)
- Add comment with @mentions
- Attach files to comments
- View task details
- View commit diffs
- Add/remove blocking relationships
- View diagnostic reasoning
- Transition ticket status
- Link/unlink related tickets

**Navigation**:
- **From**: Kanban board (click ticket), search results, activity feed
- **To**: Task detail, commit detail, related tickets, spec workspace

**Content**:
- **Details Tab**:
  - Ticket title and description
  - Status and phase badges
  - Priority indicator
  - Created/updated timestamps
  - Assigned agent
  - Linked spec (if any)
- **Comments Tab**:
  - Comment thread (chronological)
  - Comment editor with @mention support
  - File attachments
- **Tasks Tab**:
  - Task list with status, agent, progress
- **Commits Tab**:
  - Commit list with messages, authors, diffs
- **Blocking Tab**:
  - Dependency graph visualization
  - Blocker tickets list
  - Blocked-by tickets list
- **Reasoning Tab**:
  - Discovery events timeline
  - Task spawning reasoning
  - Ticket linking reasoning

**States**:
- **Loading**: Show skeleton content
- **Loaded**: Show ticket with tabs
- **Editing**: Show edit mode
- **Saving**: Show save progress
- **Error**: Show error message

---

## Graph & Visualization Pages

### Dependency Graph (`/graph/:projectId`)

**Purpose**: Visualize full project dependency graph showing tickets, tasks, and their relationships.

**Layout Structure**: Full-page graph canvas with controls overlay, left sidebar with filters, right sidebar with node details.

**Key Components**:
- Graph canvas (React Flow or similar)
- Zoom/pan controls
- Filter sidebar (Phase, Status, Type, Agent)
- Node details panel (shows on node click)
- Legend (node types, edge types)
- Search bar
- View options (Show/Hide nodes, layout options)

**Interactive Elements**:
- Pan graph (drag background)
- Zoom in/out (mouse wheel, buttons)
- Click node → Show details panel
- Click edge → Show relationship details
- Filter nodes by phase/status/type
- Search for specific nodes
- Toggle node visibility
- Change layout (hierarchical, force-directed)

**Navigation**:
- **From**: Project overview, sidebar navigation
- **To**: Ticket detail (click ticket node), task detail (click task node), `/graph/:projectId/:ticketId` (focused view)

**Content**:
- Graph nodes:
  - Ticket nodes (rectangles, color by status)
  - Task nodes (circles, color by phase)
  - Discovery nodes (diamonds, purple)
- Graph edges:
  - Dependency edges (blocking relationships)
  - Discovery edges (spawning relationships)
  - Normal flow edges (phase progression)
- Node labels: Ticket/task title
- Edge labels: Relationship type

**States**:
- **Loading**: Show loading spinner
- **Rendering**: Show graph with nodes appearing
- **Empty**: Show "No dependencies yet" message
- **Error**: Show error message

---

### Ticket Graph (`/graph/:projectId/:ticketId`)

**Purpose**: Focused dependency graph for a specific ticket showing its blocking relationships.

**Layout Structure**: Same as full graph but centered on selected ticket, with ticket detail panel.

**Key Components**:
- Graph canvas (focused on ticket)
- Ticket detail panel (inline or sidebar)
- Related tickets highlighted
- Path highlighting (show dependency chains)

**Interactive Elements**:
- Same as full graph
- Click related ticket → Navigate to ticket detail
- Highlight dependency paths

**Navigation**:
- **From**: Ticket detail page, full graph
- **To**: Related ticket details, full graph

**Content**:
- Centered ticket node (highlighted)
- Blocker tickets (above, red)
- Blocked tickets (below, orange)
- Dependency paths highlighted

**States**:
- Same as full graph
- **Focused**: Ticket node highlighted and centered

---

## Phase Management Pages

### Phase Overview (`/projects/:projectId/phases`)

**Purpose**: Dashboard showing all phases with task counts, active agents, and discovery indicators.

**Layout Structure**: Page header, phase cards grid (2-3 columns), each card showing phase stats and actions.

**Key Components**:
- Page header ("Phases" title, "Create Custom Phase" button)
- Phase cards grid
- Phase card (phase number, name, description, task stats, agent count, discovery indicator, "View Tasks" button)
- Empty state (if no phases)

**Interactive Elements**:
- Click phase card → Navigate to phase detail
- Click "View Tasks" button → Navigate to phase-specific task list
- Click "Create Custom Phase" button → Create phase page
- Filter phases (All, Active, Completed, Idle)

**Navigation**:
- **From**: Project overview, sidebar navigation
- **To**: `/projects/:projectId/phases/:phaseId` (phase detail), `/projects/:projectId/phases/new` (create), `/projects/:projectId/tasks/phases` (task management)

**Content**:
- Phase cards show:
  - Phase number and name: "Phase 1: Requirements Analysis"
  - Description: Brief phase purpose
  - Task stats: "28 total, 22 done, 2 active"
  - Active agents: "2 agents working"
  - Discovery indicator: "3 new branches spawned"
  - Status badge: "Active", "Completed", "Idle"
  - "View Tasks →" button

**States**:
- **Loading**: Skeleton cards
- **Empty**: "No phases configured" message
- **Populated**: Phase cards grid
- **Error**: Error message

---

### Phase Detail (`/projects/:projectId/phases/:phaseId`)

**Purpose**: View and edit phase configuration including done definitions, phase prompt, expected outputs, and transitions.

**Layout Structure**: Phase header with name and actions, tab navigation, main content area with form sections, save/cancel buttons.

**Key Components**:
- Phase header (phase ID, name, description, edit/save buttons)
- Tab navigation (Basic Info, Done Definitions, Expected Outputs, Phase Prompt, Transitions, Configuration)
- Basic Info tab: Name, description, sequence order, terminal status
- Done Definitions tab: List of completion criteria (add/edit/delete)
- Expected Outputs tab: Artifact patterns list
- Phase Prompt tab: Large text editor for agent instructions
- Transitions tab: Allowed transitions checklist
- Configuration tab: JSONB editor or form fields for phase-specific settings
- Save/Cancel buttons

**Interactive Elements**:
- Switch tabs
- Edit phase name, description
- Add/edit/delete done definitions
- Add/edit/delete expected outputs
- Edit phase prompt (large text editor)
- Toggle allowed transitions
- Edit configuration (JSONB or form)
- Save changes
- Cancel edits
- Delete phase (if custom)

**Navigation**:
- **From**: Phase overview, project settings
- **To**: Phase overview (after save), `/projects/:projectId/phases` (cancel)

**Content**:
- **Basic Info Tab**:
  - Phase ID (read-only for default phases)
  - Name input
  - Description textarea
  - Sequence Order number input
  - Terminal Phase checkbox
- **Done Definitions Tab**:
  - List of criteria (one per line or item)
  - "+ Add Criterion" button
  - Example: "Component code files created", "Minimum 3 test cases written"
- **Phase Prompt Tab**:
  - Large text editor (Markdown supported)
  - Preview toggle
  - Example: "YOU ARE A SOFTWARE ENGINEER IN THE IMPLEMENTATION PHASE..."
- **Transitions Tab**:
  - Checklist of phase IDs
  - Note about discovery-based spawning bypassing restrictions
- **Configuration Tab**:
  - Timeout (seconds)
  - Max Retries
  - Retry Strategy dropdown
  - WIP Limit

**States**:
- **Viewing**: Read-only mode
- **Editing**: Form fields enabled, save button visible
- **Saving**: Save button shows spinner
- **Saved**: Success message, form disabled
- **Error**: Error message

---

### Create Custom Phase (`/projects/:projectId/phases/new`)

**Purpose**: Create new custom phase for specialized workflows.

**Layout Structure**: Same as Phase Detail but in creation mode, with phase ID input.

**Key Components**:
- Phase creation form (same tabs as Phase Detail)
- Phase ID input (must start with "PHASE_")
- Form validation
- Create/Cancel buttons

**Interactive Elements**:
- Enter phase ID (validated format)
- Fill all phase properties
- Create phase
- Cancel creation

**Navigation**:
- **From**: Phase overview "Create Custom Phase" button
- **To**: `/projects/:projectId/phases/:phaseId` (after creation), `/projects/:projectId/phases` (cancel)

**Content**:
- Same as Phase Detail but with:
  - Phase ID input (required, must start with "PHASE_")
  - All other fields same as Phase Detail

**States**:
- **Empty**: Form with placeholders
- **Validating**: Real-time validation
- **Creating**: Create button shows spinner
- **Success**: Redirect to new phase detail
- **Error**: Error message (ID taken, validation errors)

---

### Task Phase Management (`/projects/:projectId/tasks/phases`)

**Purpose**: Organize tasks by phase, move tasks between phases, bulk phase transitions.

**Layout Structure**: Page header with filters, expandable phase sections, task cards within sections, bulk actions bar.

**Key Components**:
- Page header ("Tasks by Phase" title, filters, search)
- Filter bar (All Phases, All Status, All Priorities, Search)
- Expandable phase sections (one per phase)
- Task cards within sections (task description, status, agent, priority, "Move to Phase" button)
- Bulk actions bar (Select All, Move Selected to Phase, Bulk Edit)
- Empty states per phase

**Interactive Elements**:
- Expand/collapse phase sections
- Filter tasks (phase, status, priority)
- Search tasks
- Select tasks (checkbox)
- Click "Move to Phase" button → Move task modal
- Bulk select tasks
- Bulk move tasks to phase
- Click task card → Navigate to task detail

**Navigation**:
- **From**: Phase overview, project overview
- **To**: `/tasks/:taskId/move-phase` (move task modal), task detail pages

**Content**:
- Phase sections show:
  - Phase name and badge: "PHASE_IMPLEMENTATION (28 tasks)"
  - Expand/collapse button
  - Task count: "Total: 28, Done: 22, Active: 2"
- Task cards show:
  - Task description
  - Status badge
  - Assigned agent name
  - Priority indicator
  - Created timestamp
  - "Move to Phase ▼" button
- Empty phase sections: "No tasks in this phase"

**States**:
- **Loading**: Skeleton sections
- **Empty**: Empty phase sections
- **Populated**: Expandable sections with tasks
- **Filtered**: Filtered tasks with count
- **Error**: Error message

---

### Phase Gate Approvals (`/projects/:projectId/phase-gates`)

**Purpose**: Review and approve phase transitions with artifact validation.

**Layout Structure**: Page header with filters, pending approvals list, approval detail modal/drawer.

**Key Components**:
- Page header ("Phase Gate Approvals" title, filters)
- Filter bar (All Phases, Pending, Approved, Rejected)
- Pending approvals list (approval cards)
- Approval card (ticket name, current phase, requested transition, gate criteria status, artifacts list, action buttons)
- Approval detail modal/drawer (full approval review)
- Recent approvals section

**Interactive Elements**:
- Filter approvals (phase, status)
- Click approval card → Open detail view
- Review gate criteria
- Review artifacts (code changes, test coverage)
- Approve transition
- Reject transition
- Request more information

**Navigation**:
- **From**: Project overview, notifications (approval pending)
- **To**: Ticket detail (via approval card), approval detail modal

**Content**:
- Approval cards show:
  - Ticket name and ID
  - Current phase → Requested phase
  - Requested by: Agent name
  - Requested at: Timestamp
  - Gate criteria status: ✓/✗ indicators
  - Artifacts: "code_changes: ✓", "test_coverage: 85% ✓"
  - Action buttons: [Review Details] [Approve] [Reject]
- Approval detail shows:
  - Full transition request
  - All gate criteria with validation status
  - Artifact review (code diff, test report)
  - Comments section
  - Approval decision buttons

**States**:
- **Loading**: Skeleton cards
- **Empty**: "No pending approvals" message
- **Pending**: Approval cards list
- **Reviewing**: Approval detail modal open
- **Approving**: Show approval progress
- **Error**: Error message

---

## Statistics & Monitoring Pages

### Statistics Dashboard (`/projects/:projectId/stats`)

**Purpose**: Analytics dashboard showing project metrics across tickets, agents, code, costs, and phases.

**Layout Structure**: Page header, tab navigation, main content area with metrics sections, charts and graphs.

**Key Components**:
- Page header ("Statistics" title, date range selector)
- Tab navigation (Overview, Tickets, Agents, Code, Cost, Phases)
- Overview tab: High-level metrics cards, summary charts
- Tickets tab: Ticket statistics, completion rates, cycle times
- Agents tab: Agent performance metrics, alignment scores
- Code tab: Code change statistics, test coverage, commits
- Cost tab: LLM costs breakdown, resource usage
- Phases tab: Phase performance metrics, efficiency, bottlenecks
- Charts (line charts, bar charts, pie charts)
- Export button (export report)

**Interactive Elements**:
- Switch tabs
- Select date range
- Filter metrics (by phase, agent, date)
- Hover charts for details
- Export report (PDF, CSV)
- Drill down into specific metrics

**Navigation**:
- **From**: Project overview, sidebar navigation
- **To**: Ticket detail (from ticket metrics), agent detail (from agent metrics)

**Content**:
- **Overview Tab**:
  - Total Tickets, Tasks, Agents
  - Completion Rate
  - Average Cycle Time
  - Summary charts
- **Tickets Tab**:
  - Tickets by phase chart
  - Completion rates by type
  - Cycle time distribution
- **Agents Tab**:
  - Agent performance table
  - Alignment scores
  - Tasks completed per agent
- **Code Tab**:
  - Lines changed chart
  - Test coverage trend
  - Commits over time
- **Cost Tab**:
  - LLM costs by phase
  - Resource usage graphs
  - Budget status
- **Phases Tab**:
  - Phase performance overview
  - Phase efficiency metrics
  - Phase bottlenecks
  - Discovery activity by phase

**States**:
- **Loading**: Skeleton charts
- **Loaded**: Show metrics and charts
- **No Data**: Show "No data available" message
- **Error**: Error message

---

### Activity Timeline (`/projects/:projectId/activity`)

**Purpose**: Chronological feed of all events (ticket created, discoveries, phase transitions, agent actions, memory operations).

**Layout Structure**: Page header with filters, timeline feed (vertical), event cards, infinite scroll.

**Key Components**:
- Page header ("Activity Timeline" title, filters)
- Filter bar (All Events, Discoveries, Phase Transitions, Agent Actions, Memory Operations, Commits, Test Results)
- Date range selector
- Timeline feed (vertical, chronological)
- Event cards (icon, event type, description, timestamp, related links)
- Load more button / infinite scroll
- Empty state

**Interactive Elements**:
- Filter events by type
- Select date range
- Click event card → Navigate to related page
- Scroll to load more events
- Search timeline

**Navigation**:
- **From**: Project overview, sidebar navigation
- **To**: Ticket detail, task detail, agent detail, spec workspace (via event links)

**Content**:
- Event cards show:
  - Event icon (color-coded by type)
  - Event type badge: "Discovery", "Phase Transition", "Memory Saved"
  - Description: "Agent worker-1 discovered optimization opportunity"
  - Timestamp: "2 hours ago"
  - Related links: [View Ticket] [View Task] [View Discovery]
- Event types:
  - Ticket created/completed
  - Discovery events
  - Phase transitions
  - Agent interventions
  - Memory operations
  - Commits
  - Test results

**States**:
- **Loading**: Skeleton event cards
- **Empty**: "No activity yet" message
- **Filtered**: Filtered events with count
- **Loading More**: Show loading indicator
- **Error**: Error message

---

## Agent Management Pages

### Agents Overview (`/agents`)

**Purpose**: View all agents with status, phase assignment, performance metrics, and spawn new agents.

**Layout Structure**: Page header with "Spawn Agent" button, agent metrics cards, agent list table/cards, filters.

**Key Components**:
- Page header ("Agents" title, "Spawn Agent" button)
- Agent metrics cards (Total, Active, Idle, Stuck, Average Alignment)
- Filter bar (All, Active, Idle, Stuck, By Phase, Search)
- Agent list (table or cards)
- Agent card/row (ID, type, status, phase, current task, alignment score, metrics, actions)
- Empty state

**Interactive Elements**:
- Click "Spawn Agent" button → Spawn agent modal/page
- Filter agents (status, phase)
- Search agents
- Click agent card → Navigate to agent detail
- Click "Intervene" button → Intervention modal
- Click "Assign Task" button → Task assignment modal

**Navigation**:
- **From**: Project overview, sidebar navigation
- **To**: `/agents/spawn` (spawn agent), `/agents/:agentId` (agent detail)

**Content**:
- Metrics cards:
  - Total Agents: "5"
  - Active: "3"
  - Idle: "1"
  - Stuck: "1"
  - Average Alignment: "78%"
- Agent cards show:
  - Agent ID and type
  - Status badge (🟢 Active, 🟡 Idle, 🔴 Stuck)
  - Phase assignment: "PHASE_IMPLEMENTATION"
  - Current task: "Implement JWT" or "None"
  - Alignment score: "85%" (if active)
  - Tasks completed: "8"
  - Commits: "15"
  - Lines changed: "+2,450 -120"
  - Actions: [View Details] [Intervene] [Assign Task]

**States**:
- **Loading**: Skeleton cards
- **Empty**: "No agents yet" message
- **Populated**: Agent list with metrics
- **Filtered**: Filtered agents
- **Error**: Error message

---

### Spawn Agent (`/agents/spawn`)

**Purpose**: Create new agent with phase assignment and capabilities.

**Layout Structure**: Centered form layout with agent configuration options.

**Key Components**:
- Agent creation form
- Agent type selector (worker, validator, monitor)
- Phase assignment dropdown
- Capabilities selector (multi-select)
- Capacity input
- Tags input
- Create/Cancel buttons

**Interactive Elements**:
- Select agent type
- Select phase assignment
- Select capabilities (checkboxes)
- Set capacity
- Add tags
- Create agent
- Cancel creation

**Navigation**:
- **From**: `/agents` overview page
- **To**: `/agents/:agentId` (after creation), `/agents` (cancel)

**Content**:
- Form fields:
  - Agent Type: [Worker ▼] [Validator] [Monitor]
  - Phase Assignment: [PHASE_IMPLEMENTATION ▼] (dropdown)
  - Capabilities: [ ] Python [ ] FastAPI [ ] PostgreSQL [ ] Testing
  - Capacity: [1] (number input)
  - Tags: [worker] [implementation] (tag input)
- Create button: "Spawn Agent"
- Cancel button: "Cancel"

**States**:
- **Empty**: Form with defaults
- **Validating**: Real-time validation
- **Creating**: Create button spinner
- **Success**: Redirect to agent detail
- **Error**: Error message

---

### Agent Detail (`/agents/:agentId`)

**Purpose**: View agent details, current task, alignment score, intervention history, and workspace.

**Layout Structure**: Agent header with status, tab navigation, main content area, right sidebar with quick stats.

**Key Components**:
- Agent header (ID, type, status badge, phase badge, actions menu)
- Tab navigation (Overview, Tasks, Interventions, Workspace, Logs)
- Overview tab: Current task, alignment score, performance metrics
- Tasks tab: Task history table
- Interventions tab: Guardian intervention history
- Workspace tab: Workspace details, commits, merge conflicts
- Logs tab: Agent execution logs
- Right sidebar: Quick stats, health indicators

**Interactive Elements**:
- Switch tabs
- View task details
- View intervention details
- View workspace commits
- View logs (with search/filter)
- Intervene agent (send message, pause, refocus)
- Assign task

**Navigation**:
- **From**: `/agents` overview, activity feed
- **To**: Task detail, workspace detail, intervention modal

**Content**:
- **Overview Tab**:
  - Current task card
  - Alignment score gauge
  - Performance metrics (tasks completed, commits, lines changed)
  - Health indicators
- **Tasks Tab**:
  - Task history table (task, status, completed at)
- **Interventions Tab**:
  - Intervention history (type, message, timestamp, result)
- **Workspace Tab**:
  - Workspace path
  - Git branch name
  - Commits list
  - Merge conflicts (if any)
- **Logs Tab**:
  - Execution logs (searchable, filterable)

**States**:
- **Loading**: Skeleton content
- **Loaded**: Show agent details
- **Active**: Show current task and alignment
- **Idle**: Show "No current task" message
- **Error**: Error message

---

### Workspace Detail (`/agents/:agentId/workspace`)

**Purpose**: View agent workspace details including commits, merge conflicts, and settings.

**Layout Structure**: Workspace header, tab navigation (Commits, Merge Conflicts, Settings), main content area.

**Key Components**:
- Workspace header (workspace path, git branch, workspace type)
- Tab navigation (Commits, Merge Conflicts, Settings)
- Commits tab: Commit list with messages, diffs, timestamps
- Merge Conflicts tab: Conflict list with resolution status
- Settings tab: Workspace configuration, retention policies
- Commit diff viewer

**Interactive Elements**:
- Switch tabs
- View commit diffs
- Resolve merge conflicts (if any)
- Configure workspace settings
- Browse workspace files (future)

**Navigation**:
- **From**: Agent detail page
- **To**: Commit detail, agent detail

**Content**:
- **Commits Tab**:
  - Commit list (SHA, message, author, timestamp, files changed)
  - Commit diff viewer
- **Merge Conflicts Tab**:
  - Conflict list (file, status, resolution method)
  - Resolution details
- **Settings Tab**:
  - Workspace path (read-only)
  - Git branch (read-only)
  - Workspace type (local/docker/kubernetes/remote)
  - Parent agent (if inherited)
  - Retention policy settings

**States**:
- **Loading**: Skeleton content
- **Loaded**: Show workspace details
- **No Conflicts**: Show "No merge conflicts" message
- **Error**: Error message

---

## Diagnostic Pages

### Diagnostic Reasoning View (`/diagnostic/ticket/:ticketId`)

**Purpose**: Unified view explaining why actions happened (task spawning, ticket linking, blocking relationships).

**Layout Structure**: Diagnostic header, tab navigation (Timeline, Graph, Details), main content area with reasoning chain.

**Key Components**:
- Diagnostic header (ticket name, "Diagnostic Reasoning" title)
- Tab navigation (Timeline, Graph, Details)
- Timeline tab: Chronological reasoning chain with events
- Graph tab: Visual graph showing relationships and reasoning
- Details tab: Detailed reasoning explanations
- Reasoning event cards (discovery, linking, spawning events)
- Evidence panels (code snippets, logs, agent decisions)

**Interactive Elements**:
- Switch tabs
- Expand/collapse reasoning events
- View evidence (code, logs)
- Navigate to related tickets/tasks
- Filter by event type
- Search reasoning chain

**Navigation**:
- **From**: Ticket detail, dependency graph, activity feed
- **To**: Related tickets, tasks, discoveries

**Content**:
- **Timeline Tab**:
  - Reasoning events in chronological order:
    - "Ticket Created - Reason: Infrastructure needed for auth system"
    - "Task Spawned - Reason: Discovery: Bug found in login flow"
    - "Ticket Linked - Reason: Dependency detected: Auth depends on Database"
  - Each event shows:
    - Timestamp
    - Event type icon
    - Reasoning description
    - Evidence (if available)
    - Related links
- **Graph Tab**:
  - Visual graph with reasoning annotations
  - Hover to see reasoning
- **Details Tab**:
  - Detailed explanations
  - Agent decision logs
  - Discovery evidence

**States**:
- **Loading**: Skeleton content
- **Loaded**: Show reasoning chain
- **Empty**: "No diagnostic data available"
- **Error**: Error message

---

## Settings Pages

### User Settings (`/settings`)

**Purpose**: Main settings landing page with navigation to all user settings sections.

**Layout Structure**: Settings header, left sidebar with settings sections, main content area (redirects to first section).

**Key Components**:
- Settings header ("Settings" title)
- Settings sidebar (Profile, API Keys, Sessions, Notifications, Appearance)
- Main content area (shows selected section or redirects to Profile)

**Interactive Elements**:
- Click settings section → Navigate to section page
- (This page may redirect directly to Profile)

**Navigation**:
- **From**: User menu, any page
- **To**: All settings sub-pages

**Content**:
- Settings navigation menu
- Brief description of each section

**States**:
- **Default**: Redirect to Profile settings

---

### Profile Settings (`/settings/profile`)

**Purpose**: Edit user profile information and preferences.

**Layout Structure**: Settings header, form sections, save button.

**Key Components**:
- Profile form (display name, email, avatar upload)
- Email preferences section
- Timezone selector
- Language selector
- Theme selector (light/dark/system)
- Save button

**Interactive Elements**:
- Edit display name
- Upload avatar
- Change email preferences
- Select timezone
- Select language
- Select theme
- Save changes

**Navigation**:
- **From**: `/settings` main page, user menu
- **To**: `/settings` (after save)

**Content**:
- Display Name input
- Email (read-only, with change email link)
- Avatar upload area
- Email Preferences: [ ] In-app [ ] Email [ ] Slack
- Timezone: [UTC ▼]
- Language: [English ▼]
- Theme: [Light] [Dark] [System]

**States**:
- **Loading**: Skeleton form
- **Editing**: Form enabled
- **Saving**: Save button spinner
- **Saved**: Success message
- **Error**: Error message

---

### API Keys (`/settings/api-keys`)

**Purpose**: List and manage API keys for programmatic access.

**Layout Structure**: Page header with "Generate Key" button, API keys list table, key detail modal.

**Key Components**:
- Page header ("API Keys" title, "Generate Key" button)
- API keys table (name, scope, created, last used, actions)
- Key detail modal (full key value, scopes, usage stats)
- Revoke confirmation modal

**Interactive Elements**:
- Click "Generate Key" button → Generate key modal/page
- Click key row → View key details
- Copy key value
- Revoke key (with confirmation)
- Filter keys (All, Active, Revoked)

**Navigation**:
- **From**: `/settings` main page
- **To**: `/settings/api-keys/new` (generate), `/settings/api-keys/:id` (key detail)

**Content**:
- API keys table shows:
  - Key Name
  - Scope: "Project: auth-system" or "Organization: acme-corp"
  - Created: "2 days ago"
  - Last Used: "1 hour ago" or "Never"
  - Actions: [View] [Revoke]
- Empty state: "No API keys yet"

**States**:
- **Loading**: Skeleton table
- **Empty**: Empty state with CTA
- **Populated**: Keys table
- **Revoking**: Show confirmation modal
- **Error**: Error message

---

### Create API Key (`/settings/api-keys/new`)

**Purpose**: Generate new API key with scoping configuration.

**Layout Structure**: Centered form layout with key generation form.

**Key Components**:
- API key creation form
- Key name input
- Scope selector (Project, Organization, Global)
- Scope target selector (project/org dropdown)
- Permissions checklist (read, write, admin)
- Expiration selector (optional)
- Generate button
- Generated key display (after generation)

**Interactive Elements**:
- Enter key name
- Select scope type
- Select scope target
- Select permissions
- Set expiration (optional)
- Generate key
- Copy key value
- Close modal/page

**Navigation**:
- **From**: `/settings/api-keys` list page
- **To**: `/settings/api-keys` (after generation, with key displayed)

**Content**:
- Form fields:
  - Key Name: [My CI/CD Key]
  - Scope: [Project ▼] [Organization] [Global]
  - Scope Target: [auth-system ▼] (if Project/Org selected)
  - Permissions: [ ] Read [ ] Write [ ] Admin
  - Expiration: [Never ▼] [30 days] [90 days] [Custom]
- Generate button: "Generate API Key"
- After generation:
  - Key value display (masked, with copy button)
  - Warning: "This key will only be shown once"
  - "Done" button

**States**:
- **Empty**: Form with defaults
- **Generating**: Generate button spinner
- **Generated**: Show key value with copy button
- **Error**: Error message

---

### API Key Detail (`/settings/api-keys/:id`)

**Purpose**: View API key details, usage statistics, and manage key.

**Layout Structure**: Key header, detail sections, usage stats, actions.

**Key Components**:
- Key header (key name, status badge)
- Key details section (scope, permissions, created, expires)
- Usage statistics section (requests, last used, rate limits)
- Actions section (regenerate, revoke buttons)
- Revoke confirmation modal

**Interactive Elements**:
- View key details
- View usage stats
- Regenerate key
- Revoke key (with confirmation)
- Copy key value (if not revoked)

**Navigation**:
- **From**: `/settings/api-keys` list page
- **To**: `/settings/api-keys` (after revoke)

**Content**:
- Key Name and Status
- Details:
  - Scope: "Project: auth-system"
  - Permissions: "Read, Write"
  - Created: "2 days ago"
  - Expires: "Never" or date
- Usage Stats:
  - Total Requests: "1,234"
  - Last Used: "1 hour ago"
  - Rate Limit: "1000/hour"
- Actions:
  - [Regenerate Key]
  - [Revoke Key]

**States**:
- **Loading**: Skeleton content
- **Loaded**: Show key details
- **Revoked**: Show "Revoked" status, disable actions
- **Error**: Error message

---

### Active Sessions (`/settings/sessions`)

**Purpose**: View and manage active user sessions.

**Layout Structure**: Page header, sessions list table, session detail modal.

**Key Components**:
- Page header ("Active Sessions" title)
- Sessions table (device, location, IP, last active, actions)
- Session detail modal (full session info)
- Revoke session confirmation

**Interactive Elements**:
- View session details
- Revoke session (with confirmation)
- Revoke all other sessions
- Filter sessions (All, Active, Expired)

**Navigation**:
- **From**: `/settings` main page
- **To**: (stays on page after actions)

**Content**:
- Sessions table shows:
  - Device: "Chrome on macOS"
  - Location: "San Francisco, CA"
  - IP Address: "192.168.1.1"
  - Last Active: "2 hours ago"
  - Current Session indicator
  - Actions: [View] [Revoke]
- Empty state: "No active sessions"

**States**:
- **Loading**: Skeleton table
- **Loaded**: Sessions table
- **Revoking**: Show confirmation
- **Error**: Error message

---

## Project Settings Pages

### Project Settings (`/projects/:id/settings`)

**Purpose**: Main project settings landing page with navigation to all settings sections.

**Layout Structure**: Settings header, left sidebar with settings tabs, main content area (shows selected tab or redirects to General).

**Key Components**:
- Settings header (project name, "Settings" title)
- Settings sidebar (General, Board, Phases, GitHub, Integrations tabs)
- Main content area (shows selected tab content)

**Interactive Elements**:
- Switch settings tabs
- (Content varies by tab)

**Navigation**:
- **From**: Project overview, project header
- **To**: All settings sub-sections

**Content**:
- Settings navigation menu
- Tab content (varies by tab)

**States**:
- **Default**: Show General tab or redirect to it

---

### Board Configuration (`/projects/:id/settings/board`)

**Purpose**: Configure Kanban board columns, ticket types, WIP limits, and board behavior.

**Layout Structure**: Settings header, form sections, save button.

**Key Components**:
- Board columns editor (add/edit/delete columns)
- Column configuration (name, phase mapping, WIP limit)
- Ticket types configuration (add/edit/delete types)
- Default ticket type selector
- Initial status selector
- Auto-transition settings
- Save button

**Interactive Elements**:
- Add/edit/delete board columns
- Configure column properties (name, phase mapping, WIP limit)
- Add/edit/delete ticket types
- Set default ticket type
- Set initial status
- Configure auto-transitions
- Save changes

**Navigation**:
- **From**: Project settings, board page
- **To**: Board page (to see changes), project settings

**Content**:
- Board Columns:
  - Column list (drag to reorder)
  - Column editor: Name, Phase Mapping dropdown, WIP Limit input
  - "+ Add Column" button
- Ticket Types:
  - Type list (component, bug, feature, etc.)
  - Type editor: Name, Color, Icon
  - "+ Add Type" button
- Defaults:
  - Default Ticket Type: [component ▼]
  - Initial Status: [backlog ▼]
- Auto-Transitions:
  - [ ] Auto-transition when phase completes
  - [ ] Auto-unblock when blocker resolves

**States**:
- **Loading**: Skeleton form
- **Editing**: Form enabled
- **Saving**: Save button spinner
- **Saved**: Success message
- **Error**: Error message

---

### Phase Configuration (`/projects/:id/settings/phases`)

**Purpose**: Manage phases (view default phases, edit phases, create custom phases).

**Layout Structure**: Settings header, default phases list, custom phases list, "Create Custom Phase" button.

**Key Components**:
- Default phases list (read-only, with "View Details" links)
- Custom phases list (editable, with edit/delete buttons)
- Phase cards (phase ID, name, description, sequence order)
- "Create Custom Phase" button
- Phase detail links

**Interactive Elements**:
- View default phase details
- Edit custom phases
- Delete custom phases
- Create custom phase
- Import phases from YAML

**Navigation**:
- **From**: Project settings
- **To**: `/projects/:id/phases/:phaseId` (phase detail), `/projects/:id/phases/new` (create)

**Content**:
- Default Phases section:
  - List of 8 default phases
  - Each shows: Phase ID, Name, Description, Sequence Order
  - [View Details] button (read-only)
- Custom Phases section:
  - List of custom phases (if any)
  - Each shows: Phase ID, Name, [Edit] [Delete] buttons
- "+ Create Custom Phase" button
- "Import from YAML" button

**States**:
- **Loading**: Skeleton lists
- **Loaded**: Show phases lists
- **Empty Custom**: Show "No custom phases" message
- **Error**: Error message

---

### GitHub Integration (`/projects/:id/settings/github`)

**Purpose**: Connect GitHub repository, configure webhooks, and manage GitHub integration settings.

**Layout Structure**: Settings header, GitHub connection status, repository selector, webhook configuration, auto-sync settings.

**Key Components**:
- GitHub connection status card (connected/disconnected)
- "Authorize GitHub" button (if not connected)
- Repository selector dropdown (if connected)
- Webhook configuration section
- Auto-sync settings (checkboxes for issues, commits, PRs, workflows)
- Connection test button
- Disconnect/reauthorize buttons

**Interactive Elements**:
- Authorize GitHub (OAuth flow)
- Select repository
- Configure webhook
- Toggle auto-sync options
- Test connection
- Disconnect GitHub
- Reauthorize GitHub

**Navigation**:
- **From**: Project settings
- **To**: GitHub OAuth authorization (external), project settings

**Content**:
- Connection Status:
  - "Connected" badge or "Not Connected" message
  - GitHub username/organization
- Repository Selection:
  - Repository dropdown: [Select Repository ▼]
  - Selected repository name and URL
- Webhook Configuration:
  - Webhook URL (read-only)
  - Webhook status: "Active" or "Inactive"
  - [Test Webhook] button
- Auto-Sync Settings:
  - [ ] Sync Issues
  - [ ] Sync Commits
  - [ ] Sync Pull Requests
  - [ ] Sync Workflow Runs
- Actions:
  - [Disconnect GitHub]
  - [Reauthorize GitHub]

**States**:
- **Not Connected**: Show "Authorize GitHub" CTA
- **Connected**: Show repository selector and settings
- **Testing**: Show test progress
- **Error**: Show error message

---

## GitHub Integration Pages

### GitHub OAuth Authorization

**Purpose**: External GitHub page for authorizing OmoiOS app permissions.

**Layout Structure**: GitHub OAuth authorization page (external, GitHub-hosted).

**Key Components**:
- GitHub authorization page
- Permission scopes list (repo, actions, workflow)
- Authorize/Cancel buttons

**Interactive Elements**:
- Review permissions
- Authorize application
- Cancel authorization

**Navigation**:
- **From**: `/login/oauth`, GitHub integration settings
- **To**: GitHub OAuth callback (back to OmoiOS)

**Content**:
- GitHub authorization page content
- Permission scopes:
  - "Read and write repository contents"
  - "Read and write GitHub Actions workflows"
  - "Read workflow files"

**States**:
- **Authorizing**: Show authorization progress
- **Authorized**: Redirect to callback
- **Cancelled**: Redirect back to OmoiOS

---

### GitHub OAuth Callback

**Purpose**: Handle OAuth callback from GitHub and complete authentication.

**Layout Structure**: Full-page loading/redirect state.

**Key Components**:
- Loading spinner
- Status message
- Error message (if failed)

**Interactive Elements**:
- Automatic processing
- Manual retry (if error)

**Navigation**:
- **From**: GitHub OAuth authorization page
- **To**: `/dashboard` (after success), `/login` (if error)

**Content**:
- Loading message: "Completing GitHub authorization..."
- Success: Redirect to dashboard
- Error: Show error message with "Try Again" button

**States**:
- **Processing**: Show spinner
- **Success**: Redirect to dashboard
- **Error**: Show error message

---

**Total Pages Documented**: 40+ pages with complete architecture specifications covering layout, components, interactions, navigation, content, and states.

