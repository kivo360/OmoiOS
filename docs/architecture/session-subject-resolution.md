# Session Subject Resolution

**Created**: 2026-04-24
**Status**: Approved
**Purpose**: Documents how runtime code (orchestrator, Daytona spawner, task
queue, access-control checks) resolves a session's owning org, user, repo,
and environment — uniformly across ticket-driven legacy sessions and
SDK-direct ticket-less sessions introduced by migration 071.

## Why this exists

Before migration 071, every `Task` (= Session per spec §17) was required to
point at a `Ticket`. The workflow, the orchestrator, the spawner, and the
task queue all walked the same relationship chain to get the facts they
needed:

```
task -> task.ticket
       -> task.ticket.project
          -> project.organization_id
             project.github_owner / github_repo
             project.created_by
       -> ticket.user_id
```

That chain was both the FK constraint that forced ticket creation before an
SDK caller could make a session, and the ambient assumption baked into five
services. The decoupling plan broke the FK (`tasks.ticket_id` is now
nullable) and promoted the key facts to direct columns on `tasks` + new
GitHub columns on `workspaces`. But every consumer still needs the same
unified view, so we funnel all reads through a single resolver.

## The two entry points

```
    SDK call                            Dashboard workflow
    POST /sessions                      POST /tickets
    {workspace_id | github_repo,        {github_owner, github_repo,
     prompt}                             title, description, ...}
        │                                     │
        ▼                                     ▼
    ensure_workspace_for_github_repo      ensure_project_for_github_repo
        │                                     │
        ▼                                     ▼
    Task(ticket_id=None,                  Ticket(project_id=...) ────►
         workspace_id=...,                Task(ticket_id=...,
         environment_version_id=...,           workspace_id=None,
         created_by=..., github_repo=...)      ... all direct cols null)
        │                                     │
        └──────────────────┬──────────────────┘
                           ▼
                    SessionSubject.resolve(task)
                           │
        ┌──────────────────┼──────────────────────────────┐
        ▼                  ▼                              ▼
    orchestrator       daytona_spawner              task_queue
    env extraction     branch / auth-token          org concurrency
```

Both paths converge on the same `SessionSubject` dataclass. No service
reads `task.ticket.project.*` directly anymore — there's exactly one
resolver, `omoi_os.services.session_subject.resolve`.

## Field precedence

For each field, the resolver returns the first non-null source:

| Field                     | 1st (SDK-direct)        | 2nd (workspace)           | 3rd (legacy ticket chain)                  | 4th (default)     |
|---------------------------|-------------------------|---------------------------|--------------------------------------------|-------------------|
| `organization_id`         | —                       | `workspace.organization_id` | `ticket.project.organization_id`           | `None`            |
| `workspace_id`            | `task.workspace_id`     | —                         | —                                          | `None`            |
| `environment_version_id`  | `task.environment_version_id` | —                   | —                                          | `None`            |
| `github_owner/repo`       | `task.github_repo` (parsed) | `workspace.github_owner/repo` | `ticket.project.github_owner/repo`     | `None, None`      |
| `user_id_for_token`       | `task.created_by`       | —                         | `ticket.project.created_by` → `ticket.user_id` | `None`            |
| `title`                   | `task.title`            | —                         | `ticket.title`                             | `f"session-{id}"` |
| `description`             | `task.description`      | —                         | `ticket.description`                       | `""`              |
| `priority`                | `task.priority`         | —                         | `ticket.priority`                          | `"MEDIUM"`        |
| `ticket_id`               | `None`                  | —                         | `task.ticket_id`                           | `None`            |
| `ticket_type`             | `None`                  | —                         | derived from priority/title                | `None`            |

The four shapes covered by the unit table-test (`tests/unit/services/test_session_subject.py`):

- **(a) SDK-direct**: `workspace_id + github_repo + created_by` set; `ticket_id=None`.
- **(b) Workflow-full**: `ticket_id + ticket.project` populated; direct columns null.
- **(c) Ticket-only**: `ticket_id` set, `ticket.project_id=None`, `ticket.user_id` provides ownership.
- **(d) Orphan**: nothing set — falls through to defaults.

## verify_task_access precedence

The API dependency `verify_task_access` mirrors the same "direct first,
legacy second" philosophy but for ACL rather than data. Five steps, first
match wins:

1. **SessionACL grant** — spec §07 multiplayer (`owner` / `editor` / `viewer`).
2. **Workspace org membership** — `task.workspace_id → workspace.organization_id ∈ user's orgs`.
3. **Direct ownership** — `task.created_by == current_user.id`.
4. **Legacy ticket chain** — delegates to `verify_ticket_access`.
5. **Deny** — 403.

The ordering matters: an explicit SessionACL grant takes precedence over
workspace-org membership so a session shared cross-workspace still obeys
its grants. Direct ownership sits between workspace and ticket so a
ticket-less session's creator is always reachable, even without an ACL row.

## Why direct columns, not a new table

Three alternatives were considered:

1. **Direct nullable columns on `tasks`** (chosen). Minimal blast radius,
   reversible via `alembic downgrade -1`, zero dual-writes across tables,
   and keeps every existing FK (`events`, `session_acls`, `session_forks`,
   `cost_records`, `task_memory`, ...) pointing at the same row.
2. Synthetic ticket per session. Doubles every workflow-irrelevant session
   into the `tickets` table, where `ticket_workflow` / `phase_gate` /
   `board` would try to advance it through phases — a subtle source of
   phantom board rows and spurious `phase_history` entries.
3. New `sessions` table. The "correct" greenfield answer, but requires
   dual-writing every lifecycle event during cutover plus a dozen FK
   re-points. Deferred to a later quarter; spec §17 §2 explicitly tells us
   to keep the DB name `tasks` indefinitely.

The fallback chain handles historical rows (which have `ticket_id NOT
NULL AND workspace_id IS NULL`) identically to the pre-decoupling
codepath. No backfill is needed — and running one would only add a
migration window and derivation-bug risk.

## Files

- `backend/omoi_os/services/session_subject.py` — the dataclass + `resolve()`
- `backend/omoi_os/workers/orchestrator_worker.py` — `_extract_session_env` consumer
- `backend/omoi_os/services/daytona_spawner.py` — narrow touch: auth-token resolver + branch naming
- `backend/omoi_os/services/task_queue.py` — `_resolve_organization_id` + concurrency accounting
- `backend/omoi_os/api/dependencies.py` — `verify_task_access` precedence chain
- `backend/omoi_os/api/routes/sessions.py` — `SessionCreate` spec §03 body + `_create_ticketless_session`
- `backend/omoi_os/services/workspace_binding.py` — `ensure_workspace_for_github_repo` auto-bind
- `backend/migrations/versions/071_decouple_session_from_ticket.py` — the schema shift
- `tests/unit/services/test_session_subject.py` — table test over the four task shapes

## Related plans

- `.sisyphus/plans/session-ticket-decoupling.md` — the wave-structured
  implementation plan this doc realizes.
- `.sisyphus/plans/sessions-surface-spec-alignment.md` — the earlier plan
  that made sessions.py the canonical surface.
