"""PreviewSession model for live preview lifecycle tracking.

Phase 1: Backend Preview Routes + DaytonaSpawner Integration.

Tracks preview sessions per sandbox so any frontend task can expose a live preview URL.
The frontend can poll or receive WebSocket updates when a preview becomes READY.
"""

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class PreviewStatus(str, enum.Enum):
    """Status of a live preview session."""

    PENDING = "pending"  # Sandbox created, dev server not yet started
    STARTING = "starting"  # Dev server starting up
    READY = "ready"  # Preview URL available and responding
    STOPPED = "stopped"  # Manually stopped or sandbox deleted
    FAILED = "failed"  # Dev server failed to start


class PreviewSession(Base):
    """PreviewSession tracks a live preview for a sandbox.

    When a frontend task spawns a sandbox, a PreviewSession is created to
    track the dev server lifecycle and expose the preview URL to the frontend.

    Attributes:
        id: Unique preview session identifier (UUID)
        sandbox_id: Daytona sandbox ID (unique — one preview per sandbox)
        task_id: Optional FK to the task that triggered this preview
        project_id: Optional FK to the project
        user_id: Optional FK to the user who owns the preview
        status: Current preview lifecycle status
        preview_url: Public Daytona preview URL (set when READY)
        preview_token: Auth token from get_preview_link()
        port: Dev server port (default 3000)
        framework: Detected framework (vite, next, vue, etc.)
        session_id: Daytona session ID for the dev server process
        command_id: Daytona command ID for the dev server process
        error_message: Error details if preview failed to start
        started_at: When the dev server was started
        ready_at: When the preview became available
        stopped_at: When the preview was stopped
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "preview_sessions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    sandbox_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Daytona sandbox ID (one preview per sandbox)",
    )
    task_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Task that triggered this preview",
    )
    project_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        index=True,
        comment="User who owns this preview session",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=PreviewStatus.PENDING.value,
        index=True,
    )
    preview_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Public Daytona preview URL",
    )
    preview_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Auth token from sandbox.get_preview_link()",
    )
    port: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3000,
        comment="Dev server port",
    )
    framework: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Detected framework: vite, next, vue, etc.",
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Daytona session ID for dev server process",
    )
    command_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Daytona command ID for dev server process",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if preview failed to start",
    )

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When dev server was started",
    )
    ready_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When preview became available",
    )
    stopped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When preview was stopped",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    def __repr__(self) -> str:
        return (
            f"<PreviewSession(id={self.id[:8]}, sandbox_id={self.sandbox_id}, "
            f"status={self.status}, port={self.port})>"
        )

    @property
    def is_active(self) -> bool:
        """Check if preview is in an active state."""
        return self.status in (
            PreviewStatus.PENDING.value,
            PreviewStatus.STARTING.value,
            PreviewStatus.READY.value,
        )
