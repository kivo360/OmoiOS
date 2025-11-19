# Intelligent Monitoring System Testing Guide

This guide explains how to test the intelligent monitoring system that has been integrated into your OmoiOS project.

## 🧪 Testing Strategy

The intelligent monitoring system includes comprehensive testing at multiple levels:

### 1. Unit Tests (`tests/test_intelligent_monitoring.py`)
- **Individual component testing** with mocks
- **Edge case handling** and error conditions
- **Fast, isolated tests** for each service

### 2. Integration Tests (`test_intelligent_monitoring.py`)
- **End-to-end workflow testing**
- **Service interaction validation**
- **Event publishing verification**

### 3. Smoke Tests (`scripts/test_intelligent_monitoring.py`)
- **Real database testing**
- **Live system validation**
- **Production readiness checking**

## 🚀 Quick Start Testing

### 1. Run the Database Migration

First, ensure the intelligent monitoring tables are created:

```bash
# Run the migration to add intelligent monitoring tables
uv run alembic upgrade head
```

### 2. Run Unit Tests

```bash
# Run all intelligent monitoring tests
uv run pytest tests/test_intelligent_monitoring.py -v

# Run specific test classes
uv run pytest tests/test_intelligent_monitoring.py::TestAgentOutputCollector -v
uv run pytest tests/test_intelligent_monitoring.py::TestTrajectoryContext -v
uv run pytest tests/test_intelligent_monitoring.py::TestIntelligentGuardian -v
uv run pytest tests/test_intelligent_monitoring.py::TestConductorService -v
uv run pytest tests/test_intelligent_monitoring.py::TestMonitoringLoop -v
```

### 3. Run Smoke Tests (Real Database)

```bash
# Make the script executable
chmod +x scripts/test_intelligent_monitoring.py

# Run smoke tests against your actual database
uv run python scripts/test_intelligent_monitoring.py
```

### 4. Run API Integration Tests

```bash
# Start the API server
uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 18000 --reload

# In another terminal, test the monitoring endpoints
curl -X GET "http://localhost:18000/board/wip-violations"
curl -X POST "http://localhost:18000/tickets/detect-blocking"
```

## 📊 Test Coverage Areas

### ✅ AgentOutputCollector Tests
- [x] Database log retrieval
- [x] Workspace file scanning
- [x] Event logging and publishing
- [x] Active agent detection
- [x] Responsiveness checking

### ✅ TrajectoryContext Tests
- [x] Accumulated context building
- [x] Constraint extraction and tracking
- [x] Reference resolution
- [x] Phase journey tracking
- [x] Cache management

### ✅ IntelligentGuardian Tests
- [x] LLM-powered trajectory analysis
- [x] Steering intervention detection
- [x] Agent health scoring
- [x] System trajectory overview
- [x] Emergency analysis capabilities

### ✅ ConductorService Tests
- [x] System coherence analysis
- [x] Duplicate work detection
- [x] Phase coherence scoring
- [x] Load balance analysis
- [x] Health summary generation

### ✅ MonitoringLoop Tests
- [x] Async orchestration
- [x] Background task management
- [x] Single cycle execution
- [x] Emergency analysis triggering
- [x] Status reporting

## 🔧 Detailed Testing Commands

### Unit Testing with Coverage

```bash
# Run tests with coverage report
uv run pytest tests/test_intelligent_monitoring.py --cov=omoi_os.services.intelligent_guardian --cov=omoi_os.services.conductor --cov=omoi_os.services.trajectory_context --cov=omoi_os.services.agent_output_collector --cov=omoi_os.services.monitoring_loop --cov-report=html

# Run tests with coverage for specific module
uv run pytest tests/test_intelligent_monitoring.py::TestIntelligentGuardian --cov=omoi_os.services.intelligent_guardian --cov-report=term-missing
```

### Performance Testing

```bash
# Run performance-focused tests
uv run pytest tests/test_intelligent_monitoring.py::TestMonitoringLoop::test_run_single_cycle_success -v -s
```

### Error Scenario Testing

```bash
# Test failure scenarios
uv run pytest tests/test_intelligent_monitoring.py::TestMonitoringLoop::test_run_single_cycle_failure -v
```

## 🐛 Common Testing Issues and Solutions

### 1. Database Connection Issues

**Problem**: Tests fail with database connection errors

**Solution**: Ensure your database is running and environment variables are set:

```bash
# Check database status
docker-compose ps

# Set environment variables
export DATABASE_URL="postgresql://postgres:password@localhost:15432/omoi_os"
export REDIS_URL="redis://localhost:16379/0"
```

