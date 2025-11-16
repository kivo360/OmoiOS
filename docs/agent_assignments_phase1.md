# Phase 1 Agent Assignments - Quick Reference

**Status**: Ready for Assignment  
**Timeline**: Week 1-2  
**All streams can start immediately (Week 1)**

---

## 🎯 Agent A: Task Dependencies & Blocking

### Files to Modify
- `omoi_os/models/task.py` - Add `dependencies` field
- `omoi_os/services/task_queue.py` - Add dependency resolution
- `omoi_os/api/routes/tasks.py` - Add dependency endpoints
- `tests/test_task_dependencies.py` - **NEW FILE**

### Database Migration
```python
# Add to migration file (coordinate with other agents)
op.add_column('tasks', sa.Column('dependencies', sa.dialects.postgresql.JSONB, nullable=True))
op.create_index('idx_tasks_dependencies', 'tasks', ['dependencies'], postgresql_using='gin')
```

### Key Methods to Implement
```python
# TaskQueueService
def check_dependencies_complete(self, task_id: str) -> bool:
    """Check if all dependencies are completed"""
    
def get_blocked_tasks(self, task_id: str) -> list[Task]:
    """Get tasks blocked by this task"""
    
def get_next_task(self, phase_id: str) -> Task | None:
    """UPDATED: Filter out tasks with incomplete dependencies"""
```

### Success Criteria
- ✅ Tasks can have dependencies (list of task IDs)
- ✅ `get_next_task()` only returns tasks with completed dependencies
- ✅ Circular dependency detection
- ✅ Tests pass

---

## 🔄 Agent B: Error Handling & Retries

### Files to Modify
- `omoi_os/models/task.py` - Add `retry_count`, `max_retries` fields
- `omoi_os/worker.py` - Add retry logic
- `omoi_os/services/task_queue.py` - Add retry helper methods
- `tests/test_retry_logic.py` - **NEW FILE**

### Database Migration
```python
# Add to migration file (coordinate with other agents)
op.add_column('tasks', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
op.add_column('tasks', sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'))
```

### Key Methods to Implement
```python
# TaskQueueService
def should_retry(self, task_id: str) -> bool:
    """Check if task should be retried"""
    
def increment_retry(self, task_id: str) -> None:
    """Increment retry count and reset status to pending"""

# Worker
def execute_task_with_retry(self, task: Task) -> None:
    """Execute task with exponential backoff retry logic"""
```

### Success Criteria
- ✅ Failed tasks automatically retry up to `max_retries`
- ✅ Exponential backoff (1s, 2s, 4s, 8s)
- ✅ Permanent failures marked after max retries
- ✅ Tests pass

---

## 💓 Agent C: Agent Health & Heartbeat

### Files to Modify
- `omoi_os/worker.py` - Add heartbeat emission
- `omoi_os/services/agent_health.py` - **NEW FILE**
- `omoi_os/api/routes/agents.py` - **NEW FILE** (health endpoints)
- `tests/test_agent_health.py` - **NEW FILE**

### Database Migration
- ✅ No changes needed (`last_heartbeat` already exists in Agent model)

### Key Methods to Implement
```python
# AgentHealthService (NEW)
class AgentHealthService:
    def emit_heartbeat(self, agent_id: str) -> None:
        """Update agent.last_heartbeat timestamp"""
        
    def check_agent_health(self, agent_id: str) -> dict:
        """Return health status"""
        
    def detect_stale_agents(self, timeout_seconds: int = 90) -> list[Agent]:
        """Find agents that haven't heartbeated recently"""

# Worker
def heartbeat_loop(agent_id: str):
    """Emit heartbeat every 30 seconds (background thread)"""
```

### Success Criteria
- ✅ Agents emit heartbeats every 30 seconds
- ✅ Stale agents detected (no heartbeat for 90+ seconds)
- ✅ Health check API endpoint (`GET /api/v1/agents/{id}/health`)
- ✅ Tests pass

---

## ⏱️ Agent D: Task Timeout & Cancellation

### Files to Modify
- `omoi_os/models/task.py` - Add `timeout_seconds` field
- `omoi_os/api/main.py` - Add timeout detection in orchestrator
- `omoi_os/api/routes/tasks.py` - Add cancellation endpoint
- `omoi_os/worker.py` - Add timeout handling
- `tests/test_task_timeout.py` - **NEW FILE**

### Database Migration
```python
# Add to migration file (coordinate with other agents)
op.add_column('tasks', sa.Column('timeout_seconds', sa.Integer(), nullable=True))
```

### Key Methods to Implement
```python
# TaskQueueService
def check_task_timeout(self, task_id: str) -> bool:
    """Check if task has exceeded timeout"""
    
def cancel_task(self, task_id: str) -> None:
    """Cancel a running task"""

# Worker
def handle_task_timeout(self, task: Task) -> None:
    """Kill conversation, update status, cleanup resources"""

# API
@router.post("/tasks/{task_id}/cancel")
async def cancel_task(...):
    """Cancel a running task"""
```

### Success Criteria
- ✅ Tasks can have timeout (seconds)
- ✅ Orchestrator detects timeouts
- ✅ Tasks can be cancelled via API
- ✅ Worker handles timeout (kills conversation)
- ✅ Tests pass

---

## 🔄 Coordination Points

### 1. Database Migration File
**Action**: Agent A creates migration file, others add to it
```bash
# Agent A runs:
alembic revision -m "phase_1_enhancements"

# File created: migrations/versions/002_phase_1_enhancements.py
# All agents add their schema changes to this file
```

### 2. Task Model Coordination
**Strategy**: Sequential merges
1. Agent A merges `dependencies` field
2. Agent B merges `retry_count`, `max_retries` fields  
3. Agent D merges `timeout_seconds` field

**OR**: Use feature branches, merge in order

### 3. TaskQueueService Coordination
**Strategy**: Each agent adds new methods (minimal overlap)
- Agent A: Modifies `get_next_task()`, adds dependency methods
- Agent B: Adds retry helper methods
- Agent D: Adds timeout/cancellation methods

---

## 📋 Daily Checklist

### Morning Sync (15 min)
- [ ] Share progress from previous day
- [ ] Identify any conflicts early
- [ ] Coordinate database migration changes
- [ ] Review test failures

### Evening Sync (15 min)
- [ ] Review merges
- [ ] Resolve conflicts
- [ ] Run full test suite
- [ ] Plan next day

---

## ✅ Definition of Done

Each agent's work is done when:
1. ✅ All code implemented
2. ✅ All tests written and passing
3. ✅ Database migration created/updated
4. ✅ Code reviewed
5. ✅ Merged to main branch
6. ✅ Integration tests pass

---

## 🚀 Getting Started

### For Each Agent:
1. Create feature branch: `git checkout -b feature/phase1-{stream-letter}`
2. Read the detailed stream description in `docs/parallel_work_streams.md`
3. Start with database migration (coordinate with others)
4. Implement model changes
5. Implement service logic
6. Write tests
7. Submit for review

### Example Branch Names:
- `feature/phase1-a-dependencies`
- `feature/phase1-b-retries`
- `feature/phase1-c-heartbeat`
- `feature/phase1-d-timeout`

---

## 📞 Communication

- **Slack/Channel**: #phase1-coordination
- **Daily Standup**: 9:00 AM
- **Conflict Resolution**: Tag @tech-lead
- **Questions**: Ask in channel, don't block

---

**Ready to assign agents!** 🎉

