"""Comprehensive tests for intelligent monitoring system."""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from omoi_os.models.agent import Agent
from omoi_os.models.agent_log import AgentLog
from omoi_os.models.task import Task
from omoi_os.models.trajectory_analysis import (
    SystemHealthResponse,
)
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.llm_service import LLMService
from omoi_os.services.agent_output_collector import AgentOutputCollector
from omoi_os.services.trajectory_context import TrajectoryContext
from omoi_os.services.intelligent_guardian import IntelligentGuardian
from omoi_os.services.conductor import ConductorService
from omoi_os.services.monitoring_loop import MonitoringLoop, MonitoringConfig


@pytest.fixture
def mock_db():
    """Mock database service."""
    mock_db = Mock(spec=DatabaseService)
    # Setup context manager for get_session()
    mock_session = Mock()
    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_session)
    mock_context.__exit__ = Mock(return_value=False)
    mock_db.get_session.return_value = mock_context
    return mock_db


@pytest.fixture
def mock_event_bus():
    """Mock event bus service."""
    event_bus = Mock(spec=EventBusService)
    event_bus.publish = Mock()
    return event_bus


@pytest.fixture
def mock_llm_service():
    """Mock LLM service."""
    llm_service = Mock(spec=LLMService)
    llm_service.ainvoke = Mock()
    return llm_service


@pytest.fixture
def sample_agent():
    """Create a sample agent for testing."""
    return Agent(
        id="test-agent-001",
        agent_type="worker",
        status="working",
        phase_id="PHASE_IMPLEMENTATION",
        capacity=100,
        last_heartbeat=datetime.utcnow(),
    )


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        id=uuid.uuid4(),
        title="Test Task",
        raw_description="Implement user authentication",
        enriched_description="Implement secure user authentication with JWT tokens",
        phase_id="PHASE_IMPLEMENTATION",
        status="in_progress",
        priority="HIGH",
        estimated_complexity=5,
        done_definition="Users can register, login, and access protected endpoints",
    )


@pytest.fixture
def sample_agent_logs(sample_agent):
    """Create sample agent logs for testing."""
    logs = [
        AgentLog(
            id=str(uuid.uuid4()),
            agent_id=sample_agent.id,
            log_type="input",
            message="Start implementing user authentication",
            created_at=datetime.utcnow() - timedelta(minutes=30),
            details={"phase": "PHASE_IMPLEMENTATION"},
        ),
        AgentLog(
            id=str(uuid.uuid4()),
            agent_id=sample_agent.id,
            log_type="output",
            message="Created user model with email and password fields",
            created_at=datetime.utcnow() - timedelta(minutes=25),
            details={"files_created": ["models/user.py"]},
        ),
        AgentLog(
            id=str(uuid.uuid4()),
            agent_id=sample_agent.id,
            log_type="output",
            message="Implemented JWT token generation and validation",
            created_at=datetime.utcnow() - timedelta(minutes=20),
            details={"files_created": ["services/auth.py"]},
        ),
        AgentLog(
            id=str(uuid.uuid4()),
            agent_id=sample_agent.id,
            log_type="output",
            message="Working on login endpoint authentication",
            created_at=datetime.utcnow() - timedelta(minutes=10),
            details={"current_focus": "login endpoint"},
        ),
    ]
    return logs


