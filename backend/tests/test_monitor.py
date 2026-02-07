"""Tests for monitor service."""

import pytest

from omoi_os.services.monitor import MonitorService
from omoi_os.telemetry import MetricSample
from tests.test_helpers import create_test_agent, create_test_task, create_test_ticket


@pytest.fixture
def monitor_service(db_service, event_bus_service):
    """Create monitor service instance."""
    return MonitorService(db_service, event_bus_service)


class TestMetricsCollection:
    """Tests for metrics collection."""

    def test_collect_task_metrics(self, monitor_service, db_service):
        """Test collecting task metrics."""
        ticket = create_test_ticket(db_service)

        # Create tasks in different states
        create_test_task(
            db_service,
            ticket_id=ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            priority="HIGH",
            status="pending",
        )
        create_test_task(
            db_service,
            ticket_id=ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            priority="MEDIUM",
            status="pending",
        )
        create_test_task(
            db_service,
            ticket_id=ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            status="completed",
        )

        metrics = monitor_service.collect_task_metrics("PHASE_IMPLEMENTATION")

        # Should have queue depth metrics
        assert any("tasks_queued" in k for k in metrics.keys())
        assert any("tasks_completed" in k for k in metrics.keys())

    def test_collect_agent_metrics(self, monitor_service, db_service):
        """Test collecting agent metrics."""
        create_test_agent(db_service, status="idle")
        create_test_agent(db_service, status="running")

        metrics = monitor_service.collect_agent_metrics()

        # Should have agent count metrics
        assert any("agents_active" in k for k in metrics.keys())
        # Should have heartbeat age metrics
        assert any("heartbeat_age" in k for k in metrics.keys())

    def test_collect_lock_metrics(self, monitor_service, db_service):
        """Test collecting lock metrics."""
        from omoi_os.services.resource_lock import ResourceLockService
        from tests.test_helpers import (
            create_test_agent,
            create_test_task,
            create_test_ticket,
        )

        lock_service = ResourceLockService(db_service)
        agent = create_test_agent(db_service)
        ticket = create_test_ticket(db_service)
        task = create_test_task(db_service, ticket_id=ticket.id)

        # Create a lock
        lock_service.acquire_lock(
            resource_type="file",
            resource_id="/test.py",
            task_id=task.id,
            agent_id=agent.id,
        )

        metrics = monitor_service.collect_lock_metrics()

        # Should have lock count metrics
        assert any("locks_active" in k for k in metrics.keys())

    def test_collect_all_metrics(self, monitor_service, db_service):
        """Test collecting all metrics."""
        ticket = create_test_ticket(db_service)
        create_test_task(db_service, ticket_id=ticket.id, status="pending")
        create_test_agent(db_service)

        metrics = monitor_service.collect_all_metrics()

        # Should have all metric types
        assert len(metrics) > 0
        assert all(isinstance(m, MetricSample) for m in metrics.values())


