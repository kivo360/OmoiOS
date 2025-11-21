# Workflow Interconnection Validation

**Created**: 2025-11-21
**Status**: Validation Document
**Purpose**: Validate that OmoiOS UI supports all Hephaestus workflow interconnection patterns
**Related**: [Mission Control Exploration](./mission_control_exploration.md), [Hephaestus Workflow Enhancements](../../implementation/workflows/hephaestus_workflow_enhancements.md)

---

## Overview

This document validates that our current UI design (traditional Linear-style) fully supports the **5 key interconnection patterns** from Hephaestus:

1. Ticket Threading Through Phases
2. Discovery Branching
3. Feedback Loops
4. Phase Jumping
5. Parallel Branching

---

## Validation Against Hephaestus Patterns

### Pattern 1: Ticket Threading Through Phases ✅

**Hephaestus Pattern:**
> Tickets move through Kanban columns as they progress through phases. All context (comments, commits, decisions) stays attached to the ticket.

**OmoiOS Implementation:**

**✅ Data Model:**
- `Ticket` model with `phase_id` field
- `TicketComment` for discussions
- `TicketCommit` for code changes
- `TicketHistory` for change tracking
- `blocked_by_ticket_ids` for dependencies

**✅ Backend Services:**
- `TicketWorkflowOrchestrator.transition_status()` moves tickets between phases
- `PHASE_TO_STATUS` and `STATUS_TO_PHASE` mappings
- Phase history tracking via `PhaseHistory` model

**✅ UI Components:**

**Kanban Board** (`/board/:projectId`):
```
┌──────────────────────────────────────────────────────────────┐
│ BACKLOG │ ANALYZING │ BUILDING │ TESTING │ DONE │ BLOCKED   │
├─────────┼───────────┼──────────┼─────────┼──────┼───────────┤
│         │ [Ticket]  │ [Ticket] │         │      │           │
│         │ Auth Sys  │ Pay API  │         │      │           │
│         │ Phase: P1 │ Phase: P2│         │      │           │
└──────────────────────────────────────────────────────────────┘
```

**Ticket Detail** (`/board/:projectId/:ticketId`):
- **Comments Tab**: Shows all discussions as ticket moves through phases
- **Commits Tab**: Shows all code changes linked to this ticket
- **Tasks Tab**: Shows all tasks associated with this ticket
- **Blocking Tab**: Shows what this ticket blocks and what blocks it

**Validation**: ✅ **Fully Supported** - Tickets thread through phases with all context preserved.

---

### Pattern 2: Discovery Branching ✅

**Hephaestus Pattern:**
> Phase 3 agent discovers optimization → Spawns Phase 1 investigation task → Investigation spawns Phase 2 implementation → New feature branch emerges. Original work continues in parallel.

**OmoiOS Implementation:**

**✅ Data Model:**
- `TaskDiscovery` model: Tracks `source_task_id`, `discovery_type`, `description`, `spawned_task_ids`
- `Task.parent_task_id`: Links spawned tasks to source

**✅ Backend Services:**
- `DiscoveryService.record_discovery_and_branch()`: Records discovery and spawns tasks in ANY phase
- Bypasses `allowed_transitions` restriction (explicitly documented in phase prompts)
- Discovery types: bug, optimization, clarification, security, performance, etc.

**✅ Phase Prompts** (`software_development.yaml`):
```yaml
phase_prompt: |
  IF you discover bugs:
    - Use discovery_service.record_discovery_and_branch() to spawn immediate fix task
    - Continue your implementation work (don't stop)
  
  IF requirements are unclear or missing:
    - JUMP BACK to Phase 1 for clarification:
      discovery_service.record_discovery_and_branch(
        discovery_type="clarification_needed",
        spawn_phase_id="PHASE_REQUIREMENTS",  # Phase jumping - bypasses allowed_transitions
      )
```

**✅ UI Components:**

**Dependency Graph** (`/graph/:projectId`):
```
┌──────────────────────────────────────────────────────────────┐
│  Phase 1    │    Phase 2    │    Phase 3                     │
│             │               │                                 │
│ [Analysis]  │  [Build API]  │  [Test API] ────┐              │
│      │      │      │        │      │          │              │
│      └──────┴──────┘        │      │          ↓              │
│                             │      │   [Discovery: Cache]    │
│                             │      │          │              │
│                             │      │          ↓              │
│                             │      │   Phase 1: Investigate  │
│                             │      │          │              │
│                             │      │          ↓              │
│                             │      │   Phase 2: Implement    │
└──────────────────────────────────────────────────────────────┘

Edge Types:
─── Normal flow (green)
··· Discovery branch (purple)
```

