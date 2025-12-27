# TSK-002: Create Database Migration for Webhook Fields

**Status**: pending
**Parent Ticket**: TKT-001
**Estimate**: S
**Assignee**: (unassigned)
**Depends On**: TSK-001

## Objective

Create Alembic migration to add webhook_url columns to projects and tickets tables.

## Deliverables

- [ ] `backend/migrations/versions/xxx_add_webhook_url_fields.py`

## Implementation Notes

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

## Acceptance Criteria

- Migration runs without errors: `uv run alembic upgrade head`
- Migration is reversible: `uv run alembic downgrade -1`
- Existing data is preserved
