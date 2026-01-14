# Spec-Driven Development - Comprehensive Status Report

**Created**: 2025-01-14
**Updated**: 2025-01-14 (Full Frontend Audit Completed)
**Purpose**: Complete status of ALL spec-driven development components including orchestrator lifecycle, sandbox management, and frontend integration

---

## Executive Summary

The spec-driven development system is **fully complete** with both backend and frontend integration for the GitHub/PR workflow. The core execution pipeline (Command Page → Spec → Sandbox → State Machine) is complete and working, including the full GitHub integration flow and real-time event monitoring.

### Recent Updates (2025-01-14)

1. **Real-time Events System** ✅
   - `getSpecEvents()` API function in `frontend/lib/api/specs.ts`
   - `useSpecEvents()` hook with 2-second polling in `frontend/hooks/useSpecs.ts`
   - `EventTimeline` component with live feed, pause/resume, auto-scroll
   - `PhaseProgress` + `PhaseProgressInline` components for visual phase tracking
   - Integrated into spec detail page (header + sidebar + execution tab)

2. **Command Page Direct Launch** ✅
   - `launchSpec()` API function in `frontend/lib/api/specs.ts`
   - `useLaunchSpec()` hook in `frontend/hooks/useSpecs.ts`
   - Command page now uses direct spec launch for `spec_driven` mode (bypasses tickets)
   - Redirects directly to spec detail page after launch

3. **GitHub Integration UI** ✅ (previously completed)
   - Branch/PR creation buttons in spec detail page
   - PR status display with links
   - Force PR option to skip task completion check

4. **Board/Ticket/Task Visualization Audit** ✅ (Audited 2025-01-14)
   - Board page (`/board/[projectId]/page.tsx`) - Full Kanban with drag-drop, real-time WebSocket events
   - Ticket detail page (`/board/[projectId]/[ticketId]/page.tsx`) - Tasks tab, commits, blocking info
   - Agent panel slides in for live task monitoring
   - `SpecTaskExecutionService` bridges Spec → Ticket → Task with `context.spec_id` tracking

---

## 1. Orchestrator & Sandbox Lifecycle Management ✅ COMPLETE

### 1.1 Sandbox Creation (`orchestrator_worker.py`)

The orchestrator is responsible for polling pending tasks and spawning sandboxes:

```
Task Queue (pending) → Orchestrator → Daytona Spawner → Sandbox
```

**Key Code**: `orchestrator_worker.py:300-1040`
- Polls `TaskQueueService.get_next_task_with_concurrency_limit()`
- Spawns sandboxes via `daytona_spawner.spawn_for_task()`
- Sets `task.sandbox_id` and `task.status = "assigned"`
- Publishes `SANDBOX_SPAWNED` event

### 1.2 Sandbox Termination

Three mechanisms for sandbox termination:

| Mechanism | Trigger | Code Location |
|-----------|---------|---------------|
| **Auto-Cleanup** | Sandbox completes/fails | `daytona_spawner.py:3003-3015` |
| **Idle Detection** | No work events for X minutes | `idle_sandbox_monitor.py:427-496` |
| **Stale Task Cleanup** | Tasks stuck in "assigned" for too long | `orchestrator_worker.py:1041-1120` |

**Idle Sandbox Monitor**:
- Runs in `orchestrator_worker.py:1122-1203`
- Checks for sandboxes with heartbeats but no work events
- Configurable via `IDLE_THRESHOLD_MINUTES` (default: 10)
- Extracts session transcript before termination
- Updates task status to `failed`

### 1.3 Lifecycle Events

The orchestrator subscribes to these events for coordination:

| Event | Purpose |
|-------|---------|
| `TASK_CREATED` | Wake up to spawn sandbox |
| `SANDBOX_agent.completed` | Free up concurrency slot |
| `SANDBOX_agent.failed` | Free up concurrency slot |
| `TASK_VALIDATION_FAILED` | Reset task for revision |

---

## 2. Spec Execution Flow ✅ COMPLETE

### 2.1 Entry Points

