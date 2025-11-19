# Test 1: Basic Conversation Creation and Execution - Detailed Explanation

## Overview

Test 1 demonstrates the **fundamental conversation lifecycle** - from creation to execution to state inspection. This is the foundation for all conversation control operations.

## Step-by-Step Breakdown

### Step 1: Setup Controller

```python
controller = ConversationController()
```

**What happens:**
- Creates workspace directory (`./test_workspace`)
- Initializes LLM with API key
- Creates OpenHands agent with default tools
- Sets up persistence directory structure

**Key Point:** The controller encapsulates all the setup needed to work with OpenHands conversations.

---

### Step 2: Create Conversation

```python
conversation = controller.create_conversation(conversation_id="test-conv-1")
```

**What happens internally:**

```python
# Inside create_conversation():
persistence_dir = os.path.join(self.workspace_dir, "conversation")
os.makedirs(persistence_dir, exist_ok=True)

conversation = Conversation(
    agent=self.agent,
    workspace=self.workspace_dir,
    persistence_dir=persistence_dir,
    conversation_id=conversation_id,  # "test-conv-1"
)
```

**Key Points:**
- **conversation_id**: Explicit ID allows resuming later
- **persistence_dir**: Where conversation state is saved to disk
- **workspace**: Directory for agent's file operations
- **agent**: The OpenHands agent instance (with LLM and tools)

**State immediately after creation:**
```
ID: test-conv-1
Agent Status: IDLE
Execution Status: (initial state)
Events: 0
```

---

### Step 3: Inspect Initial State

```python
controller.print_state(conversation, "Initial State")
```

**What we see:**
- Conversation has an ID immediately
- Agent status is `IDLE` (waiting for input)
- No events yet (no messages sent)
- Persistence directory is ready

**Why this matters:**
- State is **always accessible** - you can check it at any time
- `IDLE` means the agent is ready to receive messages
- The conversation exists in memory AND on disk (persistence)

---

### Step 4: Send Task Message

```python
conversation.send_message("Write a simple hello world Python script")
```

**What happens:**
1. Message is added to conversation's message queue
2. An event is created (MessageEvent)
3. Agent status may still be `IDLE` (message queued, not processed yet)
4. Event count increases

**State after sending:**
```
Agent Status: IDLE (or RUNNING if auto-started)
Events: 1+ (message event added)
```

**Key Point:** `send_message()` is **non-blocking** - it queues the message but doesn't execute it.

---

### Step 5: Execute Conversation

```python
conversation.run()
```

**What happens:**
1. Agent starts processing the queued message
2. Agent status changes to `RUNNING`
3. Agent uses tools (file operations, code execution, etc.)
4. Multiple events are generated:
   - ToolCallEvent (when agent calls a tool)
   - ToolResultEvent (tool results)
   - AgentMessageEvent (agent responses)
5. Agent status returns to `IDLE` when done
6. Execution status becomes `COMPLETED`

**State during execution:**
```
Agent Status: RUNNING
Events: Increasing (2, 5, 8, 12...)
```

**State after execution:**
```
Agent Status: IDLE
Execution Status: COMPLETED
Events: 12+ (all events from execution)
```

**Key Point:** `run()` is **blocking** - it waits until the agent finishes processing.

---

### Step 6: Inspect Final State

```python
controller.print_state(conversation, "Final State")
```

**What we see:**
- Agent is back to `IDLE` (execution complete)
- Execution status shows completion
- Multiple events were generated
- Cost metrics are available

**Event types typically seen:**
- `MessageEvent` - User messages
- `ToolCallEvent` - Agent calling tools
- `ToolResultEvent` - Tool execution results
- `AgentMessageEvent` - Agent responses
- `ExecutionStatusEvent` - Status changes

---

### Step 7: Save Metadata

```python
metadata = {
    "conversation_id": conversation.state.id,
    "persistence_dir": persistence_dir,
}
```

**Why this matters:**
- These two pieces of information allow **resuming** the conversation later
- Can be stored in database (Task model)
- Enables Guardian interventions

**For OmoiOS:**
```python
# In Task model:
task.conversation_id = conversation.state.id
task.persistence_dir = persistence_dir
```

---

### Step 8: Cleanup

```python
conversation.close()
```

**What happens:**
- Conversation resources are freed
- Final state is written to persistence directory
- Conversation can no longer be used (but can be resumed)

**Key Point:** Always close conversations to free resources.

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│ 1. Create Conversation                                  │
│    • conversation_id = "test-conv-1"                    │
│    • persistence_dir = "./workspace/conversation"        │
│    • State: IDLE, Events: 0                             │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Send Message                                         │
│    • "Write a simple hello world Python script"         │
│    • State: IDLE, Events: 1                             │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Run Conversation                                     │
│    • conversation.run()                                 │
│    • State: RUNNING → IDLE                              │
│    • Events: 1 → 12+                                    │
│    • Agent executes task                                │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Inspect Results                                      │
│    • State: IDLE, COMPLETED                             │
│    • Events: 12+                                        │
│    • Cost: $0.00XX                                      │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Save Metadata                                        │
│    • conversation_id                                    │
│    • persistence_dir                                    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 6. Close Conversation                                   │
│    • conversation.close()                               │
│    • State persisted to disk                            │
└─────────────────────────────────────────────────────────┘
```

## Key Concepts Demonstrated

### 1. **State Access**
```python
state = conversation.state
print(state.agent_status)      # IDLE or RUNNING
print(state.execution_status)   # Status of execution
print(len(state.events))        # Number of events
```

**Always available** - can check state at any time, even during execution.

### 2. **Persistence**
```python
conversation = Conversation(
    conversation_id="test-conv-1",  # Explicit ID
    persistence_dir="./persistence", # Where to save
    ...
)
```

**Enables resumption** - conversation state is saved to disk automatically.

### 3. **Lifecycle**
```
Create → Send Message → Run → Inspect → Close
```

**Clear lifecycle** - each step has a specific purpose.

### 4. **Non-blocking vs Blocking**

- **`send_message()`** - Non-blocking, queues message
- **`run()`** - Blocking, waits for completion
- **`state` access** - Non-blocking, always available

## Real-World Usage Pattern

```python
# 1. Prepare conversation (before execution)
metadata = agent_executor.prepare_conversation(task_id="task-123")
# Returns: {"conversation_id": "...", "persistence_dir": "..."}

# 2. Store in database
task.conversation_id = metadata["conversation_id"]
task.persistence_dir = metadata["persistence_dir"]
db.session.commit()

# 3. Execute task
result = agent_executor.execute_task(
    task_description="...",
    conversation_metadata=metadata
)

# 4. Results include conversation info
print(result["conversation_id"])
print(result["status"])  # COMPLETED, FAILED, etc.
```

## What This Enables

1. **Resumption** - Can resume conversations later using ID + persistence_dir
2. **Intervention** - Can send messages to conversations (Test 2)
3. **Monitoring** - Can check state during execution
4. **Debugging** - Can inspect events and state at any point

## Next Steps

After understanding Test 1:
- **Test 2**: See how to send interventions during execution
- **Test 3**: See how to resume conversations
- **Test 4**: See how to inspect state in detail
