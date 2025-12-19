"""Trajectory context management for accumulated agent understanding.

This class implements the core concept from trajectory thinking:
- Build accumulated understanding from entire conversation
- Track constraints that persist until lifted
- Resolve references like "this/that"
- Understand the complete journey, not just current state
"""

import re
from collections import defaultdict
from datetime import timedelta
from typing import Dict, Any, List, Optional, Tuple

from omoi_os.logging import get_logger
from omoi_os.models.agent import Agent
from omoi_os.utils.datetime import utc_now
from omoi_os.models.agent_log import AgentLog
from omoi_os.models.sandbox_event import SandboxEvent
from omoi_os.models.task import Task
from omoi_os.models.trajectory_analysis import (
    ConversationEvent,
    PersistentConstraint,
    AccumulatedContext,
    TrajectoryContext as TrajectoryContextModel,
)
from omoi_os.services.database import DatabaseService

logger = get_logger(__name__)


class TrajectoryContext:
    """
    Manages accumulated context for agents using trajectory thinking.

    This class implements the core concept from trajectory thinking:
    - Build accumulated understanding from entire conversation
    - Track constraints that persist until lifted
    - Resolve references like "this/that"
    - Understand the complete journey, not just current state
    """

    def __init__(self, db: DatabaseService):
        """Initialize TrajectoryContext manager.

        Args:
            db: Database service for accessing agent logs
        """
        self.db = db

        # Cache for performance
        self.context_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = timedelta(minutes=5)

    def build_accumulated_context(
        self,
        agent_id: str,
        include_full_history: bool = True,
    ) -> Dict[str, Any]:
        """
        Build complete accumulated context for an agent.

        This is the core method that builds understanding from the ENTIRE
        conversation, not just recent messages.

        Args:
            agent_id: Agent ID to build context for
            include_full_history: Whether to include full conversation history

        Returns:
            Complete accumulated context including goals, constraints, references
        """
        logger.debug(f"Building accumulated context for agent {agent_id}")

        # Check cache first
        if agent_id in self.context_cache:
            cached = self.context_cache[agent_id]
            if cached["timestamp"] > utc_now() - self.cache_ttl:
                return cached["context"]

        with self.db.get_session() as session:
            # Get all logs for complete understanding
            logs = (
                session.query(AgentLog)
                .filter_by(agent_id=agent_id)
                .order_by(AgentLog.created_at)
                .all()
            )

            if not logs:
                logger.warning(f"No logs found for agent {agent_id}")
                return self._get_empty_context()

            # Get agent and task for initial context
            agent = session.query(Agent).filter_by(id=agent_id).first()
            task = None
            if agent:
                # Get current running task assigned to this agent
                task = (
                    session.query(Task)
                    .filter_by(assigned_agent_id=str(agent.id), status="running")
                    .first()
                )

            # Build conversation history
            conversation = self._build_conversation_history(logs, include_full_history)

            # Extract accumulated understanding
            context = {
                # Core trajectory elements
                "overall_goal": self._extract_overall_goal(conversation, task),
                "evolved_goals": self._track_goal_evolution(conversation),
                "constraints": self._extract_persistent_constraints(conversation),
                "lifted_constraints": self._identify_lifted_constraints(conversation),
                "standing_instructions": self._extract_standing_instructions(
                    conversation
                ),
                # Reference resolution
                "references": self._resolve_references(conversation),
                "context_markers": self._extract_context_markers(conversation),
                # Journey tracking
                "phases_completed": self._identify_completed_phases(conversation),
                "current_focus": self._determine_current_focus(conversation),
                "attempted_approaches": self._extract_attempted_approaches(
                    conversation
                ),
                "discovered_blockers": self._find_discovered_blockers(conversation),
                # Meta information
                "conversation_length": len(conversation),
                "session_duration": self._calculate_session_duration(logs),
                "last_activity": logs[-1].created_at if logs else utc_now(),
                "agent_id": agent_id,
                "agent_type": agent.agent_type if agent else "unknown",
                "agent_status": agent.status if agent else "unknown",
            }

            # Add task-specific context
            if task:
                context["task_id"] = task.id
                context["task_description"] = (
                    task.enriched_description or task.raw_description
                )
                context["done_definition"] = task.done_definition
                context["task_complexity"] = task.estimated_complexity or 5
                context["task_status"] = task.status
                context["phase_id"] = task.phase_id

            # Convert to Pydantic models
            accumulated_context = AccumulatedContext(
                agent_id=agent_id,
                context_summary=context.get("overall_goal", ""),
                persistent_constraints=[
                    PersistentConstraint(
                        constraint_type=constraint.get("type", "general"),
                        description=constraint.get("description", ""),
                        source=constraint.get("source", "conversation"),
                        strength=constraint.get("strength", 1.0),
                        created_at=utc_now(),  # Would need actual timestamp from constraint
                    )
                    for constraint in context.get("constraints", [])
                ],
                session_duration=context.get("session_duration"),
                conversation_events=[
                    ConversationEvent(
                        id=log.id or "unknown",  # AgentLog might not have UUID
                        agent_id=agent_id,
                        event_type=log.log_type,
                        content=log.message,
                        timestamp=log.created_at,
                        metadata=log.details or {},
                    )
                    for log in logs[-20:]  # Last 20 events as conversation events
                ],
                task_completion_rate=self._calculate_completion_rate(context, task),
                last_updated=utc_now(),
            )

            trajectory_context = TrajectoryContextModel(
                accumulated_context=accumulated_context,
                current_phase=context.get("phase_id", "unknown"),
                current_focus=context.get("current_focus", "Unknown"),
                accumulated_goal=context.get("overall_goal"),
                conversation_length=context.get("conversation_length", 0),
                session_duration=context.get("session_duration"),
                last_claude_message_marker=self._find_last_claude_marker(context),
            )

            # Cache the context (still store dict for cache)
            self.context_cache[agent_id] = {
                "context": context,
                "timestamp": utc_now(),
            }

            return trajectory_context.model_dump()

    def _build_conversation_history(
        self,
        logs: List[AgentLog],
        include_full: bool,
    ) -> List[Dict[str, Any]]:
        """Build structured conversation history from logs."""
        conversation = []

        for log in logs:
            entry = {
                "type": log.log_type,
                "content": log.message,
                "timestamp": log.created_at,
                "details": log.details or {},
            }

            # Add to conversation based on log type
            if log.log_type in [
                "input",
                "output",
                "message",
                "steering",
                "intervention",
            ]:
                conversation.append(entry)
            elif log.log_type == "steering":
                # Include steering as it affects trajectory
                conversation.append(
                    {
                        **entry,
                        "steering_type": log.details.get("type", "unknown"),
                    }
                )

        # Limit history if requested (but keep key messages)
        if not include_full and len(conversation) > 200:
            # Keep first 50, last 100, and all interventions
            important = conversation[:50]
            recent = conversation[-100:]
            interventions = [
                c for c in conversation[50:-100] if c.get("intervention_type")
            ]

            conversation = important + interventions + recent
            logger.debug(
                f"Limited conversation from {len(logs)} to {len(conversation)} entries"
            )

        return conversation

    def _extract_overall_goal(
        self,
        conversation: List[Dict[str, Any]],
        task: Optional[Task],
    ) -> str:
        """Extract the overall accumulated goal from conversation."""
        # Start with task description if available
        if task:
            base_goal = task.enriched_description or task.raw_description
        else:
            base_goal = "Complete assigned task"

        # Look for goal refinements in conversation
        goal_patterns = [
            r"(?:the goal is|we need to|task is to|objective:)\s*(.+?)(?:\.|$)",
            r"(?:implement|create|build|fix|add|update)\s+(.+?)(?:\.|$)",
            r"(?:working on|focused on|trying to)\s+(.+?)(?:\.|$)",
        ]

        refined_goals = []
        for entry in conversation:
            content_lower = entry["content"].lower()
            for pattern in goal_patterns:
                matches = re.findall(pattern, content_lower, re.IGNORECASE)
                refined_goals.extend(matches)

        # Find most recent significant goal statement
        if refined_goals and len(refined_goals) > 0:
            # Use the most detailed recent goal
            recent_goal = (
                max(refined_goals[-5:], key=len) if refined_goals else base_goal
            )
            if len(recent_goal) > len(base_goal) * 0.5:  # If it's substantial enough
                return recent_goal.strip().capitalize()

        return base_goal

    def _track_goal_evolution(self, conversation: List[Dict[str, Any]]) -> List[str]:
        """Track how the goal evolved over the conversation."""
        goals = []

        # Patterns that indicate goal evolution
        evolution_patterns = [
            r"(?:now|next|then) (?:we need to|let's|I'll)\s+(.+?)(?:\.|$)",
            r"(?:actually|instead|rather),?\s+(?:we should|let's)\s+(.+?)(?:\.|$)",
            r"(?:changing|switching|pivoting) (?:to|towards?)\s+(.+?)(?:\.|$)",
        ]

        for entry in conversation:
            for pattern in evolution_patterns:
                matches = re.findall(pattern, entry["content"], re.IGNORECASE)
                for match in matches:
                    if match and len(match) > 20:  # Substantial goal statement
                        goals.append(match.strip())

        return goals[-5:] if goals else []  # Keep last 5 goal evolutions

    def _extract_persistent_constraints(
        self,
        conversation: List[Dict[str, Any]],
    ) -> List[str]:
        """Extract constraints that persist until explicitly lifted."""
        constraints = []

        # Patterns for constraint detection
        constraint_patterns = [
            r"(?:don't|do not|never|avoid|without)\s+(.+?)(?:\.|$)",
            r"(?:only use|must use|should use)\s+(.+?)(?:\.|$)",
            r"(?:keep|make sure|ensure)\s+(?:it's|it is|things? are)\s+(.+?)(?:\.|$)",
            r"(?:constraint:|requirement:|rule:)\s*(.+?)(?:\.|$)",
        ]

        for entry in conversation:
            content = entry["content"]
            for pattern in constraint_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Clean and normalize constraint
                    constraint = match.strip().lower()
                    if len(constraint) > 10 and constraint not in constraints:
                        constraints.append(constraint)

        # Filter out lifted constraints
        lifted = self._identify_lifted_constraints(conversation)
        active_constraints = [c for c in constraints if c not in lifted]

        return active_constraints[:10]  # Keep top 10 most relevant

    def _identify_lifted_constraints(
        self,
        conversation: List[Dict[str, Any]],
    ) -> List[str]:
        """Identify constraints that have been explicitly lifted."""
        lifted = []

        # Patterns for lifted constraints
        lift_patterns = [
            r"(?:you can now|feel free to|go ahead and)\s+(.+?)(?:\.|$)",
            r"(?:constraint lifted:|no longer need to:|don't worry about)\s+(.+?)(?:\.|$)",
            r"(?:ignore|disregard) (?:the )? (?:previous )?(?:constraint|rule) (?:about )?\s+(.+?)(?:\.|$)",
        ]

        for entry in conversation:
            for pattern in lift_patterns:
                matches = re.findall(pattern, entry["content"], re.IGNORECASE)
                lifted.extend([m.strip().lower() for m in matches])

        return lifted

    def _extract_standing_instructions(
        self,
        conversation: List[Dict[str, Any]],
    ) -> List[str]:
        """Extract standing instructions that apply throughout."""
        instructions = []

        instruction_patterns = [
            r"(?:always|make sure to|remember to)\s+(.+?)(?:\.|$)",
            r"(?:for all|throughout|during)\s+(?:this task|the implementation),?\s+(.+?)(?:\.|$)",
            r"(?:important:|note:|remember:)\s*(.+?)(?:\.|$)",
        ]

        for entry in conversation[:20]:  # Focus on early instructions
            for pattern in instruction_patterns:
                matches = re.findall(pattern, entry["content"], re.IGNORECASE)
                for match in matches:
                    instruction = match.strip()
                    if len(instruction) > 15 and instruction not in instructions:
                        instructions.append(instruction)

        return instructions[:5]  # Keep top 5 standing instructions

    def _resolve_references(
        self,
        conversation: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Resolve 'this/that/it' references from conversation context."""
        references = {}

        # Track recent nouns/concepts that could be referenced
        recent_concepts = []

        for i, entry in enumerate(conversation):
            content = entry["content"]

            # Extract potential reference targets (nouns, files, functions, etc.)
            concept_patterns = [
                r"(?:file|function|class|module|component|feature|bug|error|issue)\s+called\s+(\S+)",
                r"(?:the|a)\s+(\w+\.(?:py|js|ts|tsx|jsx|java|go|rs|cpp|c|h))",
                r"(?:implement|create|fix|update|modify)\s+(?:the\s+)?(\w+(?:\s+\w+)?)",
            ]

            for pattern in concept_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                recent_concepts.extend(matches)

            # Keep only last 10 concepts
            recent_concepts = recent_concepts[-10:]

            # Look for reference usage and resolve
            ref_patterns = [
                r"\b(this|that|it)\s+(.+?)(?:\.|,|$)",
                r"(?:do|implement|fix|update)\s+(this|that|it)\b",
            ]

            for pattern in ref_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    ref_word = match[0] if isinstance(match, tuple) else match
                    # Resolve to most recent concept
                    if recent_concepts:
                        references[f"{ref_word}_{i}"] = recent_concepts[-1]

        return references

    def _extract_context_markers(
        self,
        conversation: List[Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        """Extract important context markers from conversation."""
        markers = defaultdict(list)

        # Different types of context markers
        marker_patterns = {
            "decisions": r"(?:decided to|chose|selected|going with)\s+(.+?)(?:\.|$)",
            "discoveries": r"(?:found|discovered|realized|noticed)\s+(?:that\s+)?(.+?)(?:\.|$)",
            "blockers": r"(?:blocked by|stuck on|can't|cannot)\s+(.+?)(?:\.|$)",
            "completions": r"(?:completed|finished|done with)\s+(.+?)(?:\.|$)",
        }

        for entry in conversation:
            for marker_type, pattern in marker_patterns.items():
                matches = re.findall(pattern, entry["content"], re.IGNORECASE)
                for match in matches:
                    if len(match) > 10:  # Meaningful marker
                        markers[marker_type].append(match.strip())

        # Limit each type to most recent/relevant
        for marker_type in markers:
            markers[marker_type] = markers[marker_type][-5:]

        return dict(markers)

    def _identify_completed_phases(
        self,
        conversation: List[Dict[str, Any]],
    ) -> List[str]:
        """Identify which phases have been completed."""
        completed = []

        completion_patterns = [
            r"(?:completed|finished|done)\s+(?:the\s+)?(\w+(?:\s+\w+)?)\s+phase",
            r"(\w+(?:\s+\w+)?)\s+phase\s+(?:is\s+)?(?:complete|done|finished)",
            r"(?:exploration|planning|implementation|testing|verification)\s+(?:is\s+)?(?:complete|done)",
        ]

        for entry in conversation:
            for pattern in completion_patterns:
                matches = re.findall(pattern, entry["content"], re.IGNORECASE)
                for match in matches:
                    phase = match.strip().lower()
                    if phase and phase not in completed:
                        completed.append(phase)

        return completed

    def _determine_current_focus(
        self,
        conversation: List[Dict[str, Any]],
    ) -> str:
        """Determine current focus from recent conversation."""
        if not conversation:
            return "initializing"

        # Look at last 10 messages for current focus
        recent = conversation[-10:] if len(conversation) > 10 else conversation

        focus_keywords = {
            "exploring": ["reading", "examining", "looking at", "exploring"],
            "implementing": ["creating", "writing", "implementing", "coding"],
            "debugging": ["error", "bug", "issue", "problem", "fixing"],
            "testing": ["test", "verify", "check", "validate"],
            "planning": ["plan", "approach", "design", "architect"],
        }

        # Count occurrences in recent messages
        focus_scores = defaultdict(int)
        for entry in recent:
            content_lower = entry["content"].lower()
            for focus, keywords in focus_keywords.items():
                for keyword in keywords:
                    if keyword in content_lower:
                        focus_scores[focus] += 1

        # Return highest scoring focus
        if focus_scores:
            return max(focus_scores, key=focus_scores.get)

        return "working"

    def _extract_attempted_approaches(
        self,
        conversation: List[Dict[str, Any]],
    ) -> List[str]:
        """Extract approaches that have been attempted."""
        approaches = []

        approach_patterns = [
            r"(?:trying|attempting|going to try)\s+(.+?)(?:\.|$)",
            r"(?:approach:|strategy:|plan:)\s*(.+?)(?:\.|$)",
            r"(?:let me|I'll|I will)\s+(.+?)(?:\.|$)",
        ]

        for entry in conversation:
            for pattern in approach_patterns:
                matches = re.findall(pattern, entry["content"], re.IGNORECASE)
                for match in matches:
                    if len(match) > 20:  # Substantial approach description
                        approaches.append(match.strip())

        return approaches[-10:] if approaches else []  # Last 10 approaches

    def _find_discovered_blockers(
        self,
        conversation: List[Dict[str, Any]],
    ) -> List[str]:
        """Find blockers discovered during the conversation."""
        blockers = []

        blocker_patterns = [
            r"(?:blocked by|stuck on|waiting for)\s+(.+?)(?:\.|$)",
            r"(?:can't|cannot|unable to)\s+(.+?)(?:\.|$)",
            r"(?:error:|issue:|problem:)\s*(.+?)(?:\.|$)",
        ]

        for entry in conversation:
            for pattern in blocker_patterns:
                matches = re.findall(pattern, entry["content"], re.IGNORECASE)
                for match in matches:
                    blocker = match.strip()
                    if len(blocker) > 10 and blocker not in blockers:
                        blockers.append(blocker)

        return blockers[:10]  # Top 10 blockers

    def _calculate_session_duration(self, logs: List[AgentLog]) -> timedelta:
        """Calculate total session duration."""
        if not logs:
            return timedelta(0)

        first_log = logs[0]
        last_log = logs[-1]
        return last_log.created_at - first_log.created_at

    def _get_empty_context(self) -> Dict[str, Any]:
        """Get empty context structure."""
        return {
            "overall_goal": "Unknown",
            "evolved_goals": [],
            "constraints": [],
            "lifted_constraints": [],
            "standing_instructions": [],
            "references": {},
            "context_markers": {},
            "phases_completed": [],
            "current_focus": "initializing",
            "attempted_approaches": [],
            "discovered_blockers": [],
            "conversation_length": 0,
            "session_duration": timedelta(0),
            "last_activity": utc_now(),
            "agent_id": None,
            "agent_type": "unknown",
            "agent_status": "unknown",
        }

    def check_constraint_violations(
        self,
        action: str,
        constraints: List[str],
    ) -> Tuple[bool, List[str]]:
        """
        Check if an action violates any constraints.

        Args:
            action: The action being taken
            constraints: List of active constraints

        Returns:
            Tuple of (has_violations, list_of_violations)
        """
        violations = []
        action_lower = action.lower()

        for constraint in constraints:
            constraint_lower = constraint.lower()

            # Check for direct violations
            violation_checks = [
                ("no external" in constraint_lower and "pip install" in action_lower),
                ("no external" in constraint_lower and "npm install" in action_lower),
                (
                    "simple" in constraint_lower
                    and any(
                        term in action_lower
                        for term in ["factory", "abstract", "framework"]
                    )
                ),
                (
                    "don't write" in constraint_lower
                    and any(
                        term in action_lower
                        for term in ["creating", "writing", "implementing"]
                    )
                ),
                (
                    "avoid" in constraint_lower
                    and any(
                        avoided in action_lower
                        for avoided in constraint_lower.split("avoid")[1].split()
                    )
                ),
            ]

            if any(violation_checks):
                violations.append(constraint)

        return (len(violations) > 0, violations)

    def get_trajectory_summary(self, agent_id: str) -> str:
        """
        Get a concise trajectory summary for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Trajectory summary string
        """
        context = self.build_accumulated_context(agent_id, include_full_history=False)

        summary_parts = [
            f"Goal: {context['overall_goal'][:100]}",
            f"Focus: {context['current_focus']}",
            f"Duration: {str(context['session_duration']).split('.')[0]}",
        ]

        if context["constraints"]:
            summary_parts.append(f"Constraints: {len(context['constraints'])}")

        if context["discovered_blockers"]:
            summary_parts.append(f"Blockers: {len(context['discovered_blockers'])}")

        return " | ".join(summary_parts)

    def clear_cache(self, agent_id: Optional[str] = None):
        """Clear context cache."""
        if agent_id:
            if agent_id in self.context_cache:
                del self.context_cache[agent_id]
        else:
            self.context_cache.clear()

    # Helper methods for Pydantic model conversion
    def _calculate_completion_rate(
        self, context: Dict[str, Any], task: Optional[Task]
    ) -> float:
        """Calculate task completion rate from context."""
        if not task:
            return 0.0

        # Simple heuristic based on completed phases
        completed_phases = context.get("phases_completed", [])
        total_phases = 4  # Typical number of phases in OmoiOS

        return len(completed_phases) / max(total_phases, 1)

    def _find_last_claude_marker(self, context: Dict[str, Any]) -> Optional[str]:
        """Find the last Claude message marker."""
        context_markers = context.get("context_markers", {})

        # Look for recent Claude markers in various marker types
        for marker_type in ["decisions", "discoveries", "completions"]:
            markers = context_markers.get(marker_type, [])
            if markers:
                # Return the most recent marker
                return markers[-1]

        return None

    # -------------------------------------------------------------------------
    # Sandbox-Aware Methods (Phase 6)
    # -------------------------------------------------------------------------

    def get_sandbox_id_for_agent(self, agent_id: str) -> Optional[str]:
        """Get the sandbox_id for an agent/sandbox identifier.

        This method handles both cases:
        1. agent_id is actually a sandbox_id (from sandbox-aware monitoring)
        2. agent_id is a legacy agent_id with an associated sandbox task

        Args:
            agent_id: Agent ID or sandbox ID to look up

        Returns:
            sandbox_id if found, None otherwise
        """
        with self.db.get_session() as session:
            # First check if agent_id is itself a sandbox_id
            task = (
                session.query(Task)
                .filter(
                    Task.sandbox_id == agent_id,
                    Task.status.in_(["running", "assigned"]),
                )
                .first()
            )
            if task and task.sandbox_id:
                return task.sandbox_id

            # Fallback: check if it's a legacy agent with sandbox task
            task = (
                session.query(Task)
                .filter(
                    Task.assigned_agent_id == agent_id,
                    Task.sandbox_id.isnot(None),
                    Task.status.in_(["running", "assigned"]),
                )
                .first()
            )
            if task and task.sandbox_id:
                return task.sandbox_id

            return None

    def is_sandbox_agent(self, agent_id: str) -> bool:
        """Check if an agent is running in a sandbox.

        Args:
            agent_id: Agent ID to check

        Returns:
            True if agent has an associated sandbox_id
        """
        return self.get_sandbox_id_for_agent(agent_id) is not None

    def get_sandbox_events(
        self, sandbox_id: str, limit: int = 100
    ) -> List[SandboxEvent]:
        """Get sandbox events for trajectory analysis.

        Args:
            sandbox_id: Sandbox ID to query
            limit: Maximum number of events to return

        Returns:
            List of SandboxEvent objects ordered by created_at
        """
        with self.db.get_session() as session:
            events = (
                session.query(SandboxEvent)
                .filter(SandboxEvent.sandbox_id == sandbox_id)
                .order_by(SandboxEvent.created_at)
                .limit(limit)
                .all()
            )
            # Expunge to use outside session
            for event in events:
                session.expunge(event)
            return events

    def _convert_sandbox_events_to_logs(
        self, events: List[SandboxEvent], agent_id: str
    ) -> List[AgentLog]:
        """Convert SandboxEvents to AgentLog format for trajectory analysis.

        This bridges the gap between sandbox events and the existing
        trajectory analysis infrastructure.

        Args:
            events: List of SandboxEvent objects
            agent_id: Agent ID to associate with logs

        Returns:
            List of AgentLog-like objects (duck-typed for compatibility)
        """
        from dataclasses import dataclass

        @dataclass
        class PseudoAgentLog:
            """Duck-typed AgentLog for sandbox events."""
            id: str
            agent_id: str
            log_type: str
            message: str
            details: Optional[dict]
            created_at: Any

        logs = []
        for event in events:
            # Map sandbox event types to log types
            event_type = event.event_type or ""
            log_type = self._map_event_type_to_log_type(event_type)

            # Build message from event data
            event_data = event.event_data or {}
            message = self._build_message_from_event(event_type, event_data)

            logs.append(
                PseudoAgentLog(
                    id=event.id,
                    agent_id=agent_id,
                    log_type=log_type,
                    message=message,
                    details=event_data,
                    created_at=event.created_at,
                )
            )

        return logs

    def _map_event_type_to_log_type(self, event_type: str) -> str:
        """Map sandbox event types to AgentLog log types.

        Args:
            event_type: Sandbox event type (e.g., 'agent.tool_use')

        Returns:
            AgentLog log_type (e.g., 'output', 'input', 'intervention')
        """
        mapping = {
            # Agent output events
            "agent.assistant_message": "output",
            "agent.tool_result": "output",
            "agent.completed": "output",
            "agent.file_edited": "output",
            # Agent action events
            "agent.tool_use": "action",
            "agent.subagent_completed": "action",
            "agent.skill_completed": "action",
            # Status events
            "agent.started": "status",
            "agent.thinking": "status",
            "agent.waiting": "status",
            "agent.heartbeat": "heartbeat",
            # Error events
            "agent.error": "error",
            # Intervention events
            "agent.message_injected": "intervention",
            "agent.interrupted": "intervention",
        }
        return mapping.get(event_type, "event")

    def _build_message_from_event(
        self, event_type: str, event_data: dict
    ) -> str:
        """Build a human-readable message from sandbox event data.

        Args:
            event_type: Type of event
            event_data: Event payload

        Returns:
            Formatted message string
        """
        # Extract common fields
        content = event_data.get("content", "")
        tool_name = event_data.get("tool_name", "")
        file_path = event_data.get("file_path", "")
        error = event_data.get("error", "")
        message = event_data.get("message", "")

        if event_type == "agent.assistant_message":
            return content[:500] if content else "Assistant response"
        elif event_type == "agent.tool_use":
            return f"Tool: {tool_name}" if tool_name else "Tool execution"
        elif event_type == "agent.tool_result":
            return f"Tool result: {content[:200]}" if content else "Tool completed"
        elif event_type == "agent.file_edited":
            return f"Edited: {file_path}" if file_path else "File edited"
        elif event_type == "agent.error":
            return f"Error: {error}" if error else "Error occurred"
        elif event_type == "agent.completed":
            return message if message else "Task completed"
        elif event_type == "agent.message_injected":
            msg_type = event_data.get("message_type", "user")
            return f"[{msg_type}] {content[:200]}" if content else "Message received"
        elif event_type == "agent.thinking":
            return "Processing..."
        elif event_type == "agent.heartbeat":
            return "Heartbeat"
        else:
            # Generic fallback
            return message or content or event_type

    def build_sandbox_context(
        self, agent_id: str, sandbox_id: str
    ) -> Dict[str, Any]:
        """Build accumulated context from sandbox events.

        This is the sandbox-aware version of build_accumulated_context.

        Args:
            agent_id: Agent ID
            sandbox_id: Sandbox ID to query events from

        Returns:
            Complete accumulated context from sandbox events
        """
        logger.debug(
            f"Building sandbox context for agent {agent_id}, sandbox {sandbox_id}"
        )

        # Check cache first
        cache_key = f"sandbox:{sandbox_id}"
        if cache_key in self.context_cache:
            cached = self.context_cache[cache_key]
            if cached["timestamp"] > utc_now() - self.cache_ttl:
                return cached["context"]

        # Get sandbox events
        events = self.get_sandbox_events(sandbox_id, limit=200)

        if not events:
            logger.warning(f"No sandbox events found for {sandbox_id}")
            return self._get_empty_context()

        # Convert to AgentLog-compatible format
        pseudo_logs = self._convert_sandbox_events_to_logs(events, agent_id)

        with self.db.get_session() as session:
            # Get agent and task for context
            agent = session.query(Agent).filter_by(id=agent_id).first()
            task = (
                session.query(Task)
                .filter_by(sandbox_id=sandbox_id)
                .first()
            )

            # Build conversation history from pseudo-logs
            conversation = self._build_conversation_history(
                pseudo_logs, include_full_history=True
            )

            # Extract accumulated understanding
            context = {
                # Core trajectory elements
                "overall_goal": self._extract_overall_goal(conversation, task),
                "evolved_goals": self._track_goal_evolution(conversation),
                "constraints": self._extract_persistent_constraints(conversation),
                "lifted_constraints": self._identify_lifted_constraints(conversation),
                "standing_instructions": self._extract_standing_instructions(
                    conversation
                ),
                # Reference resolution
                "references": self._resolve_references(conversation),
                "context_markers": self._extract_context_markers(conversation),
                # Journey tracking
                "phases_completed": self._identify_completed_phases(conversation),
                "current_focus": self._determine_current_focus(conversation),
                "attempted_approaches": self._extract_attempted_approaches(
                    conversation
                ),
                "discovered_blockers": self._find_discovered_blockers(conversation),
                # Meta information
                "conversation_length": len(conversation),
                "session_duration": self._calculate_session_duration(pseudo_logs),
                "last_activity": events[-1].created_at if events else utc_now(),
                "agent_id": agent_id,
                "sandbox_id": sandbox_id,
                "agent_type": agent.agent_type if agent else "unknown",
                "agent_status": agent.status if agent else "unknown",
                "is_sandbox": True,
            }

            # Add task-specific context
            if task:
                context["task_id"] = str(task.id)
                context["task_description"] = task.description or ""
                context["task_status"] = task.status
                context["phase_id"] = task.phase_id

            # Cache the result
            self.context_cache[cache_key] = {
                "timestamp": utc_now(),
                "context": context,
            }

            return context

    def build_accumulated_context_auto(
        self, agent_id: str, include_full_history: bool = True
    ) -> Dict[str, Any]:
        """Automatically detect if agent is in sandbox and build appropriate context.

        This is the main entry point that routes to either:
        - build_sandbox_context() for sandbox agents
        - build_accumulated_context() for legacy agents

        Args:
            agent_id: Agent ID to build context for
            include_full_history: Whether to include full history

        Returns:
            Accumulated context from the appropriate source
        """
        # Check if agent is running in a sandbox
        sandbox_id = self.get_sandbox_id_for_agent(agent_id)

        if sandbox_id:
            logger.debug(f"Agent {agent_id} is sandbox agent, using sandbox events")
            return self.build_sandbox_context(agent_id, sandbox_id)
        else:
            logger.debug(f"Agent {agent_id} is legacy agent, using agent logs")
            return self.build_accumulated_context(agent_id, include_full_history)