### 2. LLM Service Configuration

**Problem**: Tests fail with LLM service errors

**Solution**: Mock the LLM service or configure it:

```python
# In tests, use mock_llm_service fixture
mock_llm_service.ainvoke.return_value = {
    "trajectory_aligned": True,
    "alignment_score": 0.8,
    # ... other fields
}
```

### 3. OpenHands Integration

**Problem**: Tests fail due to OpenHands SDK dependencies

**Solution**: Mock OpenHands components:

```python
# Mock OpenHands workspace
with patch('omoi_os.services.agent_executor.OpenHandsSDK') as mock_sdk:
    mock_sdk.return_value.run.return_value = {"output": "test output"}
```

## 📈 Test Results Interpretation

### Success Indicators

✅ **All Unit Tests Pass**: Individual components work correctly
✅ **Integration Tests Pass**: Services work together properly
✅ **Smoke Tests Pass**: System works with real database
✅ **High Test Coverage**: Most code paths are tested
✅ **Performance Acceptable**: Tests complete in reasonable time

### Warning Signs

⚠️ **Mock Dependencies**: Many tests rely on mocks
⚠️ **LLM Service Missing**: LLM-related tests are skipped
⚠️ **Slow Tests**: Some tests take too long
⚠️ **Flaky Tests**: Tests sometimes pass, sometimes fail

## 🔄 Continuous Integration

### GitHub Actions Workflow

```yaml
name: Intelligent Monitoring Tests

on:
  push:
    paths:
      - 'omoi_os/services/intelligent_guardian.py'
      - 'omoi_os/services/conductor.py'
      - 'omoi_os/services/trajectory_context.py'
      - 'omoi_os/services/monitoring_loop.py'
      - 'tests/test_intelligent_monitoring.py'

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 15432:5432

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        pip install uv
        uv sync --group test

    - name: Run database migrations
      run: |
        uv run alembic upgrade head
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:15432/omoi_os_test

    - name: Run unit tests
      run: |
        uv run pytest tests/test_intelligent_monitoring.py -v --cov=omoi_os.services.intelligent_monitoring
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:15432/omoi_os_test
```

## 🎯 Manual Testing Checklist

### 1. Basic Functionality

- [ ] Database migration runs successfully
- [ ] Unit tests all pass
- [ ] Smoke tests complete without errors
- [ ] API endpoints respond correctly

### 2. Monitoring Features

- [ ] Agent output collection works
- [ ] Trajectory context building works
- [ ] Guardian analysis completes (if LLM configured)
- [ ] Conductor analysis runs successfully
- [ ] Monitoring loop orchestration works

### 3. Event System

- [ ] Events are published on agent state changes
- [ ] Monitoring events are published correctly
- [ ] Event bus receives all expected events

### 4. Error Handling

- [ ] System handles missing agents gracefully
- [ ] Database connection failures are handled
- [ ] LLM service failures don't crash the system
- [ ] Invalid data is handled appropriately

## 🚨 Production Readiness

Before deploying to production, ensure:

1. **All Tests Pass**: Unit, integration, and smoke tests
2. **Performance Acceptable**: Monitoring doesn't significantly impact system performance
3. **Error Handling**: Graceful degradation when components fail
4. **Resource Usage**: Memory and CPU usage are within limits
5. **Security**: No sensitive data in logs or events
6. **Monitoring**: The monitoring system itself is monitored

## 📝 Test Data Management

### Test Database

- **Separate Test Database**: Use different database for testing
- **Data Cleanup**: Tests should clean up after themselves
- **Isolation**: Tests should not interfere with each other

### Mock Data

- **Realistic Data**: Use realistic test data
- **Edge Cases**: Test with unusual data combinations
- **Scale Testing**: Test with various data volumes

## 🔍 Debugging Test Failures

### Common Issues

1. **Database Timeouts**: Increase timeout or check database performance
2. **Async Race Conditions**: Use proper async/await patterns
3. **Mock Configuration**: Ensure mocks are set up correctly
4. **Environment Variables**: Check all required environment variables

### Debug Commands

```bash
# Run specific test with debugging
uv run pytest tests/test_intelligent_monitoring.py::TestIntelligentGuardian::test_analyze_agent_trajectory_success -v -s --pdb

# Run tests with verbose logging
uv run pytest tests/test_intelligent_monitoring.py -v -s --log-cli-level=DEBUG

# Run tests and stop on first failure
uv run pytest tests/test_intelligent_monitoring.py -x --tb=short
```

This comprehensive testing strategy ensures your intelligent monitoring system works correctly and reliably in production.