**Activity Timeline** (`/projects/:projectId/activity?filter=discoveries`):
```
Timeline Filter: [Discoveries]

● 10:45 AM - Discovery: Optimization Opportunity
  Agent: Worker-3 (Phase 3 Testing)
  Type: optimization
  Description: "Caching could improve API performance 40%"
  Spawned: 
    - Phase 1: Investigate Redis caching
    - Phase 2: Implement caching layer
  [View Discovery Details] [View Graph]

● 10:23 AM - Discovery: Bug Found
  Agent: Worker-2 (Phase 2 Implementation)
  Type: bug
  Description: "Auth token timeout not configurable"
  Spawned:
    - Phase 2: Add timeout configuration
  [View Discovery Details]
```

**Diagnostic Reasoning View** (`/diagnostic/ticket/:ticketId`):
Shows complete discovery chain with reasoning.

**Validation**: ✅ **Fully Supported** - Discovery branching tracked and visualized.

---

### Pattern 3: Feedback Loops ✅

**Hephaestus Pattern:**
> Phase 3 validation fails → Spawns Phase 2 fix task → Fix spawns Phase 3 revalidation → Loops until success.

**OmoiOS Implementation:**

**✅ Phase Prompts** (`software_development.yaml`):
```yaml
# PHASE_TESTING prompt:
phase_prompt: |
  STEP 3a: If ALL tests pass:
    - Resolve the ticket
  
  STEP 3b: If tests fail:
    - Add comment with failure details
    - Create Phase 2 bug-fix task:
      create_task({
          "description": "Phase 2: Fix bugs in [Component] - TICKET: ticket-xxx. [Specific failures]",
          "phase_id": "PHASE_IMPLEMENTATION",
          "ticket_id": "ticket-xxx"
      })
```

**✅ Backend Services:**
- `ValidationOrchestrator.give_review()`: Returns feedback to task
- `Task.validation_iteration`: Tracks iteration count
- `ValidationReview` model: Stores each review cycle

**✅ UI Components:**

**Task Detail - Validation Tab**:
```
┌──────────────────────────────────────────────────────────┐
│  Validation History                                      │
│  ──────────────────────────────────────────────────────  │
│  Iteration 1: FAILED                                     │
│  Feedback: "3 test cases failing - auth timeout issues"  │
│  Action: Spawned fix task (task-fix-001)               │
│                                                          │
│  Iteration 2: FAILED                                     │
│  Feedback: "2 test cases still failing - DB connection"  │
│  Action: Spawned fix task (task-fix-002)               │
│                                                          │
│  Iteration 3: PASSED ✓                                   │
│  Feedback: "All tests passing"                          │
│  Action: Marked as complete                             │
└──────────────────────────────────────────────────────────┘
```

**Dependency Graph** shows feedback loop:
```
[Build Auth] ──→ [Test Auth] ──→ [Fix Auth Bug] ──→ [Retest Auth] ──→ ✓
                     │                  │                  │
                     └──────────────────┴──────────────────┘
                            Feedback Loop (3 iterations)
```

**Validation**: ✅ **Fully Supported** - Feedback loops tracked with iteration counts and visible in UI.

---

### Pattern 4: Phase Jumping ✅

**Hephaestus Pattern:**
> Phase 2 implementation discovers missing requirements → Spawns Phase 1 clarification task → Original task marked as blocked → Clarification completes → Implementation resumes.

**OmoiOS Implementation:**

**✅ Phase Prompts** (`software_development.yaml`):
```yaml
# PHASE_IMPLEMENTATION prompt:
phase_prompt: |
  IF requirements are unclear or missing:
    - JUMP BACK to Phase 1 for clarification:
      discovery_service.record_discovery_and_branch(
        discovery_type="clarification_needed",
        spawn_phase_id="PHASE_REQUIREMENTS",  # Phase jumping
        spawn_description="Clarify [What's unclear] - TICKET: ticket-xxx"
      )
    - Mark your task as blocked until clarification received
      update_task_status(task_id="current-task", status="blocked", 
                         error_message="Waiting for requirements clarification")
```

