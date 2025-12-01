# Testing Sandboxes: Extending Your Daytona Integration

## Executive Summary

This report outlines how to **test sending out sandboxes** by extending your existing **Daytona integration**. You already have:
- `DaytonaWorkspace` - Core wrapper around Daytona SDK
- `OpenHandsDaytonaWorkspace` - OpenHands SDK-compatible adapter
- `OpenHandsWorkspaceFactory` - Supports `daytona` mode

The goal: Create a **lightweight test harness** that bypasses the worker polling and directly spawns sandboxes.

---

## Current Architecture

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

**Key files:**
- `omoi_os/workspace/daytona.py` - DaytonaWorkspace, OpenHandsDaytonaWorkspace
- `omoi_os/services/workspace_manager.py` - OpenHandsWorkspaceFactory
- `omoi_os/services/agent_executor.py` - AgentExecutor
- `omoi_os/worker.py` - Worker polling loop

---

## Option 1: Direct Sandbox Test Harness

Bypass the worker entirely and directly use `OpenHandsDaytonaWorkspace` with OpenHands SDK.

### Implementation

```python
# omoi_os/testing/sandbox_test_executor.py
"""Test harness for sandbox execution without worker."""

import os
from typing import Optional
from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

from omoi_os.config import load_daytona_settings, load_llm_settings
from omoi_os.workspace.daytona import OpenHandsDaytonaWorkspace


class SandboxTestExecutor:
    """Execute tasks directly in Daytona sandboxes for testing.
    
    Bypasses worker polling - use for testing/development.
    
    Usage:
        executor = SandboxTestExecutor(project_id="test-123")
        result = executor.execute("Create a hello.py file that prints 'Hello World'")
        print(result)
    """
    
    def __init__(
        self,
        project_id: str,
        planning_mode: bool = False,
        custom_tools: list[Tool] | None = None,
    ):
        self.project_id = project_id
        self.planning_mode = planning_mode
        self.custom_tools = custom_tools
        self._workspace: Optional[OpenHandsDaytonaWorkspace] = None
        
    def _create_workspace(self) -> OpenHandsDaytonaWorkspace:
        """Create Daytona workspace."""
        settings = load_daytona_settings()
        return OpenHandsDaytonaWorkspace(
            working_dir=f"/tmp/sandbox-{self.project_id}",
            project_id=self.project_id,
            settings=settings,
        )
    
    def _create_agent(self, llm: LLM) -> Agent:
        """Create OpenHands agent with tools."""
        tools = self.custom_tools or [
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
        ]
        
        if self.planning_mode:
            from openhands.tools.preset.planning import get_planning_tools
            tools = get_planning_tools() + tools
            
        return Agent(llm=llm, tools=tools)
    
    def execute(
        self,
        task_description: str,
        timeout: int = 300,
    ) -> dict:
        """Execute task in Daytona sandbox.
        
        Args:
            task_description: What to do in the sandbox
            timeout: Execution timeout in seconds
            
        Returns:
            dict with status, events, cost, sandbox_id
        """
        llm_settings = load_llm_settings()
        llm = LLM(
            model=llm_settings.model,
            api_key=llm_settings.api_key,
            base_url=llm_settings.base_url,
        )
        
        agent = self._create_agent(llm)
        workspace = self._create_workspace()
        
        with workspace:
            print(f"🚀 Sandbox created: {workspace.sandbox_id}")
            
            # Verify sandbox is working
            result = workspace.execute_command("echo 'Sandbox ready!'")
            print(f"✓ Sandbox verified: {result.stdout.strip()}")
            
            # Create conversation with Daytona workspace
            conversation = Conversation(
                agent=agent,
                workspace=workspace,  # OpenHandsDaytonaWorkspace is OpenHands-compatible
            )
            
            try:
                conversation.send_message(task_description)
                conversation.run()
                
                return {
                    "status": str(conversation.state.execution_status),
                    "event_count": len(conversation.state.events),
                    "cost": conversation.conversation_stats.get_combined_metrics().accumulated_cost,
                    "sandbox_id": workspace.sandbox_id,
                    "conversation_id": str(conversation.state.id),
                }
            finally:
                conversation.close()
                # Sandbox auto-cleaned up by context manager
                print(f"🧹 Sandbox cleaned up: {workspace.sandbox_id}")


def quick_sandbox_test(task: str, project_id: str = "quick-test") -> dict:
    """One-liner to test sandbox execution.
    
    Usage:
        from omoi_os.testing.sandbox_test_executor import quick_sandbox_test
        result = quick_sandbox_test("echo 'hello' && ls -la")
    """
    executor = SandboxTestExecutor(project_id=project_id)
    return executor.execute(task)
```

