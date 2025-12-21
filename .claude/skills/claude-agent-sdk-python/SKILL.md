---
name: claude-agent-sdk-python
description: Build and test Python applications using the Claude Agent SDK. Use when creating agent applications, custom MCP tools, permission handlers, lifecycle hooks, or multi-turn conversations. Covers query(), ClaudeSDKClient, @tool decorator, create_sdk_mcp_server(), hooks, permissions, and independent app testing patterns.
---

# Claude Agent SDK Python

Build production-ready agent applications with the Claude Agent SDK for Python.

## Quick Reference

### Installation

```bash
pip install claude-agent-sdk
```

Requires Python 3.10+ and bundled Claude CLI v2.0.60+.

### Core APIs

| API | Use Case |
|-----|----------|
| `query()` | One-shot or simple multi-turn queries |
| `ClaudeSDKClient` | Interactive streaming, bidirectional control |
| `@tool` + `create_sdk_mcp_server()` | Custom in-process tools |
| `can_use_tool` callback | Fine-grained permission control |
| `hooks` | Lifecycle event interception |

## Basic Patterns

### One-Shot Query

```python
import anyio
from claude_agent_sdk import query, AssistantMessage, TextBlock, ResultMessage

async def main():
    async for msg in query(prompt="Explain Python decorators"):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    print(block.text)
        elif isinstance(msg, ResultMessage):
            print(f"Cost: ${msg.total_cost_usd:.4f}")

anyio.run(main)
```

### Interactive Client

```python
import anyio
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ResultMessage,
)

async def main():
    options = ClaudeAgentOptions(
        system_prompt="You are a helpful assistant",
        allowed_tools=["Read", "Write", "Bash"],
        permission_mode="acceptEdits",
        max_turns=10,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Analyze main.py")

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(block.text)
            elif isinstance(msg, ResultMessage):
                print(f"Done. Cost: ${msg.total_cost_usd:.4f}")

anyio.run(main)
```

### Custom Tools

```python
from typing import Any
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions

@tool("add", "Add two numbers", {"a": float, "b": float})
async def add(args: dict[str, Any]) -> dict[str, Any]:
    result = args["a"] + args["b"]
    return {"content": [{"type": "text", "text": f"Result: {result}"}]}

@tool("divide", "Divide two numbers", {"a": float, "b": float})
async def divide(args: dict[str, Any]) -> dict[str, Any]:
    if args["b"] == 0:
        return {
            "content": [{"type": "text", "text": "Error: Division by zero"}],
            "is_error": True
        }
    return {"content": [{"type": "text", "text": f"Result: {args['a'] / args['b']}"}]}

calculator = create_sdk_mcp_server(
    name="calculator",
    version="1.0.0",
    tools=[add, divide]
)

options = ClaudeAgentOptions(
    mcp_servers={"calc": calculator},
    allowed_tools=["mcp__calc__add", "mcp__calc__divide"],
    permission_mode="acceptEdits",
)
```

## Configuration Reference

### ClaudeAgentOptions

```python
ClaudeAgentOptions(
    # Model
    model="claude-sonnet-4-20250514",
    fallback_model=None,

    # Prompts
    system_prompt="You are a helpful assistant",

    # Limits
    max_turns=10,
    max_budget_usd=1.00,
    max_thinking_tokens=8000,

    # Environment
    cwd="/path/to/project",
    env={"CUSTOM_VAR": "value"},

    # Tools
    tools=["Read", "Write", "Bash"],  # or {"type": "preset", "preset": "claude_code"}
    allowed_tools=["Read", "Write"],  # whitelist
    disallowed_tools=["WebFetch"],    # blacklist
    mcp_servers={"name": config},     # custom tools

    # Permissions
    permission_mode="acceptEdits",  # default, acceptEdits, plan, bypassPermissions
    can_use_tool=my_permission_callback,

    # Sessions
    continue_conversation=False,
    resume="session-id",
    fork_session=False,

    # Hooks
    hooks={"PreToolUse": [HookMatcher(matcher="*", hooks=[my_hook])]},
)
```

### Permission Modes

| Mode | Behavior |
|------|----------|
| `"default"` | Prompt for all actions |
| `"acceptEdits"` | Auto-approve file edits |
| `"plan"` | Planning mode (no execution) |
| `"bypassPermissions"` | Auto-approve all (use with caution) |

## Advanced Patterns

For detailed examples of:
- **Permission callbacks**: See [references/permissions.md](references/permissions.md)
- **Lifecycle hooks**: See [references/hooks.md](references/hooks.md)
- **Testing patterns**: See [references/testing.md](references/testing.md)
- **Production patterns**: See [references/production.md](references/production.md)

## Independent App Testing

Use `scripts/run_agent_app.py` to test agent applications in isolation:

```bash
# Run a simple agent app
python scripts/run_agent_app.py path/to/app.py

# Run with custom options
python scripts/run_agent_app.py path/to/app.py --cwd /project --max-turns 5
```

Use `scripts/create_agent_project.py` to scaffold new agent projects:

```bash
# Create a basic agent project
python scripts/create_agent_project.py my_agent --template basic

# Create with custom tools
python scripts/create_agent_project.py my_agent --template custom-tools

# Create interactive chat app
python scripts/create_agent_project.py my_agent --template chat
```

## Message Types

| Type | Description |
|------|-------------|
| `AssistantMessage` | Claude's responses (text, thinking, tool use) |
| `UserMessage` | User input or tool results |
| `ResultMessage` | Session summary (always last) |
| `SystemMessage` | System events |

### Content Blocks

```python
from claude_agent_sdk import TextBlock, ThinkingBlock, ToolUseBlock, ToolResultBlock

# In AssistantMessage.content
for block in msg.content:
    if isinstance(block, TextBlock):
        print(block.text)
    elif isinstance(block, ThinkingBlock):
        print(f"Thinking: {block.thinking}")
    elif isinstance(block, ToolUseBlock):
        print(f"Tool: {block.name}, Input: {block.input}")
```

## Error Handling

```python
from claude_agent_sdk import (
    ClaudeSDKError,
    CLINotFoundError,
    ProcessError,
    SDKJSONDecodeError,
)

try:
    async with ClaudeSDKClient(options) as client:
        await client.query("Do something")
        async for msg in client.receive_response():
            process(msg)
except CLINotFoundError:
    print("Claude CLI not found. Install from https://claude.ai")
except ProcessError as e:
    print(f"CLI failed with exit code: {e.exit_code}")
except SDKJSONDecodeError:
    print("Failed to parse CLI response")
```

## Best Practices

1. **Always use context managers** for `ClaudeSDKClient` to ensure cleanup
2. **Set `max_budget_usd`** to prevent runaway costs
3. **Use `permission_mode="acceptEdits"`** for file operations without prompts
4. **Return `is_error: True`** from custom tools on failure
5. **Use structured outputs** for predictable JSON responses
6. **Test tools independently** before integrating with full agent
