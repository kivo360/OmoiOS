# Foundation Architecture & Smallest Runnable Code Path

**Document Purpose**: Cross-reference OpenHands SDK capabilities with Tier 0 critical questions and define the absolute minimum working system we need to build iteratively.

**Created**: 2025-11-16  
**Related Documents**:
- [OpenHands Insights & Prioritization](./openhands_insights_and_prioritization.md)
- [Implementation Questions](./implementation_questions.md)
- [Multi-Agent Orchestration Design](./design/multi_agent_orchestration.md)

---

## Part 1: Cross-Reference Analysis - OpenHands vs. Our Needs

### Tier 0 Question: Q1.5 - State Store Selection

**What OpenHands Provides**:
- File-based conversation persistence (`FileStore` → `LocalFileStore`)
- `ConversationState` with fields: `id`, `agent`, `workspace`, `persistence_dir`, `max_iterations`, `agent_status`, `stats`
- `EventLog` stores events separately in `events/` directory
- SQLite used by agent-server for server metadata only (not conversation data)
- Custom persistence: Implement `FileStore` interface (`write`, `read`, `list`, `delete`)

**What We Need But OpenHands Doesn't Provide**:
- ❌ Ticket state management (status, phase, priority, blocking_ticket_id)
- ❌ Task queue with priority and dependencies
- ❌ Agent registry (agent_id, agent_type, status, capabilities, last_heartbeat)
- ❌ System-wide event history with cross-conversation queries
- ❌ Alert/diagnostic records
- ❌ Workflow orchestration state (phase gates, validation results)
- ❌ ACID transactions across multiple entities
- ❌ Complex queries (e.g., "find all HIGH priority tasks for PHASE_IMPLEMENTATION")

**Gap Analysis**:
- OpenHands conversation persistence is **orthogonal** to our orchestration state
- We need a **separate PostgreSQL database** for tickets, tasks, agents, alerts
- OpenHands conversations can live in filesystem while orchestration metadata lives in PostgreSQL
- Alternative: Implement custom `FileStore` that syncs to PostgreSQL, but adds complexity

**Decision for Smallest Runnable**:
✅ **Use PostgreSQL for all orchestration state (tickets, tasks, agents, events)**  
✅ **Let OpenHands use file-based persistence for conversations (default behavior)**  
✅ **Link via foreign key: `Task.conversation_id` → OpenHands conversation directory name**

---

### Tier 0 Question: Q1.4 - Event Bus Architecture

**What OpenHands Provides**:
- `EventService` with `PubSub[Event]` for conversation-scoped pub/sub
- Event types: `MessageEvent`, `ActionEvent`, `ObservationEvent`, `AgentErrorEvent`, `ConversationStateUpdateEvent`
- WebSocket streaming: `/conversations/{id}/events/socket`
- Callbacks: `Conversation(callbacks=[event_callback])` for event hooks
- Events are **conversation-scoped** only

**What We Need But OpenHands Doesn't Provide**:
- ❌ System-wide event bus for cross-agent communication
- ❌ Event types: `AGENT_REGISTERED`, `HEARTBEAT_MISSED`, `TASK_ASSIGNED`, `TASK_COMPLETED`, `PHASE_TRANSITION`, `ALERT_RAISED`
- ❌ Topic-based routing (subscribe to ticket_id, phase_id, agent_id)
- ❌ Event delivery guarantees (at-least-once, exactly-once)
- ❌ Event persistence with retention policies
- ❌ Dead letter queue for failed deliveries
- ❌ Cross-conversation event queries

**Gap Analysis**:
- OpenHands events are **internal to a conversation**
- We need a **separate event bus** for orchestration-level events
- We can bridge: Use OpenHands callbacks to publish conversation events to our system bus

**Decision for Smallest Runnable**:
✅ **Build system-wide event bus using Redis Pub/Sub** (simplest, no additional dependencies)  
✅ **Define orchestration event types separate from OpenHands events**  
✅ **Use OpenHands callbacks to bridge: conversation events → system event bus**  
✅ **Store critical events in PostgreSQL for audit/replay**

---

### Tier 0 Question: Q4.1 - Task Queue Implementation

**What OpenHands Provides**:
- `TaskTrackerTool` for agent-internal task decomposition (conversation-scoped)
- GitHub Actions examples for external orchestration
- No built-in priority queue, task assignment, or retry logic

