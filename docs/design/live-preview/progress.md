# Live Preview — Implementation Progress

**Created**: 2026-02-09
**Status**: In Progress (Backend complete, E2E testing pending)
**Purpose**: Track implementation progress and roadmap for live preview feature

---

## Summary

The live preview feature enables frontend tasks to automatically start a dev server in the sandbox and display it to the user via an iframe in the frontend. Three critical gaps were closed on Feb 8:

1. **Tasks never got `required_capabilities`** → `_is_frontend_task()` always returned false
2. **No preview status update endpoint** → worker couldn't signal readiness
3. **Worker had no dev-server startup logic** → preview never transitioned to READY

---

## What's Done

### Backend Implementation (Feb 8) — `81093c08`, `2a1e8aca`

| File | Change | Status |
|------|--------|--------|
| `services/task_queue.py` | Added `required_capabilities` parameter to `enqueue_task()` | Done |
| `api/routes/tickets.py` | Added `_detect_frontend_capabilities()` keyword matcher + wired into quick-mode and approval flows | Done |
| `api/routes/tasks.py` | Added capability detection to direct task creation API | Done |
| `services/daytona_spawner.py` | Moved `_is_frontend_task()` before sandbox creation, set `PREVIEW_ENABLED` env var, pre-store Daytona preview URL | Done |
| `api/routes/preview.py` | Added `POST /notify` endpoint for worker callbacks | Done |
| `workers/claude_sandbox_worker.py` | System prompt injection + `PreviewSetupManager` background class | Done |

### Tests (Feb 8) — `81093c08`

| File | Tests | Status |
|------|-------|--------|
| `tests/unit/test_frontend_capability_detection.py` | 17 tests (positive, negative, edge cases) | All passing |
| `tests/integration/test_preview_notify_route.py` | 9 tests (status transitions, URL logic, errors) | All passing |
| `tests/unit/workers/test_preview_setup.py` | 16 tests (init, find_frontend_dir, notify, prompt injection) | All passing |

### Endpoint Verification (Feb 9)

- `/notify` returns 404 for unknown sandbox — verified via curl
- `/notify` returns 422 for missing `sandbox_id` — verified via curl
- `/notify` correctly validates status before processing — verified

---

## What's Left

### E2E Testing (Next Session)

- [ ] Start OmoiOS frontend (resolve port conflict — another project was on 3000)
- [ ] Create frontend task from command page: "Build a React counter component with Tailwind"
- [ ] Verify `required_capabilities` populated on task in DB
- [ ] Verify backend logs: `[PREVIEW] Preview enabled`, `[PREVIEW] Preview session created`
- [ ] Verify `preview_sessions` table: `status=pending`, `preview_url` from Daytona SDK
- [ ] Wait for sandbox worker to start dev server
- [ ] Verify preview session transitions `PENDING → STARTING → READY`
- [ ] Verify frontend shows Preview tab with working iframe
- [ ] Negative test: Python-only task produces no capabilities, no preview session

### Bug Fixes / Polish (If E2E Reveals Issues)

- [ ] Debug any issues with Daytona `get_preview_link()` returning usable URLs
- [ ] Verify WebSocket event propagation (`PREVIEW_READY` → `usePreview` hook → tab auto-switch)
- [ ] Handle edge case: sandbox created but Daytona snapshot inactive (known issue — `97969353`)
- [ ] Address uncommitted change in `frontend/app/(auth)/callback/page.tsx`

### Future Improvements (Not Blocking)

- [ ] Add capability detection to spec-driven workflow task creation (currently only quick-mode + approval + direct API)
- [ ] Consider LLM-based detection for ambiguous cases (currently keyword-only)
- [ ] Warm pool for faster sandbox startup (<3s target from prototype plan)
- [ ] Interactive mid-task sessions (ask_user, interrupt/resume)
- [ ] Port configuration per-framework (Vite=5173, Next=3000, etc.)

---

## Architecture (How It Works)

```
Ticket created
  → _detect_frontend_capabilities() keyword-matches title/description
  → enqueue_task() with required_capabilities=["react", "component", "tailwind"]
  → Orchestrator claims task, spawns sandbox via DaytonaSpawner

DaytonaSpawner.spawn_for_task()
  → _is_frontend_task() checks required_capabilities on task
  → Sets PREVIEW_ENABLED=true, PREVIEW_PORT=3000 in sandbox env vars
  → Creates Daytona sandbox
  → _setup_preview_for_sandbox() creates PreviewSession(PENDING)
  → Gets preview URL from daytona_sandbox.get_preview_link(3000)
  → Pre-stores URL on preview_sessions record

Sandbox Worker starts
  → WorkerConfig detects PREVIEW_ENABLED, injects system prompt instructions
  → PreviewSetupManager launches in background (asyncio.create_task)
  → Agent builds frontend code, installs deps, starts dev server (via prompt)
  → PreviewSetupManager polls localhost:3000, detects server ready
  → Calls POST /api/v1/preview/notify with status="ready"

Backend /notify endpoint
  → Looks up PreviewSession by sandbox_id
  → Calls PreviewManager.mark_ready() with pre-stored URL
  → Publishes PREVIEW_READY event via EventBus

Frontend
  → usePreview hook polls for preview status, listens for PREVIEW_READY WebSocket event
  → PreviewPanel renders iframe with preview URL
  → Tab auto-switches to Preview when justBecameReady fires
```

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Keyword matching over LLM detection | Speed and cost — no API call needed, runs in <1ms |
| Pre-store Daytona URL server-side | Worker doesn't need URL construction logic; just signals "ready" |
| Dual dev-server strategy (prompt + fallback) | Primary: agent starts server via instructions. Fallback: PreviewSetupManager auto-starts if agent doesn't |
| No auth on `/notify` endpoint | Same pattern as `POST /sandboxes/{id}/events` — worker callbacks are trusted |
| 22-keyword frozenset | Covers React, Vue, Angular, Svelte, Next, Vite, Tailwind, HTML/CSS basics — expandable |

---

## Related Files

- Plan: `docs/design/live-preview/prototype-plan.md`
- Preview routes: `backend/omoi_os/api/routes/preview.py`
- Preview manager: `backend/omoi_os/services/preview_manager.py`
- Preview model: `backend/omoi_os/models/preview_session.py`
- Spawner: `backend/omoi_os/services/daytona_spawner.py`
- Worker: `backend/omoi_os/workers/claude_sandbox_worker.py`
- Capability detection: `backend/omoi_os/api/routes/tickets.py` (`_detect_frontend_capabilities`)
- Frontend hook: `frontend/hooks/usePreview.ts`
- Frontend panel: `frontend/components/preview/PreviewPanel.tsx`
