---
id: TSK-TQU-001
title: Create database migration for user plan columns
parent_ticket: TKT-TQU-001
created: 2024-12-29
updated: 2024-12-29
status: pending
priority: HIGH
type: implementation
estimate: 1h
depends_on: []
---

# TSK-TQU-001: Create database migration for user plan columns

## Description

Create an Alembic migration that adds plan-related columns to the users table.

## Acceptance Criteria

- [ ] Migration adds plan_tier VARCHAR(20) DEFAULT 'free'
- [ ] Migration adds max_concurrent_agents INT DEFAULT 1
- [ ] Migration adds max_task_duration_minutes INT DEFAULT 30
- [ ] Migration adds monthly_agent_hours_limit INT DEFAULT 10
- [ ] Migration adds monthly_agent_hours_used DECIMAL(10,2) DEFAULT 0
- [ ] Migration adds billing_cycle_reset_at TIMESTAMP
- [ ] Index created on plan_tier column
- [ ] Migration is reversible (downgrade works)
- [ ] Migration tested on fresh and existing databases

## Implementation Notes

```bash
uv run alembic revision -m "add_user_plan_columns"
```

```python
def upgrade():
    op.add_column('users', sa.Column('plan_tier', sa.String(20), server_default='free'))
    op.add_column('users', sa.Column('max_concurrent_agents', sa.Integer(), server_default='1'))
    op.add_column('users', sa.Column('max_task_duration_minutes', sa.Integer(), server_default='30'))
    op.add_column('users', sa.Column('monthly_agent_hours_limit', sa.Integer(), server_default='10'))
    op.add_column('users', sa.Column('monthly_agent_hours_used', sa.Numeric(10, 2), server_default='0'))
    op.add_column('users', sa.Column('billing_cycle_reset_at', sa.DateTime(timezone=True)))
    op.create_index('idx_users_plan', 'users', ['plan_tier'])

def downgrade():
    op.drop_index('idx_users_plan')
    op.drop_column('users', 'billing_cycle_reset_at')
    op.drop_column('users', 'monthly_agent_hours_used')
    op.drop_column('users', 'monthly_agent_hours_limit')
    op.drop_column('users', 'max_task_duration_minutes')
    op.drop_column('users', 'max_concurrent_agents')
    op.drop_column('users', 'plan_tier')
```

## Dependencies

None - first task in the chain.
