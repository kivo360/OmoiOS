"""Alert schemas for API requests and responses."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    """Alert response schema."""
    id: str
    rule_id: str
    metric_name: str
    severity: str
    current_value: float
    threshold: float
    message: str
    labels: Optional[dict] = None
    triggered_at: str
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None


class AlertAcknowledgeRequest(BaseModel):
    """Request to acknowledge an alert."""
    acknowledged_by: str = Field(..., description="User or agent ID acknowledging the alert")


class AlertResolveRequest(BaseModel):
    """Request to resolve an alert."""
    resolved_by: str = Field(..., description="User or agent ID resolving the alert")
    note: Optional[str] = Field(None, description="Optional resolution note")


class AlertRuleResponse(BaseModel):
    """Alert rule response schema."""
    rule_id: str
    name: str
    metric_name: str
    condition: str
    severity: str
    routing: List[str]
    enabled: bool

