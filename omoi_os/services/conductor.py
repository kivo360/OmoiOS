"""Conductor service for system coherence analysis and duplicate detection.

This service analyzes Guardian trajectory analyses to compute system-wide
coherence scores, detect duplicate work, and identify coordination opportunities.
Replaces the original tmux-based agent communication with database-driven analysis.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from omoi_os.models.agent import Agent
from omoi_os.models.trajectory_analysis import (
    ConductorAnalysis as ConductorAnalysisModel,
    DetectedDuplicate as DetectedDuplicateModel,
    SystemCoherenceResponse,
    SystemHealthResponse,
)
from omoi_os.services.database import DatabaseService
from omoi_os.services.llm_service import LLMService
from omoi_os.utils.datetime import utc_now

logger = logging.getLogger(__name__)


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


class ConductorService:
    """Conductor service for system-wide coherence analysis.

    This service replaces complex inter-agent communication protocols
    with intelligent database analysis and LLM-powered reasoning.
    """

    def __init__(
        self,
        db: DatabaseService,
        llm_service: Optional[LLMService] = None,
    ):
        """Initialize conductor service.

        Args:
            db: Database service for persistence
            llm_service: Optional LLM service for analysis
        """
        self.db = db
        self.llm_service = llm_service or LLMService()

    def analyze_system_coherence(
        self,
        cycle_id: Optional[uuid.UUID] = None,
    ) -> ConductorAnalysis:
        """
        Analyze system coherence across all active agents.

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

                # Get active agents
                active_agents = self._get_active_agents(session)
                num_agents = len(active_agents)

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

                # Get recent Guardian analyses
                guardian_analyses = self._get_guardian_analyses(session, active_agents)

                # Compute coherence score
                coherence_score = self._compute_coherence_score(
                    session, guardian_analyses, active_agents
                )

                # Detect duplicate work
                duplicates = self._detect_duplicates(session, guardian_analyses)

                # Identify termination and coordination opportunities
                termination_count = self._identify_termination_candidates(guardian_analyses)
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
        """Get list of active agents."""
        active_statuses = ["working", "pending", "assigned", "idle"]
        return (
            session.query(Agent)
            .filter(Agent.status.in_(active_statuses))
            .filter(Agent.last_heartbeat > utc_now() - timedelta(minutes=2))
            .all()
        )

    def _get_guardian_analyses(
        self, session: Session, active_agents: List[Agent]
    ) -> List[Dict[str, Any]]:
        """Get recent Guardian analyses for active agents."""
        if not active_agents:
            return []

        agent_ids = [agent.id for agent in active_agents]

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
            1 for analysis in guardian_analyses if analysis.get("trajectory_aligned", True)
        )
        trajectory_penalty = (
            len(active_agents) - trajectory_aligned_count
        ) / len(active_agents) * 0.2

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
        max_variance = mean_count ** 2 if mean_count > 0 else 1.0

        # Convert to 0-1 scale (higher is better)
        balance_score = 1.0 - (variance / max_variance) if max_variance > 0 else 1.0
        return max(0.0, balance_score)

    def _detect_duplicates(
        self, session: Session, guardian_analyses: List[Dict[str, Any]]
    ) -> List[DuplicateDetection]:
        """Detect duplicate work across agents using LLM analysis."""
        duplicates = []

        if len(guardian_analyses) < 2:
            return duplicates

        # Compare each pair of agents
        for i, analysis1 in enumerate(guardian_analyses):
            for j, analysis2 in enumerate(guardian_analyses[i + 1 :], i + 1):
                duplicate = self._analyze_pair_for_duplicates(analysis1, analysis2)
                if duplicate and duplicate.similarity_score > 0.7:
                    duplicates.append(duplicate)

        return duplicates

    def _analyze_pair_for_duplicates(
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
            duplicate_analysis = self._llm_duplicate_analysis(
                focus1, summary1, focus2, summary2, phase1
            )

            if duplicate_analysis and duplicate_analysis.get("is_duplicate", False):
                return DuplicateDetection(
                    agent1_id=analysis1["agent_id"],
                    agent2_id=analysis2["agent_id"],
                    similarity_score=duplicate_analysis.get("similarity_score", 0.0),
                    work_description=duplicate_analysis.get("work_description", ""),
                    resources=duplicate_analysis.get("resources", {}),
                    confidence=duplicate_analysis.get("confidence", 0.0),
                )

        except Exception as e:
            logger.error(f"Failed to analyze pair for duplicates: {e}")

        return None

    def _llm_duplicate_analysis(
        self,
        focus1: str,
        summary1: str,
        focus2: str,
        summary2: str,
        phase: str,
    ) -> Optional[Dict[str, Any]]:
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

            Return a JSON analysis with:
            - is_duplicate (boolean): True if working on essentially the same task
            - similarity_score (0-1): How similar their work is
            - work_description (string): Description of the duplicate work
            - confidence (0-1): How confident you are in this assessment
            - resources (object): Key resources they might be conflicting over
            """

            response = self.llm_service.ainvoke(prompt)
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
            recommendations.append("System coherence is critically low - requires immediate attention")
            recommendations.append("Consider reducing concurrent agents or improving task coordination")

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
            recommendations.append("System coherence is excellent - current patterns are working well")

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
        """Store conductor analysis in database."""
        analysis_id = uuid.uuid4()

        query = text("""
            INSERT INTO conductor_analyses (
                id, cycle_id, coherence_score, system_status, num_agents,
                duplicate_count, termination_count, coordination_count, details, created_at, updated_at
            ) VALUES (
                :id, :cycle_id, :coherence_score, :system_status, :num_agents,
                :duplicate_count, :termination_count, :coordination_count, :details, :created_at, :updated_at
            )
        """)

        session.execute(
            query,
            {
                "id": analysis_id,
                "cycle_id": cycle_id,
                "coherence_score": coherence_score,
                "system_status": system_status,
                "num_agents": num_agents,
                "duplicate_count": duplicate_count,
                "termination_count": termination_count,
                "coordination_count": coordination_count,
                "details": details,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            },
        )

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
        """Store detected duplicate in database."""
        duplicate_id = uuid.uuid4()

        query = text("""
            INSERT INTO detected_duplicates (
                id, conductor_analysis_id, agent1_id, agent2_id, similarity_score,
                work_description, resources, created_at
            ) VALUES (
                :id, :conductor_analysis_id, :agent1_id, :agent2_id, :similarity_score,
                :work_description, :resources, :created_at
            )
        """)

        session.execute(
            query,
            {
                "id": duplicate_id,
                "conductor_analysis_id": conductor_analysis_id,
                "agent1_id": agent1_id,
                "agent2_id": agent2_id,
                "similarity_score": similarity_score,
                "work_description": work_description,
                "resources": resources,
                "created_at": utc_now(),
            },
        )

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
                recent_analysis = dict(result.fetchone()._mapping) if result.fetchone() else None

                # Get active agent count
                active_count = len(self._get_active_agents(session))

                # Get recent duplicate count
                query = text("""
                    SELECT COUNT(*) as count
                    FROM detected_duplicates
                    WHERE created_at > :cutoff
                """)
                result = session.execute(query, {"cutoff": utc_now() - timedelta(hours=1)})
                recent_duplicates = result.fetchone().count

                # Get average coherence over last hour
                query = text("""
                    SELECT AVG(coherence_score) as avg_score
                    FROM conductor_analyses
                    WHERE created_at > :cutoff
                """)
                result = session.execute(query, {"cutoff": utc_now() - timedelta(hours=1)})
                avg_coherence = result.fetchone().avg_score or 0.0

                return {
                    "current_status": recent_analysis.get("system_status") if recent_analysis else "unknown",
                    "current_coherence": recent_analysis.get("coherence_score") if recent_analysis else 0.0,
                    "average_coherence_1h": avg_coherence,
                    "active_agents": active_count,
                    "recent_duplicates": recent_duplicates,
                    "last_analysis": recent_analysis.get("created_at") if recent_analysis else None,
                }

        except Exception as e:
            logger.error(f"Failed to get system health summary: {e}")
            return {"error": str(e), "status": "error"}

    # Pydantic model response methods
    def analyze_system_coherence_response(
        self,
        cycle_id: Optional[uuid.UUID] = None,
    ) -> SystemCoherenceResponse:
        """Analyze system coherence and return Pydantic response model."""
        analysis = self.analyze_system_coherence(cycle_id)

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
            # Get phase distribution
            active_agents = self._get_active_agents(session)
            phase_distribution = {}
            steering_types = {}

            for agent in active_agents:
                phase = agent.phase_id or "unknown"
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