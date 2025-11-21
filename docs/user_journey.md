# OmoiOS User Journey & Flow

**Created**: 2025-01-30  
**Status**: User Journey Documentation  
**Purpose**: Complete user flow from onboarding to feature completion

---

## Overview

OmoiOS follows a **spec-driven autonomous engineering workflow** where users describe what they want built, and the system automatically plans, executes, and monitors the work. Users provide strategic oversight at approval gates rather than micromanaging every step.

---

## Complete User Journey

### Phase 1: Onboarding & First Project Setup

#### 1.1 Initial Login & Authentication
```
1. User visits OmoiOS dashboard
   ↓
2. OAuth login (GitHub/GitLab)
   ↓
3. First-time user sees onboarding tour
   ↓
4. Dashboard shows empty state: "Create your first project"
```

**Key Actions:**
- Connect GitHub/GitLab account
- Set up organization/workspace
- Configure notification preferences

#### 1.2 Project Creation Options

**Option A: AI-Assisted Project Exploration** (Recommended for new projects)
```
1. User clicks "Explore New Project"
   ↓
2. Enters initial idea: "I want to create an authentication system with plugins"
   ↓
3. AI asks clarifying questions:
   - "What authentication methods should be supported?"
   - "Should this support multi-tenant scenarios?"
   - "What technology stack do you prefer?"
   ↓
4. User answers questions in chat interface
   ↓
5. AI generates Requirements Document (EARS-style format)
   ↓
6. User reviews requirements → Approves/Rejects/Provides feedback
   ↓
7. AI refines requirements based on feedback
   ↓
8. User approves final requirements
   ↓
9. AI generates Design Document:
   - Architecture diagrams
   - Component design
   - Security design
   - Implementation plan
   ↓
10. User reviews design → Approves/Rejects/Provides feedback
   ↓
11. AI refines design
   ↓
12. User approves final design
   ↓
13. User clicks "Initialize Project"
   ↓
14. System creates:
    - Project record
    - Initial tickets (based on design phases)
    - Tasks for each ticket
    - Spec workspace (Requirements | Design | Tasks | Execution tabs)
   ↓
15. Project ready for development!
```

**Option B: Quick Start** (For existing projects)
```
1. User clicks "Create Project"
   ↓
2. Enters project name and description
   ↓
3. Connects GitHub repository
   ↓
4. System analyzes codebase
   ↓
5. User creates first ticket manually or via GitHub issue sync
   ↓
6. Project ready!
```

---

### Phase 2: Feature Request & Planning

#### 2.1 Creating a Feature Request

**Method 1: Natural Language Feature Request**
```
1. User navigates to project dashboard
   ↓
2. Clicks "New Feature" or uses Command Palette (Cmd+K)
   ↓
3. Types: "Add payment processing with Stripe"
   ↓
4. System analyzes:
   - Current codebase structure
   - Existing dependencies
   - Similar features in codebase
   ↓
5. System generates spec-driven workflow:
   - Requirements Phase (EARS-style requirements)
   - Design Phase (architecture, sequence diagrams)
   - Planning Phase (task breakdown with dependencies)
   - Execution Phase (autonomous code generation)
   ↓
6. Spec appears in Spec Workspace (multi-tab view)
```

**Method 2: GitHub Issue Integration**
```
1. GitHub issue created
   ↓
2. Webhook → OmoiOS receives issue
   ↓
3. System creates ticket automatically
   ↓
4. Ticket appears in Kanban board (Backlog column)
   ↓
5. User can trigger spec generation from ticket
```

#### 2.2 Spec Review & Approval

```
1. User navigates to Spec Workspace
   ↓
2. Views multi-tab interface:
   - Requirements tab: EARS-style requirements with WHEN/THE SYSTEM SHALL patterns
   - Design tab: Architecture diagrams, sequence diagrams, data models
   - Tasks tab: Discrete tasks with dependencies
   - Execution tab: (empty until execution starts)
   ↓
3. User reviews each section:
   - Can edit requirements/design/tasks
   - Can add constraints or clarifications
   - Can approve/reject sections
   ↓
4. User clicks "Approve Plan" when satisfied
   ↓
5. System transitions to Execution Phase
   ↓
6. Tickets move from Backlog → Initial phase in Kanban board
```

**Spec Workspace Features:**
- **Structured blocks** (Notion-style) for requirements/design content
- **Spec switcher** to switch between multiple specs within each tab
- **Collapsible sidebar** for spec navigation (Obsidian-style)
- **Export options**: Markdown, YAML, PDF
- **Version history**: Track spec changes over time

---

### Phase 3: Autonomous Execution & Monitoring

#### 3.1 Agent Assignment & Execution

```
1. System automatically assigns tasks to available agents
   ↓
2. Agents pick up tasks from queue (priority-based)
   ↓
3. Agents execute in isolated workspaces:
   - Clone repository
   - Analyze requirements
   - Write code
   - Run tests
   - Self-correct on failures
   ↓
4. Real-time updates via WebSocket:
   - Task status changes
   - Agent heartbeats
   - Code commits
   - Test results
   ↓
5. Dashboard updates in real-time:
   - Kanban board: Tickets move through phases
   - Dependency graph: Tasks complete, dependencies resolve
   - Activity timeline: Shows all agent actions
```

