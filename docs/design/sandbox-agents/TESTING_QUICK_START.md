# Testing Quick Start Guide

**Quick reference for testing the sandbox agents system**

---

## 🚀 Quick Commands

### Fast Feedback Loop (Development)

```bash
# Run unit + integration tests (fast)
cd backend
pytest tests/unit/ tests/integration/sandbox/ -v --maxfail=1

# Run specific test
pytest tests/integration/sandbox/test_event_callback.py::test_endpoint_exists_and_accepts_valid_event -v

# Run with coverage
pytest tests/integration/sandbox/ --cov=omoi_os.api.routes.sandbox --cov-report=html
```

### Script-Based Testing (Manual Validation)

```bash
# E2E flow test
cd backend
uv run python scripts/test_spawner_e2e.py

# Claude SDK test
uv run python scripts/test_sandbox_claude_sdk.py

# Simple smoke test
uv run python scripts/test_sandbox_simple.py
```

### Full Test Suite

```bash
# All integration tests
pytest tests/integration/sandbox/ -v

# E2E tests (slow, requires real sandboxes)
pytest tests/e2e/ -v --slow

# All tests with markers
pytest tests/ -v -m "integration and not slow"
```

---

## 📋 Testing Decision Tree

**What are you testing?**

- **Logic/Algorithm?** → `pytest tests/unit/`
- **API Endpoint?** → `pytest tests/integration/sandbox/`
- **Full User Flow?** → `pytest tests/e2e/` OR `scripts/test_*.py`
- **Debugging?** → `scripts/debug_*.py`

---

## 🎯 Common Testing Scenarios

### Scenario 1: Testing New Feature

```bash
# 1. Write test first
pytest tests/integration/sandbox/test_new_feature.py -v  # Should fail

# 2. Implement feature
# ... edit code ...

# 3. Run test again
pytest tests/integration/sandbox/test_new_feature.py -v  # Should pass

# 4. Run all related tests
pytest tests/ -k "sandbox" -v --maxfail=1
```

### Scenario 2: Debugging Failing Test

```bash
# Run with verbose output
pytest tests/integration/sandbox/test_event_callback.py::test_name -v -s

# Run with debugger
pytest tests/integration/sandbox/test_event_callback.py::test_name --pdb
```

### Scenario 3: Manual E2E Validation

```bash
# Terminal 1: Start server
cd backend
uv run uvicorn omoi_os.main:app --reload --port 8000

# Terminal 2: Run E2E script
cd backend
uv run python scripts/test_spawner_e2e.py
```

---

## 📚 Documentation

- **[Testing Workflows](./11_testing_workflows.md)** - Comprehensive testing guide
- **[Development Workflow](./10_development_workflow.md)** - Implementation guide
- **[Implementation Checklist](./06_implementation_checklist.md)** - Test specifications

---

## 🔧 Test Organization

```
backend/
├── tests/
│   ├── unit/              # Fast, isolated
│   ├── integration/       # API, services
│   ├── e2e/              # Full flows
│   └── contract/         # API contracts
└── scripts/              # Manual/exploratory
    ├── test_spawner_e2e.py
    ├── test_sandbox_claude_sdk.py
    └── debug_*.py
```

---

## 💡 Pro Tips

1. **Test First** - Write tests before implementation
2. **Fast Feedback** - Use `--maxfail=1` to stop on first failure
3. **Use Scripts** - For manual validation and debugging
4. **Check Coverage** - Run with `--cov` to see what's tested
5. **Read Docs** - See [11_testing_workflows.md](./11_testing_workflows.md) for details

---

## 🆘 Need Help?

Use these AI prompts:

```
@docs/design/sandbox-agents/11_testing_workflows.md
@docs/design/sandbox-agents/TESTING_QUICK_START.md

[DESCRIBE YOUR TESTING NEED]
```
