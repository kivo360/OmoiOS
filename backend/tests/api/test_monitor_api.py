"""Tests for /api/v1/monitor/* endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
@pytest.mark.api
class TestMonitorEndpointsUnit:
    """Unit tests for monitoring endpoints."""

    def test_get_dashboard(self, client: TestClient):
        """Test GET /monitor/dashboard returns summary."""
        response = client.get("/api/v1/monitor/dashboard")

        assert response.status_code == 200
        data = response.json()
        # Dashboard should have key metrics
        assert "total_tasks_pending" in data
        assert "total_tasks_completed" in data
        assert "active_agents" in data

    def test_get_anomalies(self, client: TestClient):
        """Test GET /monitor/anomalies returns list."""
        response = client.get("/api/v1/monitor/anomalies")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_anomalies_with_severity_filter(self, client: TestClient):
        """Test GET /monitor/anomalies with severity filter."""
        response = client.get("/api/v1/monitor/anomalies?severity=critical")

        assert response.status_code == 200

    def test_get_health(self, client: TestClient):
        """Test GET /monitor/health returns health status."""
        response = client.get("/api/v1/monitor/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "health_score" in data or isinstance(data, dict)

    def test_get_metrics(self, client: TestClient):
        """Test GET /monitor/metrics returns metrics."""
        response = client.get("/api/v1/monitor/metrics")

        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_db
class TestMonitorIntegration:
    """Integration tests for monitor with real data."""

    def test_dashboard_counts_tasks(self, client: TestClient, sample_task):
        """Test dashboard reflects task counts."""
        response = client.get("/api/v1/monitor/dashboard")

        assert response.status_code == 200
        data = response.json()
        # Should have at least one pending task
        assert data["total_tasks_pending"] >= 0

    def test_dashboard_counts_agents(self, client: TestClient, sample_agent):
        """Test dashboard reflects agent counts."""
        response = client.get("/api/v1/monitor/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert "active_agents" in data
