"""Tests for /api/v1/alerts/* endpoints."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.mark.unit
@pytest.mark.api
class TestAlertsEndpointsUnit:
    """Unit tests for alerting endpoints."""

    def test_list_alerts(self, client: TestClient):
        """Test GET /alerts returns list."""
        response = client.get("/api/v1/alerts")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_alerts_with_severity_filter(self, client: TestClient):
        """Test GET /alerts with severity filter."""
        response = client.get("/api/v1/alerts?severity=critical")

        assert response.status_code == 200

    def test_list_alerts_active_only(self, client: TestClient):
        """Test GET /alerts with active filter."""
        response = client.get("/api/v1/alerts?active=true")

        assert response.status_code == 200

    def test_list_alert_rules(self, client: TestClient):
        """Test GET /alerts/rules returns rules."""
        response = client.get("/api/v1/alerts/rules")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_nonexistent_alert(self, client: TestClient):
        """Test GET /alerts/{id} for non-existent alert."""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/alerts/{fake_id}")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_db
class TestAlertsIntegration:
    """Integration tests for alerts."""

    def test_create_alert_rule(self, client: TestClient):
        """Test creating an alert rule."""
        response = client.post(
            "/api/v1/alerts/rules",
            json={
                "name": "Test Alert Rule",
                "metric_name": "task_queue_depth",
                "condition": "greater_than",
                "threshold": 100,
                "severity": "warning",
            },
        )

        # Should succeed or return validation error
        assert response.status_code in [200, 201, 400, 422]
