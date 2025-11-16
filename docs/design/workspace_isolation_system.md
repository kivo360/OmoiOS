# Workspace Isolation System Documentation

## Overview

The **Workspace Isolation System** provides automatic workspace isolation for Hephaestus agents, enabling parallel agent execution without conflicts. Each workspace maintains its own filesystem, execution environment, and Git-managed state, while remaining completely transparent to agents — they are never aware that isolation or Git operations occur behind the scenes.

Workspaces act as the foundational execution environment for agents and support:

* Local directory workspaces
* Git-backed workspaces
* Container-backed workspaces (future)
* Remote execution workspaces (future)

## Key Features

* **Complete Transparency**: Agents do NOT know they are running in isolated workspaces.
* **Git-Backed Snapshots**: Each workspace is tied to a Git branch with automated commit history.
* **Zero Conflicts**: Parallel agents operate independently without overwriting each other's work.
* **Knowledge Inheritance**: Child workspaces inherit the exact Git state and filesystem contents of their parents.
* **Automatic Merge Resolution**: The system uses a deterministic "newest file wins" strategy.
* **Clean Experimentation**: Every workspace has its own branch; experiments never pollute the main branch.
* **Pluggable Execution Environment**: Future support for containerized or remote workspace types.

## Problem Solved

When multiple agents modify the same repository simultaneously, they create:

* race conditions
* file conflicts
* overwritten commits
* polluted repository state
* unclear history of changes

The Workspace Isolation System solves all of this by providing each agent with a safe, isolated workspace backed by Git and unified through a WorkspaceManager.

---

# Architecture

## System Components

```
┌──────────────────────────────────────────────────────────────┐
│                        AgentManager                          │
│  - Creates and manages agents                                 │
│  - Handles agent lifecycle & tmux sessions                    │
│  - Integrates with WorkspaceManager                           │
└───────────────────────────┬────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                     WorkspaceManager                         │
│  - Creates isolated workspaces                                │
│  - Manages parent-child relationships                         │
│  - Handles Git branching, commits, merges                     │
│  - Performs cleanup, retention, archiving                     │
└───────────────────────────┬────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                        Workspaces                            │
│  - Local directory workspace                                  │
│  - Git-managed branch per workspace                           │
│  - Rooted in /tmp/hephaestus_workspaces/                      │
│  - Future: container/remote workspace types                   │
└──────────────────────────────────────────────────────────────┘
```

---

# Database Schema

The system maintains three main tables:

### **agent_workspaces**

Tracks workspace paths, Git branches, parent-child relationships.

### **workspace_commits**

Stores checkpoint commits for validation, debugging, and auditing.

### **merge_conflict_resolutions**

Logs automatic conflict resolutions and merge metadata.

---

# API Reference

## WorkspaceManager Class

---

## `create_workspace(agent_id, parent_id=None)`

Creates a new isolated workspace for an agent with Git branching.

### Parameters:

| Name        | Type        | Description                     |
| ----------- | ----------- | ------------------------------- |
| `agent_id`  | str         | Unique agent identifier         |
| `parent_id` | str or None | Parent agent ID for inheritance |

### Returns:

```json
{
  "working_directory": "/tmp/hephaestus_workspaces/ws_agent123",
  "branch_name": "workspace-agent-123",
  "parent_commit": "abc123def456"
}
```

Agents see only `working_directory`.

### Example:

```python
workspace = workspace_manager.create_workspace(
    agent_id="agent-123",
    parent_id="agent-001"
)

working_dir = workspace["working_directory"]
```

---

## `commit_for_validation(agent_id, iteration)`

Creates a Git commit representing the workspace's state for validator inspection.

### Returns:

```json
{
  "commit_sha": "def456ghi789",
  "files_changed": 7,
  "message": "[Agent 123] Iteration 1 - Ready for validation"
}
```

---

## `merge_to_parent(agent_id)`

Merges a workspace’s changes back into its parent or main branch.

### Merge Strategy:

* File-level timestamps
* “Newest file wins”
* Delete conflicts resolved deterministically

### Returns:

```json
{
  "status": "success" | "conflict_resolved",
  "merged_to": "main",
  "commit_sha": "xyz789abc123",
  "conflicts_resolved": [...],
  "resolution_strategy": "newest_file_wins",
  "total_conflicts": 0
}
```

---

## `get_workspace_changes(agent_id, since_commit=None)`

Returns detailed file diff metadata.

### Returns:

```json
{
  "files_created": [...],
  "files_modified": [...],
  "files_deleted": [...],
  "total_changes": 3,
  "stats": {
    "insertions": 150,
    "deletions": 30
  },
  "detailed_diff": "..."
}
```

---

## `cleanup_workspace(agent_id)`

Deletes a workspace and (optionally) preserves its Git branch for debugging.

### Returns:

```json
{
  "status": "cleaned",
  "branch_preserved": true,
  "disk_space_freed_mb": 90
}
```

---

# Integration with AgentManager

When creating an agent:

```python
workspace_info = self.workspace_manager.create_workspace(
    agent_id=agent_id,
    parent_id=parent_agent_id
)

agent_working_dir = workspace_info["working_directory"]

# Create the agent execution context (process/session/container) bound to the workspace.
exec_ctx = self._create_execution_context(
    name=session_name,
    working_directory=agent_working_dir
)
```

Everything is automatic and invisible to agents.

---

# Configuration

Configuration is managed by environment variables and `simple_config.py`.

### **Environment Variables**

```bash
# Workspace paths
WORKSPACE_BASE_PATH=/tmp/hephaestus_workspaces
MAIN_REPO_PATH=/path/to/repo

# Limits
WORKSPACE_MAX_COUNT=50
WORKSPACE_MAX_DEPTH=10
WORKSPACE_DISK_THRESHOLD_GB=10

# Merge strategy
WORKSPACE_AUTO_MERGE=true
WORKSPACE_CONFLICT_STRATEGY=newest_file_wins
WORKSPACE_PREFER_CHILD_ON_TIE=true

# Cleanup
WORKSPACE_AUTO_CLEANUP=true
WORKSPACE_CLEANUP_INTERVAL_HOURS=6
WORKSPACE_RETENTION_MERGED=1
WORKSPACE_RETENTION_FAILED=24

# Checkpointing
WORKSPACE_AUTO_CHECKPOINT=true
WORKSPACE_CHECKPOINT_INTERVAL=30
WORKSPACE_CHECKPOINT_ON_ERROR=true

# Git branch naming
WORKSPACE_BRANCH_PREFIX=workspace-
WORKSPACE_ARCHIVE_PREFIX=refs/archive/
```

---

# Usage Examples

## Creating a Child Workspace with Inheritance

```python
parent_agent = agent_manager.create_agent_for_task(task=analysis_task)

child_agent = agent_manager.create_agent_for_task(
    task=implementation_task,
    parent_agent_id=parent_agent.id
)
```

The child immediately sees all parent files.

---

## Parallel Workspaces

```python
agent1 = agent_manager.create_agent_for_task(task1)
agent2 = agent_manager.create_agent_for_task(task2)
agent3 = agent_manager.create_agent_for_task(task3)
```

No conflicts, even if all modify the same files.

---

## Automatic Merge with Conflict Resolution

```python
async def on_task_complete(agent_id):
    merge_result = workspace_manager.merge_to_parent(agent_id)

    if merge_result["total_conflicts"] > 0:
        print("Resolved conflicts:", merge_result["conflicts_resolved"])

    workspace_manager.cleanup_workspace(agent_id)
```

---

# Git Operations

## Commit Message Formats

| Type                | Format                                                  | Example                                                  |
| ------------------- | ------------------------------------------------------- | -------------------------------------------------------- |
| Parent Checkpoint   | `[Workspace {id}] Checkpoint before spawning: {task}`   | `[Workspace 123] Checkpoint before spawning: Create API` |
| Validation Ready    | `[Workspace {id}] Iteration {n} - Ready for validation` | `[Workspace 123] Iteration 1 - Ready for validation`     |
| Final               | `[Workspace {id}] Final - Task completed`               | `[Workspace 123] Final - Task completed`                 |
| Conflict Resolution | `[Auto-Merge] Resolved conflicts using {strategy}`      | `[Auto-Merge] Resolved conflicts using newest_file_wins` |

---

# Error Handling

| Error                      | Cause                     | Solution                  |
| -------------------------- | ------------------------- | ------------------------- |
| "Not a git repository"     | MAIN_REPO_PATH is invalid | Initialize Git repo       |
| "Disk space exhausted"     | Too many workspaces       | Cleanup old workspaces    |
| "Branch already exists"    | Stale previous branch     | Force recreate            |
| "Workspace already exists" | Cleanup failed            | Force delete and recreate |

---

# Troubleshooting

### Debugging Commands

```bash
# List workspace directories
ls -lh /tmp/hephaestus_workspaces/

# List Git branches
git branch --list "workspace-*"

# Prune archived branches
git worktree prune || true
```

---

# Performance Considerations

* Workspace creation: **< 2 seconds**
* Git merges: **< 5 seconds**
* Cleanup: **< 1 second**
* Disk usage: **~100MB per workspace**

### Optimization Tips

* Use shallow clones for large repos
* Apply aggressive cleanup policies
* Archive branches instead of deleting
* Separate repos per project

---

# Future Enhancements

* Distributed workspaces across nodes
* Containerized workspace support
* AI-assisted merge conflict resolution
* Workspace templates
* Workspace profiling dashboards

---

# Summary

The Workspace Isolation System provides:

* parallel execution
* Git-backed reproducibility
* conflict-free workflow
* transparent isolation
* clean history and auditing

It is a foundational component enabling accurate, scalable, safe execution of agents across many simultaneous tasks.

---

If you'd like, I can also generate:

✅ A **Mermaid architecture diagram**
✅ A **WorkspaceManager Python implementation skeleton**
✅ A **migration plan** from Worktrees → Workspaces
✅ Integration notes for Validation, Memory, Monitoring, Queue, etc.

Just tell me what you want next.