class TestAgentOutputCollector:
    """Test cases for AgentOutputCollector service."""

    def test_get_agent_output_with_logs(
        self, mock_db, mock_event_bus, sample_agent_logs
    ):
        """Test getting agent output from database logs."""
        # Get the session from the fixture's context manager
        mock_session = mock_db.get_session.return_value.__enter__.return_value

        # Chain: query(AgentLog).filter_by(agent_id=...).filter(...).order_by(...).limit(...).all()
        mock_query = Mock()
        mock_filter_by = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        mock_limit = Mock()

        mock_query.filter_by.return_value = mock_filter_by
        mock_filter_by.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.limit.return_value = mock_limit
        mock_limit.all.return_value = sample_agent_logs

        mock_session.query.return_value = mock_query

        collector = AgentOutputCollector(mock_db, mock_event_bus)
        output = collector.get_agent_output(sample_agent_logs[0].agent_id)

        assert (
            "Recent Logs" in output
            or "Start implementing user authentication" in output
        )
        assert (
            "Start implementing user authentication" in output
            or "Working on login endpoint" in output
        )

    def test_get_agent_output_empty(self, mock_db, mock_event_bus):
        """Test getting agent output when no logs exist."""
        mock_session = mock_db.get_session.return_value.__enter__.return_value
        # Setup proper query chain
        mock_query = Mock()
        mock_filter_by = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        mock_limit = Mock()

        mock_query.filter_by.return_value = mock_filter_by
        mock_filter_by.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.limit.return_value = mock_limit
        mock_limit.all.return_value = []

        mock_session.query.return_value = mock_query

        collector = AgentOutputCollector(mock_db, mock_event_bus)
        output = collector.get_agent_output("non-existent-agent")

        assert "No agent output available" in output or "No recent logs found" in output

    def test_log_agent_event(self, mock_db, mock_event_bus):
        """Test logging agent events."""
        mock_session = mock_db.get_session.return_value.__enter__.return_value

        collector = AgentOutputCollector(mock_db, mock_event_bus)
        collector.log_agent_event(
            "test-agent", "output", "Test message", {"key": "value"}
        )

        # Verify log entry was created
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.event_type == "agent.event"
        assert event.entity_id == "test-agent"

    def test_get_active_agents(self, mock_db, mock_event_bus, sample_agent):
        """Test getting list of active agents."""
        mock_session = mock_db.get_session.return_value.__enter__.return_value
        # Chain: query(Agent).filter(...).filter(...).all()
        mock_query = Mock()
        mock_filter1 = Mock()
        mock_filter2 = Mock()

        mock_query.filter.return_value = mock_filter1
        mock_filter1.filter.return_value = mock_filter2
        mock_filter2.all.return_value = [sample_agent]

        mock_session.query.return_value = mock_query

        collector = AgentOutputCollector(mock_db, mock_event_bus)
        active_agents = collector.get_active_agents()

        assert len(active_agents) == 1
        assert active_agents[0].id == sample_agent.id

    def test_check_agent_responsiveness(self, mock_db, mock_event_bus, sample_agent):
        """Test checking agent responsiveness."""
        mock_session = mock_db.get_session.return_value.__enter__.return_value
        # Setup query chains for both Agent and AgentLog queries
        mock_agent_query = Mock()
        mock_agent_filter_by = Mock()
        mock_agent_query.filter_by.return_value = mock_agent_filter_by
        mock_agent_filter_by.first.return_value = sample_agent

        mock_log_query = Mock()
        mock_log_filter_by = Mock()
        mock_log_filter = Mock()
        mock_log_query.filter_by.return_value = mock_log_filter_by
        mock_log_filter_by.filter.return_value = mock_log_filter
        mock_log_filter.first.return_value = AgentLog(
            id=str(uuid.uuid4()),
            agent_id=sample_agent.id,
            log_type="output",
            message="Recent activity",
            created_at=datetime.utcnow() - timedelta(minutes=1),
        )

        # Make query() return different mocks based on what's queried
        def query_side_effect(model):
            if model == Agent:
                return mock_agent_query
            elif model == AgentLog:
                return mock_log_query
            return Mock()

        mock_session.query.side_effect = query_side_effect

        collector = AgentOutputCollector(mock_db, mock_event_bus)
        responsive = collector.check_agent_responsiveness(sample_agent.id)

        assert responsive is True


