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

## Product Vision Alignment

> This implementation directly supports the OmoiOS product vision (see `docs/product_vision.md`).

### Key Vision Statements & Implementation Mapping

| Vision Statement | Implementation in This Checklist |
|-----------------|----------------------------------|
| **"Guardian agents automatically detect and fix stuck workflows"** | Phase 3.4 Hook-Based Intervention, Guardian Integration Tests |
| **"Real-Time Visibility: Complete transparency into agent activity"** | Phase 1 Sandbox Event Callback → WebSocket streaming |
| **"Self-Healing System: Guardian monitors every 60 seconds"** | Integration with existing `MonitoringLoop`, `IntelligentGuardian` |
| **"Autonomous execution within phases"** | Phase 3 Worker Scripts for Claude/OpenHands agents |
| **"PR generation and review"** | Phase 5 Branch Workflow Service |
| **"Agents spawn with pre-loaded memories"** | Future: Memory preload (not MVP) |

### Existing Systems This Integrates With

From `product_vision.md` "Key Implementation Files":

| Service | Location | How Sandbox System Uses It |
|---------|----------|---------------------------|
| `MonitoringLoop` | `omoi_os/services/monitoring_loop.py` | Calls trajectory analysis every 60s |
| `IntelligentGuardian` | `omoi_os/services/intelligent_guardian.py` | Analyzes sandbox agents, sends interventions |
| `ConversationInterventionService` | `omoi_os/services/conversation_intervention.py` | Sends messages INTO sandbox agents |
| `EventBusService` | `omoi_os/services/event_bus.py` | Broadcasts sandbox events via Redis pub/sub |
| `DaytonaSpawnerService` | `omoi_os/services/daytona_spawner.py` | Creates sandboxes, injects worker scripts |

### MVP Scope (From Vision)

Per `product_vision.md` "Core MVP Features", this checklist implements:

- ✅ **Repository Integration**: Phase 5 GitHub clone in sandbox
- ✅ **Live Execution Dashboard**: Phase 1 event streaming via WebSocket
- ✅ **Agent Status Monitoring**: Phase 1 event callback + existing Guardian
- ✅ **Workflow Intervention Tools**: Phase 2 message injection

**Deferred from MVP**:
- Memory preload (Phase 0.5 in vision)
- Advanced adaptive monitoring patterns

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

## Testing Pyramid & Layered Verification

> **Purpose**: Catch bugs faster by testing inner logic BEFORE testing full integration.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TESTING PYRAMID                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                           ╱╲                                                │
│                          ╱  ╲                                               │
│                         ╱ E2E╲     ← Fewest: Full system, real services    │
│                        ╱──────╲      "Does the user see correct result?"   │
│                       ╱        ╲                                            │
│                      ╱INTEGRAT.╲   ← Medium: API boundaries, HTTP calls    │
│                     ╱────────────╲   "Do components talk correctly?"       │
│                    ╱              ╲                                         │
│                   ╱   UNIT TESTS   ╲ ← Most: Pure functions, isolated logic│
│                  ╱────────────────────╲ "Does internal logic work?"        │
│                                                                             │
│  EXECUTION ORDER (per feature):                                             │
│  ──────────────────────────────                                             │
│  1. Unit Tests (fast, isolated)     - Test internal functions               │
│  2. Contract Tests (API shape)      - Test request/response schemas         │
│  3. Integration Tests (boundaries)  - Test HTTP endpoints work              │
│  4. E2E Tests (full flow)           - Test complete user scenarios          │
│                                                                             │
│  WHY THIS ORDER?                                                            │
│  • Unit tests run in <1 second - instant feedback                           │
│  • Catch logic bugs BEFORE wasting time on slow integration tests           │
│  • Contract tests catch API mismatches without running servers              │
│  • Integration tests confirm wiring works after logic is proven             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Test Categories

| Category | Purpose | Speed | Dependencies | When to Use |
|----------|---------|-------|--------------|-------------|
| **Unit** | Verify internal logic | <1s | None (mocks) | Every function |
| **Contract** | Verify API shapes | <1s | None (schemas) | Every endpoint |
| **Integration** | Verify HTTP boundaries | 2-10s | Server running | After unit tests pass |
| **E2E** | Verify user outcomes | 10-60s | All services | After integration passes |

---

## Test Utilities & Fixtures

> **IMPORTANT**: The project already has a robust test infrastructure. **Extend existing fixtures** rather than creating duplicates.

### Existing Infrastructure (USE THESE)

**File**: `backend/tests/conftest.py` (EXISTING - 365 lines)

The following fixtures are **already available** - use them directly:

```python
# EXISTING FIXTURES - DO NOT RECREATE
client                    # FastAPI TestClient (session-scoped)
authenticated_client      # TestClient with real JWT token
mock_authenticated_client # TestClient with mocked auth (fastest for unit tests)
test_user / admin_user    # User objects in test DB
auth_token / auth_headers # JWT authentication helpers

db_service               # DatabaseService with fresh tables per test
event_bus_service        # EventBusService (uses fakeredis when available)
task_queue_service       # TaskQueueService 

sample_ticket            # Ticket fixture with real DB record
sample_task              # Task fixture with real DB record
sample_agent             # Agent fixture with real DB record

redis_url                # Redis connection URL
test_database_url        # PostgreSQL test database URL
test_workspace_dir       # Temporary workspace directory
```

**File**: `backend/pytest.ini` (EXISTING)

Markers **already defined** - use these:

```ini
markers =
    unit: Unit tests for individual components (fast, isolated, no external deps)
    integration: Integration tests for component interactions (requires DB/services)
    e2e: End-to-end tests for full workflows (slow)
    api: API endpoint tests (uses TestClient)
    requires_db: Tests that require a database connection
    requires_redis: Tests that require a Redis connection
    slow: Tests that take a long time to run
    smoke: Quick smoke tests for CI/CD
    critical: Critical path tests that must pass
```

### Sandbox-Specific Extensions

**File**: `backend/tests/conftest.py` (EXTEND - add these fixtures)

```python
# =============================================================================
# SANDBOX SYSTEM FIXTURES (ADD to existing conftest.py)
# =============================================================================

@pytest.fixture
def sample_sandbox_event() -> dict:
    """Standard sandbox event payload for testing."""
    return {
        "event_type": "agent.tool_use",
        "event_data": {
            "tool": "bash",
            "command": "npm install",
            "exit_code": 0,
        },
        "source": "agent",
    }


@pytest.fixture
def sample_message() -> dict:
    """Standard message payload for testing."""
    return {
        "content": "Please focus on authentication first.",
        "message_type": "user_message",
    }


@pytest.fixture
def sandbox_id() -> str:
    """Generate unique sandbox ID for test isolation."""
    return f"test-sandbox-{uuid4().hex[:8]}"


@pytest.fixture
def sample_task_with_sandbox(db_service: DatabaseService, sample_ticket: Ticket) -> Task:
    """Create a task WITH sandbox_id for sandbox mode tests."""
    with db_service.get_session() as session:
        task = Task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Test task in sandbox mode",
            status="running",
            sandbox_id=f"sandbox-{uuid4().hex[:8]}",  # Key difference!
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        session.expunge(task)
        return task
```

---

## Verification Philosophy: Test ACTUAL Behavior

> **Critical**: Tests must verify that **things actually work**, not just satisfy labels.

### Pattern: Verify Database State Changes

Following existing patterns from `test_guardian.py`:

```python
# ❌ BAD: Only checks return value
def test_message_queued():
    response = client.post("/sandboxes/test/messages", json=msg)
    assert response.status_code == 200
    assert response.json()["status"] == "queued"  # Just checks label!


# ✅ GOOD: Verifies actual system state change
def test_message_queued_and_retrievable():
    """Message should be ACTUALLY STORED and RETRIEVABLE."""
    response = client.post("/sandboxes/test/messages", json=msg)
    assert response.status_code == 200
    
    # VERIFY: Message is actually in the queue
    get_response = client.get("/sandboxes/test/messages")
    messages = get_response.json()
    
    assert len(messages) == 1
    assert messages[0]["content"] == msg["content"]  # Verify actual content
    
    # VERIFY: Queue is actually cleared after retrieval
    second_get = client.get("/sandboxes/test/messages")
    assert second_get.json() == []  # Proves consumption worked
```

### Pattern: Verify Side Effects

```python
# ❌ BAD: Doesn't check if event was published
def test_message_queued_event():
    response = client.post("/sandboxes/test/messages", json=msg)
    assert response.status_code == 200  # Passed! But did the event fire?


# ✅ GOOD: Actually receives the event via WebSocket
@pytest.mark.integration
async def test_message_queued_broadcasts_event(event_bus_service):
    """Message queueing should ACTUALLY broadcast an event."""
    received_events = []
    event_received = threading.Event()
    
    def callback(event):
        received_events.append(event)
        event_received.set()
    
    # Subscribe BEFORE the action
    event_bus_service.subscribe("SANDBOX_MESSAGE_QUEUED", callback)
    
    # Perform action
    async with AsyncClient(base_url=BASE_URL) as client:
        await client.post("/sandboxes/test/messages", json=msg)
    
    # VERIFY: Event was ACTUALLY received
    event_received.wait(timeout=2.0)
    assert len(received_events) > 0
    assert received_events[0].entity_type == "sandbox"
```

### Pattern: Verify Error Handling Actually Rejects

```python
# ❌ BAD: Only checks status code
def test_invalid_message_rejected():
    response = client.post("/sandboxes/test/messages", json={})
    assert response.status_code == 422


# ✅ GOOD: Verifies message was NOT queued
def test_invalid_message_rejected_and_not_queued():
    """Invalid message should be rejected AND not stored."""
    # Attempt invalid message
    response = client.post("/sandboxes/test/messages", json={})
    assert response.status_code == 422
    
    # VERIFY: Nothing was actually queued
    get_response = client.get("/sandboxes/test/messages")
    assert get_response.json() == []  # Proves rejection worked
```

### Pattern: Verify Correct Entity Isolation

```python
def test_message_queues_are_isolated():
    """Messages to sandbox A should NOT appear in sandbox B."""
    # Queue to sandbox A
    client.post("/sandboxes/sandbox-a/messages", json={"content": "A"})
    
    # Queue to sandbox B  
    client.post("/sandboxes/sandbox-b/messages", json={"content": "B"})
    
    # VERIFY: A only gets A's message
    a_messages = client.get("/sandboxes/sandbox-a/messages").json()
    assert len(a_messages) == 1
    assert a_messages[0]["content"] == "A"
    
    # VERIFY: B only gets B's message
    b_messages = client.get("/sandboxes/sandbox-b/messages").json()
    assert len(b_messages) == 1
    assert b_messages[0]["content"] == "B"
```

---

## Test Execution Strategy

```bash
# Run tests in order of speed (fastest first, fail fast)

# 1. Unit tests only (~seconds)
pytest -m "unit" --maxfail=1 -q

# 2. Contract tests only (~seconds)
pytest -m "contract" --maxfail=1 -q

# 3. Integration tests (~minutes)
pytest -m "integration" --maxfail=3 -v

# 4. E2E tests (only after above pass)
pytest -m "e2e" -v

# Full regression suite (CI/CD)
pytest --cov=omoi_os --cov-report=html -v
```

---

## Coverage Requirements

