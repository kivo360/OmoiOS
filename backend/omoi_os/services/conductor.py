"""Conductor service for system coherence analysis and duplicate detection.

This service analyzes Guardian trajectory analyses to compute system-wide
coherence scores, detect duplicate work, and identify coordination opportunities.
Replaces the original tmux-based agent communication with database-driven analysis.
"""

import uuid
from datetime import timedelta
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from omoi_os.logging import get_logger
from omoi_os.models.agent import Agent
from omoi_os.models.task import Task
from omoi_os.models.guardian_analysis import (
    ConductorAnalysisModel,
    DetectedDuplicateModel,
)
from omoi_os.models.trajectory_analysis import (
    SystemCoherenceResponse,
    SystemHealthResponse,
)
from omoi_os.services.database import DatabaseService
from omoi_os.services.llm_service import LLMService
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)


class ConductorAnalysis:
    """Container for conductor analysis results."""

    def __init__(
        self,
        coherence_score: float,
        system_status: str,
        num_agents: int,
        duplicate_count: int,
        termination_count: int,
        coordination_count: int,
        detected_duplicates: List[Dict[str, Any]],
        recommendations: List[str],
    ):
        self.coherence_score = coherence_score
        self.system_status = system_status
        self.num_agents = num_agents
        self.duplicate_count = duplicate_count
        self.termination_count = termination_count
        self.coordination_count = coordination_count
        self.detected_duplicates = detected_duplicates
        self.recommendations = recommendations


class DuplicateDetection:
    """Container for duplicate work detection results."""

    def __init__(
        self,
        agent1_id: str,
        agent2_id: str,
        similarity_score: float,
        work_description: str,
        resources: Dict[str, Any],
        confidence: float,
    ):
        self.agent1_id = agent1_id
        self.agent2_id = agent2_id
        self.similarity_score = similarity_score
        self.work_description = work_description
        self.resources = resources
        self.confidence = confidence


class LLMDuplicateAnalysisResponse(BaseModel):
    """Pydantic model for LLM duplicate work analysis response."""

    is_duplicate: bool = Field(
        default=False,
        description="True if the agents are working on essentially the same task",
    )
    similarity_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How similar their work is (0-1)",
    )
    work_description: str = Field(
        default="",
        description="Description of the duplicate work",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How confident the assessment is (0-1)",
    )
    resources: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key resources they might be conflicting over",
    )


