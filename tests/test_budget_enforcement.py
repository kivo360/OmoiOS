"""Tests for budget enforcement service."""

import pytest
from omoi_os.models.budget import Budget, BudgetScope
from omoi_os.services.budget_enforcer import BudgetEnforcerService
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
def budget_service(db, event_bus):
    """Create budget enforcer service."""
    return BudgetEnforcerService(db, event_bus)


def test_create_global_budget(budget_service):
    """Test creating a global budget."""
    budget = budget_service.create_budget(
        scope_type="global",
        limit_amount=100.0,
        alert_threshold=0.8,
    )
    
    assert budget.id is not None
    assert budget.scope_type == "global"
    assert budget.scope_id is None
    assert budget.limit_amount == 100.0
    assert budget.spent_amount == 0.0
    assert budget.remaining_amount == 100.0
    assert budget.alert_threshold == 0.8
    assert not budget.alert_triggered


def test_create_scoped_budget(budget_service):
    """Test creating a scoped budget (ticket/agent/phase)."""
    budget = budget_service.create_budget(
        scope_type="ticket",
        scope_id="ticket-123",
        limit_amount=50.0,
        alert_threshold=0.9,
    )
    
    assert budget.scope_type == "ticket"
    assert budget.scope_id == "ticket-123"
    assert budget.limit_amount == 50.0
    assert budget.alert_threshold == 0.9


def test_create_budget_validation(budget_service):
    """Test budget creation validation."""
    # Invalid scope_type
    with pytest.raises(ValueError, match="Invalid scope_type"):
        budget_service.create_budget(
            scope_type="invalid",
            limit_amount=100.0,
        )
    
    # Missing scope_id for non-global scope
    with pytest.raises(ValueError, match="scope_id required"):
        budget_service.create_budget(
            scope_type="ticket",
            limit_amount=100.0,
        )


def test_get_budget(budget_service):
    """Test retrieving a budget."""
    # Create budget
    created = budget_service.create_budget(
        scope_type="agent",
        scope_id="agent-456",
        limit_amount=75.0,
    )
    
    # Retrieve budget
    retrieved = budget_service.get_budget("agent", "agent-456")
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.scope_type == "agent"
    assert retrieved.scope_id == "agent-456"


def test_get_nonexistent_budget(budget_service):
    """Test retrieving a budget that doesn't exist."""
    budget = budget_service.get_budget("phase", "nonexistent-phase")
    assert budget is None


def test_check_budget_exists(budget_service):
    """Test checking budget status when budget exists."""
    # Create budget
    budget_service.create_budget(
        scope_type="global",
        limit_amount=100.0,
        alert_threshold=0.8,
    )
    
    # Check budget
    status = budget_service.check_budget("global")
    
    assert status["exists"] is True
    assert status["limit"] == 100.0
    assert status["spent"] == 0.0
    assert status["remaining"] == 100.0
    assert status["utilization_percent"] == 0.0
    assert status["exceeded"] is False
    assert status["alert_threshold"] == 0.8
    assert status["alert_triggered"] is False


def test_check_budget_not_exists(budget_service):
    """Test checking budget status when budget doesn't exist."""
    status = budget_service.check_budget("ticket", "nonexistent")
    
    assert status["exists"] is False
    assert status["limit"] is None
    assert status["spent"] == 0.0
    assert status["remaining"] is None
    assert status["utilization_percent"] == 0.0
    assert status["exceeded"] is False


def test_update_budget_spent(budget_service):
    """Test updating budget spent amount."""
    # Create budget
    budget_service.create_budget(
        scope_type="global",
        limit_amount=100.0,
        alert_threshold=0.8,
    )
    
    # Update spent amount
    updated = budget_service.update_budget_spent("global", 25.0)
    
    assert updated is not None
    assert updated.spent_amount == 25.0
    assert updated.remaining_amount == 75.0
    assert not updated.alert_triggered


def test_update_budget_alert_threshold(budget_service):
    """Test budget alert triggering."""
    # Create budget with 80% threshold
    budget_service.create_budget(
        scope_type="global",
        limit_amount=100.0,
        alert_threshold=0.8,
    )
    
    # Spend just below threshold (79%)
    updated = budget_service.update_budget_spent("global", 79.0)
    assert not updated.alert_triggered
    
    # Spend to cross threshold (85%)
    updated = budget_service.update_budget_spent("global", 6.0)
    assert updated.alert_triggered
    assert updated.spent_amount == 85.0


def test_update_budget_exceeded(budget_service):
    """Test budget exceeded detection."""
    # Create budget
    budget_service.create_budget(
        scope_type="ticket",
        scope_id="ticket-789",
        limit_amount=50.0,
    )
    
    # Spend up to limit
    updated = budget_service.update_budget_spent("ticket", 50.0, scope_id="ticket-789")
    assert updated.is_exceeded()
    assert updated.remaining_amount == 0.0
    
    # Spend beyond limit
    updated = budget_service.update_budget_spent("ticket", 10.0, scope_id="ticket-789")
    assert updated.is_exceeded()
    assert updated.spent_amount == 60.0
    assert updated.remaining_amount == -10.0


def test_list_budgets(budget_service):
    """Test listing all budgets."""
    # Create multiple budgets
    budget_service.create_budget("global", limit_amount=100.0)
    budget_service.create_budget("ticket", limit_amount=50.0, scope_id="ticket-1")
    budget_service.create_budget("agent", limit_amount=75.0, scope_id="agent-1")
    
    # List all budgets
    budgets = budget_service.list_budgets()
    assert len(budgets) >= 3


def test_list_budgets_filtered(budget_service):
    """Test listing budgets filtered by scope type."""
    # Create multiple budgets
    budget_service.create_budget("global", limit_amount=100.0)
    budget_service.create_budget("ticket", limit_amount=50.0, scope_id="ticket-1")
    budget_service.create_budget("ticket", limit_amount=60.0, scope_id="ticket-2")
    budget_service.create_budget("agent", limit_amount=75.0, scope_id="agent-1")
    
    # List only ticket budgets
    ticket_budgets = budget_service.list_budgets(scope_type="ticket")
    assert len(ticket_budgets) >= 2
    assert all(b.scope_type == "ticket" for b in ticket_budgets)


def test_is_budget_available(budget_service):
    """Test checking if budget has sufficient funds."""
    # Create budget
    budget_service.create_budget(
        scope_type="global",
        limit_amount=100.0,
    )
    
    # Check if 30.0 cost is available (should be True)
    assert budget_service.is_budget_available("global", 30.0) is True
    
    # Spend 80.0
    budget_service.update_budget_spent("global", 80.0)
    
    # Check if 30.0 cost is available (should be False, only 20.0 remaining)
    assert budget_service.is_budget_available("global", 30.0) is False
    
    # Check if 15.0 cost is available (should be True)
    assert budget_service.is_budget_available("global", 15.0) is True


def test_is_budget_available_no_budget(budget_service):
    """Test budget availability when no budget exists."""
    # Should return True (no budget means no limit)
    assert budget_service.is_budget_available("nonexistent", 999999.0) is True

