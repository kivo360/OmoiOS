"""Composite anomaly scorer for agent-level anomaly detection."""

from typing import Dict, Optional

from omoi_os.models.agent import Agent
from omoi_os.models.agent_baseline import AgentBaseline
from omoi_os.models.task import Task
from omoi_os.services.baseline_learner import BaselineLearner
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now


class CompositeAnomalyScorer:
    """
    Composite anomaly scorer per REQ-FT-AN-001.
    
    Computes anomaly_score (0-1) from:
    - Latency deviation (z-score)
    - Error rate trend (EMA)
    - Resource skew (CPU/Memory vs baseline)
    - Queue impact (blocked dependents)
    """

    # Weight distribution per REQ-FT-AN-001 (sums to 1.0)
    LATENCY_WEIGHT = 0.35
    ERROR_RATE_WEIGHT = 0.30
    RESOURCE_SKEW_WEIGHT = 0.20
    QUEUE_IMPACT_WEIGHT = 0.15

    # Default threshold per REQ-FT-AN-001
    ANOMALY_THRESHOLD = 0.8

    # EMA decay factor for error rate
    ERROR_RATE_EMA_ALPHA = 0.1

    def __init__(self, db: DatabaseService, baseline_learner: BaselineLearner):
        """
        Initialize CompositeAnomalyScorer.

        Args:
            db: Database service instance
            baseline_learner: BaselineLearner service for retrieving baselines
        """
        self.db = db
        self.baseline_learner = baseline_learner

        # Track error rate EMA per agent (in-memory cache)
        # In production, this could be stored in database
        self._error_rate_ema: Dict[str, float] = {}

    def compute_anomaly_score(
        self,
        agent_id: str,
        latency_ms: Optional[float] = None,
        error_rate: Optional[float] = None,
        cpu_usage_percent: Optional[float] = None,
        memory_usage_mb: Optional[float] = None,
        health_metrics: Optional[Dict] = None,
    ) -> float:
        """
        Compute composite anomaly score per REQ-FT-AN-001.

        Args:
            agent_id: Agent ID
            latency_ms: Current latency in milliseconds (optional, will be computed if None)
            error_rate: Current error rate (optional, will be computed if None)
            cpu_usage_percent: Current CPU usage percentage (optional, from health_metrics)
            memory_usage_mb: Current memory usage in MB (optional, from health_metrics)
            health_metrics: Health metrics dict from heartbeat (optional)

        Returns:
            Composite anomaly score (0-1)
        """
        with self.db.get_session() as session:
            agent = session.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                return 0.0

            # Extract health metrics if provided
            if health_metrics:
                cpu_usage_percent = cpu_usage_percent or health_metrics.get(
                    "cpu_usage_percent", 0.0
                )
                memory_usage_mb = memory_usage_mb or health_metrics.get(
                    "memory_usage_mb", 0.0
                )

            # Get baseline for agent type and phase
            baseline = self.baseline_learner.get_baseline(
                agent.agent_type, agent.phase_id
            )

            # Compute each component score
            latency_score = self.compute_latency_z_score(
                agent_id, latency_ms, agent, baseline
            )

            error_rate_score = self.compute_error_rate_ema(
                agent_id, error_rate, agent, baseline
            )

            resource_score = self.compute_resource_skew(
                agent_id,
                cpu_usage_percent,
                memory_usage_mb,
                agent,
                baseline,
            )

            queue_score = self.compute_queue_impact(agent_id, session)

            # Normalize each component to [0, 1] range
            latency_normalized = min(1.0, abs(latency_score) / 3.0)  # z-score > 3 is extreme
            error_rate_normalized = min(1.0, error_rate_score)
            resource_normalized = min(1.0, resource_score)
            queue_normalized = min(1.0, queue_score)

            # Weighted combination per REQ-FT-AN-001
            composite = (
                self.LATENCY_WEIGHT * latency_normalized
                + self.ERROR_RATE_WEIGHT * error_rate_normalized
                + self.RESOURCE_SKEW_WEIGHT * resource_normalized
                + self.QUEUE_IMPACT_WEIGHT * queue_normalized
            )

            return min(1.0, composite)

    def compute_latency_z_score(
        self,
        agent_id: str,
        latency_ms: Optional[float],
        agent: Agent,
        baseline: Optional[AgentBaseline],
    ) -> float:
        """
        Compute z-score for latency against baseline per REQ-FT-AN-001.

        Args:
            agent_id: Agent ID
            latency_ms: Current latency in milliseconds (computed if None)
            agent: Agent object
            baseline: AgentBaseline object

        Returns:
            Z-score (standard deviations from baseline)
        """
        # Compute latency if not provided
        if latency_ms is None:
            latency_ms = self._compute_agent_latency(agent_id)

        if not baseline or baseline.latency_std == 0:
            return 0.0  # No baseline or no variance

        # Z-score = (observed - mean) / std_dev
        # Convert Decimal to float for PostgreSQL compatibility
        baseline_latency = float(baseline.latency_ms) if baseline.latency_ms else 0.0
        baseline_std = float(baseline.latency_std) if baseline.latency_std else 1.0
        z_score = (latency_ms - baseline_latency) / baseline_std
        return z_score

    def compute_error_rate_ema(
        self,
        agent_id: str,
        error_rate: Optional[float],
        agent: Agent,
        baseline: Optional[AgentBaseline],
    ) -> float:
        """
        Compute error rate EMA (exponential moving average) per REQ-FT-AN-001.

        Args:
            agent_id: Agent ID
            error_rate: Current error rate (computed if None)
            agent: Agent object
            baseline: AgentBaseline object

        Returns:
            Error rate EMA (0-1)
        """
        # Compute error rate if not provided
        if error_rate is None:
            error_rate = self._compute_agent_error_rate(agent_id)

        # Update EMA
        if agent_id not in self._error_rate_ema:
            self._error_rate_ema[agent_id] = error_rate
        else:
            # EMA: new_value = alpha * current + (1 - alpha) * previous
            self._error_rate_ema[agent_id] = (
                self.ERROR_RATE_EMA_ALPHA * error_rate
                + (1 - self.ERROR_RATE_EMA_ALPHA) * self._error_rate_ema[agent_id]
            )

        ema_value = self._error_rate_ema[agent_id]

        # Compare to baseline (if baseline exists, compute deviation)
        if baseline and baseline.error_rate > 0:
            # Return relative error rate increase
            baseline_error_rate = float(baseline.error_rate) if baseline.error_rate else 0.0
            if baseline_error_rate > 0:
                return max(0.0, (ema_value - baseline_error_rate) / baseline_error_rate)
            return ema_value

        return ema_value

    def compute_resource_skew(
        self,
        agent_id: str,
        cpu_usage_percent: Optional[float],
        memory_usage_mb: Optional[float],
        agent: Agent,
        baseline: Optional[AgentBaseline],
    ) -> float:
        """
        Compute resource skew (CPU/Memory vs baseline) per REQ-FT-AN-001.

        Args:
            agent_id: Agent ID
            cpu_usage_percent: Current CPU usage percentage
            memory_usage_mb: Current memory usage in MB
            agent: Agent object
            baseline: AgentBaseline object

        Returns:
            Resource skew score (0-1), higher = more skewed
        """
        if not baseline:
            return 0.0  # No baseline to compare

        cpu_skew = 0.0
        memory_skew = 0.0

        # Convert Decimal to float for PostgreSQL compatibility
        baseline_cpu = float(baseline.cpu_usage_percent) if baseline.cpu_usage_percent else 0.0
        baseline_memory = float(baseline.memory_usage_mb) if baseline.memory_usage_mb else 0.0

        # CPU skew
        if cpu_usage_percent is not None and baseline_cpu > 0:
            cpu_deviation = abs(cpu_usage_percent - baseline_cpu)
            # Normalize by baseline (if baseline is 50%, deviation of 50% = 1.0)
            cpu_skew = min(1.0, cpu_deviation / max(baseline_cpu, 1.0))

        # Memory skew
        if memory_usage_mb is not None and baseline_memory > 0:
            memory_deviation = abs(memory_usage_mb - baseline_memory)
            memory_skew = min(
                1.0, memory_deviation / max(baseline_memory, 1.0)
            )

        # Average of CPU and memory skew
        resource_skew = (cpu_skew + memory_skew) / 2.0 if (cpu_skew or memory_skew) else 0.0
        return resource_skew

    def compute_queue_impact(self, agent_id: str, session) -> float:
        """
        Compute queue impact (blocked dependents) per REQ-FT-AN-001.

        Args:
            agent_id: Agent ID
            session: Database session

        Returns:
            Queue impact score (0-1), higher = more tasks blocked
        """
        # Count tasks assigned to this agent that are blocking others
        agent_tasks = (
            session.query(Task)
            .filter(
                Task.assigned_agent_id == agent_id,
                Task.status.in_(["assigned", "running"]),
            )
            .all()
        )

        if not agent_tasks:
            return 0.0

        # Count tasks that depend on these tasks
        blocking_count = 0
        total_dependents = 0

        for task in agent_tasks:
            # Find tasks that depend on this task
            dependents = (
                session.query(Task)
                .filter(
                    Task.dependencies.isnot(None),
                    Task.status == "pending",
                )
                .all()
            )

            for dependent in dependents:
                if dependent.dependencies and dependent.dependencies.get(
                    "depends_on"
                ):
                    depends_on = dependent.dependencies["depends_on"]
                    if isinstance(depends_on, list) and task.id in depends_on:
                        total_dependents += 1
                        if dependent.priority == "CRITICAL":
                            blocking_count += 2  # CRITICAL tasks count double
                        else:
                            blocking_count += 1

        # Normalize: max impact if blocking many high-priority tasks
        # Normalize to [0, 1] range (assuming max reasonable blocking is 10 tasks)
        queue_impact = min(1.0, blocking_count / 10.0)
        return queue_impact

    def _compute_agent_latency(self, agent_id: str) -> float:
        """Compute average task latency for agent (in milliseconds)."""
        from datetime import timedelta
        from sqlalchemy import func

        with self.db.get_session() as session:
            one_hour_ago = utc_now() - timedelta(hours=1)
            result = (
                session.query(
                    func.avg(
                        func.extract(
                            "epoch", Task.completed_at - Task.started_at
                        )
                        * 1000
                    ).label("avg_latency_ms")
                )
                .filter(
                    Task.assigned_agent_id == agent_id,
                    Task.status == "completed",
                    Task.completed_at >= one_hour_ago,
                    Task.started_at.isnot(None),
                )
                .scalar()
            )

            return float(result) if result else 0.0

    def _compute_agent_error_rate(self, agent_id: str) -> float:
        """Compute error rate for agent (0-1)."""
        from datetime import timedelta
        from sqlalchemy import func

        with self.db.get_session() as session:
            one_hour_ago = utc_now() - timedelta(hours=1)

            total_tasks = (
                session.query(func.count(Task.id))
                .filter(
                    Task.assigned_agent_id == agent_id,
                    Task.status.in_(["completed", "failed"]),
                    Task.completed_at >= one_hour_ago,
                )
                .scalar()
            )

            if total_tasks == 0:
                return 0.0

            failed_tasks = (
                session.query(func.count(Task.id))
                .filter(
                    Task.assigned_agent_id == agent_id,
                    Task.status == "failed",
                    Task.completed_at >= one_hour_ago,
                )
                .scalar()
            )

            return failed_tasks / total_tasks

