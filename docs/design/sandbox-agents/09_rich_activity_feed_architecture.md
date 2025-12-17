# Rich Activity Feed Architecture

**Created**: 2025-12-12  
**Status**: Phase 2 Implemented ✅ | Remaining phases: Future Enhancement (Post-MVP)  
**Priority**: Phase 2: Complete | Remaining: Nice-to-have  
**Related**: [08_frontend_integration.md](./08_frontend_integration.md) (UI spec)

---

## Overview

This document describes the **architectural changes** required to support a rich, real-time activity feed showing detailed tool calls, file edits, and streaming messages—similar to Cursor IDE's background agent view.

**Current State**: Sandbox agents report high-level progress events ("step_completed", "file_modified").

**Target State**: Real-time streaming of individual tool calls, inline file diffs, and character-by-character message streaming.

---

## Architectural Gap Analysis

### What Currently Exists ✅

| Component | Location | Capability |
|-----------|----------|------------|
| Event Callback Endpoint | `04_communication_patterns.md` | Sandbox → Backend HTTP events |
| WebSocket Relay | `01_architecture.md` | Backend → Frontend real-time events |
| PreToolUse Hooks | `04_communication_patterns.md` | Intervention injection before tool calls |
| PostToolUse Hooks | SDK documentation | Callback after tool execution |
| Event Bus | `07_existing_systems_integration.md` | Redis pub/sub for event distribution |

### What's Missing ❌

