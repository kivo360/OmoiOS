# Development Workflow Guide

**Created**: 2025-12-12  
**Purpose**: Practical step-by-step guide for using the sandbox agents design documentation to implement features.

---

## Overview

This guide explains **how to use** the design documents in this directory to actually build the sandbox agents system. The key insight is that `06_implementation_checklist.md` is your **actionable guide** — it contains copy-pasteable test code and implementation code for each step.

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
