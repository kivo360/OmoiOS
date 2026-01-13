# Phase Data Flow - What Actually Happens

**Created**: 2025-01-11
**Status**: GAP ANALYSIS
**Purpose**: Trace exactly what data is saved at each step

---

## Current Implementation - Phase by Phase

### Phase 1: EXPLORE

**What runs**: Agent explores codebase, identifies structure, conventions, tech stack.

**What's saved**:
```python
# spec_state_machine.py:898-917
spec.phase_data["explore"] = {
    "project_type": "fastapi",
    "structure": {...},
    "existing_models": [...],
    "conventions": {...},
    "tech_stack": {...},
}
spec.phase_attempts["explore"] = attempt_count
spec.session_transcripts["explore"] = {...}
await db.commit()  # Saved to Spec.phase_data JSONB column
```

**Where it goes**: `specs.phase_data` JSONB column in Spec table.

**Separate entities created**: ❌ NONE

---

### Phase 2: REQUIREMENTS

**What runs**: Agent generates EARS-format requirements.

**What's saved**:
```python
spec.phase_data["requirements"] = {
    "requirements": [
        {
            "title": "...",
            "condition": "WHEN...",
            "action": "THE SYSTEM SHALL...",
            "acceptance_criteria": [...],
            "priority": "high",
        },
        ...
    ]
}
await db.commit()
```

**Where it goes**: `specs.phase_data` JSONB column.

**Separate entities created**: ❌ NONE (just stored as JSON!)

---

### Phase 3: DESIGN

**What runs**: Agent creates architecture, data model, API spec.

**What's saved**:
```python
spec.phase_data["design"] = {
    "architecture": "...",
    "data_model": [...],
    "api_endpoints": [...],
}
await db.commit()
```

**Where it goes**: `specs.phase_data` JSONB column.

**Separate entities created**: ❌ NONE

---

### Phase 4: TASKS

**What runs**: Agent breaks design into discrete tasks.

**What's saved**:
```python
spec.phase_data["tasks"] = {
    "tasks": [
        {
            "title": "...",
            "description": "...",
            "phase": "backend",
            "priority": "high",
            "dependencies": [...],
        },
        ...
    ]
}
await db.commit()
```

**Where it goes**: `specs.phase_data` JSONB column.

**Separate entities created**: ❌ NONE (just stored as JSON!)

---

### Phase 5: SYNC

**What runs**: `_execute_sync_phase()` → `SpecSyncService.sync_spec()`

**What happens** (from `spec_sync.py`):
```python
# 1. Read requirements from phase_data
requirements_data = spec.phase_data.get("requirements", {})

# 2. Create SpecRequirement records (FINALLY!)
for req_data in requirements_data:
    new_req = SpecRequirement(
        spec_id=spec.id,
        title=req_data.get("title", ""),
        condition=req_data.get("condition", ""),
        action=req_data.get("action", ""),
    )
    session.add(new_req)

    # 3. Create SpecAcceptanceCriterion records
    for criterion in req_data.get("acceptance_criteria", []):
        new_crit = SpecAcceptanceCriterion(
            requirement_id=new_req.id,
            text=criterion,
        )
        session.add(new_crit)

# 4. Read tasks from phase_data
tasks_data = spec.phase_data.get("tasks", {})

# 5. Create SpecTask records
for task_data in tasks_data:
    new_task = SpecTask(
        spec_id=spec.id,
        title=task_data.get("title", ""),
        description=task_data.get("description"),
    )
    session.add(new_task)
```

**Entities created**:
- ✅ `SpecRequirement` records
- ✅ `SpecAcceptanceCriterion` records
- ✅ `SpecTask` records

**NOT created**:
- ❌ `Ticket` records
- ❌ `Task` records (the execution tasks, not spec tasks)

---

### Phase 6: COMPLETE

**What runs**: Just marks spec complete.

```python
spec.status = "completed"
spec.current_phase = "complete"
await db.commit()
```

**Entities created**: ❌ NONE

---

## The Data Model Problem

