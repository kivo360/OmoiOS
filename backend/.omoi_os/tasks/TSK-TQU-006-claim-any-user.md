---
id: TSK-TQU-006
title: Implement claim_next_task_any_user
parent_ticket: TKT-TQU-003
created: 2024-12-29
updated: 2024-12-29
status: pending
priority: HIGH
type: implementation
estimate: 2h
depends_on:
  - TSK-TQU-005
---

# TSK-TQU-006: Implement claim_next_task_any_user

## Description

Add method to claim next available task across all users while respecting per-user limits.

## Acceptance Criteria

- [ ] claim_next_task_any_user() finds eligible users with pending tasks
- [ ] Respects max_concurrent_agents per user
- [ ] Prioritizes users with fewer running agents (fairness)
- [ ] Checks monthly hour limits before claiming
- [ ] Uses atomic claim with SKIP LOCKED
- [ ] Returns None if no eligible tasks
- [ ] Integration test with multiple users

## Implementation

```python
async def claim_next_task_any_user(self) -> Optional[Task]:
    """
    Claim next available task across all users (for orchestrator).
    Respects per-user limits, prioritizes users with fewer running agents.
    """
    async with self.db.get_async_session() as session:
        # Find eligible users
        eligible_users = await session.execute(text("""
            WITH user_running AS (
                SELECT user_id, COUNT(*) as running_count
                FROM tasks
                WHERE status IN ('claimed', 'running')
                GROUP BY user_id
            ),
            user_pending AS (
                SELECT DISTINCT user_id
                FROM tasks
                WHERE status = 'pending'
            )
            SELECT up.user_id, u.max_concurrent_agents,
                   COALESCE(ur.running_count, 0) as running
            FROM user_pending up
            JOIN users u ON up.user_id = u.id
            LEFT JOIN user_running ur ON up.user_id = ur.user_id
            WHERE COALESCE(ur.running_count, 0) < u.max_concurrent_agents
            ORDER BY COALESCE(ur.running_count, 0) ASC
            LIMIT 10
        """))

        for user in eligible_users:
            # Check monthly limits
            can_claim, _ = await self.plan_service.can_claim_task(
                user["user_id"], user["running"]
            )
            if not can_claim:
                continue

            task = await self.claim_next_task_for_user(user["user_id"])
            if task:
                return task

        return None
```

## Dependencies

- TSK-TQU-005: get_running_count (for user running count)
