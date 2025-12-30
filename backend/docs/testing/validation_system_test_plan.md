# Validation System Test Plan

**Created**: 2025-12-29
**Status**: Draft
**Purpose**: Comprehensive test plan for the task validation system

## Overview

The validation system ensures completed work meets quality standards before marking tasks as complete. This document outlines how to test the complete validation flow.

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          VALIDATION FLOW                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Implementer Completes Work                                              │
│     └─► agent.completed event with branch_name                              │
│                                                                             │
│  2. Event Handler (sandbox.py)                                              │
│     └─► Extracts branch_name, stores in task.result                         │
│     └─► Calls TaskValidatorService.request_validation()                     │
│                                                                             │
│  3. TaskValidatorService.request_validation()                               │
│     └─► Updates task.status to "pending_validation"                         │
│     └─► Spawns validator sandbox via Daytona with:                          │
│         - GITHUB_REPO, GITHUB_REPO_OWNER, GITHUB_REPO_NAME                 │
│         - BRANCH_NAME (from task.result)                                    │
│         - GITHUB_TOKEN (from project owner)                                 │
│         - VALIDATION_MODE=true                                              │
│                                                                             │
│  4. Validator Agent Runs                                                    │
│     └─► Checks: tests, build, git status, PR exists                         │
│     └─► Reports result via POST /api/v1/sandbox/{id}/validation-result      │
│                                                                             │
│  5. TaskValidatorService.handle_validation_result()                         │
│     └─► PASSED: task.status = "completed"                                   │
│     └─► FAILED: task.status = "needs_revision"                              │
│         └─► Publishes TASK_VALIDATION_FAILED event                          │
│                                                                             │
│  6. Orchestrator (on TASK_VALIDATION_FAILED)                                │
│     └─► Resets task to "pending" with revision_feedback                     │
│     └─► Implementer respawns with feedback context                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Test Categories

### 1. Unit Tests

Test individual methods of `TaskValidatorService` in isolation.

**File**: `tests/test_task_validator_service.py`

| Test Case | Description | Expected Outcome |
|-----------|-------------|------------------|
| `test_request_validation_creates_pending_status` | Call request_validation with valid task | Task status → "pending_validation" |
| `test_request_validation_increments_iteration` | Request validation multiple times | iteration increments 1, 2, 3 |
| `test_request_validation_fails_after_max_iterations` | Exceed MAX_VALIDATION_ITERATIONS | Task status → "failed" |
| `test_request_validation_disabled_auto_approves` | TASK_VALIDATION_ENABLED=false | Task status → "completed" immediately |
| `test_handle_validation_result_passed` | Submit passed validation | Task status → "completed" |
| `test_handle_validation_result_failed` | Submit failed validation | Task status → "needs_revision" |
| `test_handle_validation_result_creates_review_record` | Submit any result | ValidationReview record created |
| `test_spawn_validator_gets_repo_info` | Spawn validator for task with project | extra_env includes GITHUB_REPO, BRANCH_NAME |
| `test_spawn_validator_gets_github_token` | Spawn validator with user token | extra_env includes GITHUB_TOKEN |
| `test_auto_approve_marks_completed` | _auto_approve called | Task status → "completed", auto_approved=True |

### 2. Integration Tests

Test the complete flow across multiple services.

**File**: `tests/integration/test_validation_integration.py`

| Test Case | Description | Expected Outcome |
|-----------|-------------|------------------|
| `test_completion_event_triggers_validation` | Emit agent.completed event | task.status → "pending_validation" |
| `test_validation_passed_completes_task` | Full flow with passing validation | task.status → "completed" |
| `test_validation_failed_triggers_retry` | Full flow with failing validation | task.status → "pending", respawn triggered |
| `test_feedback_propagates_to_respawn` | Fail validation, respawn | New implementer receives revision_feedback |
| `test_branch_name_propagates_to_validator` | Complete task with branch | Validator gets BRANCH_NAME env var |

### 3. API Endpoint Tests

Test the validation result endpoint directly.

**File**: `tests/api/test_validation_endpoint.py`

| Test Case | Description | Expected Outcome |
|-----------|-------------|------------------|
| `test_post_validation_result_passed` | POST /validation-result with passed=true | 200, task completed |
| `test_post_validation_result_failed` | POST /validation-result with passed=false | 200, task needs_revision |
| `test_post_validation_result_wrong_sandbox` | POST with mismatched sandbox_id | 403 or logged warning |
| `test_post_validation_result_missing_task` | POST for non-existent task | 404 |

### 4. Event Tests

Test event publishing and handling.

| Test Case | Description | Expected Outcome |
|-----------|-------------|------------------|
| `test_validation_requested_event_published` | request_validation called | TASK_VALIDATION_REQUESTED event published |
| `test_validation_passed_event_published` | Validation passes | TASK_VALIDATION_PASSED event published |
| `test_validation_failed_event_published` | Validation fails | TASK_VALIDATION_FAILED event published |
| `test_orchestrator_handles_validation_failed` | TASK_VALIDATION_FAILED event | Task reset to "pending" |

## Manual Testing Guide

### Prerequisites

1. Running services:
   ```bash
   docker-compose up -d postgres redis
   uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 18000 --reload
   ```

2. Database migrations applied:
   ```bash
   uv run alembic upgrade head
   ```

3. Daytona configured (or mocked)

### Manual Test 1: Trigger Validation Flow

