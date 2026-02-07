"""Tests for enhanced heartbeat protocol (REQ-ALM-002, REQ-FT-HB-001 to REQ-FT-HB-004)."""

import pytest
from datetime import timedelta
from unittest.mock import Mock, patch

from omoi_os.models.agent import Agent
from omoi_os.models.heartbeat_message import HeartbeatAck, HeartbeatMessage
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.heartbeat_protocol import HeartbeatProtocolService
from omoi_os.utils.datetime import utc_now


def mock_db_session():
    """Create a properly mocked database session with context manager."""
    mock_session = Mock()
    mock_context_manager = Mock()
    mock_context_manager.__enter__ = Mock(return_value=mock_session)
    mock_context_manager.__exit__ = Mock(return_value=None)
    return mock_session, mock_context_manager


@pytest.fixture
def event_bus_service():
    """Create a mock event bus service."""
    return Mock(spec=EventBusService)


@pytest.fixture
def heartbeat_protocol_service(
    db_service: DatabaseService, event_bus_service: EventBusService
):
    """Create heartbeat protocol service."""
    return HeartbeatProtocolService(db=db_service, event_bus=event_bus_service)


@pytest.fixture
def sample_agent(db_service: DatabaseService):
    """Create a sample agent for testing."""
    from uuid import uuid4
    from omoi_os.models.agent_status import AgentStatus

    agent_id = f"test-agent-{uuid4().hex[:8]}"
    with db_service.get_session() as session:
        agent = Agent(
            id=agent_id,
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            status=AgentStatus.IDLE.value,  # Use uppercase IDLE
            capabilities=["bash"],
            sequence_number=0,
            last_expected_sequence=0,
            consecutive_missed_heartbeats=0,
            created_at=utc_now(),
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
        session.expunge(agent)
        return agent


@pytest.fixture
def running_agent(db_service: DatabaseService):
    """Create a running agent for testing."""
    from uuid import uuid4
    from omoi_os.models.agent_status import AgentStatus

    agent_id = f"running-agent-{uuid4().hex[:8]}"
    with db_service.get_session() as session:
        agent = Agent(
            id=agent_id,
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            status=AgentStatus.RUNNING.value,  # Use uppercase RUNNING
            capabilities=["bash"],
            sequence_number=5,
            last_expected_sequence=6,
            consecutive_missed_heartbeats=0,
            created_at=utc_now(),
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
        session.expunge(agent)
        return agent


class TestHeartbeatProtocolService:
    """Test cases for HeartbeatProtocolService."""

    def test_receive_heartbeat_success(self, heartbeat_protocol_service, sample_agent):
        """Test successful heartbeat reception with valid checksum."""
        # Create heartbeat message with consistent timestamp
        timestamp = utc_now()
        payload = {
            "agent_id": sample_agent.id,
            "timestamp": timestamp.isoformat(),
            "sequence_number": 1,
            "status": "idle",
            "current_task_id": None,
            "health_metrics": {"cpu_usage_percent": 45.2, "memory_usage_mb": 384},
        }
        checksum = heartbeat_protocol_service._calculate_checksum(payload)

        message = HeartbeatMessage(
            agent_id=sample_agent.id,
            timestamp=timestamp,
            sequence_number=1,
            status="idle",
            current_task_id=None,
            health_metrics={"cpu_usage_percent": 45.2, "memory_usage_mb": 384},
            checksum=checksum,
        )

        # Receive heartbeat
        ack = heartbeat_protocol_service.receive_heartbeat(message)

        assert ack.received is True
        assert ack.sequence_number == 1
        assert ack.agent_id == sample_agent.id

        # Verify agent was updated
        with heartbeat_protocol_service.db.get_session() as session:
            agent = session.get(Agent, sample_agent.id)
            assert agent.sequence_number == 1
            assert agent.last_expected_sequence == 2
            assert agent.consecutive_missed_heartbeats == 0
            assert agent.last_heartbeat is not None

    def test_receive_heartbeat_invalid_checksum(
        self, heartbeat_protocol_service, sample_agent
    ):
        """Test heartbeat rejection with invalid checksum."""
        message = HeartbeatMessage(
            agent_id=sample_agent.id,
            timestamp=utc_now(),
            sequence_number=1,
            status="idle",
            current_task_id=None,
            health_metrics={},
            checksum="invalid_checksum",
        )

        ack = heartbeat_protocol_service.receive_heartbeat(message)

        assert ack.received is False
        assert "Checksum validation failed" in ack.message

    def test_receive_heartbeat_agent_not_found(self, heartbeat_protocol_service):
        """Test heartbeat rejection when agent not found."""
        timestamp = utc_now()
        payload = {
            "agent_id": "non-existent-agent",
            "timestamp": timestamp.isoformat(),
            "sequence_number": 1,
            "status": "idle",
            "current_task_id": None,
            "health_metrics": {},
        }
        checksum = heartbeat_protocol_service._calculate_checksum(payload)

        message = HeartbeatMessage(
            agent_id="non-existent-agent",
            timestamp=timestamp,
            sequence_number=1,
            status="idle",
            current_task_id=None,
            health_metrics={},
            checksum=checksum,
        )

        ack = heartbeat_protocol_service.receive_heartbeat(message)

        assert ack.received is False
        assert "Agent not found" in ack.message

    def test_receive_heartbeat_sequence_gap_detection(
        self, heartbeat_protocol_service, running_agent
    ):
        """Test sequence gap detection (REQ-FT-HB-003)."""
        # Agent has sequence_number=5, last_expected_sequence=6
        # Send heartbeat with sequence_number=8 (gaps at 6 and 7)
        timestamp = utc_now()
        payload = {
            "agent_id": running_agent.id,
            "timestamp": timestamp.isoformat(),
            "sequence_number": 8,
            "status": "running",
            "current_task_id": None,
            "health_metrics": {},
        }
        checksum = heartbeat_protocol_service._calculate_checksum(payload)

        message = HeartbeatMessage(
            agent_id=running_agent.id,
            timestamp=timestamp,
            sequence_number=8,
            status="running",
            current_task_id=None,
            health_metrics={},
            checksum=checksum,
        )

        ack = heartbeat_protocol_service.receive_heartbeat(message)

        assert ack.received is True
        assert ack.message is not None
        assert "Sequence gaps" in ack.message

    def test_get_ttl_threshold_idle(self, heartbeat_protocol_service):
        """Test TTL threshold for IDLE agents (30s per REQ-FT-HB-002)."""
        threshold = heartbeat_protocol_service._get_ttl_threshold("idle", "worker")
        assert threshold == 30

    def test_get_ttl_threshold_running(self, heartbeat_protocol_service):
        """Test TTL threshold for RUNNING agents (15s per REQ-FT-HB-002)."""
        threshold = heartbeat_protocol_service._get_ttl_threshold("running", "worker")
        assert threshold == 15

    def test_get_ttl_threshold_monitor(self, heartbeat_protocol_service):
        """Test TTL threshold for MONITOR agents (15s per REQ-FT-HB-002)."""
        # Monitor agents use running threshold regardless of status
        threshold = heartbeat_protocol_service._get_ttl_threshold("running", "monitor")
        assert threshold == 15

    def test_check_missed_heartbeats_none(
        self, heartbeat_protocol_service, sample_agent
    ):
        """Test checking missed heartbeats when none are missed."""
        # Update agent with recent heartbeat
        with heartbeat_protocol_service.db.get_session() as session:
            agent = session.get(Agent, sample_agent.id)
            agent.last_heartbeat = utc_now()
            session.commit()

        missed = heartbeat_protocol_service.check_missed_heartbeats()

        # Filter to only our test agent (shared database may have other agents)
        test_agent_missed = [m for m in missed if m[0]["id"] == sample_agent.id]
        assert len(test_agent_missed) == 0

    def test_check_missed_heartbeats_one_missed(
        self, heartbeat_protocol_service, sample_agent, event_bus_service
    ):
        """Test escalation ladder: 1 missed → warn (REQ-FT-AR-001)."""
        from omoi_os.models.agent_status import AgentStatus

        # Update agent with old heartbeat (beyond TTL threshold)
        with heartbeat_protocol_service.db.get_session() as session:
            agent = session.get(Agent, sample_agent.id)
            agent.last_heartbeat = utc_now() - timedelta(seconds=35)  # Beyond 30s TTL
            agent.status = AgentStatus.IDLE.value
            session.commit()
            # Expunge so we can use agent outside session
            session.expunge(agent)

        missed = heartbeat_protocol_service.check_missed_heartbeats()

        # Filter to only our test agent (shared database may have other agents)
        test_agent_missed = [m for m in missed if m[0]["id"] == sample_agent.id]
        assert len(test_agent_missed) == 1
        agent_data, missed_count = test_agent_missed[0]
        assert agent_data["id"] == sample_agent.id
        assert missed_count == 1

        # Verify event was published for our test agent
        assert event_bus_service.publish.called
        # Find the call for our specific agent (entity_id is the agent ID)
        heartbeat_missed_calls = [
            call[0][0]
            for call in event_bus_service.publish.call_args_list
            if call[0][0].event_type == "HEARTBEAT_MISSED"
            and call[0][0].entity_id == sample_agent.id
        ]
        assert len(heartbeat_missed_calls) >= 1
        call_args = heartbeat_missed_calls[0]
        assert call_args.payload["missed_count"] == 1
        assert call_args.payload["escalation_level"] == "warn"

    def test_check_missed_heartbeats_two_missed_degraded(
        self, heartbeat_protocol_service, sample_agent, event_bus_service
    ):
        """Test escalation ladder: 2 missed → DEGRADED (REQ-FT-AR-001)."""
        from omoi_os.models.agent_status import AgentStatus

        # Set agent to 1 missed heartbeat, then check again
        with heartbeat_protocol_service.db.get_session() as session:
            agent = session.get(Agent, sample_agent.id)
            agent.consecutive_missed_heartbeats = 1
            agent.last_heartbeat = utc_now() - timedelta(seconds=35)
            agent.status = AgentStatus.IDLE.value
            session.commit()

        missed = heartbeat_protocol_service.check_missed_heartbeats()

        # Filter to only our test agent (shared database may have other agents)
        test_agent_missed = [m for m in missed if m[0]["id"] == sample_agent.id]
        assert len(test_agent_missed) == 1
        agent_data, missed_count = test_agent_missed[0]
        assert agent_data["id"] == sample_agent.id
        assert missed_count == 2

        # Verify agent status changed to DEGRADED
        with heartbeat_protocol_service.db.get_session() as session:
            agent = session.get(Agent, sample_agent.id)
            assert agent.status == AgentStatus.DEGRADED.value  # Uppercase DEGRADED
            assert agent.health_status == "degraded"

        # Verify events were published for our test agent
        assert event_bus_service.publish.call_count >= 2
        # Check for AGENT_STATUS_CHANGED event for our specific agent
        status_changed_calls = [
            call[0][0]
            for call in event_bus_service.publish.call_args_list
            if call[0][0].event_type == "AGENT_STATUS_CHANGED"
            and call[0][0].entity_id == sample_agent.id
        ]
        assert len(status_changed_calls) > 0
        assert (
            status_changed_calls[0].payload["new_status"] == AgentStatus.DEGRADED.value
        )

    def test_check_missed_heartbeats_three_missed_unresponsive(
        self, heartbeat_protocol_service, sample_agent, event_bus_service
    ):
        """Test escalation ladder: 3 missed → FAILED (REQ-FT-AR-001)."""
        from omoi_os.models.agent_status import AgentStatus

        # Set agent to 2 missed heartbeats, then check again
        with heartbeat_protocol_service.db.get_session() as session:
            agent = session.get(Agent, sample_agent.id)
            agent.consecutive_missed_heartbeats = 2
            agent.last_heartbeat = utc_now() - timedelta(seconds=35)
            agent.status = AgentStatus.DEGRADED.value
            session.commit()

        missed = heartbeat_protocol_service.check_missed_heartbeats()

        # Filter to only our test agent (shared database may have other agents)
        test_agent_missed = [m for m in missed if m[0]["id"] == sample_agent.id]
        assert len(test_agent_missed) == 1
        agent_data, missed_count = test_agent_missed[0]
        assert agent_data["id"] == sample_agent.id
        assert missed_count == 3

        # Verify agent status changed to FAILED (status) with health_status="unresponsive"
        with heartbeat_protocol_service.db.get_session() as session:
            agent = session.get(Agent, sample_agent.id)
            assert agent.status == AgentStatus.FAILED.value  # Status is FAILED
            assert (
                agent.health_status == "unresponsive"
            )  # health_status is unresponsive

        # Verify restart protocol event was published for our test agent
        # Event uses entity_id, not agent_id in payload
        restart_calls = [
            call[0][0]
            for call in event_bus_service.publish.call_args_list
            if call[0][0].event_type == "HEARTBEAT_MISSED"
            and call[0][0].payload.get("escalation_level") == "unresponsive"
            and call[0][0].entity_id == sample_agent.id
        ]
        assert len(restart_calls) > 0
        assert restart_calls[0].payload["action"] == "Initiate restart protocol"

    def test_check_agent_health_with_ttl_idle(
        self, heartbeat_protocol_service, sample_agent
    ):
        """Test health check with state-based TTL for IDLE agent."""
        from omoi_os.models.agent_status import AgentStatus

        # Update agent with recent heartbeat
        with heartbeat_protocol_service.db.get_session() as session:
            agent = session.get(Agent, sample_agent.id)
            agent.last_heartbeat = utc_now() - timedelta(seconds=20)  # Within 30s TTL
            agent.status = AgentStatus.IDLE.value
            session.commit()

        health = heartbeat_protocol_service.check_agent_health_with_ttl(sample_agent.id)

        assert health["healthy"] is True
        assert health["ttl_threshold"] == 30
        assert health["time_since_last_heartbeat"] < 30

    def test_check_agent_health_with_ttl_running(
        self, heartbeat_protocol_service, running_agent
    ):
        """Test health check with state-based TTL for RUNNING agent."""
        from omoi_os.models.agent_status import AgentStatus

        # Update agent with recent heartbeat
        with heartbeat_protocol_service.db.get_session() as session:
            agent = session.get(Agent, running_agent.id)
            agent.last_heartbeat = utc_now() - timedelta(seconds=10)  # Within 15s TTL
            agent.status = AgentStatus.RUNNING.value
            session.commit()

        health = heartbeat_protocol_service.check_agent_health_with_ttl(
            running_agent.id
        )

        assert health["healthy"] is True
        assert health["ttl_threshold"] == 15
        assert health["time_since_last_heartbeat"] < 15

    def test_check_agent_health_with_ttl_stale_running(
        self, heartbeat_protocol_service, running_agent
    ):
        """Test health check detects stale RUNNING agent beyond TTL."""
        from omoi_os.models.agent_status import AgentStatus

        # Update agent with old heartbeat (beyond 15s TTL)
        with heartbeat_protocol_service.db.get_session() as session:
            agent = session.get(Agent, running_agent.id)
            agent.last_heartbeat = utc_now() - timedelta(seconds=20)  # Beyond 15s TTL
            agent.status = AgentStatus.RUNNING.value
            session.commit()

        health = heartbeat_protocol_service.check_agent_health_with_ttl(
            running_agent.id
        )

        assert health["healthy"] is False
        assert health["ttl_threshold"] == 15
        assert health["time_since_last_heartbeat"] > 15

    def test_checksum_calculation(self, heartbeat_protocol_service):
        """Test checksum calculation and validation."""
        payload1 = {
            "agent_id": "test-agent",
            "timestamp": "2025-01-27T12:00:00Z",
            "sequence_number": 1,
            "status": "idle",
            "current_task_id": None,
            "health_metrics": {},
        }

        payload2 = {
            "agent_id": "test-agent",
            "timestamp": "2025-01-27T12:00:00Z",
            "sequence_number": 2,  # Different sequence number
            "status": "idle",
            "current_task_id": None,
            "health_metrics": {},
        }

        checksum1 = heartbeat_protocol_service._calculate_checksum(payload1)
        checksum2 = heartbeat_protocol_service._calculate_checksum(payload2)

        assert (
            checksum1 != checksum2
        )  # Different payloads should have different checksums
        assert len(checksum1) == 64  # SHA256 hex string length
        assert len(checksum2) == 64

    def test_validate_checksum_valid(self, heartbeat_protocol_service):
        """Test checksum validation with valid checksum."""
        from datetime import datetime, timezone

        # Use a fixed timestamp for consistent checksum
        fixed_timestamp = datetime(2025, 1, 27, 12, 0, 0, tzinfo=timezone.utc)
        payload = {
            "agent_id": "test-agent",
            "timestamp": fixed_timestamp.isoformat(),
            "sequence_number": 1,
            "status": "idle",
            "current_task_id": None,
            "health_metrics": {},
        }
        checksum = heartbeat_protocol_service._calculate_checksum(payload)

        message = HeartbeatMessage(
            agent_id="test-agent",
            timestamp=fixed_timestamp,
            sequence_number=1,
            status="idle",
            current_task_id=None,
            health_metrics={},
            checksum=checksum,
        )

        assert heartbeat_protocol_service._validate_checksum(message) is True

    def test_validate_checksum_invalid(self, heartbeat_protocol_service):
        """Test checksum validation with invalid checksum."""
        message = HeartbeatMessage(
            agent_id="test-agent",
            timestamp=utc_now(),
            sequence_number=1,
            status="idle",
            current_task_id=None,
            health_metrics={},
            checksum="invalid_checksum",
        )

        assert heartbeat_protocol_service._validate_checksum(message) is False

    def test_receive_heartbeat_resets_missed_count(
        self, heartbeat_protocol_service, sample_agent
    ):
        """Test that receiving heartbeat resets consecutive_missed_heartbeats."""
        # Set agent to have missed heartbeats
        with heartbeat_protocol_service.db.get_session() as session:
            agent = session.get(Agent, sample_agent.id)
            agent.consecutive_missed_heartbeats = 2
            session.commit()

        # Send heartbeat with consistent timestamp
        timestamp = utc_now()
        payload = {
            "agent_id": sample_agent.id,
            "timestamp": timestamp.isoformat(),
            "sequence_number": 1,
            "status": "idle",
            "current_task_id": None,
            "health_metrics": {},
        }
        checksum = heartbeat_protocol_service._calculate_checksum(payload)

        message = HeartbeatMessage(
            agent_id=sample_agent.id,
            timestamp=timestamp,
            sequence_number=1,
            status="idle",
            current_task_id=None,
            health_metrics={},
            checksum=checksum,
        )

        heartbeat_protocol_service.receive_heartbeat(message)

        # Verify missed count was reset
        with heartbeat_protocol_service.db.get_session() as session:
            agent = session.get(Agent, sample_agent.id)
            assert agent.consecutive_missed_heartbeats == 0


class TestRestartOrchestrator:
    """Test cases for RestartOrchestrator."""

    @pytest.fixture
    def restart_orchestrator(self, db_service, event_bus_service):
        """Create restart orchestrator with dependencies."""
        from omoi_os.services.agent_registry import AgentRegistryService
        from omoi_os.services.task_queue import TaskQueueService
        from omoi_os.services.restart_orchestrator import RestartOrchestrator

        registry = AgentRegistryService(db_service, event_bus_service)
        queue = TaskQueueService(db_service)

        return RestartOrchestrator(
            db=db_service,
            agent_registry=registry,
            task_queue=queue,
            event_bus=event_bus_service,
        )

    def test_initiate_restart_success(
        self, restart_orchestrator, sample_agent, event_bus_service
    ):
        """Test successful restart initiation (REQ-FT-AR-002)."""
        from omoi_os.models.guardian_action import AuthorityLevel

        result = restart_orchestrator.initiate_restart(
            agent_id=sample_agent.id,
            reason="missed_heartbeats",
            authority=AuthorityLevel.MONITOR,
        )

        assert result is not None
        assert result["agent_id"] == sample_agent.id
        assert result["reason"] == "missed_heartbeats"
        assert "replacement_agent_id" in result
        assert "reassigned_tasks" in result

        # Verify AGENT_RESTARTED event was published
        assert event_bus_service.publish.called
        restart_calls = [
            call[0][0]
            for call in event_bus_service.publish.call_args_list
            if call[0][0].event_type == "AGENT_RESTARTED"
        ]
        assert len(restart_calls) > 0
        assert restart_calls[0].entity_id == sample_agent.id

    def test_initiate_restart_insufficient_authority(
        self, restart_orchestrator, sample_agent
    ):
        """Test restart fails with insufficient authority."""
        from omoi_os.models.guardian_action import AuthorityLevel

        with pytest.raises(PermissionError):
            restart_orchestrator.initiate_restart(
                agent_id=sample_agent.id,
                reason="test",
                authority=AuthorityLevel.WORKER,  # Insufficient authority
            )


class TestEnhancedHeartbeatManager:
    """Test cases for enhanced HeartbeatManager."""

    @patch("time.sleep")
    def test_heartbeat_manager_adaptive_interval_idle(self, mock_sleep):
        """Test adaptive interval for IDLE agents (30s per REQ-FT-HB-002)."""
        from omoi_os.worker import HeartbeatManager

        mock_protocol_service = Mock()
        mock_protocol_service._calculate_checksum.return_value = "test_checksum"
        mock_protocol_service.receive_heartbeat.return_value = HeartbeatAck(
            agent_id="test-agent",
            sequence_number=1,
            received=True,
        )

        manager = HeartbeatManager(
            agent_id="test-agent",
            heartbeat_protocol_service=mock_protocol_service,
            get_agent_status=lambda: "idle",
        )

        interval = manager._get_interval()
        assert interval == 30

    @patch("time.sleep")
    def test_heartbeat_manager_adaptive_interval_running(self, mock_sleep):
        """Test adaptive interval for RUNNING agents (15s per REQ-FT-HB-002)."""
        from omoi_os.worker import HeartbeatManager

        mock_protocol_service = Mock()
        mock_protocol_service._calculate_checksum.return_value = "test_checksum"
        mock_protocol_service.receive_heartbeat.return_value = HeartbeatAck(
            agent_id="test-agent",
            sequence_number=1,
            received=True,
        )

        manager = HeartbeatManager(
            agent_id="test-agent",
            heartbeat_protocol_service=mock_protocol_service,
            get_agent_status=lambda: "running",
        )

        interval = manager._get_interval()
        assert interval == 15

    def test_heartbeat_manager_sequence_number_increment(self):
        """Test sequence number increments on each heartbeat."""
        from omoi_os.worker import HeartbeatManager

        mock_protocol_service = Mock()
        mock_protocol_service._calculate_checksum.return_value = "test_checksum"

        manager = HeartbeatManager(
            agent_id="test-agent",
            heartbeat_protocol_service=mock_protocol_service,
            get_agent_status=lambda: "idle",
        )

        assert manager._sequence_number == 0

        # Create first heartbeat
        message1 = manager._create_heartbeat_message()
        assert message1.sequence_number == 1
        assert manager._sequence_number == 1

        # Create second heartbeat
        message2 = manager._create_heartbeat_message()
        assert message2.sequence_number == 2
        assert manager._sequence_number == 2

    def test_heartbeat_manager_health_metrics_collection(self):
        """Test health metrics are collected and included in heartbeat."""
        from omoi_os.worker import HeartbeatManager

        mock_protocol_service = Mock()
        mock_protocol_service._calculate_checksum.return_value = "test_checksum"

        def collect_metrics():
            return {
                "cpu_usage_percent": 45.2,
                "memory_usage_mb": 384,
                "active_connections": 3,
            }

        manager = HeartbeatManager(
            agent_id="test-agent",
            heartbeat_protocol_service=mock_protocol_service,
            get_agent_status=lambda: "idle",
            collect_health_metrics=collect_metrics,
        )

        message = manager._create_heartbeat_message()

        assert message.health_metrics["cpu_usage_percent"] == 45.2
        assert message.health_metrics["memory_usage_mb"] == 384
        assert message.health_metrics["active_connections"] == 3

    @patch("time.sleep")
    def test_heartbeat_manager_loop_with_acknowledgment(self, mock_sleep):
        """Test heartbeat loop processes acknowledgment correctly."""
        from omoi_os.worker import HeartbeatManager

        mock_protocol_service = Mock()
        mock_protocol_service._calculate_checksum.return_value = "test_checksum"
        mock_protocol_service.receive_heartbeat.return_value = HeartbeatAck(
            agent_id="test-agent",
            sequence_number=1,
            received=True,
            message="Sequence gaps detected: [6, 7]",
        )

        manager = HeartbeatManager(
            agent_id="test-agent",
            heartbeat_protocol_service=mock_protocol_service,
            get_agent_status=lambda: "idle",
        )

        manager._running = True
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                manager._running = False
            return None

        mock_sleep.side_effect = side_effect

        manager._heartbeat_loop()

        assert mock_protocol_service.receive_heartbeat.call_count == 2
        assert mock_sleep.call_count == 2
        # Verify sleep was called with 30s interval for IDLE
        assert mock_sleep.call_args_list[0][0][0] == 30

    @patch("time.sleep")
    def test_heartbeat_manager_loop_no_acknowledgment(self, mock_sleep):
        """Test heartbeat loop handles missing acknowledgment."""
        from omoi_os.worker import HeartbeatManager

        mock_protocol_service = Mock()
        mock_protocol_service._calculate_checksum.return_value = "test_checksum"
        mock_protocol_service.receive_heartbeat.return_value = HeartbeatAck(
            agent_id="test-agent",
            sequence_number=1,
            received=False,
            message="Agent not found",
        )

        manager = HeartbeatManager(
            agent_id="test-agent",
            heartbeat_protocol_service=mock_protocol_service,
            get_agent_status=lambda: "idle",
        )

        manager._running = True

        def side_effect(*args, **kwargs):
            manager._running = False
            return None

        mock_sleep.side_effect = side_effect

        manager._heartbeat_loop()

        assert mock_protocol_service.receive_heartbeat.call_count == 1
