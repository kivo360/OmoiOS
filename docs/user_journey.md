# OmoiOS User Journey & Flow

**Created**: 2025-01-30  
**Status**: User Journey Documentation  
**Purpose**: Complete user flow from onboarding to feature completion

---

## Overview

OmoiOS follows a **spec-driven autonomous engineering workflow** where users describe what they want built, and the system automatically plans, executes, and monitors the work. Users provide strategic oversight at approval gates rather than micromanaging every step.

---

## Dashboard Layout

### Main Dashboard Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Header: Logo | Projects | Search | Notifications | Profile  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────┐  ┌──────────────────────────────────────┐   │
│  │ Sidebar │  │  Main Content Area                    │   │
│  │         │  │                                       │   │
│  │ • Home  │  │  ┌────────────────────────────────┐ │   │
│  │ • Board │  │  │ Overview Section                │ │   │
│  │ • Graph │  │  │ • Total Specs: 5                │ │   │
│  │ • Specs │  │  │ • Active Agents: 3              │ │   │
│  │ • Stats │  │  │ • Tickets in Progress: 12        │ │   │
│  │ • Agents│  │  │ • Recent Commits: 8              │ │   │
│  │ • Cost  │  │  └────────────────────────────────┘ │   │
│  │ • Audit │  │                                       │   │
│  │         │  │  ┌────────────────────────────────┐ │   │
│  │         │  │  │ Active Specs Grid               │ │   │
│  │         │  │  │                                │ │   │
│  │         │  │  │ ┌──────────┐  ┌──────────┐   │ │   │
│  │         │  │  │ │ Spec 1    │  │ Spec 2    │   │ │   │
│  │         │  │  │ │ Progress: │  │ Progress: │   │ │   │
│  │         │  │  │ │ ████░░ 60%│  │ ██████ 80%│   │ │   │
│  │         │  │  │ └──────────┘  └──────────┘   │ │   │
│  │         │  │  └────────────────────────────────┘ │   │
│  │         │  │                                       │   │
│  │         │  │  ┌────────────────────────────────┐ │   │
│  │         │  │  │ Quick Actions                   │ │   │
│  │         │  │  │ [+ New Spec] [+ New Project]   │ │   │
│  │         │  │  └────────────────────────────────┘ │   │
│  └─────────┘  └──────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Right Sidebar (Collapsible)                        │  │
│  │  Recent Activity Feed                                │  │
│  │  • Spec "Auth System" requirements approved          │  │
│  │  • Agent worker-1 completed task "Setup JWT"        │  │
│  │  • Discovery: Bug found in login flow               │  │
│  │  • Guardian intervention sent to worker-2            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Dashboard Sections:**
- **Overview Section**: Key metrics (total specs, active agents, tickets in progress, recent commits)
- **Active Specs Grid**: Cards showing all active specs with progress bars
- **Quick Actions**: Buttons for common actions (+ New Spec, + New Project)
- **Recent Activity Sidebar**: Chronological feed of recent events (collapsible)

**Managing Multiple Specs:**
- Dashboard shows grid view of all active specs
- Each spec card displays:
  - Spec name and description
  - Progress bar (0-100%)
  - Status badge (Draft, Requirements, Design, Tasks, Executing, Completed)
  - Last updated timestamp
  - Quick actions ([View] [Edit] [Export])
- Filter options: All | Active | Completed | Draft
- Search bar to find specs by name

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
- **Agent Configuration** (New):
  - Set number of parallel agents (1-5)
  - Configure agent preferences (capabilities, phase assignments)
  - Set review requirements (auto-approve vs manual approval gates)
  - Configure agent types (Worker, Planner, Validator)

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
3. Spec Creation Modal appears with fields:
   - Spec Title: [________________]
   - Description (natural language): [Add payment processing with Stripe]
   - Repository Selection: [Select Repository ▼]
   - Priority: [Low] [Medium] [High] (default: Medium)
   ↓
4. User clicks "Create Spec"
   ↓
5. System validates inputs:
   - Title required
   - Description minimum length check
   - Repository must be connected
   ↓
