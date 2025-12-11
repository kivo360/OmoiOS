"""Baseline learning service for anomaly detection."""

from typing import Dict, Optional

from omoi_os.models.agent_baseline import AgentBaseline
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now


class BaselineLearner:
    """
    Baseline learning service per REQ-FT-AN-002.
    
    Learns per-agent-type and phase baselines using exponential moving average (EMA).
    Decays baselines after agent resurrection to allow re-learning.
    """

    # EMA learning rate (alpha) for baseline updates
    LEARNING_RATE = 0.1  # How much weight to give new observations

    # Baseline decay factor after resurrection
    DECAY_FACTOR = 0.9  # Reduce baseline values by 10% after resurrection

    def __init__(self, db: DatabaseService):
        """
        Initialize BaselineLearner.

        Args:
            db: Database service instance
        """
        self.db = db

    def learn_baseline(
        self,
        agent_type: str,
        phase_id: Optional[str],
        metrics: Dict[str, float],
    ) -> AgentBaseline:
        """
        Update baseline using exponential moving average per REQ-FT-AN-002.

        Args:
            agent_type: Type of agent (worker, monitor, etc.)
            phase_id: Optional phase identifier
            metrics: Dictionary of current metrics with keys:
                - latency_ms: Task latency in milliseconds
                - error_rate: Error rate (0-1)
                - cpu_usage_percent: CPU usage percentage
                - memory_usage_mb: Memory usage in MB
                - Additional metrics (optional)

        Returns:
            Updated AgentBaseline object
        """
        with self.db.get_session() as session:
            # Find or create baseline
            baseline = (
                session.query(AgentBaseline)
                .filter(
                    AgentBaseline.agent_type == agent_type,
                    AgentBaseline.phase_id == phase_id,
                )
                .first()
            )

            if not baseline:
                # Initialize baseline with first observation
                baseline = AgentBaseline(
                    agent_type=agent_type,
                    phase_id=phase_id,
                    latency_ms=metrics.get("latency_ms", 0.0),
                    latency_std=metrics.get("latency_std", 1.0),
                    error_rate=metrics.get("error_rate", 0.0),
                    cpu_usage_percent=metrics.get("cpu_usage_percent", 0.0),
                    memory_usage_mb=metrics.get("memory_usage_mb", 0.0),
                    additional_metrics={k: v for k, v in metrics.items() if k not in [
                        "latency_ms", "latency_std", "error_rate",
                        "cpu_usage_percent", "memory_usage_mb"
                    ]},
                    sample_count=1,
                    last_updated=utc_now(),
                )
                session.add(baseline)
            else:
                # EMA update: new_baseline = alpha * metrics + (1 - alpha) * baseline
                alpha = self.LEARNING_RATE

                # Update latency (also update std dev if provided)
                if "latency_ms" in metrics:
                    baseline.latency_ms = (
                        alpha * metrics["latency_ms"]
                        + (1 - alpha) * baseline.latency_ms
                    )
                if "latency_std" in metrics:
                    baseline.latency_std = (
                        alpha * metrics["latency_std"]
                        + (1 - alpha) * baseline.latency_std
                    )

                # Update error rate (EMA)
                if "error_rate" in metrics:
                    baseline.error_rate = (
                        alpha * metrics["error_rate"]
                        + (1 - alpha) * baseline.error_rate
                    )

                # Update resource metrics
                if "cpu_usage_percent" in metrics:
                    baseline.cpu_usage_percent = (
                        alpha * metrics["cpu_usage_percent"]
                        + (1 - alpha) * baseline.cpu_usage_percent
                    )
                if "memory_usage_mb" in metrics:
                    baseline.memory_usage_mb = (
                        alpha * metrics["memory_usage_mb"]
                        + (1 - alpha) * baseline.memory_usage_mb
                    )

                # Update additional metrics
                if baseline.additional_metrics is None:
                    baseline.additional_metrics = {}

                for key, value in metrics.items():
                    if key not in [
                        "latency_ms",
                        "latency_std",
                        "error_rate",
                        "cpu_usage_percent",
                        "memory_usage_mb",
                    ]:
                        if key in baseline.additional_metrics:
                            baseline.additional_metrics[key] = (
                                alpha * value
                                + (1 - alpha) * baseline.additional_metrics[key]
                            )
                        else:
                            baseline.additional_metrics[key] = value

                baseline.sample_count += 1
                baseline.last_updated = utc_now()

            session.commit()
            session.refresh(baseline)
            session.expunge(baseline)
            return baseline

    def get_baseline(
        self, agent_type: str, phase_id: Optional[str]
    ) -> Optional[AgentBaseline]:
        """
        Get baseline for agent type and phase.

        Args:
            agent_type: Type of agent
            phase_id: Optional phase identifier

        Returns:
            AgentBaseline object or None if not found
        """
        with self.db.get_session() as session:
            baseline = (
                session.query(AgentBaseline)
                .filter(
                    AgentBaseline.agent_type == agent_type,
                    AgentBaseline.phase_id == phase_id,
                )
                .first()
            )

            if baseline:
                session.expunge(baseline)

            return baseline

    def decay_baseline(self, agent_type: str, phase_id: Optional[str]) -> None:
        """
        Decay baseline after agent resurrection per REQ-FT-AN-002.

        This allows the baseline to adapt to changed conditions after restart.

        Args:
            agent_type: Type of agent
            phase_id: Optional phase identifier
        """
        with self.db.get_session() as session:
            baseline = (
                session.query(AgentBaseline)
                .filter(
                    AgentBaseline.agent_type == agent_type,
                    AgentBaseline.phase_id == phase_id,
                )
                .first()
            )

            if baseline:
                # Apply decay factor to all metrics
                baseline.latency_ms *= self.DECAY_FACTOR
                baseline.latency_std *= self.DECAY_FACTOR
                baseline.error_rate *= self.DECAY_FACTOR
                baseline.cpu_usage_percent *= self.DECAY_FACTOR
                baseline.memory_usage_mb *= self.DECAY_FACTOR

                if baseline.additional_metrics:
                    baseline.additional_metrics = {
                        k: v * self.DECAY_FACTOR
                        for k, v in baseline.additional_metrics.items()
                    }

                baseline.last_updated = utc_now()
                session.commit()


