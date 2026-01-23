"""Pydantic schemas for resource usage data and limits."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ThresholdLevel(str, Enum):
    """Threshold level for resource alerts."""

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class ResourceLimits(BaseModel):
    """Resource limits for a Daytona sandbox.

    Enforces Daytona constraints:
    - CPU: 1-4 cores
    - Memory: 1-8 GiB
    - Disk: 1-10 GiB
    """

    cpu_cores: int = Field(ge=1, le=4, description="Number of CPU cores (1-4)")
    memory_gib: int = Field(ge=1, le=8, description="Memory in GiB (1-8)")
    disk_gib: int = Field(ge=1, le=10, description="Disk space in GiB (1-10)")
    version: int = Field(ge=0, default=0, description="Version for optimistic locking")


class ResourceUsage(BaseModel):
    """Current resource usage metrics for a sandbox."""

    cpu_percent: float = Field(ge=0, le=100, description="CPU utilization percentage")
    memory_mb: float = Field(ge=0, description="Memory usage in MB")
    memory_percent: float = Field(ge=0, le=100, description="Memory utilization percentage")
    disk_gb: float = Field(ge=0, description="Disk usage in GB")
    disk_percent: float = Field(ge=0, le=100, description="Disk utilization percentage")


class ResourceUsageWithTimestamp(ResourceUsage):
    """Resource usage with timestamp for historical tracking."""

    timestamp: datetime = Field(..., description="Timestamp of the measurement")


class SandboxResourceMetrics(BaseModel):
    """Complete resource metrics for a sandbox."""

    sandbox_id: str = Field(..., description="Sandbox identifier")
    agent_id: Optional[UUID] = Field(None, description="Associated agent ID")
    usage: ResourceUsage = Field(..., description="Current resource usage")
    limits: ResourceLimits = Field(..., description="Resource limits")
    threshold_level: ThresholdLevel = Field(
        default=ThresholdLevel.NORMAL,
        description="Current threshold alert level"
    )
    collected_at: datetime = Field(..., description="When metrics were collected")

    model_config = ConfigDict(from_attributes=True)


class ResourceThresholds(BaseModel):
    """Configurable thresholds for resource alerts."""

    cpu_warning: float = Field(default=70.0, ge=0, le=100, description="CPU warning threshold %")
    cpu_critical: float = Field(default=90.0, ge=0, le=100, description="CPU critical threshold %")
    memory_warning: float = Field(default=70.0, ge=0, le=100, description="Memory warning threshold %")
    memory_critical: float = Field(default=90.0, ge=0, le=100, description="Memory critical threshold %")
    disk_warning: float = Field(default=80.0, ge=0, le=100, description="Disk warning threshold %")
    disk_critical: float = Field(default=95.0, ge=0, le=100, description="Disk critical threshold %")


class ResourceTrendPoint(BaseModel):
    """A single point in resource trend data."""

    timestamp: datetime = Field(..., description="Timestamp of measurement")
    cpu_percent: float = Field(ge=0, le=100, description="CPU utilization percentage")
    memory_percent: float = Field(ge=0, le=100, description="Memory utilization percentage")
    disk_percent: float = Field(ge=0, le=100, description="Disk utilization percentage")


class ResourceAlert(BaseModel):
    """Alert generated when resource thresholds are exceeded."""

    sandbox_id: str = Field(..., description="Sandbox identifier")
    agent_id: Optional[UUID] = Field(None, description="Associated agent ID")
    resource_type: str = Field(..., description="Type of resource: cpu, memory, disk")
    current_value: float = Field(..., description="Current utilization percentage")
    threshold_value: float = Field(..., description="Threshold that was exceeded")
    level: ThresholdLevel = Field(..., description="Alert level")
    message: str = Field(..., description="Human-readable alert message")
    triggered_at: datetime = Field(..., description="When the alert was triggered")