6. System analyzes:
   - Current codebase structure
   - Existing dependencies
   - Similar features in codebase
   ↓
7. System generates spec-driven workflow:
   - Requirements Phase (EARS-style requirements)
   - Design Phase (architecture, sequence diagrams)
   - Planning Phase (task breakdown with dependencies)
   - Execution Phase (autonomous code generation)
   ↓
8. Spec appears in Spec Workspace (multi-tab view)
   ↓
9. Toast notification: "Spec created successfully"
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
3. User reviews Requirements tab:
   - Views EARS format examples:
     ```
     REQ-001
     WHEN: User enables 2FA in account settings
     THE SYSTEM SHALL: Display QR code for authenticator app setup
     ACCEPTANCE CRITERIA:
     ✓ QR code generates valid TOTP secret
     ✓ User can scan with Google Authenticator
     ✓ Backup codes generated automatically
     ```
   - Can edit requirements inline (structured blocks)
   - Can add new requirements
   - Can delete or reorder requirements
   ↓
4. User clicks "Approve Requirements" button
   ↓
5. Toast notification: "Requirements approved ✓"
   ↓
6. User reviews Design tab:
   - Views architecture components with names:
     - Authentication Service
       ├─ OAuth2 Handler
       ├─ JWT Generator
       └─ Token Validator
   - Views data model examples (JavaScript/Python)
   - Views sequence diagrams
   - Can edit design components inline
   ↓
7. User clicks "Approve Design" button
   ↓
8. Toast notification: "Design approved ✓"
   ↓
9. User reviews Tasks tab:
   - Views discrete tasks with dependencies
   - Can edit task descriptions
   - Can adjust dependencies
   ↓
10. User clicks "Approve Plan" when satisfied
    ↓
11. System transitions to Execution Phase
    ↓
12. Toast notification: "Plan approved. Execution starting..."
    ↓
13. Tickets move from Backlog → Initial phase in Kanban board
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
2. System pre-loads relevant memories (collective intelligence):
   - Searches memory system for top 20 most relevant memories
   - Based on task description similarity
   - Covers 80% of agent needs upfront
   - Includes: error fixes, discoveries, decisions, codebase knowledge
   ↓
3. Agent spawns with enriched context:
   - Task description
   - Pre-loaded memories embedded in system prompt
   - Phase instructions and constraints
   - Related requirements and design docs
   ↓
4. Agents pick up tasks from queue (priority-based)
   ↓
5. Execution Tab shows Progress Dashboard:
   - Overall progress bar (0-100%)
   - Test coverage percentage
   - Tests passing count (e.g., "45/50 passing")
   - Active agents count
   - Running tasks section with real-time cards
   - Pull Requests section with PR cards
   ↓
6. Agents execute in isolated workspaces:
   - Clone repository
   - Use pre-loaded memories to avoid common pitfalls
   - Analyze requirements
   - Write code
   - Run tests
   - Self-correct on failures
   - Search memories dynamically when encountering errors (find_memory)
   - Save discoveries for other agents (save_memory)
   ↓
7. Running Tasks Section shows real-time cards:
   - Task name and description
   - Current status (in progress, testing, committing)
   - Assigned agent name
   - Progress percentage
   - Time elapsed
   - [View Live Logs] button
   ↓
8. Pull Requests Section shows PR cards:
   - PR title and number
   - Status (open, review, merged)
   - Linked task
   - Files changed (+X -Y)
   - [Review PR] button opens PR Review Modal
   ↓
9. PR Review Modal (when clicking "Review PR"):
   - Side-by-side diff viewer
   - File list with change stats
   - Test results summary
   - Commit history
   - Agent attribution
   - [Approve] [Request Changes] [View Full Diff] buttons
   ↓
10. Agent Activity Log shows timestamped events:
    - "10:23 AM - Agent worker-1 started task 'Implement JWT'"
    - "10:25 AM - Agent worker-1 committed changes (+450 lines)"
    - "10:27 AM - Agent worker-1 ran tests (45/50 passing)"
    - "10:28 AM - Guardian intervention sent: 'Focus on core flow'"
    ↓