**✅ Backend Services:**
- `DiscoveryService` allows spawning in ANY phase (bypasses `allowed_transitions`)
- Task status can be `blocked` with reason
- Ticket can be moved back to earlier phases

**✅ UI Components:**

**Task Detail - Blocking Status**:
```
┌──────────────────────────────────────────────────────────┐
│  Task: Implement Payment API                            │
│  Status: ⚠ BLOCKED                                      │
│  ──────────────────────────────────────────────────────  │
│  Reason: Waiting for requirements clarification         │
│  Blocked since: 10:23 AM (15m ago)                      │
│                                                          │
│  Blocking Task:                                          │
│  → Phase 1: Clarify payment provider requirements       │
│    Status: In Progress                                   │
│    ETA: 20m                                              │
│                                                          │
│  [View Blocking Task] [Unblock]                         │
└──────────────────────────────────────────────────────────┘
```

**Dependency Graph** shows phase jump:
```
Phase 2: Build Payment
       │
       │ discovers missing requirements
       ↓
Phase 1: Clarify Requirements  ← Phase Jump
       │
       │ clarification complete
       ↓
Phase 2: Resume Build Payment
       │
       ↓
Phase 3: Test Payment
```

**Validation**: ✅ **Fully Supported** - Phase jumping enabled via discovery service, visualized in graph.

---

### Pattern 5: Parallel Branching ✅

**Hephaestus Pattern:**
> Phase 1 identifies 5 components → Spawns 5 Phase 2 tasks in parallel → Each Phase 2 task spawns its own Phase 3 validation → All run in parallel.

**OmoiOS Implementation:**

**✅ Phase Prompts** (`software_development.yaml`):
```yaml
# PHASE_REQUIREMENTS prompt:
phase_prompt: |
  For each component you identify:
    1. Search for existing tickets first (avoid duplicates!)
       search_tickets(query="component name", search_type="hybrid")
    
    2. Create ticket with dependencies:
       create_ticket({
           "title": "Build [Component]",
           "ticket_type": "component",
           "blocked_by_ticket_ids": [infrastructure_ticket_id]
       })
    
    3. Create Phase 2 task linking to the ticket:
       create_task({
           "description": "Phase 2: Build [Component] - TICKET: ticket-xxx",
           "phase_id": "PHASE_IMPLEMENTATION",
           "ticket_id": "ticket-xxx"
       })
```

**✅ Backend Services:**
- `TaskQueueService.get_next_task()`: Returns tasks by phase for parallel assignment
- Multiple agents can work on tasks in same phase simultaneously
- Blocking relationships prevent parallel work on dependent components

**✅ UI Components:**

**Phase Overview Dashboard** (`/projects/:projectId/phases`):
```
┌──────────────────────────────────────────────────────────────┐
│  PHASE_REQUIREMENTS                                         │
│  Tasks: 1 total, 1 done, 0 active                           │
│  Discovered: 5 components → Spawned 5 Phase 2 tasks         │
│  [View Tasks]                                                │
├──────────────────────────────────────────────────────────────┤
│  PHASE_IMPLEMENTATION                                        │
│  Tasks: 28 total, 22 done, 5 active  ← 5 tasks in parallel  │
│  Agents: 5 active (Worker-1, Worker-2, ...)                 │
│  [View Tasks]                                                │
├──────────────────────────────────────────────────────────────┤
│  PHASE_TESTING                                               │
│  Tasks: 23 total, 20 done, 3 active  ← Validating in parallel│
│  Agents: 3 active (Validator-1, Validator-2, ...)           │
│  [View Tasks]                                                │
└──────────────────────────────────────────────────────────────┘
```

**Dependency Graph** shows parallel branches:
```
                 Phase 1: Analyze PRD
                          │
           ┌──────────────┼──────────────┐
           │              │              │
    Phase 2: Auth   Phase 2: API   Phase 2: Frontend
           │              │              │
    Phase 3: Test   Phase 3: Test  Phase 3: Test
```

**Agent Status Panel** (future enhancement):
Shows all 5 agents working in parallel:
```
AGENTS (5 active)
● Worker-1  [████░] Auth     15m
● Worker-2  [███░░] API      32m
● Worker-3  [██░░░] Frontend 45m
● Worker-4  [█░░░░] Database 1h
● Worker-5  [████░] Workers  20m
```

**Validation**: ✅ **Fully Supported** - Parallel branching visible in phase dashboard and graph.

---

## UI Coverage Analysis

### What We Already Show (Current Design)

