# User Flows Summary - Updated Documentation

**Created**: 2025-01-30  
**Status**: Summary Document  
**Purpose**: Summary of updated user journey, page flow, and UI documentation

---

## Overview

This document summarizes the comprehensive updates made to user journey, user flow, and page flow documentation to reflect the current codebase implementation, including authentication, multi-tenant organizations, and workspace isolation systems.

---

## Updated Documents

### 1. User Journey (`docs/user_journey.md`)

**Major Updates**:
- ✅ **Authentication Flows**: Email/password registration, OAuth, password reset, API keys, sessions
- ✅ **Organization Management**: Multi-tenant setup, resource limits, organization settings
- ✅ **Workspace Isolation**: Isolated agent workspaces, Git branching, inheritance, conflict resolution
- ✅ **Updated User Personas**: Added organization and workspace management tasks

**Key Sections Added**:
- Phase 1.1: Initial Registration & Authentication (expanded)
- Workspace Management section in Phase 3.1
- Organization management in user personas

### 2. Page Flow (`docs/page_flow.md`)

**Major Updates**:
- ✅ **New Authentication Pages**: `/register`, `/verify-email`, `/forgot-password`, `/reset-password`
- ✅ **Organization Pages**: `/organizations`, `/organizations/new`, `/organizations/:id/settings`
- ✅ **Workspace Pages**: `/agents/:agentId/workspace`, workspace detail views
- ✅ **API Key Pages**: `/settings/api-keys`, key generation and management

**New Flow Sections**:
- Flow 6: Organization Management & Multi-Tenancy
- Flow 7: Workspace Management & Isolation
- Flow 8: API Key Management

**Updated Navigation**:
- Complete route structure with all new pages
- Updated key user actions to include new flows

### 3. Frontend Design (`docs/design/frontend/project_management_dashboard.md`)

**Updates**:
- ✅ Added references to updated user journey and page flow documents
- ✅ Updated authentication section to reflect implemented features
- ✅ Added workspace isolation system documentation

---

## Key Features Documented

### Authentication System
- Email/password registration with verification
- OAuth login (GitHub/GitLab)
- Password reset flow
- API key generation with scoping
- Session management
- Multi-factor authentication (future)

### Multi-Tenant Organizations
- Organization creation with unique slugs
- Resource limits (max concurrent agents, max runtime hours)
- Organization settings (JSONB)
- Billing email configuration
- Member management (future)
- RBAC roles and permissions (future)

### Workspace Isolation System
- Automatic workspace creation per agent
- Git-backed workspaces with branch per agent
- Workspace inheritance from parent agents
- Automatic merge conflict resolution (newest file wins)
- Workspace checkpoint commits for validation
- Workspace retention and cleanup policies
- Workspace type support (local, docker, kubernetes, remote)

---

## All Views & Pages Required

### Core Project Views
- **Kanban Board** (`/board/:projectId`) - Ticket management with drag-and-drop
- **Dependency Graph** (`/graph/:projectId`) - Visual dependency visualization
- **Spec Workspace** (`/projects/:projectId/specs/:specId`) - Multi-tab spec editor
- **Statistics Dashboard** (`/projects/:projectId/stats`) - Analytics and metrics
- **Activity Timeline** (`/projects/:projectId/activity`) - Chronological event feed

### Ticket Views
- **Ticket Detail** (`/board/:projectId/:ticketId`) - Full ticket view with tabs:
  - Details tab: Ticket info, description, status, phase, priority
  - Tasks tab: Related tasks list
  - Commits tab: Commit history linked to ticket
  - Graph tab: Ticket dependency graph
  - Comments tab: Discussion and collaboration
  - Audit tab: Complete audit trail

### Graph Views
- **Project Graph** (`/graph/:projectId`) - Full project dependency graph
- **Ticket Graph** (`/graph/:projectId/:ticketId`) - Focused ticket dependencies
- **Graph Controls**: Zoom, pan, filter by phase/status, show/hide nodes

### Spec Workspace Views
- **Specs List** (`/projects/:projectId/specs`) - All specs for project
- **Spec Viewer** (`/projects/:projectId/specs/:specId`) - Multi-tab workspace:
  - Requirements tab: EARS-style requirements with structured blocks
  - Design tab: Architecture diagrams, sequence diagrams, data models
  - Tasks tab: Task breakdown with dependencies
  - Execution tab: Progress dashboard, running tasks, PRs

