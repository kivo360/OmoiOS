# Testing Workflows & Prompts

**Created**: 2025-12-12  
**Purpose**: Comprehensive testing strategies, workflows, and AI prompts for validating the sandbox agents system  
**Related**: [Development Workflow](./10_development_workflow.md) | [Implementation Checklist](./06_implementation_checklist.md)

---

## Overview

This document provides:
1. **Testing Pyramid Strategy** - Unit → Integration → E2E → Manual
2. **Script-Based Testing** - Fast iteration for manual validation
3. **Improved AI Prompts** - Context-aware prompts for different testing scenarios
4. **Test Execution Workflows** - When to use which type of test

---

## Testing Pyramid

```
┌─────────────────────────────────────────────────────────────┐
│                    TESTING PYRAMID                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                        MANUAL                               │
│                   (Scripts in /scripts)                      │
│                  ────────────────────                        │
│                                                             │
│                    E2E TESTS                                │
│            (Full flow with real sandboxes)                  │
│                  ────────────────────                        │
│                                                             │
│                 INTEGRATION TESTS                           │
│         (API endpoints, services, mocks)                    │
│                  ────────────────────                        │
│                                                             │
│                    UNIT TESTS                               │
│              (Fast, isolated, no I/O)                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### When to Use Each Level

| Level | Use For | Speed | Isolation | Cost |
|-------|---------|-------|-----------|------|
| **Unit** | Logic validation, edge cases | ⚡ Fast | ✅ High | 💰 Free |
| **Integration** | API contracts, service interactions | 🚀 Medium | ⚠️ Medium | 💰 Low |
| **E2E** | Full user flows, real sandboxes | 🐌 Slow | ❌ Low | 💰💰 High |
| **Manual** | Exploratory, debugging, demos | 🐌 Slow | ❌ None | 💰💰💰 Very High |

---

## Testing Workflows

### Workflow 1: Fast Development Loop (Unit + Integration)

**Use this for**: Implementing new features, fixing bugs

```bash
# 1. Write unit test first
pytest tests/unit/test_sandbox_service.py::test_create_sandbox -v

# 2. Implement feature
# ... edit code ...

# 3. Run unit test (should pass)
pytest tests/unit/test_sandbox_service.py::test_create_sandbox -v

# 4. Run integration test
pytest tests/integration/sandbox/test_event_callback.py -v

# 5. Run all related tests
pytest tests/ -k "sandbox" -v --maxfail=1
```

**AI Prompt**:
```
@docs/design/sandbox-agents/11_testing_workflows.md
@backend/omoi_os/services/daytona_spawner.py
@backend/tests/unit/

I'm implementing a new feature in DaytonaSpawnerService. Help me:

1. Write a unit test first (fast, no I/O)
2. Then write an integration test (with mocks)
3. Show me the pytest commands to run both

Feature: [DESCRIBE YOUR FEATURE]
```

---

### Workflow 2: API Contract Validation (Integration)

**Use this for**: Validating HTTP endpoints match design docs

```bash
# 1. Run contract tests
pytest tests/integration/sandbox/test_event_callback.py::test_endpoint_exists_and_accepts_valid_event -v

# 2. Check API schema matches design
pytest tests/contract/test_sandbox_api_contract.py -v

# 3. Validate request/response shapes
pytest tests/integration/sandbox/ -k "contract" -v
```

**AI Prompt**:
```
@docs/design/sandbox-agents/05_http_api_migration.md
@docs/design/sandbox-agents/04_communication_patterns.md
@backend/tests/integration/sandbox/test_event_callback.py

I need to validate that my API implementation matches the design docs:

1. Check that POST /api/v1/sandbox/{id}/events matches the schema in communication_patterns.md
2. Verify request/response shapes are correct
3. Add contract tests if missing

Show me what to check and how to fix any mismatches.
```

---

### Workflow 3: E2E Flow Validation (Scripts + E2E Tests)

**Use this for**: Validating complete flows work end-to-end

```bash
# Option A: Use script for quick manual validation
cd backend
uv run python scripts/test_spawner_e2e.py

