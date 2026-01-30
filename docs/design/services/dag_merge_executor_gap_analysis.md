# DAG Merge Executor Gap Analysis

**Created**: 2026-01-30
**Status**: Analysis Complete
**Purpose**: Compare DAG Merge Executor design against current implementation, identify gaps, and plan integration while maintaining ticket-level branching.

---

## Executive Summary

The DAG Merge Executor design provides a sophisticated approach to parallel task execution with git branch merging and LLM-assisted conflict resolution. Our current implementation has strong foundations in task coordination and result synthesis, but lacks the **code synthesis** capabilities (branch merging, conflict resolution) that would enable true parallel code development.

**Key Decision**: Maintain **ticket-level branches** (not task-level) while adding merge capabilities for convergence points within a ticket's task DAG.

---

## Current Implementation Status

### What We Have (Working)

| Component | Location | Description |
|-----------|----------|-------------|
| **Task Dependencies** | `Task.dependencies` JSONB | DAG structure with `depends_on` lists |
| **Parallel Opportunity Detection** | `SpecTaskExecutionService._parse_parallel_opportunities()` | Parses SYNC phase output |
| **Convergence Point Detection** | `SpecTaskExecutionService._find_continuation_task()` | Finds tasks depending on ALL parallel sources |
| **Coordination Registration** | `CoordinationService.register_join()` | Publishes `coordination.join.created` events |
| **Result Synthesis** | `SynthesisService` | Merges task result metadata into `synthesis_context` |
| **File Ownership** | `OwnershipValidationService` + `Task.owned_files` | Conflict prevention via file patterns |
| **Sandbox Isolation** | `DaytonaSpawner` | Isolated Daytona environments per task |
| **Ticket-Level Branches** | `BranchWorkflowService` | Git branches per ticket (e.g., `ticket/TKT-001`) |

### Data Flow (Current)

```
SYNC Phase → parallel_opportunities
    ↓
SpecTaskExecutionService → register_join()
    ↓
coordination.join.created event
    ↓
SynthesisService tracks pending join
    ↓
Parallel tasks complete → TASK_COMPLETED events
    ↓
SynthesisService merges RESULTS (metadata only)
    ↓
Continuation task receives synthesis_context
```

**What's Missing**: The current flow synthesizes **task results** (metadata, outputs) but not **code changes** (git commits, file modifications).

---

## Gap Analysis

### Gap 1: Branch Merge at Convergence Points

**DAG Executor Has:**
```python
class MergeCoordinator:
    async def merge_convergence_point(
        self,
        git_ops: GitOperations,
        incoming_branches: List[str],
        target_branch: str,
        task: Task,
        dag_run: DAGRun
    ) -> str:
        # Score branches, sort by conflicts, merge sequentially
```

**We Have:**
- `SynthesisService` merges task result dicts
- No git branch merging

**Impact:**
- Parallel tasks can work on code, but their changes don't merge
- Continuation tasks don't have access to code from ALL parallel predecessors
- Only the last task's code changes persist (or conflicts occur)

**Recommendation:**
Create `ConvergenceMerger` service that:
1. Operates at **ticket-level** (all parallel tasks share the ticket branch)
2. Uses **sequential commits** instead of branch merge when possible
3. Falls back to **sandbox-based merge** when conflicts are detected
4. Invokes **LLM conflict resolution** via Claude Agent SDK

---

### Gap 2: Least-Conflicts-First Merge Ordering

**DAG Executor Has:**
```python
async def _score_conflicts(self, git_ops, base, candidates) -> dict[str, int]:
    """Score conflict count for each candidate against base."""
    for branch in candidates:
        count = await git_ops.count_conflicts_dry_run(branch)
        scores[branch] = count
    return scores
```

**We Have:**
- Nothing - no conflict scoring

**Impact:**
- If we add branch merging, merging in wrong order increases conflicts
- Each conflict requires LLM invocation (expensive)

