# Demo Board Implementation Plan

## Vision
A single page where you:
1. **Create tickets** using spec-driven-dev skill OR the command center
2. Click **"Start Processing"** and watch AI agents work through tickets
3. See **cards moving across a kanban board** in real-time
4. Watch **multiple agents working in parallel** on dependent tasks
5. Click into any card to see the **live agent terminal output**
6. Watch **PRs appear** when agents complete work

---

## Current State (What Already Exists)

### Frontend (95% Ready)
| Component | Location | Status |
|-----------|----------|--------|
| Kanban Board | `/app/(app)/board/[projectId]/page.tsx` | ✅ Full drag-drop, WIP limits, filters |
| Sandbox Viewer | `/app/(app)/sandbox/[sandboxId]/page.tsx` | ✅ Live event stream, 40+ event types |
| Command Center | `/app/(app)/command/page.tsx` | ✅ Creates tickets, launches sandboxes |
| WebSocket Provider | `/providers/WebSocketProvider.tsx` | ✅ Auto-reconnect, auth-aware |
| Task Cards | `/components/custom/TaskCard.tsx` | ✅ Status badges, animations |
| Board API | `/lib/api/board.ts` | ✅ Move tickets, get stats |
| Real-time hooks | `/hooks/useSandbox.ts` | ✅ SSE event subscription |
| Workflow Modes | `/components/command/WorkflowModeSelector.tsx` | ✅ Quick vs Spec-Driven modes |

### Backend (100% Ready)
| Component | Location | Status |
|-----------|----------|--------|
| Spawn Tasks | `POST /tickets/{id}/spawn-phase-tasks` | ✅ Creates tasks for phase |
| Task Queue | `TaskQueueService` | ✅ Priority queue, concurrency limits |
| Orchestrator | `orchestrator_worker.py` | ✅ Polls every 1s, spawns sandboxes |
| Dependency Graph | `dependency_graph.py` | ✅ Blocks until deps complete |
| Phase Progression | `phase_progression_service.py` | ✅ Auto-advances on completion |
| Event Bus | `event_bus.py` | ✅ Redis pub/sub to WebSocket |
| Spec Workflow MCP | `mcp/spec_workflow.py` | ✅ Create specs, tickets, tasks via MCP |

### Spec-Driven Dev Skill (Available)
| Tool | Purpose |
|------|---------|
| `spec_cli.py` | CLI for viewing, validating, syncing specs |
| `mcp__spec_workflow__create_spec` | Create specification |
| `mcp__spec_workflow__create_ticket` | Create ticket from spec |
| `mcp__spec_workflow__add_spec_task` | Add task to spec |
| Local `.omoi_os/` files | Backup/reference for specs, tickets, tasks |

---

## What's Missing (The 5% Gap)

### 1. "Start Processing" Button on Board
The board exists but has no button to kick off execution:
- Button in board header: "Start Processing"
- Calls `POST /tickets/{id}/spawn-phase-tasks` for each ticket in backlog
- Or a batch endpoint to process all pending tickets

### 2. Real-Time Board Updates
The WebSocket is connected but board doesn't subscribe to task/ticket events:
- When `TASK_STATUS_CHANGED` fires → update card status badge
- When `TICKET_PHASE_ADVANCED` fires → move card to next column
- When `SANDBOX_SPAWNED` fires → show "running" indicator on card

### 3. Click Card → See Agent Working
Cards exist but don't link to the sandbox viewer:
- Each task has a `sandbox_id` when running
- Card click should open sandbox viewer in a panel/modal
- Show live agent output alongside the board

### 4. Ticket Creation on Board
Need to show tickets being created live:
- When using command center or spec-driven skill
- New ticket card should animate onto the board
- Subscribe to `TICKET_CREATED` events

### 5. Demo Data Seeding
Need a project with:
- 4-5 board columns mapped to phases
- 5-10 tickets spread across columns
- Tasks with dependencies (some parallel, some sequential)

---

## Three Entry Points for Demo

### Entry Point 1: Command Center (Already Works)
`/command` → Create ticket → Sandbox spawns → Redirect to sandbox viewer

**What exists:**
- Quick mode: Creates ticket in PHASE_IMPLEMENTATION, auto-spawns sandbox
- Spec-driven mode: Creates ticket in PHASE_REQUIREMENTS, generates spec