# Option B: Run E2E pytest (slower, more thorough)
pytest tests/e2e/test_sandbox_lifecycle.py -v --slow

# Option C: Run specific E2E scenario
pytest tests/e2e/test_sandbox_lifecycle.py::test_complete_task_flow -v
```

**AI Prompt**:
```
@docs/design/sandbox-agents/11_testing_workflows.md
@backend/scripts/test_spawner_e2e.py
@backend/tests/e2e/

I need to test the complete sandbox lifecycle:

1. Spawn sandbox
2. Agent executes task
3. Events are reported back
4. Messages can be injected
5. Sandbox cleans up

Help me:
- Create/update the E2E test script
- Add assertions for each step
- Show me how to run it

Should I use the script approach or pytest E2E?
```

---

### Workflow 4: Manual Exploration & Debugging (Scripts)

**Use this for**: Debugging issues, exploring behavior, demos

```bash
# 1. Start backend server
cd backend
uv run uvicorn omoi_os.main:app --reload --port 8000

# 2. In another terminal, run exploration script
uv run python scripts/test_sandbox_simple.py

# 3. Or use interactive script
uv run python scripts/debug_sandbox_flow.py --interactive
```

**AI Prompt**:
```
@backend/scripts/
@docs/design/sandbox-agents/11_testing_workflows.md

I'm debugging an issue where sandbox events aren't being received. Help me:

1. Create a debug script that:
   - Spawns a sandbox
   - Waits for events
   - Prints all received events with timestamps
   - Shows network errors if any

2. Make it easy to run: `uv run python scripts/debug_sandbox_events.py`

