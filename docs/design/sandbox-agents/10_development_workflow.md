# Development Workflow Guide

**Created**: 2025-12-12  
**Purpose**: Practical step-by-step guide for using the sandbox agents design documentation to implement features.

---

## Overview

This guide explains **how to use** the design documents in this directory to actually build the sandbox agents system. The key insight is that `06_implementation_checklist.md` is your **actionable guide** — it contains copy-pasteable test code and implementation code for each step.

**Using Cursor?** Jump to [🤖 Cursor AI Prompts](#-cursor-ai-prompts) for ready-to-use prompts with the right `@` context for each phase.

---

## Document Purpose Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DOCUMENT PURPOSE MAP                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PLANNING (Read first):                                             │
│  ├─ README.md              → Overview, quick orientation            │
│  └─ 02_gap_analysis.md     → What exists (85%!), what's missing    │
│                                                                     │
│  IMPLEMENTATION (Follow this):                                      │
│  └─ 06_implementation_checklist.md  ⭐ YOUR MAIN GUIDE             │
│     Contains: Tests → Code → Gates for each phase                   │
│                                                                     │
│  REFERENCE (Look up as needed):                                     │
│  ├─ 01_architecture.md     → System design diagrams                 │
│  ├─ 04_communication_patterns.md → API schemas, security           │
│  ├─ 05_http_api_migration.md → Endpoint mappings                   │
│  └─ 07_existing_systems_integration.md → Guardian, etc.            │
│                                                                     │
│  FUTURE (Don't implement yet):                                      │
│  ├─ 08_frontend_integration.md → UI spec                           │
│  └─ 09_rich_activity_feed_architecture.md → Post-MVP               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Development Workflow

### Step 1: Environment Setup

```bash
# Navigate to the backend directory
cd backend

# Sync dependencies with UV
uv sync

# Verify your environment is working
pytest tests/ -v --collect-only  # Should show available tests
```

---

### Step 2: Follow the Phase-Based Workflow

The implementation is broken into phases. Each phase has:
- **Tests to Write** — Copy these first
- **Implementation Code** — Copy after tests exist
- **Gate Checklist** — Validation before moving on

```
┌─────────────────────────────────────────────────────────────────────┐
│                 DEVELOPMENT LOOP (REPEAT PER PHASE)                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. OPEN the checklist at the current phase                         │
│     └─ Find the "Tests to Write" section                           │
│                                                                     │
│  2. COPY the test code from the doc                                 │
│     └─ Create new test file: tests/integration/test_sandbox_*.py   │
│     └─ Paste the test specification                                │
│                                                                     │
│  3. RUN the test (it should FAIL)                                   │
│     └─ pytest tests/integration/test_sandbox_events.py -v          │
│     └─ Red = expected (feature doesn't exist yet)                  │
│                                                                     │
│  4. IMPLEMENT the minimum code to make test pass                    │
│     └─ Copy implementation from "Implementation" section            │
│     └─ Create/modify backend files as specified                     │
│                                                                     │
│  5. RUN the test again (it should PASS)                             │
│     └─ pytest tests/integration/test_sandbox_events.py -v          │
│     └─ Green = feature works ✅                                     │
│                                                                     │
│  6. CHECK the phase gate                                            │
│     └─ Run ALL tests for the phase                                 │
│     └─ All green = ready for next phase                            │
│                                                                     │
│  7. COMMIT with meaningful message                                  │
│     └─ git commit -m "Phase 1.2: Add sandbox event callback"       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Step 3: Concrete First Steps

#### Phase 0: Validate Infrastructure (~1-2 hours)

**Goal**: Confirm existing systems work before writing new code.

```bash
# Navigate to backend
cd /Users/kevinhill/Coding/Experiments/senior-sandbox/senior_sandbox/backend

# Run Phase 0 validation tests
pytest tests/integration/ -v -k "websocket or event_bus"

# Expected results:
# ✅ If tests pass → Existing WebSocket + Event Bus work, proceed to Phase 1
# ❌ If tests fail → Fix existing infrastructure before proceeding
```

#### Phase 1: Sandbox Event Callback (~2-3 hours)

**Goal**: Create endpoint for sandbox to report events back to server.

```bash
# 1. Create the test file (copy content from 06_implementation_checklist.md)
mkdir -p tests/integration/sandbox
touch tests/integration/sandbox/test_event_callback.py

# 2. Copy the test code from the checklist into this file
#    Look for: "## Phase 1: Sandbox Event Callback"
#    Copy the test specifications

# 3. Run test (should FAIL initially - endpoint doesn't exist)
pytest tests/integration/sandbox/test_event_callback.py -v

# 4. Implement the endpoint
#    Create: backend/omoi_os/api/routes/sandbox.py
#    Copy implementation code from checklist

# 5. Run test again (should PASS now)
pytest tests/integration/sandbox/test_event_callback.py -v

# 6. Commit your work
git add -A
git commit -m "Phase 1: Add sandbox event callback endpoint"
```

---

## 🤖 Cursor AI Prompts

Copy these prompts directly into Cursor. The `@` references will automatically include the right context.

### Phase 0: Validate Infrastructure

```
@docs/design/sandbox-agents/06_implementation_checklist.md 
@docs/design/sandbox-agents/02_gap_analysis.md

I'm starting Phase 0 of the sandbox agents implementation. Help me:

1. Identify which existing tests I need to run to validate infrastructure
2. Run the WebSocket and EventBus integration tests
3. Check if there are any failing tests I need to fix before proceeding

Show me the exact pytest commands to run and explain what each test validates.
```

### Phase 1: Sandbox Event Callback

```
@docs/design/sandbox-agents/06_implementation_checklist.md 
@docs/design/sandbox-agents/04_communication_patterns.md
@backend/tests/conftest.py

I'm implementing Phase 1: Sandbox Event Callback. Following the test-first approach:

1. Create the test file at `tests/integration/sandbox/test_event_callback.py`
2. Copy the Phase 1 test specifications from the checklist
3. Make sure the tests use existing fixtures from conftest.py

Start by creating the test file with the test code from the checklist.
```

**After tests exist:**

```
@docs/design/sandbox-agents/06_implementation_checklist.md
@docs/design/sandbox-agents/05_http_api_migration.md
@backend/omoi_os/api/routes/

The Phase 1 tests are failing (as expected). Now implement the sandbox event callback endpoint:

1. Create `backend/omoi_os/api/routes/sandbox.py`
2. Implement POST /api/v1/sandbox/{sandbox_id}/events
3. Register the route in the API router
4. Follow the patterns from existing routes

Use the implementation code from the checklist.
```

### Phase 2: Message Injection

```
@docs/design/sandbox-agents/06_implementation_checklist.md
@docs/design/sandbox-agents/04_communication_patterns.md
@backend/omoi_os/api/routes/sandbox.py

I'm implementing Phase 2: Message Injection. Following test-first:

1. Add the Phase 2 test specifications to the sandbox test file
2. The tests should cover message posting and queue retrieval
3. Use existing fixtures from conftest.py

Create the tests first, then we'll implement.
```

**After tests exist:**

```
@docs/design/sandbox-agents/06_implementation_checklist.md
@backend/omoi_os/api/routes/sandbox.py
@backend/omoi_os/services/event_bus.py

Phase 2 tests are ready. Now implement:

1. POST /api/v1/sandbox/{sandbox_id}/messages - Accept messages for injection
2. GET /api/v1/sandbox/{sandbox_id}/messages - Poll for pending messages
3. Use Redis for the message queue (follow EventBusService patterns)

Implement these endpoints to make the tests pass.
```

### Phase 3: Worker Script Updates

```
@docs/design/sandbox-agents/06_implementation_checklist.md
@docs/design/sandbox-agents/01_architecture.md
@docs/libraries/claude-agent-sdk-python-clean.md
@backend/omoi_os/services/daytona_spawner.py

I'm implementing Phase 3: Worker Script Updates. I need to:

1. Update the Claude worker script to use HTTP callbacks instead of MCP
2. Add PreToolUse hooks for message injection (sub-second intervention)
3. Make the worker report events via POST to our new endpoints

Show me how to modify the worker script template in daytona_spawner.py.
```

**For OpenHands worker:**

```
@docs/design/sandbox-agents/06_implementation_checklist.md
@docs/libraries/software-agent-sdk-clean.md
@backend/omoi_os/services/daytona_spawner.py

Now update the OpenHands worker script similarly:

1. Add HTTP callbacks for event reporting
2. Implement hook-based message injection
3. Follow the same patterns as the Claude worker

Show me the OpenHands-specific modifications.
```

### Phase 3.5: GitHub Clone Integration

```
@docs/design/sandbox-agents/06_implementation_checklist.md
@docs/design/sandbox-agents/03_git_branch_workflow.md
@backend/omoi_os/services/daytona_spawner.py
@backend/omoi_os/services/github_api.py

I'm implementing Phase 3.5: GitHub Clone Integration. I need to:

1. Inject GitHub OAuth token into sandbox environment
2. Clone the repository when sandbox starts
3. Create a feature branch for the task

Show me how to modify spawn_sandbox() to include GitHub setup.
```

### Phase 4: Database Persistence

```
@docs/design/sandbox-agents/06_implementation_checklist.md
@docs/design/sandbox-agents/07_existing_systems_integration.md
@backend/omoi_os/models/

I'm implementing Phase 4: Database Persistence. I need to:

1. Create a SandboxEvent model for persisting events
2. Add migration for the new table
3. Update the event callback endpoint to persist events

Follow existing model patterns and avoid SQLAlchemy reserved keywords (no `metadata` attribute!).
```

### Phase 5: Branch Workflow Service

```
@docs/design/sandbox-agents/06_implementation_checklist.md
@docs/design/sandbox-agents/03_git_branch_workflow.md
@backend/omoi_os/services/github_api.py

I'm implementing Phase 5: BranchWorkflowService. This handles:

1. Creating feature branches when tasks start
2. Creating PRs when tasks complete
3. Managing the branch lifecycle (Musubi workflow)

Create the BranchWorkflowService class following existing service patterns.
```

### Phase 6: Guardian Integration

```
@docs/design/sandbox-agents/06_implementation_checklist.md
@docs/design/sandbox-agents/07_existing_systems_integration.md
@backend/omoi_os/services/intelligent_guardian.py
@backend/omoi_os/services/conversation_intervention.py

I'm implementing Phase 6: Guardian Integration. I need to:

1. Connect IntelligentGuardian to monitor sandbox agents
2. Route interventions through message injection (not MCP)
3. Update trajectory analysis to handle sandbox mode

Show me the modifications needed to integrate Guardian with sandboxes.
```

### Phase 7: Fault Tolerance

```
@docs/design/sandbox-agents/06_implementation_checklist.md
@docs/design/sandbox-agents/07_existing_systems_integration.md
@backend/omoi_os/services/restart_orchestrator.py

I'm implementing Phase 7: Fault Tolerance. I need to:

1. Make RestartOrchestrator sandbox-aware
2. Add heartbeat monitoring for sandbox agents
3. Implement graceful shutdown and recovery

Show me how to extend the fault tolerance system for sandboxes.
```

### Debugging / Test Failures

```
@docs/design/sandbox-agents/06_implementation_checklist.md
@backend/tests/integration/sandbox/

My sandbox tests are failing. Here's the error:

[PASTE ERROR HERE]

Help me debug this. Check:
1. Is the route registered correctly?
2. Are all imports working?
3. Does the test use the right fixtures?
```

### Running All Phase Tests

```
@docs/design/sandbox-agents/06_implementation_checklist.md

I've completed Phase [X]. Help me verify by:

1. Running all tests for this phase
2. Checking test coverage
3. Running linting and type checks
4. Confirming I can proceed to the next phase

What commands should I run?
```

---

### Utility Prompts

#### Understanding the Architecture

```
@docs/design/sandbox-agents/01_architecture.md
@docs/design/sandbox-agents/02_gap_analysis.md

Explain the sandbox agents architecture to me:
1. How do sandboxes communicate with the main server?
2. What's the flow when a user sends a message to an agent?
3. How does Guardian monitor and intervene?

Use diagrams from the architecture doc.
```

#### Code Review Before Commit

```
@docs/design/sandbox-agents/06_implementation_checklist.md
@backend/omoi_os/api/routes/sandbox.py

Review my sandbox.py implementation:
1. Does it follow the checklist specifications?
2. Are there any security issues?
3. Does it match the API patterns in communication_patterns.md?
4. Any missing error handling?
```

#### Understanding Existing Code

```
@backend/omoi_os/services/daytona_spawner.py
@docs/design/sandbox-agents/02_gap_analysis.md

Help me understand the existing DaytonaSpawnerService:
1. How does spawn_sandbox() work?
2. Where do I need to add GitHub token injection?
3. What worker script templates exist?
```

#### Creating a PR Summary

```
@docs/design/sandbox-agents/06_implementation_checklist.md

I just completed Phase [X]. Help me write a PR description that includes:
1. What was implemented
2. How it was tested
3. Any decisions made
4. What's next (Phase X+1)
```

#### Quick Context Refresh

```
@docs/design/sandbox-agents/README.md
@docs/design/sandbox-agents/06_implementation_checklist.md

I'm returning to this project after a break. Give me a quick summary:
1. What phase am I on?
2. What's left to do for MVP?
3. What should I work on next?
```

#### SDK Reference

```
@docs/libraries/claude-agent-sdk-python-clean.md

Show me how to use PreToolUse hooks in the Claude Agent SDK.
I need to inject a check for pending messages before each tool call.
```

```
@docs/libraries/software-agent-sdk-clean.md

Show me how OpenHands/Software Agent SDK handles tool execution hooks.
I need to add message injection similar to what I did for Claude.
```

---

### Testing & Validation Prompts

#### Contract Testing

```
@backend/tests/contract/test_sandbox_event_contract.py
@docs/design/sandbox-agents/04_communication_patterns.md

Create/extend contract tests for sandbox APIs:
1. Validate SandboxEventPayload schema matches design docs
2. Test all event_type enum values are handled
3. Ensure request/response shapes are backward compatible
4. Add contract tests for message injection endpoint

Follow the existing contract test patterns.
```

#### E2E Flow Validation ("Does This Actually Work?")

```
@docs/design/sandbox-agents/01_architecture.md
@docs/design/sandbox-agents/06_implementation_checklist.md
@backend/tests/integration/sandbox/

Test the complete sandbox lifecycle end-to-end:
1. User sends message → Sandbox spawned
2. Worker starts → Reports AGENT_STARTED event
3. Worker executes tool → Reports TOOL_CALL event  
4. User sends intervention → Message injected to worker
5. Worker completes → Reports TASK_COMPLETED
6. Sandbox cleaned up

Write an integration test that validates this entire flow works together.
This is the "does this shit actually work" test.
```

#### Mocking External Services

```
@backend/tests/conftest.py
@backend/omoi_os/services/daytona_spawner.py
@backend/omoi_os/services/github_api.py

Set up test fixtures that mock external services:
1. Mock Daytona API (create_sandbox, execute_command, delete_sandbox)
2. Mock GitHub API (clone repo, create branch, create PR)
3. Ensure tests can run without real API credentials
4. Follow existing mock patterns in conftest.py

Show me the fixtures I need to create.
```

---

## Phase Progress Tracking

Copy this checklist into your notes and update as you progress:

### MVP Track (Phases 0-3.5)

```markdown
## Phase 0: Validate Infrastructure
- [ ] Run existing WebSocket tests
- [ ] Run existing EventBus tests
- [ ] Confirm Daytona spawner tests pass
- [ ] **GATE**: All infrastructure tests pass

## Phase 1: Sandbox Event Callback
- [ ] Write `test_sandbox_can_post_event`
- [ ] Write `test_sandbox_event_broadcasts_to_websocket`
- [ ] Implement `POST /api/v1/sandbox/{id}/events`
- [ ] **GATE**: Phase 1 tests pass

## Phase 2: Message Injection
- [ ] Write `test_sandbox_can_receive_message`
- [ ] Write `test_message_appears_in_queue`
- [ ] Implement `POST /api/v1/sandbox/{id}/messages`
- [ ] Implement message queue polling
- [ ] **GATE**: Phase 2 tests pass

## Phase 3: Worker Script Updates
- [ ] Update Claude worker script for HTTP callbacks
- [ ] Update OpenHands worker script for HTTP callbacks
- [ ] Add hook-based message injection
- [ ] **GATE**: Phase 3 tests pass

## Phase 3.5: GitHub Clone Integration
- [ ] Write GitHub clone tests
- [ ] Implement OAuth token injection
- [ ] Implement repository cloning on sandbox start
- [ ] **GATE**: 🎉 MVP COMPLETE!
```

### Full Integration Track (Phases 4-7)

```markdown
## Phase 4: Database Persistence
- [ ] Add sandbox events table
- [ ] Implement event persistence
- [ ] Add history retrieval endpoint
- [ ] **GATE**: Phase 4 tests pass

## Phase 5: Branch Workflow Service
- [ ] Implement BranchWorkflowService
- [ ] Add branch creation logic
- [ ] Add PR creation logic
- [ ] Add merge logic
- [ ] **GATE**: Phase 5 tests pass

## Phase 6: Guardian Integration
- [ ] Connect Guardian to sandbox monitoring
- [ ] Implement intervention via message injection
- [ ] Add trajectory analysis for sandboxes
- [ ] **GATE**: Phase 6 tests pass

## Phase 7: Fault Tolerance
- [ ] Integrate RestartOrchestrator with sandboxes
- [ ] Add heartbeat monitoring
- [ ] Implement graceful shutdown
- [ ] **GATE**: 🎉 FULL INTEGRATION COMPLETE!
```

---

## MVP vs Full Integration

```
┌─────────────────────────────────────────────────────────────────────┐
│                    WHEN TO STOP (MVP vs FULL)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  MVP COMPLETE (Stop here first!):                                   │
│  ═══════════════════════════════                                    │
│  ✅ Phase 0: Validate infrastructure          (~1-2h)               │
│  ✅ Phase 1: Sandbox event callback           (~2-3h)               │
│  ✅ Phase 2: Message injection                (~4-6h)               │
│  ✅ Phase 3: Worker script updates            (~4h)                 │
│  ✅ Phase 3.5: GitHub clone integration       (~3-4h)               │
│  ────────────────────────────────────────────────────               │
│  🎉 MVP DONE! Test with real agent. ~14-17 hours total             │
│                                                                     │
│  FULL INTEGRATION (After MVP works):                                │
│  ═══════════════════════════════════                                │
│  Phase 4: Database persistence                (~4-6h)               │
│  Phase 5: Branch workflow service             (~10-15h)             │
│  Phase 6: Guardian integration                (~6-8h)               │
│  Phase 7: Fault tolerance                     (~8-12h)              │
│  ────────────────────────────────────────────────────               │
│  🚀 Production ready! ~38-50 hours total                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference Commands

### Testing

```bash
# Run all sandbox tests
pytest tests/integration/sandbox/ -v

# Run specific test file
pytest tests/integration/sandbox/test_event_callback.py -v

# Run specific test
pytest tests/integration/sandbox/test_event_callback.py::test_sandbox_can_post_event -v

# Run with coverage
pytest tests/integration/sandbox/ -v --cov=omoi_os.api.routes.sandbox

# Run fast unit tests only
pytest tests/ -v -m "unit"

# Run integration tests only
pytest tests/ -v -m "integration"
```

### Code Quality

```bash
# Check for lint issues
ruff check backend/omoi_os/

# Auto-fix lint issues
ruff check backend/omoi_os/ --fix

# Format code
black backend/omoi_os/

# Type check
mypy backend/omoi_os/
```

### Git Workflow

```bash
# Before starting a phase
git checkout -b feature/sandbox-phase-1

# After completing a phase
git add -A
git commit -m "Phase 1: Add sandbox event callback endpoint"
git push -u origin feature/sandbox-phase-1

# Create PR for review
gh pr create --title "Phase 1: Sandbox Event Callback" --body "Implements event callback endpoint for sandbox agents"
```

---

## Troubleshooting

### Test Won't Pass

1. **Check the test output** — What's the actual vs expected?
2. **Check imports** — Is the route registered in `api/__init__.py`?
3. **Check the checklist** — Did you copy all the implementation code?
4. **Run in isolation** — `pytest path/to/test.py -v -s` for verbose output

### Existing Tests Fail in Phase 0

1. **Check database** — Is PostgreSQL running? `docker ps`
2. **Check Redis** — Is Redis running? `redis-cli ping`
3. **Check environment** — Are `.env` variables set?
4. **Run sync** — `uv sync` to ensure dependencies

### Import Errors

1. **Check file exists** — Did you create the new file?
2. **Check `__init__.py`** — Is the module exported?
3. **Restart test runner** — Sometimes pytest caches imports

---

## Summary Workflow

| Step | What to Do | Document |
|------|------------|----------|
| 1 | Read this guide | `10_development_workflow.md` (you are here) |
| 2 | Skim README for overview | `README.md` |
| 3 | Skim Gap Analysis | `02_gap_analysis.md` |
| 4 | **Follow Phase 0-3.5 for MVP** | `06_implementation_checklist.md` ⭐ |
| 5 | Reference API patterns as needed | `04_communication_patterns.md` |
| 6 | After MVP, follow Phases 4-7 | `06_implementation_checklist.md` |

---

## Related Documents

- [README](./README.md) — Project overview
- [Gap Analysis](./02_gap_analysis.md) — What exists vs. what's needed
- [Implementation Checklist](./06_implementation_checklist.md) — ⭐ Main implementation guide
- [Architecture](./01_architecture.md) — System design reference
- [Communication Patterns](./04_communication_patterns.md) — API schemas and security
