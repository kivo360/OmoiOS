# MEMORY.md — Proactive Session Memory

> **Read this at session start.** This file is the persistent brain across Claude Code sessions.
> It survives context loss, session boundaries, and compaction.
>
> Inspired by [halthelobster/proactive-agent](https://clawhub.ai/halthelobster/proactive-agent) WAL Protocol + Working Buffer patterns.

---

## How This Works

### Three-Tier Memory

| Tier | File | Purpose | Update Frequency |
|------|------|---------|------------------|
| **Active State** | `memory/working-buffer.md` | What's happening RIGHT NOW — current task, blockers, decisions | Every session, every significant decision |
| **Progress Log** | `memory/YYYY-MM-DD.md` | Daily raw capture — what was done, what was tried, what failed | During session |
| **Long-Term** | This file (`MEMORY.md`) | Curated project state, architecture decisions, where things stand | Periodically distilled from daily logs |

### WAL Protocol (Write-Ahead Log)

**The rule:** If a decision, correction, or important detail surfaces during a session, write it to `memory/working-buffer.md` BEFORE continuing work. Context will vanish. The working buffer won't.

**Triggers — scan every user message for:**
- Corrections: "actually...", "no, I meant...", "use X not Y"
- Decisions: "let's go with...", "skip that", "do X first"
- Architecture choices: "we should use...", "don't add..."
- Priorities: "this is blocking...", "do this before..."
- Names/values: specific IDs, URLs, branch names, config values

### Compaction Recovery

When a session starts with truncated context or `<summary>` tags:
1. Read `memory/working-buffer.md` — raw recent state
2. Read this file (`MEMORY.md`) — curated long-term state
3. Read today's daily log if it exists
4. Read `tasks/todo.md` — active work items
5. Read `tasks/lessons.md` — patterns to avoid

**Never ask "what were we doing?" — the memory files have it.**

---

## Project State

### OmoiOS — What It Is

Autonomous engineering platform. Users describe features → system plans them (spec-driven pipeline) → agents execute in Daytona sandboxes → PRs are produced. Multi-agent orchestration with monitoring, trajectory analysis, and self-correction.

### Architecture Summary (Current)

```
Frontend (Next.js 15) → Backend (FastAPI) → Daytona Sandboxes (Claude Agent SDK)
                              ↕
                    PostgreSQL + Redis + EventBus (WebSocket)
```

**Key reference:** `ARCHITECTURE.md` — the canonical architecture doc with deep-dive links.

### What's Built and Working

- Planning System: Spec-Sandbox state machine (EXPLORE → PRD → REQUIREMENTS → DESIGN → TASKS → SYNC)
- Execution System: OrchestratorWorker → DaytonaSpawner → ClaudeSandboxWorker
- Monitoring: IntelligentGuardian (trajectory), ConductorService (coherence), heartbeats
- Task Queue: PostgreSQL-based with dynamic priority scoring
- Event System: Redis pub/sub → WebSocket to frontend
- Frontend: ~94 pages, ShadCN UI, Kanban board, spec workspace, sandbox event viewer
- Auth: JWT + OAuth (GitHub/Google)
- Billing: Stripe integration with tier-based subscriptions
- Memory: Pattern RAG with pgvector embeddings

### What's NOT Built Yet (Known Gaps)

**Critical gaps (from `docs/architecture/14-integration-gaps.md`):**
- ~~`CoordinationService` — not initialized anywhere~~ **FIXED 2026-02-07**
- ~~`ConvergenceMergeService` — not initialized anywhere~~ **FIXED 2026-02-07**
- ~~`OwnershipValidationService` — not initialized anywhere~~ **FIXED 2026-02-07**
- ~~DAG merge system — designed but not wired end-to-end~~ **FIXED 2026-02-07 (87 tests)**
- Git workflow — branch creation → commit → push → PR needs E2E testing with real Daytona sandboxes

**New features (designed, not built):**
- Live preview rendering (Daytona preview URLs in iframe)
- Prototyping sandbox mode (fast prompt → code → HMR loop)
- Warm sandbox pool (snapshot-based <3s startup)
- Interactive agent sessions (ask_user, interrupt/resume)
- Agent adapter abstraction (multi-agent support)

---

## Active Workstreams

### 1. DAG + Git Integration — COMPLETE

**Status:** Done (2026-02-07)
**What was done:**
- Wired CoordinationService, ConvergenceMergeService, OwnershipValidationService into orchestrator_worker.py
- Updated ARCHITECTURE.md Service Availability Matrix
- Created test_dag_event_chain.py (7 tests: full 3-service event chain verification)
- Created test_dag_merge_e2e.py (12 tests: real git repos, real DB records, LocalGitSandbox adapter)
- All 87 DAG-related tests passing
- Commits: `402d3133`, `99e60e50`

### 2. Live Preview System (ACTIVE — DAG gaps closed, starting now)

**Status:** Design doc complete, prototype plan written, starting Phase 0
**Design docs:**
- `docs/design/live-preview/prototype-plan.md` — phased implementation plan
- Root-level design docs (live-preview-design-doc.md, background-agent-design-doc.md)

**Implementation order:**
1. Phase 0: POC script proving Daytona preview URLs work with HMR
2. Phase 1: Backend preview routes + DaytonaSpawner integration
3. Phase 2: Frontend PreviewPanel component
4. Phase 3: Prototyping mode (separate fast-iteration UI)
5. Phase 4: Warm pool for <3s startup
6. Phase 5: Interactive agent sessions

**Key insight from analysis:** ~60% of the Background Agent design doc describes existing infrastructure. Skip Cloudflare Durable Objects (use existing Redis + WebSocket). Skip Redis sorted set queue (our PostgreSQL queue is better). Skip Agent Adapter abstraction until we have a second agent.

### 3. Landing Page (PAUSED)

**Status:** Dark mode fixed, fake social proof removed, conversion optimization backlog exists
**Reference:** `tasks/todo.md` has detailed checklist
**Key metric:** 8s avg session, 23% scroll depth, 84% bounce rate (from PostHog)
**Next when resumed:** Headline clarity test, above-fold email capture, real social proof

---

## Architecture Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-07 | Skip Cloudflare Durable Objects for live preview v1 | Existing Redis pub/sub + WebSocket handles our scale. Adding CF edge layer is premature complexity. |
| 2026-02-07 | Keep PostgreSQL TaskQueueService, don't switch to Redis sorted sets | Our queue has dynamic scoring (age, deadline, blockers, retry penalty). Redis sorted sets would be a downgrade. |
| 2026-02-07 | Defer Agent Adapter abstraction until second agent is ready | YAGNI. Only Claude Agent SDK is used. Build the interface when OpenCode/Aider integration is imminent. |
| 2026-02-07 | DAG + git gaps must close before live preview work begins | Preview rendering requires reliable sandbox execution with working git operations. Without that foundation, debugging preview issues becomes impossible. |
| 2026-02-07 | Use `public=True` Daytona sandboxes for dev/staging previews | Simpler than managing auth tokens for iframe embedding. Production can use private sandboxes with `x-daytona-preview-token`. |

---

## Key Files Quick Reference

| What | Where |
|------|-------|
| Architecture overview | `ARCHITECTURE.md` |
| Backend-specific guide | `backend/CLAUDE.md` |
| Integration gaps | `docs/architecture/14-integration-gaps.md` |
| Current vs target arch | `docs/architecture/services/architecture_comparison_current_vs_target.md` |
| Live preview design | `docs/design/live-preview/prototype-plan.md` |
| Active tasks | `tasks/todo.md` |
| Lessons learned | `tasks/lessons.md` |
| Daily session logs | `memory/YYYY-MM-DD.md` |
| Working buffer | `memory/working-buffer.md` |
| Product vision | `docs/product_vision.md` |
| Frontend architecture | `docs/design/frontend/frontend_architecture_shadcn_nextjs.md` |
| DaytonaSpawner | `backend/omoi_os/services/daytona_spawner.py` |
| TaskQueueService | `backend/omoi_os/services/task_queue.py` |
| EventBusService | `backend/omoi_os/services/event_bus.py` |
| Orchestrator worker | `backend/omoi_os/workers/orchestrator_worker.py` |

---

## Session Protocol

### Starting a Session

1. Read `MEMORY.md` (this file) — project state, active workstreams, decisions
2. Read `memory/working-buffer.md` — what was happening most recently
3. Read `tasks/todo.md` — active checklist
4. Read `tasks/lessons.md` — mistakes to avoid
5. If resuming specific work: read the relevant daily log

### During a Session

- **WAL Protocol:** Write decisions/corrections to `memory/working-buffer.md` before acting on them
- **Track progress:** Update `tasks/todo.md` as items complete
- **Capture lessons:** When something fails unexpectedly, add pattern to `tasks/lessons.md`
- **Daily log:** Write significant actions to `memory/YYYY-MM-DD.md`

### Ending a Session

1. Update `memory/working-buffer.md` with current state and next steps
2. Mark completed items in `tasks/todo.md`
3. If new lessons learned: update `tasks/lessons.md`
4. If architecture decisions made: add to the ADL table in this file
5. Write daily log entry to `memory/YYYY-MM-DD.md`
