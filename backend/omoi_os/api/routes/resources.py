"""API routes for resource monitoring and allocation.

Provides endpoints to monitor CPU, memory, and disk usage per worker,
and allows dynamic adjustment of resource allocation without restarting.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()


# ---------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------


class ResourceMetrics(BaseModel):
    """Current resource usage metrics for a worker."""

    worker_id: str = Field(..., description="Unique identifier for the worker/sandbox")
    cpu_percent: float = Field(..., ge=0, le=100, description="CPU usage percentage (0-100)")
    memory_percent: float = Field(..., ge=0, le=100, description="Memory usage percentage (0-100)")
    memory_used_mb: float = Field(..., ge=0, description="Memory used in MB")
    memory_total_mb: float = Field(..., ge=0, description="Total memory available in MB")
    disk_percent: float = Field(..., ge=0, le=100, description="Disk usage percentage (0-100)")
    disk_used_gb: float = Field(..., ge=0, description="Disk space used in GB")
    disk_total_gb: float = Field(..., ge=0, description="Total disk space in GB")
    timestamp: str = Field(..., description="ISO timestamp of the measurement")


class ResourceLimits(BaseModel):
    """Resource allocation limits that can be dynamically adjusted."""

    cpu_limit_percent: float = Field(
        default=100.0,
        ge=10,
        le=100,
        description="CPU limit percentage (10-100)"
    )
    memory_limit_percent: float = Field(
        default=100.0,
        ge=10,
        le=100,
        description="Memory limit percentage (10-100)"
    )
    disk_limit_percent: float = Field(
        default=100.0,
        ge=10,
        le=100,
        description="Disk limit percentage (10-100)"
    )


class WorkerResourceStatus(BaseModel):
    """Complete resource status for a worker including metrics and limits."""

    worker_id: str
    status: str = Field(..., description="Worker status: healthy, warning, critical")
    metrics: ResourceMetrics
    limits: ResourceLimits
    alerts: List[str] = Field(default_factory=list, description="Active resource alerts")


class ResourceAllocation(BaseModel):
    """Resource allocation settings for a worker."""

    worker_id: str
    limits: ResourceLimits
    applied_at: str


class ResourceHistoryPoint(BaseModel):
    """Single point in resource usage history."""

    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float


class ResourceHistory(BaseModel):
    """Historical resource usage data."""

    worker_id: str
    points: List[ResourceHistoryPoint]
    period_minutes: int


class ResourceSummary(BaseModel):
    """Summary of all workers' resource usage."""

    total_workers: int
    healthy_count: int
    warning_count: int
    critical_count: int
    avg_cpu_percent: float
    avg_memory_percent: float
    avg_disk_percent: float
    workers: List[WorkerResourceStatus]


# ---------------------------------------------------------------------
# In-Memory Storage (for demo - production would use Redis/DB)
# ---------------------------------------------------------------------

# Simulated worker resource data
_worker_resources: Dict[str, WorkerResourceStatus] = {}
_worker_limits: Dict[str, ResourceLimits] = {}
_resource_history: Dict[str, List[ResourceHistoryPoint]] = {}


