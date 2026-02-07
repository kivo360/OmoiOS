# Live Preview System — Prototype Plan

**Author:** Kevin
**Status:** Implementation Plan
**Date:** 2026-02-07
**Prerequisite:** DAG merge + git integration gaps must be closed first
**Parent Docs:** [Live Preview Design Doc](../../../live-preview-design-doc.md), [Background Agent Design Doc](../../../background-agent-design-doc.md)

---

## Context

We have two design docs (Live Preview v2, Background Agent v1) describing a full live-preview and background-agent system. Analysis against `ARCHITECTURE.md` shows **~60% of the background agent doc describes what already exists** (TaskQueueService, DaytonaSpawner, EventBusService, Guardian, heartbeats). The genuinely new work is:

1. Preview URL rendering (Daytona `get_preview_link()` → iframe)
2. Prototyping sandbox mode (fast prompt → code → HMR loop)
3. Warm pool for <3s sandbox startup
4. Interactive mid-task agent sessions (ask_user, interrupt/resume)
5. Agent adapter abstraction (when we add a second agent)

This doc defines how to prototype each piece with **clear verification at every step** — nothing moves forward until the previous step demonstrably works.

---

## What We Skip (Already Exists)

| Design Doc Component | Current Equivalent | Action |
|---|---|---|
| `AgentRunner._execute_tool()` | MCP tools in sandbox worker | Reuse |
| `TaskQueue` (Redis sorted sets) | `TaskQueueService` (PostgreSQL, dynamic scoring) | Keep ours — it's better |
| `FileWatcher` (inotify) | `FileChangeTracker` in sandbox worker | Reuse |
| `AgentEvent` protocol | `SystemEvent` via `EventBusService` | Extend, don't replace |
| Heartbeat/health monitoring | `AgentHealthService` + `HeartbeatProtocolService` | Already mature |
| Guardian/trajectory analysis | `IntelligentGuardian` + `ConductorService` | Already built |
| Cloudflare Durable Objects | Redis pub/sub + WebSocket | Skip — no bottleneck |
| Separate `AgentRunner` process | `ClaudeSandboxWorker` | Refactor later if needed |

---

## Prototype Phases

### Phase 0: Proof of Concept — Preview URL Works (1 day)

**Goal:** Prove we can get a Daytona sandbox to serve a working preview URL with HMR.

**What to build:**
- A standalone test script: `scripts/test_preview_poc.py`
- Creates a public Daytona sandbox
- Scaffolds a Vite + React app inside it
- Writes the HMR-ready `vite.config.ts` (binds `0.0.0.0`, `clientPort: 443`, `protocol: 'wss'`)
- Starts the dev server via `sandbox.process.create_session()` + `execute_session_command()`
- Calls `sandbox.get_preview_link(3000)` and prints the URL
- Modifies a file via `sandbox.fs.upload_file()` to test HMR

**Verify:**
1. Run the script
2. Open the printed URL in a browser — see the rendered app
3. Script modifies `src/App.tsx` — browser hot-updates without full reload
4. All three must pass

**Key config to validate:**
```typescript
// vite.config.ts — must be exactly this for Daytona proxy
server: {
  host: '0.0.0.0',
  port: 3000,
  hmr: { clientPort: 443, protocol: 'wss' },
  headers: { 'X-Frame-Options': 'ALLOWALL' },
}
```

**Files:**
- `scripts/test_preview_poc.py` — the POC script
- No backend/frontend changes

---

### Phase 1: Backend Preview Routes + DaytonaSpawner Integration (2-3 days)

**Goal:** Wire preview URLs into the existing backend so any frontend task can expose a preview.

**What to build:**

1. **Database:** Add `preview_url` column to the existing sandbox/task tracking (or a lightweight `preview_sessions` table if we want clean separation)

