# Diagnostic Agent System

**Workflow self-healing and stuck detection**

---

## Overview

The Diagnostic Agent System prevents workflows from getting permanently stuck by automatically detecting when workflows have completed all tasks but haven't achieved their goal, then spawning diagnostic agents to create recovery tasks.

### Purpose

Workflows can get stuck when:
- All tasks complete but no final result is submitted
- Agents think they're done but goal not achieved  
- Work stops in a particular phase when it should continue
- Validation failures block progress repeatedly

The diagnostic agent acts as a "workflow doctor" that:
- Detects stuck workflows automatically
- Analyzes what's been accomplished vs. what's needed
- Diagnoses what's missing
- Creates targeted recovery tasks

---

## When It Activates

Diagnostic agents trigger automatically when **ALL** conditions are met:

1. **Active workflow exists** — A workflow with phases is running
2. **Tasks exist** — At least one task has been created
3. **All tasks finished** — No tasks with status: pending, assigned, running, under_review, validation_in_progress
4. **No validated result** — No WorkflowResult with status="validated"
5. **Cooldown passed** — At least 60s since last diagnostic for this workflow
6. **Stuck long enough** — At least 60s since last task activity

---

## How It Works

### 1. Detection (Monitoring Loop)

Every 60 seconds, the diagnostic monitoring loop checks:

```python
if workflow_exists and has_tasks:
    if all_tasks_finished and no_validated_result:
        if cooldown_passed and stuck_long_enough:
            spawn_diagnostic_agent()
```

### 2. Context Gathering

When triggered, system gathers:

**Workflow Information:**
- Workflow goal (from result_criteria config)
- All phase definitions
- Current phase status

**Recent History:**
- Last 15 completed/failed tasks
- Task descriptions and outcomes
- Completion notes and errors

**System State:**
- Task distribution by phase
- Recent agent activity
- Validation feedback

### 3. Diagnostic Task Creation

A DiagnosticRun record is created:

```python
DiagnosticRun(
    workflow_id=ticket_id,
    triggered_at=now,
    total_tasks_at_trigger=10,
    done_tasks_at_trigger=10,
    time_since_last_task_seconds=300,
    status="created"
)
```

### 4. Recovery Task Spawning

Diagnostic uses the Discovery system to spawn recovery tasks:

```python
discovery_service.spawn_diagnostic_recovery(
    ticket_id=workflow_id,
    diagnostic_run_id=run.id,
    reason="All tasks done but no validated result",
    suggested_phase="PHASE_FINAL",
    suggested_priority="HIGH"
)
```

### 5. Workflow Progression

Once diagnostic creates recovery tasks:
- Tasks picked up by regular agents
- Workflow progresses toward goal
- System continues monitoring
- Another diagnostic may trigger if needed (after cooldown)

---

## Configuration

### Default Values

```python
DIAGNOSTIC_COOLDOWN_SECONDS = 60  # Min time between diagnostics
DIAGNOSTIC_STUCK_THRESHOLD = 60   # Min stuck time to trigger
MAX_AGENTS_TO_ANALYZE = 15        # Number of recent tasks in context
```

### Workflow Configuration

From `software_development.yaml`:

```yaml
has_result: true
result_criteria: "All components implemented, tested, and deployed"
on_result_found: "stop_all"  # or "do_nothing"
```

---

## Database Schema

### `diagnostic_runs` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | String (PK) | UUID |
| `workflow_id` | String (FK) | Workflow being diagnosed |
| `diagnostic_agent_id` | String (FK) | Agent that ran diagnostic |
| `diagnostic_task_id` | String (FK) | Diagnostic task |
| `triggered_at` | Timestamp | When diagnostic triggered |
| `total_tasks_at_trigger` | Integer | Total tasks when triggered |
| `done_tasks_at_trigger` | Integer | Completed tasks |
| `failed_tasks_at_trigger` | Integer | Failed tasks |
| `time_since_last_task_seconds` | Integer | How long stuck |
| `tasks_created_count` | Integer | Recovery tasks created |
| `tasks_created_ids` | JSONB | Array of task IDs |
| `workflow_goal` | Text | From result_criteria |
| `phases_analyzed` | JSONB | Phase status snapshot |
| `agents_reviewed` | JSONB | Recent agent summaries |
| `diagnosis` | Text | Diagnostic analysis |
| `completed_at` | Timestamp | When completed |
| `status` | String | created, running, completed, failed |
| `created_at` | Timestamp | Record creation |

