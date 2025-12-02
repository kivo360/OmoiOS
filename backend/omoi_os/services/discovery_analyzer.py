"""LLM-Powered Discovery Analyzer for OmoiOS.

This service uses fast LLMs to analyze patterns in discoveries and provide
intelligent insights about workflow health, common issues, and optimization
opportunities.

The analyzer:
1. Identifies patterns across discoveries (recurring bugs, blockers)
2. Suggests priority adjustments based on discovery patterns
3. Predicts potential blockers based on similar past discoveries
4. Recommends agent assignments based on discovery context
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import timedelta

from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from omoi_os.models.task_discovery import DiscoveryType, TaskDiscovery
from omoi_os.models.task import Task
from omoi_os.services.llm_service import LLMService, get_llm_service
from omoi_os.utils.datetime import utc_now

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models for Structured LLM Output
# =============================================================================


class DiscoveryPattern(BaseModel):
    """A discovered pattern across multiple discoveries."""

    pattern_type: str = Field(
        description="Type of pattern (recurring_bug, blocker_chain, optimization_opportunity)"
    )
    description: str = Field(description="Description of the pattern")
    severity: str = Field(description="Pattern severity (low, medium, high, critical)")
    affected_components: List[str] = Field(
        default_factory=list, description="Components affected by this pattern"
    )
    suggested_action: str = Field(
        description="Recommended action to address this pattern"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in this pattern (0-1)"
    )


class PatternAnalysisResult(BaseModel):
    """Result of pattern analysis across discoveries."""

    patterns: List[DiscoveryPattern] = Field(
        default_factory=list, description="Discovered patterns"
    )
    summary: str = Field(description="High-level summary of the analysis")
    health_score: float = Field(
        ge=0.0, le=1.0, description="Overall workflow health score (0-1)"
    )
    priority_recommendations: Dict[str, str] = Field(
        default_factory=dict, description="Task ID -> recommended priority"
    )
    hotspots: List[str] = Field(
        default_factory=list, description="Components with most issues"
    )


class BlockerPrediction(BaseModel):
    """Prediction of potential blockers."""

    likely_blockers: List[str] = Field(
        description="Likely issues that may block progress"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in predictions")
    prevention_suggestions: List[str] = Field(
        description="Suggestions to prevent blockers"
    )
    similar_past_discoveries: List[str] = Field(
        description="IDs of similar past discoveries"
    )


class AgentRecommendation(BaseModel):
    """Recommendation for agent assignment."""

    recommended_agent_type: str = Field(
        description="Recommended agent type (planner, implementer, validator, diagnostician)"
    )
    reasoning: str = Field(description="Why this agent type is recommended")
    alternative_types: List[str] = Field(
        default_factory=list, description="Alternative agent types"
    )
    special_instructions: str = Field(
        default="", description="Special instructions for the agent"
    )


# =============================================================================
# Discovery Analyzer Service
# =============================================================================


class DiscoveryAnalyzerService:
    """LLM-powered analysis of discoveries for pattern detection and insights.

    Uses fast LLMs (not traditional ML) to analyze discoveries in real-time
    and provide actionable insights for workflow optimization.

    Usage:
        analyzer = DiscoveryAnalyzerService()

        # Analyze patterns across recent discoveries
        patterns = await analyzer.analyze_patterns(session, ticket_id="ticket-123")

        # Predict potential blockers
        blockers = await analyzer.predict_blockers(session, task_id="task-456")

        # Get agent recommendation for a discovery
        rec = await analyzer.recommend_agent(session, discovery_id="disc-789")
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """Initialize the analyzer.

        Args:
            llm_service: LLM service for structured outputs (uses fast models)
        """
        self.llm = llm_service or get_llm_service()

    async def analyze_patterns(
        self,
        session: Session,
        ticket_id: Optional[str] = None,
        hours_back: int = 24,
        min_discoveries: int = 3,
    ) -> PatternAnalysisResult:
        """Analyze patterns across recent discoveries.

        Args:
            session: Database session
            ticket_id: Optional ticket to focus analysis on
            hours_back: How far back to look for discoveries
            min_discoveries: Minimum discoveries needed for analysis

        Returns:
            PatternAnalysisResult with patterns and recommendations
        """
        # Fetch recent discoveries
        cutoff = utc_now() - timedelta(hours=hours_back)

        query = select(TaskDiscovery).where(TaskDiscovery.discovered_at >= cutoff)
        if ticket_id:
            # Join with tasks to filter by ticket
            query = query.join(Task, TaskDiscovery.source_task_id == Task.id).where(
                Task.ticket_id == ticket_id
            )
        query = query.order_by(TaskDiscovery.discovered_at.desc()).limit(100)

        discoveries = list(session.execute(query).scalars().all())

        if len(discoveries) < min_discoveries:
            return PatternAnalysisResult(
                patterns=[],
                summary=f"Not enough discoveries to analyze (found {len(discoveries)}, need {min_discoveries})",
                health_score=1.0,
                priority_recommendations={},
                hotspots=[],
            )

        # Build context for LLM
        discovery_summaries = []
        for d in discoveries:
            discovery_summaries.append(
                {
                    "id": str(d.id),
                    "type": d.discovery_type,
                    "description": d.description[:200] if d.description else "",
                    "priority_boost": d.priority_boost,
                    "resolution_status": d.resolution_status,
                    "spawned_count": len(d.spawned_task_ids)
                    if d.spawned_task_ids
                    else 0,
                }
            )

        prompt = f"""Analyze these {len(discoveries)} workflow discoveries and identify patterns:

DISCOVERIES:
{_format_discoveries(discovery_summaries)}

ANALYSIS TASK:
1. Identify recurring patterns (similar bugs, repeated blockers, optimization themes)
2. Assess overall workflow health (are there systemic issues?)
3. Identify hotspot components (which areas have the most issues?)
4. Recommend priority adjustments if needed
5. Calculate a health score (1.0 = healthy, 0.0 = critical issues)

Focus on actionable insights that can improve workflow efficiency."""

        system_prompt = """You are an expert workflow analyst. Analyze discovery patterns to:
- Find recurring issues that indicate systemic problems
- Identify components that need attention
- Recommend priority changes to optimize workflow
- Provide a health assessment

Be specific and actionable. Focus on patterns, not individual discoveries."""

        try:
            result = await self.llm.structured_output(
                prompt=prompt,
                output_type=PatternAnalysisResult,
                system_prompt=system_prompt,
                output_retries=3,
            )
            return result
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            return PatternAnalysisResult(
                patterns=[],
                summary=f"Analysis failed: {str(e)}",
                health_score=0.5,
                priority_recommendations={},
                hotspots=[],
            )

    async def predict_blockers(
        self,
        session: Session,
        task_id: str,
        context_window: int = 10,
    ) -> BlockerPrediction:
        """Predict potential blockers for a task based on similar past discoveries.

        Args:
            session: Database session
            task_id: Task to predict blockers for
            context_window: Number of past discoveries to consider

        Returns:
            BlockerPrediction with likely blockers and prevention suggestions
        """
        # Get task info
        task = session.get(Task, task_id)
        if not task:
            return BlockerPrediction(
                likely_blockers=["Task not found"],
                confidence=0.0,
                prevention_suggestions=[],
                similar_past_discoveries=[],
            )

        # Get similar past discoveries (same phase, similar description)
        query = (
            select(TaskDiscovery)
            .join(Task, TaskDiscovery.source_task_id == Task.id)
            .where(Task.phase_id == task.phase_id)
            .where(
                TaskDiscovery.discovery_type.in_(
                    [
                        DiscoveryType.BUG_FOUND,
                        DiscoveryType.BLOCKER_IDENTIFIED,
                        DiscoveryType.MISSING_DEPENDENCY,
                    ]
                )
            )
            .order_by(TaskDiscovery.discovered_at.desc())
            .limit(context_window)
        )

        past_discoveries = list(session.execute(query).scalars().all())

        if not past_discoveries:
            return BlockerPrediction(
                likely_blockers=[],
                confidence=0.3,
                prevention_suggestions=["No historical data - monitor closely"],
                similar_past_discoveries=[],
            )

        # Build context
        discovery_context = [
            {
                "id": str(d.id),
                "type": d.discovery_type,
                "description": d.description[:150] if d.description else "",
            }
            for d in past_discoveries
        ]

        prompt = f"""Based on historical discoveries for similar tasks, predict potential blockers.

CURRENT TASK:
- Phase: {task.phase_id}
- Description: {task.description[:200] if task.description else "No description"}

SIMILAR PAST DISCOVERIES:
{_format_discoveries(discovery_context)}

PREDICTION TASK:
1. What blockers are likely to occur based on this pattern?
2. How confident are you in these predictions?
3. What can be done to prevent these blockers?
4. Which past discoveries are most relevant?"""

        system_prompt = """You are a predictive workflow analyst. Based on historical patterns,
predict likely blockers for the current task. Be specific about:
- What issues are likely to occur
- Why they're likely (based on patterns)
- How to prevent them proactively

Be realistic - only predict blockers that have clear historical precedent."""

        try:
            result = await self.llm.structured_output(
                prompt=prompt,
                output_type=BlockerPrediction,
                system_prompt=system_prompt,
                output_retries=2,
            )
            return result
        except Exception as e:
            logger.error(f"Blocker prediction failed: {e}")
            return BlockerPrediction(
                likely_blockers=[f"Prediction failed: {str(e)}"],
                confidence=0.0,
                prevention_suggestions=[],
                similar_past_discoveries=[],
            )

    async def recommend_agent(
        self,
        session: Session,
        discovery_id: Optional[str] = None,
        task_id: Optional[str] = None,
        discovery_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> AgentRecommendation:
        """Recommend the best agent type to handle a discovery or task.

        Args:
            session: Database session
            discovery_id: Discovery to recommend agent for
            task_id: Or task to recommend agent for
            discovery_type: Discovery type (if not using discovery_id)
            description: Description (if not using discovery_id)

        Returns:
            AgentRecommendation with agent type and reasoning
        """
        context = ""

        if discovery_id:
            discovery = session.get(TaskDiscovery, discovery_id)
            if discovery:
                context = f"""
DISCOVERY:
- Type: {discovery.discovery_type}
- Description: {discovery.description}
- Priority Boost: {discovery.priority_boost}
"""
        elif task_id:
            task = session.get(Task, task_id)
            if task:
                context = f"""
TASK:
- Phase: {task.phase_id}
- Type: {task.task_type}
- Description: {task.description}
- Priority: {task.priority}
"""
        else:
            context = f"""
DISCOVERY:
- Type: {discovery_type or "unknown"}
- Description: {description or "No description"}
"""

        prompt = f"""{context}

AVAILABLE AGENT TYPES:
1. planner - Analyzes requirements, creates tasks, read-only access
2. implementer - Writes code, full file access, runs tests
3. validator - Reviews code, runs tests, spawns fix tasks
4. diagnostician - Analyzes stuck workflows, spawns recovery tasks
5. coordinator - Orchestrates workflows, manages agents

Which agent type is best suited to handle this? Explain why."""

        system_prompt = """You are an expert at matching work to agent capabilities.
Consider:
- What kind of work needs to be done
- What capabilities are required
- What phase the work is in
- Any special considerations

Always recommend the most appropriate agent type with clear reasoning."""

        try:
            result = await self.llm.structured_output(
                prompt=prompt,
                output_type=AgentRecommendation,
                system_prompt=system_prompt,
                output_retries=2,
            )
            return result
        except Exception as e:
            logger.error(f"Agent recommendation failed: {e}")
            return AgentRecommendation(
                recommended_agent_type="implementer",
                reasoning=f"Default recommendation (analysis failed: {str(e)})",
                alternative_types=["validator", "planner"],
                special_instructions="",
            )

    async def summarize_workflow_health(
        self,
        session: Session,
        ticket_id: str,
    ) -> Dict[str, Any]:
        """Get a comprehensive health summary for a workflow.

        Args:
            session: Database session
            ticket_id: Ticket/workflow to analyze

        Returns:
            Dictionary with health metrics and recommendations
        """
        # Get discovery counts by type
        type_counts = dict(
            session.execute(
                select(TaskDiscovery.discovery_type, func.count(TaskDiscovery.id))
                .join(Task, TaskDiscovery.source_task_id == Task.id)
                .where(Task.ticket_id == ticket_id)
                .group_by(TaskDiscovery.discovery_type)
            ).all()
        )

        # Get resolution stats
        resolution_counts = dict(
            session.execute(
                select(TaskDiscovery.resolution_status, func.count(TaskDiscovery.id))
                .join(Task, TaskDiscovery.source_task_id == Task.id)
                .where(Task.ticket_id == ticket_id)
                .group_by(TaskDiscovery.resolution_status)
            ).all()
        )

        # Get task status breakdown
        task_counts = dict(
            session.execute(
                select(Task.status, func.count(Task.id))
                .where(Task.ticket_id == ticket_id)
                .group_by(Task.status)
            ).all()
        )

        # Calculate metrics
        total_discoveries = sum(type_counts.values())
        open_discoveries = resolution_counts.get("open", 0)
        bug_count = type_counts.get(DiscoveryType.BUG_FOUND, 0)
        blocker_count = type_counts.get(DiscoveryType.BLOCKER_IDENTIFIED, 0)

        # Run pattern analysis
        patterns = await self.analyze_patterns(session, ticket_id=ticket_id)

        return {
            "ticket_id": ticket_id,
            "total_discoveries": total_discoveries,
            "open_discoveries": open_discoveries,
            "resolved_discoveries": resolution_counts.get("resolved", 0),
            "bugs_found": bug_count,
            "blockers_identified": blocker_count,
            "task_breakdown": task_counts,
            "health_score": patterns.health_score,
            "patterns": [p.model_dump() for p in patterns.patterns],
            "hotspots": patterns.hotspots,
            "summary": patterns.summary,
            "priority_recommendations": patterns.priority_recommendations,
        }


def _format_discoveries(discoveries: List[Dict[str, Any]]) -> str:
    """Format discoveries for LLM prompt."""
    lines = []
    for i, d in enumerate(discoveries, 1):
        lines.append(
            f"{i}. [{d.get('type', 'unknown')}] {d.get('description', 'No description')}"
        )
        if d.get("priority_boost"):
            lines.append("   (PRIORITY BOOST)")
        if d.get("spawned_count", 0) > 0:
            lines.append(f"   (spawned {d['spawned_count']} tasks)")
    return "\n".join(lines)


# Global singleton
_analyzer_service: Optional[DiscoveryAnalyzerService] = None


def get_discovery_analyzer(
    llm_service: Optional[LLMService] = None,
) -> DiscoveryAnalyzerService:
    """Get or create the global discovery analyzer service."""
    global _analyzer_service

    if _analyzer_service is None:
        _analyzer_service = DiscoveryAnalyzerService(llm_service)

    return _analyzer_service
