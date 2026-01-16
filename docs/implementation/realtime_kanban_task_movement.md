# Real-Time Kanban Board Task Movement

**Created**: 2025-01-15
**Status**: Design/Investigation
**Purpose**: Document how tasks should move through Kanban columns in real-time

---

## Problem Statement

From the screenshot annotation:
> "As tasks are getting worked on they should move through these steps too. No idea how to do it within workers or reflect it on the UI real time."

Currently, tickets appear in Kanban columns based on their `phase_id`, but:
1. Workers don't update ticket/task phases during execution
2. Phase transitions aren't reflected in real-time on the UI
3. The progression (Backlog → Analyzing → Building → Testing → Deploying → Done) isn't automatic

---

## Current Architecture

### Kanban Column Structure

Based on the screenshot, the board has these columns:
- **Backlog** (0) - Initial state
- **Analyzing** (1/5) - Requirements analysis
- **Building** (1/10) - Implementation
- **Testing** (0/8) - Testing phase
- **Deploying** (0/3) - Deployment
- **Done** - Completed

### How Columns Currently Work

**File:** `frontend/app/(app)/board/[projectId]/page.tsx`

Tickets are grouped by `phase_id`:

```typescript
const columns = [
  { id: "PHASE_BACKLOG", title: "Backlog", icon: Inbox },
  { id: "PHASE_ANALYZING", title: "Analyzing", icon: Search },
  { id: "PHASE_BUILDING", title: "Building", icon: Wrench },
  { id: "PHASE_TESTING", title: "Testing", icon: TestTube },
  { id: "PHASE_DEPLOYING", title: "Deploying", icon: Rocket },
  { id: "PHASE_DONE", title: "Done", icon: CheckCircle },
]

// Tickets filtered by column
const ticketsInColumn = tickets.filter(t => t.phase_id === column.id)
```

### What's Missing

1. **Backend:** Workers don't update `ticket.phase_id` during execution
2. **Backend:** No logic maps task types/status to phases
3. **Frontend:** No WebSocket events for phase changes
4. **Frontend:** No automatic phase advancement

---

## Proposed Solution

### Phase Mapping Strategy

Map task execution stages to Kanban phases:

| Task Activity | Kanban Phase | Trigger Event |
|---------------|--------------|---------------|
| Ticket created | PHASE_BACKLOG | Initial state |
| Analysis task started | PHASE_ANALYZING | task.type = 'analyze_*' |
| Implementation task started | PHASE_BUILDING | task.type = 'implement_*' |
| Test task started | PHASE_TESTING | task.type = 'test_*' |
| Deploy task started | PHASE_DEPLOYING | task.type = 'deploy_*' |
| All tasks completed | PHASE_DONE | All tasks status='completed' |

### Backend Changes Required

#### 1. Add Phase Advancement Logic

**File:** `omoi_os/services/task_queue.py`

```python
async def advance_ticket_phase_if_needed(
    self,
    task: Task,
    new_status: str
) -> Optional[str]:
    """
    Advance the parent ticket's phase based on task activity.

    Returns the new phase_id if changed, None otherwise.
    """
    TASK_TYPE_TO_PHASE = {
        # Analysis tasks
        "analyze_codebase": "PHASE_ANALYZING",
        "analyze_requirements": "PHASE_ANALYZING",
        "create_spec": "PHASE_ANALYZING",
        "create_requirements": "PHASE_ANALYZING",

        # Building tasks
        "implement": "PHASE_BUILDING",
        "implement_feature": "PHASE_BUILDING",
        "create_component": "PHASE_BUILDING",
        "refactor": "PHASE_BUILDING",

        # Testing tasks
        "test": "PHASE_TESTING",
        "validate": "PHASE_TESTING",
        "review_code": "PHASE_TESTING",
        "run_tests": "PHASE_TESTING",

        # Deployment tasks
        "deploy": "PHASE_DEPLOYING",
        "create_pr": "PHASE_DEPLOYING",
        "merge_pr": "PHASE_DEPLOYING",
    }

    async with self.db.get_async_session() as session:
        ticket = await session.get(Ticket, task.ticket_id)
        if not ticket:
            return None

        # Get target phase for this task type
        target_phase = TASK_TYPE_TO_PHASE.get(task.task_type)
        if not target_phase:
            return None

        # Only advance if the target is "ahead" of current phase
        PHASE_ORDER = [
            "PHASE_BACKLOG",
            "PHASE_ANALYZING",
            "PHASE_BUILDING",
            "PHASE_TESTING",
            "PHASE_DEPLOYING",
            "PHASE_DONE"
        ]

        current_index = PHASE_ORDER.index(ticket.phase_id)
        target_index = PHASE_ORDER.index(target_phase)

        if target_index > current_index and new_status in ["running", "assigned"]:
            # Advance to new phase
            ticket.phase_id = target_phase
            ticket.updated_at = utc_now()
            await session.commit()

            # Publish phase change event
            self.event_bus.publish(SystemEvent(
                event_type="TICKET_PHASE_ADVANCED",
                entity_type="ticket",
                entity_id=str(ticket.id),
                payload={
                    "old_phase": PHASE_ORDER[current_index],
                    "new_phase": target_phase,
                    "triggered_by_task": str(task.id),
                }
            ))

            return target_phase

        # Check if ticket should move to DONE
        if new_status == "completed":
            # Check if ALL tasks for this ticket are completed
            result = await session.execute(
                select(Task).filter(
                    Task.ticket_id == ticket.id,
                    Task.status != "completed"
                )
            )
            incomplete_tasks = result.scalars().all()

            if len(incomplete_tasks) == 0:
                ticket.phase_id = "PHASE_DONE"
                ticket.status = "done"
                ticket.updated_at = utc_now()
                await session.commit()

                self.event_bus.publish(SystemEvent(
                    event_type="TICKET_COMPLETED",
                    entity_type="ticket",
                    entity_id=str(ticket.id),
                    payload={"final_phase": "PHASE_DONE"}
                ))

                return "PHASE_DONE"

        return None
```