**Recommendation:**
Add `ConflictScorer` that:
1. Uses `git merge-tree --write-tree` for dry-run conflict detection (Git 2.38+)
2. Scores branches before merging
3. Sorts by ascending conflict count
4. Passes order to `ConvergenceMerger`

---

### Gap 3: LLM Conflict Resolution (Claude Agent SDK)

**DAG Executor Has:**
```python
class LLMResolver:
    async def resolve_conflict(
        self,
        file_path: str,
        ours: str,
        theirs: str,
        context: MergeContext
    ) -> str:
        # Uses Claude Agent SDK (agentic, not one-shot)
        async for message in query(prompt=prompt, options=options):
            # Process tool use, file reads, etc.
```

**We Have:**
- `LLMService` with `structured_output()` (one-shot)
- No Claude Agent SDK integration for agentic workflows

**Impact:**
- Cannot intelligently resolve merge conflicts
- Manual intervention required for any git conflicts

**Recommendation:**
Create `AgentConflictResolver` that:
1. Uses **Claude Agent SDK** (`claude-code-sdk` package)
2. Runs **inside a Daytona sandbox** (isolated environment)
3. Has access to `Read`, `Write`, `Bash` tools for context gathering
4. Can examine related files to make informed merge decisions
5. Includes retry logic with exponential backoff

**Prerequisites:**
```bash
# Claude Code CLI (required by SDK)
npm install -g @anthropic-ai/claude-code

# Python SDK
pip install claude-code-sdk

# Environment
export ANTHROPIC_API_KEY=your-key
```

---

### Gap 4: Git Operations for Merge

**DAG Executor Has:**
```python
class GitOperations:
    async def merge(self, branch: str, no_commit: bool = True) -> MergeResult
    async def merge_abort(self) -> None
    async def count_conflicts_dry_run(self, branch: str) -> int
    async def get_conflict_content(self, file_path: str) -> ConflictInfo
    async def write_file(self, file_path: str, content: str) -> None
```

**We Have:**
- `DaytonaSpawner` with basic git setup (clone, checkout)
- No merge operations

**Impact:**
- Cannot perform git merges in sandboxes

**Recommendation:**
Create `SandboxGitOperations` that:
1. Wraps Daytona sandbox git operations
2. Adds merge capabilities via `sandbox.process.exec()`
3. Includes conflict detection and content extraction
4. Works with `AgentConflictResolver` for resolution

---

### Gap 5: MergeAttempt Audit Trail

**DAG Executor Has:**
```python
class MergeAttempt(Base):
    id: str
    task_id: str
    incoming_branches: List[str]
    merge_order: List[str]
    conflict_scores: dict
    success: bool
    llm_invocations: int
    llm_resolution_log: dict
```

**We Have:**
- Nothing - no merge audit trail

**Impact:**
- Cannot debug merge failures
- No visibility into LLM conflict resolution decisions
- Cannot analyze merge patterns over time

**Recommendation:**
Create `MergeAttempt` model and `MergeAttemptRepository`:
1. Track all merge attempts at convergence points
2. Store conflict scores and merge order
3. Log LLM resolution decisions
4. Enable post-hoc analysis and debugging

---

## Proposed Architecture (Ticket-Level Branching)

### Design Decision: Ticket-Level vs Task-Level Branches

**Task-Level Branches (DAG Executor):**
```
main
  └── task/TSK-001 (parallel)
  └── task/TSK-002 (parallel)
      └── Merge at convergence → task/TSK-003
```

**Ticket-Level Branches (Our Approach):**
```
main
  └── ticket/TKT-001
        ├── TSK-001 commits (sequential within ticket)
        ├── TSK-002 commits (may conflict with TSK-001)
        └── Convergence: merge/resolve before TSK-003
```

**Why Ticket-Level is Better for Us:**

