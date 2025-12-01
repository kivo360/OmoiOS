# Testing Sandboxes: Extending Your Daytona Integration

## Executive Summary

This report outlines how to **test sending out sandboxes** by extending your existing **Daytona integration** in `omoi_os/workspace/daytona.py`. Since you already have:
- `DaytonaWorkspace` - Core wrapper around Daytona SDK
- `OpenHandsDaytonaWorkspace` - OpenHands SDK-compatible adapter
- `OpenHandsWorkspaceFactory` - Supports `daytona` mode

The goal is to create a **lightweight test harness** that bypasses the worker polling loop and directly spawns sandboxes for testing.

---

## Current Architecture

Your current setup:
```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────────────┐
│  Task Queue │ ──▶ │    Worker    │ ──▶ │     AgentExecutor           │
│  (polling)  │     │  worker.py   │     │  ↓                          │
└─────────────┘     └──────────────┘     │  OpenHandsWorkspaceFactory  │
                                         │  ↓                          │
                                         │  OpenHandsDaytonaWorkspace  │
                                         │  ↓                          │
                                         │  Daytona Cloud Sandbox      │
                                         └─────────────────────────────┘
```

Key components:
1. **`worker.py`** - Polls task queue, calls `AgentExecutor`
2. **`AgentExecutor`** - Wraps OpenHands `Agent` + `Conversation`
3. **`OpenHandsWorkspaceFactory`** - Creates workspace based on `WORKSPACE_MODE`
4. **`OpenHandsDaytonaWorkspace`** - Implements OpenHands workspace interface over Daytona
5. **`DaytonaWorkspace`** - Direct Daytona SDK wrapper

---

## Proposed: Direct Sandbox Testing (Bypass Worker)

### Why Skip the Worker?

For testing, you want:
- **Fast iteration** - No polling delay
- **Isolation** - Test sandbox creation independently
- **Visibility** - Direct access to sandbox output
- **Control** - Programmatic start/stop

### Architecture for Testing

```
┌─────────────────────────────────────────────────────────────────┐
│                    Test Harness                                 │
│  ┌───────────────┐     ┌─────────────────────────────────────┐  │
│  │  Test Script  │ ──▶ │  SandboxTestExecutor                │  │
│  │  (pytest)     │     │  ↓                                  │  │
│  └───────────────┘     │  OpenHandsDaytonaWorkspace          │  │
│                        │  ↓                                  │  │
│                        │  DaytonaWorkspace (sandbox.process) │  │
│                        │  ↓                                  │  │
│                        │  Daytona Cloud                      │  │
│                        └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Options

### Option 1: Direct Agent Server (Simplest)

Start the OpenHands agent server and send tasks via REST API.

```bash
# Start agent server
uv run python -m openhands.agent_server --host localhost --port 8000

# Or with auto-reload for development
uv run python -m openhands.agent_server --reload
```

**Test script:**

```python
# tests/test_agent_server_sandbox.py
import requests
import os

AGENT_SERVER_URL = "http://localhost:8000"

