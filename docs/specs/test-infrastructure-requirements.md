# Test Infrastructure and Fixtures Setup - Requirements Analysis

## Executive Summary

This document analyzes the requirements for the Test Infrastructure and Fixtures Setup task for OmoiOS. The analysis is based on a comprehensive exploration of the existing codebase, which already has a **mature testing infrastructure** in place.

**Key Finding**: The testing infrastructure is largely complete and well-architected. This analysis identifies the current state, gaps, and opportunities for enhancement.

---

## 1. Current State Assessment

### 1.1 Frontend Testing Stack (Complete ✅)

| Component | Technology | Status |
|-----------|------------|--------|
| Unit/Component Tests | Vitest 4.0.15 | ✅ Configured |
| DOM Environment | jsdom | ✅ Configured |
| Component Testing | @testing-library/react 16.3.1 | ✅ Configured |
| User Interactions | @testing-library/user-event 14.6.1 | ✅ Configured |
| API Mocking | MSW 2.12.4 | ✅ Configured |
| E2E Tests | Playwright 1.57.0 | ✅ Configured |
| Coverage | v8 provider | ✅ Configured |

**Configuration Files**:
- `/workspace/frontend/vitest.config.ts` - Unit test configuration
- `/workspace/frontend/playwright.config.ts` - E2E configuration
- `/workspace/frontend/__tests__/setup.tsx` - Global test setup
- `/workspace/frontend/__tests__/utils.tsx` - Test utilities

### 1.2 Backend Testing Stack (Complete ✅)

| Component | Technology | Status |
|-----------|------------|--------|
| Test Framework | Pytest 8.0.0+ | ✅ Configured |
| Async Support | pytest-asyncio 0.23.0+ | ✅ Configured |
| Coverage | pytest-cov 4.1.0+ | ✅ Configured |
| Parallel Execution | pytest-xdist 3.8.0 | ✅ Configured |
| Redis Mocking | fakeredis 2.20.0+ | ✅ Configured |
| Output Enhancement | pytest-sugar 1.1.1 | ✅ Configured |

**Configuration Files**:
- `/workspace/backend/pytest.ini` - Pytest configuration with markers
- `/workspace/backend/tests/conftest.py` - Shared fixtures

### 1.3 Test Organization

```
Frontend Tests (~15 files):
├── __tests__/
│   ├── setup.tsx              # MSW, Next.js mocks, browser APIs
│   ├── utils.tsx              # Custom render, TestProviders
│   ├── fixtures/index.ts      # Typed mock data
│   ├── mocks/                 # MSW handlers
│   ├── unit/                  # Component & hook tests
│   ├── integration/           # Feature integration tests
│   └── e2e/                   # Playwright tests

Backend Tests (~60+ files):
├── tests/
│   ├── conftest.py            # 20+ reusable fixtures
│   ├── api/                   # 13 API endpoint test files
│   ├── integration/           # 7 sandbox integration tests
│   ├── contract/              # API schema validation
│   ├── unit/                  # Isolated unit tests
│   └── e2e/                   # Full workflow tests
```

---

## 2. Identified Gaps and Requirements

### 2.1 Frontend Gaps

#### REQ-F1: Expand Component Test Coverage
**Condition**: WHEN new components are added to the UI
**Action**: THE SYSTEM SHALL have corresponding unit tests in `__tests__/unit/components/`

**Current State**: Only 2 component tests exist (`AgentCard.test.tsx`, `Button.test.tsx`)
**Gap**: Many UI components in `/workspace/frontend/components/` lack test coverage

**Acceptance Criteria**:
- [ ] All ShadCN UI wrapper components have basic render tests
- [ ] Interactive components have user interaction tests
- [ ] Components with conditional logic have branch coverage tests

#### REQ-F2: Expand Hook Test Coverage
**Condition**: WHEN custom hooks are created
**Action**: THE SYSTEM SHALL have corresponding tests in `__tests__/unit/hooks/`

**Current State**: Only 2 hook tests exist (`useProjects.test.ts`, `useTickets.test.ts`)
**Gap**: Multiple hooks in `/workspace/frontend/hooks/` need coverage

**Acceptance Criteria**:
- [ ] All data-fetching hooks have success/error/loading state tests
- [ ] Mutation hooks have optimistic update tests
- [ ] Custom utility hooks have edge case coverage