**What's missing:**
- After sandbox spawns, should also show on board (real-time update)
- Spec-driven should show spec workspace for approval before implementation

### Entry Point 2: Board Page (Needs Work)
`/board/[projectId]` → See all tickets → Click "Start Processing" → Watch cards move

**What exists:**
- Kanban board with drag-drop
- Ticket cards with status badges

**What's missing:**
- "Start Processing" button
- Real-time card updates from WebSocket
- Click card → See agent panel

### Entry Point 3: Spec-Driven Skill (Needs Integration)
Use Claude skill → Generate specs/tickets/tasks → Sync to API → Process on board

**What exists:**
- Full spec-driven-dev skill with MCP tools
- `spec_cli.py` for syncing to API
- Dual-write to `.omoi_os/` for backup

**What's missing:**
- UI for spec approval workflow
- Integration between spec workspace and board
- Automatic ticket creation from approved specs

---

## Implementation Plan

### Phase 0: Understand the Flow (Before Coding)
**Goal:** Map the complete user journey from idea to PR

```
User Journey:
1. User has an idea → Command Center OR Spec-Driven Skill
2. Ticket created → Appears on Board (Backlog column)
3. User clicks "Start Processing" → Tasks spawn for ticket
4. Orchestrator picks up tasks → Sandboxes spawn
5. Agent works → Events stream to board (status updates)
6. Task completes → Card updates, phase may advance
7. All tasks done → Ticket moves to next column
8. PR created → Link appears on card
```

### Phase 1: Start Button + Task Spawning (30 min)
**Goal:** Click button, tasks get created and queued

1. Add "Start Processing" button to board header
2. On click:
   - Get all tickets in "Backlog" column (or selected tickets)
   - Call `POST /tickets/{id}/spawn-phase-tasks` for each
   - Show toast: "Spawned X tasks"

**Files to modify:**
- `/app/(app)/board/[projectId]/page.tsx` - Add button
- `/lib/api/tickets.ts` - Add `spawnPhaseTasks(ticketId)` function

### Phase 2: Real-Time Card Updates (45 min)
**Goal:** Cards update status live as agents work

1. Subscribe board to WebSocket events
2. Handle events:
   ```typescript
   TICKET_CREATED → Add new card to appropriate column
   TASK_CREATED → Add task count badge to ticket card
   TASK_STATUS_CHANGED → Update status icon (pending→running→completed)
   TICKET_STATUS_CHANGED → Move card to appropriate column
   SANDBOX_SPAWNED → Show "Agent running" indicator
   ```
3. Use React Query cache invalidation or optimistic updates

**Files to modify:**
- `/app/(app)/board/[projectId]/page.tsx` - Add event subscription
- `/hooks/useBoard.ts` - Add real-time update handler

### Phase 3: Split View - Board + Agent (1 hour)
**Goal:** See board and agent output side-by-side

**Option A: Collapsible Panel (Recommended)**
- Add collapsible right panel to existing board page
- Click card → Panel slides in with sandbox viewer
- Shows "Select a task to view agent" when nothing selected

**Option B: New Demo Page**
- Create `/app/(app)/demo/[projectId]/page.tsx`
- Fixed split layout: Board (60%) | Agent Viewer (40%)
- More impressive but more work

**Files to create/modify:**
- `/components/board/AgentPanel.tsx` - Embedded sandbox viewer
- `/app/(app)/board/[projectId]/page.tsx` - Add panel toggle

### Phase 4: Ticket Creation Flow (30 min)
**Goal:** See tickets appear on board as they're created

1. From Command Center:
   - After ticket created, board should show it (already have events)
   - Just need board to subscribe to `TICKET_CREATED`

2. From Spec-Driven Skill:
   - Use `spec_cli.py sync push` to create tickets from local files
   - Board picks up via events
   - OR add "Sync Specs" button to board that calls the API

**Files to modify:**
- `/app/(app)/board/[projectId]/page.tsx` - Handle TICKET_CREATED event

### Phase 5: Spec-Driven Workflow UI (Optional - 2 hours)
**Goal:** Visual spec approval before implementation

This is a bigger piece - creating a spec workspace. Could be Phase 2 of demo:
1. Spec approval page showing requirements/design
2. "Approve & Generate Tasks" button
3. Tasks created → Tickets updated → Board shows work items