def test_sandbox_via_agent_server():
    """Test sending a task to the agent server."""
    
    # Create a new conversation with initial task
    response = requests.post(
        f"{AGENT_SERVER_URL}/api/conversations",
        json={
            "agent": {
                "discriminator": "Agent",
                "llm": {
                    "model": "openhands/claude-sonnet-4-5-20250929",
                    "api_key": os.getenv("LLM_API_KEY"),
                },
                "tools": [
                    {"name": "TerminalTool"},
                    {"name": "FileEditorTool"},
                ],
            },
            "workspace": {
                "working_dir": "/tmp/test_sandbox",
            },
            "initial_message": {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Create a file called hello.txt with 'Hello World'"}
                ],
                "run": True,  # Auto-run after sending
            },
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    conversation_id = data["conversation_id"]
    print(f"Created conversation: {conversation_id}")
    
    # Check conversation state
    state_response = requests.get(
        f"{AGENT_SERVER_URL}/api/conversations/{conversation_id}"
    )
    print(f"State: {state_response.json()}")
    
    return conversation_id
```

### Option 2: Remote Workspace Integration

Use `RemoteWorkspace` to connect your existing `AgentExecutor` to a running agent server.

```python
# omoi_os/services/agent_executor_remote.py
from openhands.sdk import LLM, Agent, Conversation
from openhands.sdk.workspace import RemoteWorkspace

class RemoteAgentExecutor:
    """Execute tasks via remote OpenHands agent server."""
    
    def __init__(
        self,
        phase_id: str,
        agent_server_url: str = "http://localhost:8000",
        api_key: str | None = None,
    ):
        self.phase_id = phase_id
        self.agent_server_url = agent_server_url
        self.api_key = api_key
        
    def execute_task(self, task_description: str) -> dict:
        """Execute task on remote agent server."""
        from omoi_os.config import load_llm_settings
        
        llm_settings = load_llm_settings()
        llm = LLM(
            model=llm_settings.model,
            api_key=llm_settings.api_key,
            base_url=llm_settings.base_url,
        )
        
        # Create agent with your tools
        from openhands.tools.preset.default import get_default_agent
        agent = get_default_agent(llm=llm, cli_mode=True)
        
        # Connect to remote workspace (agent server)
        workspace = RemoteWorkspace(
            host=self.agent_server_url,
            api_key=self.api_key,
        )
        
        # Create conversation on remote server
        conversation = Conversation(
            agent=agent,
            workspace=workspace,
        )
        
        try:
            conversation.send_message(task_description)
            conversation.run()
            
            return {
                "status": str(conversation.state.execution_status),
                "event_count": len(conversation.state.events),
                "conversation_id": str(conversation.state.id),
            }
        finally:
            conversation.close()
```

### Option 3: Docker Workspace with Agent Server

For fully isolated sandboxes, combine Docker workspaces with the agent server.

```python
# omoi_os/services/sandbox_executor.py
from openhands.workspace.docker import DockerWorkspace
from openhands.sdk import LLM, Conversation
from openhands.tools.preset.default import get_default_agent

class SandboxExecutor:
    """Execute tasks in Docker sandboxes."""
    
    def __init__(self, docker_image: str = "python:3.12-slim"):
        self.docker_image = docker_image
        
    def execute_in_sandbox(
        self,
        task_description: str,
        workspace_dir: str,
        timeout: int = 300,
    ) -> dict:
        """Execute task in isolated Docker container."""
        from omoi_os.config import load_llm_settings
        
        llm_settings = load_llm_settings()
        llm = LLM(
            model=llm_settings.model,
            api_key=llm_settings.api_key,
        )
        
        agent = get_default_agent(llm=llm, cli_mode=True)
        
        # Create Docker workspace - isolated container
        workspace = DockerWorkspace(
            base_image=self.docker_image,
            mount_dir=workspace_dir,
            working_dir="/workspace",
        )
        
        conversation = Conversation(
            agent=agent,
            workspace=workspace,
        )
        
        try:
            # Test workspace connectivity
            result = workspace.execute_command("pwd")
            print(f"Sandbox working directory: {result.stdout}")
            
            conversation.send_message(task_description)
            conversation.run()
            
            return {
                "status": str(conversation.state.execution_status),
                "event_count": len(conversation.state.events),
                "cost": conversation.conversation_stats.get_combined_metrics().accumulated_cost,
            }
        finally:
            conversation.close()
            workspace.close()  # Cleanup container
```

---

## Testing Strategy

### 1. Unit Tests (No Agent Server)

Test sandbox creation without full execution:

```python
# tests/test_sandbox_creation.py
import pytest
from openhands.sdk.workspace import LocalWorkspace

def test_local_workspace_creation():
    """Test creating a local workspace."""
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = LocalWorkspace(working_dir=tmpdir)
        result = workspace.execute_command("echo 'hello'")
        assert result.exit_code == 0
        assert "hello" in result.stdout

@pytest.mark.skipif(
    not _docker_available(),
    reason="Docker not available"
)
def test_docker_workspace_creation():
    """Test creating a Docker workspace."""
    from openhands.workspace.docker import DockerWorkspace
    
    workspace = DockerWorkspace(
        base_image="python:3.12-slim",
        mount_dir="/tmp/test_mount",
        working_dir="/workspace",
    )
    
    try:
        result = workspace.execute_command("python --version")
        assert result.exit_code == 0
        assert "Python 3.12" in result.stdout
    finally:
        workspace.close()
```

### 2. Integration Tests (With Agent Server)

```python
# tests/integration/test_agent_server.py
import pytest
import subprocess
import time
import requests

@pytest.fixture(scope="module")
def agent_server():
    """Start agent server for integration tests."""
    proc = subprocess.Popen(
        ["uv", "run", "python", "-m", "openhands.agent_server", "--port", "8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Wait for server to start
    for _ in range(30):
        try:
            requests.get("http://localhost:8765/health")
            break
        except requests.ConnectionError:
            time.sleep(0.5)
    
    yield "http://localhost:8765"
    
    proc.terminate()
    proc.wait()

def test_conversation_lifecycle(agent_server):
    """Test full conversation lifecycle via agent server."""
    import os
    
    # Create conversation
    response = requests.post(
        f"{agent_server}/api/conversations",
        json={
            "agent": {
                "discriminator": "Agent",
                "llm": {
                    "model": os.getenv("LLM_MODEL", "openhands/claude-sonnet-4-5-20250929"),
                    "api_key": os.getenv("LLM_API_KEY"),
                },
                "tools": [{"name": "TerminalTool"}],
            },
            "workspace": {"working_dir": "/tmp/agent_test"},
        },
    )
    
    assert response.status_code == 200
    conv_id = response.json()["conversation_id"]
    
    # Send message
    requests.post(
        f"{agent_server}/api/conversations/{conv_id}/events",
        json={
            "role": "user",
            "content": [{"type": "text", "text": "echo 'test'"}],
            "run": True,
        },
    )
    
    # Wait and check state
    time.sleep(5)
    state = requests.get(f"{agent_server}/api/conversations/{conv_id}").json()
    
    assert state["execution_status"] in ["completed", "running"]
    
    # Cleanup
    requests.delete(f"{agent_server}/api/conversations/{conv_id}")
```

### 3. WebSocket Event Streaming Test

```python
# tests/integration/test_websocket_events.py
import asyncio
import websockets
import json

async def test_websocket_streaming(agent_server_url: str, conversation_id: str):
    """Test real-time event streaming via WebSocket."""
    ws_url = agent_server_url.replace("http://", "ws://")
    
    async with websockets.connect(
        f"{ws_url}/conversations/{conversation_id}/events/socket"
    ) as ws:
        # Receive events
        events = []
        try:
            async for message in asyncio.wait_for(
                ws_receive_all(ws), timeout=30
            ):
                event = json.loads(message)
                events.append(event)
                print(f"Event: {event.get('type', 'unknown')}")
        except asyncio.TimeoutError:
            pass
        
        return events

async def ws_receive_all(ws):
    while True:
        yield await ws.recv()
```

---

## Configuration

### Environment Variables

Add to `.env.local`:

```bash
# Agent Server Configuration
AGENT_SERVER_HOST=localhost
AGENT_SERVER_PORT=8000
AGENT_SERVER_API_KEY=your-secret-key  # Optional

# Workspace Mode (local, docker, remote, daytona)
WORKSPACE_MODE=local

# Docker Workspace (if using docker mode)
WORKSPACE_DOCKER_SERVER_IMAGE=ghcr.io/openhands/runtime:0.41-nikolaik
WORKSPACE_DOCKER_BASE_IMAGE=python:3.12-slim

# Remote Workspace (if using agent server mode)
WORKSPACE_REMOTE_HOST=http://localhost:8000
WORKSPACE_REMOTE_API_KEY=your-api-key
```

### Agent Server Config File

Create `config/agent_server.json`:

```json
{
  "session_api_key": "your-secret-api-key",
  "allow_cors_origins": ["http://localhost:3000"],
  "conversations_path": "workspaces/conversations",
  "webhooks": [
    {
      "webhook_url": "http://localhost:18000/webhooks/agent-events",
      "method": "POST",
      "event_buffer_size": 10,
      "num_retries": 3,
      "retry_delay": 5
    }
  ]
}
```

---

## Migration Path

### Phase 1: Parallel Testing
1. Keep existing worker running
2. Start agent server on different port (8000)
3. Create test scripts that send tasks to agent server
4. Compare results with worker-based execution

### Phase 2: Integration
1. Add `RemoteAgentExecutor` class
2. Update `AgentExecutor.create_for_project()` to support `remote` mode
3. Add webhook endpoint to receive agent events

### Phase 3: Full Migration (Optional)
1. Replace worker polling with agent server
2. Use agent server's built-in persistence
3. Leverage WebSocket for real-time updates

---

## Quick Start Commands

```bash
# 1. Start agent server (in one terminal)
cd /Users/kevinhill/Coding/Experiments/senior-sandbox/senior_sandbox/backend
uv run python -m openhands.agent_server --port 8000 --reload

# 2. Run test (in another terminal)
cd /Users/kevinhill/Coding/Experiments/senior-sandbox/senior_sandbox/backend
uv run pytest tests/integration/test_agent_server.py -v

# 3. Manual test via curl
curl -X POST http://localhost:8000/api/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "agent": {
      "discriminator": "Agent",
      "llm": {"model": "your-model", "api_key": "your-key"},
      "tools": [{"name": "TerminalTool"}]
    },
    "workspace": {"working_dir": "/tmp/sandbox"},
    "initial_message": {
      "role": "user",
      "content": [{"type": "text", "text": "echo hello"}],
      "run": true
    }
  }'
```

---

## Benefits of Agent Server Approach

1. **REST API** - Easy to test with curl/Postman
2. **WebSocket** - Real-time event streaming for UI
3. **Persistence** - Built-in conversation storage
4. **Webhooks** - Push events to your backend
5. **Isolation** - Docker/Daytona sandboxes supported
6. **No Polling** - Event-driven instead of polling

---

## Files to Create/Modify

1. `omoi_os/services/agent_executor_remote.py` - Remote executor
2. `omoi_os/services/sandbox_executor.py` - Docker sandbox executor
3. `tests/integration/test_agent_server.py` - Integration tests
4. `config/agent_server.json` - Server configuration
5. `scripts/start_agent_server.sh` - Startup script

---

## References

- [OpenHands Agent Server Docs](https://docs.openhands.dev/sdk/guides/agent-server/local-server)
- [OpenHands SDK GitHub](https://github.com/OpenHands/software-agent-sdk)
- Your existing code: `omoi_os/services/workspace_manager.py`
