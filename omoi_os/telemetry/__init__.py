"""Telemetry configuration and shared contracts for Phase 4 monitoring."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class MetricType(str, Enum):
    """Metric types for monitoring."""

    COUNTER = "counter"  # Cumulative count (tasks completed, events published)
    GAUGE = "gauge"  # Point-in-time value (queue depth, active agents)
    HISTOGRAM = "histogram"  # Distribution (task latency, lock wait time)
    SUMMARY = "summary"  # Aggregated stats (p50, p95, p99)


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricDefinition:
    """Definition of a monitoring metric."""

    name: str
    metric_type: MetricType
    description: str
    unit: str
    labels: list[str]  # Label names (agent_id, phase_id, etc.)


@dataclass
class MetricSample:
    """A single metric measurement."""

    metric_name: str
    value: float
    labels: dict[str, str]
    timestamp: datetime


@dataclass
class AlertRule:
    """Alert rule configuration."""

    rule_id: str
    metric_name: str
    condition: str  # "gt", "lt", "eq", etc.
    threshold: float
    severity: AlertSeverity
    duration_seconds: int  # How long condition must be true
    description: str
    routing: list[str]  # Channels: ["email", "slack", "webhook"]


@dataclass
class Alert:
    """Active alert instance."""

    alert_id: str
    rule_id: str
    metric_name: str
    current_value: float
    threshold: float
    severity: AlertSeverity
    message: str
    labels: dict[str, str]
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


# ---------------------------------------------------------------------
# Standard Metrics Catalog
# ---------------------------------------------------------------------

STANDARD_METRICS = [
    # Task Metrics
    MetricDefinition(
        name="tasks_queued_total",
        metric_type=MetricType.GAUGE,
        description="Number of tasks in pending state",
        unit="count",
        labels=["phase_id", "priority"],
    ),
    MetricDefinition(
        name="tasks_completed_total",
        metric_type=MetricType.COUNTER,
        description="Total tasks completed",
        unit="count",
        labels=["phase_id", "agent_id"],
    ),
    MetricDefinition(
        name="task_duration_seconds",
        metric_type=MetricType.HISTOGRAM,
        description="Task execution duration",
        unit="seconds",
        labels=["phase_id", "task_type"],
    ),
    # Agent Metrics
    MetricDefinition(
        name="agents_active",
        metric_type=MetricType.GAUGE,
        description="Number of active agents",
        unit="count",
        labels=["agent_type", "phase_id"],
    ),
    MetricDefinition(
        name="agent_heartbeat_age_seconds",
        metric_type=MetricType.GAUGE,
        description="Time since last heartbeat",
        unit="seconds",
        labels=["agent_id"],
    ),
    # Lock Metrics
    MetricDefinition(
        name="resource_locks_active",
        metric_type=MetricType.GAUGE,
        description="Number of active resource locks",
        unit="count",
        labels=["resource_type"],
    ),
    MetricDefinition(
        name="lock_wait_time_seconds",
        metric_type=MetricType.HISTOGRAM,
        description="Time spent waiting for locks",
        unit="seconds",
        labels=["resource_type", "lock_mode"],
    ),
    # Collaboration Metrics
    MetricDefinition(
        name="collaboration_threads_active",
        metric_type=MetricType.GAUGE,
        description="Number of active collaboration threads",
        unit="count",
        labels=["thread_type"],
    ),
    MetricDefinition(
        name="handoffs_requested_total",
        metric_type=MetricType.COUNTER,
        description="Total handoff requests",
        unit="count",
        labels=["from_agent_id", "to_agent_id"],
    ),
]


__all__ = [
    "Alert",
    "AlertRule",
    "AlertSeverity",
    "MetricDefinition",
    "MetricSample",
    "MetricType",
    "STANDARD_METRICS",
]

