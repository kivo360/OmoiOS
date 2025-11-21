# Workspace Manager Integration Guide

**Created**: 2025-01-XX
**Status**: Implementation Guide
**Purpose**: Guide for integrating the unified WorkspaceManagerService with existing application code

---

## Overview

The `WorkspaceManagerService` integrates the OOP workspace managers (`examples/workspace_managers.py`) with the application's workspace isolation system. It provides:

- **Git-backed workspaces** with automatic branching
- **Database tracking** of workspace metadata
- **Commit management** for validation checkpoints
- **Merge capabilities** with conflict resolution
- **Support for both local and Docker workspaces**

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              WorkspaceManagerService                     │
│  - create_workspace()                                   │
│  - commit_for_validation()                             │
│  - merge_to_parent()                                    │
│  - cleanup_workspace()                                  │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│         OOP Workspace Managers (examples/)              │
│  - LocalWorkspaceManager                                │
│  - DockerWorkspaceManager                               │
│  - RepositoryManager                                    │
│  - CommandExecutor                                      │
└─────────────────────────────────────────────────────────┘
```

---

## Integration Points

### 1. AgentExecutor Integration

**Before** (current code):
```python
class AgentExecutor:
    def __init__(self, phase_id: str, workspace_dir: str, db: Optional[DatabaseService] = None):
        self.workspace_dir = workspace_dir  # Simple string path
        # ... rest of initialization
```

**After** (with WorkspaceManagerService):
```python
from omoi_os.services.workspace_manager import WorkspaceManagerService

class AgentExecutor:
    def __init__(
        self,
        phase_id: str,
        workspace_dir: Optional[str] = None,  # Optional - can create workspace
        db: Optional[DatabaseService] = None,
        workspace_manager: Optional[WorkspaceManagerService] = None,
        agent_id: Optional[str] = None,
    ):
        self.db = db or DatabaseService()
        self.workspace_manager = workspace_manager or WorkspaceManagerService(self.db)
        
        # Create workspace if not provided
        if workspace_dir is None and agent_id:
            workspace_info = self.workspace_manager.create_workspace(
                agent_id=agent_id,
                repo_url=None,  # Use existing repo or configure
                branch="main",
            )
            self.workspace_dir = workspace_info.working_directory
        else:
            self.workspace_dir = workspace_dir
        
        # ... rest of initialization
```

### 2. Worker Integration

**Before** (current code):
```python
def main():
    workspace_dir = "/tmp/omoi_os_workspaces/worker_123"
    executor = AgentExecutor(phase_id="PHASE_IMPLEMENTATION", workspace_dir=workspace_dir)
```

**After** (with WorkspaceManagerService):
```python
from omoi_os.services.workspace_manager import WorkspaceManagerService

def main():
    db = DatabaseService()
    workspace_manager = WorkspaceManagerService(db)
    agent_id = register_agent(db, agent_type="worker", phase_id="PHASE_IMPLEMENTATION")
    
    # Create workspace automatically
    workspace_info = workspace_manager.create_workspace(
        agent_id=str(agent_id),
        repo_url=os.getenv("REPO_URL"),  # Optional: clone repo
        branch="main",
    )
    
    executor = AgentExecutor(
        phase_id="PHASE_IMPLEMENTATION",
        workspace_dir=workspace_info.working_directory,
        workspace_manager=workspace_manager,
        agent_id=str(agent_id),
    )
```

### 3. Validation System Integration

**Before**:
```python
# Manual commit creation
subprocess.run(["git", "add", "-A"], cwd=workspace_dir)
subprocess.run(["git", "commit", "-m", "Validation checkpoint"], cwd=workspace_dir)
```

**After**:
```python
from omoi_os.services.workspace_manager import WorkspaceManagerService

workspace_manager = WorkspaceManagerService(db)

# Create validation checkpoint
commit_info = workspace_manager.commit_for_validation(
    agent_id=agent_id,
    iteration=iteration_number,
    message=f"[Validation] Iteration {iteration_number}"
)

# Use commit_info.commit_sha for validation
validator.check_commit(commit_info.commit_sha)
```

### 4. Ticket Workflow Integration

**Before**:
```python
# Simple workspace directory
workspace_dir = f"/tmp/workspaces/ticket_{ticket_id}"
```

**After**:
```python
from omoi_os.services.workspace_manager import WorkspaceManagerService

