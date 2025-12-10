from __future__ import annotations

from datetime import datetime

from omoi_os.utils.datetime import utc_now
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String, index=True)
    created_by_agent_id: Mapped[str] = mapped_column(String, nullable=False)
    assigned_agent_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    ticket_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    parent_ticket_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("tickets.id"), nullable=True
    )
    related_task_ids: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    related_ticket_ids: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    embedding: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    embedding_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Optional pgvector column for semantic search
    # Dimension must match EmbeddingSettings.dimensions (default 1536)
    embedding_vector: Mapped[Optional[list[float]]] = mapped_column(
        Vector(1536), nullable=True
    )

    blocked_by_ticket_ids: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )

    parent: Mapped["Ticket"] = relationship(remote_side=[id])
    comments: Mapped[list["TicketComment"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
    history: Mapped[list["TicketHistory"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
    commits: Mapped[list["TicketCommit"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_tickets_workflow_status", "workflow_id", "status"),
        Index("idx_tickets_created_at", "created_at"),
        # Vector index (created in init_db to control extension availability)
    )


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ticket_id: Mapped[str] = mapped_column(
        String, ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[str] = mapped_column(String, index=True)

    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    comment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mentions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    attachments: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    ticket: Mapped["Ticket"] = relationship(back_populates="comments")

    __table_args__ = (Index("idx_comments_created_at", "created_at"),)


class TicketHistory(Base):
    __tablename__ = "ticket_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(
        String, ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[str] = mapped_column(String, index=True)

    change_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    field_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    change_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    change_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="history")


class TicketCommit(Base):
    __tablename__ = "ticket_commits"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ticket_id: Mapped[str] = mapped_column(
        String, ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[str] = mapped_column(String, index=True)

    commit_sha: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    commit_message: Mapped[str] = mapped_column(Text, nullable=False)
    commit_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    files_changed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    insertions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    deletions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    files_list: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    link_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    ticket: Mapped["Ticket"] = relationship(back_populates="commits")

    __table_args__ = (
        Index("idx_unique_ticket_commit", "ticket_id", "commit_sha", unique=True),
    )


class BoardConfig(Base):
    __tablename__ = "board_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    columns: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ticket_types: Mapped[dict] = mapped_column(JSONB, nullable=False)
    default_ticket_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    initial_status: Mapped[str] = mapped_column(String(50), nullable=False)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