11. Pause/Resume Control:
    - [Pause Execution] button pauses all agents
    - [Resume Execution] button resumes paused agents
    - Individual task pause/resume available
    ↓
12. Real-time updates via WebSocket:
    - Task status changes
    - Agent heartbeats
    - Code commits
    - Test results
    - Memory operations (MEMORY_SAVED, MEMORY_SEARCHED)
    ↓
13. Dashboard updates in real-time:
    - Kanban board: Tickets move through phases
    - Dependency graph: Tasks complete, dependencies resolve
    - Activity timeline: Shows all agent actions (including memory operations)
    - Progress dashboard: Metrics update live
```

#### 3.2 Monitoring Views

**Kanban Board View:**
```
Columns: BACKLOG → INITIAL → IMPLEMENTATION → INTEGRATION → REFACTORING → DONE

Features:
- **Drag-and-Drop**: Mouse drag or keyboard navigation (arrow keys: h/l to move left/right, j/k to move up/down)
- **Ticket Details Drawer**: Slides from right when clicking ticket card
  - Shows full ticket details
  - Tabs: Details | Tasks | Commits | Graph | Comments | Audit
  - Can edit ticket inline
  - Can link/unlink related tickets
- **View Switcher**: Toggle between Kanban | List | Graph views
- **Filters**: 
  - Type filter (bug, feature, optimization)
  - Phase filter (show only specific phases)
  - Status filter (active, blocked, completed)
  - Error filter (show tickets with errors)
- **WIP Limit Indicators**: Visual warnings when column exceeds limit
- **Commit Indicators**: (+X -Y) on ticket cards showing code changes
- **Phase Badges**: Color-coded phase indicators
- **Priority Indicators**: CRITICAL (red), HIGH (orange), MEDIUM (yellow), LOW (gray)
- **Real-Time Updates**: Live synchronization as agents work
- **Keyboard Shortcuts**:
  - `j/k`: Navigate up/down tickets
  - `h/l`: Navigate left/right columns
  - `Enter`: Open selected ticket drawer
  - `Space`: Toggle ticket selection
  - `Esc`: Close drawer
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
- Memory operations (agents saving/finding memories)
- Approvals/rejections
- Code commits
- Test results

Features:
- Filter by event type
- Search timeline
- Link to related tickets/tasks
- Show agent reasoning summaries
- Show memory activity (collective learning)
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
1. Agent encounters error or identifies issue
   ↓
2. Agent searches memory: find_memory("database connection timeout")
   - May find similar past issues
   - Learns from previous solutions
   ↓
3. Agent calls DiscoveryService.record_discovery_and_branch()
   ↓
4. System creates:
   - TaskDiscovery record (type: "bug")
   - New Task B: "Fix bug"
   - Links Task B as child of Task A
   ↓
5. Agent saves discovery to memory: save_memory()
   - Content: "Found database connection timeout in payment service"
   - Memory type: discovery
   - Tags: ["database", "payment", "timeout"]
   ↓
6. WebSocket events:
   - DISCOVERY_MADE
   - TASK_CREATED
   - MEMORY_SAVED
   ↓
7. Dashboard updates:
   - Dependency graph shows new branch
   - Activity timeline shows discovery event and memory save
   - Kanban board shows new task
   ↓
8. Workflow branches:
   Original path continues
   New branch handles bug fix
   Both paths execute in parallel
   ↓
9. Future agents benefit:
   - Pre-loaded memories include this discovery
   - Similar issues detected faster
   - Solutions propagate automatically
```

**Discovery Types:**
- Bug found
- Optimization opportunity
- Missing requirement
- Security issue
- Performance issue
- Technical debt
- Integration issue

**Memory-Enhanced Discovery:**
- Agents check memory before creating duplicate discoveries
- Past solutions inform new discovery handling
- Discoveries saved for future reference
- Collective intelligence improves over time

#### 3.4 Collective Intelligence & Memory System

**How Agents Learn from Each Other:**

```
Agent A encounters PostgreSQL timeout error:
   ↓