### Usage Examples

```python
# Example 1: Quick test
from omoi_os.testing.sandbox_test_executor import quick_sandbox_test

result = quick_sandbox_test("Create a Python file that prints 'Hello World'")
print(f"Status: {result['status']}")
print(f"Cost: ${result['cost']:.4f}")

# Example 2: With custom configuration
from omoi_os.testing.sandbox_test_executor import SandboxTestExecutor

executor = SandboxTestExecutor(
    project_id="my-test-project",
    planning_mode=True,  # Include planning tools
)
result = executor.execute("""
    Analyze the current directory and create a PLAN.md file
    with recommendations for improvement.
""")
```

---

## Option 2: Extend DaytonaWorkspace for Agent Spawning

Add a method to spawn a full agent session directly from `DaytonaWorkspace`.

### Implementation

```python
# Add to omoi_os/workspace/daytona.py

class DaytonaWorkspace:
    # ... existing code ...
    
    def spawn_agent_session(
        self,
        task_description: str,
        llm_model: str = "anthropic/claude-sonnet-4-5-20250929",
        llm_api_key: str | None = None,
        tools: list | None = None,
    ) -> dict:
        """Spawn an OpenHands agent session in this sandbox.
        
        This is the key integration point - uses DaytonaWorkspace as
        the execution backend for OpenHands agents.
        
        Args:
            task_description: Task for the agent to execute
            llm_model: LLM model to use
            llm_api_key: API key (or uses LLM_API_KEY env var)
            tools: Custom tools (defaults to Terminal + FileEditor)
            
        Returns:
            dict with execution results
            
        Example:
            with DaytonaWorkspace(config) as ws:
                result = ws.spawn_agent_session(
                    "Create a FastAPI app with a /health endpoint"
                )
                print(result['status'])
        """
        import os
        from pydantic import SecretStr
        from openhands.sdk import LLM, Agent, Conversation, Tool
        from openhands.tools.file_editor import FileEditorTool
        from openhands.tools.terminal import TerminalTool
        
        api_key = llm_api_key or os.getenv("LLM_API_KEY")
        if not api_key:
            raise ValueError("LLM API key required. Set LLM_API_KEY or pass llm_api_key")
        
        llm = LLM(
            model=llm_model,
            api_key=SecretStr(api_key),
        )
        
        agent_tools = tools or [
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
        ]
        
        agent = Agent(llm=llm, tools=agent_tools)
        
        # Create adapter that wraps self for OpenHands compatibility
        from omoi_os.workspace.daytona import _DaytonaOpenHandsAdapter
        adapter = _DaytonaOpenHandsAdapter(self)
        
        conversation = Conversation(
            agent=agent,
            workspace=adapter,
        )
        
        try:
            conversation.send_message(task_description)
            conversation.run()
            
            return {
                "status": str(conversation.state.execution_status),
                "event_count": len(conversation.state.events),
                "cost": conversation.conversation_stats.get_combined_metrics().accumulated_cost,
                "sandbox_id": self.sandbox_id,
            }
        finally:
            conversation.close()


class _DaytonaOpenHandsAdapter:
    """Minimal adapter to make DaytonaWorkspace work with OpenHands Conversation.
    
    This wraps DaytonaWorkspace to implement the interface Conversation expects.
    """
    
    def __init__(self, daytona_workspace: DaytonaWorkspace):
        self._ws = daytona_workspace
        self.working_dir = daytona_workspace.working_dir
        
    def execute_command(self, command: str, cwd: str | None = None, timeout: float = 30.0):
        from openhands.sdk.workspace.models import CommandResult
        result = self._ws.execute_command(command, cwd)
        return CommandResult(
            command=command,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            timeout_occurred=False,
        )
```

