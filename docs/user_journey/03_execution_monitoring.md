# 3 Execution Monitoring

**Part of**: [User Journey Documentation](./README.md)

---
### Phase 3: Autonomous Execution & Monitoring

#### 3.1 Agent Assignment & Execution

```
1. System automatically assigns tasks to available agents
   ↓
2. **Workspace Isolation System** creates isolated workspace:
   - Each agent gets dedicated workspace directory
   - Git branch created per workspace (e.g., `workspace-agent-123`)
   - Workspace inherits from parent agent (if specified)
   - Base branch configured (default: `main`)
   - Workspace type: local, docker, kubernetes, or remote
   ↓
3. System pre-loads relevant memories (collective intelligence):
   - Searches memory system for top 20 most relevant memories
   - Based on task description similarity
   - Covers 80% of agent needs upfront
   - Includes: error fixes, discoveries, decisions, codebase knowledge
   ↓
4. Agent spawns with enriched context:
   - Task description
   - Pre-loaded memories embedded in system prompt
   - Phase instructions and constraints
   - Related requirements and design docs
   - Isolated workspace path (agent never sees Git operations)
   ↓
5. Agents pick up tasks from queue (priority-based)
   ↓
6. **Workspace Operations** (transparent to agent):
   - Agent works in isolated directory
   - System commits workspace state for validation checkpoints
   - Merge conflicts resolved automatically (newest file wins)
   - Workspace cleanup and retention policies applied
   ↓
7. Execution Tab shows Progress Dashboard:
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
  - Phase badges show current phase (PHASE_REQUIREMENTS, PHASE_IMPLEMENTATION, etc.)
  - Click badge → Navigate to Phase Overview dashboard
  - Hover → See phase description and completion criteria
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
- **Workspace Information**:
  - Workspace directory path
  - Git branch name
  - Workspace type (local/docker/kubernetes/remote)
  - Parent agent (if workspace inherited)
  - Active workspace status
  - Workspace commits count
```

**Workspace Management:**
```
Workspace Isolation Features:
- Each agent gets isolated workspace automatically
- Git-backed workspaces with branch per agent
- Zero conflicts: Parallel agents work independently
- Knowledge inheritance: Child workspaces inherit parent state
- Automatic merge resolution: Deterministic conflict handling
- Clean experimentation: Each workspace has own branch
- Workspace retention: Configurable cleanup policies
- Checkpoint commits: Validation checkpoints tracked
- Merge conflict logging: All resolutions logged for audit
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


---

**Next**: See [README.md](./README.md) for complete documentation index.