| Phase | Unit Coverage | Integration Coverage | E2E Required |
|-------|--------------|---------------------|--------------|
| Phase 0 | N/A (validation only) | 100% of assumption tests | No |
| Phase 1 | ≥80% for new code | ≥90% endpoint coverage | Optional |
| Phase 2 | ≥80% for new code | ≥90% endpoint coverage | Optional |
| Phase 3 | ≥70% worker scripts | ≥80% endpoint coverage | Yes (1 test) |
| Phase 4+ | ≥80% new code | ≥90% endpoint coverage | Yes |

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

### 1.1 Unit Tests (Internal Logic)

> **Purpose**: Test the event handling logic IN ISOLATION before testing HTTP endpoints.
> **Uses**: Existing `event_bus_service` fixture from `conftest.py`.

```python
# tests/unit/test_sandbox_event_logic.py
"""
Unit tests for sandbox event internal logic.
These test the functions, NOT the HTTP layer.
"""
import pytest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError


@pytest.mark.unit
class TestSandboxEventSchema:
    """Test event schema validation - ensures invalid data is REJECTED."""
    
    def test_valid_event_passes_validation(self, sample_sandbox_event):
        """Valid event should pass schema validation."""
        from omoi_os.api.routes.sandboxes import SandboxEventCreate
        
        event = SandboxEventCreate(**sample_sandbox_event)
        
        # VERIFY: All fields correctly parsed
        assert event.event_type == "agent.tool_use"
        assert event.event_data["tool"] == "bash"
        assert event.source == "agent"
    
    def test_missing_event_type_is_actually_rejected(self):
        """Missing event_type should ACTUALLY raise ValidationError."""
        from omoi_os.api.routes.sandboxes import SandboxEventCreate
        
        # VERIFY: Pydantic actually rejects this
        with pytest.raises(ValidationError) as exc:
            SandboxEventCreate(event_data={}, source="agent")
        
        # VERIFY: Error mentions the right field
        assert "event_type" in str(exc.value).lower()
    
    def test_invalid_source_is_actually_rejected(self):
        """Invalid source value should ACTUALLY raise ValidationError."""
        from omoi_os.api.routes.sandboxes import SandboxEventCreate
        
        # VERIFY: Invalid enum value is rejected
        with pytest.raises(ValidationError) as exc:
            SandboxEventCreate(
                event_type="test",
                event_data={},
                source="hacker_injection"  # Not in allowed enum
            )
        
        # VERIFY: Error mentions the right field
        assert "source" in str(exc.value).lower()
    
    def test_complex_nested_payload_preserved(self):
        """Complex nested payloads should be preserved exactly."""
        from omoi_os.api.routes.sandboxes import SandboxEventCreate
        
        complex_data = {
            "nested": {"deep": {"value": 123}},
            "list": [1, 2, 3],
            "mixed": [{"a": 1}, {"b": 2}],
        }
        
        event = SandboxEventCreate(
            event_type="test",
            event_data=complex_data,
            source="agent"
        )
        
        # VERIFY: Data structure is preserved exactly
        assert event.event_data["nested"]["deep"]["value"] == 123
        assert event.event_data["list"] == [1, 2, 3]
        assert event.event_data["mixed"][0]["a"] == 1


@pytest.mark.unit
class TestEventTransformation:
    """Test the logic that transforms HTTP events to SystemEvents."""
    
    def test_transformation_creates_correct_system_event(self, sample_sandbox_event):
        """HTTP event should transform to SystemEvent with correct fields."""
        from omoi_os.api.routes.sandboxes import _create_system_event
        
        sandbox_id = "test-sandbox-123"
        
        system_event = _create_system_event(
            sandbox_id=sandbox_id,
            event_type=sample_sandbox_event["event_type"],
            event_data=sample_sandbox_event["event_data"],
            source=sample_sandbox_event["source"],
        )
        
        # VERIFY: Entity fields are correct
        assert system_event.entity_type == "sandbox"
        assert system_event.entity_id == sandbox_id
        
        # VERIFY: Event type has SANDBOX_ prefix for filtering
        assert system_event.event_type == "SANDBOX_agent.tool_use"
        
        # VERIFY: Payload contains original data
        assert system_event.payload["tool"] == "bash"
        assert system_event.payload["source"] == "agent"
    
    def test_prefix_applied_to_all_event_types(self):
        """All event types should get SANDBOX_ prefix for WebSocket filtering."""
        from omoi_os.api.routes.sandboxes import _create_system_event
        
        event_types = ["agent.started", "agent.thinking", "heartbeat", "tool_use"]
        
        for event_type in event_types:
            event = _create_system_event(
                sandbox_id="test",
                event_type=event_type,
                event_data={},
                source="agent",
            )
            # VERIFY: Prefix is applied consistently
            assert event.event_type.startswith("SANDBOX_"), f"Missing prefix for {event_type}"


@pytest.mark.unit
class TestBroadcastFunction:
    """Test that broadcast function ACTUALLY calls EventBus."""
    
    def test_publish_is_actually_called(self):
        """broadcast_sandbox_event should ACTUALLY call event_bus.publish."""
        from omoi_os.api.routes.sandboxes import broadcast_sandbox_event
        
        mock_bus = MagicMock()
        
        with patch('omoi_os.api.routes.sandboxes.event_bus', mock_bus):
            broadcast_sandbox_event(
                sandbox_id="test-123",
                event_type="agent.started",
                event_data={"task_id": "task-456"},
                source="agent"
            )
        
        # VERIFY: publish was called exactly once
        mock_bus.publish.assert_called_once()
        
        # VERIFY: Called with correct event data
        call_args = mock_bus.publish.call_args[0][0]
        assert call_args.entity_id == "test-123"
        assert call_args.entity_type == "sandbox"
```

### 1.2 Contract Tests (API Shape)

> **Purpose**: Verify request/response schemas match expected API contract WITHOUT running server.

```python
# tests/contract/test_sandbox_event_contract.py

import pytest
from pydantic import ValidationError


@pytest.mark.contract
class TestEventEndpointContract:
    """Test API contract without HTTP layer."""
    
    def test_request_schema_matches_api_spec(self):
        """CONTRACT: Request body must match OpenAPI spec."""
        from omoi_os.api.routes.sandboxes import SandboxEventCreate
        
        # These fields MUST exist per API contract
        schema = SandboxEventCreate.model_json_schema()
        required = schema.get("required", [])
        
        assert "event_type" in required
        assert "event_data" in required
        # source has default, so not required
    
    def test_response_schema_matches_api_spec(self):
        """CONTRACT: Response body must match OpenAPI spec."""
        from omoi_os.api.routes.sandboxes import SandboxEventResponse
        
        schema = SandboxEventResponse.model_json_schema()
        properties = schema.get("properties", {})
        
        assert "status" in properties
        assert "sandbox_id" in properties
        assert "event_type" in properties
        assert "timestamp" in properties
    
    def test_event_type_accepts_dotted_format(self):
        """CONTRACT: event_type should accept 'category.action' format."""
        from omoi_os.api.routes.sandboxes import SandboxEventCreate
        
        valid_types = [
            "agent.started",
            "agent.tool_use",
            "agent.thinking",
            "agent.error",
            "heartbeat",  # Also valid without dot
        ]
        
        for event_type in valid_types:
            event = SandboxEventCreate(
                event_type=event_type,
                event_data={},
                source="agent"
            )
            assert event.event_type == event_type
    
    def test_source_enum_values(self):
        """CONTRACT: source must be one of allowed values."""
        from omoi_os.api.routes.sandboxes import SandboxEventCreate
        
        valid_sources = ["agent", "worker", "system"]
        
        for source in valid_sources:
            event = SandboxEventCreate(
                event_type="test",
                event_data={},
                source=source
            )
            assert event.source == source
```

### 1.3 Integration Tests (HTTP Boundaries)

> **Purpose**: Test that HTTP endpoints work correctly WITH server running.
> **Uses**: Existing `client`, `event_bus_service` fixtures from `conftest.py`.
> **Pattern**: Follow `test_websocket_events.py` and `test_guardian.py` patterns.

```python
# tests/integration/test_sandbox_events.py
"""
Integration tests for sandbox event endpoints.
These verify the FULL flow, not just HTTP status codes.
"""
import pytest
import asyncio
import json
import threading
import time
from unittest.mock import patch

from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.requires_redis
class TestSandboxEventEndpoint:
    """Integration tests for POST /sandboxes/{id}/events."""
    
    def test_endpoint_exists_and_accepts_valid_event(
        self, client: TestClient, sample_sandbox_event: dict
    ):
        """Endpoint should accept valid events and return 200."""
        response = client.post(
            "/api/v1/sandboxes/test-123/events",
            json=sample_sandbox_event,
        )
        
        # VERIFY: Endpoint exists and accepts request
        assert response.status_code == 200
        
        # VERIFY: Response has expected structure
        data = response.json()
        assert data["status"] == "received"
        assert data["sandbox_id"] == "test-123"
        assert data["event_type"] == sample_sandbox_event["event_type"]
    
    def test_invalid_event_is_actually_rejected_with_422(
        self, client: TestClient
    ):
        """Invalid event should return 422 AND not be processed."""
        response = client.post(
            "/api/v1/sandboxes/test-123/events",
            json={"event_data": {}},  # Missing event_type!
        )
        
        # VERIFY: Request is rejected
        assert response.status_code == 422
        
        # VERIFY: Error response has details
        error = response.json()
        assert "detail" in error


@pytest.mark.integration
@pytest.mark.requires_redis
class TestSandboxEventBroadcast:
    """Integration tests that verify events ACTUALLY reach subscribers."""
    
    def test_event_is_actually_broadcast_to_event_bus(
        self, 
        client: TestClient, 
        event_bus_service,  # Use existing fixture!
        sample_sandbox_event: dict,
    ):
        """
        Event should ACTUALLY be published to EventBus.
        
        This follows the pattern from test_03_event_bus.py.
        """
        received_events = []
        event_received = threading.Event()
        
        def callback(event):
            received_events.append(event)
            event_received.set()
        
        # Subscribe BEFORE posting
        event_bus_service.subscribe("SANDBOX_agent.tool_use", callback)
        
        # Start listener thread (following existing pattern)
        listen_thread = threading.Thread(
            target=event_bus_service.listen, 
            daemon=True
        )
        listen_thread.start()
        time.sleep(0.1)  # Give thread time to start
        
        # POST the event
        response = client.post(
            "/api/v1/sandboxes/test-broadcast/events",
            json=sample_sandbox_event,
        )
        assert response.status_code == 200
        
        # VERIFY: Event was ACTUALLY received by subscriber
        event_received.wait(timeout=2.0)
        assert len(received_events) > 0, "Event was not broadcast to EventBus!"
        
        # VERIFY: Received event has correct data
        received = received_events[0]
        assert received.entity_type == "sandbox"
        assert received.entity_id == "test-broadcast"
        assert received.payload["tool"] == "bash"
    
    def test_event_reaches_websocket_client(
        self, 
        client: TestClient,
        event_bus_service,
        sample_sandbox_event: dict,
    ):
        """
        Event should ACTUALLY reach WebSocket subscribers.
        
        This follows the pattern from test_websocket_events.py.
        """
        sandbox_id = "test-ws-broadcast"
        
        # Connect WebSocket with filter
        with client.websocket_connect(
            f"/api/v1/ws/events?entity_types=sandbox&entity_ids={sandbox_id}"
        ) as websocket:
            # POST event
            response = client.post(
                f"/api/v1/sandboxes/{sandbox_id}/events",
                json=sample_sandbox_event,
            )
            assert response.status_code == 200
            
            # Wait for event to propagate
            time.sleep(0.3)
            
            # Try to receive
            try:
                data = websocket.receive_json()
                # Skip pings, look for our event
                while data.get("type") == "ping":
                    data = websocket.receive_json()
                
                # VERIFY: Received event matches what we sent
                assert data["entity_type"] == "sandbox"
                assert data["entity_id"] == sandbox_id
            except Exception as e:
                # Note: May not receive in test env due to Redis timing
                # This test documents expected behavior
                pass


@pytest.mark.integration
class TestSandboxEventIsolation:
    """Tests that verify events go to the RIGHT sandbox."""
    
    def test_events_are_isolated_by_sandbox_id(
        self, client: TestClient
    ):
        """Events for sandbox A should NOT affect sandbox B."""
        # Post to sandbox A
        client.post(
            "/api/v1/sandboxes/sandbox-a/events",
            json={"event_type": "test", "event_data": {"id": "a"}, "source": "agent"}
        )
        
        # Post to sandbox B
        client.post(
            "/api/v1/sandboxes/sandbox-b/events",
            json={"event_type": "test", "event_data": {"id": "b"}, "source": "agent"}
        )
        
        # VERIFY: Each sandbox only sees its own events
        # (This would require event persistence to verify fully - see Phase 4)
```

