"""Agent baseline model for anomaly detection."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class AgentBaseline(Base):
    """
    Baseline metrics for agent types and phases per REQ-FT-AN-002.
    
    Stores learned baselines (latency, error rate, CPU, memory) per agent_type/phase_id
    combination for anomaly detection.
    """

    __tablename__ = "agent_baselines"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    agent_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # worker, monitor, watchdog, guardian
    phase_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )  # Optional phase identifier
    
    # Baseline metrics (learned via EMA)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="Baseline latency in milliseconds")
    latency_std: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, comment="Standard deviation of latency")
    error_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="Baseline error rate (0-1)")
    cpu_usage_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="Baseline CPU usage percentage")
    memory_usage_mb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="Baseline memory usage in MB")
    
    # Additional metrics stored as JSONB for flexibility
    additional_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="Additional baseline metrics (e.g., active_connections, pending_operations)"
    )
    
    # Metadata
    sample_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Number of samples used to compute baseline"
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


