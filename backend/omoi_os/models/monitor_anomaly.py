"""Monitoring and anomaly detection models."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class MonitorAnomaly(Base):
    """Detected anomaly in system metrics."""

    __tablename__ = "monitor_anomalies"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    metric_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    anomaly_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # spike, drop, threshold_breach, pattern_change
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # info, warning, error, critical

    baseline_value: Mapped[float] = mapped_column(Float, nullable=False)
    observed_value: Mapped[float] = mapped_column(Float, nullable=False)
    deviation_percent: Mapped[float] = mapped_column(Float, nullable=False)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    labels: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    context: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Additional diagnostic info

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Alert(Base):
    """Active alert from monitoring system."""

    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    rule_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # info, warning, error, critical

    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    labels: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
