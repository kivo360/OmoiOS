# Skill to API Flow - Complete Ticket Creation Trace

**Created**: 2025-01-11
**Status**: CRITICAL ANALYSIS
**Purpose**: Document how tickets flow from Claude Skill (`.omoi_os/` files) to the OmoiOS API and identify the `user_id` gap

---

## TL;DR: TWO PATHS, SAME PROBLEM

There are **TWO paths** for creating tickets in the system:

1. **Backend Service Path**: `SpecTaskExecutionService` creates bridging tickets from Specs
2. **CLI Sync Path**: Claude Skill creates `.omoi_os/tickets/*.md` files → `spec_cli.py sync push` → API

**BOTH paths have the SAME critical bug**: Neither sets `user_id`, causing tickets to be **INVISIBLE** on the board!

---

## Path 1: Backend Service (SpecTaskExecutionService)

### Flow

```
Spec Creation → State Machine Phases → SpecTask Records → Execute Tasks API
                                                              │
                                                              ▼
                                            SpecTaskExecutionService
                                                              │
                                                              ▼
                                            _get_or_create_ticket()
                                                              │
                                                              ▼
                                            Ticket Created WITHOUT user_id!
```

### Code Location

`omoi_os/services/spec_task_execution.py:314-328`:

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
    # ❌ NO user_id SET!
)
```

### Root Cause

The `Spec` model has **NO `user_id` field**! Even if we wanted to pass it, we can't:

```python
# omoi_os/models/spec.py - NO user_id field exists!
class Spec(Base):
    id: Mapped[str]
    title: Mapped[str]
    description: Mapped[Optional[str]]
    project_id: Mapped[Optional[str]]
    # ... other fields
    # ❌ NO user_id ANYWHERE
```

---

## Path 2: CLI Sync (Claude Skill → API)

### Flow

```
Claude Agent (in Daytona sandbox)
    │
    │ Creates markdown files with YAML frontmatter
    ▼
.omoi_os/tickets/TKT-XXX.md
    │
    │ Agent runs: spec_cli.py sync push
    ▼
parse_specs.py (ParsedTicket model)
    │
    │ Validates and structures data
    ▼
api_client.py (OmoiOSClient.create_ticket())
    │
    │ POST /api/v1/tickets
    ▼
Ticket Created WITHOUT user_id!
```

### Code Locations

#### 1. ParsedTicket Model (Local)

`.claude/skills/spec-driven-dev/scripts/models.py:208-232`:

```python
@dataclass
class ParsedTicket:
    """Parsed ticket from .omoi_os/tickets/*.md"""

    id: str
    title: str
    status: str
    priority: str
    estimate: str
    created: date
    updated: date
    feature: Optional[str] = None
    requirements: list[str] = field(default_factory=list)
    design_ref: Optional[str] = None
    tasks: list[str] = field(default_factory=list)
    dependencies: TicketDependencies = field(default_factory=TicketDependencies)
    description: str = ""
    full_body: str = ""
    file_path: str = ""
    # ❌ NO user_id FIELD!
```

#### 2. Ticket Parsing

`.claude/skills/spec-driven-dev/scripts/parse_specs.py:646-662`:

```python
return ParsedTicket(
    id=frontmatter["id"],
    title=frontmatter["title"],
    status=frontmatter["status"],
    priority=frontmatter["priority"],
    estimate=frontmatter["estimate"],
    created=self._parse_date(frontmatter["created"]),
    updated=self._parse_date(frontmatter["updated"]),
    feature=frontmatter.get("feature"),
    requirements=frontmatter.get("requirements", []) or [],
    design_ref=frontmatter.get("design_ref"),
    tasks=frontmatter.get("tasks", []) or [],
    dependencies=dependencies,
    description=self._extract_description(body),
    full_body=self._extract_full_body(body),
    file_path=str(file_path),
    # ❌ NO user_id PARSED!
)
```

#### 3. API Client - Ticket Creation

`.claude/skills/spec-driven-dev/scripts/api_client.py:201-226`:

```python
async def create_ticket(
    self, ticket: ParsedTicket, project_id: Optional[str] = None
) -> tuple[bool, str]:
    """Create ticket in OmoiOS API."""
    description_text = ticket.full_body if ticket.full_body else ticket.description

    payload = {
        "title": ticket.title,
        "description": description_text,
        "priority": ticket.priority,
        "phase_id": "PHASE_IMPLEMENTATION",  # Default phase
    }
    if project_id:
        payload["project_id"] = project_id

    # ❌ NO user_id IN PAYLOAD!

    status, data = await self._request("POST", "/api/v1/tickets", json=payload)
