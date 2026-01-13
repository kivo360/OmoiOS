# Ticket Field Gap Analysis - UI Compatibility

**Created**: 2025-01-11
**Status**: CRITICAL GAP IDENTIFIED
**Purpose**: Document missing Ticket fields that will break the UI when SpecTaskExecutionService creates bridging tickets

---

## TL;DR: Visibility Depends on Which API You Use

The `SpecTaskExecutionService._get_or_create_ticket()` creates tickets **WITHOUT `user_id`**.

**Two Different Behaviors:**

| API Endpoint | Filter Logic | Tickets Without `user_id` |
|--------------|--------------|---------------------------|
| `/api/v1/tickets` (Ticket List) | `project_id` only | ✅ **VISIBLE** |
| `/api/v1/board/view` (Board View) | `project_id` AND `user_id` | ⚠️ **INVISIBLE** |

This may be **intentional design**: Board shows "my tickets", List shows "all project tickets".

---

## What SpecTaskExecutionService Creates

From `omoi_os/services/spec_task_execution.py:314-328`:

```python
ticket = Ticket(
    id=str(uuid4()),
    title=f"[Spec] {spec.title}",
    description=spec.description,
    phase_id="PHASE_IMPLEMENTATION",
    status="building",
    priority="MEDIUM",
    project_id=spec.project_id,
    context={
        "spec_id": spec.id,
        "spec_title": spec.title,
        "source": "spec_task_execution",
    },
)
```

### Fields SET ✅

| Field | Value | Notes |
|-------|-------|-------|
| `id` | UUID | Generated |
| `title` | `"[Spec] {spec.title}"` | Prefixed with [Spec] |
| `description` | `spec.description` | Passed through |
| `phase_id` | `"PHASE_IMPLEMENTATION"` | Hardcoded |
| `status` | `"building"` | Hardcoded |
| `priority` | `"MEDIUM"` | Hardcoded |
| `project_id` | `spec.project_id` | Passed through |
| `context` | JSONB with spec_id | Stores spec link |

### Fields NOT SET ❌

| Field | Impact | Severity |
|-------|--------|----------|
| **`user_id`** | **TICKETS INVISIBLE ON BOARD!** | **🔴 CRITICAL** |
| `approval_status` | Defaults to `pending_review` | 🟡 Medium |
| `created_at` | Auto-set by DB | ✅ OK |
| `updated_at` | Auto-set by DB | ✅ OK |

---

## The Critical Bug: `user_id` Not Set

### How the Board Filters Tickets

From `omoi_os/services/board.py:65-66`:

```python
# Filter by user if specified (only show user's tickets)
if user_id is not None:
    query = query.where(Ticket.user_id == user_id)
```

From `omoi_os/api/routes/board.py:86`:

```python
board_data = board_service.get_board_view(session=session, project_id=project_id, user_id=user_id)
```

### What Happens

1. User creates a spec via `/specs/{id}/execute`
2. `SpecTaskExecutionService` creates bridging ticket **WITHOUT** `user_id`
3. User opens board page
4. Board API filters by `user_id = current_user.id`
5. **Ticket doesn't appear because `user_id IS NULL`!**

### The User Experience

```
User: "I created a spec and executed it. Where are my tickets?"
System: *crickets* - Tickets exist but are invisible!
User: "The system is broken!"
```

---

## What the Frontend Expects

### Frontend Ticket Type

From `frontend/lib/api/types.ts:330-341`:

```typescript
export interface Ticket {
  id: string
  title: string
  description: string | null
  status: string
  priority: string
  phase_id: string
  approval_status: string | null  // ← Optional, OK if null
  created_at: string | null
  updated_at?: string | null
  project_id?: string
}
```

**Note**: The frontend Ticket type does NOT include `user_id` - it's not displayed in the UI.

### What Board API Returns

From `omoi_os/services/board.py:83-91`:

```python
"tickets": [
    {
        "id": t.id,
        "title": t.title,
        "phase_id": t.phase_id,
        "priority": t.priority,
        "status": t.status,
    }
    for t in tickets_in_column
],
```

**Note**: The Board API doesn't return `description` or `approval_status`!

### What Board UI Uses

From `frontend/app/(app)/board/[projectId]/page.tsx:458-472`:

```typescript
const allTickets: BoardTicket[] = useMemo(() => {
  return boardData.columns.flatMap((col) =>
    col.tickets.map((t: ApiTicket) => ({
      id: t.id,
      title: t.title,
      columnId: col.id,
      priority: (t.priority?.toLowerCase() || "medium"),
      status: t.status,
      phase: t.phase_id,
      description: t.description,        // ← NOT RETURNED BY API!
      approval_status: t.approval_status, // ← NOT RETURNED BY API!
    }))
  )
}, [boardData])
```

---

## Field Compatibility Matrix

| Field | Ticket Model | SpecTaskExec Creates | Board API Returns | Frontend Uses |
|-------|-------------|---------------------|-------------------|---------------|
| `id` | ✅ Required | ✅ Yes | ✅ Yes | ✅ Yes |
| `title` | ✅ Required | ✅ Yes | ✅ Yes | ✅ Yes |
| `description` | ⚪ Optional | ✅ Yes | ❌ No | ✅ Yes |
| `phase_id` | ✅ Required | ✅ Yes | ✅ Yes | ✅ Yes |
| `status` | ✅ Required | ✅ Yes | ✅ Yes | ✅ Yes |
| `priority` | ✅ Required | ✅ Yes | ✅ Yes | ✅ Yes |
| `user_id` | ⚪ Optional | ❌ **NO** | N/A (filter) | N/A |
| `project_id` | ⚪ Optional | ✅ Yes | N/A (filter) | N/A |
| `approval_status` | ⚪ Optional | ❌ No | ❌ No | ✅ Yes |
| `created_at` | ⚪ Auto | ⚪ Auto | ❌ No | N/A |
| `updated_at` | ⚪ Auto | ⚪ Auto | ❌ No | N/A |

