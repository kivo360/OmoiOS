---
id: TSK-TQU-004
title: Implement PlanService class
parent_ticket: TKT-TQU-002
created: 2024-12-29
updated: 2024-12-29
status: pending
priority: HIGH
type: implementation
estimate: 2h
depends_on:
  - TSK-TQU-002
  - TSK-TQU-003
---

# TSK-TQU-004: Implement PlanService class

## Description

Create PlanService in services/plan_service.py with methods for limits lookup, usage tracking, and claim eligibility.

## Acceptance Criteria

- [ ] PlanService class created with DatabaseService dependency
- [ ] get_limits(user_id) returns PlanLimits from user's plan_tier
- [ ] get_monthly_hours_used(user_id) returns current monthly_agent_hours_used
- [ ] add_usage_hours(user_id, hours) increments monthly_agent_hours_used
- [ ] can_claim_task(user_id, running_count) checks concurrency and monthly limits
- [ ] Returns tuple[bool, Optional[str]] with denial reason
- [ ] Async versions of all methods
- [ ] Unit tests for each method

## Implementation

```python
# services/plan_service.py
from typing import Optional, Tuple
from config.plans import PlanLimits, get_plan_limits
from omoi_os.services.database import DatabaseService

class PlanService:
    def __init__(self, db: DatabaseService):
        self.db = db

    async def get_limits(self, user_id: str) -> PlanLimits:
        """Get plan limits for a user."""
        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(User.plan_tier).where(User.id == user_id)
            )
            plan_tier = result.scalar_one_or_none() or "free"
            return get_plan_limits(plan_tier)

    async def get_monthly_hours_used(self, user_id: str) -> float:
        """Get current monthly usage in hours."""
        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(User.monthly_agent_hours_used).where(User.id == user_id)
            )
            return float(result.scalar_one_or_none() or 0)

    async def add_usage_hours(self, user_id: str, hours: float) -> None:
        """Add hours to user's monthly usage."""
        async with self.db.get_async_session() as session:
            await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(monthly_agent_hours_used=User.monthly_agent_hours_used + hours)
            )
            await session.commit()

    async def can_claim_task(
        self, user_id: str, running_count: int
    ) -> Tuple[bool, Optional[str]]:
        """Check if user can claim another task."""
        limits = await self.get_limits(user_id)

        if running_count >= limits.max_concurrent_agents:
            return False, f"At limit: {running_count}/{limits.max_concurrent_agents} agents running"

        if limits.monthly_agent_hours is not None:
            used = await self.get_monthly_hours_used(user_id)
            if used >= limits.monthly_agent_hours:
                return False, f"Monthly limit reached: {used}/{limits.monthly_agent_hours} hours"

        return True, None
```

## Dependencies

- TSK-TQU-002: Plan config module (for get_plan_limits)
- TSK-TQU-003: User model updates (for plan fields)
