"""Cost tracking models for LLM API usage."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class CostRecord(Base):
    """Record of LLM API costs for a task execution.

    Tracks token usage and costs for each LLM API call made during task execution.
    Supports multiple providers (OpenAI, Anthropic, etc.) with different pricing models.

    Billing Integration:
    - Links to billing_account_id for cost aggregation per organization
    - Automatically created from sandbox agent.completed events
    - Used to track workflow costs for tier usage limits
    """

    __tablename__ = "cost_records"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )

    # Task and agent association
    task_id: Mapped[str] = mapped_column(
        String, ForeignKey("tasks.id"), nullable=False, index=True
    )
    agent_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("agents.id"), nullable=True, index=True
    )

    # Sandbox association (for linking to sandbox events)
    sandbox_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )

    # Billing association (for cost aggregation per organization)
    billing_account_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("billing_accounts.id"), nullable=True, index=True
    )
    
    # LLM provider information
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # 'openai', 'anthropic', etc.
    model: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # 'gpt-4', 'claude-sonnet', etc.
    
    # Token usage
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Cost calculation (in USD)
    prompt_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    completion_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    
    # Metadata
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    
    # Relationships
    task = relationship("Task", back_populates="cost_records")
    agent = relationship("Agent", back_populates="cost_records")
    
    def __repr__(self) -> str:
        return (
            f"<CostRecord(id={self.id}, task_id={self.task_id}, "
            f"provider={self.provider}, model={self.model}, "
            f"total_cost=${self.total_cost:.4f})>"
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "sandbox_id": self.sandbox_id,
            "billing_account_id": str(self.billing_account_id) if self.billing_account_id else None,
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "prompt_cost": self.prompt_cost,
            "completion_cost": self.completion_cost,
            "total_cost": self.total_cost,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }

