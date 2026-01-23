"""Resource Monitor Service for sandbox CPU/memory/disk tracking.

This service provides:
1. Resource allocation tracking per sandbox
2. Real-time usage metrics collection
3. Dynamic resource adjustment without restart
4. Historical metrics for trending and analysis
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from omoi_os.logging import get_logger
from omoi_os.models.sandbox_resource import SandboxResource, SandboxResourceMetrics
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)


@dataclass
class ResourceAllocation:
    """Resource allocation settings for a sandbox."""
    cpu_cores: int
    memory_gb: int
    disk_gb: int


@dataclass
class ResourceUsage:
    """Current resource usage metrics."""
    cpu_usage_percent: float
    memory_usage_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    disk_used_gb: float


@dataclass
class SandboxResourceInfo:
    """Complete resource information for a sandbox."""
    sandbox_id: str
    task_id: Optional[str]
    agent_id: Optional[str]
    allocation: ResourceAllocation
    usage: ResourceUsage
    status: str
    last_updated: datetime
    created_at: datetime


class ResourceMonitorService:
    """Service for monitoring and managing sandbox resource allocation and usage.

    This service tracks:
    - Resource allocation (CPU cores, memory GB, disk GB) per sandbox
    - Real-time usage metrics (utilization percentages)
    - Historical usage data for trending

    Usage:
        service = ResourceMonitorService(db)

        # Register a new sandbox with allocation
        await service.register_sandbox(
            sandbox_id="sb-123",
            task_id="task-456",
            agent_id="agent-789",
            cpu_cores=2,
            memory_gb=4,
            disk_gb=8
        )

        # Update usage metrics (from heartbeat)
        await service.update_metrics(
            sandbox_id="sb-123",
            cpu_percent=45.5,
            memory_percent=62.3,
            memory_used_mb=2540,
            disk_percent=35.0,
            disk_used_gb=2.8
        )

        # Adjust allocation dynamically
        await service.update_allocation(
            sandbox_id="sb-123",
            cpu_cores=4,
            memory_gb=8,
            disk_gb=10
        )

        # Get all active sandboxes with metrics
        sandboxes = await service.get_active_sandboxes()
    """

    def __init__(self, db: Optional[DatabaseService] = None):
        """Initialize the resource monitor service.

        Args:
            db: Database service for persistence
        """
        self.db = db

    async def register_sandbox(
        self,
        sandbox_id: str,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        cpu_cores: int = 2,
        memory_gb: int = 4,
        disk_gb: int = 8,
        status: str = "creating",
    ) -> SandboxResource:
        """Register a new sandbox with its resource allocation.

        Args:
            sandbox_id: Unique identifier for the sandbox
            task_id: Optional task ID being executed
            agent_id: Optional agent ID associated with sandbox
            cpu_cores: Number of CPU cores allocated
            memory_gb: Memory allocated in GiB
            disk_gb: Disk space allocated in GiB
            status: Initial status (creating, running, etc.)

        Returns:
            The created SandboxResource record
        """
        if not self.db:
            logger.warning("No database service configured, skipping sandbox registration")
            return None

        resource = SandboxResource(
            id=str(uuid4()),
            sandbox_id=sandbox_id,
            task_id=task_id,
            agent_id=agent_id,
            allocated_cpu_cores=cpu_cores,
            allocated_memory_gb=memory_gb,
            allocated_disk_gb=disk_gb,
            status=status,
            created_at=utc_now(),
            last_updated=utc_now(),
        )

        async with self.db.session() as session:
            session.add(resource)
            await session.commit()
            await session.refresh(resource)
            logger.info(
                f"Registered sandbox {sandbox_id} with allocation: "
                f"CPU={cpu_cores}, Memory={memory_gb}GB, Disk={disk_gb}GB"
            )
            return resource

    async def update_metrics(
        self,
        sandbox_id: str,
        cpu_percent: float,
        memory_percent: float,
        memory_used_mb: float = 0.0,
        disk_percent: float = 0.0,
        disk_used_gb: float = 0.0,
        status: Optional[str] = None,
        record_history: bool = True,
    ) -> Optional[SandboxResource]:
        """Update resource usage metrics for a sandbox.

        This is typically called from heartbeat processing to update
        the current resource utilization.

        Args:
            sandbox_id: The sandbox to update
            cpu_percent: CPU utilization (0-100)
            memory_percent: Memory utilization (0-100)
            memory_used_mb: Memory used in MB
            disk_percent: Disk utilization (0-100)
            disk_used_gb: Disk used in GiB
            status: Optional status update
            record_history: Whether to record to time-series table

        Returns:
            Updated SandboxResource or None if not found
        """
        if not self.db:
            return None

        now = utc_now()

        async with self.db.session() as session:
            # Update current state
            stmt = (
                update(SandboxResource)
                .where(SandboxResource.sandbox_id == sandbox_id)
                .values(
                    cpu_usage_percent=cpu_percent,
                    memory_usage_percent=memory_percent,
                    memory_used_mb=memory_used_mb,
                    disk_usage_percent=disk_percent,
                    disk_used_gb=disk_used_gb,
                    last_updated=now,
                    **({"status": status} if status else {}),
                )
                .returning(SandboxResource)
            )
            result = await session.execute(stmt)
            resource = result.scalar_one_or_none()

            if not resource:
                logger.warning(f"Sandbox {sandbox_id} not found for metrics update")
                return None

            # Record to time-series table for historical tracking
            if record_history:
                metrics = SandboxResourceMetrics(
                    id=str(uuid4()),
                    sandbox_id=sandbox_id,
                    cpu_usage_percent=cpu_percent,
                    memory_usage_percent=memory_percent,
                    memory_used_mb=memory_used_mb,
                    disk_usage_percent=disk_percent,
                    disk_used_gb=disk_used_gb,
                    recorded_at=now,
                )
                session.add(metrics)

            await session.commit()
            logger.debug(
                f"Updated metrics for {sandbox_id}: "
                f"CPU={cpu_percent:.1f}%, Memory={memory_percent:.1f}%"
            )
            return resource

    async def update_allocation(
        self,
        sandbox_id: str,
        cpu_cores: Optional[int] = None,
        memory_gb: Optional[int] = None,
        disk_gb: Optional[int] = None,
    ) -> Optional[SandboxResource]:
        """Update resource allocation for a sandbox.

        This allows dynamic adjustment of resource limits without
        requiring a sandbox restart (where supported by the platform).

        Args:
            sandbox_id: The sandbox to update
            cpu_cores: New CPU core allocation (1-4)
            memory_gb: New memory allocation in GiB (1-8)
            disk_gb: New disk allocation in GiB (1-10)

        Returns:
            Updated SandboxResource or None if not found
        """
        if not self.db:
            return None

        # Validate and clamp values to safe ranges
        updates: Dict[str, Any] = {"last_updated": utc_now()}

        if cpu_cores is not None:
            updates["allocated_cpu_cores"] = max(1, min(4, cpu_cores))
        if memory_gb is not None:
            updates["allocated_memory_gb"] = max(1, min(8, memory_gb))
        if disk_gb is not None:
            updates["allocated_disk_gb"] = max(1, min(10, disk_gb))

        async with self.db.session() as session:
            stmt = (
                update(SandboxResource)
                .where(SandboxResource.sandbox_id == sandbox_id)
                .values(**updates)
                .returning(SandboxResource)
            )
            result = await session.execute(stmt)
            resource = result.scalar_one_or_none()
            await session.commit()

            if resource:
                logger.info(
                    f"Updated allocation for {sandbox_id}: "
                    f"CPU={resource.allocated_cpu_cores}, "
                    f"Memory={resource.allocated_memory_gb}GB, "
                    f"Disk={resource.allocated_disk_gb}GB"
                )
            return resource

    async def update_status(
        self,
        sandbox_id: str,
        status: str,
    ) -> Optional[SandboxResource]:
        """Update the status of a sandbox.

        Args:
            sandbox_id: The sandbox to update
            status: New status (creating, running, completed, failed, terminated)

        Returns:
            Updated SandboxResource or None if not found
        """
        if not self.db:
            return None

        async with self.db.session() as session:
            stmt = (
                update(SandboxResource)
                .where(SandboxResource.sandbox_id == sandbox_id)
                .values(status=status, last_updated=utc_now())
                .returning(SandboxResource)
            )
            result = await session.execute(stmt)
            resource = result.scalar_one_or_none()
            await session.commit()
            return resource

    async def get_sandbox(self, sandbox_id: str) -> Optional[SandboxResource]:
        """Get resource information for a specific sandbox.

        Args:
            sandbox_id: The sandbox to look up

        Returns:
            SandboxResource or None if not found
        """
        if not self.db:
            return None

        async with self.db.session() as session:
            stmt = select(SandboxResource).where(
                SandboxResource.sandbox_id == sandbox_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_active_sandboxes(
        self,
        statuses: Optional[List[str]] = None,
    ) -> List[SandboxResource]:
        """Get all active sandboxes with their resource metrics.

        Args:
            statuses: Filter by these statuses. Defaults to ["creating", "running"]

        Returns:
            List of SandboxResource records
        """
        if not self.db:
            return []

        if statuses is None:
            statuses = ["creating", "running"]

        async with self.db.session() as session:
            stmt = (
                select(SandboxResource)
                .where(SandboxResource.status.in_(statuses))
                .order_by(SandboxResource.created_at.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_metrics_history(
        self,
        sandbox_id: str,
        hours: int = 1,
        limit: int = 100,
    ) -> List[SandboxResourceMetrics]:
        """Get historical metrics for a sandbox.

        Args:
            sandbox_id: The sandbox to get history for
            hours: How many hours of history to retrieve
            limit: Maximum number of records to return

        Returns:
            List of SandboxResourceMetrics records, newest first
        """
        if not self.db:
            return []

        cutoff = utc_now() - timedelta(hours=hours)

        async with self.db.session() as session:
            stmt = (
                select(SandboxResourceMetrics)
                .where(
                    SandboxResourceMetrics.sandbox_id == sandbox_id,
                    SandboxResourceMetrics.recorded_at >= cutoff,
                )
                .order_by(SandboxResourceMetrics.recorded_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def delete_sandbox(self, sandbox_id: str) -> bool:
        """Remove a sandbox resource record.

        Args:
            sandbox_id: The sandbox to remove

        Returns:
            True if deleted, False if not found
        """
        if not self.db:
            return False

        async with self.db.session() as session:
            stmt = delete(SandboxResource).where(
                SandboxResource.sandbox_id == sandbox_id
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def cleanup_old_metrics(self, days: int = 7) -> int:
        """Clean up old time-series metrics data.

        Args:
            days: Delete metrics older than this many days

        Returns:
            Number of records deleted
        """
        if not self.db:
            return 0

        cutoff = utc_now() - timedelta(days=days)

        async with self.db.session() as session:
            stmt = delete(SandboxResourceMetrics).where(
                SandboxResourceMetrics.recorded_at < cutoff
            )
            result = await session.execute(stmt)
            await session.commit()

            deleted = result.rowcount
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old resource metrics records")
            return deleted

    async def get_resource_summary(self) -> Dict[str, Any]:
        """Get aggregate resource usage summary across all active sandboxes.

        Returns:
            Dictionary with summary statistics
        """
        if not self.db:
            return {}

        sandboxes = await self.get_active_sandboxes()

        if not sandboxes:
            return {
                "total_sandboxes": 0,
                "total_cpu_allocated": 0,
                "total_memory_allocated_gb": 0,
                "total_disk_allocated_gb": 0,
                "avg_cpu_usage_percent": 0.0,
                "avg_memory_usage_percent": 0.0,
                "avg_disk_usage_percent": 0.0,
            }

        total_cpu = sum(s.allocated_cpu_cores for s in sandboxes)
        total_memory = sum(s.allocated_memory_gb for s in sandboxes)
        total_disk = sum(s.allocated_disk_gb for s in sandboxes)
        avg_cpu = sum(s.cpu_usage_percent for s in sandboxes) / len(sandboxes)
        avg_memory = sum(s.memory_usage_percent for s in sandboxes) / len(sandboxes)
        avg_disk = sum(s.disk_usage_percent for s in sandboxes) / len(sandboxes)

        return {
            "total_sandboxes": len(sandboxes),
            "total_cpu_allocated": total_cpu,
            "total_memory_allocated_gb": total_memory,
            "total_disk_allocated_gb": total_disk,
            "avg_cpu_usage_percent": round(avg_cpu, 1),
            "avg_memory_usage_percent": round(avg_memory, 1),
            "avg_disk_usage_percent": round(avg_disk, 1),
        }


# Module-level singleton for convenience
_resource_monitor: Optional[ResourceMonitorService] = None


def get_resource_monitor(db: Optional[DatabaseService] = None) -> ResourceMonitorService:
    """Get or create the resource monitor service singleton.

    Args:
        db: Database service (required on first call)

    Returns:
        ResourceMonitorService instance
    """
    global _resource_monitor
    if _resource_monitor is None:
        _resource_monitor = ResourceMonitorService(db)
    return _resource_monitor
