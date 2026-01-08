# Spec-Driven Development Feature - Continuation Transcript

## Date: 2025-01-07

## Summary

This session completed the frontend-to-backend flow for the spec-driven-dev skill enforcement feature. When users select "Spec Driven" mode from the frontend dropdown, the system now reliably enforces the spec-driven-dev skill.

## What Was Implemented

### 1. Task Model Enhancement
- Added `execution_config` JSONB column to Task model (`omoi_os/models/task.py`)
- Stores skill selection: `{"require_spec_skill": true, "selected_skill": "spec-driven-dev"}`
- Migration: `migrations/versions/044_add_execution_config_to_tasks.py`

### 2. API Schema Updates
- Added `ExecutionConfig` schema to `omoi_os/api/routes/tasks.py`
- Updated `TaskCreate` to accept `execution_config` from frontend
- Added `workflow_mode` field to `TicketCreate` in `omoi_os/api/routes/tickets.py`

### 3. Task Queue Service
- Updated `enqueue_task()` in `omoi_os/services/task_queue.py` to accept `execution_config` parameter
- Passes config to Task creation in both session branches

### 4. Ticket → Task Flow
- When ticket is created with `workflow_mode: "spec_driven"`:
  - Backend sets `execution_config.require_spec_skill = true`
  - Backend sets `execution_config.selected_skill = "spec-driven-dev"`

### 5. Orchestrator Loop
- Updated `omoi_os/api/main.py` to extract `require_spec_skill` from `task.execution_config`
- Passes to `spawn_for_task()` along with `project_id`

### 6. Spawner Environment Variables
- `omoi_os/services/daytona_spawner.py` sets:
  - `REQUIRE_SPEC_SKILL=true`
  - `OMOIOS_PROJECT_ID` (from ticket's project)
  - `OMOIOS_API_KEY` (from settings or parameter)

### 7. Worker Enforcement (from previous session)
- `omoi_os/workers/claude_sandbox_worker.py`:
  - Injects skill content directly into system prompt
  - Validates spec output before task completion
  - Checks `.omoi_os/` directory for files with proper YAML frontmatter

## Complete Flow

```
Frontend (WorkflowModeSelector)
    ↓ workflow_mode: "spec_driven"
POST /tickets (TicketCreate)
    ↓ workflow_mode → execution_config
Task Creation (enqueue_task)
    ↓ execution_config stored in DB
Orchestrator Loop (main.py)
    ↓ reads task.execution_config
spawn_for_task()
    ↓ require_spec_skill=True, project_id=...
Spawner (daytona_spawner.py)
    ↓ REQUIRE_SPEC_SKILL=true env var
Worker (claude_sandbox_worker.py)
    ↓ Skill injection + validation
Agent creates .omoi_os/ specs with frontmatter
```

## Files Modified

1. `omoi_os/models/task.py` - Added `execution_config` field
2. `omoi_os/api/routes/tasks.py` - Added `ExecutionConfig` schema, updated `TaskCreate`
3. `omoi_os/api/routes/tickets.py` - Added `workflow_mode`, passes to task creation
4. `omoi_os/services/task_queue.py` - Updated `enqueue_task()` signature
5. `omoi_os/api/main.py` - Extract and pass execution_config to spawner
6. `omoi_os/services/daytona_spawner.py` - Added `project_id`, `omoios_api_key` params
7. `omoi_os/workers/claude_sandbox_worker.py` - Skill enforcement (previous session)
8. `migrations/versions/044_add_execution_config_to_tasks.py` - New migration

## Commits

1. `a35f5da` - feat(spawner): add project_id and omoios_api_key params for spec CLI
2. `583ed18` - feat(tasks): add execution_config for frontend skill selection
3. `e966930` - feat(tickets): pass workflow_mode to task execution_config

## What to Test

1. Go to Command Center (`/command`)
2. Select "Spec Driven" mode
3. Enter a prompt and submit
4. Verify:
   - Sandbox creates `.omoi_os/` directory
   - Spec files have YAML frontmatter (id, title, status, etc.)
   - Agent commits and pushes specs

## Logs to Check

- Spawner: `Spec skill enforcement enabled`
- Worker: `REQUIRE_SPEC_SKILL=true` in config
- Worker: `Spec validation PASSED` or `FAILED`

## Next Steps (If Needed)

1. If validation fails, check worker logs for specific frontmatter errors
2. May need to adjust frontmatter requirements in `check_spec_output()`
3. Consider adding spec sync to API (CLI uses `OMOIOS_PROJECT_ID`)
