"""Alert API routes per REQ-ALERT-001."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from omoi_os.models.monitor_anomaly import Alert
from omoi_os.schemas.alert import (
    AlertAcknowledgeRequest,
    AlertResponse,
    AlertResolveRequest,
    AlertRuleResponse,
)
from omoi_os.services.alerting import AlertService
from omoi_os.services.database import DatabaseService, get_db_service
from omoi_os.services.event_bus import EventBusService, get_event_bus_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


def get_alert_service(
    db: DatabaseService = Depends(get_db_service),
    event_bus: Optional[EventBusService] = Depends(get_event_bus_service),
) -> AlertService:
    """Get AlertService instance."""
    return AlertService(db=db, event_bus=event_bus)


@router.get("", response_model=List[AlertResponse])
async def list_alerts(
    severity: Optional[str] = None,
    limit: int = 100,
    alert_service: AlertService = Depends(get_alert_service),
):
    """List active alerts."""
    alerts = alert_service.get_active_alerts(severity=severity, limit=limit)
    return [AlertResponse.model_validate(alert) for alert in alerts]


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: UUID,
    db: DatabaseService = Depends(get_db_service),
):
    """Get alert details."""
    with db.get_session() as session:
        alert = session.get(Alert, str(alert_id))
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        session.expunge(alert)
        return AlertResponse.model_validate(alert)


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: UUID,
    request: AlertAcknowledgeRequest,
    alert_service: AlertService = Depends(get_alert_service),
):
    """Acknowledge an alert."""
    try:
        alert = alert_service.acknowledge_alert(
            str(alert_id), request.acknowledged_by
        )
        return AlertResponse.model_validate(alert)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: UUID,
    request: AlertResolveRequest,
    alert_service: AlertService = Depends(get_alert_service),
):
    """Resolve an alert."""
    try:
        alert = alert_service.resolve_alert(
            str(alert_id), request.resolved_by, request.note
        )
        return AlertResponse.model_validate(alert)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/rules", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    alert_service: AlertService = Depends(get_alert_service),
):
    """List alert rules."""
    rules = []
    for rule_id, rule in alert_service.rules.items():
        rules.append(
            AlertRuleResponse(
                rule_id=rule_id,
                name=rule.name,
                metric_name=rule.metric_name,
                condition=rule.condition,
                severity=rule.severity,
                routing=rule.routing,
                enabled=rule.enabled,
            )
        )
    return rules