**A. Command Page (Ticket-Based)**
```
User → Command Page → createTicket(spec_driven mode) → Ticket → Task → Sandbox
```
- File: `frontend/app/(app)/command/page.tsx`
- Creates ticket with `workflow_mode: "spec_driven"`
- Backend spawns sandbox via orchestrator
- Frontend redirects to board page

**B. Direct Spec Execution**
```
User → Spec Detail Page → POST /specs/{id}/execute → Sandbox
```
- File: `backend/omoi_os/api/routes/specs.py`
- Spawns sandbox via `daytona_spawner.spawn_for_phase()`
- Runs `SpecStateMachine` inside sandbox

**C. Spec Launch Endpoint**
```
User → POST /specs/launch → Create Spec → Sandbox (if auto_execute=true)
```
- File: `backend/omoi_os/api/routes/specs.py`
- Creates spec and optionally starts execution
- Returns `sandbox_id` for tracking

### 2.2 Inside the Sandbox

The sandbox worker (`claude_sandbox_worker.py`) runs:
1. **Spec Mode**: `SpecStateMachine` with phases (EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC)
2. **Task Mode**: `AgentLoop` for implementation tasks

After SYNC phase, `SpecTaskExecutionService` converts `SpecTask` → `Task` + `Ticket` for execution.

---

## 3. GitHub Integration ✅ COMPLETE

### 3.1 Backend Components ✅

| Component | Status | Location |
|-----------|--------|----------|
| `Project.github_owner/repo` | ✅ Exists | `models/project.py` |
| `CredentialsService.get_github_credentials()` | ✅ Exists | `services/credentials.py` |
| `spawn_for_phase()` GitHub injection | ✅ Implemented | `services/daytona_spawner.py:750-850` |
| `Spec.branch_name/pull_request_url/number` | ✅ Implemented | `models/spec.py:131-145` |
| `SpecCompletionService` | ✅ Implemented | `services/spec_completion_service.py` |
| `POST /specs/{id}/create-branch` | ✅ Implemented | `api/routes/specs.py` |
| `POST /specs/{id}/create-pr` | ✅ Implemented | `api/routes/specs.py` |

### 3.2 Frontend Components ✅ (Implemented 2025-01-14)

| Feature | Status | Location |
|---------|--------|----------|
| **Spec interface PR fields** | ✅ Implemented | `frontend/lib/api/specs.ts` |
| **`createSpecBranch()` API function** | ✅ Implemented | `frontend/lib/api/specs.ts:500-504` |
| **`createSpecPR()` API function** | ✅ Implemented | `frontend/lib/api/specs.ts:510-518` |
| **`useCreateSpecBranch()` hook** | ✅ Implemented | `frontend/hooks/useSpecs.ts:383-393` |
| **`useCreateSpecPR()` hook** | ✅ Implemented | `frontend/hooks/useSpecs.ts:399-409` |
| **Branch Creation UI** | ✅ Implemented | Spec detail page right sidebar |
| **PR Creation UI** | ✅ Implemented | Spec detail page right sidebar + execution tab |
| **PR Status Display** | ✅ Implemented | Shows branch name and PR link with status |
| **Force PR Option** | ✅ Implemented | Skip task completion check |

### 3.3 UI Locations

**Right Sidebar - GitHub Section:**
- Shows current branch name if exists
- "Create Branch" button if no branch
- Shows PR link with status badge if PR exists
- "Create Pull Request" button if branch exists but no PR
- "Force Create PR" option to skip task check

**Execution Tab - GitHub Integration Card:**
- Appears when all tasks are complete (`executionStatus.is_complete`)
- Branch status display
- PR creation flow with clear CTAs

### 3.4 Implementation Reference (Historical)

