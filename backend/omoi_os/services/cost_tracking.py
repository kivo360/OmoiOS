"""Cost tracking service for LLM API usage monitoring."""

from pathlib import Path
from typing import Optional

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from omoi_os.models.cost_record import CostRecord
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now


class CostTrackingService:
    """Service for tracking and analyzing LLM API costs.

    Responsibilities:
    - Record LLM API costs per task/agent
    - Calculate costs using provider-specific pricing
    - Aggregate costs by task, agent, phase, ticket
    - Forecast future costs based on queue depth
    - Publish cost events for budget enforcement
    """

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
        cost_models_path: Optional[str] = None,
    ):
        self.db = db
        self.event_bus = event_bus

        # Load cost models from YAML
        if cost_models_path is None:
            config_dir = Path(__file__).parent.parent / "config"
            cost_models_path = str(config_dir / "cost_models.yaml")

        with open(cost_models_path, "r") as f:
            self.cost_config = yaml.safe_load(f)

        self.providers = self.cost_config.get("providers", {})
        self.defaults = self.cost_config.get("defaults", {})

    def get_model_pricing(self, provider: str, model: str) -> dict:
        """Get pricing information for a specific provider and model.

        Returns:
            dict with 'prompt_token_cost' and 'completion_token_cost' keys
        """
        # Check if provider exists in config
        if provider not in self.providers:
            return self.defaults

        provider_models = self.providers[provider]

        # Check if model exists for this provider
        if model not in provider_models:
            return self.defaults

        return provider_models[model]

    def calculate_cost(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> dict:
        """Calculate cost breakdown for token usage.

        Returns:
            dict with 'prompt_cost', 'completion_cost', and 'total_cost'
        """
        pricing = self.get_model_pricing(provider, model)

        prompt_cost = prompt_tokens * pricing["prompt_token_cost"]
        completion_cost = completion_tokens * pricing["completion_token_cost"]
        total_cost = prompt_cost + completion_cost

        return {
            "prompt_cost": prompt_cost,
            "completion_cost": completion_cost,
            "total_cost": total_cost,
        }

    def record_llm_cost(
        self,
        task_id: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        agent_id: Optional[str] = None,
        sandbox_id: Optional[str] = None,
        billing_account_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> CostRecord:
        """Record LLM API cost for a task execution.

        Args:
            task_id: Task that incurred the cost
            provider: LLM provider ('openai', 'anthropic', etc.)
            model: Model name ('gpt-4', 'claude-sonnet', etc.)
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            agent_id: Agent that executed the task (optional)
            sandbox_id: Sandbox where execution occurred (optional)
            billing_account_id: Billing account for cost aggregation (optional)
            session: Database session (creates new if not provided)

        Returns:
            Created CostRecord
        """
        # Calculate cost breakdown
        costs = self.calculate_cost(provider, model, prompt_tokens, completion_tokens)
        total_tokens = prompt_tokens + completion_tokens

        def _record(sess: Session) -> CostRecord:
            # Create cost record
            cost_record = CostRecord(
                task_id=task_id,
                agent_id=agent_id,
                sandbox_id=sandbox_id,
                billing_account_id=billing_account_id,
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                prompt_cost=costs["prompt_cost"],
                completion_cost=costs["completion_cost"],
                total_cost=costs["total_cost"],
                recorded_at=utc_now(),
            )
            sess.add(cost_record)
            sess.flush()
            sess.expunge(cost_record)  # Detach from session
            return cost_record

        if session:
            record = _record(session)
        else:
            with self.db.get_session() as sess:
                record = _record(sess)
                sess.commit()

        # Publish cost event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="cost.recorded",
                    entity_type="cost_record",
                    entity_id=str(record.id),
                    payload={
                        "task_id": task_id,
                        "agent_id": agent_id,
                        "sandbox_id": sandbox_id,
                        "billing_account_id": billing_account_id,
                        "provider": provider,
                        "model": model,
                        "total_cost": costs["total_cost"],
                        "total_tokens": total_tokens,
                    },
                )
            )

        return record

    def record_sandbox_cost(
        self,
        task_id: str,
        sandbox_id: str,
        cost_usd: float,
        input_tokens: int,
        output_tokens: int,
        model: str = "claude-sonnet-4",
        provider: str = "anthropic",
        agent_id: Optional[str] = None,
        billing_account_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> CostRecord:
        """Record cost from sandbox agent.completed event.

        This is called when a sandbox reports completion with cost data.
        Uses the reported cost_usd directly instead of calculating from tokens.

        Args:
            task_id: Task that incurred the cost
            sandbox_id: Sandbox where execution occurred
            cost_usd: Total cost reported by the sandbox (in USD)
            input_tokens: Input/prompt tokens used
            output_tokens: Output/completion tokens used
            model: Model used (default: claude-sonnet-4)
            provider: Provider (default: anthropic)
            agent_id: Agent that executed the task (optional)
            billing_account_id: Billing account for cost aggregation (optional)
            session: Database session (creates new if not provided)

        Returns:
            Created CostRecord
        """
        total_tokens = input_tokens + output_tokens

        # Estimate cost breakdown (assume ~70/30 split for prompt/completion cost)
        prompt_cost = cost_usd * 0.3  # Input tokens are usually cheaper
        completion_cost = cost_usd * 0.7  # Output tokens are usually more expensive

        def _record(sess: Session) -> CostRecord:
            cost_record = CostRecord(
                task_id=task_id,
                agent_id=agent_id,
                sandbox_id=sandbox_id,
                billing_account_id=billing_account_id,
                provider=provider,
                model=model,
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=total_tokens,
                prompt_cost=prompt_cost,
                completion_cost=completion_cost,
                total_cost=cost_usd,
                recorded_at=utc_now(),
            )
            sess.add(cost_record)
            sess.flush()
            sess.expunge(cost_record)
            return cost_record

        if session:
            record = _record(session)
        else:
            with self.db.get_session() as sess:
                record = _record(sess)
                sess.commit()

        # Publish cost event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="cost.recorded",
                    entity_type="cost_record",
                    entity_id=str(record.id),
                    payload={
                        "task_id": task_id,
                        "sandbox_id": sandbox_id,
                        "billing_account_id": billing_account_id,
                        "provider": provider,
                        "model": model,
                        "total_cost": cost_usd,
                        "total_tokens": total_tokens,
                    },
                )
            )

        return record

    def get_billing_account_costs(
        self,
        billing_account_id: str,
        session: Optional[Session] = None,
    ) -> list[CostRecord]:
        """Get all cost records for a billing account."""

        def _get(sess: Session) -> list[CostRecord]:
            result = sess.execute(
                select(CostRecord).where(
                    CostRecord.billing_account_id == billing_account_id
                )
            )
            return list(result.scalars().all())

        if session:
            return _get(session)
        else:
            with self.db.get_session() as sess:
                return _get(sess)

    def get_sandbox_costs(
        self,
        sandbox_id: str,
        session: Optional[Session] = None,
    ) -> list[CostRecord]:
        """Get all cost records for a specific sandbox."""

        def _get(sess: Session) -> list[CostRecord]:
            result = sess.execute(
                select(CostRecord).where(CostRecord.sandbox_id == sandbox_id)
            )
            return list(result.scalars().all())

        if session:
            return _get(session)
        else:
            with self.db.get_session() as sess:
                return _get(sess)

    def get_task_costs(
        self, task_id: str, session: Optional[Session] = None
    ) -> list[CostRecord]:
        """Get all cost records for a specific task."""

        def _get(sess: Session) -> list[CostRecord]:
            result = sess.execute(
                select(CostRecord).where(CostRecord.task_id == task_id)
            )
            return list(result.scalars().all())

        if session:
            return _get(session)
        else:
            with self.db.get_session() as sess:
                return _get(sess)

    def get_agent_costs(
        self, agent_id: str, session: Optional[Session] = None
    ) -> list[CostRecord]:
        """Get all cost records for a specific agent."""

        def _get(sess: Session) -> list[CostRecord]:
            result = sess.execute(
                select(CostRecord).where(CostRecord.agent_id == agent_id)
            )
            return list(result.scalars().all())

        if session:
            return _get(session)
        else:
            with self.db.get_session() as sess:
                return _get(sess)

    def get_cost_summary(
        self,
        scope_type: str,
        scope_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> dict:
        """Get cost summary for a specific scope (ticket, agent, phase, billing_account, global).

        Args:
            scope_type: 'ticket', 'agent', 'phase', 'billing_account', or 'global'
            scope_id: ID of the scoped entity (required unless scope_type='global')
            session: Database session

        Returns:
            dict with 'total_cost', 'total_tokens', 'record_count', breakdown by provider/model
        """

        def _get_summary(sess: Session) -> dict:
            query = select(
                CostRecord.provider,
                CostRecord.model,
                func.sum(CostRecord.total_cost).label("total_cost"),
                func.sum(CostRecord.total_tokens).label("total_tokens"),
                func.count(CostRecord.id).label("record_count"),
            )

            # Apply scope filter
            if scope_type == "agent":
                query = query.where(CostRecord.agent_id == scope_id)
            elif scope_type == "task":
                query = query.where(CostRecord.task_id == scope_id)
            elif scope_type == "ticket":
                # Join with tasks to filter by ticket
                query = query.join(Task, CostRecord.task_id == Task.id).where(
                    Task.ticket_id == scope_id
                )
            elif scope_type == "phase":
                # Join with tasks to filter by phase
                query = query.join(Task, CostRecord.task_id == Task.id).where(
                    Task.phase_id == scope_id
                )
            elif scope_type == "billing_account":
                query = query.where(CostRecord.billing_account_id == scope_id)
            # 'global' scope has no filter

            query = query.group_by(CostRecord.provider, CostRecord.model)

            result = sess.execute(query)
            rows = result.all()

            # Calculate totals and breakdown
            total_cost = 0.0
            total_tokens = 0
            record_count = 0
            breakdown = []

            for row in rows:
                total_cost += row.total_cost or 0.0
                total_tokens += row.total_tokens or 0
                record_count += row.record_count or 0
                breakdown.append(
                    {
                        "provider": row.provider,
                        "model": row.model,
                        "cost": row.total_cost,
                        "tokens": row.total_tokens,
                        "records": row.record_count,
                    }
                )

            return {
                "scope_type": scope_type,
                "scope_id": scope_id,
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "record_count": record_count,
                "breakdown": breakdown,
            }

        if session:
            return _get_summary(session)
        else:
            with self.db.get_session() as sess:
                return _get_summary(sess)

    def forecast_costs(
        self,
        pending_task_count: int,
        avg_tokens_per_task: Optional[int] = None,
        provider: str = "anthropic",
        model: str = "claude-sonnet-4.5",
    ) -> dict:
        """Forecast costs for pending tasks.

        Args:
            pending_task_count: Number of pending tasks in queue
            avg_tokens_per_task: Average tokens per task (uses config default if not provided)
            provider: LLM provider to use for cost calculation
            model: Model to use for cost calculation

        Returns:
            dict with 'estimated_cost', 'estimated_tokens', 'task_count'
        """
        if avg_tokens_per_task is None:
            forecasting_config = self.cost_config.get("forecasting", {})
            avg_tokens_per_task = forecasting_config.get("avg_tokens_per_task", 5000)

        # Assume 50/50 split between prompt and completion tokens
        avg_prompt_tokens = avg_tokens_per_task // 2
        avg_completion_tokens = avg_tokens_per_task // 2

        # Calculate cost per task
        cost_per_task = self.calculate_cost(
            provider, model, avg_prompt_tokens, avg_completion_tokens
        )["total_cost"]

        # Apply buffer multiplier for safety
        forecasting_config = self.cost_config.get("forecasting", {})
        buffer_multiplier = forecasting_config.get("buffer_multiplier", 1.2)

        estimated_cost = cost_per_task * pending_task_count * buffer_multiplier
        estimated_tokens = avg_tokens_per_task * pending_task_count

        return {
            "task_count": pending_task_count,
            "estimated_cost": estimated_cost,
            "estimated_tokens": estimated_tokens,
            "avg_tokens_per_task": avg_tokens_per_task,
            "buffer_multiplier": buffer_multiplier,
        }