#### 2. Call Phase Advancement in Task Status Updates

**File:** `omoi_os/services/task_queue.py`

In `update_task_status_async`:

```python
async def update_task_status_async(
    self,
    task_id: str,
    status: str,
    result: Optional[dict] = None,
    error_message: Optional[str] = None,
) -> Task:
    """Update task status and potentially advance ticket phase."""
    async with self.db.get_async_session() as session:
        task = await session.get(Task, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Update task status
        task.status = status
        if result:
            task.result = result
        if error_message:
            task.error_message = error_message
        task.updated_at = utc_now()

        if status == "completed":
            task.completed_at = utc_now()
        elif status in ["running", "assigned"]:
            task.started_at = task.started_at or utc_now()

        await session.commit()
        await session.refresh(task)

        # Check if ticket phase should advance
        await self.advance_ticket_phase_if_needed(task, status)

        # Publish task status event
        self.event_bus.publish(SystemEvent(
            event_type="TASK_STATUS_CHANGED",
            entity_type="task",
            entity_id=str(task.id),
            payload={
                "new_status": status,
                "ticket_id": str(task.ticket_id),
            }
        ))

        return task
```

### Frontend Changes Required

#### 1. Handle TICKET_PHASE_ADVANCED Event

**File:** `frontend/hooks/useBoardEvents.ts`

```typescript
case "TICKET_PHASE_ADVANCED":
  // Invalidate the specific ticket to get updated phase
  queryClient.invalidateQueries({
    queryKey: ["tickets", event.entity_id]
  })

  // Also invalidate board to re-render columns
  queryClient.invalidateQueries({ queryKey: ["board"] })

  // Show toast for visibility
  toast.info(`Ticket moved to ${event.payload.new_phase}`, {
    description: `Triggered by task execution`
  })
  break

case "TICKET_COMPLETED":
  queryClient.invalidateQueries({
    queryKey: ["tickets", event.entity_id]
  })
  queryClient.invalidateQueries({ queryKey: ["board"] })

  toast.success("Ticket completed!", {
    description: "All tasks finished successfully"
  })
  break
```

#### 2. Add Animation for Phase Transitions

**File:** `frontend/components/board/TicketCard.tsx`

```tsx
import { motion, AnimatePresence } from "framer-motion"

// Wrap ticket card in motion component
<AnimatePresence mode="popLayout">
  <motion.div
    key={ticket.id}
    layout
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, scale: 0.9 }}
    transition={{ duration: 0.2 }}
  >
    <TicketCardContent ticket={ticket} />
  </motion.div>
</AnimatePresence>
```

---

## Alternative: Task-Based Column Display

Instead of moving tickets between columns, show TASKS in columns based on their type/status:

### Pros
- More granular visibility
- Shows parallel work across phases
- Tickets can have tasks in multiple phases

### Cons
- More complex UI
- Different mental model
- May be overwhelming with many tasks

### Implementation

```typescript
// Group tasks by type/phase instead of tickets
const tasksInColumn = allTasks.filter(task => {
  const taskPhase = getPhaseForTaskType(task.task_type)
  return taskPhase === column.id
})

// Show mini-cards for tasks within each column
<Column>
  {tasksInColumn.map(task => (
    <TaskMiniCard
      key={task.id}
      task={task}
      parentTicket={tickets.find(t => t.id === task.ticket_id)}
    />
  ))}
</Column>
```

---

## Implementation Priority

### Phase 1: Backend Events (Required)
1. Add `advance_ticket_phase_if_needed()` method
2. Call it from `update_task_status_async()`
3. Publish `TICKET_PHASE_ADVANCED` events

### Phase 2: Frontend Real-Time Updates (Required)
1. Handle `TICKET_PHASE_ADVANCED` in WebSocket handler
2. Invalidate React Query cache for affected tickets
3. Add toast notifications

### Phase 3: Animations (Nice to Have)
1. Add Framer Motion for smooth transitions
2. Animate cards moving between columns
3. Add celebration effect when ticket reaches Done

### Phase 4: Task-Level View (Optional)
1. Add toggle to show tasks vs tickets
2. Implement task grouping by phase
3. Add task mini-cards

---

## Testing

### Test Cases

1. **Create task with type "analyze_requirements"**
   - Verify ticket moves to PHASE_ANALYZING
   - Verify WebSocket event received
   - Verify UI updates

2. **Complete all tasks on a ticket**
   - Verify ticket moves to PHASE_DONE
   - Verify ticket status changes to "done"

3. **Concurrent tasks in different phases**
   - Verify ticket advances to latest phase
   - Verify no regression to earlier phases

4. **WebSocket disconnection during transition**
   - Verify UI catches up on reconnect
   - Verify no lost phase changes

---

## Related Documentation

- [Autonomous Execution Feature](./autonomous_execution_feature.md)
- [Task Queue Service](../../backend/omoi_os/services/task_queue.py)
- [WebSocket Events](../../frontend/hooks/useBoardEvents.ts)