### Statistics Views
- **Overview Tab**: High-level metrics (tickets, tasks, agents, completion rate)
- **Tickets Tab**: Tickets by phase, completion rates by type
- **Agents Tab**: Agent performance, alignment scores, interventions
- **Code Tab**: Code changes, test coverage, commits
- **Cost Tab**: LLM costs, resource usage

### Phase Management Views
- **Phases List** (`/projects/:projectId/phases`) - View all phases with order, transitions, status
- **Phase Editor** (`/projects/:projectId/phases/:phaseId`) - Edit phase configuration:
  - Basic info (name, description, sequence order, terminal status)
  - Allowed transitions
  - Done definitions (completion criteria)
  - Expected outputs (artifact patterns)
  - Phase prompt (agent instructions)
  - Next steps guide

### Task Phase Management Views
- **Tasks by Phase** (`/projects/:projectId/tasks/phases`) - Tasks organized by phase:
  - Expandable phase sections
  - Task cards with status, agent, progress
  - Move task to phase action
  - Bulk phase transitions
  - Filter by phase/status
- **Move Task Phase** (`/tasks/:taskId/move-phase`) - Transition task to new phase:
  - Show allowed transitions
  - Reason input
  - Validation of transition rules

### Phase Gate Approval Views
- **Phase Gates** (`/projects/:projectId/phase-gates`) - Manage phase transitions:
  - Pending approvals list
  - Gate requirements check (done definitions, expected outputs)
  - Validation status (passed/failed)
  - Approve/reject transitions
  - Recent transition history
  - Auto-approved transitions log

### Activity Timeline Views
- **Chronological Feed**: All events in timeline order
- **Filters**: By event type, agent, date range
- **Event Types**: Ticket created/completed, discoveries, memory operations, interventions, commits, test results

### Comments & Collaboration Views
- **Comments Tab** (`/board/:projectId/:ticketId` - Comments tab) - Comment thread display:
  - Comment list with agent/user attribution
  - Rich text comment editor
  - @mention autocomplete for agents/users
  - File attachment support
  - Comment types (general, status_change, resolution)
  - Real-time updates via WebSocket (COMMENT_ADDED event)
  - Reply functionality
  - Edit/delete comments

### Ticket Search Views
- **Search Modal** - Global ticket search:
  - Search bar with query input
  - Search type selector (Hybrid/Semantic/Keyword)
  - Filters (status, type, phase, priority)
  - Include comments option
  - Search results display with match indicators
  - Click to view ticket

### Ticket Creation Views
- **Create Ticket Modal** (`/board/:projectId` - Create button) - Ticket creation form:
  - Basic info (title, description, type, priority, phase)
  - Blocking relationships selector
  - Related items (specs, tasks)
  - Tags input
  - Real-time appearance on board via WebSocket

### Status Transition Views
- **Transition Modal** (`/board/:projectId/:ticketId` - Move Ticket) - Status change:
  - Current status display
  - New status selector (shows valid transitions)
  - Reason input field
  - Add comment option
  - Real-time board update via WebSocket

### Blocking Management Views
- **Blocking Tab** (`/board/:projectId/:ticketId` - Blocking tab) - Dependency management:
  - Blocked by list (tickets blocking this one)
  - Blocks list (tickets blocked by this one)
  - Add/remove blocker UI
  - Dependency graph visualization
  - Auto-unblocking indicators
  - Real-time updates when blockers resolve

### Board Configuration Views
- **Board Settings** (`/projects/:projectId/settings` - Board tab) - Board customization:
  - Column editor (name, color, WIP limits, phase mapping)
  - Column reordering (drag-and-drop)
  - Ticket types configuration
  - Default settings (default type, initial status)
  - Real-time board updates when saved

### GitHub Integration Views
- **GitHub OAuth Authorization** (`/login/oauth/github`) - GitHub OAuth flow:
  - Redirect to GitHub authorization page
  - Permission scopes request (repo, actions, workflow)
  - User grants permissions
  - OAuth callback handler
  - Token storage and account creation