**Skip for MVP demo** - can show spec-driven via CLI instead.

### Phase 6: Demo Data + Polish (30 min)
**Goal:** Have a compelling demo ready

1. Create seed script or use `spec_cli.py`:
   ```bash
   # Use spec-driven skill to generate specs
   # Then sync to API
   cd .claude/skills/spec-driven-dev/scripts
   python spec_cli.py sync push --project-id <id>
   ```

2. Or create via Command Center:
   - Create 5-10 tickets with realistic titles
   - Mix of different phases

3. Polish:
   - Loading states while spawning
   - Progress indicator (3/10 tasks complete)
   - Success animation when all done

---

## Using Spec-Driven Dev Skill for Demo Data

The spec-driven-dev skill can auto-generate tickets and tasks from a feature description:

### Quick Generation Flow
```bash
# 1. Describe feature to Claude with spec-driven skill
"I want to build a notification system with email and in-app notifications"

# 2. Claude generates:
#    - .omoi_os/requirements/notifications.md
#    - .omoi_os/designs/notifications.md
#    - .omoi_os/tickets/TKT-001.md, TKT-002.md, etc.
#    - .omoi_os/tasks/TSK-001.md through TSK-010.md

# 3. Sync to API
cd .claude/skills/spec-driven-dev/scripts
python spec_cli.py sync push --project-id <your-project-id>

# 4. Tickets and tasks now exist in system
# 5. Go to /board/<project-id> and click "Start Processing"
```

### What the Skill Generates
- **Requirements** (EARS format): "WHEN user receives notification, THE SYSTEM SHALL display it within 5 seconds"
- **Designs**: Architecture, data models, API specs
- **Tickets**: Parent work items with acceptance criteria
- **Tasks**: Atomic units with dependencies

### MCP Tools Available
If MCP server is running, Claude can use:
```python
mcp__spec_workflow__create_spec(project_id, title, description)
mcp__spec_workflow__add_requirement(spec_id, title, condition, action)
mcp__spec_workflow__create_ticket(title, description, priority, phase_id, project_id)
mcp__spec_workflow__add_spec_task(spec_id, title, description, phase, priority)
```

---

## API Endpoints Reference

### Already Exist
```
POST /api/v1/tickets                            ← Create ticket
POST /api/v1/tickets/{id}/spawn-phase-tasks     ← Spawn tasks for ticket
GET  /api/v1/board/view?project_id={id}         ← Board columns + tickets
POST /api/v1/board/move                          ← Move ticket between columns
WS   /api/v1/ws/events                           ← Real-time event stream
GET  /api/v1/sandbox/{id}/events                 ← Sandbox event history
GET  /api/v1/tasks?ticket_id={id}               ← Tasks for a ticket
```

### May Need to Add
```
POST /api/v1/board/{project_id}/start-processing  ← Batch spawn all backlog tickets
GET  /api/v1/board/{project_id}/progress          ← Overall completion stats
```

---

## Event Types to Handle

From WebSocket, filter for these:

| Event | Action |
|-------|--------|
| `ticket.created` | Add new card to Backlog column |
| `task.created` | Increment task count on ticket card |
| `task.status_changed` | Update task status badge |
| `task.completed` | Check if all tasks done, show checkmark |
| `ticket.status_changed` | Move card to new column |
| `ticket.phase_advanced` | Move card, spawn next phase tasks |
| `sandbox.spawned` | Show "Agent running" indicator |
| `sandbox.completed` | Show completion state |

---

