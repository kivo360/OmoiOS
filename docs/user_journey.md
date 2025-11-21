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

## Additional Flows & Edge Cases

### Error Handling & Failure Recovery

#### Agent Failure Scenarios

**Task Execution Failure:**
```
Agent fails to complete task:
   ↓
1. System detects failure (timeout, exception, test failure)
   ↓
2. Automatic retry logic:
   - Exponential backoff (1s, 2s, 4s, 8s + jitter)
   - Maximum retry attempts (configurable)
   - Error classification (retryable vs permanent)
   ↓
3. If retryable:
   - Agent retries with updated context
   - Guardian may provide intervention
   ↓
4. If permanent failure:
   - Task marked as failed
   - Discovery created (type: "bug" or "clarification_needed")
   - User notified
   - Option to spawn new task or update requirements
```

**Agent Stuck Detection:**
```
Agent stops responding:
   ↓
1. Heartbeat timeout (90s without heartbeat)
   ↓
2. System marks agent as "stuck"
   ↓
3. Guardian analyzes trajectory:
   - Checks alignment score
   - Reviews recent actions
   - Determines intervention needed
   ↓
4. Guardian sends intervention:
   - "[GUARDIAN INTERVENTION] Please provide status update"
   ↓
5. If no response:
   - Agent marked as failed
   - Task reassigned to new agent
   - Original agent's work preserved
```

**Spec Generation Failure:**
```
AI fails to generate spec:
   ↓
1. User sees error message:
   - "Unable to generate spec. Please try again or provide more details."
   ↓
2. Options:
   - Retry with same input
   - Provide more context
   - Use manual spec creation
   ↓
3. System logs error for analysis
   ↓
4. User can contact support if persistent
```

### Notification & Alert Flows

#### Notification Types

**In-App Notifications:**
```
Notification Center (Bell Icon):
   ↓
Shows unread notifications:
- Phase transition approval pending
- PR ready for review
- Agent stuck/failed
- Discovery made
- Budget threshold exceeded
- WIP limit violation
   ↓
Click notification → Navigate to relevant page
   ↓
Mark as read / Dismiss
```

**Email Notifications:**
```
User configures email preferences:
   ↓
Receives emails for:
- Critical: Agent failures, budget exceeded
- Important: Phase approvals, PR reviews
- Informational: Task completions, discoveries
   ↓
Email contains:
- Summary of event
- Direct link to relevant page
- Action buttons (Approve/Reject)
```

**Slack/Webhook Integration:**
```
Configure webhook in settings:
   ↓
System sends webhook events:
- Ticket created/completed
- Agent status changes
- Discovery events
- Approval requests
   ↓
Slack channel receives updates:
- Rich formatted messages
- Links back to dashboard
- Quick action buttons
```

### Settings & Configuration

#### User Settings Flow

**Profile Settings:**
```
Navigate to /settings/profile:
   ↓
Configure:
- Display name
- Email preferences
- Timezone
- Language
- Theme (light/dark)
   ↓
Save changes → Applied immediately
```

**Notification Preferences:**
```
Navigate to /settings/notifications:
   ↓
Configure per notification type:
- In-app: ✓ Enabled
- Email: ✓ Enabled
- Slack: ✓ Enabled
   ↓
Set frequency:
- Real-time
- Daily digest
- Weekly summary
   ↓
Save preferences
```

**Integration Settings:**
```
Navigate to /settings/integrations:
   ↓
GitHub Integration:
- Connected repositories
- Webhook status
- Permissions granted
- [Reconnect] [Disconnect]
   ↓
Slack Integration:
- Workspace connection
- Channel selection
- Event subscriptions
- [Connect] [Disconnect]
```

#### Project Settings Flow

**Project Configuration:**
```
Navigate to /projects/:id/settings:
   ↓
General Tab:
- Project name, description
- Default phase
- Status (active/archived)
   ↓
GitHub Tab:
- Repository connection
- Branch selection
- Webhook configuration
   ↓
Phases Tab:
- Phase definitions
- Done criteria
- Expected outputs
   ↓
Board Tab:
- WIP limits per phase
- Column configuration
- Auto-transition rules
   ↓
Notifications Tab:
- Project-specific alerts
- Team member preferences
```

### Multi-User Collaboration

#### Team Workflows

**Role-Based Access:**
```
User Roles:
- Admin: Full control (settings, agents, projects)
- Manager: Approve/reject, monitor, intervene
- Viewer: Read-only access
   ↓
Permissions enforced:
- Can only approve if Manager+
- Can only spawn agents if Admin
- Can only modify settings if Admin
```

**Collaborative Review:**
```
Multiple users review same PR:
   ↓
1. User A reviews → Requests changes
   ↓
2. User B reviews → Approves
   ↓
3. System shows:
   - Both reviews visible
   - Approval status: "1 approve, 1 request changes"
   - Requires all approvers to approve
   ↓
4. User A updates review → Approves
   ↓
5. PR can be merged
```