#### REQ-F3: Complete MSW Handler Coverage
**Condition**: WHEN API endpoints are used by the frontend
**Action**: THE SYSTEM SHALL have corresponding MSW mock handlers

**Current State**: ~230 lines of handlers in `mocks/handlers.ts`
**Gap**: Ensure all API endpoints have mock handlers

**Acceptance Criteria**:
- [ ] All GET endpoints have success handlers
- [ ] All mutation endpoints have success/error handlers
- [ ] Pagination scenarios are mocked
- [ ] Error responses (401, 403, 404, 500) are mocked

#### REQ-F4: E2E Test Expansion
**Condition**: WHEN critical user flows exist
**Action**: THE SYSTEM SHALL have Playwright E2E tests covering the flow

**Current State**: Only 2 E2E tests (`auth.spec.ts`, `board.spec.ts`)
**Gap**: Missing E2E tests for other critical flows

**Acceptance Criteria**:
- [ ] Project creation/management flow tested
- [ ] Ticket lifecycle flow tested
- [ ] Agent monitoring flow tested
- [ ] Settings/configuration flow tested

### 2.2 Backend Gaps

#### REQ-B1: Standardize Test Markers Usage
**Condition**: WHEN a test is created
**Action**: THE SYSTEM SHALL use appropriate pytest markers for categorization

**Current State**: Markers defined in `pytest.ini` but inconsistently applied
**Gap**: Some tests lack proper marker classification

**Acceptance Criteria**:
- [ ] All tests have at least one category marker (`unit`, `integration`, `e2e`, `api`)
- [ ] Tests requiring external services are marked (`requires_db`, `requires_redis`)
- [ ] Slow tests are marked for optional exclusion (`slow`, `skip_ci`)

#### REQ-B2: Contract Test Expansion
**Condition**: WHEN API schemas change
**Action**: THE SYSTEM SHALL have contract tests validating the schema

**Current State**: 2 contract tests (`test_message_contract.py`, `test_sandbox_event_contract.py`)
**Gap**: API response schemas need broader contract testing

**Acceptance Criteria**:
- [ ] All API response models have schema validation tests
- [ ] Breaking changes are detected by contract tests
- [ ] OpenAPI schema consistency is verified

#### REQ-B3: Performance Test Baseline
**Condition**: WHEN performance-critical operations exist
**Action**: THE SYSTEM SHALL have performance benchmark tests

**Current State**: `@pytest.mark.performance` marker exists but minimal tests
**Gap**: No systematic performance testing

**Acceptance Criteria**:
- [ ] Database query performance baselines established
- [ ] API endpoint response time benchmarks set
- [ ] Task queue throughput tests implemented

### 2.3 Cross-Cutting Requirements

#### REQ-X1: CI/CD Test Integration
**Condition**: WHEN code is pushed to the repository
**Action**: THE SYSTEM SHALL run the appropriate test suite

**Acceptance Criteria**:
- [ ] GitHub Actions workflow runs frontend tests (Vitest + Playwright)
- [ ] GitHub Actions workflow runs backend tests (Pytest)
- [ ] Coverage reports are generated and tracked
- [ ] Test results are visible in PR checks

#### REQ-X2: Test Documentation
**Condition**: WHEN developers need to write or run tests
**Action**: THE SYSTEM SHALL provide clear documentation

**Acceptance Criteria**:
- [ ] README or TESTING.md documents how to run tests
- [ ] Fixture usage is documented with examples
- [ ] Test patterns and conventions are documented

#### REQ-X3: Shared Test Data Consistency
**Condition**: WHEN test fixtures are used
**Action**: THE SYSTEM SHALL maintain consistency between frontend and backend fixtures

**Current State**: Frontend has `fixtures/index.ts`, backend has `conftest.py` fixtures
**Gap**: No guarantee of data model alignment

**Acceptance Criteria**:
- [ ] Frontend fixture types match backend Pydantic schemas
- [ ] IDs and relationships are consistent across test files
- [ ] Factory functions use consistent patterns

---

## 3. Existing Fixtures Analysis

### 3.1 Frontend Fixtures (`/workspace/frontend/__tests__/fixtures/index.ts`)