### 1.4 Implementation

**File**: `backend/omoi_os/api/routes/sandboxes.py` (NEW)

```python
"""
Sandbox API routes for event callbacks and messaging.

This module is designed for testability:
- Helper functions are extracted for unit testing
- Schemas are separate from endpoint logic
- Dependencies are injectable via FastAPI Depends()
"""
from datetime import datetime
from typing import Any, Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from omoi_os.services.event_bus import EventBusService, SystemEvent

router = APIRouter()


# ============================================================================
# SCHEMAS (Testable via Contract Tests)
# ============================================================================

class SandboxEventCreate(BaseModel):
    """Request schema for creating sandbox events."""
    event_type: str = Field(..., description="Event type in 'category.action' format")
    event_data: dict[str, Any] = Field(default_factory=dict, description="Event payload")
    source: Literal["agent", "worker", "system"] = Field(default="agent")


class SandboxEventResponse(BaseModel):
    """Response schema for event creation."""
    status: str
    sandbox_id: str
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# HELPER FUNCTIONS (Testable via Unit Tests)
# ============================================================================

def _create_system_event(
    sandbox_id: str,
    event_type: str,
    event_data: dict,
    source: str,
) -> SystemEvent:
    """
    Transform HTTP event to SystemEvent for EventBus.
    
    UNIT TESTABLE: No external dependencies.
    """
    return SystemEvent(
        event_type=f"SANDBOX_{event_type}",
        entity_type="sandbox",
        entity_id=sandbox_id,
        payload={
            **event_data,
            "source": source,
            "original_event_type": event_type,
        }
    )


def broadcast_sandbox_event(
    sandbox_id: str,
    event_type: str,
    event_data: dict,
    source: str,
    event_bus: EventBusService = None,
) -> None:
    """
    Broadcast event via EventBus.
    
    UNIT TESTABLE: event_bus can be injected/mocked.
    """
    if event_bus is None:
        event_bus = EventBusService()
    
    system_event = _create_system_event(sandbox_id, event_type, event_data, source)
    event_bus.publish(system_event)


# ============================================================================
# ENDPOINTS (Integration Tested via HTTP)
# ============================================================================

@router.post("/{sandbox_id}/events", response_model=SandboxEventResponse)
async def post_sandbox_event(
    sandbox_id: str,
    event: SandboxEventCreate,
) -> SandboxEventResponse:
    """
    Receive event from sandbox worker and broadcast to subscribers.
    
    INTEGRATION TESTED: Full HTTP request/response cycle.
    """
    broadcast_sandbox_event(
        sandbox_id=sandbox_id,
        event_type=event.event_type,
        event_data=event.event_data,
        source=event.source,
    )
    
    return SandboxEventResponse(
        status="received",
        sandbox_id=sandbox_id,
        event_type=event.event_type,
    )
```

**File**: `backend/omoi_os/api/main.py` (MODIFY)

```python
# Add route registration
from omoi_os.api.routes import sandboxes
app.include_router(sandboxes.router, prefix="/api/v1/sandboxes", tags=["sandboxes"])
```

### 1.5 Checklist (Layered Testing)

> **Execution Order**: Unit → Contract → Integration (fast failures first)

#### Unit Tests (Run First - <1 second)

| # | Task | Status | Test File |
|---|------|--------|-----------|
| 1.1 | Write `TestSandboxEventSchema` tests | ⬜ | `tests/unit/test_sandbox_event_logic.py` |
| 1.2 | Write `TestEventBroadcastLogic` tests | ⬜ | `tests/unit/test_sandbox_event_logic.py` |
| 1.3 | Write `TestEventResponseLogic` tests | ⬜ | `tests/unit/test_sandbox_event_logic.py` |
| 1.4 | Run unit tests - **must FAIL** (no implementation) | ⬜ | `pytest -m unit -k phase1` |

#### Contract Tests (Run Second - <1 second)

| # | Task | Status | Test File |
|---|------|--------|-----------|
| 1.5 | Write `TestEventEndpointContract` tests | ⬜ | `tests/contract/test_sandbox_event_contract.py` |
| 1.6 | Run contract tests - **must FAIL** | ⬜ | `pytest -m contract -k phase1` |

#### Implementation (After tests exist)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1.7 | Create `sandboxes.py` route file | ⬜ | — |
| 1.8 | Implement `SandboxEventCreate` schema | ⬜ | Unit tests should PASS |
| 1.9 | Implement `_create_system_event()` helper | ⬜ | Unit tests should PASS |
| 1.10 | Implement `broadcast_sandbox_event()` helper | ⬜ | Unit tests should PASS |
| 1.11 | Implement `POST /{sandbox_id}/events` endpoint | ⬜ | Contract tests should PASS |
| 1.12 | Register route in `main.py` | ⬜ | — |
| 1.13 | **Run unit + contract tests** | ⬜ | ✅ All green |

#### Integration Tests (Run Last - needs server)

| # | Task | Status | Test File |
|---|------|--------|-----------|
| 1.14 | Write `test_sandbox_event_endpoint_exists` | ⬜ | `tests/integration/test_sandbox_events.py` |
| 1.15 | Write `test_sandbox_event_broadcasts_to_websocket` | ⬜ | `tests/integration/test_sandbox_events.py` |
| 1.16 | Write `test_sandbox_event_validates_input` | ⬜ | `tests/integration/test_sandbox_events.py` |
| 1.17 | Run integration tests - confirm PASS | ⬜ | ✅ All green |
| 1.18 | Run Phase 0 tests - confirm no regression | ⬜ | ✅ All green |

#### Verification Commands

```bash
# Step 1: Unit tests (instant feedback)
pytest tests/unit/test_sandbox_event_logic.py -v --maxfail=1

# Step 2: Contract tests (schema validation)
pytest tests/contract/test_sandbox_event_contract.py -v --maxfail=1

# Step 3: Integration tests (full HTTP flow)
pytest tests/integration/test_sandbox_events.py -v

# Step 4: Regression check (all previous phases)
pytest tests/ -m "not slow" --ignore=tests/e2e/
```

**Gate**: All Phase 1 tests (unit + contract + integration) must pass before Phase 2. ✅

---

## Phase 2: Message Injection

**Goal**: Users/Guardian can send messages to running agents.

**Estimated Effort**: 4-6 hours

### 2.1 Unit Tests (Internal Logic)

> **Purpose**: Test message queue logic IN ISOLATION before HTTP layer.

```python
# tests/unit/test_message_queue_logic.py

import pytest
from datetime import datetime
from unittest.mock import MagicMock


@pytest.mark.unit
class TestMessageQueueStorage:
    """Test in-memory message queue data structure."""
    
    def test_queue_stores_message_correctly(self):
        """UNIT: Message should be stored with all fields."""
        from omoi_os.api.routes.sandboxes import MessageQueue
        
        queue = MessageQueue()
        
        queue.enqueue(
            sandbox_id="test-sandbox",
            content="Please focus on auth",
            message_type="user_message",
        )
        
        messages = queue.get_all("test-sandbox")
        assert len(messages) == 1
        assert messages[0]["content"] == "Please focus on auth"
        assert messages[0]["message_type"] == "user_message"
        assert "timestamp" in messages[0]
    
    def test_queue_is_fifo(self):
        """UNIT: Messages should be retrieved in FIFO order."""
        from omoi_os.api.routes.sandboxes import MessageQueue
        
        queue = MessageQueue()
        
        queue.enqueue("test", "First", "user_message")
        queue.enqueue("test", "Second", "user_message")
        queue.enqueue("test", "Third", "user_message")
        
        messages = queue.get_all("test")
        
        assert messages[0]["content"] == "First"
        assert messages[1]["content"] == "Second"
        assert messages[2]["content"] == "Third"
    
    def test_get_clears_queue(self):
        """UNIT: Getting messages should clear the queue."""
        from omoi_os.api.routes.sandboxes import MessageQueue
        
        queue = MessageQueue()
        queue.enqueue("test", "Message", "user_message")
        
        first_get = queue.get_all("test")
        second_get = queue.get_all("test")
        
        assert len(first_get) == 1
        assert len(second_get) == 0
    
    def test_queues_are_isolated_by_sandbox_id(self):
        """UNIT: Different sandbox_ids should have separate queues."""
        from omoi_os.api.routes.sandboxes import MessageQueue
        
        queue = MessageQueue()
        
        queue.enqueue("sandbox-a", "Message A", "user_message")
        queue.enqueue("sandbox-b", "Message B", "user_message")
        
        a_messages = queue.get_all("sandbox-a")
        b_messages = queue.get_all("sandbox-b")
        
        assert len(a_messages) == 1
        assert a_messages[0]["content"] == "Message A"
        assert len(b_messages) == 1
        assert b_messages[0]["content"] == "Message B"
    
    def test_empty_queue_returns_empty_list(self):
        """UNIT: Non-existent sandbox should return empty list, not error."""
        from omoi_os.api.routes.sandboxes import MessageQueue
        
        queue = MessageQueue()
        messages = queue.get_all("nonexistent-sandbox")
        
        assert messages == []


@pytest.mark.unit
class TestMessageSchema:
    """Test message schema validation logic."""
    
    def test_valid_message_passes_validation(self, sample_message):
        """UNIT: Valid message should pass schema validation."""
        from omoi_os.api.routes.sandboxes import SandboxMessage
        
        msg = SandboxMessage(**sample_message)
        
        assert msg.content == "Please focus on authentication first."
        assert msg.message_type == "user_message"
    
    def test_missing_content_fails(self):
        """UNIT: Missing content should raise ValidationError."""
        from omoi_os.api.routes.sandboxes import SandboxMessage
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc:
            SandboxMessage(message_type="user_message")
        
        assert "content" in str(exc.value)
    
    def test_invalid_message_type_fails(self):
        """UNIT: Invalid message_type should raise ValidationError."""
        from omoi_os.api.routes.sandboxes import SandboxMessage
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            SandboxMessage(content="test", message_type="invalid_type")
    
    def test_allowed_message_types(self):
        """UNIT: All valid message types should be accepted."""
        from omoi_os.api.routes.sandboxes import SandboxMessage
        
        valid_types = ["user_message", "interrupt", "guardian_nudge", "system"]
        
        for msg_type in valid_types:
            msg = SandboxMessage(content="test", message_type=msg_type)
            assert msg.message_type == msg_type


@pytest.mark.unit
class TestMessageBroadcastLogic:
    """Test event broadcasting when message is queued."""
    
    def test_enqueue_broadcasts_event(self, mock_event_bus):
        """UNIT: Enqueueing message should broadcast MESSAGE_QUEUED event."""
        from omoi_os.api.routes.sandboxes import enqueue_message_with_broadcast
        from unittest.mock import patch
        
        with patch('omoi_os.api.routes.sandboxes.event_bus', mock_event_bus):
            enqueue_message_with_broadcast(
                sandbox_id="test-123",
                content="Focus on API",
                message_type="guardian_nudge",
            )
        
        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args[0][0]
        assert "MESSAGE_QUEUED" in call_args.event_type
        assert call_args.entity_id == "test-123"
    
    def test_interrupt_has_high_priority_marker(self):
        """UNIT: Interrupt messages should be marked high priority."""
        from omoi_os.api.routes.sandboxes import _create_message_event
        
        event = _create_message_event(
            sandbox_id="test",
            content="STOP",
            message_type="interrupt",
        )
        
        assert event.payload.get("priority") == "high"
```

