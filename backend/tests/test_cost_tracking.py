"""Tests for cost tracking service."""

import pytest
from omoi_os.models.cost_record import CostRecord
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.models.agent import Agent
from omoi_os.services.cost_tracking import CostTrackingService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService


@pytest.fixture
def db(tmp_path):
    """Create temporary database for testing."""
    db_path = tmp_path / "test.db"
    db = DatabaseService(connection_string=f"sqlite:///{db_path}")
    db.create_tables()
    yield db


@pytest.fixture
def event_bus():
    """Create event bus for testing."""
    return EventBusService(redis_url="fakeredis://localhost:6379")


@pytest.fixture
def cost_service(db, event_bus):
    """Create cost tracking service."""
    return CostTrackingService(db, event_bus)


@pytest.fixture
def sample_task(db):
    """Create a sample task for testing."""
    with db.get_session() as session:
        # Create ticket first
        ticket = Ticket(
            title="Test Ticket",
            description="Test",
            phase_id="PHASE_IMPLEMENTATION",
            status="active",
            priority="HIGH",
        )
        session.add(ticket)
        session.flush()

        # Create task
        task = Task(
            ticket_id=ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Test task",
            priority="HIGH",
            status="completed",
        )
        session.add(task)
        session.flush()

        task_id = task.id
        session.commit()

    return task_id


@pytest.fixture
def sample_agent(db):
    """Create a sample agent for testing."""
    with db.get_session() as session:
        agent = Agent(
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            status="idle",
            capabilities=["python", "testing"],
        )
        session.add(agent)
        session.flush()
        agent_id = agent.id
        session.commit()

    return agent_id


def test_get_model_pricing(cost_service):
    """Test retrieving model pricing."""
    # Test known provider and model
    pricing = cost_service.get_model_pricing("openai", "gpt-4-turbo")
    assert pricing["prompt_token_cost"] == 0.00001
    assert pricing["completion_token_cost"] == 0.00003

    # Test unknown model (should return defaults)
    pricing = cost_service.get_model_pricing("unknown", "unknown-model")
    assert pricing["prompt_token_cost"] == cost_service.defaults["prompt_token_cost"]
    assert (
        pricing["completion_token_cost"]
        == cost_service.defaults["completion_token_cost"]
    )


def test_calculate_cost(cost_service):
    """Test cost calculation."""
    # Test with known pricing
    costs = cost_service.calculate_cost("openai", "gpt-4-turbo", 1000, 2000)

    # Expected: 1000 * 0.00001 + 2000 * 0.00003 = 0.01 + 0.06 = 0.07
    assert costs["prompt_cost"] == 0.01
    assert costs["completion_cost"] == 0.06
    assert costs["total_cost"] == 0.07


def test_record_llm_cost(cost_service, db, sample_task, sample_agent):
    """Test recording LLM cost."""
    # Record cost
    record = cost_service.record_llm_cost(
        task_id=sample_task,
        provider="openai",
        model="gpt-4-turbo",
        prompt_tokens=1000,
        completion_tokens=2000,
        agent_id=sample_agent,
    )

    # Verify record created
    assert record.id is not None
    assert record.task_id == sample_task
    assert record.agent_id == sample_agent
    assert record.provider == "openai"
    assert record.model == "gpt-4-turbo"
    assert record.prompt_tokens == 1000
    assert record.completion_tokens == 2000
    assert record.total_tokens == 3000
    assert record.total_cost == 0.07

    # Verify persisted
    with db.get_session() as session:
        from sqlalchemy import select

        result = session.execute(select(CostRecord).where(CostRecord.id == record.id))
        persisted = result.scalars().first()
        assert persisted is not None
        assert persisted.total_cost == 0.07


def test_record_llm_cost_without_agent(cost_service, sample_task):
    """Test recording cost without agent."""
    record = cost_service.record_llm_cost(
        task_id=sample_task,
        provider="anthropic",
        model="claude-sonnet-4.5",
        prompt_tokens=5000,
        completion_tokens=3000,
        agent_id=None,
    )

    assert record.agent_id is None
    assert record.task_id == sample_task
    # Expected cost: 5000 * 0.000003 + 3000 * 0.000015 = 0.015 + 0.045 = 0.06
    assert record.total_cost == 0.06