class ConductorService:
    """Conductor service for system-wide coherence analysis.

    This service replaces complex inter-agent communication protocols
    with intelligent database analysis and LLM-powered reasoning.
    """

    def __init__(
        self,
        db: DatabaseService,
        llm_service: Optional[LLMService] = None,
        llm_analysis_enabled: bool = True,
    ):
        """Initialize conductor service.

        Args:
            db: Database service for persistence
            llm_service: Optional LLM service for analysis
            llm_analysis_enabled: Whether to perform LLM-based duplicate analysis
                Set to False to save tokens (will skip duplicate detection)
        """
        self.db = db
        self.llm_service = llm_service or LLMService()
        self.llm_analysis_enabled = llm_analysis_enabled

    async def analyze_system_coherence(
        self,
        cycle_id: Optional[uuid.UUID] = None,
    ) -> ConductorAnalysis:
        """
        Analyze system coherence across all active agents (legacy + sandbox).

        This method now handles both:
        - Legacy agents: Registered in agents table with heartbeats
        - Sandbox agents: Tasks with sandbox_id that are in 'running' status

        Args:
            cycle_id: Optional cycle ID for tracking analysis cycles

        Returns:
            System coherence analysis results
        """
        try:
            with self.db.get_session() as session:
                # Generate cycle ID if not provided
                if not cycle_id:
                    cycle_id = uuid.uuid4()

                # Get all active agent IDs (legacy + sandbox)
                all_agent_ids = self._get_all_active_agent_ids(session)
                num_agents = len(all_agent_ids)

                # Also get legacy agents for backward compatibility with some methods
                active_agents = self._get_active_agents(session)

                if num_agents == 0:
                    return ConductorAnalysis(
                        coherence_score=1.0,
                        system_status="no_agents",
                        num_agents=0,
                        duplicate_count=0,
                        termination_count=0,
                        coordination_count=0,
                        detected_duplicates=[],
                        recommendations=["No active agents to analyze"],
                    )

                # Get recent Guardian analyses for ALL agents (legacy + sandbox)
                guardian_analyses = self._get_guardian_analyses_by_ids(
                    session, all_agent_ids
                )

                logger.info(
                    f"Conductor coherence analysis: {len(active_agents)} legacy agents, "
                    f"{num_agents - len(active_agents)} sandbox agents, "
                    f"{len(guardian_analyses)} Guardian analyses found"
                )

                # Compute coherence score
                coherence_score = self._compute_coherence_score(
                    session, guardian_analyses, active_agents
                )

                # Detect duplicate work
                duplicates = await self._detect_duplicates(session, guardian_analyses)

                # Identify termination and coordination opportunities
                termination_count = self._identify_termination_candidates(
                    guardian_analyses
                )
                coordination_count = self._identify_coordination_opportunities(
                    session, guardian_analyses
                )

                # Generate recommendations
                recommendations = self._generate_recommendations(
                    coherence_score, duplicates, guardian_analyses, active_agents
                )

                # Determine system status
                system_status = self._determine_system_status(
                    coherence_score, num_agents, duplicates
                )

                # Store analysis in database
                analysis_id = self._store_conductor_analysis(
                    session,
                    cycle_id,
                    coherence_score,
                    system_status,
                    num_agents,
                    len(duplicates),
                    termination_count,
                    coordination_count,
                    {
                        "recommendations": recommendations,
                        "guardian_analyses_count": len(guardian_analyses),
                    },
                )

                # Store detected duplicates
                for duplicate in duplicates:
                    self._store_duplicate(
                        session,
                        analysis_id,
                        duplicate.agent1_id,
                        duplicate.agent2_id,
                        duplicate.similarity_score,
                        duplicate.work_description,
                        duplicate.resources,
                    )

                return ConductorAnalysis(
                    coherence_score=coherence_score,
                    system_status=system_status,
                    num_agents=num_agents,
                    duplicate_count=len(duplicates),
                    termination_count=termination_count,
                    coordination_count=coordination_count,
                    detected_duplicates=[
                        {
                            "agent1_id": d.agent1_id,
                            "agent2_id": d.agent2_id,
                            "similarity_score": d.similarity_score,
                            "work_description": d.work_description,
                            "confidence": d.confidence,
                        }
                        for d in duplicates
                    ],
                    recommendations=recommendations,
                )

        except Exception as e:
            logger.error(f"Failed to analyze system coherence: {e}")
            return ConductorAnalysis(
                coherence_score=0.0,
                system_status="error",
                num_agents=0,
                duplicate_count=0,
                termination_count=0,
                coordination_count=0,
                detected_duplicates=[],
                recommendations=[f"Analysis error: {str(e)}"],
            )

    def _get_active_agents(self, session: Session) -> List[Agent]:
        """Get list of active legacy agents (with recent heartbeats)."""
        # Use proper AgentStatus enum values
        from omoi_os.models.agent_status import AgentStatus

        active_statuses = [AgentStatus.IDLE.value, AgentStatus.RUNNING.value]
        return (
            session.query(Agent)
            .filter(Agent.status.in_(active_statuses))
            .filter(Agent.last_heartbeat > utc_now() - timedelta(minutes=2))
            .all()
        )

    def _get_active_sandbox_agent_ids(self, session: Session) -> List[str]:
        """Get sandbox IDs for all running sandbox tasks.

        Sandbox tasks have sandbox_id set and are executing in a Daytona sandbox.
        Note: Sandbox tasks do NOT have assigned_agent_id - they use sandbox_id
        as the execution context identifier.

        Returns:
            List of sandbox_ids for running sandbox tasks (used as agent identifiers)
        """
        try:
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

            # Return sandbox_ids as the identifiers for coherence analysis
            return [
                str(task.sandbox_id)
                for task in running_sandbox_tasks
                if task.sandbox_id
            ]

        except Exception as e:
            logger.error(f"Failed to get active sandbox IDs: {e}")
            return []

    def _get_all_active_agent_ids(self, session: Session) -> List[str]:
        """Get all active agent IDs (both legacy and sandbox).

        This combines:
        - Legacy agents: Registered in agents table with recent heartbeats
        - Sandbox agents: Tasks with sandbox_id that are in 'running' status

        Returns:
            List of all active agent IDs
        """
        agent_ids: set[str] = set()

        # Get legacy agent IDs
        legacy_agents = self._get_active_agents(session)
        for agent in legacy_agents:
            agent_ids.add(str(agent.id))

        # Get sandbox agent IDs
        sandbox_agent_ids = self._get_active_sandbox_agent_ids(session)
        agent_ids.update(sandbox_agent_ids)

        return list(agent_ids)

    def _get_guardian_analyses(
        self, session: Session, active_agents: List[Agent]
    ) -> List[Dict[str, Any]]:
        """Get recent Guardian analyses for active agents (legacy only - for backward compat)."""
        if not active_agents:
            return []

        agent_ids = [str(agent.id) for agent in active_agents]
        return self._get_guardian_analyses_by_ids(session, agent_ids)

    def _get_guardian_analyses_by_ids(
        self, session: Session, agent_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Get recent Guardian analyses for specified agent IDs.

        This method works with both legacy and sandbox agents since
        the Guardian now stores analyses for both types.

        Args:
            session: Database session
            agent_ids: List of agent ID strings

        Returns:
            List of Guardian analysis dictionaries
        """
        if not agent_ids:
            return []

        # Get the most recent analysis for each active agent
        query = text("""
            WITH ranked_analyses AS (
                SELECT
                    ga.*,
                    ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY created_at DESC) as rn
                FROM guardian_analyses ga
                WHERE ga.agent_id = ANY(:agent_ids)
                AND ga.created_at > :cutoff
            )
            SELECT * FROM ranked_analyses WHERE rn = 1
        """)

        result = session.execute(
            query,
            {"agent_ids": agent_ids, "cutoff": utc_now() - timedelta(minutes=10)},
        )

        return [dict(row._mapping) for row in result.fetchall()]

    def _compute_coherence_score(
        self,
        session: Session,
        guardian_analyses: List[Dict[str, Any]],
        active_agents: List[Agent],
    ) -> float:
        """Compute overall system coherence score.

        0.0 = completely incoherent (chaos, conflicts, major duplications)
        1.0 = perfectly coherent (optimal coordination, no conflicts)
        """
        if not guardian_analyses or not active_agents:
            return 1.0  # No conflicts if no activity

        # Base score from individual agent alignments
        individual_scores = [
            analysis.get("alignment_score", 0.0) for analysis in guardian_analyses
        ]
        base_alignment = sum(individual_scores) / len(individual_scores)

        # Penalty for trajectory misalignment
        trajectory_aligned_count = sum(
            1
            for analysis in guardian_analyses
            if analysis.get("trajectory_aligned", True)
        )
        trajectory_penalty = (
            (len(active_agents) - trajectory_aligned_count) / len(active_agents) * 0.2
        )

        # Penalty for agents needing steering
        steering_needed_count = sum(
            1 for analysis in guardian_analyses if analysis.get("needs_steering", False)
        )
        steering_penalty = steering_needed_count / len(active_agents) * 0.3

        # Phase coherence bonus
        phase_coherence = self._calculate_phase_coherence(active_agents)

        # Agent load balance
        load_balance = self._calculate_load_balance(active_agents)

        # Combine factors
        coherence_score = base_alignment - trajectory_penalty - steering_penalty
        coherence_score += phase_coherence * 0.1  # Bonus for phase coherence
        coherence_score += load_balance * 0.1  # Bonus for balanced load

        return max(0.0, min(1.0, coherence_score))

    def _calculate_phase_coherence(self, active_agents: List[Agent]) -> float:
        """Calculate phase coherence bonus.

        Diversified phases get higher scores than clustering.
        """
        if not active_agents:
            return 0.0

        phase_counts = {}
        for agent in active_agents:
            phase = agent.phase_id or "unknown"
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

        # Perfect distribution: each agent in different phase
        max_phases = len(active_agents)
        actual_phases = len(phase_counts)

        return actual_phases / max_phases

    def _calculate_load_balance(self, active_agents: List[Agent]) -> float:
        """Calculate load balance across phases."""
        if not active_agents:
            return 0.0

        phase_counts = {}
        for agent in active_agents:
            phase = agent.phase_id or "unknown"
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

        # Lower variance = better balance
        counts = list(phase_counts.values())
        if not counts:
            return 0.0

        mean_count = sum(counts) / len(counts)
        variance = sum((c - mean_count) ** 2 for c in counts) / len(counts)
        max_variance = mean_count**2 if mean_count > 0 else 1.0

        # Convert to 0-1 scale (higher is better)
        balance_score = 1.0 - (variance / max_variance) if max_variance > 0 else 1.0
        return max(0.0, balance_score)

    async def _detect_duplicates(
        self, session: Session, guardian_analyses: List[Dict[str, Any]]
    ) -> List[DuplicateDetection]:
        """Detect duplicate work across agents using LLM analysis."""
        duplicates = []

        # Skip LLM-based duplicate detection if disabled (to save tokens)
        if not self.llm_analysis_enabled:
            logger.debug(
                "llm_duplicate_detection_disabled",
                reason="LLM analysis disabled via config",
            )
            return duplicates

        if len(guardian_analyses) < 2:
            return duplicates

        # Compare each pair of agents
        for i, analysis1 in enumerate(guardian_analyses):
            for j, analysis2 in enumerate(guardian_analyses[i + 1 :], i + 1):
                duplicate = await self._analyze_pair_for_duplicates(
                    analysis1, analysis2
                )
                if duplicate and duplicate.similarity_score > 0.7:
                    duplicates.append(duplicate)

        return duplicates

    async def _analyze_pair_for_duplicates(
        self, analysis1: Dict[str, Any], analysis2: Dict[str, Any]
    ) -> Optional[DuplicateDetection]:
        """Analyze a pair of agents for potential duplicate work."""
        try:
            # Extract current work contexts
            focus1 = analysis1.get("current_focus", "")
            summary1 = analysis1.get("trajectory_summary", "")
            phase1 = analysis1.get("current_phase", "")

            focus2 = analysis2.get("current_focus", "")
            summary2 = analysis2.get("trajectory_summary", "")
            phase2 = analysis2.get("current_phase", "")

            # Quick phase-based filter (same phase = higher duplicate probability)
            if phase1 != phase2:
                return None

            # Use LLM to analyze for duplicates
            duplicate_analysis = await self._llm_duplicate_analysis(
                focus1, summary1, focus2, summary2, phase1
            )

            if duplicate_analysis and duplicate_analysis.is_duplicate:
                return DuplicateDetection(
                    agent1_id=analysis1["agent_id"],
                    agent2_id=analysis2["agent_id"],
                    similarity_score=duplicate_analysis.similarity_score,
                    work_description=duplicate_analysis.work_description,
                    resources=duplicate_analysis.resources,
                    confidence=duplicate_analysis.confidence,
                )

        except Exception as e:
            logger.error(f"Failed to analyze pair for duplicates: {e}")

        return None

    async def _llm_duplicate_analysis(
        self,
        focus1: str,
        summary1: str,
        focus2: str,
        summary2: str,
        phase: str,
    ) -> Optional[LLMDuplicateAnalysisResponse]:
        """Use LLM to analyze for duplicate work."""
        try:
            prompt = f"""
            Analyze if these two agents are working on the same task:

            Agent 1:
            - Phase: {phase}
            - Current Focus: {focus1}
            - Work Summary: {summary1}

            Agent 2:
            - Phase: {phase}
            - Current Focus: {focus2}
            - Work Summary: {summary2}

            Determine if they are working on essentially the same task and might
            conflict over the same resources.
            """

            response = await self.llm_service.structured_output(
                prompt=prompt,
                output_type=LLMDuplicateAnalysisResponse,
                system_prompt="You are an expert at detecting duplicate work between agents.",
                output_retries=3,
            )
            return response

        except Exception as e:
            logger.error(f"LLM duplicate analysis failed: {e}")
            return None

    def _identify_termination_candidates(
        self, guardian_analyses: List[Dict[str, Any]]
    ) -> int:
        """Identify agents that could be safely terminated."""
        return sum(
            1
            for analysis in guardian_analyses
            if analysis.get("trajectory_summary", "").lower()
            in ["completed", "finished", "done", "resolved"]
        )

    def _identify_coordination_opportunities(
        self, session: Session, guardian_analyses: List[Dict[str, Any]]
    ) -> int:
        """Identify opportunities for agent coordination."""
        opportunities = 0

        # Look for agents in same phase with complementary work
        phase_groups = {}
        for analysis in guardian_analyses:
            phase = analysis.get("current_phase", "unknown")
            if phase not in phase_groups:
                phase_groups[phase] = []
            phase_groups[phase].append(analysis)

        for phase, agents in phase_groups.items():
            if len(agents) > 1:
                # Check if their work could be coordinated
                foci = [agent.get("current_focus", "") for agent in agents]
                if self._could_coordinate(foci):
                    opportunities += 1

        return opportunities

    def _could_coordinate(self, foci: List[str]) -> bool:
        """Check if agents with these focuses could benefit from coordination."""
        # Simple heuristic: look for related keywords
        all_text = " ".join(foci).lower()
        coordination_keywords = [
            "integration",
            "interface",
            "api",
            "connection",
            "communication",
            "dependency",
            "shared",
            "common",
        ]

        return any(keyword in all_text for keyword in coordination_keywords)

    def _generate_recommendations(
        self,
        coherence_score: float,
        duplicates: List[DuplicateDetection],
        guardian_analyses: List[Dict[str, Any]],
        active_agents: List[Agent],
    ) -> List[str]:
        """Generate system improvement recommendations."""
        recommendations = []

        # Low coherence recommendations
        if coherence_score < 0.5:
            recommendations.append(
                "System coherence is critically low - requires immediate attention"
            )
            recommendations.append(
                "Consider reducing concurrent agents or improving task coordination"
            )

        # Duplicate work recommendations
        if duplicates:
            recommendations.append(
                f"Found {len(duplicates)} duplicate work items - consolidate overlapping efforts"
            )
            for duplicate in duplicates[:3]:  # Top 3 duplicates
                recommendations.append(
                    f"Duplicate detected: {duplicate.agent1_id} and {duplicate.agent2_id} working on similar tasks"
                )

        # Load balancing recommendations
        phase_counts = {}
        for agent in active_agents:
            phase = agent.phase_id or "unknown"
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

        if phase_counts:
            max_count = max(phase_counts.values())
            if max_count > len(active_agents) * 0.6:  # More than 60% in one phase
                most_common_phase = max(phase_counts, key=phase_counts.get)
                recommendations.append(
                    f"Agent concentration too high in {most_common_phase} - redistribute workload"
                )

        # High coherence recommendations
        if coherence_score > 0.8:
            recommendations.append(
                "System coherence is excellent - current patterns are working well"
            )

        return recommendations

    def _determine_system_status(
        self,
        coherence_score: float,
        num_agents: int,
        duplicates: List[DuplicateDetection],
    ) -> str:
        """Determine overall system status."""
        if num_agents == 0:
            return "no_agents"
        elif coherence_score < 0.3:
            return "critical"
        elif coherence_score < 0.5:
            return "warning"
        elif len(duplicates) > num_agents * 0.3:
            return "inefficient"
        elif coherence_score > 0.8:
            return "optimal"
        else:
            return "normal"

    def _store_conductor_analysis(
        self,
        session: Session,
        cycle_id: uuid.UUID,
        coherence_score: float,
        system_status: str,
        num_agents: int,
        duplicate_count: int,
        termination_count: int,
        coordination_count: int,
        details: Dict[str, Any],
    ) -> uuid.UUID:
        """Store conductor analysis in database using SQLAlchemy ORM model.

        This handles JSONB conversion automatically through SQLAlchemy.
        """
        analysis_id = uuid.uuid4()

        # Use SQLAlchemy ORM model - JSONB conversion is automatic!
        conductor_analysis = ConductorAnalysisModel(
            id=analysis_id,
            cycle_id=cycle_id,
            coherence_score=coherence_score,
            system_status=system_status,
            num_agents=num_agents,
            duplicate_count=duplicate_count,
            termination_count=termination_count,
            coordination_count=coordination_count,
            details=details,  # Dict automatically converted to JSONB!
            created_at=utc_now(),
            updated_at=utc_now(),
        )

        session.add(conductor_analysis)
        return analysis_id

    def _store_duplicate(
        self,
        session: Session,
        conductor_analysis_id: uuid.UUID,
        agent1_id: str,
        agent2_id: str,
        similarity_score: float,
        work_description: str,
        resources: Dict[str, Any],
    ) -> None:
        """Store detected duplicate in database using SQLAlchemy ORM model.

        This handles JSONB conversion automatically through SQLAlchemy.
        """
        # Use SQLAlchemy ORM model - JSONB conversion is automatic!
        duplicate = DetectedDuplicateModel(
            id=uuid.uuid4(),
            conductor_analysis_id=conductor_analysis_id,
            agent1_id=agent1_id,
            agent2_id=agent2_id,
            similarity_score=similarity_score,
            work_description=work_description,
            resources=resources,  # Dict automatically converted to JSONB!
            created_at=utc_now(),
        )

        session.add(duplicate)

    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get a comprehensive system health summary."""
        try:
            with self.db.get_session() as session:
                # Get most recent conductor analysis
                query = text("""
                    SELECT * FROM conductor_analyses
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                result = session.execute(query)
                row = result.fetchone()
                recent_analysis = dict(row._mapping) if row else None

                # Get active agent count (legacy + sandbox)
                active_count = len(self._get_all_active_agent_ids(session))

                # Get recent duplicate count
                query = text("""
                    SELECT COUNT(*) as count
                    FROM detected_duplicates
                    WHERE created_at > :cutoff
                """)
                result = session.execute(
                    query, {"cutoff": utc_now() - timedelta(hours=1)}
                )
                row = result.fetchone()
                recent_duplicates = row.count if row else 0

                # Get average coherence over last hour
                query = text("""
                    SELECT AVG(coherence_score) as avg_score
                    FROM conductor_analyses
                    WHERE created_at > :cutoff
                """)
                result = session.execute(
                    query, {"cutoff": utc_now() - timedelta(hours=1)}
                )
                row = result.fetchone()
                avg_coherence = row.avg_score if row and row.avg_score else 0.0

                return {
                    "current_status": (
                        recent_analysis.get("system_status")
                        if recent_analysis
                        else "unknown"
                    ),
                    "current_coherence": (
                        recent_analysis.get("coherence_score")
                        if recent_analysis
                        else 0.0
                    ),
                    "average_coherence_1h": avg_coherence,
                    "active_agents": active_count,
                    "recent_duplicates": recent_duplicates,
                    "last_analysis": (
                        recent_analysis.get("created_at") if recent_analysis else None
                    ),
                }

        except Exception as e:
            logger.error(f"Failed to get system health summary: {e}")
            return {"error": str(e), "status": "error"}

    # Pydantic model response methods
    async def analyze_system_coherence_response(
        self,
        cycle_id: Optional[uuid.UUID] = None,
    ) -> SystemCoherenceResponse:
        """Analyze system coherence and return Pydantic response model."""
        analysis = await self.analyze_system_coherence(cycle_id)

        return SystemCoherenceResponse(
            coherence_score=analysis.coherence_score,
            system_status=analysis.system_status,
            num_agents=analysis.num_agents,
            duplicate_count=analysis.duplicate_count,
            termination_count=analysis.termination_count,
            coordination_count=analysis.coordination_count,
            detected_duplicates=analysis.detected_duplicates,
            recommendations=analysis.recommendations,
            analysis_id=uuid.uuid4(),  # Would be actual ID from database
        )

    def get_system_health_response(self) -> SystemHealthResponse:
        """Get system health summary as Pydantic response model."""
        health_data = self.get_system_health_summary()

        if "error" in health_data:
            return SystemHealthResponse(
                active_agents=0,
                average_alignment=0.0,
                agents_need_steering=0,
                system_health="error",
                phase_distribution={},
                steering_types={},
                recent_duplicates=0,
            )

        # Get additional data for full response
        with self.db.get_session() as session:
            # Get phase distribution (legacy agents + sandbox tasks)
            phase_distribution: Dict[str, int] = {}
            steering_types: Dict[str, int] = {}

            # Count legacy agents by phase
            active_agents = self._get_active_agents(session)
            for agent in active_agents:
                phase = agent.phase_id or "unknown"
                phase_distribution[phase] = phase_distribution.get(phase, 0) + 1

            # Count sandbox tasks by phase
            running_sandbox_tasks = (
                session.query(Task)
                .filter(
                    Task.status == "running",
                    Task.sandbox_id.isnot(None),
                )
                .all()
            )
            for task in running_sandbox_tasks:
                phase = task.phase_id or "unknown"
                phase_distribution[phase] = phase_distribution.get(phase, 0) + 1

            # Get recent steering types from guardian analyses
            try:
                query = text("""
                    SELECT steering_type, COUNT(*) as count
                    FROM guardian_analyses
                    WHERE needs_steering = true
                    AND steering_type IS NOT NULL
                    AND created_at > :cutoff
                    GROUP BY steering_type
                """)
                result = session.execute(
                    query, {"cutoff": utc_now() - timedelta(hours=1)}
                )
                for row in result.fetchall():
                    steering_types[row.steering_type] = row.count
            except Exception as e:
                logger.warning(f"Failed to get steering types: {e}")

        return SystemHealthResponse(
            active_agents=health_data.get("active_agents", 0),
            average_alignment=health_data.get("average_coherence_1h", 0.0),
            agents_need_steering=health_data.get("recent_duplicates", 0),  # Approximate
            system_health=health_data.get("current_status", "unknown"),
            phase_distribution=phase_distribution,
            steering_types=steering_types,
            recent_duplicates=health_data.get("recent_duplicates", 0),
            last_analysis=health_data.get("last_analysis"),
        )