**What We Need But OpenHands Doesn't Provide**:
- ❌ Priority queue (CRITICAL > HIGH > MEDIUM > LOW)
- ❌ Task assignment to agents based on phase and availability
- ❌ Task dependencies and blocking relationships
- ❌ Retry logic with max attempts
- ❌ Task timeout handling
- ❌ Phase-based task routing
- ❌ Discovery-based task spawning

**Gap Analysis**:
- OpenHands provides **zero task queue infrastructure**
- We must build **entire task queue system** from scratch
- OpenHands agents are **invoked as workers** by our queue

**Decision for Smallest Runnable**:
✅ **Use PostgreSQL for task queue** (avoid Redis dependency; leverage ACID transactions)  
✅ **Task table with: id, ticket_id, phase_id, priority, status, assigned_agent_id, dependencies**  
✅ **Simple assignment algorithm: `SELECT * FROM tasks WHERE status='pending' AND phase_id=? ORDER BY priority DESC LIMIT 1`**  
✅ **Poll-based initially (no real-time push); optimize later**

---

### Tier 0 Question: Q2.3 - Agent-to-Conversation Mapping

**What OpenHands Provides**:
- `Conversation` object manages agent lifecycle
- `conversation_id` can be provided for resumption: `Conversation(conversation_id="session-001", persistence_dir="/path")`
- `ConversationState.create()` handles agent reconciliation on resume
- One conversation per agent instance is typical pattern

**What We Need to Decide**:
- 🤔 One conversation per **task**? (task finishes → conversation ends)
- 🤔 One conversation per **ticket**? (ticket spans multiple tasks/phases)
- 🤔 One conversation per **agent**? (agent reuses conversation for multiple tasks)

**Gap Analysis**:
- OpenHands doesn't prescribe mapping strategy
- Conversation lifecycle tied to `Conversation.run()` → `Conversation.close()`
- Context accumulates in conversation history (token costs increase)

**Decision for Smallest Runnable**:
✅ **One conversation per TASK** (1:1 mapping)  
✅ **Task.conversation_id stores the OpenHands conversation ID**  
✅ **Create new conversation per task: `Conversation(agent=agent, workspace=workspace)`**  
✅ **Link tasks to ticket via `Task.ticket_id` foreign key**  
✅ **Benefit: Clean isolation, predictable token costs, easier debugging**

---

## Part 2: The Absolute Foundation - Smallest Runnable System

Based on cross-reference analysis, here's the **minimum viable system** we need to build:

### Foundation Layer 1: Data Models & Storage

**PostgreSQL Schema (Minimal)**:
```sql
-- Ticket tracking
CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    phase_id VARCHAR(50) NOT NULL,  -- PHASE_REQUIREMENTS, PHASE_IMPLEMENTATION, etc.
    status VARCHAR(50) NOT NULL,     -- pending, in_progress, completed, failed
    priority VARCHAR(20) NOT NULL,   -- CRITICAL, HIGH, MEDIUM, LOW
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Task queue
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID REFERENCES tickets(id) ON DELETE CASCADE,
    phase_id VARCHAR(50) NOT NULL,
    task_type VARCHAR(100) NOT NULL,  -- analyze_requirements, implement_feature, etc.
    description TEXT,
    priority VARCHAR(20) NOT NULL,
    status VARCHAR(50) NOT NULL,      -- pending, assigned, running, completed, failed
    assigned_agent_id UUID,           -- NULL if unassigned
    conversation_id VARCHAR(255),     -- OpenHands conversation ID
    result JSONB,                     -- Task result/output
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Agent registry
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,  -- worker, monitor, watchdog, guardian
    phase_id VARCHAR(50),             -- For worker agents: which phase they handle
    status VARCHAR(50) NOT NULL,      -- idle, running, degraded, failed
    capabilities JSONB,               -- Tools, skills available to agent
    last_heartbeat TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- System events (orchestration-level)
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,  -- TASK_ASSIGNED, TASK_COMPLETED, etc.
    entity_type VARCHAR(50),           -- ticket, task, agent
    entity_id UUID,
    payload JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_tasks_status_priority ON tasks(status, priority DESC);
CREATE INDEX idx_tasks_ticket ON tasks(ticket_id);
CREATE INDEX idx_tasks_agent ON tasks(assigned_agent_id);
CREATE INDEX idx_agents_type_status ON agents(agent_type, status);
CREATE INDEX idx_events_type_timestamp ON events(event_type, timestamp DESC);
```

