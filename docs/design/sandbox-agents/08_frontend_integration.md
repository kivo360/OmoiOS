# Frontend Integration for Sandbox Agents

**Created**: 2025-12-12  
**Status**: Addendum to Existing UI Docs  
**Priority**: Optional (Phase 5 enhancement)

---

## Overview

This document describes **sandbox-specific additions** to the existing frontend. It is NOT a standalone UI spec—the comprehensive UI documentation already exists:

### Existing UI Documentation (Reference These First!)

| Document | Location | Covers |
|----------|----------|--------|
| **Agent Management** | [`page_flows/03_agents_workspaces.md`](../../page_flows/03_agents_workspaces.md) | Agent list, detail view, trajectory, interventions |
| **Command Center** | [`page_flows/10_command_center.md`](../../page_flows/10_command_center.md) | Primary landing, agent spawning, Guardian indicator |
| **Monitoring System** | [`page_flows/10a_monitoring_system.md`](../../page_flows/10a_monitoring_system.md) | System health, trajectory analysis, intervention management |
| **Execution Monitoring** | [`user_journey/03_execution_monitoring.md`](../../user_journey/03_execution_monitoring.md) | User journey for monitoring agents |

---

## What Already Exists (No Changes Needed)

These features are **already designed** in the existing docs:

| Feature | Location | Status |
|---------|----------|--------|
| Agent list with status indicators | `03_agents_workspaces.md` | ✅ Designed |
| Agent detail view with tabs | `03_agents_workspaces.md` | ✅ Designed |
| Real-time activity feed | `10_command_center.md` | ✅ Designed |
| Trajectory timeline | `10a_monitoring_system.md` | ✅ Designed |
| Send intervention UI | `10a_monitoring_system.md` | ✅ Designed |
| Guardian status indicator | `10_command_center.md` | ✅ Designed |
| WebSocket event integration | `10a_monitoring_system.md` | ✅ Designed |
| Agent spawning modal | `03_agents_workspaces.md` | ✅ Designed |

---

## Sandbox-Specific Additions

The following are **new UI elements** specific to sandbox agents that need to be added:

### 1. Sandbox Lifecycle Badge

**Where**: Agent list cards and detail view header

**Current Design** (from `03_agents_workspaces.md`):
```
│ Agent: worker-1                                │
│ Status: 🟢 Active                               │
│ Phase: IMPLEMENTATION                          │
```

**Sandbox Addition**:
```
│ Agent: worker-1                                │
│ Status: 🟢 Active                               │
│ Phase: IMPLEMENTATION                          │
│ Sandbox: ☁️ Daytona • Running                  │  ← NEW
│ Branch: feature/TICKET-123-auth               │  ← NEW
```

**Sandbox Lifecycle States**:
| State | Badge | Color |
|-------|-------|-------|
| PENDING | `⏳ Pending` | Gray |
| CREATING | `🔄 Creating` | Blue |
| RUNNING | `☁️ Running` | Green |
| COMPLETING | `📦 Creating PR` | Yellow |
| COMPLETED | `✅ Completed` | Green |
| FAILED | `❌ Failed` | Red |

---

### 2. Branch & PR Section

**Where**: Agent detail view → New "Git" tab (after existing tabs)

```
┌──────────────────────────────────────────────────────┐
│  Tabs: [Overview] [Trajectory] [Tasks] [Logs] [Git]  │
│                                               ^^^^^   │
│                                               NEW     │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Git Tab                                             │
│                                                      │
│  Repository: kivo360/auth-system                    │
│  Branch: feature/TICKET-123-oauth-setup             │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │  Commits (3)                                   │ │
│  │                                                │ │
│  │  abc1234 feat: add OAuth2 configuration       │ │
│  │          5 files changed, +127 -12            │ │
│  │          12 minutes ago                        │ │
│  │                                                │ │
│  │  def5678 refactor: extract auth service       │ │
│  │          3 files changed, +45 -8              │ │
│  │          8 minutes ago                         │ │
│  │                                                │ │
│  │  ghi9012 fix: handle token expiration         │ │
│  │          2 files changed, +18 -3              │ │
│  │          2 minutes ago                         │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  Pull Request:                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │  PR #42: [TICKET-123] Implement OAuth setup   │ │
│  │  Status: 🟢 Ready for review                  │ │
│  │  Base: main ← feature/TICKET-123-oauth-setup  │ │
│  │                                                │ │
│  │  [View on GitHub] [Approve & Merge]           │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  Merge Conflicts: None ✅                           │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

### 3. Sandbox Resource Indicator

**Where**: Agent detail view header (alongside existing heartbeat)

**Current Design**:
```
│ Heartbeat: 5s ago ✓                            │
```

**Sandbox Addition**:
```
│ Heartbeat: 5s ago ✓                            │
│ Sandbox: ☁️ us-east-1 • 2.1 GB memory          │  ← NEW
│ Uptime: 23m 15s                                │  ← NEW
```

---

### 4. Clone Status During Spawn

**Where**: Spawn agent modal → Processing step

**Enhancement** to existing spawn flow in `10_command_center.md`:

```
┌──────────────────────────────────────────────────────┐
│  Processing...                                       │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │ 1. Creating project (if needed)...  ✓         │ │
│  │ 2. Spawning sandbox environment...   ✓         │ │  ← NEW
│  │ 3. Cloning repository...             ⟳         │ │  ← NEW
│  │    kivo360/auth-system (124 MB)               │ │
│  │    ████████████░░░░░░░░ 60%                   │ │
│  │ 4. Creating branch...                ⏳         │ │  ← NEW
│  │ 5. Starting agent...                 ⏳         │ │
│  └────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

