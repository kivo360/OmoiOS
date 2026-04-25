# Agent Workspace Platform — Known Issues & Gotchas

## Critical Gotchas

### SQLAlchemy Reserved Words
- NEVER use `metadata` or `registry` as column names
- Use `change_metadata`, `item_metadata`, `config_metadata` instead
- Violation causes `InvalidRequestError` on import

### Service Initialization
- Two separate initialization points:
  - `api/main.py` — API server (25+ services)
  - `workers/orchestrator_worker.py` — background worker
- They run as separate processes, do not share state
- Check Service Availability Matrix in ARCHITECTURE.md

### Datetime Handling
- NEVER use `datetime.utcnow()` — naive datetime
- ALWAYS use `omoi_os.utils.datetime.utc_now()` — timezone-aware
- Database requires timezone-aware datetimes

### LLM Response Parsing
- NEVER manually parse JSON from LLM responses
- ALWAYS use `llm_service.structured_output()` with Pydantic model
- Handles streaming, validation, error cases

## Migration Safety
- Always test `alembic upgrade head` and `alembic downgrade -1`
- Never drop columns with data in same migration that adds replacement
- Use separate migrations for: add column → backfill → drop old

## Security Boundaries
- No plaintext credentials in any file (logs, errors, responses)
- No credential caching in Redis for v1 (fail-closed)
- No cross-workspace access patterns
- No WebSocket support in egress proxy v1

## Testing Requirements
- Must have 80%+ coverage on new code
- Must save evidence to `.sisyphus/evidence/`
- Must test both happy path and error cases
- Must verify feature flags guard all new routes

## DetachedInstanceError (CRITICAL — Wave 2 bug)

**Problem**: SQLAlchemy ORM objects returned from a service method after `with db.get_session() as session:` closes become **detached**. Any attribute access (`.id`, `.name`) triggers an expired-attribute reload → `DetachedInstanceError`.

**Symptom**: Tests fail with `sqlalchemy.orm.exc.DetachedInstanceError: Instance <X at 0xABC> is not bound to a Session; attribute refresh operation cannot proceed`.

**Fix**: Before `return` in any service method returning ORM objects:
```python
with db.get_session() as session:
    obj = session.query(...).first()  # or session.add(...); session.commit(); session.refresh(obj)
    session.expunge(obj)   # <-- REQUIRED before the block exits
    return obj

# For lists:
    items = session.query(...).all()
    for item in items:
        session.expunge(item)
    return items
```

Seen in: `environment_service.py`, `artifact_service.py` (both fixed in commit fcf5b92c).
Reference implementation: `backend/omoi_os/services/environment_service.py` lines 105-117, 132-141, 162-176, 285-299.

## Service DB construction pattern

There is no `get_database_service()` global. Services must lazily construct their own:
```python
def _get_db(self) -> DatabaseService:
    if self._db is None:
        from omoi_os.config import get_app_settings
        from omoi_os.services.database import DatabaseService
        settings = get_app_settings()
        self._db = DatabaseService(connection_string=settings.database.url)
    return self._db
```
Constructor allows injecting a DB for tests: `def __init__(self, db=None, encryption=None)`.

## Migration chain discipline

The migration chain (as of commit fcf5b92c):
```
060_add_spec_share_fields
  ↓
061_add_encrypted_api_key
  ↓
062_add_environments
  ↓
063_add_artifacts
  ↓
064_... (next Wave 3+)
```

When creating a new migration:
1. Read the CURRENT head: `uv run alembic heads`
2. Set `down_revision = "<current_head>"` in your migration file
3. Apply locally with `uv run alembic upgrade head` to verify
4. Test reversibility: `uv run alembic downgrade -1 && uv run alembic upgrade head`

## 2026-04-23 — Verification note

- `just test-unit` did not finish within two verification attempts in this environment (timed out at ~57% after 10 minutes); targeted `tests/unit/test_workspace_isolation.py` passed.

## 2026-04-23 — F4 scope fidelity verification

- F4 scope fidelity rejected: only Task 7 stayed within the strict file-isolation checklist; Tasks 3, 4, 5, 8, 10, and 12 had out-of-scope effective or working-tree changes.
- The required `main..HEAD` unaccounted-change command is empty because work is currently on local `main`; `origin/main..HEAD` exposes broad unrelated committed deltas, and the working tree has additional unaccounted test/service changes.
- Evidence saved to `.sisyphus/evidence/f4-scope-fidelity.txt`.
## 2026-04-24 — Broker runtime test isolation

- Initial runtime broker tests accidentally used the persisted `admin_user` fixture, which requires local Postgres on port 15432. Fixed by using a non-persisted admin `User` object so the unit route tests remain DB-independent.