#### 3.2 Monitoring Views

**Kanban Board View:**
```
Columns: INITIAL → IMPLEMENTATION → INTEGRATION → REFACTORING → DONE

Features:
- Drag-and-drop ticket prioritization
- WIP limit indicators
- Commit indicators (+X -Y) on ticket cards
- Phase badges and priority indicators
- Real-time updates as agents work
```

**Dependency Graph View:**
```
Visualization:
- Nodes: Tasks/Tickets
- Edges: Dependencies
- Colors: Status (pending, in-progress, completed, blocked)
- Discovery nodes: Show workflow branching (bugs found, optimizations discovered)
- Animated updates: Nodes turn green as dependencies resolve

Features:
- Zoom/pan controls
- Filter by phase/status
- Click node to see details
- See blocking relationships
```

**Activity Timeline/Feed:**
```
Chronological feed showing:
- Specs/tasks/tickets created
- Discovery events (why workflows branch)
- Phase transitions
- Agent interventions (Guardian steering)
- Approvals/rejections
- Code commits
- Test results

Features:
- Filter by event type
- Search timeline
- Link to related tickets/tasks
- Show agent reasoning summaries
```

**Agent Status Monitoring:**
```
Live agent dashboard:
- Agent status: active, idle, stuck, failed
- Heartbeat indicators (30s intervals)
- Guardian intervention alerts
- Agent performance metrics
- Tasks currently working on
```

#### 3.3 Discovery & Workflow Branching

```
Agent working on Task A discovers bug:
   ↓
1. Agent calls DiscoveryService.record_discovery_and_branch()
   ↓
2. System creates:
   - TaskDiscovery record (type: "bug")
   - New Task B: "Fix bug"
   - Links Task B as child of Task A
   ↓
3. WebSocket events:
   - DISCOVERY_MADE
   - TASK_CREATED
   ↓
4. Dashboard updates:
   - Dependency graph shows new branch
   - Activity timeline shows discovery event
   - Kanban board shows new task
   ↓
5. Workflow branches:
   Original path continues
   New branch handles bug fix
   Both paths execute in parallel
```

**Discovery Types:**
- Bug found
- Optimization opportunity
- Missing requirement
- Security issue
- Performance issue
- Technical debt
- Integration issue

#### 3.4 Guardian Interventions

```
Guardian monitors agent trajectories every 60 seconds:
   ↓
1. Guardian analyzes agent alignment with goals
   ↓
2. Detects drift (alignment_score drops to 45%)
   ↓
3. Guardian generates SteeringIntervention
   ↓
4. ConversationInterventionService sends message to active conversation
   ↓
5. Agent receives intervention: "[GUARDIAN INTERVENTION] Please focus on core authentication flow first"
   ↓
6. Agent processes intervention asynchronously (non-blocking)
   ↓
7. Agent adjusts course based on intervention
   ↓
8. WebSocket: STEERING_ISSUED → Dashboard shows intervention
```

**Intervention Types:**
- Prioritize: Focus on specific area
- Stop: Halt current work
- Refocus: Change direction
- Add constraint: Add new requirement
- Inject tool call: Force specific action

---

### Phase 4: Approval Gates & Phase Transitions

#### 4.1 Phase Gate Approvals

```
Agent completes all tasks in PHASE_IMPLEMENTATION:
   ↓
1. System checks done_definitions:
   - Component code files created ✓
   - Minimum 3 test cases passing ✓
   - Phase 3 validation task created ✓
   ↓
2. System validates expected_outputs:
   - Files match patterns ✓
   - Tests pass ✓
   ↓
3. System requests user approval for phase transition
   ↓
4. Notification appears:
   - In-app notification
   - Email (if configured)
   - Dashboard shows approval pending badge
   ↓
5. User reviews:
   - Code changes (commit diff viewer)
   - Test results
   - Agent reasoning summaries
   ↓
6. User approves or rejects:
   - Approve → Ticket moves to PHASE_INTEGRATION
   - Reject → Ticket regresses, agent receives feedback
   ↓
7. Workflow continues autonomously
```

**Approval Points:**
- Phase transitions (INITIAL → IMPLEMENTATION → INTEGRATION → REFACTORING)
- PR reviews (before merge)
- Budget threshold exceeded
- High-risk changes

#### 4.2 PR Review & Merge

```
Agent completes feature implementation:
   ↓
1. Agent creates PR automatically
   ↓
2. System generates PR summary:
   - Code changes summary
   - Test coverage report
   - Risk assessment
   ↓
3. User receives notification: "PR ready for review"
   ↓
4. User reviews:
   - Commit diff viewer (side-by-side, syntax highlighted)
   - See exactly which code each agent modified
   - Test results
   - Agent reasoning
   ↓
5. User approves PR:
   - Merge PR
   - Ticket moves to DONE
   - Feature complete!
   ↓
OR
5. User requests changes:
   - Agent receives feedback
   - Agent makes changes
   - PR updated
   - Cycle repeats
```