3. Include verbose logging to see what's happening
```

---

## Script-Based Testing Strategy

### Script Categories

Scripts in `backend/scripts/` serve different purposes:

| Script Type | Purpose | Example |
|-------------|---------|---------|
| **Quick Validation** | Fast smoke tests | `test_sandbox_simple.py` |
| **E2E Flow** | Complete lifecycle | `test_spawner_e2e.py` |
| **SDK Testing** | Validate SDK integration | `test_sandbox_claude_sdk.py` |
| **Debugging** | Investigate issues | `debug_sandbox_flow.py` |
| **API Testing** | Test HTTP endpoints | `test_api_sandbox_spawn.py` |

### Script Template

```python
#!/usr/bin/env python3
"""Test: [DESCRIPTION]

Tests:
1. [Test case 1]
2. [Test case 2]
3. [Test case 3]

Usage:
    cd backend
    uv run python scripts/[script_name].py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env.local")


async def main():
    print("=" * 60)
    print("🧪 [TEST NAME]")
    print("=" * 60)
    
    # Setup
    # ... create services, check env vars ...
    
    try:
        # Test 1
        print("\n📋 Test 1: [Description]")
        # ... test code ...
        print("✅ Test 1 passed")
        
        # Test 2
        print("\n📋 Test 2: [Description]")
        # ... test code ...
        print("✅ Test 2 passed")
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
```

**AI Prompt**:
```
@docs/design/sandbox-agents/11_testing_workflows.md
@backend/scripts/test_spawner_e2e.py

I need to create a new test script for [FEATURE]. Help me:

1. Use the script template from the testing workflows doc
2. Follow the pattern from test_spawner_e2e.py
3. Include proper error handling and cleanup
4. Make it easy to run with clear output

Feature to test: [DESCRIBE]
```

---

## Improved AI Prompts by Scenario

### Scenario 1: Writing Tests for New Feature

```
@docs/design/sandbox-agents/06_implementation_checklist.md
@docs/design/sandbox-agents/11_testing_workflows.md
@backend/tests/integration/sandbox/test_event_callback.py

I'm implementing [FEATURE_NAME] from Phase [X]. Help me:

1. Write the test FIRST (test-driven approach)
   - Unit test for the service logic
   - Integration test for the API endpoint
   - Use existing fixtures from conftest.py

2. Show me the pytest command to run the test

3. After I implement, help me verify the test passes

Feature: [DESCRIBE THE FEATURE]
```

---

### Scenario 2: Debugging Failing Test

```
@backend/tests/integration/sandbox/test_[test_file].py
@docs/design/sandbox-agents/11_testing_workflows.md

My test is failing. Here's the error:

[PASTE ERROR OUTPUT]

Help me:
1. Understand what the test is trying to do
2. Identify why it's failing
3. Fix the issue (code or test)
4. Verify the fix works

Test: [TEST_NAME]
```

---

### Scenario 3: Adding Test Coverage

```
@docs/design/sandbox-agents/11_testing_workflows.md
@backend/tests/integration/sandbox/
@backend/omoi_os/api/routes/sandbox.py

I need to improve test coverage for the sandbox routes. Help me:

1. Identify gaps in current test coverage
2. Write tests for edge cases:
   - Invalid sandbox IDs
   - Missing authentication
   - Network timeouts
   - Concurrent requests
3. Add tests for error handling paths

Show me what's missing and how to add it.
```

---

### Scenario 4: Validating E2E Flow

```
@docs/design/sandbox-agents/11_testing_workflows.md
@backend/scripts/test_spawner_e2e.py
@docs/design/sandbox-agents/01_architecture.md

I want to validate the complete E2E flow works:

1. User creates task → Sandbox spawned
2. Worker starts → Reports AGENT_STARTED
3. Worker executes → Reports TOOL_CALL events
4. User intervenes → Message injected
5. Worker completes → Reports TASK_COMPLETED
6. Sandbox cleaned up

Help me:
- Create/update E2E test script
- Add assertions for each step
- Show me how to run it
- What to look for in the output
```

---

### Scenario 5: Testing HTTP API Migration

```
@docs/design/sandbox-agents/05_http_api_migration.md
@docs/design/sandbox-agents/11_testing_workflows.md
@backend/omoi_os/api/routes/

I'm testing the HTTP API migration. Help me:

1. Create tests that verify each MCP tool has an HTTP equivalent
2. Test that the HTTP endpoints match the design doc schemas
3. Validate request/response formats
4. Test error handling

Focus on: [TICKETS | TASKS | DISCOVERY | etc.]
```

---

### Scenario 6: Performance Testing

```
@docs/design/sandbox-agents/11_testing_workflows.md
@backend/scripts/

I need to test performance of the sandbox system:

1. Create a script that:
   - Spawns multiple sandboxes concurrently
   - Measures spawn time
   - Tracks event throughput
   - Monitors resource usage

2. Help me interpret the results

3. Identify bottlenecks

Show me how to create a performance test script.
```

---

### Scenario 7: Contract Testing

```
@docs/design/sandbox-agents/04_communication_patterns.md
@docs/design/sandbox-agents/11_testing_workflows.md
@backend/tests/contract/

I need contract tests to ensure API compatibility:

1. Validate request schemas match design docs
2. Validate response schemas
3. Test backward compatibility
4. Check enum values are correct

Help me create contract tests for the sandbox API.
```

---

## Test Execution Commands

### Quick Reference

```bash
# Unit tests (fast)
pytest tests/unit/ -v

# Integration tests (medium speed)
pytest tests/integration/sandbox/ -v

# E2E tests (slow, requires real sandboxes)
pytest tests/e2e/ -v --slow

# Specific test file
pytest tests/integration/sandbox/test_event_callback.py -v

# Specific test
pytest tests/integration/sandbox/test_event_callback.py::test_endpoint_exists_and_accepts_valid_event -v

# Run with coverage
pytest tests/integration/sandbox/ -v --cov=omoi_os.api.routes.sandbox --cov-report=html

# Run with markers
pytest tests/ -v -m "integration and not slow"

# Run until first failure (fast feedback)
pytest tests/integration/sandbox/ -v --maxfail=1

# Run with verbose output
pytest tests/integration/sandbox/ -v -s

# Run script-based test
cd backend && uv run python scripts/test_spawner_e2e.py
```

---

## Test Organization

### Directory Structure

```
backend/
├── tests/
│   ├── unit/                    # Fast, isolated tests
│   │   └── test_sandbox_service.py
│   ├── integration/             # API, service integration
│   │   └── sandbox/
│   │       ├── test_event_callback.py
│   │       ├── test_sandbox_messages.py
│   │       └── test_worker_integration.py
│   ├── e2e/                     # Full flow tests
│   │   └── test_sandbox_lifecycle.py
│   └── contract/                # API contract tests
│       └── test_sandbox_api_contract.py
└── scripts/                     # Manual/exploratory tests
    ├── test_spawner_e2e.py
    ├── test_sandbox_claude_sdk.py
    └── debug_sandbox_flow.py
```

---

## Test Fixtures & Utilities

### Common Fixtures (conftest.py)

```python
# backend/tests/conftest.py

@pytest.fixture
def client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient
    from omoi_os.main import app
    return TestClient(app)

@pytest.fixture
def sample_sandbox_event():
    """Sample sandbox event payload."""
    return {
        "event_type": "TOOL_CALL",
        "payload": {
            "tool": "bash",
            "command": "echo hello",
        },
    }

@pytest.fixture
def mock_sandbox():
    """Mock sandbox for testing."""
    # ... mock implementation ...
```

**AI Prompt**:
```
@backend/tests/conftest.py
@docs/design/sandbox-agents/11_testing_workflows.md

I need a new fixture for [PURPOSE]. Help me:

1. Add it to conftest.py following existing patterns
2. Make it reusable across tests
3. Include proper cleanup

Fixture purpose: [DESCRIBE]
```

---

## Continuous Testing Workflow

### Pre-Commit Checklist

```bash
# 1. Run unit tests (fast)
pytest tests/unit/ -v --maxfail=1

# 2. Run integration tests (medium)
pytest tests/integration/sandbox/ -v --maxfail=1

# 3. Check linting
ruff check backend/omoi_os/

# 4. Check types
mypy backend/omoi_os/

# 5. Run relevant script test
uv run python scripts/test_sandbox_simple.py
```

**AI Prompt**:
```
@docs/design/sandbox-agents/11_testing_workflows.md

Before committing, help me:

1. Run the pre-commit test checklist
2. Fix any failures
3. Verify everything passes

Show me the commands and what to check.
```

---

## Debugging Test Failures

### Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| **Fixture not found** | `FixtureNotFoundError` | Check fixture is in `conftest.py` or test file |
| **Import error** | `ModuleNotFoundError` | Check `sys.path` includes backend directory |
| **Database not initialized** | `OperationalError` | Run database migrations or use test DB |
| **Redis not running** | `ConnectionRefusedError` | Start Redis or use mock |
| **Sandbox timeout** | `TimeoutError` | Increase timeout or check Daytona API key |
| **Event not received** | Test waits forever | Check EventBus subscription, add timeout |

**AI Prompt**:
```
@docs/design/sandbox-agents/11_testing_workflows.md
@backend/tests/integration/sandbox/test_[test_file].py

My test is failing with: [ERROR MESSAGE]

Help me:
1. Identify the root cause using the debugging guide
2. Check common issues table
3. Fix the issue
4. Verify the fix

Test: [TEST_NAME]
Error: [FULL ERROR]
```

---

## Test Data Management

### Test Sandboxes

For E2E tests that need real sandboxes:

```python
# Use ephemeral sandboxes for tests
sandbox = daytona.create(
    params=CreateSandboxFromImageParams(
        image="python:3.12-slim",
        ephemeral=True,  # Auto-delete after test
        labels={"test": "integration"},
    ),
    timeout=120,
)

# Always cleanup in finally block
try:
    # ... test code ...
finally:
    if sandbox:
        daytona.delete(sandbox)
```

**AI Prompt**:
```
@docs/design/sandbox-agents/11_testing_workflows.md
@backend/scripts/test_spawner_e2e.py

I need to manage test sandboxes properly:

1. Use ephemeral sandboxes for tests
2. Always cleanup in finally blocks
3. Handle cleanup errors gracefully
4. Add timeout handling

Show me the best practices for test sandbox management.
```

---

## Performance Testing

### Load Testing Script Template

```python
#!/usr/bin/env python3
"""Load test: Spawn multiple sandboxes concurrently."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

