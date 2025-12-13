# Improved Testing Guide

**Created**: 2025-12-13  
**Purpose**: Streamlined testing workflows for sandbox agents system  
**Replaces**: Consolidates guidance from 10, 11, TESTING_QUICK_START

---

## The Testing Ladder 🪜

Run tests in this order. Stop when something fails, fix it, then continue.

```
┌─────────────────────────────────────────────────────────────┐
│                    THE TESTING LADDER                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Level 0: SMOKE TEST (30 seconds)                           │
│  "Does the basic infrastructure even work?"                 │
│  → scripts/smoke_test.py                                    │
│                                                              │
│  Level 1: UNIT TESTS (1-2 minutes)                          │
│  "Does my logic work in isolation?"                         │
│  → pytest tests/unit/ -v --maxfail=1                        │
│                                                              │
│  Level 2: INTEGRATION TESTS (2-5 minutes)                   │
│  "Do the APIs and services work together?"                  │
│  → pytest tests/integration/sandbox/ -v --maxfail=1         │
│                                                              │
│  Level 3: E2E SCRIPTS (5-15 minutes)                        │
│  "Does it actually work with real sandboxes?"               │
│  → scripts/test_spawner_e2e.py                              │
│                                                              │
│  Level 4: FULL VALIDATION (15-30 minutes)                   │
│  "Is everything production-ready?"                          │
│  → scripts/run_all_tests.py                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start Commands

Copy-paste these commands based on what you're doing:

### 🔥 Just Made a Change

```bash
cd backend

# Quick smoke test (30s)
uv run python scripts/smoke_test.py

# If smoke passes, run integration tests (2-5min)
pytest tests/integration/sandbox/ -v --maxfail=1
```

### 🧪 Testing New Feature

```bash
cd backend

# 1. Write test first (it should FAIL)
pytest tests/integration/sandbox/test_YOUR_FEATURE.py -v

# 2. Implement feature, then run again (should PASS)
pytest tests/integration/sandbox/test_YOUR_FEATURE.py -v

# 3. Run all sandbox tests
pytest tests/integration/sandbox/ -v --maxfail=1
```

### 🐛 Something's Broken

```bash
cd backend

# Run failing test with verbose output
pytest tests/integration/sandbox/test_event_callback.py::test_name -v -s

# Or use debugging script
uv run python scripts/debug_sandbox_flow.py
```

### ✅ Before Commit/PR

```bash
cd backend

# Full validation (run all levels)
uv run python scripts/run_all_tests.py

# Or manually:
pytest tests/unit/ tests/integration/sandbox/ -v --maxfail=1
uv run python scripts/test_spawner_e2e.py
```

---

## Script Organization

### Naming Convention

Scripts follow this pattern: `{type}_{feature}.py`

| Type | Purpose | Example |
|------|---------|---------|
| `smoke_` | Quick validation | `smoke_test.py` |
| `test_` | Feature testing | `test_spawner_e2e.py` |
| `debug_` | Investigation | `debug_sandbox_flow.py` |
| `verify_` | Flow validation | `verify_sandbox_flow.py` |

### Script Inventory

```bash
# Core testing scripts (run in this order)
scripts/
├── smoke_test.py              # Level 0: Quick checks
├── test_sandbox_simple.py     # Level 2: Basic sandbox ops
├── test_sandbox_claude_sdk.py # Level 3: SDK integration
├── test_spawner_e2e.py        # Level 3: Full E2E
├── verify_sandbox_flow.py     # Level 3: API flow validation
└── run_all_tests.py           # Level 4: Everything (NEW)
```

---

## AI Prompts by Scenario

### Prompt 1: Implementing New Feature

```
@docs/design/sandbox-agents/12_improved_testing_guide.md
@docs/design/sandbox-agents/06_implementation_checklist.md
@backend/tests/integration/sandbox/

I'm implementing [FEATURE_NAME] from Phase [X].

Help me:
1. Create a failing test first
2. Implement the minimum code to pass
3. Run the testing ladder to validate

Feature: [ONE SENTENCE DESCRIPTION]
```

### Prompt 2: Test Is Failing

```
@docs/design/sandbox-agents/12_improved_testing_guide.md
@backend/tests/integration/sandbox/test_[FILE].py

