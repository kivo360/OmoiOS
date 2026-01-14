# Sandbox Execution - Critical Architecture Issue

**Created**: 2025-01-11
**Updated**: 2025-01-13 (clarified sandbox infrastructure status)
**Status**: CRITICAL - API Trigger Gap (not infrastructure gap)
**Purpose**: Document where spec execution SHOULD vs DOES run

---

## 🔄 Cross-Reference Update (2025-01-13)

**Important Clarification**: The sandbox infrastructure is **FULLY IMPLEMENTED** (see `docs/design/sandbox-agents/IMPLEMENTATION_COMPLETE_STATUS.md`):
- ✅ `spawn_for_phase()` method exists at `daytona_spawner.py:750`
- ✅ Worker can run in spec mode when `SPEC_PHASE` and `SPEC_ID` env vars are set
- ✅ Worker's `_run_spec_state_machine()` method at `claude_sandbox_worker.py:4211`
- ✅ Sandbox event reporting works (`sandbox.py:365`)
- ✅ Message injection works (`sandbox.py:758,803`)
- ✅ Guardian can intervene with sandboxes (`intelligent_guardian.py:693-887`)

**The GAP**: The API endpoint `POST /specs/{id}/execute` runs `run_spec_state_machine()` directly in the API process instead of calling `spawn_for_phase()`. This is a **wiring issue**, not a missing infrastructure issue.

---

## The Critical Question

> "When we launch it, is it launching inside of a sandbox?"

**Answer**: Currently, NO - the `POST /specs/{id}/execute` endpoint runs the state machine **directly in the backend API process**, not in a sandbox.

---

## Current State (PROBLEMATIC)

### Path A: API Direct Execution

```
POST /api/v1/specs/{spec_id}/execute
    │
    ▼
specs.py:1410
    working_dir = request.working_directory or os.getcwd()
    │
    ▼
specs.py:1416
    await run_spec_state_machine(spec_id, working_dir, ...)
    │
    ▼
RUNS IN BACKEND API PROCESS
    │
    ▼
Operates on BACKEND SERVER's filesystem! ← WRONG!
```

**Problems**:
- Runs in API process, not isolated sandbox
- `os.getcwd()` = backend server's directory
- Could modify backend codebase!
- No isolation from user's actual project
- Security risk

### Path B: Sandbox Execution (CORRECT but not triggered)

```
daytona_spawner.spawn_for_phase(spec_id, phase, project_id, ...)
    │
    ▼
Creates Daytona sandbox with env vars:
    SPEC_ID=<spec_id>
    SPEC_PHASE=<phase>
    PROJECT_ID=<project_id>
    │
    ▼
User's codebase mounted in sandbox
    │
    ▼
claude_sandbox_worker.py starts in sandbox
    │
    ▼
claude_sandbox_worker.py:4430-4431
    if config.spec_phase and config.spec_id:
        return await _run_spec_state_machine()
    │
    ▼
Uses self.config.cwd = sandbox working directory ← CORRECT!
    │
    ▼
Operates on USER's codebase in isolated sandbox
```

**This is the correct path** - but it's only triggered by:
1. `spawn_for_phase()` (crash recovery)
2. Setting env vars manually

---

## What `/execute` Should Do

The `POST /api/v1/specs/{id}/execute` endpoint should NOT run the state machine directly. Instead:

```python
@router.post("/{spec_id}/execute", response_model=SpecExecuteResponse)
async def execute_spec(
    spec_id: str,
    request: SpecExecuteRequest,
    db: DatabaseService = Depends(get_db_service),
):
    # 1. Get spec and project info
    spec = await _get_spec_async(db, spec_id)
    project = await _get_project_async(db, spec.project_id)

    # 2. Get the Daytona spawner
    from omoi_os.services.daytona_spawner import get_daytona_spawner
    spawner = get_daytona_spawner()

    # 3. Spawn sandbox with spec context
    sandbox_id = await spawner.spawn_for_phase(
        spec_id=spec_id,
        phase="explore",  # Start from beginning
        project_id=spec.project_id,
        # Project's git repo or working directory
        phase_context={
            "title": spec.title,
            "description": spec.description,
        },
    )

    # 4. Return immediately - sandbox handles execution
    return SpecExecuteResponse(
        spec_id=spec_id,
        status="started",
        message="Spec execution started in sandbox",
        sandbox_id=sandbox_id,
        current_phase="explore",
    )
```

---

## Files That Need Changes

