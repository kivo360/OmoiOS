"""API routes for sandbox resource monitoring and allocation.

This module provides endpoints for:
1. Getting resource metrics for all active sandboxes
2. Getting resource metrics for a specific sandbox
3. Updating resource allocation (CPU, memory, disk) dynamically
4. Getting historical resource usage data
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from omoi_os.api.dependencies import get_db_service
from omoi_os.logging import get_logger
from omoi_os.services.database import DatabaseService
from omoi_os.services.resource_monitor import ResourceMonitorService

logger = get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------


class ResourceAllocationDTO(BaseModel):
    """Resource allocation settings."""
    cpu_cores: int = Field(..., ge=1, le=4, description="CPU cores (1-4)")
    memory_gb: int = Field(..., ge=1, le=8, description="Memory in GiB (1-8)")
    disk_gb: int = Field(..., ge=1, le=10, description="Disk space in GiB (1-10)")


class ResourceUsageDTO(BaseModel):
    """Current resource usage metrics."""
    cpu_usage_percent: float = Field(..., ge=0, le=100, description="CPU utilization %")
    memory_usage_percent: float = Field(..., ge=0, le=100, description="Memory utilization %")
    memory_used_mb: float = Field(..., ge=0, description="Memory used in MB")
    disk_usage_percent: float = Field(..., ge=0, le=100, description="Disk utilization %")
    disk_used_gb: float = Field(..., ge=0, description="Disk used in GiB")


class SandboxResourceDTO(BaseModel):
    """Complete resource information for a sandbox."""
    sandbox_id: str
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    allocation: ResourceAllocationDTO
    usage: ResourceUsageDTO
    status: str
    last_updated: str
    created_at: str


class ResourceMetricsHistoryDTO(BaseModel):
    """Historical resource metrics data point."""
    cpu_usage_percent: float
    memory_usage_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    disk_used_gb: float
    recorded_at: str


class ResourceSummaryDTO(BaseModel):
    """Aggregate resource summary across all active sandboxes."""
    total_sandboxes: int
    total_cpu_allocated: int
    total_memory_allocated_gb: int
    total_disk_allocated_gb: int
    avg_cpu_usage_percent: float
    avg_memory_usage_percent: float
    avg_disk_usage_percent: float


class UpdateAllocationRequest(BaseModel):
    """Request to update resource allocation."""
    cpu_cores: Optional[int] = Field(None, ge=1, le=4, description="CPU cores (1-4)")
    memory_gb: Optional[int] = Field(None, ge=1, le=8, description="Memory in GiB (1-8)")
    disk_gb: Optional[int] = Field(None, ge=1, le=10, description="Disk space in GiB (1-10)")


class UpdateAllocationResponse(BaseModel):
    """Response from allocation update."""
    success: bool
    sandbox_id: str
    message: str
    allocation: Optional[ResourceAllocationDTO] = None


# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------


def _sandbox_to_dto(sandbox) -> SandboxResourceDTO:
    """Convert a SandboxResource model to DTO."""
    return SandboxResourceDTO(
        sandbox_id=sandbox.sandbox_id,
        task_id=sandbox.task_id,
        agent_id=sandbox.agent_id,
        allocation=ResourceAllocationDTO(
            cpu_cores=sandbox.allocated_cpu_cores,
            memory_gb=sandbox.allocated_memory_gb,
            disk_gb=sandbox.allocated_disk_gb,
        ),
        usage=ResourceUsageDTO(
            cpu_usage_percent=sandbox.cpu_usage_percent,
            memory_usage_percent=sandbox.memory_usage_percent,
            memory_used_mb=sandbox.memory_used_mb,
            disk_usage_percent=sandbox.disk_usage_percent,
            disk_used_gb=sandbox.disk_used_gb,
        ),
        status=sandbox.status,
        last_updated=sandbox.last_updated.isoformat(),
        created_at=sandbox.created_at.isoformat(),
    )


# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------


@router.get("/resources/sandboxes", response_model=List[SandboxResourceDTO])
async def get_sandbox_resources(
    status: Optional[str] = Query(None, description="Filter by status (creating, running, completed, failed, terminated)"),
    db: DatabaseService = Depends(get_db_service),
):
    """Get resource metrics for all sandboxes.

    Returns a list of all sandboxes with their current resource allocation
    and usage metrics. By default returns only active sandboxes (creating, running).
    """
    try:
        service = ResourceMonitorService(db)

        if status:
            statuses = [status]
        else:
            statuses = ["creating", "running"]

        sandboxes = await service.get_active_sandboxes(statuses=statuses)
        return [_sandbox_to_dto(s) for s in sandboxes]
    except Exception as exc:
        logger.error(f"Failed to get sandbox resources: {exc}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get sandbox resources: {exc}"
        ) from exc


@router.get("/resources/sandboxes/{sandbox_id}", response_model=SandboxResourceDTO)
async def get_sandbox_resource(
    sandbox_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Get resource metrics for a specific sandbox.

    Returns the current resource allocation and usage metrics
    for the specified sandbox.
    """
    try:
        service = ResourceMonitorService(db)
        sandbox = await service.get_sandbox(sandbox_id)

        if not sandbox:
            raise HTTPException(
                status_code=404, detail=f"Sandbox {sandbox_id} not found"
            )

        return _sandbox_to_dto(sandbox)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to get sandbox {sandbox_id}: {exc}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get sandbox resource: {exc}"
        ) from exc


