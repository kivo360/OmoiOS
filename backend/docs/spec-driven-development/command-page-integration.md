# Command Page Integration - Spec-Driven Development

**Created**: 2025-01-11
**Status**: Proposed
**Purpose**: Enable spec-driven workflow directly from the command page

---

## The Vision

The command page is like Google - simple, intuitive, just type and go:

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│     What do you want to build?                              │
│                                                             │
│     ┌─────────────────────────────────────────────────┐     │
│     │ Add user authentication with OAuth support...   │     │
│     └─────────────────────────────────────────────────┘     │
│                                                             │
│     ○ Quick Task    ● Spec-Driven                          │
│                                                             │
│                          [Enter ↵]                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

User types idea → Selects "Spec-Driven" → Hits Enter → System handles everything.

---

## Current State (What Happens Now)

```
Command Page
    │
    ▼
Creates Ticket (clutters kanban)
    │
    ▼
Creates Task with require_spec_skill=true
    │
    ▼
Agent gets prompt telling it to manually create specs
    │
    ▼
Agent works... but no Spec record exists
    │
    ▼
Results scattered, no structured tracking
```

**Problems**:
- Ticket created (kanban clutter)
- No Spec record auto-created
- State machine never triggered
- Agent manually follows prompt (inconsistent)

---

## Desired State (What Should Happen)

```
Command Page (Spec-Driven mode)
    │
    ▼
POST /api/v1/specs/launch
    │
    ├─► Creates Spec record
    │
    ├─► Starts SpecStateMachine
    │
    └─► Returns spec_id
    │
    ▼
Frontend redirects to Spec Detail Page
    │
    ▼
User watches phases progress:
    EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC
    │
    ▼
Spec complete with all artifacts
```

**Benefits**:
- No ticket clutter
- Spec record created immediately
- State machine handles phases automatically
- Structured output in database
- User can watch progress

---

## Implementation Plan

### Backend Changes

#### 1. New Endpoint: `POST /api/v1/specs/launch`

**CRITICAL**: Must spawn a Daytona sandbox, NOT run in API process!
See [sandbox-execution.md](./sandbox-execution.md) for details.

```python
# omoi_os/api/routes/specs.py

class SpecLaunchRequest(BaseModel):
    """Request to create and execute a spec in one step."""
    title: str
    description: str
    project_id: str  # REQUIRED - determines which codebase to mount
    auto_execute: bool = True  # Default: start state machine immediately


class SpecLaunchResponse(BaseModel):
    """Response from spec launch."""
    spec_id: str
    status: str  # "created" or "executing"
    current_phase: Optional[str] = None
    sandbox_id: Optional[str] = None  # Sandbox ID if executing
    message: str


@router.post("/launch", response_model=SpecLaunchResponse)
async def launch_spec(
    request: SpecLaunchRequest,
    db: DatabaseService = Depends(get_db_service),
    current_user: User = Depends(get_current_user),
):
    """
    Create a spec and optionally start execution in a SANDBOX.

    This is the "Google-like" entry point - user provides idea,
    system creates spec and spawns sandbox to run state machine.

    IMPORTANT: Execution happens in Daytona sandbox, NOT in API process!
    """
    # 1. Create spec record
    spec = Spec(
        title=request.title,
        description=request.description,
        project_id=request.project_id,
        status="draft" if not request.auto_execute else "executing",
        current_phase="explore",
        user_id=current_user.id,
    )

    async with db.get_async_session() as session:
        session.add(spec)
        await session.commit()
        await session.refresh(spec)
        spec_id = spec.id

    # 2. Spawn sandbox if auto_execute
    sandbox_id = None
    if request.auto_execute:
        from omoi_os.services.daytona_spawner import get_daytona_spawner
        spawner = get_daytona_spawner()

        # Spawn sandbox with spec context
        # The sandbox will have user's project codebase mounted
        sandbox_id = await spawner.spawn_for_phase(
            spec_id=spec_id,
            phase="explore",
            project_id=request.project_id,
            phase_context={
                "title": request.title,
                "description": request.description,
            },
        )

        return SpecLaunchResponse(
            spec_id=spec_id,
            status="executing",
            current_phase="explore",
            sandbox_id=sandbox_id,
            message="Spec created and execution started in sandbox",
        )

    return SpecLaunchResponse(
        spec_id=spec_id,
        status="created",
        current_phase=None,
        sandbox_id=None,
        message="Spec created (not executing)",
    )
```

