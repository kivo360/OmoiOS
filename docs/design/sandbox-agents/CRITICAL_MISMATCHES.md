# Critical Mismatches: Design Docs vs Claude Agent SDK Reality

**Created**: 2025-01-XX  
**Status**: ⚠️ **CRITICAL** - Design assumptions don't match actual SDK behavior  
**Purpose**: Document discrepancies that prevent working prototype matching Claude Code web

---

## Executive Summary

After comparing the design documentation with the actual Claude Agent SDK implementation, several **critical mismatches** have been identified that explain why prototypes don't work like Claude Code web. These need to be fixed before implementation.

---

## 🚨 Critical Issue #1: Message Injection Misconception

### What the Design Says

The design documents (especially `04_communication_patterns.md` and `01_architecture.md`) claim that **PreToolUse hooks can inject messages** into the conversation via `systemMessage`:

```python
# From design docs - INCORRECT ASSUMPTION
async def check_pending_interventions(input_data, tool_use_id, context):
    intervention = await fetch_next_intervention()
    if intervention:
        return {
            "reason": intervention["message"],
            "systemMessage": f"[{intervention['source'].upper()}] {intervention['message']}",
        }
```

**Design Claim**: "Hook returns `systemMessage` → Claude receives context and responds"

### What the SDK Actually Does

**Reality**: `systemMessage` in hook output is **NOT a new user message**. It's a **notification/warning** that appears in the UI but doesn't trigger Claude to respond.

**Actual SDK Behavior**:
- Hooks can **modify tool execution** (allow/deny, modify inputs)
- Hooks can **add context** via `systemMessage` (but this is just a notification)
- Hooks **CANNOT inject new user messages** that Claude responds to

### How Claude Code Web Actually Works

In Claude Code web, when you type a message:
1. Frontend calls `client.query(new_message)` 
2. This creates a **new user message** in the conversation
3. Claude processes it and responds

**For message injection to work like Claude Code web, you MUST:**
```python
# CORRECT PATTERN - Multi-turn with message injection
async with ClaudeSDKClient(options=options) as client:
    # Initial task
    await client.query(task_description)
    
    # Stream responses
    async for msg in client.receive_response():
        # Process messages...
        pass
    
    # When intervention arrives, inject as NEW USER MESSAGE
    if intervention_received:
        await client.query(intervention_message)  # ← This is how Claude Code does it
        async for msg in client.receive_response():
            # Process follow-up response...
            pass
```

### Impact

- ❌ Current worker script pattern won't support real-time message injection
- ❌ Hooks can't inject messages mid-conversation
- ❌ Design assumes capabilities that don't exist

### Fix Required