def test_get_task_costs(cost_service, sample_task, sample_agent):
    """Test retrieving costs for a task."""
    # Create multiple cost records
    cost_service.record_llm_cost(
        task_id=sample_task,
        provider="openai",
        model="gpt-4-turbo",
        prompt_tokens=1000,
        completion_tokens=2000,
        agent_id=sample_agent,
    )
    cost_service.record_llm_cost(
        task_id=sample_task,
        provider="openai",
        model="gpt-3.5-turbo",
        prompt_tokens=500,
        completion_tokens=1000,
        agent_id=sample_agent,
    )

    # Retrieve costs
    costs = cost_service.get_task_costs(sample_task)
    assert len(costs) == 2
    assert all(c.task_id == sample_task for c in costs)


def test_get_agent_costs(cost_service, sample_task, sample_agent):
    """Test retrieving costs for an agent."""
    # Create cost records
    cost_service.record_llm_cost(
        task_id=sample_task,
        provider="openai",
        model="gpt-4-turbo",
        prompt_tokens=1000,
        completion_tokens=2000,
        agent_id=sample_agent,
    )

    # Retrieve costs
    costs = cost_service.get_agent_costs(sample_agent)
    assert len(costs) == 1
    assert costs[0].agent_id == sample_agent


def test_get_cost_summary_task_scope(cost_service, sample_task, sample_agent):
    """Test cost summary for task scope."""
    # Create cost records
    cost_service.record_llm_cost(
        task_id=sample_task,
        provider="openai",
        model="gpt-4-turbo",
        prompt_tokens=1000,
        completion_tokens=2000,
        agent_id=sample_agent,
    )
    cost_service.record_llm_cost(
        task_id=sample_task,
        provider="openai",
        model="gpt-3.5-turbo",
        prompt_tokens=500,
        completion_tokens=1000,
        agent_id=sample_agent,
    )

    # Get summary
    summary = cost_service.get_cost_summary("task", sample_task)

    assert summary["scope_type"] == "task"
    assert summary["scope_id"] == sample_task
    assert summary["record_count"] == 2
    assert summary["total_tokens"] == 4500  # 3000 + 1500
    assert len(summary["breakdown"]) == 2  # 2 different models


def test_get_cost_summary_agent_scope(cost_service, sample_task, sample_agent):
    """Test cost summary for agent scope."""
    # Create cost records
    cost_service.record_llm_cost(
        task_id=sample_task,
        provider="anthropic",
        model="claude-sonnet-4.5",
        prompt_tokens=5000,
        completion_tokens=3000,
        agent_id=sample_agent,
    )

    # Get summary
    summary = cost_service.get_cost_summary("agent", sample_agent)

    assert summary["scope_type"] == "agent"
    assert summary["scope_id"] == sample_agent
    assert summary["record_count"] == 1
    assert summary["total_cost"] == 0.06


def test_forecast_costs(cost_service):
    """Test cost forecasting."""
    # Forecast for 10 pending tasks
    forecast = cost_service.forecast_costs(
        pending_task_count=10,
        avg_tokens_per_task=5000,
        provider="anthropic",
        model="claude-sonnet-4.5",
    )

    assert forecast["task_count"] == 10
    assert forecast["avg_tokens_per_task"] == 5000
    assert forecast["estimated_tokens"] == 50000
    # With buffer multiplier of 1.2:
    # Cost per task: (2500 * 0.000003) + (2500 * 0.000015) = 0.0075 + 0.0375 = 0.045
    # Total: 0.045 * 10 * 1.2 = 0.54
    assert forecast["estimated_cost"] == pytest.approx(0.54)
    assert forecast["buffer_multiplier"] == 1.2


def test_forecast_costs_with_defaults(cost_service):
    """Test cost forecasting with default parameters."""
    # Forecast without specifying avg_tokens_per_task (should use config default)
    forecast = cost_service.forecast_costs(
        pending_task_count=5,
        provider="openai",
        model="gpt-4-turbo",
    )

    assert forecast["task_count"] == 5
    assert forecast["avg_tokens_per_task"] == 5000  # Config default
    assert forecast["estimated_tokens"] == 25000
    # Cost per task: (2500 * 0.00001) + (2500 * 0.00003) = 0.025 + 0.075 = 0.1
    # Total: 0.1 * 5 * 1.2 = 0.6
    assert forecast["estimated_cost"] == pytest.approx(0.6)
