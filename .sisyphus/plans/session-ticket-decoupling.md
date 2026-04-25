# Session ↔ Ticket Decoupling

## TL;DR

> **Quick Summary**: Break the hard coupling between `sessions` and the internal `Ticket → Project → Task` workflow by (1) making `tasks.ticket_id` nullable, (2) promoting `workspace_id`, `environment_version_id`, `created_by`, and `github_repo` to first-class columns on `tasks`, (3) teaching the orchestrator + spawner + task_queue to read those columns first and fall back to the ticket chain, and (4) rewriting `POST /api/v1/sessions` to take `{workspace_id, prompt, environment_id?, github_repo?, metadata?}` with no ticket_id. Tickets and Projects remain the workflow/dashboard surface, unchanged; the spec §03 session create body finally works end-to-end from the SDK without hand-seeding a project + ticket in the DB. No DB renames, no schema drops, no touching `daytona_spawner.py` internals — purely additive columns + guarded fallbacks + one route body rewrite.
>
> **Deliverables**:
> - Migration 071: `tasks.ticket_id NULL`; add `workspace_id/environment_version_id/created_by/github_repo` columns + indexes
> - `SessionSubject` dataclass resolved once per task (direct columns → ticket fallback → defaults), consumed by orchestrator, spawner, task_queue
> - Rewritten `POST /api/v1/sessions` body (Pydantic `SessionCreateV2`) that **does not accept** `ticket_id` — keeps legacy field ignored with deprecation header
> - Workspace auto-bind from `github_repo` string (mirrors the existing project auto-create pattern, but on Workspace)
> - `verify_task_access` fallback chain: SessionACL → workspace org → legacy ticket chain
> - `TaskQueueService.get_organization_id_for_task()` reads `task.workspace_id.organization_id` first, falls back to `task.ticket_id → project.organization_id`
> - Python + TypeScript SDK `sessions.create()` signatures drop `ticket_id` (and `phase_id`, `priority`, `task_type`); legacy params removed
> - Smoke test `scripts/smoke_agent_platform.py` `session_create` phase runs against a plain API-key + workspace, no DB seeding
> - Doc: `docs/architecture/session-subject-resolution.md` explaining the fallback precedence
>
> **Estimated Effort**: Medium (~5 working days)
> **Parallel Execution**: YES — 5 waves
> **Critical Path**: Wave 1 (schema) → Wave 2 (runtime fallbacks) → Wave 3 (API body) → Wave 5 (SDK + smoke)

---

## Context

### Original Request
> The agent-workspace platform treats sessions as the primary surface (spec §03), but the current implementation couples sessions tightly to the `Ticket → Project → Task` workflow machinery. SDK users can't create a session without first hand-seeding org → project → ticket via direct DB writes. Map the coupling, propose a clean decoupling strategy.

### Discovery Findings (confirmed by grep + read, not speculation)

**Schema coupling — the FK chain forces ticket creation:**
- `backend/omoi_os/models/task.py:32-34` — `ticket_id: String, nullable=False, ForeignKey("tickets.id", ondelete="CASCADE")`. Every Task (= Session per spec §17 name-mapping) must point at a ticket.
- `backend/omoi_os/models/ticket.py:128-133` — `project_id: String, nullable=True, FK projects`. Technically nullable at DB level.
- `backend/omoi_os/models/ticket.py:119-125` — `user_id: UUID, nullable=True, FK users`. Direct ownership exists but is optional.
- `backend/omoi_os/models/project.py:32-37` — `organization_id: UUID, nullable=True, FK organizations`. Nullable, with a legacy warning path in `verify_project_access`.
- `backend/omoi_os/models/workspace.py:34-39` — **`Workspace.organization_id: UUID, nullable=False`**. This is the spec §02 `ws_` resource and it's always org-scoped. This is the right single-hop parent for org-scoping sessions.

**Access coupling — three forced hops before a session is visible:**
- `backend/omoi_os/api/dependencies.py:1233-1271` — `verify_task_access` → `verify_ticket_access` → `verify_project_access` → user must be a member of the project's org.
- `backend/omoi_os/api/dependencies.py:1089-1115` — `get_accessible_project_ids` returns `[]` if user has no org memberships.
- `backend/omoi_os/api/routes/tickets.py:113-118` — `list_tickets` returns empty if `accessible_project_ids` is empty, even if the user has tickets by direct `user_id` ownership (the `Ticket.user_id` path is not honoured in the list query).

**Runtime coupling — what actually reads ticket fields:**
- `backend/omoi_os/workers/orchestrator_worker.py:200-386` — `_determine_ticket_type`, `_build_fallback_context`, `_extract_ticket_env` read `ticket.title`, `ticket.description`, `ticket.priority`, `ticket.context`, `ticket.project.github_owner/github_repo`, `ticket.project.created_by`, `ticket.user_id`. The spawn env depends on these for:
  - `TICKET_ID`, `TICKET_TITLE`, `TICKET_DESCRIPTION`, `TICKET_TYPE`, `TICKET_PRIORITY` env vars
  - `GITHUB_REPO`, `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME` env vars (for git clone inside the sandbox)
  - `USER_ID` env var → used to look up `user.attributes['github_access_token']` for the sandbox
- `backend/omoi_os/services/daytona_spawner.py:404-406, 658-700` — reads `task.ticket_id` to compute a branch name (`feature/TKT-123-slug`) and pull ticket fields when the orchestrator didn't pre-populate env. Lines 777-778, 2167, 2291, 2652, 2775 thread `ticket_id` through spawn/agent env.
- `backend/omoi_os/services/task_queue.py:1766-1770, 1955-1983, 2131-2148` — org-level concurrency limits resolve org via `ticket → project → organization_id`.
- `backend/omoi_os/services/result_submission.py:434-453`, `diagnostic.py:660-779`, `dependency_graph.py:148-165`, `ticket_workflow.py` — all read ticket for workflow/dashboard features (phases, board, merges, PR publication).

**API coupling — where sessions.py demands ticket_id:**
- `backend/omoi_os/api/routes/sessions.py:82-94` — `SessionCreate` requires `ticket_id: str` (non-optional).
- Line 312-363 — `create_session` delegates to `tasks_router.create_task(task_data)`, which at `routes/tasks.py:633` calls `await verify_ticket_access(task_data.ticket_id, ...)` and **hard-fails** if the ticket doesn't exist or is cross-org.
- Line 715-727 — `session_fork` copies `parent.ticket_id` to the child. If parent's ticket_id is null, this will now be fine; if it's set, the fork inherits it.
- All other session routes (`/messages`, `/share`, `/events`, `/artifacts`) go through `verify_task_access` which today walks the ticket chain.

