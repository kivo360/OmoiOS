"""Sandbox Resource model for tracking resource allocation and usage per worker.

This model stores both the allocated resources (limits) and current usage
for each sandbox worker, enabling real-time monitoring and dynamic adjustment.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class SandboxResource(Base):
    """SandboxResource tracks resource allocation and usage for sandbox workers.

    Stores both allocation (limits) and current usage metrics, enabling:
    - Real-time monitoring of CPU/memory/disk per worker
    - Dynamic resource adjustment without restart
    - Resource usage analytics and alerts

    Attributes:
        id: Unique identifier (UUID)
        sandbox_id: ID of the sandbox this resource belongs to
        task_id: Optional task ID associated with this sandbox
        agent_id: Optional agent ID running in this sandbox

        # Allocation limits (what's been assigned)
        cpu_allocated: CPU cores allocated (e.g., 2.0)
        memory_allocated_mb: Memory allocated in MB (e.g., 4096)
        disk_allocated_gb: Disk space allocated in GB (e.g., 8)

        # Current usage metrics
        cpu_usage_percent: Current CPU usage as percentage (0-100)
        memory_usage_mb: Current memory usage in MB
        disk_usage_gb: Current disk usage in GB

        # Timestamps
        created_at: When resource record was created
        updated_at: When resource metrics were last updated
    """

    __tablename__ = "sandbox_resources"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    sandbox_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    task_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )
    agent_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )

    # Allocation limits
    cpu_allocated: Mapped[float] = mapped_column(
        Float, nullable=False, default=2.0,
        comment="CPU cores allocated"
    )
    memory_allocated_mb: Mapped[int] = mapped_column(
        Integer, nullable=False, default=4096,
        comment="Memory allocated in MB"
    )
    disk_allocated_gb: Mapped[int] = mapped_column(
        Integer, nullable=False, default=8,
        comment="Disk space allocated in GB"
    )

    # Current usage metrics
    cpu_usage_percent: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Current CPU usage percentage (0-100)"
    )
    memory_usage_mb: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Current memory usage in MB"
    )
    disk_usage_gb: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Current disk usage in GB"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active",
        comment="Resource status: active, paused, terminated"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    def __repr__(self) -> str:
        return (
            f"<SandboxResource(sandbox_id={self.sandbox_id}, "
            f"cpu={self.cpu_usage_percent:.1f}%, "
            f"mem={self.memory_usage_mb:.0f}MB)>"
        )

    @property
    def cpu_usage_ratio(self) -> float:
        """Get CPU usage as ratio of allocated."""
        if self.cpu_allocated <= 0:
            return 0.0
        return self.cpu_usage_percent / 100.0

    @property
    def memory_usage_ratio(self) -> float:
        """Get memory usage as ratio of allocated."""
        if self.memory_allocated_mb <= 0:
            return 0.0
        return self.memory_usage_mb / self.memory_allocated_mb

    @property
    def disk_usage_ratio(self) -> float:
        """Get disk usage as ratio of allocated."""
        if self.disk_allocated_gb <= 0:
            return 0.0
        return self.disk_usage_gb / self.disk_allocated_gb
