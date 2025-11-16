# Parallel Work Streams & Agent Assignment Plan

**Document Purpose**: Identify parallelizable work streams that can be assigned to different agents simultaneously, with clear boundaries and interfaces.

**Created**: 2025-11-16  
**Status**: Active Planning  
**Related Documents**:
- [Implementation Roadmap](./implementation_roadmap.md)
- [Foundation & Smallest Runnable](./foundation_and_smallest_runnable.md)

---

## Parallelization Strategy

### Principles
1. **Independent Work Streams**: Tasks that don't share code paths or have minimal overlap
2. **Clear Interfaces**: Well-defined contracts between components
3. **Database Schema Coordination**: Shared schema changes need coordination
4. **Test Isolation**: Each stream has its own test suite

---

## Phase 1: Core Workflow Enhancement - Parallel Streams

### Stream A: Task Dependencies & Blocking
**Agent Assignment**: Agent A  
**Files to Modify**:
- `omoi_os/models/task.py` (add `dependencies` JSONB field)
- `omoi_os/services/task_queue.py` (dependency resolution logic)
- `omoi_os/api/routes/tasks.py` (dependency API endpoints)
- `tests/test_task_dependencies.py` (new test file)

**Database Changes**:
- Migration: Add `dependencies` JSONB column to `tasks` table
- Index: Add GIN index on `dependencies` for query performance

**Interface Contracts**:
```python
# Task model
dependencies: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
# Format: {"depends_on": ["task_id_1", "task_id_2"], "blocks": ["task_id_3"]}

# TaskQueueService methods
def get_next_task(self, phase_id: str) -> Task | None:
    # Must filter out tasks with incomplete dependencies
    
def check_dependencies_complete(self, task_id: str) -> bool:
    # New method: Check if all dependencies are completed
    
def get_blocked_tasks(self, task_id: str) -> list[Task]:
    # New method: Get tasks blocked by this task
```

**Dependencies**: None (can start immediately)

**Deliverables**:
- ✅ Task model with dependencies field
- ✅ Dependency resolution in `get_next_task()`
- ✅ Circular dependency detection
- ✅ Tests for dependency resolution

---

### Stream B: Error Handling & Retries
**Agent Assignment**: Agent B  
**Files to Modify**:
- `omoi_os/models/task.py` (add `retry_count`, `max_retries` fields)
- `omoi_os/worker.py` (retry logic)
- `omoi_os/services/task_queue.py` (retry helper methods)
- `tests/test_retry_logic.py` (new test file)

**Database Changes**:
- Migration: Add `retry_count` (INT, default 0) and `max_retries` (INT, default 3) to `tasks` table

**Interface Contracts**:
```python
# Task model
retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

# TaskQueueService methods
def should_retry(self, task_id: str) -> bool:
    # Check if task should be retried
    
def increment_retry(self, task_id: str) -> None:
    # Increment retry count and reset status to pending

# Worker retry logic
def execute_task_with_retry(...):
    # Execute with exponential backoff
```

**Dependencies**: None (can start immediately)

**Deliverables**:
- ✅ Task model with retry fields
- ✅ Retry logic in worker
- ✅ Exponential backoff implementation
- ✅ Error categorization
- ✅ Tests for retry logic

---

### Stream C: Agent Health & Heartbeat
**Agent Assignment**: Agent C  
**Files to Modify**:
- `omoi_os/models/agent.py` (add `last_heartbeat` tracking - already exists)
- `omoi_os/worker.py` (heartbeat emission)
- `omoi_os/services/agent_health.py` (new service)
- `omoi_os/api/routes/agents.py` (new routes file)
- `tests/test_agent_health.py` (new test file)

**Database Changes**:
- No schema changes needed (`last_heartbeat` already exists)

**Interface Contracts**:
```python
# AgentHealthService (new)
class AgentHealthService:
    def emit_heartbeat(self, agent_id: str) -> None:
        # Update agent.last_heartbeat timestamp
        
    def check_agent_health(self, agent_id: str) -> dict:
        # Return health status
        
    def detect_stale_agents(self, timeout_seconds: int = 90) -> list[Agent]:
        # Find agents that haven't heartbeated recently

# Worker heartbeat
def heartbeat_loop(agent_id: str):
    # Emit heartbeat every 30 seconds
```

**Dependencies**: None (can start immediately)

**Deliverables**:
- ✅ Heartbeat mechanism in worker
- ✅ Agent health service
- ✅ Health check API endpoint
- ✅ Stale agent detection
- ✅ Tests for heartbeat and health checks

---

### Stream D: Task Timeout & Cancellation
**Agent Assignment**: Agent D  
**Files to Modify**:
- `omoi_os/models/task.py` (add `timeout_seconds` field)
- `omoi_os/api/main.py` (timeout detection in orchestrator)
- `omoi_os/api/routes/tasks.py` (cancellation endpoint)
- `omoi_os/worker.py` (timeout handling)
- `tests/test_task_timeout.py` (new test file)

