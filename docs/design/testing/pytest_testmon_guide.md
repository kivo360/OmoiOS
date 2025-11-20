# Pytest-Testmon Usage Guide

**Status**: Active
**Related**: docs/testing/pytest_guide.md, docs/testing/ci_cd_testing.md, docs/testing/testmon_adr.md

---


**Created**: 2025-11-20
**Purpose**: Complete guide to using pytest-testmon for intelligent test execution

---

## What is Pytest-Testmon?

Pytest-testmon tracks which tests depend on which parts of your code. It only runs tests that are affected by your changes, dramatically reducing test execution time during development.

**Key Features**:
- Tracks test-to-code dependencies
- Only runs affected tests after code changes
- Persists data between runs
- Works with pytest-xdist for parallel execution
- Integrates with CI/CD pipelines

---

## Installation

```bash
# Add to test dependencies
uv add --group test pytest-testmon

# Install with other recommended plugins
uv add --group test pytest-xdist pytest-sugar pytest-timeout
```

---

## Basic Usage

### First Run (Baseline Collection)

```bash
# Initial run: Collect all test dependencies
uv run pytest --testmon

# Output:
# ===== 245 passed in 180.23s =====
# testmon: 245 tests affected by changes since last successful execution
```

This creates `.testmondata` file tracking all dependencies.

### Subsequent Runs (Smart Execution)

```bash
# Make a code change
echo "# Updated" >> omoi_os/services/task_queue.py

# Run again: Only affected tests execute
uv run pytest --testmon

# Output:
# ===== 12 passed, 233 deselected in 8.45s =====
# testmon: 12 tests affected by changes
```

**Result**: ~95% time savings! 🚀

---

## Common Commands

### Development Workflow

```bash
# 1. Quick feedback (stop on first failure)
uv run pytest --testmon -x

# 2. Only changed tests
uv run pytest --testmon

# 3. Show which tests would run (dry-run)
uv run pytest --testmon --collect-only

# 4. Disable testmon (run all tests)
uv run pytest --no-testmon

# 5. Clear testmon cache and rebuild
uv run pytest --testmon-nocache

# 6. Run failed tests only
uv run pytest --lf --testmon

# 7. Run last failed, then all affected
uv run pytest --lf --testmon --ff
```

### Category-Specific Testing

```bash
# Unit tests with testmon
uv run pytest tests/unit/ --testmon

# Integration tests with testmon
uv run pytest tests/integration/ --testmon

# Marked tests with testmon
uv run pytest -m "unit and not slow" --testmon

# Critical path only
uv run pytest -m critical --testmon
```

### Parallel Execution

```bash
# Run affected tests in parallel
uv run pytest --testmon -n auto

# Limit to 4 workers
uv run pytest --testmon -n 4

# Parallel with coverage
uv run pytest --testmon -n auto --cov
```

---

## Advanced Features

### 1. Selective Test Execution

```bash
# Run only tests that touch specific module
uv run pytest --testmon tests/ -k task_queue

# Run only tests in specific directory
uv run pytest --testmon tests/unit/services/

# Combine with markers
uv run pytest --testmon -m "integration and requires_db"
```

### 2. Coverage Integration

```bash
# Testmon + coverage (only cover affected tests)
uv run pytest --testmon --cov=omoi_os --cov-report=html

# Full coverage (ignore testmon)
uv run pytest --no-testmon --cov=omoi_os --cov-report=html
```

### 3. Debugging with Testmon

```bash
# Run affected tests with debugger
uv run pytest --testmon --pdb

# Verbose output for affected tests
uv run pytest --testmon -vv

# Show which code changes triggered which tests
uv run pytest --testmon --collect-only -v
```

### 4. Reset and Rebuild

```bash
# Clear all testmon data
rm -rf .testmondata

# Rebuild from scratch
uv run pytest --testmon

# Or use --testmon-nocache flag
uv run pytest --testmon-nocache
```

---

## CI/CD Integration

### Strategy 1: Incremental Testing (PRs)