1. **Update worker script** to use `receive_messages()` (indefinite) instead of `receive_response()` (stops at ResultMessage)
2. **Add message polling loop** that calls `client.query()` when interventions arrive
3. **Remove hook-based message injection** from design (or clarify it's only for context, not new messages)

---

## 🚨 Critical Issue #2: Single Query Pattern vs Multi-Turn

### What the Design Shows

Current worker script pattern:
```python
async with ClaudeSDKClient(options=options) as client:
    await client.query(task_description)  # ← Called ONCE
    async for msg in client.receive_response():  # ← Streams until ResultMessage
        # Process messages
    # Done - no way to inject follow-up messages
```

### What Claude Code Web Does

Claude Code web maintains an **active conversation loop**:
- User can send messages at any time
- Each message triggers `client.query()`
- Responses stream continuously
- Conversation state is maintained

### Fix Required

**Pattern should be:**
```python
async with ClaudeSDKClient(options=options) as client:
    # Initial query
    await client.query(task_description)
    
    # Use receive_messages() for indefinite streaming
    message_queue = asyncio.Queue()
    
    async def message_stream():
        async for msg in client.receive_messages():  # ← Indefinite, not receive_response()
            await message_queue.put(msg)
    
    async def intervention_handler():
        while True:
            # Poll for interventions
            interventions = await poll_interventions()
            if interventions:
                for intervention in interventions:
                    await client.query(intervention["message"])  # ← Inject as new user message
    
    # Run both concurrently
    await asyncio.gather(
        message_stream(),
        intervention_handler(),
    )
```

---

## 🚨 Critical Issue #3: Hook Output Misunderstanding

### What the Design Says

Design docs show hooks returning `systemMessage` and expecting Claude to respond:

```python
return {
    "systemMessage": injected_context,  # ← Design assumes Claude responds to this
    "reason": "Injected guidance from message queue",
}
```

### What Hooks Actually Do

From SDK docs, `systemMessage` in hook output:
- Is a **notification/warning** shown to the user
- Does **NOT** create a new user message
- Does **NOT** trigger Claude to respond
- Is just **contextual information** displayed in the UI

**Hook output fields:**
- `continue_`: Control execution flow
- `stopReason`: Why execution stopped
- `systemMessage`: **UI notification only** (not a message Claude responds to)
- `reason`: Feedback for Claude (but doesn't create new message)
- `hookSpecificOutput`: Tool-specific controls

### Fix Required

**Clarify in design docs:**
- Hooks can add **context** but not inject **new user messages**
- Real message injection requires `client.query(new_message)`
- `systemMessage` is for notifications, not conversation messages

---

## 🚨 Critical Issue #4: Event Streaming Pattern

### What the Design Shows

Design shows events being reported via HTTP callbacks, but doesn't clearly show:
- How to stream events in real-time
- How to handle `StreamEvent` messages from SDK
- How to map SDK message types to our event types

### What the SDK Provides

SDK streams:
- `AssistantMessage` - Claude's responses
- `TextBlock`, `ThinkingBlock`, `ToolUseBlock`, `ToolResultBlock` - Content blocks
- `StreamEvent` - Partial updates during streaming
- `ResultMessage` - Final summary

### Fix Required

**Map SDK messages to our event types:**
```python
async for msg in client.receive_messages():
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, ThinkingBlock):
                await report_event("agent.thinking", {"content": block.text})
            elif isinstance(block, ToolUseBlock):
                await report_event("agent.tool_use", {
                    "tool": block.name,
                    "input": block.input
                })
            elif isinstance(block, ToolResultBlock):
                await report_event("agent.tool_result", {
                    "tool": block.tool_use_id,
                    "result": block.content
                })
            elif isinstance(block, TextBlock):
                await report_event("agent.message", {"content": block.text})
```

---

## 🚨 Critical Issue #5: Session Management

### What the Design Assumes

Design assumes:
- Single query per task
- Session ends when task completes
- No need for session resumption

### What Claude Code Web Does

- Maintains conversation history
- Supports session resumption
- Allows conversation forking
- Tracks session state

### Fix Required

**Add session management:**
```python
# Store session_id for resumption
session_id = None

async with ClaudeSDKClient(options=options) as client:
    # If resuming, use existing session
    if session_id:
        # Resume conversation (SDK supports this)
        pass
    
    # Track session_id from ResultMessage
    async for msg in client.receive_messages():
        if isinstance(msg, ResultMessage):
            session_id = msg.session_id
            # Store for later resumption
```

---

## Files That Need Immediate Attention

### High Priority (Blocking Prototype)

1. **`01_architecture.md`**
   - Fix message injection pattern (remove hook-based injection claim)
   - Update worker script pattern to multi-turn
   - Clarify hook limitations

2. **`04_communication_patterns.md`**
   - Remove hook-based message injection section
   - Add correct multi-turn pattern with `client.query()`
   - Clarify `systemMessage` is notification, not message

3. **`backend/omoi_os/services/daytona_spawner.py`**
   - Update `_get_claude_worker_script()` to use multi-turn pattern
   - Change from `receive_response()` to `receive_messages()`
   - Add intervention polling that calls `client.query()`

### Medium Priority (Clarification)

4. **`06_implementation_checklist.md`**
   - Update tests to reflect multi-turn pattern
   - Fix message injection test expectations

5. **`10_development_workflow.md`**
   - Update examples to show correct patterns

---

## Recommended Fix Order

1. **Fix worker script** (`daytona_spawner.py`) - This is the actual implementation
2. **Update architecture doc** (`01_architecture.md`) - Core design document
3. **Fix communication patterns** (`04_communication_patterns.md`) - Message injection docs
4. **Update other docs** - For consistency

---

## Testing Strategy

After fixes, test that:
1. ✅ Worker script supports multi-turn conversations
2. ✅ Interventions can be injected via `client.query()`
3. ✅ Events stream correctly from SDK messages
4. ✅ Session state is maintained
5. ✅ Behavior matches Claude Code web

---

## References

- **SDK Docs**: `docs/libraries/claude-agent-sdk-python-clean.md`
  - Section: "ClaudeSDKClient" (lines 412-535)
  - Section: "Lifecycle Hooks" (lines 1130-1296)
  - Section: "Interactive Streaming Patterns" (line 111)

- **Current Worker**: `backend/omoi_os/services/daytona_spawner.py`
  - Method: `_get_claude_worker_script()` (line 946)

