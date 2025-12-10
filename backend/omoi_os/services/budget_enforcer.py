"""Budget enforcement service for cost control."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from omoi_os.models.budget import Budget
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now


class BudgetEnforcerService:
    """Service for enforcing budget limits and triggering alerts.

    Responsibilities:
    - Create and manage budget limits
    - Check budget availability before task execution
    - Update spent amounts as costs are recorded
    - Trigger alerts when thresholds are exceeded
    - Publish budget events for monitoring
    """

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
    ):
        self.db = db
        self.event_bus = event_bus

    def create_budget(
        self,
        scope_type: str,
        limit_amount: float,
        scope_id: Optional[str] = None,
        period_end: Optional[object] = None,
        alert_threshold: float = 0.8,
        session: Optional[Session] = None,
    ) -> Budget:
        """Create a new budget limit.

        Args:
            scope_type: 'global', 'ticket', 'agent', or 'phase'
            limit_amount: Maximum allowed spend (USD)
            scope_id: ID of scoped entity (required unless scope_type='global')
            period_end: Budget period end datetime (None for indefinite)
            alert_threshold: Trigger alert at this percentage (default 0.8 = 80%)
            session: Database session

        Returns:
            Created Budget
        """
        # Validate scope
        if scope_type not in ["global", "ticket", "agent", "phase"]:
            raise ValueError(f"Invalid scope_type: {scope_type}")

        if scope_type != "global" and not scope_id:
            raise ValueError(f"scope_id required for scope_type={scope_type}")

        def _create(sess: Session) -> Budget:
            budget = Budget(
                scope_type=scope_type,
                scope_id=scope_id,
                limit_amount=limit_amount,
                spent_amount=0.0,
                remaining_amount=limit_amount,
                period_start=utc_now(),
                period_end=period_end,
                alert_threshold=alert_threshold,
                alert_triggered=0,
            )
            sess.add(budget)
            sess.flush()
            sess.expunge(budget)
            return budget

        if session:
            budget = _create(session)
        else:
            with self.db.get_session() as sess:
                budget = _create(sess)
                sess.commit()

        # Publish budget created event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="budget.created",
                    entity_type="budget",
                    entity_id=str(budget.id),
                    payload={
                        "scope_type": budget.scope_type,
                        "scope_id": budget.scope_id,
                        "limit_amount": budget.limit_amount,
                    },
                )
            )

        return budget

    def get_budget(
        self,
        scope_type: str,
        scope_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> Optional[Budget]:
        """Get active budget for a scope.

        Returns the most recently created active budget for the scope.
        """

        def _get(sess: Session) -> Optional[Budget]:
            query = select(Budget).where(Budget.scope_type == scope_type)

            if scope_id:
                query = query.where(Budget.scope_id == scope_id)
            else:
                query = query.where(Budget.scope_id.is_(None))

            # Get most recent active budget
            query = query.order_by(Budget.created_at.desc())

            result = sess.execute(query)
            return result.scalars().first()

        if session:
            return _get(session)
        else:
            with self.db.get_session() as sess:
                return _get(sess)

    def check_budget(
        self,
        scope_type: str,
        scope_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> dict:
        """Check budget status for a scope.

        Returns:
            dict with 'limit', 'spent', 'remaining', 'utilization_percent', 'exceeded'
        """
        budget = self.get_budget(scope_type, scope_id, session)

        if not budget:
            return {
                "exists": False,
                "limit": None,
                "spent": 0.0,
                "remaining": None,
                "utilization_percent": 0.0,
                "exceeded": False,
            }

        return {
            "exists": True,
            "limit": budget.limit_amount,
            "spent": budget.spent_amount,
            "remaining": budget.remaining_amount,
            "utilization_percent": (
                (budget.spent_amount / budget.limit_amount * 100)
                if budget.limit_amount > 0
                else 0.0
            ),
            "exceeded": budget.is_exceeded(),
            "alert_threshold": budget.alert_threshold,
            "alert_triggered": bool(budget.alert_triggered),
        }

    def update_budget_spent(
        self,
        scope_type: str,
        amount: float,
        scope_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> Optional[Budget]:
        """Update budget spent amount and check for threshold violations.

        Args:
            scope_type: Budget scope type
            amount: Amount to add to spent (USD)
            scope_id: Scope identifier
            session: Database session

        Returns:
            Updated Budget, or None if no budget exists
        """

        def _update(sess: Session) -> Optional[Budget]:
            budget = self.get_budget(scope_type, scope_id, sess)

            if not budget:
                return None

            # Check if alert was already triggered
            was_triggered = bool(budget.alert_triggered)

            # Update spent amount
            budget.update_spent(amount)
            budget.updated_at = utc_now()

            sess.flush()
            sess.expunge(budget)

            # Publish events if thresholds crossed
            if self.event_bus:
                # Alert threshold crossed
                if not was_triggered and budget.alert_triggered:
                    self.event_bus.publish(
                        SystemEvent(
                            event_type="cost.budget.warning",
                            entity_type="budget",
                            entity_id=str(budget.id),
                            payload={
                                "scope_type": budget.scope_type,
                                "scope_id": budget.scope_id,
                                "limit": budget.limit_amount,
                                "spent": budget.spent_amount,
                                "remaining": budget.remaining_amount,
                                "threshold_percent": budget.alert_threshold * 100,
                            },
                        )
                    )

                # Budget exceeded
                if budget.is_exceeded():
                    self.event_bus.publish(
                        SystemEvent(
                            event_type="cost.budget.exceeded",
                            entity_type="budget",
                            entity_id=str(budget.id),
                            payload={
                                "scope_type": budget.scope_type,
                                "scope_id": budget.scope_id,
                                "limit": budget.limit_amount,
                                "spent": budget.spent_amount,
                                "overage": budget.spent_amount - budget.limit_amount,
                            },
                        )
                    )

            return budget

        if session:
            return _update(session)
        else:
            with self.db.get_session() as sess:
                budget = _update(sess)
                sess.commit()
                return budget

    def list_budgets(
        self,
        scope_type: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> list[Budget]:
        """List all budgets, optionally filtered by scope type."""

        def _list(sess: Session) -> list[Budget]:
            query = select(Budget)

            if scope_type:
                query = query.where(Budget.scope_type == scope_type)

            query = query.order_by(Budget.created_at.desc())

            result = sess.execute(query)
            budgets = list(result.scalars().all())

            # Expunge objects so they can be used after session closes
            for budget in budgets:
                sess.expunge(budget)

            return budgets

        if session:
            return _list(session)
        else:
            with self.db.get_session() as sess:
                return _list(sess)

    def is_budget_available(
        self,
        scope_type: str,
        estimated_cost: float,
        scope_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> bool:
        """Check if budget has enough remaining for an estimated cost.

        Args:
            scope_type: Budget scope type
            estimated_cost: Estimated cost to check against budget
            scope_id: Scope identifier
            session: Database session

        Returns:
            True if budget available or no budget exists, False if budget exceeded
        """
        budget = self.get_budget(scope_type, scope_id, session)

        # If no budget exists, allow operation
        if not budget:
            return True

        # Check if adding this cost would exceed budget
        return (budget.spent_amount + estimated_cost) <= budget.limit_amount