**The "project = git repo" mapping (tickets.py:456-541):**
- When a ticket create carries `github_owner + github_repo` without `project_id`, the route auto-creates a Project with `github_owner/github_repo/github_connected=True/created_by=user.id/organization_id=first_user_org`.
- Existing match: `Project.github_owner == owner AND Project.github_repo == repo`, scoped by `(Project.created_by == user.id OR Project.organization_id IN user_orgs)`.
- This is the key pattern to preserve — it's the UX that "I point at a repo and get a workspace." We keep it on Tickets and **add the same pattern on Workspaces** so SDK sessions can bind a repo without creating a ticket.

**What the spec actually says (§03, §17, §18):**
- Spec §03 create body: `{workspace_id, environment_id, prompt, share_with, webhook_subscription, metadata}` — **no ticket_id**. Zero mention of tickets anywhere in the spec.
- Spec §17 §4 "task → session refactor (the cheap way)": keep the `tasks` DB table, add the spec-shaped create body on top, serialize task rows as `SessionResponse`. We've done that; we're now finishing the part §17 glossed over — the *input* body still demands ticket_id.
- Spec §18 §5 "metadata is opaque to the SDK": any workflow linkage (ticket_id, phase_id) belongs in `metadata`, not in the core create body. The SDK never changes when a client invents a new metadata schema.

### Metis Review

**Architectural trade-offs considered:**

1. **Direct nullable columns on `tasks` vs. synthetic ticket per session vs. new `sessions` table.** Synthetic tickets are clever but double-write every workflow-irrelevant session into a table the workflow engine then tries to advance through phases — a subtle source of phantom board rows and spurious phase_history entries. A new `sessions` table is the "correct" greenfield answer but requires dual-writing every lifecycle event to two tables during cutover, plus a dozen FK re-points across `events`, `session_acls`, `session_forks`, `cost_records`, `task_memory`, etc. **Decision**: additive nullable columns on `tasks`. Minimal blast radius, reversible, preserves all existing FKs, zero dual-writes. Spec §17 §2 already tells us to keep the DB name `tasks` indefinitely; we're just aligning the columns with the API shape.

2. **Workspace adopts git-repo binding vs. Project stays authoritative.** If we move `github_owner/github_repo` to Workspace now, we either (a) dual-write to both for every ticket create — brittle — or (b) break the dashboard's "project = repo" mental model. **Decision**: Workspace gets **optional** `github_owner/github_repo/github_connected` columns (same shape as Project), Project stays authoritative for workflow-driven tickets, spawner reads Workspace first → falls back to ticket.project. SDK session create with `github_repo` string auto-creates-or-binds a Workspace matching `(org_id, github_owner, github_repo)`; UI session create via ticket still auto-creates a Project. Two entry points, one runtime contract (the spawner gets GH info from wherever it finds it first).

3. **Multi-tenancy scope without tickets.** Four options: (a) `task.workspace_id → workspace.organization_id` — one hop, workspace is NOT NULL org; (b) add `task.organization_id` directly — denormalized, risk of drift; (c) keep ticket chain forever — defeats the purpose; (d) session ACL only — can't enforce org limits. **Decision**: (a). Workspace is the spec's `ws_` resource and its org_id is non-null by construction. When `task.workspace_id` is set, the org comes from the workspace; when it's null (legacy rows), fall back to `task.ticket_id → project.organization_id`. Both paths converge on `organization_id` for concurrency limits, audit, billing.

4. **verify_task_access fallback order.** SessionACL grants (from Wave 2 of the prior plan) already exist and bypass org membership. We need to preserve that path while adding workspace-based access. **Decision**: explicit precedence — (1) `SessionACL` grant (owner/editor/viewer) returns immediately; (2) `task.workspace_id → workspace.organization_id` in user's orgs returns access; (3) `task.created_by == current_user.id` returns access (direct ownership, mirrors `Ticket.user_id` pattern); (4) legacy `verify_ticket_access` chain for rows with `ticket_id IS NOT NULL`; (5) deny. Documented precedence means no ambiguity when a task has both a workspace and a ticket in different orgs (a case that shouldn't happen but is possible during cutover).

5. **Backfill strategy.** Two options: (a) run a one-shot backfill populating `task.workspace_id/created_by` from `ticket.project.organization_id` + `ticket.user_id` for all historical rows; (b) leave historical rows with null direct columns and rely on the fallback chain forever. **Decision**: (b). Backfill adds a migration window, risks derivation bugs, and gains nothing — the fallback chain handles legacy rows identically to the pre-decoupling codepath. New rows get direct columns; old rows walk the ticket chain exactly like today. We revisit backfill only if the fallback chain becomes a hot path that shows up in p99 latency.

**Risks logged:**
- **Orchestrator reads `ticket.project.github_owner/github_repo` lazy-loaded via `ticket.project` relationship.** If `task.ticket_id IS NULL`, that access path vanishes. ✅ Mitigated: Wave 2 Task 4 introduces `SessionSubject.resolve(task)` — single source of truth — that reads `task.workspace → workspace.github_owner` first, then `task.github_repo` column, then `ticket.project.github_owner`. Orchestrator calls `resolve()` once and gets a dataclass; no more relationship chasing.
- **`Task.dependencies` and parallel coordination logic in task_queue might read sibling tasks on the same ticket.** ✅ Verified: `dependencies` JSONB is self-contained (task_id-based), no ticket-scoped queries. Parallel tasks on the same session are rare and currently rely on `parent_task_id`, which is already session-level.
- **`ticket_workflow.py`, `board.py`, `phase_gate.py`, `approval.py`, `ticket_dedup.py` all assume every Task has a Ticket.** ✅ Verified: those services are invoked only from ticket-ful flows (the dashboard workflow). None is triggered by SDK session create. Wave 2 adds a guard: if `task.ticket_id IS NULL`, these services short-circuit with a `SessionWithoutTicketError` log-and-skip, not a 500.
- **`events.entity_id` is `task.id`, already session-scoped — no change needed.** ✅ Verified.
- **`sessions_api_v1` feature flag + `ticket_id` being a request field.** The current `SessionCreate` model has `ticket_id: str` (non-optional). Client SDKs already don't send it (they hand-roll HTTP or use workspace params) — meaning the SDKs' create path is currently broken for users without a hand-seeded ticket. ✅ Wave 3 fixes this by removing `ticket_id` from the input schema entirely.

---

## Work Objectives

