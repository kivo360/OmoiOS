"""Learned pattern model for task pattern recognition."""

import uuid
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from sqlalchemy import String, Float, Integer, DateTime
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from whenever import Instant

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


@dataclass
class TaskPattern:
    """
    Data class for task patterns (used by Quality Squad and other consumers).

    This is the contract interface exported by the Memory Squad.
    """

    pattern_id: str
    pattern_type: str
    task_type_pattern: str
    success_indicators: List[str]
    failure_indicators: List[str]
    recommended_context: Dict[str, Any]
    confidence_score: float
    usage_count: int

    @classmethod
    def from_model(cls, pattern: "LearnedPattern") -> "TaskPattern":
        """Convert a LearnedPattern model to a TaskPattern data class."""
        return cls(
            pattern_id=pattern.id,
            pattern_type=pattern.pattern_type,
            task_type_pattern=pattern.task_type_pattern,
            success_indicators=pattern.success_indicators or [],
            failure_indicators=pattern.failure_indicators or [],
            recommended_context=pattern.recommended_context or {},
            confidence_score=pattern.confidence_score,
            usage_count=pattern.usage_count,
        )


class LearnedPattern(Base):
    """
    Stores learned patterns from task execution history.

    Used for pattern matching, quality prediction, and context suggestions.
    """

    __tablename__ = "learned_patterns"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    pattern_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: success, failure, optimization",
    )
    task_type_pattern: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Regex or template matching task descriptions",
    )
    success_indicators: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of indicators that suggest success",
    )
    failure_indicators: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of indicators that suggest failure",
    )
    recommended_context: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Context recommendations for matching tasks",
    )
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        ARRAY(Float, dimensions=1),
        nullable=True,
        comment="1536-dimensional pattern embedding",
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        index=True,
        comment="Confidence score (0.0 to 1.0)",
    )
    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        index=True,
        comment="Number of times this pattern was applied",
    )
    created_at: Mapped[Instant] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        comment="When this pattern was first learned",
    )
    updated_at: Mapped[Instant] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        comment="Last time this pattern was updated",
    )

    def __repr__(self) -> str:
        return (
            f"<LearnedPattern(id={self.id}, type={self.pattern_type}, "
            f"confidence={self.confidence_score:.2f}, usage={self.usage_count})>"
        )

    def increment_usage(self) -> None:
        """Increment usage counter when this pattern is applied."""
        self.usage_count += 1
        self.updated_at = utc_now()

    def update_confidence(self, new_score: float) -> None:
        """Update confidence score (0.0 to 1.0)."""
        if not 0.0 <= new_score <= 1.0:
            raise ValueError(
                f"Confidence score must be between 0.0 and 1.0, got {new_score}"
            )
        self.confidence_score = new_score
        self.updated_at = utc_now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "pattern_type": self.pattern_type,
            "task_type_pattern": self.task_type_pattern,
            "success_indicators": self.success_indicators or [],
            "failure_indicators": self.failure_indicators or [],
            "recommended_context": self.recommended_context or {},
            "has_embedding": self.embedding is not None,
            "confidence_score": self.confidence_score,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_pattern(self) -> TaskPattern:
        """Convert to TaskPattern data class (contract interface)."""
        return TaskPattern.from_model(self)