async def spawn_and_test(sandbox_id: int):
    """Spawn one sandbox and run test."""
    # ... spawn sandbox ...
    # ... run test ...
    # ... cleanup ...
    return {"sandbox_id": sandbox_id, "duration": duration}

async def main():
    num_sandboxes = 10
    start_time = time.time()
    
    results = await asyncio.gather(*[
        spawn_and_test(i) for i in range(num_sandboxes)
    ])
    
    total_time = time.time() - start_time
    avg_time = total_time / num_sandboxes
    
    print(f"✅ Spawned {num_sandboxes} sandboxes in {total_time:.1f}s")
    print(f"   Average: {avg_time:.1f}s per sandbox")
```

**AI Prompt**:
```
@docs/design/sandbox-agents/11_testing_workflows.md

I need to test system performance:

1. Create a load test script
2. Test concurrent sandbox spawning
3. Measure event throughput
4. Identify bottlenecks

Help me create a performance test script.
```

---

## Test Reporting

### Generate Test Reports

```bash
# HTML coverage report
pytest tests/integration/sandbox/ --cov=omoi_os.api.routes.sandbox --cov-report=html
open htmlcov/index.html

# JSON report for CI
pytest tests/ --json-report --json-report-file=test_report.json

# JUnit XML for CI
pytest tests/ --junitxml=test_results.xml
```

**AI Prompt**:
```
@docs/design/sandbox-agents/11_testing_workflows.md