---

### Phase 5: Ongoing Monitoring & Optimization

#### 5.1 Statistics Dashboard

```
User navigates to Statistics dashboard:
   ↓
Views analytics:
- Ticket statistics: Completion rates, cycle times
- Agent performance: Tasks completed, code quality
- Code change statistics: Lines changed, files modified
- Project health: WIP violations, budget status
- Discovery analytics: Discovery rates by type
- Cost tracking: LLM costs per workflow
```

#### 5.2 Search & Filtering

```
User uses Command Palette (Cmd+K) or Search bar:
   ↓
Search across:
- Tickets (by title, description, phase)
- Tasks (by description, status)
- Commits (by message, author, date)
- Agents (by status, capabilities)
- Code changes (by file, agent)
   ↓
Advanced filters:
- Date range
- Phase/status
- Agent
- Project
- Discovery type
```

#### 5.3 Audit Trails

```
User views audit trail for ticket:
   ↓
Sees complete history:
- When ticket created
- All phase transitions
- All agent assignments
- All code commits
- All discoveries made
- All interventions sent
- All approvals/rejections
   ↓
Can export audit trail:
- PDF report
- CSV export
- JSON export
```

---

## Key User Interactions

### Command Palette (Cmd+K)
Quick navigation to:
- Create new ticket
- Search tickets/tasks/commits
- Navigate to projects
- Open spec workspace
- View agent status
- Access settings

### Real-Time Updates
All views update automatically via WebSocket:
- Kanban board: Tickets move as agents work
- Dependency graph: Nodes update as tasks complete
- Activity timeline: New events appear instantly
- Agent status: Heartbeats update every 30s

### Intervention Tools
Users can intervene at any time:
- Pause/resume workflows
- Add constraints: "Make sure to use port 8020"
- Prioritize: "Focus on tests first"
- Refocus: "Switch to authentication flow"
- Stop: "Halt current work"

### Spec Management
Users can:
- View/edit specs in multi-tab workspace
- Switch between multiple specs
- Export specs to Markdown/YAML
- Version control specs
- Link specs to tickets

---

## User Personas & Use Cases

### Engineering Manager
**Primary Use Case**: Monitor multiple projects, approve phase transitions, review PRs

**Typical Flow:**
1. Logs in → Sees dashboard overview
2. Reviews pending approvals → Approves phase transitions
3. Monitors agent activity → Sees Guardian interventions
4. Reviews PRs → Approves merges
5. Checks statistics → Views project health

**Time Investment**: 10-15 minutes per day for strategic oversight

### Senior IC Engineer
**Primary Use Case**: Create feature requests, review code changes, provide technical guidance

**Typical Flow:**
1. Creates feature request → "Add payment processing"
2. Reviews generated spec → Edits requirements/design
3. Approves plan → System executes autonomously
4. Reviews code changes → Approves PRs
5. Provides feedback → Agents adjust

**Time Investment**: 30-60 minutes per feature (mostly review time)

### CTO/Technical Lead
**Primary Use Case**: Set up projects, configure workflows, monitor system health

**Typical Flow:**
1. Sets up new project → AI-assisted exploration
2. Configures approval gates → Sets phase gate requirements
3. Monitors system health → Views statistics dashboard
4. Reviews cost tracking → Optimizes agent usage
5. Configures Guardian rules → Sets intervention thresholds

**Time Investment**: Initial setup (1-2 hours), ongoing monitoring (15 min/day)

---

## Visual Design Principles

### Linear/Arc Aesthetic
- Clean, minimal, white-space-heavy
- Modern SaaS look
- Smooth animations
- Gentle shadows and subtle gradients

### Notion-Style Structured Blocks
- Spec workspace uses structured blocks for requirements/design
- Collapsible sections
- Rich text editing
- Block-level comments

### Obsidian-Style Sidebar
- Collapsible sidebar for spec navigation
- Quick access to all specs
- Search within sidebar
- Recent specs list

### Real-Time Indicators
- Live status badges
- Animated progress indicators
- WebSocket connection status
- Agent heartbeat indicators

---

## Success Metrics

### User Experience Goals
- **Reduced monitoring time**: From hours to minutes per day
- **Faster delivery**: Agents work 24/7 autonomously
- **Clear visibility**: Complete transparency into agent activity
- **Confidence**: Trust system enough to approve PRs without manual review

### System Goals
- **Autonomous execution**: Agents handle 80%+ of work without intervention
- **Self-healing**: Guardian detects and fixes 90%+ of stuck workflows
- **Discovery-driven**: System adapts to new requirements automatically
- **Quality gates**: 95%+ of PRs pass on first approval

---

## Related Documents

- [Product Vision](./product_vision.md) - Complete product concept
- [Front-End Design](./design/frontend/project_management_dashboard.md) - Detailed UI/UX specifications
- [Hephaestus Workflow Enhancements](./implementation/workflows/hephaestus_workflow_enhancements.md) - Spec-driven workflow implementation
- [Architecture Overview](../CLAUDE.md#architecture-overview) - Technical architecture
