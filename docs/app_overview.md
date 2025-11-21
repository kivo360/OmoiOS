# OmoiOS App Overview

## 1. App Type & Purpose

**What kind of app is this?**
OmoiOS is a spec-driven autonomous engineering platform that orchestrates multiple AI agents through adaptive, phase-based workflows to build software from requirements to deployment.

**What core problem(s) does it solve?**
- Scaling software development without proportional headcount growth
- Coordinating multiple AI agents effectively without micromanagement
- Enabling workflows that adapt to reality rather than breaking when plans don't match execution
- Reducing cognitive load on engineers who don't want to think about every single step

**Who is the target audience?**
- **Engineering Managers**: Monitor multiple projects, approve phase transitions, review PRs, manage organizations
- **Senior IC Engineers**: Create feature requests, review code changes, provide technical guidance
- **CTOs/Technical Leads**: Set up projects, configure workflows, monitor system health, manage organizations

---

## 2. Core Features

### Feature 1: Spec-Driven Workflow Orchestration
**Description**: Users describe what they want built in structured specs (Requirements → Design → Tasks → Execution), and the system automatically plans, executes, and monitors the work autonomously.

**Why it matters**: Engineers provide strategic direction instead of step-by-step instructions, enabling autonomous execution while maintaining control.

### Feature 2: Adaptive Phase-Based Workflows
**Description**: Workflows organized into phases (Requirements, Implementation, Testing, Deployment) with agents specialized per phase. Agents can spawn tasks in any phase via discovery-based branching, enabling workflows that adapt when bugs are found, optimizations discovered, or requirements clarified.

**Why it matters**: Workflows adapt to reality—agents discover issues and spawn fixes automatically without breaking the main flow, creating self-building workflows that evolve based on what agents find.

### Feature 3: Real-Time Kanban Board & Ticket Tracking
**Description**: Visual Kanban board showing tickets moving through workflow phases, with blocking relationships, real-time updates via WebSocket, and automatic unblocking when dependencies resolve.

**Why it matters**: Provides real-time visibility into what agents are working on, which components are blocked, and how work progresses—without manual status updates.

### Feature 4: Multi-Agent Coordination & Memory System
**Description**: Multiple agents work in parallel on different components, coordinated through tickets and phases. A collective memory system captures discoveries, fixes, and decisions so agents learn from each other's work.

**Why it matters**: Agents avoid repeating mistakes, share solutions automatically, and build on each other's work—creating collective intelligence that improves over time.

### Feature 5: Phase Gate Approvals & Quality Validation
**Description**: System validates phase completion criteria (done definitions, expected outputs, artifacts) before allowing transitions, with optional human approval gates for strategic oversight.

**Why it matters**: Ensures quality at each phase while giving users control at critical decision points—autonomous execution with human oversight where it matters most.

### Feature 6: Discovery-Based Branching & Diagnostic Reasoning
**Description**: Agents discover bugs, optimizations, or missing requirements during work and automatically spawn investigation/fix tasks in appropriate phases. Full diagnostic reasoning explains why tasks were created, tickets linked, or workflows branched.

**Why it matters**: Workflows adapt automatically to discoveries, and users understand why decisions were made—transparency and adaptability without manual intervention.

### Feature 7: Workspace Isolation & Git Integration
**Description**: Each agent gets an isolated workspace with its own Git branch, enabling parallel work without conflicts. Automatic merge resolution, workspace inheritance, and commit tracking link code changes to tickets.

**Why it matters**: Multiple agents can work simultaneously without conflicts, and all code changes are tracked and linked to work items—enabling true parallel development.

---

## 3. User Flow

1. **Onboarding & Registration**: User registers via email/password or OAuth (GitHub), verifies email, completes onboarding tour
2. **Organization Setup**: User creates organization, configures resource limits (max agents, runtime hours), sets up multi-tenant workspace
3. **Project Creation**: User creates new project, optionally uses AI-assisted exploration to generate initial requirements and design
4. **Feature Request**: User creates feature spec or ticket describing what to build, system spawns Phase 1 agent (Requirements Analysis)
5. **Autonomous Planning**: Phase 1 agent analyzes requirements, identifies components, creates tickets with blocking relationships, spawns Phase 2 tasks
6. **Autonomous Execution**: Phase 2 agents work in parallel on unblocked tickets, move tickets through Kanban board, leave progress comments, spawn Phase 3 validation tasks
7. **Real-Time Monitoring**: User monitors progress via Kanban board, dependency graph, activity timeline, and agent status dashboard—all updating in real time via WebSocket
8. **Phase Gate Approval**: When phase completes, system validates criteria and requests user approval (if enabled), user reviews artifacts and approves/rejects transition
9. **Quality Validation**: Phase 3 agents test components, spawn fixes if needed, resolve tickets when tests pass—automatically unblocking dependent work
10. **PR Review & Merge**: Agents create PRs automatically, user reviews code changes, approves merges, tickets move to completion
11. **Ongoing Optimization**: User monitors statistics dashboard, views phase performance metrics, optimizes workflows based on bottlenecks and costs
12. **Strategic Oversight**: User intervenes only when needed (pause workflows, add constraints, prioritize work) while system handles execution autonomously