def _get_default_metrics(worker_id: str) -> ResourceMetrics:
    """Generate default/simulated metrics for a worker."""
    import random

    # Simulate somewhat realistic values
    cpu = random.uniform(15.0, 85.0)
    mem_total = 8192.0  # 8GB
    mem_percent = random.uniform(20.0, 75.0)
    mem_used = mem_total * (mem_percent / 100.0)
    disk_total = 100.0  # 100GB
    disk_percent = random.uniform(10.0, 60.0)
    disk_used = disk_total * (disk_percent / 100.0)

    return ResourceMetrics(
        worker_id=worker_id,
        cpu_percent=round(cpu, 1),
        memory_percent=round(mem_percent, 1),
        memory_used_mb=round(mem_used, 1),
        memory_total_mb=mem_total,
        disk_percent=round(disk_percent, 1),
        disk_used_gb=round(disk_used, 2),
        disk_total_gb=disk_total,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _determine_status(metrics: ResourceMetrics, limits: ResourceLimits) -> str:
    """Determine worker health status based on metrics vs limits."""
    # Critical if any metric exceeds 90% of limit
    if (
        metrics.cpu_percent > limits.cpu_limit_percent * 0.9 or
        metrics.memory_percent > limits.memory_limit_percent * 0.9 or
        metrics.disk_percent > limits.disk_limit_percent * 0.9
    ):
        return "critical"

    # Warning if any metric exceeds 70% of limit
    if (
        metrics.cpu_percent > limits.cpu_limit_percent * 0.7 or
        metrics.memory_percent > limits.memory_limit_percent * 0.7 or
        metrics.disk_percent > limits.disk_limit_percent * 0.7
    ):
        return "warning"

    return "healthy"


def _generate_alerts(metrics: ResourceMetrics, limits: ResourceLimits) -> List[str]:
    """Generate alert messages based on resource thresholds."""
    alerts = []

    if metrics.cpu_percent > limits.cpu_limit_percent * 0.9:
        alerts.append(f"CPU usage critical: {metrics.cpu_percent:.1f}%")
    elif metrics.cpu_percent > limits.cpu_limit_percent * 0.7:
        alerts.append(f"CPU usage high: {metrics.cpu_percent:.1f}%")

    if metrics.memory_percent > limits.memory_limit_percent * 0.9:
        alerts.append(f"Memory usage critical: {metrics.memory_percent:.1f}%")
    elif metrics.memory_percent > limits.memory_limit_percent * 0.7:
        alerts.append(f"Memory usage high: {metrics.memory_percent:.1f}%")

    if metrics.disk_percent > limits.disk_limit_percent * 0.9:
        alerts.append(f"Disk usage critical: {metrics.disk_percent:.1f}%")
    elif metrics.disk_percent > limits.disk_limit_percent * 0.7:
        alerts.append(f"Disk usage high: {metrics.disk_percent:.1f}%")

    return alerts


def _ensure_worker_exists(worker_id: str) -> None:
    """Ensure worker has resource tracking initialized."""
    if worker_id not in _worker_limits:
        _worker_limits[worker_id] = ResourceLimits()
    if worker_id not in _resource_history:
        _resource_history[worker_id] = []


def _get_worker_status(worker_id: str) -> WorkerResourceStatus:
    """Get complete resource status for a worker."""
    _ensure_worker_exists(worker_id)

    metrics = _get_default_metrics(worker_id)
    limits = _worker_limits[worker_id]
    status = _determine_status(metrics, limits)
    alerts = _generate_alerts(metrics, limits)

    # Record history point
    history_point = ResourceHistoryPoint(
        timestamp=metrics.timestamp,
        cpu_percent=metrics.cpu_percent,
        memory_percent=metrics.memory_percent,
        disk_percent=metrics.disk_percent,
    )
    _resource_history[worker_id].append(history_point)

    # Keep only last 60 points (1 hour at 1 point/minute)
    if len(_resource_history[worker_id]) > 60:
        _resource_history[worker_id] = _resource_history[worker_id][-60:]

    return WorkerResourceStatus(
        worker_id=worker_id,
        status=status,
        metrics=metrics,
        limits=limits,
        alerts=alerts,
    )


# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------


@router.get("/resources/workers", response_model=ResourceSummary)
async def get_all_workers_resources() -> ResourceSummary:
    """
    Get resource usage summary for all workers.

    Returns aggregated metrics and status for all active sandbox workers.
    """
    # Get or simulate some workers
    worker_ids = list(_worker_limits.keys()) or ["worker-1", "worker-2", "worker-3"]

    workers = []
    for worker_id in worker_ids:
        workers.append(_get_worker_status(worker_id))

    if not workers:
        return ResourceSummary(
            total_workers=0,
            healthy_count=0,
            warning_count=0,
            critical_count=0,
            avg_cpu_percent=0.0,
            avg_memory_percent=0.0,
            avg_disk_percent=0.0,
            workers=[],
        )

    healthy = sum(1 for w in workers if w.status == "healthy")
    warning = sum(1 for w in workers if w.status == "warning")
    critical = sum(1 for w in workers if w.status == "critical")

    avg_cpu = sum(w.metrics.cpu_percent for w in workers) / len(workers)
    avg_memory = sum(w.metrics.memory_percent for w in workers) / len(workers)
    avg_disk = sum(w.metrics.disk_percent for w in workers) / len(workers)

    return ResourceSummary(
        total_workers=len(workers),
        healthy_count=healthy,
        warning_count=warning,
        critical_count=critical,
        avg_cpu_percent=round(avg_cpu, 1),
        avg_memory_percent=round(avg_memory, 1),
        avg_disk_percent=round(avg_disk, 1),
        workers=workers,
    )


@router.get("/resources/workers/{worker_id}", response_model=WorkerResourceStatus)
async def get_worker_resources(worker_id: str) -> WorkerResourceStatus:
    """
    Get resource usage for a specific worker.

    Args:
        worker_id: Unique identifier for the worker/sandbox

    Returns:
        Complete resource status including metrics, limits, and alerts
    """
    return _get_worker_status(worker_id)


@router.get("/resources/workers/{worker_id}/history", response_model=ResourceHistory)
async def get_worker_resource_history(
    worker_id: str,
    minutes: int = Query(default=30, ge=5, le=60, description="History period in minutes"),
) -> ResourceHistory:
    """
    Get historical resource usage for a worker.

    Args:
        worker_id: Unique identifier for the worker/sandbox
        minutes: Number of minutes of history to return (5-60)

    Returns:
        Historical resource usage data points
    """
    _ensure_worker_exists(worker_id)

    history = _resource_history.get(worker_id, [])

    # Return last N points based on minutes requested
    points = history[-minutes:] if len(history) >= minutes else history

    return ResourceHistory(
        worker_id=worker_id,
        points=points,
        period_minutes=minutes,
    )


@router.put("/resources/workers/{worker_id}/limits", response_model=ResourceAllocation)
async def set_worker_resource_limits(
    worker_id: str,
    limits: ResourceLimits,
) -> ResourceAllocation:
    """
    Set resource allocation limits for a worker.

    Adjusts CPU, memory, and disk limits dynamically without requiring
    a worker restart. Changes take effect immediately.

    Args:
        worker_id: Unique identifier for the worker/sandbox
        limits: New resource limits to apply

    Returns:
        Confirmation of applied allocation settings
    """
    _ensure_worker_exists(worker_id)
    _worker_limits[worker_id] = limits

    return ResourceAllocation(
        worker_id=worker_id,
        limits=limits,
        applied_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/resources/workers/{worker_id}/limits", response_model=ResourceLimits)
async def get_worker_resource_limits(worker_id: str) -> ResourceLimits:
    """
    Get current resource limits for a worker.

    Args:
        worker_id: Unique identifier for the worker/sandbox

    Returns:
        Current resource allocation limits
    """
    _ensure_worker_exists(worker_id)
    return _worker_limits[worker_id]


@router.post("/resources/workers/{worker_id}/reset-limits", response_model=ResourceAllocation)
async def reset_worker_resource_limits(worker_id: str) -> ResourceAllocation:
    """
    Reset resource limits to defaults for a worker.

    Args:
        worker_id: Unique identifier for the worker/sandbox

    Returns:
        Confirmation of reset allocation settings
    """
    _ensure_worker_exists(worker_id)
    _worker_limits[worker_id] = ResourceLimits()  # Default values

    return ResourceAllocation(
        worker_id=worker_id,
        limits=_worker_limits[worker_id],
        applied_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/resources/alerts", response_model=List[Dict])
async def get_resource_alerts() -> List[Dict]:
    """
    Get all active resource alerts across all workers.

    Returns:
        List of active alerts with worker information
    """
    alerts = []
    worker_ids = list(_worker_limits.keys()) or ["worker-1", "worker-2", "worker-3"]

    for worker_id in worker_ids:
        status = _get_worker_status(worker_id)
        for alert_msg in status.alerts:
            alerts.append({
                "worker_id": worker_id,
                "message": alert_msg,
                "severity": status.status,
                "timestamp": status.metrics.timestamp,
            })

    return alerts