---

## API Endpoints

### Get Stuck Workflows

```http
GET /api/v1/diagnostic/stuck-workflows
```

Returns workflows currently meeting stuck conditions.

### Get Diagnostic Runs

```http
GET /api/v1/diagnostic/runs?workflow_id={id}&limit=100
```

Get diagnostic run history.

### Manual Trigger

```http
POST /api/v1/diagnostic/trigger/{workflow_id}
```

Manually trigger diagnostic (bypasses cooldown/threshold).

### Get Run Details

```http
GET /api/v1/diagnostic/runs/{run_id}
```

Get detailed diagnostic run information.

---

## Integration

### With Discovery System

Diagnostics use DiscoveryService to spawn tasks:
- Creates TaskDiscovery record (type: diagnostic_no_result)
- Spawns recovery task via record_discovery_and_branch()
- Maintains audit trail

### With Memory System

Diagnostic context includes:
- Similar past stuck workflows
- Learned patterns for recovery
- Historical success/failure indicators

### With Guardian

Escalation path:
- If diagnostic fails repeatedly → Guardian intervention
- Guardian can boost priority of recovery tasks

---

## Troubleshooting

### Diagnostic Not Triggering

**Check:**
1. Are all tasks actually finished?
2. Has 60s passed since last task?
3. Is there a validated WorkflowResult?
4. Has cooldown passed?

**Debug:**
```http
GET /api/v1/diagnostic/stuck-workflows
```

### Too Many Diagnostics

**Solutions:**
- Increase cooldown_seconds
- Increase stuck_threshold_seconds
- Improve phase done_definitions

### Diagnostic Creates Wrong Tasks

**Solutions:**
- Improve workflow result_criteria clarity
- Review diagnostic_run.diagnosis field
- Check task descriptions in context

---

## Best Practices

### 1. Clear Workflow Goals

```yaml
# ❌ Vague
result_criteria: "Complete the project"

# ✅ Specific
result_criteria: |
  Submit result.md containing:
  - Solution or deliverable
  - Evidence of completion
  - Methodology used
  - Use submit_result() tool
```

### 2. Detailed Done Definitions

```yaml
done_definitions:
  - "All unit tests pass with 0 failures"
  - "Integration tests execute successfully"
  - "Test results saved to test_results.txt"
  - "submit_result() called with evidence"
```

### 3. Submit Results

Agents should explicitly submit workflow results:

```python
# Via API
POST /api/v1/submit_result
{
  "workflow_id": "ticket-123",
  "markdown_file_path": "/path/to/solution.md"
}
```

---

## Monitoring

### Key Metrics

```sql
-- Diagnostic effectiveness
SELECT
    COUNT(CASE WHEN tasks_created_count > 0 THEN 1 END) as successful,
    COUNT(*) as total
FROM diagnostic_runs;

-- Which phases need diagnostics
SELECT
    phases_analyzed,
    COUNT(*) as diagnostic_count
FROM diagnostic_runs
GROUP BY phases_analyzed;
```

### Events Published

- `diagnostic.triggered` — Diagnostic run started
- `diagnostic.completed` — Diagnostic finished
- `discovery.recorded` — Recovery task spawned

---

## Version History

- **v1.0** — Initial release
  - Stuck workflow detection
  - Diagnostic task spawning via Discovery
  - Integration with Memory and Guardian
  - Automatic recovery task creation