### Core Objective
Let a caller with only a platform API key (`rpk_live_…`) and an org create a session with `POST /api/v1/sessions {workspace_id, prompt}` — no project, no ticket, no phase_id, no DB seeding — and have the sandbox boot, clone the repo declared on the workspace (if any), stream events via SSE, reply + fork + share work correctly, and get cleanly scoped by org for concurrency limits. All existing ticket-driven dashboard flows continue to work byte-identically.

### Concrete Deliverables
- Alembic migration `071_decouple_session_from_ticket.py`:
  - `ALTER TABLE tasks ALTER COLUMN ticket_id DROP NOT NULL`
  - `ADD COLUMN workspace_id UUID NULL REFERENCES workspaces(id) ON DELETE SET NULL`
  - `ADD COLUMN environment_version_id UUID NULL REFERENCES environment_versions(id) ON DELETE SET NULL`
  - `ADD COLUMN created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL`
  - `ADD COLUMN github_repo VARCHAR(511) NULL` (format: `owner/repo`, denormalized for the SDK-direct path)
  - Partial index `ix_tasks_workspace_active` on `(workspace_id, status)` where `workspace_id IS NOT NULL`
  - `ALTER TABLE workspaces ADD COLUMN github_owner VARCHAR(255) NULL, ADD COLUMN github_repo VARCHAR(255) NULL, ADD COLUMN github_connected BOOLEAN NOT NULL DEFAULT FALSE`
  - Unique partial index `ux_workspaces_org_repo` on `(organization_id, github_owner, github_repo)` where both github columns are non-null
- `backend/omoi_os/services/session_subject.py` — new module, `SessionSubject` dataclass + `resolve(task, session) -> SessionSubject` function (see Wave 2 Task 4)
- Updates to:
  - `backend/omoi_os/workers/orchestrator_worker.py` — `_extract_ticket_env` → `_extract_session_env` consuming `SessionSubject`
  - `backend/omoi_os/services/daytona_spawner.py` — the two `task.ticket_id` reads at lines 404-406 become `SessionSubject.title/description`; no internal rewrite
  - `backend/omoi_os/services/task_queue.py` — three `ticket.project_id → organization_id` lookups (lines 1766-1770, 1955-1983, 2131-2148) become `SessionSubject.organization_id`
  - `backend/omoi_os/api/dependencies.py` — `verify_task_access` precedence chain (ACL → workspace → created_by → ticket → deny)
  - `backend/omoi_os/api/routes/sessions.py` — new `SessionCreateV2` Pydantic model without `ticket_id`, new `create_session` body that directly instantiates a `Task` with `workspace_id + created_by + environment_version_id + github_repo`
  - `backend/omoi_os/api/routes/tickets.py` — unchanged; dashboard path still auto-creates project + ticket
  - `backend/omoi_os/services/workspace_binding.py` — new module, `ensure_workspace_for_github_repo(org_id, github_repo, created_by) -> Workspace` (mirrors the ticket auto-project pattern but scoped to workspaces)
- SDK changes:
  - `sdk/python/omoios/resources/sessions.py` — `create()` signature drops `ticket_id`, `phase_id`, `priority`, `task_type`; adds `github_repo: Optional[str] = None`, `metadata: Optional[dict] = None`. Method body no longer requires workspace_id when github_repo is provided
  - `sdk/typescript/src/resources/sessions.ts` — same
- Smoke test updates:
  - `scripts/smoke_agent_platform.py` phase `session_create` uses `OmoiOSClient.sessions.create(workspace_id=..., prompt=..., github_repo="owner/repo")` — no `sdk_prereqs_ticket` seeding
  - New phase `session_create_ticketless` asserts the session lands in `tasks` with `ticket_id IS NULL` and completes successfully
- Doc: `docs/architecture/session-subject-resolution.md` — 2-page explainer with precedence table + diagram

### Definition of Done
- [ ] `alembic upgrade head` and `alembic downgrade -1` both clean on a fresh DB and on a production-shape snapshot
- [ ] `just test-all` passes — no regression in ticket-driven suites
- [ ] `just check` passes (ruff + mypy + eslint + tsc)
- [ ] Smoke test: `session_create_ticketless` PASSes with only `OMOIOS_PLATFORM_API_KEY + DAYTONA_API_KEY` in env and **no hand-seeded tickets/projects**
- [ ] SDK e2e suites (`sdk/python/tests/test_e2e_spec_patterns.py`, `sdk/typescript/tests/spec-patterns.e2e.test.ts`) pass using the new ticket-less create
- [ ] Existing dashboard ticket → task flow produces rows with `task.ticket_id IS NOT NULL AND task.workspace_id IS NULL` (legacy shape) and the spawner still works end-to-end
- [ ] `POST /api/v1/tickets` + auto-project path preserved byte-identically (`git diff tickets.py` on the key section is an empty diff)
- [ ] `openapi.json`: `POST /api/v1/sessions` body schema no longer contains `ticket_id` (but accepts it with a deprecation field-level note if a client sends it, to avoid an immediate 422 for any lingering clients)

### Must Have
- `Task.ticket_id` nullable at DB level, with every existing read-site hardened against `None`
- `POST /api/v1/sessions` returns 201 with `ticket_id: null` for SDK-created sessions
- Workspace auto-bind: `SessionCreateV2 {workspace_id: None, github_repo: "owner/repo"}` resolves to an existing or freshly-minted Workspace scoped to the caller's org
- `verify_task_access` honors SessionACL → workspace-org → created_by → ticket-chain in that precedence
- Org concurrency limits apply to ticket-less sessions via `workspace.organization_id`
- Sandbox env contains `GITHUB_REPO`, `OMOIOS_WORKSPACE_ID`, `USER_ID`, `SESSION_ID` (not `TICKET_ID`) for ticket-less sessions; keeps `TICKET_ID` for ticket-ful ones
- `SessionSubject` dataclass is the single source of truth read by orchestrator + spawner + task_queue; no service directly accesses `task.ticket.project.*` anymore

### Must NOT Have (Guardrails)
- Do **not** rewrite `daytona_spawner.py` internals — the 3,866-line module is stable. Only the narrow `task.ticket_id` reads at lines 404-406 and the env-var population in `_extract_ticket_env` upstream get touched, via the `SessionSubject` adapter
- Do **not** rename the `tasks` DB table; no `sessions` table migration
- Do **not** deprecate `POST /api/v1/tickets` or the auto-project path — dashboard UX depends on it
- Do **not** backfill `task.workspace_id` / `task.created_by` for historical rows — the fallback chain handles them
- Do **not** drop `ticket_id` from the `tasks` column — just make it nullable
- Do **not** modify `Ticket` or `Project` schemas — the only schema touches are on `tasks` and `workspaces`
- Do **not** reroute `verify_ticket_access` or `list_tickets` — those stay ticket-first (the dashboard still needs them). Only `verify_task_access` gets the precedence chain
- Do **not** change spec §05 environment immutability — `environment_version_id` on tasks is pinned at create time; the direct column mirrors what `execution_config.environment_id` already resolved
- Do **not** include `<THINKING>`, `<TASK>`, or agent XML wrappers in code — spec-doc artifacts, not Python/TS syntax
- Do **not** introduce a new Pydantic v1/v2 model — use v2 throughout, matching existing code

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — all verification is agent-executed. Evidence saved to `.sisyphus/evidence/session-ticket-decoupling/task-{N}-{slug}.{ext}`.