- **GitHub Settings** (`/projects/:projectId/settings/github`) - Repository connection:
  - Authorization status check
  - Repository search and selection
  - Webhook configuration
  - Auto-sync options (issues, commits, PRs, workflows)
  - Connection testing
  - Disconnect/reauthorize options

### Phase Management Views (Phasor System)
- **Phase Overview Dashboard** (`/projects/:projectId/phases`) - Phase orchestration:
  - Phase cards showing task counts (Total, Done, Active)
  - Active agents per phase
  - Discovery indicators (new branches spawned)
  - Phase status (active, completed, idle)
  - "View Tasks" button per phase
  - Real-time updates via WebSocket (phase status changes)
- **Phase Detail View** (`/projects/:projectId/phases/:phaseId`) - Phase configuration:
  - Phase identity (id, name, description, sequence_order)
  - Done definitions (concrete completion criteria)
  - Phase prompt (system instructions for agents - loaded automatically)
  - Expected outputs (required artifacts with patterns)
  - Next steps guide (what happens after phase completes)
  - Allowed transitions (structured flow - normal progression)
  - Configuration (timeouts, retry limits, WIP limits)
  - Free spawning note (discovery-based branching bypasses restrictions)
- **Phase Configuration** (`/projects/:projectId/settings/phases`) - Manage phases:
  - View all default phases (8 phases)
  - Edit phase properties (done definitions, prompts, transitions)
  - Create custom phases (for specialized workflows)
  - Delete custom phases (default phases cannot be deleted)
  - Import phases from YAML configuration
- **Workflow Graph** (`/projects/:projectId/graph`) - Phasor visualization:
  - Phase columns (Phase 1, Phase 2, Phase 3)
  - Task nodes with phase badges
  - Discovery edges (purple) showing branching
  - Normal flow edges (green) showing progression
  - Click node → Task details with phase context
  - Click edge → Discovery reasoning (why branch spawned)
  - Hover → Highlight reasoning chain
  - Filter by phase, discovery type, agent
- **Discovery Timeline** (`/projects/:projectId/activity?filter=discoveries`) - Discovery events:
  - Chronological discovery events
  - Source task and spawned tasks (with phase context)
  - Discovery type (bug, optimization, clarification, etc.)
  - Discovery description (reasoning captured)
  - Branch visualization (shows workflow adaptation)
- **Task Phase Management** (`/projects/:projectId/tasks/phases`) - Phase-based task organization:
  - Tasks organized by phase (expandable sections)
  - Phase-specific task lists with filters
  - Move task to phase (with transition validation)
  - Bulk phase transitions
  - Phase assignment indicators
- **Phase Gate Approvals** (`/projects/:projectId/phase-gates`) - Gate management:
  - Pending gate approvals (phase transition requests)
  - Gate criteria validation status
  - Artifact review (code changes, test coverage, etc.)
  - Approve/reject transitions
  - Auto-progression when criteria met
- **Phase Metrics Dashboard** (`/projects/:projectId/stats?tab=phases`) - Phase performance:
  - Phase performance overview (tasks, completion rates)
  - Phase efficiency metrics (average time, success rate)
  - Phase bottlenecks (queue depth, WIP violations)
  - Phase cost breakdown (LLM costs per phase)
  - Discovery activity by phase (discoveries, branches spawned)

## UI Pages Required

### Authentication Pages
- `/register` - Email registration form
- `/login` - Email login form  
- `/login/oauth` - OAuth redirect handler
- `/verify-email` - Email verification page
- `/forgot-password` - Password reset request
- `/reset-password` - Password reset confirmation

### Organization Pages
- `/organizations` - Organization list
- `/organizations/new` - Create organization
- `/organizations/:id` - Organization detail
- `/organizations/:id/settings` - Organization settings (tabs: General, Resources, Members, Billing)

### Workspace Pages
- `/agents/:agentId/workspace` - Workspace detail view
- `/workspaces` - Workspace list (optional)
- Workspace tabs: Commits, Merge Conflicts, Settings

### Settings Pages
- `/settings/api-keys` - API key list
- `/settings/api-keys/new` - Generate new API key
- `/settings/api-keys/:id` - API key details
- `/settings/profile` - User profile
- `/settings/sessions` - Active sessions

---

