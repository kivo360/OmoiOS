"""Resource Monitor Service for tracking and managing sandbox resource allocation.

This service provides functionality to:
- Track resource allocation per sandbox worker
- Monitor real-time CPU/memory/disk usage
- Dynamically adjust resource limits without restart
- Emit events when resources are updated
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func

from omoi_os.logging import get_logger
from omoi_os.models.sandbox_resource import SandboxResource
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)


# Default resource limits
DEFAULT_CPU_CORES = 2.0
DEFAULT_MEMORY_MB = 4096
DEFAULT_DISK_GB = 8

# Maximum resource limits
MAX_CPU_CORES = 4.0
MAX_MEMORY_MB = 8192
MAX_DISK_GB = 10


@dataclass
class ResourceAllocation:
    """Represents resource allocation for a sandbox."""
    cpu_cores: float
    memory_mb: int
    disk_gb: int


@dataclass
class ResourceUsage:
    """Represents current resource usage for a sandbox."""
    cpu_percent: float
    memory_mb: float
    disk_gb: float


@dataclass
class ResourceStatus:
    """Complete resource status including allocation and usage."""
    sandbox_id: str
    task_id: Optional[str]
    agent_id: Optional[str]
    status: str
    allocation: ResourceAllocation
    usage: ResourceUsage
    updated_at: str


class ResourceMonitorService:
    """Service for monitoring and managing sandbox resource allocation.

    This service tracks both the allocated resources (limits) and current
    usage metrics for each sandbox, enabling real-time monitoring and
    dynamic resource adjustment.

    Usage:
        service = ResourceMonitorService(db, event_bus)

        # Register a new sandbox with resources
        await service.register_sandbox(
            sandbox_id="sandbox-123",
            task_id="task-456",
            cpu_cores=2.0,
            memory_mb=4096,
            disk_gb=8
        )

        # Update resource allocation (dynamic adjustment)
        await service.update_allocation(
            sandbox_id="sandbox-123",
            cpu_cores=4.0,
            memory_mb=8192
        )

        # Update usage metrics (from heartbeat)
        await service.update_usage(
            sandbox_id="sandbox-123",
            cpu_percent=45.0,
            memory_mb=2048.0,
            disk_gb=3.5
        )

        # Get status for all active sandboxes
        statuses = await service.get_all_resource_status()
    """

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
    ):
        """Initialize ResourceMonitorService.

        Args:
            db: Database service for persistence
            event_bus: Optional event bus for publishing resource events
        """
        self.db = db
        self.event_bus = event_bus

    async def register_sandbox(
        self,
        sandbox_id: str,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        cpu_cores: float = DEFAULT_CPU_CORES,
        memory_mb: int = DEFAULT_MEMORY_MB,
        disk_gb: int = DEFAULT_DISK_GB,
    ) -> SandboxResource:
        """Register a sandbox with its initial resource allocation.

        Args:
            sandbox_id: Unique identifier for the sandbox
            task_id: Optional task ID associated with this sandbox
            agent_id: Optional agent ID running in this sandbox
            cpu_cores: CPU cores to allocate (default: 2.0)
            memory_mb: Memory in MB to allocate (default: 4096)
            disk_gb: Disk space in GB to allocate (default: 8)

        Returns:
            The created SandboxResource record
        """
        # Enforce maximum limits
        cpu_cores = min(cpu_cores, MAX_CPU_CORES)
        memory_mb = min(memory_mb, MAX_MEMORY_MB)
        disk_gb = min(disk_gb, MAX_DISK_GB)

        async with self.db.get_async_session() as session:
            # Check if sandbox already exists
            result = await session.execute(
                select(SandboxResource).where(
                    SandboxResource.sandbox_id == sandbox_id
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                existing.task_id = task_id or existing.task_id
                existing.agent_id = agent_id or existing.agent_id
                existing.cpu_allocated = cpu_cores
                existing.memory_allocated_mb = memory_mb
                existing.disk_allocated_gb = disk_gb
                existing.status = "active"
                existing.updated_at = utc_now()
                await session.commit()
                await session.refresh(existing)
                logger.info(
                    "sandbox_resource_updated",
                    sandbox_id=sandbox_id,
                    cpu=cpu_cores,
                    memory_mb=memory_mb,
                    disk_gb=disk_gb,
                )
                return existing

            # Create new record
            resource = SandboxResource(
                sandbox_id=sandbox_id,
                task_id=task_id,
                agent_id=agent_id,
                cpu_allocated=cpu_cores,
                memory_allocated_mb=memory_mb,
                disk_allocated_gb=disk_gb,
                cpu_usage_percent=0.0,
                memory_usage_mb=0.0,
                disk_usage_gb=0.0,
                status="active",
            )
            session.add(resource)
            await session.commit()
            await session.refresh(resource)

            logger.info(
                "sandbox_resource_registered",
                sandbox_id=sandbox_id,
                task_id=task_id,
                cpu=cpu_cores,
                memory_mb=memory_mb,
                disk_gb=disk_gb,
            )

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="resource.sandbox_registered",
                        entity_type="sandbox_resource",
                        entity_id=sandbox_id,
                        payload={
                            "sandbox_id": sandbox_id,
                            "task_id": task_id,
                            "cpu_allocated": cpu_cores,
                            "memory_allocated_mb": memory_mb,
                            "disk_allocated_gb": disk_gb,
                        },
                    )
                )

            return resource

    async def update_allocation(
        self,
        sandbox_id: str,
        cpu_cores: Optional[float] = None,
        memory_mb: Optional[int] = None,
        disk_gb: Optional[int] = None,
    ) -> Optional[SandboxResource]:
        """Update resource allocation for a sandbox (dynamic adjustment).

        This allows adjusting resource limits without restarting the sandbox.
        Note: Actual enforcement depends on the sandbox runtime (Daytona).

        Args:
            sandbox_id: ID of the sandbox to update
            cpu_cores: New CPU cores allocation (None = keep current)
            memory_mb: New memory allocation in MB (None = keep current)
            disk_gb: New disk allocation in GB (None = keep current)

        Returns:
            Updated SandboxResource or None if not found
        """
        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(SandboxResource).where(
                    SandboxResource.sandbox_id == sandbox_id
                )
            )
            resource = result.scalar_one_or_none()

            if not resource:
                logger.warning(
                    "sandbox_resource_not_found",
                    sandbox_id=sandbox_id,
                )
                return None

            old_values = {
                "cpu": resource.cpu_allocated,
                "memory_mb": resource.memory_allocated_mb,
                "disk_gb": resource.disk_allocated_gb,
            }

            # Update only provided values, enforcing limits
            if cpu_cores is not None:
                resource.cpu_allocated = min(cpu_cores, MAX_CPU_CORES)
            if memory_mb is not None:
                resource.memory_allocated_mb = min(memory_mb, MAX_MEMORY_MB)
            if disk_gb is not None:
                resource.disk_allocated_gb = min(disk_gb, MAX_DISK_GB)

            resource.updated_at = utc_now()
            await session.commit()
            await session.refresh(resource)

            logger.info(
                "sandbox_resource_allocation_updated",
                sandbox_id=sandbox_id,
                old_values=old_values,
                new_values={
                    "cpu": resource.cpu_allocated,
                    "memory_mb": resource.memory_allocated_mb,
                    "disk_gb": resource.disk_allocated_gb,
                },
            )

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="resource.allocation_updated",
                        entity_type="sandbox_resource",
                        entity_id=sandbox_id,
                        payload={
                            "sandbox_id": sandbox_id,
                            "cpu_allocated": resource.cpu_allocated,
                            "memory_allocated_mb": resource.memory_allocated_mb,
                            "disk_allocated_gb": resource.disk_allocated_gb,
                            "old_values": old_values,
                        },
                    )
                )

            return resource

    async def update_usage(
        self,
        sandbox_id: str,
        cpu_percent: float,
        memory_mb: float,
        disk_gb: float,
    ) -> Optional[SandboxResource]:
        """Update resource usage metrics for a sandbox.

        Called from heartbeat events to track current resource consumption.

        Args:
            sandbox_id: ID of the sandbox
            cpu_percent: Current CPU usage percentage (0-100)
            memory_mb: Current memory usage in MB
            disk_gb: Current disk usage in GB

        Returns:
            Updated SandboxResource or None if not found
        """
        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(SandboxResource).where(
                    SandboxResource.sandbox_id == sandbox_id
                )
            )
            resource = result.scalar_one_or_none()

            if not resource:
                # Auto-register if not found
                logger.debug(
                    "auto_registering_sandbox_resource",
                    sandbox_id=sandbox_id,
                )
                # Create with defaults, will be updated below
                resource = SandboxResource(
                    sandbox_id=sandbox_id,
                    status="active",
                )
                session.add(resource)

            # Update usage metrics
            resource.cpu_usage_percent = min(max(cpu_percent, 0.0), 100.0)
            resource.memory_usage_mb = max(memory_mb, 0.0)
            resource.disk_usage_gb = max(disk_gb, 0.0)
            resource.updated_at = utc_now()

            await session.commit()
            await session.refresh(resource)

            return resource

    async def mark_terminated(self, sandbox_id: str) -> bool:
        """Mark a sandbox as terminated.

        Args:
            sandbox_id: ID of the sandbox to terminate

        Returns:
            True if found and updated, False otherwise
        """
        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(SandboxResource).where(
                    SandboxResource.sandbox_id == sandbox_id
                )
            )
            resource = result.scalar_one_or_none()

            if not resource:
                return False

            resource.status = "terminated"
            resource.updated_at = utc_now()
            await session.commit()

            logger.info(
                "sandbox_resource_terminated",
                sandbox_id=sandbox_id,
            )

            return True

    async def get_resource_status(
        self, sandbox_id: str
    ) -> Optional[ResourceStatus]:
        """Get resource status for a specific sandbox.

        Args:
            sandbox_id: ID of the sandbox

        Returns:
            ResourceStatus or None if not found
        """
        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(SandboxResource).where(
                    SandboxResource.sandbox_id == sandbox_id
                )
            )
            resource = result.scalar_one_or_none()

            if not resource:
                return None

            return ResourceStatus(
                sandbox_id=resource.sandbox_id,
                task_id=resource.task_id,
                agent_id=resource.agent_id,
                status=resource.status,
                allocation=ResourceAllocation(
                    cpu_cores=resource.cpu_allocated,
                    memory_mb=resource.memory_allocated_mb,
                    disk_gb=resource.disk_allocated_gb,
                ),
                usage=ResourceUsage(
                    cpu_percent=resource.cpu_usage_percent,
                    memory_mb=resource.memory_usage_mb,
                    disk_gb=resource.disk_usage_gb,
                ),
                updated_at=resource.updated_at.isoformat(),
            )

    async def get_all_resource_status(
        self,
        status_filter: Optional[str] = "active",
    ) -> List[ResourceStatus]:
        """Get resource status for all sandboxes.

        Args:
            status_filter: Filter by status (None for all)

        Returns:
            List of ResourceStatus objects
        """
        async with self.db.get_async_session() as session:
            query = select(SandboxResource)
            if status_filter:
                query = query.where(SandboxResource.status == status_filter)
            query = query.order_by(SandboxResource.updated_at.desc())

            result = await session.execute(query)
            resources = result.scalars().all()

            return [
                ResourceStatus(
                    sandbox_id=r.sandbox_id,
                    task_id=r.task_id,
                    agent_id=r.agent_id,
                    status=r.status,
                    allocation=ResourceAllocation(
                        cpu_cores=r.cpu_allocated,
                        memory_mb=r.memory_allocated_mb,
                        disk_gb=r.disk_allocated_gb,
                    ),
                    usage=ResourceUsage(
                        cpu_percent=r.cpu_usage_percent,
                        memory_mb=r.memory_usage_mb,
                        disk_gb=r.disk_usage_gb,
                    ),
                    updated_at=r.updated_at.isoformat(),
                )
                for r in resources
            ]

    async def get_resource_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all active sandbox resources.

        Returns:
            Dictionary with summary statistics
        """
        async with self.db.get_async_session() as session:
            # Get active sandboxes
            result = await session.execute(
                select(SandboxResource).where(
                    SandboxResource.status == "active"
                )
            )
            resources = result.scalars().all()

            if not resources:
                return {
                    "total_sandboxes": 0,
                    "total_cpu_allocated": 0.0,
                    "total_memory_allocated_mb": 0,
                    "total_disk_allocated_gb": 0,
                    "avg_cpu_usage_percent": 0.0,
                    "avg_memory_usage_percent": 0.0,
                    "avg_disk_usage_percent": 0.0,
                    "high_cpu_count": 0,
                    "high_memory_count": 0,
                }

            total_cpu = sum(r.cpu_allocated for r in resources)
            total_memory = sum(r.memory_allocated_mb for r in resources)
            total_disk = sum(r.disk_allocated_gb for r in resources)

            avg_cpu = sum(r.cpu_usage_percent for r in resources) / len(resources)

            # Calculate average memory/disk usage as percentage of allocation
            memory_usage_percents = [
                (r.memory_usage_mb / r.memory_allocated_mb * 100)
                if r.memory_allocated_mb > 0 else 0
                for r in resources
            ]
            disk_usage_percents = [
                (r.disk_usage_gb / r.disk_allocated_gb * 100)
                if r.disk_allocated_gb > 0 else 0
                for r in resources
            ]

            avg_memory = sum(memory_usage_percents) / len(resources)
            avg_disk = sum(disk_usage_percents) / len(resources)

            # Count high usage sandboxes (>80%)
            high_cpu = sum(1 for r in resources if r.cpu_usage_percent > 80)
            high_memory = sum(
                1 for p in memory_usage_percents if p > 80
            )

            return {
                "total_sandboxes": len(resources),
                "total_cpu_allocated": total_cpu,
                "total_memory_allocated_mb": total_memory,
                "total_disk_allocated_gb": total_disk,
                "avg_cpu_usage_percent": round(avg_cpu, 1),
                "avg_memory_usage_percent": round(avg_memory, 1),
                "avg_disk_usage_percent": round(avg_disk, 1),
                "high_cpu_count": high_cpu,
                "high_memory_count": high_memory,
            }


# Global instance for dependency injection
_resource_monitor_service: Optional[ResourceMonitorService] = None


def get_resource_monitor_service() -> ResourceMonitorService:
    """Get or create the global ResourceMonitorService instance."""
    global _resource_monitor_service
    if _resource_monitor_service is None:
        from omoi_os.api.dependencies import get_db_service, get_event_bus

        db = get_db_service()
        event_bus = get_event_bus()
        _resource_monitor_service = ResourceMonitorService(db, event_bus)
    return _resource_monitor_service


def reset_resource_monitor_service() -> None:
    """Reset global instance (for testing)."""
    global _resource_monitor_service
    _resource_monitor_service = None