### Test Decision
- **Framework**: pytest (backend + Python SDK), vitest (TS SDK), smoke test script
- **TDD**: RED → GREEN → REFACTOR per task
- **Integration surface**: mocked httpx for SDK unit tests; real local backend + real Daytona for SDK e2e and smoke test (per memory `feedback_agent_platform_smoke_test.md`)

### QA Policy
Every task MUST include agent-executed QA scenarios. Evidence:
- **Migration**: `alembic upgrade head` then psql `\d tasks` shows `ticket_id` as `null: true`, four new columns present, two new workspace columns present. `alembic downgrade -1` cleanly reverses.
- **SessionSubject unit**: pytest table test — seed (a) task with direct workspace_id + github_repo, (b) task with ticket+project, (c) task with only ticket (no project), (d) legacy task with only ticket_id. Assert resolved `organization_id`, `github_repo`, `created_by`, `title`, `description` for all four shapes.
- **Ticket-less session create**: curl with `Authorization: Bearer rpk_live_<key>` → `POST /api/v1/sessions {workspace_id, prompt}` → assert 201, `ticket_id: null` in response, row exists in `tasks` with `workspace_id NOT NULL AND ticket_id IS NULL`. Save curl -i output.
- **Workspace auto-bind**: curl `POST /api/v1/sessions {github_repo: "test/repo", prompt: "..."}` with no `workspace_id`; assert a Workspace row exists for `(org_id=apikey.org, github_owner='test', github_repo='repo')`; repeat — assert idempotent (same workspace reused).
- **Access control**: as user A in org X, create ticket-less session; as user B in org X, GET /sessions/{id} → 200; as user C in org Y, GET → 404.
- **Org concurrency**: seed workspace in org with `max_concurrent_agents=1`; create 2 ticket-less sessions; assert the 2nd is backpressured the same way ticket-ful sessions are. Save task_queue log lines.
- **Dashboard regression**: run `just test-integration backend/tests/integration/test_ticket_workflow.py` — no regression.
- **Smoke test**: `uv run python scripts/smoke_agent_platform.py --only session_create_ticketless,session_create,session_events,session_reply,session_fork,session_share --report .sisyphus/evidence/session-ticket-decoupling/smoke.json`. Expected: all PASS, zero regression from baseline.
- **SDK e2e**: `uv run pytest sdk/python/tests/test_e2e_spec_patterns.py -v` and `cd sdk/typescript && pnpm test tests/spec-patterns.e2e.test.ts`.

---

## Execution Strategy

### Wave Structure

```
Wave 1 — Schema [parallel where possible]
  ├─ Task 1: Alembic migration 071 (nullable ticket_id + new columns on tasks + workspace github columns)
  └─ Task 2: SQLAlchemy model updates (Task + Workspace)

Wave 2 — Runtime adapter [gated by Wave 1]
  ├─ Task 3: SessionSubject dataclass + resolve()
  ├─ Task 4: Orchestrator refactor — consume SessionSubject
  ├─ Task 5: Spawner narrow touch — replace the two task.ticket_id reads
  └─ Task 6: TaskQueueService.get_organization_id_for_task() fallback

Wave 3 — API + Access [gated by Wave 2]
  ├─ Task 7: SessionCreateV2 Pydantic model + create_session rewrite
  ├─ Task 8: Workspace auto-bind service (ensure_workspace_for_github_repo)
  └─ Task 9: verify_task_access precedence chain

Wave 4 — SDK surface [parallel, gated by Wave 3]
  ├─ Task 10: Python SDK sessions.create() signature refresh
  ├─ Task 11: TypeScript SDK sessions.create() signature refresh
  └─ Task 12: SDK types (Session.ticket_id becomes Optional[str])

Wave 5 — Tests + doc [gated by Wave 4]
  ├─ Task 13: Smoke test session_create_ticketless phase
  ├─ Task 14: SDK e2e for ticket-less Pattern B + C
  └─ Task 15: docs/architecture/session-subject-resolution.md

Final Verification Wave [sequential]
  ├─ F1: Full smoke test (ticket-less + ticket-ful paths coexist)
  ├─ F2: Dashboard regression (existing ticket workflow unchanged)
  └─ F3: OpenAPI schema diff (session create body no longer requires ticket_id)
```

### Dependency Matrix

| Task | Depends on | Blocks |
|------|-----------|--------|
| 1    | —         | 2, 3, 4, 5, 6, 7, 8 |
| 2    | 1         | 3, 4, 5, 6, 7, 8, 9 |
| 3    | 2         | 4, 5, 6, 9 |
| 4    | 3         | 13, F1 |
| 5    | 3         | 13, F1 |
| 6    | 3         | 13, F1 |
| 7    | 2, 9      | 10, 11, 13 |
| 8    | 2         | 7, 13 |
| 9    | 2, 3      | 7, 13, F1 |
| 10   | 7         | 13, 14 |
| 11   | 7         | 14 |
| 12   | 7         | 10, 11 |
| 13   | 4, 5, 6, 7, 9, 10 | F1 |
| 14   | 10, 11    | F1 |
| 15   | 3, 9      | F3 |

---

## TODOs

### Wave 1 — Schema