**Entity Coverage**:
| Entity | Variants | Factory Function |
|--------|----------|------------------|
| User | default, admin, unverified | `createUser()` |
| Project | active, paused, archived | `createProject()` |
| Ticket | inProgress, todo, done, blocked | `createTicket()`, `createTicketList()` |
| Agent | active, idle, unhealthy | `createAgent()` |
| Task | completed, pending, failed | `createTask()` |
| BoardView | default, empty | - |

**Strengths**:
- Type-safe with `satisfies` keyword
- Factory functions for custom overrides
- Multiple variants per entity for different test scenarios
- Centralized location for easy maintenance

**Improvements Needed**:
- Add `createBoardView()` factory function
- Add `Phase` fixtures (referenced but not defined)
- Add `createAgentList()` and `createTaskList()` for bulk scenarios

### 3.2 Backend Fixtures (`/workspace/backend/tests/conftest.py`)

**Fixture Categories**:

| Category | Fixtures | Scope |
|----------|----------|-------|
| Database | `db_service`, `test_database_url` | function/session |
| Auth | `test_user`, `admin_user`, `auth_token`, `auth_headers`, `mock_user` | function |
| Clients | `client`, `authenticated_client`, `mock_authenticated_client` | function |
| Services | `task_queue_service`, `event_bus_service`, `collaboration_service`, `lock_service`, `monitor_service` | function |
| Data | `sample_ticket`, `sample_task`, `sample_agent`, `sample_task_with_sandbox` | function |
| Sandbox | `sandbox_id`, `sample_sandbox_event`, `sample_message` | function |
| Workspace | `test_workspace_dir` | function |

**Strengths**:
- Proper session vs function scope usage
- Environment setup prevents slow model loading
- Comprehensive service fixtures
- Auth fixtures with real and mock variants

**Improvements Needed**:
- Add `sample_project` fixture
- Add `sample_phase` fixture
- Add bulk data fixtures for load testing
- Document fixture dependencies

---

## 4. Recommended Actions

### Priority 1: Documentation (Low Effort, High Value)
1. Create `TESTING.md` documenting test patterns and conventions
2. Add JSDoc comments to frontend fixture factory functions
3. Add docstrings to backend fixtures explaining usage

### Priority 2: Fixture Enhancements (Medium Effort, High Value)
1. Add missing frontend factory functions (`createBoardView`, `createPhase`)
2. Add missing backend fixtures (`sample_project`, `sample_phase`)
3. Create bulk data generators for both stacks

### Priority 3: Test Coverage Expansion (High Effort, High Value)
1. Add component tests for high-value UI components
2. Add hook tests for data-fetching hooks
3. Expand E2E tests for critical user journeys

### Priority 4: CI/CD Integration (Medium Effort, High Value)
1. Create GitHub Actions workflow for test execution
2. Set up coverage reporting and thresholds
3. Configure test result artifacts

---

## 5. Test Execution Commands

### Frontend
```bash
# Unit tests
cd frontend && npm run test

# Unit tests with UI
cd frontend && npm run test:ui

# Unit tests with coverage
cd frontend && npm run test:coverage

# E2E tests
cd frontend && npm run test:e2e

# E2E tests with UI
cd frontend && npm run test:e2e:ui
```

### Backend
```bash
# All tests
cd backend && uv run pytest

# Unit tests only
cd backend && uv run pytest -m unit

# API tests only
cd backend && uv run pytest -m api

# Integration tests
cd backend && uv run pytest -m integration

# With coverage
cd backend && uv run pytest --cov=omoi_os --cov-report=html

# Parallel execution
cd backend && uv run pytest -n auto
```

---

## 6. Conclusion

The OmoiOS project has a **well-established testing infrastructure** with:
- Modern testing frameworks (Vitest, Playwright, Pytest)
- Type-safe fixtures with factory patterns
- API mocking with MSW
- Comprehensive pytest markers for test categorization
- Both real and mock authentication fixtures

The primary opportunities for improvement are:
1. **Expanding test coverage** for UI components and hooks
2. **Enhancing fixtures** with missing entities and bulk generators
3. **Adding CI/CD integration** for automated test execution
4. **Documenting conventions** for new contributors

The infrastructure foundation is solid; the focus should be on coverage expansion and automation.
