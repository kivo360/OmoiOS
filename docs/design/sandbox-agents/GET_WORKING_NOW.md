# Get It Working NOW - Action Plan

**Goal**: Get a working sandbox agent in the next 30 minutes.

---

## ✅ What's Already Fixed

1. ✅ **Worker script** - Uses correct `receive_messages()` + `client.query()` pattern
2. ✅ **Documentation** - Matches actual SDK behavior
3. ✅ **Event mapping** - Properly maps SDK messages to events

---

## 🚀 Quick Test (5 minutes)

### Test 1: Verify SDK Pattern Works

```bash
# Install SDK if needed
pip install claude-agent-sdk

# Set Z.AI credentials (matching worker script)
export ANTHROPIC_AUTH_TOKEN=your_z_ai_token
export ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
export ANTHROPIC_MODEL=glm-4.6v

# Or use regular Anthropic:
# export ANTHROPIC_API_KEY=your_anthropic_key
# export ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Run minimal test
python test_claude_agent_minimal.py
```

**Expected output:**
```
✅ Got first AssistantMessage
✅ Message injected via client.query()
✅ ALL TESTS PASSED - Pattern matches Claude Code web!
```

**If this fails:** SDK setup issue - fix API key or installation first.

---

## 🎯 Next: Test Full Worker Script

### Option A: Test in Real Sandbox (15 minutes)

1. **Start backend:**
   ```bash
   cd backend
   uv run python -m omoi_os.api.main
   ```

2. **Create sandbox via API:**
   ```bash
   curl -X POST http://localhost:18000/api/v1/sandboxes \
     -H "Content-Type: application/json" \
     -d '{
       "task_id": "test-1",
       "agent_id": "agent-1",
       "runtime": "claude"
     }'
   ```

3. **Watch logs** - Should see:
   - `Claude Agent Worker starting`
   - `Reporting event: agent.started`
   - `Streaming messages...`

4. **Inject message:**
   ```bash
   curl -X POST http://localhost:18000/api/v1/sandboxes/{sandbox_id}/messages \
     -H "Content-Type: application/json" \
     -d '{"content": "Focus on tests", "message_type": "user_message"}'
   ```

5. **Verify in logs:**
   - `Polling messages... found 1`
   - `Injecting: Focus on tests`
   - `Reporting event: agent.message_injected`

### Option B: Test Worker Script Directly (10 minutes)

```python
# test_worker_pattern.py
import asyncio
import sys
sys.path.insert(0, 'backend')

# Simulate worker environment
import os
os.environ['TASK_ID'] = 'test-1'
os.environ['AGENT_ID'] = 'agent-1'
os.environ['SANDBOX_ID'] = 'sandbox-1'
os.environ['BASE_URL'] = 'http://localhost:18000'
os.environ['ANTHROPIC_API_KEY'] = 'your-key'

# Import worker functions (extract from daytona_spawner.py)
# Or just copy the run_agent function and test it

async def test():
    task_desc = "List files in /workspace"
    success, result = await run_agent(task_desc)
    print(f"Success: {success}")
    print(f"Result: {result[:200]}")

asyncio.run(test())
```

---

## 🔍 What to Verify

### ✅ Core Flow Works

- [ ] Agent starts → `agent.started` event
- [ ] Agent thinks → `agent.thinking` event  
- [ ] Agent uses tool → `agent.tool_use` event
- [ ] Agent responds → `agent.message` event
- [ ] Message injected → `agent.message_injected` event
- [ ] Agent responds to injection → New `agent.message` event

### ✅ Pattern Matches Claude Code Web

- [ ] Uses `receive_messages()` (indefinite streaming)
- [ ] Uses `client.query()` for message injection
- [ ] Maintains conversation state
- [ ] Streams events in real-time

---

## 🐛 Common Issues & Quick Fixes

### Issue: "receive_messages() hangs"
**Fix:** Make sure you're inside `async with ClaudeSDKClient()` context

### Issue: "No events appearing"
**Fix:** Check `report_event()` is actually being called - add logging

### Issue: "Message injection doesn't work"
**Fix:** 
1. Verify polling loop is running (check logs)
2. Verify `client.query()` is being called (check logs)
3. Verify message is in queue (check API endpoint)

---

## 📋 Checklist: Is It Working?

- [ ] Minimal test passes (`test_claude_agent_minimal.py`)
- [ ] Worker script runs without errors
- [ ] Events appear in logs/WebSocket
- [ ] Message injection creates new conversation turn
- [ ] Agent responds to injected messages

**If all checked:** ✅ **IT WORKS - You have a working prototype!**

---

## 🎯 Next Steps After It Works

1. **Add frontend visualization** (use existing WebSocket)
2. **Add one integration test** (verify end-to-end)
3. **Fix CORS** (from quality assessment)
4. **Add rate limiting** (from quality assessment)

**But first: GET IT WORKING. Then optimize.**

---

## 🆘 Still Not Working?

1. **Check logs** - What errors appear?
2. **Run minimal test** - Does SDK work at all?
3. **Check API key** - Is it valid?
4. **Check network** - Can sandbox reach backend?

**Share the error and we'll fix it immediately.**