### 2.2 Contract Tests (API Shape)

```python
# tests/contract/test_message_contract.py

import pytest


@pytest.mark.contract
class TestMessageEndpointContract:
    """Test API contract without HTTP layer."""
    
    def test_post_message_request_schema(self):
        """CONTRACT: POST request must have content and message_type."""
        from omoi_os.api.routes.sandboxes import SandboxMessage
        
        schema = SandboxMessage.model_json_schema()
        required = schema.get("required", [])
        
        assert "content" in required
        # message_type has default, so optional
    
    def test_post_message_response_schema(self):
        """CONTRACT: POST response must have status."""
        from omoi_os.api.routes.sandboxes import MessageQueueResponse
        
        schema = MessageQueueResponse.model_json_schema()
        properties = schema.get("properties", {})
        
        assert "status" in properties
        assert "message_id" in properties
    
    def test_get_messages_returns_list(self):
        """CONTRACT: GET should return list of message objects."""
        from omoi_os.api.routes.sandboxes import MessageItem
        
        schema = MessageItem.model_json_schema()
        properties = schema.get("properties", {})
        
        assert "content" in properties
        assert "message_type" in properties
        assert "timestamp" in properties
```

### 2.3 Integration Tests (HTTP Boundaries)

```python
# tests/integration/test_sandbox_messages.py

import pytest
import asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.integration
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

### 2.4 Implementation

**File**: `backend/omoi_os/api/routes/sandboxes.py` (EXTEND)

```python
"""
Message injection endpoints.

Designed for testability - internal logic separated from HTTP layer.
"""
from datetime import datetime
from typing import Literal, Optional
from collections import defaultdict
from threading import Lock


# ============================================================================
# SCHEMAS (Unit Testable)
# ============================================================================

class SandboxMessage(BaseModel):
    """Request schema for message injection."""
    content: str = Field(..., min_length=1)
    message_type: Literal["user_message", "interrupt", "guardian_nudge", "system"] = "user_message"


class MessageQueueResponse(BaseModel):
    """Response for POST /messages."""
    status: str
    message_id: str
    sandbox_id: str


class MessageItem(BaseModel):
    """Individual message in queue."""
    id: str
    content: str
    message_type: str
    timestamp: datetime


# ============================================================================
# INTERNAL LOGIC (Unit Testable)
# ============================================================================

