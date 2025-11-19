# OpenHands Conversation Control Prototype

This directory contains minimal prototypes for testing OpenHands conversation control concepts.

## Files

- **`test_conversation_control.py`** - Comprehensive prototype with multiple test scenarios
- **`test_conversation_control_minimal.py`** - Minimal single-file test (recommended for quick analysis)

## Quick Start

### Prerequisites

```bash
# Install OpenHands SDK
pip install openhands

# Set API key
export OPENAI_API_KEY="your-key-here"
# OR
export ANTHROPIC_API_KEY="your-key-here"
```

### Run Minimal Test

```bash
python test_conversation_control_minimal.py
```

### Run Full Test Suite

```bash
python test_conversation_control.py
```

## What These Prototypes Demonstrate

### 1. **Conversation Creation with Persistence**

```python
conversation = Conversation(
    agent=agent,
    workspace="./workspace",
    persistence_dir="./persistence",
    conversation_id="my-conversation-id"
)
```

**Key Points:**
- Conversations can be created with explicit IDs
- Persistence directory allows resuming conversations
- State is immediately accessible via `conversation.state`

### 2. **State Inspection**

```python
state = conversation.state
print(f"Agent Status: {state.agent_status}")
print(f"Execution Status: {state.execution_status}")
print(f"Event Count: {len(state.events)}")
```

**Key Points:**
- State is always accessible, even during execution
- `agent_status` can be `IDLE` or `RUNNING`
- Events are tracked and accessible

### 3. **Intervention During Execution**

```python
# Send message even while agent is running
conversation.send_message("[INTERVENTION] Your message here")

# If agent is idle, trigger processing
if conversation.state.agent_status == AgentExecutionStatus.IDLE:
    conversation.run()  # Can run in background thread
```

**Key Points:**
- Messages can be sent to running conversations
- OpenHands queues messages automatically
- If agent is idle, you need to call `run()` to process

### 4. **Conversation Resumption**

```python
# Close conversation
conversation.close()

# Later, resume from persistence
resumed = Conversation(
    conversation_id="my-conversation-id",
    persistence_dir="./persistence",
    agent=agent,
    workspace="./workspace"
)
```

**Key Points:**
- Conversations persist to disk automatically
- Can resume with same ID and persistence_dir
- Previous events and state are restored

## Key Insights for OmoiOS Integration

### 1. **State Machine**

OpenHands conversations have two main states:
- **IDLE**: Agent is waiting for input
- **RUNNING**: Agent is actively processing

You can check state at any time:
```python
from openhands.sdk.conversation.state import AgentExecutionStatus

if conversation.state.agent_status == AgentExecutionStatus.IDLE:
    # Safe to send intervention
    conversation.send_message("...")
    conversation.run()  # Start processing
```

### 2. **Persistence Strategy**

For OmoiOS:
- Store `conversation_id` in Task model
- Store `persistence_dir` in Task model
- Use task_id as conversation_id for easy mapping
- Persistence directory: `{workspace_dir}/conversation/{task_id}`

### 3. **Intervention Pattern**

```python
# Guardian intervention flow:
# 1. Get task's conversation_id and persistence_dir from DB
# 2. Resume conversation
conversation = Conversation(
    conversation_id=task.conversation_id,
    persistence_dir=task.persistence_dir,
    agent=agent,
    workspace=task.workspace_dir
)

# 3. Send intervention
conversation.send_message(f"[GUARDIAN] {intervention_message}")

# 4. Trigger if idle
if conversation.state.agent_status == AgentExecutionStatus.IDLE:
    conversation.run()  # Background thread recommended
```

### 4. **Threading Considerations**

- `conversation.run()` is blocking
- Use background threads for non-blocking execution
- State is thread-safe (can be read from any thread)
- Multiple `send_message()` calls are safe

### 5. **Error Handling**

- Always close conversations: `conversation.close()`
- Check state before operations
- Handle exceptions during `run()` gracefully
- Persistence directory must exist before creating conversation

## Testing Scenarios

### Scenario 1: Basic Execution
- Create conversation
- Send task
- Run to completion
- Inspect results

### Scenario 2: Intervention During Execution
- Start long-running task
- Monitor state
- Send intervention mid-execution
- Verify intervention is processed

### Scenario 3: Resumption
- Create and run conversation
- Close conversation
- Resume from persistence
- Send follow-up message
- Verify continuity

### Scenario 4: State Monitoring
- Create conversation
- Monitor state changes
- Track event count
- Detect completion

## Expected Output

```
1️⃣ Creating conversation...
   ID: test-minimal
   Status: AgentExecutionStatus.IDLE

2️⃣ Sending task...
3️⃣ Running conversation in background...
4️⃣ Monitoring state...
   [1s] Status: AgentExecutionStatus.RUNNING, Events: 2
   [2s] Status: AgentExecutionStatus.RUNNING, Events: 5
   [3s] Status: AgentExecutionStatus.IDLE, Events: 8

5️⃣ Sending intervention...
   → Agent idle, triggering processing...

6️⃣ Monitoring after intervention...
   [1s] Events: 9
   [2s] Events: 12

7️⃣ Final state:
   Status: AgentExecutionStatus.IDLE
   Events: 12
   Execution: ExecutionStatus.COMPLETED

8️⃣ Testing resumption...
   Resumed ID: test-minimal
   Previous events: 12

✅ Test complete!
```

## Integration Notes

### For OmoiOS Agent Executor:

1. **prepare_conversation()** - Creates conversation, returns metadata
2. **execute_task()** - Uses prepared conversation or creates new one
3. **Always close** - Use try/finally to ensure cleanup

### For Guardian Intervention:

1. **Resume conversation** - Use stored conversation_id and persistence_dir
2. **Check state** - Verify agent is responsive
3. **Send message** - Format with [GUARDIAN] prefix
4. **Trigger if needed** - Call run() if agent is idle

### For State Monitoring:

1. **Poll state** - Check agent_status periodically
2. **Track events** - Monitor event count for progress
3. **Detect completion** - Check execution_status

## Limitations & Considerations

1. **Thread Safety**: State reads are safe, but be careful with concurrent writes
2. **Persistence**: Directory must exist and be writable
3. **Agent Matching**: Resumed conversations need same agent configuration
4. **Resource Cleanup**: Always close conversations to free resources
5. **Error Recovery**: Handle exceptions during run() gracefully

## Next Steps

After testing these prototypes:

1. Integrate into `AgentExecutor` service
2. Add conversation metadata to Task model
3. Implement Guardian intervention service
4. Add state monitoring to Intelligent Guardian
5. Test with real tasks and interventions