1. Agent A calls find_memory("PostgreSQL timeout"):
   - Searches semantic memory using hybrid search (semantic + keyword)
   - Finds relevant memories from past agents
   ↓
2. System returns top 5 matching memories:
   - Memory 1: "Fixed PostgreSQL timeout by increasing pool_size to 20" (score: 0.89)
   - Memory 2: "Connection timeout solution: set pool_timeout=30" (score: 0.82)
   - Memory 3: "PostgreSQL connection pooling best practices" (score: 0.75)
   ↓
3. Agent A applies solution from Memory 1
   ↓
4. Agent A fixes the issue successfully
   ↓
5. Agent A calls save_memory():
   - Content: "Fixed PostgreSQL timeout by increasing pool_size to 20 and setting pool_timeout=30"
   - Memory type: error_fix
   - Tags: ["postgresql", "timeout", "connection-pool"]
   - Related files: ["config/database.py"]
   ↓
6. Memory stored in system:
   - Semantic embedding generated
   - Available for future agents to find
   - WebSocket: MEMORY_SAVED → Dashboard shows memory activity
   ↓
7. Agent B (working on different task) encounters similar issue:
   - Pre-loaded memories already include Agent A's solution
   - Agent B applies fix immediately without searching
   - Problem solved faster thanks to collective intelligence
```

**Memory Operations Flow:**

**Pre-loaded Context (80% Coverage):**
- Happens automatically at agent spawn
- Top 20 most relevant memories embedded in agent's initial prompt
- Covers common scenarios, patterns, and solutions
- Reduces need for dynamic searches during execution

**Dynamic Search (20% Coverage):**
- Agent calls `find_memory(query)` when encountering:
  - Errors not in pre-loaded context
  - Need for implementation details
  - Finding related work or patterns
- Uses hybrid search (semantic + keyword with RRF)
- Returns top matching memories with similarity scores

**Memory Saving:**
- Agent calls `save_memory()` after:
  - Fixing errors (memory_type: error_fix)
  - Making discoveries (memory_type: discovery)
  - Making decisions (memory_type: decision)
  - Learning patterns (memory_type: learning)
  - Finding gotchas (memory_type: warning)
  - Understanding codebase (memory_type: codebase_knowledge)

**Memory Types:**
- `error_fix`: Solutions to errors (e.g., "Fixed ModuleNotFoundError by adding src/ to PYTHONPATH")
- `discovery`: Important findings (e.g., "Authentication uses JWT with 24h expiry")
- `decision`: Key decisions & rationale (e.g., "Chose Redis over Memcached for pub/sub support")
- `learning`: Lessons learned (e.g., "Always validate input before SQL queries")
- `warning`: Gotchas to avoid (e.g., "Don't use os.fork() with SQLite connections")
- `codebase_knowledge`: Code structure insights (e.g., "API routes are defined in src/api/routes/")

**Benefits:**
- Agents avoid repeating mistakes
- Solutions propagate across workflows
- Faster problem resolution
- Consistent patterns across codebase
- Knowledge accumulates over time

#### 3.5 Guardian Interventions

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

#### 4.3 Completion Summary & Export

```
All tasks completed and PRs merged:
   ↓
1. System shows Completion Summary checklist:
   ✅ All requirements met
   ✅ All tests passing (50/50)
   ✅ All PRs merged
   ✅ Code deployed to staging (if configured)
   ✅ Documentation updated
   ↓
2. User reviews completion summary
   ↓
3. User clicks "Mark as Complete"
   ↓
4. Spec status changes to "Completed"
   ↓
5. Spec moves to "Completed" section in dashboard
   ↓
6. User can export spec:
   - Click "Export Spec" button
   - Select format: Markdown | YAML | PDF
   - Download file with complete spec (Requirements + Design + Tasks + Execution history)
   ↓