### 5. User Message Panel (Sandbox-Specific)

**Where**: Agent detail view → Bottom of page (like existing intervention modal but for users)

The existing intervention UI in `10a_monitoring_system.md` is for **Guardian-initiated** interventions. For sandbox agents, we need a simpler **user message** panel:

```
┌──────────────────────────────────────────────────────┐
│  Send Message to Agent                               │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │ Also add input validation for the email field │ │
│  │ and make sure to handle empty strings.        │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  ℹ️ Message will be delivered before next action    │
│                                                      │
│  [Send Message]                                      │
└──────────────────────────────────────────────────────┘
```

**API**: Uses existing `POST /api/v1/sandboxes/{id}/messages` endpoint.

**Difference from Guardian Intervention**:
- User messages use `[USER MESSAGE]` prefix
- No intervention type selection (always "guidance")
- Simpler UI without alignment tracking

---

## New API Endpoints Needed

These endpoints are **in addition to** existing APIs documented in `10a_monitoring_system.md`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/sandboxes/{id}` | GET | Get sandbox details (lifecycle, branch, PR) |
| `/api/v1/sandboxes/{id}/git/commits` | GET | Get commits from sandbox branch |
| `/api/v1/sandboxes/{id}/git/pr` | GET | Get PR status if created |
| `/api/v1/sandboxes/{id}/git/pr/merge` | POST | Merge PR (user action) |

**Note**: Core sandbox message/event APIs are already defined in:
- [`04_communication_patterns.md`](./04_communication_patterns.md)
- [`05_http_api_migration.md`](./05_http_api_migration.md)

---

## WebSocket Event Additions

Add these events to the existing event types in `10a_monitoring_system.md`:

| Event Type | Entity Type | Description |
|------------|-------------|-------------|
| `SANDBOX_CREATED` | sandbox | Sandbox environment created |
| `SANDBOX_CLONE_STARTED` | sandbox | Git clone began |
| `SANDBOX_CLONE_COMPLETED` | sandbox | Git clone finished |
| `SANDBOX_BRANCH_CREATED` | sandbox | Feature branch created |
| `SANDBOX_PR_CREATED` | sandbox | Pull request created |
| `SANDBOX_PR_MERGED` | sandbox | Pull request merged |
| `SANDBOX_TERMINATED` | sandbox | Sandbox shut down |

---

## Integration Points with Existing UI

### Agent List (`/agents`)

**Modification**: Add sandbox indicator to agent cards

```tsx
// In existing AgentCard component
{agent.sandbox_id && (
  <div className="sandbox-badge">
    <CloudIcon /> {agent.sandbox_status}
  </div>
)}
```

### Agent Detail View (`/agents/:agentId`)

**Modification**: Add Git tab if agent has `sandbox_id`

```tsx
// In existing agent detail page
const tabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'trajectory', label: 'Trajectory' },
  { id: 'tasks', label: 'Tasks' },
  { id: 'logs', label: 'Logs' },
  // Conditionally add Git tab for sandbox agents
  ...(agent.sandbox_id ? [{ id: 'git', label: 'Git' }] : []),
];
```

### Command Center (`/`)

**Modification**: Spawn flow shows clone progress for sandbox agents

```tsx
// In existing spawn processing component
{spawnConfig.useSandbox && (
  <>
    <ProcessStep status={cloneStatus}>
      Cloning repository... {cloneProgress}%
    </ProcessStep>
    <ProcessStep status={branchStatus}>
      Creating branch: {branchName}
    </ProcessStep>
  </>
)}
```

---

## Implementation Priority

Since the core agent UI already exists, sandbox-specific additions are **lower priority**:

| Feature | Priority | Effort | Depends On |
|---------|----------|--------|------------|
| Sandbox lifecycle badge | Medium | 2h | Backend API |
| Clone progress in spawn | Medium | 3h | Spawn flow exists |
| Git tab with commits/PR | Low | 4h | Branch workflow (Phase 5) |
| User message panel | Low | 2h | Message API exists |

**Total Sandbox-Specific UI Effort**: ~11 hours

---

## Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SANDBOX UI: BUILD ON EXISTING UI                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  EXISTING UI (No changes needed):                                           │
│  ├─ Agent list page             → 03_agents_workspaces.md                   │
│  ├─ Agent detail with tabs      → 03_agents_workspaces.md                   │
│  ├─ Trajectory & interventions  → 10a_monitoring_system.md                  │
│  ├─ Real-time WebSocket events  → 10a_monitoring_system.md                  │
│  └─ Command center & spawn      → 10_command_center.md                      │
│                                                                             │
│  SANDBOX ADDITIONS (This document):                                         │
│  ├─ Sandbox lifecycle badge     → Agent cards & detail header               │
│  ├─ Git tab with branch/PR      → New tab in agent detail                   │
│  ├─ Clone progress during spawn → Enhancement to spawn modal                │
│  └─ User message panel          → Simple UI for sending messages            │
│                                                                             │
│  KEY INSIGHT: Most UI already exists! Sandbox agents are just               │
│  "agents with extra context" - reuse existing components.                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Future Enhancement: Rich Activity Feed

**Status**: Future / Post-MVP  
**Priority**: Nice-to-have  
**Effort**: ~2-3 weeks

### Current State

The existing agent detail view (`10_command_center.md`) shows:
- ✅ Agent thinking indicator ("Thought for 3s")
- ⚠️ Tool use summary only ("Explored 15 files")
- ✅ Agent text responses (rendered blocks)
- ✅ User follow-up input

**What's missing**: Detailed, real-time tool calls and file edits inline (like Cursor/Claude.ai).

---

### Proposed: Rich Activity Feed

Transform the activity feed into a Cursor-style chat interface with expandable tool calls:

```
┌──────────────────────────────────────────────────────────────────────┐
│  Agent Activity Feed                                                  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  💭 Thinking...                                                │ │
│  │  I'll analyze the authentication module to understand the      │ │
│  │  current implementation before adding OAuth2 support.          │ │
│  │                                                     (3.2s)     │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  🔧 Read file: src/auth/handler.py                   [▼ Show]  │ │
│  │     248 lines • completed in 0.3s                              │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  🔧 Search codebase: "jwt token validation"          [▼ Show]  │ │
│  │     Found 3 files • completed in 1.2s                          │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  💬 Agent Response                                             │ │
│  │                                                                │ │
│  │  I've analyzed the codebase. The current auth system uses      │ │
│  │  basic JWT validation in `handler.py`. I'll now add OAuth2     │ │
│  │  support by:                                                   │ │
│  │                                                                │ │
│  │  1. Creating an OAuth2 configuration module                    │ │
│  │  2. Adding token refresh logic                                 │ │
│  │  3. Updating the handler to support both flows                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  📝 Edited: src/auth/oauth2.py (NEW)                 [▼ Diff]  │ │
│  │     +127 lines • created new file                              │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │  + """OAuth2 authentication module."""                   │ │ │
│  │  │  + from typing import Optional                           │ │ │
│  │  │  + import jwt                                            │ │ │
│  │  │  +                                                       │ │ │
│  │  │  + class OAuth2Handler:                                  │ │ │
│  │  │  +     def __init__(self, client_id: str):              │ │ │
│  │  │  +         self.client_id = client_id                   │ │ │
│  │  │  +         ...                                          │ │ │
│  │  │  │                                    [View Full Diff →] │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  📝 Edited: src/auth/handler.py                      [▼ Diff]  │ │
│  │     +15 -3 lines                                               │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │    def validate_token(self, token: str):                 │ │ │
│  │  │  -     return jwt.decode(token, self.secret)             │ │ │
│  │  │  +     # Support both JWT and OAuth2 tokens              │ │ │
│  │  │  +     if self._is_oauth_token(token):                   │ │ │
│  │  │  +         return self.oauth2.validate(token)            │ │ │
│  │  │  +     return jwt.decode(token, self.secret)             │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  🔧 Run command: pytest tests/auth/                  [▼ Show]  │ │
│  │     ✅ 12 passed • completed in 4.5s                           │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  [Ask follow-up or provide guidance...]                      [Send] │
└──────────────────────────────────────────────────────────────────────┘
```

---

### New WebSocket Events Required

Add these to the event types in `10a_monitoring_system.md`:

```python
# Tool Execution Events
TOOL_STARTED = "TOOL_STARTED"
TOOL_COMPLETED = "TOOL_COMPLETED"
TOOL_FAILED = "TOOL_FAILED"

