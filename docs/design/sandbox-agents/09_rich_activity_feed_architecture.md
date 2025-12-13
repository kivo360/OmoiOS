# Rich Activity Feed Architecture

**Created**: 2025-12-12  
**Status**: Future Enhancement (Post-MVP)  
**Priority**: Nice-to-have  
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

| Gap | Impact | Section |
|-----|--------|---------|
| **Granular Tool Events** | Can't show individual tool calls | [1. Event Granularity](#1-event-granularity-enhancement) |
| **High-Frequency Event Handling** | Performance issues at scale | [2. Event Throttling](#2-event-throttling-strategy) |
| **File Diff Generation** | Can't show inline code changes | [3. Diff Capture](#3-file-diff-capture) |
| **Message Streaming** | Can't show typewriter effect | [4. Message Streaming](#4-message-streaming-architecture) |
| **Tool Event Persistence** | Can't replay/audit tool history | [5. Event Storage](#5-event-storage-strategy) |
| **SDK Abstraction** | Different patterns for Claude/OpenHands | [6. SDK Integration](#6-sdk-integration-layer) |

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
│  • TOOL_FAILED - User needs to know immediately                            │
│  • FILE_EDITED - High-value visibility                                     │
│  • AGENT_MESSAGE_CHUNK - Streaming text                                    │
│  • Task status changes                                                     │
│                                                                             │
│  TIER 2: Informational Events (Batched, 500ms window)                       │
│  ─────────────────────────────────────────────────────                      │
│  • TOOL_STARTED - Can be batched                                           │
│  • TOOL_COMPLETED (success) - Can be batched                               │
│  • FILE_CREATED - Less urgent                                              │
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

### Solution: Tool Result Interception

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FILE DIFF CAPTURE FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Agent calls str_replace_editor tool                                     │
│                                                                             │
│  2. PostToolUse hook fires AFTER tool execution                             │
│     └─ Captures: file_path, old_content (cached), new_content              │
│                                                                             │
│  3. Diff generator creates unified diff                                     │
│     └─ Uses Python difflib or similar                                      │
│     └─ Truncates to first 50 lines for preview                             │
│                                                                             │
│  4. FILE_EDITED event emitted with:                                         │
│     └─ file_path, lines_added, lines_removed                               │
│     └─ diff_preview (truncated, ~2KB max)                                  │
│     └─ full_diff_url (for on-demand fetch)                                 │
│                                                                             │
│  5. Frontend shows collapsed diff card                                      │
│     └─ On expand: fetches full diff if needed                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Implementation

#### 3.1 Worker Script Enhancement

```python
# In sandbox worker - PostToolUse hook

import difflib
from typing import Optional

class FileChangeTracker:
    """Tracks file changes for diff generation."""
    
    def __init__(self):
        self.file_cache: dict[str, str] = {}  # path → content before edit
    
    def cache_file_before_edit(self, path: str, content: str):
        """Called by PreToolUse hook when str_replace_editor is about to run."""
        self.file_cache[path] = content
    
    def generate_diff(self, path: str, new_content: str) -> dict:
        """Generate diff after edit completes."""
        old_content = self.file_cache.pop(path, "")
        
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        ))
        
        lines_added = sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))
        lines_removed = sum(1 for l in diff if l.startswith('-') and not l.startswith('---'))
        
        # Truncate diff preview
        diff_preview = ''.join(diff[:100])  # First 100 lines
        if len(diff) > 100:
            diff_preview += f"\n... ({len(diff) - 100} more lines)"
        
        return {
            "file_path": path,
            "change_type": "edit",
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "diff_preview": diff_preview[:5000],  # Max 5KB
            "full_diff_available": len(diff) > 100,
        }

# Integration with PostToolUse
async def post_tool_use_handler(tool_name: str, tool_args: dict, result: Any):
    if tool_name == "str_replace_editor":
        file_path = tool_args.get("path")
        # Read new content
        new_content = read_file(file_path)
        diff_info = file_tracker.generate_diff(file_path, new_content)
        
        await report_event("FILE_EDITED", diff_info)
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
│  OpenHands SDK (event-based):                                               │
│  ───────────────────────────────                                            │
│  # Messages arrive complete, no native streaming                            │
│  # Option 1: Fake streaming (split complete message into chunks)            │
│  # Option 2: Accept complete messages for OpenHands                         │
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

Claude SDK and OpenHands SDK have different hook/callback mechanisms. We need a unified abstraction.

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
│  │ ClaudeSDKAdapter    │ │ OpenHandsAdapter    │ │ FutureSDKAdapter    │   │
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
        await self.report("FILE_EDITED", {
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
        from claude_sdk import HookMatcher
        
        self.file_tracker = FileChangeTracker()
        self.tool_start_times: dict[str, float] = {}
        
        async def pre_tool_use(tool_name: str, tool_args: dict):
            tool_id = str(uuid.uuid4())
            tool_args["_tool_id"] = tool_id
            self.tool_start_times[tool_id] = time.time()
            
            # Cache file content for diff
            if tool_name == "str_replace_editor" and "path" in tool_args:
                try:
                    content = read_file(tool_args["path"])
                    self.file_tracker.cache_file_before_edit(tool_args["path"], content)
                except FileNotFoundError:
                    pass  # New file
            
            await self.on_tool_start(tool_id, tool_name, tool_args)
        
        async def post_tool_use(tool_name: str, tool_args: dict, result: Any):
            tool_id = tool_args.get("_tool_id", "unknown")
            start_time = self.tool_start_times.pop(tool_id, time.time())
            duration_ms = int((time.time() - start_time) * 1000)
            
            result_summary = self._summarize_result(tool_name, result)
            await self.on_tool_complete(tool_id, duration_ms, result_summary)
            
            # Generate diff for file edits
            if tool_name == "str_replace_editor" and "path" in tool_args:
                new_content = read_file(tool_args["path"])
                diff_info = self.file_tracker.generate_diff(tool_args["path"], new_content)
                await self.on_file_changed(tool_args["path"], "edit", diff_info)
        
        # Register hooks with agent
        agent.options.hooks = {
            "PreToolUse": [HookMatcher(matcher="*", hooks=[pre_tool_use])],
            "PostToolUse": [HookMatcher(matcher="*", hooks=[post_tool_use])],
        }
    
    def _summarize_result(self, tool_name: str, result: Any) -> str:
        if tool_name == "read_file":
            return f"{result.count(chr(10)) + 1} lines"
        elif tool_name == "str_replace_editor":
            return "File updated"
        elif tool_name == "bash":
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

- [ ] Implement FileChangeTracker
- [ ] Add PreToolUse caching for str_replace_editor
- [ ] Generate diff previews
- [ ] Frontend: FileChangeCard component with expandable diff

### Phase 3: Message Streaming (~1 week)

- [ ] Create `/message-chunks` endpoint
- [ ] Integrate Claude SDK streaming
- [ ] Frontend: StreamingMessage component

### Phase 4: Polish & Performance (~1 week)

- [ ] Event batching infrastructure
- [ ] Redis event storage
- [ ] OpenHands adapter
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
│  ├─ SDK adapter layer (ClaudeSDKAdapter, OpenHandsAdapter)                 │
│  ├─ PreToolUse + PostToolUse hook registration                             │
│  ├─ FileChangeTracker for diff capture                                     │
│  └─ Streaming message chunking                                              │
│                                                                             │
│  API CHANGES:                                                               │
│  ├─ POST /api/v1/sandbox/task/{id}/tool-events                             │
│  ├─ POST /api/v1/sandbox/task/{id}/message-chunks                          │
│  └─ GET /api/v1/sandbox/{id}/file-diffs/{event_id}                         │
│                                                                             │
│  EVENT BUS CHANGES:                                                         │
│  ├─ New event types (TOOL_*, FILE_*, AGENT_MESSAGE_*)                      │
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

**Status**: This document is a **future enhancement spec**. Implementation should begin after MVP is complete and validated.
