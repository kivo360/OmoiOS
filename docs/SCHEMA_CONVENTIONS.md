# OmoiOS Database Schema Conventions

**Purpose:** Ensure consistency across parallel development contexts  
**Status:** MANDATORY for Phase 4 & 5 development

---

## Primary Key Conventions

### ✅ ALL IDs ARE VARCHAR (String), NOT INTEGER

**Reason:** UUIDs used throughout the system for distributed ID generation

```python
# ✅ CORRECT
from uuid import uuid4
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

id: Mapped[str] = mapped_column(
    String, primary_key=True, default=lambda: str(uuid4())
)

# ❌ WRONG — Never use Integer/Serial
id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
```

---

## Foreign Key Conventions

### All FKs Must Match Parent Type

```python
# ✅ CORRECT — FK to tasks.id (String)
task_id: Mapped[str] = mapped_column(
    String, ForeignKey("tasks.id"), nullable=False
)

# ✅ CORRECT — FK to agents.id (String)
agent_id: Mapped[str] = mapped_column(
    String, ForeignKey("agents.id"), nullable=False
)

# ❌ WRONG — Type mismatch
task_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("tasks.id")  # ← tasks.id is String!
)
```

---

## Existing Schema Reference

### Core Tables (All use String PKs)

**tickets:**
- `id: String` (UUID)

**tasks:**
- `id: String` (UUID)
- `ticket_id: String` FK → tickets.id

**agents:**
- `id: String` (UUID)

**events:**
- `id: String` (UUID)

### Phase 2 Tables (All use String PKs)

**phase_history:**
- `id: String` (UUID)
- `ticket_id: String` FK → tickets.id

**phase_gate_artifacts:**
- `id: String` (UUID)
- `ticket_id: String` FK → tickets.id

**phase_context:**
- `id: String` (UUID)
- `ticket_id: String` FK → tickets.id

### Phase 3 Tables (All use String PKs)

**agent_messages:**
- `id: String` (UUID)
- `from_agent_id: String` FK → agents.id
- `to_agent_id: String` FK → agents.id

**collaboration_threads:**
- `id: String` (UUID)
- `ticket_id: String` FK → tickets.id
- `task_id: String` FK → tasks.id

**resource_locks:**
- `id: String` (UUID)
- `locked_by_task_id: String` FK → tasks.id
- `locked_by_agent_id: String` FK → agents.id

### Phase 4 Tables (All use String PKs)

**monitor_anomalies:**
- `id: String` (UUID)

**alerts:**
- `id: String` (UUID)

---

## JSONB Field Conventions

### Use for Flexible/Nested Data

```python
# ✅ CORRECT
from sqlalchemy.dialects.postgresql import JSONB

metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
```

### Reserved Names

**NEVER use these as column names** (SQLAlchemy reserved):
- ❌ `metadata` — Use `message_metadata`, `thread_metadata`, etc.
- ❌ `type` — Use `record_type`, `message_type`, etc.

---

## Datetime Conventions

### Always Timezone-Aware

```python
# ✅ CORRECT
from sqlalchemy import DateTime
from omoi_os.utils.datetime import utc_now

created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),  # ← MUST have timezone=True
    nullable=False,
    default=utc_now  # ← Use omoi_os.utils.datetime.utc_now
)

# ❌ WRONG — Offset-naive datetime
from datetime import datetime as dt

created_at: Mapped[datetime] = mapped_column(
    DateTime,  # ← Missing timezone=True
    default=dt.utcnow  # ← Deprecated, use utc_now()
)
```

---

## Index Conventions

### Create Indexes for

Query Patterns:**
- Foreign keys (automatic in some DBs, explicit in migrations)
- Status/state fields (`status`, `severity`, etc.)
- Timestamp fields used in range queries
- JSONB fields with containment queries (use GIN index)

```python
# In migration file
op.create_index("ix_tasks_status", "tasks", ["status"])
op.create_index("ix_tasks_phase_id", "tasks", ["phase_id"])
op.create_index(
    "idx_tasks_dependencies",
    "tasks",
    ["dependencies"],
    postgresql_using="gin"  # ← For JSONB
)
```

---

## Naming Conventions

### Tables: Plural, Snake Case
- ✅ `tasks`, `agents`, `cost_records`, `guardian_actions`
- ❌ `Task`, `Agent`, `CostRecord`

### Columns: Snake Case
- ✅ `task_id`, `created_at`, `message_metadata`
- ❌ `taskId`, `createdAt`, `messageMetadata`

### Indexes: Prefixed
- `ix_` for regular indexes
- `idx_` for special indexes (GIN, composite)
- Example: `ix_tasks_status`, `idx_tasks_dependencies`

---

## Migration Conventions

### File Naming
```
{revision}_{description}.py

Examples:
001_initial_foundation_models.py
002_phase_1_enhancements.py
003_agent_registry_expansion.py
004_collaboration_and_locking.py
005_monitoring_observability.py
```

### Revision Chain (Linear)
```python
revision: str = "005_monitoring"
down_revision: Union[str, None] = "004_collab_locks"  # ← Previous revision
```

**Current Chain:**
```
001_initial
  ↓
002_phase1
  ↓
003_agent_registry
  ↓
003_phase_workflow
  ↓
004_collab_locks
  ↓
005_monitoring
  ↓
006+ (Phase 5 migrations)
```

---

## Quick Checklist for New Models

Before committing a new model, verify:

- [ ] PK is `String` with UUID default
- [ ] All FKs match parent table type (String)
- [ ] DateTime fields have `timezone=True`
- [ ] Default uses `utc_now` not `datetime.utcnow()`
- [ ] No reserved column names (`metadata` → `xxx_metadata`)
- [ ] JSONB fields for flexible data
- [ ] Expunge objects before returning from service methods
- [ ] Migration file created with proper down_revision
- [ ] Indexes on FK/status/timestamp fields

---

## Common Mistakes to Avoid

### ❌ Type Mismatches
```python
# WRONG
task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id"))

# RIGHT
task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.id"))
```

### ❌ Reserved Names
```python
# WRONG
metadata: Mapped[dict] = mapped_column(JSONB)

# RIGHT
record_metadata: Mapped[dict] = mapped_column(JSONB)
```

### ❌ Offset-Naive Datetimes
```python
# WRONG
from datetime import datetime
created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# RIGHT
from omoi_os.utils.datetime import utc_now
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), default=utc_now
)
```

---

## For Phase 5 Developers (Parallel Contexts)

**CRITICAL:** All your models MUST follow these conventions:

- ✅ cost_record.py: `task_id: Mapped[str]` not `Mapped[int]`
- ✅ guardian_action.py: `target_entity_id: Mapped[str]`
- ✅ task_memory.py: `task_id: Mapped[str]`
- ✅ All IDs: String with UUID default

**If you see FK type errors in tests, check:**
1. Is your FK column `String` or `Integer`?
2. Does it match the parent table's PK type?
3. Are you using `utc_now()` or deprecated `datetime.utcnow()`?

---

**This document is the source of truth for schema design.** 🎯