## UI Mockup (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Demo Board                         [+ New Ticket] [Start Processing] [⚙️] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │   BACKLOG    │ │ IN PROGRESS  │ │    REVIEW    │ │     DONE     │       │
│  │      3       │ │      2       │ │      0       │ │      1       │       │
│  │              │ │              │ │              │ │              │       │
│  │ ┌──────────┐ │ │ ┌──────────┐ │ │              │ │ ┌──────────┐ │       │
│  │ │ Ticket 1 │ │ │ │ Ticket 3 │ │ │              │ │ │ Ticket 5 │ │       │
│  │ │ 3 tasks  │ │ │ │ ●Running │ │ │              │ │ │ ✓ Done   │ │       │
│  │ │ ○○○      │ │ │ │ ●●○      │ │ │              │ │ │ PR #42   │ │       │
│  │ └──────────┘ │ │ └──────────┘ │ │              │ │ └──────────┘ │       │
│  │              │ │              │ │              │ │              │       │
│  │ ┌──────────┐ │ │ ┌──────────┐ │ │              │ │              │       │
│  │ │ Ticket 2 │ │ │ │ Ticket 4 │ │ │              │ │              │       │
│  │ │ Pending  │ │ │ │ 2/4 done │ │ │              │ │              │       │
│  │ └──────────┘ │ │ └──────────┘ │ │              │ │              │       │
│  │              │ │              │ │              │ │              │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Agent Output (Ticket 3 - implement_auth)                          [Close] │
│  ─────────────────────────────────────────────────────────────────────────  │
│  │ 🤖 Reading src/auth/middleware.ts...                                    │
│  │ 📝 Editing file: +15 -3 lines                                           │
│  │ 🔧 Running: npm test                                                    │
│  │ ✅ All tests passed                                                     │
│  │ 📤 Creating PR: "Add JWT middleware"                                    │
│  │ █                                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Demo Script (What to Show)

### Act 1: Create Work Items (2 min)
1. Open Command Center (`/command`)
2. Type: "Build a user notification system with email and in-app alerts"
3. Select "Spec-Driven" mode
4. Click "Create Spec"
5. Show spec being generated (or use pre-seeded data)
6. Navigate to Board

### Act 2: Start Processing (1 min)
1. Show board with tickets in Backlog
2. Click "Start Processing"
3. Toast: "Spawned 8 tasks across 3 tickets"
4. Cards start showing "Spawning..." status

### Act 3: Watch Agents Work (3-5 min)
1. Cards update to "Running" with animated indicator
2. Click a running card → Agent panel opens
3. Watch agent:
   - Read files
   - Make edits (show diff)
   - Run tests
   - Create PR
4. Task completes → Card updates
5. Show parallel execution (multiple cards running)

### Act 4: Completion (1 min)
1. All cards move to "Done"
2. Show PR links on completed cards
3. Click through to see generated PR

**Total demo time: ~7-10 minutes**

---

## Success Criteria

A successful demo shows:
1. ✅ Create tickets (via command center or spec skill)
2. ✅ See tickets appear on board in real-time
3. ✅ Click "Start" → Tasks spawn (toasts confirm)
4. ✅ Cards show "Running" indicator within seconds
5. ✅ Click card → See live agent output
6. ✅ Watch agent read files, make edits, run tests
7. ✅ Card moves to next column when phase completes
8. ✅ Multiple cards processing in parallel
9. ✅ Final state: All cards in "Done" with PR links

---

## Execution Order (Monday Plan)

### Morning Session (3 hours)
```
9:00  - Phase 1: Add Start Processing button (30 min)
9:30  - Phase 2: Real-time board updates (45 min)
10:15 - Break
10:30 - Phase 3: Agent panel integration (1 hour)
11:30 - Testing + fixes (30 min)
```

### Afternoon Session (2 hours)
```
1:00  - Phase 4: Ticket creation flow (30 min)
1:30  - Phase 6: Demo data + polish (30 min)
2:00  - Full demo run-through
2:30  - Record demo video or prepare live demo
```

---

## Files Summary

**Modify:**
- `/app/(app)/board/[projectId]/page.tsx` - Add start button, event subscription, agent panel
- `/hooks/useBoard.ts` - Add real-time handlers
- `/lib/api/tickets.ts` - Add spawnPhaseTasks function

**Create:**
- `/components/board/AgentPanel.tsx` - Embedded sandbox viewer
- `/lib/api/board.ts` - Add batch processing endpoint call (if needed)

**Backend (if needed):**
- `/api/routes/board.py` - Add batch start endpoint

**Use Existing:**
- `.claude/skills/spec-driven-dev/` - For generating demo data
- `spec_cli.py` - For syncing specs to API

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Orchestrator not running | Add health check indicator on board |
| WebSocket disconnects | Already has auto-reconnect |
| Tasks fail | Show error state on card, allow retry |
| Too many parallel tasks | Respect existing concurrency limits (5/project) |
| Slow sandbox spawn | Show "Provisioning..." state |
| Demo data not ready | Pre-seed via spec_cli.py before demo |