```
┌─────────────────────────────────────────────────────────────┐
│                    WHAT WE HAVE NOW                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Spec                                                        │
│   │                                                          │
│   ├── phase_data: {                                          │
│   │       "explore": {...},       <── JSON blob              │
│   │       "requirements": {...},  <── JSON blob              │
│   │       "design": {...},        <── JSON blob              │
│   │       "tasks": {...},         <── JSON blob              │
│   │   }                                                      │
│   │                                                          │
│   ├── SpecRequirement (created in SYNC)                      │
│   │       └── SpecAcceptanceCriterion                        │
│   │                                                          │
│   └── SpecTask (created in SYNC)                             │
│           │                                                  │
│           └── DEAD END - Never becomes Ticket!               │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    EXECUTION DOMAIN                          │
│                    (DISCONNECTED)                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Ticket (no spec_id!)                                        │
│   │                                                          │
│   └── Task (agent execution unit)                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## What's Missing at Each Step

### EXPLORE Phase
- ❌ No sync at this step (just stores to `phase_data`)

### REQUIREMENTS Phase
- ❌ No sync at this step (just stores to `phase_data`)
- **Should create**: `SpecRequirement` + `SpecAcceptanceCriterion` records

### DESIGN Phase
- ❌ No sync at this step (just stores to `phase_data`)
- Could optionally create design artifacts as separate records

### TASKS Phase
- ❌ No sync at this step (just stores to `phase_data`)
- **Should create**: `SpecTask` records

### SYNC Phase (Current)
- ✅ Creates `SpecRequirement` records
- ✅ Creates `SpecAcceptanceCriterion` records
- ✅ Creates `SpecTask` records
- ❌ **Missing**: Create `Ticket` records
- ❌ **Missing**: Create `Task` records (execution units)

### COMPLETE Phase
- ❌ Just marks complete
- ❌ **Missing**: Link tickets back to spec for completion tracking

---

## Two Options to Consider

### Option A: Sync Incrementally at Each Phase

```
EXPLORE phase completes
    └── Sync: Update spec.exploration_summary (or keep in phase_data, this is fine)

REQUIREMENTS phase completes
    └── Sync: Create SpecRequirement + SpecAcceptanceCriterion records NOW

DESIGN phase completes
    └── Sync: Update spec.design JSONB column NOW

TASKS phase completes
    └── Sync: Create SpecTask records NOW

EXECUTION phase (NEW!) - NOT "SYNC"
    └── Sync: Create Ticket + Task records from SpecTasks
    └── Agents start working on tickets

FINAL_SYNC phase (NEW!)
    └── When all tickets complete, mark spec complete
```

**Pros**: Data is saved incrementally, easier crash recovery
**Cons**: More complex, more database writes

### Option B: Keep Batched Sync but Add Ticket Creation

```
EXPLORE → REQUIREMENTS → DESIGN → TASKS
    └── All saved to phase_data JSON (current behavior)

SYNC phase
    └── Create SpecRequirement records (current)
    └── Create SpecAcceptanceCriterion records (current)
    └── Create SpecTask records (current)
    └── NEW: Create Ticket records from SpecTasks
    └── NEW: Create Task records (execution units)

When all tickets complete
    └── Mark spec complete
```

**Pros**: Simpler, fewer changes to existing flow
**Cons**: All-or-nothing sync, data in JSON until SYNC

---

## Questions This Raises

1. **When to create tickets?**
   - At SYNC phase (all at once)?
   - After user reviews/approves requirements and design?

2. **What triggers execution?**
   - Auto-start after SYNC?
   - Require user approval first?

3. **How to track completion?**
   - When ticket marked done, check if all tickets for spec are done?
   - Need a "spec completion watcher" service?

4. **What about incremental syncs?**
   - If user modifies a requirement, re-run from that phase?
   - How to handle partial re-syncs?

---

## Summary

**Current Reality**:
1. Phases 1-4 save to `phase_data` JSONB (just JSON blobs)
2. SYNC phase creates `SpecRequirement`, `SpecAcceptanceCriterion`, `SpecTask` records
3. `SpecTask` records just sit there - never converted to `Ticket`
4. No actual execution ever happens!

**The Gap**:
- `SpecTask` ≠ `Ticket`
- No code exists to convert SpecTask → Ticket
- No link from Ticket back to Spec
- No completion tracking from Ticket → Spec

This is why you were right to be terrified - the planning system is complete, but it never connects to the execution system!