#### 1. Kanban Board (`/board/:projectId`)
**Shows:**
- ✅ Tickets moving through phases (columns)
- ✅ Phase badges on tickets
- ✅ Blocking relationships (blocked indicator)
- ✅ Real-time updates (WebSocket)

**Interconnection Support:**
- ✅ Ticket threading visible (ticket moves through columns)
- ✅ Blocking relationships visible (blocked badge)

---

#### 2. Dependency Graph (`/graph/:projectId`)
**Shows:**
- ✅ Task nodes with phase badges
- ✅ Dependency edges (what blocks what)
- ✅ Discovery nodes and edges
- ✅ Parent-child relationships

**Edge Types:**
- `depends_on`: Blue solid line (task dependencies)
- `spawned_from`: Purple dotted line (discovery branches)
- `parent_child`: Purple solid line (sub-tasks)

**Interconnection Support:**
- ✅ Discovery branching visible (purple edges from discovery nodes)
- ✅ Feedback loops visible (edges back to earlier phases)
- ✅ Phase jumping visible (edges from Phase 3 → Phase 1)
- ✅ Parallel branching visible (multiple edges from one node)

---

#### 3. Activity Timeline (`/projects/:projectId/activity`)
**Shows:**
- ✅ Discovery events (with type, description)
- ✅ Phase transitions
- ✅ Task spawning events
- ✅ Ticket creation/linking

**Filter Option:**
- `/projects/:projectId/activity?filter=discoveries` - Show only discovery events

**Interconnection Support:**
- ✅ Discovery branching visible (chronological feed)
- ✅ Phase jumping visible (Phase X → Phase Y events)

---

#### 4. Ticket Detail - Reasoning Tab (`/board/:projectId/:ticketId`)
**Shows:**
- ✅ Discovery events related to this ticket
- ✅ Task spawning reasoning
- ✅ Ticket linking reasoning

**Interconnection Support:**
- ✅ Shows WHY tasks were created
- ✅ Shows WHY tickets are connected
- ✅ Shows discovery chain

---

#### 5. Phase Overview Dashboard (`/projects/:projectId/phases`)
**Shows:**
- ✅ All phases with task counts
- ✅ Active agents per phase
- ✅ Discovery indicators ("3 new branches spawned")

**Interconnection Support:**
- ✅ Shows parallel work (tasks count per phase)
- ✅ Shows discovery activity (branch count)

---

#### 6. Task Phase Management (`/projects/:projectId/tasks/phases`)
**Shows:**
- ✅ Tasks organized by phase (expandable sections)
- ✅ Phase badges on tasks
- ✅ Move task to phase action

**Interconnection Support:**
- ✅ Shows which phase each task belongs to
- ✅ Allows manual phase transitions (with reason)

---

#### 7. Diagnostic Reasoning View (`/diagnostic/ticket/:ticketId`)
**Shows:**
- ✅ Complete reasoning chain
- ✅ Discovery timeline
- ✅ Ticket linking reasoning
- ✅ Task spawning reasoning

**Interconnection Support:**
- ✅ Full diagnostic of all interconnections
- ✅ Shows WHY workflows branched
- ✅ Shows evidence and agent decisions

---

## Enhanced Components for V1

### Quick Win 1: Add Discovery Indicators to Cards

**Current Card:**
```
┌─────────────────────────────┐
│ Auth System Implementation  │
│ Status: Building            │
│ Progress: ████████░░ 65%    │
│ [View Details]              │
└─────────────────────────────┘
```

**Enhanced Card (V1.5):**
```
┌──────────────────────────────────────┐
│ Auth System Implementation           │
│ Status: Building | Phase: P2         │
│ Progress: ████████░░ 65% (13/20)     │
│ ────────────────────────────────────  │
│ Last: PR #234 opened • 5m ago        │
│ Next: Integration tests (est. 15m)   │
│ Discoveries: 2 (1 bug, 1 optimization│ ← NEW
│ ────────────────────────────────────  │
│ [Details] [Discoveries] [Graph]      │
└──────────────────────────────────────┘
```

**Click "Discoveries"** → Navigate to activity timeline filtered by this ticket's discoveries.

---

### Quick Win 2: Add Phase Flow Indicator