```typescript
// frontend/lib/api/specs.ts - ADD THESE FUNCTIONS:

export interface CreateBranchResponse {
  success: boolean
  branch_name?: string
  error?: string
}

export interface CreatePRResponse {
  success: boolean
  pr_number?: number
  pr_url?: string
  error?: string
  already_exists?: boolean
}

export async function createSpecBranch(specId: string): Promise<CreateBranchResponse> {
  return apiRequest<CreateBranchResponse>(`/api/v1/specs/${specId}/create-branch`, {
    method: "POST",
  })
}

export async function createSpecPR(
  specId: string,
  force?: boolean
): Promise<CreatePRResponse> {
  return apiRequest<CreatePRResponse>(`/api/v1/specs/${specId}/create-pr`, {
    method: "POST",
    body: { force: force || false },
  })
}
```

```typescript
// frontend/hooks/useSpecs.ts - ADD THESE HOOKS:

export function useCreateSpecBranch(specId: string) {
  const queryClient = useQueryClient()
  return useMutation<CreateBranchResponse, Error, void>({
    mutationFn: () => createSpecBranch(specId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}

export function useCreateSpecPR(specId: string) {
  const queryClient = useQueryClient()
  return useMutation<CreatePRResponse, Error, { force?: boolean }>({
    mutationFn: ({ force }) => createSpecPR(specId, force),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: specsKeys.detail(specId) })
    },
  })
}
```

### 3.4 Spec Type Update Needed

```typescript
// frontend/lib/api/specs.ts - UPDATE Spec interface:

export interface Spec {
  // ... existing fields ...

  // GitHub/PR tracking (NEW)
  branch_name: string | null
  pull_request_url: string | null
  pull_request_number: number | null
}
```

---

## 4. Event Reporting ✅ COMPLETE

### 4.1 Spec Events via SandboxEvent

Events are stored in `sandbox_events` table with `spec_id` FK:
- `spec_id` column added in migration 052
- Events queryable via `GET /specs/{id}/events`

Event types:
- `spec.execution_started`
- `spec.phase_started`
- `spec.phase_completed`
- `spec.phase_failed`
- `spec.execution_completed`

### 4.2 Frontend Integration ✅ (Implemented 2025-01-14)

| Feature | Status | Location |
|---------|--------|----------|
| **`getSpecEvents()` API function** | ✅ Implemented | `frontend/lib/api/specs.ts` |
| **`useSpecEvents()` hook** | ✅ Implemented | `frontend/hooks/useSpecs.ts` |
| **`EventTimeline` component** | ✅ Implemented | `frontend/components/spec/EventTimeline.tsx` |
| **`PhaseProgress` component** | ✅ Implemented | `frontend/components/spec/PhaseProgress.tsx` |
| **`PhaseProgressInline` component** | ✅ Implemented | `frontend/components/spec/PhaseProgress.tsx` |
| **Integration in spec detail page** | ✅ Implemented | Header, sidebar, execution tab |

**EventTimeline Features:**
- Real-time polling (2s interval during execution)
- Pause/Resume functionality
- Auto-scroll to newest events
- New event highlighting with animation
- Event type icons and source badges
- Expandable/collapsible interface

**PhaseProgress Features:**
- Visual phase indicator (EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC)
- Completed phases (green checkmark)
- Current phase (blue, pulsing animation)
- Pending phases (gray)
- Failed phases (red)
- Tooltips with phase descriptions

---

## 5. Command Page Integration ✅ COMPLETE (Updated 2025-01-14)

### 5.1 Current Flow (Direct Spec Launch)

For `spec_driven` mode:
1. User selects `spec_driven` mode on command page
2. User enters feature description
3. Frontend calls `launchSpec()` directly (bypasses tickets)
4. Backend creates spec and spawns sandbox via `spawn_for_phase()`
5. Frontend redirects to spec detail page

For `quick_task` mode:
1. User selects `quick_task` mode
2. Frontend calls `createTicket()`
3. Redirects to sandbox page

### 5.2 Frontend Implementation ✅ (Implemented 2025-01-14)

| Feature | Status | Location |
|---------|--------|----------|
| **`launchSpec()` API function** | ✅ Implemented | `frontend/lib/api/specs.ts` |
| **`useLaunchSpec()` hook** | ✅ Implemented | `frontend/hooks/useSpecs.ts` |
| **Command page spec_driven handling** | ✅ Implemented | `frontend/app/(app)/command/page.tsx` |
| **Redirect to spec detail page** | ✅ Implemented | After successful launch |

