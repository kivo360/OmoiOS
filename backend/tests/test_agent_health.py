"""Simplified tests for Agent Health Service functionality."""

from datetime import timedelta
from unittest.mock import Mock, patch

from omoi_os.models.agent import Agent
from omoi_os.services.agent_health import AgentHealthService
from omoi_os.services.database import DatabaseService
from omoi_os.worker import HeartbeatManager
from omoi_os.utils.datetime import utc_now


def mock_db_session():
    """Create a properly mocked database session with context manager."""
    mock_session = Mock()
    mock_context_manager = Mock()
    mock_context_manager.__enter__ = Mock(return_value=mock_session)
    mock_context_manager.__exit__ = Mock(return_value=None)
    return mock_session, mock_context_manager


class TestAgentHealthService:
    """Test cases for AgentHealthService."""

    def test_emit_heartbeat_success(self):
        """Test successful heartbeat emission."""
        mock_db = Mock(spec=DatabaseService)
        mock_session, mock_context = mock_db_session()
        mock_db.get_session.return_value = mock_context

        health_service = AgentHealthService(mock_db)

        sample_agent = Agent(
            id="test-agent-123",
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            status="idle",
            capabilities=["bash"],
            last_heartbeat=None,
            created_at=utc_now(),
        )

        mock_session.query.return_value.filter.return_value.first.return_value = (
            sample_agent
        )

        result = health_service.emit_heartbeat("test-agent-123")

        assert result is True
        assert sample_agent.last_heartbeat is not None
        assert sample_agent.health_status == "healthy"
        mock_session.commit.assert_called_once()

    def test_emit_heartbeat_agent_not_found(self):
        """Test heartbeat emission when agent not found."""
        mock_db = Mock(spec=DatabaseService)
        mock_session, mock_context = mock_db_session()
        mock_db.get_session.return_value = mock_context

        health_service = AgentHealthService(mock_db)

        mock_session.query.return_value.filter.return_value.first.return_value = None

        result = health_service.emit_heartbeat("non-existent-agent")

        assert result is False
        mock_session.commit.assert_not_called()

    def test_check_agent_health_healthy(self):
        """Test checking health of a healthy agent."""
        mock_db = Mock(spec=DatabaseService)
        mock_session, mock_context = mock_db_session()
        mock_db.get_session.return_value = mock_context

        health_service = AgentHealthService(mock_db)

        healthy_agent = Agent(
            id="test-agent-123",
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            status="idle",
            capabilities=["bash"],
            last_heartbeat=utc_now() - timedelta(seconds=30),
            created_at=utc_now(),
        )

        mock_session.query.return_value.filter.return_value.first.return_value = (
            healthy_agent
        )

        result = health_service.check_agent_health("test-agent-123", timeout_seconds=90)

        assert result["agent_id"] == "test-agent-123"
        assert result["healthy"] is True
        assert result["status"] == "idle"
        assert result["agent_type"] == "worker"
        assert result["phase_id"] == "PHASE_IMPLEMENTATION"
        assert result["health_status"] == "healthy"

    def test_check_agent_health_stale(self):
        """Test checking health of a stale agent."""
        mock_db = Mock(spec=DatabaseService)
        mock_session, mock_context = mock_db_session()
        mock_db.get_session.return_value = mock_context

        health_service = AgentHealthService(mock_db)

        stale_agent = Agent(
            id="test-agent-123",
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            status="idle",
            capabilities=["bash"],
            last_heartbeat=utc_now() - timedelta(minutes=5),
            created_at=utc_now(),
        )

        mock_session.query.return_value.filter.return_value.first.return_value = (
            stale_agent
        )

        result = health_service.check_agent_health("test-agent-123", timeout_seconds=90)

        assert result["agent_id"] == "test-agent-123"
        assert result["healthy"] is False
        assert result["time_since_last_heartbeat"] > 90
        assert stale_agent.status == "stale"
        assert stale_agent.health_status == "stale"
        assert result["health_status"] == "stale"
        mock_session.commit.assert_called_once()

    def test_get_agent_statistics(self):
        """Test getting agent statistics."""
        mock_db = Mock(spec=DatabaseService)
        mock_session, mock_context = mock_db_session()
        mock_db.get_session.return_value = mock_context

        health_service = AgentHealthService(mock_db)

        now = utc_now()
        agents = [
            Agent(
                id="worker-1",
                agent_type="worker",
                phase_id="PHASE_1",
                status="idle",
                capabilities=[],
                last_heartbeat=now - timedelta(seconds=30),
                created_at=now,
                health_status="healthy",
            ),
            Agent(
                id="worker-2",
                agent_type="worker",
                phase_id="PHASE_1",
                status="running",
                capabilities=[],
                last_heartbeat=now - timedelta(minutes=2),
                created_at=now,
                health_status="stale",
            ),
        ]

        mock_session.query.return_value.all.return_value = agents

        result = health_service.get_agent_statistics()

        assert result["total_agents"] == 2
        assert result["by_status"]["idle"] == 1
        assert result["by_status"]["running"] == 1
        assert result["by_type"]["worker"] == 2
        assert result["by_phase"]["PHASE_1"] == 2
        assert result["health_summary"]["healthy"] == 1
        assert result["health_summary"]["unhealthy"] == 1

    def test_detect_stale_agents(self):
        """Test detection of stale agents."""
        mock_db = Mock(spec=DatabaseService)
        mock_session, mock_context = mock_db_session()
        mock_db.get_session.return_value = mock_context

        health_service = AgentHealthService(mock_db)

        stale_agent = Agent(
            id="stale-agent",
            agent_type="worker",
            status="idle",
            capabilities=[],
            last_heartbeat=utc_now() - timedelta(minutes=5),
            created_at=utc_now(),
        )

        mock_session.query.return_value.filter.return_value.all.return_value = [
            stale_agent
        ]

        result = health_service.detect_stale_agents(timeout_seconds=90)

        assert len(result) == 1
        assert stale_agent.status == "stale"
        assert stale_agent.health_status == "stale"
        mock_session.commit.assert_called_once()

    def test_cleanup_stale_agents(self):
        """Test cleanup of stale agents."""
        mock_db = Mock(spec=DatabaseService)
        mock_session, mock_context = mock_db_session()
        mock_db.get_session.return_value = mock_context

        health_service = AgentHealthService(mock_db)

        stale_agent = Agent(
            id="stale-agent",
            agent_type="worker",
            status="stale",
            capabilities=[],
            last_heartbeat=utc_now() - timedelta(minutes=5),
            created_at=utc_now(),
        )

        mock_session.query.return_value.filter.return_value.all.return_value = [
            stale_agent
        ]

        result = health_service.cleanup_stale_agents(
            timeout_seconds=90, mark_as="timeout"
        )

        assert result == 1
        assert stale_agent.status == "timeout"
        assert stale_agent.health_status == "timeout"
        mock_session.commit.assert_called_once()

    def test_get_all_agents_health(self):
        """Test getting health status for all agents."""
        mock_db = Mock(spec=DatabaseService)
        mock_session, mock_context = mock_db_session()
        mock_db.get_session.return_value = mock_context

        health_service = AgentHealthService(mock_db)

        healthy_agent = Agent(
            id="healthy-agent",
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            status="idle",
            capabilities=["bash"],
            last_heartbeat=utc_now() - timedelta(seconds=30),
            created_at=utc_now(),
        )

        stale_agent = Agent(
            id="stale-agent",
            agent_type="monitor",
            phase_id=None,
            status="idle",
            capabilities=["monitoring"],
            last_heartbeat=utc_now() - timedelta(minutes=5),
            created_at=utc_now(),
        )

        mock_session.query.return_value.all.return_value = [healthy_agent, stale_agent]

        result = health_service.get_all_agents_health(timeout_seconds=90)

        assert len(result) == 2

        healthy_result = next(r for r in result if r["agent_id"] == "healthy-agent")
        assert healthy_result["healthy"] is True
        assert healthy_result["status"] == "idle"
        assert healthy_result["health_status"] == "healthy"

        stale_result = next(r for r in result if r["agent_id"] == "stale-agent")
        assert stale_result["healthy"] is False
        assert stale_result["status"] == "stale"
        assert stale_result["health_status"] == "stale"

        mock_session.commit.assert_called_once()