---

## 4. Page / Screen List

### Authentication Pages
- **Landing Page** (`/`): Initial entry point with login/register options
- **Register** (`/register`): Email/password registration form
- **Login** (`/login`): Email/password login form
- **Login OAuth** (`/login/oauth`): OAuth redirect handler for GitHub/GitLab
- **Verify Email** (`/verify-email`): Email verification confirmation page
- **Forgot Password** (`/forgot-password`): Password reset request form
- **Reset Password** (`/reset-password`): Password reset confirmation form

### Organization Pages
- **Organizations List** (`/organizations`): View all organizations user belongs to
- **Create Organization** (`/organizations/new`): Create new organization with resource limits
- **Organization Detail** (`/organizations/:id`): View organization overview and members
- **Organization Settings** (`/organizations/:id/settings`): Configure organization settings, resource limits, billing (tabs: General, Resources, Members, Billing)

### Dashboard & Project Pages
- **Dashboard** (`/dashboard`): Overview of all projects, active specs, quick actions, recent activity feed
- **Projects List** (`/projects`): View all projects user has access to
- **Create Project** (`/projects/new`): Create new project with initial configuration
- **Project Overview** (`/projects/:id`): Main project dashboard with overview metrics and quick navigation
- **AI-Assisted Exploration** (`/projects/:id/explore`): AI generates requirements and design from project description

### Spec Workspace Pages
- **Specs List** (`/projects/:id/specs`): View all specs for project
- **Spec Workspace** (`/projects/:id/specs/:specId`): Multi-tab workspace for viewing/editing spec (Requirements, Design, Tasks, Execution tabs)

### Kanban Board Pages
- **Kanban Board** (`/board/:projectId`): Visual Kanban board with drag-and-drop ticket management
- **Ticket Detail** (`/board/:projectId/:ticketId`): Full ticket details with tabs (Details, Comments, Tasks, Commits, Blocking, Reasoning)

### Graph & Visualization Pages
- **Dependency Graph** (`/graph/:projectId`): Full project dependency graph visualization
- **Ticket Graph** (`/graph/:projectId/:ticketId`): Focused ticket dependency visualization

### Phase Management Pages
- **Phase Overview** (`/projects/:projectId/phases`): Dashboard showing all phases with task counts and active agents
- **Phase Detail** (`/projects/:projectId/phases/:phaseId`): View and edit phase configuration (done definitions, phase prompt, transitions)
- **Create Custom Phase** (`/projects/:projectId/phases/new`): Create new custom phase for specialized workflows
- **Task Phase Management** (`/projects/:projectId/tasks/phases`): Organize tasks by phase, move tasks between phases
- **Phase Gate Approvals** (`/projects/:projectId/phase-gates`): Review and approve phase transitions with artifact validation

### Statistics & Monitoring Pages
- **Statistics Dashboard** (`/projects/:projectId/stats`): Analytics dashboard with tabs (Overview, Tickets, Agents, Code, Cost, Phases)
- **Activity Timeline** (`/projects/:projectId/activity`): Chronological feed of all events (filterable by discovery type, agent, date)

### Agent Management Pages
- **Agents Overview** (`/agents`): View all agents with status, phase assignment, performance metrics
- **Spawn Agent** (`/agents/spawn`): Create new agent with phase assignment and capabilities
- **Agent Detail** (`/agents/:agentId`): View agent details, current task, alignment score, intervention history
- **Workspace Detail** (`/agents/:agentId/workspace`): View agent workspace with tabs (Commits, Merge Conflicts, Settings)

### Diagnostic Pages
- **Diagnostic Reasoning View** (`/diagnostic/ticket/:ticketId`): Unified view explaining why actions happened (discoveries, ticket linking, task spawning)

### Settings Pages
- **User Settings** (`/settings`): Main settings page
- **Profile Settings** (`/settings/profile`): Edit user profile, display name, email preferences
- **API Keys** (`/settings/api-keys`): List and manage API keys for programmatic access
- **Create API Key** (`/settings/api-keys/new`): Generate new API key with scoping
- **API Key Detail** (`/settings/api-keys/:id`): View API key details, usage, revoke
- **Active Sessions** (`/settings/sessions`): View and manage active user sessions

### Project Settings Pages
- **Project Settings** (`/projects/:id/settings`): Configure project settings (tabs: General, Board, Phases, GitHub, Integrations)
- **Board Configuration** (`/projects/:id/settings/board`): Configure Kanban board columns, ticket types, WIP limits
- **Phase Configuration** (`/projects/:id/settings/phases`): Manage phases (view default, edit, create custom)
- **GitHub Integration** (`/projects/:id/settings/github`): Connect GitHub repository, configure webhooks, manage permissions

### GitHub Integration Pages
- **GitHub OAuth Authorization**: GitHub authorization page for granting permissions
- **GitHub OAuth Callback**: Callback handler after GitHub authorization

---

**Total Pages**: ~40 distinct pages/screens covering authentication, organization management, project orchestration, agent coordination, and strategic oversight.

