---
id: TSK-014
title: Write integration tests for API routes
created: 2026-01-09
status: pending
priority: HIGH
type: test
parent_ticket: TKT-007
estimate: M
dependencies:
  depends_on:
    - TSK-010
    - TSK-011
    - TSK-012
  blocks: []
---

# TSK-014: Write integration tests for API routes

## Objective

Create integration tests for all GitHub repository API routes, testing the full request/response cycle.

## Deliverables

- [ ] `backend/tests/integration/api/test_github_routes.py`

## Implementation Notes

Use FastAPI TestClient with mocked GitHub responses.

```python
# backend/tests/integration/api/test_github_routes.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

@pytest.fixture
def client(app):
    return TestClient(app)

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}

class TestGitHubRoutes:

    def test_list_owners_requires_auth(self, client):
        response = client.get("/api/v1/github/owners")
        assert response.status_code == 401

    def test_list_owners_returns_owners(self, client, auth_headers):
        with patch("omoi_os.services.repository_service.RepositoryService") as mock:
            mock.return_value.list_owners = AsyncMock(return_value=[...])
            response = client.get("/api/v1/github/owners", headers=auth_headers)
            assert response.status_code == 200
            assert "owners" in response.json()

    def test_check_availability_available(self, client, auth_headers):
        with patch("omoi_os.services.repository_service.RepositoryService") as mock:
            mock.return_value.check_availability = AsyncMock(return_value=(True, None))
            response = client.get(
                "/api/v1/github/repos/owner/repo/available",
                headers=auth_headers
            )
            assert response.status_code == 200
            assert response.json()["available"] is True

    def test_create_repository_success(self, client, auth_headers):
        # Test full creation flow
        pass

    def test_create_repository_name_taken(self, client, auth_headers):
        # Test error when name exists
        pass
```

## Done When

- [ ] Tests for all 3 routes
- [ ] Auth requirement tested
- [ ] Success cases tested
- [ ] Error cases tested
- [ ] All tests pass
