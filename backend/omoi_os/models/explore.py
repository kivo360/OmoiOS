"""Code exploration models for AI-powered codebase Q&A."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.project import Project


class ExploreConversation(Base):
    """Conversation session for code exploration Q&A."""

    __tablename__ = "explore_conversations"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: f"conv-{uuid4().hex[:8]}"
    )
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    last_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Preview of last message for listing"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="conversations")
    messages: Mapped[list["ExploreMessage"]] = relationship(
        "ExploreMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ExploreMessage.timestamp",
    )

    __table_args__ = {"comment": "Code exploration conversation sessions"}


class ExploreMessage(Base):
    """Individual message in a code exploration conversation."""

    __tablename__ = "explore_messages"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: f"msg-{uuid4().hex[:8]}"
    )
    conversation_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("explore_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Message role: user or assistant",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    # Relationships
    conversation: Mapped["ExploreConversation"] = relationship(
        "ExploreConversation", back_populates="messages"
    )

    __table_args__ = {"comment": "Messages in code exploration conversations"}