class TestAnomalyDetection:
    """Tests for anomaly detection."""

    def test_detect_anomalies_no_baseline(self, monitor_service):
        """Test that anomaly detection requires baseline."""
        metrics = {
            "test_metric": MetricSample(
                metric_name="test",
                value=100.0,
                labels={},
                timestamp=pytest.importorskip("omoi_os.utils.datetime").utc_now(),
            )
        }

        # First few samples shouldn't trigger anomalies (building baseline)
        for _ in range(5):
            anomalies = monitor_service.detect_anomalies(metrics)
            assert len(anomalies) == 0

    def test_detect_spike_anomaly(self, monitor_service):
        """Test detecting spike anomalies."""
        from omoi_os.utils.datetime import utc_now

        # Build baseline (mean ~100, std_dev ~10)
        for i in range(20):
            metrics = {
                "test_metric": MetricSample(
                    metric_name="test_counter",
                    value=100.0 + (i % 10),
                    labels={"phase": "test"},
                    timestamp=utc_now(),
                )
            }
            monitor_service.detect_anomalies(metrics, sensitivity=2.0)

        # Inject spike (value >> baseline)
        spike_metrics = {
            "test_metric": MetricSample(
                metric_name="test_counter",
                value=200.0,  # 2x baseline
                labels={"phase": "test"},
                timestamp=utc_now(),
            )
        }

        anomalies = monitor_service.detect_anomalies(spike_metrics, sensitivity=2.0)
        assert len(anomalies) > 0
        assert anomalies[0].anomaly_type == "spike"

    def test_detect_drop_anomaly(self, monitor_service):
        """Test detecting drop anomalies."""
        from omoi_os.utils.datetime import utc_now

        # Build baseline
        for i in range(20):
            metrics = {
                "test_metric": MetricSample(
                    metric_name="test_gauge",
                    value=100.0,
                    labels={},
                    timestamp=utc_now(),
                )
            }
            monitor_service.detect_anomalies(metrics)

        # Inject drop
        drop_metrics = {
            "test_metric": MetricSample(
                metric_name="test_gauge",
                value=10.0,  # Significant drop
                labels={},
                timestamp=utc_now(),
            )
        }

        anomalies = monitor_service.detect_anomalies(drop_metrics, sensitivity=2.0)
        assert len(anomalies) > 0
        assert anomalies[0].anomaly_type == "drop"

    def test_anomaly_severity_levels(self, monitor_service):
        """Test that severity scales with deviation."""
        from omoi_os.utils.datetime import utc_now

        # Build baseline
        for i in range(20):
            metrics = {
                "test_metric": MetricSample(
                    metric_name="test",
                    value=100.0,
                    labels={},
                    timestamp=utc_now(),
                )
            }
            monitor_service.detect_anomalies(metrics)

        # 3+ sigma deviation should be critical
        critical_metrics = {
            "test_metric": MetricSample(
                metric_name="test",
                value=300.0,
                labels={},
                timestamp=utc_now(),
            )
        }

        anomalies = monitor_service.detect_anomalies(critical_metrics, sensitivity=2.0)
        if anomalies:
            # Should be high severity due to large deviation
            assert anomalies[0].severity in ["error", "critical"]


class TestAnomalyManagement:
    """Tests for anomaly management."""

    def test_get_recent_anomalies(self, monitor_service, db_service):
        """Test retrieving recent anomalies."""

        # Create an anomaly
        anomaly = monitor_service._create_anomaly(
            metric_name="test_metric",
            anomaly_type="spike",
            severity="warning",
            baseline_value=100.0,
            observed_value=150.0,
            deviation_percent=50.0,
        )

        # Retrieve recent anomalies
        anomalies = monitor_service.get_recent_anomalies(hours=24)
        assert len(anomalies) >= 1
        assert any(a.id == anomaly.id for a in anomalies)

    def test_get_recent_anomalies_severity_filter(self, monitor_service):
        """Test filtering anomalies by severity."""
        # Create anomalies with different severities
        monitor_service._create_anomaly(
            metric_name="test1",
            anomaly_type="spike",
            severity="warning",
            baseline_value=100.0,
            observed_value=120.0,
            deviation_percent=20.0,
        )
        monitor_service._create_anomaly(
            metric_name="test2",
            anomaly_type="spike",
            severity="critical",
            baseline_value=100.0,
            observed_value=200.0,
            deviation_percent=100.0,
        )

        # Get only critical
        critical = monitor_service.get_recent_anomalies(hours=24, severity="critical")
        assert all(a.severity == "critical" for a in critical)

    def test_acknowledge_anomaly(self, monitor_service):
        """Test acknowledging an anomaly."""
        anomaly = monitor_service._create_anomaly(
            metric_name="test",
            anomaly_type="spike",
            severity="warning",
            baseline_value=100.0,
            observed_value=150.0,
            deviation_percent=50.0,
        )

        success = monitor_service.acknowledge_anomaly(anomaly.id)
        assert success is True

        # Verify acknowledged
        anomalies = monitor_service.get_recent_anomalies(hours=1)
        ack_anomaly = next(a for a in anomalies if a.id == anomaly.id)
        assert ack_anomaly.acknowledged_at is not None
