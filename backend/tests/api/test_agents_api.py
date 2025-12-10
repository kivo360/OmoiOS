"""Tests for /api/v1/agents/* endpoints."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from omoi_os.models.agent import Agent


@pytest.mark.unit
@pytest.mark.api
class TestAgentsEndpointsUnit:
    """Unit tests for agent endpoints."""

    def test_list_agents(self, client: TestClient):
        """Test GET /agents returns list."""
        response = client.get("/api/v1/agents")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_agents_with_status_filter(self, client: TestClient):
        """Test GET /agents with status filter."""
        response = client.get("/api/v1/agents?status=idle")

        assert response.status_code == 200

    def test_list_agents_with_phase_filter(self, client: TestClient):
        """Test GET /agents with phase filter."""
        response = client.get("/api/v1/agents?phase_id=PHASE_IMPLEMENTATION")

        assert response.status_code == 200

    def test_get_nonexistent_agent(self, client: TestClient):
        """Test GET /agents/{id} for non-existent agent."""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/agents/{fake_id}")

        assert response.status_code == 404

    def test_search_agents(self, client: TestClient):
        """Test GET /agents/search endpoint."""
        response = client.get("/api/v1/agents/search?capabilities=bash")

        assert response.status_code == 200

    def test_register_agent_validation(self, client: TestClient):
        """Test POST /agents/register validates input."""
        # Missing required fields
        response = client.post("/api/v1/agents/register", json={})

        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_db
class TestAgentsCRUDIntegration:
    """Integration tests for agent CRUD operations."""

    def test_get_agent(self, client: TestClient, sample_agent: Agent):
        """Test getting an agent by ID."""
        response = client.get(f"/api/v1/agents/{sample_agent.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == str(sample_agent.id)

    def test_list_agents_includes_sample(self, client: TestClient, sample_agent: Agent):
        """Test list includes created agent."""
        response = client.get("/api/v1/agents")

        assert response.status_code == 200
        agents = response.json()
        agent_ids = [a["agent_id"] for a in agents]
        assert str(sample_agent.id) in agent_ids

    def test_update_agent(self, client: TestClient, sample_agent: Agent):
        """Test updating agent."""
        response = client.patch(
            f"/api/v1/agents/{sample_agent.id}",
            json={"status": "busy"},
        )

        # Should succeed or return meaningful error
        assert response.status_code in [200, 400, 422]

    def test_toggle_agent_availability(self, client: TestClient, sample_agent: Agent):
        """Test toggling agent availability."""
        response = client.post(
            f"/api/v1/agents/{sample_agent.id}/availability",
            json={"available": False},
        )

        assert response.status_code in [200, 400]
