"""Quality gate model for advanced validation rules."""

import uuid
from typing import Optional, Dict, Any

from sqlalchemy import String, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base


class QualityGate(Base):
    """
    Advanced quality gate definitions.

    Extends Phase 2 phase gates with ML-based predictions and
    quality metric requirements.
    """

    __tablename__ = "quality_gates"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    phase_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Phase this gate applies to",
    )
    gate_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: quality, ml_prediction, custom",
    )
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Gate name/description"
    )
    requirements: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Quality requirements: {min_test_coverage: 80, max_lint_errors: 0, ...}",
    )
    predictor_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="ML predictor model name (if ml_prediction type)",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether gate is active",
    )
    failure_action: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Action on failure: block, warn, log",
        default="block",
    )

    def __repr__(self) -> str:
        return (
            f"<QualityGate(id={self.id}, phase={self.phase_id}, "
            f"type={self.gate_type}, enabled={self.enabled})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "phase_id": self.phase_id,
            "gate_type": self.gate_type,
            "name": self.name,
            "requirements": self.requirements,
            "predictor_model": self.predictor_model,
            "enabled": self.enabled,
            "failure_action": self.failure_action,
        }

    def get_requirement(self, key: str, default: Any = None) -> Any:
        """Get a specific requirement value."""
        return self.requirements.get(key, default)
