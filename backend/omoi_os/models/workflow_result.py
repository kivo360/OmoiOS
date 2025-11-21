"""Workflow result model for workflow-level completion."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class WorkflowResult(Base):
    """Workflow-level result submission.
    
    Marks workflow completion with definitive solution or final deliverable.
    Triggers automatic validation when has_result=true in workflow config.
    Can trigger workflow termination based on on_result_found configuration.
    """

    __tablename__ = "workflow_results"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    workflow_id: Mapped[str] = mapped_column(
        String, ForeignKey("tickets.id"), nullable=False, index=True
    )  # ticket_id in our system
    agent_id: Mapped[str] = mapped_column(
        String, ForeignKey("agents.id"), nullable=False, index=True
    )

    # Result content
    markdown_file_path: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Path to result markdown file
    explanation: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Optional explanation of what was accomplished
    evidence: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Array of evidence items

    # Validation metadata
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending_validation", index=True
    )  # pending_validation, validated, rejected
    validated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    validation_feedback: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Validator's feedback on the result

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

