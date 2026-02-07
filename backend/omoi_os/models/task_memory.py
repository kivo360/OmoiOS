"""Task memory model for storing execution history with embeddings."""

import uuid
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import (
    String,
    Text,
    Boolean,
    Integer,
    Float,
    DateTime,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from whenever import Instant

from omoi_os.models.base import Base
from omoi_os.models.memory_type import MemoryType
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.task import Task


class TaskMemory(Base):
    """
    Stores execution history and learned context from completed tasks.

    Used for pattern recognition and context retrieval for similar tasks.
    """

    __tablename__ = "task_memories"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    task_id: Mapped[str] = mapped_column(
        String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    execution_summary: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Summary of task execution and results"
    )
    memory_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=MemoryType.DISCOVERY.value,
        index=True,
        comment="Memory type: error_fix, discovery, decision, learning, warning, codebase_knowledge (REQ-MEM-TAX-001)",
    )
    # ACE workflow fields (REQ-MEM-ACE-001)
    goal: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="What the agent was trying to accomplish (REQ-MEM-ACE-001)",
    )
    result: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="What actually happened (REQ-MEM-ACE-001)"
    )
    feedback: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Output from environment (stdout, stderr, test results) (REQ-MEM-ACE-001)",
    )
    tool_usage: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Tools used during task execution (REQ-MEM-ACE-001)",
    )
    context_embedding: Mapped[Optional[List[float]]] = mapped_column(
        ARRAY(Float, dimensions=1),
        nullable=True,
        comment="1536-dimensional embedding vector for similarity search",
    )
    success: Mapped[bool] = mapped_column(
        Boolean, nullable=False, index=True, comment="Whether execution was successful"
    )
    error_patterns: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Error patterns extracted from failed executions",
    )
    learned_at: Mapped[Instant] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
        comment="When this memory was created",
    )
    reused_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of times this memory was used for context",
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="memories")

    def __repr__(self) -> str:
        return (
            f"<TaskMemory(id={self.id}, task_id={self.task_id}, "
            f"success={self.success}, reused_count={self.reused_count})>"
        )

    def increment_reuse(self) -> None:
        """Increment the reuse counter when this memory is referenced."""
        self.reused_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "execution_summary": self.execution_summary,
            "memory_type": self.memory_type,
            "goal": self.goal,
            "result": self.result,
            "feedback": self.feedback,
            "tool_usage": self.tool_usage,
            "has_embedding": self.context_embedding is not None,
            "embedding_dimensions": (
                len(self.context_embedding) if self.context_embedding else 0
            ),
            "success": self.success,
            "error_patterns": self.error_patterns,
            "learned_at": self.learned_at.isoformat() if self.learned_at else None,
            "reused_count": self.reused_count,
        }
