# DAG System ↔ Orchestrator Worker Integration Gaps

**Created**: 2026-02-01  
**Status**: Critical - Integration Incomplete  
**Purpose**: Document ALL integration gaps between DAG/Merge system and Orchestrator Worker  
**Related**: `parallel_systems_analysis.md` (process-level conflicts)

---

## Executive Summary

The DAG merge system (convergence/synthesis/coordination) was **designed but not wired** to the Orchestrator Worker. This document identifies **7 critical gaps** that will prevent parallel task coordination from working.

**Bottom line**: If you run parallel tasks today, they will:
1. Execute independently ✅
2. NOT have their results merged ❌
3. NOT have their code merged ❌
4. Leave continuation tasks waiting forever ❌

---

## The DAG System Architecture (What Should Happen)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INTENDED DAG FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. SPLIT: Task A splits into parallel tasks B, C, D                        │
│     └─ CoordinationService.split_task() → creates tasks with depends_on A   │
│                                                                              │
│  2. EXECUTE: Tasks B, C, D run in parallel sandboxes                        │
│     └─ OrchestratorWorker spawns sandboxes via DaytonaSpawner               │
│                                                                              │
│  3. JOIN: When B, C, D complete, create continuation task E                 │
│     └─ CoordinationService.join_tasks() → publishes coordination.join.created│
│                                                                              │
│  4. SYNTHESIS: Merge task results (data) into E's context                   │
│     └─ SynthesisService listens for join, tracks completion                 │
│     └─ When all sources done: merge results → inject into E.synthesis_context│
│     └─ Publishes coordination.synthesis.completed                           │
│                                                                              │
│  5. MERGE: Merge git branches before E starts                               │
│     └─ ConvergenceMergeService listens for synthesis.completed              │
│     └─ Spawns MERGE SANDBOX → runs git merge operations                     │
│     └─ Resolves conflicts via LLM if needed                                 │
│                                                                              │
│  6. CONTINUE: Task E executes with merged context + merged code             │
│     └─ OrchestratorWorker spawns sandbox for E                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Critical Gap #1: CoordinationService Never Initialized

**Severity**: 🔴 CRITICAL  
**Impact**: NO coordination events are published. JOIN/SPLIT/SYNC never happen.

### Evidence

**Orchestrator Worker** (`orchestrator_worker.py` init_services):
```python
# Services initialized:
db = DatabaseService(...)
event_bus = EventBusService(...)
queue = TaskQueueService(...)
registry_service = AgentRegistryService(...)
phase_progression = get_phase_progression_service(...)
synthesis_service = SynthesisService(...)  # ✅ Initialized
synthesis_service.subscribe_to_events()     # ✅ Subscribes to events

# ❌ MISSING:
# coordination_service = CoordinationService(db, queue, event_bus)
```

### What This Breaks

- `coordination.join.created` events are NEVER published
- SynthesisService listens but receives nothing
- Tasks with `depends_on` multiple parents never get merged results
- The entire DAG coordination pattern is dead

### Fix Required

```python
# Add to orchestrator_worker.py init_services():
from omoi_os.services.coordination import CoordinationService

coordination_service = CoordinationService(
    db=db,
    queue=queue,
    event_bus=event_bus,
)
```

---

## Critical Gap #2: ConvergenceMergeService Never Initialized

**Severity**: 🔴 CRITICAL  
**Impact**: NO git merges happen at convergence points.

### Evidence

```python
# orchestrator_worker.py - ConvergenceMergeService is NEVER initialized
# The singleton getter get_convergence_merge_service() is NEVER called

# convergence_merge_service.py:676 - The getter exists but:
grep -r "get_convergence_merge_service" omoi_os/
# → Only found in: convergence_merge_service.py (definition), tests
```

### What This Breaks

- Parallel task branches are NEVER merged
- When synthesis completes, the event is published but no merger receives it
- Code from parallel tasks stays in separate branches forever
- Continuation tasks start with UNMERGED code → immediate conflicts

### Fix Required

```python
# Add to orchestrator_worker.py init_services():
from omoi_os.services.convergence_merge_service import (
    get_convergence_merge_service,
    ConvergenceMergeConfig,
)

convergence_merge_service = get_convergence_merge_service(
    db=db,
    event_bus=event_bus,
    config=ConvergenceMergeConfig(
        max_conflicts_auto_resolve=10,
        enable_auto_push=False,
    ),
)
convergence_merge_service.subscribe_to_events()
```

---

## Critical Gap #3: No Sandbox Spawned for Merge Operations

**Severity**: 🔴 CRITICAL  
**Impact**: Even if ConvergenceMergeService was initialized, merges can't execute.

### Evidence

