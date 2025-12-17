"""Claude Session Transcript model for storing Claude Code session transcripts.

Enables cross-sandbox session resumption by storing session transcripts
as base64-encoded JSONL files in the database.

IMPORTANT: Do NOT use 'metadata' as an attribute name - it's reserved by SQLAlchemy!
We use 'session_metadata' instead to store additional session information.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class ClaudeSessionTranscript(Base):
    """Stores Claude Code session transcripts for cross-sandbox resumption.

    When a Claude Code conversation completes or is paused, the session transcript
    (JSONL file) can be stored in this table. Later, when starting a new sandbox,
    the transcript can be retrieved and written to the local session store, enabling
    the conversation to resume with full history.

    Attributes:
        id: Unique identifier (UUID)
        session_id: Claude Code session ID (unique, indexed)
        transcript_b64: Base64-encoded JSONL transcript content
        sandbox_id: Daytona sandbox ID where session was created
        task_id: Optional task ID associated with this session
        session_metadata: JSONB field with additional metadata (cost, turns, model, etc.)
        created_at: When the transcript was first stored
        updated_at: When the transcript was last updated
    """

    __tablename__ = "claude_session_transcripts"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )

    session_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Claude Code session ID (UUID format)",
    )

    transcript_b64: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Base64-encoded JSONL transcript file content for cross-sandbox resumption",
    )

    sandbox_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Daytona sandbox ID where this session was created",
    )

    task_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional task ID associated with this session",
    )

    # Session metadata (cost, turns, model, etc.)
    # Using 'session_metadata' to avoid conflict with SQLAlchemy's reserved 'metadata' attribute
    session_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional session metadata: cost, turns, model, etc.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        comment="When the session transcript was first stored",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        comment="When the session transcript was last updated",
    )

    def __repr__(self) -> str:
        return f"<ClaudeSessionTranscript(id={self.id}, session_id={self.session_id}, sandbox_id={self.sandbox_id})>"
