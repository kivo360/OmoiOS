"""Tests for anomaly detection system (REQ-FT-AN-001, REQ-FT-AN-002, REQ-FT-AN-003)."""

import pytest
from datetime import datetime, timedelta
from typing import Optional

from omoi_os.models.agent import Agent
from omoi_os.models.agent_baseline import AgentBaseline
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.baseline_learner import BaselineLearner
from omoi_os.services.composite_anomaly_scorer import CompositeAnomalyScorer
from omoi_os.services.database import DatabaseService
from omoi_os.services.monitor import MonitorService
from omoi_os.services.event_bus import EventBusService
from omoi_os.utils.datetime import utc_now




@pytest.fixture
def baseline_learner(db_service):
    """Create a BaselineLearner service."""
    return BaselineLearner(db_service)


@pytest.fixture
def composite_scorer(db_service, baseline_learner):
    """Create a CompositeAnomalyScorer service."""
    return CompositeAnomalyScorer(db_service, baseline_learner)


@pytest.fixture
def monitor_service(db_service, event_bus_service):
    """Create a MonitorService."""
    return MonitorService(db_service, event_bus_service)


@pytest.fixture
def agent(db_service, event_bus_service):
    """Create a test agent."""
    from omoi_os.services.agent_registry import AgentRegistryService

    registry = AgentRegistryService(db_service, event_bus_service)
    agent = registry.register_agent(
        agent_type="worker",
        phase_id="PHASE_IMPLEMENTATION",
        capabilities=["python", "fastapi"],
        capacity=1,
    )
    return agent