# File Change Events
FILE_CREATED = "FILE_CREATED"
FILE_EDITED = "FILE_EDITED"
FILE_DELETED = "FILE_DELETED"

# Streaming Events
AGENT_THINKING_START = "AGENT_THINKING_START"
AGENT_THINKING_END = "AGENT_THINKING_END"
AGENT_MESSAGE_CHUNK = "AGENT_MESSAGE_CHUNK"
AGENT_MESSAGE_END = "AGENT_MESSAGE_END"
```

**Event Payloads**:

```json
// TOOL_STARTED
{
  "event_type": "TOOL_STARTED",
  "entity_type": "agent",
  "entity_id": "worker-1",
  "payload": {
    "tool_id": "uuid",
    "tool_name": "read_file",
    "tool_args": {
      "path": "src/auth/handler.py"
    }
  }
}

// TOOL_COMPLETED
{
  "event_type": "TOOL_COMPLETED",
  "entity_type": "agent",
  "entity_id": "worker-1",
  "payload": {
    "tool_id": "uuid",
    "tool_name": "read_file",
    "duration_ms": 320,
    "result_summary": "248 lines",
    "result_preview": "First 500 chars...",  // Optional, for expandable view
    "success": true
  }
}

// FILE_EDITED
{
  "event_type": "FILE_EDITED",
  "entity_type": "agent",
  "entity_id": "worker-1",
  "payload": {
    "file_path": "src/auth/handler.py",
    "change_type": "edit",  // "create", "edit", "delete"
    "lines_added": 15,
    "lines_removed": 3,
    "diff_preview": "--- a/src/auth/handler.py\n+++ b/src/auth/handler.py\n...",
    "commit_sha": null  // Filled after commit
  }
}