class TestTrajectoryContext:
    """Test cases for TrajectoryContext service."""

    def test_build_accumulated_context_with_logs(
        self, mock_db, sample_agent_logs, sample_task
    ):
        """Test building accumulated context from agent logs."""
        mock_session = mock_db.get_session.return_value.__enter__.return_value
        # Setup query chains
        mock_log_query = Mock()
        mock_log_filter_by = Mock()
        mock_log_order_by = Mock()
        mock_log_query.filter_by.return_value = mock_log_filter_by
        mock_log_filter_by.order_by.return_value = mock_log_order_by
        mock_log_order_by.all.return_value = sample_agent_logs

        mock_agent_query = Mock()
        mock_agent_filter_by = Mock()
        mock_agent_query.filter_by.return_value = mock_agent_filter_by
        mock_agent_filter_by.first.return_value = Agent(
            id=sample_agent_logs[0].agent_id, agent_type="worker", status="working"
        )

        mock_task_query = Mock()
        mock_task_filter_by = Mock()
        mock_task_query.filter_by.return_value = mock_task_filter_by
        mock_task_filter_by.first.return_value = sample_task

        def query_side_effect(model):
            if model == AgentLog:
                return mock_log_query
            elif model == Agent:
                return mock_agent_query
            elif model == Task:
                return mock_task_query
            return Mock()

        mock_session.query.side_effect = query_side_effect

        trajectory_context = TrajectoryContext(mock_db)
        context = trajectory_context.build_accumulated_context(
            sample_agent_logs[0].agent_id
        )

        assert context is not None
        assert "accumulated_context" in context or "current_phase" in context

    def test_build_accumulated_context_no_logs(self, mock_db):
        """Test building context when no logs exist."""
        mock_session = mock_db.get_session.return_value.__enter__.return_value
        # Setup query chains
        mock_log_query = Mock()
        mock_log_filter_by = Mock()
        mock_log_order_by = Mock()
        mock_log_query.filter_by.return_value = mock_log_filter_by
        mock_log_filter_by.order_by.return_value = mock_log_order_by
        mock_log_order_by.all.return_value = []

        mock_agent_query = Mock()
        mock_agent_filter_by = Mock()
        mock_agent_query.filter_by.return_value = mock_agent_filter_by
        mock_agent_filter_by.first.return_value = None

        def query_side_effect(model):
            if model == AgentLog:
                return mock_log_query
            elif model == Agent:
                return mock_agent_query
            return Mock()

        mock_session.query.side_effect = query_side_effect

        trajectory_context = TrajectoryContext(mock_db)
        context = trajectory_context.build_accumulated_context("non-existent-agent")

        assert context is not None

    def test_get_trajectory_summary(self, mock_db, sample_agent_logs):
        """Test getting trajectory summary."""
        mock_session = mock_db.get_session.return_value.__enter__.return_value
        # Setup query chain for logs
        mock_log_query = Mock()
        mock_log_filter_by = Mock()
        mock_log_order_by = Mock()
        mock_log_query.filter_by.return_value = mock_log_filter_by
        mock_log_filter_by.order_by.return_value = mock_log_order_by
        mock_log_order_by.all.return_value = sample_agent_logs

        def query_side_effect(model):
            if model == AgentLog:
                return mock_log_query
            return Mock()

        mock_session.query.side_effect = query_side_effect

        trajectory_context = TrajectoryContext(mock_db)
        with patch.object(
            trajectory_context, "build_accumulated_context"
        ) as mock_build:
            mock_build.return_value = {
                "overall_goal": "Implement user authentication",
                "current_focus": "login endpoint",
                "session_duration": timedelta(minutes=30),
                "constraints": [],
                "discovered_blockers": [],
            }

            summary = trajectory_context.get_trajectory_summary("test-agent")

            assert (
                "Goal: Implement user authentication" in summary
                or "login endpoint" in summary
            )

    def test_clear_cache(self, mock_db):
        """Test clearing context cache."""
        trajectory_context = TrajectoryContext(mock_db)

        # Add some cached data
        trajectory_context.context_cache["test-agent"] = {
            "context": {"test": "data"},
            "timestamp": datetime.utcnow(),
        }

        # Clear specific agent cache
        trajectory_context.clear_cache("test-agent")
        assert "test-agent" not in trajectory_context.context_cache

        # Add data back and clear all
        trajectory_context.context_cache["test-agent"] = {
            "context": {"test": "data"},
            "timestamp": datetime.utcnow(),
        }
        trajectory_context.clear_cache()
        assert len(trajectory_context.context_cache) == 0