## Navigation Structure

```
/ (Landing)
├── /register
├── /login
├── /login/oauth
├── /verify-email
├── /forgot-password
├── /reset-password
├── /onboarding
└── /dashboard
    ├── /organizations
    │   ├── /organizations/new
    │   └── /organizations/:id
    │       ├── /organizations/:id/settings
    │       └── /organizations/:id/members
    ├── /projects
    │   ├── /projects/new
    │   ├── /projects/:id
    │   ├── /projects/:id/explore
    │   ├── /projects/:id/specs
    │   │   └── /projects/:id/specs/:specId
    │   ├── /projects/:id/stats
    │   ├── /projects/:id/activity
    │   ├── /projects/:id/phases
    │   │   └── /projects/:id/phases/:phaseId
    │   ├── /projects/:id/tasks/phases
    │   ├── /projects/:id/phase-gates
    │   └── /projects/:id/settings
    │       └── /projects/:id/settings/github
    ├── /board/:projectId
    ├── /diagnostic/:entityType/:entityId
    │   ├── /diagnostic/ticket/:ticketId
    │   ├── /diagnostic/task/:taskId
    │   └── /diagnostic/agent/:agentId
    │   └── /board/:projectId/:ticketId
    ├── /graph/:projectId
    │   └── /graph/:projectId/:ticketId
    ├── /agents
    │   ├── /agents/spawn
    │   ├── /agents/:agentId
    │   └── /agents/:agentId/workspace
    ├── /workspaces
    ├── /commits/:commitSha
    └── /settings
        ├── /settings/profile
        ├── /settings/api-keys
        ├── /settings/sessions
        └── /settings/preferences
```

---

## User Flows

### Registration Flow
1. Landing → Register/Login → Email Verification → Onboarding → Dashboard

### Organization Setup Flow
1. Onboarding → Create Organization → Configure Limits → Dashboard

### Kanban Board Flow
1. Project → Board → View Tickets → Click Ticket → Ticket Detail → (Details/Tasks/Commits/Graph/Comments/Audit)

### Dependency Graph Flow
1. Project → Graph → View Dependencies → Click Node → Ticket Graph View → View Ticket Details

### Spec Workspace Flow
1. Project → Specs List → View Spec → (Requirements → Design → Tasks → Execution) → Approve → Execution Starts

### Statistics Flow
1. Project → Stats → View Analytics → Switch Tabs (Overview/Tickets/Agents/Code/Cost) → Drill Down

### Activity Timeline Flow
1. Project → Activity → View Events → Filter by Type/Agent → Click Event → View Details

### Phase Management Flow
1. Project → Phases → View Phases → Edit Phase → Configure Done Definitions → Set Expected Outputs → Save

### Task Phase Management Flow
1. Project → Tasks by Phase → View Tasks → Select Task → Move to Phase → Select Target → Approve Transition

### Phase Gate Approval Flow
1. Project → Phase Gates → View Pending → Review Requirements → Check Validation → Approve/Reject Transition

### Comments & Collaboration Flow
1. Ticket Detail → Comments Tab → Add Comment → Mention Agents → Attach Files → Post → Real-time Updates
2. Agent adds comment via MCP tool → WebSocket broadcast → All users see comment instantly

### Ticket Search Flow
1. Board → Search Modal → Enter Query → Select Search Type (Hybrid/Semantic/Keyword) → View Results → Click Ticket
2. Agent searches before creating → Finds duplicates → References existing or creates new

### Ticket Creation Flow
1. Board → Create Ticket Modal → Fill Form → Set Blocking Relationships → Select Type/Priority → Create → Real-time Appears
2. Agent creates via MCP tool → WebSocket: TICKET_CREATED → Board updates instantly

### Status Transition Flow
1. Ticket Detail → Move Ticket → Select New Status → Add Reason/Comment → Confirm → Real-time Board Update
2. Agent transitions via MCP tool → WebSocket: TICKET_UPDATED → Board reflects change immediately

### Blocking Management Flow
1. Ticket Detail → Blocking Tab → Add/Remove Blockers → View Dependency Graph → Auto-unblock on Resolve
2. Blocker ticket resolves → System detects → Auto-unblocks dependent tickets → WebSocket: TICKET_UNBLOCKED