// AGENT_MESSAGE_CHUNK (for streaming)
{
  "event_type": "AGENT_MESSAGE_CHUNK",
  "entity_type": "agent",
  "entity_id": "worker-1",
  "payload": {
    "message_id": "uuid",
    "chunk": "I've analyzed the codebase. The current auth system uses ",
    "chunk_index": 0,
    "is_thinking": false
  }
}
```

---

### New UI Components Required

```tsx
// 1. ToolCallCard - Expandable tool execution display
interface ToolCallCardProps {
  toolName: string;
  toolArgs: Record<string, any>;
  status: 'running' | 'completed' | 'failed';
  durationMs?: number;
  resultSummary?: string;
  resultPreview?: string;  // For expansion
}

// 2. FileChangeCard - Inline diff preview
interface FileChangeCardProps {
  filePath: string;
  changeType: 'create' | 'edit' | 'delete';
  linesAdded: number;
  linesRemoved: number;
  diffPreview: string;
  isExpanded: boolean;
  onToggle: () => void;
}

// 3. StreamingMessage - Typewriter-style message rendering
interface StreamingMessageProps {
  messageId: string;
  chunks: string[];
  isComplete: boolean;
  isThinking: boolean;
}

// 4. ActivityFeed - Container for all activity items
interface ActivityFeedProps {
  agentId: string;
  items: ActivityItem[];  // Union of tools, files, messages
  onSendMessage: (message: string) => void;
}
```

---

### Backend Implementation Required

#### 1. SDK Hook Integration

Hook into Claude Agent SDK callbacks to emit events:

```python
# In sandbox worker or agent wrapper
from claude_sdk import Agent, PreToolUseHook, PostToolUseHook

