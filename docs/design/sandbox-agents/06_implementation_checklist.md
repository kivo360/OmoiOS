# Sandbox System Implementation Checklist

**Created**: 2025-12-12  
**Purpose**: Test-driven, iterative implementation plan with assumption validation at each step  
**Methodology**: Each phase starts with tests that define expected behavior, then implements to make tests pass

---

## Table of Contents

1. [Philosophy: Test-First Implementation](#philosophy-test-first-implementation)
2. [Phase 0: Validate Existing Infrastructure](#phase-0-validate-existing-infrastructure)
3. [Phase 1: Sandbox Event Callback](#phase-1-sandbox-event-callback)
4. [Phase 2: Message Injection](#phase-2-message-injection)
5. [Phase 3: Worker Script Updates](#phase-3-worker-script-updates)
6. [Phase 4: Database Persistence (Optional)](#phase-4-database-persistence-optional)
7. [Phase 5: Branch Workflow Service](#phase-5-branch-workflow-service)
8. [Integration Test Suite](#integration-test-suite)
9. [Assumption Validation Matrix](#assumption-validation-matrix)

---

## Philosophy: Test-First Implementation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TEST-DRIVEN IMPLEMENTATION FLOW                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  For EACH feature:                                                          │
│                                                                             │
│  1. WRITE THE TEST FIRST                                                    │
│     └─ Define expected behavior                                             │
│     └─ Test should FAIL initially                                           │
│                                                                             │
│  2. VERIFY ASSUMPTIONS                                                      │
│     └─ Run any dependency tests                                             │
│     └─ Confirm external services work                                       │
│                                                                             │
│  3. IMPLEMENT MINIMUM CODE                                                  │
│     └─ Just enough to make test pass                                        │
│     └─ No extra features                                                    │
│                                                                             │
│  4. RUN TEST - CONFIRM PASS                                                 │
│     └─ If fails, fix implementation                                         │
│     └─ Don't move on until green                                            │
│                                                                             │
│  5. INTEGRATION CHECK                                                       │
│     └─ Run full integration test suite                                      │
│     └─ Verify no regressions                                                │
│                                                                             │
│  BENEFITS:                                                                  │
│  ├─ Assumptions are validated BEFORE heavy implementation                   │
│  ├─ Each feature is provably working before moving on                       │
│  ├─ Regressions are caught immediately                                      │
│  └─ Documentation through tests                                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 0: Validate Existing Infrastructure

**Goal**: Confirm that existing WebSocket system works as documented before building on it.

### 0.1 WebSocket Event Flow Test

**Assumption to validate**: Events published via `EventBusService` reach WebSocket clients.

```python
# tests/integration/test_websocket_existing.py

import pytest
import asyncio
import json
from httpx import AsyncClient
from websockets import connect as ws_connect

from omoi_os.services.event_bus import EventBusService, SystemEvent


@pytest.mark.asyncio
async def test_event_bus_to_websocket_flow():
    """
    ASSUMPTION: Publishing to EventBusService results in WebSocket message.
    
    This test validates our core assumption that the existing infrastructure
    works as documented in the gap analysis.
    """
    received_events = []
    
    # 1. Connect WebSocket client with sandbox filter
    async with ws_connect("ws://localhost:18000/api/v1/events/ws/events?entity_types=sandbox") as ws:
        
        # 2. Publish event via EventBusService
        event_bus = EventBusService()
        event_bus.publish(SystemEvent(
            event_type="TEST_SANDBOX_EVENT",
            entity_type="sandbox",
            entity_id="test-sandbox-123",
            payload={"test": True, "timestamp": "2025-12-12"}
        ))
        
        # 3. Wait for WebSocket message (with timeout)
        try:
            message = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(message)
            
            # Skip ping messages
            while data.get("type") == "ping":
                message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(message)
            
            received_events.append(data)
        except asyncio.TimeoutError:
            pytest.fail("WebSocket did not receive event within 5 seconds")
    
    # 4. Verify event was received
    assert len(received_events) == 1
    assert received_events[0]["event_type"] == "TEST_SANDBOX_EVENT"
    assert received_events[0]["entity_type"] == "sandbox"
    assert received_events[0]["entity_id"] == "test-sandbox-123"
    assert received_events[0]["payload"]["test"] is True


@pytest.mark.asyncio  
async def test_websocket_filter_excludes_non_matching():
    """
    ASSUMPTION: WebSocket filters correctly exclude non-matching events.
    """
    received_events = []
    
    async with ws_connect("ws://localhost:18000/api/v1/events/ws/events?entity_types=sandbox") as ws:
        event_bus = EventBusService()
        
        # Publish non-sandbox event
        event_bus.publish(SystemEvent(
            event_type="TASK_COMPLETED",
            entity_type="task",  # Not sandbox!
            entity_id="task-456",
            payload={}
        ))
        
        # Should NOT receive this event
        try:
            message = await asyncio.wait_for(ws.recv(), timeout=2.0)
            data = json.loads(message)
            if data.get("type") != "ping":
                received_events.append(data)
        except asyncio.TimeoutError:
            pass  # Expected - no matching event
    
    # Should not have received the task event
    assert len(received_events) == 0
```

### 0.2 Redis Pub/Sub Test

**Assumption to validate**: Redis is accessible and pub/sub works.

```python
# tests/integration/test_redis_connectivity.py

import pytest
import redis


def test_redis_connection():
    """ASSUMPTION: Redis is available at redis://localhost:16379"""
    client = redis.from_url("redis://localhost:16379", decode_responses=True)
    assert client.ping() is True


def test_redis_pubsub_roundtrip():
    """ASSUMPTION: Redis pub/sub delivers messages correctly"""
    client = redis.from_url("redis://localhost:16379", decode_responses=True)
    pubsub = client.pubsub()
    
    pubsub.psubscribe("test.channel.*")
    
    # Need to process subscription message first
    pubsub.get_message()
    
    # Publish
    client.publish("test.channel.events", '{"test": true}')
    
    # Receive
    message = pubsub.get_message(timeout=2.0)
    assert message is not None
    assert message["type"] == "pmessage"
    assert message["data"] == '{"test": true}'
    
    pubsub.close()
```

### Checklist

| # | Test | Status | Notes |
|---|------|--------|-------|
| 0.1.1 | `test_event_bus_to_websocket_flow` | ⬜ | Core assumption |
| 0.1.2 | `test_websocket_filter_excludes_non_matching` | ⬜ | Filter correctness |
| 0.2.1 | `test_redis_connection` | ⬜ | Infrastructure |
| 0.2.2 | `test_redis_pubsub_roundtrip` | ⬜ | Infrastructure |

**Gate**: Do NOT proceed to Phase 1 until all Phase 0 tests pass. ✅

---

## Phase 1: Sandbox Event Callback

**Goal**: Workers can POST events that reach WebSocket clients.

**Estimated Effort**: 2-3 hours

### 1.1 Write Tests First

```python
# tests/integration/test_sandbox_events.py

import pytest
import asyncio
import json
from httpx import AsyncClient
from websockets import connect as ws_connect


@pytest.mark.asyncio
async def test_sandbox_event_endpoint_exists():
    """
    SPEC: POST /api/v1/sandboxes/{sandbox_id}/events should exist.
    """
    async with AsyncClient(base_url="http://localhost:18000") as client:
        response = await client.post(
            "/api/v1/sandboxes/test-123/events",
            json={
                "event_type": "agent.started",
                "event_data": {"task_id": "task-456"},
                "source": "agent"
            }
        )
        # Should not 404
        assert response.status_code != 404


@pytest.mark.asyncio
async def test_sandbox_event_broadcasts_to_websocket():
    """
    SPEC: POSTing to sandbox event endpoint should broadcast via WebSocket.
    
    This is the critical integration test - validates the full flow:
    Worker POST → Server → EventBus → Redis → WebSocketManager → Client
    """
    received_events = []
    sandbox_id = "test-sandbox-event-broadcast"
    
    # 1. Connect WebSocket, filtered to this sandbox
    async with ws_connect(
        f"ws://localhost:18000/api/v1/events/ws/events?entity_types=sandbox&entity_ids={sandbox_id}"
    ) as ws:
        
        # Give connection time to establish
        await asyncio.sleep(0.5)
        
        # 2. POST event via HTTP (simulating worker)
        async with AsyncClient(base_url="http://localhost:18000") as client:
            response = await client.post(
                f"/api/v1/sandboxes/{sandbox_id}/events",
                json={
                    "event_type": "agent.tool_use",
                    "event_data": {
                        "tool": "bash",
                        "command": "npm install",
                        "exit_code": 0
                    },
                    "source": "agent"
                }
            )
            assert response.status_code == 200
        
        # 3. Receive via WebSocket
        try:
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=3.0)
                data = json.loads(message)
                if data.get("type") != "ping":
                    received_events.append(data)
                    break
        except asyncio.TimeoutError:
            pytest.fail("Did not receive event via WebSocket")
    
    # 4. Verify
    assert len(received_events) == 1
    event = received_events[0]
    assert event["entity_type"] == "sandbox"
    assert event["entity_id"] == sandbox_id
    assert "tool_use" in event["event_type"].lower() or "tool" in str(event["payload"])


@pytest.mark.asyncio
async def test_sandbox_event_validates_input():
    """
    SPEC: Invalid event should return 422 validation error.
    """
    async with AsyncClient(base_url="http://localhost:18000") as client:
        # Missing required field
        response = await client.post(
            "/api/v1/sandboxes/test-123/events",
            json={
                "event_data": {}
                # Missing event_type!
            }
        )
        assert response.status_code == 422
```

### 1.2 Implementation

**File**: `backend/omoi_os/api/routes/sandboxes.py` (NEW)

```python
# See code example in 02_gap_analysis.md - Example 1
```

**File**: `backend/omoi_os/api/main.py` (MODIFY)

```python
# Add route registration
from omoi_os.api.routes import sandboxes
app.include_router(sandboxes.router, prefix="/api/v1/sandboxes", tags=["sandboxes"])
```

### 1.3 Checklist

| # | Task | Status | Test |
|---|------|--------|------|
| 1.1 | Write `test_sandbox_event_endpoint_exists` | ⬜ | — |
| 1.2 | Write `test_sandbox_event_broadcasts_to_websocket` | ⬜ | — |
| 1.3 | Write `test_sandbox_event_validates_input` | ⬜ | — |
| 1.4 | Run tests - confirm they FAIL | ⬜ | All should fail with 404 |
| 1.5 | Create `sandboxes.py` route file | ⬜ | — |
| 1.6 | Implement `SandboxEventCreate` schema | ⬜ | — |
| 1.7 | Implement `POST /{sandbox_id}/events` endpoint | ⬜ | — |
| 1.8 | Register route in `main.py` | ⬜ | — |
| 1.9 | Run tests - confirm they PASS | ⬜ | ✅ All green |
| 1.10 | Run Phase 0 tests - confirm no regression | ⬜ | ✅ All green |

**Gate**: All Phase 1 tests must pass before Phase 2. ✅

---

## Phase 2: Message Injection

**Goal**: Users/Guardian can send messages to running agents.

**Estimated Effort**: 4-6 hours

### 2.1 Write Tests First

```python
# tests/integration/test_sandbox_messages.py

import pytest
import asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_message_queue_roundtrip():
    """
    SPEC: POST message → GET messages returns it.
    
    This validates the message queue mechanism independent of workers.
    """
    sandbox_id = "test-message-queue"
    
    async with AsyncClient(base_url="http://localhost:18000") as client:
        # 1. Queue a message
        response = await client.post(
            f"/api/v1/sandboxes/{sandbox_id}/messages",
            json={
                "content": "Please focus on the authentication module first.",
                "message_type": "user_message"
            }
        )
        assert response.status_code == 200
        assert response.json()["status"] == "queued"
        
        # 2. Retrieve message
        response = await client.get(f"/api/v1/sandboxes/{sandbox_id}/messages")
        assert response.status_code == 200
        messages = response.json()
        
        assert len(messages) == 1
        assert messages[0]["content"] == "Please focus on the authentication module first."
        assert messages[0]["message_type"] == "user_message"
        
        # 3. Messages should be cleared after retrieval
        response = await client.get(f"/api/v1/sandboxes/{sandbox_id}/messages")
        assert response.json() == []


@pytest.mark.asyncio
async def test_message_queue_fifo_order():
    """
    SPEC: Messages should be returned in FIFO order.
    """
    sandbox_id = "test-message-fifo"
    
    async with AsyncClient(base_url="http://localhost:18000") as client:
        # Queue multiple messages
        for i in range(3):
            await client.post(
                f"/api/v1/sandboxes/{sandbox_id}/messages",
                json={"content": f"Message {i}", "message_type": "user_message"}
            )
        
        # Retrieve and verify order
        response = await client.get(f"/api/v1/sandboxes/{sandbox_id}/messages")
        messages = response.json()
        
        assert len(messages) == 3
        assert messages[0]["content"] == "Message 0"
        assert messages[1]["content"] == "Message 1"
        assert messages[2]["content"] == "Message 2"


@pytest.mark.asyncio
async def test_interrupt_message_type():
    """
    SPEC: "interrupt" message type should be supported.
    """
    sandbox_id = "test-interrupt"
    
    async with AsyncClient(base_url="http://localhost:18000") as client:
        response = await client.post(
            f"/api/v1/sandboxes/{sandbox_id}/messages",
            json={"content": "STOP", "message_type": "interrupt"}
        )
        assert response.status_code == 200
        
        messages = (await client.get(f"/api/v1/sandboxes/{sandbox_id}/messages")).json()
        assert messages[0]["message_type"] == "interrupt"


@pytest.mark.asyncio
async def test_message_queued_event_broadcast():
    """
    SPEC: Queueing a message should broadcast a WebSocket event.
    
    This allows the frontend to show "message sent" feedback immediately.
    """
    import json
    from websockets import connect as ws_connect
    
    sandbox_id = "test-message-event"
    received_events = []
    
    async with ws_connect(
        f"ws://localhost:18000/api/v1/events/ws/events?entity_types=sandbox&entity_ids={sandbox_id}"
    ) as ws:
        await asyncio.sleep(0.3)
        
        async with AsyncClient(base_url="http://localhost:18000") as client:
            await client.post(
                f"/api/v1/sandboxes/{sandbox_id}/messages",
                json={"content": "Test", "message_type": "user_message"}
            )
        
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                data = json.loads(msg)
                if data.get("type") != "ping":
                    received_events.append(data)
                    break
        except asyncio.TimeoutError:
            pytest.fail("No WebSocket event for queued message")
    
    assert len(received_events) == 1
    assert "MESSAGE_QUEUED" in received_events[0]["event_type"]
```

### 2.2 Implementation

**File**: `backend/omoi_os/api/routes/sandboxes.py` (EXTEND)

```python
# See code example in 02_gap_analysis.md - Example 2
```

### 2.3 Checklist

| # | Task | Status | Test |
|---|------|--------|------|
| 2.1 | Write `test_message_queue_roundtrip` | ⬜ | — |
| 2.2 | Write `test_message_queue_fifo_order` | ⬜ | — |
| 2.3 | Write `test_interrupt_message_type` | ⬜ | — |
| 2.4 | Write `test_message_queued_event_broadcast` | ⬜ | — |
| 2.5 | Run tests - confirm FAIL (404) | ⬜ | — |
| 2.6 | Implement `SandboxMessage` schema | ⬜ | — |
| 2.7 | Implement `POST /{sandbox_id}/messages` | ⬜ | — |
| 2.8 | Implement `GET /{sandbox_id}/messages` | ⬜ | — |
| 2.9 | Add message queue storage (in-memory or Redis) | ⬜ | — |
| 2.10 | Run tests - confirm PASS | ⬜ | ✅ All green |
| 2.11 | Run Phase 0+1 tests - confirm no regression | ⬜ | ✅ All green |

**Gate**: All Phase 2 tests must pass before Phase 3. ✅

---

## Phase 3: Worker Script Updates

**Goal**: Worker scripts use new endpoints and poll for messages.

**Estimated Effort**: 4 hours

### 3.1 Write Tests First

```python
# tests/integration/test_worker_integration.py

import pytest
import asyncio
from unittest.mock import patch, MagicMock


class MockSandbox:
    """Mock Daytona sandbox for testing worker script behavior."""
    
    def __init__(self):
        self.executed_commands = []
        self.uploaded_files = {}
        
    class process:
        @classmethod
        def exec(cls, cmd, **kwargs):
            MockSandbox._instance.executed_commands.append(cmd)
            return MagicMock(returncode=0)
    
    class fs:
        @classmethod
        def upload_file(cls, content, path):
            MockSandbox._instance.uploaded_files[path] = content


def test_worker_script_reports_to_sandbox_endpoint():
    """
    SPEC: Worker script should POST events to /api/v1/sandboxes/{id}/events
    (not the old /tasks/{id}/events endpoint).
    """
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService
    
    spawner = DaytonaSpawnerService()
    script = spawner._get_worker_script()
    
    # Verify script POSTs to correct endpoint
    assert "/api/v1/sandboxes/" in script or "sandboxes/{" in script.lower()
    assert "/events" in script


def test_worker_script_polls_for_messages():
    """
    SPEC: Worker script should poll GET /api/v1/sandboxes/{id}/messages.
    """
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService
    
    spawner = DaytonaSpawnerService()
    script = spawner._get_worker_script()
    
    # Verify script has message polling
    assert "messages" in script.lower()
    assert ("poll" in script.lower() or "get" in script.lower())


def test_worker_script_handles_interrupt():
    """
    SPEC: Worker script should handle "interrupt" message type.
    """
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService
    
    spawner = DaytonaSpawnerService()
    script = spawner._get_worker_script()
    
    assert "interrupt" in script.lower()


@pytest.mark.asyncio
async def test_end_to_end_worker_event_flow():
    """
    INTEGRATION: Simulate worker posting event, verify WebSocket receives it.
    
    This simulates what happens when a real worker runs in Daytona.
    """
    import json
    from httpx import AsyncClient
    from websockets import connect as ws_connect
    
    sandbox_id = "e2e-worker-test"
    received = []
    
    async with ws_connect(
        f"ws://localhost:18000/api/v1/events/ws/events?entity_types=sandbox&entity_ids={sandbox_id}"
    ) as ws:
        await asyncio.sleep(0.3)
        
        # Simulate worker posting event (like real worker would)
        async with AsyncClient(base_url="http://localhost:18000") as client:
            await client.post(
                f"/api/v1/sandboxes/{sandbox_id}/events",
                json={
                    "event_type": "agent.tool_use",
                    "event_data": {
                        "tool": "write_file",
                        "path": "/workspace/src/main.py",
                        "success": True
                    },
                    "source": "agent"
                }
            )
        
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                data = json.loads(msg)
                if data.get("type") != "ping":
                    received.append(data)
                    break
        except asyncio.TimeoutError:
            pytest.fail("Worker event not received")
    
    assert len(received) == 1
    assert received[0]["entity_id"] == sandbox_id
```

### 3.2 Implementation

**File**: `backend/omoi_os/services/daytona_spawner.py` (MODIFY)

Update `_get_worker_script()` and `_get_claude_worker_script()` to:
- POST events to `/api/v1/sandboxes/{SANDBOX_ID}/events`
- Poll `GET /api/v1/sandboxes/{SANDBOX_ID}/messages` after each agent turn
- Handle "interrupt" message type

### 3.3 Checklist

| # | Task | Status | Test |
|---|------|--------|------|
| 3.1 | Write `test_worker_script_reports_to_sandbox_endpoint` | ⬜ | — |
| 3.2 | Write `test_worker_script_polls_for_messages` | ⬜ | — |
| 3.3 | Write `test_worker_script_handles_interrupt` | ⬜ | — |
| 3.4 | Write `test_end_to_end_worker_event_flow` | ⬜ | — |
| 3.5 | Run tests - verify they FAIL | ⬜ | — |
| 3.6 | Update OpenHands worker script | ⬜ | — |
| 3.7 | Update Claude worker script | ⬜ | — |
| 3.8 | Add `report_event()` helper function | ⬜ | — |
| 3.9 | Add `poll_for_messages()` helper function | ⬜ | — |
| 3.10 | Add interrupt handling logic | ⬜ | — |
| 3.11 | Run tests - confirm PASS | ⬜ | ✅ All green |
| 3.12 | Run Phase 0+1+2 tests - confirm no regression | ⬜ | ✅ All green |

**Gate**: All Phase 3 tests must pass. ✅ MVP COMPLETE at this point!

---

## Phase 4: Database Persistence (Optional)

**Goal**: Persist sandbox sessions and events for audit trail and restart recovery.

**Estimated Effort**: 4-6 hours

### 4.1 Write Tests First

```python
# tests/integration/test_sandbox_persistence.py

import pytest
from omoi_os.services.database import DatabaseService


def test_sandbox_session_persists():
    """
    SPEC: SandboxSession should persist across server restarts.
    """
    from omoi_os.models.sandbox import SandboxSession
    
    db = DatabaseService()
    
    with db.get_session() as session:
        # Create
        sandbox = SandboxSession(
            sandbox_id="persist-test-123",
            task_id="task-456",
            agent_id="agent-789",
            status="running"
        )
        session.add(sandbox)
        session.commit()
        
        sandbox_id = sandbox.id
    
    # Retrieve in new session (simulates restart)
    with db.get_session() as session:
        sandbox = session.query(SandboxSession).filter_by(sandbox_id="persist-test-123").first()
        assert sandbox is not None
        assert sandbox.status == "running"


def test_sandbox_events_persisted():
    """
    SPEC: Events should be queryable from database.
    """
    from omoi_os.models.sandbox import SandboxEvent
    
    db = DatabaseService()
    
    with db.get_session() as session:
        event = SandboxEvent(
            sandbox_id="event-persist-test",
            event_type="agent.tool_use",
            event_data={"tool": "bash"},
            source="agent"
        )
        session.add(event)
        session.commit()
    
    with db.get_session() as session:
        events = session.query(SandboxEvent).filter_by(sandbox_id="event-persist-test").all()
        assert len(events) == 1
        assert events[0].event_type == "agent.tool_use"
```

### 4.2 Checklist

| # | Task | Status |
|---|------|--------|
| 4.1 | Write persistence tests | ⬜ |
| 4.2 | Create `SandboxSession` model | ⬜ |
| 4.3 | Create `SandboxEvent` model | ⬜ |
| 4.4 | Create Alembic migration | ⬜ |
| 4.5 | Run migration | ⬜ |
| 4.6 | Update `DaytonaSpawnerService` to persist | ⬜ |
| 4.7 | Update event endpoint to persist | ⬜ |
| 4.8 | Run tests - confirm PASS | ⬜ |
| 4.9 | Run full test suite - confirm no regression | ⬜ |

---

## Phase 5: Branch Workflow Service

**Goal**: Full Git branch lifecycle management.

**Estimated Effort**: 10-15 hours

### 5.1 Write Tests First

```python
# tests/integration/test_branch_workflow.py

import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_start_work_creates_branch():
    """
    SPEC: start_work_on_ticket should create a new branch.
    """
    from omoi_os.services.branch_workflow import BranchWorkflowService
    
    mock_github = MagicMock()
    mock_github.create_branch.return_value = {"success": True, "ref": "refs/heads/feature/123-add-auth"}
    
    service = BranchWorkflowService(github_service=mock_github)
    
    result = await service.start_work_on_ticket(
        ticket_id="123",
        ticket_title="Add authentication",
        repo_owner="myorg",
        repo_name="myapp"
    )
    
    assert result["success"] is True
    assert "feature/" in result["branch_name"]
    mock_github.create_branch.assert_called_once()


@pytest.mark.asyncio
async def test_finish_work_creates_pr():
    """
    SPEC: finish_work_on_ticket should create a pull request.
    """
    from omoi_os.services.branch_workflow import BranchWorkflowService
    
    mock_github = MagicMock()
    mock_github.create_pull_request.return_value = {
        "success": True,
        "number": 42,
        "html_url": "https://github.com/myorg/myapp/pull/42"
    }
    
    service = BranchWorkflowService(github_service=mock_github)
    
    result = await service.finish_work_on_ticket(
        ticket_id="123",
        branch_name="feature/123-add-auth"
    )
    
    assert result["success"] is True
    assert result["pr_number"] == 42


@pytest.mark.asyncio
async def test_merge_work_completes_pr():
    """
    SPEC: merge_ticket_work should merge PR and cleanup branch.
    """
    from omoi_os.services.branch_workflow import BranchWorkflowService
    
    mock_github = MagicMock()
    mock_github.merge_pull_request.return_value = {"success": True, "sha": "abc123"}
    mock_github.delete_branch.return_value = {"success": True}
    
    service = BranchWorkflowService(github_service=mock_github)
    
    result = await service.merge_ticket_work(
        ticket_id="123",
        pr_number=42
    )
    
    assert result["success"] is True
    mock_github.merge_pull_request.assert_called_once()
    mock_github.delete_branch.assert_called_once()
```

### 5.2 Checklist

| # | Task | Status |
|---|------|--------|
| 5.1 | Write branch workflow tests | ⬜ |
| 5.2 | Add `merge_pull_request` to GitHubAPIService | ⬜ |
| 5.3 | Add `delete_branch` to GitHubAPIService | ⬜ |
| 5.4 | Add `compare_branches` to GitHubAPIService | ⬜ |
| 5.5 | Create `BranchWorkflowService` | ⬜ |
| 5.6 | Implement `start_work_on_ticket` | ⬜ |
| 5.7 | Implement `finish_work_on_ticket` | ⬜ |
| 5.8 | Implement `merge_ticket_work` | ⬜ |
| 5.9 | Add AI branch naming | ⬜ |
| 5.10 | Run tests - confirm PASS | ⬜ |

---

## Integration Test Suite

Run this after each phase to ensure no regressions:

```bash
# Full integration test suite
pytest tests/integration/ -v --tb=short

# By phase
pytest tests/integration/test_websocket_existing.py -v  # Phase 0
pytest tests/integration/test_sandbox_events.py -v       # Phase 1
pytest tests/integration/test_sandbox_messages.py -v     # Phase 2
pytest tests/integration/test_worker_integration.py -v   # Phase 3
```

---

## Assumption Validation Matrix

Track which assumptions have been validated:

| Assumption | Test | Validated | Notes |
|------------|------|-----------|-------|
| Redis available at :16379 | `test_redis_connection` | ⬜ | Phase 0 |
| Redis pub/sub works | `test_redis_pubsub_roundtrip` | ⬜ | Phase 0 |
| EventBus → WebSocket flow works | `test_event_bus_to_websocket_flow` | ⬜ | Phase 0 |
| WebSocket filters work correctly | `test_websocket_filter_excludes_non_matching` | ⬜ | Phase 0 |
| Event callback broadcasts | `test_sandbox_event_broadcasts_to_websocket` | ⬜ | Phase 1 |
| Message queue FIFO order | `test_message_queue_fifo_order` | ⬜ | Phase 2 |
| Worker can POST events | `test_end_to_end_worker_event_flow` | ⬜ | Phase 3 |
| Worker polls messages | `test_worker_script_polls_for_messages` | ⬜ | Phase 3 |
| Sandbox session persists | `test_sandbox_session_persists` | ⬜ | Phase 4 |
| Branch creation works | `test_start_work_creates_branch` | ⬜ | Phase 5 |
| PR creation works | `test_finish_work_creates_pr` | ⬜ | Phase 5 |

---

## Phase 6: Guardian & Existing Systems Integration

**Goal**: Enable the IntelligentGuardian to monitor and intervene with sandbox agents.

**Estimated Effort**: 6-8 hours

### 6.1 Background: Why This Phase is Critical

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GUARDIAN INTEGRATION PROBLEM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CURRENT STATE (Legacy Agents):                                             │
│  ─────────────────────────────────────────────────────────────              │
│  IntelligentGuardian.execute_steering_intervention()                        │
│       │                                                                     │
│       └─► ConversationInterventionService.send_intervention()               │
│                │                                                            │
│                └─► Conversation(                                            │
│                        persistence_dir=task.persistence_dir  ← LOCAL PATH! │
│                    ).send_message(intervention)                             │
│                                                                             │
│  PROBLEM: Sandbox agents have state INSIDE Daytona, not local filesystem!  │
│                                                                             │
│  SANDBOX AGENTS:                                                            │
│  ─────────────────────────────────────────────────────────────              │
│  - Task has sandbox_id (which we need to ADD to the model)                 │
│  - Conversation state is in /tmp/openhands INSIDE the sandbox              │
│  - Local persistence_dir doesn't exist or is empty                         │
│  - Guardian CANNOT inject messages using current mechanism                  │
│                                                                             │
│  SOLUTION: Route Guardian interventions through message injection API       │
│                                                                             │
│  IntelligentGuardian.execute_steering_intervention()                        │
│       │                                                                     │
│       ├─► IF task.sandbox_id EXISTS:                                        │
│       │       POST /api/v1/sandboxes/{sandbox_id}/messages                 │
│       │       { message_type: "guardian_intervention", content: ... }      │
│       │                                                                     │
│       └─► ELSE (legacy agent):                                              │
│               ConversationInterventionService.send_intervention()           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Write Tests First

```python
# tests/integration/test_guardian_sandbox_integration.py

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


def test_task_model_has_sandbox_id():
    """
    SPEC: Task model should have sandbox_id field.
    
    This was identified as a bug - the register_conversation endpoint
    tries to set task.sandbox_id but the field doesn't exist!
    """
    from omoi_os.models.task import Task
    
    task = Task(
        ticket_id="ticket-123",
        phase_id="PHASE_IMPLEMENTATION",
        description="Test task",
    )
    
    # This should not raise an error
    task.sandbox_id = "sandbox-xyz-123"
    assert task.sandbox_id == "sandbox-xyz-123"


@pytest.mark.asyncio
async def test_guardian_detects_sandbox_mode():
    """
    SPEC: Guardian should detect when a task is in sandbox mode.
    """
    from omoi_os.services.intelligent_guardian import IntelligentGuardian
    from omoi_os.models.task import Task
    
    guardian = IntelligentGuardian()
    
    # Legacy task (no sandbox_id)
    legacy_task = Task(
        id="task-legacy",
        conversation_id="conv-123",
        persistence_dir="/tmp/openhands/conv-123",
    )
    assert guardian._is_sandbox_task(legacy_task) is False
    
    # Sandbox task (has sandbox_id)
    sandbox_task = Task(
        id="task-sandbox",
        sandbox_id="sandbox-xyz",
        conversation_id="conv-456",
    )
    assert guardian._is_sandbox_task(sandbox_task) is True


@pytest.mark.asyncio
async def test_guardian_intervention_uses_message_injection_for_sandbox():
    """
    SPEC: Guardian should POST to message injection endpoint for sandbox agents.
    """
    from omoi_os.services.intelligent_guardian import IntelligentGuardian
    from omoi_os.models.task import Task
    
    guardian = IntelligentGuardian()
    
    sandbox_task = Task(
        id="task-123",
        sandbox_id="sandbox-xyz",
        agent_id="agent-456",
    )
    
    intervention = MagicMock()
    intervention.message = "Please focus on the authentication module."
    intervention.agent_id = "agent-456"
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        
        success = await guardian.execute_steering_intervention(
            intervention=intervention,
            task=sandbox_task,
        )
        
        # Should have called the message injection endpoint
        mock_client.return_value.__aenter__.return_value.post.assert_called_once()
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        assert "sandboxes/sandbox-xyz/messages" in call_args[0][0]
        assert call_args[1]["json"]["message_type"] == "guardian_intervention"


@pytest.mark.asyncio
async def test_guardian_intervention_uses_legacy_for_non_sandbox():
    """
    SPEC: Guardian should use ConversationInterventionService for legacy agents.
    """
    from omoi_os.services.intelligent_guardian import IntelligentGuardian
    from omoi_os.models.task import Task
    
    guardian = IntelligentGuardian()
    
    legacy_task = Task(
        id="task-123",
        conversation_id="conv-456",
        persistence_dir="/tmp/openhands/conv-456",
        agent_id="agent-789",
    )
    
    intervention = MagicMock()
    intervention.message = "Please focus on the authentication module."
    intervention.agent_id = "agent-789"
    
    with patch.object(guardian, '_legacy_intervention') as mock_legacy:
        mock_legacy.return_value = True
        
        success = await guardian.execute_steering_intervention(
            intervention=intervention,
            task=legacy_task,
        )
        
        mock_legacy.assert_called_once()


@pytest.mark.asyncio
async def test_end_to_end_guardian_to_sandbox_message():
    """
    INTEGRATION: Full flow - Guardian intervention reaches sandbox message queue.
    
    This tests the complete path:
    1. Guardian detects intervention needed
    2. Guardian POSTs to /sandboxes/{id}/messages
    3. Worker polls and receives intervention
    """
    from httpx import AsyncClient
    
    sandbox_id = "guardian-test-sandbox"
    
    async with AsyncClient(base_url="http://localhost:18000") as client:
        # 1. Queue a guardian intervention
        response = await client.post(
            f"/api/v1/sandboxes/{sandbox_id}/messages",
            json={
                "content": "Guardian intervention: Please verify the test results.",
                "message_type": "guardian_intervention"
            }
        )
        assert response.status_code == 200
        
        # 2. Worker polls for messages
        response = await client.get(f"/api/v1/sandboxes/{sandbox_id}/messages")
        messages = response.json()
        
        # 3. Should receive the intervention
        assert len(messages) == 1
        assert messages[0]["message_type"] == "guardian_intervention"
        assert "Guardian intervention" in messages[0]["content"]
```

### 6.3 Implementation: Add sandbox_id to Task Model

**File**: `backend/omoi_os/models/task.py` (MODIFY)

```python
# Add this field to the Task model class
sandbox_id: Mapped[Optional[str]] = mapped_column(
    String(255), 
    nullable=True,
    index=True,
    comment="Daytona sandbox ID if task is running in sandbox mode"
)
```

**Migration**: Create Alembic migration

```bash
alembic revision --autogenerate -m "add_sandbox_id_to_task"
alembic upgrade head
```

### 6.4 Implementation: Update IntelligentGuardian

**File**: `backend/omoi_os/services/intelligent_guardian.py` (MODIFY)

```python
# Add these methods to IntelligentGuardian class

def _is_sandbox_task(self, task: Task) -> bool:
    """Determine if task is running in sandbox mode."""
    return bool(task.sandbox_id)


async def _sandbox_intervention(
    self,
    sandbox_id: str,
    message: str,
) -> bool:
    """Send intervention to sandbox via message injection API."""
    import httpx
    from omoi_os.config import get_app_settings
    
    settings = get_app_settings()
    base_url = settings.server.base_url or "http://localhost:18000"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/v1/sandboxes/{sandbox_id}/messages",
                json={
                    "content": message,
                    "message_type": "guardian_intervention",
                },
                timeout=10.0,
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to send sandbox intervention: {e}")
        return False


async def _legacy_intervention(
    self,
    task: Task,
    message: str,
    workspace_dir: str,
) -> bool:
    """Send intervention using legacy ConversationInterventionService."""
    intervention_service = ConversationInterventionService()
    return intervention_service.send_intervention(
        conversation_id=task.conversation_id,
        persistence_dir=task.persistence_dir,
        workspace_dir=workspace_dir,
        message=message,
    )


# Update execute_steering_intervention to use the appropriate method
async def execute_steering_intervention(
    self,
    intervention: SteeringIntervention,
    task: Optional[Task] = None,
) -> bool:
    """
    Execute steering intervention - routes to sandbox or legacy path.
    """
    if not task:
        # Try to look up task by agent_id
        task = self._get_task_for_agent(intervention.agent_id)
    
    if not task:
        logger.warning(f"No task found for agent {intervention.agent_id}")
        return False
    
    # Route to appropriate intervention mechanism
    if self._is_sandbox_task(task):
        # Sandbox mode - use message injection
        return await self._sandbox_intervention(
            sandbox_id=task.sandbox_id,
            message=intervention.message,
        )
    else:
        # Legacy mode - use local filesystem
        if not task.conversation_id or not task.persistence_dir:
            logger.warning(f"Task {task.id} missing conversation info for legacy intervention")
            return False
        
        workspace_dir = f"/workspace/{task.ticket_id}"
        return await self._legacy_intervention(
            task=task,
            message=intervention.message,
            workspace_dir=workspace_dir,
        )
```

### 6.5 Implementation: Update Worker Script to Handle Guardian Messages

Worker script should check for `message_type == "guardian_intervention"` and handle appropriately:

```python
# In worker script message handling

def handle_message(msg: dict):
    """Handle incoming message from message queue."""
    if msg["message_type"] == "guardian_intervention":
        # Guardian interventions are high-priority steering messages
        logger.info(f"Guardian intervention: {msg['content']}")
        agent.inject_system_message(
            f"[GUARDIAN INTERVENTION] {msg['content']}"
        )
    elif msg["message_type"] == "user_message":
        # Regular user message
        agent.inject_message(msg["content"])
    elif msg["message_type"] == "interrupt":
        agent.stop()
```

### 6.6 Checklist

| # | Task | Status | Test |
|---|------|--------|------|
| 6.1 | Write `test_task_model_has_sandbox_id` | ⬜ | — |
| 6.2 | Write `test_guardian_detects_sandbox_mode` | ⬜ | — |
| 6.3 | Write `test_guardian_intervention_uses_message_injection_for_sandbox` | ⬜ | — |
| 6.4 | Write `test_guardian_intervention_uses_legacy_for_non_sandbox` | ⬜ | — |
| 6.5 | Write `test_end_to_end_guardian_to_sandbox_message` | ⬜ | — |
| 6.6 | Run tests - verify FAIL | ⬜ | All should fail |
| 6.7 | Add `sandbox_id` field to Task model | ⬜ | — |
| 6.8 | Create and run Alembic migration | ⬜ | — |
| 6.9 | Add `_is_sandbox_task()` method to Guardian | ⬜ | — |
| 6.10 | Add `_sandbox_intervention()` method | ⬜ | — |
| 6.11 | Add `_legacy_intervention()` method | ⬜ | — |
| 6.12 | Update `execute_steering_intervention()` | ⬜ | — |
| 6.13 | Update worker script message handling | ⬜ | — |
| 6.14 | Run tests - confirm PASS | ⬜ | ✅ All green |
| 6.15 | Run Phase 0-5 tests - confirm no regression | ⬜ | ✅ All green |

**Gate**: All Phase 6 tests must pass. Guardian integration complete! ✅

---

## Phase 7: Fault Tolerance Integration (Full Integration Track)

**Goal**: Connect sandbox agents to the existing fault tolerance system for production-grade resilience.

**Estimated Effort**: 8-12 hours

**Prerequisites**: Phases 0-6 complete (especially Phase 4 for DB persistence)

### 7.1 Background: Why This Phase

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              FAULT TOLERANCE INTEGRATION OVERVIEW                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  EXISTING FAULT TOLERANCE SYSTEM (from docs/design/monitoring/):           │
│  ────────────────────────────────────────────────────────────────          │
│  • Heartbeat Detection: Agents send heartbeats every 15-30s               │
│  • Escalation Ladder: 1 miss → warn, 2 → DEGRADED, 3 → restart           │
│  • Restart Orchestrator: Graceful stop → Force terminate → Spawn new      │
│  • Anomaly Detection: Baseline learning, composite scoring                │
│  • Quarantine: Isolation, forensics collection, clearance                 │
│                                                                             │
│  PROBLEM: None of this knows about Daytona sandboxes!                      │
│                                                                             │
│  MVP WORKAROUND (Phases 0-3):                                              │
│  • Task timeout instead of heartbeats                                      │
│  • Simple restart: terminate sandbox + spawn new                           │
│  • No escalation ladder                                                    │
│                                                                             │
│  FULL INTEGRATION (This Phase):                                            │
│  • Workers send heartbeats via event callback                             │
│  • RestartOrchestrator calls DaytonaSpawnerService                        │
│  • Trajectory context pulls from event store (not local FS)               │
│  • Forensics can pull logs from sandbox before termination                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Write Tests First

```python
# tests/integration/test_sandbox_fault_tolerance.py

import pytest
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_sandbox_worker_sends_heartbeats():
    """
    SPEC: Sandbox workers should POST heartbeat events every 15 seconds.
    """
    from httpx import AsyncClient
    
    sandbox_id = "heartbeat-test-sandbox"
    
    async with AsyncClient(base_url="http://localhost:18000") as client:
        # Worker sends heartbeat
        response = await client.post(
            f"/api/v1/sandboxes/{sandbox_id}/events",
            json={
                "event_type": "heartbeat",
                "event_data": {
                    "status": "running",
                    "timestamp": datetime.utcnow().isoformat(),
                    "current_action": "processing_task"
                }
            }
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_heartbeat_analyzer_detects_sandbox_miss():
    """
    SPEC: HeartbeatAnalyzer should detect missed sandbox heartbeats.
    """
    from omoi_os.services.fault_tolerance import HeartbeatAnalyzer
    from omoi_os.models.task import Task
    
    analyzer = HeartbeatAnalyzer()
    
    # Create task with sandbox_id
    task = Task(
        id="task-123",
        sandbox_id="sandbox-xyz",
        status="in_progress",
    )
    
    # Simulate missed heartbeat (last heartbeat > TTL)
    task.last_heartbeat = datetime.utcnow() - timedelta(seconds=30)
    
    missed = await analyzer.check_sandbox_ttl(task)
    assert missed is True


@pytest.mark.asyncio
async def test_restart_orchestrator_handles_sandbox():
    """
    SPEC: RestartOrchestrator should use DaytonaSpawner for sandbox agents.
    """
    from unittest.mock import AsyncMock, patch
    from omoi_os.services.fault_tolerance import RestartOrchestrator
    from omoi_os.models.task import Task
    
    orchestrator = RestartOrchestrator()
    
    task = Task(
        id="task-123",
        sandbox_id="sandbox-xyz",
        phase_id="PHASE_IMPLEMENTATION",
    )
    
    with patch.object(orchestrator, 'daytona_spawner') as mock_spawner:
        mock_spawner.terminate_sandbox = AsyncMock()
        mock_spawner.spawn_for_task = AsyncMock(return_value="new-sandbox-abc")
        
        await orchestrator.initiate_restart(
            agent_id="agent-456",
            reason="missed_heartbeats",
            task=task,
        )
        
        # Should have terminated old sandbox
        mock_spawner.terminate_sandbox.assert_called_once_with("sandbox-xyz")
        
        # Should have spawned new sandbox
        mock_spawner.spawn_for_task.assert_called_once()


@pytest.mark.asyncio
async def test_trajectory_context_from_event_store():
    """
    SPEC: TrajectoryContextBuilder should get sandbox logs from event store.
    """
    from omoi_os.services.monitoring_loop import TrajectoryContextBuilder
    from omoi_os.models.task import Task
    
    builder = TrajectoryContextBuilder()
    
    task = Task(
        id="task-123",
        sandbox_id="sandbox-xyz",
    )
    
    # First, populate some events
    # (In real test, POST events via API)
    
    context = await builder.build_for_sandbox(task.sandbox_id)
    
    assert context.logs_snippet is not None
    assert context.agent_id is not None
```

### 7.3 Implementation: Heartbeat in Worker Script

**File**: `backend/omoi_os/services/daytona_spawner.py` (MODIFY worker script)

```python
# Add to worker script (_get_worker_script)

import threading
import time

def heartbeat_loop():
    \"\"\"Send heartbeat every 15 seconds.\"\"\"
    while not shutdown_flag.is_set():
        try:
            requests.post(
                f"{API_BASE}/api/v1/sandboxes/{sandbox_id}/events",
                json={
                    "event_type": "heartbeat",
                    "event_data": {
                        "status": "running",
                        "timestamp": datetime.utcnow().isoformat(),
                        "current_action": agent.current_action if agent else "initializing",
                        "memory_mb": get_memory_usage(),
                    }
                },
                timeout=5
            )
        except Exception as e:
            logger.warning(f"Heartbeat failed: {e}")
        time.sleep(15)

# Start heartbeat thread
shutdown_flag = threading.Event()
heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
heartbeat_thread.start()

# On shutdown:
# shutdown_flag.set()
```

### 7.4 Implementation: RestartOrchestrator Integration

**File**: `backend/omoi_os/services/fault_tolerance/restart_orchestrator.py` (MODIFY)

```python
async def initiate_restart(self, agent_id: str, reason: str) -> RestartEvent:
    task = await self._get_task_for_agent(agent_id)
    
    # Detect execution mode
    if task and task.sandbox_id:
        return await self._restart_sandbox_agent(task, reason)
    else:
        return await self._restart_legacy_agent(agent_id, reason)


async def _restart_sandbox_agent(self, task: Task, reason: str) -> RestartEvent:
    """Restart an agent running in a Daytona sandbox."""
    old_sandbox_id = task.sandbox_id
    
    # Step 1: Terminate old sandbox (graceful first, then force)
    try:
        await self.daytona_spawner.terminate_sandbox(
            old_sandbox_id, 
            graceful_timeout=10
        )
    except Exception as e:
        logger.warning(f"Graceful termination failed: {e}, forcing...")
        await self.daytona_spawner.force_terminate_sandbox(old_sandbox_id)
    
    # Step 2: Spawn replacement sandbox
    new_sandbox_id = await self.daytona_spawner.spawn_for_task(
        task_id=str(task.id),
        agent_id=task.assigned_agent_id,
        phase_id=task.phase_id,
        agent_type=task.agent_type or "openhands",
    )
    
    # Step 3: Update task with new sandbox_id
    async with self.db.get_session() as session:
        task.sandbox_id = new_sandbox_id
        session.commit()
    
    # Step 4: Emit event
    restart_event = RestartEvent(
        agent_id=task.assigned_agent_id,
        reason=reason,
        graceful_attempt_ms=10000,
        forced=False,
        spawned_sandbox_id=new_sandbox_id,
        old_sandbox_id=old_sandbox_id,
        occurred_at=datetime.utcnow()
    )
    
    await self.event_bus.publish(AgentRestartedEvent(restart_event))
    
    return restart_event
```

### 7.5 Implementation: Trajectory Context from Event Store

**File**: `backend/omoi_os/services/trajectory_context.py` (MODIFY)

```python
async def build_for_task(self, task: Task) -> AgentTrajectoryContext:
    """Build trajectory context - sandbox or legacy mode."""
    if task.sandbox_id:
        return await self._build_from_event_store(task)
    else:
        return await self._build_from_filesystem(task)


async def _build_from_event_store(self, task: Task) -> AgentTrajectoryContext:
    """Build context from events POSTed by sandbox worker."""
    async with self.db.get_session() as session:
        # Get recent events from database (requires Phase 4 DB persistence)
        events = await session.query(SandboxEvent).filter(
            SandboxEvent.sandbox_id == task.sandbox_id
        ).order_by(
            SandboxEvent.created_at.desc()
        ).limit(self.context_history_lines).all()
    
    # Build logs snippet from events
    logs_lines = []
    for event in reversed(events):
        if event.event_type in ("agent_message", "agent_thinking", "tool_use"):
            logs_lines.append(f"[{event.event_type}] {event.payload.get('message', '')}")
    
    return AgentTrajectoryContext(
        agent_id=task.assigned_agent_id,
        age_seconds=int((datetime.utcnow() - task.created_at).total_seconds()),
        logs_snippet="\n".join(logs_lines[-self.context_history_lines:]),
        prior_summaries=await self._get_prior_summaries(task.assigned_agent_id),
        status=task.status,
        resource_metrics=await self._get_resource_metrics_from_events(events),
    )
```

### 7.6 Checklist

| # | Task | Status | Test |
|---|------|--------|------|
| 7.1 | Write `test_sandbox_worker_sends_heartbeats` | ⬜ | — |
| 7.2 | Write `test_heartbeat_analyzer_detects_sandbox_miss` | ⬜ | — |
| 7.3 | Write `test_restart_orchestrator_handles_sandbox` | ⬜ | — |
| 7.4 | Write `test_trajectory_context_from_event_store` | ⬜ | — |
| 7.5 | Run tests - verify FAIL | ⬜ | All should fail |
| 7.6 | Add heartbeat thread to worker script | ⬜ | — |
| 7.7 | Add `_restart_sandbox_agent()` to RestartOrchestrator | ⬜ | — |
| 7.8 | Inject DaytonaSpawnerService into RestartOrchestrator | ⬜ | — |
| 7.9 | Add `_build_from_event_store()` to TrajectoryContextBuilder | ⬜ | — |
| 7.10 | Update HeartbeatAnalyzer to check sandbox events | ⬜ | — |
| 7.11 | Run tests - confirm PASS | ⬜ | ✅ All green |
| 7.12 | Run Phase 0-6 tests - confirm no regression | ⬜ | ✅ All green |
| 7.13 | End-to-end test: heartbeat miss → restart → new sandbox | ⬜ | ✅ Integration |

**Gate**: All Phase 7 tests must pass. Fault tolerance integration complete! ✅

---

## Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        IMPLEMENTATION PROGRESS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│                         MVP TRACK (Quick Start)                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  Phase 0: Validate Existing Infrastructure     ⬜ Not Started              │
│  ├─ Tests written: 0/4                                                     │
│  └─ Blocking: Phase 1                                                      │
│                                                                             │
│  Phase 1: Sandbox Event Callback               ⬜ Not Started              │
│  ├─ Tests written: 0/3                                                     │
│  ├─ Implementation: 0%                                                     │
│  └─ Blocking: Phase 2                                                      │
│                                                                             │
│  Phase 2: Message Injection                    ⬜ Not Started              │
│  ├─ Tests written: 0/4                                                     │
│  ├─ Implementation: 0%                                                     │
│  └─ Blocking: Phase 3                                                      │
│                                                                             │
│  Phase 3: Worker Script Updates                ⬜ Not Started              │
│  ├─ Tests written: 0/4                                                     │
│  ├─ Implementation: 0%                                                     │
│  └─ 🎉 MVP COMPLETE when this passes                                       │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  MVP Effort: 10-13 hours (~1-2 days)                                       │
│  You can STOP HERE and have working sandbox agents!                        │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│                    FULL INTEGRATION (Production Ready)                      │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  Phase 4: Database Persistence                 ⬜ Not Started              │
│  ├─ Required for: Phase 7 trajectory context                               │
│  └─ Enables: Event history, audit trail                                    │
│                                                                             │
│  Phase 5: Branch Workflow Service              ⬜ Not Started              │
│  └─ Enables: Automated Git branch/PR management                            │
│                                                                             │
│  Phase 6: Guardian & Systems Integration       ⬜ Not Started              │
│  ├─ Tests written: 0/5                                                     │
│  ├─ Implementation: 0%                                                     │
│  └─ Enables: Guardian can steer sandbox agents                             │
│                                                                             │
│  Phase 7: Fault Tolerance Integration          ⬜ Not Started              │
│  ├─ Tests written: 0/4                                                     │
│  ├─ Implementation: 0%                                                     │
│  └─ Enables: Heartbeats, automatic restart, full monitoring               │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Full Integration Effort: 38-50 hours (~1 week)                            │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  KEY INSIGHT: Each phase BUILDS ON the previous ones.                      │
│  MVP creates the extension points that Full Integration uses.              │
│  This is NOT a parallel system - it's one system growing.                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Related Documents

- [Gap Analysis](./02_gap_analysis.md) - What exists vs. what's needed
- [Architecture](./01_architecture.md) - System design
- [HTTP API Migration](./05_http_api_migration.md) - MCP → HTTP mapping