```yaml
# .github/workflows/test-pr.yml
name: PR Tests

on: pull_request

jobs:
  test-changed:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Need full history
      
      - name: Get base branch testmon data
        uses: actions/cache/restore@v3
        with:
          path: .testmondata
          key: testmon-${{ github.base_ref }}
      
      - name: Setup Python & Install
        # ... setup steps ...
      
      - name: Run affected tests only
        run: uv run pytest --testmon --cov
      
      - name: Save testmon data
        uses: actions/cache/save@v3
        if: success()
        with:
          path: .testmondata
          key: testmon-${{ github.head_ref }}-${{ github.sha }}
```

### Strategy 2: Full Testing (Main Branch)

```yaml
# .github/workflows/test-main.yml
name: Main Tests

on:
  push:
    branches: [main]

jobs:
  test-full:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup & Install
        # ... setup steps ...
      
      - name: Run all tests (no testmon)
        run: uv run pytest --no-testmon --cov
      
      - name: Build fresh testmon cache
        run: uv run pytest --testmon-nocache
      
      - name: Save testmon baseline
        uses: actions/cache/save@v3
        with:
          path: .testmondata
          key: testmon-main-${{ github.sha }}
```

### Strategy 3: Hybrid Approach

```yaml
# .github/workflows/test-hybrid.yml
name: Hybrid Tests

on: [push, pull_request]

jobs:
  quick-check:
    name: Quick Check (Affected Tests)
    runs-on: ubuntu-latest
    
    steps:
      - name: Restore testmon cache
        uses: actions/cache/restore@v3
        with:
          path: .testmondata
          key: testmon-${{ github.base_ref }}
      
      - name: Run affected tests
        run: uv run pytest --testmon -n auto
      
      - name: Cache results
        uses: actions/cache/save@v3
        with:
          path: .testmondata
          key: testmon-${{ github.sha }}
  
  full-suite:
    name: Full Suite (Nightly)
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' || contains(github.event.head_commit.message, '[full-test]')
    
    steps:
      - name: Run all tests
        run: uv run pytest --no-testmon --cov
```

---

## Testmon Data Management

### What is .testmondata?

The `.testmondata` file is a SQLite database that tracks:
- Which source files each test depends on
- Which tests passed/failed
- Code coverage per test
- Test execution times

### Size and Performance

```bash
# Check testmon data size
ls -lh .testmondata

# Typical size: 1-10 MB for 200-500 tests
# Performance impact: Negligible (< 100ms overhead)
```

### When to Clear

Clear testmon data when:
- Major refactoring changes many files
- Moving/renaming many test files
- Seeing incorrect test selection
- After merging large branches

```bash
# Clear and rebuild
rm .testmondata
uv run pytest --testmon
```

### Backup and Restore

```bash
# Backup before major changes
cp .testmondata .testmondata.backup

# Restore if needed
cp .testmondata.backup .testmondata
```

---

## Integration with Reorganized Test Structure

### Directory-Specific Testing

```bash
# Unit tests only (fast feedback)
uv run pytest tests/unit/ --testmon -n auto

# Integration tests
uv run pytest tests/integration/ --testmon

# E2E tests (slow, rarely needed)
uv run pytest tests/e2e/ --testmon

# Performance tests
uv run pytest tests/performance/ --testmon --benchmark-only
```

### Marker-Based Testing

```bash
# Run only unit tests, skip slow ones
uv run pytest -m "unit and not slow" --testmon

# Critical path tests only
uv run pytest -m critical --testmon -x

# Tests that need database
uv run pytest -m requires_db --testmon

# Tests that DON'T need Redis (faster)
uv run pytest -m "not requires_redis" --testmon
```

---

## Performance Comparison

### Without Testmon

```bash
# Every change requires full test suite
$ uv run pytest
===== 245 passed in 180.23s =====

# Change one service file
$ echo "# comment" >> omoi_os/services/task_queue.py

# Must run all tests again
$ uv run pytest
===== 245 passed in 182.45s =====
```

