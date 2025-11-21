"""Agent model for agent registry."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.cost_record import CostRecord
    from omoi_os.models.auth import APIKey
    from omoi_os.models.organization import OrganizationMembership


class Agent(Base):
    """Agent represents a registered worker, monitor, watchdog, or guardian agent."""

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    agent_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Human-readable name: {type}-{phase}-{sequence} (REQ-ALM-001)",
    )
    agent_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # worker, monitor, watchdog, guardian
    phase_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )  # For worker agents: which phase they handle
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # SPAWNING, IDLE, RUNNING, DEGRADED, FAILED, QUARANTINED, TERMINATED (REQ-ALM-004)
    capabilities: Mapped[list[str]] = mapped_column(
        PG_ARRAY(String(100)), nullable=False, default=list
    )  # Tools, skills available to agent
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    health_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unknown", index=True
    )
    tags: Mapped[Optional[list[str]]] = mapped_column(
        PG_ARRAY(String(50)), nullable=True
    )
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Enhanced heartbeat protocol fields (REQ-ALM-002, REQ-FT-HB-003)
    sequence_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Monotonically increasing sequence number for heartbeat
    last_expected_sequence: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Last expected sequence number (for gap detection)
    consecutive_missed_heartbeats: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Count of consecutive missed heartbeats (for escalation ladder)

    # Validation field (REQ-VAL-DM-002)
    kept_alive_for_validation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # Whether the agent should be retained across iterations for validation-driven work

    # Anomaly detection field (REQ-FT-AN-001)
    anomaly_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        index=True,
        comment="Composite anomaly score (0-1) from latency, error rate, resource skew, queue impact",
    )
    consecutive_anomalous_readings: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Count of consecutive readings with anomaly_score >= threshold",
    )

    # Registration enhancement fields (REQ-ALM-001)
    crypto_public_key: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Public key from cryptographic identity pair (REQ-ALM-001)",
    )
    crypto_identity_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Cryptographic identity metadata: key_id, algorithm, created_at (REQ-ALM-001)",
    )
    agent_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        name="metadata",
        comment="Additional agent metadata: version, binary_path, config, resource_requirements (REQ-ALM-001)",
    )
    registered_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Orchestrator instance that registered this agent (REQ-ALM-001)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    cost_records: Mapped[list["CostRecord"]] = relationship(
        "CostRecord", back_populates="agent", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey",
        back_populates="agent",
        foreign_keys="APIKey.agent_id",
        cascade="all, delete-orphan",
    )
    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        "OrganizationMembership",
        back_populates="agent",
        foreign_keys="OrganizationMembership.agent_id",
        cascade="all, delete-orphan",
    )
    # Note: spawned_by_user relationship not included due to type mismatch
    # (Agent.registered_by is VARCHAR, User.id is UUID)