The `merge_at_convergence` method REQUIRES an active sandbox:

```python
# convergence_merge_service.py:172-181
async def merge_at_convergence(
    self,
    continuation_task_id: str,
    source_task_ids: List[str],
    ticket_id: str,
    sandbox: "Sandbox",  # ← REQUIRED parameter
    ...
) -> ConvergenceMergeResult:
```

But the `_handle_synthesis_completed` event handler DOES NOT spawn a sandbox:

```python
# convergence_merge_service.py:138-170
def _handle_synthesis_completed(self, event_data: Dict[str, Any]) -> None:
    # ... extracts continuation_task_id, source_task_ids, ticket_id ...
    
    logger.info("synthesis_completed_triggering_merge", ...)
    
    # Note: The actual merge happens when the sandbox is spawned
    # This is because we need an active sandbox to run git commands
    # The merge_at_convergence method is called by DaytonaSpawner
    #                                          ^^^^^^^^^^^^^^^^
    # THIS IS A LIE - DaytonaSpawner NEVER calls merge_at_convergence
```

**DaytonaSpawner has NO merge code:**
```bash
grep -n "merge_at_convergence\|ConvergenceMerge" daytona_spawner.py
# → No matches found
```

### What This Breaks

- Synthesis completes (results merged) ✅
- But `coordination.synthesis.completed` event just logs and does nothing
- No sandbox is created for the merge operation
- Git branches are never actually merged
- Continuation task E starts with code from only ONE branch (whichever was last checked out)

### Fix Required

**Option A: Pre-merge before continuation task spawn**

Modify `orchestrator_worker.py` to check if task has synthesis_context and trigger merge:

```python
# In orchestrator_loop(), before spawning sandbox for a task:
async def spawn_task_sandbox(task):
    if task.synthesis_context and task.dependencies:
        # This task is a continuation - merge before spawn
        source_task_ids = task.dependencies.get("depends_on", [])
        if len(source_task_ids) > 1:
            # Create a temporary merge sandbox
            merge_sandbox = await daytona.create_sandbox_for_merge(
                task_id=task.id,
                ticket_id=task.ticket_id,
            )
            try:
                result = await convergence_merge.merge_at_convergence(
                    continuation_task_id=str(task.id),
                    source_task_ids=source_task_ids,
                    ticket_id=task.ticket_id,
                    sandbox=merge_sandbox,
                )
                if not result.success:
                    # Mark task as blocked, needs manual intervention
                    task.status = "blocked"
                    task.error = f"Merge failed: {result.error_message}"
                    return
            finally:
                await daytona.terminate_sandbox(merge_sandbox.id)
    
    # Proceed with normal task spawn
    await daytona.spawn_for_task(task_id=str(task.id), ...)
```