### Board Configuration Flow
1. Project Settings → Board Tab → Edit Columns → Configure Ticket Types → Set WIP Limits → Save → Real-time Updates

### GitHub OAuth Flow
1. Login → Click "Login with GitHub" → Redirect to GitHub → Grant Permissions (repo, actions, workflow) → Authorize → Callback → Dashboard

### GitHub Integration Flow
1. Project Settings → GitHub Tab → Check Authorization → Authorize GitHub (if needed) → Select Repository → Configure Webhook → Connect → Test Connection

### Diagnostic Reasoning Flow
1. Ticket/Task Detail → Click "View Reasoning Chain" → Diagnostic View → See Discoveries → View Blocking Relationships → View Task Links → View Agent Memory → Understand WHY actions happened
2. Dependency Graph → Click Edge → Diagnostic View → See Relationship Reasoning → View Evidence → View Agent Decision
3. Kanban Board → Click Task → "Why was this created?" → Diagnostic View → See Discovery → View Source Task → View Spawned Tasks

### Workspace Management Flow
1. Agents → Agent Detail → Workspace Detail → View Commits → View Merge Conflicts

### API Access Flow
1. Settings → API Keys → Generate Key → Configure Scope → Use in CI/CD

### Phase Overview Flow
1. Project → Phases Tab → View Phase Cards → See Task Counts → View Active Agents → Click "View Tasks" → See Phase-Specific Tasks
2. Phase Card → Click "View Discoveries" → See Discovery Events → View Branch Visualization

### Phase Configuration Flow
1. Project Settings → Phases Tab → View Default Phases → Click "Edit" → Configure Done Definitions → Set Phase Prompt → Set Allowed Transitions → Save
2. Project Settings → Phases Tab → Click "Create Custom Phase" → Define Phase Properties → Set Completion Criteria → Configure Transitions → Save

### Phase Gate Approval Flow
1. Agent Completes Phase → System Checks Done Definitions → Validates Artifacts → Requests Approval → User Reviews → Approve/Reject → Ticket Transitions
2. Phase Gates Page → View Pending Approvals → Review Gate Criteria → Review Artifacts → Approve/Reject → Auto-Progress Ticket

### Task Phase Management Flow
1. Project → Tasks → Filter by Phase → View Phase-Specific Tasks → Click "Move to Phase" → Select Target Phase → Add Reason → Validate Transition → Move
2. Tasks by Phase → Select Multiple Tasks → Bulk Actions → Move Selected to Phase → Validate Transitions → Bulk Move

### Phase Metrics Flow
1. Project → Statistics → Phases Tab → View Phase Performance → Compare Phase Efficiency → Identify Bottlenecks → View Phase Costs → View Discovery Activity

### Discovery-Based Branching Flow
1. Agent Working in Phase 3 → Discovers Optimization → Calls DiscoveryService → Spawns Phase 1 Investigation Task → Original Work Continues → New Branch Emerges
2. Workflow Graph → View Discovery Edges → Click Edge → See Discovery Reasoning → View Spawned Tasks → Understand Adaptive Workflow

---

## Related Documents

- [User Journey](./user_journey.md) - Complete user journey with all flows
- [Page Flow](./page_flow.md) - Detailed page-by-page navigation
- [Frontend Design](./design/frontend/project_management_dashboard.md) - UI/UX specifications
- [Product Vision](./product_vision.md) - Product concept

---

## Next Steps for UI Implementation

1. **Authentication UI**: Implement registration, login, and password reset pages
2. **Organization UI**: Build organization list, creation, and settings pages
3. **Workspace UI**: Create workspace detail views with commits and merge conflicts
4. **API Key UI**: Build API key management interface
5. **Integration**: Connect all pages to existing API endpoints
6. **Testing**: Test all flows end-to-end

---

## Notes

- All authentication endpoints are implemented (`omoi_os/api/routes/auth.py`)
- Organization models are implemented (`omoi_os/models/organization.py`)
- Workspace isolation system is implemented (`omoi_os/models/workspace.py`, `omoi_os/services/workspace_manager.py`)
- API key management is implemented (`omoi_os/models/auth.py`)

The documentation now accurately reflects the current codebase state and can be used to guide UI implementation.