### Usage

```python
from omoi_os.workspace.daytona import DaytonaWorkspace, DaytonaWorkspaceConfig

config = DaytonaWorkspaceConfig.from_settings()

with DaytonaWorkspace(config) as workspace:
    # Run simple commands
    result = workspace.execute_command("python --version")
    print(result.stdout)
    
    # Spawn a full agent session
    agent_result = workspace.spawn_agent_session(
        "Create a FastAPI app with /health and /ready endpoints"
    )
    print(f"Agent status: {agent_result['status']}")
    print(f"Cost: ${agent_result['cost']:.4f}")
```

---

## Option 3: pytest Fixtures for Sandbox Testing

Create reusable fixtures for integration tests.

### Implementation

```python
# tests/conftest.py
import pytest
from omoi_os.config import load_daytona_settings
from omoi_os.workspace.daytona import DaytonaWorkspace, DaytonaWorkspaceConfig


@pytest.fixture(scope="function")
def daytona_sandbox():
    """Ephemeral Daytona sandbox for a single test.
    
    Sandbox is created before test, deleted after.
    """
    settings = load_daytona_settings()
    if not settings.api_key:
        pytest.skip("DAYTONA_API_KEY not set")
    
    config = DaytonaWorkspaceConfig.from_settings(
        settings=settings,
        labels={"test": "true"},
        ephemeral=True,
    )
    
    workspace = DaytonaWorkspace(config)
    workspace.__enter__()
    
    yield workspace
    
    workspace.__exit__(None, None, None)


@pytest.fixture(scope="module")
def shared_daytona_sandbox():
    """Shared Daytona sandbox for a test module.
    
    Reuses sandbox across multiple tests for speed.
    """
    settings = load_daytona_settings()
    if not settings.api_key:
        pytest.skip("DAYTONA_API_KEY not set")
    
    config = DaytonaWorkspaceConfig.from_settings(
        settings=settings,
        labels={"test": "shared"},
        ephemeral=False,  # Keep alive for module
    )
    
    workspace = DaytonaWorkspace(config)
    workspace.__enter__()
    
    yield workspace
    
    workspace.__exit__(None, None, None)


@pytest.fixture
def sandbox_with_agent(daytona_sandbox):
    """Sandbox with OpenHands agent pre-configured."""
    from omoi_os.testing.sandbox_test_executor import SandboxTestExecutor
    
    executor = SandboxTestExecutor(
        project_id=f"test-{daytona_sandbox.sandbox_id[:8]}",
    )
    executor._workspace = daytona_sandbox
    
    return executor
```

### Test Examples