class TestIntelligentGuardian:
    """Test cases for IntelligentGuardian service."""

    def test_analyze_agent_trajectory_success(
        self, mock_db, mock_llm_service, mock_event_bus, sample_agent, sample_task
    ):
        """Test successful agent trajectory analysis."""
        # Mock LLM response
        mock_llm_service.ainvoke.return_value = {
            "trajectory_aligned": True,
            "alignment_score": 0.85,
            "needs_steering": False,
            "steering_type": None,
            "steering_recommendation": None,
            "trajectory_summary": "Agent is implementing user authentication successfully",
            "current_focus": "login endpoint implementation",
            "accumulated_goal": "Implement complete user authentication system",
            "conversation_length": 15,
            "session_duration": "0:45:00",
            "last_claude_message_marker": "JWT token validation implemented",
            "details": {"confidence": 0.9},
        }

        # Mock database queries
        mock_session = Mock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            sample_agent
        )
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock trajectory context
        with (
            patch.object(
                IntelligentGuardian, "_get_recent_analysis", return_value=None
            ),
            patch.object(
                IntelligentGuardian, "_get_workspace_dir", return_value="/tmp/workspace"
            ),
            patch(
                "omoi_os.services.intelligent_guardian.TrajectoryContext"
            ) as mock_trajectory,
        ):
            mock_trajectory.return_value.build_accumulated_context.return_value = {
                "accumulated_context": "Test context",
                "constraints": [],
                "session_duration": timedelta(minutes=45),
            }

            # Mock agent output collector
            with patch.object(
                IntelligentGuardian, "AgentOutputCollector"
            ) as mock_collector:
                mock_collector.return_value.get_agent_output.return_value = (
                    "Recent agent output"
                )

                guardian = IntelligentGuardian(
                    mock_db, llm_service=mock_llm_service, event_bus=mock_event_bus
                )
                analysis = guardian.analyze_agent_trajectory(sample_agent.id)

                assert analysis is not None
                assert analysis.agent_id == sample_agent.id
                assert analysis.alignment_score == 0.85
                assert analysis.trajectory_aligned is True
                assert analysis.needs_steering is False

    def test_analyze_agent_trajectory_not_found(
        self, mock_db, mock_llm_service, mock_event_bus
    ):
        """Test analyzing trajectory for non-existent agent."""
        mock_session = mock_db.get_session.return_value.__enter__.return_value
        mock_query = Mock()
        mock_filter_by = Mock()
        mock_query.filter_by.return_value = mock_filter_by
        mock_filter_by.first.return_value = None
        mock_session.query.return_value = mock_query

        guardian = IntelligentGuardian(
            mock_db, llm_service=mock_llm_service, event_bus=mock_event_bus
        )
        analysis = guardian.analyze_agent_trajectory("non-existent-agent")

        assert analysis is None

    def test_detect_steering_interventions(
        self, mock_db, mock_llm_service, mock_event_bus
    ):
        """Test detecting steering interventions."""
        # Create mock analyses that need steering
        mock_analyses = [
            Mock(
                agent_id="agent-1",
                needs_steering=True,
                steering_type="guidance",
                steering_recommendation="Focus on security best practices",
            ),
            Mock(
                agent_id="agent-2",
                needs_steering=False,
                steering_type=None,
                steering_recommendation=None,
            ),
        ]

        with patch.object(
            IntelligentGuardian, "analyze_all_active_agents", return_value=mock_analyses
        ):
            guardian = IntelligentGuardian(
                mock_db, llm_service=mock_llm_service, event_bus=mock_event_bus
            )
            interventions = guardian.detect_steering_interventions()

            assert len(interventions) == 1
            assert interventions[0].agent_id == "agent-1"
            assert interventions[0].steering_type == "guidance"

    def test_execute_steering_intervention(
        self, mock_db, mock_llm_service, mock_event_bus
    ):
        """Test executing steering intervention."""
        intervention = Mock(
            agent_id="test-agent",
            steering_type="guidance",
            message="Please focus on test coverage",
            actor_type="guardian",
            actor_id="intelligent_guardian",
            reason="Low test coverage detected",
            confidence=0.8,
        )

        guardian = IntelligentGuardian(
            mock_db, llm_service=mock_llm_service, event_bus=mock_event_bus
        )

        with (
            patch.object(guardian, "_store_steering_intervention") as mock_store,
            patch.object(guardian, "_execute_intervention_action") as mock_execute,
        ):
            mock_execute.return_value = True

            result = guardian.execute_steering_intervention(
                intervention, auto_execute=True
            )

            assert result is True
            mock_store.assert_called_once()
            mock_execute.assert_called_once()

    def test_get_agent_trajectory_health(
        self, mock_db, mock_llm_service, mock_event_bus
    ):
        """Test getting agent trajectory health."""
        mock_analysis = Mock(
            agent_id="test-agent",
            alignment_score=0.9,
            trajectory_aligned=True,
            needs_steering=False,
            current_phase="PHASE_IMPLEMENTATION",
            current_focus="authentication",
            conversation_length=25,
        )

        with (
            patch.object(
                IntelligentGuardian,
                "analyze_agent_trajectory",
                return_value=mock_analysis,
            ),
            patch.object(
                IntelligentGuardian, "_get_recent_interventions", return_value=[]
            ),
        ):
            guardian = IntelligentGuardian(
                mock_db, llm_service=mock_llm_service, event_bus=mock_event_bus
            )
            health = guardian.get_agent_trajectory_health("test-agent")

            assert health["status"] == "healthy"
            assert health["agent_id"] == "test-agent"
            assert health["health_score"] == 0.9
            assert health["alignment_score"] == 0.9
            assert health["recent_interventions"] == 0

    def test_get_system_trajectory_overview(
        self, mock_db, mock_llm_service, mock_event_bus
    ):
        """Test getting system trajectory overview."""
        mock_analyses = [
            Mock(
                alignment_score=0.9,
                needs_steering=False,
                current_phase="PHASE_IMPLEMENTATION",
            ),
            Mock(
                alignment_score=0.7, needs_steering=True, current_phase="PHASE_TESTING"
            ),
            Mock(
                alignment_score=0.85,
                needs_steering=False,
                current_phase="PHASE_IMPLEMENTATION",
            ),
        ]

        with patch.object(
            IntelligentGuardian, "analyze_all_active_agents", return_value=mock_analyses
        ):
            guardian = IntelligentGuardian(
                mock_db, llm_service=mock_llm_service, event_bus=mock_event_bus
            )
            overview = guardian.get_system_trajectory_overview()

            assert overview["active_agents"] == 3
            assert (
                abs(overview["average_alignment"] - 0.8166666666666667) < 0.0001
            )  # (0.9 + 0.7 + 0.85) / 3
            assert overview["agents_need_steering"] == 1
            assert overview["system_health"] == "good"


