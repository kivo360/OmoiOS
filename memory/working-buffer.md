# Working Buffer

> **Active working memory.** This is the WAL target — write here FIRST, respond SECOND.
> Read this at session start to recover context.

**Last Updated:** 2026-02-07
**Status:** ACTIVE

---

## Current Focus

**Workstream:** Architecture analysis + planning (not coding yet)
**Blocking next step:** DAG merge + git integration gaps must close before live preview work

## What Just Happened (2026-02-07)

1. Analyzed Live Preview Design Doc v2 and Background Agent Design Doc v1 against `ARCHITECTURE.md`
2. Found ~60% of Background Agent doc describes existing infrastructure (TaskQueue, DaytonaSpawner, EventBus, Guardian, heartbeats)
3. Identified genuinely new work: preview URLs, prototyping mode, warm pool, interactive sessions, agent adapters
4. Created prototype plan: `docs/design/live-preview/prototype-plan.md` — 6 phases with clear verification at each step
5. Decided to skip: Cloudflare DOs, Redis sorted set queue, Agent Adapter abstraction (premature), separate AgentRunner process
6. Set up proactive memory system (this file + MEMORY.md + daily logs)

## Decisions Made This Session

| Decision | Detail |
|----------|--------|
| DAG first, preview second | Kevin confirmed: close DAG + git gaps before starting live preview |
| Test Opus 4.6 on DAG | Kevin wants to see if Opus 4.6 can 1-shot the DAG + git integration work |
| Skip CF Durable Objects | Use existing Redis pub/sub + WebSocket — no bottleneck at current scale |
| Keep PostgreSQL TaskQueue | Dynamic scoring > Redis sorted sets |
| Defer Agent Adapter | YAGNI until second agent (OpenCode/Aider) is imminent |
| Proactive memory system | Adopted WAL Protocol + Working Buffer pattern from halthelobster/proactive-agent |

## Next Steps (Priority Order)

1. **DAG + Git Integration** — Close gaps from `docs/architecture/14-integration-gaps.md`:
   - Wire `CoordinationService` into orchestrator worker
   - Wire `ConvergenceMergeService` into orchestrator worker
   - E2E test branch → commit → push → PR workflow
   - E2E test parallel task merge via DAG
   - Kevin wants to attempt this as a 1-shot with Opus 4.6

2. **Live Preview Phase 0** — After DAG gaps closed:
   - Write `scripts/test_preview_poc.py`
   - Prove Daytona preview URL + HMR works end-to-end

3. **Live Preview Phases 1-5** — Follow `docs/design/live-preview/prototype-plan.md`

## Open Threads

- Landing page work is paused (dark mode fixed, fake social proof removed, conversion backlog in `tasks/todo.md`)
- PostHog metrics: 8s avg session, 23% scroll depth, 84% bounce rate — headline clarity is highest-leverage fix when resumed

## Files Modified This Session

- `docs/design/live-preview/prototype-plan.md` — NEW: phased implementation plan
- `MEMORY.md` — NEW: proactive session memory system
- `memory/working-buffer.md` — NEW: this file
- `memory/2026-02-07.md` — NEW: daily log