**Comments & Mentions:**
```
User adds comment to ticket:
   ↓
1. Types comment with @mention:
   - "@john please review this approach"
   ↓
2. System:
   - Notifies @john via in-app + email
   - Links comment to ticket
   - Shows in activity timeline
   ↓
3. @john receives notification:
   - Clicks link → Goes to ticket
   - Sees comment highlighted
   - Can reply or take action
```

### Keyboard Shortcuts & Accessibility

#### Keyboard Navigation

**Global Shortcuts:**
```
Cmd+K (Mac) / Ctrl+K (Windows):
   - Opens command palette
   - Quick navigation/search
   ↓
Cmd+/ (Mac) / Ctrl+/ (Windows):
   - Shows keyboard shortcuts help
   ↓
Esc:
   - Closes modals
   - Exits fullscreen views
   ↓
Arrow Keys:
   - Navigate lists
   - Move between tickets in board
```

**Board Shortcuts:**
```
j/k: Navigate up/down tickets
h/l: Navigate left/right columns
Enter: Open selected ticket
Space: Toggle ticket selection
```

**Spec Workspace Shortcuts:**
```
Tab: Switch between Requirements/Design/Tasks/Execution
Cmd+S: Save spec changes
Cmd+E: Export spec
Cmd+/: Show formatting help
```

#### Accessibility Features

**Screen Reader Support:**
```
- ARIA labels on all interactive elements
- Semantic HTML structure
- Keyboard navigation support
- Screen reader announcements for:
  - Real-time updates
  - Status changes
  - Error messages
```

**Visual Accessibility:**
```
- High contrast mode option
- Color-blind friendly color schemes
- Resizable text
- Focus indicators
- Reduced motion option
```

### Mobile & Responsive Design

#### Mobile Experience

**Responsive Layout:**
```
Mobile (< 768px):
- Collapsible sidebar (hamburger menu)
- Stacked columns on Kanban board
- Simplified ticket cards
- Touch-optimized controls
   ↓
Tablet (768px - 1024px):
- Sidebar can be toggled
- Board shows 2-3 columns
- Full ticket details available
   ↓
Desktop (> 1024px):
- Full sidebar visible
- All columns visible
- Multi-panel layouts
```

**Mobile-Specific Features:**
```
- Swipe gestures:
  - Swipe right: Open ticket
  - Swipe left: Quick actions
- Pull to refresh:
  - Refresh board data
  - Sync latest updates
- Touch targets:
  - Minimum 44x44px
  - Adequate spacing
```

### Troubleshooting & Support

#### Common Issues & Solutions

**WebSocket Connection Lost:**
```
Issue: Real-time updates stop working
   ↓
System detects disconnection:
   - Shows "Reconnecting..." indicator
   - Attempts automatic reconnection
   ↓
If reconnection fails:
   - Shows "Connection lost" banner
   - Manual refresh button
   - Falls back to polling
```

**Agent Not Picking Up Tasks:**
```
Issue: Tasks stuck in queue
   ↓
Check:
1. Agent status (active/idle/stuck)
2. Agent phase assignment matches task phase
3. Task dependencies satisfied
4. WIP limits not exceeded
   ↓
Solutions:
- Spawn new agent
- Manually assign task
- Check agent logs
- Contact support
```

**Spec Generation Slow:**
```
Issue: Spec takes > 5 minutes to generate
   ↓
Possible causes:
- Large codebase analysis
- Complex requirements
- LLM API rate limiting
   ↓
User sees:
- Progress indicator
- Estimated time remaining
- Option to cancel
   ↓
If timeout:
- Saves partial spec
- Allows manual completion
- Option to retry
```

### Export & Import Flows

#### Exporting Data

**Spec Export:**
```
Navigate to spec → Click "Export":
   ↓
Options:
- Markdown (.md)
- YAML (.yaml)
- PDF (.pdf)
   ↓
Select format → Download
   ↓
File contains:
- All requirements
- Design documents
- Task breakdown
- Version history (optional)
```

**Audit Trail Export:**
```
Navigate to ticket → Audit tab → Export:
   ↓
Options:
- PDF report
- CSV data
- JSON format
   ↓
Contains:
- Complete history
- All events
- Timestamps
- User actions
```

**Project Export:**
```
Navigate to project settings → Export:
   ↓
Exports:
- All tickets
- All tasks
- All specs
- Agent history
- Commit history
   ↓
Use cases:
- Backup
- Migration
- Compliance
```

---

## Related Documents

- [Product Vision](./product_vision.md) - Complete product concept
- [Front-End Design](./design/frontend/project_management_dashboard.md) - Detailed UI/UX specifications
- [Hephaestus Workflow Enhancements](./implementation/workflows/hephaestus_workflow_enhancements.md) - Spec-driven workflow implementation
- [Architecture Overview](../CLAUDE.md#architecture-overview) - Technical architecture