2. **DaytonaSpawner changes** (`backend/omoi_os/services/daytona_spawner.py`):
   - After sandbox creation, detect if task involves frontend code (check `task.required_capabilities` for `['vite', 'next', 'react', 'vue', 'frontend']`)
   - If yes: write the HMR-ready config, start dev server, call `get_preview_link(port)`, store URL
   - Use `public=True` for dev/staging sandboxes

3. **API routes** (`backend/omoi_os/api/routes/preview.py`):
   ```
   POST   /api/v1/preview/           — Create preview for a sandbox
   GET    /api/v1/preview/{id}       — Get preview status + URL
   DELETE /api/v1/preview/{id}       — Stop preview
   GET    /api/v1/preview/sandbox/{sandbox_id} — Get preview by sandbox
   ```

4. **Event integration:** Publish `PREVIEW_READY` event via `EventBusService` when preview URL is available, so frontend can react in real-time

**Verify:**
1. Spawn a frontend task via existing API
2. `GET /api/v1/preview/sandbox/{sandbox_id}` returns `{ status: "ready", preview_url: "https://3000-..." }`
3. Open the URL — see the app
4. WebSocket client receives `PREVIEW_READY` event

**Files:**
- `backend/omoi_os/api/routes/preview.py` — new route file
- `backend/omoi_os/services/daytona_spawner.py` — extend with preview logic
- `backend/omoi_os/services/preview_manager.py` — lightweight service (optional, could be methods on DaytonaSpawner)
- Migration for `preview_url` column if using existing table

---

### Phase 2: Frontend Preview Panel (1-2 days)

**Goal:** Show the preview in an iframe on the existing sandbox detail page.

**What to build:**

1. **PreviewPanel component** (`frontend/components/preview/PreviewPanel.tsx`):
   - Props: `previewUrl`, `status`, `onRefresh`, `onStop`
   - States: loading spinner (pending/starting), iframe (ready), error with retry button
   - Iframe sandbox: `allow-scripts allow-same-origin allow-forms allow-popups`
   - Toolbar: URL display, refresh button, stop button, open-in-new-tab button

2. **API hook** (`frontend/hooks/usePreview.ts`):
   - `usePreview(sandboxId)` — React Query hook polling preview status
   - Listens for `PREVIEW_READY` WebSocket event to invalidate cache

3. **Integration into sandbox page** (`frontend/app/(app)/sandbox/[sandboxId]/page.tsx`):
   - Add a "Preview" tab alongside existing event view
   - Only show tab when preview is available or starting

**Verify:**
1. Navigate to a sandbox page for a frontend task
2. See "Preview" tab appear
3. Click it — iframe loads the live app
4. Agent modifies a file — HMR updates the iframe in <2s
5. Click refresh — iframe reloads
6. Click stop — preview stops, tab shows "stopped" state

**Files:**
- `frontend/components/preview/PreviewPanel.tsx`
- `frontend/hooks/usePreview.ts`
- `frontend/lib/api/preview.ts` — API client functions
- Modify `frontend/app/(app)/sandbox/[sandboxId]/page.tsx`

---

### Phase 3: Prototyping Mode (3-4 days)

**Goal:** A separate UI for fast prompt → code → preview iteration outside the spec pipeline.

**What to build:**

1. **Backend — PrototypeManager service** (`backend/omoi_os/services/prototype_manager.py`):
   - `start_session(user_id, framework)` — creates sandbox from snapshot, starts dev server, returns preview URL
   - `apply_prompt(session_id, prompt)` — sends prompt to a lightweight Claude agent that edits files in the sandbox (HMR handles the rest)
   - `export_to_repo(session_id, repo_url, branch)` — git init, commit, push prototype code
   - `end_session(session_id)` — cleanup sandbox

2. **Backend — Prototype routes** (`backend/omoi_os/api/routes/prototype.py`):
   ```
   POST   /api/v1/prototype/session              — Start session
   POST   /api/v1/prototype/session/{id}/prompt   — Apply prompt
   POST   /api/v1/prototype/session/{id}/export   — Export to repo
   DELETE /api/v1/prototype/session/{id}           — End session
   ```

