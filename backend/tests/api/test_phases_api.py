"""Tests for /api/v1/phases/* endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
@pytest.mark.api
class TestPhasesEndpointsUnit:
    """Unit tests for phase endpoints."""

    def test_list_phases(self, client: TestClient):
        """Test GET /phases returns list of phases."""
        response = client.get("/api/v1/phases")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_phases_have_required_fields(self, client: TestClient):
        """Test phases have expected structure."""
        response = client.get("/api/v1/phases")

        assert response.status_code == 200
        phases = response.json()

        if phases:
            phase = phases[0]
            # Phases should have at least id and name
            assert "id" in phase or "phase_id" in phase

    def test_get_phase_config(self, client: TestClient):
        """Test GET /phases/config returns configuration."""
        response = client.get("/api/v1/phases/config")

        assert response.status_code == 200

    def test_get_phase_gates(self, client: TestClient):
        """Test GET /phases/gates returns gate info."""
        response = client.get("/api/v1/phases/gates")

        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_db
class TestPhasesIntegration:
    """Integration tests for phases with tickets."""

    def test_get_phase_tickets(self, client: TestClient, sample_ticket):
        """Test getting tickets for a phase."""
        phase_id = sample_ticket.phase_id
        response = client.get(f"/api/v1/phases/{phase_id}/tickets")

        assert response.status_code == 200
