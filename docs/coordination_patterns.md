# Coordination Patterns Documentation

This document describes the coordination patterns system for multi-agent workflow orchestration in OmoiOS.

## Overview

Coordination patterns provide reusable templates for common multi-agent workflows, enabling:
- **Parallel Execution**: Split work into independent parallel tasks
- **Synchronization**: Wait for multiple tasks to complete before proceeding
- **Result Aggregation**: Merge results from multiple tasks
- **Workflow Orchestration**: Coordinate complex multi-step workflows

## Core Primitives

### 1. Sync Point

A synchronization point waits for multiple tasks to complete before allowing dependent tasks to proceed.

```python
sync_point = coordination_service.create_sync_point(
    sync_id="implementation_sync",
    waiting_task_ids=["task_1", "task_2", "task_3"],
    required_count=3,  # Wait for all, or specify a number
    timeout_seconds=3600,  # Optional timeout
)

# Check if sync point is ready
is_ready = coordination_service.check_sync_point_ready("implementation_sync", sync_point)
```

### 2. Split

Split a single task into multiple parallel tasks that can execute independently.

```python
parallel_tasks = coordination_service.split_task(
    split_id="parallel_impl_split",
    source_task_id="source_task_id",
    target_tasks=[
        {
            "phase_id": "PHASE_IMPLEMENTATION",
            "task_type": "implement_module_a",
            "description": "Implement module A",
            "priority": "HIGH",
        },
        {
            "phase_id": "PHASE_IMPLEMENTATION",
            "task_type": "implement_module_b",
            "description": "Implement module B",
            "priority": "HIGH",
        },
    ],
    required_capabilities=["python", "fastapi"],  # Optional
)
```

### 3. Join

Join multiple parallel tasks and create a continuation task that depends on all joined tasks completing.

```python
continuation = coordination_service.join_tasks(
    join_id="integration_join",
    source_task_ids=["task_1", "task_2", "task_3"],
    continuation_task={
        "phase_id": "PHASE_INTEGRATION",
        "task_type": "integrate_modules",
        "description": "Integrate all modules",
        "priority": "HIGH",
    },
    merge_strategy="all",  # "all", "first", "majority"
)
```

### 4. Merge

Merge results from multiple tasks using a specified strategy.

```python
merged_result = coordination_service.merge_task_results(
    merge_id="result_merge",
    source_task_ids=["task_1", "task_2", "task_3"],
    merge_strategy="combine",  # "combine", "union", "intersection", "custom"
    custom_merge_fn=None,  # Optional custom function reference
)
```

## Pattern Configuration Files

Patterns are defined in YAML files under `omoi_os/config/patterns/`. Each pattern file defines:

- **name**: Pattern identifier
- **description**: Human-readable description
- **pattern**: Main pattern definition (split, join, etc.)
- **sync_points**: Optional synchronization points
- **join**: Optional join configuration
- **merge**: Optional merge configuration

### Example: Parallel Implementation Pattern

```yaml
name: parallel_implementation
description: |
  Splits a large implementation task into multiple parallel subtasks,
  executes them concurrently, and joins results for integration.

pattern:
  type: split
  id: parallel_impl_split
  source_task_id: "${source_task_id}"
  target_tasks:
    - phase_id: PHASE_IMPLEMENTATION
      task_type: implement_module
      description: "Implement module 1"
      priority: MEDIUM

sync_points:
  - id: implementation_complete
    waiting_task_ids:
      - "${split_task_1_id}"
      - "${split_task_2_id}"
    required_count: null  # Wait for all

join:
  id: integration_join
  source_task_ids:
    - "${split_task_1_id}"
    - "${split_task_2_id}"
  continuation_task:
    phase_id: PHASE_INTEGRATION
    task_type: integrate_modules
    description: "Integrate all modules together"
    priority: HIGH
  merge_strategy: combine
```

## Using Patterns in Code

### Loading and Applying Patterns

```python
from omoi_os.services.coordination import CoordinationService
from omoi_os.services.pattern_loader import PatternLoader
from omoi_os.services.orchestrator_coordination import OrchestratorCoordination

# Initialize services
coordination = CoordinationService(db, queue, event_bus)
pattern_loader = PatternLoader()
orchestrator_coord = OrchestratorCoordination(coordination, pattern_loader)

# Apply pattern to a ticket
result = orchestrator_coord.apply_pattern_to_ticket(
    ticket_id="ticket_123",
    pattern_name="parallel_implementation",
    context={
        "source_task_id": "initial_task_id",
        "split_task_1_id": "task_1",
        "split_task_2_id": "task_2",
    },
)
```

### Generating Tasks with Patterns

```python
# Generate tasks using a pattern
task_ids = orchestrator_coord.generate_tasks_with_pattern(
    ticket_id="ticket_123",
    initial_task_type="design_architecture",
    pattern_name="parallel_implementation",
    pattern_context={"module_count": 3},
)
```

## Available Patterns

### 1. `parallel_implementation`

Splits a large implementation task into multiple parallel subtasks, executes them concurrently, and joins results for integration.

**Use Case**: Implementing a feature with multiple independent modules.

### 2. `review_feedback_loop`

Splits work into parallel implementation tasks, waits for review tasks to complete, merges feedback, and continues with refinement tasks.

**Use Case**: Code review workflow with parallel implementation and review.

### 3. `majority_vote`

Creates multiple parallel tasks that vote on a decision, then merges results using majority vote strategy.

**Use Case**: Architectural decision making with multiple evaluators.

## Merge Strategies

### `combine`
Combines all results into a single dictionary. Overlapping keys use values from later results.

### `union`
Union of all keys, values from last result (same as combine).

### `intersection`
Only includes keys present in all results.

### `majority`
For voting scenarios, selects the majority result (requires custom implementation).

## Event Publishing

Coordination operations publish events to the event bus:

- `coordination.sync.created`: Sync point created
- `coordination.sync.ready`: Sync point ready
- `coordination.split.created`: Task split created
- `coordination.join.created`: Join created
- `coordination.merge.completed`: Merge completed

## Testing

Run coordination pattern tests:

```bash
uv run pytest tests/test_coordination_patterns.py -v
uv run pytest tests/test_e2e_parallel.py -v
```

Run simulation script:

```bash
uv run python scripts/simulate_parallel_workflow.py
```

## Integration with Orchestrator

The orchestrator can use coordination patterns when generating tasks from tickets. Patterns are applied automatically based on ticket metadata or explicitly via API.

## Future Enhancements

- Custom merge functions
- Pattern composition (patterns using other patterns)
- Pattern templates with parameterization
- Visual pattern editor
- Pattern performance metrics