class TestConductorService:
    """Test cases for ConductorService."""

    def test_analyze_system_coherence_no_agents(self, mock_db, mock_llm_service):
        """Test system coherence analysis with no active agents."""
        mock_session = mock_db.get_session.return_value.__enter__.return_value
        mock_query = Mock()
        mock_filter1 = Mock()
        mock_filter2 = Mock()
        mock_query.filter.return_value = mock_filter1
        mock_filter1.filter.return_value = mock_filter2
        mock_filter2.all.return_value = []
        mock_session.query.return_value = mock_query

        conductor = ConductorService(mock_db, llm_service=mock_llm_service)
        analysis = conductor.analyze_system_coherence()

        assert analysis.num_agents == 0
        assert analysis.coherence_score == 1.0
        assert analysis.system_status == "no_agents"
        assert len(analysis.detected_duplicates) == 0

    def test_analyze_system_coherence_with_agents(
        self, mock_db, mock_llm_service, sample_agent
    ):
        """Test system coherence analysis with active agents."""
        # Mock active agents
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.filter.return_value.all.return_value = [
            sample_agent
        ]

        # Mock guardian analyses
        mock_guardian_analyses = [
            {
                "agent_id": sample_agent.id,
                "alignment_score": 0.8,
                "trajectory_aligned": True,
                "needs_steering": False,
                "current_phase": "PHASE_IMPLEMENTATION",
            }
        ]
        mock_session = mock_db.get_session.return_value.__enter__.return_value
        mock_query = Mock()
        mock_filter1 = Mock()
        mock_filter2 = Mock()
        mock_query.filter.return_value = mock_filter1
        mock_filter1.filter.return_value = mock_filter2
        mock_filter2.all.return_value = [sample_agent]
        mock_session.query.return_value = mock_query

        mock_session.execute.return_value.fetchall.return_value = [
            Mock(
                _mapping=lambda: {
                    "agent_id": sample_agent.id,
                    "alignment_score": 0.8,
                    "trajectory_aligned": True,
                    "needs_steering": False,
                    "current_phase": "PHASE_IMPLEMENTATION",
                }
            )
        ]

        # Mock duplicate detection to return no duplicates
        with patch.object(ConductorService, "_detect_duplicates", return_value=[]):
            conductor = ConductorService(mock_db, llm_service=mock_llm_service)
            analysis = conductor.analyze_system_coherence()

            assert analysis.num_agents == 1
            assert analysis.coherence_score > 0.5  # Should be reasonably high
            assert analysis.duplicate_count == 0

    def test_detect_duplicates_no_matches(self, mock_db, mock_llm_service):
        """Test duplicate detection with no matching agents."""
        analyses = [
            {
                "agent_id": "agent-1",
                "current_phase": "PHASE_IMPLEMENTATION",
                "trajectory_summary": "Working on auth",
            },
            {
                "agent_id": "agent-2",
                "current_phase": "PHASE_TESTING",
                "trajectory_summary": "Writing tests",
            },
        ]

        with patch.object(
            ConductorService, "_analyze_pair_for_duplicates", return_value=None
        ):
            conductor = ConductorService(mock_db, llm_service=mock_llm_service)
            duplicates = conductor._detect_duplicates(None, analyses)

            assert len(duplicates) == 0

    def test_get_system_health_summary(self, mock_db, mock_llm_service):
        """Test getting system health summary."""
        mock_session = mock_db.get_session.return_value.__enter__.return_value

        # Mock recent conductor analysis
        mock_result1 = Mock()
        mock_result1.system_status = "optimal"
        mock_result1.coherence_score = 0.9
        mock_result1.created_at = datetime.utcnow()

        # Mock execute results
        mock_execute_result1 = Mock()
        mock_execute_result1.fetchone.return_value = mock_result1

        mock_execute_result2 = Mock()
        mock_execute_result2.count = 1

        mock_execute_result3 = Mock()
        mock_execute_result3.avg_score = 0.85

        mock_session.execute.side_effect = [
            mock_execute_result1,  # recent analysis
            mock_execute_result2,  # recent_duplicates
            mock_execute_result3,  # avg_coherence
        ]

        # Mock active agents count
        with patch.object(
            ConductorService, "_get_active_agents", return_value=[Mock()]
        ):
            conductor = ConductorService(mock_db, llm_service=mock_llm_service)
            health = conductor.get_system_health_summary()

            assert health["current_status"] == "optimal"
            assert health["current_coherence"] == 0.9
            assert health["average_coherence_1h"] == 0.85
            assert health["active_agents"] == 1
            assert health["recent_duplicates"] == 1


