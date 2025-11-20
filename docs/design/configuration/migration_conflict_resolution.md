# Migration Conflict Resolution

**Issue:** Two migration files both claim revision `003_*` with same parent:
- `003_agent_registry_expansion.py` — Revision: `003_agent_registry`, Parent: `002_phase1`
- `003_phase_workflow.py` — Revision: `003_phase_workflow`, Parent: `002_phase1`

This creates a branching migration tree, which Alembic cannot resolve automatically.

---

## Option 1: Linear Chain (Recommended)

Make `003_phase_workflow` depend on `003_agent_registry`:

```python
# In migrations/versions/003_phase_workflow.py

revision: str = "003_phase_workflow"
down_revision: Union[str, None] = "003_agent_registry"  # Changed from 002_phase1
```

**Migration Order:**
```
001_initial → 002_phase1 → 003_agent_registry → 003_phase_workflow
```

---

## Option 2: Use Branch Labels

Keep both as independent branches merging from `002_phase1`:

```python
# In migrations/versions/003_agent_registry_expansion.py
revision: str = "003_agent_registry"
down_revision: Union[str, None] = "002_phase1"
branch_labels: Union[str, Sequence[str], None] = ("registry",)

# In migrations/versions/003_phase_workflow.py
revision: str = "003_phase_workflow"
down_revision: Union[str, None] = "002_phase1"
branch_labels: Union[str, Sequence[str], None] = ("workflow",)
```

Then create a merge migration:

```bash
uv run alembic merge -m "merge_registry_and_workflow" 003_agent_registry 003_phase_workflow
```

**Migration Order:**
```
001_initial → 002_phase1 → [003_agent_registry]
                         ↘ [003_phase_workflow] ↘
                                                  004_merge
```

---

## Recommended Action

**Use Option 1** for simplicity since:
1. Agent registry changes are orthogonal to phase workflow
2. No conflicting table/column modifications
3. Linear history is easier to reason about

### Steps:
1. Update `003_phase_workflow.py` line 17:
   ```python
   down_revision: Union[str, None] = "003_agent_registry"
   ```

2. Verify migration chain:
   ```bash
   uv run alembic history
   ```

3. Test on fresh database:
   ```bash
   uv run alembic upgrade head
   ```

---

## Current Workaround

Tests pass because the test database is dropped/recreated each run, so Alembic never sees the conflict. However, production deployments or incremental migrations will fail.

**Status:** Safe for testing, **unsafe for production** until resolved.