1. **Simpler branch management** - One branch per ticket, not N branches per ticket
2. **Natural PR workflow** - Ticket branch → PR to main
3. **Existing infrastructure** - `BranchWorkflowService` already works this way
4. **Conflict surface** - Conflicts happen within ticket branch, easier to reason about
5. **Spec context preserved** - All tasks for a spec share context in one branch

**Trade-off:**
- Parallel tasks within a ticket can't truly run in parallel on code
- Must serialize commits or merge mid-flight

### Proposed Solution: Sequential-First, Merge-on-Conflict

```
┌─────────────────────────────────────────────────────────────────┐
│                    Ticket Branch: ticket/TKT-001                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TSK-001 ────────► commits ────┐                               │
│  (parallel)                    │                               │
│                                ├──► Convergence Point (TSK-003)│
│  TSK-002 ────────► commits ────┘                               │
│  (parallel)                    │                               │
│                                │                               │
│  Strategy:                     │                               │
│  1. TSK-001 completes, pushes  │                               │
│  2. TSK-002 pulls, rebases     │                               │
│     - If clean: push           │                               │
│     - If conflict: LLM resolve │                               │
│  3. TSK-003 starts with merged │                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ConvergenceMergeService                      │
├─────────────────────────────────────────────────────────────────┤
│  - Detects when convergence point task is ready                 │
│  - Coordinates merge of parallel task commits                   │
│  - Uses ConflictScorer for ordering                             │
│  - Delegates to AgentConflictResolver for conflicts             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐
│ ConflictScorer  │ │ SandboxGitOps   │ │ AgentConflictResolver   │
├─────────────────┤ ├─────────────────┤ ├─────────────────────────┤
│ - Dry-run merge │ │ - Git merge     │ │ - Claude Agent SDK      │
│ - Count conflicts│ │ - Conflict info │ │ - Runs in sandbox       │
│ - Sort branches │ │ - Rebase        │ │ - File context access   │
│                 │ │ - Push          │ │ - Agentic resolution    │
└─────────────────┘ └─────────────────┘ └─────────────────────────┘
                                                    │
                                                    ▼
                                        ┌─────────────────────────┐
                                        │   MergeAttemptRepository│
                                        ├─────────────────────────┤
                                        │ - Audit trail           │
                                        │ - LLM decision log      │
                                        │ - Conflict metrics      │
                                        └─────────────────────────┘
```

---

## Implementation Plan

### Phase A: Foundation (Monitoring & Audit)

**Goal**: Understand real conflict patterns before building resolution

| Task | Description | Effort |
|------|-------------|--------|
| A1 | Create `MergeAttempt` model and migration | 2h |
| A2 | Add conflict detection to `DaytonaSpawner` (log only) | 3h |
| A3 | Create `OwnershipConflictMetrics` dashboard | 2h |
| A4 | Monitor owned_files overlaps in production | 1 week observation |

**Output**: Data on how often parallel tasks would conflict

---

### Phase B: Git Operations

**Goal**: Enable git merge operations in sandboxes

| Task | Description | Effort |
|------|-------------|--------|
| B1 | Create `SandboxGitOperations` service | 4h |
| B2 | Implement merge, rebase, conflict detection | 4h |
| B3 | Add `git merge-tree` dry-run for conflict scoring | 2h |
| B4 | Create `ConflictScorer` service | 3h |
| B5 | Unit tests for git operations | 3h |

**Output**: Ability to merge branches and detect conflicts in sandboxes

---

### Phase C: LLM Conflict Resolution

**Goal**: Agentic conflict resolution using Claude Agent SDK

| Task | Description | Effort |
|------|-------------|--------|
| C1 | Add `claude-code-sdk` dependency | 1h |
| C2 | Create `AgentConflictResolver` service | 6h |
| C3 | Build merge context for LLM (task info, related files) | 3h |
| C4 | Implement retry with exponential backoff | 2h |
| C5 | Add MCP tools for git context (optional) | 4h |
| C6 | Integration tests with mock sandbox | 4h |