3. **Snapshot creation script** (`scripts/build_prototype_snapshots.py`):
   - Create snapshots for: `react-vite`, `next`, `vue-vite`
   - Each has deps pre-installed, HMR config baked in, dev server ready to start
   - Run once, record snapshot IDs in config

4. **Frontend — Prototype page** (`frontend/app/(app)/prototype/page.tsx`):
   - Split layout: prompt input (left) + live preview iframe (right)
   - Framework selector dropdown
   - Code panel (optional, read-only view of generated files)
   - "Export to Repo" button

**Verify:**
1. Go to `/prototype`
2. Select "react-vite", click "Start"
3. See preview iframe load with default Vite app in <15s (cold) or <3s (warm)
4. Type "Add a navbar with dark mode toggle" → see it render in <10s
5. Type "Make the hero section have a gradient background" → see it update
6. Click "Export to Repo" → see code pushed to a branch
7. End session → sandbox cleaned up

**Files:**
- `backend/omoi_os/services/prototype_manager.py`
- `backend/omoi_os/api/routes/prototype.py`
- `scripts/build_prototype_snapshots.py`
- `frontend/app/(app)/prototype/page.tsx`
- `frontend/components/prototype/PrototypeWorkspace.tsx`
- `frontend/hooks/usePrototype.ts`
- `frontend/lib/api/prototype.ts`

---

### Phase 4: Warm Pool (1-2 days)

**Goal:** Eliminate cold-start latency for prototyping sessions.

**What to build:**

1. **Warm pool logic** in `SandboxManager` or as extension to `DaytonaSpawner`:
   - `dict[str, list[str]]` mapping framework → list of pre-warmed sandbox IDs
   - Background task: after a sandbox is claimed, replenish the pool
   - Pool size: 2-3 per framework (configurable)
   - Sandboxes in pool have dev server already running

2. **Health check:** Periodic verification that pooled sandboxes are still alive (Daytona auto-stop can kill them)

3. **Metrics:** Log pool hit rate, cold start vs warm start latency

**Verify:**
1. Start prototype session — measure time to preview URL
2. Warm pool hit: <3s
3. Cold start (pool empty): <15s
4. Pool replenishes in background after claim
5. Stale sandbox in pool gets evicted and replaced

**Files:**
- Extend `backend/omoi_os/services/daytona_spawner.py` or new `backend/omoi_os/services/sandbox_pool.py`
- Config: `backend/config/default.yaml` — pool size settings

---

### Phase 5: Interactive Agent Sessions (3-4 days)

**Goal:** Users can watch agents work in real-time and interact mid-task.

**What to build:**

1. **`ask_user` MCP tool:** When agent calls this, emit a `QUESTION` event via EventBus and block execution until answer arrives

2. **Interrupt/resume API:**
   ```
   POST /api/v1/sandbox/{id}/interrupt  — pause agent
   POST /api/v1/sandbox/{id}/resume     — resume with optional new instruction
   POST /api/v1/sandbox/{id}/answer     — answer a pending question
   ```

3. **WebSocket per-session filtering:** Extend `WebSocketEventManager` to efficiently filter events by `sandbox_id` so the session interior page only gets relevant events

4. **Session Interior page** (`frontend/app/(app)/sandbox/[sandboxId]/session/page.tsx`):
   - Left panel: Agent activity feed (reuse `EventRenderer`)
   - Right panel tabs: Terminal (xterm.js), Preview (iframe), Files (diff viewer)
   - Question prompt: When `QUESTION` event arrives, show input field
   - Interrupt/resume buttons in toolbar

5. **Terminal integration:** Wire xterm.js (already in `package.json`) to sandbox process output via WebSocket

