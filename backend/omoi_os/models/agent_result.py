"""Agent result model for task-level achievements."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class AgentResult(Base):
    """Task-level result submission.
    
    Agents submit results for individual tasks with comprehensive evidence
    and documentation. Multiple results can be submitted per task.
    Results are immutable and tracked through verification states.
    """

    __tablename__ = "agent_results"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    agent_id: Mapped[str] = mapped_column(
        String, ForeignKey("agents.id"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(
        String, ForeignKey("tasks.id"), nullable=False, index=True
    )

    # Content storage
    markdown_content: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Full markdown content
    markdown_file_path: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Source file path

    # Classification
    result_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # implementation, analysis, fix, design, test, documentation
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    # Verification tracking
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unverified", index=True
    )  # unverified, verified, disputed
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_by_validation_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Links to validation_reviews table when available

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