class EventEmittingHooks:
    def __init__(self, event_bus: EventBusService, agent_id: str):
        self.event_bus = event_bus
        self.agent_id = agent_id
    
    async def pre_tool_use(self, tool_name: str, tool_args: dict) -> None:
        """Emit TOOL_STARTED event."""
        await self.event_bus.publish(SystemEvent(
            event_type="TOOL_STARTED",
            entity_type="agent",
            entity_id=self.agent_id,
            payload={
                "tool_id": str(uuid.uuid4()),
                "tool_name": tool_name,
                "tool_args": tool_args,
            }
        ))
    
    async def post_tool_use(
        self, 
        tool_name: str, 
        tool_args: dict, 
        result: Any,
        duration_ms: int,
    ) -> None:
        """Emit TOOL_COMPLETED event with result summary."""
        await self.event_bus.publish(SystemEvent(
            event_type="TOOL_COMPLETED",
            entity_type="agent",
            entity_id=self.agent_id,
            payload={
                "tool_id": tool_args.get("_tool_id"),
                "tool_name": tool_name,
                "duration_ms": duration_ms,
                "result_summary": self._summarize_result(tool_name, result),
                "success": True,
            }
        ))
    
    def _summarize_result(self, tool_name: str, result: Any) -> str:
        """Create human-readable summary of tool result."""
        if tool_name == "read_file":
            return f"{result.count(chr(10)) + 1} lines"
        elif tool_name == "str_replace_editor":
            # Parse the edit result
            return f"+{result.lines_added} -{result.lines_removed} lines"
        elif tool_name == "bash":
            return f"Exit code: {result.exit_code}"
        # ... other tools
        return "Completed"
```

#### 2. File Change Detection

```python
# Track file changes from str_replace_editor tool
async def on_file_edit(
    self,
    file_path: str,
    old_content: str,
    new_content: str,
) -> None:
    """Emit FILE_EDITED event with diff preview."""
    import difflib
    
    diff = list(difflib.unified_diff(
        old_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
    ))
    
    lines_added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
    lines_removed = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
    
    await self.event_bus.publish(SystemEvent(
        event_type="FILE_EDITED",
        entity_type="agent",
        entity_id=self.agent_id,
        payload={
            "file_path": file_path,
            "change_type": "edit",
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "diff_preview": ''.join(diff[:50]),  # First 50 lines of diff
        }
    ))
```

#### 3. Streaming Message Support

```python
# Wrap agent message streaming
async def stream_agent_response(
    self,
    message_id: str,
    response_stream: AsyncIterator[str],
) -> None:
    """Stream agent response chunks over WebSocket."""
    chunk_index = 0
    
    async for chunk in response_stream:
        await self.event_bus.publish(SystemEvent(
            event_type="AGENT_MESSAGE_CHUNK",
            entity_type="agent",
            entity_id=self.agent_id,
            payload={
                "message_id": message_id,
                "chunk": chunk,
                "chunk_index": chunk_index,
                "is_thinking": False,
            }
        ))
        chunk_index += 1
    
    await self.event_bus.publish(SystemEvent(
        event_type="AGENT_MESSAGE_END",
        entity_type="agent",
        entity_id=self.agent_id,
        payload={"message_id": message_id}
    ))
```

---

### Implementation Effort Estimate

| Component | Effort | Notes |
|-----------|--------|-------|
| **Backend: SDK Hooks** | 3-4 days | Hook into Claude SDK callbacks |
| **Backend: Event Types** | 1 day | Add new event types to system |
| **Backend: Diff Generation** | 1 day | Parse and summarize file changes |
| **Frontend: ToolCallCard** | 2 days | Expandable component with syntax highlighting |
| **Frontend: FileChangeCard** | 2-3 days | Inline diff viewer |
| **Frontend: StreamingMessage** | 2 days | Typewriter effect, chunk assembly |
| **Frontend: ActivityFeed** | 2-3 days | Container, virtual scrolling, state management |
| **Integration Testing** | 2 days | WebSocket flow, UI tests |
| **Total** | **~2-3 weeks** | |

---

### Phased Rollout

**Phase 1 (MVP - 1 week)**:
- Tool call cards (collapsed by default)
- Basic file change notifications
- No streaming (render complete messages)

**Phase 2 (Enhanced - 1 week)**:
- Expandable tool results
- Inline diff previews
- Streaming message support

**Phase 3 (Polish - 1 week)**:
- Syntax highlighting in diffs
- Virtual scrolling for long sessions
- Export activity log

---

### Inspiration

This design is inspired by:
- **Cursor IDE** - Background agent activity feed
- **Claude.ai** - Artifacts with tool use display
- **GitHub Copilot Workspace** - Step-by-step execution visibility
- **Devin** - Full session replay with tool calls

---

## Related Documents

- [Architecture](./01_architecture.md) - System design
- [Communication Patterns](./04_communication_patterns.md) - API specs with security
- [Implementation Checklist](./06_implementation_checklist.md) - Phase 5 details
- [Agent Management (Existing)](../../page_flows/03_agents_workspaces.md) - Core agent UI
- [Monitoring System (Existing)](../../page_flows/10a_monitoring_system.md) - Health & interventions