**Option B: In-task merge (merge happens inside continuation task's sandbox)**

Have the continuation task's sandbox run merge as first operation:
- Pros: Simpler, single sandbox
- Cons: Task execution is blocked by merge, harder to retry just the merge

---

## Critical Gap #4: Event Chain is Broken (Complete Failure Path)

**Severity**: 🔴 CRITICAL  
**Impact**: Even with all services initialized, the event flow doesn't work.

### The Broken Chain

```
1. Parallel tasks complete
   └─ TASK_COMPLETED published ✅

2. SynthesisService._handle_task_completed()
   └─ Marks source as complete ✅
   └─ Checks if all sources done ✅
   └─ IF ready: calls _trigger_synthesis() ✅

3. _trigger_synthesis()
   └─ Merges results ✅
   └─ Injects into task.synthesis_context ✅
   └─ Publishes coordination.synthesis.completed ✅

4. ConvergenceMergeService._handle_synthesis_completed()
   └─ Logs "triggering merge" ✅
   └─ DOES NOTHING ELSE ❌  ← BREAKS HERE
   └─ Comment says "merge happens when sandbox spawned" but:
      - DaytonaSpawner doesn't know about merges
      - OrchestratorWorker doesn't check synthesis_context before spawn

5. Continuation task picked up by orchestrator
   └─ Task has synthesis_context (results merged) ✅
   └─ But git branches NOT merged ❌
   └─ Sandbox spawned on wrong branch state ❌
   └─ Agent starts with broken/conflicting code ❌
```

### Fix Required

The event handler needs to actually trigger the merge, not just log:

```python
# convergence_merge_service.py - Replace _handle_synthesis_completed

async def _handle_synthesis_completed(self, event_data: Dict[str, Any]) -> None:
    """Handle synthesis completion by triggering merge."""
    payload = event_data.get("payload", {})
    continuation_task_id = payload.get("continuation_task_id")
    source_task_ids = payload.get("source_task_ids", [])
    ticket_id = payload.get("ticket_id")

    if not continuation_task_id or not source_task_ids:
        return

    # Create a dedicated merge sandbox
    merge_sandbox = await self._create_merge_sandbox(ticket_id)
    
    try:
        result = await self.merge_at_convergence(
            continuation_task_id=continuation_task_id,
            source_task_ids=source_task_ids,
            ticket_id=ticket_id,
            sandbox=merge_sandbox,
        )
        
        if result.success:
            # Mark continuation task as ready for execution
            self._mark_task_ready_for_spawn(continuation_task_id)
        else:
            # Mark task as blocked
            self._mark_task_merge_failed(continuation_task_id, result.error_message)
            
    finally:
        await self._terminate_merge_sandbox(merge_sandbox)
```

---

## Critical Gap #5: JOIN Registration Never Happens Outside Spec Flow

**Severity**: 🟡 HIGH  
**Impact**: Non-spec tasks with parallel dependencies never get coordinated.

### Evidence

`CoordinationService.join_tasks()` and `register_join()` create JOIN events.

**Where they're called:**
```bash
grep -rn "join_tasks\|register_join" omoi_os/
# → Only in:
#   - coordination.py (definitions)
#   - spec_task_execution.py (spec-only flow)
#   - tests
```

`SpecTaskExecutionService` calls `register_join()` when converting spec tasks:
```python
# spec_task_execution.py - When creating tasks from specs with dependencies
coordination.register_join(
    join_id=f"join-{task.id}",
    source_task_ids=dependency_task_ids,
    continuation_task_id=str(task.id),
)
```

But regular tasks created via API or discovery DON'T get this treatment.

### What This Breaks

- Tasks created via API with `depends_on` array pointing to multiple tasks
- Discovery-spawned tasks with multiple dependencies
- Any non-spec parallel work

### Fix Required

The orchestrator or task queue needs to auto-detect multi-dependency tasks:

```python
# In TaskQueueService.enqueue_task() or orchestrator_worker:
def maybe_register_join(task):
    """Register JOIN if task has multiple dependencies."""
    depends_on = task.dependencies.get("depends_on", [])
    if len(depends_on) > 1:
        coordination_service.register_join(
            join_id=f"auto-join-{task.id}",
            source_task_ids=depends_on,
            continuation_task_id=str(task.id),
            merge_strategy="combine",
        )
```

---

## Critical Gap #6: Ticket-Level vs Task-Level Branching Mismatch

**Severity**: 🟡 HIGH  
**Impact**: Git branch strategy doesn't match task execution model.

### The Problem

**Current branch model** (from DaytonaSpawner):
- One branch per TICKET: `ticket/{ticket_id}`
- All tasks for a ticket work on same branch
- Sequential commits, not parallel branches

**DAG merge model expects**:
- One branch per TASK: `task/{task_id}` or commits tagged by task
- Parallel tasks = parallel branches
- Convergence = merge branches together

### Evidence

```python
# daytona_spawner.py creates branches BEFORE sandbox:
effective_target_branch = target_branch or f"ticket/{ticket_id}"
```

```python
# convergence_merge_service.py expects to merge task branches:
async def _score_source_tasks(...):
    # Get commit SHAs for each task
    # For now, we use task IDs as branch refs (they may be commits or branches)
    task_commits = {task_id: task_id for task_id in source_task_ids}
    #              ^^^^^^^^^^^^^^^^
    # This assumes task_id = branch name, which is FALSE
```

### What This Breaks

If parallel tasks A, B, C all commit to `ticket/TKT-123`:
- Task A commits: `abc123`
- Task B starts from `abc123`, commits: `def456`
- Task C starts from `abc123`, commits: `ghi789`
- Task B and C have DIVERGENT histories
- `merge_at_convergence` can't find separate branches to merge
- The "merge" is meaningless

### Fix Options

**Option A: Task-level branching**
```python
# DaytonaSpawner creates task branches:
branch = f"ticket/{ticket_id}/task-{task_id}"
# After task complete: auto-PR to ticket branch
```

**Option B: Cherry-pick model**
```python
# Track commit SHAs per task in Task.result
# At convergence: cherry-pick commits from each task onto ticket branch
```

**Option C: Sequential execution for dependent tasks**
```python
# Don't allow parallel execution within same ticket
# Only parallelize across tickets
```

---

## Critical Gap #7: OwnershipValidationService Never Used

**Severity**: 🟡 HIGH  
**Impact**: Parallel tasks can edit same files → merge conflicts guaranteed.

### Evidence

```python
# ownership_validation.py exists with:
class OwnershipValidationService:
    """Prevents parallel task file conflicts."""
    
def get_ownership_validation_service() -> OwnershipValidationService:
    ...
```

```bash
grep -rn "get_ownership_validation_service\|OwnershipValidation" omoi_os/
# → Only in:
#   - ownership_validation.py (definition)
#   - daytona_spawner.py (import only, never called)
#   - tests
```

**DaytonaSpawner imports but doesn't use:**
```python
# daytona_spawner.py:27
from omoi_os.services.ownership_validation import OwnershipValidationService, OwnershipConflictError
# But neither is ever used in the file!
```

### What This Breaks

- Parallel tasks A and B both modify `auth.py`
- No validation prevents this
- Both complete successfully
- At merge time: CONFLICT
- LLM conflict resolution needed (expensive, error-prone)

### Fix Required

```python
# In orchestrator_worker, before assigning task to sandbox:
async def validate_task_files(task):
    ownership = get_ownership_validation_service()
    try:
        ownership.claim_files_for_task(
            task_id=str(task.id),
            file_paths=task.estimated_file_paths,  # Need to add this field
        )
    except OwnershipConflictError as e:
        # Don't spawn - wait for conflicting task to complete
        logger.warning(f"Task {task.id} blocked by file ownership: {e}")
        return False
    return True
```

---

## Summary: All Gaps

| # | Gap | Severity | What Breaks | Fix Effort |
|---|-----|----------|-------------|------------|
| 1 | CoordinationService not initialized | 🔴 Critical | No JOIN events created | 30 min |
| 2 | ConvergenceMergeService not initialized | 🔴 Critical | No git merges | 30 min |
| 3 | No sandbox for merge operations | 🔴 Critical | Merges can't execute | 4-8 hours |
| 4 | Event chain broken (_handle_synthesis_completed does nothing) | 🔴 Critical | Synthesis → Merge doesn't flow | 2-4 hours |
| 5 | JOIN not registered outside spec flow | 🟡 High | Non-spec parallel tasks orphaned | 2 hours |
| 6 | Ticket-level branching mismatch | 🟡 High | Branch model incompatible | 8-16 hours |
| 7 | OwnershipValidation never used | 🟡 High | File conflicts guaranteed | 4 hours |

---

## Recommended Implementation Order

### Week 1: Minimal Viable Parallel Tasks

**Day 1-2: Service Initialization**
1. Initialize CoordinationService in orchestrator_worker.py
2. Initialize ConvergenceMergeService in orchestrator_worker.py
3. Verify event subscriptions fire (add logging)

**Day 3-4: Merge Sandbox**
4. Add `create_merge_sandbox()` to DaytonaSpawner
5. Implement `_handle_synthesis_completed()` to actually spawn merge sandbox
6. Add merge_sandbox cleanup logic

**Day 5: Auto-JOIN Registration**
7. Auto-register JOINs for tasks with multiple dependencies
8. Test end-to-end with 2-way parallel → continuation

### Week 2: Production-Ready

**Day 1-2: Branching Model**
9. Decide: task-level branches vs cherry-pick model
10. Implement chosen model in DaytonaSpawner

**Day 3-4: Ownership Validation**
11. Add file estimation to task creation
12. Wire OwnershipValidationService into orchestrator

**Day 5: Testing**
13. Integration tests for full parallel flow
14. Load test with 5+ parallel tasks

---

## Test Scenarios Before Production

### Scenario 1: Basic 2-way Parallel
```
Task A (setup)
    ├── Task B (implement feature X)
    └── Task C (implement feature Y)
        └── Task D (integrate X + Y)
```
**Verify**: D receives merged results AND merged code

### Scenario 2: File Conflict Prevention
```
Task A edits auth.py
Task B wants to edit auth.py
```
**Verify**: B is blocked until A completes

### Scenario 3: Merge Conflict Resolution
```
Task A edits line 50 of config.py
Task B edits line 50 of config.py (different change)
```
**Verify**: LLM resolver is invoked, resolution recorded in MergeAttempt

### Scenario 4: 3-way Parallel with Dependencies
```
A → B (depends on A)
A → C (depends on A)
B, C → D (depends on both)
```
**Verify**: D waits for both B and C, gets merged context

### Scenario 5: Discovery-spawned Parallel Tasks
```
Task A discovers need for B
Task A discovers need for C
B and C can run in parallel
```
**Verify**: System recognizes parallelism opportunity (or serializes intentionally)

---

## Related Documentation

- `ARCHITECTURE.md` Part 6-11: DAG system design and known gaps
- `parallel_systems_analysis.md`: API/Worker process conflicts
- `services/convergence_merge_service.py`: Merge implementation (needs wiring)
- `services/coordination.py`: Coordination primitives
- `services/synthesis_service.py`: Result synthesis