**Database Changes**:
- Migration: Add `timeout_seconds` (INT, nullable) to `tasks` table

**Interface Contracts**:
```python
# Task model
timeout_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

# TaskQueueService methods
def check_task_timeout(self, task_id: str) -> bool:
    # Check if task has exceeded timeout
    
def cancel_task(self, task_id: str) -> None:
    # Cancel a running task

# Worker timeout handling
def handle_task_timeout(task: Task):
    # Kill conversation, update status, cleanup
```

**Dependencies**: None (can start immediately)

**Deliverables**:
- ✅ Task model with timeout field
- ✅ Timeout detection in orchestrator
- ✅ Task cancellation API
- ✅ Timeout handling in worker
- ✅ Tests for timeout and cancellation

---

## Phase 1 Coordination Points

### Database Migration Coordination
**When**: Before any agent starts database changes  
**Action**: Create shared migration file that all agents can add to:
```bash
# Create migration file
alembic revision -m "phase_1_enhancements"
# Agents add their schema changes to this file
```

**Coordination Method**:
1. Agent A creates migration file: `002_phase_1_enhancements.py`
2. Agents B, C, D add their changes to the same file
3. Final review before applying migration

### Model Changes Coordination
**Task Model** (`omoi_os/models/task.py`):
- Stream A: Adds `dependencies` field
- Stream B: Adds `retry_count`, `max_retries` fields
- Stream D: Adds `timeout_seconds` field

**Coordination**: Use feature branches, merge in order (A → B → D), or use Git conflict resolution

### Service Interface Coordination
**TaskQueueService** (`omoi_os/services/task_queue.py`):
- Stream A: Modifies `get_next_task()` to respect dependencies
- Stream B: Adds retry helper methods
- Stream D: Adds timeout/cancellation methods

**Coordination**: Each agent adds methods, minimal overlap

---

## Phase 2: Multi-Phase Workflow - Parallel Streams

### Stream E: Phase Definitions & State Machine
**Agent Assignment**: Agent E  
**Files to Create/Modify**:
- `omoi_os/models/phases.py` (new: phase constants and state machine)
- `omoi_os/models/ticket.py` (add phase transition tracking)
- `omoi_os/services/phase_service.py` (new: phase state machine)
- `omoi_os/api/routes/tickets.py` (phase transition endpoint)
- `tests/test_phase_state_machine.py` (new test file)

**Dependencies**: None (can start immediately)

---

### Stream F: Phase-Specific Task Generation
**Agent Assignment**: Agent F  
**Files to Create/Modify**:
- `omoi_os/services/task_generator.py` (new: task generation service)
- `omoi_os/services/task_templates.py` (new: phase-specific templates)
- `omoi_os/api/routes/tickets.py` (task generation endpoint)
- `tests/test_task_generation.py` (new test file)

**Dependencies**: 
- Requires Stream E (phase definitions) - can start after E completes phase constants

**Coordination**: 
- Stream F can start once Stream E defines phase constants
- Stream F uses phase constants from Stream E

---

### Stream G: Phase Gates & Validation
**Agent Assignment**: Agent G  
**Files to Create/Modify**:
- `omoi_os/services/phase_gate.py` (new: gate validation service)
- `omoi_os/services/validation_agent.py` (new: validation agent)
- `omoi_os/api/routes/phases.py` (new: phase gate endpoints)
- `tests/test_phase_gates.py` (new test file)

**Dependencies**:
- Requires Stream E (phase definitions)
- Can start in parallel with Stream F

---

### Stream H: Cross-Phase Context Passing
**Agent Assignment**: Agent H  
**Files to Create/Modify**:
- `omoi_os/models/ticket.py` (add context storage)
- `omoi_os/services/context_service.py` (new: context aggregation)
- `omoi_os/services/context_summarizer.py` (new: context summarization)
- `tests/test_context_passing.py` (new test file)

**Dependencies**:
- Requires Stream E (phase definitions)
- Can start in parallel with Streams F and G

---

## Phase 3: Multi-Agent Coordination - Parallel Streams

### Stream I: Agent Registry & Discovery
**Agent Assignment**: Agent I  
**Files to Create/Modify**:
- `omoi_os/models/agent.py` (enhance capabilities field)
- `omoi_os/services/agent_registry.py` (new: registry service)
- `omoi_os/api/routes/agents.py` (discovery endpoints)
- `tests/test_agent_registry.py` (new test file)

**Dependencies**: None (can start immediately)

---

### Stream J: Agent Communication Protocol
**Agent Assignment**: Agent J  
**Files to Create/Modify**:
- `omoi_os/services/event_bus.py` (add agent messaging)
- `omoi_os/services/agent_messaging.py` (new: messaging service)
- `omoi_os/models/event.py` (add agent-to-agent event types)
- `tests/test_agent_messaging.py` (new test file)