@router.post("/resources/sandboxes/{sandbox_id}/allocate", response_model=UpdateAllocationResponse)
async def update_sandbox_allocation(
    sandbox_id: str,
    request: UpdateAllocationRequest,
    db: DatabaseService = Depends(get_db_service),
):
    """Update resource allocation for a sandbox.

    Allows dynamic adjustment of CPU, memory, and disk allocation
    without requiring a sandbox restart (where supported by platform).

    Limits:
    - CPU: 1-4 cores
    - Memory: 1-8 GiB
    - Disk: 1-10 GiB
    """
    try:
        service = ResourceMonitorService(db)

        # Check if sandbox exists
        existing = await service.get_sandbox(sandbox_id)
        if not existing:
            raise HTTPException(
                status_code=404, detail=f"Sandbox {sandbox_id} not found"
            )

        # Validate at least one field is being updated
        if request.cpu_cores is None and request.memory_gb is None and request.disk_gb is None:
            raise HTTPException(
                status_code=400, detail="At least one allocation field must be provided"
            )

        # Update allocation
        updated = await service.update_allocation(
            sandbox_id=sandbox_id,
            cpu_cores=request.cpu_cores,
            memory_gb=request.memory_gb,
            disk_gb=request.disk_gb,
        )

        if not updated:
            raise HTTPException(
                status_code=500, detail="Failed to update allocation"
            )

        logger.info(
            f"Updated allocation for {sandbox_id}: "
            f"CPU={updated.allocated_cpu_cores}, "
            f"Memory={updated.allocated_memory_gb}GB, "
            f"Disk={updated.allocated_disk_gb}GB"
        )

        return UpdateAllocationResponse(
            success=True,
            sandbox_id=sandbox_id,
            message="Resource allocation updated successfully",
            allocation=ResourceAllocationDTO(
                cpu_cores=updated.allocated_cpu_cores,
                memory_gb=updated.allocated_memory_gb,
                disk_gb=updated.allocated_disk_gb,
            ),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to update allocation for {sandbox_id}: {exc}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update allocation: {exc}"
        ) from exc


@router.get("/resources/sandboxes/{sandbox_id}/history", response_model=List[ResourceMetricsHistoryDTO])
async def get_sandbox_metrics_history(
    sandbox_id: str,
    hours: int = Query(1, ge=1, le=24, description="Hours of history to retrieve (1-24)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: DatabaseService = Depends(get_db_service),
):
    """Get historical resource metrics for a sandbox.

    Returns time-series data showing resource usage over time.
    Useful for identifying trends and spikes.
    """
    try:
        service = ResourceMonitorService(db)
        metrics = await service.get_metrics_history(
            sandbox_id=sandbox_id,
            hours=hours,
            limit=limit,
        )

        return [
            ResourceMetricsHistoryDTO(
                cpu_usage_percent=m.cpu_usage_percent,
                memory_usage_percent=m.memory_usage_percent,
                memory_used_mb=m.memory_used_mb,
                disk_usage_percent=m.disk_usage_percent,
                disk_used_gb=m.disk_used_gb,
                recorded_at=m.recorded_at.isoformat(),
            )
            for m in metrics
        ]
    except Exception as exc:
        logger.error(f"Failed to get metrics history for {sandbox_id}: {exc}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get metrics history: {exc}"
        ) from exc


@router.get("/resources/summary", response_model=ResourceSummaryDTO)
async def get_resource_summary(
    db: DatabaseService = Depends(get_db_service),
):
    """Get aggregate resource summary across all active sandboxes.

    Returns totals and averages for CPU, memory, and disk usage
    across all currently active sandboxes.
    """
    try:
        service = ResourceMonitorService(db)
        summary = await service.get_resource_summary()

        return ResourceSummaryDTO(**summary)
    except Exception as exc:
        logger.error(f"Failed to get resource summary: {exc}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get resource summary: {exc}"
        ) from exc