7. Toast notification: "Spec completed and exported ✓"
```

**Completion Summary Checklist:**
- All requirements met (verified against EARS requirements)
- All tests passing (with coverage percentage)
- All PRs merged (with commit SHAs)
- Code deployed (if deployment configured)
- Documentation updated (if documentation tasks exist)
- All agent learnings saved to memory system

**Export Options:**
- **Markdown**: Complete spec in markdown format
- **YAML**: Structured YAML export for version control
- **PDF**: Formatted PDF report for documentation

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

#### 5.2 Agents Overview Page

```
User navigates to /agents:
   ↓
Views Agents Overview Page:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Agents Overview                              [Spawn Agent] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Agent Metrics                                       │  │
│  │                                                      │  │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐          │  │
│  │  │  5   │  │  3   │  │  2   │  │  1   │          │  │
│  │  │Total │  │Active│  │Idle  │  │Stuck │          │  │
│  │  └──────┘  └──────┘  └──────┘  └──────┘          │  │
│  │                                                      │  │
│  │  Average Alignment: 78%                            │  │
│  │  Tasks Completed Today: 12                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Agent List                                          │  │
│  │                                                      │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │ Agent: worker-1                               │  │  │
│  │  │ Status: 🟢 Active                             │  │  │
│  │  │ Phase: IMPLEMENTATION                         │  │  │
│  │  │ Current Task: "Implement JWT"                │  │  │
│  │  │ Alignment: 85%                                │  │  │
│  │  │ Tasks Completed: 8                            │  │  │
│  │  │ Commits: 15                                   │  │  │
│  │  │ Lines Changed: +2,450 -120                    │  │  │
│  │  │ [View Details] [Intervene]                    │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  │                                                      │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │ Agent: worker-2                               │  │  │
│  │  │ Status: 🟡 Idle                                │  │  │
│  │  │ Phase: INTEGRATION                            │  │  │
│  │  │ Current Task: None                            │  │  │
│  │  │ Alignment: N/A                                │  │  │
│  │  │ Tasks Completed: 5                            │  │  │
│  │  │ Commits: 8                                    │  │  │
│  │  │ Lines Changed: +890 -45                       │  │  │
│  │  │ [View Details] [Assign Task]                  │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Filters: [All ▼] [Active] [Idle] [Stuck] [By Phase ▼]     │
│  Search: [________________] [🔍]                            │
└─────────────────────────────────────────────────────────────┘
```

**Agent Metrics:**
- Total agents count
- Active agents (currently working)
- Idle agents (waiting for tasks)
- Stuck agents (needs intervention)
- Average alignment score across all agents
- Tasks completed today
- Total commits made
- Total lines changed

**Agent Card Details:**
- Agent ID and type
- Current status (Active, Idle, Stuck, Failed)
- Phase assignment
- Current task (if active)
- Alignment score (if active)
- Performance metrics (tasks completed, commits, lines changed)
- Quick actions ([View Details] [Intervene] [Assign Task])

#### 5.3 Theme Settings

```
User navigates to Settings → Appearance:
   ↓
Views Theme Settings:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Theme Settings                                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Theme Mode:                                               │
│  ○ Light (default)                                         │
│  ● Dark                                                    │
│  ○ System (follows OS preference)                          │
│                                                              │
│  Accent Color:                                             │
│  [Select Color ▼]                                          │
│  • Blue (default)                                          │
│  • Green                                                   │
│  • Purple                                                  │
│  • Orange                                                  │
│                                                              │
│  Font Size:                                                │
│  [Small] [Medium] [Large]                                  │
│                                                              │
│  Reduced Motion:                                           │
│  ☐ Enable reduced motion animations                        │
│                                                              │
│  [Save Changes]                                            │
└─────────────────────────────────────────────────────────────┘
```

**Theme Options:**
- **Light Mode**: Default light theme
- **Dark Mode**: Dark theme for low-light environments
- **System**: Automatically follows OS theme preference
- **Accent Color**: Customize primary color scheme
- **Font Size**: Adjustable text size
- **Reduced Motion**: Disable animations for accessibility

#### 5.4 Search & Filtering

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

#### 5.5 Audit Trails

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