| Gap | Impact | Section | Status |
|-----|--------|---------|--------|
| **Granular Tool Events** | Can't show individual tool calls | [1. Event Granularity](#1-event-granularity-enhancement) | ⏳ Pending |
| **High-Frequency Event Handling** | Performance issues at scale | [2. Event Throttling](#2-event-throttling-strategy) | ⏳ Pending |
| **File Diff Generation** | Can't show inline code changes | [3. Diff Capture](#3-file-diff-capture) | ✅ **IMPLEMENTED** |
| **Message Streaming** | Can't show typewriter effect | [4. Message Streaming](#4-message-streaming-architecture) | ⏳ Pending |
| **Tool Event Persistence** | Can't replay/audit tool history | [5. Event Storage](#5-event-storage-strategy) | ⏳ Pending |
| **SDK Integration** | Claude Agent SDK patterns | [6. SDK Integration](#6-sdk-integration-layer) | ✅ **IMPLEMENTED** |

---

## 1. Event Granularity Enhancement

### Current: Task-Level Events

```python
# Current progress event (04_communication_patterns.md)
{
    "event_type": "step_completed",
    "message": "Analyzed 15 files",
    "progress_percent": 30
}
```

### Target: Tool-Level Events

```python
# New granular events
{
    "event_type": "TOOL_STARTED",
    "tool_name": "read_file",
    "tool_args": {"path": "src/auth/handler.py"},
    "tool_id": "uuid-123"
}

{
    "event_type": "TOOL_COMPLETED",
    "tool_id": "uuid-123",
    "tool_name": "read_file",
    "duration_ms": 320,
    "result_summary": "248 lines",
    "success": true
}
```

### Required Changes

#### 1.1 New Event Types

Add to `04_communication_patterns.md` event type enum:

```python
# backend/omoi_os/models/events.py

class SandboxEventType(str, Enum):
    # Existing
    STEP_COMPLETED = "step_completed"
    FILE_MODIFIED = "file_modified"
    ERROR = "error"
    INFO = "info"
    
    # NEW: Tool-level events
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    TOOL_FAILED = "TOOL_FAILED"
    
    # NEW: File-level events
    FILE_CREATED = "FILE_CREATED"
    FILE_EDITED = "FILE_EDITED"
    FILE_DELETED = "FILE_DELETED"
    
    # NEW: Message streaming events
    AGENT_THINKING_START = "AGENT_THINKING_START"
    AGENT_THINKING_END = "AGENT_THINKING_END"
    AGENT_MESSAGE_CHUNK = "AGENT_MESSAGE_CHUNK"
    AGENT_MESSAGE_END = "AGENT_MESSAGE_END"
```

#### 1.2 API Changes

Enhance the existing `/api/v1/sandbox/task/{task_id}/progress` endpoint to accept tool-level events:

```python
# backend/omoi_os/api/routes/sandbox.py

class ToolEventCreate(BaseModel):
    """Tool-level event (higher frequency than progress events)."""
    event_type: Literal["TOOL_STARTED", "TOOL_COMPLETED", "TOOL_FAILED"]
    tool_id: str = Field(..., description="Unique ID for this tool call")
    tool_name: str = Field(..., max_length=100)
    tool_args: dict[str, Any] = Field(default_factory=dict)
    
    # For TOOL_COMPLETED/TOOL_FAILED only
    duration_ms: Optional[int] = None
    result_summary: Optional[str] = Field(None, max_length=500)
    result_preview: Optional[str] = Field(None, max_length=5000)
    success: Optional[bool] = None
    error_message: Optional[str] = None

@router.post("/task/{task_id}/tool-events")
async def report_tool_event(
    task_id: str,
    event: ToolEventCreate,
    sandbox: SandboxSession = Depends(get_sandbox_from_token),
    event_bus: EventBusService = Depends(),
):
    """Report a tool-level event (for Rich Activity Feed)."""
    # Validate task ownership
    # Broadcast to WebSocket
    # Optionally persist (see Section 5)
    pass
```

---

## 2. Event Throttling Strategy

### Problem

Tool calls can happen **very frequently** (10-100+ per minute). Naive broadcasting will:
- Overwhelm the WebSocket connection
- Flood the frontend with updates
- Create excessive Redis pub/sub traffic

### Solution: Tiered Event Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EVENT TIERING STRATEGY                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TIER 1: Critical Events (Always broadcast immediately)                     │
│  ─────────────────────────────────────────────────────                      │
│  • agent.tool_failed - User needs to know immediately                      │
│  • agent.file_edited - High-value visibility (file changes)                │
│  • agent.message_chunk - Streaming text                                    │
│  • Task status changes                                                     │
│                                                                             │
│  TIER 2: Informational Events (Batched, 500ms window)                       │
│  ─────────────────────────────────────────────────────                      │
│  • agent.tool_use (started) - Can be batched                              │
│  • agent.tool_completed (success) - Can be batched                        │
│  • agent.file_created - Less urgent                                       │
│                                                                             │
│  TIER 3: Diagnostic Events (On-demand only)                                 │
│  ─────────────────────────────────────────────────────                      │
│  • Full tool arguments (large payloads)                                    │
│  • Result previews (can be 5KB+)                                           │
│  • Persisted, fetched on expand                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Implementation

#### 2.1 Backend Event Batcher

```python
# backend/omoi_os/services/event_batcher.py

from collections import defaultdict
import asyncio

class EventBatcher:
    """Batches Tier 2 events to reduce WebSocket traffic."""
    
    def __init__(self, flush_interval_ms: int = 500):
        self.flush_interval = flush_interval_ms / 1000
        self.buffers: dict[str, list] = defaultdict(list)  # sandbox_id → events
        self._flush_tasks: dict[str, asyncio.Task] = {}
    
    async def add_event(self, sandbox_id: str, event: dict, tier: int = 2):
        if tier == 1:
            # Tier 1: Immediate broadcast
            await self._broadcast_immediate(sandbox_id, event)
        else:
            # Tier 2: Buffer and batch
            self.buffers[sandbox_id].append(event)
            self._schedule_flush(sandbox_id)
    
    def _schedule_flush(self, sandbox_id: str):
        if sandbox_id not in self._flush_tasks:
            self._flush_tasks[sandbox_id] = asyncio.create_task(
                self._delayed_flush(sandbox_id)
            )
    
    async def _delayed_flush(self, sandbox_id: str):
        await asyncio.sleep(self.flush_interval)
        events = self.buffers.pop(sandbox_id, [])
        del self._flush_tasks[sandbox_id]
        if events:
            await self._broadcast_batch(sandbox_id, events)
    
    async def _broadcast_batch(self, sandbox_id: str, events: list):
        """Broadcast multiple events as a single WebSocket message."""
        await event_bus.publish(SystemEvent(
            event_type="TOOL_EVENTS_BATCH",
            entity_type="sandbox",
            entity_id=sandbox_id,
            payload={"events": events, "count": len(events)}
        ))
```

#### 2.2 Frontend Event Processing

```typescript
// frontend/hooks/useToolEvents.ts

interface ToolEvent {
  event_type: string;
  tool_id: string;
  tool_name: string;
  // ...
}

export function useToolEvents(sandboxId: string) {
  const [events, setEvents] = useState<ToolEvent[]>([]);
  
  useEntityEvents("sandbox", sandboxId, (event) => {
    if (event.event_type === "TOOL_EVENTS_BATCH") {
      // Handle batched events
      setEvents(prev => [...prev, ...event.payload.events]);
    } else if (event.event_type.startsWith("TOOL_")) {
      // Handle individual events (Tier 1)
      setEvents(prev => [...prev, event]);
    }
  });
  
  return events;
}
```

---

## 3. File Diff Capture

### Problem

To show inline file diffs, we need to capture the **before** and **after** state of files.

### Solution: PreToolUse + PostToolUse Hook Interception

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FILE DIFF CAPTURE FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Agent calls Write or Edit tool (Claude Agent SDK)                       │
│                                                                             │
│  2. PreToolUse hook fires BEFORE tool execution                             │
│     └─ Reads and caches current file content (if file exists)             │
│     └─ Stores in FileChangeTracker cache                                   │
│                                                                             │
│  3. Tool executes (Write/Edit modifies file)                                 │
│                                                                             │
│  4. PostToolUse hook fires AFTER tool execution                              │
│     └─ Retrieves new content from tool_input or filesystem                 │
│     └─ Generates unified diff using cached old_content                     │
│                                                                             │
│  5. agent.file_edited event emitted with:                                  │
│     └─ file_path, lines_added, lines_removed                               │
│     └─ diff_preview (truncated, ~5KB max)                                   │
│     └─ full_diff (if small) or full_diff_available flag                     │
│                                                                             │
│  6. Frontend shows collapsed diff card                                      │
│     └─ On expand: fetches full diff if needed                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Implementation

#### 3.1 Worker Script Enhancement (Claude Agent SDK)

```python
# In claude_sandbox_worker.py - PreToolUse + PostToolUse hooks

import difflib
from pathlib import Path
from typing import Optional, Any
from claude_agent_sdk import HookMatcher, HookInput, HookContext, HookJSONOutput

class FileChangeTracker:
    """Tracks file changes for diff generation."""
    
    def __init__(self):
        self.file_cache: dict[str, str] = {}  # path → content before edit
    
    def cache_file_before_edit(self, path: str, content: str):
        """Called by PreToolUse hook when Write/Edit is about to run."""
        self.file_cache[path] = content
    
    def generate_diff(self, path: str, new_content: str) -> dict:
        """Generate diff after edit completes."""
        old_content = self.file_cache.pop(path, "")
        
        # Handle new file creation (no old content)
        if not old_content:
            # Count lines in new file
            new_lines = new_content.splitlines(keepends=True)
            lines_added = len(new_lines)
            lines_removed = 0
            
            # Create diff showing all new lines
            diff = [f"--- /dev/null\n", f"+++ b/{path}\n"]
            for i, line in enumerate(new_lines, 1):
                diff.append(f"+{line}")
            
            change_type = "created"
        else:
            # Existing file modification
            old_lines = old_content.splitlines(keepends=True)
            new_lines = new_content.splitlines(keepends=True)
            
            diff = list(difflib.unified_diff(
                old_lines, new_lines,
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm='',
            ))
            
            lines_added = sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))
            lines_removed = sum(1 for l in diff if l.startswith('-') and not l.startswith('---'))
            change_type = "modified"
        
        # Truncate diff preview (first 100 lines)
        diff_text = ''.join(diff)
        diff_preview = '\n'.join(diff[:100])
        if len(diff) > 100:
            diff_preview += f"\n... ({len(diff) - 100} more lines)"
        
        return {
            "file_path": path,
            "change_type": change_type,  # "created" or "modified"
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "diff_preview": diff_preview[:5000],  # Max 5KB preview
            "full_diff": diff_text if len(diff_text) <= 50000 else None,  # Full diff if < 50KB
            "full_diff_available": len(diff_text) > 5000,
            "full_diff_size": len(diff_text),
        }

# Initialize tracker
file_tracker = FileChangeTracker()

# PreToolUse hook: Cache file content BEFORE edit
async def pre_tool_use_file_cache(
    input_data: HookInput,
    tool_use_id: str | None,
    context: HookContext
) -> HookJSONOutput:
    """Cache file content before Write/Edit tool executes."""
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    
    # Handle Write tool (full file write)
    if tool_name == "Write":
        file_path = tool_input.get("file_path")
        if file_path:
            file_path = Path(file_path)
            if file_path.exists():
                try:
                    old_content = file_path.read_text()
                    file_tracker.cache_file_before_edit(str(file_path), old_content)
                except Exception as e:
                    print(f"[FileTracker] Failed to cache {file_path}: {e}")
    
    # Handle Edit tool (partial replacement)
    elif tool_name == "Edit":
        file_path = tool_input.get("file_path")
        if file_path:
            file_path = Path(file_path)
            if file_path.exists():
                try:
                    old_content = file_path.read_text()
                    file_tracker.cache_file_before_edit(str(file_path), old_content)
                except Exception as e:
                    print(f"[FileTracker] Failed to cache {file_path}: {e}")
    
    return {}  # Allow tool to proceed

# PostToolUse hook: Generate diff AFTER edit
async def post_tool_use_file_diff(
    input_data: HookInput,
    tool_use_id: str | None,
    context: HookContext
) -> HookJSONOutput:
    """Generate file diff after Write/Edit tool completes."""
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    tool_response = input_data.get("tool_response", "")
    
    # Handle Write tool
    if tool_name == "Write":
        file_path = tool_input.get("file_path")
        if file_path:
            file_path = Path(file_path)
            # New content is in tool_input["content"] for Write
            new_content = tool_input.get("content", "")
            
            if new_content:
                diff_info = file_tracker.generate_diff(str(file_path), new_content)
                await reporter.report("agent.file_edited", {
                    "turn": turn_count,
                    "tool_use_id": tool_use_id,
                    **diff_info,
                })
    
    # Handle Edit tool (partial replacement)
    elif tool_name == "Edit":
        file_path = tool_input.get("file_path")
        if file_path:
            file_path = Path(file_path)
            # For Edit, we need to read the file after edit completes
            # because Edit does partial replacement
            if file_path.exists():
                try:
                    new_content = file_path.read_text()
                    diff_info = file_tracker.generate_diff(str(file_path), new_content)
                    await reporter.report("agent.file_edited", {
                        "turn": turn_count,
                        "tool_use_id": tool_use_id,
                        **diff_info,
                    })
                except Exception as e:
                    print(f"[FileTracker] Failed to read {file_path} after edit: {e}")
    
    return {}

# Register hooks with ClaudeAgentOptions
options = ClaudeAgentOptions(
    # ... other options ...
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Write", hooks=[pre_tool_use_file_cache]),
            HookMatcher(matcher="Edit", hooks=[pre_tool_use_file_cache]),
        ],
        "PostToolUse": [
            HookMatcher(matcher="Write", hooks=[post_tool_use_file_diff]),
            HookMatcher(matcher="Edit", hooks=[post_tool_use_file_diff]),
        ],
    },
)
```

#### 3.1.1 Tool-Specific Handling

**Write Tool** (Full file replacement):
- `tool_input["file_path"]`: Target file path
- `tool_input["content"]`: Complete new file content
- New content available in `tool_input`, no filesystem read needed

**Edit Tool** (Partial replacement):
- `tool_input["file_path"]`: Target file path
- `tool_input["old_string"]`: Text to replace
- `tool_input["new_string"]`: Replacement text
- Must read filesystem after edit to get final content

#### 3.2 Event Structure

```python
# agent.file_edited event payload
{
    "event_type": "agent.file_edited",
    "event_data": {
        "turn": 3,
        "tool_use_id": "tool_abc123",
        "file_path": "/workspace/src/auth/handler.py",
        "change_type": "modified",  # or "created"
        "lines_added": 15,
        "lines_removed": 8,
        "diff_preview": "--- a/src/auth/handler.py\n+++ b/src/auth/handler.py\n@@ -10,7 +10,9 @@\n...",
        "full_diff": "...",  # Only if < 50KB
        "full_diff_available": true,
        "full_diff_size": 12345,
    }
}
```

#### 3.1.5 Integration with Existing Worker

**✅ IMPLEMENTATION COMPLETE** - The following steps have been implemented in `claude_sandbox_worker.py`:

1. ✅ **Add FileChangeTracker to SandboxWorker** - COMPLETE
2. ✅ **Create PreToolUse hook for file caching** - COMPLETE
3. ✅ **Enhance PostToolUse hook to generate diffs** - COMPLETE
4. ✅ **Update WorkerConfig.to_sdk_options() to accept PreToolUse hooks** - COMPLETE

The implementation is active and emitting `agent.file_edited` events with full diff data.

**Step 1: Add FileChangeTracker**

```python
# In claude_sandbox_worker.py - SandboxWorker class

class SandboxWorker:
    def __init__(self, config: WorkerConfig):
        # ... existing init ...
        self.file_tracker = FileChangeTracker()  # Add this
```

**Step 2: Create PreToolUse Hook**

```python
async def _create_pre_tool_hook(self):
    """Create PreToolUse hook for file caching."""
    file_tracker = self.file_tracker
    
    async def pre_tool_use_file_cache(
        input_data: HookInput,
        tool_use_id: str | None,
        context: HookContext
    ) -> HookJSONOutput:
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        
        # Cache file content before Write/Edit
        if tool_name in ["Write", "Edit"]:
            file_path = tool_input.get("file_path")
            if file_path:
                file_path = Path(file_path)
                if file_path.exists():
                    try:
                        old_content = file_path.read_text()
                        file_tracker.cache_file_before_edit(str(file_path), old_content)
                    except Exception as e:
                        print(f"[FileTracker] Failed to cache {file_path}: {e}")
        
        return {}
    
    return pre_tool_use_file_cache
```

**Step 3: Enhance PostToolUse Hook**

```python
async def _create_post_tool_hook(self):
    """Create PostToolUse hook with file diff generation."""
    reporter = self.reporter
    file_tracker = self.file_tracker
    turn_count = self.turn_count
    
    async def post_tool_use_with_diff(
        input_data: HookInput,
        tool_use_id: str | None,
        context: HookContext
    ) -> HookJSONOutput:
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", "")
        
        # Existing tool tracking
        event_data = {
            "turn": turn_count,
            "tool": tool_name,
            "tool_input": tool_input,
            "tool_response": str(tool_response)[:2000] if tool_response else None,
        }
        
        # File diff generation for Write/Edit
        if tool_name == "Write":
            file_path = tool_input.get("file_path")
            new_content = tool_input.get("content", "")
            if file_path and new_content:
                diff_info = file_tracker.generate_diff(file_path, new_content)
                await reporter.report("agent.file_edited", {
                    "turn": turn_count,
                    "tool_use_id": tool_use_id,
                    **diff_info,
                })
        
        elif tool_name == "Edit":
            file_path = tool_input.get("file_path")
            if file_path:
                file_path = Path(file_path)
                if file_path.exists():
                    try:
                        new_content = file_path.read_text()
                        diff_info = file_tracker.generate_diff(str(file_path), new_content)
                        await reporter.report("agent.file_edited", {
                            "turn": turn_count,
                            "tool_use_id": tool_use_id,
                            **diff_info,
                        })
                    except Exception as e:
                        print(f"[FileTracker] Failed to read {file_path} after edit: {e}")
        
        # Existing tool completion tracking
        await reporter.report("agent.tool_completed", event_data)
        return {}
    
    return post_tool_use_with_diff
```

**Step 4: Update WorkerConfig.to_sdk_options()**

```python
# In WorkerConfig class

def to_sdk_options(self, pre_tool_hook=None, post_tool_hook=None) -> "ClaudeAgentOptions":
    """Create ClaudeAgentOptions from config with hooks."""
    # ... existing options_kwargs setup ...
    
    # Add hooks
    hooks = {}
    if pre_tool_hook:
        hooks["PreToolUse"] = [
            HookMatcher(matcher="Write", hooks=[pre_tool_hook]),
            HookMatcher(matcher="Edit", hooks=[pre_tool_hook]),
        ]
    if post_tool_hook:
        hooks["PostToolUse"] = [
            HookMatcher(matcher=None, hooks=[post_tool_hook]),  # All tools
        ]
    
    if hooks:
        options_kwargs["hooks"] = hooks
    
    return ClaudeAgentOptions(**options_kwargs)
```

**Step 5: Wire Up in run() Method**

```python
async def run(self):
    # ... existing setup ...
    
    # Create hooks
    pre_tool_hook = await self._create_pre_tool_hook()
    post_tool_hook = await self._create_post_tool_hook()
    
    # Update SDK options with both hooks
    sdk_options = self.config.to_sdk_options(
        pre_tool_hook=pre_tool_hook,
        post_tool_hook=post_tool_hook,
    )
    
    # ... rest of run() ...
```

#### 3.3 Full Diff Fetch Endpoint

```python
# backend/omoi_os/api/routes/sandbox.py

@router.get("/{sandbox_id}/file-diffs/{event_id}")
async def get_full_diff(
    sandbox_id: str,
    event_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Fetch full diff for a file edit event (when preview is truncated)."""
    # Retrieve event from database
    event = db.get_sandbox_event(sandbox_id, event_id)
    if not event or event.event_type != "agent.file_edited":
        raise HTTPException(404, "Diff not found")
    
    # If full diff was stored, return it
    if event.event_data.get("full_diff"):
        return {
            "file_path": event.event_data["file_path"],
            "diff": event.event_data["full_diff"],
        }
    
    # Otherwise, fetch from Redis event store (see Section 5)
    # or regenerate from stored file states
    raise HTTPException(404, "Full diff not available")
```

#### 3.4 Frontend Event Consumption

The frontend receives `agent.file_edited` events via WebSocket and displays them:

```typescript
// frontend/hooks/useSandboxEvents.ts

interface FileEditedEvent {
  event_type: "agent.file_edited"
  event_data: {
    turn: number
    tool_use_id: string
    file_path: string
    change_type: "created" | "modified"
    lines_added: number
    lines_removed: number
    diff_preview: string
    full_diff?: string
    full_diff_available: boolean
    full_diff_size?: number
  }
}

// Component that renders file changes
function FileChangeCard({ event }: { event: FileEditedEvent }) {
  const [expanded, setExpanded] = useState(false)
  const [fullDiff, setFullDiff] = useState<string | null>(null)
  
  const needsFullDiff = event.event_data.full_diff_available && !event.event_data.full_diff
  
  const loadFullDiff = async () => {
    if (needsFullDiff) {
      const response = await fetch(
        `/api/v1/sandboxes/${sandboxId}/file-diffs/${event.event_id}`
      )
      const data = await response.json()
      setFullDiff(data.diff)
    }
  }
  
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <FileCode className="h-4 w-4" />
          <span className="font-mono text-sm">{event.event_data.file_path}</span>
          <Badge>{event.event_data.change_type}</Badge>
          <span className="text-green-600">+{event.event_data.lines_added}</span>
          <span className="text-red-500">-{event.event_data.lines_removed}</span>
        </div>
      </CardHeader>
      <CardContent>
        <DiffViewer
          diff={expanded && fullDiff ? fullDiff : event.event_data.diff_preview}
        />
        {needsFullDiff && !expanded && (
          <Button onClick={() => { setExpanded(true); loadFullDiff() }}>
            Show full diff ({event.event_data.full_diff_size} bytes)
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
```

#### 3.2 Full Diff Fetch Endpoint

```python
# backend/omoi_os/api/routes/sandbox.py

@router.get("/sandbox/{sandbox_id}/file-diffs/{event_id}")
async def get_full_diff(
    sandbox_id: str,
    event_id: str,
    sandbox: SandboxSession = Depends(get_sandbox_from_token),
):
    """Fetch full diff for a file edit event (when preview is truncated)."""
    # Retrieve from event storage (see Section 5)
    pass
```

---

## 4. Message Streaming Architecture

### Problem

Current design renders complete agent messages. Users want to see messages as they're generated (typewriter effect).

### Solution: Chunk-Based Streaming

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MESSAGE STREAMING FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Claude SDK (has native streaming):                                         │
│  ─────────────────────────────────                                          │
│  async for event in agent.run_async():                                      │
│      if isinstance(event, TextEvent):                                       │
│          # Stream each text chunk                                           │
│          await report_chunk(event.text)                                     │
│                                                                             │
│  Claude Agent SDK (streaming-based):                                        │
│  ──────────────────────────────────                                          │
│  # Messages stream via receive_*() methods                                  │
│  # Option 1: Stream chunks as they arrive                                    │
│  # Option 2: Accept complete messages for Claude Agent SDK                    │
│                                                                             │
│  Backend Relay:                                                             │
│  ──────────────                                                             │
│  POST /api/v1/sandbox/task/{task_id}/message-chunks                        │
│  { message_id, chunk_index, chunk_text, is_thinking, is_final }            │
│                                                                             │
│  WebSocket Broadcast:                                                       │
│  ───────────────────                                                        │
│  Event: AGENT_MESSAGE_CHUNK                                                 │
│  Payload: { message_id, chunk, chunk_index, is_thinking }                  │
│                                                                             │
│  Frontend Assembly:                                                         │
│  ─────────────────                                                          │
│  Accumulate chunks by message_id                                            │
│  Render with typewriter animation                                           │
│  Mark complete when is_final=true                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Implementation

#### 4.1 Streaming Endpoint

```python
# backend/omoi_os/api/routes/sandbox.py

class MessageChunkCreate(BaseModel):
    message_id: str
    chunk: str = Field(..., max_length=1000)
    chunk_index: int
    is_thinking: bool = False
    is_final: bool = False

@router.post("/task/{task_id}/message-chunks")
async def report_message_chunk(
    task_id: str,
    chunk: MessageChunkCreate,
    sandbox: SandboxSession = Depends(get_sandbox_from_token),
    event_bus: EventBusService = Depends(),
):
    """Stream agent message chunks for real-time display."""
    event_bus.publish(SystemEvent(
        event_type="AGENT_MESSAGE_CHUNK",
        entity_type="task",
        entity_id=task_id,
        payload=chunk.dict()
    ))
    return {"success": True}
```

#### 4.2 Worker Script Integration (Claude SDK)

```python
# Streaming wrapper for Claude SDK

async def run_agent_with_streaming(agent, task):
    message_id = str(uuid.uuid4())
    chunk_index = 0
    
    async for event in agent.run_async():
        if isinstance(event, TextEvent):
            # Report thinking
            if event.thinking:
                await report_chunk(message_id, event.text, chunk_index, is_thinking=True)
            else:
                await report_chunk(message_id, event.text, chunk_index, is_thinking=False)
            chunk_index += 1
        
        elif isinstance(event, StopEvent):
            # Mark message complete
            await report_chunk(message_id, "", chunk_index, is_final=True)
            message_id = str(uuid.uuid4())  # New message ID for next response
            chunk_index = 0
```

---

## 5. Event Storage Strategy

### Problem

Tool events are ephemeral by default. For session replay, debugging, and on-demand expansion, we need to persist them.

### Options

| Option | Pros | Cons | Recommended |
|--------|------|------|-------------|
| **A. Redis (TTL 24h)** | Fast, simple | No long-term history | ✅ MVP |
| **B. PostgreSQL** | Durable, queryable | Volume concerns | For audit logs |
| **C. S3/Blob Storage** | Cheap, unlimited | Slow retrieval | For session replay |

### Recommended: Hybrid Approach

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EVENT STORAGE TIERS                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  HOT STORAGE (Redis, 24h TTL):                                              │
│  ─────────────────────────────                                              │
│  • All tool events for active sessions                                      │
│  • Full diffs (for on-demand expansion)                                     │
│  • Message chunks (for reconnection)                                        │
│  Key pattern: sandbox:{id}:events:{timestamp}                              │
│                                                                             │
│  WARM STORAGE (PostgreSQL, 30 days):                                        │
│  ────────────────────────────────────                                       │
│  • Aggregated tool statistics per session                                   │
│  • File edit summaries (without full diffs)                                │
│  • Error events (for debugging)                                             │
│                                                                             │
│  COLD STORAGE (S3, unlimited):                                              │
│  ──────────────────────────────                                             │
│  • Full session replays (compressed JSON)                                   │
│  • Archived after sandbox terminates                                        │
│  • On-demand retrieval for audit                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Implementation

#### 5.1 Redis Event Buffer

```python
# backend/omoi_os/services/tool_event_store.py

class ToolEventStore:
    """Short-term storage for tool events."""
    
    def __init__(self, redis_client, ttl_seconds: int = 86400):  # 24h
        self.redis = redis_client
        self.ttl = ttl_seconds
    
    async def store_event(self, sandbox_id: str, event: dict):
        key = f"sandbox:{sandbox_id}:events"
        await self.redis.lpush(key, json.dumps(event))
        await self.redis.expire(key, self.ttl)
        
        # Keep max 10000 events per sandbox
        await self.redis.ltrim(key, 0, 9999)
    
    async def get_events(
        self, 
        sandbox_id: str, 
        start: int = 0, 
        count: int = 100
    ) -> list[dict]:
        key = f"sandbox:{sandbox_id}:events"
        events = await self.redis.lrange(key, start, start + count - 1)
        return [json.loads(e) for e in events]
    
    async def get_event_by_id(self, sandbox_id: str, event_id: str) -> Optional[dict]:
        """Retrieve specific event (for full diff fetch)."""
        # This requires indexing by event_id
        # Consider using Redis hash or sorted set for efficient lookup
        pass
```

---

## 6. SDK Integration Layer

### Problem

Claude Agent SDK uses PreToolUse/PostToolUse hooks for intervention and event reporting.

### Solution: Agent Event Adapter

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SDK ADAPTER LAYER                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                       ┌─────────────────────────┐                           │
│                       │   AgentEventAdapter     │                           │
│                       │   (Abstract Interface)   │                           │
│                       └───────────┬─────────────┘                           │
│                                   │                                         │
│               ┌───────────────────┼───────────────────┐                     │
│               │                   │                   │                     │
│               ▼                   ▼                   ▼                     │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐   │
│  │ ClaudeSDKAdapter    │ │ FutureSDKAdapter    │   │
│  │                     │ │                     │ │                     │   │
│  │ • PreToolUse hook   │ │ • Event callback    │ │ • ...               │   │
│  │ • PostToolUse hook  │ │ • Action intercept  │ │                     │   │
│  │ • Stream events     │ │ • Batch events      │ │                     │   │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘   │
│                                                                             │
│  All adapters emit UNIFIED events:                                          │
│  • on_tool_start(tool_id, tool_name, tool_args)                            │
│  • on_tool_complete(tool_id, duration_ms, result_summary)                  │
│  • on_file_changed(path, change_type, diff)                                │
│  • on_message_chunk(message_id, chunk, is_thinking)                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# backend/omoi_os/sandbox_worker/adapters/base.py

from abc import ABC, abstractmethod
from typing import Callable, Any

class AgentEventAdapter(ABC):
    """Unified interface for SDK event capture."""
    
    def __init__(self, event_reporter: Callable[[str, dict], None]):
        self.report = event_reporter
    
    @abstractmethod
    async def setup_hooks(self, agent: Any) -> None:
        """Configure SDK-specific hooks/callbacks."""
        pass
    
    async def on_tool_start(self, tool_id: str, tool_name: str, tool_args: dict):
        await self.report("TOOL_STARTED", {
            "tool_id": tool_id,
            "tool_name": tool_name,
            "tool_args": self._sanitize_args(tool_args),
        })
    
    async def on_tool_complete(
        self, 
        tool_id: str, 
        duration_ms: int,
        result_summary: str,
        success: bool = True
    ):
        await self.report("TOOL_COMPLETED", {
            "tool_id": tool_id,
            "duration_ms": duration_ms,
            "result_summary": result_summary,
            "success": success,
        })
    
    async def on_file_changed(self, path: str, change_type: str, diff_info: dict):
        await self.report("agent.file_edited", {
            "file_path": path,
            "change_type": change_type,
            **diff_info,
        })
    
    async def on_message_chunk(
        self, 
        message_id: str, 
        chunk: str, 
        chunk_index: int,
        is_thinking: bool = False,
        is_final: bool = False
    ):
        await self.report("AGENT_MESSAGE_CHUNK", {
            "message_id": message_id,
            "chunk": chunk,
            "chunk_index": chunk_index,
            "is_thinking": is_thinking,
            "is_final": is_final,
        })
    
    def _sanitize_args(self, args: dict) -> dict:
        """Remove sensitive/large values from tool args."""
        sanitized = {}
        for k, v in args.items():
            if isinstance(v, str) and len(v) > 1000:
                sanitized[k] = f"<{len(v)} chars>"
            else:
                sanitized[k] = v
        return sanitized
```

```python
# backend/omoi_os/sandbox_worker/adapters/claude.py

class ClaudeSDKAdapter(AgentEventAdapter):
    """Adapter for Claude Agent SDK."""
    
    async def setup_hooks(self, agent) -> None:
        """Register PreToolUse and PostToolUse hooks."""
        from claude_agent_sdk import HookMatcher, HookInput, HookContext, HookJSONOutput
        from pathlib import Path
        
        self.file_tracker = FileChangeTracker()
        self.tool_start_times: dict[str, float] = {}
        
        async def pre_tool_use(
            input_data: HookInput,
            tool_use_id: str | None,
            context: HookContext
        ) -> HookJSONOutput:
            tool_name = input_data.get("tool_name", "")
            tool_input = input_data.get("tool_input", {})
            tool_id = tool_use_id or str(uuid.uuid4())
            
            self.tool_start_times[tool_id] = time.time()
            
            # Cache file content for diff (Write and Edit tools)
            if tool_name in ["Write", "Edit"]:
                file_path = tool_input.get("file_path")
                if file_path:
                    file_path = Path(file_path)
                    if file_path.exists():
                        try:
                            content = file_path.read_text()
                            self.file_tracker.cache_file_before_edit(str(file_path), content)
                        except FileNotFoundError:
                            pass  # New file, nothing to cache
                        except Exception as e:
                            print(f"[FileTracker] Failed to cache {file_path}: {e}")
            
            await self.on_tool_start(tool_id, tool_name, tool_input)
            return {}
        
        async def post_tool_use(
            input_data: HookInput,
            tool_use_id: str | None,
            context: HookContext
        ) -> HookJSONOutput:
            tool_name = input_data.get("tool_name", "")
            tool_input = input_data.get("tool_input", {})
            tool_response = input_data.get("tool_response", "")
            tool_id = tool_use_id or "unknown"
            
            start_time = self.tool_start_times.pop(tool_id, time.time())
            duration_ms = int((time.time() - start_time) * 1000)
            
            result_summary = self._summarize_result(tool_name, tool_response)
            await self.on_tool_complete(tool_id, duration_ms, result_summary)
            
            # Generate diff for file edits
            if tool_name == "Write":
                file_path = tool_input.get("file_path")
                if file_path:
                    # Write tool: new content is in tool_input["content"]
                    new_content = tool_input.get("content", "")
                    if new_content:
                        diff_info = self.file_tracker.generate_diff(file_path, new_content)
                        await self.on_file_changed(file_path, diff_info.get("change_type", "modified"), diff_info)
            
            elif tool_name == "Edit":
                file_path = tool_input.get("file_path")
                if file_path:
                    # Edit tool: must read filesystem to get final content
                    file_path = Path(file_path)
                    if file_path.exists():
                        try:
                            new_content = file_path.read_text()
                            diff_info = self.file_tracker.generate_diff(str(file_path), new_content)
                            await self.on_file_changed(str(file_path), diff_info.get("change_type", "modified"), diff_info)
                        except Exception as e:
                            print(f"[FileTracker] Failed to read {file_path} after edit: {e}")
            
            return {}
        
        # Register hooks with ClaudeAgentOptions
        agent.options.hooks = {
            "PreToolUse": [
                HookMatcher(matcher="Write", hooks=[pre_tool_use]),
                HookMatcher(matcher="Edit", hooks=[pre_tool_use]),
            ],
            "PostToolUse": [
                HookMatcher(matcher="Write", hooks=[post_tool_use]),
                HookMatcher(matcher="Edit", hooks=[post_tool_use]),
            ],
        }
    
    def _summarize_result(self, tool_name: str, result: Any) -> str:
        if tool_name == "Read":
            result_str = str(result)
            return f"{result_str.count(chr(10)) + 1} lines"
        elif tool_name == "Write":
            return "File written"
        elif tool_name == "Edit":
            return "File edited"
        elif tool_name == "Bash":
            return f"Exit code: {getattr(result, 'exit_code', 'unknown')}"
        return "Completed"
```

---

## 7. Performance Considerations

### Estimated Event Volumes

| Scenario | Tool Calls/min | Events/min | WebSocket msgs/min |
|----------|----------------|------------|--------------------|
| Simple task | 5-10 | 15-30 | 15-30 |
| Complex task | 30-50 | 90-150 | 30-50 (batched) |
| Heavy coding | 50-100 | 150-300 | 50-100 (batched) |

### Mitigation Strategies

1. **Event Batching**: Tier 2 events batched in 500ms windows (reduces ~3x)
2. **Payload Compression**: Full diffs gzipped before transmission
3. **Client-Side Virtualization**: Frontend only renders visible events
4. **Rate Limiting**: Max 200 events/min per sandbox (existing security)
5. **Lazy Loading**: Full diffs fetched on-demand, not embedded

### Monitoring Metrics

Add to existing monitoring (see `07_existing_systems_integration.md`):

```python
# backend/omoi_os/services/metrics.py

tool_events_total = Counter("sandbox_tool_events_total", ["sandbox_id", "event_type"])
event_batch_size = Histogram("sandbox_event_batch_size", ["sandbox_id"])
websocket_message_size = Histogram("websocket_message_bytes", ["event_type"])
```

---

## 8. Implementation Phases

### Phase 1: Basic Tool Events (~1 week)

- [ ] Add TOOL_STARTED, TOOL_COMPLETED event types
- [ ] Implement PostToolUse hook in Claude adapter
- [ ] Create `/tool-events` endpoint
- [ ] Frontend: ToolCallCard component (collapsed by default)

### Phase 2: File Diff Capture (~1 week)

- [x] Implement FileChangeTracker class
- [x] Add PreToolUse hook for Write and Edit tools (cache file content)
- [x] Add PostToolUse hook for Write and Edit tools (generate diffs)
- [x] Handle both Write (full file) and Edit (partial) tools
- [x] Generate unified diff with proper line counting
- [x] Emit agent.file_edited events with diff data
- [ ] Frontend: FileChangeCard component with expandable diff viewer

### Phase 3: Message Streaming (~1 week)

- [ ] Create `/message-chunks` endpoint
- [ ] Integrate Claude SDK streaming
- [ ] Frontend: StreamingMessage component

### Phase 4: Polish & Performance (~1 week)

- [ ] Event batching infrastructure
- [ ] Redis event storage
- [x] Claude Agent SDK adapter
- [ ] Frontend virtualization
- [ ] Session replay capability

---

## 9. Related Documents

| Document | Relevance |
|----------|-----------|
| [01_architecture.md](./01_architecture.md) | Base architecture, WebSocket flow |
| [04_communication_patterns.md](./04_communication_patterns.md) | HTTP patterns, hook-based injection |
| [06_implementation_checklist.md](./06_implementation_checklist.md) | Implementation phases |
| [08_frontend_integration.md](./08_frontend_integration.md) | UI components, frontend spec |
| [07_existing_systems_integration.md](./07_existing_systems_integration.md) | Event bus integration |

---

## 10. Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              RICH ACTIVITY FEED: ARCHITECTURAL CHANGES SUMMARY               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  WORKER CHANGES:                                                            │
│  ├─ SDK adapter layer (ClaudeSDKAdapter)                                    │
│  ├─ ✅ PreToolUse hook: Cache file content before Write/Edit (IMPLEMENTED)  │
│  ├─ ✅ PostToolUse hook: Generate diffs after Write/Edit (IMPLEMENTED)      │
│  ├─ ✅ FileChangeTracker for diff capture and generation (IMPLEMENTED)       │
│  ├─ ✅ Handle Write (full file) and Edit (partial) tools (IMPLEMENTED)      │
│  └─ Streaming message chunking                                              │
│                                                                             │
│  API CHANGES:                                                               │
│  ├─ POST /api/v1/sandbox/task/{id}/tool-events                             │
│  ├─ POST /api/v1/sandbox/task/{id}/message-chunks                          │
│  └─ GET /api/v1/sandbox/{id}/file-diffs/{event_id}                         │
│                                                                             │
│  EVENT BUS CHANGES:                                                         │
│  ├─ ✅ agent.file_edited event type (IMPLEMENTED)                          │
│  ├─ New event types (agent.tool_*, agent.message_*)                         │
│  ├─ Event batcher for Tier 2 events                                        │
│  └─ Redis event storage (24h TTL)                                          │
│                                                                             │
│  FRONTEND CHANGES:                                                          │
│  ├─ useToolEvents() hook                                                   │
│  ├─ ToolCallCard, FileChangeCard, StreamingMessage components              │
│  └─ ActivityFeed container with virtualization                              │
│                                                                             │
│  EFFORT: ~4 weeks post-MVP                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Key Implementation Notes for Claude Agent SDK

### Tool Names
- ✅ Use `Write` (full file replacement) and `Edit` (partial replacement)
- ❌ Do NOT use `str_replace_editor` (that's OpenHands SDK)

### Event Naming Convention
- ✅ Use `agent.*` prefix: `agent.file_edited`, `agent.tool_use`, etc.
- ❌ Do NOT use uppercase: `FILE_EDITED`, `TOOL_STARTED`

### Hook Structure
- ✅ Use `HookMatcher(matcher="Write", hooks=[...])` for specific tools
- ✅ Use `HookMatcher(matcher=None, hooks=[...])` for all tools
- ✅ Hook functions must match signature: `(HookInput, tool_use_id, HookContext) -> HookJSONOutput`

### File Content Retrieval
- **Write tool**: New content is in `tool_input["content"]` (no filesystem read needed)
- **Edit tool**: Must read filesystem after edit: `Path(file_path).read_text()`

### Diff Generation
- Use Python `difflib.unified_diff()` for standard format
- Handle new file creation (no old content)
- Truncate preview to 5KB, full diff to 50KB max
- Include `full_diff_available` flag for on-demand fetching

### Event Payload Structure
```python
{
    "event_type": "agent.file_edited",
    "event_data": {
        "turn": 3,
        "tool_use_id": "tool_abc123",
        "file_path": "/workspace/src/file.py",
        "change_type": "modified",  # or "created"
        "lines_added": 15,
        "lines_removed": 8,
        "diff_preview": "...",  # First 100 lines, max 5KB
        "full_diff": "...",  # Only if < 50KB
        "full_diff_available": true,
        "full_diff_size": 12345,
    }
}
```

---

**Status**: Phase 2 (File Diff Capture) **IMPLEMENTED** ✅. Remaining phases are future enhancements.

**Implementation Status**:
- ✅ **Phase 2 Complete**: File diff tracking implemented in `claude_sandbox_worker.py`
  - FileChangeTracker class with caching and diff generation
  - PreToolUse hook for file content caching
  - PostToolUse hook for diff generation and event emission
  - Supports both Write (full file) and Edit (partial) tools
  - Unified diff format with proper line counting
  - `agent.file_edited` events with full metadata
- ⏳ **Phase 1**: Tool-level events (pending)
- ⏳ **Phase 3**: Message streaming (pending)
- ⏳ **Phase 4**: Polish & Performance (pending)

**Last Updated**: 2025-12-17 - Phase 2 implementation completed. File diff tracking now active in production worker.
