# GitHub Integration Gap - Spec-Driven Development

**Created**: 2025-01-13
**Updated**: 2025-01-14 (ALL GAPS RESOLVED)
**Status**: ✅ COMPLETE
**Purpose**: Document the missing pieces for end-to-end spec execution with GitHub integration

---

## ✅ STATUS: ALL GAPS RESOLVED (2025-01-14)

All GitHub integration gaps have been fixed. Here's a summary:

| Gap | Original Status | Resolution |
|-----|-----------------|------------|
| Gap 1: Project → GitHub Repo | ❌ Missing | ✅ **EXISTED** - `Project.github_owner`, `Project.github_repo` already present |
| Gap 2: User → GitHub Token | ❌ Missing | ✅ **EXISTED** - `CredentialsService.get_github_credentials()` works |
| Gap 3: Spec Execution → Sandbox | ❌ Missing | ✅ **FIXED** - `spawn_for_phase()` now fetches credentials |
| Gap 4: Progress Monitoring | ⚠️ Partial | ✅ **EXISTED** - Sandbox heartbeats work, `spec_id` on events |
| Gap 5: Auto PR Creation | ❌ Missing | ✅ **FIXED** - `SpecCompletionService` + API endpoints |
| Gap 6: Branch Naming | ❌ Missing | ✅ **FIXED** - `spec/{id}-{slug}` pattern in `SpecCompletionService` |

### What Was Implemented

1. **`spawn_for_phase()` GitHub Credential Injection** (`daytona_spawner.py:~800-850`)
   - Fetches user's GitHub credentials via `CredentialsService`
   - Passes `GITHUB_TOKEN`, `GITHUB_REPO`, `GITHUB_REPO_OWNER`, `GITHUB_USERNAME` to sandbox
   - Also fetches Anthropic credentials (`CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`)

2. **PR Tracking Fields on Spec Model** (`models/spec.py`)
   - `branch_name: String(255)` - Git branch for the spec
   - `pull_request_url: String(500)` - GitHub PR URL
   - `pull_request_number: Integer` - PR number

3. **Migration 053** (`migrations/versions/053_add_spec_pr_tracking_fields.py`)
   - Adds the three PR tracking columns to `specs` table

4. **`SpecCompletionService`** (`services/spec_completion_service.py`)
   - `create_branch_for_spec()` - Creates branch via `BranchWorkflowService`
   - `create_pr_for_spec()` - Creates PR after all tasks complete
   - `on_all_tickets_complete()` - Main entry point for completion workflow
   - Branch naming: `spec/{spec_id[:8]}-{slugified_title}`

5. **API Endpoints** (`api/routes/specs.py`)
   - `POST /specs/{id}/create-branch` - Manually trigger branch creation
   - `POST /specs/{id}/create-pr` - Manually trigger PR creation

---

## Original Gap Analysis (Preserved for Reference)

---

## 🔄 Cross-Reference Status (2025-01-13)

**This document has been cross-referenced with:**
- `docs/design/sandbox-agents/02_gap_analysis.md` - Sandbox system implementation (MOSTLY COMPLETE)
- `docs/design/sandbox-agents/IMPLEMENTATION_COMPLETE_STATUS.md` - Backend 100% complete
- `backend/omoi_os/workers/claude_sandbox_worker.py` - Production worker implementation

### Key Clarification: Two Different Scopes