class TestMonitoringLoop:
    """Test cases for MonitoringLoop orchestration."""

    @pytest.fixture
    def monitoring_config(self):
        """Create test monitoring configuration."""
        return MonitoringConfig(
            guardian_interval_seconds=10,
            conductor_interval_seconds=30,
            health_check_interval_seconds=5,
            auto_steering_enabled=False,
            max_concurrent_analyses=2,
        )

    @pytest.mark.asyncio
    async def test_start_stop_monitoring_loop(
        self, mock_db, mock_event_bus, monitoring_config
    ):
        """Test starting and stopping the monitoring loop."""
        with patch("asyncio.create_task") as mock_create_task:
            mock_task = AsyncMock()
            mock_create_task.return_value = mock_task

            monitoring_loop = MonitoringLoop(mock_db, mock_event_bus, monitoring_config)

            # Test start
            await monitoring_loop.start()

            assert monitoring_loop.running is True
            assert monitoring_loop.current_cycle_id is not None
            assert (
                mock_create_task.call_count == 3
            )  # guardian, conductor, health_check tasks

            # Test stop
            await monitoring_loop.stop()

            assert monitoring_loop.running is False
            mock_task.cancel.assert_called()

    @pytest.mark.asyncio
    async def test_run_single_cycle_success(
        self, mock_db, mock_event_bus, monitoring_config
    ):
        """Test running a single monitoring cycle successfully."""
        monitoring_loop = MonitoringLoop(mock_db, mock_event_bus, monitoring_config)

        # Mock the individual analysis steps
        with (
            patch.object(
                monitoring_loop,
                "_run_guardian_analysis",
                return_value=[{"agent_id": "agent-1", "alignment_score": 0.8}],
            ),
            patch.object(
                monitoring_loop,
                "_run_conductor_analysis",
                return_value={"coherence_score": 0.85, "system_status": "good"},
            ),
            patch.object(
                monitoring_loop, "_process_steering_interventions", return_value=[]
            ),
        ):
            cycle = await monitoring_loop.run_single_cycle()

            assert cycle.success is True
            assert cycle.cycle_id is not None
            assert len(cycle.guardian_analyses) == 1
            assert cycle.conductor_analysis["coherence_score"] == 0.85
            assert cycle.error_message is None

    @pytest.mark.asyncio
    async def test_run_single_cycle_failure(
        self, mock_db, mock_event_bus, monitoring_config
    ):
        """Test running a single monitoring cycle with failure."""
        monitoring_loop = MonitoringLoop(mock_db, mock_event_bus, monitoring_config)

        # Mock guardian analysis to raise an exception
        with patch.object(
            monitoring_loop,
            "_run_guardian_analysis",
            side_effect=Exception("Test error"),
        ):
            cycle = await monitoring_loop.run_single_cycle()

            assert cycle.success is False
            assert cycle.error_message == "Test error"
            assert monitoring_loop.failed_cycles == 1

    @pytest.mark.asyncio
    async def test_get_system_health(self, mock_db, mock_event_bus, monitoring_config):
        """Test getting system health from monitoring loop."""
        monitoring_loop = MonitoringLoop(mock_db, mock_event_bus, monitoring_config)

        # Mock conductor response
        mock_health_response = SystemHealthResponse(
            active_agents=3,
            average_alignment=0.82,
            agents_need_steering=1,
            system_health="good",
            phase_distribution={"PHASE_IMPLEMENTATION": 2, "PHASE_TESTING": 1},
            steering_types={"guidance": 1},
            recent_duplicates=0,
        )

        with patch.object(
            monitoring_loop.conductor,
            "get_system_health_response",
            return_value=mock_health_response,
        ):
            health = await monitoring_loop.get_system_health()

            assert health.active_agents == 3
            assert health.average_alignment == 0.82
            assert health.system_health == "good"

    @pytest.mark.asyncio
    async def test_analyze_agent_trajectory(
        self, mock_db, mock_event_bus, monitoring_config
    ):
        """Test analyzing specific agent trajectory."""
        monitoring_loop = MonitoringLoop(mock_db, mock_event_bus, monitoring_config)

        # Mock guardian analysis
        mock_analysis = Mock(
            agent_id="test-agent",
            current_phase="PHASE_IMPLEMENTATION",
            trajectory_aligned=True,
            alignment_score=0.9,
            needs_steering=False,
            steering_type=None,
            steering_recommendation=None,
            trajectory_summary="Agent is working well",
            current_focus="authentication",
            conversation_length=20,
            session_duration=timedelta(minutes=45),
        )

        with patch.object(
            monitoring_loop.guardian,
            "analyze_agent_trajectory",
            return_value=mock_analysis,
        ):
            response = await monitoring_loop.analyze_agent_trajectory("test-agent")

            assert response.agent_id == "test-agent"
            assert response.alignment_score == 0.9
            assert (
                response.health_score == 0.9
            )  # Should equal alignment_score when no penalties

    @pytest.mark.asyncio
    async def test_trigger_emergency_analysis(
        self, mock_db, mock_event_bus, monitoring_config
    ):
        """Test triggering emergency analysis for specific agents."""
        monitoring_loop = MonitoringLoop(mock_db, mock_event_bus, monitoring_config)

        agent_ids = ["agent-1", "agent-2"]

        # Mock individual agent analyses
        mock_analyses = [
            Mock(
                agent_id="agent-1",
                needs_steering=True,
                steering_type="emergency",
                steering_recommendation="Immediate action required",
            ),
            Mock(
                agent_id="agent-2",
                needs_steering=False,
                steering_type=None,
                steering_recommendation=None,
            ),
        ]

        with (
            patch.object(
                monitoring_loop, "analyze_agent_trajectory", side_effect=mock_analyses
            ),
            patch.object(
                monitoring_loop.conductor,
                "analyze_system_coherence_response",
                return_value=Mock(coherence_score=0.7),
            ),
        ):
            result = await monitoring_loop.trigger_emergency_analysis(agent_ids)

            assert result["emergency_analyses"] == 2
            assert result["system_coherence"] == 0.7
            assert len(result["emergency_interventions"]) == 1
            assert result["emergency_interventions"][0]["agent_id"] == "agent-1"

    def test_get_status(self, mock_db, mock_event_bus, monitoring_config):
        """Test getting monitoring loop status."""
        monitoring_loop = MonitoringLoop(mock_db, mock_event_bus, monitoring_config)

        # Set some state
        monitoring_loop.running = True
        monitoring_loop.current_cycle_id = uuid.uuid4()
        monitoring_loop.total_cycles = 10
        monitoring_loop.successful_cycles = 8
        monitoring_loop.failed_cycles = 2
        monitoring_loop.total_interventions = 3
        monitoring_loop.last_guardian_run = datetime.utcnow()

        status = monitoring_loop.get_status()

        assert status["running"] is True
        assert status["current_cycle_id"] is not None
        assert status["metrics"]["total_cycles"] == 10
        assert status["metrics"]["successful_cycles"] == 8
        assert status["metrics"]["failed_cycles"] == 2
        assert status["metrics"]["success_rate"] == 0.8
        assert status["config"]["guardian_interval"] == 10
        assert status["config"]["auto_steering_enabled"] is False


