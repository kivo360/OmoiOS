"""Heartbeat message models for bidirectional heartbeat protocol."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from omoi_os.utils.datetime import utc_now


class HeartbeatMessage(BaseModel):
    """
    Heartbeat message structure per REQ-ALM-002.

    Represents a heartbeat sent from an agent to the monitoring system.
    """

    agent_id: str = Field(..., description="UUID of the agent sending heartbeat")
    timestamp: datetime = Field(
        default_factory=utc_now, description="ISO8601 timestamp"
    )
    sequence_number: int = Field(
        ..., description="Monotonically increasing sequence number"
    )
    status: str = Field(
        ..., description="Agent status: idle, running, degraded, failed"
    )
    current_task_id: Optional[str] = Field(
        None, description="UUID of current task or null"
    )
    health_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Health metrics: cpu_usage_percent, memory_usage_mb, active_connections, etc.",
    )
    checksum: str = Field(
        ..., description="SHA256 checksum of payload for integrity validation"
    )


class HeartbeatAck(BaseModel):
    """
    Heartbeat acknowledgment message per REQ-FT-HB-001.

    Represents an acknowledgment sent back to the agent from the monitoring system.
    """

    agent_id: str = Field(..., description="UUID of the agent")
    sequence_number: int = Field(..., description="Sequence number being acknowledged")
    timestamp: datetime = Field(
        default_factory=utc_now, description="ISO8601 timestamp of ack"
    )
    received: bool = Field(
        True, description="Whether heartbeat was successfully processed"
    )
    message: Optional[str] = Field(
        None, description="Optional message (warnings, errors, etc.)"
    )