I need to generate test reports:

1. Coverage report (HTML)
2. Test results (JSON/XML for CI)
3. Performance metrics

Show me how to generate and interpret these reports.
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Test Sandbox System

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: |
          cd backend
          uv sync
          pytest tests/unit/ tests/integration/sandbox/ -v --cov
```

**AI Prompt**:
```
@docs/design/sandbox-agents/11_testing_workflows.md

I need to set up CI/CD testing:

1. Run unit and integration tests on PR
2. Skip E2E tests (too slow/expensive)
3. Generate coverage reports
4. Fail fast on errors

Help me create a GitHub Actions workflow.
```

---

## Summary: Testing Decision Tree

```
┌─────────────────────────────────────────────────────────────┐
│                    TESTING DECISION TREE                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  What are you testing?                                      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Logic/Algorithm?                                    │   │
│  │ → Unit Test (pytest tests/unit/)                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ API Endpoint?                                        │   │
│  │ → Integration Test (pytest tests/integration/)      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Full User Flow?                                     │   │
│  │ → E2E Test (pytest tests/e2e/)                      │   │
│  │   OR Script (backend/scripts/)                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Debugging/Exploring?                                │   │
│  │ → Script (backend/scripts/)                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Reference: Testing Commands

```bash
# Fast feedback loop
pytest tests/unit/ tests/integration/sandbox/ -v --maxfail=1

# Full integration suite
pytest tests/integration/sandbox/ -v

# E2E validation
pytest tests/e2e/ -v --slow

# Manual exploration
cd backend && uv run python scripts/test_spawner_e2e.py

# Coverage report
pytest tests/integration/sandbox/ --cov=omoi_os.api.routes.sandbox --cov-report=html

# Debug specific test
pytest tests/integration/sandbox/test_event_callback.py::test_endpoint_exists_and_accepts_valid_event -v -s
```

---

## Related Documents

- [Development Workflow](./10_development_workflow.md) - Implementation guide
- [Implementation Checklist](./06_implementation_checklist.md) - Test specifications
- [HTTP API Migration](./05_http_api_migration.md) - API endpoint reference
- [Communication Patterns](./04_communication_patterns.md) - API schemas

---

## Next Steps

1. **Start with unit tests** - Fast feedback for logic
2. **Add integration tests** - Validate API contracts
3. **Create E2E scripts** - Validate full flows
4. **Use manual scripts** - For debugging and exploration

Remember: **Test first, implement second, validate third!**
