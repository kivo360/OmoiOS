# Claude Agent SDK Integration Patterns

Reference patterns for integrating Claude Agent SDK Python into spec-driven development.

---

## Overview

When designing features that involve AI agents, use these patterns to define:
- Custom tools for agent capabilities
- Hooks for lifecycle control
- Permission callbacks for security
- Session management for stateful interactions

---

## Custom Tools

### Basic Tool Definition

```python
from typing import Any
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("tool_name", "Description of what the tool does", {
    "param1": str,
    "param2": int,
    "param3": bool
})
async def tool_name(args: dict[str, Any]) -> dict[str, Any]:
    """Implementation of the tool."""
    result = process(args["param1"], args["param2"])

    return {
        "content": [
            {"type": "text", "text": f"Result: {result}"}
        ]
    }
```

### Tool with Error Handling

```python
@tool("safe_operation", "Operation with error handling", {"input": str})
async def safe_operation(args: dict[str, Any]) -> dict[str, Any]:
    try:
        result = perform_operation(args["input"])
        return {
            "content": [{"type": "text", "text": f"Success: {result}"}]
        }
    except ValidationError as e:
        return {
            "content": [{"type": "text", "text": f"Validation error: {e}"}],
            "is_error": True
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {e}"}],
            "is_error": True
        }
```

### Tool with State Access

```python
class ApplicationState:
    def __init__(self):
        self.items: list[str] = []
        self.counter: int = 0

state = ApplicationState()

@tool("add_item", "Add item to state", {"item": str})
async def add_item(args: dict[str, Any]) -> dict[str, Any]:
    state.items.append(args["item"])
    state.counter += 1
    return {
        "content": [{
            "type": "text",
            "text": f"Added '{args['item']}'. Total: {state.counter}"
        }]
    }

@tool("list_items", "List all items", {})
async def list_items(args: dict[str, Any]) -> dict[str, Any]:
    if not state.items:
        return {"content": [{"type": "text", "text": "No items"}]}

    items_text = "\n".join(f"- {item}" for item in state.items)
    return {"content": [{"type": "text", "text": f"Items:\n{items_text}"}]}
```

### Creating MCP Server

```python
from claude_agent_sdk import create_sdk_mcp_server

# Create server with tools
server = create_sdk_mcp_server(
    name="my_tools",
    version="1.0.0",
    tools=[add_item, list_items, safe_operation]
)
```

---

## Hooks

### PreToolUse Hook (Validation/Blocking)

```python
from claude_agent_sdk import HookMatcher, HookInput, HookContext, HookJSONOutput

async def validate_before_tool(
    input_data: HookInput,
    tool_use_id: str | None,
    context: HookContext
) -> HookJSONOutput:
    """Validate tool input before execution."""
    tool_name = input_data["tool_name"]
    tool_input = input_data["tool_input"]

    # Block dangerous operations
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        dangerous_patterns = ["rm -rf", "sudo", "chmod 777"]

        for pattern in dangerous_patterns:
            if pattern in command:
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": f"Blocked: {pattern}"
                    }
                }

    # Allow by default
    return {}
```

### PostToolUse Hook (Review/Feedback)

```python
async def review_after_tool(
    input_data: HookInput,
    tool_use_id: str | None,
    context: HookContext
) -> HookJSONOutput:
    """Review tool output and provide feedback."""
    tool_response = input_data.get("tool_response", "")

    # Check for errors
    if "error" in str(tool_response).lower():
        return {
            "systemMessage": "The command produced an error",
            "reason": "Tool execution failed",
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "Consider a different approach."
            }
        }

    return {}
```

### Registering Hooks

```python
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[validate_before_tool]),
            HookMatcher(matcher="Write", hooks=[validate_before_tool]),
        ],
        "PostToolUse": [
            HookMatcher(matcher=None, hooks=[review_after_tool]),  # All tools
        ],
    }
)
```

---

## Permission Callbacks

### Custom Permission Logic

