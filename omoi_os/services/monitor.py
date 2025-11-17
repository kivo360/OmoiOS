"""Monitor service for metrics collection and anomaly detection."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Dict, List, Optional

from sqlalchemy import func

from omoi_os.models.agent import Agent
from omoi_os.models.monitor_anomaly import MonitorAnomaly
from omoi_os.models.resource_lock import ResourceLock
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.telemetry import MetricSample
from omoi_os.utils.datetime import utc_now


class MonitorService:
    """Service for collecting metrics and detecting anomalies."""

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
    ):
        """
        Initialize monitor service.

        Args:
            db: Database service
            event_bus: Optional event bus for publishing anomalies
        """
        self.db = db
        self.event_bus = event_bus
        self._metric_history: Dict[str, List[float]] = defaultdict(list)

    # ---------------------------------------------------------------------
    # Metrics Collection
    # ---------------------------------------------------------------------

    def collect_task_metrics(self, phase_id: Optional[str] = None) -> Dict[str, MetricSample]:
        """
        Collect task-related metrics.

        Args:
            phase_id: Optional phase filter

        Returns:
            Dictionary of metric name to MetricSample
        """
        now = utc_now()
        metrics = {}

        with self.db.get_session() as session:
            # Queue depth by phase
            query = session.query(
                Task.phase_id,
                Task.priority,
                func.count(Task.id).label("count")
            ).filter(Task.status == "pending")
            
            if phase_id:
                query = query.filter(Task.phase_id == phase_id)
            
            queue_stats = query.group_by(Task.phase_id, Task.priority).all()
            
            for phase, priority, count in queue_stats:
                metrics[f"tasks_queued_{phase}_{priority}"] = MetricSample(
                    metric_name="tasks_queued_total",
                    value=float(count),
                    labels={"phase_id": phase, "priority": priority},
                    timestamp=now,
                )

            # Completed tasks
            completed_query = session.query(
                Task.phase_id,
                func.count(Task.id).label("count")
            ).filter(Task.status == "completed")
            
            if phase_id:
                completed_query = completed_query.filter(Task.phase_id == phase_id)
            
            completed_stats = completed_query.group_by(Task.phase_id).all()
            
            for phase, count in completed_stats:
                metrics[f"tasks_completed_{phase}"] = MetricSample(
                    metric_name="tasks_completed_total",
                    value=float(count),
                    labels={"phase_id": phase},
                    timestamp=now,
                )

            # Task duration (completed in last hour)
            one_hour_ago = now - timedelta(hours=1)
            duration_query = session.query(
                Task.phase_id,
                func.avg(
                    func.extract('epoch', Task.completed_at - Task.started_at)
                ).label("avg_duration")
            ).filter(
                Task.status == "completed",
                Task.completed_at >= one_hour_ago,
                Task.started_at.isnot(None),
            )
            
            if phase_id:
                duration_query = duration_query.filter(Task.phase_id == phase_id)
            
            duration_stats = duration_query.group_by(Task.phase_id).all()
            
            for phase, avg_dur in duration_stats:
                if avg_dur:
                    metrics[f"task_duration_{phase}"] = MetricSample(
                        metric_name="task_duration_seconds",
                        value=float(avg_dur),
                        labels={"phase_id": phase},
                        timestamp=now,
                    )

        return metrics

    def collect_agent_metrics(self) -> Dict[str, MetricSample]:
        """Collect agent-related metrics."""
        now = utc_now()
        metrics = {}

        with self.db.get_session() as session:
            # Active agents by type
            agent_stats = session.query(
                Agent.agent_type,
                Agent.status,
                func.count(Agent.id).label("count")
            ).group_by(Agent.agent_type, Agent.status).all()

            for agent_type, status, count in agent_stats:
                if status in ["idle", "running"]:  # Active agents
                    metrics[f"agents_active_{agent_type}"] = MetricSample(
                        metric_name="agents_active",
                        value=float(count),
                        labels={"agent_type": agent_type, "status": status},
                        timestamp=now,
                    )

            # Heartbeat age
            agents = session.query(Agent).filter(
                Agent.last_heartbeat.isnot(None)
            ).all()

            for agent in agents:
                age_seconds = (now - agent.last_heartbeat).total_seconds()
                metrics[f"heartbeat_age_{agent.id}"] = MetricSample(
                    metric_name="agent_heartbeat_age_seconds",
                    value=age_seconds,
                    labels={"agent_id": agent.id, "agent_type": agent.agent_type},
                    timestamp=now,
                )

        return metrics

    def collect_lock_metrics(self) -> Dict[str, MetricSample]:
        """Collect resource lock metrics."""
        now = utc_now()
        metrics = {}

        with self.db.get_session() as session:
            # Active locks by type
            lock_stats = session.query(
                ResourceLock.resource_type,
                ResourceLock.lock_mode,
                func.count(ResourceLock.id).label("count")
            ).filter(
                ResourceLock.released_at.is_(None)
            ).group_by(ResourceLock.resource_type, ResourceLock.lock_mode).all()

            for res_type, lock_mode, count in lock_stats:
                metrics[f"locks_active_{res_type}_{lock_mode}"] = MetricSample(
                    metric_name="resource_locks_active",
                    value=float(count),
                    labels={"resource_type": res_type, "lock_mode": lock_mode},
                    timestamp=now,
                )

        return metrics

    def collect_all_metrics(self, phase_id: Optional[str] = None) -> Dict[str, MetricSample]:
        """
        Collect all system metrics.

        Args:
            phase_id: Optional phase filter for task metrics

        Returns:
            Dictionary of all metric samples
        """
        metrics = {}
        metrics.update(self.collect_task_metrics(phase_id))
        metrics.update(self.collect_agent_metrics())
        metrics.update(self.collect_lock_metrics())
        return metrics

    # ---------------------------------------------------------------------
    # Anomaly Detection
    # ---------------------------------------------------------------------

    def detect_anomalies(
        self,
        metric_samples: Dict[str, MetricSample],
        sensitivity: float = 2.0,
    ) -> List[MonitorAnomaly]:
        """
        Detect anomalies using rolling statistics.

        Args:
            metric_samples: Current metric samples
            sensitivity: Standard deviations for anomaly threshold (default: 2.0)

        Returns:
            List of detected anomalies
        """
        anomalies = []

        for metric_key, sample in metric_samples.items():
            # Update history
            self._metric_history[metric_key].append(sample.value)
            # Keep last 100 samples
            if len(self._metric_history[metric_key]) > 100:
                self._metric_history[metric_key] = self._metric_history[metric_key][-100:]

            # Need at least 10 samples for baseline
            if len(self._metric_history[metric_key]) < 10:
                continue

            # Calculate baseline statistics
            history = self._metric_history[metric_key]
            mean = sum(history) / len(history)
            variance = sum((x - mean) ** 2 for x in history) / len(history)
            std_dev = variance ** 0.5

            # Detect anomalies
            deviation = abs(sample.value - mean)
            deviation_percent = (deviation / mean * 100) if mean != 0 else 0

            if std_dev > 0 and deviation > (sensitivity * std_dev):
                # Anomaly detected
                if sample.value > mean:
                    anomaly_type = "spike"
                else:
                    anomaly_type = "drop"

                # Determine severity
                if deviation > (3 * std_dev):
                    severity = "critical"
                elif deviation > (2.5 * std_dev):
                    severity = "error"
                elif deviation > (2 * std_dev):
                    severity = "warning"
                else:
                    severity = "info"

                anomaly = self._create_anomaly(
                    metric_name=sample.metric_name,
                    anomaly_type=anomaly_type,
                    severity=severity,
                    baseline_value=mean,
                    observed_value=sample.value,
                    deviation_percent=deviation_percent,
                    labels=sample.labels,
                )
                anomalies.append(anomaly)

        return anomalies

    def _create_anomaly(
        self,
        metric_name: str,
        anomaly_type: str,
        severity: str,
        baseline_value: float,
        observed_value: float,
        deviation_percent: float,
        labels: Optional[dict] = None,
    ) -> MonitorAnomaly:
        """Create and persist an anomaly record."""
        description = (
            f"{metric_name} {anomaly_type}: observed {observed_value:.2f} "
            f"vs baseline {baseline_value:.2f} ({deviation_percent:.1f}% deviation)"
        )

        with self.db.get_session() as session:
            anomaly = MonitorAnomaly(
                metric_name=metric_name,
                anomaly_type=anomaly_type,
                severity=severity,
                baseline_value=baseline_value,
                observed_value=observed_value,
                deviation_percent=deviation_percent,
                description=description,
                labels=labels,
            )
            session.add(anomaly)
            session.commit()
            session.refresh(anomaly)
            session.expunge(anomaly)

            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="monitor.anomaly.detected",
                        entity_type="anomaly",
                        entity_id=anomaly.id,
                        payload={
                            "metric_name": metric_name,
                            "anomaly_type": anomaly_type,
                            "severity": severity,
                            "deviation_percent": deviation_percent,
                            "labels": labels,
                        },
                    )
                )

            return anomaly

    def get_recent_anomalies(
        self,
        hours: int = 24,
        severity: Optional[str] = None,
    ) -> List[MonitorAnomaly]:
        """
        Get recent anomalies.

        Args:
            hours: Look back period in hours
            severity: Optional severity filter

        Returns:
            List of MonitorAnomaly objects
        """
        cutoff = utc_now() - timedelta(hours=hours)

        with self.db.get_session() as session:
            query = session.query(MonitorAnomaly).filter(
                MonitorAnomaly.detected_at >= cutoff
            )

            if severity:
                query = query.filter(MonitorAnomaly.severity == severity)

            anomalies = query.order_by(MonitorAnomaly.detected_at.desc()).all()

            for anomaly in anomalies:
                session.expunge(anomaly)

            return anomalies

    def acknowledge_anomaly(self, anomaly_id: str) -> bool:
        """Acknowledge an anomaly."""
        with self.db.get_session() as session:
            anomaly = session.query(MonitorAnomaly).filter(
                MonitorAnomaly.id == anomaly_id
            ).first()
            if not anomaly:
                return False

            anomaly.acknowledged_at = utc_now()
            session.commit()
            return True