My test is failing with this error:

[PASTE FULL ERROR]

Help me:
1. Understand what the test expects
2. Identify the root cause
3. Fix it and verify
```

### Prompt 3: Adding Test Coverage

```
@docs/design/sandbox-agents/12_improved_testing_guide.md
@backend/omoi_os/api/routes/sandbox.py
@backend/tests/integration/sandbox/

I need to add tests for the sandbox API. Help me:

1. Identify untested code paths
2. Write tests for edge cases:
   - Invalid input
   - Missing auth
   - Timeout scenarios
3. Show me how to run with coverage
```

### Prompt 4: E2E Validation

```
@docs/design/sandbox-agents/12_improved_testing_guide.md
@backend/scripts/test_spawner_e2e.py
@docs/design/sandbox-agents/01_architecture.md

I want to validate the complete flow works:
1. Task created → Sandbox spawned
2. Worker executes → Events reported
3. Message injected → Worker receives
4. Task completes → Cleanup

Help me run and interpret the E2E test results.
```

### Prompt 5: Debug Script Creation

```
@docs/design/sandbox-agents/12_improved_testing_guide.md
@backend/scripts/

I'm debugging [ISSUE]. Help me create a debug script that:

1. Isolates the problem
2. Has verbose logging
3. Includes cleanup
4. Shows clear pass/fail output

Issue: [DESCRIBE THE PROBLEM]
```

### Prompt 6: Pre-Commit Validation

```
@docs/design/sandbox-agents/12_improved_testing_guide.md

I'm about to commit changes. Help me:

1. Run the testing ladder
2. Fix any failures
3. Verify coverage is adequate
4. Check linting and types

Changes: [LIST MODIFIED FILES]
```

### Prompt 7: Understanding Test Failure

```
@docs/design/sandbox-agents/12_improved_testing_guide.md
@backend/tests/conftest.py

I don't understand why this test is failing:

Test: [TEST_NAME]
Error: [ERROR MESSAGE]

Help me:
1. Explain what the test is checking
2. What's the expected vs actual behavior
3. Common causes for this type of failure
4. How to fix it
```

### Prompt 8: Creating Contract Tests

```
@docs/design/sandbox-agents/05_http_api_migration.md
@docs/design/sandbox-agents/04_communication_patterns.md
@backend/tests/contract/

I need contract tests to validate API compatibility:

1. Request schemas match design docs
2. Response shapes are correct
3. Enum values are valid
4. Backward compatibility maintained

Endpoint: [ENDPOINT_NAME]
```

---

## Testing Workflows by Phase

### Phase 0-1: Infrastructure & Event Callback

```bash
# Quick validation
cd backend
pytest tests/integration/ -k "websocket or event" -v

# E2E with real sandbox
uv run python scripts/test_sandbox_simple.py
```

**Prompt:**
```
@docs/design/sandbox-agents/12_improved_testing_guide.md
@docs/design/sandbox-agents/06_implementation_checklist.md

I'm on Phase [0/1]. Validate my infrastructure:
1. WebSocket working?
2. EventBus publishing?
3. Sandbox spawning?
```

### Phase 2-3: Message Injection & Worker Scripts

```bash
# Test message injection
pytest tests/integration/sandbox/test_sandbox_messages.py -v

# Test with real SDK
uv run python scripts/test_sandbox_claude_sdk.py
```

**Prompt:**
```
@docs/design/sandbox-agents/12_improved_testing_guide.md
@backend/scripts/test_sandbox_claude_sdk.py

I'm on Phase [2/3]. Validate:
1. Messages can be injected?
2. Worker script executes correctly?
3. SDK integration works?
```

### Phase 3.5: GitHub Integration

```bash
# Test git operations
uv run python scripts/test_sandbox_git.py

# Verify full flow
uv run python scripts/verify_sandbox_flow.py
```

**Prompt:**
```
@docs/design/sandbox-agents/12_improved_testing_guide.md
@docs/design/sandbox-agents/03_git_branch_workflow.md