class TestHeartbeatManager:
    """Test cases for HeartbeatManager."""

    def test_heartbeat_manager_initialization(self):
        """Test HeartbeatManager initialization."""
        mock_health_service = Mock(spec=AgentHealthService)
        heartbeat_manager = HeartbeatManager(
            "test-agent-123", mock_health_service, interval_seconds=1
        )

        assert heartbeat_manager.agent_id == "test-agent-123"
        assert heartbeat_manager.health_service == mock_health_service
        assert heartbeat_manager.interval_seconds == 1
        assert heartbeat_manager._running is False
        assert heartbeat_manager._thread is None

    @patch("threading.Thread")
    def test_start_heartbeat_manager(self, mock_thread):
        """Test starting the heartbeat manager."""
        mock_health_service = Mock(spec=AgentHealthService)
        heartbeat_manager = HeartbeatManager(
            "test-agent-123", mock_health_service, interval_seconds=1
        )

        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        heartbeat_manager.start()

        assert heartbeat_manager._running is True
        mock_thread.assert_called_once_with(
            target=heartbeat_manager._heartbeat_loop, daemon=True
        )
        mock_thread_instance.start.assert_called_once()

    def test_stop_heartbeat_manager(self):
        """Test stopping the heartbeat manager."""
        mock_health_service = Mock(spec=AgentHealthService)
        heartbeat_manager = HeartbeatManager(
            "test-agent-123", mock_health_service, interval_seconds=1
        )

        heartbeat_manager._running = True
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        heartbeat_manager._thread = mock_thread

        heartbeat_manager.stop()

        assert heartbeat_manager._running is False
        mock_thread.join.assert_called_once_with(timeout=6)  # interval_seconds + 5

    @patch("time.sleep")
    def test_heartbeat_loop_success(self, mock_sleep):
        """Test successful heartbeat loop."""
        mock_health_service = Mock(spec=AgentHealthService)
        heartbeat_manager = HeartbeatManager(
            "test-agent-123", mock_health_service, interval_seconds=1
        )

        mock_health_service.emit_heartbeat.return_value = True
        heartbeat_manager._running = True

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                heartbeat_manager._running = False
            return None

        mock_sleep.side_effect = side_effect

        heartbeat_manager._heartbeat_loop()

        assert mock_health_service.emit_heartbeat.call_count == 2
        assert mock_sleep.call_count == 2

    @patch("time.sleep")
    def test_heartbeat_loop_agent_not_found(self, mock_sleep):
        """Test heartbeat loop when agent not found."""
        mock_health_service = Mock(spec=AgentHealthService)
        heartbeat_manager = HeartbeatManager(
            "test-agent-123", mock_health_service, interval_seconds=1
        )

        mock_health_service.emit_heartbeat.return_value = False
        heartbeat_manager._running = True

        def side_effect(*args, **kwargs):
            heartbeat_manager._running = False
            return None

        mock_sleep.side_effect = side_effect

        heartbeat_manager._heartbeat_loop()

        mock_health_service.emit_heartbeat.assert_called_once_with("test-agent-123")
        mock_sleep.assert_called_once_with(1)

    @patch("time.sleep")
    def test_heartbeat_loop_exception_handling(self, mock_sleep):
        """Test heartbeat loop exception handling."""
        mock_health_service = Mock(spec=AgentHealthService)
        heartbeat_manager = HeartbeatManager(
            "test-agent-123", mock_health_service, interval_seconds=1
        )

        mock_health_service.emit_heartbeat.side_effect = Exception("Database error")
        heartbeat_manager._running = True

        def side_effect(*args, **kwargs):
            heartbeat_manager._running = False
            return None

        mock_sleep.side_effect = side_effect

        heartbeat_manager._heartbeat_loop()

        mock_health_service.emit_heartbeat.assert_called_once()
        mock_sleep.assert_called_once_with(1)