```

---

## Where This Matters: Two Different Views

### 1. Ticket List API (`/api/v1/tickets`) - ✅ Tickets VISIBLE

`omoi_os/api/routes/tickets.py:79`:

```python
# Filter to accessible projects (via organization membership)
stmt = select(Ticket).filter(Ticket.project_id.in_([str(pid) for pid in accessible_project_ids]))
```

**No `user_id` filter** - shows all tickets in user's accessible projects.

### 2. Board View API (`/api/v1/board/view`) - ⚠️ Tickets MAY BE INVISIBLE

`omoi_os/services/board.py:62-66`:

```python
# Filter by project if specified
if project_id is not None:
    query = query.where(Ticket.project_id == project_id)
# Filter by user if specified (only show user's tickets)
if user_id is not None:
    query = query.where(Ticket.user_id == user_id)
```

The board view **always** receives `user_id` from the route:

```python
# board.py:191
board_data = await asyncio.to_thread(
    _get_board_view_sync, db, board_service, current_user.id, project_id
)
```

### What This Means

| Scenario | `user_id` Set? | Ticket List | Board View |
|----------|---------------|-------------|------------|
| Spec-generated ticket | ❌ No | ✅ Visible (project filter) | ❌ Invisible (user filter) |
| User-created ticket | ✅ Yes | ✅ Visible | ✅ Visible |
| Assigned ticket | ✅ Yes | ✅ Visible | ✅ Visible |

### Is This Intentional?

This might be **intended behavior**:
- **Ticket List**: Shows all project tickets (for project overview)
- **Board View**: Shows "my tickets" (for personal kanban)

If so, spec-generated tickets need a way to be assigned to a user before appearing on their board. This could be:
- Auto-assign to spec creator
- Require explicit assignment step
- Add "unassigned" column to board

---

## The Environment Variable That Could Help

The SKILL.md documents that sandbox agents receive environment variables:

```markdown
### Environment Variables (Auto-Injected)

The following environment variables are automatically available in the sandbox:

| Variable | Description | Example |
|----------|-------------|---------|
| `OMOIOS_API_URL` | Base URL for OmoiOS API | `http://api:8000` |
| `OMOIOS_API_KEY` | API authentication key | `sk-...` |
| `OMOIOS_PROJECT_ID` | Current project context | `proj_abc123` |
| `OMOIOS_SPEC_ID` | Spec being executed | `spec_xyz789` |
| `OMOIOS_USER_ID` | User who owns the spec | `user_123` |  <-- THIS EXISTS!
```

**The user_id IS available in the sandbox!** But neither:
- The `ParsedTicket` model includes it
- The `api_client.py` sends it
- The `parse_specs.py` looks for it in frontmatter

---

## Complete Fix Required

### Fix 1: Spec Model (Backend)

Add `user_id` to the Spec model:

```python
# omoi_os/models/spec.py
class Spec(Base):
    # ... existing fields ...

    user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
```

### Fix 2: Spec Routes (Backend)

Add authentication to spec routes:

```python
# omoi_os/api/routes/specs.py
@router.post("", response_model=SpecResponse)
async def create_spec(
    spec: SpecCreate,
    db: DatabaseService = Depends(get_db_service),
    current_user: User = Depends(get_current_user),  # ADD THIS
):
    # Set user_id from current user
    spec.user_id = current_user.id
```

### Fix 3: SpecTaskExecutionService (Backend)

Pass `user_id` to ticket creation:

```python
# omoi_os/services/spec_task_execution.py
ticket = Ticket(
    # ... existing fields ...
    user_id=spec.user_id,  # ADD THIS
)
```

### Fix 4: ParsedTicket Model (Skill)

Add `user_id` field:

```python
# .claude/skills/spec-driven-dev/scripts/models.py
@dataclass
class ParsedTicket:
    # ... existing fields ...
    user_id: Optional[str] = None  # ADD THIS