I'm on Phase 3.5. Validate GitHub integration:
1. OAuth token injection?
2. Repo cloning?
3. Branch creation?
```

---

## Common Issues & Fixes

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `DAYTONA_API_KEY not set` | Missing env var | Check `.env.local` |
| `Connection refused` | Server not running | Start with `uv run uvicorn...` |
| `ModuleNotFoundError` | Missing dependency | Run `uv sync` |
| `Timeout` | Sandbox slow to start | Increase timeout or check Daytona dashboard |
| `404 on endpoint` | Route not registered | Check `api/__init__.py` |
| `Fixture not found` | Missing from conftest | Add fixture or import |

---

## Testing Checklist Template

Copy this for each feature:

```markdown
## Feature: [NAME]

### Pre-Implementation
- [ ] Test file created: `tests/integration/sandbox/test_[feature].py`
- [ ] Test runs and FAILS (TDD)

### Post-Implementation
- [ ] Test PASSES
- [ ] Smoke test passes: `smoke_test.py`
- [ ] Integration tests pass: `pytest tests/integration/sandbox/ -v`
- [ ] E2E works: `test_spawner_e2e.py`

### Cleanup
- [ ] No linting errors: `ruff check backend/`
- [ ] Types check: `mypy backend/`
- [ ] Coverage adequate: `pytest --cov=omoi_os.api.routes.sandbox`
```

---

## The "Run All Tests" Master Script

This script runs all levels of the testing ladder:

```python
#!/usr/bin/env python3
"""Master test script - runs all levels of the testing ladder.

Usage:
    cd backend
    uv run python scripts/run_all_tests.py [--quick] [--skip-e2e]
"""

import subprocess
import sys
import time

def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"   Command: {' '.join(cmd)}")
    print('='*60)
    
    start = time.time()
    result = subprocess.run(cmd)
    elapsed = time.time() - start
    
    if result.returncode == 0:
        print(f"✅ PASSED in {elapsed:.1f}s")
        return True
    else:
        print(f"❌ FAILED in {elapsed:.1f}s")
        return False

def main():
    quick = "--quick" in sys.argv
    skip_e2e = "--skip-e2e" in sys.argv
    
    print("=" * 60)
    print("🪜 TESTING LADDER - Full Validation")
    print("=" * 60)
    
    results = []
    
    # Level 0: Smoke test
    results.append(("Level 0: Smoke", run_command(
        ["uv", "run", "python", "scripts/smoke_test.py"],
        "Smoke Test"
    )))
    
    if not results[-1][1]:
        print("\n❌ Smoke test failed - fix before continuing")
        sys.exit(1)
    
    # Level 1: Unit tests
    results.append(("Level 1: Unit", run_command(
        ["pytest", "tests/unit/", "-v", "--maxfail=1"],
        "Unit Tests"
    )))
    
    # Level 2: Integration tests
    results.append(("Level 2: Integration", run_command(
        ["pytest", "tests/integration/sandbox/", "-v", "--maxfail=1"],
        "Integration Tests"
    )))
    
    # Level 3: E2E (optional)
    if not skip_e2e and not quick:
        results.append(("Level 3: E2E", run_command(
            ["uv", "run", "python", "scripts/test_spawner_e2e.py"],
            "E2E Tests"
        )))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TESTING LADDER RESULTS")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"   {status} {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
```

---

## Summary

**The Testing Ladder:**
1. **Smoke** (30s) → Quick sanity check
2. **Unit** (1-2min) → Logic validation
3. **Integration** (2-5min) → API/service tests
4. **E2E** (5-15min) → Real sandbox validation
5. **Full** (15-30min) → Everything

**Key Commands:**
```bash
# Quick validation (Levels 0-2)
cd backend && uv run python scripts/smoke_test.py && pytest tests/integration/sandbox/ -v --maxfail=1

# Full validation (All levels)
cd backend && uv run python scripts/run_all_tests.py

# Before commit
cd backend && uv run python scripts/run_all_tests.py --skip-e2e
```

**When tests fail:**
1. Read the error message
2. Use the debug prompt
3. Fix the root cause
4. Re-run the failed level
5. Continue up the ladder

---

## Related Documents

- [Development Workflow](./10_development_workflow.md) - Implementation guide
- [Testing Workflows](./11_testing_workflows.md) - Detailed testing strategies  
- [Implementation Checklist](./06_implementation_checklist.md) - Phase-by-phase guide
- [HTTP API Migration](./05_http_api_migration.md) - API endpoint reference