workspace_manager = WorkspaceManagerService(db)

# Create workspace for ticket
workspace_info = workspace_manager.create_workspace(
    agent_id=f"ticket-{ticket_id}",
    repo_url=ticket.repo_url,
    branch=ticket.branch or "main",
    parent_id=parent_ticket_id,  # If this is a child ticket
)

# Use workspace_info.working_directory for agent execution
```

---

## Migration Strategy

### Phase 1: Add WorkspaceManagerService (Non-Breaking)

1. **Add the service** without changing existing code:
   ```python
   # New code can use WorkspaceManagerService
   workspace_manager = WorkspaceManagerService(db)
   workspace_info = workspace_manager.create_workspace(agent_id="new-agent")
   
   # Old code continues to work
   executor = AgentExecutor(workspace_dir="/tmp/old/path")
   ```

2. **Make workspace_dir optional** in AgentExecutor:
   ```python
   def __init__(self, ..., workspace_dir: Optional[str] = None, ...):
       if workspace_dir is None:
           # Create workspace automatically
           workspace_info = self.workspace_manager.create_workspace(...)
           workspace_dir = workspace_info.working_directory
   ```

### Phase 2: Update Worker Code

1. **Update worker registration** to create workspaces:
   ```python
   agent_id = register_agent(db, agent_type="worker", phase_id=phase_id)
   workspace_manager = WorkspaceManagerService(db)
   workspace_info = workspace_manager.create_workspace(agent_id=str(agent_id))
   ```

2. **Pass workspace_info to AgentExecutor**:
   ```python
   executor = AgentExecutor(
       phase_id=phase_id,
       workspace_dir=workspace_info.working_directory,
       workspace_manager=workspace_manager,
   )
   ```

### Phase 3: Add Database Schema

1. **Create migration** for workspace tables:
   ```python
   # alembic/versions/XXX_add_workspace_tables.py
   def upgrade():
       op.create_table(
           'agent_workspaces',
           sa.Column('agent_id', sa.String(), primary_key=True),
           sa.Column('working_directory', sa.String(), nullable=False),
           sa.Column('branch_name', sa.String(), nullable=False),
           sa.Column('parent_commit', sa.String(), nullable=True),
           sa.Column('created_at', sa.DateTime(), nullable=False),
           # ...
       )
       
       op.create_table(
           'workspace_commits',
           sa.Column('id', sa.String(), primary_key=True),
           sa.Column('agent_id', sa.String(), nullable=False),
           sa.Column('commit_sha', sa.String(), nullable=False),
           sa.Column('files_changed', sa.Integer(), nullable=False),
           sa.Column('message', sa.String(), nullable=False),
           sa.Column('created_at', sa.DateTime(), nullable=False),
           # ...
       )
   ```

2. **Update WorkspaceManagerService** to use database:
   ```python
   def _store_workspace_info(self, agent_id, working_directory, branch_name, parent_commit):
       with self.db.get_session() as session:
           workspace = AgentWorkspace(
               agent_id=agent_id,
               working_directory=working_directory,
               branch_name=branch_name,
               parent_commit=parent_commit,
               created_at=utc_now(),
           )
           session.add(workspace)
           session.commit()
   ```

### Phase 4: Add Validation Checkpoints

1. **Update ValidationOrchestrator** to use commit_for_validation:
   ```python
   from omoi_os.services.workspace_manager import WorkspaceManagerService
   
   workspace_manager = WorkspaceManagerService(db)
   
   # Before validation
   commit_info = workspace_manager.commit_for_validation(
       agent_id=agent_id,
       iteration=iteration,
   )
   
   # Validate the commit
   validation_result = validator.validate_commit(commit_info.commit_sha)
   ```

### Phase 5: Add Merge Capabilities

1. **Update ticket completion** to merge workspace:
   ```python
   # When ticket is completed
   merge_result = workspace_manager.merge_to_parent(
       agent_id=agent_id,
       target_branch="main",
   )
   
   # Cleanup workspace
   cleanup_result = workspace_manager.cleanup_workspace(
       agent_id=agent_id,
       preserve_branch=True,  # Keep branch for debugging
   )
   ```

---

## Configuration

### Environment Variables

```bash
# Workspace paths (from WorkspaceSettings)
WORKSPACE_ROOT=/path/to/workspaces
WORKSPACE_WORKER_DIR=/tmp/omoi_os_workspaces