**Output**: LLM-powered conflict resolution that runs in sandboxes

---

### Phase D: Convergence Merge Service

**Goal**: Orchestrate merge at convergence points

| Task | Description | Effort |
|------|-------------|--------|
| D1 | Create `ConvergenceMergeService` | 6h |
| D2 | Integrate with `SynthesisService` events | 3h |
| D3 | Implement least-conflicts-first ordering | 2h |
| D4 | Handle edge cases (single dep, no conflicts) | 2h |
| D5 | Update `DaytonaSpawner` to call merge before spawn | 3h |
| D6 | End-to-end tests | 4h |

**Output**: Automatic merge at convergence points before continuation task spawns

---

### Phase E: Integration & Polish

**Goal**: Production-ready integration

| Task | Description | Effort |
|------|-------------|--------|
| E1 | Wire into `orchestrator_worker.py` | 2h |
| E2 | Add observability (metrics, logging) | 3h |
| E3 | Error handling and recovery | 3h |
| E4 | Documentation | 2h |
| E5 | Load testing with parallel specs | 4h |

**Output**: Production-ready convergence merge system

---

## Total Estimated Effort

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| A: Foundation | ~1 week (+ observation) | None |
| B: Git Operations | ~16h | None |
| C: LLM Resolution | ~20h | B |
| D: Convergence Merge | ~20h | B, C |
| E: Integration | ~14h | D |

**Total**: ~70 hours of development + 1 week observation

---

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `services/sandbox_git_operations.py` | Git operations within Daytona sandboxes |
| `services/conflict_scorer.py` | Dry-run merge conflict scoring |
| `services/agent_conflict_resolver.py` | Claude Agent SDK conflict resolution |
| `services/convergence_merge_service.py` | Orchestrates merge at convergence points |
| `models/merge_attempt.py` | Audit trail for merge attempts |
| `migrations/XXX_add_merge_attempt.py` | Database migration |

### Modified Files

| File | Changes |
|------|---------|
| `services/daytona_spawner.py` | Call convergence merge before spawn |
| `services/synthesis_service.py` | Emit events for merge coordination |
| `workers/orchestrator_worker.py` | Initialize convergence merge service |
| `pyproject.toml` | Add `claude-code-sdk` dependency |

---

## Risk Assessment

### Low Risk
- **MergeAttempt model**: Pure addition, no breaking changes
- **ConflictScorer**: Read-only git operations

### Medium Risk
- **SandboxGitOperations**: New git operations, need thorough testing
- **ConvergenceMergeService**: Orchestration complexity

### High Risk
- **AgentConflictResolver**:
  - Claude Agent SDK is relatively new
  - LLM decisions can be unpredictable
  - Need good fallback (manual resolution flag)
  - Cost implications for many conflicts

### Mitigation
- Feature flag for convergence merge (enable per project)
- Fallback to manual resolution if LLM fails N times
- Comprehensive audit logging for debugging
- Start with opt-in, graduate to default

---

## Open Questions

1. **Conflict threshold**: How many conflicts before flagging for human review?
2. **Cost limits**: Budget for LLM conflict resolution per ticket?
3. **Timeout handling**: What if merge takes too long?
4. **Partial merge**: If 2/3 branches merge cleanly, proceed or wait?
5. **Rollback**: How to handle failed merges mid-convergence?

---

## Conclusion

The current implementation has strong foundations for parallel task coordination and result synthesis. The main gap is **code synthesis** - merging actual git changes from parallel tasks.

**Recommended approach:**
1. Keep ticket-level branches (simpler, aligns with PR workflow)
2. Add merge capabilities at convergence points within tickets
3. Use Claude Agent SDK for intelligent, agentic conflict resolution
4. Build comprehensive audit trail for debugging and analysis
5. Start with monitoring to understand real conflict patterns

This approach maintains our existing architecture while adding the powerful merge capabilities from the DAG Executor design.
