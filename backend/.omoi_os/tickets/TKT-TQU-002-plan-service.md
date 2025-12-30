---
id: TKT-TQU-002
title: Plan Service Implementation
feature: task-queue-user-limits
created: 2024-12-29
updated: 2024-12-29
status: open
priority: HIGH
phase: PHASE_IMPLEMENTATION
type: feature
requirements:
  - REQ-TQU-CONC-001
  - REQ-TQU-CONC-002
  - REQ-TQU-CONC-003
  - REQ-TQU-USAGE-001
  - REQ-TQU-USAGE-002
  - REQ-TQU-USAGE-004
linked_design: designs/task-queue-user-limits.md
estimate: 4h
depends_on:
  - TKT-TQU-001
---

# TKT-TQU-002: Plan Service Implementation

## Summary

Create PlanService class that handles plan limits lookup, usage tracking, and claim eligibility checks.

## Acceptance Criteria

- [ ] PlanService class created in services/plan_service.py
- [ ] get_limits(user_id) returns PlanLimits for user
- [ ] get_monthly_hours_used(user_id) returns current usage
- [ ] add_usage_hours(user_id, hours) increments usage
- [ ] can_claim_task(user_id) checks both concurrency and monthly limits
- [ ] Returns descriptive reason when claim is denied
- [ ] Unit tests for all methods

## Technical Details

### PlanService Interface
```python
class PlanService:
    def __init__(self, db: DatabaseService):
        self.db = db

    async def get_limits(self, user_id: str) -> PlanLimits:
        """Get plan limits for a user."""

    async def get_monthly_hours_used(self, user_id: str) -> float:
        """Get current monthly usage in hours."""

    async def add_usage_hours(self, user_id: str, hours: float) -> None:
        """Add hours to user's monthly usage."""

    async def can_claim_task(self, user_id: str, running_count: int) -> tuple[bool, Optional[str]]:
        """Check if user can claim another task."""
```

### Integration Points
- Uses DatabaseService for user queries
- Called by TaskQueueService for claim eligibility
- Called by API for queue status

## Dependencies

- TKT-TQU-001: Database & Plan Models (columns must exist)

## Related

- Design: DESIGN-TQU-001
- Requirements: REQ-TQU-CONC-001 through REQ-TQU-CONC-003
