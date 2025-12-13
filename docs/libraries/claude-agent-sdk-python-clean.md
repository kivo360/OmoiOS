# Claude Agent SDK for Python Documentation

*Generated documentation for the Claude Agent SDK Python - A typed Python interface for building AI agent applications with Claude Code.*

## Table of Contents

### Core SDK Documentation

1. [Overview](#overview)
   - [Key Features](#key-features)
   - [Three-Tier Architecture](#three-tier-architecture)
2. [Installation and Setup](#installation-and-setup)
   - [Requirements](#requirements)
   - [Platform Support](#platform-support)
   - [Dependencies](#dependencies)
3. [Quick Start](#quick-start)
   - [Basic Query Example](#basic-query-example)
   - [Interactive Streaming Example](#interactive-streaming-example)

### Basic Usage

4. [query() Function](#query-function)
   - [Parameters](#query-parameters)
   - [Return Types](#query-return-types)
   - [Usage Examples](#query-usage-examples)
5. [ClaudeSDKClient](#claudesdkclient)
   - [Client Lifecycle](#client-lifecycle)
   - [Methods](#client-methods)
   - [Streaming Capabilities](#streaming-capabilities)
   - [Context Manager Usage](#context-manager-usage)
6. [ClaudeAgentOptions Configuration](#claudeagentoptions-configuration)
   - [Basic Configuration](#basic-configuration)
   - [Environment Configuration](#environment-configuration)
   - [Tool Configuration](#tool-configuration)
   - [Permission System](#permission-system-options)
   - [Session Management Options](#session-management-options)

### Message Types and Content

7. [Message Types](#message-types)
   - [UserMessage](#usermessage)
   - [AssistantMessage](#assistantmessage)
   - [SystemMessage](#systemmessage)
   - [ResultMessage](#resultmessage)
   - [StreamEvent](#streamevent)
8. [Content Blocks](#content-blocks)
   - [TextBlock](#textblock)
   - [ThinkingBlock](#thinkingblock)
   - [ToolUseBlock](#tooluseblock)
   - [ToolResultBlock](#toolresultblock)

### Transport and Communication

9. [SubprocessCLITransport](#subprocessclitransport)
   - [CLI Discovery](#cli-discovery)
   - [Lifecycle Management](#lifecycle-management)
   - [Stdin/Stdout Communication](#stdinstdout-communication)
   - [Command Building](#command-building)
   - [JSON Streaming](#json-streaming)
10. [Control Protocol](#control-protocol)
    - [CLI-to-SDK Request Types](#cli-to-sdk-request-types)
    - [SDK-to-CLI Request Types](#sdk-to-cli-request-types)
    - [Request/Response Correlation](#requestresponse-correlation)

### Extension Points

11. [Custom Tools (SDK MCP Servers)](#custom-tools-sdk-mcp-servers)
    - [@tool Decorator](#tool-decorator)
    - [create_sdk_mcp_server()](#create_sdk_mcp_server)
    - [McpSdkServerConfig](#mcpsdkserverconfig)
    - [Complete Custom Tool Example](#complete-custom-tool-example)
12. [Permission Callbacks](#permission-callbacks)
    - [can_use_tool Callback](#can_use_tool-callback)
    - [ToolPermissionContext](#toolpermissioncontext)
    - [PermissionResultAllow](#permissionresultallow)
    - [PermissionResultDeny](#permissionresultdeny)
    - [Permission Handling Examples](#permission-handling-examples)
13. [Lifecycle Hooks](#lifecycle-hooks)
    - [Hook Events](#hook-events)
    - [Hook Input Types](#hook-input-types)
    - [Hook Output Types](#hook-output-types)
    - [Hook Examples](#hook-examples)
14. [External MCP Servers](#external-mcp-servers)
    - [McpServerConfig](#mcpserverconfig)
    - [StdioMcpServerConfig](#stdiomcpserverconfig)
    - [SseMcpServerConfig](#ssemcpserverconfig)

### Advanced Features

15. [Session Management](#session-management)
    - [Session ID](#session-id)
    - [Continue Conversation](#continue-conversation)
    - [Resume Sessions](#resume-sessions)
    - [Conversation Forking](#conversation-forking)
16. [Resource Limits and Cost Control](#resource-limits-and-cost-control)
    - [max_turns](#max_turns)
    - [max_budget_usd](#max_budget_usd)
    - [max_thinking_tokens](#max_thinking_tokens)
    - [Monitoring Costs](#monitoring-costs)
17. [Security and Sandbox Settings](#security-and-sandbox-settings)
    - [Permission Modes](#permission-modes)
    - [Sandbox Configuration](#sandbox-configuration)
    - [Security Best Practices](#security-best-practices)
18. [Structured Outputs](#structured-outputs)
    - [output_format Configuration](#output_format-configuration)
    - [JSON Schema Definition](#json-schema-definition)
    - [Structured Output Examples](#structured-output-examples)

### Examples and Patterns

19. [Interactive Streaming Patterns](#interactive-streaming-patterns)
    - [Real-time Message Processing](#real-time-message-processing)
    - [Progress Tracking](#progress-tracking)
    - [Building Interactive Chat Applications](#building-interactive-chat-applications)
20. [Error Handling Patterns](#error-handling-patterns)
    - [Exception Types](#exception-types)
    - [Error Recovery Strategies](#error-recovery-strategies)
    - [Debugging Techniques](#debugging-techniques)
21. [Tool Integration Examples](#tool-integration-examples)
    - [Built-in Tools](#built-in-tools)
    - [Custom Tool Examples](#custom-tool-examples)

### Development Guide

22. [Project Structure](#project-structure)
    - [Directory Layout](#directory-layout)
    - [Modules and Purposes](#modules-and-purposes)
23. [Testing Strategy](#testing-strategy)
    - [Test Categories](#test-categories)
    - [Test Fixtures and Mocking](#test-fixtures-and-mocking)
    - [Running Tests](#running-tests)
24. [Build and Release Process](#build-and-release-process)
    - [Wheel Building](#wheel-building)
    - [CLI Bundling](#cli-bundling)
    - [GitHub Actions Workflows](#github-actions-workflows)
25. [Code Quality Standards](#code-quality-standards)
    - [Mypy Configuration](#mypy-configuration)
    - [Ruff Rules](#ruff-rules)
    - [CI Quality Gates](#ci-quality-gates)

### Multi-User SaaS Integration

26. [Multi-Tenant SaaS Platform Architecture](#multi-tenant-saas-platform-architecture)
    - [Architecture Overview](#architecture-overview-1)
    - [Component Responsibilities](#component-responsibilities)
    - [Multi-Tenant Isolation](#multi-tenant-isolation)
27. [SaaS Platform Experiment](#saas-platform-experiment)
    - [Architecture Diagram](#architecture-diagram-1)
    - [Sequence Diagram](#sequence-diagram)
    - [Orchestration Layer](#orchestration-layer)
    - [Test Client](#test-client)
28. [Production Best Practices & Common Pitfalls](#production-best-practices--common-pitfalls)
    - [Claude API Rate Limits and Retry Logic](#claude-api-rate-limits-and-retry-logic)
    - [Session State Machine](#session-state-machine)
    - [WebSocket Reconnection Pattern](#websocket-reconnection-pattern)
    - [Zombie Session Cleanup](#zombie-session-cleanup)
    - [Graceful Shutdown](#graceful-shutdown)
    - [Error Codes Reference](#error-codes-reference)
    - [Cost Tracking Best Practices](#cost-tracking-best-practices)
29. [Expanding the SaaS Experiment](#expanding-the-saas-experiment)
    - [Expansion Roadmap](#expansion-roadmap)
    - [Database Persistence](#expansion-1-add-database-persistence)
    - [Webhook Notifications](#expansion-2-add-webhook-notifications)

---

## Overview

> **Official Resources:**
> - 📦 **GitHub Repository**: [https://github.com/anthropics/claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python)
> - 📚 **DeepWiki Documentation**: [https://deepwiki.com/anthropics/claude-agent-sdk-python](https://deepwiki.com/anthropics/claude-agent-sdk-python)
> - 📖 **PyPI Package**: [https://pypi.org/project/claude-agent-sdk/](https://pypi.org/project/claude-agent-sdk/)

The `claude-agent-sdk` is a Python library that enables programmatic interaction with Claude agents via the Claude CLI. The SDK provides a high-level Python API for managing agent conversations, custom tool integration, permission control, and lifecycle hooks. It communicates with Claude agents by managing a subprocess running the Claude CLI (bundled at version 2.0.60), which in turn communicates with Anthropic's hosted Claude Agent service.

### Key Features

- **Bidirectional Control Protocol**: Applications can send messages to Claude and receive streaming responses, while simultaneously handling control requests from the CLI for permissions, hooks, and custom tool invocations
- **Built-in Tool Ecosystem**: Access to Claude Code's built-in tools (Read, Write, Bash, etc.) with fine-grained permission control
- **In-process Custom Tools**: Define Python functions as MCP servers that run in the same process as your application
- **Lifecycle Hooks**: Register callbacks invoked at specific points in the agent loop for deterministic control
- **Session Management**: Support for multi-turn conversations, session resumption, and conversation forking
- **Structured Outputs**: Generate validated JSON outputs conforming to JSON Schema specifications
- **Type Safety**: Strongly-typed Python interface with comprehensive type annotations

### Three-Tier Architecture

The SDK implements a three-tier architecture that separates concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Tier 1: Public API Layer                      │
├─────────────────────────────────────────────────────────────────┤
│  query()          │  ClaudeSDKClient  │  ClaudeAgentOptions      │
│  (one-shot)       │  (interactive)    │  (configuration)         │
│                   │                    │                          │
│  @tool decorator  │  create_sdk_mcp_server()                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               Tier 2: Core SDK Components                        │
├─────────────────────────────────────────────────────────────────┤
│  Query Class           │  Control Protocol Handler               │
│  (bidirectional comm)  │  (request/response correlation)         │
│                        │                                          │
│  SubprocessCLITransport│  MessageParser                          │
│  (process management)  │  (JSON → typed objects)                 │
│                        │                                          │
│  SDK MCP Server        │  Hook/Permission Handlers               │
│  (in-process tools)    │  (callback invocation)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               Tier 3: External Components                        │
├─────────────────────────────────────────────────────────────────┤
│  Claude CLI Process    │  Anthropic Agent Service                │
│  (bundled v2.0.60)     │  (remote API)                           │
│                        │                                          │
│  stdin/stdout          │  HTTPS                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Tier 1 - Public API Layer:**
- `query()` function for simple one-shot or multi-turn interactions
- `ClaudeSDKClient` class for bidirectional streaming conversations
- `ClaudeAgentOptions` dataclass for configuration
- `@tool` decorator and `create_sdk_mcp_server()` for custom tools

**Tier 2 - Core Components:**
- `Query` class manages the bidirectional control protocol
- `SubprocessCLITransport` handles subprocess management and stdin/stdout communication
- `MessageParser` converts raw JSON into strongly-typed Python objects
- SDK MCP Server handles in-process tool execution

**Tier 3 - External Components:**
- Claude CLI subprocess (bundled with SDK)
- Anthropic's hosted Claude Agent service (via HTTPS)

---

## Installation and Setup

### Requirements

```bash
pip install claude-agent-sdk
```

### Platform Support

| Platform | Architecture | Support |
|----------|-------------|---------|
| Linux | x86_64 | ✅ |
| Linux | ARM64 | ✅ |
| macOS | Universal (Intel + Apple Silicon) | ✅ |
| Windows | x64 | ✅ |

**Python Version Requirements:**
- Python 3.10, 3.11, 3.12, or 3.13

**Claude CLI:**
- Bundled version: 2.0.60
- Minimum supported: 2.0.0+
- The CLI is automatically bundled with the package during installation

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `anyio` | >=4.0.0 | Async I/O abstraction (supports asyncio and trio) |
| `typing_extensions` | >=4.0.0 | Type hints for Python <3.11 |
| `mcp` | >=0.1.0 | Model Context Protocol support |

**Development Dependencies:**
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `mypy` - Static type checking
- `ruff` - Linting and formatting

### Custom CLI Path

If you need to use a specific CLI installation:

```python
from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    cli_path="/path/to/custom/claude"
)
```

---

## Quick Start

### Basic Query Example

```python
import anyio
from claude_agent_sdk import query, AssistantMessage, TextBlock

async def main():
    async for message in query(prompt="What is 2 + 2?"):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Claude: {block.text}")

anyio.run(main)
```

### Interactive Streaming Example

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
        system_prompt="You are a helpful coding assistant",
        allowed_tools=["Read", "Write", "Bash"],
        permission_mode="acceptEdits",
        max_turns=10,
    )
    
    async with ClaudeSDKClient(options=options) as client:
        await client.query("Analyze the main.py file")
        
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")
            elif isinstance(msg, ResultMessage):
                print(f"Turns: {msg.num_turns}, Cost: ${msg.total_cost_usd:.4f}")

anyio.run(main)
```

---

## query() Function

The `query()` function provides a simple entry point for one-shot or multi-turn queries with Claude.

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `prompt` | `str \| AsyncIterable[dict[str, Any]]` | Single message string or async iterator for streaming multiple messages |
| `options` | `ClaudeAgentOptions \| None` | Optional configuration object |
| `transport` | `Transport \| None` | Optional custom transport (for testing) |

### Query Return Types

The function returns an `AsyncIterator[Message]` where `Message` is a union of:
- `AssistantMessage` - Claude's responses
- `ResultMessage` - Session summary (always last)
- `UserMessage` - User input echoed back
- `SystemMessage` - System events

### Query Usage Examples

**Simple Query:**

```python
from claude_agent_sdk import query

async for message in query(prompt="What is 2 + 2?"):
    print(message)
```

**Query with Options:**

```python
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    system_prompt="You are a helpful assistant",
    max_turns=1,
    model="claude-sonnet-4-20250514"
)

async for message in query(prompt="Tell me a joke", options=options):
    print(message)
```

**Processing Messages by Type:**

```python
from claude_agent_sdk import query, AssistantMessage, TextBlock, ResultMessage

async for message in query(prompt="Explain Python decorators"):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                print(f"Claude: {block.text}")
    elif isinstance(message, ResultMessage):
        print(f"Session completed. Cost: ${message.total_cost_usd:.4f}")
```

---

## ClaudeSDKClient

`ClaudeSDKClient` provides a stateful, bidirectional interface for interactive conversations with Claude Code.

### Client Lifecycle

```
┌──────────────┐     ┌─────────────────┐     ┌────────────────────┐
│ Initialization│ --> │    Connection   │ --> │   Connected State  │
│   __init__() │     │    connect()    │     │  query/receive     │
└──────────────┘     └─────────────────┘     └────────────────────┘
                                                      │
                                                      ▼
                                              ┌────────────────────┐
                                              │   Disconnection    │
                                              │   disconnect()     │
                                              └────────────────────┘
```

1. **Initialization**: Create instance with `ClaudeAgentOptions`
2. **Connection**: Call `connect()` or use `async with`
3. **Connected State**: Send/receive messages, control conversation
4. **Disconnection**: Call `disconnect()` or exit context manager

### Client Methods

**Connection Management:**

| Method | Description |
|--------|-------------|
| `async connect(prompt=None)` | Establishes connection to Claude CLI |
| `async disconnect()` | Closes connection and releases resources |

**Sending Messages:**

| Method | Description |
|--------|-------------|
| `async query(prompt, session_id="default")` | Sends a message or stream of messages |

**Receiving Messages:**

| Method | Description |
|--------|-------------|
| `async receive_messages()` | Async iterator yielding all messages indefinitely |
| `async receive_response()` | Async iterator yielding messages until ResultMessage |

**Control Methods:**

| Method | Description |
|--------|-------------|
| `async interrupt()` | Stops current agent operation |
| `async set_permission_mode(mode)` | Changes permission mode mid-conversation |
| `async set_model(model)` | Switches AI model mid-conversation |
| `async get_server_info()` | Retrieves server capabilities |

### Streaming Capabilities

`ClaudeSDKClient` always operates in streaming mode, enabling:
- Real-time message processing
- Bidirectional control protocol
- Dynamic permission and model changes
- Interrupt capabilities

### Context Manager Usage

```python
async with ClaudeSDKClient(options=options) as client:
    # Client automatically connected
    await client.query("Hello!")
    
    async for msg in client.receive_response():
        print(msg)
    
    # Client automatically disconnected on exit
```

**Complete Multi-Turn Example:**

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
        system_prompt="You are a helpful coding assistant",
        allowed_tools=["Read", "Write", "Bash"],
        permission_mode="acceptEdits",
        max_turns=10,
    )
    
    async with ClaudeSDKClient(options=options) as client:
        # First query
        await client.query("Analyze the main.py file")
        
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")
            elif isinstance(msg, ResultMessage):
                print(f"Turn {msg.num_turns}, Cost: ${msg.total_cost_usd:.4f}")
        
        # Follow-up with context maintained
        await client.query("Add docstrings to the functions you found")
        
        async for msg in client.receive_response():
            if isinstance(msg, ResultMessage):
                print(f"Total turns: {msg.num_turns}")
        
        # Interrupt example
        await client.query("Refactor the entire codebase")
        first_msg = await client.receive_response().__anext__()
        print("Got first message, interrupting...")
        await client.interrupt()

anyio.run(main)
```

---

## ClaudeAgentOptions Configuration

`ClaudeAgentOptions` is the central configuration dataclass for all SDK options.

### Basic Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `model` | `str \| None` | `None` | Claude model to use (defaults to latest Sonnet) |
| `fallback_model` | `str \| None` | `None` | Automatic fallback if primary unavailable |
| `system_prompt` | `str \| SystemPromptPreset \| None` | `None` | Agent's system prompt |
| `max_turns` | `int \| None` | `None` | Maximum conversation turns |
| `max_budget_usd` | `float \| None` | `None` | Maximum spending limit in USD |
| `max_thinking_tokens` | `int \| None` | `None` | Maximum tokens for extended thinking |

### Environment Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `cwd` | `str \| Path \| None` | `None` | Working directory for CLI subprocess |
| `env` | `dict[str, str]` | `{}` | Environment variables for CLI |
| `user` | `str \| None` | `None` | User identifier for session attribution |
| `add_dirs` | `list[str \| Path]` | `[]` | Additional accessible directories |
| `cli_path` | `str \| Path \| None` | `None` | Custom path to Claude CLI |

### Tool Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `tools` | `list[str] \| ToolsPreset \| None` | `None` | Base set of available tools |
| `allowed_tools` | `list[str]` | `[]` | Whitelist filter for tools |
| `disallowed_tools` | `list[str]` | `[]` | Blacklist filter for tools |
| `mcp_servers` | `dict[str, McpServerConfig]` | `{}` | MCP server configurations |

### Permission System Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `permission_mode` | `PermissionMode \| None` | `None` | Coarse-grained permission control |
| `can_use_tool` | `CanUseTool \| None` | `None` | Fine-grained permission callback |

**Permission Modes:**
- `"default"` - Prompt for all actions
- `"acceptEdits"` - Auto-approve file edits
- `"plan"` - Plan mode
- `"bypassPermissions"` - Auto-approve all (use with caution)

### Session Management Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `continue_conversation` | `bool` | `False` | Resume most recent session |
| `resume` | `str \| None` | `None` | Specific session_id to resume |
| `fork_session` | `bool` | `False` | Fork from resumed session |

**Configuration Example:**

```python
from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    # Basic
    model="claude-sonnet-4-20250514",
    system_prompt="You are a helpful coding assistant",
    max_turns=10,
    max_budget_usd=1.00,
    
    # Environment
    cwd="/path/to/project",
    env={"CUSTOM_VAR": "value"},
    
    # Tools
    allowed_tools=["Read", "Write", "Bash"],
    disallowed_tools=["WebFetch"],
    
    # Permissions
    permission_mode="acceptEdits",
    
    # Session
    continue_conversation=False,
)
```

---

## Message Types

### UserMessage

Represents user input or tool results sent to Claude.

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str \| list[ContentBlock]` | Text or structured content |
| `parent_tool_use_id` | `str \| None` | Links to parent tool use (subagent) |

### AssistantMessage

Represents Claude's responses including text, reasoning, and tool invocations.

| Field | Type | Description |
|-------|------|-------------|
| `content` | `list[ContentBlock]` | Text, thinking, or tool use blocks |
| `model` | `str` | Model that generated the response |
| `parent_tool_use_id` | `str \| None` | Links to parent tool use |
| `error` | `AssistantMessageError \| None` | Failure condition indicator |

### SystemMessage

Represents system-level events and metadata from the CLI.

| Field | Type | Description |
|-------|------|-------------|
| `subtype` | `str` | Message type (start, stop, error) |
| `data` | `dict[str, Any]` | Additional metadata |

### ResultMessage

Provides session summary at the end of each query.

| Field | Type | Description |
|-------|------|-------------|
| `subtype` | `str` | Result type (success, error) |
| `duration_ms` | `int` | Total duration in milliseconds |
| `duration_api_ms` | `int` | Time in API calls |
| `is_error` | `bool` | Error indicator |
| `num_turns` | `int` | Conversation turns completed |
| `session_id` | `str` | Unique session identifier |
| `total_cost_usd` | `float \| None` | Total cost in USD |
| `usage` | `dict[str, Any] \| None` | Token usage statistics |
| `result` | `str \| None` | Final result text |
| `structured_output` | `Any` | Structured output data |

### StreamEvent

Represents partial message updates during streaming.

| Field | Type | Description |
|-------|------|-------------|
| `uuid` | `str` | Unique identifier |
| `session_id` | `str` | Session identifier |
| `event` | `dict[str, Any]` | Raw Anthropic API stream event |
| `parent_tool_use_id` | `str \| None` | Parent tool use identifier |

---

## Content Blocks

### TextBlock

Plain text content.

```python
@dataclass
class TextBlock:
    text: str
```

### ThinkingBlock

Extended reasoning content from Claude.

```python
@dataclass
class ThinkingBlock:
    thinking: str  # Reasoning content
    signature: str  # Cryptographic verification
```

### ToolUseBlock

Claude's invocation of a tool.

```python
@dataclass
class ToolUseBlock:
    id: str  # Unique identifier
    name: str  # Tool name
    input: dict[str, Any]  # Input parameters
```

### ToolResultBlock

Result of a tool execution.

```python
@dataclass
class ToolResultBlock:
    tool_use_id: str  # Matches ToolUseBlock.id
    content: str | list[dict[str, Any]] | None  # Output
    is_error: bool | None  # Error indicator
```

---

## SubprocessCLITransport

Manages the interaction between the SDK and the Claude Code CLI subprocess.

### CLI Discovery

The transport locates the CLI binary in this order:
1. Bundled CLI in `_bundled/` directory
2. System PATH via `shutil.which("claude")`
3. Predefined common installation directories
4. Custom path via `ClaudeAgentOptions.cli_path`

If not found, raises `CLINotFoundError`.

### Lifecycle Management

**connect():**
- Performs CLI version check (warns if below 2.0.0)
- Builds command-line arguments
- Merges environment variables
- Spawns subprocess with stdin/stdout/stderr pipes

**close():**
- Deletes temporary files
- Cancels stderr handling task
- Closes communication streams
- Terminates subprocess

### Stdin/Stdout Communication

**Stdin (Input):**
- Streaming mode: stdin remains open for control messages
- String mode: stdin closed after prompt passed via args
- `write()` method sends data with readiness checks
- `end_input()` explicitly closes stdin

**Stdout (Output):**
- `read_messages()` continuously reads JSON from stdout
- Uses `json_buffer` to accumulate partial JSON
- Parses complete JSON objects and yields them

**Stderr Handling:**
- Optional stderr piping for debugging
- Background task reads stderr lines
- Invokes callback or writes to debug file

### Command Building

The `_build_command()` method translates options to CLI flags:

| Option | CLI Flag |
|--------|----------|
| `system_prompt` | `--system-prompt` or `--append-system-prompt` |
| `tools` | `--tools` |
| `allowed_tools` | `--allowedTools` |
| `disallowed_tools` | `--disallowedTools` |
| `model` | `--model` |
| `fallback_model` | `--fallback-model` |
| `continue_conversation` | `--continue` |
| `resume` | `--resume` |
| `mcp_servers` | `--mcp-config` (JSON) |
| `permission_mode` | `--permission-mode` |

**Long Command Optimization:**
For commands exceeding length limits (especially Windows), the transport writes JSON to a temporary file and uses `@filepath` reference.

### JSON Streaming

**Buffering Algorithm:**
1. Read lines from stdout stream
2. Split by `\n` for multiple JSON objects
3. Append fragments to buffer
4. Attempt `json.loads()` on buffer
5. On success: yield parsed data, clear buffer
6. On `JSONDecodeError`: continue buffering

**Buffer Size Management:**
- Default max: 1MB
- Exceeding limit raises `SDKJSONDecodeError`
- Prevents memory exhaustion from malformed data

---

## Control Protocol

The Control Protocol facilitates bidirectional communication between the SDK and the Claude CLI process.

### CLI-to-SDK Request Types

**can_use_tool:**
- CLI requests permission before executing a tool
- Includes `tool_name` and `input`
- SDK invokes `can_use_tool` callback
- Returns `PermissionResultAllow` or `PermissionResultDeny`

**hook_callback:**
- CLI invokes registered lifecycle hooks
- Includes `callback_id` to lookup callback
- SDK executes callback and returns output
- Converts Python field names (`async_` → `async`)

**mcp_message:**
- Routes JSONRPC messages to SDK MCP servers
- Specifies `server_name` and `message` payload
- Handles `initialize`, `tools/list`, `tools/call`

**initialize:**
- Handshake when SDK connects in streaming mode
- SDK registers configured hooks
- CLI responds with supported capabilities

### SDK-to-CLI Request Types

**interrupt:**
- Stops current agent operation
- Exposed via `ClaudeSDKClient.interrupt()`

**set_permission_mode:**
- Changes permission mode during conversation
- Values: `default`, `acceptEdits`, `bypassPermissions`, `plan`

**set_model:**
- Switches AI model mid-conversation

### Request/Response Correlation

```
┌─────────┐                    ┌─────────┐
│   SDK   │                    │   CLI   │
└────┬────┘                    └────┬────┘
     │                              │
     │  control_request             │
     │  request_id: "abc123"        │
     │  ─────────────────────────>  │
     │                              │
     │  control_response            │
     │  request_id: "abc123"        │
     │  <─────────────────────────  │
     │                              │
```

1. **Request Generation**: Unique `request_id` combining counter + random bytes
2. **Event Creation**: `anyio.Event` stored in `pending_control_responses`
3. **Response Handling**: `_read_messages` task matches incoming `request_id`
4. **Correlation**: Result stored in `pending_control_results`, event set
5. **Result Retrieval**: Original caller retrieves result

---

## Custom Tools (SDK MCP Servers)

Custom tools are Python functions that Claude can invoke during conversations, running in-process without subprocess overhead.

### @tool Decorator

Transforms an async Python function into a tool:

```python
from claude_agent_sdk import tool
from typing import Any

@tool("add", "Add two numbers", {"a": float, "b": float})
async def add(args: dict[str, Any]) -> dict[str, Any]:
    result = args["a"] + args["b"]
    return {"content": [{"type": "text", "text": f"Result: {result}"}]}
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Unique tool identifier |
| `description` | `str` | Human-readable explanation |
| `input_schema` | `dict \| TypedDict \| JSONSchema` | Input parameters definition |

**Handler Requirements:**
- Must be `async` function
- Accepts single `dict[str, Any]` argument
- Returns `dict[str, Any]` with `"content"` key
- Include `"is_error": True` for errors

### create_sdk_mcp_server()

Bundles multiple tools into an MCP server:

```python
from claude_agent_sdk import create_sdk_mcp_server

calculator = create_sdk_mcp_server(
    name="calculator",
    version="1.0.0",
    tools=[add, subtract, multiply, divide]
)
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Server identifier |
| `version` | `str` | Version string (default: "1.0.0") |
| `tools` | `list[SdkMcpTool]` | List of @tool decorated functions |

### McpSdkServerConfig

Returned by `create_sdk_mcp_server()`:

```python
class McpSdkServerConfig(TypedDict):
    type: Literal["sdk"]
    name: str
    instance: McpServer
```

### Complete Custom Tool Example

```python
import anyio
from typing import Any
from claude_agent_sdk import (
    tool,
    create_sdk_mcp_server,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    TextBlock,
)

# Define tools
@tool("add", "Add two numbers", {"a": float, "b": float})
async def add(args: dict[str, Any]) -> dict[str, Any]:
    result = args["a"] + args["b"]
    return {"content": [{"type": "text", "text": f"{args['a']} + {args['b']} = {result}"}]}

@tool("subtract", "Subtract two numbers", {"a": float, "b": float})
async def subtract(args: dict[str, Any]) -> dict[str, Any]:
    result = args["a"] - args["b"]
    return {"content": [{"type": "text", "text": f"{args['a']} - {args['b']} = {result}"}]}

@tool("multiply", "Multiply two numbers", {"a": float, "b": float})
async def multiply(args: dict[str, Any]) -> dict[str, Any]:
    result = args["a"] * args["b"]
    return {"content": [{"type": "text", "text": f"{args['a']} × {args['b']} = {result}"}]}

@tool("divide", "Divide two numbers", {"a": float, "b": float})
async def divide(args: dict[str, Any]) -> dict[str, Any]:
    if args["b"] == 0:
        return {
            "content": [{"type": "text", "text": "Error: Division by zero"}],
            "is_error": True
        }
    result = args["a"] / args["b"]
    return {"content": [{"type": "text", "text": f"{args['a']} ÷ {args['b']} = {result}"}]}

# Create MCP server
calculator = create_sdk_mcp_server(
    name="calculator",
    version="1.0.0",
    tools=[add, subtract, multiply, divide]
)

# Use with ClaudeSDKClient
async def main():
    options = ClaudeAgentOptions(
        mcp_servers={"calc": calculator},
        allowed_tools=[
            "mcp__calc__add",
            "mcp__calc__subtract",
            "mcp__calc__multiply",
            "mcp__calc__divide",
        ],
        permission_mode="acceptEdits",
    )
    
    async with ClaudeSDKClient(options=options) as client:
        await client.query("Calculate: (10 + 5) * 3")
        
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(block.text)

anyio.run(main)
```

---

## Permission Callbacks

Permission callbacks provide fine-grained control over tool execution.

### can_use_tool Callback

```python
async def can_use_tool(
    tool_name: str,
    input_data: dict[str, Any],
    context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    ...
```

### ToolPermissionContext

Context information passed to the callback:

```python
@dataclass
class ToolPermissionContext:
    suggestions: list[str]  # Permission suggestions from CLI
    signal: None  # Reserved for future abort signal
```

### PermissionResultAllow

Allow tool execution:

```python
@dataclass
class PermissionResultAllow:
    updated_input: dict[str, Any] | None = None  # Modified input
    updated_permissions: dict | None = None  # Dynamic rule changes
```

### PermissionResultDeny

Deny tool execution:

```python
@dataclass
class PermissionResultDeny:
    message: str | None = None  # Denial reason
    interrupt: bool = False  # Stop execution entirely
```

### Permission Handling Examples

**Allow All:**

```python
from claude_agent_sdk import PermissionResultAllow, ToolPermissionContext

async def allow_all(
    tool_name: str,
    input_data: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow:
    return PermissionResultAllow()
```

**Deny Dangerous Commands:**

```python
from claude_agent_sdk import PermissionResultDeny, ToolPermissionContext

async def deny_dangerous(
    tool_name: str,
    input_data: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    if tool_name == "Bash":
        command = input_data.get("command", "")
        if "rm -rf" in command:
            return PermissionResultDeny(
                message="Dangerous command blocked",
                interrupt=True
            )
    return PermissionResultAllow()
```

**Modify Tool Input:**

```python
from claude_agent_sdk import PermissionResultAllow, ToolPermissionContext

async def add_safe_mode(
    tool_name: str,
    input_data: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow:
    modified = input_data.copy()
    modified["safe_mode"] = True
    return PermissionResultAllow(updated_input=modified)
```

**Integration with Options:**

```python
from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    can_use_tool=deny_dangerous,
    allowed_tools=["Read", "Write", "Bash"],
)
```

---

## Lifecycle Hooks

Hooks are Python callbacks invoked at specific points during agent execution.

### Hook Events

| Event | When Invoked |
|-------|--------------|
| `PreToolUse` | Before tool execution |
| `PostToolUse` | After tool execution |
| `UserPromptSubmit` | User message submitted |
| `Stop` | Agent session stopping |
| `SubagentStop` | Subagent completed |
| `PreCompact` | Before transcript compaction |

### Hook Input Types

**BaseHookInput (common fields):**

```python
@dataclass
class BaseHookInput:
    session_id: str
    transcript_path: str
    cwd: str
    permission_mode: str
```

**PreToolUseHookInput:**

```python
@dataclass
class PreToolUseHookInput(BaseHookInput):
    hook_event_name: Literal["PreToolUse"]
    tool_name: str
    tool_input: dict[str, Any]
```

**PostToolUseHookInput:**

```python
@dataclass
class PostToolUseHookInput(BaseHookInput):
    hook_event_name: Literal["PostToolUse"]
    tool_name: str
    tool_input: dict[str, Any]
    tool_response: Any
```

**UserPromptSubmitHookInput:**

```python
@dataclass
class UserPromptSubmitHookInput(BaseHookInput):
    hook_event_name: Literal["UserPromptSubmit"]
    prompt: str
```

**StopHookInput:**

```python
@dataclass
class StopHookInput(BaseHookInput):
    hook_event_name: Literal["Stop"]
    stop_hook_active: bool
```

**PreCompactHookInput:**

```python
@dataclass
class PreCompactHookInput(BaseHookInput):
    hook_event_name: Literal["PreCompact"]
    trigger: Literal["manual", "auto"]
    custom_instructions: str | None
```

### Hook Output Types

**SyncHookJSONOutput:**

```python
class SyncHookJSONOutput(TypedDict, total=False):
    continue_: bool  # Proceed with execution (default: True)
    suppressOutput: bool  # Hide stdout from transcript
    stopReason: str  # Message if continue_ is False
    decision: Literal["block"]  # Blocking behavior
    systemMessage: str  # Warning message for user
    reason: str  # Feedback for Claude
    hookSpecificOutput: dict  # Event-specific controls
```

**PreToolUseHookSpecificOutput:**

```python
class PreToolUseHookSpecificOutput(TypedDict, total=False):
    permissionDecision: Literal["allow", "deny", "ask"]
    permissionDecisionReason: str
    updatedInput: dict[str, Any]
```

**AsyncHookJSONOutput:**

```python
class AsyncHookJSONOutput(TypedDict, total=False):
    async_: bool  # Defer execution (True)
    asyncTimeout: int  # Timeout in milliseconds
```

### Hook Examples

**Block Dangerous Bash Commands:**

```python
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher

async def check_bash_command(input_data, tool_use_id, context):
    tool_name = input_data["tool_name"]
    tool_input = input_data["tool_input"]
    
    if tool_name != "Bash":
        return {}
    
    command = tool_input.get("command", "")
    blocked_patterns = ["rm -rf", "sudo", "> /dev/"]
    
    for pattern in blocked_patterns:
        if pattern in command:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Blocked: {pattern}",
                }
            }
    
    return {}

options = ClaudeAgentOptions(
    allowed_tools=["Bash"],
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[check_bash_command]),
        ],
    }
)
```

**Log All Tool Usage:**

```python
async def log_tool_use(input_data, tool_use_id, context):
    print(f"Tool: {input_data['tool_name']}")
    print(f"Input: {input_data['tool_input']}")
    return {}  # Don't modify behavior

async def log_tool_result(input_data, tool_use_id, context):
    print(f"Result: {input_data['tool_response']}")
    return {}

options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [HookMatcher(matcher="*", hooks=[log_tool_use])],
        "PostToolUse": [HookMatcher(matcher="*", hooks=[log_tool_result])],
    }
)
```

---

## External MCP Servers

External MCP servers run as separate processes or services.

### McpServerConfig

Union type for MCP server configurations:

```python
McpServerConfig = (
    McpStdioServerConfig |
    McpSSEServerConfig |
    McpHttpServerConfig |
    McpSdkServerConfig
)
```

### StdioMcpServerConfig

For servers communicating via stdin/stdout:

```python
class McpStdioServerConfig(TypedDict, total=False):
    type: Literal["stdio"]  # Optional for backwards compatibility
    command: str  # Executable command
    args: list[str]  # Command arguments
    env: dict[str, str]  # Environment variables
```

**Example:**

```python
options = ClaudeAgentOptions(
    mcp_servers={
        "filesystem": {
            "type": "stdio",
            "command": "npx",
            "args": ["@modelcontextprotocol/server-filesystem", "/path"],
        }
    }
)
```

### SseMcpServerConfig

For servers using Server-Sent Events over HTTP:

```python
class McpSSEServerConfig(TypedDict):
    type: Literal["sse"]
    url: str  # SSE endpoint URL
    headers: dict[str, str]  # Optional HTTP headers
```

**Example:**

```python
options = ClaudeAgentOptions(
    mcp_servers={
        "remote": {
            "type": "sse",
            "url": "https://mcp.example.com/sse",
            "headers": {"Authorization": "Bearer token"},
        }
    }
)
```

---

## Session Management

### Session ID

Every interaction generates a unique `session_id` returned in `ResultMessage`:

```python
async for msg in client.receive_response():
    if isinstance(msg, ResultMessage):
        print(f"Session: {msg.session_id}")
```

### Continue Conversation

Resume the most recent session:

```python
options = ClaudeAgentOptions(
    continue_conversation=True  # Maps to --continue flag
)
```

### Resume Sessions

Resume a specific session by ID:

```python
options = ClaudeAgentOptions(
    resume="session-abc123"  # Maps to --resume flag
)
```

### Conversation Forking

Create a new session branching from an existing one:

```python
options = ClaudeAgentOptions(
    resume="session-abc123",
    fork_session=True  # Inherits history, creates new ID
)
```

**Use Cases:**
- A/B testing different approaches
- Multi-user scenarios
- Exploring alternatives without altering original

---

## Resource Limits and Cost Control

### max_turns

Limits conversation rounds:

```python
options = ClaudeAgentOptions(
    max_turns=10  # Stop after 10 turns
)
```

When reached, returns `ResultMessage` with `num_turns` field.

### max_budget_usd

Sets maximum spending limit:

```python
options = ClaudeAgentOptions(
    max_budget_usd=1.00  # Maximum $1.00
)
```

**Behavior:**
- Checked after each API call
- Final cost may slightly exceed limit
- On exceed: `ResultMessage.subtype = "error_max_budget_usd"`

### max_thinking_tokens

Limits extended thinking tokens:

```python
options = ClaudeAgentOptions(
    max_thinking_tokens=8000  # Limit reasoning tokens
)
```

### Monitoring Costs

Monitor via `ResultMessage`:

```python
async for msg in client.receive_response():
    if isinstance(msg, ResultMessage):
        print(f"Cost: ${msg.total_cost_usd:.4f}")
        print(f"Turns: {msg.num_turns}")
        print(f"Duration: {msg.duration_ms}ms")
        print(f"Usage: {msg.usage}")
```

**Combining Limits:**

```python
options = ClaudeAgentOptions(
    max_turns=20,
    max_budget_usd=5.00,
    max_thinking_tokens=10000
)
# Session terminates when ANY limit is reached
```

---

## Security and Sandbox Settings

### Permission Modes

| Mode | Description |
|------|-------------|
| `"default"` | Prompt for all actions |
| `"acceptEdits"` | Auto-approve file edits |
| `"plan"` | Planning mode (no execution) |
| `"bypassPermissions"` | Auto-approve all (dangerous) |

**Dynamic Changes:**

```python
await client.set_permission_mode("acceptEdits")
```

### Sandbox Configuration

```python
from claude_agent_sdk import ClaudeAgentOptions, SandboxSettings

options = ClaudeAgentOptions(
    sandbox=SandboxSettings(
        enabled=True,  # Enable bash sandboxing
        autoAllowBashIfSandboxed=True,  # Auto-approve sandboxed commands
        excludedCommands=["git", "docker"],  # Run outside sandbox
        allowUnsandboxedCommands=False,  # Force sandbox
        enableWeakerNestedSandbox=False,  # Linux Docker only
    )
)
```

**SandboxSettings Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` | Enable bash sandboxing (macOS/Linux) |
| `autoAllowBashIfSandboxed` | `bool` | Auto-approve sandboxed commands |
| `excludedCommands` | `list[str]` | Commands running outside sandbox |
| `allowUnsandboxedCommands` | `bool` | Allow bypassing sandbox |
| `network` | `SandboxNetworkConfig` | Network access configuration |
| `ignoreViolations` | `SandboxIgnoreViolations` | Violations to ignore |
| `enableWeakerNestedSandbox` | `bool` | Weaker sandbox for Docker (Linux) |

### Security Best Practices

1. **Avoid `bypassPermissions`** unless absolutely necessary
2. **Use `can_use_tool` callback** for custom permission logic
3. **Configure `excludedCommands` carefully** to minimize attack surface
4. **Use hooks** to audit and log all tool usage
5. **Set `max_budget_usd`** to prevent runaway costs
6. **Validate tool inputs** in custom tools before execution

---

## Structured Outputs

Generate validated JSON outputs conforming to JSON Schema.

### output_format Configuration

```python
options = ClaudeAgentOptions(
    output_format={
        "type": "json_schema",
        "schema": {
            "type": "object",
            "properties": {
                "field": {"type": "string"}
            },
            "required": ["field"]
        }
    }
)
```

### JSON Schema Definition

Supports standard JSON Schema features:
- `type`: object, array, string, number, boolean
- `properties`: Define object fields
- `required`: Required field names
- `enum`: Constrained values
- Nested objects and arrays

### Structured Output Examples

**Simple Schema:**

```python
schema = {
    "type": "object",
    "properties": {
        "file_count": {"type": "number"},
        "has_tests": {"type": "boolean"},
    },
    "required": ["file_count", "has_tests"],
}

options = ClaudeAgentOptions(
    output_format={"type": "json_schema", "schema": schema},
    permission_mode="acceptEdits",
)

async for msg in query(prompt="Count Python files", options=options):
    if isinstance(msg, ResultMessage):
        output = msg.structured_output
        print(f"Files: {output['file_count']}")
        print(f"Has tests: {output['has_tests']}")
```

**Nested Schema:**

```python
schema = {
    "type": "object",
    "properties": {
        "analysis": {
            "type": "object",
            "properties": {
                "word_count": {"type": "number"},
                "character_count": {"type": "number"},
            },
            "required": ["word_count", "character_count"],
        },
        "words": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["analysis", "words"],
}
```

**Enum Constraints:**

```python
schema = {
    "type": "object",
    "properties": {
        "test_framework": {
            "type": "string",
            "enum": ["pytest", "unittest", "nose", "unknown"],
        },
        "test_count": {"type": "number"},
    },
    "required": ["test_framework"],
}
```

---

## Interactive Streaming Patterns

### Real-time Message Processing

**Using receive_messages():**

```python
async with ClaudeSDKClient(options) as client:
    await client.query("Process this file")
    
    count = 0
    async for msg in client.receive_messages():
        print(msg)
        count += 1
        if count > 10:  # Manual termination
            break
```

**Using receive_response():**

```python
async with ClaudeSDKClient(options) as client:
    await client.query("What is 2+2?")
    
    # Automatically stops at ResultMessage
    messages = [msg async for msg in client.receive_response()]
    result = messages[-1]
```

### Progress Tracking

```python
async for msg in client.receive_response():
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                print(f"Progress: {block.text[:50]}...")
    elif isinstance(msg, ResultMessage):
        print(f"Completed in {msg.duration_ms}ms")
        print(f"Cost: ${msg.total_cost_usd:.4f}")
        print(f"Turns: {msg.num_turns}")
```

### Building Interactive Chat Applications

```python
import anyio
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ResultMessage,
)

async def chat():
    options = ClaudeAgentOptions(
        system_prompt="You are a helpful assistant",
        max_turns=50,
        permission_mode="acceptEdits",
    )
    
    async with ClaudeSDKClient(options=options) as client:
        while True:
            user_input = input("You: ")
            if user_input.lower() in ["quit", "exit"]:
                break
            
            await client.query(user_input)
            
            print("Claude: ", end="", flush=True)
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            print(block.text, end="", flush=True)
                elif isinstance(msg, ResultMessage):
                    print(f"\n[Cost: ${msg.total_cost_usd:.4f}]")

anyio.run(chat)
```

---

## Error Handling Patterns

### Exception Types

| Exception | Description |
|-----------|-------------|
| `ClaudeSDKError` | Base exception for all SDK errors |
| `CLINotFoundError` | Claude CLI binary not found |
| `CLIConnectionError` | Connection issues with CLI |
| `ProcessError` | CLI process failed with non-zero exit |
| `SDKJSONDecodeError` | Failed to parse CLI JSON response |

### Error Recovery Strategies

**Tool Handler Errors:**

```python
@tool("safe_operation", "Performs safe operation", {"input": str})
async def safe_operation(args: dict[str, Any]) -> dict[str, Any]:
    try:
        result = perform_operation(args["input"])
        return {"content": [{"type": "text", "text": result}]}
    except ValueError as e:
        return {
            "content": [{"type": "text", "text": f"Error: {e}"}],
            "is_error": True
        }
```

**Permission Callback Errors:**

```python
async def safe_permission(tool_name, input_data, context):
    try:
        # Custom logic
        return PermissionResultAllow()
    except Exception as e:
        # Return deny on error for safety
        return PermissionResultDeny(message=str(e))
```

**Connection Errors:**

```python
from claude_agent_sdk import CLINotFoundError, ProcessError

try:
    async with ClaudeSDKClient(options) as client:
        # ...
except CLINotFoundError:
    print("Claude CLI not found. Install with: curl -fsSL https://claude.ai/install.sh | bash")
except ProcessError as e:
    print(f"CLI process failed with exit code: {e.exit_code}")
```

### Debugging Techniques

**Enable Logging:**

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Capture Stderr:**

```python
options = ClaudeAgentOptions(
    extra_args=["--debug-to-stderr"],
    stderr=lambda line: print(f"STDERR: {line}"),
)
```

**Use Context Manager:**

```python
# Ensures cleanup even on exception
async with ClaudeSDKClient(options) as client:
    try:
        await client.query("risky operation")
        async for msg in client.receive_response():
            process(msg)
    except Exception as e:
        print(f"Error: {e}")
        # Client properly disconnected
```

---

## Tool Integration Examples

### Built-in Tools

The `claude_code` preset includes standard tools:

| Tool | Description |
|------|-------------|
| `Read` | Read file contents |
| `Write` | Write to files |
| `Edit` | Edit existing files |
| `Bash` | Execute shell commands |
| `Grep` | Search file contents |
| `Glob` | Find files by pattern |
| `WebFetch` | Fetch web content |
| `Task` | Task management |

**Configuring Tools:**

```python
# Use default tools
options = ClaudeAgentOptions(
    tools={"type": "preset", "preset": "claude_code"}
)

# Specify exact tools
options = ClaudeAgentOptions(
    tools=["Read", "Edit", "Bash"]
)

# Whitelist filter
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Write"]  # Only these allowed
)

# Blacklist filter
options = ClaudeAgentOptions(
    disallowed_tools=["Bash", "WebFetch"]  # These disabled
)

# Disable all built-in tools
options = ClaudeAgentOptions(
    tools=[]  # Only custom MCP tools available
)
```

### Custom Tool Examples

**File Processor:**

```python
@tool("process_file", "Process and analyze a file", {
    "path": str,
    "operation": str
})
async def process_file(args: dict[str, Any]) -> dict[str, Any]:
    path = args["path"]
    operation = args["operation"]
    
    if operation == "count_lines":
        with open(path) as f:
            count = len(f.readlines())
        return {"content": [{"type": "text", "text": f"Lines: {count}"}]}
    
    return {
        "content": [{"type": "text", "text": f"Unknown operation: {operation}"}],
        "is_error": True
    }
```

**API Client:**

```python
import httpx

@tool("api_call", "Make an API request", {
    "url": str,
    "method": str,
    "body": dict
})
async def api_call(args: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=args["method"],
            url=args["url"],
            json=args.get("body")
        )
        return {
            "content": [{
                "type": "text",
                "text": f"Status: {response.status_code}\nBody: {response.text}"
            }]
        }
```

**Database Query:**

```python
import aiosqlite

@tool("query_db", "Execute SQL query", {"sql": str, "params": list})
async def query_db(args: dict[str, Any]) -> dict[str, Any]:
    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute(args["sql"], args.get("params", []))
        rows = await cursor.fetchall()
        return {
            "content": [{
                "type": "text",
                "text": f"Results: {rows}"
            }]
        }
```

---

## Project Structure

### Directory Layout

```
claude-agent-sdk-python/
├── README.md                          # Documentation
├── pyproject.toml                     # Project metadata and config
├── scripts/
│   ├── download_cli.py                # CLI download script
│   ├── build_wheel.py                 # Wheel building script
│   └── update_version.py              # Version update script
├── examples/
│   ├── mcp_calculator.py              # Custom tools example
│   ├── quick_start.py                 # Basic usage example
│   ├── streaming_mode.py              # ClaudeSDKClient example
│   └── streaming_mode_ipython.py      # Interactive example
├── src/claude_agent_sdk/
│   ├── __init__.py                    # Public exports
│   ├── _version.py                    # SDK version
│   ├── _cli_version.py                # Bundled CLI version
│   ├── _errors.py                     # Exception classes
│   ├── client.py                      # ClaudeSDKClient
│   ├── query.py                       # query() function
│   ├── types.py                       # Type definitions
│   ├── _bundled/                      # CLI binary location
│   └── _internal/
│       ├── client.py                  # Internal client
│       ├── query.py                   # Control protocol
│       ├── message_parser.py          # JSON parsing
│       └── transport/
│           ├── __init__.py            # Transport base
│           └── subprocess_cli.py      # CLI subprocess
├── tests/                             # Unit/integration tests
└── e2e-tests/                         # End-to-end tests
```

### Modules and Purposes

| Module | Purpose |
|--------|---------|
| `claude_agent_sdk` | Top-level package with public API |
| `claude_agent_sdk.query` | Simple query function |
| `claude_agent_sdk.client` | Interactive ClaudeSDKClient |
| `claude_agent_sdk.types` | Type definitions and dataclasses |
| `claude_agent_sdk._errors` | Custom exceptions |
| `claude_agent_sdk._internal.query` | Control protocol implementation |
| `claude_agent_sdk._internal.transport` | CLI subprocess management |

---

## Testing Strategy

### Test Categories

**Unit Tests:**
- Validate individual components in isolation
- Mock external dependencies
- Location: `tests/` directory

**Integration Tests:**
- Verify component interactions
- Mock CLI process with simulated responses
- Location: `tests/` directory

**End-to-End Tests:**
- Validate entire SDK stack
- Require real CLI and API key
- Marked with `@pytest.mark.e2e`
- Location: `e2e-tests/` directory

### Test Fixtures and Mocking

**Mocking SubprocessCLITransport:**

```python
from unittest.mock import patch, AsyncMock

@patch("claude_agent_sdk._internal.transport.subprocess_cli.SubprocessCLITransport")
async def test_query(mock_transport):
    mock_instance = AsyncMock()
    mock_transport.return_value = mock_instance
    
    # Configure mock responses
    mock_instance.read_messages.return_value = async_iter([
        {"type": "assistant", "content": [{"type": "text", "text": "Hello"}]},
        {"type": "result", "subtype": "success"}
    ])
    
    # Test
    messages = [msg async for msg in query("Hi")]
    assert len(messages) == 2
```

**MockTextReceiveStream:**

```python
class MockTextReceiveStream:
    def __init__(self, lines: list[str]):
        self.lines = iter(lines)
    
    async def __anext__(self):
        try:
            return next(self.lines)
        except StopIteration:
            raise StopAsyncIteration
```

### Running Tests

**Unit Tests:**

```bash
pytest tests/ -v
```

**With Coverage:**

```bash
pytest tests/ -v --cov=claude_agent_sdk --cov-report=xml
```

**E2E Tests (requires API key):**

```bash
export ANTHROPIC_API_KEY=your_key
pytest e2e-tests/ -v -m e2e
```

**All Tests:**

```bash
pytest -v
```

---

## Build and Release Process

### Wheel Building

The `scripts/build_wheel.py` script:
1. Optionally updates package version
2. Downloads Claude CLI via `scripts/download_cli.py`
3. Copies CLI to `src/claude_agent_sdk/_bundled/`
4. Builds wheel using `python -m build --wheel`
5. Retags wheel as platform-specific
6. Builds source distribution
7. Validates with `twine check`

### CLI Bundling

Platform-specific CLI binaries:
- Linux x86_64: `claude-linux-x64`
- Linux ARM64: `claude-linux-arm64`
- macOS: `claude-macos` (universal)
- Windows: `claude-win32-x64.exe`

### GitHub Actions Workflows

**publish.yml:**
1. `test` job: pytest across Python 3.10-3.13
2. `lint` job: ruff and mypy checks
3. `build-wheels` job: Platform-specific builds
4. `publish` job: Version update, PyPI upload, PR creation

**create-release-tag.yml:**
- Triggered on merged release PR
- Creates Git tag
- Creates GitHub Release with notes

**Test Matrix:**

| Python | Ubuntu | macOS | Windows |
|--------|--------|-------|---------|
| 3.10 | ✅ | ✅ | ✅ |
| 3.11 | ✅ | ✅ | ✅ |
| 3.12 | ✅ | ✅ | ✅ |
| 3.13 | ✅ | ✅ | ✅ |

---

## Code Quality Standards

### Mypy Configuration

Strict type checking enabled in `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.10"
strict = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_return_any = true
warn_unused_configs = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true
```

### Ruff Rules

Linting configuration in `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py310"
line-length = 88

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "PTH", # flake8-use-pathlib
    "SIM", # flake8-simplify
]
ignore = ["E501"]  # Handled by formatter

[tool.ruff.lint.isort]
known-first-party = ["claude_agent_sdk"]
```

### CI Quality Gates

Before any release:
1. **pytest**: All tests must pass
2. **ruff check**: No linting errors
3. **ruff format --check**: Consistent formatting
4. **mypy**: No type errors

```bash
# Run locally
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/
pytest tests/ -v
```

---

## Skills System

The Claude Agent SDK has a **native Skills system** that uses filesystem-based `SKILL.md` files. Skills are automatically discovered and invoked by Claude based on context. This is complemented by programmatic approaches for dynamic context injection.

### Native Skills (Filesystem-Based)

Skills are defined as `SKILL.md` files in specific directories. Claude autonomously chooses when to use them based on task context.

#### Skill Locations

| Location | Type | Description |
|----------|------|-------------|
| `.claude/skills/` | Project Skills | Shared via git, loaded with `setting_sources=["project"]` |
| `~/.claude/skills/` | User Skills | Personal skills across all projects, loaded with `setting_sources=["user"]` |
| Plugin directories | Plugin Skills | Bundled with installed Claude Code plugins |

#### Creating a Skill

Create a `SKILL.md` file in the appropriate directory:

```markdown
<!-- .claude/skills/pdf-extractor/SKILL.md -->
# PDF Text Extractor

## Description
Extract text content from PDF files using various methods.

## When to Use
- User asks to extract text from a PDF
- User wants to analyze PDF content
- User needs to convert PDF to text

## Instructions
1. Check if the PDF file exists
2. Use pdftotext or similar tool to extract content
3. Handle multi-page documents appropriately
4. Return formatted text output

## Example Usage
"Extract text from invoice.pdf"
"Get the content from report.pdf"
```

#### Using Skills in the SDK

**Important:** Skills require explicit configuration to load:

```python
from claude_agent_sdk import query, ClaudeAgentOptions

# Load Skills from filesystem
options = ClaudeAgentOptions(
    cwd="/path/to/project",
    setting_sources=["user", "project"],  # REQUIRED to load Skills
    allowed_tools=["Skill", "Read", "Bash"]  # Must include "Skill" tool
)

async for message in query(
    prompt="Extract text from invoice.pdf",
    options=options
):
    print(message)
    # Claude automatically invokes the PDF Extractor skill
```

#### Key Points About Native Skills

1. **Filesystem artifacts only**: Unlike custom tools, Skills cannot be registered programmatically
2. **Automatic invocation**: Claude decides when to use Skills based on task context
3. **Requires `setting_sources`**: By default, the SDK does NOT load filesystem settings
4. **Requires `"Skill"` in `allowed_tools`**: Must explicitly enable the Skill tool

### CLAUDE.md Project Instructions

CLAUDE.md files provide project-specific instructions that are always active (similar to "always-on" skills):

```markdown
<!-- CLAUDE.md in project root -->
# Project Guidelines

## Code Style
- Use TypeScript strict mode
- Follow ESLint configuration
- Prefer functional components in React

## Testing Requirements
- All new features must have tests
- Minimum 80% coverage
- Use Jest and React Testing Library
```

**Critical**: The `claude_code` preset alone does **NOT** load CLAUDE.md files:

```python
# ❌ WRONG - CLAUDE.md will NOT be loaded
options = ClaudeAgentOptions(
    system_prompt={"type": "preset", "preset": "claude_code"}
)

# ✅ CORRECT - Explicitly load project settings
options = ClaudeAgentOptions(
    system_prompt={"type": "preset", "preset": "claude_code"},
    setting_sources=["project"]  # REQUIRED for CLAUDE.md
)
```

### Skills System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SKILLS SYSTEM COMPONENTS                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    FILESYSTEM SKILLS (Native)                        │    │
│  │                                                                      │    │
│  │  ~/.claude/skills/           .claude/skills/        Plugin Skills    │    │
│  │  (User Skills)               (Project Skills)       (Bundled)        │    │
│  │                                                                      │    │
│  │  ➜ Loaded via setting_sources=["user", "project"]                   │    │
│  │  ➜ Requires "Skill" in allowed_tools                                │    │
│  │  ➜ Auto-invoked by Claude based on context                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │  System Prompt  │  │  Custom Tools   │  │ Lifecycle Hooks │              │
│  │  Customization  │  │  (SDK MCP)      │  │                 │              │
│  │  + CLAUDE.md    │  │                 │  │                 │              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
│           │                    │                    │                        │
│           ▼                    ▼                    ▼                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    ClaudeAgentOptions                                │    │
│  │  • system_prompt      (static/dynamic knowledge)                     │    │
│  │  • setting_sources    (load CLAUDE.md, skills, settings)            │    │
│  │  • mcp_servers        (specialized capabilities)                     │    │
│  │  • hooks              (event-driven context injection)               │    │
│  │  • can_use_tool       (permission-based context)                     │    │
│  │  • agents             (programmatic subagents)                       │    │
│  │  • plugins            (load plugin bundles)                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       TRIGGER MECHANISMS                             │    │
│  │                                                                      │    │
│  │  • Always Active (system_prompt, CLAUDE.md)                          │    │
│  │  • Context-Based (native Skills - auto-invoked)                      │    │
│  │  • Tool-Based (mcp_servers, can_use_tool)                           │    │
│  │  • Event-Driven (hooks: PreToolUse, PostToolUse, etc.)              │    │
│  │  • Session-Based (resume, fork_session)                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Programmatic Subagents

Define specialized agents inline that Claude can delegate tasks to:

```python
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    agents={
        'code-reviewer': {
            'description': 'Expert code review specialist. Use for quality, security, and maintainability reviews.',
            'prompt': '''You are a code review specialist with expertise in security, performance, and best practices.

When reviewing code:
- Identify security vulnerabilities
- Check for performance issues
- Verify adherence to coding standards
- Suggest specific improvements

Be thorough but concise in your feedback.''',
            'tools': ['Read', 'Grep', 'Glob'],
            'model': 'sonnet'
        },
        'test-runner': {
            'description': 'Runs and analyzes test suites. Use for test execution and coverage analysis.',
            'prompt': '''You are a test execution specialist. Run tests and provide clear analysis of results.

Focus on:
- Running test commands
- Analyzing test output
- Identifying failing tests
- Suggesting fixes for failures''',
            'tools': ['Bash', 'Read', 'Grep'],
            'model': 'sonnet'
        },
        'performance-optimizer': {
            'description': 'Use PROACTIVELY when code changes might impact performance.',
            'prompt': 'You are a performance optimization specialist...',
            'tools': ['Read', 'Edit', 'Bash', 'Grep'],
            'model': 'sonnet'
        }
    }
)

async for message in query(
    prompt="Review the authentication module for security issues",
    options=options
):
    print(message)
```

#### Common Tool Combinations for Subagents

| Agent Type | Tools | Use Case |
|------------|-------|----------|
| Read-only (analysis, review) | `['Read', 'Grep', 'Glob']` | Code review, security audit |
| Test execution | `['Bash', 'Read', 'Grep']` | Running tests, CI/CD |
| Code modification | `['Read', 'Edit', 'Write', 'Grep', 'Glob']` | Refactoring, fixes |

### Plugins System

Load plugin bundles that provide commands, agents, skills, and more:

```python
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    plugins=[
        {"type": "local", "path": "./my-plugin"},
        {"type": "local", "path": "~/.claude/custom-plugins/shared-plugin"}
    ]
)

async for message in query(prompt="Hello", options=options):
    # Check what plugins loaded
    if message.type == "system" and message.subtype == "init":
        print("Plugins:", message.data.get("plugins"))
        print("Commands:", message.data.get("slash_commands"))
```

### Skill Definition Patterns (Programmatic)

### Skill Definition Patterns

#### Pattern 1: Always-Active Skills (System Prompt)

Skills that are always active, providing general guidance or domain expertise:

```python
from claude_agent_sdk import ClaudeAgentOptions

# Define skill content
PYTHON_EXPERT_SKILL = """
You are an expert Python developer with deep knowledge of:
- Python best practices and PEP standards
- Type hints and static analysis
- Async programming with asyncio
- Testing with pytest

Always:
- Use type hints for function signatures
- Follow PEP 8 style guidelines
- Suggest tests for any code changes
- Consider edge cases and error handling
"""

SECURITY_AUDIT_SKILL = """
When reviewing or writing code, always consider:
- Input validation and sanitization
- SQL injection prevention
- XSS and CSRF protection
- Secure credential handling
- Principle of least privilege
"""

# Combine skills into system prompt
options = ClaudeAgentOptions(
    system_prompt=f"""
{PYTHON_EXPERT_SKILL}

{SECURITY_AUDIT_SKILL}

Apply these guidelines to all tasks.
""",
    allowed_tools=["Read", "Write", "Bash"],
)
```

#### Pattern 2: Keyword-Triggered Skills (Custom Tools)

Skills activated when specific capabilities are needed:

```python
from typing import Any
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions

# Database skill - activated when database operations are needed
@tool("query_database", "Execute SQL queries safely", {
    "query": str,
    "params": list,
    "database": str
})
async def database_skill(args: dict[str, Any]) -> dict[str, Any]:
    """Specialized database interaction skill."""
    # Sanitize and validate query
    query = args["query"]
    params = args.get("params", [])
    database = args.get("database", "default")
    
    # Execute with connection pooling
    result = await execute_query(database, query, params)
    
    return {
        "content": [{
            "type": "text",
            "text": f"Query executed successfully:\n{result}"
        }]
    }

# API integration skill
@tool("call_api", "Make authenticated API requests", {
    "endpoint": str,
    "method": str,
    "body": dict,
    "headers": dict
})
async def api_skill(args: dict[str, Any]) -> dict[str, Any]:
    """Specialized API integration skill."""
    import httpx
    
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=args["method"],
            url=args["endpoint"],
            json=args.get("body"),
            headers=args.get("headers", {})
        )
        
    return {
        "content": [{
            "type": "text",
            "text": f"Status: {response.status_code}\nResponse: {response.text}"
        }]
    }

# Create MCP server with skills
skills_server = create_sdk_mcp_server(
    name="specialized_skills",
    version="1.0.0",
    tools=[database_skill, api_skill]
)

options = ClaudeAgentOptions(
    mcp_servers={"skills": skills_server},
    allowed_tools=[
        "mcp__skills__query_database",
        "mcp__skills__call_api",
        "Read", "Write"
    ]
)
```

### Complete Hook Events Reference

The Claude Agent SDK provides a comprehensive set of lifecycle hooks for event-driven control:

| Hook Event | When Triggered | Input Fields | Use Case |
|------------|----------------|--------------|----------|
| `PreToolUse` | Before tool execution | `tool_name`, `tool_input` | Validate, block, or modify tool calls |
| `PostToolUse` | After tool execution | `tool_name`, `tool_input`, `tool_response` | Log results, inject follow-up context |
| `UserPromptSubmit` | When user sends prompt | `prompt` | Modify/augment user prompts |
| `SessionStart` | Session begins | Session metadata | Initialize tracking, logging |
| `SessionEnd` | Session ends | Session metadata | Cleanup, final logging |
| `Stop` | Stop signal received | `stop_hook_active` | Handle graceful shutdown |
| `SubagentStop` | Subagent stops | `stop_hook_active` | Handle subagent completion |
| `PreCompact` | Before conversation compaction | Conversation state | Preserve important context |
| `Notification` | Notifications occur | Notification data | Handle system notifications |

#### Hook Output Options

```python
# HookJSONOutput fields
{
    "continue_": True,          # Continue execution (False to stop)
    "stopReason": "string",     # Reason for stopping (if continue_=False)
    "systemMessage": "string",  # Inject system message
    "reason": "string",         # Explanation for decision
    "suppressOutput": False,    # Suppress tool output
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow" | "deny" | "ask",
        "permissionDecisionReason": "string",
        "updatedPrompt": "string",        # For UserPromptSubmit
        "additionalContext": "string"     # Extra context injection
    }
}
```

#### Example: UserPromptSubmit Hook (Modify User Prompts)

```python
from datetime import datetime
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, HookContext

async def add_timestamp_to_prompts(
    input_data: dict,
    tool_use_id: str | None,
    context: HookContext
) -> dict:
    """Add timestamp context to all user prompts."""
    original_prompt = input_data.get('prompt', '')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return {
        'hookSpecificOutput': {
            'hookEventName': 'UserPromptSubmit',
            'updatedPrompt': f"[{timestamp}] {original_prompt}"
        }
    }

options = ClaudeAgentOptions(
    hooks={
        'UserPromptSubmit': [
            HookMatcher(hooks=[add_timestamp_to_prompts])
        ]
    }
)
```

#### Example: PostToolUse Hook (Error Handling)

```python
async def stop_on_critical_error(
    input_data: dict,
    tool_use_id: str | None,
    context: HookContext
) -> dict:
    """Stop execution if critical error detected."""
    tool_response = input_data.get("tool_response", "")
    
    if "critical" in str(tool_response).lower():
        return {
            "continue_": False,
            "stopReason": "Critical error detected - halting for safety",
            "systemMessage": "🛑 Execution stopped due to critical error"
        }
    
    return {"continue_": True}

options = ClaudeAgentOptions(
    hooks={
        "PostToolUse": [
            HookMatcher(matcher="Bash", hooks=[stop_on_critical_error])
        ]
    }
)
```

#### Pattern 3: Event-Triggered Skills (Lifecycle Hooks)

Skills activated at specific points in the agent lifecycle:

```python
from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    HookInput,
    HookContext,
    HookJSONOutput,
)

# Code review skill - activated before any Write operation
async def code_review_skill(
    input_data: HookInput,
    tool_use_id: str | None,
    context: HookContext
) -> HookJSONOutput:
    """Inject code review guidelines before file writes."""
    if input_data["hook_event_name"] == "PreToolUse":
        if input_data["tool_name"] == "Write":
            file_path = input_data["tool_input"].get("file_path", "")
            
            # Inject review context based on file type
            if file_path.endswith(".py"):
                return {
                    "reason": """
Before writing this Python file, ensure:
- All functions have docstrings
- Type hints are present
- Tests exist or are planned
- No hardcoded secrets
""",
                    "continue_": True
                }
            elif file_path.endswith((".js", ".ts")):
                return {
                    "reason": """
Before writing this JavaScript/TypeScript file, ensure:
- Proper error handling
- Input validation
- No console.log in production code
""",
                    "continue_": True
                }
    
    return {}

# Deployment safety skill - activated before Bash commands
async def deployment_skill(
    input_data: HookInput,
    tool_use_id: str | None,
    context: HookContext
) -> HookJSONOutput:
    """Inject deployment safety checks."""
    if input_data["hook_event_name"] == "PreToolUse":
        if input_data["tool_name"] == "Bash":
            command = input_data["tool_input"].get("command", "")
            
            # Check for deployment-related commands
            deployment_keywords = ["deploy", "kubectl", "docker push", "terraform"]
            if any(kw in command for kw in deployment_keywords):
                return {
                    "systemMessage": "⚠️ Deployment command detected. Verify environment and permissions.",
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "ask",
                        "permissionDecisionReason": "Deployment commands require confirmation"
                    }
                }
    
    return {}

# Configure hooks
options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Write", hooks=[code_review_skill]),
            HookMatcher(matcher="Bash", hooks=[deployment_skill]),
        ]
    },
    allowed_tools=["Read", "Write", "Bash"]
)
```

#### Pattern 4: Task-Triggered Skills (Subagents)

Specialized agents for specific task types:

```python
from claude_agent_sdk import ClaudeAgentOptions, AgentDefinition

options = ClaudeAgentOptions(
    agents={
        # Research skill/agent
        "researcher": AgentDefinition(
            description="Research and information gathering specialist",
            prompt="""You are a research specialist. Your role is to:
- Find accurate, up-to-date information
- Cite sources when possible
- Synthesize findings into clear summaries
- Flag any uncertainties or conflicting information
""",
            tools=["WebFetch", "Read"],
            model="sonnet"
        ),
        
        # Code refactoring skill/agent
        "refactorer": AgentDefinition(
            description="Code refactoring and optimization specialist",
            prompt="""You are a code refactoring specialist. Your role is to:
- Identify code smells and anti-patterns
- Suggest performance optimizations
- Improve code readability and maintainability
- Ensure changes don't break functionality
""",
            tools=["Read", "Write", "Bash"],
            model="sonnet"
        ),
        
        # Testing skill/agent
        "tester": AgentDefinition(
            description="Testing and quality assurance specialist",
            prompt="""You are a testing specialist. Your role is to:
- Write comprehensive unit tests
- Create integration test scenarios
- Identify edge cases
- Ensure good test coverage
""",
            tools=["Read", "Write", "Bash"],
            model="sonnet"
        )
    }
)
```

### AgentContext: Managing Skills Dynamically

Create a context manager for dynamic skill injection:

```python
from dataclasses import dataclass, field
from typing import Callable, Any
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

@dataclass
class Skill:
    """A skill that can be injected into agent context."""
    name: str
    content: str
    trigger: str | list[str] | None = None  # None = always active
    source: str = "custom"

@dataclass
class AgentContext:
    """Manages skills and context for Claude agents."""
    skills: list[Skill] = field(default_factory=list)
    system_message_suffix: str = ""
    user_message_prefix: str = ""
    
    def get_active_skills(self, message: str) -> list[Skill]:
        """Get skills that should be active for a given message."""
        active = []
        for skill in self.skills:
            if skill.trigger is None:
                # Always active
                active.append(skill)
            elif isinstance(skill.trigger, str):
                if skill.trigger.lower() in message.lower():
                    active.append(skill)
            elif isinstance(skill.trigger, list):
                if any(t.lower() in message.lower() for t in skill.trigger):
                    active.append(skill)
        return active
    
    def build_system_prompt(self, message: str) -> str:
        """Build system prompt with active skills."""
        active_skills = self.get_active_skills(message)
        
        parts = []
        for skill in active_skills:
            parts.append(f"## {skill.name}\n{skill.content}")
        
        if self.system_message_suffix:
            parts.append(self.system_message_suffix)
        
        return "\n\n".join(parts)
    
    def build_options(self, message: str, base_options: dict = None) -> ClaudeAgentOptions:
        """Build ClaudeAgentOptions with context-aware system prompt."""
        options_dict = base_options or {}
        options_dict["system_prompt"] = self.build_system_prompt(message)
        return ClaudeAgentOptions(**options_dict)

# Usage example
async def main():
    # Define skills
    python_skill = Skill(
        name="Python Expert",
        content="You are an expert Python developer...",
        trigger=["python", "py", ".py"]
    )
    
    database_skill = Skill(
        name="Database Expert",
        content="You are a database specialist...",
        trigger=["sql", "database", "query", "postgres", "mysql"]
    )
    
    general_skill = Skill(
        name="General Guidelines",
        content="Always be helpful and thorough.",
        trigger=None  # Always active
    )
    
    # Create context
    context = AgentContext(
        skills=[python_skill, database_skill, general_skill],
        system_message_suffix="Always explain your reasoning."
    )
    
    # Use with message
    message = "Help me optimize this Python database query"
    options = context.build_options(message, {
        "allowed_tools": ["Read", "Write", "Bash"],
        "max_turns": 10
    })
    
    async with ClaudeSDKClient(options=options) as client:
        await client.query(message)
        async for msg in client.receive_response():
            print(msg)
```

### Skill Trigger Comparison

| Trigger Type | Mechanism | Location | Use Case | Example |
|--------------|-----------|----------|----------|---------|
| **Native Skills** | `SKILL.md` files | `.claude/skills/`, `~/.claude/skills/` | Context-based auto-invocation | PDF extraction |
| **Always Active** | `system_prompt` / `CLAUDE.md` | Code / Project root | General guidelines | Coding standards |
| **Capability-Based** | Custom tools (MCP) | In-process | Specialized capabilities | Database queries |
| **Event-Driven** | Lifecycle hooks | Code | Process control | Pre-deployment checks |
| **Task-Based** | Subagents | Code | Complex workflows | Research, code review |
| **Permission-Based** | `can_use_tool` | Code | Security controls | File access rules |
| **Plugin-Based** | Plugins | Local directories | Bundled functionality | Team workflows |

### Configuration Checklist

| Feature | Required Configuration |
|---------|----------------------|
| Native Skills | `setting_sources=["user", "project"]` + `"Skill"` in `allowed_tools` |
| CLAUDE.md | `setting_sources=["project"]` |
| User settings | `setting_sources=["user"]` |
| Custom tools | `mcp_servers={"name": server}` + tool names in `allowed_tools` |
| Subagents | `agents={"name": {...}}` |
| Plugins | `plugins=[{"type": "local", "path": "..."}]` |
| Hooks | `hooks={"EventName": [HookMatcher(...)]}` |

---

## Multi-Tenant SaaS Platform Architecture

This section covers architectural patterns for building a multi-tenant SaaS platform using the Claude Agent SDK Python.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              YOUR EXISTING SYSTEM                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │   Frontend   │  │  Auth Service│  │   Database   │  │   Billing    │                 │
│  │   (React,    │  │  (JWT/OAuth) │  │  (Postgres,  │  │   Service    │                 │
│  │    Vue, etc) │  │              │  │   Redis)     │  │              │                 │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                 │
└─────────┼─────────────────┼─────────────────┼─────────────────┼─────────────────────────┘
          │                 │                 │                 │
          │    ┌────────────┴─────────────────┴─────────────────┘
          │    │
          ▼    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         CLAUDE AGENT ORCHESTRATION LAYER                                │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                        AgentOrchestrator                                        │    │
│  │                                                                                 │    │
│  │   • Maps users → ClaudeSDKClient instances                                      │    │
│  │   • Manages session lifecycle and isolation                                     │    │
│  │   • Tracks costs per user/organization                                          │    │
│  │   • Enforces resource limits by tier                                            │    │
│  │   • Routes WebSocket streams to frontends                                       │    │
│  │                                                                                 │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                          │                              │                               │
└──────────────────────────┼──────────────────────────────┼───────────────────────────────┘
                           │                              │
           ┌───────────────┘                              └───────────────┐
           │                                                              │
           ▼                                                              ▼
┌──────────────────────────────────────────┐    ┌──────────────────────────────────────────┐
│       CLAUDE AGENT SDK                   │    │           SANDBOX PROVIDER               │
│                                          │    │         (Optional - Daytona)             │
│  ┌────────────────────────────────────┐  │    │                                          │
│  │  ClaudeSDKClient (per session)     │  │    │  ┌────────────────────────────────────┐  │
│  │  • Bidirectional streaming         │  │    │  │  Isolated Execution Environments   │  │
│  │  • Custom tools (SDK MCP)          │  │    │  │                                    │  │
│  │  • Permission callbacks            │  │    │  │  ┌──────────┐ ┌──────────┐         │  │
│  │  • Cost tracking via ResultMessage │  │    │  │  │ User A   │ │ User B   │  ...    │  │
│  └────────────────────────────────────┘  │    │  │  │ Sandbox  │ │ Sandbox  │         │  │
│                                          │    │  │  │ (Docker) │ │ (Docker) │         │  │
│  ┌────────────────────────────────────┐  │    │  │  └──────────┘ └──────────┘         │  │
│  │  Claude CLI (bundled)              │  │    │  └────────────────────────────────────┘  │
│  │  • Communicates with Anthropic API │  │    │                                          │
│  └────────────────────────────────────┘  │    │                                          │
└──────────────────────────────────────────┘    └──────────────────────────────────────────┘

LEGEND:
  ────────►  HTTP/REST Request
  ─ ─ ─ ─►  WebSocket Stream
  ════════►  SDK Communication
```

### Core Components

#### 1. Session Manager

Manages isolated sessions per user/tenant:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import uuid

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    ResultMessage,
)

class SessionStatus(str, Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class UserSession:
    """Represents a user's agent session."""
    session_id: str
    user_id: str
    tenant_id: str
    claude_session_id: Optional[str] = None
    status: SessionStatus = SessionStatus.INITIALIZING
    total_cost_usd: float = 0.0
    total_turns: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

class SessionManager:
    """Manages user sessions with Claude agents."""
    
    def __init__(self, db_client, redis_client=None):
        self.db = db_client
        self.redis = redis_client
        self.active_clients: Dict[str, ClaudeSDKClient] = {}
    
    async def create_session(
        self,
        user_id: str,
        tenant_id: str,
        tier: str = "free",
        initial_message: Optional[str] = None
    ) -> UserSession:
        """Create a new isolated session for a user."""
        session_id = f"sess-{uuid.uuid4().hex[:12]}"
        
        # Get tier-specific limits
        limits = self._get_tier_limits(tier)
        
        # Build options with tenant isolation
        options = ClaudeAgentOptions(
            max_turns=limits["max_turns"],
            max_budget_usd=limits["max_budget_usd"],
            max_thinking_tokens=limits["max_thinking_tokens"],
            system_prompt=self._get_tenant_prompt(tenant_id),
            permission_mode="acceptEdits",
            cwd=f"/workspaces/{tenant_id}/{user_id}",
        )
        
        # Create and connect client
        client = ClaudeSDKClient(options=options)
        await client.connect(initial_message)
        
        # Store session
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id,
            status=SessionStatus.ACTIVE
        )
        
        self.active_clients[session_id] = client
        await self._persist_session(session)
        
        return session
    
    async def send_message(
        self, 
        session_id: str, 
        message: str
    ) -> AsyncIterator[Any]:
        """Send a message and stream responses."""
        client = self.active_clients.get(session_id)
        if not client:
            raise ValueError(f"Session {session_id} not found or not active")
        
        session = await self._get_session(session_id)
        session.last_activity = datetime.utcnow()
        
        await client.query(message)
        
        async for msg in client.receive_response():
            if isinstance(msg, ResultMessage):
                # Track costs
                session.total_cost_usd += msg.total_cost_usd or 0
                session.total_turns += 1
                session.claude_session_id = msg.session_id
                await self._persist_session(session)
            
            yield msg
    
    async def pause_session(self, session_id: str) -> bool:
        """Pause a session (keeps state, releases resources)."""
        session = await self._get_session(session_id)
        client = self.active_clients.pop(session_id, None)
        
        if client:
            await client.disconnect()
        
        session.status = SessionStatus.PAUSED
        await self._persist_session(session)
        return True
    
    async def resume_session(self, session_id: str) -> UserSession:
        """Resume a paused session."""
        session = await self._get_session(session_id)
        
        if session.status != SessionStatus.PAUSED:
            raise ValueError("Session is not paused")
        
        # Reconnect with resume
        tier = await self._get_user_tier(session.user_id)
        limits = self._get_tier_limits(tier)
        
        options = ClaudeAgentOptions(
            resume=session.claude_session_id,
            max_turns=limits["max_turns"],
            max_budget_usd=limits["max_budget_usd"] - session.total_cost_usd,
        )
        
        client = ClaudeSDKClient(options=options)
        await client.connect()
        
        self.active_clients[session_id] = client
        session.status = SessionStatus.ACTIVE
        await self._persist_session(session)
        
        return session
    
    def _get_tier_limits(self, tier: str) -> Dict[str, Any]:
        """Get resource limits based on subscription tier."""
        return {
            "free": {
                "max_turns": 10,
                "max_budget_usd": 0.50,
                "max_thinking_tokens": 2000,
                "concurrent_sessions": 1,
            },
            "pro": {
                "max_turns": 50,
                "max_budget_usd": 5.00,
                "max_thinking_tokens": 8000,
                "concurrent_sessions": 5,
            },
            "enterprise": {
                "max_turns": 200,
                "max_budget_usd": 50.00,
                "max_thinking_tokens": 16000,
                "concurrent_sessions": 20,
            },
        }.get(tier, {})
```

#### 2. Cost Tracking Service

Track and aggregate costs per user/tenant:

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Any

@dataclass
class UsageRecord:
    """Records usage for billing."""
    user_id: str
    tenant_id: str
    session_id: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    thinking_tokens: int
    timestamp: datetime

class CostTrackingService:
    """Track costs and usage for billing."""
    
    def __init__(self, db_client):
        self.db = db_client
    
    async def record_usage(
        self,
        session_id: str,
        result_message: ResultMessage
    ) -> UsageRecord:
        """Record usage from a ResultMessage."""
        session = await self._get_session(session_id)
        
        record = UsageRecord(
            user_id=session.user_id,
            tenant_id=session.tenant_id,
            session_id=session_id,
            cost_usd=result_message.total_cost_usd or 0,
            input_tokens=result_message.usage.get("input_tokens", 0) if result_message.usage else 0,
            output_tokens=result_message.usage.get("output_tokens", 0) if result_message.usage else 0,
            thinking_tokens=result_message.usage.get("thinking_tokens", 0) if result_message.usage else 0,
            timestamp=datetime.utcnow()
        )
        
        await self._save_record(record)
        return record
    
    async def get_user_usage(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get usage summary for a user."""
        records = await self._query_records(user_id, start_date, end_date)
        
        return {
            "user_id": user_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_cost_usd": sum(r.cost_usd for r in records),
            "total_sessions": len(set(r.session_id for r in records)),
            "total_tokens": {
                "input": sum(r.input_tokens for r in records),
                "output": sum(r.output_tokens for r in records),
                "thinking": sum(r.thinking_tokens for r in records),
            },
            "daily_breakdown": self._aggregate_by_day(records)
        }
    
    async def get_tenant_usage(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get usage summary for entire tenant/organization."""
        records = await self._query_tenant_records(tenant_id, start_date, end_date)
        
        # Group by user
        user_usage = {}
        for record in records:
            if record.user_id not in user_usage:
                user_usage[record.user_id] = {
                    "cost_usd": 0,
                    "sessions": set(),
                    "tokens": {"input": 0, "output": 0, "thinking": 0}
                }
            user_usage[record.user_id]["cost_usd"] += record.cost_usd
            user_usage[record.user_id]["sessions"].add(record.session_id)
            user_usage[record.user_id]["tokens"]["input"] += record.input_tokens
            user_usage[record.user_id]["tokens"]["output"] += record.output_tokens
            user_usage[record.user_id]["tokens"]["thinking"] += record.thinking_tokens
        
        return {
            "tenant_id": tenant_id,
            "total_cost_usd": sum(r.cost_usd for r in records),
            "total_users": len(user_usage),
            "user_breakdown": user_usage
        }
    
    async def check_budget_limit(
        self,
        user_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Check if user/tenant is within budget limits."""
        # Get current billing period usage
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        
        user_usage = await self.get_user_usage(user_id, start_of_month, datetime.utcnow())
        tenant_usage = await self.get_tenant_usage(tenant_id, start_of_month, datetime.utcnow())
        
        # Get limits from subscription
        user_limit = await self._get_user_budget_limit(user_id)
        tenant_limit = await self._get_tenant_budget_limit(tenant_id)
        
        return {
            "user": {
                "used": user_usage["total_cost_usd"],
                "limit": user_limit,
                "remaining": max(0, user_limit - user_usage["total_cost_usd"]),
                "exceeded": user_usage["total_cost_usd"] >= user_limit
            },
            "tenant": {
                "used": tenant_usage["total_cost_usd"],
                "limit": tenant_limit,
                "remaining": max(0, tenant_limit - tenant_usage["total_cost_usd"]),
                "exceeded": tenant_usage["total_cost_usd"] >= tenant_limit
            }
        }
```

#### 3. Multi-Tenant Isolation

Ensure complete isolation between tenants:

```python
from claude_agent_sdk import (
    ClaudeAgentOptions,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)

class TenantIsolationService:
    """Ensures isolation between tenants."""
    
    def __init__(self, tenant_id: str, user_id: str):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.allowed_paths = [
            f"/workspaces/{tenant_id}/{user_id}",
            f"/shared/{tenant_id}",
            "/tmp"
        ]
    
    def build_options(self, base_options: Dict[str, Any] = None) -> ClaudeAgentOptions:
        """Build options with tenant isolation enforced."""
        options_dict = base_options or {}
        
        # Set isolated working directory
        options_dict["cwd"] = f"/workspaces/{self.tenant_id}/{self.user_id}"
        
        # Inject tenant-specific environment
        options_dict["env"] = {
            "TENANT_ID": self.tenant_id,
            "USER_ID": self.user_id,
            "WORKSPACE_ROOT": f"/workspaces/{self.tenant_id}/{self.user_id}",
        }
        
        # Set permission callback for path isolation
        options_dict["can_use_tool"] = self.permission_callback
        
        return ClaudeAgentOptions(**options_dict)
    
    async def permission_callback(
        self,
        tool_name: str,
        input_data: dict,
        context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        """Enforce tenant isolation in all tool operations."""
        
        # Check file operations
        if tool_name in ["Read", "Write", "Edit"]:
            file_path = input_data.get("file_path", "")
            if not self._is_path_allowed(file_path):
                return PermissionResultDeny(
                    message=f"Access denied: Path outside tenant workspace",
                    interrupt=False
                )
        
        # Check bash commands for path access
        if tool_name == "Bash":
            command = input_data.get("command", "")
            if self._contains_forbidden_path(command):
                return PermissionResultDeny(
                    message="Access denied: Command accesses forbidden paths",
                    interrupt=False
                )
        
        return PermissionResultAllow()
    
    def _is_path_allowed(self, path: str) -> bool:
        """Check if path is within allowed directories."""
        import os
        abs_path = os.path.abspath(path)
        return any(abs_path.startswith(allowed) for allowed in self.allowed_paths)
    
    def _contains_forbidden_path(self, command: str) -> bool:
        """Check if command accesses forbidden paths."""
        # Simple heuristic - production would need more sophisticated analysis
        forbidden_patterns = [
            "/workspaces/(?!{})".format(self.tenant_id),
            "/etc/",
            "/root/",
            "~/.ssh",
        ]
        import re
        return any(re.search(pattern, command) for pattern in forbidden_patterns)
```

### Message Flow: Complete Request-Response Cycle

```
┌────────┐     ┌────────────┐     ┌─────────────┐     ┌───────────────┐
│ Client │     │ API Gateway│     │ Orchestrator│     │ ClaudeSDKClient│
└───┬────┘     └─────┬──────┘     └──────┬──────┘     └───────┬───────┘
    │                │                   │                    │
    │  POST /chat    │                   │                    │
    │ ─────────────> │                   │                    │
    │                │  Validate JWT     │                    │
    │                │ ─────────────>    │                    │
    │                │  User Context     │                    │
    │                │ <─────────────    │                    │
    │                │                   │                    │
    │                │  Check Limits     │                    │
    │                │ ─────────────>    │                    │
    │                │  OK / Exceeded    │                    │
    │                │ <─────────────    │                    │
    │                │                   │                    │
    │                │  Get/Create       │                    │
    │                │  Session          │                    │
    │                │ ─────────────>    │                    │
    │                │                   │  client.query()    │
    │                │                   │ ─────────────────> │
    │                │                   │                    │
    │                │                   │  Stream Messages   │
    │                │                   │ <═══════════════   │
    │  WebSocket     │                   │                    │
    │  Events        │                   │                    │
    │ <═════════════ │ <═══════════════  │                    │
    │                │                   │                    │
    │                │                   │  ResultMessage     │
    │                │                   │ <─────────────────  │
    │                │                   │                    │
    │                │  Record Usage     │                    │
    │                │ <─────────────    │                    │
    │                │                   │                    │
    │  Final Result  │                   │                    │
    │ <───────────── │                   │                    │
    │                │                   │                    │
```

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA FLOW                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐            │
│  │   Request   │         │  Processing │         │   Response  │            │
│  │   Input     │  ───>   │   Layer     │  ───>   │   Output    │            │
│  └─────────────┘         └─────────────┘         └─────────────┘            │
│        │                       │                       │                     │
│        ▼                       ▼                       ▼                     │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐            │
│  │ • User ID   │         │ • Auth      │         │ • Messages  │            │
│  │ • Tenant ID │         │ • Rate Limit│         │ • Costs     │            │
│  │ • Message   │         │ • Isolation │         │ • Session   │            │
│  │ • Session ID│         │ • Routing   │         │ • Metrics   │            │
│  └─────────────┘         └─────────────┘         └─────────────┘            │
│                                                                              │
│  ════════════════════════════════════════════════════════════════════════   │
│                                                                              │
│                        STORAGE LAYER                                         │
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │  PostgreSQL │    │    Redis    │    │    S3/GCS   │    │   ClickHouse│   │
│  │  • Sessions │    │  • Cache    │    │  • Files    │    │  • Analytics│   │
│  │  • Users    │    │  • Pub/Sub  │    │  • Outputs  │    │  • Metrics  │   │
│  │  • Tenants  │    │  • Rate Lim │    │  • Backups  │    │  • Costs    │   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## SaaS Platform Experiment

This section provides a minimal, working experiment to validate the Claude Agent SDK in a multi-tenant SaaS context.

### Experiment Overview

**Goal**: Build a thin orchestration layer that:
1. Provides user authentication and session isolation
2. Manages Claude agent sessions per user
3. Tracks costs and enforces limits
4. Streams responses via WebSocket

**Key Principle**: The Claude Agent SDK already handles the complexity. We just need to orchestrate multiple instances.

### Experiment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXPERIMENT COMPONENTS                                │
│                                                                              │
│  ┌─────────────────────┐                                                     │
│  │    Test Client      │  Simulates multiple users                           │
│  │    (test_client.py) │  sending concurrent requests                        │
│  └──────────┬──────────┘                                                     │
│             │                                                                │
│             ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │              Orchestration Layer (orchestrator.py)                   │    │
│  │                                                                      │    │
│  │   FastAPI Server with:                                               │    │
│  │   • POST /sessions          - Create new session                     │    │
│  │   • POST /sessions/{id}/chat - Send message                          │    │
│  │   • GET /sessions/{id}      - Get session status                     │    │
│  │   • DELETE /sessions/{id}   - End session                            │    │
│  │   • WS /ws/{id}             - Stream events                          │    │
│  │   • GET /users/{id}/usage   - Get usage/costs                        │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                          │                                                   │
│                          ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                  Claude Agent SDK                                    │    │
│  │                                                                      │    │
│  │   Multiple ClaudeSDKClient instances (one per active session)        │    │
│  │   • Isolated by session_id                                           │    │
│  │   • Cost tracking via ResultMessage                                  │    │
│  │   • Resource limits via ClaudeAgentOptions                           │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step 1: Create the Orchestration Layer

Create `claude_orchestrator.py`:

```python
#!/usr/bin/env python3
"""
Claude Agent SDK - SaaS Orchestration Layer Experiment

This minimal experiment demonstrates:
1. Multi-user session management
2. Cost tracking per user
3. Resource limits by tier
4. WebSocket streaming
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
)

# ============================================================================
# Configuration
# ============================================================================

class Config:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "your-api-key")
    DEFAULT_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    
    # Tier limits
    TIERS = {
        "free": {
            "max_turns": 5,
            "max_budget_usd": 0.25,
            "max_thinking_tokens": 1000,
            "concurrent_sessions": 1,
        },
        "pro": {
            "max_turns": 25,
            "max_budget_usd": 2.50,
            "max_thinking_tokens": 4000,
            "concurrent_sessions": 3,
        },
        "enterprise": {
            "max_turns": 100,
            "max_budget_usd": 25.00,
            "max_thinking_tokens": 8000,
            "concurrent_sessions": 10,
        },
    }

# ============================================================================
# Data Models
# ============================================================================

class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class UserSession:
    session_id: str
    user_id: str
    tier: str
    status: SessionStatus = SessionStatus.ACTIVE
    total_cost_usd: float = 0.0
    total_turns: int = 0
    claude_session_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    messages: list = field(default_factory=list)

class CreateSessionRequest(BaseModel):
    user_id: str
    tier: str = "free"
    initial_message: Optional[str] = None
    system_prompt: Optional[str] = None

class ChatRequest(BaseModel):
    message: str

class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    status: str
    total_cost_usd: float
    total_turns: int

# ============================================================================
# Orchestration Layer
# ============================================================================

class ClaudeOrchestrator:
    """Orchestrates multiple Claude agent sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
        self.clients: Dict[str, ClaudeSDKClient] = {}
        self.user_sessions: Dict[str, list[str]] = {}  # user_id -> session_ids
    
    async def create_session(
        self,
        user_id: str,
        tier: str = "free",
        initial_message: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> UserSession:
        """Create a new agent session for a user."""
        # Check concurrent session limit
        limits = Config.TIERS.get(tier, Config.TIERS["free"])
        user_active_sessions = [
            sid for sid in self.user_sessions.get(user_id, [])
            if self.sessions.get(sid, {}).status == SessionStatus.ACTIVE
        ]
        
        if len(user_active_sessions) >= limits["concurrent_sessions"]:
            raise HTTPException(
                status_code=429,
                detail=f"Concurrent session limit ({limits['concurrent_sessions']}) reached"
            )
        
        session_id = f"sess-{uuid.uuid4().hex[:12]}"
        
        # Build options with tier limits
        options = ClaudeAgentOptions(
            model=Config.DEFAULT_MODEL,
            max_turns=limits["max_turns"],
            max_budget_usd=limits["max_budget_usd"],
            max_thinking_tokens=limits["max_thinking_tokens"],
            system_prompt=system_prompt or f"You are a helpful assistant for user {user_id}.",
            permission_mode="acceptEdits",
        )
        
        # Create and connect client
        client = ClaudeSDKClient(options=options)
        await client.connect(initial_message)
        
        # Store session
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            tier=tier
        )
        
        self.sessions[session_id] = session
        self.clients[session_id] = client
        
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        self.user_sessions[user_id].append(session_id)
        
        print(f"[Orchestrator] Created session {session_id} for user {user_id} (tier: {tier})")
        return session
    
    async def send_message(
        self,
        session_id: str,
        message: str
    ) -> AsyncIterator[Dict[str, Any]]:
        """Send a message and stream responses."""
        if session_id not in self.sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = self.sessions[session_id]
        client = self.clients.get(session_id)
        
        if not client or session.status != SessionStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Session not active")
        
        # Send query
        await client.query(message)
        session.messages.append({"role": "user", "content": message})
        
        # Stream responses
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                text_content = ""
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text_content += block.text
                
                yield {
                    "type": "assistant_message",
                    "content": text_content,
                    "model": msg.model
                }
                
                session.messages.append({"role": "assistant", "content": text_content})
            
            elif isinstance(msg, ResultMessage):
                session.total_cost_usd += msg.total_cost_usd or 0
                session.total_turns += 1
                session.claude_session_id = msg.session_id
                
                # Check if budget exceeded
                if msg.subtype == "error_max_budget_usd":
                    session.status = SessionStatus.COMPLETED
                    yield {
                        "type": "budget_exceeded",
                        "total_cost_usd": session.total_cost_usd
                    }
                
                yield {
                    "type": "result",
                    "session_id": session_id,
                    "total_cost_usd": session.total_cost_usd,
                    "total_turns": session.total_turns,
                    "duration_ms": msg.duration_ms
                }
    
    async def get_session(self, session_id: str) -> UserSession:
        """Get session details."""
        if session_id not in self.sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        return self.sessions[session_id]
    
    async def end_session(self, session_id: str) -> bool:
        """End and cleanup a session."""
        if session_id not in self.sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = self.sessions[session_id]
        client = self.clients.pop(session_id, None)
        
        if client:
            await client.disconnect()
        
        session.status = SessionStatus.COMPLETED
        print(f"[Orchestrator] Ended session {session_id} (cost: ${session.total_cost_usd:.4f})")
        return True
    
    def get_user_usage(self, user_id: str) -> Dict[str, Any]:
        """Get usage summary for a user."""
        session_ids = self.user_sessions.get(user_id, [])
        sessions = [self.sessions[sid] for sid in session_ids if sid in self.sessions]
        
        return {
            "user_id": user_id,
            "total_sessions": len(sessions),
            "active_sessions": len([s for s in sessions if s.status == SessionStatus.ACTIVE]),
            "total_cost_usd": sum(s.total_cost_usd for s in sessions),
            "total_turns": sum(s.total_turns for s in sessions),
            "sessions": [
                {
                    "session_id": s.session_id,
                    "status": s.status.value,
                    "cost_usd": s.total_cost_usd,
                    "turns": s.total_turns
                }
                for s in sessions
            ]
        }

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(title="Claude Agent SaaS Experiment")
orchestrator = ClaudeOrchestrator()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/sessions", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new agent session."""
    session = await orchestrator.create_session(
        user_id=request.user_id,
        tier=request.tier,
        initial_message=request.initial_message,
        system_prompt=request.system_prompt
    )
    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        status=session.status.value,
        total_cost_usd=session.total_cost_usd,
        total_turns=session.total_turns
    )

@app.post("/sessions/{session_id}/chat")
async def chat(session_id: str, request: ChatRequest):
    """Send a message to a session (non-streaming)."""
    responses = []
    async for response in orchestrator.send_message(session_id, request.message):
        responses.append(response)
    return {"responses": responses}

@app.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for streaming chat."""
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message", "")
            
            # Stream responses
            async for response in orchestrator.send_message(session_id, message):
                await websocket.send_json(response)
    
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}")

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details."""
    session = await orchestrator.get_session(session_id)
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "tier": session.tier,
        "status": session.status.value,
        "total_cost_usd": session.total_cost_usd,
        "total_turns": session.total_turns,
        "message_count": len(session.messages)
    }

@app.delete("/sessions/{session_id}")
async def end_session(session_id: str):
    """End a session."""
    await orchestrator.end_session(session_id)
    return {"status": "ended"}

@app.get("/users/{user_id}/usage")
async def get_user_usage(user_id: str):
    """Get usage summary for a user."""
    return orchestrator.get_user_usage(user_id)

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": len([
            s for s in orchestrator.sessions.values()
            if s.status == SessionStatus.ACTIVE
        ])
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Step 2: Create the Test Client

Create `test_client.py`:

```python
#!/usr/bin/env python3
"""
Test client for Claude Agent SaaS Experiment

Simulates multiple concurrent users interacting with the orchestration layer.
"""

import asyncio
import httpx
import json
import websockets
from typing import Optional

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

async def create_session(
    client: httpx.AsyncClient,
    user_id: str,
    tier: str = "free",
    initial_message: Optional[str] = None
) -> dict:
    """Create a new session."""
    response = await client.post(
        f"{BASE_URL}/sessions",
        json={
            "user_id": user_id,
            "tier": tier,
            "initial_message": initial_message
        }
    )
    response.raise_for_status()
    return response.json()

async def chat_http(
    client: httpx.AsyncClient,
    session_id: str,
    message: str
) -> dict:
    """Send message via HTTP (non-streaming)."""
    response = await client.post(
        f"{BASE_URL}/sessions/{session_id}/chat",
        json={"message": message},
        timeout=60.0
    )
    response.raise_for_status()
    return response.json()

async def chat_websocket(session_id: str, message: str):
    """Send message via WebSocket (streaming)."""
    async with websockets.connect(f"{WS_URL}/ws/{session_id}") as ws:
        await ws.send(json.dumps({"message": message}))
        
        while True:
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=30.0)
                data = json.loads(response)
                print(f"  [{data['type']}] ", end="")
                
                if data["type"] == "assistant_message":
                    print(data["content"][:100] + "..." if len(data.get("content", "")) > 100 else data.get("content", ""))
                elif data["type"] == "result":
                    print(f"Cost: ${data['total_cost_usd']:.4f}, Turns: {data['total_turns']}")
                    break
                else:
                    print(data)
            except asyncio.TimeoutError:
                print("  [timeout]")
                break

async def get_usage(client: httpx.AsyncClient, user_id: str) -> dict:
    """Get user usage summary."""
    response = await client.get(f"{BASE_URL}/users/{user_id}/usage")
    response.raise_for_status()
    return response.json()

async def simulate_user(user_id: str, tier: str, messages: list[str]):
    """Simulate a single user's interaction."""
    print(f"\n{'='*60}")
    print(f"User: {user_id} (Tier: {tier})")
    print(f"{'='*60}")
    
    async with httpx.AsyncClient() as client:
        # Create session
        print(f"\n[{user_id}] Creating session...")
        session = await create_session(client, user_id, tier)
        session_id = session["session_id"]
        print(f"[{user_id}] Session created: {session_id}")
        
        # Send messages
        for i, message in enumerate(messages):
            print(f"\n[{user_id}] Message {i+1}: {message[:50]}...")
            
            try:
                # Use HTTP for simplicity in test
                result = await chat_http(client, session_id, message)
                
                for response in result["responses"]:
                    if response["type"] == "assistant_message":
                        content = response["content"]
                        print(f"[{user_id}] Response: {content[:100]}...")
                    elif response["type"] == "result":
                        print(f"[{user_id}] Cost: ${response['total_cost_usd']:.4f}")
                    elif response["type"] == "budget_exceeded":
                        print(f"[{user_id}] BUDGET EXCEEDED!")
                        break
                        
            except httpx.HTTPStatusError as e:
                print(f"[{user_id}] Error: {e.response.status_code} - {e.response.text}")
                break
        
        # Get final usage
        usage = await get_usage(client, user_id)
        print(f"\n[{user_id}] Final Usage Summary:")
        print(f"  Total Cost: ${usage['total_cost_usd']:.4f}")
        print(f"  Total Turns: {usage['total_turns']}")
        print(f"  Sessions: {usage['total_sessions']}")

async def run_experiment():
    """Run the multi-user experiment."""
    print("="*60)
    print("Claude Agent SaaS Experiment")
    print("="*60)
    
    # Define test scenarios
    scenarios = [
        {
            "user_id": "user-free-001",
            "tier": "free",
            "messages": [
                "What is 2 + 2?",
                "Now multiply that by 10",
            ]
        },
        {
            "user_id": "user-pro-001",
            "tier": "pro",
            "messages": [
                "Explain the concept of recursion in programming",
                "Give me an example in Python",
                "How would this work with memoization?",
            ]
        },
        {
            "user_id": "user-enterprise-001",
            "tier": "enterprise",
            "messages": [
                "Design a microservices architecture for an e-commerce platform",
                "What databases would you recommend for each service?",
            ]
        },
    ]
    
    # Run users concurrently
    tasks = [
        simulate_user(s["user_id"], s["tier"], s["messages"])
        for s in scenarios
    ]
    
    await asyncio.gather(*tasks)
    
    print("\n" + "="*60)
    print("Experiment Complete!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_experiment())
```

### Step 3: Run the Experiment

```bash
# Terminal 1: Start the orchestrator
export ANTHROPIC_API_KEY="your-api-key"
python claude_orchestrator.py

# Terminal 2: Run the test client
python test_client.py
```

### Expected Output

```
============================================================
Claude Agent SaaS Experiment
============================================================

============================================================
User: user-free-001 (Tier: free)
============================================================

[user-free-001] Creating session...
[user-free-001] Session created: sess-a1b2c3d4e5f6

[user-free-001] Message 1: What is 2 + 2?...
[user-free-001] Response: 2 + 2 equals 4...
[user-free-001] Cost: $0.0012

[user-free-001] Message 2: Now multiply that by 10...
[user-free-001] Response: 4 multiplied by 10 equals 40...
[user-free-001] Cost: $0.0025

[user-free-001] Final Usage Summary:
  Total Cost: $0.0025
  Total Turns: 2
  Sessions: 1

============================================================
User: user-pro-001 (Tier: pro)
============================================================
...

============================================================
Experiment Complete!
============================================================
```

### Experiment Metrics to Collect

| Metric | Description | How to Collect |
|--------|-------------|----------------|
| Session Latency | Time from request to first response | Measure `client.connect()` duration |
| Message Latency | Time per message round-trip | Measure `client.query()` to `ResultMessage` |
| Cost per Session | Total API costs | Sum `ResultMessage.total_cost_usd` |
| Tokens per Session | Token usage breakdown | Extract from `ResultMessage.usage` |
| Concurrent Sessions | Active sessions at peak | Track `len(active_clients)` |
| Error Rate | Failed requests percentage | Count exceptions vs total requests |

### Experiment Variations

1. **Stress Test**: Increase concurrent users to find limits
2. **Long Sessions**: Test multi-turn conversations over time
3. **Budget Exhaustion**: Verify limits are enforced correctly
4. **Session Resume**: Test pause/resume functionality
5. **WebSocket Streaming**: Compare HTTP vs WebSocket performance

---

## Production Best Practices & Common Pitfalls

> **⚠️ Critical Section**: This section covers real-world implementation patterns that prevent production failures. Review carefully before deploying a SaaS system.

### Claude API Rate Limits and Retry Logic

The Claude SDK communicates with Anthropic's API, which has rate limits. Implement proper retry logic:

#### Rate Limit Configuration

```python
from dataclasses import dataclass
from typing import Optional
import asyncio
import random

@dataclass
class RetryConfig:
    """Configuration for API retry behavior."""
    max_retries: int = 5
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

class RateLimitHandler:
    """Handle Anthropic API rate limits gracefully."""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
    
    def calculate_delay(self, attempt: int, retry_after: Optional[float] = None) -> float:
        """Calculate delay with exponential backoff and jitter."""
        if retry_after:
            return retry_after
        
        delay = min(
            self.config.initial_delay * (self.config.exponential_base ** attempt),
            self.config.max_delay
        )
        
        if self.config.jitter:
            delay = delay * (0.5 + random.random())
        
        return delay
    
    async def execute_with_retry(self, operation, *args, **kwargs):
        """Execute an operation with retry logic."""
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Check for rate limit errors
                if "rate limit" in error_str or "429" in error_str:
                    if attempt < self.config.max_retries:
                        delay = self.calculate_delay(attempt)
                        print(f"Rate limited. Retrying in {delay:.1f}s (attempt {attempt + 1})")
                        await asyncio.sleep(delay)
                        continue
                
                # Check for overloaded errors
                if "overloaded" in error_str or "529" in error_str:
                    if attempt < self.config.max_retries:
                        delay = self.calculate_delay(attempt) * 2  # Longer delay for overload
                        print(f"API overloaded. Retrying in {delay:.1f}s")
                        await asyncio.sleep(delay)
                        continue
                
                # Don't retry client errors (400, 401, 403, 404)
                if any(code in error_str for code in ["400", "401", "403", "404"]):
                    raise
                
                # Retry server errors (500, 502, 503, 504)
                if any(code in error_str for code in ["500", "502", "503", "504"]):
                    if attempt < self.config.max_retries:
                        delay = self.calculate_delay(attempt)
                        await asyncio.sleep(delay)
                        continue
                
                raise
        
        raise last_error
```

#### Using Retry Logic with the Orchestrator

```python
class ProductionOrchestrator(ClaudeOrchestrator):
    """Production-ready orchestrator with retry handling."""
    
    def __init__(self):
        super().__init__()
        self.rate_limiter = RateLimitHandler(RetryConfig(
            max_retries=5,
            initial_delay=1.0,
            max_delay=60.0
        ))
    
    async def send_message_with_retry(
        self,
        session_id: str,
        message: str
    ) -> AsyncIterator[Dict[str, Any]]:
        """Send message with automatic retry on rate limits."""
        
        async def _send():
            async for response in self.send_message(session_id, message):
                yield response
        
        # For streaming, wrap the generator
        try:
            async for response in _send():
                yield response
        except Exception as e:
            if "rate limit" in str(e).lower():
                await asyncio.sleep(self.rate_limiter.calculate_delay(0))
                async for response in _send():
                    yield response
            else:
                raise
```

### Session State Machine

Understanding session states prevents invalid operations:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SESSION STATE MACHINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│    ┌──────────┐    connect()    ┌──────────┐                    │
│    │ CREATING │ ──────────────► │  ACTIVE  │◄────────┐          │
│    └──────────┘                 └────┬─────┘         │          │
│                                      │               │          │
│                              query() │         resume()         │
│                                      ▼               │          │
│                                ┌──────────┐         │          │
│                                │ RUNNING  │─────────┤          │
│                                └────┬─────┘         │          │
│                                     │               │          │
│                    ┌────────────────┼────────────────┐          │
│                    │                │                │          │
│                    ▼                ▼                ▼          │
│              ┌──────────┐    ┌──────────┐    ┌──────────┐       │
│              │  PAUSED  │    │ COMPLETED│    │  ERROR   │       │
│              └────┬─────┘    └──────────┘    └────┬─────┘       │
│                   │                               │              │
│                   └───────────────────────────────┘              │
│                              Can be resumed                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### State-Aware Operations

```python
from enum import Enum
from typing import Optional

class SessionState(Enum):
    CREATING = "creating"
    ACTIVE = "active"       # Connected, waiting for input
    RUNNING = "running"     # Processing a query
    PAUSED = "paused"       # Paused by user
    COMPLETED = "completed" # Finished successfully
    ERROR = "error"         # Error occurred

class StatefulSession:
    """Session with explicit state management."""
    
    VALID_TRANSITIONS = {
        SessionState.CREATING: {SessionState.ACTIVE, SessionState.ERROR},
        SessionState.ACTIVE: {SessionState.RUNNING, SessionState.PAUSED, SessionState.COMPLETED, SessionState.ERROR},
        SessionState.RUNNING: {SessionState.ACTIVE, SessionState.PAUSED, SessionState.COMPLETED, SessionState.ERROR},
        SessionState.PAUSED: {SessionState.ACTIVE, SessionState.RUNNING, SessionState.COMPLETED, SessionState.ERROR},
        SessionState.COMPLETED: set(),  # Terminal state
        SessionState.ERROR: {SessionState.ACTIVE},  # Can be recovered
    }
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._state = SessionState.CREATING
    
    @property
    def state(self) -> SessionState:
        return self._state
    
    def can_transition_to(self, new_state: SessionState) -> bool:
        """Check if transition is valid."""
        return new_state in self.VALID_TRANSITIONS.get(self._state, set())
    
    def transition_to(self, new_state: SessionState) -> bool:
        """Attempt state transition."""
        if not self.can_transition_to(new_state):
            raise InvalidStateTransition(
                f"Cannot transition from {self._state.value} to {new_state.value}"
            )
        self._state = new_state
        return True
    
    def can_send_message(self) -> bool:
        """Check if session can accept messages."""
        return self._state in {SessionState.ACTIVE, SessionState.RUNNING}
    
    def can_pause(self) -> bool:
        """Check if session can be paused."""
        return self._state in {SessionState.ACTIVE, SessionState.RUNNING}
    
    def can_resume(self) -> bool:
        """Check if session can be resumed."""
        return self._state in {SessionState.PAUSED, SessionState.ERROR}

class InvalidStateTransition(Exception):
    """Raised when an invalid state transition is attempted."""
    pass
```

### WebSocket Reconnection Pattern

The basic WebSocket handler doesn't handle disconnections gracefully:

#### ❌ Basic WebSocket (No Reconnection)

```python
# This is what the experiment has - connection drops silently
@app.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            # ... process ...
    except WebSocketDisconnect:
        print(f"Disconnected: {session_id}")  # Lost forever!
```

#### ✅ Production WebSocket (Client-Side Reconnection)

```javascript
class RobustClaudeWebSocket {
    constructor(sessionId, baseUrl) {
        this.sessionId = sessionId;
        this.baseUrl = baseUrl;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.messageQueue = [];  // Queue messages during reconnection
        this.lastMessageId = 0;
    }

    connect() {
        const url = `${this.baseUrl}/ws/${this.sessionId}?last_msg_id=${this.lastMessageId}`;
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            console.log('Connected to Claude session');
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            
            // Flush queued messages
            while (this.messageQueue.length > 0) {
                const msg = this.messageQueue.shift();
                this.send(msg);
            }
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.message_id) {
                this.lastMessageId = Math.max(this.lastMessageId, data.message_id);
            }
            this.onMessage(data);
        };

        this.ws.onclose = (event) => {
            if (!event.wasClean) {
                this.attemptReconnect();
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this.onMaxRetriesExceeded();
            return;
        }

        this.reconnectAttempts++;
        const delay = Math.min(
            this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
            30000
        );

        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        setTimeout(() => this.connect(), delay);
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            // Queue for later
            this.messageQueue.push(message);
        }
    }

    onMessage(data) {
        // Override in subclass
    }

    onMaxRetriesExceeded() {
        console.error('Max reconnection attempts reached');
        // Show user notification
    }

    disconnect() {
        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
        }
    }
}
```

### Zombie Session Cleanup

Sessions can become orphaned. Implement periodic cleanup:

```python
import asyncio
from datetime import datetime, timedelta
from typing import Dict

class SessionCleaner:
    """Clean up abandoned/zombie sessions."""
    
    def __init__(
        self,
        orchestrator: ClaudeOrchestrator,
        max_idle_minutes: int = 30,
        max_active_minutes: int = 120,
        cleanup_interval_seconds: int = 300
    ):
        self.orchestrator = orchestrator
        self.max_idle = timedelta(minutes=max_idle_minutes)
        self.max_active = timedelta(minutes=max_active_minutes)
        self.cleanup_interval = cleanup_interval_seconds
        self.session_last_activity: Dict[str, datetime] = {}
    
    def record_activity(self, session_id: str):
        """Record session activity timestamp."""
        self.session_last_activity[session_id] = datetime.utcnow()
    
    async def start_cleanup_loop(self):
        """Run periodic cleanup."""
        while True:
            try:
                await self.cleanup_stale_sessions()
            except Exception as e:
                print(f"Cleanup error: {e}")
            await asyncio.sleep(self.cleanup_interval)
    
    async def cleanup_stale_sessions(self):
        """Find and clean up stale sessions."""
        now = datetime.utcnow()
        sessions_to_end = []
        
        for session_id, session in self.orchestrator.sessions.items():
            last_activity = self.session_last_activity.get(
                session_id, 
                session.created_at if hasattr(session, 'created_at') else now
            )
            idle_time = now - last_activity
            
            # Check for zombie sessions
            if session.status == SessionStatus.ACTIVE:
                if idle_time > self.max_idle:
                    print(f"Session {session_id} idle for {idle_time}, cleaning up")
                    sessions_to_end.append(session_id)
            
            # Check for runaway sessions
            elif session.status == SessionStatus.RUNNING:
                if idle_time > self.max_active:
                    print(f"Session {session_id} running too long ({idle_time}), force ending")
                    sessions_to_end.append(session_id)
        
        # Clean up sessions
        for session_id in sessions_to_end:
            try:
                await self.orchestrator.end_session(session_id)
            except Exception as e:
                print(f"Failed to clean up session {session_id}: {e}")
                # Force remove from tracking
                self.orchestrator.sessions.pop(session_id, None)
                self.orchestrator.clients.pop(session_id, None)
```

### Graceful Shutdown

Properly handle server shutdown to preserve user sessions:

```python
import signal
import asyncio
from typing import List

class GracefulShutdownManager:
    """Handle graceful shutdown of all sessions."""
    
    def __init__(self, orchestrator: ClaudeOrchestrator):
        self.orchestrator = orchestrator
        self.shutdown_event = asyncio.Event()
        self.active_requests: List[asyncio.Task] = []
    
    def setup_signal_handlers(self):
        """Register signal handlers."""
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self.shutdown(s))
            )
    
    async def shutdown(self, sig):
        """Gracefully shutdown all sessions."""
        print(f"Received signal {sig.name}, shutting down...")
        self.shutdown_event.set()
        
        # Stop accepting new requests
        # (handled by web framework)
        
        # Wait for active requests to complete (with timeout)
        if self.active_requests:
            print(f"Waiting for {len(self.active_requests)} active requests...")
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.active_requests, return_exceptions=True),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                print("Timeout waiting for requests, forcing shutdown")
        
        # Pause all active sessions (preserves state for resume)
        active_sessions = [
            sid for sid, s in self.orchestrator.sessions.items()
            if s.status == SessionStatus.ACTIVE
        ]
        
        print(f"Pausing {len(active_sessions)} active sessions...")
        for session_id in active_sessions:
            try:
                await self.orchestrator.pause_session(session_id)
            except Exception as e:
                print(f"Failed to pause {session_id}: {e}")
        
        # Disconnect all clients
        for client in self.orchestrator.clients.values():
            try:
                await client.disconnect()
            except Exception:
                pass
        
        print("Graceful shutdown complete")
    
    def track_request(self, task: asyncio.Task):
        """Track an active request for graceful shutdown."""
        self.active_requests.append(task)
        task.add_done_callback(lambda t: self.active_requests.remove(t))
```

### Error Codes Reference

| Error | Description | Retry? | Action |
|-------|-------------|--------|--------|
| `CLINotFoundError` | Claude CLI not installed | No | Install CLI |
| `CLIConnectionError` | Connection to CLI failed | Yes | Retry with backoff |
| `ProcessError` | CLI process crashed | Maybe | Check error details, may retry |
| `SDKJSONDecodeError` | Invalid response from CLI | No | Bug report |
| Rate Limit (429) | Too many requests | Yes | Wait for `retry-after` |
| Overloaded (529) | API overloaded | Yes | Wait longer, reduce load |
| Auth Error (401) | Invalid API key | No | Check credentials |
| Bad Request (400) | Invalid request format | No | Fix request |
| Server Error (5xx) | Anthropic server issue | Yes | Retry with backoff |

### Quick Reference: SaaS Pitfalls Checklist

| Category | ❌ Don't | ✅ Do |
|----------|---------|-------|
| **Rate Limits** | Retry immediately | Exponential backoff with jitter |
| **Sessions** | Assume always active | Check state before operations |
| **WebSocket** | Let connections die | Implement reconnection logic |
| **Resources** | Unlimited sessions | Enforce per-user limits |
| **Cleanup** | Forget abandoned sessions | Run periodic cleanup |
| **Shutdown** | Kill processes | Pause sessions, wait for completion |
| **Errors** | Retry all errors | Only retry 429/5xx |
| **Costs** | Trust estimates | Track actual `ResultMessage.total_cost_usd` |
| **Concurrency** | Unlimited parallel | Semaphore for concurrent sessions |

### Cost Tracking Best Practices

```python
from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime

@dataclass
class CostTracker:
    """Track costs per user with alerts."""
    
    user_id: str
    tier: str
    budget_limit: float
    current_spend: float = 0.0
    session_costs: Dict[str, float] = field(default_factory=dict)
    cost_history: List[Dict] = field(default_factory=list)
    
    def record_cost(self, session_id: str, cost: float, tokens: int):
        """Record a cost event."""
        self.current_spend += cost
        self.session_costs[session_id] = self.session_costs.get(session_id, 0) + cost
        
        self.cost_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "cost": cost,
            "tokens": tokens,
            "cumulative": self.current_spend
        })
        
        # Check budget
        self.check_budget_alerts()
    
    def check_budget_alerts(self):
        """Check and trigger budget alerts."""
        usage_percent = (self.current_spend / self.budget_limit) * 100
        
        if usage_percent >= 100:
            raise BudgetExceededError(
                f"User {self.user_id} exceeded budget: ${self.current_spend:.2f} / ${self.budget_limit:.2f}"
            )
        elif usage_percent >= 90:
            print(f"⚠️ User {self.user_id} at 90% budget")
        elif usage_percent >= 75:
            print(f"ℹ️ User {self.user_id} at 75% budget")
    
    def get_remaining_budget(self) -> float:
        """Get remaining budget."""
        return max(0, self.budget_limit - self.current_spend)

class BudgetExceededError(Exception):
    """Raised when user exceeds their budget."""
    pass
```

---

## Expanding the SaaS Experiment

### Expansion Roadmap

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXPANSION PHASES                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Phase 1: Foundation          Phase 2: Production        Phase 3: Scale     │
│  ─────────────────           ─────────────────          ────────────────    │
│  ✅ In-memory sessions       □ PostgreSQL persistence   □ Redis cluster     │
│  ✅ Basic cost tracking      □ Full billing system      □ Horizontal scale  │
│  ✅ Tier-based limits        □ Stripe integration       □ Load balancing    │
│  ✅ HTTP + WebSocket         □ User authentication      □ Multi-region      │
│                              □ Webhook notifications    □ Analytics         │
│                              □ Sandbox isolation        □ ML monitoring     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Expansion 1: Add Database Persistence

```python
# Add to claude_orchestrator.py

import asyncpg
from typing import Optional

class DatabaseService:
    """PostgreSQL persistence for sessions."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(self.database_url)
        await self._create_tables()
    
    async def _create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id VARCHAR(50) PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    tenant_id VARCHAR(100),
                    tier VARCHAR(20) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    claude_session_id VARCHAR(100),
                    total_cost_usd DECIMAL(10, 6) DEFAULT 0,
                    total_turns INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS usage_records (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(50) REFERENCES sessions(session_id),
                    user_id VARCHAR(100) NOT NULL,
                    cost_usd DECIMAL(10, 6) NOT NULL,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    thinking_tokens INTEGER,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_records(user_id);
                CREATE INDEX IF NOT EXISTS idx_usage_created ON usage_records(created_at);
            """)
    
    async def save_session(self, session: UserSession):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO sessions (session_id, user_id, tier, status, claude_session_id, 
                                     total_cost_usd, total_turns)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (session_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    claude_session_id = EXCLUDED.claude_session_id,
                    total_cost_usd = EXCLUDED.total_cost_usd,
                    total_turns = EXCLUDED.total_turns,
                    updated_at = NOW()
            """, session.session_id, session.user_id, session.tier,
                session.status.value, session.claude_session_id,
                session.total_cost_usd, session.total_turns)
    
    async def record_usage(self, session_id: str, user_id: str, 
                          result_message: ResultMessage):
        async with self.pool.acquire() as conn:
            usage = result_message.usage or {}
            await conn.execute("""
                INSERT INTO usage_records (session_id, user_id, cost_usd,
                                          input_tokens, output_tokens, thinking_tokens)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, session_id, user_id, result_message.total_cost_usd or 0,
                usage.get("input_tokens", 0), usage.get("output_tokens", 0),
                usage.get("thinking_tokens", 0))
    
    async def get_user_usage_summary(self, user_id: str, 
                                    start_date: datetime, 
                                    end_date: datetime) -> dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    COUNT(DISTINCT session_id) as total_sessions,
                    SUM(cost_usd) as total_cost,
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens
                FROM usage_records
                WHERE user_id = $1 AND created_at BETWEEN $2 AND $3
            """, user_id, start_date, end_date)
            
            return {
                "user_id": user_id,
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "total_sessions": row["total_sessions"] or 0,
                "total_cost_usd": float(row["total_cost"] or 0),
                "total_tokens": {
                    "input": row["total_input_tokens"] or 0,
                    "output": row["total_output_tokens"] or 0
                }
            }
```

### Expansion 2: Add User Authentication

```python
# Add JWT authentication

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

class AuthService:
    """JWT-based authentication."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_token(self, user_id: str, tenant_id: str, tier: str) -> str:
        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "tier": tier,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

auth_service = AuthService(secret_key=os.getenv("JWT_SECRET", "your-secret"))

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    return auth_service.verify_token(credentials.credentials)

# Update endpoints to use authentication
@app.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    current_user: dict = Depends(get_current_user)
):
    session = await orchestrator.create_session(
        user_id=current_user["user_id"],
        tier=current_user["tier"],
        initial_message=request.initial_message,
        system_prompt=request.system_prompt
    )
    return SessionResponse(...)
```

### Expansion 3: Add Webhook Notifications

```python
# Webhook system for real-time notifications

import httpx
from typing import Callable

class WebhookService:
    """Send webhook notifications for session events."""
    
    def __init__(self):
        self.subscribers: Dict[str, list[str]] = {}  # tenant_id -> webhook_urls
        self.client = httpx.AsyncClient()
    
    async def notify(self, tenant_id: str, event_type: str, payload: dict):
        urls = self.subscribers.get(tenant_id, [])
        
        for url in urls:
            try:
                await self.client.post(
                    url,
                    json={
                        "event_type": event_type,
                        "timestamp": datetime.utcnow().isoformat(),
                        "payload": payload
                    },
                    timeout=5.0
                )
            except Exception as e:
                print(f"Webhook failed for {url}: {e}")
    
    def register(self, tenant_id: str, webhook_url: str):
        if tenant_id not in self.subscribers:
            self.subscribers[tenant_id] = []
        self.subscribers[tenant_id].append(webhook_url)

# Event types
class WebhookEvents:
    SESSION_CREATED = "session.created"
    SESSION_COMPLETED = "session.completed"
    BUDGET_EXCEEDED = "budget.exceeded"
    MESSAGE_RECEIVED = "message.received"

# Usage in orchestrator
async def send_message(self, session_id: str, message: str):
    # ... existing code ...
    
    async for msg in client.receive_response():
        if isinstance(msg, ResultMessage):
            await self.webhooks.notify(
                tenant_id=session.tenant_id,
                event_type=WebhookEvents.MESSAGE_RECEIVED,
                payload={
                    "session_id": session_id,
                    "cost_usd": msg.total_cost_usd,
                    "turns": session.total_turns
                }
            )
        yield msg
```

### Production Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              PRODUCTION ARCHITECTURE                                     │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                           LOAD BALANCER (nginx/ALB)                              │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                        │                                                 │
│                    ┌───────────────────┼───────────────────┐                            │
│                    │                   │                   │                            │
│                    ▼                   ▼                   ▼                            │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐               │
│  │   Orchestrator 1    │ │   Orchestrator 2    │ │   Orchestrator N    │               │
│  │   (FastAPI)         │ │   (FastAPI)         │ │   (FastAPI)         │               │
│  └──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘               │
│             │                       │                       │                           │
│             └───────────────────────┼───────────────────────┘                           │
│                                     │                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                              SHARED SERVICES                                     │    │
│  │                                                                                  │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │    │
│  │  │   Redis      │  │  PostgreSQL  │  │   S3/GCS    │  │  ClickHouse  │         │    │
│  │  │  • Sessions  │  │  • Users     │  │  • Outputs  │  │  • Analytics │         │    │
│  │  │  • Pub/Sub   │  │  • Billing   │  │  • Backups  │  │  • Metrics   │         │    │
│  │  │  • Cache     │  │  • History   │  │  • Files    │  │  • Costs     │         │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘         │    │
│  │                                                                                  │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                           EXTERNAL SERVICES                                      │    │
│  │                                                                                  │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │    │
│  │  │  Anthropic   │  │   Stripe     │  │  Auth0/     │  │   Daytona    │         │    │
│  │  │  API         │  │  (Billing)   │  │  Clerk      │  │  (Sandboxes) │         │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘         │    │
│  │                                                                                  │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Next Steps Checklist

- [ ] **Phase 1: Foundation** (Current experiment)
  - [x] Basic session management
  - [x] Cost tracking per session
  - [x] Tier-based limits
  - [x] HTTP and WebSocket APIs
  - [ ] Add structured logging
  - [ ] Add health checks and metrics

- [ ] **Phase 2: Production Readiness**
  - [ ] PostgreSQL persistence
  - [ ] Redis for session state
  - [ ] JWT authentication
  - [ ] Webhook notifications
  - [ ] Rate limiting
  - [ ] Stripe billing integration

- [ ] **Phase 3: Scale**
  - [ ] Horizontal scaling
  - [ ] Load balancing
  - [ ] Multi-region deployment
  - [ ] Advanced analytics
  - [ ] ML-based monitoring

---

## Conclusion

The Claude Agent SDK for Python provides a comprehensive, type-safe interface for building AI agent applications with Claude Code. Key takeaways:

1. **Two Entry Points**: Use `query()` for simple interactions, `ClaudeSDKClient` for interactive sessions
2. **Extensible Tools**: Create custom tools with `@tool` decorator and `create_sdk_mcp_server()`
3. **Fine-grained Control**: Lifecycle hooks and permission callbacks for precise control
4. **Session Management**: Multi-turn conversations with resume and forking capabilities
5. **Cost Control**: Built-in limits for turns, budget, and thinking tokens
6. **Type Safety**: Comprehensive type annotations throughout the SDK
7. **Production Ready**: Robust error handling, testing, and quality standards
8. **Skills System**: Dynamic context injection via system prompts, custom tools, and hooks
9. **SaaS Ready**: Patterns for multi-tenant isolation, cost tracking, and scaling

For the latest updates and detailed API reference, visit the [official documentation](https://deepwiki.com/anthropics/claude-agent-sdk-python).