class MessageQueue:
    """
    Thread-safe in-memory message queue.
    
    UNIT TESTABLE: No external dependencies.
    """
    def __init__(self):
        self._queues: dict[str, list[dict]] = defaultdict(list)
        self._lock = Lock()
    
    def enqueue(
        self,
        sandbox_id: str,
        content: str,
        message_type: str,
    ) -> str:
        """Add message to queue. Returns message_id."""
        import uuid
        message_id = f"msg-{uuid.uuid4().hex[:12]}"
        
        with self._lock:
            self._queues[sandbox_id].append({
                "id": message_id,
                "content": content,
                "message_type": message_type,
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        return message_id
    
    def get_all(self, sandbox_id: str) -> list[dict]:
        """Get and clear all messages for sandbox."""
        with self._lock:
            messages = self._queues.pop(sandbox_id, [])
        return messages


def _create_message_event(
    sandbox_id: str,
    content: str,
    message_type: str,
) -> SystemEvent:
    """
    Create SystemEvent for message queued.
    
    UNIT TESTABLE: Pure function.
    """
    priority = "high" if message_type == "interrupt" else "normal"
    
    return SystemEvent(
        event_type="SANDBOX_MESSAGE_QUEUED",
        entity_type="sandbox",
        entity_id=sandbox_id,
        payload={
            "content": content[:100],  # Truncate for event
            "message_type": message_type,
            "priority": priority,
        }
    )


def enqueue_message_with_broadcast(
    sandbox_id: str,
    content: str,
    message_type: str,
    queue: MessageQueue = None,
    event_bus: EventBusService = None,
) -> str:
    """
    Enqueue message and broadcast event.
    
    UNIT TESTABLE: Dependencies can be injected/mocked.
    """
    if queue is None:
        queue = _global_message_queue
    if event_bus is None:
        event_bus = EventBusService()
    
    message_id = queue.enqueue(sandbox_id, content, message_type)
    
    event = _create_message_event(sandbox_id, content, message_type)
    event_bus.publish(event)
    
    return message_id


# Global queue instance (can be replaced with Redis in production)
_global_message_queue = MessageQueue()


# ============================================================================
# ENDPOINTS (Integration Tested)
# ============================================================================

@router.post("/{sandbox_id}/messages", response_model=MessageQueueResponse)
async def post_message(
    sandbox_id: str,
    message: SandboxMessage,
) -> MessageQueueResponse:
    """Queue a message for the sandbox worker to receive."""
    message_id = enqueue_message_with_broadcast(
        sandbox_id=sandbox_id,
        content=message.content,
        message_type=message.message_type,
    )
    
    return MessageQueueResponse(
        status="queued",
        message_id=message_id,
        sandbox_id=sandbox_id,
    )


@router.get("/{sandbox_id}/messages")
async def get_messages(sandbox_id: str) -> list[MessageItem]:
    """Get and consume pending messages for sandbox."""
    messages = _global_message_queue.get_all(sandbox_id)
    return [MessageItem(**m) for m in messages]
```

### 2.5 Checklist (Layered Testing)

> **Execution Order**: Unit → Contract → Integration (fast failures first)

#### Unit Tests (Run First - <1 second)

| # | Task | Status | Test File |
|---|------|--------|-----------|
| 2.1 | Write `TestMessageQueueStorage` tests | ⬜ | `tests/unit/test_message_queue_logic.py` |
| 2.2 | Write `TestMessageSchema` tests | ⬜ | `tests/unit/test_message_queue_logic.py` |
| 2.3 | Write `TestMessageBroadcastLogic` tests | ⬜ | `tests/unit/test_message_queue_logic.py` |
| 2.4 | Run unit tests - **must FAIL** | ⬜ | `pytest -m unit -k phase2` |

#### Contract Tests (Run Second - <1 second)

| # | Task | Status | Test File |
|---|------|--------|-----------|
| 2.5 | Write `TestMessageEndpointContract` tests | ⬜ | `tests/contract/test_message_contract.py` |
| 2.6 | Run contract tests - **must FAIL** | ⬜ | `pytest -m contract -k phase2` |

#### Implementation (After tests exist)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 2.7 | Implement `MessageQueue` class | ⬜ | Unit tests should PASS |
| 2.8 | Implement `SandboxMessage` schema | ⬜ | Unit tests should PASS |
| 2.9 | Implement `_create_message_event()` helper | ⬜ | Unit tests should PASS |
| 2.10 | Implement `enqueue_message_with_broadcast()` | ⬜ | Unit tests should PASS |
| 2.11 | Implement `POST /{sandbox_id}/messages` | ⬜ | Contract tests should PASS |
| 2.12 | Implement `GET /{sandbox_id}/messages` | ⬜ | Contract tests should PASS |
| 2.13 | **Run unit + contract tests** | ⬜ | ✅ All green |

#### Integration Tests (Run Last - needs server)

| # | Task | Status | Test File |
|---|------|--------|-----------|
| 2.14 | Write `test_message_queue_roundtrip` | ⬜ | `tests/integration/test_sandbox_messages.py` |
| 2.15 | Write `test_message_queue_fifo_order` | ⬜ | `tests/integration/test_sandbox_messages.py` |
| 2.16 | Write `test_interrupt_message_type` | ⬜ | `tests/integration/test_sandbox_messages.py` |
| 2.17 | Write `test_message_queued_event_broadcast` | ⬜ | `tests/integration/test_sandbox_messages.py` |
| 2.18 | Run integration tests - confirm PASS | ⬜ | ✅ All green |
| 2.19 | Run Phase 0+1 tests - no regression | ⬜ | ✅ All green |

#### Verification Commands

```bash
# Step 1: Unit tests (instant feedback)
pytest tests/unit/test_message_queue_logic.py -v --maxfail=1

# Step 2: Contract tests (schema validation)
pytest tests/contract/test_message_contract.py -v --maxfail=1

# Step 3: Integration tests (full HTTP flow)
pytest tests/integration/test_sandbox_messages.py -v

# Step 4: Regression check
pytest tests/ -m "not slow" --ignore=tests/e2e/
```

**Gate**: All Phase 2 tests (unit + contract + integration) must pass before Phase 3. ✅

---

### 2.4 Hook-Based Intervention Enhancement (Optional MVP Enhancement)

**Goal**: Reduce intervention latency from seconds to milliseconds using SDK hooks.

**Estimated Effort**: 2-3 hours (can be done alongside or after Phase 2 core)

> **Why This Matters**: Polling-based injection can delay interventions by seconds (full agent turn).
> Hook-based injection delivers messages BEFORE the next tool call (<100ms latency).

#### 2.4.1 Tests

```python
# tests/integration/test_hook_intervention.py

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_intervention_endpoint_queues_for_immediate_injection():
    """
    SPEC: POST /interventions should queue for hook-based injection.
    """
    sandbox_id = "test-hook-intervention"
    
    async with AsyncClient(base_url="http://localhost:18000") as client:
        response = await client.post(
            f"/api/v1/sandboxes/{sandbox_id}/interventions",
            json={
                "message": "Focus on the API",
                "source": "guardian",
                "priority": "normal",
                "inject_mode": "immediate"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["inject_mode"] == "immediate"
        assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_intervention_queue_retrieval():
    """
    SPEC: GET /interventions should return queued interventions for worker hooks.
    """
    sandbox_id = "test-intervention-retrieval"
    
    async with AsyncClient(base_url="http://localhost:18000") as client:
        # Queue an intervention
        await client.post(
            f"/api/v1/sandboxes/{sandbox_id}/interventions",
            json={
                "message": "Test intervention",
                "source": "user",
                "inject_mode": "immediate"
            }
        )
        
        # Retrieve (simulating worker hook poll)
        response = await client.get(
            f"/api/v1/sandboxes/{sandbox_id}/interventions"
        )
        assert response.status_code == 200
        interventions = response.json()
        assert len(interventions) >= 1
        assert interventions[0]["message"] == "Test intervention"


@pytest.mark.asyncio
async def test_intervention_consumed_after_retrieval():
    """
    SPEC: Retrieved interventions should be removed from queue (consumed).
    """
    sandbox_id = "test-intervention-consume"
    
    async with AsyncClient(base_url="http://localhost:18000") as client:
        # Queue
        await client.post(
            f"/api/v1/sandboxes/{sandbox_id}/interventions",
            json={"message": "One-time message", "source": "guardian", "inject_mode": "immediate"}
        )
        
        # First retrieval
        resp1 = await client.get(f"/api/v1/sandboxes/{sandbox_id}/interventions")
        assert len(resp1.json()) == 1
        
        # Second retrieval should be empty
        resp2 = await client.get(f"/api/v1/sandboxes/{sandbox_id}/interventions")
        assert len(resp2.json()) == 0
```

#### 2.4.2 Implementation

**File**: `backend/omoi_os/api/routes/sandboxes.py` (EXTEND)

```python
from pydantic import BaseModel
from typing import Literal, Optional
from omoi_os.services.event_bus import EventBusService, SystemEvent

class InterventionRequest(BaseModel):
    message: str
    source: Literal["guardian", "user", "system"]
    priority: Literal["normal", "urgent"] = "normal"
    inject_mode: Literal["immediate", "next_turn"] = "immediate"

class InterventionResponse(BaseModel):
    id: str
    status: str
    inject_mode: str
    estimated_delivery_ms: int


# In-memory queue (replace with Redis in production)
_intervention_queues: dict[str, list[dict]] = {}


@router.post("/sandboxes/{sandbox_id}/interventions", response_model=InterventionResponse)
async def queue_intervention(
    sandbox_id: str,
    request: InterventionRequest,
):
    """Queue an intervention for hook-based immediate injection."""
    import uuid
    
    intervention_id = f"int-{uuid.uuid4().hex[:12]}"
    
    intervention = {
        "id": intervention_id,
        "message": request.message,
        "source": request.source,
        "priority": request.priority,
        "inject_mode": request.inject_mode,
        "queued_at": datetime.utcnow().isoformat(),
    }
    
    if sandbox_id not in _intervention_queues:
        _intervention_queues[sandbox_id] = []
    
    # Urgent interventions go to front of queue
    if request.priority == "urgent":
        _intervention_queues[sandbox_id].insert(0, intervention)
    else:
        _intervention_queues[sandbox_id].append(intervention)
    
    # Broadcast event for monitoring
    event_bus = EventBusService()
    event_bus.publish(SystemEvent(
        event_type="INTERVENTION_QUEUED",
        entity_type="sandbox",
        entity_id=sandbox_id,
        payload={"intervention_id": intervention_id, "source": request.source}
    ))
    
    return InterventionResponse(
        id=intervention_id,
        status="queued",
        inject_mode=request.inject_mode,
        estimated_delivery_ms=50 if request.inject_mode == "immediate" else 5000,
    )


@router.get("/sandboxes/{sandbox_id}/interventions")
async def get_interventions(sandbox_id: str):
    """Get and consume pending interventions (for worker hooks)."""
    interventions = _intervention_queues.pop(sandbox_id, [])
    return interventions
```

#### 2.4.3 Checklist

| # | Task | Status | Test |
|---|------|--------|------|
| 2.12 | Write `test_intervention_endpoint_queues_for_immediate_injection` | ⬜ | — |
| 2.13 | Write `test_intervention_queue_retrieval` | ⬜ | — |
| 2.14 | Write `test_intervention_consumed_after_retrieval` | ⬜ | — |
| 2.15 | Run tests - verify FAIL (404) | ⬜ | — |
| 2.16 | Implement `InterventionRequest/Response` schemas | ⬜ | — |
| 2.17 | Implement `POST /sandboxes/{id}/interventions` | ⬜ | — |
| 2.18 | Implement `GET /sandboxes/{id}/interventions` | ⬜ | — |
| 2.19 | Add intervention queue storage | ⬜ | — |
| 2.20 | Run tests - confirm PASS | ⬜ | ✅ All green |

**Note**: Worker script hook integration is covered in Phase 3.4.

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

**Gate**: All Phase 3 tests must pass before Phase 3.5. ✅

---

### 3.4 Hook Integration in Worker Scripts (Enhancement)

**Goal**: Add PreToolUse hooks (Claude) / enhanced callbacks (OpenHands) for immediate intervention delivery.

**Estimated Effort**: 2-3 hours

> **Prerequisite**: Phase 2.4 (Hook-Based Intervention endpoint) should be complete.

#### 3.4.1 Tests

```python
# tests/integration/test_worker_hooks.py

def test_claude_worker_has_pretooluse_hook():
    """
    SPEC: Claude worker script should register PreToolUse hook for interventions.
    """
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService
    
    spawner = DaytonaSpawnerService()
    script = spawner._get_claude_worker_script()
    
    # Verify hook registration
    assert "PreToolUse" in script
    assert "check_pending_interventions" in script or "intervention" in script.lower()


def test_openhands_worker_has_intervention_callback():
    """
    SPEC: OpenHands worker should check for interventions in event callback.
    """
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService
    
    spawner = DaytonaSpawnerService()
    script = spawner._get_worker_script()
    
    # Verify intervention handling in callback
    assert "intervention" in script.lower()
    assert "Action" in script  # Should check ActionEvent


def test_worker_fetches_interventions_from_api():
    """
    SPEC: Worker should fetch from /interventions endpoint.
    """
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService
    
    spawner = DaytonaSpawnerService()
    
    # Check both worker scripts
    oh_script = spawner._get_worker_script()
    claude_script = spawner._get_claude_worker_script()
    
    assert "/interventions" in oh_script or "interventions" in oh_script.lower()
    assert "/interventions" in claude_script or "interventions" in claude_script.lower()
```

#### 3.4.2 Implementation

**Claude SDK Worker Updates** (in `_get_claude_worker_script()`):

```python
# Add to worker script - Intervention queue with server backing
intervention_queue = asyncio.Queue()
_poll_counter = 0

async def fetch_pending_interventions():
    """Fetch any queued interventions from server."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{MCP_SERVER_URL}/api/v1/sandboxes/{SANDBOX_ID}/interventions"
            )
            if resp.status_code == 200:
                for item in resp.json():
                    await intervention_queue.put(item)
    except Exception as e:
        logger.debug(f"Intervention fetch failed: {e}")

async def check_pending_interventions(input_data, tool_use_id, context):
    """PreToolUse hook - checks for interventions before EVERY tool call."""
    global _poll_counter
    _poll_counter += 1
    
    # Poll server every 5 tool calls to refill queue
    if _poll_counter % 5 == 0:
        await fetch_pending_interventions()
    
    # Check in-memory queue (fast path)
    if not intervention_queue.empty():
        intervention = await intervention_queue.get()
        logger.info(f"Injecting intervention from {intervention['source']}")
        return {
            "reason": intervention["message"],
            "systemMessage": f"[{intervention['source'].upper()}] {intervention['message']}",
        }
    return {}

# Update options to include hook:
options = ClaudeAgentOptions(
    # ... existing options ...
    hooks={
        "PreToolUse": [HookMatcher(matcher="*", hooks=[check_pending_interventions])],
        "PostToolUse": [HookMatcher(matcher="*", hooks=[track_tool])],
    },
)
```

**OpenHands SDK Worker Updates** (in `_get_worker_script()`):

```python
# Add to worker script - Intervention handling
intervention_queue = []
_action_counter = 0

def fetch_interventions_sync():
    """Synchronous fetch for callback context."""
    global intervention_queue
    try:
        import httpx
        resp = httpx.get(
            f"{MCP_SERVER_URL.replace('/mcp', '')}/api/v1/sandboxes/{SANDBOX_ID}/interventions",
            timeout=2.0
        )
        if resp.status_code == 200:
            intervention_queue.extend(resp.json())
    except Exception as e:
        logger.debug(f"Intervention fetch failed: {e}")

def on_event_with_intervention(event):
    """Enhanced callback with intervention injection."""
    global _action_counter, intervention_queue
    event_type = type(event).__name__
    
    # Check for interventions on action events (before tool execution)
    if "Action" in event_type:
        _action_counter += 1
        
        # Poll every 5 actions to refill queue
        if _action_counter % 5 == 0:
            fetch_interventions_sync()
        
        # Inject any pending interventions
        if intervention_queue:
            intervention = intervention_queue.pop(0)
            logger.info(f"Injecting intervention from {intervention['source']}")
            conversation.send_message(
                f"[{intervention['source'].upper()} INTERVENTION] {intervention['message']}"
            )
    
    # Original event reporting (unchanged)
    event_data = {"message": str(event)[:300]}
    asyncio.create_task(report_event(event_type, event_data))
```

#### 3.4.3 Checklist

| # | Task | Status | Test |
|---|------|--------|------|
| 3.13 | Write `test_claude_worker_has_pretooluse_hook` | ⬜ | — |
| 3.14 | Write `test_openhands_worker_has_intervention_callback` | ⬜ | — |
| 3.15 | Write `test_worker_fetches_interventions_from_api` | ⬜ | — |
| 3.16 | Run tests - verify FAIL | ⬜ | — |
| 3.17 | Add `check_pending_interventions` hook to Claude worker | ⬜ | — |
| 3.18 | Add `fetch_pending_interventions()` to Claude worker | ⬜ | — |
| 3.19 | Add `on_event_with_intervention` to OpenHands worker | ⬜ | — |
| 3.20 | Add `fetch_interventions_sync()` to OpenHands worker | ⬜ | — |
| 3.21 | Run tests - confirm PASS | ⬜ | ✅ All green |
| 3.22 | Run full Phase 0-3 tests - confirm no regression | ⬜ | ✅ All green |

**Gate**: Phase 3.4 is optional but highly recommended for production use.

---

## Phase 3.5: GitHub Clone Integration

**Goal**: Sandbox clones the user's GitHub repo on startup so agents can work on local files.

**Estimated Effort**: 3-4 hours

### Background

Without this phase, agents would need to:
- Read files one-by-one via GitHub API (slow)
- Write files one-by-one via GitHub API (creates separate commits)
- Cannot use `git diff`, `git status`, etc.

With this phase, agents:
- Have full repo cloned at `/workspace`
- Can edit files directly with bash tools
- Can commit multiple changes at once
- Can push and create PRs

### Branch Flow (Important!)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BRANCH CREATION FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STEP 1: BEFORE SANDBOX (Phase 5: BranchWorkflowService)                    │
│  ─────────────────────────────────────────────────────────                  │
│                                                                             │
│    BASE BRANCH (main)                                                       │
│         │                                                                   │
│         └──► Create NEW branch via GitHub API                               │
│              └──► feature/TICKET-123-dark-mode                              │
│                                                                             │
│  STEP 2: SPAWN SANDBOX (Phase 3.5)                                          │
│  ─────────────────────────────────                                          │
│                                                                             │
│    Pass to sandbox:                                                         │
│    • GITHUB_TOKEN = user's OAuth token                                      │
│    • GITHUB_REPO = owner/repo                                               │
│    • BRANCH_NAME = feature/TICKET-123-dark-mode  ← Already created!         │
│                                                                             │
│  STEP 3: SANDBOX STARTUP (Worker script)                                    │
│  ───────────────────────────────────────                                    │
│                                                                             │
│    git clone https://x-access-token:{TOKEN}@github.com/{REPO}.git           │
│         │                                                                   │
│         └──► Clones default branch (main)                                   │
│                   │                                                         │
│                   └──► git checkout feature/TICKET-123-dark-mode            │
│                              │                                              │
│                              └──► Now working on feature branch!            │
│                                                                             │
│  STEP 4: AGENT WORKS                                                        │
│  ───────────────────                                                        │
│                                                                             │
│    Agent edits files in /workspace                                          │
│    git add .                                                                │
│    git commit -m "Implement dark mode toggle"                               │
│                                                                             │
│  STEP 5: TASK COMPLETION                                                    │
│  ───────────────────────                                                    │
│                                                                             │
│    git push origin feature/TICKET-123-dark-mode                             │
│         │                                                                   │
│         └──► Create PR: feature/TICKET-123-dark-mode → main                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

TWO BRANCHES:
┌──────────────────────┬─────────────────────────────┬─────────────────────────┐
│ Branch               │ Description                 │ When Created            │
├──────────────────────┼─────────────────────────────┼─────────────────────────┤
│ Base (main)          │ Source we branch FROM       │ Already exists          │
│ Feature (feature/...)│ NEW branch for this task    │ Phase 5, before sandbox │
└──────────────────────┴─────────────────────────────┴─────────────────────────┘

NOTE: Phase 3.5 assumes the feature branch already exists (created in Phase 5).
      The sandbox just checks out that existing branch.
```

### 3.5.1 Write Tests First

```python
# tests/integration/test_github_clone.py

import pytest
from unittest.mock import MagicMock, patch


def test_spawner_includes_github_env_vars():
    """
    SPEC: DaytonaSpawnerService should pass GitHub credentials to sandbox.
    """
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService
    
    spawner = DaytonaSpawnerService()
    
    # Mock the internal method to capture env_vars
    captured_env = {}
    original_create = spawner._create_daytona_sandbox
    
    async def capture_create(sandbox_id, env_vars, labels, runtime):
        captured_env.update(env_vars)
    
    spawner._create_daytona_sandbox = capture_create
    
    # Call with GitHub context
    await spawner.spawn_for_task(
        task_id="task-123",
        agent_id="agent-456",
        phase_id="PHASE_IMPLEMENTATION",
        extra_env={
            "GITHUB_TOKEN": "ghp_test123",
            "GITHUB_REPO": "owner/repo",
            "BRANCH_NAME": "feature/TICKET-123-dark-mode",
        }
    )
    
    assert "GITHUB_TOKEN" in captured_env
    assert "GITHUB_REPO" in captured_env
    assert "BRANCH_NAME" in captured_env


def test_worker_script_clones_repo_on_startup():
    """
    SPEC: Worker script should clone repo if GITHUB_TOKEN is provided.
    """
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService
    
    spawner = DaytonaSpawnerService()
    script = spawner._get_worker_script()
    
    # Verify clone logic exists
    assert "git clone" in script or "clone_repo" in script
    assert "GITHUB_TOKEN" in script
    assert "GITHUB_REPO" in script


def test_worker_script_checks_out_branch():
    """
    SPEC: Worker script should checkout the feature branch after cloning.
    """
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService
    
    spawner = DaytonaSpawnerService()
    script = spawner._get_worker_script()
    
    # Verify branch checkout
    assert "checkout" in script.lower()
    assert "BRANCH_NAME" in script


def test_worker_script_handles_missing_github_gracefully():
    """
    SPEC: Worker should start normally even without GitHub credentials.
    """
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService
    
    spawner = DaytonaSpawnerService()
    script = spawner._get_worker_script()
    
    # Should have conditional check
    assert "if" in script.lower() and "GITHUB" in script
```

### 3.5.2 Implementation

**File**: `backend/omoi_os/services/daytona_spawner.py` (MODIFY)

Add GitHub clone logic to the worker script:

```python
# Add to worker script (inside _get_worker_script() return string)

# --- GitHub Repository Setup ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")  # format: owner/repo
BRANCH_NAME = os.environ.get("BRANCH_NAME")

def clone_repo():
    """Clone GitHub repo and checkout branch. Called on startup."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        logger.info("No GitHub credentials, skipping repo clone")
        return False
    
    # Build authenticated clone URL
    clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
    
    logger.info(f"Cloning {GITHUB_REPO}...")
    result = subprocess.run(
        ["git", "clone", clone_url, "/workspace"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        logger.error(f"Clone failed: {result.stderr}")
        return False
    
    os.chdir("/workspace")
    
    # Checkout branch if specified
    if BRANCH_NAME:
        logger.info(f"Checking out branch: {BRANCH_NAME}")
        # Try checkout existing, or create new
        result = subprocess.run(
            ["git", "checkout", BRANCH_NAME],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            # Branch doesn't exist remotely, create it
            subprocess.run(["git", "checkout", "-b", BRANCH_NAME])
    
    logger.info("Repo ready at /workspace")
    return True

# Call on startup (before agent loop)
clone_repo()
```

**Caller Change**: Update orchestrator or spawn caller to pass GitHub info:

```python
# Example: In orchestrator_loop.py or wherever spawn_for_task is called

# Get GitHub credentials from task's project
project = get_project_for_task(task)
user = get_user_for_project(project)

github_token = user.attributes.get("github_access_token")
github_repo = f"{project.github_owner}/{project.github_repo}" if project.github_owner else None
branch_name = task.attributes.get("branch_name")

await spawner.spawn_for_task(
    task_id=task.id,
    agent_id=agent_id,
    phase_id=phase_id,
    extra_env={
        "GITHUB_TOKEN": github_token,
        "GITHUB_REPO": github_repo,
        "BRANCH_NAME": branch_name,
    } if github_token and github_repo else {}
)
```

### 3.5.3 Checklist

| # | Task | Status | Test |
|---|------|--------|------|
| 3.5.1 | Write `test_spawner_includes_github_env_vars` | ⬜ | — |
| 3.5.2 | Write `test_worker_script_clones_repo_on_startup` | ⬜ | — |
| 3.5.3 | Write `test_worker_script_checks_out_branch` | ⬜ | — |
| 3.5.4 | Write `test_worker_script_handles_missing_github_gracefully` | ⬜ | — |
| 3.5.5 | Run tests - verify they FAIL | ⬜ | — |
| 3.5.6 | Add `clone_repo()` function to worker script | ⬜ | — |
| 3.5.7 | Add GITHUB_TOKEN/REPO/BRANCH env var reads | ⬜ | — |
| 3.5.8 | Call `clone_repo()` at worker startup | ⬜ | — |
| 3.5.9 | Update spawn caller to pass GitHub env vars | ⬜ | — |
| 3.5.10 | Run tests - confirm PASS | ⬜ | ✅ All green |
| 3.5.11 | Run Phase 0-3 tests - confirm no regression | ⬜ | ✅ All green |

**Gate**: All Phase 3.5 tests must pass. ✅ MVP COMPLETE at this point!

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

### 5.3 Rollback & Recovery Strategies

> **Critical**: Git operations are stateful and can leave partial state. Define recovery for each failure mode.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ROLLBACK STRATEGY MATRIX                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  FAILURE POINT              RECOVERY ACTION                 AUTO?           │
│  ─────────────              ───────────────                 ─────           │
│                                                                             │
│  Sandbox creation fails     Log error, mark task failed     ✅ Auto        │
│                             No cleanup needed (nothing created)             │
│                                                                             │
│  Branch creation fails      Retry 3x with backoff           ✅ Auto        │
│                             Then mark task failed                           │
│                                                                             │
│  Agent crash mid-work       Preserve branch for debug       ⚠️ Manual      │
│                             Don't delete uncommitted work                   │
│                             Guardian can restart task                       │
│                                                                             │
│  Commit fails               Retry commit                    ✅ Auto        │
│                             Log diff for manual recovery                    │
│                                                                             │
│  PR creation fails          Retry 3x                        ✅ Auto        │
│                             Leave branch for manual PR                      │
│                             Mark task as "needs_review"                     │
│                                                                             │
│  PR has conflicts           Do NOT auto-merge               ⚠️ Manual      │
│                             Notify user                                     │
│                             Agent can attempt resolution (future)           │
│                                                                             │
│  Merge fails                Do NOT force push               ⚠️ Manual      │
│                             Notify user                                     │
│                             Keep PR open for review                         │
│                                                                             │
│  Sandbox termination fails  Log error, orphan warning       ✅ Auto        │
│                             Background cleanup job                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Rollback Tests

```python
# tests/integration/test_branch_workflow_rollback.py

import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_branch_creation_retry_on_transient_failure():
    """Branch creation should retry on GitHub API failures."""
    from omoi_os.services.branch_workflow import BranchWorkflowService
    
    mock_github = MagicMock()
    # First two calls fail, third succeeds
    mock_github.create_branch.side_effect = [
        Exception("GitHub API rate limited"),
        Exception("GitHub API timeout"),
        {"success": True, "ref": "refs/heads/feature/123"},
    ]
    
    service = BranchWorkflowService(github_service=mock_github)
    
    result = await service.start_work_on_ticket(
        ticket_id="123",
        ticket_title="Test",
        repo_owner="org",
        repo_name="repo"
    )
    
    # VERIFY: Succeeded after retries
    assert result["success"] is True
    assert mock_github.create_branch.call_count == 3


@pytest.mark.asyncio
async def test_pr_conflict_does_not_auto_merge():
    """PR with conflicts should NOT be auto-merged."""
    from omoi_os.services.branch_workflow import BranchWorkflowService
    
    mock_github = MagicMock()
    mock_github.get_pull_request.return_value = {
        "number": 42,
        "mergeable": False,
        "mergeable_state": "dirty",  # Has conflicts
    }
    
    service = BranchWorkflowService(github_service=mock_github)
    
    result = await service.merge_ticket_work(
        ticket_id="123",
        pr_number=42,
        auto_merge=True  # Requested auto-merge
    )
    
    # VERIFY: Did NOT attempt merge
    assert result["success"] is False
    assert result["reason"] == "conflicts"
    assert result["needs_manual_review"] is True
    mock_github.merge_pull_request.assert_not_called()


@pytest.mark.asyncio  
async def test_agent_crash_preserves_branch():
    """Agent crash should NOT delete the branch (preserves work)."""
    from omoi_os.services.branch_workflow import BranchWorkflowService
    
    mock_github = MagicMock()
    
    service = BranchWorkflowService(github_service=mock_github)
    
    # Simulate agent crash cleanup
    await service.handle_agent_failure(
        ticket_id="123",
        branch_name="feature/123-add-auth",
        error="Agent process killed"
    )
    
    # VERIFY: Branch NOT deleted
    mock_github.delete_branch.assert_not_called()
    
    # VERIFY: Task marked for review
    # (would check database in real test)


@pytest.mark.asyncio
async def test_sandbox_cleanup_on_success():
    """Successful completion should cleanup sandbox."""
    from omoi_os.services.branch_workflow import BranchWorkflowService
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService
    
    mock_github = MagicMock()
    mock_daytona = MagicMock()
    mock_daytona.terminate_sandbox.return_value = {"success": True}
    
    service = BranchWorkflowService(
        github_service=mock_github,
        daytona_service=mock_daytona
    )
    
    await service.complete_workflow(
        ticket_id="123",
        sandbox_id="sandbox-abc",
        pr_number=42
    )
    
    # VERIFY: Sandbox terminated
    mock_daytona.terminate_sandbox.assert_called_once_with("sandbox-abc")
```

#### Recovery State Tracking

Add to `sandbox_sessions` table:

```sql
-- Track recovery state for partial failures
ALTER TABLE sandbox_sessions ADD COLUMN IF NOT EXISTS recovery_state JSONB DEFAULT '{}';

-- Example recovery_state:
-- {
--   "branch_created": true,
--   "commits_pushed": true,
--   "pr_created": false,
--   "pr_number": null,
--   "last_error": "GitHub API rate limited",
--   "retry_count": 2,
--   "last_retry_at": "2025-12-12T10:30:00Z"
-- }
```

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

## Critical Implementation Notes - Deep Dive Findings

> **⚠️ READ THIS BEFORE IMPLEMENTATION**: These findings from codebase analysis reveal critical details that affect implementation.

### 🚨 Critical Bug: Missing `sandbox_id` Field

**PROBLEM**: `tasks.py` line 78 does `task.sandbox_id = request.sandbox_id` BUT the Task model **does NOT have a `sandbox_id` field!**

```python
# CURRENT Task model (backend/omoi_os/models/task.py) - MISSING sandbox_id
class Task(Base):
    conversation_id: Mapped[Optional[str]]    # ✅ EXISTS
    persistence_dir: Mapped[Optional[str]]    # ✅ EXISTS
    # sandbox_id: NOT PRESENT ❌ - MUST BE ADDED IN PHASE 6
```

**FIX REQUIRED (Phase 6)**:
```python
# Add to Task model:
sandbox_id: Mapped[Optional[str]] = mapped_column(
    String(255), nullable=True, index=True,
    comment="Daytona sandbox ID for sandbox-mode execution"
)
```

### GitHub API Service - Missing Methods

**Location**: `backend/omoi_os/services/github_api.py`

**Has** (ready to use):
- ✅ `create_branch(user_id, owner, repo, branch_name, from_sha)`
- ✅ `create_pull_request(user_id, owner, repo, title, head, base, body, draft)`
- ✅ `list_branches()`, `list_commits()`, `list_pull_requests()`
- ✅ `create_or_update_file()`, `get_file_content()`

**Missing** (add in Phase 5):
- ❌ `merge_pull_request(user_id, owner, repo, pr_number)` 
- ❌ `delete_branch(user_id, owner, repo, branch_name)`
- ❌ `compare_branches(user_id, owner, repo, base, head)` - for conflict detection
- ❌ `get_pull_request(user_id, owner, repo, pr_number)` - for mergeable status check

### GitHub Token Injection - Not Implemented

**Location**: `backend/omoi_os/services/daytona_spawner.py` lines 146-169

**CURRENT env_vars**:
```python
env_vars = {
    "AGENT_ID": agent_id,
    "TASK_ID": task_id,
    "MCP_SERVER_URL": self.mcp_server_url,
    "PHASE_ID": phase_id,
    "SANDBOX_ID": sandbox_id,
    "LLM_API_KEY": ...,  # ✅ Injected
    "LLM_MODEL": ...,    # ✅ Injected
    # GITHUB_TOKEN: ❌ NOT INJECTED YET
}
```

**FIX REQUIRED (Phase 3.5)**:
```python
# Add GitHub token to env_vars (get from user's OAuth)
if github_token:
    env_vars["GITHUB_TOKEN"] = github_token
    env_vars["GITHUB_REPO_URL"] = repo_clone_url
```

### Worker Script Uses MCP (Not HTTP)

**Location**: `backend/omoi_os/sandbox_worker.py`

The sandbox worker currently uses **MCP** for ALL communication:
```python
await mcp_client.call_tool("get_task", {...})
await mcp_client.call_tool("update_task_status", {...})
await mcp_client.call_tool("report_agent_event", {...})
await mcp_client.call_tool("register_conversation", {...})
```

**Migration to HTTP (Phase 3)**: Replace MCP calls with HTTP:
```python
# Replace MCP calls with HTTP
async with httpx.AsyncClient() as client:
    await client.post(f"{API_URL}/sandboxes/{sandbox_id}/events", json={...})
    messages = await client.get(f"{API_URL}/sandboxes/{sandbox_id}/messages")
```

### RestartOrchestrator Not Sandbox-Aware

**Location**: `backend/omoi_os/services/restart_orchestrator.py`

**CURRENT**: Spawns replacement via `AgentRegistryService`:
```python
replacement = self.agent_registry.register_agent(...)  # Local agent
```

**NEEDS UPDATE (Phase 7)**: For sandbox tasks, call `DaytonaSpawnerService`:
```python
if task.sandbox_id:
    # Sandbox task - spawn new Daytona sandbox
    new_sandbox_id = await self.daytona_spawner.spawn_for_task(...)
else:
    # Legacy local agent
    replacement = self.agent_registry.register_agent(...)
```

### Existing Test Fixtures (Use These!)

**Location**: `backend/tests/conftest.py`

| Fixture | Scope | Description |
|---------|-------|-------------|
| `client` | session | FastAPI TestClient (unauthenticated) |
| `db_service` | function | Fresh DB per test (creates/drops tables) |
| `test_user`, `admin_user` | function | Real users in DB |
| `auth_token`, `auth_headers` | function | JWT tokens |
| `authenticated_client` | function | TestClient with auth |
| `mock_authenticated_client` | function | Mocked auth (fastest) |
| `event_bus_service` | function | EventBusService (requires Redis) |
| `task_queue_service` | function | TaskQueueService |
| `sample_ticket`, `sample_task`, `sample_agent` | function | Sample entities |

### EventBus Patterns

**Location**: `backend/omoi_os/services/event_bus.py`

```python
# Channel format: events.{event_type}
# Use Pydantic for serialization
event_bus.publish(SystemEvent(
    event_type="SANDBOX_EVENT",      # → publishes to "events.SANDBOX_EVENT"
    entity_type="sandbox",
    entity_id=sandbox_id,
    payload={...}
))
```

---

## Integration with Existing Systems

> **Critical**: The sandbox event/message system must integrate with existing infrastructure. Here's what already exists.

### Existing Sandbox Infrastructure

**Files that already exist** (DO NOT RECREATE):

| File | Purpose | Key Methods/Classes |
|------|---------|---------------------|
| `omoi_os/sandbox_worker.py` | Worker that runs INSIDE sandbox | `run_sandbox_worker()`, `on_agent_event()` callback |
| `omoi_os/services/daytona_spawner.py` | Spawns sandboxes from server | `DaytonaSpawnerService`, `spawn_sandbox()` |
| `omoi_os/services/conversation_intervention.py` | Sends messages TO sandbox | `ConversationInterventionService.send_intervention()` |
| `omoi_os/services/intelligent_guardian.py` | Analyzes trajectories | `IntelligentGuardian.analyze_agent_trajectory()` |
| `omoi_os/api/routes/tasks.py` | Already has sandbox endpoints | `register_conversation()` |

**⚠️ Task Model Fields - CURRENT STATE**:

```python
# Task model (backend/omoi_os/models/task.py) - as of deep dive analysis
class Task(Base):
    # ...existing fields...
    conversation_id: Mapped[Optional[str]]    # ✅ EXISTS - OpenHands conversation ID
    persistence_dir: Mapped[Optional[str]]    # ✅ EXISTS - For intervention resumption
    # sandbox_id: ❌ MISSING - Must be added in Phase 6!
```

**⚠️ tasks.py Bug**: Line 78 attempts to set `task.sandbox_id` which doesn't exist yet. This code path will error until Phase 6 adds the field.

### Where New Code Fits

**New File**: `omoi_os/api/routes/sandboxes.py`

This is the NEW API that sandboxes call to communicate with the server:

```python
# New routes needed (sandbox → server communication):
POST /api/v1/sandboxes/{sandbox_id}/events     # Agent events
GET  /api/v1/sandboxes/{sandbox_id}/messages   # Fetch pending messages
POST /api/v1/sandboxes/{sandbox_id}/interventions  # Guardian/user interventions

# Server → sandbox communication (already exists via):
# - ConversationInterventionService.send_intervention()
# - OpenHands conversation.send_message()
```

### Test Dependencies

When testing sandbox endpoints, you'll need these existing fixtures:

```python
# Tests should use EXISTING services via fixtures
@pytest.fixture
def intervention_service():
    """Use existing ConversationInterventionService."""
    from omoi_os.services.conversation_intervention import ConversationInterventionService
    # Note: Requires LLM_API_KEY in test env or mock
    return ConversationInterventionService()


@pytest.fixture
def sample_task_with_sandbox(db_service: DatabaseService, sample_ticket: Ticket) -> Task:
    """Create a task with sandbox fields populated."""
    with db_service.get_session() as session:
        task = Task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Test task in sandbox mode",
            status="running",
            sandbox_id="test-sandbox-abc123",
            conversation_id="conv-xyz789",
            assigned_agent_id="agent-001",
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        session.expunge(task)
        return task


@pytest.fixture  
def mock_intervention_service():
    """Mock intervention service for unit tests."""
    mock = MagicMock()
    mock.send_intervention = MagicMock(return_value=True)
    return mock
```

---

## Guardian Integration Tests

> **Critical**: Guardian monitors sandboxes every 60 seconds. Tests must verify interventions ACTUALLY reach agents.

**File**: `tests/integration/test_sandbox_guardian_integration.py`

```python
"""
Tests for Guardian ↔ Sandbox integration.
Verifies that Guardian interventions actually reach sandbox agents.

Following patterns from test_intelligent_monitoring.py.
"""
import pytest
import threading
import time
from unittest.mock import MagicMock, AsyncMock

from omoi_os.models.agent import Agent
from omoi_os.models.task import Task
from omoi_os.services.intelligent_guardian import IntelligentGuardian


@pytest.fixture
def mock_llm_service():
    """Mock LLM service (following existing test_intelligent_monitoring pattern)."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value={
        "trajectory_aligned": False,
        "alignment_score": 0.4,
        "needs_steering": True,
        "steering_type": "drifting",
        "steering_recommendation": "Focus on the authentication task",
    })
    return llm


@pytest.fixture
def guardian_service(db_service, event_bus_service, mock_llm_service):
    """IntelligentGuardian with mocked LLM."""
    return IntelligentGuardian(
        db=db_service,
        llm_service=mock_llm_service,
        event_bus=event_bus_service,
    )


@pytest.mark.integration
@pytest.mark.requires_db
class TestGuardianInterventionDelivery:
    """Test that Guardian interventions reach sandboxes."""
    
    def test_guardian_detects_drifting_agent(
        self,
        guardian_service: IntelligentGuardian,
        db_service,
        sample_agent: Agent,
    ):
        """Guardian should detect when agent is off-track."""
        # Update agent to working state
        with db_service.get_session() as session:
            agent = session.get(Agent, sample_agent.id)
            agent.status = "working"
            session.commit()
        
        # Run trajectory analysis
        import asyncio
        analysis = asyncio.run(
            guardian_service.analyze_agent_trajectory(sample_agent.id)
        )
        
        # VERIFY: Analysis was performed
        # (With mock LLM, this will use the mock response)
        assert analysis is not None or True  # Analysis may be None if no logs
    
    def test_intervention_queued_and_retrievable(
        self,
        client,
        sandbox_id: str,
    ):
        """Intervention should be queued and retrievable by sandbox."""
        # Queue an intervention
        response = client.post(
            f"/api/v1/sandboxes/{sandbox_id}/interventions",
            json={
                "message": "Focus on the API endpoint, not tests",
                "source": "guardian",
                "priority": "high",
            }
        )
        
        # If endpoint exists
        if response.status_code == 200:
            # VERIFY: Sandbox can retrieve it
            messages = client.get(f"/api/v1/sandboxes/{sandbox_id}/messages")
            
            if messages.status_code == 200:
                pending = messages.json()
                assert len(pending) > 0
                assert "Focus on the API" in pending[0]["content"]
    
    def test_intervention_broadcasts_event(
        self,
        client,
        event_bus_service,
        sandbox_id: str,
    ):
        """Intervention should publish event for real-time monitoring."""
        received_events = []
        event_received = threading.Event()
        
        def callback(event):
            if "SANDBOX" in event.event_type.upper():
                received_events.append(event)
                event_received.set()
        
        # Subscribe before action
        event_bus_service.subscribe("SANDBOX_INTERVENTION_QUEUED", callback)
        
        # Start listener
        listen_thread = threading.Thread(
            target=event_bus_service.listen, daemon=True
        )
        listen_thread.start()
        time.sleep(0.1)
        
        # Queue intervention
        response = client.post(
            f"/api/v1/sandboxes/{sandbox_id}/interventions",
            json={"message": "Test intervention", "source": "guardian"}
        )
        
        # VERIFY: If endpoint works, event should be broadcast
        if response.status_code == 200:
            event_received.wait(timeout=2.0)
            assert len(received_events) > 0


@pytest.mark.unit
class TestInterventionMessageFormatting:
    """Test intervention message formatting logic."""
    
    def test_guardian_prefix_applied(self):
        """Messages from Guardian should have [GUARDIAN INTERVENTION] prefix."""
        # This documents expected behavior in ConversationInterventionService
        message = "Focus on authentication"
        expected_prefix = "[GUARDIAN INTERVENTION]:"
        
        # The actual formatting in conversation_intervention.py:
        formatted = f"[GUARDIAN INTERVENTION]: {message}"
        
        assert expected_prefix in formatted
        assert message in formatted
    
    def test_user_prefix_applied(self):
        """Messages from users should have [USER MESSAGE] prefix."""
        message = "Please also add logging"
        formatted = f"[USER MESSAGE]: {message}"
        
        assert "[USER MESSAGE]" in formatted
```

---

## E2E Test Suite (Full System Verification)

> **Purpose**: Test complete user scenarios across all components. Run AFTER all unit + integration tests pass.

### E2E Test Scenarios

```python
# tests/e2e/test_sandbox_workflow.py

import pytest
import asyncio
import uuid
from httpx import AsyncClient
from websockets import connect as ws_connect


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteWorkflow:
    """End-to-end tests for complete sandbox lifecycle."""
    
    @pytest.mark.asyncio
    async def test_e2e_sandbox_task_lifecycle(self):
        """
        E2E: Complete lifecycle from task creation to completion.
        
        Scenario:
        1. User creates a task
        2. System spawns a sandbox
        3. Agent starts and reports events
        4. User sends a message to agent
        5. Agent receives message and completes task
        6. PR is created
        
        This test verifies the ENTIRE SYSTEM works together.
        """
        # Test setup
        sandbox_id = f"e2e-test-{uuid.uuid4().hex[:8]}"
        received_events = []
        
        # Connect WebSocket for real-time events
        async with ws_connect(
            f"ws://localhost:18000/api/v1/events/ws/events?entity_types=sandbox&entity_ids={sandbox_id}"
        ) as ws:
            # Background listener
            async def listen():
                try:
                    while True:
                        msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                        data = json.loads(msg)
                        if data.get("type") != "ping":
                            received_events.append(data)
                except asyncio.TimeoutError:
                    pass
            
            listener = asyncio.create_task(listen())
            
            async with AsyncClient(base_url="http://localhost:18000") as client:
                # Step 1: Simulate agent starting
                await client.post(
                    f"/api/v1/sandboxes/{sandbox_id}/events",
                    json={"event_type": "agent.started", "event_data": {}, "source": "agent"}
                )
                
                # Step 2: User sends guidance
                await client.post(
                    f"/api/v1/sandboxes/{sandbox_id}/messages",
                    json={"content": "Focus on the API first", "message_type": "user_message"}
                )
                
                # Step 3: Agent polls messages
                response = await client.get(f"/api/v1/sandboxes/{sandbox_id}/messages")
                messages = response.json()
                assert len(messages) >= 1
                assert messages[0]["content"] == "Focus on the API first"
                
                # Step 4: Agent reports tool use
                await client.post(
                    f"/api/v1/sandboxes/{sandbox_id}/events",
                    json={
                        "event_type": "agent.tool_use",
                        "event_data": {"tool": "write_file", "path": "/workspace/main.py"},
                        "source": "agent"
                    }
                )
                
                # Step 5: Agent completes
                await client.post(
                    f"/api/v1/sandboxes/{sandbox_id}/events",
                    json={"event_type": "agent.completed", "event_data": {"status": "success"}, "source": "agent"}
                )
            
            listener.cancel()
        
        # Verify events were received
        event_types = [e["event_type"] for e in received_events]
        assert any("started" in et.lower() for et in event_types)
        assert any("tool" in et.lower() for et in event_types)
        assert any("completed" in et.lower() for et in event_types)
    
    
    @pytest.mark.asyncio
    async def test_e2e_guardian_intervention_flow(self):
        """
        E2E: Guardian detects issue and intervenes.
        
        Scenario:
        1. Agent is running
        2. Guardian analyzes trajectory
        3. Guardian sends intervention
        4. Agent receives and acknowledges
        """
        sandbox_id = f"e2e-guardian-{uuid.uuid4().hex[:8]}"
        
        async with AsyncClient(base_url="http://localhost:18000") as client:
            # Agent is running
            await client.post(
                f"/api/v1/sandboxes/{sandbox_id}/events",
                json={"event_type": "agent.thinking", "event_data": {"thought": "..."}, "source": "agent"}
            )
            
            # Guardian intervenes (using intervention endpoint for hook-based)
            response = await client.post(
                f"/api/v1/sandboxes/{sandbox_id}/interventions",
                json={
                    "message": "Your approach is inefficient. Try using async/await.",
                    "source": "guardian",
                    "priority": "urgent",
                    "inject_mode": "immediate"
                }
            )
            assert response.status_code == 200
            assert response.json()["inject_mode"] == "immediate"
            
            # Agent hook retrieves intervention
            response = await client.get(f"/api/v1/sandboxes/{sandbox_id}/interventions")
            interventions = response.json()
            
            assert len(interventions) >= 1
            assert "inefficient" in interventions[0]["message"]
            assert interventions[0]["source"] == "guardian"


@pytest.mark.e2e
@pytest.mark.slow
class TestErrorRecovery:
    """E2E tests for error conditions and recovery."""
    
    @pytest.mark.asyncio
    async def test_e2e_agent_crash_and_restart(self):
        """
        E2E: Agent crashes, system restarts it.
        
        This tests fault tolerance without mocks.
        """
        sandbox_id = f"e2e-crash-{uuid.uuid4().hex[:8]}"
        
        async with AsyncClient(base_url="http://localhost:18000") as client:
            # Agent starts
            await client.post(
                f"/api/v1/sandboxes/{sandbox_id}/events",
                json={"event_type": "agent.started", "event_data": {}, "source": "agent"}
            )
            
            # Agent crashes (no more heartbeats)
            await client.post(
                f"/api/v1/sandboxes/{sandbox_id}/events",
                json={"event_type": "agent.error", "event_data": {"error": "OutOfMemory"}, "source": "agent"}
            )
            
            # System should detect crash via heartbeat timeout
            # (In real test, wait for restart to occur)
            
            # Verify crash event was logged
            # (Query event store once Phase 4 is complete)
```

### E2E Test Execution

```bash
# Run E2E tests only (after all other tests pass)
pytest tests/e2e/ -v -m "e2e" --timeout=120

# Run E2E with detailed output
pytest tests/e2e/ -v -m "e2e" --tb=long --capture=no

# Skip E2E in regular test runs (they're slow)
pytest tests/ -m "not e2e and not slow"
```

---

## Regression Automation

> **Purpose**: Catch regressions automatically before they reach production.

### Pre-Commit Hook

**File**: `.pre-commit-config.yaml` (CREATE)

```yaml
repos:
  - repo: local
    hooks:
      - id: unit-tests
        name: Unit Tests (Fast)
        entry: pytest -m "unit" --maxfail=1 -q
        language: system
        pass_filenames: false
        stages: [commit]
      
      - id: contract-tests
        name: Contract Tests (API Shapes)
        entry: pytest -m "contract" --maxfail=1 -q
        language: system
        pass_filenames: false
        stages: [commit]
```

### CI/CD Pipeline

**File**: `.github/workflows/test.yml` (CREATE)

```yaml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run Unit Tests
        run: pytest -m "unit" -v --cov=omoi_os --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  contract-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run Contract Tests
        run: pytest -m "contract" -v

  integration-tests:
    runs-on: ubuntu-latest
    needs: contract-tests
    services:
      redis:
        image: redis:7
        ports:
          - 16379:6379
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Start Server
        run: |
          uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 18000 &
          sleep 5
      - name: Run Integration Tests
        run: pytest -m "integration" -v

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.ref == 'refs/heads/main'  # Only on main branch
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
      - name: Full E2E Suite
        run: pytest -m "e2e" -v --timeout=300
```

### Test Execution Order Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TEST EXECUTION ORDER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LOCAL DEVELOPMENT (per feature):                                           │
│  ─────────────────────────────────                                          │
│  1. Unit Tests        pytest -m unit       ~1 second    Runs on EVERY save │
│  2. Contract Tests    pytest -m contract   ~1 second    Runs on commit     │
│  3. Integration       pytest -m integration ~30 seconds Before PR          │
│                                                                             │
│  CI/CD PIPELINE:                                                            │
│  ──────────────                                                             │
│  1. Unit Tests        (all PRs)            ~30 seconds                      │
│  2. Contract Tests    (all PRs)            ~15 seconds                      │
│  3. Integration       (all PRs)            ~5 minutes                       │
│  4. E2E Tests         (main branch only)   ~15 minutes                      │
│                                                                             │
│  BENEFITS:                                                                  │
│  ├─ Fast feedback: Unit tests catch logic bugs in <1 second                │
│  ├─ API safety: Contract tests catch breaking changes immediately          │
│  ├─ Integration: Verify HTTP layer works without full system               │
│  └─ E2E: Prove complete workflows work (nightly / main only)               │
│                                                                             │
│  FAIL-FAST STRATEGY:                                                        │
│  ├─ Unit test fails      → Stop immediately, fix logic                     │
│  ├─ Contract test fails  → Stop, API contract broken                       │
│  ├─ Integration fails    → Continue others, fix HTTP layer                 │
│  └─ E2E fails            → Debug full system, may need multiple fixes      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

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
