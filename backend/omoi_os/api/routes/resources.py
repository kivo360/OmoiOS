"""API routes for resource monitoring and management.

This module provides endpoints for:
- Viewing resource allocation and usage per sandbox worker
- Dynamically adjusting resource limits (CPU/memory/disk)
- Getting resource summary statistics
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from omoi_os.services.resource_monitor import (
    get_resource_monitor_service,
    MAX_CPU_CORES,
    MAX_MEMORY_MB,
    MAX_DISK_GB,
)

router = APIRouter()


# ---------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------


class ResourceAllocationDTO(BaseModel):
    """Resource allocation limits."""

    cpu_cores: float = Field(..., description="CPU cores allocated")
    memory_mb: int = Field(..., description="Memory allocated in MB")
    disk_gb: int = Field(..., description="Disk space allocated in GB")


class ResourceUsageDTO(BaseModel):
    """Current resource usage metrics."""

    cpu_percent: float = Field(..., description="CPU usage percentage (0-100)")
    memory_mb: float = Field(..., description="Memory usage in MB")
    disk_gb: float = Field(..., description="Disk usage in GB")


class ResourceStatusDTO(BaseModel):
    """Complete resource status for a sandbox."""

    sandbox_id: str
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    status: str = Field(..., description="Resource status: active, paused, terminated")
    allocation: ResourceAllocationDTO
    usage: ResourceUsageDTO
    updated_at: str


class ResourceSummaryDTO(BaseModel):
    """Summary statistics for all sandbox resources."""

    total_sandboxes: int
    total_cpu_allocated: float
    total_memory_allocated_mb: int
    total_disk_allocated_gb: int
    avg_cpu_usage_percent: float
    avg_memory_usage_percent: float
    avg_disk_usage_percent: float
    high_cpu_count: int = Field(
        ..., description="Number of sandboxes with CPU usage > 80%"
    )
    high_memory_count: int = Field(
        ..., description="Number of sandboxes with memory usage > 80%"
    )


class ResourceLimitsDTO(BaseModel):
    """Maximum resource limits for allocation."""

    max_cpu_cores: float
    max_memory_mb: int
    max_disk_gb: int


class UpdateAllocationRequest(BaseModel):
    """Request to update resource allocation."""

    cpu_cores: Optional[float] = Field(
        None, ge=0.5, le=MAX_CPU_CORES, description="CPU cores to allocate"
    )
    memory_mb: Optional[int] = Field(
        None, ge=512, le=MAX_MEMORY_MB, description="Memory in MB to allocate"
    )
    disk_gb: Optional[int] = Field(
        None, ge=1, le=MAX_DISK_GB, description="Disk space in GB to allocate"
    )


class UpdateUsageRequest(BaseModel):
    """Request to update resource usage metrics."""

    cpu_percent: float = Field(..., ge=0, le=100, description="CPU usage percentage")
    memory_mb: float = Field(..., ge=0, description="Memory usage in MB")
    disk_gb: float = Field(..., ge=0, description="Disk usage in GB")


# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------


@router.get("/resources", response_model=List[ResourceStatusDTO])
async def list_resources(
    status: Optional[str] = Query(
        "active", description="Filter by status (active, paused, terminated, or None for all)"
    ),
):
    """List resource status for all sandboxes.

    Returns current allocation and usage for each sandbox worker.
    By default, only returns active sandboxes.
    """
    service = get_resource_monitor_service()

    # Handle "all" or empty string as no filter
    status_filter = status if status and status != "all" else None

    try:
        statuses = await service.get_all_resource_status(status_filter=status_filter)
        return [
            ResourceStatusDTO(
                sandbox_id=s.sandbox_id,
                task_id=s.task_id,
                agent_id=s.agent_id,
                status=s.status,
                allocation=ResourceAllocationDTO(
                    cpu_cores=s.allocation.cpu_cores,
                    memory_mb=s.allocation.memory_mb,
                    disk_gb=s.allocation.disk_gb,
                ),
                usage=ResourceUsageDTO(
                    cpu_percent=s.usage.cpu_percent,
                    memory_mb=s.usage.memory_mb,
                    disk_gb=s.usage.disk_gb,
                ),
                updated_at=s.updated_at,
            )
            for s in statuses
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to list resources: {exc}"
        ) from exc


@router.get("/resources/summary", response_model=ResourceSummaryDTO)
async def get_resource_summary():
    """Get summary statistics for all active sandbox resources.

    Returns aggregate metrics like total allocation, average usage,
    and counts of high-usage sandboxes.
    """
    service = get_resource_monitor_service()

    try:
        summary = await service.get_resource_summary()
        return ResourceSummaryDTO(**summary)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to get resource summary: {exc}"
        ) from exc


@router.get("/resources/limits", response_model=ResourceLimitsDTO)
async def get_resource_limits():
    """Get maximum resource limits for allocation.

    These are the hard limits that cannot be exceeded when adjusting
    resource allocation via the sliders.
    """
    return ResourceLimitsDTO(
        max_cpu_cores=MAX_CPU_CORES,
        max_memory_mb=MAX_MEMORY_MB,
        max_disk_gb=MAX_DISK_GB,
    )


@router.get("/resources/{sandbox_id}", response_model=ResourceStatusDTO)
async def get_resource_status(sandbox_id: str):
    """Get resource status for a specific sandbox.

    Returns current allocation and usage metrics for the specified
    sandbox worker.
    """
    service = get_resource_monitor_service()

    try:
        status = await service.get_resource_status(sandbox_id)
        if not status:
            raise HTTPException(
                status_code=404, detail=f"Resource not found for sandbox {sandbox_id}"
            )

        return ResourceStatusDTO(
            sandbox_id=status.sandbox_id,
            task_id=status.task_id,
            agent_id=status.agent_id,
            status=status.status,
            allocation=ResourceAllocationDTO(
                cpu_cores=status.allocation.cpu_cores,
                memory_mb=status.allocation.memory_mb,
                disk_gb=status.allocation.disk_gb,
            ),
            usage=ResourceUsageDTO(
                cpu_percent=status.usage.cpu_percent,
                memory_mb=status.usage.memory_mb,
                disk_gb=status.usage.disk_gb,
            ),
            updated_at=status.updated_at,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to get resource status: {exc}"
        ) from exc


@router.patch("/resources/{sandbox_id}/allocation", response_model=ResourceStatusDTO)
async def update_resource_allocation(
    sandbox_id: str,
    request: UpdateAllocationRequest,
):
    """Update resource allocation for a sandbox.

    Dynamically adjusts resource limits without restarting the sandbox.
    Only provided fields will be updated.

    Note: Actual enforcement depends on the sandbox runtime (Daytona).
    """
    service = get_resource_monitor_service()

    # Check if at least one field is provided
    if request.cpu_cores is None and request.memory_mb is None and request.disk_gb is None:
        raise HTTPException(
            status_code=400,
            detail="At least one resource field must be provided",
        )

    try:
        resource = await service.update_allocation(
            sandbox_id=sandbox_id,
            cpu_cores=request.cpu_cores,
            memory_mb=request.memory_mb,
            disk_gb=request.disk_gb,
        )

        if not resource:
            raise HTTPException(
                status_code=404, detail=f"Resource not found for sandbox {sandbox_id}"
            )

        return ResourceStatusDTO(
            sandbox_id=resource.sandbox_id,
            task_id=resource.task_id,
            agent_id=resource.agent_id,
            status=resource.status,
            allocation=ResourceAllocationDTO(
                cpu_cores=resource.cpu_allocated,
                memory_mb=resource.memory_allocated_mb,
                disk_gb=resource.disk_allocated_gb,
            ),
            usage=ResourceUsageDTO(
                cpu_percent=resource.cpu_usage_percent,
                memory_mb=resource.memory_usage_mb,
                disk_gb=resource.disk_usage_gb,
            ),
            updated_at=resource.updated_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to update allocation: {exc}"
        ) from exc


@router.post("/resources/{sandbox_id}/usage", response_model=dict)
async def report_resource_usage(
    sandbox_id: str,
    request: UpdateUsageRequest,
):
    """Report resource usage metrics for a sandbox.

    Called by sandbox workers to report current CPU/memory/disk usage.
    This is typically called from heartbeat events.
    """
    service = get_resource_monitor_service()

    try:
        resource = await service.update_usage(
            sandbox_id=sandbox_id,
            cpu_percent=request.cpu_percent,
            memory_mb=request.memory_mb,
            disk_gb=request.disk_gb,
        )

        return {
            "status": "success",
            "sandbox_id": sandbox_id,
            "updated_at": resource.updated_at.isoformat() if resource else None,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to report usage: {exc}"
        ) from exc


@router.delete("/resources/{sandbox_id}", response_model=dict)
async def terminate_resource(sandbox_id: str):
    """Mark a sandbox resource as terminated.

    Called when a sandbox is terminated to update its resource status.
    """
    service = get_resource_monitor_service()

    try:
        success = await service.mark_terminated(sandbox_id)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Resource not found for sandbox {sandbox_id}"
            )

        return {
            "status": "success",
            "sandbox_id": sandbox_id,
            "terminated": True,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to terminate resource: {exc}"
        ) from exc
