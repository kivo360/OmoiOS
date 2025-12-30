---
id: TSK-TQU-003
title: Update User model with plan fields
parent_ticket: TKT-TQU-001
created: 2024-12-29
updated: 2024-12-29
status: pending
priority: HIGH
type: implementation
estimate: 1h
depends_on:
  - TSK-TQU-001
---

# TSK-TQU-003: Update User model with plan fields

## Description

Add plan-related mapped columns to the User SQLAlchemy model.

## Acceptance Criteria

- [ ] User model has plan_tier: Mapped[str] with default 'free'
- [ ] User model has max_concurrent_agents: Mapped[int] with default 1
- [ ] User model has max_task_duration_minutes: Mapped[int] with default 30
- [ ] User model has monthly_agent_hours_limit: Mapped[Optional[int]] with default 10
- [ ] User model has monthly_agent_hours_used: Mapped[Decimal] with default 0
- [ ] User model has billing_cycle_reset_at: Mapped[Optional[datetime]]
- [ ] Model matches migration schema

## Implementation

Add to `omoi_os/models/user.py`:

```python
from decimal import Decimal

# Plan tier
plan_tier: Mapped[str] = mapped_column(
    String(20), default="free", nullable=False
)
max_concurrent_agents: Mapped[int] = mapped_column(
    Integer, default=1, nullable=False
)
max_task_duration_minutes: Mapped[int] = mapped_column(
    Integer, default=30, nullable=False
)
monthly_agent_hours_limit: Mapped[Optional[int]] = mapped_column(
    Integer, default=10, nullable=True
)
monthly_agent_hours_used: Mapped[Decimal] = mapped_column(
    Numeric(10, 2), default=Decimal("0"), nullable=False
)
billing_cycle_reset_at: Mapped[Optional[datetime]] = mapped_column(
    DateTime(timezone=True), nullable=True
)
```

## Dependencies

- TSK-TQU-001: Migration must be created first to ensure schema matches
