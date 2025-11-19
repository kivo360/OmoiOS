"""Intelligent Guardian service with LLM-powered trajectory analysis.

This service combines the existing emergency intervention capabilities
with sophisticated trajectory analysis using OpenHands conversation data
and LLM-powered agent understanding.
"""

import logging
import uuid
from datetime import timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from omoi_os.models.agent import Agent
from omoi_os.models.task import Task
from omoi_os.models.phase import PhaseModel
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.llm_service import LLMService
from omoi_os.services.trajectory_context import TrajectoryContext
from omoi_os.services.agent_output_collector import AgentOutputCollector
from omoi_os.services.guardian import GuardianService
from omoi_os.services.conversation_intervention import ConversationInterventionService
from omoi_os.services.template_service import get_template_service
from omoi_os.utils.datetime import utc_now

logger = logging.getLogger(__name__)


class TrajectoryAnalysis:
    """Container for trajectory analysis results."""

    def __init__(
        self,
        agent_id: str,
        current_phase: str,
        trajectory_aligned: bool,
        alignment_score: float,
        needs_steering: bool,
        steering_type: Optional[str],
        steering_recommendation: Optional[str],
        trajectory_summary: str,
        last_claude_message_marker: Optional[str],
        accumulated_goal: Optional[str],
        current_focus: str,
        session_duration: Optional[timedelta],
        conversation_length: int,
        details: Dict[str, Any],
    ):
        self.agent_id = agent_id
        self.current_phase = current_phase
        self.trajectory_aligned = trajectory_aligned
        self.alignment_score = alignment_score
        self.needs_steering = needs_steering
        self.steering_type = steering_type
        self.steering_recommendation = steering_recommendation
        self.trajectory_summary = trajectory_summary
        self.last_claude_message_marker = last_claude_message_marker
        self.accumulated_goal = accumulated_goal
        self.current_focus = current_focus
        self.session_duration = session_duration
        self.conversation_length = conversation_length
        self.details = details


class SteeringIntervention:
    """Container for steering intervention decisions."""

    def __init__(
        self,
        agent_id: str,
        steering_type: str,
        message: str,
        actor_type: str,
        actor_id: str,
        reason: str,
        confidence: float,
    ):
        self.agent_id = agent_id
        self.steering_type = steering_type
        self.message = message
        self.actor_type = actor_type
        self.actor_id = actor_id
        self.reason = reason
        self.confidence = confidence