```bash
# 1. Create a task in the database
curl -X POST http://localhost:18000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "ticket_id": "<ticket-id>",
    "phase_id": "PHASE_IMPLEMENTATION",
    "task_type": "implement_feature",
    "description": "Test validation flow"
  }'

# 2. Simulate completion event (normally from worker)
# Use the test script below
```

### Test Script: `scripts/test_validation_flow.py`

```python
#!/usr/bin/env python
"""Test script for validation flow."""
import asyncio
import os
from uuid import uuid4

# Set test env
os.environ["TASK_VALIDATION_ENABLED"] = "true"

from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.task_validator import TaskValidatorService
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.models.project import Project


async def test_validation_flow():
    # Initialize services
    db = DatabaseService()
    event_bus = EventBusService()
    validator = TaskValidatorService(db=db, event_bus=event_bus)

    # Create test project, ticket, task
    with db.get_session() as session:
        project = Project(
            name="Test Project",
            github_owner="test-owner",
            github_repo="test-repo",
        )
        session.add(project)
        session.commit()

        ticket = Ticket(
            title="Test Ticket",
            project_id=project.id,
            status="in_progress",
        )
        session.add(ticket)
        session.commit()

        task = Task(
            ticket_id=ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Test task",
            status="running",
            sandbox_id=f"test-sandbox-{uuid4().hex[:8]}",
            result={"branch_name": "feature/test-branch"},
        )
        session.add(task)
        session.commit()
        task_id = str(task.id)
        sandbox_id = task.sandbox_id

    print(f"Created task: {task_id}")
    print(f"Sandbox ID: {sandbox_id}")

    # Request validation
    validation_id = await validator.request_validation(
        task_id=task_id,
        sandbox_id=sandbox_id,
        implementation_result={
            "success": True,
            "branch_name": "feature/test-branch",
        }
    )

    print(f"Validation requested: {validation_id}")

    # Check task status
    with db.get_session() as session:
        task = session.get(Task, task_id)
        print(f"Task status: {task.status}")
        print(f"Task result: {task.result}")

    # Simulate validation result (passed)
    await validator.handle_validation_result(
        task_id=task_id,
        validator_agent_id=str(uuid4()),
        passed=True,
        feedback="All checks passed!",
        evidence={"tests": "passed", "build": "success"},
    )

    # Check final status
    with db.get_session() as session:
        task = session.get(Task, task_id)
        print(f"Final task status: {task.status}")
        print(f"Validation passed: {task.result.get('validation_passed')}")


if __name__ == "__main__":
    asyncio.run(test_validation_flow())
```

### Manual Test 2: API Endpoint

```bash
# After running a task through validation flow, test the endpoint:

# Simulate validator reporting success
curl -X POST http://localhost:18000/api/v1/sandbox/test-sandbox-123/validation-result \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "<task-id>",
    "passed": true,
    "feedback": "All tests pass, code is production-ready",
    "evidence": {
      "test_output": "...",
      "build_log": "..."
    }
  }'

# Simulate validator reporting failure
curl -X POST http://localhost:18000/api/v1/sandbox/test-sandbox-123/validation-result \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "<task-id>",
    "passed": false,
    "feedback": "Tests failing: 3 unit tests failed",
    "evidence": {
      "test_output": "FAILED test_foo, test_bar, test_baz"
    },
    "recommendations": [
      "Fix test_foo by updating the expected value",
      "Fix test_bar by handling null case"
    ]
  }'
```

## Running Tests

### Quick Unit Tests
```bash
uv run pytest tests/test_task_validator_service.py -v
```

### Full Validation Suite
```bash
uv run pytest tests/ -k "validation" -v
```

### With Coverage
```bash
uv run pytest tests/test_task_validator_service.py --cov=omoi_os.services.task_validator --cov-report=html
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TASK_VALIDATION_ENABLED` | `true` | Enable/disable validation system |
| `MAX_VALIDATION_ITERATIONS` | `3` | Max retries before task fails |
| `TESTING` | `false` | Skip background loops in tests |

## Database Tables

### validation_reviews
- `id` (UUID): Primary key
- `task_id` (UUID): Foreign key to tasks
- `validator_agent_id` (String): Agent that performed validation
- `iteration_number` (Integer): Which validation attempt
- `validation_passed` (Boolean): Pass/fail status
- `feedback` (Text): Human-readable feedback
- `evidence` (JSONB): Test output, logs, etc.
- `recommendations` (JSONB): List of fix recommendations
- `created_at` (DateTime): When review was created

## Related Files

- `omoi_os/services/task_validator.py` - Core validation service
- `omoi_os/api/routes/sandbox.py` - Validation result endpoint
- `omoi_os/workers/orchestrator_worker.py` - Handles TASK_VALIDATION_FAILED
- `omoi_os/workers/claude_sandbox_worker.py` - Includes branch_name in completion
- `omoi_os/models/validation_review.py` - ValidationReview model
- `migrations/versions/010_validation_system.py` - Database migration

## Troubleshooting

### Task stuck in "pending_validation"
- Check Daytona logs for validator spawn errors
- Verify GITHUB_TOKEN is set for project owner
- Check if validator sandbox started successfully

### Validation always fails
- Check validator agent logs
- Verify repo/branch info is correct
- Check if tests actually pass in the sandbox

### Events not publishing
- Verify Redis is running
- Check event_bus is initialized correctly
- Look for Redis connection errors in logs