class TestIntegration:
    """Integration tests for the complete monitoring system."""

    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_workflow(
        self, mock_db, mock_event_bus, mock_llm_service
    ):
        """Test complete end-to-end monitoring workflow."""
        # This test verifies the integration between all components

        # 1. Setup monitoring loop
        config = MonitoringConfig(
            guardian_interval_seconds=1,  # Fast for testing
            conductor_interval_seconds=2,
            auto_steering_enabled=False,
        )

        with (
            patch(
                "omoi_os.services.monitoring_loop.IntelligentGuardian"
            ) as mock_guardian_class,
            patch(
                "omoi_os.services.monitoring_loop.ConductorService"
            ) as mock_conductor_class,
            patch(
                "omoi_os.services.monitoring_loop.AgentOutputCollector"
            ) as mock_collector_class,
        ):
            # Mock the service instances
            mock_guardian = AsyncMock()
            mock_conductor = AsyncMock()
            mock_collector = AsyncMock()

            mock_guardian_class.return_value = mock_guardian
            mock_conductor_class.return_value = mock_conductor
            mock_collector_class.return_value = mock_collector

            # Setup mock returns
            mock_collector.get_active_agents.return_value = [
                Mock(id="agent-1"),
                Mock(id="agent-2"),
            ]

            mock_guardian.analyze_agent_trajectory.side_effect = [
                Mock(
                    agent_id="agent-1",
                    alignment_score=0.8,
                    needs_steering=False,
                    trajectory_summary="Agent 1 working on auth",
                ),
                Mock(
                    agent_id="agent-2",
                    alignment_score=0.6,
                    needs_steering=True,
                    steering_recommendation="Focus on security",
                    trajectory_summary="Agent 2 has security issues",
                ),
            ]

            mock_guardian.detect_steering_interventions.return_value = [
                Mock(
                    agent_id="agent-2",
                    steering_type="guidance",
                    message="Focus on security best practices",
                )
            ]

            mock_conductor.analyze_system_coherence.return_value = Mock(
                coherence_score=0.73,
                system_status="warning",
                num_agents=2,
                duplicate_count=0,
                recommendations=["Review security practices"],
            )

            # 2. Create and run monitoring loop
            monitoring_loop = MonitoringLoop(mock_db, mock_event_bus, config)

            # 3. Run a single cycle
            cycle = await monitoring_loop.run_single_cycle()

            # 4. Verify results
            assert cycle.success is True
            assert len(cycle.guardian_analyses) == 2
            assert cycle.conductor_analysis["coherence_score"] == 0.73
            assert len(cycle.steering_interventions) == 1
            assert cycle.steering_interventions[0]["agent_id"] == "agent-2"

            # 5. Verify service interactions
            mock_collector.get_active_agents.assert_called()
            assert mock_guardian.analyze_agent_trajectory.call_count == 2
            mock_guardian.detect_steering_interventions.assert_called_once()
            mock_conductor.analyze_system_coherence.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_publishing_integration(self, mock_db, mock_event_bus):
        """Test that monitoring events are properly published."""
        config = MonitoringConfig(
            guardian_interval_seconds=1, auto_steering_enabled=True
        )

        with (
            patch(
                "omoi_os.services.monitoring_loop.IntelligentGuardian"
            ) as mock_guardian_class,
            patch(
                "omoi_os.services.monitoring_loop.ConductorService"
            ) as mock_conductor_class,
            patch(
                "omoi_os.services.monitoring_loop.AgentOutputCollector"
            ) as mock_collector_class,
        ):
            # Setup mocks
            mock_guardian = AsyncMock()
            mock_conductor = AsyncMock()
            mock_collector = AsyncMock()

            mock_guardian_class.return_value = mock_guardian
            mock_conductor_class.return_value = mock_conductor
            mock_collector_class.return_value = mock_collector

            # Mock minimal data for cycle
            mock_collector.get_active_agents.return_value = []
            mock_guardian.analyze_all_active_agents.return_value = []
            mock_conductor.analyze_system_coherence.return_value = Mock(
                coherence_score=1.0,
                system_status="optimal",
                num_agents=0,
                duplicate_count=0,
                recommendations=[],
            )
            mock_guardian.detect_steering_interventions.return_value = []

            monitoring_loop = MonitoringLoop(mock_db, mock_event_bus, config)

            # Run cycle
            await monitoring_loop.run_single_cycle()

            # Verify events were published
            assert mock_event_bus.publish.call_count >= 1

            # Check event types
            published_events = [
                call[0][0] for call in mock_event_bus.publish.call_args_list
            ]
            event_types = [event.event_type for event in published_events]

            # Should have system updated event
            assert "monitoring.system.updated" in event_types


# Smoke test for basic functionality
def test_basic_imports():
    """Test that all monitoring components can be imported."""
    from omoi_os.services.agent_output_collector import AgentOutputCollector
    from omoi_os.services.trajectory_context import TrajectoryContext
    from omoi_os.services.intelligent_guardian import IntelligentGuardian
    from omoi_os.services.conductor import ConductorService
    from omoi_os.services.monitoring_loop import MonitoringLoop

    # Test that imports work
    assert AgentOutputCollector is not None
    assert TrajectoryContext is not None
    assert IntelligentGuardian is not None
    assert ConductorService is not None
    assert MonitoringLoop is not None
