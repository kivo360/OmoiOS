# Lifecycle Hooks

Intercept and control agent execution at specific points.

## Hook Events

| Event | When Invoked |
|-------|--------------|
| `PreToolUse` | Before tool execution |
| `PostToolUse` | After tool execution |
| `UserPromptSubmit` | User message submitted |
| `Stop` | Agent session stopping |
| `SubagentStop` | Subagent completed |
| `PreCompact` | Before transcript compaction |

## Hook Input Types

### BaseHookInput (common fields)

```python
@dataclass
class BaseHookInput:
    session_id: str
    transcript_path: str
    cwd: str
    permission_mode: str
```

### PreToolUseHookInput

```python
@dataclass
class PreToolUseHookInput(BaseHookInput):
    hook_event_name: Literal["PreToolUse"]
    tool_name: str
    tool_input: dict[str, Any]
```

### PostToolUseHookInput

```python
@dataclass
class PostToolUseHookInput(BaseHookInput):
    hook_event_name: Literal["PostToolUse"]
    tool_name: str
    tool_input: dict[str, Any]
    tool_response: Any
```

### UserPromptSubmitHookInput

```python
@dataclass
class UserPromptSubmitHookInput(BaseHookInput):
    hook_event_name: Literal["UserPromptSubmit"]
    prompt: str
```

## Hook Output Types

### SyncHookJSONOutput

```python
class SyncHookJSONOutput(TypedDict, total=False):
    continue_: bool          # Proceed with execution (default: True)
    suppressOutput: bool     # Hide stdout from transcript
    stopReason: str          # Message if continue_ is False
    decision: Literal["block"]
    systemMessage: str       # Warning message for user
    reason: str              # Feedback for Claude
    hookSpecificOutput: dict # Event-specific controls
```

### PreToolUseHookSpecificOutput

```python
class PreToolUseHookSpecificOutput(TypedDict, total=False):
    permissionDecision: Literal["allow", "deny", "ask"]
    permissionDecisionReason: str
    updatedInput: dict[str, Any]
```

## Examples

### Block Dangerous Bash Commands

```python
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

BLOCKED_PATTERNS = ["rm -rf", "sudo", "> /dev/"]

async def check_bash_command(input_data, tool_use_id, context):
    tool_name = input_data["tool_name"]
    tool_input = input_data["tool_input"]

    if tool_name != "Bash":
        return {}

    command = tool_input.get("command", "")

    for pattern in BLOCKED_PATTERNS:
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

### Log All Tool Usage

```python
import json
from datetime import datetime

async def log_tool_use(input_data, tool_use_id, context):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": input_data["tool_name"],
        "input": input_data["tool_input"],
    }
    print(f"[TOOL] {json.dumps(log_entry)}")
    return {}

async def log_tool_result(input_data, tool_use_id, context):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": input_data["tool_name"],
        "response": str(input_data["tool_response"])[:200],
    }
    print(f"[RESULT] {json.dumps(log_entry)}")
    return {}

options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [HookMatcher(matcher="*", hooks=[log_tool_use])],
        "PostToolUse": [HookMatcher(matcher="*", hooks=[log_tool_result])],
    }
)
```

### Modify Tool Input

```python
async def add_timeout(input_data, tool_use_id, context):
    if input_data["tool_name"] == "Bash":
        original = input_data["tool_input"].get("command", "")
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "updatedInput": {
                    "command": f"timeout 30 {original}"
                },
            }
        }
    return {}
```

### Rate Limiting

```python
from collections import defaultdict
import time

call_counts = defaultdict(list)
RATE_LIMIT = 10  # calls per minute

async def rate_limit(input_data, tool_use_id, context):
    tool_name = input_data["tool_name"]
    now = time.time()

    # Clean old entries
    call_counts[tool_name] = [t for t in call_counts[tool_name] if now - t < 60]

    if len(call_counts[tool_name]) >= RATE_LIMIT:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Rate limit exceeded for {tool_name}",
            }
        }

    call_counts[tool_name].append(now)
    return {}
```

### Stop on Error Pattern

```python
async def stop_on_critical_error(input_data, tool_use_id, context):
    response = str(input_data.get("tool_response", ""))

    if "CRITICAL ERROR" in response or "FATAL" in response:
        return {
            "continue_": False,
            "stopReason": "Critical error detected in tool output",
        }
    return {}

options = ClaudeAgentOptions(
    hooks={
        "PostToolUse": [HookMatcher(matcher="*", hooks=[stop_on_critical_error])],
    }
)
```

## HookMatcher

```python
HookMatcher(
    matcher="Bash",  # Tool name, "*" for all, or regex pattern
    hooks=[callback1, callback2],  # Callbacks to invoke
)
```

Multiple hooks are invoked in order. First hook returning a decision wins.