| Documentation Set | Scope | Status |
|-------------------|-------|--------|
| **sandbox-agents/** | General sandbox infrastructure (event callback, message injection, Guardian integration, worker scripts) | ✅ Backend 100% Complete |
| **spec-driven-development/** | Spec-specific workflow (state machine, phase execution, spec→ticket bridge) | ⚠️ Gaps Remain |

**The sandbox infrastructure EXISTS and WORKS.** The spec-driven workflow doesn't fully USE it yet.

---

## ⚠️ Prior Documentation Review

**After creating this document, I discovered several related documents that partially cover these topics:**

### Already Documented & IMPLEMENTED Elsewhere

| Topic | Existing Document | What's Covered | Status |
|-------|------------------|----------------|--------|
| **GitHub OAuth UI Flow** | `docs/page_flows/08c_github_integration.md` | Full OAuth authorization flow, repo connection UI, webhook configuration UI | ✅ Design exists |
| **Sandbox GitHub Clone** | `docs/design/sandbox-agents/02_gap_analysis.md` | Daytona SDK's `git.clone()` implementation, worker script GitHub handling | ✅ **IMPLEMENTED** at `daytona_spawner.py:599-606` |
| **GitHub API Methods** | `docs/design/sandbox-agents/02_gap_analysis.md` | `get_pull_request`, `merge_pull_request`, `delete_branch`, `compare_branches` | ✅ **IMPLEMENTED** at `github_api.py:804,852,923,956` |
| **Branch Workflow Service** | `docs/design/sandbox-agents/02_gap_analysis.md` | `branch_workflow.py` exists with API routes | ✅ **IMPLEMENTED** |
| **Idle Sandbox Monitor** | `docs/design/sandbox-agents/02_gap_analysis.md` | Full design + implementation at `idle_sandbox_monitor.py` | ✅ **IMPLEMENTED** at `orchestrator_worker.py:411-492` |
| **Guardian Sandbox Integration** | `docs/design/sandbox-agents/02_gap_analysis.md` | Guardian can now intervene with sandbox agents via message injection | ✅ **IMPLEMENTED** at `intelligent_guardian.py:693-887` |
| **Sandbox Event Callback** | `docs/design/sandbox-agents/02_gap_analysis.md` | Workers POST events to backend | ✅ **IMPLEMENTED** at `sandbox.py:365` |
| **Message Injection** | `docs/design/sandbox-agents/02_gap_analysis.md` | POST/GET messages for sandbox agents | ✅ **IMPLEMENTED** at `sandbox.py:758,803` |

### What THIS Document Adds (Spec-Specific Gaps)

This document focuses on **spec-driven workflow specific gaps** that weren't covered in the sandbox agent architecture:

1. **Project model → GitHub repo link** (database schema gap)
2. **User GitHub token retrieval for specs** (not just general OAuth flow)
3. **Spec execution → sandbox spawning bridge** (specific to spec state machine)
4. **Spec-specific events** (beyond general sandbox events)
5. **Auto PR creation on spec completion** (spec workflow automation)

### Key Insight

The **infrastructure exists** (OAuth, GitHub API, sandbox clone, branch workflow), but the **spec-driven workflow doesn't use it yet**. The bridge from "spec execution starts" to "sandbox with GitHub context spawned" is missing.

### Clarification on `/execute` Endpoint

**Current implementation (`specs.py:1491`):**
```python
# This runs run_spec_state_machine() in the API process
success = await run_spec_state_machine(
    spec_id=spec_id,
    working_directory=working_dir,  # Uses os.getcwd() by default!
    enable_embeddings=request.enable_embeddings,
)
```

**The worker CAN run in spec mode** when `SPEC_PHASE` and `SPEC_ID` are set (see `claude_sandbox_worker.py:4424-4431`), but the API endpoint doesn't trigger it that way. The `spawn_for_phase()` method EXISTS at `daytona_spawner.py:750` but is documented as being "only for CRASH RECOVERY, not normal flow".

**The gap is the API trigger, not the worker capability.**

---

## TL;DR: Major Gaps in the GitHub Flow

The spec-driven workflow assumes code gets written, committed, and pushed to GitHub. But several critical pieces are **undocumented or unimplemented**:

1. **Project → GitHub Repo Connection**: How does a spec know which repo to clone?
2. **User → GitHub Token**: Where do credentials come from?
3. **Sandbox Spawning**: How does spec execution actually call `spawn_for_phase()`?
4. **Progress Monitoring**: How do we track sandbox health during spec execution?
5. **PR Creation**: What happens after spec tickets complete?

---

## Gap 1: Project → GitHub Repository Connection

### Current State

The `daytona_spawner.py` expects these environment variables:

```python
# daytona_spawner.py:1080-1083
github_repo = env_vars.pop("GITHUB_REPO", None)      # e.g., "owner/repo"
github_token = env_vars.pop("GITHUB_TOKEN", None)    # Personal access token
github_owner = env_vars.pop("GITHUB_REPO_OWNER", None)
```

### What's Missing

**Question**: Where do these values come from when executing a spec?

**Current Project model** (`omoi_os/models/project.py`):
```python
class Project(Base):
    id: Mapped[str]
    name: Mapped[str]
    organization_id: Mapped[str]
    # ...
    # ❓ Does it have github_repo_url?
    # ❓ Does it have github_default_branch?
```

### Required Changes

1. **Add GitHub fields to Project model**:
```python
class Project(Base):
    # ... existing fields ...

    # NEW: GitHub repository connection
    github_repo_url: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        comment="GitHub repository URL (e.g., 'owner/repo')"
    )
    github_default_branch: Mapped[str] = mapped_column(
        String,
        default="main",
        comment="Default branch for PRs"
    )
```

2. **Add UI for connecting GitHub repo to project**

3. **Validate repo access when connecting**

---

## Gap 2: User → GitHub Token Flow

### Current State

The system has OAuth infrastructure:
- `omoi_os/api/routes/oauth.py` - OAuth callback handling
- `omoi_os/services/auth_service.py` - Token management
- GitHub OAuth app configured

### What's Missing

**Question**: How does a user's GitHub token get associated with spec execution?

Possible flows:
1. **User-level token**: User connects GitHub once, token stored in User model
2. **Project-level token**: Each project has its own GitHub connection
3. **Organization-level token**: Org-wide GitHub App installation

### Required Investigation

- [ ] Does User model have `github_access_token` field?
- [ ] Is there a `GitHubConnection` or similar model?
- [ ] How does OAuth callback store the token?
- [ ] Is the token encrypted at rest?

### Required Changes

1. **Store GitHub token securely**:
```python
class User(Base):
    # ... existing fields ...

    # GitHub OAuth token (encrypted)
    github_access_token: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        comment="Encrypted GitHub access token from OAuth"
    )
    github_username: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        comment="GitHub username"
    )
```

2. **Token refresh flow** (GitHub tokens expire)

3. **Scope validation** (need repo write access)

---

## Gap 3: Spec Execution → Sandbox Spawning

### Current State (BROKEN)

From `sandbox-execution.md`:

```python
# specs.py - CURRENT (runs in API process!)
@router.post("/{spec_id}/execute")
async def execute_spec(...):
    working_dir = request.working_directory or os.getcwd()  # ❌ WRONG!
    await run_spec_state_machine(spec_id, working_dir, ...)  # ❌ Runs in API!
```

### What Should Happen

```python
@router.post("/{spec_id}/execute")
async def execute_spec(
    spec_id: str,
    db: DatabaseService = Depends(get_db_service),
    current_user: User = Depends(get_current_user),
):
    # 1. Load spec and project
    spec = await get_spec(db, spec_id)
    project = await get_project(db, spec.project_id)

    # 2. Get GitHub credentials
    github_token = await get_user_github_token(current_user)
    if not github_token:
        raise HTTPException(400, "GitHub not connected. Please connect GitHub first.")

    if not project.github_repo_url:
        raise HTTPException(400, "Project has no GitHub repository configured.")

    # 3. Spawn sandbox with GitHub context
    spawner = get_daytona_spawner()
    sandbox_id = await spawner.spawn_for_phase(
        spec_id=spec_id,
        phase="explore",
        project_id=spec.project_id,
        extra_env={
            "GITHUB_REPO": project.github_repo_url,
            "GITHUB_TOKEN": github_token,
            "GITHUB_REPO_OWNER": project.github_repo_url.split("/")[0],
            "SPEC_TITLE": spec.title,
            "USER_ID": str(current_user.id),
        },
    )

    # 4. Return sandbox reference for monitoring
    return SpecExecuteResponse(
        spec_id=spec_id,
        sandbox_id=sandbox_id,
        status="executing",
        current_phase="explore",
    )
```

### Files to Modify

| File | Change |
|------|--------|
| `specs.py` | Use `spawn_for_phase()` instead of direct execution |
| `daytona_spawner.py` | Ensure `spawn_for_phase()` handles spec context |
| `SpecExecuteRequest` | Add `project_id` (required), remove `working_directory` |

---

## Gap 4: Sandbox Progress Monitoring

### Current State

Monitoring infrastructure exists but isn't wired to spec execution:

| Service | Purpose | Spec Integration |
|---------|---------|------------------|
| `IdleSandboxMonitor` | Detects idle sandboxes | ❌ Not spec-aware |
| `IntelligentGuardian` | LLM trajectory analysis | ❌ Not spec-aware |
| `MonitoringLoop` | Orchestrates monitoring | ❌ Not spec-aware |
| Heartbeat system | 90s timeout | ✅ Works for any sandbox |

### What's Missing

1. **Spec-specific event types** (from `ui-and-events.md`):
```python
# Events the state machine should emit
SPEC_EVENTS = {
    "spec.execution_started",
    "spec.phase_started",
    "spec.phase_completed",
    "spec.phase_failed",
    "spec.phase_retry",
    "spec.execution_completed",
    "spec.sync_started",
    "spec.sync_completed",
}
```

2. **Link sandbox to spec**:
```python
# Need to track which sandbox is running which spec
class Sandbox(Base):
    # ... existing fields ...
    spec_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("specs.id"),
        nullable=True,
        comment="Spec being executed in this sandbox"
    )
```

3. **Spec progress endpoint**:
```python
@router.get("/{spec_id}/sandbox-status")
async def get_spec_sandbox_status(spec_id: str):
    """Get the sandbox status for a running spec."""
    # Find sandbox with this spec_id
    # Return heartbeat status, last event, phase progress
```

### Monitoring Flow

```
Spec Execution Started
    │
    ▼
Sandbox Spawned (spec_id linked)
    │
    ├── Heartbeats every 30s ──────────────────┐
    │                                          │
    ├── Work events (tool_completed, etc.) ────┤
    │                                          │
    ├── Spec events (phase_started, etc.) ─────┤
    │                                          ▼
    │                              IdleSandboxMonitor
    │                                   │
    │                                   ├── Heartbeat OK but no work? → IDLE
    │                                   ├── No heartbeat? → DEAD
    │                                   └── Work events? → ACTIVE
    │
    ▼
IntelligentGuardian (if enabled)
    │
    ├── Trajectory analysis
    ├── Alignment scoring
    └── Intervention if stuck
```

---

## Gap 5: PR Creation After Completion

### Current State

Tools exist but aren't automatically triggered:

| Component | Location | Status |
|-----------|----------|--------|
| `BranchWorkflowService.create_pull_request()` | `branch_workflow.py` | ✅ Exists |
| `GitHubApiService.create_pull_request()` | `github_api.py` | ✅ Exists |
| `pr-creator` skill | `sandbox_skills/` | ✅ Exists |
| `git-workflow` skill | `sandbox_skills/` | ✅ Exists |

### What's Missing

**Question**: What triggers PR creation after a spec completes?

**Option A: Agent Creates PR (Current)**
- Agent is told to create PR via skill/prompt
- Works but inconsistent - agent might forget

**Option B: Automatic PR Creation (Preferred)**
- When spec status → "completed"
- System creates PR automatically
- Links PR to spec in database

### Proposed Flow

```
All Spec Tickets Completed
    │
    ▼
SpecCompletionService.on_spec_complete(spec_id)
    │
    ├── 1. Verify all tickets are done
    │
    ├── 2. Get sandbox workspace (or re-spawn if needed)
    │
    ├── 3. Stage and commit changes
    │       git add -A
    │       git commit -m "feat: {spec.title}"
    │
    ├── 4. Push to branch
    │       git push origin {branch_name}
    │
    ├── 5. Create PR via GitHub API
    │       BranchWorkflowService.create_pull_request()
    │
    ├── 6. Update spec with PR URL
    │       spec.pull_request_url = pr_url
    │       spec.status = "pr_created"
    │
    └── 7. Notify user
            Event: spec.pr_created
```

### Required New Service

```python
# omoi_os/services/spec_completion_service.py

class SpecCompletionService:
    """Handles post-completion actions for specs."""

    async def on_all_tickets_complete(self, spec_id: str):
        """Called when all tickets for a spec are marked done."""
        spec = await self.get_spec(spec_id)
        project = await self.get_project(spec.project_id)
        user = await self.get_user(spec.user_id)

        # Create PR
        pr_url = await self.branch_workflow.create_pull_request(
            repo=project.github_repo_url,
            head=f"spec/{spec.id[:8]}",  # Branch name
            base=project.github_default_branch,
            title=f"feat: {spec.title}",
            body=self._generate_pr_body(spec),
        )

        # Update spec
        spec.pull_request_url = pr_url
        spec.status = "pr_created"
        await self.db.commit()

        # Notify
        await self.event_bus.publish(SystemEvent(
            event_type="SPEC_PR_CREATED",
            entity_type="spec",
            entity_id=spec_id,
            payload={"pr_url": pr_url},
        ))
```

---

## Gap 6: Branch Naming & Management

### Current State

`BranchWorkflowService` exists but spec integration is unclear:

```python
# branch_workflow.py
async def create_branch_for_ticket(self, ticket_id: str) -> str:
    """Create a feature branch for a ticket."""
    # Creates branch like: feature/TKT-123-title-slug
```

### What's Missing for Specs

1. **Branch naming for specs**: `spec/{spec_id_short}-{slug}`?
2. **One branch per spec or per ticket?**
3. **When is branch created?** At spec start? At first ticket?
4. **Branch cleanup** after PR merged?

### Proposed Branch Strategy

```
Spec Execution Starts
    │
    ▼
Create branch: spec/{spec.id[:8]}-{slugify(spec.title)}
    │
    ▼
Clone repo, checkout branch
    │
    ▼
Execute tickets (all work on same branch)
    │
    ▼
All tickets complete
    │
    ▼
Create PR: spec branch → main
    │
    ▼
PR merged
    │
    ▼
Delete spec branch (optional cleanup)
```

---

## Summary: All GitHub Integration Gaps

| # | Gap | Severity | Effort |
|---|-----|----------|--------|
| 1 | Project → GitHub repo connection | 🔴 CRITICAL | Medium |
| 2 | User → GitHub token storage | 🔴 CRITICAL | Medium |
| 3 | Spec execution → sandbox spawn | 🔴 CRITICAL | Low (code exists) |
| 4 | Sandbox → spec progress monitoring | 🟡 MEDIUM | Medium |
| 5 | Auto PR creation on completion | 🟡 MEDIUM | Medium |
| 6 | Branch naming/management | 🟢 LOW | Low |

---

## Implementation Priority

### Phase 1: Make It Work (Critical Path)
1. Add `github_repo_url` to Project model
2. Wire up user GitHub token retrieval
3. Fix `POST /specs/{id}/execute` to spawn sandbox
4. Pass GitHub env vars to sandbox

### Phase 2: Make It Observable
1. Add spec-specific event types
2. Link sandbox to spec in database
3. Add `/specs/{id}/sandbox-status` endpoint
4. Update UI to show sandbox progress

### Phase 3: Make It Complete
1. Add `SpecCompletionService`
2. Auto-create PR when all tickets done
3. Branch naming convention
4. PR template with spec summary

---

## Files to Create/Modify

### New Files
| File | Purpose |
|------|---------|
| `omoi_os/services/spec_completion_service.py` | Post-completion actions |
| `migrations/xxx_add_project_github_fields.py` | Add GitHub columns to Project |
| `migrations/xxx_add_spec_pr_fields.py` | Add PR tracking to Spec |

### Modify Files
| File | Change |
|------|--------|
| `omoi_os/models/project.py` | Add `github_repo_url`, `github_default_branch` |
| `omoi_os/models/spec.py` | Add `pull_request_url`, `branch_name` |
| `omoi_os/api/routes/specs.py` | Fix `/execute` to spawn sandbox |
| `omoi_os/workers/spec_state_machine.py` | Add event reporting |
| `omoi_os/services/daytona_spawner.py` | Ensure spec context passed |

---

## Open Questions

1. **Token storage**: Should GitHub tokens be stored encrypted? Using what method?
2. **Org vs User tokens**: Support GitHub App installations for orgs?
3. **Multiple repos per project**: Should a project support multiple GitHub repos?
4. **PR reviews**: Should the system wait for PR approval before marking spec "done"?
5. **Failed PRs**: What if PR creation fails? Retry? Notify user?
6. **Merge conflicts**: How to handle if the spec branch has conflicts with main?

---

## Related Documents

### Spec-Driven Development (This Directory)
- [sandbox-execution.md](./sandbox-execution.md) - Sandbox vs API process issue
- [ui-and-events.md](./ui-and-events.md) - Event reporting gap
- [impact-assessment.md](./impact-assessment.md) - Overall gap assessment
- [command-page-integration.md](./command-page-integration.md) - Entry point flow

### Sandbox Agent Architecture (Pre-existing)
- [../../docs/design/sandbox-agents/02_gap_analysis.md](../../docs/design/sandbox-agents/02_gap_analysis.md) - **Comprehensive** sandbox system gap analysis (mostly implemented!)
- [../../docs/design/sandbox-agents/03_git_branch_workflow.md](../../docs/design/sandbox-agents/03_git_branch_workflow.md) - Git branch workflow design

### UI/UX Flows (Pre-existing)
- [../../docs/page_flows/08c_github_integration.md](../../docs/page_flows/08c_github_integration.md) - GitHub OAuth and repo connection UI flows

### Integration Tests
- [../../tests/integration/sandbox/test_github_clone.py](../../tests/integration/sandbox/test_github_clone.py) - Tests for GitHub clone functionality