#### Task 1 — Alembic migration 071: decouple schema
**Files**: `backend/migrations/versions/071_decouple_session_from_ticket.py` (new)
**What**:
```python
# upgrade():
op.alter_column("tasks", "ticket_id", nullable=True)
op.add_column("tasks", sa.Column("workspace_id", PG_UUID(as_uuid=True),
              sa.ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True))
op.add_column("tasks", sa.Column("environment_version_id", PG_UUID(as_uuid=True),
              sa.ForeignKey("environment_versions.id"), nullable=True))
op.add_column("tasks", sa.Column("created_by", PG_UUID(as_uuid=True),
              sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
op.add_column("tasks", sa.Column("github_repo", sa.String(511), nullable=True))
op.create_index("ix_tasks_workspace_active", "tasks", ["workspace_id", "status"],
                postgresql_where=sa.text("workspace_id IS NOT NULL"))
op.create_index("ix_tasks_created_by", "tasks", ["created_by"],
                postgresql_where=sa.text("created_by IS NOT NULL"))

# workspaces: repo binding for the SDK-direct path
op.add_column("workspaces", sa.Column("github_owner", sa.String(255), nullable=True))
op.add_column("workspaces", sa.Column("github_repo", sa.String(255), nullable=True))
op.add_column("workspaces", sa.Column("github_connected", sa.Boolean(),
              nullable=False, server_default="false"))
op.create_index("ux_workspaces_org_repo", "workspaces",
                ["organization_id", "github_owner", "github_repo"],
                unique=True,
                postgresql_where=sa.text(
                    "github_owner IS NOT NULL AND github_repo IS NOT NULL"))
```
**QA**: `alembic upgrade head` on fresh DB + on prod-shape snapshot → `psql -c '\d tasks'` shows all five targeted columns. `alembic downgrade -1` reverts cleanly, restores `ticket_id NOT NULL`. Save both `\d` outputs to `.sisyphus/evidence/session-ticket-decoupling/task-1-schema.txt`.
**Must not**: Don't add FK with `ondelete="CASCADE"` on `workspace_id` — we want orphaned sessions to survive workspace deletion for audit. Don't default-backfill `github_connected=true` — only true when repo is bound.

#### Task 2 — SQLAlchemy model updates
**Files**: `backend/omoi_os/models/task.py`, `backend/omoi_os/models/workspace.py`
**What**: On `Task`:
- `ticket_id: Mapped[Optional[str]] = mapped_column(..., nullable=True, ...)`
- Add `workspace_id: Mapped[Optional[UUID]]`, `environment_version_id: Mapped[Optional[UUID]]`, `created_by: Mapped[Optional[UUID]]`, `github_repo: Mapped[Optional[str]]`
- Add relationship stubs `workspace: Mapped[Optional["Workspace"]] = relationship(...)`, `creator: Mapped[Optional["User"]] = relationship(foreign_keys=[created_by])`
- Keep `ticket: Mapped["Ticket"]` relationship but update Optional typing: `Mapped[Optional["Ticket"]] = relationship(...)`

On `Workspace`:
- Add `github_owner`, `github_repo`, `github_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")`

**QA**: `uv run python -c "from omoi_os.models import Task, Workspace; print(Task.__table__.c.keys()); print(Workspace.__table__.c.keys())"`. `uv run pytest backend/tests/unit/models/ -v`. Save to evidence.
**Must not**: Don't declare `workspace_id` as `nullable=False` in the mapping — DB column is nullable and mismatched ORM metadata will break `alembic check`. Don't shadow existing `ticket` backref.

### Wave 2 — Runtime adapter

#### Task 3 — SessionSubject dataclass + resolve()
**Files**: `backend/omoi_os/services/session_subject.py` (new)
**What**:
```python
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

@dataclass(frozen=True)
class SessionSubject:
    """Unified view of a task's session context — workspace, repo, org, user.

    Resolved once per task in the precedence order:
      1. Direct columns on `tasks` (workspace_id, environment_version_id,
         created_by, github_repo) — the spec-aligned path.
      2. Ticket chain (ticket.user_id, ticket.project.github_owner/repo,
         ticket.project.organization_id) — the legacy workflow path.
      3. Defaults (title/description from the task row, no GH, no org).

    Consumed by orchestrator_worker, daytona_spawner, task_queue — so no
    service ever threads `task.ticket.project.*` again.
    """
    task_id: str
    title: str
    description: str
    priority: str
    phase_id: Optional[str]
    context: dict
    organization_id: Optional[UUID]
    workspace_id: Optional[UUID]
    environment_version_id: Optional[UUID]
    user_id_for_token: Optional[UUID]       # who owns the GitHub OAuth token
    github_owner: Optional[str]
    github_repo: Optional[str]
    github_repo_slug: Optional[str]         # "owner/repo" for env var convenience
    ticket_id: Optional[str]                # preserved for back-compat env vars
    ticket_type: Optional[str]              # "hotfix" | "bug" | "feature" — ticket-only

def resolve(session, task) -> SessionSubject:
    """Reads a Task + its relationships inside an open SA session.

    MUST be called inside a DB session because it may traverse
    `task.workspace`, `task.ticket`, `task.ticket.project`.
    """
```
Implementation: check `task.workspace_id` first; if set, load workspace, read `workspace.organization_id/github_owner/github_repo`. Then check `task.github_repo` column for SDK-direct overrides. If `task.ticket_id` is set, load ticket + ticket.project, fill remaining blanks. `user_id_for_token` precedence: `task.created_by → ticket.project.created_by → ticket.user_id → None`. `ticket_type` only populated if `task.ticket_id IS NOT NULL`.

**QA**: Unit test table — four seeded task shapes:
- (a) SDK-direct: `workspace_id` set, `github_repo='foo/bar'`, `created_by=uid`, `ticket_id=None`
- (b) Workflow-full: `ticket_id` set with `ticket.project.github_owner='a', github_repo='b', organization_id=org`
- (c) Ticket-only: `ticket_id` set, `ticket.project_id=None`, `ticket.user_id=uid`
- (d) Orphan: `ticket_id=None, workspace_id=None, created_by=None` — all defaults

Assert resolved fields for each shape. Save to `.sisyphus/evidence/session-ticket-decoupling/task-3-subject.txt`.
**Must not**: Don't issue new DB queries — receive the `session` as a parameter and use `session.get(...)` so the caller controls transactions. Don't raise on missing data — return a SessionSubject with Nones; callers decide whether a missing field is fatal.