```

### Fix 5: Ticket Parsing (Skill)

Parse `user_id` from frontmatter:

```python
# .claude/skills/spec-driven-dev/scripts/parse_specs.py
return ParsedTicket(
    # ... existing fields ...
    user_id=frontmatter.get("user_id"),  # ADD THIS
)
```

### Fix 6: API Client (Skill)

Send `user_id` in payload:

```python
# .claude/skills/spec-driven-dev/scripts/api_client.py
payload = {
    "title": ticket.title,
    "description": description_text,
    "priority": ticket.priority,
    "phase_id": "PHASE_IMPLEMENTATION",
}
if project_id:
    payload["project_id"] = project_id
if ticket.user_id:  # ADD THIS
    payload["user_id"] = ticket.user_id
```

### Fix 7: Ticket YAML Frontmatter Template

Update templates to include `user_id`:

```yaml
---
id: TKT-XXX-001
title: "Implement Feature X"
status: pending
priority: HIGH
estimate: 4h
user_id: ${OMOIOS_USER_ID}  # ADD THIS - injected from env
created: 2025-01-11
updated: 2025-01-11
# ...
---
```

---

## Summary

| Component | Current State | Fix Required |
|-----------|---------------|--------------|
| Spec Model | No `user_id` field | Add FK to users table |
| Spec Routes | No authentication | Add `get_current_user` dependency |
| SpecTaskExecutionService | No `user_id` passed | Pass `spec.user_id` to Ticket |
| ParsedTicket Model | No `user_id` field | Add optional `user_id` field |
| parse_specs.py | No `user_id` parsing | Parse from frontmatter |
| api_client.py | No `user_id` in payload | Add to POST body |
| Ticket Templates | No `user_id` in YAML | Add using env variable |

---

## Files to Modify

### Backend
| File | Change |
|------|--------|
| `omoi_os/models/spec.py` | Add `user_id` field |
| `alembic/versions/xxx_add_spec_user_id.py` | New migration |
| `omoi_os/api/routes/specs.py` | Add `get_current_user` dependency |
| `omoi_os/services/spec_task_execution.py` | Pass `user_id` to ticket |

### Skill Scripts
| File | Change |
|------|--------|
| `.claude/skills/spec-driven-dev/scripts/models.py` | Add `user_id` to ParsedTicket |
| `.claude/skills/spec-driven-dev/scripts/parse_specs.py` | Parse `user_id` from frontmatter |
| `.claude/skills/spec-driven-dev/scripts/api_client.py` | Send `user_id` in payload |

### Skill Templates
| File | Change |
|------|--------|
| `.claude/skills/spec-driven-dev/references/ticket-template.md` | Add `user_id` to frontmatter |
| `.claude/skills/spec-driven-dev/SKILL.md` | Document `user_id` requirement |

---

## Cascading Dependencies

```
1. Add user_id to Spec model (migration)
        │
        ├── Requires: Spec routes require authentication
        │
        ▼
2. Update Spec routes to set user_id from current_user
        │
        ▼
3. Update SpecTaskExecutionService to pass user_id
        │
        ▼
4. Update Skill scripts to handle user_id
        │   ├── models.py
        │   ├── parse_specs.py
        │   └── api_client.py
        │
        ▼
5. Update Skill templates to include user_id
        │
        ▼
6. Tickets now visible on board!
```

---

## Verification Steps

After implementing fixes:

1. Create a spec via API with authenticated user
2. Verify `spec.user_id` is set
3. Execute spec via `/specs/{id}/execute-tasks`
4. Verify created Ticket has `user_id` set
5. Open board as the same user
6. Verify ticket appears on board

OR via CLI:

1. Agent creates `.omoi_os/tickets/TKT-001.md` with `user_id: ${OMOIOS_USER_ID}`
2. Agent runs `spec_cli.py sync push`
3. Verify API receives `user_id` in payload
4. Verify created Ticket has `user_id` set
5. User opens board
6. Verify ticket appears