### Frontend Changes

#### 1. Update Command Page API Call

```typescript
// When workflow_mode === "spec_driven", call launch instead of tickets

async function handleSubmit(data: CommandFormData) {
  if (data.workflowMode === "spec_driven") {
    // Direct spec launch - no ticket
    const response = await launchSpec({
      title: data.title,
      description: data.description,
      project_id: data.projectId,
      auto_execute: true,
    });

    // Redirect to spec detail page
    router.push(`/specs/${response.spec_id}`);
  } else {
    // Quick task - existing ticket flow
    const ticket = await createTicket(data);
    router.push(`/tickets/${ticket.id}`);
  }
}
```

#### 2. Add API Function

```typescript
// frontend/lib/api/specs.ts

export interface SpecLaunchRequest {
  title: string
  description: string
  project_id: string
  working_directory?: string
  auto_execute?: boolean
}

export interface SpecLaunchResponse {
  spec_id: string
  status: "created" | "executing"
  current_phase?: string
  message: string
}

export async function launchSpec(
  request: SpecLaunchRequest
): Promise<SpecLaunchResponse> {
  return apiRequest<SpecLaunchResponse>("/api/v1/specs/launch", {
    method: "POST",
    body: request,
  })
}
```

#### 3. Add React Query Hook

```typescript
// frontend/hooks/useSpecs.ts

export function useLaunchSpec() {
  const router = useRouter()

  return useMutation<SpecLaunchResponse, Error, SpecLaunchRequest>({
    mutationFn: launchSpec,
    onSuccess: (data) => {
      // Redirect to spec detail page
      router.push(`/specs/${data.spec_id}`)
    },
  })
}
```

---

## User Flow (After Implementation)

### Step 1: User Opens Command Page

Simple interface with text input and mode toggle.

### Step 2: User Types Idea

```
"Add user authentication with Google OAuth, email/password login,
and password reset functionality"
```

### Step 3: User Selects "Spec-Driven" Mode

Toggle or radio button selection.

### Step 4: User Hits Enter

Frontend calls `POST /api/v1/specs/launch`.

### Step 5: Redirect to Spec Detail Page

User sees spec with phases progressing:

```
┌─────────────────────────────────────────────────────────────┐
│  Spec: Add user authentication                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Status: Executing                                          │
│  Progress: ████████░░░░░░░░░░░░ 40%                        │
│                                                             │
│  Phases:                                                    │
│  ✓ EXPLORE      - Completed                                │
│  ✓ REQUIREMENTS - Completed                                │
│  ● DESIGN       - In Progress...                           │
│  ○ TASKS        - Pending                                  │
│  ○ SYNC         - Pending                                  │
│                                                             │
│  [View Requirements] [View Design] [View Tasks]             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Step 6: User Reviews at Each Gate (Optional Enhancement)

Could add approval gates where user reviews before next phase.

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/omoi_os/api/routes/specs.py` | Add `/launch` endpoint |
| `frontend/lib/api/specs.ts` | Add `launchSpec()` function |
| `frontend/hooks/useSpecs.ts` | Add `useLaunchSpec()` hook |
| `frontend/app/command/page.tsx` | Branch on workflow_mode |
| `frontend/app/specs/[id]/page.tsx` | Add phase progress UI |

---

## Migration Path

### Phase 1: Backend Endpoint (Day 1)
- Add `POST /api/v1/specs/launch` endpoint
- Test with curl/Postman

### Phase 2: Frontend Integration (Day 2)
- Add API function and hook
- Update command page to use launch for spec_driven mode
- Basic redirect to spec detail

### Phase 3: Progress UI (Day 3+)
- Add real-time phase progress to spec detail page
- WebSocket updates for phase changes
- Phase output viewers (requirements, design, tasks)

---

## Open Questions

1. **Default project**: If user doesn't select project, use default?
2. **Working directory**: Auto-detect from project settings?
3. **Approval gates**: Pause between phases for user review?
4. **Error handling**: What if state machine fails mid-phase?
5. **Cancel**: Allow user to cancel running spec?

---

## Why This Approach Works

1. **Simple UX**: Type → Select mode → Enter (like Google)
2. **No clutter**: No tickets created for spec work
3. **Structured output**: Spec record with phases, not scattered agent work
4. **Recoverable**: State machine has checkpoints
5. **Visible progress**: User can watch phases complete
6. **Builds on existing**: Uses existing SpecStateMachine, just adds entry point