**Why This Schema**:
- Minimal tables: Only what's needed for task queue + agent registry
- No complex relationships yet (validation, memory, diagnosis)
- JSONB for flexibility (result, capabilities, payload)
- Indexes for critical queries only

---

### Foundation Layer 2: Core Services (Python)

**Service 1: Database Service** (`services/database.py`)
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

class DatabaseService:
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Session:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
```

**Service 2: Event Bus Service** (`services/event_bus.py`)
```python
import redis
import json
from typing import Callable, Dict, Any
from dataclasses import dataclass

@dataclass
class SystemEvent:
    event_type: str
    entity_type: str
    entity_id: str
    payload: Dict[str, Any]

class EventBusService:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url)
        self.pubsub = self.redis_client.pubsub()
    
    def publish(self, event: SystemEvent) -> None:
        """Publish event to system bus"""
        channel = f"events.{event.event_type}"
        message = json.dumps(event.__dict__)
        self.redis_client.publish(channel, message)
    
    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Subscribe to event type"""
        channel = f"events.{event_type}"
        self.pubsub.subscribe(**{channel: callback})
    
    def listen(self):
        """Start listening for events (blocking)"""
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                # Callbacks are invoked automatically
                pass
```

**Service 3: Task Queue Service** (`services/task_queue.py`)
```python
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from models import Task

class TaskQueueService:
    def __init__(self, db: DatabaseService):
        self.db = db
    
    def enqueue_task(self, ticket_id: UUID, phase_id: str, 
                     task_type: str, description: str, priority: str) -> Task:
        """Add task to queue"""
        with self.db.get_session() as session:
            task = Task(
                ticket_id=ticket_id,
                phase_id=phase_id,
                task_type=task_type,
                description=description,
                priority=priority,
                status='pending'
            )
            session.add(task)
            session.flush()
            return task
    
    def get_next_task(self, phase_id: str) -> Optional[Task]:
        """Get highest priority pending task for phase"""
        with self.db.get_session() as session:
            task = session.query(Task).filter(
                Task.status == 'pending',
                Task.phase_id == phase_id
            ).order_by(Task.priority.desc()).first()
            return task
    
    def assign_task(self, task_id: UUID, agent_id: UUID) -> None:
        """Assign task to agent"""
        with self.db.get_session() as session:
            task = session.query(Task).get(task_id)
            task.assigned_agent_id = agent_id
            task.status = 'assigned'
```

---

### Foundation Layer 3: Minimal Agent Wrapper

**Service 4: Agent Executor** (`services/agent_executor.py`)
```python
from openhands.sdk import Agent, LLM, Conversation
from openhands.tools.preset.default import get_default_agent
from typing import Dict, Any
import os

class AgentExecutor:
    """Wraps OpenHands Agent for task execution"""
    
    def __init__(self, phase_id: str, workspace_dir: str):
        self.phase_id = phase_id
        self.workspace_dir = workspace_dir
        
        # Create OpenHands LLM and Agent
        self.llm = LLM(
            model="openhands/claude-sonnet-4-5-20250929",
            api_key=os.getenv("LLM_API_KEY")
        )
        self.agent = get_default_agent(llm=self.llm, cli_mode=True)
    
    def execute_task(self, task_description: str) -> Dict[str, Any]:
        """Execute a task using OpenHands agent"""
        # Create conversation (one per task)
        conversation = Conversation(
            agent=self.agent,
            workspace=self.workspace_dir
        )
        
        # Send task message
        conversation.send_message(task_description)
        
        # Run agent
        conversation.run()
        
        # Extract result
        result = {
            'status': conversation.state.execution_status,
            'event_count': len(conversation.state.events),
            'cost': conversation.conversation_stats.get_combined_metrics().accumulated_cost
        }
        
        conversation.close()
        return result
```

---

## Part 3: Smallest Runnable Test Path

### Test 1: Database Setup & Models
```python
# tests/test_01_database.py
def test_database_connection():
    db = DatabaseService("postgresql://localhost/senior_sandbox_test")
    with db.get_session() as session:
        assert session is not None

def test_create_ticket():
    db = DatabaseService("postgresql://localhost/senior_sandbox_test")
    with db.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            phase_id="PHASE_REQUIREMENTS",
            status="pending",
            priority="HIGH"
        )
        session.add(ticket)
        session.flush()
        assert ticket.id is not None
```

### Test 2: Task Queue Operations
```python
# tests/test_02_task_queue.py
def test_enqueue_and_get_task():
    db = DatabaseService("postgresql://localhost/senior_sandbox_test")
    queue = TaskQueueService(db)
    
    # Create ticket
    with db.get_session() as session:
        ticket = Ticket(title="Test", phase_id="PHASE_IMPLEMENTATION", 
                       status="pending", priority="HIGH")
        session.add(ticket)
        session.flush()
        ticket_id = ticket.id
    
    # Enqueue task
    task = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="implement_feature",
        description="Build feature X",
        priority="HIGH"
    )
    
    # Get next task
    next_task = queue.get_next_task("PHASE_IMPLEMENTATION")
    assert next_task.id == task.id
```

### Test 3: Event Bus Pub/Sub
```python
# tests/test_03_event_bus.py
def test_event_publish_subscribe():
    bus = EventBusService("redis://localhost:6379")
    
    received_events = []
    def callback(message):
        event = json.loads(message['data'])
        received_events.append(event)
    
    # Subscribe
    bus.subscribe("TASK_ASSIGNED", callback)
    
    # Publish
    event = SystemEvent(
        event_type="TASK_ASSIGNED",
        entity_type="task",
        entity_id="123",
        payload={"agent_id": "456"}
    )
    bus.publish(event)
    
    # Wait and verify
    time.sleep(0.5)
    assert len(received_events) == 1
```

### Test 4: OpenHands Agent Execution
```python
# tests/test_04_agent_execution.py
def test_agent_executes_simple_task():
    executor = AgentExecutor(
        phase_id="PHASE_IMPLEMENTATION",
        workspace_dir="/tmp/test_workspace"
    )
    
    result = executor.execute_task("Create a file called test.txt with content 'Hello World'")
    
    assert result['status'] in ['finished', 'awaiting_user_input']
    assert result['event_count'] > 0
    assert os.path.exists("/tmp/test_workspace/test.txt")
```

### Test 5: End-to-End Minimal Flow
```python
# tests/test_05_e2e_minimal.py
def test_ticket_to_task_to_execution():
    # Setup services
    db = DatabaseService("postgresql://localhost/senior_sandbox_test")
    queue = TaskQueueService(db)
    bus = EventBusService("redis://localhost:6379")
    executor = AgentExecutor("PHASE_IMPLEMENTATION", "/tmp/test_workspace")
    
    # 1. Create ticket
    with db.get_session() as session:
        ticket = Ticket(
            title="Build Hello World Feature",
            phase_id="PHASE_IMPLEMENTATION",
            status="in_progress",
            priority="HIGH"
        )
        session.add(ticket)
        session.flush()
        ticket_id = ticket.id
    
    # 2. Enqueue task
    task = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="implement_feature",
        description="Create hello.py that prints 'Hello World'",
        priority="HIGH"
    )
    
    # 3. Assign task (simulate)
    agent_id = UUID("00000000-0000-0000-0000-000000000001")
    queue.assign_task(task.id, agent_id)
    
    # 4. Execute with OpenHands
    result = executor.execute_task(task.description)
    
    # 5. Update task status
    with db.get_session() as session:
        db_task = session.query(Task).get(task.id)
        db_task.status = 'completed'
        db_task.result = result
    
    # 6. Publish event
    bus.publish(SystemEvent(
        event_type="TASK_COMPLETED",
        entity_type="task",
        entity_id=str(task.id),
        payload=result
    ))
    
    # 7. Verify
    assert os.path.exists("/tmp/test_workspace/hello.py")
    with db.get_session() as session:
        completed_task = session.query(Task).get(task.id)
        assert completed_task.status == 'completed'
```

---

## Part 4: Implementation Order (Incremental, Testable)

### Phase 1: Foundation (Week 1)
1. **Day 1-2**: Database setup
   - Create PostgreSQL database
   - Define SQLAlchemy models (Ticket, Task, Agent, Event)
   - Write migrations (Alembic)
   - Test: `test_01_database.py`

2. **Day 3-4**: Task queue service
   - Implement `TaskQueueService`
   - Methods: `enqueue_task`, `get_next_task`, `assign_task`, `update_task_status`
   - Test: `test_02_task_queue.py`

3. **Day 5**: Event bus service
   - Setup Redis
   - Implement `EventBusService`
   - Test: `test_03_event_bus.py`

### Phase 2: OpenHands Integration (Week 2)
4. **Day 1-2**: Agent executor wrapper
   - Implement `AgentExecutor` wrapping OpenHands SDK
   - Handle conversation lifecycle (create, run, close)
   - Test: `test_04_agent_execution.py`

5. **Day 3**: Conversation persistence
   - Configure OpenHands `persistence_dir`
   - Link `Task.conversation_id` to OpenHands conversation
   - Test persistence and resumption

6. **Day 4-5**: End-to-end flow
   - Implement simple orchestrator: poll queue → assign task → execute → update
   - Test: `test_05_e2e_minimal.py`

### Phase 3: Worker Agent (Week 3)
7. **Day 1-2**: Worker agent service
   - Create `WorkerAgent` class composing `AgentExecutor`
   - Add heartbeat mechanism (simple timer → event bus)
   - Add status management (idle → running → idle)

8. **Day 3-4**: Phase-specific configuration
   - Configure tools per phase (FileEditor for implementation, ReadOnly for analysis)
   - Configure LLM per phase (different models/prompts)
   - Test phase-specific execution

9. **Day 5**: Agent registry
   - Implement agent registration on startup
   - Store agent capabilities in database
   - Test agent lifecycle (register → execute tasks → deregister)

### Phase 4: Basic Orchestration (Week 4)
10. **Day 1-2**: Orchestrator service
    - Poll task queue
    - Assign tasks to available agents
    - Monitor task execution
    - Handle task completion/failure

11. **Day 3-4**: Ticket workflow
    - Create ticket API (REST endpoint)
    - Ticket → Tasks decomposition
    - Phase transitions

12. **Day 5**: Integration testing
    - Full flow: Create ticket → Generate tasks → Execute → Complete
    - Performance testing (10 concurrent tasks)

### Phase 5: Monitoring (Week 5+)
13. Add Monitor agent
14. Add health metrics collection
15. Add alerting

---

## Part 5: Key Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **State Store** | PostgreSQL for orchestration | ACID transactions, complex queries, HA |
| **OpenHands Persistence** | File-based (default) | Keep it simple; link via conversation_id |
| **Event Bus** | Redis Pub/Sub | Simple, lightweight, no additional dependencies |
| **Task Queue** | PostgreSQL-based | Avoid Redis dependency; leverage existing DB |
| **Agent-Conversation Map** | 1 Conversation per Task | Clean isolation, predictable costs |
| **Deployment** | Embedded SDK (monolith) | Start simple; migrate to microservices later |
| **Workspace** | LocalWorkspace initially | Fast iteration; switch to Docker for security later |
| **Test Strategy** | Bottom-up incremental | Test each layer before moving up |

---

## Part 6: Success Criteria for Smallest Runnable

✅ **Definition of Done**:
1. PostgreSQL database with tickets, tasks, agents, events tables
2. Task queue service can enqueue, retrieve, assign tasks
3. Event bus can publish/subscribe to system events
4. Agent executor can run OpenHands agent on a task and return result
5. End-to-end test passes: ticket → task → execution → completion
6. All unit tests pass (50+ tests)
7. Integration test demonstrates full flow
8. Documentation for running the system locally

✅ **What We Can Do**:
- Create a ticket via API
- System decomposes ticket into tasks
- Tasks are queued with priority
- Worker agent picks up task
- OpenHands agent executes task in workspace
- Task result stored in database
- Events published to system bus

✅ **What We Can't Do Yet (Deferred)**:
- ❌ Multi-agent coordination
- ❌ Heartbeat monitoring
- ❌ Anomaly detection
- ❌ Phase gates
- ❌ Validation loops
- ❌ Discovery-based task spawning
- ❌ Guardian/Watchdog agents
- ❌ Memory system
- ❌ Diagnosis agent

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-16 | AI Assistant | Initial foundation analysis and smallest runnable code path |