**Time per iteration**: ~3 minutes

### With Testmon

```bash
# First run: Build dependency graph
$ uv run pytest --testmon
===== 245 passed in 185.67s =====

# Change one service file
$ echo "# comment" >> omoi_os/services/task_queue.py

# Only affected tests run
$ uv run pytest --testmon
===== 12 passed, 233 deselected in 8.34s =====
```

**Time per iteration**: ~8 seconds (95% savings!)

### Real-World Scenarios

| Scenario | Without Testmon | With Testmon | Savings |
|----------|----------------|--------------|---------|
| Change 1 service | 180s | 8s | 95% |
| Change 1 model | 180s | 25s | 86% |
| Change multiple services | 180s | 45s | 75% |
| No changes | 180s | 1s | 99% |
| New test file | 180s | 180s | 0% (expected) |

---

## Best Practices

### 1. Commit Testmon Data to Git (Optional)

```bash
# Option A: Commit for team benefit
git add .testmondata
git commit -m "Update testmon dependency graph"

# Option B: Gitignore (regenerate per developer)
echo ".testmondata" >> .gitignore
```

**Recommendation**: Gitignore it. Each developer builds their own graph.

### 2. Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "🧪 Running affected tests..."
uv run pytest --testmon -x -q

if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Fix before committing."
    exit 1
fi

echo "✅ All affected tests passed!"
```

### 3. Make Targets

```makefile
# Makefile

.PHONY: test-quick test-full test-unit test-integration

# Quick feedback loop
test-quick:
	uv run pytest --testmon -x -n auto

# Full test suite
test-full:
	uv run pytest --no-testmon --cov

# Category-specific
test-unit:
	uv run pytest tests/unit/ --testmon -n auto

test-integration:
	uv run pytest tests/integration/ --testmon

test-e2e:
	uv run pytest tests/e2e/ --testmon

# Rebuild testmon cache
test-rebuild:
	rm -f .testmondata
	uv run pytest --testmon

# Watch mode (requires pytest-watch)
test-watch:
	uv run ptw -- --testmon -x
```

### 4. VSCode Integration

```json
// .vscode/settings.json
{
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "--testmon",
    "-v",
    "tests"
  ],
  "python.testing.autoTestDiscoverOnSaveEnabled": true
}
```

---

## Troubleshooting

### Tests Always Run (Testmon Not Working)

```bash
# Check if testmon is active
uv run pytest --testmon --collect-only | grep testmon

# Verify .testmondata exists
ls -la .testmondata

# Check pytest version compatibility
uv run pytest --version
```

### Wrong Tests Selected

```bash
# Rebuild dependency graph
uv run pytest --testmon-nocache

# Or delete and rebuild
rm .testmondata
uv run pytest --testmon
```

### Testmon + Coverage Issues

```bash
# Run testmon without coverage for speed
uv run pytest --testmon

# Run full coverage periodically
uv run pytest --no-testmon --cov
```

### CI Cache Not Working

```yaml
# Ensure fetch-depth: 0 for full git history
- uses: actions/checkout@v4
  with:
    fetch-depth: 0

# Use correct cache key
- uses: actions/cache@v3
  with:
    path: .testmondata
    key: testmon-${{ runner.os }}-${{ github.sha }}
    restore-keys: |
      testmon-${{ runner.os }}-
```

---

## Expected Results

### After Implementation

**Development Speed**:
- ✅ 80-95% faster test feedback loop
- ✅ Run only 5-20 tests instead of 200-500
- ✅ Results in seconds, not minutes

**CI/CD Speed**:
- ✅ 50-70% faster PR checks (with caching)
- ✅ Still run full suite on main branch
- ✅ Parallel execution with -n auto

**Developer Experience**:
- ✅ Faster iterations
- ✅ More frequent testing
- ✅ Reduced context switching
- ✅ Confident refactoring

---

This guide provides everything needed to effectively use pytest-testmon for intelligent test execution.

