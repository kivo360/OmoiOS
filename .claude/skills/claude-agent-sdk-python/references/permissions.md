# Permission Callbacks

Fine-grained control over tool execution with `can_use_tool` callbacks.

## Callback Signature

```python
async def can_use_tool(
    tool_name: str,
    input_data: dict[str, Any],
    context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    ...
```

## ToolPermissionContext

```python
@dataclass
class ToolPermissionContext:
    suggestions: list[str]  # Permission suggestions from CLI
    signal: None  # Reserved for future abort signal
```

## Return Types

### PermissionResultAllow

```python
@dataclass
class PermissionResultAllow:
    updated_input: dict[str, Any] | None = None  # Modify input
    updated_permissions: dict | None = None  # Change permissions dynamically
```

### PermissionResultDeny

```python
@dataclass
class PermissionResultDeny:
    message: str | None = None  # Reason for denial
    interrupt: bool = False  # Stop execution entirely
```

## Examples

### Allow All

```python
from claude_agent_sdk import PermissionResultAllow, ToolPermissionContext

async def allow_all(
    tool_name: str,
    input_data: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow:
    return PermissionResultAllow()
```

### Block Dangerous Commands

```python
from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny, ToolPermissionContext

BLOCKED_PATTERNS = ["rm -rf", "sudo", "> /dev/", "chmod 777", "curl | bash"]

async def block_dangerous(
    tool_name: str,
    input_data: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    if tool_name == "Bash":
        command = input_data.get("command", "")
        for pattern in BLOCKED_PATTERNS:
            if pattern in command:
                return PermissionResultDeny(
                    message=f"Blocked dangerous pattern: {pattern}",
                    interrupt=True
                )
    return PermissionResultAllow()
```

### Modify Tool Input

```python
async def add_safe_mode(
    tool_name: str,
    input_data: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow:
    modified = input_data.copy()
    modified["safe_mode"] = True
    return PermissionResultAllow(updated_input=modified)
```

### File Path Restrictions

```python
from pathlib import Path

ALLOWED_PATHS = ["/home/user/project", "/tmp"]

async def restrict_paths(
    tool_name: str,
    input_data: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    if tool_name in ["Read", "Write", "Edit"]:
        file_path = input_data.get("file_path", "")
        path = Path(file_path).resolve()

        if not any(str(path).startswith(allowed) for allowed in ALLOWED_PATHS):
            return PermissionResultDeny(
                message=f"Path not allowed: {file_path}"
            )
    return PermissionResultAllow()
```

### Logging Permission Decisions

```python
import logging

logger = logging.getLogger(__name__)

async def log_and_allow(
    tool_name: str,
    input_data: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow:
    logger.info(f"Tool: {tool_name}, Input: {input_data}")
    return PermissionResultAllow()
```

## Integration

```python
from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    can_use_tool=block_dangerous,
    allowed_tools=["Read", "Write", "Bash"],
)
```

## Combining with Permission Mode

```python
options = ClaudeAgentOptions(
    permission_mode="acceptEdits",  # Auto-approve file edits
    can_use_tool=block_dangerous,   # But still block dangerous bash
)
```

The `can_use_tool` callback runs after permission mode checks, allowing fine-grained control even with permissive modes.
