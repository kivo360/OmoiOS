# Test Suite

## Quick Reference

```bash
# Run all unit tests (fast, no external deps)
uv run pytest -m unit

# Run all integration tests (needs DB)
uv run pytest -m integration

# Run critical regression tests (bug fix verification)
uv run pytest -m critical

# Run API tests only
uv run pytest -m api

# Run all tests except slow ones
uv run pytest -m "not slow"

# Run with verbose output
uv run pytest -m unit -v

# Run specific test file
uv run pytest tests/api/test_auth_api.py

# Run specific test class
uv run pytest tests/api/test_auth_api.py::TestAuthEndpointsUnit

# Run specific test
uv run pytest tests/api/test_auth_api.py::TestAuthEndpointsUnit::test_get_me_mock_authenticated
```

## Test Markers

| Marker | Description | Speed |
|--------|-------------|-------|
| `unit` | Isolated tests, mocked deps | Fast (~15s) |
| `integration` | Real DB/services | Moderate |
| `critical` | Bug regression tests | Fast |
| `api` | API endpoint tests | Varies |
| `auth` | Authentication tests | Varies |
| `requires_db` | Needs database | Slow |
| `e2e` | End-to-end workflows | Slow |
| `slow` | Long-running tests | Very Slow |

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── api/                     # API endpoint tests
│   ├── test_auth_api.py     # Auth endpoints (unit + integration)
│   ├── test_tickets_api.py  # Ticket endpoints
│   └── test_fixed_endpoints.py  # Bug regression tests
├── test_*.py                # Service/model tests
```

## Key Fixtures

### For Unit Tests (No DB)
- `client` - Session-scoped TestClient
- `mock_user` - Mock User object (no DB)
- `mock_authenticated_client` - Client with mocked auth

### For Integration Tests (Need DB)
- `db_service` - Fresh test database
- `test_user` - Real user in test DB
- `auth_token` - Valid JWT token
- `auth_headers` - Headers with Bearer token
- `authenticated_client` - Client with real JWT
- `sample_ticket` - Test ticket in DB
- `sample_task` - Test task in DB
- `sample_agent` - Test agent in DB

## CI/CD Recommendation

```yaml
# Fast checks (every PR)
- name: Unit Tests
  run: uv run pytest -m unit --tb=short

# Full checks (before merge)
- name: Integration Tests
  run: uv run pytest -m "integration or critical" --tb=short
```
