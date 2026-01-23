"""Sandbox Resource Metrics model for tracking CPU/memory/disk usage.

This module provides models for:
1. SandboxResource - Tracks current resource allocation per sandbox
2. SandboxResourceMetrics - Time-series metrics for resource usage

IMPORTANT: Do NOT use 'metadata' as an attribute name - it's reserved by SQLAlchemy!
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class SandboxResource(Base):
    """Tracks current resource allocation and usage for a sandbox.

    This table stores the current state of resource allocation and real-time
    usage metrics for each active sandbox. Updated via heartbeats.

    Attributes:
        id: Unique identifier (UUID)
        sandbox_id: ID of the sandbox this resource record belongs to
        task_id: Optional task ID this sandbox is executing
        agent_id: Optional agent ID associated with this sandbox

        # Allocation (what was requested/configured)
        allocated_cpu_cores: Number of CPU cores allocated
        allocated_memory_gb: Memory allocated in GiB
        allocated_disk_gb: Disk space allocated in GiB

        # Current Usage (from monitoring)
        cpu_usage_percent: Current CPU utilization (0-100)
        memory_usage_percent: Current memory utilization (0-100)
        memory_used_mb: Current memory used in MB
        disk_usage_percent: Current disk utilization (0-100)
        disk_used_gb: Current disk used in GiB

        # Status
        status: Sandbox status (creating, running, completed, failed, terminated)
        last_updated: Last time metrics were updated
        created_at: When this record was created
    """

    __tablename__ = "sandbox_resources"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    sandbox_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agent_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Allocation settings
    allocated_cpu_cores: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    allocated_memory_gb: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    allocated_disk_gb: Mapped[int] = mapped_column(Integer, nullable=False, default=8)

    # Current usage metrics
    cpu_usage_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    memory_usage_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    memory_used_mb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    disk_usage_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    disk_used_gb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="creating", index=True
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    def __repr__(self) -> str:
        return (
            f"<SandboxResource(sandbox_id={self.sandbox_id}, "
            f"cpu={self.cpu_usage_percent:.1f}%, mem={self.memory_usage_percent:.1f}%)>"
        )


class SandboxResourceMetrics(Base):
    """Time-series metrics for sandbox resource usage.

    Stores historical resource usage data for trending and analysis.
    Each row represents a snapshot of resource usage at a specific time.

    Attributes:
        id: Unique identifier (UUID)
        sandbox_id: ID of the sandbox
        cpu_usage_percent: CPU utilization at this timestamp (0-100)
        memory_usage_percent: Memory utilization at this timestamp (0-100)
        memory_used_mb: Memory used in MB
        disk_usage_percent: Disk utilization at this timestamp (0-100)
        disk_used_gb: Disk used in GiB
        recorded_at: When this metric was recorded
    """

    __tablename__ = "sandbox_resource_metrics"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    sandbox_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Resource usage at this point in time
    cpu_usage_percent: Mapped[float] = mapped_column(Float, nullable=False)
    memory_usage_percent: Mapped[float] = mapped_column(Float, nullable=False)
    memory_used_mb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    disk_usage_percent: Mapped[float] = mapped_column(Float, nullable=False)
    disk_used_gb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    # Composite index for efficient time-series queries
    __table_args__ = (
        Index("ix_sandbox_resource_metrics_sandbox_time", "sandbox_id", "recorded_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<SandboxResourceMetrics(sandbox_id={self.sandbox_id}, "
            f"cpu={self.cpu_usage_percent:.1f}%, mem={self.memory_usage_percent:.1f}%, "
            f"recorded_at={self.recorded_at})>"
        )
