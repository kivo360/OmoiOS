# Testing Patterns

Strategies for testing Claude Agent SDK applications independently.

## Unit Testing Custom Tools

### Basic Tool Test

```python
import pytest
from typing import Any

# Your tool
@tool("process_data", "Process input data", {"data": str})
async def process_data(args: dict[str, Any]) -> dict[str, Any]:
    result = args["data"].upper()
    return {"content": [{"type": "text", "text": result}]}

# Test
@pytest.mark.asyncio
async def test_process_data():
    result = await process_data({"data": "hello"})

    assert result["content"][0]["text"] == "HELLO"
    assert "is_error" not in result
```

### Testing Error Cases

```python
@tool("divide", "Divide numbers", {"a": float, "b": float})
async def divide(args: dict[str, Any]) -> dict[str, Any]:
    if args["b"] == 0:
        return {
            "content": [{"type": "text", "text": "Division by zero"}],
            "is_error": True
        }
    return {"content": [{"type": "text", "text": str(args["a"] / args["b"])}]}

@pytest.mark.asyncio
async def test_divide_by_zero():
    result = await divide({"a": 10, "b": 0})

    assert result["is_error"] is True
    assert "zero" in result["content"][0]["text"].lower()

@pytest.mark.asyncio
async def test_divide_success():
    result = await divide({"a": 10, "b": 2})

    assert "is_error" not in result
    assert result["content"][0]["text"] == "5.0"
```

## Testing Permission Callbacks

```python
from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny, ToolPermissionContext

async def my_permission_callback(tool_name, input_data, context):
    if "rm" in input_data.get("command", ""):
        return PermissionResultDeny(message="No deletions")
    return PermissionResultAllow()

@pytest.mark.asyncio
async def test_blocks_rm():
    context = ToolPermissionContext(suggestions=[], signal=None)

    result = await my_permission_callback(
        "Bash",
        {"command": "rm -rf /"},
        context
    )

    assert isinstance(result, PermissionResultDeny)
    assert "deletions" in result.message

@pytest.mark.asyncio
async def test_allows_safe_commands():
    context = ToolPermissionContext(suggestions=[], signal=None)

    result = await my_permission_callback(
        "Bash",
        {"command": "ls -la"},
        context
    )

    assert isinstance(result, PermissionResultAllow)
```

## Testing Hooks

```python
@pytest.mark.asyncio
async def test_hook_blocks_pattern():
    async def my_hook(input_data, tool_use_id, context):
        if "danger" in input_data["tool_input"].get("command", ""):
            return {
                "hookSpecificOutput": {
                    "permissionDecision": "deny",
                }
            }
        return {}

    result = await my_hook(
        {"tool_name": "Bash", "tool_input": {"command": "danger command"}},
        "test-id",
        {}
    )

    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
```

## Integration Testing with Mock Transport

```python
from unittest.mock import AsyncMock, MagicMock
from claude_agent_sdk._internal.transport import Transport

class MockTransport(Transport):
    def __init__(self, responses: list[dict]):
        self.responses = responses
        self.sent_messages = []

    async def connect(self, prompt=None):
        pass

    async def write(self, data: str):
        self.sent_messages.append(data)

    async def read_messages(self):
        for response in self.responses:
            yield response

    async def close(self):
        pass

@pytest.mark.asyncio
async def test_with_mock_transport():
    mock_responses = [
        {
            "type": "assistant",
            "content": [{"type": "text", "text": "Hello!"}],
            "model": "claude-sonnet-4-20250514"
        },
        {
            "type": "result",
            "subtype": "success",
            "session_id": "test-session",
            "num_turns": 1,
            "total_cost_usd": 0.001,
        }
    ]

    transport = MockTransport(mock_responses)

    # Use transport with SDK
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage

    messages = []
    async for msg in query(prompt="Hi", transport=transport):
        messages.append(msg)

    assert len(messages) == 2
    assert isinstance(messages[0], AssistantMessage)
```

## End-to-End Testing

For real API tests, mark with `@pytest.mark.e2e`:

```python
import os
import pytest

@pytest.mark.e2e
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="Requires ANTHROPIC_API_KEY"
)
@pytest.mark.asyncio
async def test_real_query():
    from claude_agent_sdk import query, ResultMessage

    async for msg in query(prompt="Say 'test' and nothing else"):
        if isinstance(msg, ResultMessage):
            assert msg.num_turns >= 1
            assert msg.total_cost_usd > 0
```

## Testing with Fixtures

```python
import pytest

@pytest.fixture
def sample_tool_input():
    return {"file_path": "/tmp/test.txt", "content": "Hello"}

@pytest.fixture
def permission_context():
    return ToolPermissionContext(suggestions=[], signal=None)

@pytest.mark.asyncio
async def test_with_fixtures(sample_tool_input, permission_context):
    result = await my_permission_callback(
        "Write",
        sample_tool_input,
        permission_context
    )
    assert isinstance(result, PermissionResultAllow)
```

## Running Tests

```bash
# Run all tests
pytest

# Run only unit tests
pytest -m "not e2e"

# Run e2e tests (requires API key)
ANTHROPIC_API_KEY=xxx pytest -m e2e

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

## Test Configuration (pyproject.toml)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "e2e: end-to-end tests requiring real API",
]
testpaths = ["tests"]
```