---

## Gaps Identified

### 🔴 CRITICAL Gap 1: `user_id` Not Set

**Impact**: Tickets created by `SpecTaskExecutionService` are **INVISIBLE** on the board.

**Fix Required**:

```python
# In SpecTaskExecutionService._get_or_create_ticket()
ticket = Ticket(
    id=str(uuid4()),
    title=f"[Spec] {spec.title}",
    description=spec.description,
    phase_id="PHASE_IMPLEMENTATION",
    status="building",
    priority="MEDIUM",
    project_id=spec.project_id,
    user_id=spec.user_id,  # ← ADD THIS!
    context={
        "spec_id": spec.id,
        "spec_title": spec.title,
        "source": "spec_task_execution",
    },
)
```

### 🟡 Medium Gap 2: Board API Missing Fields

**Impact**: Frontend tries to use `description` and `approval_status` but API doesn't return them.

**Current Behavior**: Frontend shows `null` for these fields (graceful degradation).

**Fix Required**:

```python
# In BoardService.get_board_view()
"tickets": [
    {
        "id": t.id,
        "title": t.title,
        "phase_id": t.phase_id,
        "priority": t.priority,
        "status": t.status,
        "description": t.description,        # ← ADD
        "approval_status": t.approval_status, # ← ADD
    }
    for t in tickets_in_column
],
```

### 🟢 Low Gap 3: `spec_id` in Context, Not FK

**Impact**: No proper FK relationship, harder to query tickets by spec.

**Note**: This is documented in `data-flow-gap.md`.

---

## 🔴 CONFIRMED: Spec Model Has NO `user_id`!

**Checked**: `omoi_os/models/spec.py`

The Spec model does NOT have a `user_id` field.

### What This Means

1. **Spec creation doesn't track user ownership** (separate issue!)
2. **We cannot pass `spec.user_id` to ticket creation** - it doesn't exist
3. **We need to either:**
   - Add `user_id` to Spec model (requires migration)
   - Get user_id from another source at ticket creation time

### Additional Issue: Spec Routes Don't Require Authentication

From `omoi_os/api/routes/specs.py:958-962`:

```python
@router.post("", response_model=SpecResponse)
async def create_spec(
    spec: SpecCreate,
    db: DatabaseService = Depends(get_db_service),
    # ❌ NO get_current_user dependency!
):
```

The `create_spec` endpoint does NOT require authentication! This means:
- Anyone can create specs
- We don't know WHO created the spec
- This is a security/UX issue separate from the ticket gap

### Proposed Fix: Add `user_id` to Spec Model

```python
# In omoi_os/models/spec.py
from uuid import UUID

class Spec(Base):
    # ... existing fields ...

    # NEW: Track who owns this spec
    user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # Nullable for backward compatibility
        index=True,
        comment="User who created/owns this spec"
    )
```

Then in `SpecTaskExecutionService`:

```python
ticket = Ticket(
    # ... existing fields ...
    user_id=spec.user_id,  # Now we can pass it!
)
```

---

## Summary

| Gap | Severity | Impact | Fix Effort |
|-----|----------|--------|------------|
| Spec has no `user_id` | 🔴 CRITICAL | Can't set ticket owner | Medium - migration |
| Ticket `user_id` not set | 🔴 CRITICAL | Tickets invisible! | Low - once Spec has user_id |
| Spec routes no auth | 🔴 CRITICAL | Security hole | Low - add dependency |
| Board API missing fields | 🟡 Medium | UI shows null | Low - add 2 fields |
| `spec_id` not FK | 🟢 Low | Harder to query | Medium - migration |

---

## Cascading Dependencies

```
1. Add user_id to Spec model (migration)
        │
        ├── Requires: Spec routes require authentication
        │
        ▼
2. Update SpecTaskExecutionService to pass user_id
        │
        ▼
3. Tickets now visible on board
        │
        ▼
4. (Optional) Fix Board API to return description/approval_status
```

---

## Next Steps (In Order)

1. **Add `user_id` to Spec model** - Create migration
2. **Add auth to spec routes** - Add `get_current_user` dependency
3. **Update spec creation** - Set `user_id` from current user
4. **Fix `SpecTaskExecutionService`** - Add `user_id=spec.user_id`
5. **Fix Board API** - Add `description` and `approval_status` to response
6. **Test the flow** - Create spec → Execute → Verify tickets appear on board

---

## Files to Modify

| File | Change |
|------|--------|
| `omoi_os/models/spec.py` | Add `user_id` field |
| `alembic/versions/xxx_add_spec_user_id.py` | New migration |
| `omoi_os/api/routes/specs.py` | Add `get_current_user` dependency |
| `omoi_os/services/spec_task_execution.py` | Pass `user_id` to ticket |
| `omoi_os/services/board.py` | Add `description`, `approval_status` to ticket response |
