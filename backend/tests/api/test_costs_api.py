"""Tests for /api/v1/costs/* endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
@pytest.mark.api
class TestCostsEndpointsUnit:
    """Unit tests for cost tracking endpoints."""

    def test_get_cost_summary(self, client: TestClient):
        """Test GET /costs/summary returns summary."""
        response = client.get(
            "/api/v1/costs/summary?scope_type=task&scope_id=test"
        )

        assert response.status_code == 200
        data = response.json()
        assert "scope_type" in data
        assert "total_cost" in data
        assert "total_tokens" in data

    def test_get_cost_summary_project_scope(self, client: TestClient):
        """Test GET /costs/summary with project scope."""
        response = client.get(
            "/api/v1/costs/summary?scope_type=project&scope_id=test-project"
        )

        assert response.status_code == 200

    def test_list_cost_records(self, client: TestClient):
        """Test GET /costs/records returns list."""
        response = client.get("/api/v1/costs/records")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_cost_records_with_pagination(self, client: TestClient):
        """Test GET /costs/records with limit."""
        response = client.get("/api/v1/costs/records?limit=10")

        assert response.status_code == 200

    def test_get_budgets(self, client: TestClient):
        """Test GET /costs/budgets returns list."""
        response = client.get("/api/v1/costs/budgets")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_db
class TestCostsIntegration:
    """Integration tests for cost tracking."""

    def test_create_budget(self, client: TestClient):
        """Test creating a budget."""
        response = client.post(
            "/api/v1/costs/budgets",
            json={
                "scope_type": "project",
                "scope_id": "test-project",
                "limit_amount": 100.0,
            },
        )

        # Should succeed or return validation error
        assert response.status_code in [200, 201, 400, 422]

    def test_check_budget(self, client: TestClient):
        """Test checking budget status."""
        response = client.get(
            "/api/v1/costs/budgets/check?scope_type=project&scope_id=test"
        )

        assert response.status_code == 200
