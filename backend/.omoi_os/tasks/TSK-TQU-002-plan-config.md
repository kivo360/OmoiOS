---
id: TSK-TQU-002
title: Create plan configuration module
parent_ticket: TKT-TQU-001
created: 2024-12-29
updated: 2024-12-29
status: pending
priority: HIGH
type: implementation
estimate: 1h
depends_on: []
---

# TSK-TQU-002: Create plan configuration module

## Description

Create config/plans.py with PlanLimits dataclass and PLAN_LIMITS dictionary.

## Acceptance Criteria

- [ ] PlanLimits dataclass with max_concurrent_agents, max_task_duration_minutes, monthly_agent_hours
- [ ] PLAN_LIMITS dict with free, pro, team, enterprise tiers
- [ ] get_plan_limits(plan_tier: str) -> PlanLimits helper function
- [ ] Returns free tier for unknown plan names
- [ ] Unit tests for get_plan_limits()

## Implementation

```python
# config/plans.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class PlanLimits:
    max_concurrent_agents: int
    max_task_duration_minutes: int
    monthly_agent_hours: Optional[int]  # None = unlimited

PLAN_LIMITS = {
    "free": PlanLimits(
        max_concurrent_agents=1,
        max_task_duration_minutes=30,
        monthly_agent_hours=10,
    ),
    "pro": PlanLimits(
        max_concurrent_agents=3,
        max_task_duration_minutes=120,
        monthly_agent_hours=100,
    ),
    "team": PlanLimits(
        max_concurrent_agents=10,
        max_task_duration_minutes=240,
        monthly_agent_hours=None,
    ),
    "enterprise": PlanLimits(
        max_concurrent_agents=50,
        max_task_duration_minutes=480,
        monthly_agent_hours=None,
    ),
}

def get_plan_limits(plan_tier: str) -> PlanLimits:
    """Get limits for a plan tier. Defaults to free for unknown tiers."""
    return PLAN_LIMITS.get(plan_tier, PLAN_LIMITS["free"])
```

## Dependencies

None - can be done in parallel with TSK-TQU-001.