| File | Current | Should Be |
|------|---------|-----------|
| `specs.py` execute endpoint | Calls `run_spec_state_machine()` directly | Calls `spawner.spawn_for_phase()` |
| `daytona_spawner.py` | `spawn_for_phase()` exists but unused | Called by execute endpoint |
| `SpecExecuteRequest` | Has `working_directory` | Should have `project_id` (required) |

---

## Key Code Locations

### Current (Wrong) - specs.py:1410-1420

```python
# Determine working directory
working_dir = request.working_directory or os.getcwd()  # ← WRONG!

# Run the state machine asynchronously (fire and forget)
async def run_execution():
    success = await run_spec_state_machine(
        spec_id=spec_id,
        working_directory=working_dir,  # ← Runs in API process!
        ...
    )
```

### Correct Path - claude_sandbox_worker.py:4248-4251

```python
state_machine = SpecStateMachine(
    spec_id=self.config.spec_id,
    db_session=db_session,
    working_directory=self.config.cwd,  # ← Sandbox's mounted directory
    model=self.config.model,
)
```

### Sandbox Spawner - daytona_spawner.py:750-920

```python
async def spawn_for_phase(
    self,
    spec_id: str,
    phase: str,
    project_id: str,
    phase_context: Optional[dict] = None,
    resume_transcript: Optional[str] = None,
    extra_env: Optional[dict] = None,
) -> str:
    """Spawn a sandbox for a specific spec phase."""
    # Sets SPEC_ID, SPEC_PHASE, etc.
    # Creates isolated sandbox with user's codebase
```

---

## Required Changes

### 1. Update `POST /specs/{id}/execute`

```python
@router.post("/{spec_id}/execute", response_model=SpecExecuteResponse)
async def execute_spec(
    spec_id: str,
    request: SpecExecuteRequest,
    db: DatabaseService = Depends(get_db_service),
):
    """Execute spec in a sandbox (NOT in API process)."""

    spec = await _get_spec_async(db, spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    if not spec.project_id:
        raise HTTPException(
            status_code=400,
            detail="Spec must have a project_id to execute"
        )

    # Update status
    await _update_spec_async(db, spec_id, status="executing")

    # Spawn sandbox for execution
    from omoi_os.services.daytona_spawner import get_daytona_spawner
    spawner = get_daytona_spawner()

    sandbox_id = await spawner.spawn_for_phase(
        spec_id=spec_id,
        phase=spec.current_phase or "explore",
        project_id=spec.project_id,
        phase_context={
            "title": spec.title,
            "description": spec.description,
        },
    )

    return SpecExecuteResponse(
        spec_id=spec_id,
        status="started",
        message=f"Spec execution started in sandbox {sandbox_id}",
        current_phase=spec.current_phase or "explore",
    )
```

### 2. Update `SpecExecuteRequest`

```python
class SpecExecuteRequest(BaseModel):
    """Request body for spec execution."""

    # REMOVE: working_directory - not needed, sandbox has project mounted

    enable_embeddings: bool = Field(
        True,
        description="Whether to enable embedding service.",
    )

    resume_from_phase: Optional[str] = Field(
        None,
        description="Resume from specific phase (for crash recovery).",
    )
```

### 3. Ensure Project Has Git/Path Info

The Project model should have the repository URL or path that gets mounted in the sandbox.

---

## Testing Checklist

- [ ] Create spec with project_id
- [ ] Call `POST /specs/{id}/execute`
- [ ] Verify Daytona sandbox is created
- [ ] Verify sandbox has correct env vars (SPEC_ID, SPEC_PHASE)
- [ ] Verify sandbox operates on project's codebase, NOT backend
- [ ] Verify state machine runs inside sandbox
- [ ] Verify results sync back to database

---

## Security Implications

| Current State | Risk |
|---------------|------|
| Runs in API process | Code execution in production backend |
| Uses `os.getcwd()` | Could modify backend codebase |
| No isolation | Agent has access to all backend files |

| Fixed State | Benefit |
|-------------|---------|
| Runs in Daytona sandbox | Isolated environment |
| Uses project's mounted path | Only accesses user's codebase |
| Full isolation | Agent cannot affect other systems |

---

## Related Documentation

- [architecture.md](./architecture.md) - Overall flow
- [command-page-integration.md](./command-page-integration.md) - Entry point
- `daytona_spawner.py` - Sandbox creation
- `claude_sandbox_worker.py` - Sandbox worker with state machine