```python
from claude_agent_sdk import (
    ToolPermissionContext,
    PermissionResultAllow,
    PermissionResultDeny
)

async def can_use_tool(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    """Custom tool permission logic."""

    # Block writes to protected paths
    if tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        protected = ["config", "secrets", ".env"]

        if any(p in file_path.lower() for p in protected):
            return PermissionResultDeny(
                behavior="deny",
                message="Cannot write to protected files",
                interrupt=False
            )

    # Modify input for safety
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if command.startswith("rm"):
            modified_input = {**tool_input, "command": f"{command} -i"}
            return PermissionResultAllow(
                behavior="allow",
                updated_input=modified_input
            )

    return PermissionResultAllow(behavior="allow")
```

---

## Agent Configuration

### Full Configuration Example

```python
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

options = ClaudeAgentOptions(
    # System prompt
    system_prompt="You are a helpful assistant.",

    # Tool configuration
    allowed_tools=[
        "Read", "Write", "Edit",
        "mcp__my_tools__add_item",
        "mcp__my_tools__list_items",
    ],
    disallowed_tools=["Bash"],

    # MCP servers
    mcp_servers={
        "my_tools": my_tools_server,
    },

    # Permission callback
    can_use_tool=can_use_tool,

    # Hooks
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Write", hooks=[validate_before_tool]),
        ],
        "PostToolUse": [
            HookMatcher(matcher=None, hooks=[review_after_tool]),
        ],
    },

    # Execution limits
    max_turns=20,
    max_budget_usd=2.0,

    # Session management
    fork_session=True,

    # Model selection
    model="claude-sonnet-4-5",
)
```

---

## Usage Patterns

### Simple Query

```python
from claude_agent_sdk import query

async def simple_query():
    async for msg in query(prompt="Hello!", options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    print(block.text)
```

### Stateful Client

```python
from claude_agent_sdk import ClaudeSDKClient

async def stateful_session():
    async with ClaudeSDKClient(options=options) as client:
        # First query
        await client.query("Create a new item called 'apple'")
        async for msg in client.receive_response():
            process_message(msg)

        # Follow-up (maintains context)
        await client.query("Now add 'banana'")
        async for msg in client.receive_response():
            process_message(msg)
```

### Message Processing

```python
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

def process_message(msg):
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                print(f"Text: {block.text}")
            elif isinstance(block, ToolUseBlock):
                print(f"Tool: {block.name} -> {block.input}")

    elif isinstance(msg, ResultMessage):
        print(f"Done. Turns: {msg.num_turns}, Cost: ${msg.total_cost_usd:.4f}")
```

---

## Requirements Integration

When writing requirements for agent features:

```markdown
#### REQ-AGENT-TOOL-001: Custom Tool Definition
THE SYSTEM SHALL define custom tools using the `@tool` decorator with:
- Unique tool name (snake_case)
- Description for LLM understanding
- Input schema with type hints

#### REQ-AGENT-HOOK-001: PreToolUse Validation
THE SYSTEM SHALL implement PreToolUse hooks to validate and optionally block:
- Dangerous operations
- Invalid input parameters
- Unauthorized access patterns

#### REQ-AGENT-PERM-001: Permission Callback
THE SYSTEM SHALL implement `can_use_tool` callback for:
- File path access control
- Command modification
- Rate limiting
```

---

## Design Integration

When writing design docs for agent features:

```markdown
## Agent Architecture

### Custom Tools

| Tool | Purpose | Input Schema |
|------|---------|--------------|
| `add_item` | Add item to state | `{item: str}` |
| `list_items` | List all items | `{}` |

### Hooks Configuration

| Hook | Matcher | Purpose |
|------|---------|---------|
| `PreToolUse` | `Bash` | Block dangerous commands |
| `PostToolUse` | `*` | Log all tool usage |

### Permission Model

- File writes restricted to `/workspace/` directory
- Bash commands auto-modified with safety flags
- Rate limit: 100 tool calls per session
```