**Verify:**
1. Start a task, open session page
2. See events stream in real-time as agent works
3. Agent asks a question → prompt appears → answer it → agent continues
4. Click interrupt → agent pauses → click resume → agent continues
5. Terminal tab shows live command output
6. Preview tab shows live app (if frontend task)

**Files:**
- `backend/omoi_os/sandbox_skills/` — add `ask_user` tool
- `backend/omoi_os/api/routes/sandbox.py` — extend with interrupt/resume/answer
- `frontend/app/(app)/sandbox/[sandboxId]/session/page.tsx`
- `frontend/components/session/SessionInterior.tsx`
- `frontend/components/session/AgentActivityFeed.tsx`
- `frontend/components/session/TerminalView.tsx`
- `frontend/hooks/useAgentSession.ts`

---

### Phase 6: Agent Adapter Abstraction (2-3 days, deferred)

**Goal:** Extract Claude-specific code into an adapter so we can add OpenCode/Aider later.

**When to do this:** Only when we're ready to add a second agent. Not before.

**What to build:**
- `AgentAdapter` ABC in `backend/omoi_os/agents/adapter.py`
- `ClaudeAdapter` wrapping current `ClaudeSandboxWorker`
- `AgentAdapterRegistry` for discovery
- Config-based adapter selection per task

**Verify:**
- Run existing tasks with `ClaudeAdapter` — behavior unchanged
- Register a mock adapter — switch to it in config — see it execute
- Add real second adapter (OpenCode) — see it work for a task

---

## Dependency Graph

```
Phase 0 (POC)
    │
    ▼
Phase 1 (Backend routes)
    │
    ├───▶ Phase 2 (Frontend panel)
    │         │
    │         ▼
    │    Phase 5 (Interactive sessions) ──▶ Phase 6 (Adapters, deferred)
    │
    ▼
Phase 3 (Prototyping mode)
    │
    ▼
Phase 4 (Warm pool)
```

Phases 2 and 3 can run in parallel after Phase 1. Phase 5 depends on Phase 2 (needs the preview panel). Phase 6 is deferred.

---

## Blocking Prerequisite: DAG + Git Integration

Before starting Phase 1, the following gaps from `docs/architecture/14-integration-gaps.md` should be closed:

- **CoordinationService** — not initialized anywhere (needed for parallel task execution)
- **ConvergenceMergeService** — not initialized anywhere (needed for branch merging)
- **SandboxGitOperations** — needs end-to-end testing with real repos
- **Branch workflow** — verify agent creates branch → commits → pushes → creates PR

These are foundational. Preview rendering builds on top of working sandbox execution with git. If git operations are flaky, preview debugging becomes impossible.

---

## Success Metrics

| Metric | Target | How to Measure |
|---|---|---|
| Preview URL availability | >95% of frontend sandbox tasks get a working URL | Log `PREVIEW_READY` events vs frontend task count |
| HMR latency | <2s from file write to browser update | Timestamp in file write event vs browser devtools |
| Prototype session start | <3s (warm), <15s (cold) | Timer from API call to preview URL response |
| Prompt-to-visual | <10s for simple prompts | Timer from prompt submit to HMR update |
| Warm pool hit rate | >80% during active usage | Pool claim vs cold start ratio |
| Interactive session reliability | Zero dropped WebSocket connections during task | Monitor WS disconnect events |

---

## Open Questions (Carry Forward)

1. **Framework auto-detection** — Should we read `package.json` to pick framework, or require explicit selection? (Leaning: auto-detect with manual override)
2. **Snapshot rebuild cadence** — Weekly? On dependency bumps? (Leaning: weekly cron + manual trigger)
3. **Warm pool cost** — Need to measure $/sandbox/hour for idle Daytona instances to set pool size
4. **Prototyping agent model** — Sonnet for speed? Or full Claude Code for quality? (Leaning: Sonnet for prototype, Claude Code for spec tasks)
5. **Multi-file prototyping** — Full repo context or single-file focus? (Leaning: start with single-file, add repo context as needed)
