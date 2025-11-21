"""API routes for monitoring and metrics."""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from omoi_os.api.dependencies import get_monitor_service, get_monitoring_loop
from omoi_os.services.monitor import MonitorService
from omoi_os.telemetry import MetricSample

router = APIRouter()


# ---------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------


class MetricSampleDTO(BaseModel):
    metric_name: str
    value: float
    labels: Dict[str, str]
    timestamp: str


class AnomalyDTO(BaseModel):
    anomaly_id: str
    metric_name: str
    anomaly_type: str
    severity: str
    baseline_value: float
    observed_value: float
    deviation_percent: float
    description: str
    labels: Optional[Dict[str, str]]
    detected_at: str
    acknowledged_at: Optional[str]


class DashboardSummary(BaseModel):
    total_tasks_pending: int
    total_tasks_completed: int
    active_agents: int
    stale_agents: int
    active_locks: int
    recent_anomalies: int
    critical_alerts: int


# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------


@router.get("/monitor/metrics", response_model=List[MetricSampleDTO])
async def get_metrics(
    phase_id: Optional[str] = Query(None, description="Filter by phase"),
    monitor: MonitorService = Depends(get_monitor_service),
):
    """Get current system metrics."""
    try:
        metric_samples = monitor.collect_all_metrics(phase_id)
        return [
            MetricSampleDTO(
                metric_name=sample.metric_name,
                value=sample.value,
                labels=sample.labels,
                timestamp=sample.timestamp.isoformat(),
            )
            for sample in metric_samples.values()
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to collect metrics: {exc}"
        ) from exc


@router.get("/monitor/anomalies", response_model=List[AnomalyDTO])
async def get_anomalies(
    hours: int = Query(24, description="Look back period in hours"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    monitor: MonitorService = Depends(get_monitor_service),
):
    """Get recent anomalies."""
    try:
        anomalies = monitor.get_recent_anomalies(hours=hours, severity=severity)
        return [
            AnomalyDTO(
                anomaly_id=a.id,
                metric_name=a.metric_name,
                anomaly_type=a.anomaly_type,
                severity=a.severity,
                baseline_value=a.baseline_value,
                observed_value=a.observed_value,
                deviation_percent=a.deviation_percent,
                description=a.description,
                labels=a.labels,
                detected_at=a.detected_at.isoformat(),
                acknowledged_at=a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            )
            for a in anomalies
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to get anomalies: {exc}"
        ) from exc


@router.post("/monitor/anomalies/{anomaly_id}/acknowledge", response_model=dict)
async def acknowledge_anomaly(
    anomaly_id: str,
    monitor: MonitorService = Depends(get_monitor_service),
):
    """Acknowledge an anomaly."""
    success = monitor.acknowledge_anomaly(anomaly_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Anomaly {anomaly_id} not found")
    return {"success": True, "anomaly_id": anomaly_id}


@router.get("/monitor/dashboard", response_model=DashboardSummary)
async def get_dashboard_summary(
    monitor: MonitorService = Depends(get_monitor_service),
):
    """Get dashboard summary statistics."""
    try:
        # Collect key metrics for dashboard
        metrics = monitor.collect_all_metrics()
        anomalies = monitor.get_recent_anomalies(hours=1, severity="critical")

        # Aggregate for dashboard
        total_pending = sum(
            m.value for k, m in metrics.items()
            if "tasks_queued" in k
        )
        total_completed = sum(
            m.value for k, m in metrics.items()
            if "tasks_completed" in k
        )
        # Sum all agents_active_* metrics since they're already filtered for active statuses (IDLE/RUNNING)
        # The status is in labels, but we've already filtered for active statuses when creating metrics
        active_agents = sum(
            m.value for k, m in metrics.items()
            if "agents_active" in k
        )
        
        # Get counts from metrics
        active_locks = sum(
            m.value for k, m in metrics.items()
            if "locks_active" in k
        )

        return DashboardSummary(
            total_tasks_pending=int(total_pending),
            total_tasks_completed=int(total_completed),
            active_agents=int(active_agents),
            stale_agents=0,  # TODO: Add stale agent metric
            active_locks=int(active_locks),
            recent_anomalies=len(monitor.get_recent_anomalies(hours=24)),
            critical_alerts=len(anomalies),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to get dashboard summary: {exc}"
        ) from exc


@router.get("/monitor/intelligent/status")
async def get_intelligent_monitoring_status(
    monitoring_loop = Depends(get_monitoring_loop),
):
    """Get intelligent monitoring loop status and metrics."""
    try:
        status = monitoring_loop.get_status()
        return status
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503, detail=f"Monitoring loop not available: {exc}"
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to get monitoring status: {exc}"
        ) from exc


@router.get("/monitor/intelligent/health")
async def get_intelligent_monitoring_health(
    monitoring_loop = Depends(get_monitoring_loop),
):
    """Get system health from intelligent monitoring."""
    try:
        health = await monitoring_loop.get_system_health()
        return health.dict()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503, detail=f"Monitoring loop not available: {exc}"
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to get system health: {exc}"
        ) from exc


@router.post("/monitor/intelligent/analyze/{agent_id}")
async def analyze_agent_trajectory(
    agent_id: str,
    force: bool = Query(False, description="Force fresh analysis"),
    monitoring_loop = Depends(get_monitoring_loop),
):
    """Trigger trajectory analysis for a specific agent."""
    try:
        analysis = await monitoring_loop.analyze_agent_trajectory(agent_id, force_analysis=force)
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found or no analysis available")
        return analysis.dict()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503, detail=f"Monitoring loop not available: {exc}"
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze agent: {exc}"
        ) from exc


@router.post("/monitor/intelligent/emergency")
async def trigger_emergency_analysis(
    agent_ids: List[str],
    monitoring_loop = Depends(get_monitoring_loop),
):
    """Trigger emergency analysis for specific agents."""
    try:
        result = await monitoring_loop.trigger_emergency_analysis(agent_ids)
        return result
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503, detail=f"Monitoring loop not available: {exc}"
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to trigger emergency analysis: {exc}"
        ) from exc

