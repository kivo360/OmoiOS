---
id: TSK-002
title: Create Database Migration for Webhook Fields
status: pending
parent_ticket: TKT-001
estimate: S
created: 2025-12-29
assignee: null
dependencies:
  depends_on:
    - TSK-001
  blocks:
    - TSK-003
    - TSK-004
    - TSK-005
---

# TSK-002: Create Database Migration for Webhook Fields

## Objective

Create Alembic migration to add webhook_url columns to projects and tickets tables.

---

## Deliverables

- [ ] `backend/migrations/versions/xxx_add_webhook_url_fields.py`

---

## Implementation Notes

### Approach

1. Generate migration file with Alembic
2. Add upgrade logic for both columns
3. Add downgrade logic to remove columns
4. Test migration forwards and backwards

### Code Patterns

```bash
cd backend
uv run alembic revision -m "add_webhook_url_fields"
```

Migration content:
```python
def upgrade():
    op.add_column('projects', sa.Column('webhook_url', sa.String(2048), nullable=True))
    op.add_column('tickets', sa.Column('webhook_url', sa.String(2048), nullable=True))

def downgrade():
    op.drop_column('tickets', 'webhook_url')
    op.drop_column('projects', 'webhook_url')
```

### References
- Alembic documentation
- Existing migrations in backend/migrations/versions/

---

## Acceptance Criteria

- [ ] Migration runs without errors: `uv run alembic upgrade head`
- [ ] Migration is reversible: `uv run alembic downgrade -1`
- [ ] Existing data is preserved
- [ ] Columns have correct type (VARCHAR 2048, nullable)

---

## Testing Requirements

### Manual Testing
```bash
cd backend
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
```

### Edge Cases
- Running on empty database
- Running on database with existing projects/tickets

---

## Notes

Depends on TSK-001 completing first so model fields match migration.
