"""Tests for the AgentRegistryService."""

from unittest.mock import Mock

from omoi_os.services.agent_registry import AgentRegistryService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from tests.test_helpers import create_test_agent


def test_register_agent_persists_fields(db_service: DatabaseService):
    """Ensure registry persists agent metadata."""
    registry = AgentRegistryService(db_service)

    agent = registry.register_agent(
        agent_type="worker",
        phase_id="PHASE_IMPLEMENTATION",
        capabilities=["analysis", "python"],
        capacity=3,
        tags=["python", "fastapi"],
    )

    assert agent.agent_type == "worker"
    assert agent.capacity == 3
    assert agent.capabilities == ["analysis", "python"]
    assert agent.tags == ["python", "fastapi"]
    assert agent.health_status == "healthy"


def test_search_agents_ranks_best_match(db_service: DatabaseService):
    """Best-fit search should rank agents by capability overlap and availability."""
    registry = AgentRegistryService(db_service)

    # Seed agents
    create_test_agent(
        db_service,
        agent_type="worker",
        phase_id="PHASE_REQUIREMENTS",
        status="idle",
        capabilities=["analysis", "python", "fastapi"],
        capacity=3,
        tags=["analysis"],
        health_status="healthy",
    )
    secondary = create_test_agent(
        db_service,
        agent_type="worker",
        phase_id="PHASE_REQUIREMENTS",
        status="running",
        capabilities=["analysis"],
        capacity=1,
        tags=["analysis"],
        health_status="healthy",
    )

    matches = registry.search_agents(
        required_capabilities=["analysis", "python"],
        phase_id="PHASE_REQUIREMENTS",
        limit=2,
    )

    assert len(matches) == 2
    assert matches[0]["match_score"] >= matches[1]["match_score"]
    assert matches[1]["agent"].id == secondary.id


def test_update_capabilities_publishes_event(db_service: DatabaseService):
    """Capability updates should raise event bus notifications."""
    mock_event_bus = Mock(spec=EventBusService)
    registry = AgentRegistryService(db_service, mock_event_bus)

    agent = create_test_agent(
        db_service,
        capabilities=["analysis"],
        tags=["python"],
        health_status="healthy",
    )

    updated = registry.update_agent(
        agent_id=agent.id,
        capabilities=["analysis", "python"],
    )

    assert updated.capabilities == ["analysis", "python"]
    mock_event_bus.publish.assert_called_once()
    event = mock_event_bus.publish.call_args[0][0]
    assert event.event_type == "agent.capability.updated"
    assert event.payload["agent_id"] == agent.id
