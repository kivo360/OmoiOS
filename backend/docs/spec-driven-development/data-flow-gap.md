# Data Flow Gap - SpecTask to Ticket Conversion

**Created**: 2025-01-11
**Updated**: 2025-01-11
**Status**: ~~CRITICAL GAP~~ → WIRING ISSUE (Bridge exists!)
**Purpose**: Document the missing link between SpecTask and Ticket entities

---

## 🎉 UPDATE: THE BRIDGE EXISTS!

See `omoi_os/services/spec_task_execution.py` - `SpecTaskExecutionService`

The bridge is fully implemented:
- `POST /api/v1/specs/{spec_id}/execute-tasks` endpoint
- Creates bridging Ticket for Spec
- Converts SpecTask → Task
- Completion events update SpecTask status

**THE PROBLEM**: State machine doesn't call it! SYNC phase creates SpecTask records, then COMPLETE marks the spec done without executing anything.

See [impact-assessment.md](./impact-assessment.md) for full analysis.

---

## The Correct Flow (What Should Happen)

```
User Idea (Command Page)
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                          SPEC                                │
├─────────────────────────────────────────────────────────────┤
│  EXPLORE → REQUIREMENTS → DESIGN → TASKS                     │
│                                      │                       │
│                                      ▼                       │
│                              SpecTask records                │
│                              (planning artifacts)            │
└─────────────────────────────────────────────────────────────┘
                               │
                               │ CONVERSION STEP (MISSING!)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                        TICKETS                               │
├─────────────────────────────────────────────────────────────┤
│  Each SpecTask → Ticket (appears on kanban board)           │
│  Each Ticket → Task (assigned to agent for execution)       │
│                                                              │
│  Tickets work through phases:                                │
│    backlog → analyzing → building → testing → done          │
└─────────────────────────────────────────────────────────────┘
                               │
                               │ Agents execute tasks
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       FINAL SYNC                             │
├─────────────────────────────────────────────────────────────┤
│  Update spec status based on ticket completion               │
│  Mark spec as "completed" when all tickets done              │
└─────────────────────────────────────────────────────────────┘
```

---

## Current State (What Actually Happens)

```
Spec State Machine
    │
    ▼
EXPLORE → REQUIREMENTS → DESIGN → TASKS
    │
    ▼
SYNC phase creates:
    - SpecRequirement records
    - SpecAcceptanceCriterion records
    - SpecTask records
    │
    ▼
COMPLETE phase marks spec as done
    │
    ▼
DEAD END - SpecTasks just sit there!
    - No Tickets created
    - Nothing on kanban board
    - No agents assigned to work
    - Requirements/Design documented but never executed
```

---

## Entity Relationships (Current)

```
┌─────────────────────────────────────────────────────────────┐
│                      SPEC DOMAIN                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Spec                                                       │
│     │                                                        │
│     ├── SpecRequirement                                      │
│     │       └── SpecAcceptanceCriterion                     │
│     │                                                        │
│     └── SpecTask (DEAD END - never converted to Tickets!)   │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    EXECUTION DOMAIN                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Ticket (NO link to Spec!)                                  │
│     │                                                        │
│     └── Task (execution unit assigned to agent)              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**The two domains are NOT connected!**

---

## What's Missing

### 1. SpecTask → Ticket Conversion

The SYNC phase should create Tickets from SpecTasks:

```python
# Pseudo-code for what should happen in SYNC phase
for spec_task in spec.tasks:
    # Create a Ticket for each SpecTask
    ticket = Ticket(
        title=spec_task.title,
        description=spec_task.description,
        priority=map_priority(spec_task.priority),
        phase_id="PHASE_IMPLEMENTATION",
        spec_id=spec.id,  # <-- Need this FK
        spec_task_id=spec_task.id,  # <-- Need this FK
    )

    # Also create the execution Task
    task = Task(
        ticket_id=ticket.id,
        title=spec_task.title,
        description=spec_task.description,
    )
```

### 2. Ticket.spec_id Foreign Key

Ticket model needs a `spec_id` field to link back to the originating spec:

```python
class Ticket(Base):
    # ... existing fields ...

    # NEW: Link to originating spec
    spec_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("specs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Originating spec ID (for spec-driven tickets)"
    )

    # NEW: Link to specific spec task
    spec_task_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("spec_tasks.id", ondelete="SET NULL"),
        nullable=True,
        comment="Originating spec task ID"
    )
```

### 3. Final Sync (Spec Completion)

When all tickets for a spec are completed, the spec should be marked complete:

```python
async def check_spec_completion(spec_id: str):
    """Check if all tickets for a spec are done."""
    tickets = await get_tickets_by_spec_id(spec_id)

    if all(t.status == "done" for t in tickets):
        await update_spec_status(spec_id, "completed")
```

---

## Proposed Updated Flow

```
SPEC PHASES (Planning)
══════════════════════
    │
    │ 1. EXPLORE - Understand codebase
    │ 2. REQUIREMENTS - Define EARS requirements
    │ 3. DESIGN - Architecture, data model, API
    │ 4. TASKS - Break into discrete work items (SpecTask records)
    │
    ▼

TICKET CREATION (Conversion)
════════════════════════════
    │
    │ For each SpecTask:
    │   - Create Ticket with spec_id FK
    │   - Create Task with ticket_id FK
    │   - Ticket appears on kanban board
    │
    ▼

TICKET EXECUTION (Work)
═══════════════════════
    │
    │ Tickets flow through:
    │   backlog → analyzing → building → testing → done
    │
    │ For each ticket:
    │   - Agent picks up Task
    │   - Agent executes in sandbox
    │   - Agent marks Task/Ticket complete
    │
    ▼

SPEC COMPLETION (Final Sync)
════════════════════════════
    │
    │ When ALL tickets for spec are done:
    │   - Mark spec as "completed"
    │   - Update progress to 100%
    │   - Trigger completion notification
    │
    ▼

DONE
```

---

## Files to Modify

| File | Change |
|------|--------|
| `omoi_os/models/ticket.py` | Add `spec_id`, `spec_task_id` foreign keys |
| `omoi_os/services/spec_sync.py` | Add ticket creation logic to SYNC phase |
| `omoi_os/api/routes/tickets.py` | Add spec completion check when ticket marked done |
| `alembic/versions/xxx_add_spec_ticket_link.py` | Migration for new columns |

---

## Database Schema Changes

```sql
-- Add spec link to tickets
ALTER TABLE tickets
ADD COLUMN spec_id VARCHAR REFERENCES specs(id) ON DELETE SET NULL;

ALTER TABLE tickets
ADD COLUMN spec_task_id VARCHAR REFERENCES spec_tasks(id) ON DELETE SET NULL;

-- Index for efficient lookup
CREATE INDEX idx_tickets_spec_id ON tickets(spec_id) WHERE spec_id IS NOT NULL;
```

---

## Questions to Resolve

1. **One Ticket per SpecTask?** Or group related SpecTasks into one Ticket?

2. **Ticket Priority Mapping?** How to map SpecTask priority to Ticket priority?

3. **Dependency Handling?** If SpecTask A depends on SpecTask B, should Ticket A depend on Ticket B?

4. **Approval Gates?** Should tickets require approval before agents start work?

5. **What Phase?** Should all spec-generated tickets go to `PHASE_IMPLEMENTATION`?

---

## Summary

The current system has a fundamental disconnect:

- **Spec domain** (requirements, design, tasks) is complete
- **Execution domain** (tickets, agent tasks) is complete
- **The bridge between them does NOT exist!**

The SYNC phase creates `SpecTask` records but never converts them to `Ticket` records that agents can actually work on.