#### Task 4 — Orchestrator consumes SessionSubject
**Files**: `backend/omoi_os/workers/orchestrator_worker.py`
**What**: Replace `_extract_ticket_env(ctx, ticket, log)` (lines 297-386) with `_extract_session_env(ctx, subject: SessionSubject, log)`. The new function:
- Sets `TICKET_ID` only when `subject.ticket_id IS NOT NULL` (legacy rows keep the env var; new rows don't)
- Sets `SESSION_ID = ctx.task_id` unconditionally
- Sets `TICKET_TITLE/DESCRIPTION/PRIORITY/TYPE` from subject when ticket_id is set; otherwise uses `subject.title/description/priority` (which come from the Task row itself)
- Sets `GITHUB_REPO = subject.github_repo_slug`, `GITHUB_REPO_OWNER/NAME` from subject; `USER_ID = subject.user_id_for_token`
- Sets `OMOIOS_WORKSPACE_ID = subject.workspace_id` when present
- Refactor `_determine_ticket_type` to take `(priority, title)` so it's no longer ticket-specific
- Refactor `_build_fallback_context` to take `(ctx, subject)` and fold ticket block into conditional

**QA**: Unit test — two mocked subjects (ticket-ful and ticket-less); assert env vars emitted. Integration test — end-to-end launch of a ticket-less task + assert spawner receives `SESSION_ID`, no `TICKET_ID`, `GITHUB_REPO` present. Save to evidence.
**Must not**: Don't remove the TICKET_ID path outright — legacy rows still need it. Don't break the `_build_task_context` call sequence — it's the `TaskContextBuilder` integration.

#### Task 5 — Spawner narrow touch for SessionSubject
**Files**: `backend/omoi_os/services/daytona_spawner.py` (minimal edit)
**What**: At lines 404-406, replace:
```python
if task and task.ticket_id:
    ticket = session.get(Ticket, task.ticket_id)
    # ... use ticket.title / ticket.description
```
with:
```python
from omoi_os.services.session_subject import resolve as resolve_subject
subject = resolve_subject(session, task)
# ... use subject.title / subject.description
```
At lines 658-700 (branch naming), gate on `subject.ticket_id IS NOT NULL` — ticket-less sessions use a branch name derived from `subject.github_repo_slug + task_id[:8]` (e.g. `agent/foo-bar-a1b2c3d4`) instead of `feature/TKT-...`. Keep the rest of the 3,866-line module untouched.

**QA**: `uv run pytest backend/tests/unit/services/test_daytona_spawner.py -v` — no regression. Spawn a ticket-less sandbox in dev, assert the branch created is `agent/<repo>-<shortid>` shape; spawn a ticket-ful one, assert branch is `feature/TKT-...`. Save the two Daytona branch names to evidence.
**Must not**: Don't touch any other part of daytona_spawner.py. Don't rename the `extra_env` dict keys.

#### Task 6 — TaskQueueService org resolution
**Files**: `backend/omoi_os/services/task_queue.py`
**What**: Replace the three `ticket → project → organization_id` chains (lines 1766-1770, 1955-1983, 2131-2148) with a helper:
```python
def _resolve_organization_id(self, session, task: Task) -> Optional[str]:
    # Direct workspace path first
    if task.workspace_id:
        ws = session.get(Workspace, task.workspace_id)
        if ws and ws.organization_id:
            return str(ws.organization_id)
    # Legacy ticket chain
    if task.ticket_id:
        ticket = session.query(Ticket).filter(Ticket.id == task.ticket_id).first()
        if ticket and ticket.project_id:
            project = session.query(Project).filter(Project.id == ticket.project_id).first()
            if project and project.organization_id:
                return str(project.organization_id)
    return None
```
Use it in `get_organization_id_for_task` + the two concurrency-limit iterations. Keep `project_id` lookup for the per-project limit (only when project exists).

**QA**: Unit test — task in ticket-less workspace with `max_concurrent_agents=1`; enqueue 2 tasks; assert the 2nd waits. Task with ticket+project+org → same behavior. Save scheduler logs to evidence.
**Must not**: Don't break per-project concurrency limits — they still apply to ticket-ful tasks. Don't hold the DB session across async boundaries.

### Wave 3 — API + Access

#### Task 7 — SessionCreateV2 + route rewrite
**Files**: `backend/omoi_os/api/routes/sessions.py`
**What**: Introduce:
```python
class SessionCreateV2(BaseModel):
    """Spec §03-shaped session create. No ticket, no phase, no priority."""
    model_config = {"extra": "ignore"}  # tolerate legacy fields without 422

    workspace_id: Optional[UUID] = None
    environment_id: Optional[UUID] = None
    prompt: str = Field(..., min_length=1)
    github_repo: Optional[str] = Field(
        None, pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
    )
    share_with: list[UUID] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```
Rewrite `create_session`:
1. Resolve `org_id` from the auth context (platform key → `api_key.organization_id`; user JWT → first-org; session tok → its org)
2. If `workspace_id` is None and `github_repo` is set → `ensure_workspace_for_github_repo(org_id, github_repo, created_by)` (Task 8)
3. If `environment_id` is None → use `workspace.default_environment_id`; resolve latest `environment_version_id`
4. Insert `Task` directly (bypass `tasks_router.create_task`): `ticket_id=None`, `workspace_id=resolved_ws`, `environment_version_id=resolved_ev`, `created_by=current_user.id`, `github_repo=f"{ws.github_owner}/{ws.github_repo}" if ws.github_connected else github_repo`, `title=prompt[:100]`, `description=prompt`, `priority="MEDIUM"`, `phase_id="PHASE_IMPLEMENTATION"`, `task_type="implementation"`, `status="pending"`
5. Insert owner `SessionACL(task_id=task.id, user_id=current_user.id, role="owner")`
6. Upsert grants from `share_with` into `session_acls`
7. Mint the broker session token (existing `_mint_session_token_for_credentials` path) so agent-platform-gaps wiring still works
8. `queue.enqueue_task_row(task)` (queue picks up from DB — sessions.py already relies on this)
9. Return full session shape + `session_token` if minted

Keep the legacy `SessionCreate` model but have it raise a 410 Gone with `X-Deprecated: Use SessionCreateV2 shape`. On second thought — per the prior sessions plan's "no breaking changes" stance — route still accepts both shapes; if the body has `ticket_id`, log a warning and ignore it (the field is dropped on the way to the Task insert).

**QA**: curl ticket-less create → 201 with `ticket_id: null`. curl with legacy `{"ticket_id": "whatever", "workspace_id": "...", "title": "..."}` → 201 with ticket_id still null (ignored) + deprecation header. Save both curl -i outputs.
**Must not**: Don't delegate to `tasks_router.create_task` — it asserts `verify_ticket_access`. Don't skip the ACL owner grant — Wave 2 of the prior plan relies on it for `session/{id}/share`.

#### Task 8 — Workspace auto-bind service
**Files**: `backend/omoi_os/services/workspace_binding.py` (new)
**What**:
```python
async def ensure_workspace_for_github_repo(
    session,
    org_id: UUID,
    github_repo: str,          # "owner/repo"
    created_by: UUID,
) -> Workspace:
    """Idempotent: find-or-create a workspace bound to this repo within the org.

    Mirrors the auto-project pattern in tickets.py:456-541 but scoped to
    Workspace (the spec §02 resource) instead of Project (the workflow one).
    """
    owner, repo = github_repo.split("/", 1)

    # Exact match within org
    existing = await session.execute(
        select(Workspace).where(
            Workspace.organization_id == org_id,
            Workspace.github_owner == owner,
            Workspace.github_repo == repo,
        )
    )
    ws = existing.scalar_one_or_none()
    if ws:
        return ws

    # Create
    slug = f"{owner}-{repo}".lower()
    ws = Workspace(
        organization_id=org_id,
        name=github_repo,
        slug=slug,
        github_owner=owner,
        github_repo=repo,
        github_connected=True,
        settings={"source": "sdk-auto-bind", "created_by": str(created_by)},
    )
    session.add(ws)
    await session.flush()
    return ws
```
**QA**: Unit test — call twice with same inputs → same workspace_id. Call with repo slug that collides with an existing workspace in a different org → separate workspace created. Save query plans showing the `ux_workspaces_org_repo` index hit.
**Must not**: Don't create a Workspace in an org the caller isn't a member of — trust that `org_id` was resolved from auth. Don't auto-create a `default_environment_id` — that's a separate concern (env creation is admin-driven).

#### Task 9 — verify_task_access precedence chain
**Files**: `backend/omoi_os/api/dependencies.py`
**What**: Replace `verify_task_access` body with:
```python
async def verify_task_access(task_id, current_user, db):
    async with db.get_async_session() as s:
        task = (await s.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
        if not task:
            raise HTTPException(404, "Task not found")

        # 1. SessionACL grant (owner/editor/viewer)
        acl = (await s.execute(select(SessionACL).where(
            SessionACL.task_id == task_id,
            SessionACL.user_id == current_user.id,
        ))).scalar_one_or_none()
        if acl:
            return task_id

        # 2. Workspace org membership
        if task.workspace_id:
            ws = await s.get(Workspace, task.workspace_id)
            if ws and ws.organization_id in await get_user_organization_ids(current_user, db):
                return task_id

        # 3. Direct ownership (created_by)
        if task.created_by and task.created_by == current_user.id:
            return task_id

        # 4. Legacy ticket chain
        if task.ticket_id:
            await verify_ticket_access(task.ticket_id, current_user, db)
            return task_id

        # 5. Deny
        raise HTTPException(403, "You don't have access to this task")
```
**QA**: Matrix test — 5 scenarios (ACL, workspace, created_by, ticket, none) × (2 user states) = 10 assertions. Save results.
**Must not**: Don't short-circuit on `get_user_organization_ids` failures — let them raise. Don't silently degrade a `403` into a `404`.

### Wave 4 — SDK surface

#### Task 10 — Python SDK sessions.create() refresh
**Files**: `sdk/python/omoios/resources/sessions.py`, `sdk/python/omoios/types.py`
**What**:
```python
async def create(
    self,
    *,
    prompt: str,
    workspace_id: Optional[str] = None,
    environment_id: Optional[str] = None,
    github_repo: Optional[str] = None,       # "owner/repo"
    share_with: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
) -> Session:
    if not workspace_id and not github_repo:
        raise ValueError("Provide either workspace_id or github_repo")
    ...
```
Remove params: `ticket_id`, `phase_id`, `priority`, `task_type`, `title`, `description` (description derived from `prompt`).

Update `Session` Pydantic type: `ticket_id: Optional[str] = None`, `workspace_id: Optional[UUID] = None`, `github_repo: Optional[str] = None`.

**QA**: Unit test against mock httpx — assert wire body matches `{workspace_id, prompt, ...}`. e2e: `client.sessions.create(prompt="hello", github_repo="foo/bar")` returns `Session(ticket_id=None, workspace_id=<uuid>)`. Save test output.
**Must not**: Don't keep a `ticket_id` kwarg for "backward compat" — the SDKs were new in the prior plan; no v1 contract to preserve. Don't reintroduce `phase_id` on SDK surface.

#### Task 11 — TypeScript SDK sessions.create() refresh
**Files**: `sdk/typescript/src/resources/sessions.ts`, `sdk/typescript/src/types.ts`
**What**: Mirror Task 10. Method signature:
```ts
async create(params: {
  prompt: string
  workspaceId?: string
  environmentId?: string
  githubRepo?: string
  shareWith?: string[]
  metadata?: Record<string, unknown>
  idempotencyKey?: string
}): Promise<Session>
```
**QA**: vitest against mock node:http. Save output.

#### Task 12 — SDK type alignment
**Files**: same as Tasks 10-11
**What**: `Session.ticketId` becomes `Optional<string>` in both SDKs. Add `Session.workspaceId`, `Session.githubRepo`. Remove any required-on-create fields that the backend no longer expects.

### Wave 5 — Tests + doc

#### Task 13 — Smoke test session_create_ticketless
**Files**: `scripts/smoke_agent_platform.py`
**What**: New phase:
```python
async def phase_session_create_ticketless(ctx):
    """SDK-driven session create with NO hand-seeded ticket/project."""
    client = ctx.sdk_client
    session = await client.sessions.create(
        prompt="echo hello from a ticket-less session",
        github_repo="octocat/hello-world",  # auto-binds workspace
    )
    assert session.ticket_id is None
    assert session.workspace_id is not None
    # Drain a few events
    async for evt in client.sessions.events(session.id):
        if evt.type == "session_ended":
            break
    return Result(PASS, evidence={"session_id": session.id, "workspace_id": session.workspace_id})
```
Keep existing `session_create` phase (ticket-ful) for regression coverage.

**QA**: Run end-to-end with empty DB + only an org + api key. Save to `.sisyphus/evidence/session-ticket-decoupling/smoke-ticketless.json`.

#### Task 14 — SDK e2e for Pattern B + C (ticket-less)
**Files**: `sdk/python/tests/test_e2e_spec_patterns.py`, `sdk/typescript/tests/spec-patterns.e2e.test.ts`
**What**: Add `TestPatternB_SyncWait_Ticketless` and `TestPatternC_LiveStream_Ticketless` classes (mirrors in vitest). Each: create → consume events → assert terminal event. No DB seeding beyond org + api_key.

**QA**: Run against live backend + Daytona. Save pytest + vitest outputs.

#### Task 15 — Architecture doc
**Files**: `docs/architecture/session-subject-resolution.md` (new)
**What**: 2-page markdown explaining:
- The two entry points (SDK-direct vs. ticket-driven dashboard)
- SessionSubject precedence table (task.workspace → task.github_repo → task.ticket.project → defaults)
- verify_task_access precedence chain (ACL → workspace → created_by → ticket)
- Why we chose nullable columns over a separate table (link to Metis trade-off #1 above)
- ASCII diagram of the two creation paths converging on the same runtime contract

**QA**: `markdownlint` clean. Committed with the final wave.

---

## Final Verification Wave

### F1 — Full smoke test
Run both `session_create_ticketless` and `session_create` (ticket-ful) in the same smoke run. Expected: both PASS; spawner launches sandboxes in both cases; org concurrency limits respected uniformly. Save `.sisyphus/evidence/session-ticket-decoupling/f1-full-smoke.json`.

### F2 — Dashboard regression
Run the existing ticket workflow integration tests + do a manual pass through the dashboard (localhost:3000) creating a ticket from the Quick mode flow. Assert:
- Ticket appears on the board
- Auto-project was created for the GitHub repo
- Task spawned, sandbox booted with legacy `TICKET_ID` env set

Save screenshots + test output.

### F3 — OpenAPI schema diff
```bash
curl http://localhost:18000/openapi.json | jq '.paths."/api/v1/sessions".post.requestBody.content."application/json".schema' > after.json
# compare to a pre-plan copy
git diff .sisyphus/evidence/session-ticket-decoupling/openapi-before.json after.json
```
Assert: `ticket_id` is no longer in `required`; `workspace_id`, `environment_id`, `github_repo`, `prompt` appear; `prompt` is in `required`.

---

## Commit Strategy

One commit per task. Wave-level PRs land atomically. Commit format:
```
refactor(sessions): <task summary>

- <change 1>
- <change 2>

QA: <evidence file path>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

Wave 1 is mergeable independently (pure schema, no behavioral change — the fallback chain hasn't been invoked yet because no ticket-less rows exist). Wave 2 is mergeable after Wave 1 with no behavioral change for existing rows. Wave 3 is the first wave with user-visible effect — that's the cutover commit that flips the smoke test from GAP to PASS.

---

## Success Criteria

1. `scripts/smoke_agent_platform.py` `session_create_ticketless` phase = `PASS` with only `OMOIOS_PLATFORM_API_KEY + DAYTONA_API_KEY + an org` in the environment — zero hand-seeded tickets/projects
2. Existing `session_create` (ticket-ful) phase still = `PASS` — no dashboard regression
3. `verify_task_access` precedence chain documented + tested in all 5 scenarios
4. `SessionSubject` is the single reader of workflow-adjacent fields — `grep -rn "task\.ticket\.project" backend/omoi_os/services/ backend/omoi_os/workers/` returns only `session_subject.py` hits
5. `POST /api/v1/sessions` OpenAPI schema no longer lists `ticket_id` as required
6. Both SDKs' `sessions.create()` signatures take `{prompt, workspace_id?, github_repo?, ...}` — no `ticket_id` parameter
7. `alembic upgrade head` clean; `alembic downgrade -1` clean
8. `just check` + `just test-all` green
9. No regression in `backend/tests/integration/test_ticket_workflow.py` or the ticket-driven dashboard flow
10. Workspace auto-bind (`ensure_workspace_for_github_repo`) idempotent + org-scoped

---

## Out of Scope (Deferred)

- **Backfill** of `task.workspace_id/created_by/environment_version_id` for historical rows — fallback chain covers them; revisit only if the chain shows up in p99 latency
- **Dropping** `tasks.ticket_id` column — nullable is the end state for this plan; full removal is a multi-quarter deprecation
- **Deprecating** `POST /api/v1/tickets` or the auto-project path — dashboard still needs it
- **Moving** workflow logic (phase_gate, ticket_workflow, approval, board) to be session-first — they stay ticket-first
- **Renaming** `tasks` → `sessions` at the DB level — spec §17 says never, or scheduled window only
- **Changing** the `/api/v1/tasks/*` surface — legacy callers still need it; session surface owns its input schema
- **Migrating** `Project` to be workspace-backed — Project stays authoritative for workflow; Workspace is the spec §02 resource
- **Adding** `github_installation_id` / GitHub App binding to Workspace — that's the spec §04 credential-broker concern, covered by `agent-platform-gaps.md`
- **Per-metadata-field validation** on `session.metadata` — per spec §18 §5 metadata is opaque to the SDK and the API
- **Cross-org session sharing** — rejected by `verify_task_access` precedence; that's a separate governance concern
- **Extracting the session surface into a standalone deployable service** — see next section for the seam analysis that falls out of this plan

---

## Future Work: Session-Surface Extraction (informational, not in-scope)

Once this plan lands, the session surface is materially easier to extract
into its own deployable service. The prerequisite work is this plan; the
extraction itself is deferred.

**Seam after ticket-decoupling** (evidence from parallel exploration, 2026-04-24):
- `backend/omoi_os/api/routes/session_channel.py` has **zero** imports of
  `daytona_spawner`, `orchestrator_worker`, or `task_queue`. Its only DB
  write is `events` via `SessionEventEnvelope.emit()`. WS plane is already
  isolated at the code level.
- The four `tasks_router.*` delegations at `sessions.py:262, 303, 352, 457`
  vanish — this plan rewrites `create_session` to hit the DB directly and
  gives sessions.py its own list/get/patch queries.
- `tasks_router.list_tasks` INNER JOIN on `tickets` at `routes/tasks.py:495`
  stops being a constraint for sessions — sessions own their list query.
- Smoke baseline: **27 of 30** phases survive extraction today; **3** fail
  only because they hand-seed a ticket (`sdk_prereqs`, `session_create`,
  `idempotency_conflict`). Post this plan: **all 30** survive.

**Sharp edges to design around when the extraction is scheduled:**
1. `session_channel.py:49, 163` — `_rooms` is process-local; `cursor.moved`
   bypasses Redis (direct `sock.send_json()` at line 292). Multi-replica
   deployment silently fragments multiplayer. Fix: reroute `cursor.moved`
   through Redis pub/sub, or sticky-session routing at the LB.
2. `session_channel.py:133` — `_bridge_loop` psubscribes to the entire
   `events.*` firehose. At scale every replica receives every session's
   events. Fix: per-session channel naming `events.{session_id}` + matching
   publisher change.
3. `tasks` table co-owned by session service + monolith even after
   decoupling. Spec the contract (who writes which columns, lock protocol,
   schema migration coordination), or introduce a thin RPC
   (`task_queue.enqueue_session(...)`) so only the monolith writes.
4. `SessionSubject` (introduced by this plan) is cross-boundary — both the
   session service (create path) and the monolith orchestrator (spawn path)
   read it. Plan for a shared package (`omoios-shared`) when extracting.

**Before starting extraction**, re-verify the baseline with:
```bash
uv run python scripts/smoke_agent_platform.py \
  --only prereqs,org_setup,session_create,session_create_ticketless,\
session_get,session_reply,session_fork,session_share,idempotency_conflict \
  --report .sisyphus/evidence/session-extraction-baseline.json
```
Expected: 9 PASS, 0 FAIL. A missing or failing `session_create_ticketless`
means this plan isn't actually done.
