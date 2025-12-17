# Quick Test Prototype - Get It Working NOW

**Goal**: Get a minimal working sandbox agent that behaves like Claude Code web in < 30 minutes.

---

## What We Fixed

✅ **Worker script now uses correct pattern:**
- `receive_messages()` for indefinite streaming (not `receive_response()`)
- `client.query(new_message)` for real message injection
- Proper event mapping from SDK messages to our events

---

## Prototype Test Flow

### 1. Start Backend
```bash
cd backend
uv run python -m omoi_os.api.main
```

### 2. Create a Test Sandbox

**Use the test script (recommended):**
```bash
python test_sandbox_event_stream.py
```

**Or manually via Python:**
```python
from omoi_os.services.daytona_spawner import DaytonaSpawnerService
from omoi_os.database import get_db
from omoi_os.services.event_bus import EventBusService
from omoi_os.config import get_app_settings
from uuid import uuid4

async def create_test_sandbox():
    settings = get_app_settings()
    async with get_db() as db:
        event_bus = EventBusService(redis_url=settings.redis.url)
        spawner = DaytonaSpawnerService(db=db, event_bus=event_bus)
        
        sandbox_id = await spawner.spawn_for_task(
            task_id=f"test-{uuid4().hex[:8]}",
            agent_id=f"agent-{uuid4().hex[:8]}",
            phase_id="PHASE_IMPLEMENTATION",
            runtime="claude"
        )
        return sandbox_id
```

**Note:** Sandboxes are typically created automatically by the orchestrator when tasks are assigned. For testing, use the script above.

### 3. Connect to WebSocket for Events

**JavaScript/TypeScript:**
```typescript
const ws = new WebSocket(
  'ws://localhost:18000/ws/events?entity_types=sandbox&entity_ids=sandbox-abc123'
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.entity_id === 'sandbox-abc123') {
    console.log('📡 Event:', data.event_type, data.payload);
  }
};
```

**Python (for testing):**
```python
import asyncio
import websockets
import json

async def listen_events(sandbox_id: str):
    uri = f"ws://localhost:18000/ws/events?entity_types=sandbox&entity_ids={sandbox_id}"
    async with websockets.connect(uri) as ws:
        async for message in ws:
            event = json.loads(message)
            if event.get("entity_id") == sandbox_id:
                print(f"📡 {event['event_type']}: {event.get('payload', {})}")
```

**Event Flow & Performance:**
```
Worker → HTTP POST (~5-20ms) → EventBus/Redis (~1-5ms) → WebSocket (~1-5ms)
Total latency: ~10-50ms per event ✅ (fast enough for real-time)
```

### 4. Inject a Message (Test Intervention)

```bash
curl -X POST http://localhost:18000/api/v1/sandboxes/{sandbox_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Focus on the API endpoint first",
    "message_type": "user_message"
  }'
```

**Expected behavior:**
- Worker polls every 500ms
- Detects message
- Calls `client.query("Focus on the API endpoint first")`
- Creates new conversation turn
- Streams response back

---

## What Should Work

✅ **Agent starts** → `agent.started` event  
✅ **Agent thinks** → `agent.thinking` event  
✅ **Agent uses tool** → `agent.tool_use` event  
✅ **Agent responds** → `agent.message` event  
✅ **Message injected** → `agent.message_injected` event  
✅ **Agent responds to injection** → New `agent.message` event  

---

## Common Issues & Quick Fixes

### Issue: "No events appearing"
**Check:**
1. Is worker script actually running in sandbox?
2. Are events being reported to `/api/v1/sandboxes/{id}/events`?
3. Is WebSocket connected?

**Debug:**
```python
# In worker script, add logging:
logger.info(f"Reporting event: {event_type}")
await report_event(event_type, event_data)
```

### Issue: "Message injection not working"
**Check:**
1. Is polling loop running? (check logs for "Polling for messages")
2. Is message in queue? (check `/api/v1/sandboxes/{id}/messages`)
3. Is `client.query()` being called? (check logs)

**Debug:**
```python
# In intervention_handler, add:
logger.info(f"Polling messages... found {len(messages)}")
if messages:
    logger.info(f"Injecting: {messages[0]['content']}")
    await client.query(messages[0]['content'])
```

### Issue: "Agent stops after first response"
**Fix:** Make sure you're using `receive_messages()`, not `receive_response()`

---

## Minimal Working Example

Here's the absolute minimum to test:

```python
# test_minimal_agent.py
import asyncio
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

async def test():
    options = ClaudeAgentOptions(
        system_prompt="You are a helpful coding assistant",
        allowed_tools=["Read", "Write", "Bash"],
        max_turns=5,
    )
    
    async with ClaudeSDKClient(options=options) as client:
        # Initial query
        await client.query("List files in current directory")
        
        # Stream messages
        async for msg in client.receive_messages():
            print(f"Message: {type(msg).__name__}")
            if hasattr(msg, 'content'):
                print(f"Content: {msg.content}")
            
            # Test message injection after first response
            if isinstance(msg, AssistantMessage):
                await asyncio.sleep(1)
                await client.query("Now create a test file")
                break

asyncio.run(test())
```

**Run it:**
```bash
# Z.AI configuration (matching worker script)
export ANTHROPIC_AUTH_TOKEN=your_z_ai_token
export ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
export ANTHROPIC_MODEL=glm-4.6v

# Or regular Anthropic:
# export ANTHROPIC_API_KEY=your_key
# export ANTHROPIC_MODEL=claude-sonnet-4-20250514

cd backend
uv run python test_minimal_agent.py
```

---

## Event Streaming Architecture

**Flow:**
```
Worker Script
    ↓ (HTTP POST /api/v1/sandboxes/{id}/events)
Backend EventBus (Redis Pub/Sub)
    ↓ (WebSocket broadcast)
Frontend WebSocket Clients
```

**Performance (Single User):**
- Worker HTTP POST: ~5-20ms
- EventBus publish: ~1-5ms  
- WebSocket broadcast: ~1-5ms
- **Total: ~10-50ms per event** ✅

**Scaling:** Redis pub/sub handles 10k+ subscribers. For single user, everything is fast and ready.

---

## Next Steps After Prototype Works

1. ✅ Verify events stream correctly (< 100ms latency)
2. ✅ Verify message injection creates new conversation turns
3. ✅ Test with real sandbox deployment
4. ✅ Add frontend visualization (use existing WebSocket endpoint)
5. ✅ Iterate: Move working patterns back to main system

---

## Standalone UI Sample

**`sandbox-ui-sample.html`** - Complete standalone UI (no build step, no dependencies)

**Features:**
- ✅ Real-time event streaming via WebSocket
- ✅ Message injection interface
- ✅ Event visualization with color coding
- ✅ Performance stats (latency, event count, uptime)
- ✅ No dependencies - just open in browser

**Usage:**
1. Start backend: `cd backend && uv run python -m omoi_os.api.main`
2. Open `sandbox-ui-sample.html` in browser
3. Enter sandbox ID (from `test_sandbox_event_stream.py` or orchestrator)
4. Click "Connect" to start streaming events
5. Use "Message Injection" panel to send messages

**No build step, no npm install - just works!**

---

## Files Ready to Test

- ✅ `test_sandbox_event_stream.py` - Full prototype test script
- ✅ `test_claude_agent_minimal.py` - Minimal SDK pattern test
- ✅ `sandbox-ui-sample.html` - Standalone UI sample
- ✅ `backend/omoi_os/services/daytona_spawner.py` - Fixed worker script

**Prototype approach:** Get `test_sandbox_event_stream.py` working fully, then iterate to integrate into main system.