**On Ticket Detail:**
```
┌──────────────────────────────────────────────────────────┐
│  Ticket: Build Authentication System                    │
│  ──────────────────────────────────────────────────────  │
│  Phase Flow:                                             │
│  [✓ P1 Requirements] → [● P2 Implementation] → [ P3 Testing]│
│                             Current Phase                 │
│                                                          │
│  Spawned Tasks:                                          │
│  • Phase 1: Clarify session timeout (discovery)         │
│  • Phase 2: Fix auth bug (discovery)                    │
│  • Phase 3: Validate auth flow (next step)              │
└──────────────────────────────────────────────────────────┘
```

Shows:
- ✅ Which phases this ticket has gone through
- ✅ Which phase it's currently in
- ✅ What tasks were spawned via discovery
- ✅ What the next phase will be

---

### Quick Win 3: Enhanced Graph with Phase Columns

**Current Graph**: Nodes float freely.

**Enhanced Graph (V1.5)**: Organize by phase columns (like Hephaestus screenshot):
```
┌──────────────────────────────────────────────────────────────┐
│  Phase 1        │    Phase 2         │    Phase 3           │
│  Requirements   │    Implementation  │    Validation        │
│  ──────────────────────────────────────────────────────────  │
│                 │                    │                       │
│  [Analyze PRD]  │  [Build Auth]      │  [Test Auth]         │
│       │         │      │             │      │               │
│       │         │      │             │      ├─→ [Discover]  │
│       │         │      │             │      │   Bug Found   │
│       │         │      │  ┌──────────┘      │               │
│       │         │  ┌───┴──┘                 │               │
│       │         │  │                        │               │
│       │         │  [Fix Bug]                │  [Retest]     │
│       │         │      │                    │      │        │
│       │         │      └────────────────────┴──────┘        │
│                 │                                            │
└──────────────────────────────────────────────────────────────┘
```

**Visually Shows:**
- ✅ Phase progression (left to right)
- ✅ Discovery branches (diagonal edges)
- ✅ Feedback loops (edges going backward)
- ✅ Phase jumping (edges skipping phases)

---

### Quick Win 4: Discovery Event Notifications

**When Agent Discovers Something:**
```
┌──────────────────────────────────────────┐
│ 🔍 New Discovery                         │
│ ──────────────────────────────────────   │
│ Agent: Worker-3                          │
│ Type: Optimization Opportunity           │
│ Description: "Caching could improve      │
│ API performance by 40%"                  │
│                                          │
│ Spawned: 2 new tasks                     │
│ • Phase 1: Investigate caching           │
│ • Phase 2: Implement Redis cache         │
│                                          │
│ [View Discovery] [View Graph] [Dismiss]  │
└──────────────────────────────────────────┘
```

**Benefits:**
- Users see discoveries as they happen
- Understand why workflows branch
- Can review discovery reasoning inline

---

## What We're Missing (And Should Add)

### Missing 1: Discovery Counter on Workflow Cards

**Current**: No discovery indication on cards.

**Add:**
```
Discoveries: 3 (2 bugs, 1 optimization)
```

**Effort**: Low (query TaskDiscovery count by ticket_id).

---

### Missing 2: Phase Column Layout for Graph

**Current**: Nodes float freely (force-directed layout).

**Add**: Option to organize by phase columns (like Hephaestus screenshot).

**Effort**: Medium (layout algorithm change).

---

### Missing 3: Inline Discovery Details on Graph Edges

**Current**: Click edge → Navigate to diagnostic view.

**Add**: Hover edge → Tooltip shows discovery reasoning inline.

**Effort**: Low (tooltip component with discovery data).

---

## Validation Summary

### ✅ All 5 Hephaestus Patterns Supported

| Pattern | Backend | UI Visualization | Data Model |
|---------|---------|------------------|------------|
| **Ticket Threading** | ✅ `TicketWorkflowOrchestrator` | ✅ Kanban Board, Ticket Detail | ✅ `Ticket`, `TicketHistory`, `TicketCommit` |
| **Discovery Branching** | ✅ `DiscoveryService` | ✅ Graph, Activity Timeline | ✅ `TaskDiscovery` |
| **Feedback Loops** | ✅ `ValidationOrchestrator` | ✅ Task Detail, Graph | ✅ `ValidationReview`, `Task.validation_iteration` |
| **Phase Jumping** | ✅ Discovery bypasses `allowed_transitions` | ✅ Graph, Diagnostic View | ✅ `TaskDiscovery.spawn_phase_id` |
| **Parallel Branching** | ✅ `TaskQueueService`, Multiple agents | ✅ Phase Overview, Graph | ✅ Multiple `Task` records per phase |

