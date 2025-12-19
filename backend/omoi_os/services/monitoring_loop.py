"""MonitoringLoop orchestration for intelligent monitoring system.

This service orchestrates the complete monitoring workflow:
- Coordinates Guardian trajectory analysis
- Runs Conductor system coherence analysis
- Manages monitoring cycles and intervals
- Provides unified monitoring interface
- Integrates with OpenHands execution model
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from omoi_os.logging import get_logger
from omoi_os.models.trajectory_analysis import (
    SystemHealthResponse,
    TrajectoryAnalysisResponse,
)
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.intelligent_guardian import IntelligentGuardian
from omoi_os.services.conductor import ConductorService
from omoi_os.services.agent_output_collector import AgentOutputCollector
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)


@dataclass
class MonitoringConfig:
    """Configuration for monitoring loop behavior."""

    guardian_interval_seconds: int = 60  # Analyze agents every minute
    conductor_interval_seconds: int = 300  # System coherence every 5 minutes
    health_check_interval_seconds: int = 30  # Health checks every 30 seconds
    auto_steering_enabled: bool = False  # Auto-execute steering interventions
    max_concurrent_analyses: int = 5  # Limit concurrent analyses
    workspace_root: Optional[str] = None  # Root directory for agent workspaces


@dataclass
class MonitoringCycle:
    """Container for a complete monitoring cycle."""

    cycle_id: uuid.UUID
    started_at: datetime
    guardian_analyses: List[Dict[str, Any]]
    conductor_analysis: Dict[str, Any]
    steering_interventions: List[Dict[str, Any]]
    cycle_duration: timedelta
    success: bool
    error_message: Optional[str] = None


class MonitoringLoop:
    """Orchestrates the complete intelligent monitoring workflow.

    This service coordinates:
    - Trajectory analysis via IntelligentGuardian
    - System coherence analysis via Conductor
    - Steering interventions and their execution
    - Health monitoring and alerting
    - OpenHands integration
    """

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
        config: Optional[MonitoringConfig] = None,
    ):
        """Initialize monitoring loop.

        Args:
            db: Database service for persistence
            event_bus: Optional event bus for real-time updates
            config: Optional monitoring configuration
        """
        self.db = db
        self.event_bus = event_bus
        self.config = config or MonitoringConfig()

        # Initialize monitoring components
        self.guardian = IntelligentGuardian(
            db, workspace_root=self.config.workspace_root, event_bus=event_bus
        )
        self.conductor = ConductorService(db)
        self.output_collector = AgentOutputCollector(db, event_bus)

        # State tracking
        self.running = False
        self.current_cycle_id: Optional[uuid.UUID] = None
        self.last_guardian_run: Optional[datetime] = None
        self.last_conductor_run: Optional[datetime] = None
        self.last_health_check: Optional[datetime] = None

        # Async tasks
        self._guardian_task: Optional[asyncio.Task] = None
        self._conductor_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None

        # Metrics
        self.total_cycles = 0
        self.successful_cycles = 0
        self.failed_cycles = 0
        self.total_interventions = 0

    async def start(self) -> None:
        """Start the monitoring loop."""
        if self.running:
            logger.warning("Monitoring loop is already running")
            return

        logger.info("Starting intelligent monitoring loop")
        self.running = True
        self.current_cycle_id = uuid.uuid4()

        # Start background tasks
        self._guardian_task = asyncio.create_task(self._guardian_loop())
        self._conductor_task = asyncio.create_task(self._conductor_loop())
        self._health_check_task = asyncio.create_task(self._health_check_loop())

        # Publish startup event
        self._publish_event("monitoring.started", {"cycle_id": str(self.current_cycle_id)})

    async def stop(self) -> None:
        """Stop the monitoring loop."""
        if not self.running:
            logger.warning("Monitoring loop is not running")
            return

        logger.info("Stopping intelligent monitoring loop")
        self.running = False

        # Cancel background tasks
        if self._guardian_task:
            self._guardian_task.cancel()
        if self._conductor_task:
            self._conductor_task.cancel()
        if self._health_check_task:
            self._health_check_task.cancel()

        # Wait for tasks to complete
        try:
            await asyncio.gather(
                self._guardian_task,
                self._conductor_task,
                self._health_check_task,
                return_exceptions=True,
            )
        except Exception as e:
            logger.error(f"Error stopping monitoring tasks: {e}")

        # Publish shutdown event
        self._publish_event("monitoring.stopped", {"total_cycles": self.total_cycles})

    async def run_single_cycle(self) -> MonitoringCycle:
        """Run a single complete monitoring cycle."""
        cycle_id = uuid.uuid4()
        started_at = utc_now()

        logger.info(f"Starting monitoring cycle {cycle_id}")

        try:
            # Step 1: Guardian trajectory analysis
            guardian_analyses = await self._run_guardian_analysis()

            # Step 2: Conductor system coherence analysis
            conductor_analysis = await self._run_conductor_analysis(cycle_id)

            # Step 3: Generate and execute steering interventions
            steering_interventions = await self._process_steering_interventions()

            # Step 4: Update system state
            await self._update_system_state(guardian_analyses, conductor_analysis)

            cycle_duration = utc_now() - started_at

            # Create cycle result
            cycle = MonitoringCycle(
                cycle_id=cycle_id,
                started_at=started_at,
                guardian_analyses=guardian_analyses,
                conductor_analysis=conductor_analysis,
                steering_interventions=steering_interventions,
                cycle_duration=cycle_duration,
                success=True,
            )

            self.total_cycles += 1
            self.successful_cycles += 1

            logger.info(f"Completed monitoring cycle {cycle_id} in {cycle_duration}")
            return cycle

        except Exception as e:
            cycle_duration = utc_now() - started_at
            error_message = str(e)

            logger.error(f"Monitoring cycle {cycle_id} failed: {e}")

            cycle = MonitoringCycle(
                cycle_id=cycle_id,
                started_at=started_at,
                guardian_analyses=[],
                conductor_analysis={},
                steering_interventions=[],
                cycle_duration=cycle_duration,
                success=False,
                error_message=error_message,
            )

            self.total_cycles += 1
            self.failed_cycles += 1

            # Publish failure event
            self._publish_event(
                "monitoring.cycle.failed",
                {
                    "cycle_id": str(cycle_id),
                    "error": error_message,
                    "duration": cycle_duration.total_seconds(),
                },
            )

            return cycle

    async def get_system_health(self) -> SystemHealthResponse:
        """Get current system health status."""
        return self.conductor.get_system_health_response()

    async def analyze_agent_trajectory(
        self, agent_id: str, force_analysis: bool = False
    ) -> Optional[TrajectoryAnalysisResponse]:
        """Analyze a specific agent's trajectory."""
        try:
            analysis = self.guardian.analyze_agent_trajectory(agent_id, force_analysis)
            if not analysis:
                return None

            return TrajectoryAnalysisResponse(
                agent_id=analysis.agent_id,
                current_phase=analysis.current_phase,
                trajectory_aligned=analysis.trajectory_aligned,
                alignment_score=analysis.alignment_score,
                needs_steering=analysis.needs_steering,
                steering_type=analysis.steering_type,
                steering_recommendation=analysis.steering_recommendation,
                trajectory_summary=analysis.trajectory_summary,
                current_focus=analysis.current_focus,
                conversation_length=analysis.conversation_length,
                session_duration=analysis.session_duration,
                health_score=self._calculate_agent_health_score(analysis),
                last_analysis=utc_now(),
            )

        except Exception as e:
            logger.error(f"Failed to analyze trajectory for agent {agent_id}: {e}")
            return None

    async def trigger_emergency_analysis(self, agent_ids: List[str]) -> Dict[str, Any]:
        """Trigger emergency analysis for specific agents."""
        logger.info(f"Triggering emergency analysis for agents: {agent_ids}")

        try:
            # Force analyze specified agents
            emergency_analyses = []
            for agent_id in agent_ids:
                analysis = await self.analyze_agent_trajectory(agent_id, force_analysis=True)
                if analysis:
                    emergency_analyses.append(analysis)

            # Run immediate conductor analysis
            conductor_response = await self.conductor.analyze_system_coherence_response()

            # Generate emergency interventions if needed
            emergency_interventions = []
            for analysis in emergency_analyses:
                if analysis.needs_steering and analysis.steering_recommendation:
                    intervention = {
                        "agent_id": analysis.agent_id,
                        "steering_type": analysis.steering_type,
                        "message": analysis.steering_recommendation,
                        "emergency": True,
                    }
                    emergency_interventions.append(intervention)

            return {
                "emergency_analyses": len(emergency_analyses),
                "system_coherence": conductor_response.coherence_score,
                "emergency_interventions": emergency_interventions,
                "triggered_at": utc_now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Emergency analysis failed: {e}")
            return {"error": str(e), "triggered_at": utc_now().isoformat()}

    # -------------------------------------------------------------------------
    # Background Loop Methods
    # -------------------------------------------------------------------------

    async def _guardian_loop(self) -> None:
        """Background loop for Guardian trajectory analysis."""
        while self.running:
            try:
                await self._run_guardian_analysis()
                self.last_guardian_run = utc_now()
                await asyncio.sleep(self.config.guardian_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Guardian loop error: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    async def _conductor_loop(self) -> None:
        """Background loop for Conductor system coherence analysis."""
        while self.running:
            try:
                await self._run_conductor_analysis()
                self.last_conductor_run = utc_now()
                await asyncio.sleep(self.config.conductor_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Conductor loop error: {e}")
                await asyncio.sleep(10)  # Brief pause on error

    async def _health_check_loop(self) -> None:
        """Background loop for system health checks."""
        while self.running:
            try:
                await self._run_health_check()
                self.last_health_check = utc_now()
                await asyncio.sleep(self.config.health_check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    # -------------------------------------------------------------------------
    # Analysis Execution Methods
    # -------------------------------------------------------------------------

    async def _run_guardian_analysis(self) -> List[Dict[str, Any]]:
        """Run Guardian trajectory analysis on all active agents (legacy + sandbox).

        This method now handles both:
        - Legacy agents: Registered in agents table with heartbeats
        - Sandbox agents: Tasks with sandbox_id that are in 'running' status

        The Guardian's analyze_agent_trajectory method uses auto-routing to
        pull data from the appropriate source (agent_logs vs sandbox_events).
        """
        try:
            agent_ids_to_analyze: set[str] = set()

            # 1. Get active legacy agents (registered agents with recent heartbeats)
            active_agents = self.output_collector.get_active_agents()
            for agent in active_agents:
                agent_ids_to_analyze.add(agent.id)

            # 2. Get active sandbox agents (tasks with sandbox_id in running status)
            sandbox_agent_ids = self._get_active_sandbox_agent_ids()
            agent_ids_to_analyze.update(sandbox_agent_ids)

            if not agent_ids_to_analyze:
                logger.debug("No active agents or sandbox tasks to analyze")
                return []

            logger.info(
                f"Guardian analysis: {len(active_agents)} legacy agents, "
                f"{len(sandbox_agent_ids)} sandbox agents"
            )

            # Run analyses with concurrency limit
            semaphore = asyncio.Semaphore(self.config.max_concurrent_analyses)
            tasks = []

            for agent_id in agent_ids_to_analyze:
                task = asyncio.create_task(
                    self._analyze_agent_with_semaphore(semaphore, agent_id)
                )
                tasks.append(task)

            # Wait for all analyses to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            analyses = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Agent analysis failed: {result}")
                elif result:
                    analyses.append(result)

            logger.info(f"Guardian analysis completed: {len(analyses)} agents analyzed")
            return analyses

        except Exception as e:
            logger.error(f"Guardian analysis failed: {e}")
            return []

    def _get_active_sandbox_agent_ids(self) -> List[str]:
        """Get sandbox IDs for all running sandbox tasks.

        Sandbox tasks have sandbox_id set and are executing in a Daytona sandbox.
        Note: Sandbox tasks do NOT have assigned_agent_id - they use sandbox_id
        as the execution context identifier.

        Returns:
            List of sandbox_ids for running sandbox tasks (used as agent identifiers)
        """
        try:
            with self.db.get_session() as session:
                # Find running tasks that have a sandbox_id
                # NOTE: Sandbox tasks don't have assigned_agent_id
                running_sandbox_tasks = (
                    session.query(Task)
                    .filter(
                        Task.status == "running",
                        Task.sandbox_id.isnot(None),
                    )
                    .all()
                )

                # Return sandbox_ids as the identifiers for monitoring
                sandbox_ids = [
                    str(task.sandbox_id)
                    for task in running_sandbox_tasks
                    if task.sandbox_id
                ]

                return sandbox_ids

        except Exception as e:
            logger.error(f"Failed to get active sandbox IDs: {e}")
            return []

    async def _analyze_agent_with_semaphore(
        self, semaphore: asyncio.Semaphore, agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze agent with concurrency control."""
        async with semaphore:
            # Analyze agent (now async)
            analysis = await self.guardian.analyze_agent_trajectory(agent_id, False)

            if analysis:
                return {
                    "agent_id": analysis.agent_id,
                    "alignment_score": analysis.alignment_score,
                    "needs_steering": analysis.needs_steering,
                    "trajectory_summary": analysis.trajectory_summary,
                    "current_focus": analysis.current_focus,
                    "current_phase": analysis.current_phase,
                }

            return None

    async def _run_conductor_analysis(
        self, cycle_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Run Conductor system coherence analysis."""
        try:
            # analyze_system_coherence is now async, so await directly
            analysis = await self.conductor.analyze_system_coherence(cycle_id)

            if analysis:
                result = {
                    "coherence_score": analysis.coherence_score,
                    "system_status": analysis.system_status,
                    "num_agents": analysis.num_agents,
                    "duplicate_count": analysis.duplicate_count,
                    "recommendations": analysis.recommendations,
                }

                # Publish system coherence event
                self._publish_event(
                    "monitoring.conductor.analysis",
                    {
                        "coherence_score": analysis.coherence_score,
                        "system_status": analysis.system_status,
                        "duplicate_count": analysis.duplicate_count,
                    },
                )

                logger.info(f"Conductor analysis: coherence={analysis.coherence_score:.2f}")
                return result

            return {}

        except Exception as e:
            logger.error(f"Conductor analysis failed: {e}")
            return {}

    async def _run_health_check(self) -> None:
        """Run system health check and publish status."""
        try:
            health_response = await self.get_system_health()

            # Check for critical conditions
            alerts = []
            if health_response.system_health == "critical":
                alerts.append("System health is critical")
            if health_response.active_agents == 0:
                alerts.append("No active agents detected")
            if health_response.average_alignment < 0.3:
                alerts.append("Average agent alignment is very low")

            # Publish health status
            self._publish_event(
                "monitoring.health.check",
                {
                    "system_health": health_response.system_health,
                    "active_agents": health_response.active_agents,
                    "average_alignment": health_response.average_alignment,
                    "alerts": alerts,
                },
            )

            if alerts:
                logger.warning(f"Health check alerts: {alerts}")

        except Exception as e:
            logger.error(f"Health check failed: {e}")

    async def _process_steering_interventions(self) -> List[Dict[str, Any]]:
        """Process steering interventions from Guardian analyses."""
        try:
            # Detect interventions needed
            loop = asyncio.get_event_loop()
            interventions = await loop.run_in_executor(
                None, self.guardian.detect_steering_interventions
            )

            if not interventions:
                return []

            executed_interventions = []
            for intervention in interventions:
                try:
                    # Execute intervention
                    success = await loop.run_in_executor(
                        None,
                        self.guardian.execute_steering_intervention,
                        intervention,
                        self.config.auto_steering_enabled,
                    )

                    if success:
                        executed_interventions.append(
                            {
                                "agent_id": intervention.agent_id,
                                "steering_type": intervention.steering_type,
                                "message": intervention.message,
                                "executed": self.config.auto_steering_enabled,
                            }
                        )
                        self.total_interventions += 1

                        logger.info(
                            f"Steering intervention for {intervention.agent_id}: {intervention.steering_type}"
                        )

                except Exception as e:
                    logger.error(f"Failed to execute steering intervention: {e}")

            return executed_interventions

        except Exception as e:
            logger.error(f"Failed to process steering interventions: {e}")
            return []

    async def _update_system_state(
        self,
        guardian_analyses: List[Dict[str, Any]],
        conductor_analysis: Dict[str, Any],
    ) -> None:
        """Update system state based on monitoring results."""
        try:
            # Calculate system metrics
            system_metrics = {
                "guardian_analyses": len(guardian_analyses),
                "average_alignment": sum(a.get("alignment_score", 0) for a in guardian_analyses)
                / max(len(guardian_analyses), 1),
                "agents_need_steering": sum(1 for a in guardian_analyses if a.get("needs_steering", False)),
                "system_coherence": conductor_analysis.get("coherence_score", 0.0),
                "duplicate_count": conductor_analysis.get("duplicate_count", 0),
                "timestamp": utc_now().isoformat(),
            }

            # Publish system state update
            self._publish_event("monitoring.system.updated", system_metrics)

        except Exception as e:
            logger.error(f"Failed to update system state: {e}")

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _calculate_agent_health_score(self, analysis) -> float:
        """Calculate health score for an agent analysis."""
        base_score = analysis.alignment_score

        # Penalty for needing steering
        if analysis.needs_steering:
            base_score *= 0.7

        # Penalty for trajectory misalignment
        if not analysis.trajectory_aligned:
            base_score *= 0.8

        return max(0.0, min(1.0, base_score))

    def _publish_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Publish monitoring event."""
        if not self.event_bus:
            return

        event = SystemEvent(
            event_type=event_type,
            entity_type="monitoring_loop",
            entity_id="monitoring_loop",
            payload=payload,
        )
        self.event_bus.publish(event)

    # -------------------------------------------------------------------------
    # Status and Metrics Methods
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring loop status."""
        return {
            "running": self.running,
            "current_cycle_id": str(self.current_cycle_id) if self.current_cycle_id else None,
            "config": {
                "guardian_interval": self.config.guardian_interval_seconds,
                "conductor_interval": self.config.conductor_interval_seconds,
                "health_check_interval": self.config.health_check_interval_seconds,
                "auto_steering_enabled": self.config.auto_steering_enabled,
                "max_concurrent_analyses": self.config.max_concurrent_analyses,
            },
            "timing": {
                "last_guardian_run": self.last_guardian_run.isoformat() if self.last_guardian_run else None,
                "last_conductor_run": self.last_conductor_run.isoformat() if self.last_conductor_run else None,
                "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            },
            "metrics": {
                "total_cycles": self.total_cycles,
                "successful_cycles": self.successful_cycles,
                "failed_cycles": self.failed_cycles,
                "total_interventions": self.total_interventions,
                "success_rate": self.successful_cycles / max(self.total_cycles, 1),
            },
        }