### 5.3 Code Reference

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
  sandbox_id: string | null
  status: string
  message: string
}

export async function launchSpec(request: SpecLaunchRequest): Promise<SpecLaunchResponse> {
  return apiRequest<SpecLaunchResponse>("/api/v1/specs/launch", {
    method: "POST",
    body: request,
  })
}
```

```typescript
// frontend/app/(app)/command/page.tsx - spec_driven mode handling
if (selectedMode === "spec_driven") {
  const result = await launchSpecMutation.mutateAsync({
    title: prompt.slice(0, 100),
    description: prompt,
    project_id: selectedProject.id,
    auto_execute: true,
  })
  router.push(`/projects/${selectedProject.id}/specs/${result.spec_id}`)
}
```

---

## 6. Ticket/Task Visualization ✅ COMPLETE (Audited 2025-01-14)

### 6.1 Board Page (`/board/[projectId]/page.tsx`)

The Kanban board displays tickets in columns with full real-time functionality:

| Feature | Status | Notes |
|---------|--------|-------|
| Drag-and-drop ticket movement | ✅ | Uses `@dnd-kit/core` |
| WebSocket live updates | ✅ | `useBoardEvents()` hook |
| Running task indicators | ✅ | Green pulsing Bot icon on tickets |
| Agent panel slide-in | ✅ | Shows live sandbox output |
| Search and filtering | ✅ | Status, priority, text search |
| Batch task spawning | ✅ | "Start Processing" button |

**Real-time Events:**
- `TICKET_CREATED` - Toast notification
- `TASK_ASSIGNED` - Agent assigned notification
- `TASK_COMPLETED` - Success toast
- `TICKET_PHASE_ADVANCED` - Phase change notification
- `SANDBOX_SPAWNED` - Auto-opens agent panel

### 6.2 Ticket Detail Page (`/board/[projectId]/[ticketId]/page.tsx`)

Full ticket management with multiple tabs:

| Tab | Content | Status |
|-----|---------|--------|
| **Details** | Description, metadata, context summary | ✅ |
| **Comments** | Placeholder for future comments | ✅ (UI ready) |
| **Tasks** | Task list with status, agent assignment, sandbox links | ✅ |
| **Commits** | Linked commits with diff stats | ✅ |
| **Blocking** | Dependency visualization | ✅ (basic) |
| **Reasoning** | Agent diagnostic timeline | ✅ |

### 6.3 SpecTask → Ticket/Task Bridge

When specs complete the SYNC phase, `SpecTaskExecutionService` converts:

```
SpecTask (spec_tasks table) → Ticket + Task (tickets/tasks tables)
```

**Tracking Fields:**
- `Ticket.context.spec_id` - Links ticket to source spec
- `Task.result.spec_task_id` - Links task back to SpecTask
- `Task.result.spec_id` - Redundant spec reference for queries

**Ticket Naming:** `[Spec] {spec.title}` prefix identifies spec-created tickets

### 6.4 Data Flow

```
Spec Execution:
1. User launches spec (command page or spec detail)
2. Sandbox runs SpecStateMachine phases
3. SYNC phase calls SpecTaskExecutionService.execute_spec_tasks()
4. Service creates bridging Ticket with context.spec_id
5. Service converts each SpecTask → Task
6. Tasks appear in TaskQueueService for orchestrator pickup
7. Board page shows tickets with live task status
```

### 6.5 Current Gaps (Low Priority)

| Gap | Priority | Notes |
|-----|----------|-------|
| Spec→Ticket link in board UI | Low | Could show "From Spec: {title}" badge |
| SpecTask status sync back to spec page | Low | Spec detail shows SpecTasks, not bridged Tasks |
| Comments feature | Low | UI ready, backend pending |

---

## 7. Summary: What Works

### ✅ ALL COMPONENTS COMPLETE

| Component | Status |
|-----------|--------|
| Orchestrator task polling | ✅ |
| Sandbox spawning via Daytona | ✅ |
| Sandbox termination (auto + idle + stale) | ✅ |
| Sandbox lifecycle events | ✅ |
| Spec state machine execution | ✅ |
| SpecTask → Task/Ticket bridge | ✅ |
| GitHub credential injection to sandbox | ✅ |
| PR tracking fields on Spec model | ✅ |
| SpecCompletionService (branch/PR creation) | ✅ |
| Spec events endpoint | ✅ |
| Command page spec_driven mode | ✅ |
| **Frontend GitHub integration** | ✅ (2025-01-14) |
| **Branch/PR creation UI** | ✅ (2025-01-14) |
| **PR status display** | ✅ (2025-01-14) |
| **Real-time event feed (EventTimeline)** | ✅ (2025-01-14) |
| **Phase progress visualization** | ✅ (2025-01-14) |
| **Direct spec launch from command page** | ✅ (2025-01-14) |
| **Spec events API + hook** | ✅ (2025-01-14) |

### ⏳ OPTIONAL ENHANCEMENTS (Low Priority)

| Feature | Priority | Effort | Notes |
|---------|----------|--------|-------|
| Sandbox link in spec page | Low | 1 hour | Navigate to active sandbox during execution |
| Phase transition toasts | Low | 1 hour | Toast notifications when phases change |
| Error detail expansion | Low | 1 hour | Expandable error details in EventTimeline |
| Auto-PR trigger on task completion | Low | 1-2 hours | Automatically create PR when all tasks done |

---

## 7. Environment Variables Reference

### Orchestrator

| Variable | Default | Purpose |
|----------|---------|---------|
| `ORCHESTRATOR_ENABLED` | `true` | Enable/disable orchestrator loop |
| `MAX_CONCURRENT_TASKS_PER_PROJECT` | `5` | Concurrency limit |
| `STALE_TASK_CLEANUP_ENABLED` | `true` | Enable stale task cleanup |
| `STALE_TASK_THRESHOLD_MINUTES` | `3` | Time before task considered stale |
| `IDLE_DETECTION_ENABLED` | `true` | Enable idle sandbox detection |
| `IDLE_THRESHOLD_MINUTES` | `10` | Time before sandbox considered idle |
| `SANDBOX_RUNTIME` | `claude` | Worker runtime (claude vs openhands) |

### Daytona

| Variable | Default | Purpose |
|----------|---------|---------|
| `DAYTONA_SANDBOX_EXECUTION` | `true` | Enable sandbox execution mode |
| `DAYTONA_API_KEY` | - | Daytona API key |
| `DAYTONA_API_URL` | - | Daytona API URL |

---

## 8. Testing Checklist

### Manual E2E Test Flow

1. **Command Page → Spec Execution**
   - [ ] Select project with GitHub repo connected
   - [ ] Select "Spec-Driven" mode
   - [ ] Enter feature description
   - [ ] Click "Generate Spec"
   - [ ] Verify sandbox spawns (check logs)
   - [ ] Verify redirect to board page

2. **Spec Detail → PR Creation**
   - [ ] Navigate to spec detail page
   - [ ] Verify spec tasks are shown
   - [ ] Complete all tasks (or mark as complete)
   - [ ] Click "Create Branch" (when UI exists)
   - [ ] Verify branch created in GitHub
   - [ ] Click "Create PR" (when UI exists)
   - [ ] Verify PR created in GitHub
   - [ ] Verify `spec.pull_request_url` populated

3. **Idle Sandbox Termination**
   - [ ] Spawn a sandbox
   - [ ] Wait for idle threshold (10 min default)
   - [ ] Verify sandbox terminated
   - [ ] Verify task marked as failed

---

## Related Documentation

- [README.md](./README.md) - High-level status overview
- [github-integration-gap.md](./github-integration-gap.md) - GitHub integration details
- [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) - Original implementation plan
- `docs/design/sandbox-agents/IMPLEMENTATION_COMPLETE_STATUS.md` - Sandbox infrastructure