# Workspace limits (future)
WORKSPACE_MAX_COUNT=50
WORKSPACE_MAX_DEPTH=10
WORKSPACE_DISK_THRESHOLD_GB=10

# Merge strategy
WORKSPACE_AUTO_MERGE=true
WORKSPACE_CONFLICT_STRATEGY=newest_file_wins
```

### YAML Configuration

```yaml
# config/base.yaml
workspace:
  root: "workspaces"
  worker_dir: "/tmp/omoi_os_workspaces"
  max_count: 50
  max_depth: 10
  disk_threshold_gb: 10
  auto_merge: true
  conflict_strategy: "newest_file_wins"
```

---

## API Reference

### WorkspaceManagerService

#### `create_workspace()`

Creates a new isolated workspace with Git branching.

```python
workspace_info = workspace_manager.create_workspace(
    agent_id="agent-123",
    repo_url="https://github.com/user/repo.git",  # Optional
    branch="main",
    parent_id="agent-001",  # Optional: for inheritance
    use_docker=False,  # Optional: use Docker workspace
    host_port=8020,  # Optional: for Docker
)

# Returns WorkspaceInfo:
# - working_directory: str
# - branch_name: str
# - parent_commit: Optional[str]
# - workspace_id: Optional[str]
```

#### `commit_for_validation()`

Creates a Git commit for validator inspection.

```python
commit_info = workspace_manager.commit_for_validation(
    agent_id="agent-123",
    iteration=1,
    message="Optional custom message",
)

# Returns CommitInfo:
# - commit_sha: str
# - files_changed: int
# - message: str
# - timestamp: Optional[str]
```

#### `get_workspace_changes()`

Returns detailed file diff metadata.

```python
changes = workspace_manager.get_workspace_changes(
    agent_id="agent-123",
    since_commit="abc123",  # Optional: compare against specific commit
)

# Returns WorkspaceChanges:
# - files_created: List[str]
# - files_modified: List[str]
# - files_deleted: List[str]
# - total_changes: int
# - stats: Dict[str, int]
# - detailed_diff: Optional[str]
```

#### `merge_to_parent()`

Merges workspace changes back into parent branch.

```python
merge_result = workspace_manager.merge_to_parent(
    agent_id="agent-123",
    target_branch="main",
)

# Returns MergeResult:
# - status: str ("success" | "conflict_resolved")
# - merged_to: str
# - commit_sha: str
# - conflicts_resolved: List[str]
# - resolution_strategy: str
# - total_conflicts: int
```

#### `cleanup_workspace()`

Deletes workspace and optionally preserves Git branch.

```python
cleanup_result = workspace_manager.cleanup_workspace(
    agent_id="agent-123",
    preserve_branch=True,  # Keep branch for debugging
)

# Returns Dict:
# - status: str
# - branch_preserved: bool
# - disk_space_freed_mb: int
```

---

## Benefits

1. **Unified API**: Single service for all workspace operations
2. **Git Integration**: Automatic branching, commits, and merges
3. **Database Tracking**: All workspace metadata stored in database
4. **Conflict Resolution**: Automatic merge conflict handling
5. **Extensibility**: Easy to add Docker, Kubernetes, or remote workspaces
6. **Backward Compatible**: Existing code continues to work

---

## Next Steps

1. ✅ Create `WorkspaceManagerService` (done)
2. ⏳ Add database schema migration
3. ⏳ Update `AgentExecutor` to use service
4. ⏳ Update worker code to create workspaces
5. ⏳ Add validation checkpoint integration
6. ⏳ Add merge capabilities to ticket workflow
7. ⏳ Add Docker workspace support
8. ⏳ Add cleanup automation

---

## Related Documentation

- [Workspace Isolation System Design](../design/agents/workspace_isolation_system.md)
- [Agent Executor Service](../services/agent_executor.md)
- [Validation System Design](../design/workflows/validation_system.md)

