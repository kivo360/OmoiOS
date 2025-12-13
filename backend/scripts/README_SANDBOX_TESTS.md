# Sandbox Testing Scripts

Quick reference for testing the Daytona sandbox and agent execution system.

---

## Testing Ladder (Run in Order)

### Level 1: Basic Sandbox ✅
```bash
# Verify Daytona connection and basic sandbox operations
uv run python scripts/test_sandbox_simple.py
```
**Tests**: Create sandbox, run commands, cleanup

### Level 2: SDK Installation ✅
```bash
# Verify Claude SDK installs and initializes in sandbox
uv run python scripts/test_sandbox_claude_sdk.py
```
**Tests**: SDK import, options creation, API connection

### Level 3: Direct Task Injection ✅ (NEW)
```bash
# Run agent with injected task (no DB/server needed)
uv run python scripts/test_direct_task_injection.py

# OpenHands runtime
uv run python scripts/test_direct_task_injection.py --runtime openhands

# Custom task
uv run python scripts/test_direct_task_injection.py --task "Create a hello.py file"
```
**Tests**: Full agent execution with task injection

### Level 4: Full E2E with Z.AI
```bash
# End-to-end test with DaytonaSpawnerService
uv run python scripts/test_spawner_e2e.py
```
**Tests**: Spawner service, credential injection, agent execution

### Level 5: API Flow Verification
```bash
# Requires running backend server
uv run python scripts/verify_sandbox_flow.py
```
**Tests**: Ticket → Task → Sandbox → Events flow

---

## Script Comparison

| Script | Runtime | DB Needed | Server Needed | What It Tests |
|--------|---------|-----------|---------------|---------------|
| `test_sandbox_simple.py` | - | ❌ | ❌ | Basic Daytona ops |
| `test_sandbox_claude_sdk.py` | Claude | ❌ | ❌ | SDK installation |
| `test_direct_task_injection.py` | Both | ❌ | ❌ | **Agent execution** |
| `test_spawner_e2e.py` | Claude | ❌ | ❌ | Spawner service |
| `verify_sandbox_flow.py` | - | ✅ | ✅ | Full API flow |

---

## Quick Commands

```bash
# Most useful for development (no dependencies)
uv run python scripts/test_direct_task_injection.py

# Quick smoke test
uv run python scripts/test_sandbox_simple.py

# Full E2E with spawner
uv run python scripts/test_spawner_e2e.py
```

---

## Environment Variables

Required in `.env.local`:

```bash
# Always required
DAYTONA_API_KEY=dtn_...

# For Claude runtime
ANTHROPIC_API_KEY=sk-...
ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic  # Optional for Z.AI
ANTHROPIC_MODEL=glm-4.6v  # Optional

# For OpenHands runtime
LLM_API_KEY=sk-...
LLM_MODEL=anthropic/claude-sonnet-4-20250514
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `DAYTONA_API_KEY not set` | Add to `.env.local` |
| `ANTHROPIC_API_KEY not set` | Add to `.env.local` |
| Sandbox creation timeout | Check Daytona dashboard, increase timeout |
| SDK install fails | Check network, try manual install in sandbox |
| Agent hangs | Increase `--timeout`, check task complexity |

---

## What Each Script Tests

### `test_sandbox_simple.py`
- ✅ Daytona API key works
- ✅ Sandbox creates successfully  
- ✅ Commands execute in sandbox
- ✅ Cleanup works

### `test_sandbox_claude_sdk.py`
- ✅ Claude Agent SDK installs
- ✅ SDK imports work
- ✅ ClaudeAgentOptions creates
- ✅ API connection (if credentials set)

### `test_direct_task_injection.py` ⭐
- ✅ Task data injection via TASK_DATA_BASE64
- ✅ Worker script executes
- ✅ Agent receives injected task (no API fetch)
- ✅ Agent executes and produces output

### `test_spawner_e2e.py`
- ✅ DaytonaSpawnerService works
- ✅ Z.AI credentials injected
- ✅ Worker script starts
- ✅ Agent completes task

### `verify_sandbox_flow.py`
- ✅ Backend server running
- ✅ Ticket creates task
- ✅ Task gets assigned
- ✅ Sandbox spawns (if configured)
