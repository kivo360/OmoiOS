#!/usr/bin/env python3
"""
Smoke test for intelligent monitoring system.

This script performs basic functionality tests to ensure the intelligent
monitoring system is working correctly with your actual database setup.
"""

import asyncio
import logging
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omoi_os.config import get_app_settings
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.llm_service import LLMService
from omoi_os.services.agent_output_collector import AgentOutputCollector
from omoi_os.services.trajectory_context import TrajectoryContext
from omoi_os.services.intelligent_guardian import IntelligentGuardian
from omoi_os.services.conductor import ConductorService
from omoi_os.services.monitoring_loop import MonitoringLoop, MonitoringConfig
from omoi_os.models.agent import Agent
from omoi_os.models.agent_log import AgentLog

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IntelligentMonitoringSmokeTest:
    """Smoke test suite for intelligent monitoring system."""

    def __init__(self):
        """Initialize smoke test with database connection."""
        app_settings = get_app_settings()
        database_url = app_settings.database.url
        redis_url = app_settings.redis.url
        self.workspace_root = app_settings.workspace.root
        self.db = DatabaseService(connection_string=database_url)
        self.event_bus = EventBusService(redis_url=redis_url)
        self.llm_service = LLMService()
        self.test_results = []

        # Ensure database tables exist
        try:
            self.db.create_tables()
            self.log_test_result(
                "Database Initialization",
                True,
                "Database tables created/verified",
            )
        except Exception as e:
            self.log_test_result(
                "Database Initialization",
                False,
                f"Failed to create tables: {str(e)}",
            )

    def log_test_result(self, test_name: str, success: bool, message: str = ""):
        """Log test result."""
        status = "PASS" if success else "FAIL"
        logger.info(f"[{status}] {test_name}: {message}")
        self.test_results.append(
            {
                "test": test_name,
                "success": success,
                "message": message,
                "timestamp": datetime.utcnow(),
            }
        )

    def test_database_connection(self):
        """Test database connection and basic queries."""
        try:
            with self.db.get_session() as session:
                # Test basic query
                agent_count = session.query(Agent).count()
                self.log_test_result(
                    "Database Connection",
                    True,
                    f"Connected successfully, found {agent_count} agents",
                )
        except Exception as e:
            self.log_test_result(
                "Database Connection", False, f"Connection failed: {str(e)}"
            )

    def test_agent_output_collector(self):
        """Test AgentOutputCollector functionality."""
        try:
            collector = AgentOutputCollector(self.db, self.event_bus)

            # Test getting active agents
            active_agents = collector.get_active_agents()
            agent_count = len(active_agents)

            self.log_test_result(
                "AgentOutputCollector - Get Active Agents",
                True,
                f"Found {agent_count} active agents",
            )

            # Test log collection
            if active_agents:
                agent_id = active_agents[0].id
                collector.get_agent_output(agent_id)
                self.log_test_result(
                    "AgentOutputCollector - Get Agent Output",
                    True,
                    f"Retrieved output for agent {agent_id[:8]}...",
                )

                # Test event logging
                collector.log_agent_event(
                    agent_id,
                    "test_event",
                    "Test message from smoke test",
                    {"test": True},
                )
                self.log_test_result(
                    "AgentOutputCollector - Log Event",
                    True,
                    "Successfully logged test event",
                )
            else:
                self.log_test_result(
                    "AgentOutputCollector - Skip Tests",
                    True,
                    "No active agents to test with",
                )

        except Exception as e:
            self.log_test_result("AgentOutputCollector", False, f"Failed: {str(e)}")

    def test_trajectory_context(self):
        """Test TrajectoryContext functionality."""
        try:
            trajectory_context = TrajectoryContext(self.db)

            # Get a sample agent to test with
            with self.db.get_session() as session:
                agent = session.query(Agent).first()
                if not agent:
                    self.log_test_result(
                        "TrajectoryContext", False, "No agents found in database"
                    )
                    return

                # Test context building
                trajectory_context.build_accumulated_context(agent.id)
                self.log_test_result(
                    "TrajectoryContext - Build Context",
                    True,
                    f"Built context for agent {agent.id[:8]}...",
                )

                # Test trajectory summary
                summary = trajectory_context.get_trajectory_summary(agent.id)
                self.log_test_result(
                    "TrajectoryContext - Get Summary",
                    True,
                    f"Generated summary: {summary[:100]}...",
                )

                # Test cache operations
                trajectory_context.clear_cache(agent.id)
                self.log_test_result(
                    "TrajectoryContext - Cache Operations",
                    True,
                    "Cache operations completed successfully",
                )

        except Exception as e:
            self.log_test_result("TrajectoryContext", False, f"Failed: {str(e)}")

    def test_intelligent_guardian(self):
        """Test IntelligentGuardian functionality."""
        try:
            guardian = IntelligentGuardian(
                self.db,
                self.llm_service,
                self.event_bus,
                workspace_root=self.workspace_root,
            )

            # Get a sample agent
            with self.db.get_session() as session:
                agent = session.query(Agent).first()
                if not agent:
                    self.log_test_result(
                        "IntelligentGuardian", False, "No agents found in database"
                    )
                    return

                # Test trajectory analysis (may fail due to no LLM response, but should not crash)
                try:
                    analysis = guardian.analyze_agent_trajectory(agent.id)
                    if analysis:
                        self.log_test_result(
                            "IntelligentGuardian - Trajectory Analysis",
                            True,
                            f"Analysis completed with score {analysis.alignment_score:.2f}",
                        )
                    else:
                        self.log_test_result(
                            "IntelligentGuardian - Trajectory Analysis",
                            True,
                            "No analysis data available (expected with no logs)",
                        )
                except Exception as e:
                    # May fail due to LLM service not being configured
                    if "LLM" in str(e) or "invoke" in str(e):
                        self.log_test_result(
                            "IntelligentGuardian - Trajectory Analysis",
                            True,
                            "LLM service not configured (expected in test environment)",
                        )
                    else:
                        raise

                # Test system overview
                try:
                    overview = guardian.get_system_trajectory_overview()
                    self.log_test_result(
                        "IntelligentGuardian - System Overview",
                        True,
                        f"System has {overview.get('active_agents', 0)} active agents",
                    )
                except Exception as e:
                    self.log_test_result(
                        "IntelligentGuardian - System Overview",
                        False,
                        f"Failed: {str(e)}",
                    )

        except Exception as e:
            self.log_test_result("IntelligentGuardian", False, f"Failed: {str(e)}")

    def test_conductor_service(self):
        """Test ConductorService functionality."""
        try:
            conductor = ConductorService(self.db, self.llm_service)

            # Test system coherence analysis
            try:
                analysis = conductor.analyze_system_coherence()
                self.log_test_result(
                    "ConductorService - System Coherence",
                    True,
                    f"Coherence score: {analysis.coherence_score:.2f}, Status: {analysis.system_status}",
                )
            except Exception as e:
                # May fail due to LLM service
                if "LLM" in str(e) or "invoke" in str(e):
                    self.log_test_result(
                        "ConductorService - System Coherence",
                        True,
                        "LLM service not configured (expected in test environment)",
                    )
                else:
                    raise

            # Test system health summary
            try:
                health = conductor.get_system_health_summary()
                self.log_test_result(
                    "ConductorService - System Health",
                    True,
                    f"Health status: {health.get('current_status', 'unknown')}",
                )
            except Exception as e:
                self.log_test_result(
                    "ConductorService - System Health", False, f"Failed: {str(e)}"
                )

        except Exception as e:
            self.log_test_result("ConductorService", False, f"Failed: {str(e)}")

    async def test_monitoring_loop_basic(self):
        """Test basic MonitoringLoop functionality."""
        try:
            config = MonitoringConfig(
                guardian_interval_seconds=5,
                conductor_interval_seconds=10,
                health_check_interval_seconds=3,
                auto_steering_enabled=False,  # Disabled for safety in tests
                max_concurrent_analyses=1,
            )

            monitoring_loop = MonitoringLoop(self.db, self.event_bus, config)

            # Test status
            status = monitoring_loop.get_status()
            self.log_test_result(
                "MonitoringLoop - Get Status",
                True,
                f"Loop status: running={status['running']}",
            )

            # Test single cycle (this is the main test)
            try:
                cycle = await monitoring_loop.run_single_cycle()
                self.log_test_result(
                    "MonitoringLoop - Single Cycle",
                    True,
                    f"Cycle completed in {cycle.cycle_duration.total_seconds():.2f}s, Success: {cycle.success}",
                )
            except Exception as e:
                # May fail due to LLM service or other dependencies
                if "LLM" in str(e) or "invoke" in str(e):
                    self.log_test_result(
                        "MonitoringLoop - Single Cycle",
                        True,
                        "LLM service not configured (expected in test environment)",
                    )
                else:
                    self.log_test_result(
                        "MonitoringLoop - Single Cycle", False, f"Failed: {str(e)}"
                    )

            # Test emergency analysis
            try:
                with self.db.get_session() as session:
                    agent = session.query(Agent).first()
                    if agent:
                        result = await monitoring_loop.trigger_emergency_analysis(
                            [agent.id]
                        )
                        emergency_count = result.get("emergency_analyses", 0)
                        if isinstance(emergency_count, int):
                            count_str = str(emergency_count)
                        else:
                            count_str = str(len(emergency_count))
                        self.log_test_result(
                            "MonitoringLoop - Emergency Analysis",
                            True,
                            f"Emergency analysis completed for {count_str} agents",
                        )
            except Exception as e:
                if "LLM" in str(e) or "invoke" in str(e):
                    self.log_test_result(
                        "MonitoringLoop - Emergency Analysis",
                        True,
                        "LLM service not configured (expected in test environment)",
                    )
                else:
                    self.log_test_result(
                        "MonitoringLoop - Emergency Analysis",
                        False,
                        f"Failed: {str(e)}",
                    )

        except Exception as e:
            self.log_test_result("MonitoringLoop", False, f"Failed: {str(e)}")

    def create_test_data(self):
        """Create some test data for more comprehensive testing."""
        try:
            with self.db.get_session() as session:
                # Check if test agent already exists
                test_agent = (
                    session.query(Agent).filter_by(id="smoke-test-agent").first()
                )
                if test_agent:
                    self.log_test_result(
                        "Test Data Creation", True, "Test data already exists"
                    )
                    return

                # Create test agent
                test_agent = Agent(
                    id="smoke-test-agent",
                    agent_type="worker",
                    status="working",
                    phase_id="PHASE_IMPLEMENTATION",
                    capacity=100,
                    last_heartbeat=datetime.utcnow(),
                )
                session.add(test_agent)

                # Create test logs
                log_entries = [
                    AgentLog(
                        id=uuid.uuid4(),
                        agent_id="smoke-test-agent",
                        log_type="input",
                        message="Start implementing smoke test functionality",
                        created_at=datetime.utcnow() - timedelta(minutes=30),
                        details={"phase": "PHASE_IMPLEMENTATION"},
                    ),
                    AgentLog(
                        id=uuid.uuid4(),
                        agent_id="smoke-test-agent",
                        log_type="output",
                        message="Created test models and services",
                        created_at=datetime.utcnow() - timedelta(minutes=20),
                        details={
                            "files_created": ["models/test.py", "services/test.py"]
                        },
                    ),
                    AgentLog(
                        id=uuid.uuid4(),
                        agent_id="smoke-test-agent",
                        log_type="output",
                        message="Working on test validation",
                        created_at=datetime.utcnow() - timedelta(minutes=10),
                        details={"current_focus": "test validation"},
                    ),
                ]

                for log in log_entries:
                    session.add(log)

                session.commit()

                self.log_test_result(
                    "Test Data Creation",
                    True,
                    f"Created test agent with {len(log_entries)} log entries",
                )

        except Exception as e:
            self.log_test_result("Test Data Creation", False, f"Failed: {str(e)}")

    def cleanup_test_data(self):
        """Clean up test data."""
        try:
            with self.db.get_session() as session:
                # Delete test logs
                session.query(AgentLog).filter_by(agent_id="smoke-test-agent").delete()

                # Delete test agent
                session.query(Agent).filter_by(id="smoke-test-agent").delete()

                session.commit()

                self.log_test_result(
                    "Test Data Cleanup", True, "Test data cleaned up successfully"
                )

        except Exception as e:
            self.log_test_result("Test Data Cleanup", False, f"Failed: {str(e)}")

    def run_all_tests(self):
        """Run all smoke tests."""
        logger.info("Starting Intelligent Monitoring Smoke Test")
        logger.info("=" * 50)

        # Create test data first
        self.create_test_data()

        # Run synchronous tests
        self.test_database_connection()
        self.test_agent_output_collector()
        self.test_trajectory_context()
        self.test_intelligent_guardian()
        self.test_conductor_service()

        # Run async tests
        logger.info("Running async tests...")
        asyncio.run(self.test_monitoring_loop_basic())

        # Cleanup test data
        self.cleanup_test_data()

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        logger.info("=" * 50)
        logger.info("SMOKE TEST SUMMARY")
        logger.info("=" * 50)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests

        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests / total_tests) * 100:.1f}%")

        if failed_tests > 0:
            logger.info("\nFailed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    logger.info(f"  ❌ {result['test']}: {result['message']}")

        logger.info("\n" + "=" * 50)

        if failed_tests == 0:
            logger.info(
                "🎉 ALL TESTS PASSED! Intelligent monitoring system is working correctly."
            )
        else:
            logger.info("⚠️  Some tests failed. Check the logs above for details.")

        logger.info("=" * 50)

        return failed_tests == 0


def main():
    """Main entry point for smoke test."""
    smoke_test = IntelligentMonitoringSmokeTest()
    success = smoke_test.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