**Dependencies**: 
- Requires Stream I (agent registry) for agent discovery
- Can start after Stream I defines agent capabilities

---

### Stream K: Parallel Task Execution
**Agent Assignment**: Agent K  
**Files to Create/Modify**:
- `omoi_os/services/dependency_graph.py` (new: dependency resolution)
- `omoi_os/services/task_coordinator.py` (new: parallel execution)
- `omoi_os/services/resource_lock.py` (new: resource locking)
- `tests/test_parallel_execution.py` (new test file)

**Dependencies**:
- Requires Stream A (task dependencies) from Phase 1
- Can start after Stream A completes

---

### Stream L: Task Coordination Patterns
**Agent Assignment**: Agent L  
**Files to Create/Modify**:
- `omoi_os/services/task_sync.py` (new: synchronization points)
- `omoi_os/services/task_merge.py` (new: merge/join logic)
- `omoi_os/services/task_split.py` (new: task splitting)
- `tests/test_task_coordination.py` (new test file)

**Dependencies**:
- Requires Stream K (parallel execution)
- Can start after Stream K completes

---

## Agent Assignment Matrix

| Phase | Stream | Agent | Can Start | Blocks | Parallel With |
|-------|--------|-------|-----------|--------|---------------|
| 1 | A: Dependencies | Agent A | ✅ Now | None | B, C, D |
| 1 | B: Retries | Agent B | ✅ Now | None | A, C, D |
| 1 | C: Heartbeat | Agent C | ✅ Now | None | A, B, D |
| 1 | D: Timeout | Agent D | ✅ Now | None | A, B, C |
| 2 | E: Phase State | Agent E | ✅ Now | None | - |
| 2 | F: Task Gen | Agent F | After E | E (constants) | G, H |
| 2 | G: Phase Gates | Agent G | After E | E (constants) | F, H |
| 2 | H: Context | Agent H | After E | E (constants) | F, G |
| 3 | I: Registry | Agent I | ✅ Now | None | - |
| 3 | J: Messaging | Agent J | After I | I (capabilities) | - |
| 3 | K: Parallel Exec | Agent K | After A | A (dependencies) | - |
| 3 | L: Coordination | Agent L | After K | K (parallel) | - |

---

## Immediate Parallel Work (Phase 1)

### Week 1: All 4 Streams in Parallel
```
Agent A: Task Dependencies & Blocking
Agent B: Error Handling & Retries  
Agent C: Agent Health & Heartbeat
Agent D: Task Timeout & Cancellation
```

**Coordination Required**:
1. **Database Migration**: All agents coordinate on single migration file
2. **Task Model**: Sequential merges (A → B → D) or conflict resolution
3. **TaskQueueService**: Each agent adds methods, minimal overlap

**Daily Sync Points**:
- Morning: Share progress, identify conflicts early
- Evening: Review merges, resolve conflicts

---

## Work Stream Boundaries

### Clear Separation Criteria
1. **Different Files**: Streams modify different files when possible
2. **Different Services**: Each stream creates/modifies different services
3. **Different Tests**: Each stream has isolated test suite
4. **Shared Models**: Coordinate via Git branches and merge order

### Interface Contracts
Each stream defines:
- **Input Contracts**: What data/parameters it expects
- **Output Contracts**: What it returns/produces
- **Side Effects**: What it modifies (database, files, etc.)
- **Error Handling**: How it handles failures

---

## Conflict Resolution Strategy

### Database Schema Conflicts
**Strategy**: Single migration file, agents add sequentially
1. Agent A creates migration file
2. Agents B, C, D add their changes in order
3. Final review before applying

### Model Field Conflicts
**Strategy**: Sequential merges or feature flags
1. Agent A merges `dependencies` field
2. Agent B merges `retry_count`, `max_retries` fields
3. Agent D merges `timeout_seconds` field

### Service Method Conflicts
**Strategy**: Each agent adds methods, avoid modifying same methods
- If modification needed: Use feature branches, coordinate merge

---

## Testing Strategy

### Isolated Test Suites
Each stream has its own test file:
- `tests/test_task_dependencies.py` (Stream A)
- `tests/test_retry_logic.py` (Stream B)
- `tests/test_agent_health.py` (Stream C)
- `tests/test_task_timeout.py` (Stream D)

### Integration Tests
After all streams merge:
- `tests/test_phase_1_integration.py` (tests all Phase 1 features together)

---

## Next Steps

1. **Assign Agents**: Assign Agents A, B, C, D to Phase 1 streams
2. **Create Migration**: Agent A creates initial migration file
3. **Set Up Branches**: Each agent works on feature branch
4. **Daily Sync**: Establish daily coordination meetings
5. **Merge Strategy**: Define merge order and conflict resolution

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Assistant | Initial parallel work streams analysis |