```python
# tests/integration/test_sandbox_execution.py
import pytest


class TestDaytonaSandbox:
    """Test sandbox creation and command execution."""
    
    def test_sandbox_creates_successfully(self, daytona_sandbox):
        """Verify sandbox is created and accessible."""
        assert daytona_sandbox.sandbox_id is not None
        
        result = daytona_sandbox.execute_command("echo 'hello'")
        assert result.exit_code == 0
        assert "hello" in result.stdout
    
    def test_python_available(self, daytona_sandbox):
        """Verify Python is available in sandbox."""
        result = daytona_sandbox.execute_command("python --version")
        assert result.exit_code == 0
        assert "Python" in result.stdout
    
    def test_file_operations(self, daytona_sandbox):
        """Test file upload/download."""
        # Write file
        daytona_sandbox.write_file("/tmp/test.txt", "Hello World")
        
        # Read back
        content = daytona_sandbox.read_file("/tmp/test.txt")
        assert content.decode() == "Hello World"
    
    def test_git_clone(self, daytona_sandbox):
        """Test git operations."""
        daytona_sandbox.git_clone(
            "https://github.com/OpenHands/software-agent-sdk.git",
            path="/home/daytona/sdk"
        )
        
        result = daytona_sandbox.execute_command(
            "ls -la /home/daytona/sdk/README.md"
        )
        assert result.exit_code == 0


class TestAgentExecution:
    """Test OpenHands agent execution in sandbox."""
    
    @pytest.mark.slow
    def test_agent_creates_file(self, sandbox_with_agent):
        """Agent should be able to create files."""
        result = sandbox_with_agent.execute(
            "Create a file called hello.py that prints 'Hello World'"
        )
        
        assert result["status"] in ["completed", "success"]
    
    @pytest.mark.slow
    def test_agent_analyzes_repo(self, daytona_sandbox):
        """Agent should analyze a cloned repo."""
        from omoi_os.testing.sandbox_test_executor import SandboxTestExecutor
        
        # Clone a small repo first
        daytona_sandbox.git_clone(
            "https://github.com/OpenHands/software-agent-sdk.git",
            path="sdk"
        )
        
        executor = SandboxTestExecutor(project_id="analyze-test")
        result = executor.execute(
            "Read the README.md in the sdk directory and summarize it in SUMMARY.txt"
        )
        
        assert result["status"] in ["completed", "success"]
```

---

## Configuration

### Environment Variables

```bash
# .env.local
DAYTONA_API_KEY=dtn_your_key_here
WORKSPACE_MODE=daytona

# Optional
DAYTONA_TARGET=us              # or 'eu'
DAYTONA_IMAGE=python:3.12      # custom Docker image
DAYTONA_TIMEOUT=120            # sandbox creation timeout
```

### Config File

```yaml
# config/base.yaml
daytona:
  api_key: ${DAYTONA_API_KEY}
  api_url: https://app.daytona.io/api
  target: us
  snapshot: python:3.12
  timeout: 60
```

---

## Quick Start Commands

```bash
# 1. Set up environment
export DAYTONA_API_KEY="dtn_your_key"
export LLM_API_KEY="your_llm_key"

# 2. Run existing Daytona example
cd /Users/kevinhill/Coding/Experiments/senior-sandbox/senior_sandbox/backend
uv run python examples/openhands_daytona_example.py

# 3. Quick Python test
uv run python -c "
from omoi_os.workspace.daytona import DaytonaWorkspace, DaytonaWorkspaceConfig
config = DaytonaWorkspaceConfig.from_settings()
with DaytonaWorkspace(config) as ws:
    print(f'Sandbox: {ws.sandbox_id}')
    result = ws.execute_command('python --version')
    print(f'Python: {result.stdout.strip()}')
"

# 4. Run integration tests
uv run pytest tests/integration/test_sandbox_execution.py -v -s
```

---

## Comparison: Options Summary

| Option | Complexity | Use Case |
|--------|------------|----------|
| **1. SandboxTestExecutor** | Low | Quick ad-hoc testing, scripts |
| **2. spawn_agent_session()** | Medium | Integrate agent spawning into DaytonaWorkspace |
| **3. pytest fixtures** | Medium | Structured integration tests |

---

## Recommended Next Steps

1. **Create `omoi_os/testing/sandbox_test_executor.py`** - Option 1 implementation
2. **Add pytest fixtures to `tests/conftest.py`** - Option 3
3. **Update `DaytonaWorkspace` with `spawn_agent_session()`** - Option 2 (optional)
4. **Write integration tests** using the fixtures

The key insight: Your `OpenHandsDaytonaWorkspace` already implements the interface that `Conversation` expects. You just need a lightweight harness to skip the worker and test directly.

---

## References

- Your existing: `omoi_os/workspace/daytona.py`
- Your existing: `examples/openhands_daytona_example.py`
- OpenHands SDK: https://github.com/OpenHands/software-agent-sdk
- Daytona Python SDK: https://github.com/daytonaio/sdk-python
