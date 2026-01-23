"""Sandbox Resource Allocation model for tracking current resource allocations per sandbox.

Part of TKT-001: Database Models & Migrations for Resource Tracking.

This model stores the current and pending resource configuration for each sandbox,
supporting optimistic locking for concurrent modification detection (REQ-SRAD-REL-003).
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class SandboxResourceAllocation(Base):
    """Tracks current resource allocations per sandbox.

    Supports optimistic locking via the version field to detect concurrent
    modifications and prevent lost updates.

    Attributes:
        id: Unique allocation identifier (UUID)
        sandbox_id: Unique identifier for the sandbox (unique, indexed)
        task_id: Optional foreign key to associated task
        agent_id: Optional foreign key to associated agent
        cpu_cores: Current CPU cores allocated
        memory_gb: Current memory (GB) allocated
        disk_gb: Current disk space (GB) allocated
        pending_cpu_cores: Staged CPU cores change (nullable)
        pending_memory_gb: Staged memory change (nullable)
        pending_disk_gb: Staged disk change (nullable)
        version: Version number for optimistic locking
        status: Current allocation status
        created_at: Timestamp when allocation was created
        updated_at: Timestamp of last update
        updated_by: Identifier of who/what made the last update
    """

    __tablename__ = "sandbox_resource_allocations"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    sandbox_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    # Foreign keys (nullable)
    task_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("tasks.id"), nullable=True, index=True
    )
    agent_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("agents.id"), nullable=True, index=True
    )

    # Current resource allocation
    cpu_cores: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    memory_gb: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    disk_gb: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)

    # Pending resource changes (staged before commit)
    pending_cpu_cores: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pending_memory_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pending_disk_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Optimistic locking
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active", index=True
    )

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<SandboxResourceAllocation(id={self.id}, sandbox_id={self.sandbox_id}, "
            f"cpu={self.cpu_cores}, mem={self.memory_gb}GB, disk={self.disk_gb}GB, "
            f"version={self.version})>"
        )
