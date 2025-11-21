"""Workspace models for workspace isolation system."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.agent import Agent


class AgentWorkspace(Base):
    """Tracks workspace paths, Git branches, and parent-child relationships."""

    __tablename__ = "agent_workspaces"

    agent_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agents.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Agent identifier (foreign key to agents table)",
    )
    working_directory: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Absolute path to workspace directory",
    )
    branch_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Git branch name for this workspace (e.g., workspace-agent-123)",
    )
    parent_commit: Mapped[Optional[str]] = mapped_column(
        String(40),
        nullable=True,
        comment="Parent commit SHA for workspace inheritance",
    )
    parent_agent_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Parent agent ID for workspace inheritance",
    )
    repo_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Repository URL that was cloned into this workspace",
    )
    base_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="main",
        comment="Base branch that workspace was created from",
    )
    workspace_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="local",
        comment="Workspace type: local, docker, kubernetes, remote",
    )
    workspace_config: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Workspace-specific configuration (e.g., Docker port, image)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether workspace is currently active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", foreign_keys=[agent_id])
    parent_agent: Mapped[Optional["Agent"]] = relationship(
        "Agent", foreign_keys=[parent_agent_id], remote_side="Agent.id"
    )


class WorkspaceCommit(Base):
    """Stores checkpoint commits for validation, debugging, and auditing."""

    __tablename__ = "workspace_commits"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    agent_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Agent identifier",
    )
    commit_sha: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
        comment="Git commit SHA",
    )
    files_changed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of files changed in this commit",
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Git commit message",
    )
    iteration: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Iteration number for validation checkpoints",
    )
    commit_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="validation",
        index=True,
        comment="Commit type: validation, checkpoint, merge, manual",
    )
    commit_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional commit metadata (stats, diff summary, etc.)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", foreign_keys=[agent_id])


class MergeConflictResolution(Base):
    """Logs automatic conflict resolutions and merge metadata."""

    __tablename__ = "merge_conflict_resolutions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    agent_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Agent identifier",
    )
    merge_commit_sha: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
        comment="Git commit SHA of the merge",
    )
    target_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Target branch that was merged into",
    )
    source_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Source workspace branch that was merged",
    )
    conflicts_resolved: Mapped[list[str]] = mapped_column(
        PG_ARRAY(String(1000)),
        nullable=False,
        default=list,
        comment="List of file paths that had conflicts resolved",
    )
    resolution_strategy: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="newest_file_wins",
        comment="Strategy used for conflict resolution",
    )
    total_conflicts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of conflicts resolved",
    )
    merge_extra_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional merge metadata (stats, timing, etc.)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", foreign_keys=[agent_id])