### ✅ All Key Hephaestus Features Present

| Feature | OmoiOS Implementation | UI Location |
|---------|----------------------|-------------|
| **Done Definitions** | ✅ `PhaseModel.done_definitions` | Phase Detail, Phase Gate Approvals |
| **Phase Prompts** | ✅ `PhaseModel.phase_prompt` | Phase Detail (editable) |
| **Expected Outputs** | ✅ `PhaseModel.expected_outputs` | Phase Detail, Phase Gate Validation |
| **Next Steps Guide** | ✅ `PhaseModel.next_steps_guide` | Phase Detail |
| **Discovery Types** | ✅ `TaskDiscovery.discovery_type` | Activity Timeline, Diagnostic View |
| **Ticket Kanban** | ✅ `BoardConfig`, `BoardColumn` | Kanban Board |
| **Memory System** | ✅ `TaskMemory`, `MemoryService` | Agent Detail, Activity Timeline |

---

## Recommended Quick Wins for V1

To make interconnections more visible without changing layout:

### 1. Enhanced Workflow Cards
Add to existing cards:
- Last action (PR #234 opened • 5m ago)
- Next action (Integration tests, est. 15m)
- Discovery count (Discoveries: 2)
- Budget burn ($3.20 / $5.00)

**Effort**: Low
**Value**: High - More info at a glance

---

### 2. Discovery Indicator Badge
Add badge to tickets that have discoveries:
```
┌─────────────────────────────┐
│ Auth System Implementation  │
│ Status: Building            │
│ Progress: 65%               │
│ 🔍 2 Discoveries             │ ← NEW
└─────────────────────────────┘
```

**Effort**: Low
**Value**: Medium - Shows workflow is branching

---

### 3. Phase Column Layout Option for Graph
Add layout toggle:
```
Graph Controls: [Force] [Hierarchical] [Phase Columns]
```

When "Phase Columns" selected, organize nodes by phase.

**Effort**: Medium
**Value**: High - Matches Hephaestus visualization style

---

### 4. Discovery Event Toasts
When agent makes discovery, show toast notification:
```
🔍 Discovery: Bug found by Worker-2
   Spawned: Phase 2 fix task
   [View Discovery]
```

**Effort**: Low
**Value**: Medium - Real-time awareness

---

### 5. Interconnection Summary Panel
Add to Project Overview:
```
┌──────────────────────────────────────┐
│  Workflow Interconnections           │
│  ──────────────────────────────────  │
│  Active Branches: 5                  │
│  Discoveries (24h): 8                │
│  Feedback Loops: 2 (1 resolved)      │
│  Phase Jumps: 3 (clarifications)     │
│  Parallel Tasks: 12                  │
│  [View Graph] [View Timeline]        │
└──────────────────────────────────────┘
```

**Effort**: Low
**Value**: High - Shows system is adaptive

---

## Validation Result: ✅ PASS

**Conclusion**: Our current UI design (traditional Linear-style) **already supports all 5 Hephaestus interconnection patterns**:

1. ✅ **Ticket Threading**: Kanban board, ticket detail tabs
2. ✅ **Discovery Branching**: Dependency graph, activity timeline, diagnostic view
3. ✅ **Feedback Loops**: Validation history, graph showing retry edges
4. ✅ **Phase Jumping**: Graph shows edges from later phases to earlier phases
5. ✅ **Parallel Branching**: Phase overview shows multiple tasks/agents per phase

**No major changes needed.** We can enhance visibility with:
- Discovery indicators on cards
- Phase column layout option for graph
- Discovery event notifications
- Interconnection summary panel

These are **additive enhancements** that increase density without changing the fundamental Linear-style layout.

---

## Recommendation

**Ship V1 with Current Design + Quick Wins:**
1. Keep current page flows (Kanban, Graph, Timeline, Phase Overview)
2. Add enhanced workflow cards (Last, Next, Discoveries, Budget)
3. Add discovery indicators and badges
4. Add phase column layout option to graph
5. Add interconnection summary to project overview

**This gives you:**
- ✅ Familiar, clean Linear-style UI
- ✅ Full support for Hephaestus interconnection patterns
- ✅ Progressive density enhancements
- ✅ Foundation for Mission Control mode (V2+)

**You don't need to choose between Traditional and Mission Control—your current design already supports the workflow patterns. Mission Control is just a denser presentation of the same data.**

