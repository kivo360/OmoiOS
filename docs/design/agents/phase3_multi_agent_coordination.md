# Phase 3 Parallel Agent Prompt – Multi-Agent Coordination (Weeks 5-6)

**Created**: 2025-11-20
**Status**: Draft
**Purpose**: Technical design/specification for implementing Phase 3 parallel multi‑agent coordination, covering roles, APIs, contracts, and testing strategy.
**Related**: docs/design/services/event_bus.md, docs/design/services/scheduler.md, docs/requirements/phase2_state_machine.md, docs/requirements/phase1_telemetry.md, docs/implementation_roadmap.md, agent_orchestration/README.md, docs/testing/contract_tests.md

---


Use this prompt to spin up **four specialized editor agents** who will implement Phase 3 concurrently. Copy the relevant role block when launching each agent. Every agent must follow TDD, keep changes isolated, and coordinate through the shared dependency notes below.

---

## Shared Context & Readiness Checklist
- Phase 2 (state machine, task generation, phase gates, context passing) is merged and stable.
- Phase 1 heartbeat + retry telemetry is flowing into Redis/Postgres so coordination metrics have data sources.
- Alembic migration `003_phase_workflow.py` is in sync; no outstanding migrations.
- `agent_orchestration` shared module (DTOs, enums, schemas) is the single source of truth for inter-agent data contracts.
- EventBus + Redis infrastructure from MVP is available locally via `docker-compose up`.
- Run `uv run pytest` before handing off to integration QA; run targeted test files continually.

## Global Deliverables
1. Capability-aware agent registry and discovery APIs.
2. Agent-to-agent messaging & handoff protocol over the event bus.
3. Scheduler/worker support for parallel execution with dependency DAG + resource locking.
4. Coordination templates (sync, split, join, merge) consumable by orchestrator + future monitor agents.
5. Tests covering services, APIs, migrations, and concurrency edge cases.

---

## Agent Role 1 – **Registry Squad (SchemaAgent + APIAgent)**
**Scope**
- Extend `omoi_os/models/agent.py` with `capabilities: list[str]`, `capacity`, `health_status`, `last_heartbeat`, and optional `tags`.
- Add Alembic migration adding these columns plus required indexes.
- Implement registry CRUD + search in `omoi_os/services/agent_health.py` or new `agent_registry.py`.
- Expose FastAPI endpoints under `omoi_os/api/routes/agents.py`: register, update capabilities, toggle availability, search best-fit agent.
- Seed fixtures for tests in `tests/conftest.py` if necessary.

**Dependencies**
- Consumes Phase 2 ticket/task schemas (read-only).
- Provides capability data to Collaboration + Parallel Execution squads.

**Tests**
- `tests/test_agent_registry.py`: model/migration integration, search ranking, validation errors.
- Update `test_agent_health.py` to cover new heartbeat metadata.

**Hand-offs**
- Publish capability delta events (`agent.capability.updated`) on EventBus for Collaboration Squad.
- Provide Python client (`AgentRegistryClient`) inside `agent_orchestration`.

---

## Agent Role 2 – **Collaboration Squad (EventBusAgent + ConversationAgent)**
**Scope**
- Define agent-to-agent event schemas (`agent.message.sent`, `agent.handoff.requested`, `agent.collab.started`) under `omoi_os/models/events.py` or new schema module.
- Extend `omoi_os/services/event_bus.py` with typed publish/subscribe helpers for these topics.
- Build collaboration service that handles messaging, thread persistence, and handoffs.
- Add REST/WebSocket endpoints under `omoi_os/api/routes/agent_collab.py` for sending messages, listing threads, and initiating handoffs.

**Dependencies**
- Requires capability metadata + registry client from Role 1 (import from `agent_orchestration`).
- Emits collaboration metrics consumed by Roles 3 & 4 (Phase 4 Monitor).

**Tests**
- `tests/test_agent_communication.py`: schema validation, publish/subscribe roundtrip, handoff workflow (mock scheduler call).
- Update `test_event_bus.py` to include new event types.

**Hand-offs**
- Provide message DTOs and topic constants to Roles 3 & 4.
- Document handoff callback contract in `agent_orchestration/README.md`.

---

## Agent Role 3 – **Parallel Execution Squad (SchedulerAgent + LockManagerAgent)**
**Scope**
- Implement dependency-graph resolver in `omoi_os/services/task_queue.py` (or new `scheduler.py`) that batches ready tasks using DAG evaluation.
- Add resource-locking subsystem (DB table + service) to prevent conflicting tasks; include optimistic retry/backoff logic.
- Update worker (`omoi_os/worker.py`) to spin up multiple concurrent runners bounded by configuration and lock ownership.
- Integrate registry data to select best-fit agent when multiple are available.

**Dependencies**
- Consumes capability search + collaboration events (to react to handoffs or declines).
- Requires existing retry/backoff logic from Phase 1; ensure compatibility.

**Tests**
- `tests/test_parallel_execution.py`: DAG scheduling, lock acquisition/failure, fairness under contention.
- `tests/test_worker_concurrency.py`: ensures worker respects lock + capacity constraints.

**Hand-offs**
- Emit telemetry (`scheduler.ready_tasks`, `lock.wait_time`) for Phase 4 Monitor.
- Expose scheduling API (Python + HTTP) for Coordination Patterns Squad.

---

## Agent Role 4 – **Coordination Patterns Squad (TemplateAgent + PlaybookAgent)**
**Scope**
- Create coordination primitives (sync point, split, join, merge) defined as reusable templates under `omoi_os/services/coordination.py`.
- Extend orchestrator to interpret these primitives when generating tasks (hook into Phase 2 task generation where needed).
- Provide configuration files (YAML/JSON) describing common patterns (e.g., review-feedback loop).
- Build simulation scripts/tests that exercise multi-agent flows end-to-end using new scheduler + messaging.

**Dependencies**
- Requires scheduler APIs & DAG capabilities from Role 3.
- Consumes collaboration topic schemas from Role 2 to trigger pattern-specific communications.
- Reads capability data from Role 1 to ensure each sub-task requests correct skill.

**Tests**
- `tests/test_coordination_patterns.py`: verify sync/join semantics, merge correctness, deadlock avoidance.
- `tests/test_e2e_parallel.py`: scenario-based tests using fixtures to mimic multiple agents.

**Hand-offs**
- Publish pattern documentation for future phases.
- Provide metrics spec (what to monitor per pattern) to Phase 4 squads.

---

## Communication & Integration Rituals
- Daily async sync: post updates in shared doc or Slack thread with status + blockers.
- Contract tests: before merging, run small cross-team scripts that validate registry client, messaging DTOs, and scheduler API compatibility.
- Shared fixtures: store sample capability/agent/task payloads under `tests/fixtures/phase3/`.
- Merge order suggestion:
  1. Registry migration + client (Role 1)
  2. Collaboration schemas/endpoints (Role 2)
  3. Scheduler/locks (Role 3)
  4. Coordination templates + E2E sims (Role 4)
- However, all four can develop in parallel so long as DTOs and interfaces are stubbed first; maintain feature flags if needed.

---

## Definition of Done (Phase 3)
- All four milestone deliverables implemented with passing unit/integration tests.
- Cross-squad contract tests green.
- Documentation updated (`docs/implementation_roadmap.md`, service READMEs).
- Telemetry hooks emitting data required by Phase 4 Monitor.
- No regressions in existing test suite (`uv run pytest`).