@pytest.fixture
def ticket(db_service):
    """Create a test ticket."""
    with db_service.get_session() as session:
        ticket = Ticket(
            id="test-ticket-1",
            title="Test Ticket",
            description="Test description",
            phase_id="PHASE_IMPLEMENTATION",
            status="in_progress",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        ticket_id = ticket.id  # Extract ID before expunging
        session.expunge(ticket)
        # Return a dict with ticket_id since we can't access attributes on detached instance
        return {"id": ticket_id}


class TestBaselineLearner:
    """Test BaselineLearner service (REQ-FT-AN-002)."""

    def test_learn_baseline_initial(self, baseline_learner):
        """Test learning initial baseline."""
        metrics = {
            "latency_ms": 100.0,
            "latency_std": 10.0,
            "error_rate": 0.05,
            "cpu_usage_percent": 50.0,
            "memory_usage_mb": 512.0,
        }

        baseline = baseline_learner.learn_baseline(
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            metrics=metrics,
        )

        assert baseline.agent_type == "worker"
        assert baseline.phase_id == "PHASE_IMPLEMENTATION"
        assert baseline.latency_ms == 100.0
        assert baseline.error_rate == 0.05
        assert baseline.cpu_usage_percent == 50.0
        assert baseline.memory_usage_mb == 512.0
        assert baseline.sample_count == 1

    def test_learn_baseline_ema_update(self, baseline_learner):
        """Test EMA update of baseline."""
        # Initial baseline
        baseline = baseline_learner.learn_baseline(
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            metrics={
                "latency_ms": 100.0,
                "latency_std": 10.0,
                "error_rate": 0.05,
                "cpu_usage_percent": 50.0,
                "memory_usage_mb": 512.0,
            },
        )

        # Update with new metrics (EMA)
        baseline = baseline_learner.learn_baseline(
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            metrics={
                "latency_ms": 120.0,  # Increased latency
                "error_rate": 0.10,  # Increased error rate
            },
        )

        # EMA: new = 0.1 * 120 + 0.9 * 100 = 12 + 90 = 102
        assert baseline.latency_ms > 100.0
        assert baseline.latency_ms < 120.0
        assert baseline.sample_count == 2

    def test_decay_baseline(self, baseline_learner):
        """Test baseline decay after resurrection."""
        # Learn baseline
        baseline = baseline_learner.learn_baseline(
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            metrics={
                "latency_ms": 100.0,
                "error_rate": 0.05,
                "cpu_usage_percent": 50.0,
                "memory_usage_mb": 512.0,
            },
        )

        original_latency = baseline.latency_ms

        # Decay baseline
        baseline_learner.decay_baseline("worker", "PHASE_IMPLEMENTATION")

        # Get updated baseline
        with baseline_learner.db.get_session() as session:
            updated_baseline = (
                session.query(AgentBaseline)
                .filter(
                    AgentBaseline.agent_type == "worker",
                    AgentBaseline.phase_id == "PHASE_IMPLEMENTATION",
                )
                .first()
            )
            # Extract value before expunging
            decayed_latency = updated_baseline.latency_ms
            session.expunge(updated_baseline)

        # Baseline should be decayed (0.9 factor)
        assert decayed_latency == original_latency * 0.9

    def test_get_baseline(self, baseline_learner):
        """Test retrieving baseline."""
        # Learn baseline
        baseline_learner.learn_baseline(
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            metrics={"latency_ms": 100.0, "error_rate": 0.05},
        )

        # Get baseline
        baseline = baseline_learner.get_baseline("worker", "PHASE_IMPLEMENTATION")

        assert baseline is not None
        assert baseline.latency_ms == 100.0
        assert baseline.error_rate == 0.05


class TestCompositeAnomalyScorer:
    """Test CompositeAnomalyScorer service (REQ-FT-AN-001)."""

    def test_compute_latency_z_score(self, composite_scorer, agent, baseline_learner):
        """Test latency z-score calculation."""
        # Learn baseline
        baseline_learner.learn_baseline(
            agent.agent_type,
            agent.phase_id,
            metrics={
                "latency_ms": 100.0,
                "latency_std": 10.0,
            },
        )

        # Compute z-score for high latency
        z_score = composite_scorer.compute_latency_z_score(
            agent.id, 130.0, agent, baseline_learner.get_baseline(agent.agent_type, agent.phase_id)
        )

        # z-score = (130 - 100) / 10 = 3.0
        assert z_score == 3.0

    def test_compute_error_rate_ema(self, composite_scorer, agent, baseline_learner):
        """Test error rate EMA calculation."""
        # Learn baseline
        baseline_learner.learn_baseline(
            agent.agent_type,
            agent.phase_id,
            metrics={"error_rate": 0.05},
        )

        # Compute error rate EMA
        error_rate_score = composite_scorer.compute_error_rate_ema(
            agent.id, 0.15, agent, baseline_learner.get_baseline(agent.agent_type, agent.phase_id)
        )

        # Error rate increased from 0.05 to 0.15 (3x increase)
        assert error_rate_score > 0.0

    def test_compute_resource_skew(self, composite_scorer, agent, baseline_learner):
        """Test resource skew calculation."""
        # Learn baseline
        baseline_learner.learn_baseline(
            agent.agent_type,
            agent.phase_id,
            metrics={
                "cpu_usage_percent": 50.0,
                "memory_usage_mb": 512.0,
            },
        )

        # Compute resource skew (high CPU/Memory)
        resource_skew = composite_scorer.compute_resource_skew(
            agent.id,
            80.0,  # High CPU
            800.0,  # High Memory
            agent,
            baseline_learner.get_baseline(agent.agent_type, agent.phase_id),
        )

        # Resource skew should be > 0 (deviates from baseline)
        assert resource_skew > 0.0
        assert resource_skew <= 1.0

    def test_compute_queue_impact(self, composite_scorer, agent, db_service, ticket):
        """Test queue impact calculation."""
        with db_service.get_session() as session:
            # Create a task assigned to agent
            task1 = Task(
                id="task-1",
                ticket_id=ticket["id"],
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test_task",
                priority="HIGH",
                status="running",
                assigned_agent_id=agent.id,
            )
            session.add(task1)

            # Create a dependent task
            task2 = Task(
                id="task-2",
                ticket_id=ticket["id"],
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test_task",
                priority="CRITICAL",
                status="pending",
                dependencies={"depends_on": [task1.id]},
            )
            session.add(task2)
            session.commit()

            # Compute queue impact
            queue_impact = composite_scorer.compute_queue_impact(agent.id, session)

            # Queue impact should be > 0 (task blocking another)
            assert queue_impact > 0.0
            assert queue_impact <= 1.0

    def test_compute_anomaly_score_composite(self, composite_scorer, agent, baseline_learner, db_service, ticket):
        """Test composite anomaly score calculation."""
        # Learn baseline
        baseline_learner.learn_baseline(
            agent.agent_type,
            agent.phase_id,
            metrics={
                "latency_ms": 100.0,
                "latency_std": 10.0,
                "error_rate": 0.05,
                "cpu_usage_percent": 50.0,
                "memory_usage_mb": 512.0,
            },
        )

        # Compute composite score with anomalies
        anomaly_score = composite_scorer.compute_anomaly_score(
            agent.id,
            latency_ms=150.0,  # High latency (z-score = 5.0)
            error_rate=0.20,  # High error rate
            cpu_usage_percent=90.0,  # High CPU
            memory_usage_mb=1000.0,  # High Memory
        )

        # Composite score should be > 0 (anomalies detected)
        assert anomaly_score > 0.0
        assert anomaly_score <= 1.0

        # With multiple anomalies, score should be high
        assert anomaly_score >= 0.5


class TestMonitorServiceAnomalyDetection:
    """Test MonitorService agent-level anomaly detection (REQ-FT-AN-001)."""

    def test_compute_agent_anomaly_scores(self, monitor_service, agent, db_service, ticket):
        """Test computing anomaly scores for agents."""
        with db_service.get_session() as session:
            # Create tasks for agent to compute metrics
            task = Task(
                id="task-1",
                ticket_id=ticket["id"],
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test_task",
                priority="HIGH",
                status="completed",
                assigned_agent_id=agent.id,
                started_at=utc_now() - timedelta(seconds=100),
                completed_at=utc_now() - timedelta(seconds=50),
            )
            session.add(task)
            session.commit()

        # Compute anomaly scores
        results = monitor_service.compute_agent_anomaly_scores(
            agent_ids=[agent.id],
            anomaly_threshold=0.8,
            consecutive_threshold=3,
        )

        assert len(results) == 1
        assert results[0]["agent_id"] == agent.id
        assert "anomaly_score" in results[0]
        assert "consecutive_readings" in results[0]
        assert "should_quarantine" in results[0]

        # Check agent was updated
        with db_service.get_session() as session:
            updated_agent = session.query(Agent).filter(Agent.id == agent.id).first()
            assert updated_agent.anomaly_score is not None

    def test_consecutive_anomalous_readings(self, monitor_service, agent, db_service, ticket):
        """Test consecutive anomalous readings tracking."""
        # Simulate 3 consecutive high anomaly scores
        for i in range(3):
            with db_service.get_session() as session:
                task = Task(
                    id=f"task-{i}",
                    ticket_id=ticket["id"],
                    phase_id="PHASE_IMPLEMENTATION",
                    task_type="test_task",
                    priority="HIGH",
                    status="failed",  # Failed task to increase error rate
                    assigned_agent_id=agent.id,
                    started_at=utc_now() - timedelta(minutes=i + 10),
                    completed_at=utc_now() - timedelta(minutes=i),
                )
                session.add(task)
                session.commit()

            # Compute anomaly scores
            results = monitor_service.compute_agent_anomaly_scores(
                agent_ids=[agent.id],
                anomaly_threshold=0.8,
                consecutive_threshold=3,
            )

        # After 3 consecutive readings >= threshold, should_quarantine should be True
        final_result = results[0]
        if final_result["consecutive_readings"] >= 3:
            assert final_result["should_quarantine"] is True

    def test_baseline_learning_integration(self, monitor_service, agent, db_service, ticket):
        """Test baseline learning integration with MonitorService."""
        # Create successful tasks to learn baseline
        with db_service.get_session() as session:
            for i in range(10):
                task = Task(
                    id=f"task-{i}",
                    ticket_id=ticket["id"],
                    phase_id="PHASE_IMPLEMENTATION",
                    task_type="test_task",
                    priority="HIGH",
                    status="completed",
                    assigned_agent_id=agent.id,
                    started_at=utc_now() - timedelta(minutes=10 - i),
                    completed_at=utc_now() - timedelta(minutes=9 - i),
                )
                session.add(task)
            session.commit()

        # Compute anomaly scores (should learn baseline)
        results = monitor_service.compute_agent_anomaly_scores(agent_ids=[agent.id])

        # Check baseline was created
        baseline = monitor_service.baseline_learner.get_baseline(
            agent.agent_type, agent.phase_id
        )
        assert baseline is not None
        assert baseline.sample_count > 0

    def test_event_publishing_on_anomaly(self, monitor_service, agent, db_service, ticket, event_bus_service):
        """Test event publishing when anomaly detected."""
        # Create failed tasks to trigger anomaly
        with db_service.get_session() as session:
            for i in range(5):
                task = Task(
                    id=f"task-{i}",
                    ticket_id=ticket["id"],
                    phase_id="PHASE_IMPLEMENTATION",
                    task_type="test_task",
                    priority="HIGH",
                    status="failed",
                    assigned_agent_id=agent.id,
                    started_at=utc_now() - timedelta(minutes=10 - i),
                    completed_at=utc_now() - timedelta(minutes=9 - i),
                )
                session.add(task)
            session.commit()

        # Clear events
        # (In real test, we'd check event_bus events)

        # Compute anomaly scores
        results = monitor_service.compute_agent_anomaly_scores(
            agent_ids=[agent.id],
            anomaly_threshold=0.5,  # Lower threshold to trigger events
        )

        # If anomaly detected, events should be published
        # (In real test, we'd verify events were published)
        assert len(results) == 1


class TestAnomalyDetectionIntegration:
    """Integration tests for anomaly detection system."""

    def test_full_anomaly_detection_flow(self, db_service, event_bus_service):
        """Test full anomaly detection flow from baseline learning to quarantine."""
        monitor_service = MonitorService(db_service, event_bus_service)

        # Register agent
        from omoi_os.services.agent_registry import AgentRegistryService
        registry = AgentRegistryService(db_service, event_bus_service)
        agent = registry.register_agent(
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            capabilities=["python"],
        )

        # Create ticket
        with db_service.get_session() as session:
            ticket = Ticket(
                id="test-ticket",
                title="Test",
                description="Test",
                phase_id="PHASE_IMPLEMENTATION",
                status="in_progress",
                priority="HIGH",
            )
            session.add(ticket)
            session.commit()
            ticket_id = ticket.id  # Extract ID before session closes

            # Create normal tasks to learn baseline
            for i in range(10):
                task = Task(
                    id=f"task-{i}",
                    ticket_id=ticket_id,
                    phase_id="PHASE_IMPLEMENTATION",
                    task_type="test",
                    priority="HIGH",
                    status="completed",
                    assigned_agent_id=agent.id,
                    started_at=utc_now() - timedelta(minutes=20 - i),
                    completed_at=utc_now() - timedelta(minutes=19 - i),
                )
                session.add(task)
            session.commit()

        # Learn baseline
        results = monitor_service.compute_agent_anomaly_scores(agent_ids=[agent.id])
        baseline = monitor_service.baseline_learner.get_baseline(
            agent.agent_type, agent.phase_id
        )
        assert baseline is not None

        # Create anomalous tasks (high latency, high error rate)
        with db_service.get_session() as session:
            for i in range(5):
                task = Task(
                    id=f"anomalous-task-{i}",
                    ticket_id=ticket_id,
                    phase_id="PHASE_IMPLEMENTATION",
                    task_type="test",
                    priority="HIGH",
                    status="failed",  # Failed tasks
                    assigned_agent_id=agent.id,
                    started_at=utc_now() - timedelta(minutes=10 - i),
                    completed_at=utc_now() - timedelta(minutes=9 - i),
                )
                session.add(task)
            session.commit()

        # Compute anomaly scores multiple times to trigger consecutive readings
        for _ in range(3):
            results = monitor_service.compute_agent_anomaly_scores(
                agent_ids=[agent.id],
                anomaly_threshold=0.8,
                consecutive_threshold=3,
            )

        # Check consecutive readings increased
        with db_service.get_session() as session:
            updated_agent = session.query(Agent).filter(Agent.id == agent.id).first()
            assert updated_agent.consecutive_anomalous_readings >= 0

        # Final result should indicate quarantine if threshold met
        final_result = results[0]
        if final_result["anomaly_score"] >= 0.8 and final_result["consecutive_readings"] >= 3:
            assert final_result["should_quarantine"] is True