class IntelligentGuardian:
    """Intelligent Guardian with trajectory analysis and LLM-powered understanding.

    This service extends the basic Guardian capabilities with:
    - Trajectory thinking and accumulated context analysis
    - LLM-powered agent behavior understanding
    - Proactive steering interventions
    - OpenHands conversation analysis
    """

    def __init__(
        self,
        db: DatabaseService,
        llm_service: Optional[LLMService] = None,
        event_bus: Optional[EventBusService] = None,
        workspace_root: Optional[str] = None,
    ):
        """Initialize intelligent guardian.

        Args:
            db: Database service for persistence
            llm_service: Optional LLM service for analysis
            event_bus: Optional event bus for real-time updates
            workspace_root: Root directory for agent workspaces
        """
        self.db = db
        self.llm_service = llm_service or LLMService()
        self.event_bus = event_bus
        self.workspace_root = workspace_root

        # Initialize helper services
        self.trajectory_context = TrajectoryContext(db)
        self.output_collector = AgentOutputCollector(db, event_bus)
        self.guardian = GuardianService(db, event_bus)

    def analyze_agent_trajectory(
        self,
        agent_id: str,
        force_analysis: bool = False,
    ) -> Optional[TrajectoryAnalysis]:
        """
        Analyze an agent's trajectory for alignment and steering needs.

        Args:
            agent_id: Agent ID to analyze
            force_analysis: Skip cache and force fresh analysis

        Returns:
            Trajectory analysis results or None if agent not found
        """
        try:
            # Check if we already have a recent analysis
            if not force_analysis:
                recent_analysis = self._get_recent_analysis(agent_id)
                if recent_analysis:
                    return recent_analysis

            # Get agent information
            with self.db.get_session() as session:
                agent = session.query(Agent).filter_by(id=agent_id).first()
                if not agent:
                    logger.warning(
                        f"Agent {agent_id} not found for trajectory analysis"
                    )
                    return None

                # Build trajectory context
                trajectory_data = self.trajectory_context.build_accumulated_context(
                    agent_id, session=session
                )

                if not trajectory_data:
                    logger.warning(f"No trajectory data available for agent {agent_id}")
                    return None

                # Get agent output for additional context
                agent_output = self.output_collector.get_agent_output(
                    agent_id, workspace_dir=self._get_workspace_dir(agent)
                )

                # Perform LLM-powered trajectory analysis
                analysis_result = self._llm_trajectory_analysis(
                    agent, trajectory_data, agent_output
                )

                if not analysis_result:
                    logger.error(f"LLM analysis failed for agent {agent_id}")
                    return None

                # Create trajectory analysis object
                trajectory_analysis = TrajectoryAnalysis(
                    agent_id=agent_id,
                    current_phase=analysis_result.get(
                        "current_phase", agent.phase_id or "unknown"
                    ),
                    trajectory_aligned=analysis_result.get("trajectory_aligned", True),
                    alignment_score=analysis_result.get("alignment_score", 0.8),
                    needs_steering=analysis_result.get("needs_steering", False),
                    steering_type=analysis_result.get("steering_type"),
                    steering_recommendation=analysis_result.get(
                        "steering_recommendation"
                    ),
                    trajectory_summary=analysis_result.get("trajectory_summary", ""),
                    last_claude_message_marker=analysis_result.get(
                        "last_claude_message_marker"
                    ),
                    accumulated_goal=analysis_result.get("accumulated_goal"),
                    current_focus=analysis_result.get("current_focus", "Unknown"),
                    session_duration=analysis_result.get("session_duration"),
                    conversation_length=analysis_result.get("conversation_length", 0),
                    details=analysis_result.get("details", {}),
                )

                # Store analysis in database
                self._store_guardian_analysis(
                    session, trajectory_analysis, agent_output
                )
                session.commit()

                return trajectory_analysis

        except Exception as e:
            logger.error(f"Failed to analyze trajectory for agent {agent_id}: {e}")
            return None

    def analyze_all_active_agents(
        self,
        force_analysis: bool = False,
    ) -> List[TrajectoryAnalysis]:
        """Analyze trajectories of all active agents."""
        active_agents = self.output_collector.get_active_agents()
        analyses = []

        for agent in active_agents:
            analysis = self.analyze_agent_trajectory(agent.id, force_analysis)
            if analysis:
                analyses.append(analysis)

        return analyses

    def detect_steering_interventions(
        self,
        analyses: Optional[List[TrajectoryAnalysis]] = None,
    ) -> List[SteeringIntervention]:
        """Detect agents that need steering interventions.

        Args:
            analyses: Optional pre-computed trajectory analyses

        Returns:
            List of recommended steering interventions
        """
        if analyses is None:
            analyses = self.analyze_all_active_agents()

        interventions = []

        for analysis in analyses:
            if analysis.needs_steering and analysis.steering_recommendation:
                intervention = SteeringIntervention(
                    agent_id=analysis.agent_id,
                    steering_type=analysis.steering_type or "guidance",
                    message=analysis.steering_recommendation,
                    actor_type="guardian",
                    actor_id="intelligent_guardian",
                    reason=analysis.trajectory_summary,
                    confidence=analysis.alignment_score,
                )
                interventions.append(intervention)

        return interventions

    def execute_steering_intervention(
        self,
        intervention: SteeringIntervention,
        auto_execute: bool = False,
    ) -> bool:
        """Execute a steering intervention.

        Args:
            intervention: Intervention to execute
            auto_execute: Whether to auto-execute or just record

        Returns:
            True if intervention was executed/recorded successfully
        """
        try:
            with self.db.get_session() as session:
                # Store intervention in database
                self._store_steering_intervention(session, intervention)

                if auto_execute:
                    # Execute the intervention via event or direct action
                    success = self._execute_intervention_action(intervention)
                    if success:
                        session.commit()
                        return True
                    else:
                        session.rollback()
                        return False
                else:
                    session.commit()
                    return True

        except Exception as e:
            logger.error(f"Failed to execute steering intervention: {e}")
            return False

    def get_agent_trajectory_health(self, agent_id: str) -> Dict[str, Any]:
        """Get comprehensive trajectory health for an agent."""
        try:
            analysis = self.analyze_agent_trajectory(agent_id)
            if not analysis:
                return {"status": "no_analysis", "agent_id": agent_id}

            # Get additional health metrics
            with self.db.get_session() as session:
                agent = session.query(Agent).filter_by(id=agent_id).first()
                if not agent:
                    return {"status": "agent_not_found", "agent_id": agent_id}

                # Get recent steering interventions
                recent_interventions = self._get_recent_interventions(agent_id)

                # Calculate health score
                health_score = self._calculate_health_score(
                    analysis, recent_interventions
                )

                return {
                    "status": "healthy",
                    "agent_id": agent_id,
                    "health_score": health_score,
                    "alignment_score": analysis.alignment_score,
                    "trajectory_aligned": analysis.trajectory_aligned,
                    "needs_steering": analysis.needs_steering,
                    "current_phase": analysis.current_phase,
                    "current_focus": analysis.current_focus,
                    "conversation_length": analysis.conversation_length,
                    "recent_interventions": len(recent_interventions),
                    "last_analysis": utc_now().isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to get trajectory health for {agent_id}: {e}")
            return {"status": "error", "agent_id": agent_id, "error": str(e)}

    def get_system_trajectory_overview(self) -> Dict[str, Any]:
        """Get system-wide trajectory overview."""
        try:
            analyses = self.analyze_all_active_agents()

            if not analyses:
                return {
                    "active_agents": 0,
                    "average_alignment": 0.0,
                    "agents_need_steering": 0,
                    "system_health": "no_activity",
                }

            # Calculate metrics
            active_agents = len(analyses)
            alignment_scores = [a.alignment_score for a in analyses]
            average_alignment = sum(alignment_scores) / len(alignment_scores)
            agents_need_steering = sum(1 for a in analyses if a.needs_steering)

            # Determine system health
            if average_alignment > 0.8 and agents_need_steering == 0:
                system_health = "optimal"
            elif average_alignment > 0.6 and agents_need_steering < active_agents * 0.3:
                system_health = "good"
            elif average_alignment > 0.4:
                system_health = "warning"
            else:
                system_health = "critical"

            return {
                "active_agents": active_agents,
                "average_alignment": average_alignment,
                "agents_need_steering": agents_need_steering,
                "system_health": system_health,
                "phase_distribution": self._get_phase_distribution(analyses),
                "steering_types": self._get_steering_type_distribution(analyses),
            }

        except Exception as e:
            logger.error(f"Failed to get system trajectory overview: {e}")
            return {"status": "error", "error": str(e)}

    # -------------------------------------------------------------------------
    # Private Analysis Methods
    # -------------------------------------------------------------------------

    def _get_recent_analysis(self, agent_id: str) -> Optional[TrajectoryAnalysis]:
        """Get recent analysis for an agent if available."""
        try:
            with self.db.get_session() as session:
                query = text("""
                    SELECT * FROM guardian_analyses
                    WHERE agent_id = :agent_id
                    AND created_at > :cutoff
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                result = session.execute(
                    query,
                    {
                        "agent_id": agent_id,
                        "cutoff": utc_now() - timedelta(minutes=5),
                    },
                )
                row = result.fetchone()

                if row:
                    data = dict(row._mapping)
                    return TrajectoryAnalysis(
                        agent_id=data["agent_id"],
                        current_phase=data["current_phase"],
                        trajectory_aligned=data["trajectory_aligned"],
                        alignment_score=data["alignment_score"],
                        needs_steering=data["needs_steering"],
                        steering_type=data["steering_type"],
                        steering_recommendation=data["steering_recommendation"],
                        trajectory_summary=data["trajectory_summary"],
                        last_claude_message_marker=data["last_claude_message_marker"],
                        accumulated_goal=data["accumulated_goal"],
                        current_focus=data["current_focus"],
                        session_duration=data["session_duration"],
                        conversation_length=data["conversation_length"] or 0,
                        details=data["details"] or {},
                    )

        except Exception as e:
            logger.error(f"Failed to get recent analysis for {agent_id}: {e}")

        return None

    def _get_past_summaries_timeline(
        self, agent_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get past summaries timeline for trajectory context.

        Args:
            agent_id: Agent ID to get summaries for
            limit: Maximum number of past summaries to retrieve

        Returns:
            List of summary dictionaries with time_ago, trajectory_summary, alignment_score, current_focus
        """
        try:
            with self.db.get_session() as session:
                query = text("""
                    SELECT 
                        trajectory_summary,
                        alignment_score,
                        current_focus,
                        created_at,
                        EXTRACT(EPOCH FROM (NOW() - created_at)) / 60 as minutes_ago
                    FROM guardian_analyses
                    WHERE agent_id = :agent_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
                result = session.execute(
                    query,
                    {"agent_id": agent_id, "limit": limit},
                )

                summaries = []
                for row in result.fetchall():
                    data = dict(row._mapping)
                    minutes_ago = int(data["minutes_ago"] or 0)

                    # Format time ago
                    if minutes_ago < 1:
                        time_ago = "just now"
                    elif minutes_ago < 60:
                        time_ago = f"{minutes_ago} min ago"
                    else:
                        hours_ago = minutes_ago // 60
                        time_ago = f"{hours_ago} hour{'s' if hours_ago > 1 else ''} ago"

                    summaries.append(
                        {
                            "time_ago": time_ago,
                            "trajectory_summary": data["trajectory_summary"] or "",
                            "alignment_score": float(data["alignment_score"] or 0.0),
                            "current_focus": data["current_focus"] or None,
                        }
                    )

                return summaries

        except Exception as e:
            logger.error(f"Failed to get past summaries timeline for {agent_id}: {e}")
            return []

    def _get_phase_context(self, phase_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Get phase context including done definitions, expected outputs, and phase prompt.

        Args:
            phase_id: Phase ID to get context for

        Returns:
            Dictionary with phase context or None if phase not found
        """
        if not phase_id:
            return None

        try:
            with self.db.get_session() as session:
                phase = session.query(PhaseModel).filter_by(id=phase_id).first()
                if not phase:
                    return None

                return phase.to_dict()

        except Exception as e:
            logger.error(f"Failed to get phase context for {phase_id}: {e}")
            return None

    def _llm_trajectory_analysis(
        self,
        agent: Agent,
        trajectory_data: Dict[str, Any],
        agent_output: str,
    ) -> Optional[Dict[str, Any]]:
        """Perform LLM-powered trajectory analysis using Jinja2 template.

        Args:
            agent: Agent to analyze
            trajectory_data: Trajectory context data from TrajectoryContext
            agent_output: Recent agent output from AgentOutputCollector

        Returns:
            Dictionary with analysis results or None if analysis failed
        """
        try:
            # Get past summaries timeline for trajectory context
            past_summaries = self._get_past_summaries_timeline(agent.id, limit=10)

            # Get phase context for validation
            phase_context = self._get_phase_context(agent.phase_id)

            # Render template with all context
            template_service = get_template_service()
            prompt = template_service.render(
                "prompts/guardian_analysis.md.j2",
                agent=agent,
                trajectory_data=trajectory_data,
                agent_output=agent_output,
                past_summaries=past_summaries,
                phase_context=phase_context,
            )

            response = self.llm_service.ainvoke(prompt)
            return response

        except Exception as e:
            logger.error(f"LLM trajectory analysis failed for agent {agent.id}: {e}")
            return None

    def _get_workspace_dir(self, agent: Agent) -> Optional[str]:
        """Get workspace directory for an agent."""
        if not self.workspace_root:
            return None

        return f"{self.workspace_root}/{agent.id}"

    def _store_guardian_analysis(
        self,
        session: Session,
        analysis: TrajectoryAnalysis,
        agent_output: str,
    ) -> None:
        """Store guardian analysis in database."""
        query = text("""
            INSERT INTO guardian_analyses (
                id, agent_id, current_phase, trajectory_aligned, alignment_score,
                needs_steering, steering_type, steering_recommendation, trajectory_summary,
                last_claude_message_marker, accumulated_goal, current_focus,
                session_duration, conversation_length, details, created_at, updated_at
            ) VALUES (
                :id, :agent_id, :current_phase, :trajectory_aligned, :alignment_score,
                :needs_steering, :steering_type, :steering_recommendation, :trajectory_summary,
                :last_claude_message_marker, :accumulated_goal, :current_focus,
                :session_duration, :conversation_length, :details, :created_at, :updated_at
            )
        """)

        session.execute(
            query,
            {
                "id": uuid.uuid4(),
                "agent_id": analysis.agent_id,
                "current_phase": analysis.current_phase,
                "trajectory_aligned": analysis.trajectory_aligned,
                "alignment_score": analysis.alignment_score,
                "needs_steering": analysis.needs_steering,
                "steering_type": analysis.steering_type,
                "steering_recommendation": analysis.steering_recommendation,
                "trajectory_summary": analysis.trajectory_summary,
                "last_claude_message_marker": analysis.last_claude_message_marker,
                "accumulated_goal": analysis.accumulated_goal,
                "current_focus": analysis.current_focus,
                "session_duration": analysis.session_duration,
                "conversation_length": analysis.conversation_length,
                "details": analysis.details,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            },
        )

    def _store_steering_intervention(
        self,
        session: Session,
        intervention: SteeringIntervention,
    ) -> None:
        """Store steering intervention in database."""
        query = text("""
            INSERT INTO steering_interventions (
                id, agent_id, steering_type, message, actor_type, actor_id, reason, created_at
            ) VALUES (
                :id, :agent_id, :steering_type, :message, :actor_type, :actor_id, :reason, :created_at
            )
        """)

        session.execute(
            query,
            {
                "id": uuid.uuid4(),
                "agent_id": intervention.agent_id,
                "steering_type": intervention.steering_type,
                "message": intervention.message,
                "actor_type": intervention.actor_type,
                "actor_id": intervention.actor_id,
                "reason": intervention.reason,
                "created_at": utc_now(),
            },
        )

    def _execute_intervention_action(self, intervention: SteeringIntervention) -> bool:
        """Execute the actual intervention action by sending message to OpenHands conversation."""
        try:
            # Get agent's current task to find conversation info
            with self.db.get_session() as session:
                agent = session.query(Agent).filter_by(id=intervention.agent_id).first()
                if not agent:
                    logger.warning(
                        f"Agent {intervention.agent_id} not found for intervention"
                    )
                    return False

                # Find the agent's current running task
                task = (
                    session.query(Task)
                    .filter_by(
                        assigned_agent_id=intervention.agent_id, status="running"
                    )
                    .order_by(Task.started_at.desc())
                    .first()
                )

                if not task or not task.conversation_id or not task.persistence_dir:
                    logger.warning(
                        f"Task with conversation info not found for agent {intervention.agent_id}. "
                        f"Task: {task.id if task else None}, "
                        f"conversation_id: {task.conversation_id if task else None}"
                    )
                    # Still publish event and log, but can't send to conversation
                    self._publish_intervention_event(intervention)
                    self._log_intervention(intervention)
                    return False

                # Get workspace directory for the task
                workspace_dir = self._get_workspace_dir(agent)
                if not workspace_dir:
                    # Fallback: construct from task ID
                    workspace_dir = (
                        f"{self.workspace_root}/{task.id}"
                        if self.workspace_root
                        else None
                    )

                if not workspace_dir:
                    logger.error(
                        f"Cannot determine workspace directory for task {task.id}"
                    )
                    self._publish_intervention_event(intervention)
                    self._log_intervention(intervention)
                    return False

                # Send intervention via ConversationInterventionService
                intervention_service = ConversationInterventionService()
                success = intervention_service.send_intervention(
                    conversation_id=task.conversation_id,
                    persistence_dir=task.persistence_dir,
                    workspace_dir=workspace_dir,
                    message=intervention.message,
                )

                if success:
                    logger.info(
                        f"Successfully sent Guardian intervention to conversation {task.conversation_id} "
                        f"for agent {intervention.agent_id}: {intervention.steering_type}"
                    )
                else:
                    logger.warning(
                        f"Failed to send intervention to conversation {task.conversation_id}"
                    )

                # Always publish event and log, regardless of conversation delivery success
                self._publish_intervention_event(intervention)
                self._log_intervention(intervention)

                return success

        except Exception as e:
            logger.error(f"Failed to execute intervention action: {e}", exc_info=True)
            # Still try to publish event and log
            try:
                self._publish_intervention_event(intervention)
                self._log_intervention(intervention)
            except:
                pass
            return False

    def _publish_intervention_event(self, intervention: SteeringIntervention) -> None:
        """Publish intervention event to event bus."""
        if self.event_bus:
            event = SystemEvent(
                event_type="guardian.steering.intervention",
                entity_type="agent",
                entity_id=intervention.agent_id,
                payload={
                    "steering_type": intervention.steering_type,
                    "message": intervention.message,
                    "actor_type": intervention.actor_type,
                    "actor_id": intervention.actor_id,
                    "reason": intervention.reason,
                    "confidence": intervention.confidence,
                },
            )
            self.event_bus.publish(event)

    def _log_intervention(self, intervention: SteeringIntervention) -> None:
        """Log intervention to agent output collector."""
        self.output_collector.log_agent_event(
            intervention.agent_id,
            "steering_intervention",
            intervention.message,
            {
                "steering_type": intervention.steering_type,
                "actor_type": intervention.actor_type,
                "actor_id": intervention.actor_id,
                "confidence": intervention.confidence,
            },
        )

    def _get_recent_interventions(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get recent interventions for an agent."""
        try:
            with self.db.get_session() as session:
                query = text("""
                    SELECT * FROM steering_interventions
                    WHERE agent_id = :agent_id
                    AND created_at > :cutoff
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                result = session.execute(
                    query,
                    {"agent_id": agent_id, "cutoff": utc_now() - timedelta(hours=1)},
                )
                return [dict(row._mapping) for row in result.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get recent interventions for {agent_id}: {e}")
            return []

    def _calculate_health_score(
        self,
        analysis: TrajectoryAnalysis,
        recent_interventions: List[Dict[str, Any]],
    ) -> float:
        """Calculate overall health score for an agent."""
        base_score = analysis.alignment_score

        # Penalty for needing steering
        if analysis.needs_steering:
            base_score *= 0.7

        # Penalty for recent interventions
        intervention_penalty = min(0.3, len(recent_interventions) * 0.1)
        base_score -= intervention_penalty

        # Penalty for trajectory misalignment
        if not analysis.trajectory_aligned:
            base_score *= 0.8

        return max(0.0, min(1.0, base_score))

    def _get_phase_distribution(
        self, analyses: List[TrajectoryAnalysis]
    ) -> Dict[str, int]:
        """Get distribution of agents across phases."""
        phase_counts = {}
        for analysis in analyses:
            phase = analysis.current_phase or "unknown"
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
        return phase_counts

    def _get_steering_type_distribution(
        self, analyses: List[TrajectoryAnalysis]
    ) -> Dict[str, int]:
        """Get distribution of steering types."""
        steering_counts = {}
        for analysis in analyses:
            if analysis.needs_steering and analysis.steering_type:
                steering_type = analysis.steering_type
                steering_counts[steering_type] = (
                    steering_counts.get(steering_type, 0) + 1
                )
        return steering_counts
