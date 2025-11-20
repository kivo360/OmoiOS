# Tickets vs Tasks: Understanding the Hierarchy

**Created**: 2025-11-20
**Status**: Active
**Purpose**: Explain the hierarchical relationship and key differences between tickets (high‑level work items) and tasks (atomic work units) in the system.
**Related**: docs/workflows/ticket_lifecycle.md, docs/agents/task_execution.md, docs/architecture/adr_ticket_task_hierarchy.md, docs/design/services/task_queue.md

---


## Quick Summary

**Ticket** = High-level work item / Feature request  
**Task** = Single work unit assigned to an agent

**Relationship**: One Ticket → Many Tasks (1:N)

---

## Ticket (High-Level Work Item)

### Purpose
A **Ticket** represents a complete feature, bug fix, or work request that needs to be accomplished. It's the top-level unit of work that gets broken down into smaller, actionable pieces.

### Characteristics
- **Scope**: Broad, feature-level work
- **Example**: "Implement Authentication System"
- **Lifecycle**: Goes through phases (backlog → requirements → implementation → testing → done)
- **Status**: `backlog`, `analyzing`, `building`, `building-done`, `testing`, `done`
- **Can be blocked**: Has `is_blocked`, `blocked_reason`, `blocked_at` fields
- **Approval workflow**: Can require human approval before work starts
- **Not directly assigned**: Tickets don't get assigned to agents directly

### Key Fields
```python
Ticket:
    id: str
    title: str                    # "Implement Authentication System"
    description: str              # High-level description
    phase_id: str                 # PHASE_IMPLEMENTATION
    status: str                   # backlog, analyzing, building, etc.
    priority: str                 # CRITICAL, HIGH, MEDIUM, LOW
    is_blocked: bool              # Blocking overlay
    approval_status: str          # pending_review, approved, rejected
    context: dict                 # Accumulated context across phases
```

### What Happens When You Create a Ticket?
1. Ticket is created with status `backlog`
2. If approval is enabled, ticket goes to `pending_review`
3. Once approved, an initial task is automatically created (e.g., `analyze_requirements`)
4. As work progresses, more tasks are created and assigned to agents

---

## Task (Work Unit for Agents)

### Purpose
A **Task** represents a single, concrete piece of work that can be assigned to an agent and executed. Tasks are the atomic units that agents actually work on.

### Characteristics
- **Scope**: Narrow, specific work unit
- **Example**: "Design authentication architecture", "Implement JWT token generation"
- **Lifecycle**: Goes through execution states (pending → assigned → running → completed/failed)
- **Status**: `pending`, `assigned`, `running`, `completed`, `failed`
- **Directly assigned**: Tasks get assigned to specific agents
- **Has conversation**: Each task has a `conversation_id` (OpenHands conversation)
- **Can have dependencies**: Tasks can depend on other tasks completing first
- **Can have sub-tasks**: Tasks can have parent-child relationships

### Key Fields
```python
Task:
    id: str
    ticket_id: str                # Foreign key to parent ticket
    task_type: str               # analyze_requirements, implement_feature, etc.
    description: str              # Specific task description
    phase_id: str                # PHASE_IMPLEMENTATION
    priority: str                 # CRITICAL, HIGH, MEDIUM, LOW
    status: str                  # pending, assigned, running, completed, failed
    assigned_agent_id: str       # Which agent is working on this
    conversation_id: str         # OpenHands conversation ID
    dependencies: dict           # {"depends_on": ["task_id_1", "task_id_2"]}
    parent_task_id: str          # For sub-tasks
    result: dict                 # Task output/result
    error_message: str          # If task failed
```

### What Happens When a Task is Created?
1. Task is created with status `pending`
2. Task queue service evaluates it (dependencies, capabilities, priority)
3. Task gets assigned to an available agent
4. Agent executes the task using OpenHands SDK
5. Task status updates: `pending` → `assigned` → `running` → `completed`/`failed`
6. Results are stored in `task.result`

---

## Relationship Diagram

```
Ticket: "Implement Authentication System"
│
├─ Task 1: "Design authentication architecture" (completed)
│   └─ Conversation ID: conv-123
│   └─ Assigned to: agent-456
│
├─ Task 2: "Implement JWT token generation" (running)
│   └─ Depends on: Task 1
│   └─ Conversation ID: conv-789
│   └─ Assigned to: agent-456
│
├─ Task 3: "Implement OAuth2 provider" (pending)
│   └─ Depends on: Task 1
│   └─ Not yet assigned
│
└─ Task 4: "Write integration tests" (pending)
    └─ Depends on: Task 2, Task 3
    └─ Not yet assigned
```

---

## Key Differences

| Aspect | Ticket | Task |
|--------|--------|------|
| **Level** | High-level feature/work item | Low-level work unit |
| **Scope** | Broad (entire feature) | Narrow (specific action) |
| **Assignment** | Not assigned to agents | Assigned to specific agents |
| **Execution** | Not directly executed | Executed by agents |
| **Conversation** | No conversation | Has OpenHands conversation |
| **Dependencies** | Can be blocked by other tickets | Can depend on other tasks |
| **Status** | Workflow phases (backlog, building, etc.) | Execution states (pending, running, completed) |
| **Quantity** | One ticket | Many tasks per ticket |
| **Lifecycle** | Long-lived (days/weeks) | Short-lived (hours) |

---

## Real-World Analogy

Think of it like a construction project:

- **Ticket** = "Build a house" (the overall project)
  - Has phases: Planning → Foundation → Framing → Electrical → Plumbing → Finishing
  - Can be blocked: "Waiting for permits"
  - Needs approval: "Client approved the design"

- **Task** = "Install electrical wiring in kitchen" (specific work)
  - Assigned to: Electrician Agent #3
  - Depends on: "Complete kitchen framing" task
  - Status: Running
  - Result: "Wiring installed, tested, passed inspection"

---

## How They Work Together

### 1. Ticket Creation Flow
```
User creates ticket "Implement Auth System"
    ↓
Ticket created (status: backlog)
    ↓
If approved → Initial task created: "Analyze requirements"
    ↓
Task gets assigned to agent
    ↓
Agent executes task
    ↓
More tasks created based on analysis
```

### 2. Task Dependency Flow
```
Ticket: "Implement Auth System"
    ↓
Task 1: "Design architecture" (no dependencies)
    ↓ (completes)
Task 2: "Implement JWT" (depends on Task 1) ← Can now start
Task 3: "Implement OAuth2" (depends on Task 1) ← Can now start
    ↓ (both complete)
Task 4: "Write tests" (depends on Task 2, Task 3) ← Can now start
```

### 3. Discovery Flow (Hephaestus Pattern)
```
Task: "Implement JWT"
    ↓ (agent discovers issue)
Discovery: "Need refresh token mechanism"
    ↓
New Task spawned: "Implement refresh tokens"
    ↓
Task depends on original JWT task
```

---

## In the Dependency Graph

When visualizing dependencies:

- **Ticket nodes**: Top-level containers
- **Task nodes**: Individual work units
- **Edges**: 
  - `ticket_contains` → Ticket → Task (ownership)
  - `depends_on` → Task → Task (dependencies)
  - `spawned_from` → Discovery → Task (workflow branching)
  - `parent_child` → Task → Task (sub-tasks)

---

## Summary

**Tickets** are the "what" (what feature/work needs to be done)  
**Tasks** are the "how" (how it gets done, step by step)

**Tickets** organize work at a high level  
**Tasks** are what agents actually execute

**One ticket** breaks down into **many tasks** that agents work on in parallel or sequence, depending on dependencies.

