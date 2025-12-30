---
id: TKT-TQU-001
title: Database & Plan Models
feature: task-queue-user-limits
created: 2024-12-29
updated: 2024-12-29
status: open
priority: HIGH
phase: PHASE_IMPLEMENTATION
type: feature
requirements:
  - REQ-TQU-PLAN-001
  - REQ-TQU-PLAN-002
  - REQ-TQU-PLAN-003
  - REQ-TQU-DM-001
  - REQ-TQU-DM-002
linked_design: designs/task-queue-user-limits.md
estimate: 4h
---

# TKT-TQU-001: Database & Plan Models

## Summary

Add plan tier columns to users table and create plan configuration module. This is the foundation for user-based concurrency limits.

## Acceptance Criteria

- [ ] Users table has plan_tier, max_concurrent_agents, max_task_duration_minutes columns
- [ ] Users table has monthly_agent_hours_limit, monthly_agent_hours_used, billing_cycle_reset_at columns
- [ ] PlanLimits dataclass defined in config/plans.py
- [ ] PLAN_LIMITS dict with free/pro/team/enterprise tiers
- [ ] get_plan_limits() helper function
- [ ] Migration script created and tested
- [ ] Default values set for new users (free tier)

## Technical Details

### Migration Script
```sql
ALTER TABLE users ADD COLUMN plan_tier VARCHAR(20) DEFAULT 'free';
ALTER TABLE users ADD COLUMN max_concurrent_agents INT DEFAULT 1;
ALTER TABLE users ADD COLUMN max_task_duration_minutes INT DEFAULT 30;
ALTER TABLE users ADD COLUMN monthly_agent_hours_limit INT DEFAULT 10;
ALTER TABLE users ADD COLUMN monthly_agent_hours_used DECIMAL(10,2) DEFAULT 0;
ALTER TABLE users ADD COLUMN billing_cycle_reset_at TIMESTAMP;
CREATE INDEX idx_users_plan ON users(plan_tier);
```

### Plan Configuration
Create `config/plans.py` with PlanLimits dataclass and PLAN_LIMITS dictionary.

## Dependencies

None - this is the first ticket in the implementation.

## Related

- Design: DESIGN-TQU-001
- Requirements: REQ-TQU-PLAN-001, REQ-TQU-DM-001
