---
id: TKT-TQU-006
title: Integration Testing
feature: task-queue-user-limits
created: 2024-12-29
updated: 2024-12-29
status: open
priority: MEDIUM
phase: PHASE_INTEGRATION
type: test
requirements:
  - REQ-TQU-SLO-001
  - REQ-TQU-SLO-002
  - REQ-TQU-SLO-003
linked_design: designs/task-queue-user-limits.md
estimate: 4h
depends_on:
  - TKT-TQU-004
  - TKT-TQU-005
---

# TKT-TQU-006: Integration Testing

## Summary

End-to-end integration tests to verify the complete task queue flow with user limits, timeouts, and overnight execution simulation.

## Acceptance Criteria

- [ ] Test: Queue 3 tasks via API, verify orchestrator respects limits
- [ ] Test: Task timeout triggers sandbox termination
- [ ] Test: Monthly hours accumulate correctly
- [ ] Test: Queue position updates as tasks complete
- [ ] Test: Concurrent users don't interfere with each other
- [ ] Test: Cancel running task terminates sandbox
- [ ] Performance: Task claiming < 100ms
- [ ] Performance: Timeout check < 5s for 100 tasks
- [ ] Let orchestrator run for 10 minutes with mixed workload

## Technical Details

### Test Scenarios

1. **Basic Flow**
   - Create user with free plan
   - Queue 3 tasks
   - Verify only 1 runs at a time
   - Verify all 3 complete sequentially

2. **Timeout Handling**
   - Create task with 1-minute timeout
   - Start long-running agent
   - Verify timeout kills sandbox after 60s
   - Verify task marked failed with timeout reason

3. **Monthly Limits**
   - Set user to 0.1 hours remaining
   - Complete a 10-minute task
   - Verify next claim is rejected with limit message

4. **Multi-User Fairness**
   - Create 2 users, each queues 5 tasks
   - Verify tasks interleave (not all User A then all User B)

### Test Infrastructure
- Use pytest-asyncio for async tests
- Mock DaytonaSpawner for sandbox simulation
- Use test database with clean state per test

## Dependencies

- TKT-TQU-004: Orchestrator updates (full flow)
- TKT-TQU-005: API endpoints (for HTTP tests)

## Related

- Design: DESIGN-TQU-001
- Requirements: REQ-TQU-SLO-001 through SLO-003
