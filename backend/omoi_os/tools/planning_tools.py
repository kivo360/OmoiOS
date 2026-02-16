"""OmoiOS Planning Tools for OpenHands agents.

These tools provide planning agents with capabilities to gather context,
analyze requirements, search memory, and understand project structure.
"""

from __future__ import annotations

import os
import fnmatch
import re
from collections.abc import Sequence
from typing import Optional, TYPE_CHECKING

from pydantic import Field
from rich.text import Text

from openhands.sdk import Action, Observation, TextContent
from openhands.sdk.tool import (
    ToolDefinition,
    ToolAnnotations,
    ToolExecutor,
    register_tool,
)

from omoi_os.tools.protocols import (
    DatabaseServiceProtocol,
    DiscoveryServiceProtocol,
    EventBusServiceProtocol,
)

if TYPE_CHECKING:
    from openhands.sdk.conversation import LocalConversation
    from openhands.sdk.conversation.state import ConversationState


# ---------- Module-level service instances ----------

_db: Optional[DatabaseServiceProtocol] = None
_memory_service: Optional[object] = None  # MemoryService (optional)
_context_service: Optional[object] = None  # ContextService
_dependency_service: Optional[object] = None  # DependencyGraphService
_discovery_service: Optional[DiscoveryServiceProtocol] = None
_event_bus: Optional[EventBusServiceProtocol] = None


def initialize_planning_tool_services(
    db: DatabaseServiceProtocol,
    memory_service: Optional[object] = None,
    context_service: Optional[object] = None,
    dependency_service: Optional[object] = None,
    discovery_service: Optional[DiscoveryServiceProtocol] = None,
    event_bus: Optional[EventBusServiceProtocol] = None,
) -> None:
    """Initialize the module-level service instances for planning tools."""
    global \
        _db, \
        _memory_service, \
        _context_service, \
        _dependency_service, \
        _discovery_service, \
        _event_bus
    _db = db
    _memory_service = memory_service
    _context_service = context_service
    _dependency_service = dependency_service
    _discovery_service = discovery_service
    _event_bus = event_bus


# ---------- Actions ----------


class GetTicketDetailsAction(Action):
    """Get full details of a ticket for planning."""

    ticket_id: str = Field(description="Ticket ID to get details for")


class GetPhaseContextAction(Action):
    """Get context about what work has been done in a phase."""

    phase_id: str = Field(description="Phase ID to get context for")
    ticket_id: Optional[str] = Field(default=None, description="Optional ticket filter")


class SearchSimilarTasksAction(Action):
    """Search for similar tasks from memory."""

    query: str = Field(
        min_length=5, description="Description of task to find similar tasks for"
    )
    top_k: int = Field(
        default=5, ge=1, le=20, description="Number of results to return"
    )
    success_only: bool = Field(
        default=True, description="Only return successful task executions"
    )


class GetLearnedPatternsAction(Action):
    """Get learned patterns from past task executions."""

    task_type: Optional[str] = Field(default=None, description="Filter by task type")
    phase_id: Optional[str] = Field(default=None, description="Filter by phase")


class GetDependencyGraphAction(Action):
    """Get the dependency graph for a ticket's tasks."""

    ticket_id: str = Field(description="Ticket ID to get dependency graph for")


class AnalyzeBlockersAction(Action):
    """Analyze what's blocking task progress."""

    ticket_id: str = Field(description="Ticket ID to analyze blockers for")


class GetProjectStructureAction(Action):
    """Get project structure information for planning."""

    workspace_path: str = Field(description="Path to workspace to analyze")
    depth: int = Field(default=3, ge=1, le=10, description="Directory depth to scan")


class SearchCodebaseAction(Action):
    """Search the codebase for relevant code patterns."""

    query: str = Field(min_length=3, description="Search query (regex or text)")
    file_pattern: str = Field(default="*.py", description="File pattern to search")
    workspace_path: str = Field(description="Path to workspace to search")


class AnalyzeRequirementsAction(Action):
    """Analyze requirements and break them down into tasks."""

    ticket_id: str = Field(description="Ticket ID to analyze requirements for")
    requirements_text: str = Field(
        min_length=10, description="Requirements text to analyze"
    )


# ---------- Observations ----------


class PlanningObservation(Observation):
    """Observation returned by planning operations."""

    success: bool = Field(default=True)
    message: str = Field(default="")
    payload: dict = Field(default_factory=dict)

    @classmethod
    def ok(cls, message: str, payload: dict = None) -> "PlanningObservation":
        return cls(
            content=[TextContent(type="text", text=message)],
            success=True,
            message=message,
            payload=payload or {},
        )

    @classmethod
    def error(cls, message: str, payload: dict = None) -> "PlanningObservation":
        return cls(
            content=[TextContent(type="text", text=f"Error: {message}")],
            success=False,
            message=message,
            is_error=True,
            payload=payload or {},
        )

    @property
    def visualize(self) -> Text:
        text = Text()
        if self.success:
            text.append("📋 ", style="blue")
            text.append(self.message, style="white")
        else:
            text.append("❌ ", style="red")
            text.append(self.message, style="red")
        return text


# ---------- Executors (ToolExecutor subclasses) ----------


class GetTicketDetailsExecutor(
    ToolExecutor[GetTicketDetailsAction, PlanningObservation]
):
    """Executor for getting ticket details."""

    def __call__(
        self,
        action: GetTicketDetailsAction,
        conversation: "LocalConversation | None" = None,
    ) -> PlanningObservation:
        if _db is None:
            return PlanningObservation.error("Planning tools not initialized.")

        try:
            from omoi_os.models.ticket import Ticket

            with _db.get_session() as session:
                ticket = session.get(Ticket, action.ticket_id)
                if not ticket:
                    return PlanningObservation.error(
                        f"Ticket {action.ticket_id} not found"
                    )

                return PlanningObservation.ok(
                    message=f"Ticket: {ticket.title}",
                    payload={
                        "ticket_id": str(ticket.id),
                        "title": ticket.title,
                        "description": ticket.description,
                        "phase_id": ticket.phase_id,
                        "status": ticket.status,
                        "priority": ticket.priority,
                        "approval_status": ticket.approval_status,
                        "created_at": (
                            str(ticket.created_at) if ticket.created_at else None
                        ),
                    },
                )
        except Exception as e:
            return PlanningObservation.error(f"Failed to get ticket: {str(e)}")


class GetPhaseContextExecutor(ToolExecutor[GetPhaseContextAction, PlanningObservation]):
    """Executor for getting phase context."""

    def __call__(
        self,
        action: GetPhaseContextAction,
        conversation: "LocalConversation | None" = None,
    ) -> PlanningObservation:
        if _db is None:
            return PlanningObservation.error("Planning tools not initialized.")

        try:
            from omoi_os.models.task import Task
            from sqlalchemy import select, func

            with _db.get_session() as session:
                query = select(Task.status, func.count(Task.id)).where(
                    Task.phase_id == action.phase_id
                )
                if action.ticket_id:
                    query = query.where(Task.ticket_id == action.ticket_id)
                query = query.group_by(Task.status)

                results = session.execute(query).all()
                status_counts = {status: count for status, count in results}

                recent_query = (
                    select(Task)
                    .where(
                        Task.phase_id == action.phase_id,
                        Task.status == "completed",
                    )
                    .order_by(Task.updated_at.desc())
                    .limit(5)
                )

                if action.ticket_id:
                    recent_query = recent_query.where(
                        Task.ticket_id == action.ticket_id
                    )

                recent_tasks = session.execute(recent_query).scalars().all()

                return PlanningObservation.ok(
                    message=f"Phase {action.phase_id} context retrieved",
                    payload={
                        "phase_id": action.phase_id,
                        "status_counts": status_counts,
                        "recent_completed_tasks": [
                            {
                                "task_id": str(t.id),
                                "description": t.description[:100],
                                "result": t.result,
                            }
                            for t in recent_tasks
                        ],
                    },
                )
        except Exception as e:
            return PlanningObservation.error(f"Failed to get phase context: {str(e)}")


class SearchSimilarTasksExecutor(
    ToolExecutor[SearchSimilarTasksAction, PlanningObservation]
):
    """Executor for searching similar tasks."""

    def __call__(
        self,
        action: SearchSimilarTasksAction,
        conversation: "LocalConversation | None" = None,
    ) -> PlanningObservation:
        if _memory_service is None:
            return PlanningObservation.error(
                "Memory service not available. Install fastembed or configure EMBEDDING_OPENAI_API_KEY."
            )

        try:
            with _db.get_session() as session:
                similar = _memory_service.search_similar(
                    session=session,
                    task_description=action.query,
                    top_k=action.top_k,
                    success_only=action.success_only,
                )

                return PlanningObservation.ok(
                    message=f"Found {len(similar)} similar tasks",
                    payload={
                        "query": action.query,
                        "results": [
                            {
                                "task_id": str(s.task_id),
                                "description": s.description[:200],
                                "similarity": s.similarity_score,
                                "success": s.success,
                                "execution_summary": (
                                    s.execution_summary[:200]
                                    if s.execution_summary
                                    else None
                                ),
                            }
                            for s in similar
                        ],
                    },
                )
        except Exception as e:
            return PlanningObservation.error(
                f"Failed to search similar tasks: {str(e)}"
            )


class GetLearnedPatternsExecutor(
    ToolExecutor[GetLearnedPatternsAction, PlanningObservation]
):
    """Executor for getting learned patterns."""

    def __call__(
        self,
        action: GetLearnedPatternsAction,
        conversation: "LocalConversation | None" = None,
    ) -> PlanningObservation:
        if _memory_service is None:
            return PlanningObservation.error(
                "Memory service not available. Install fastembed or configure EMBEDDING_OPENAI_API_KEY."
            )

        try:
            with _db.get_session() as session:
                patterns = _memory_service.get_patterns(
                    session=session,
                    task_type=action.task_type,
                    phase_id=action.phase_id,
                )

                return PlanningObservation.ok(
                    message=f"Found {len(patterns)} learned patterns",
                    payload={
                        "patterns": [
                            {
                                "pattern_id": str(p.id),
                                "pattern_type": p.pattern_type,
                                "description": p.description[:200],
                                "confidence": p.confidence,
                                "usage_count": p.usage_count,
                            }
                            for p in patterns
                        ],
                    },
                )
        except Exception as e:
            return PlanningObservation.error(f"Failed to get patterns: {str(e)}")


class GetDependencyGraphExecutor(
    ToolExecutor[GetDependencyGraphAction, PlanningObservation]
):
    """Executor for getting dependency graph."""

    def __call__(
        self,
        action: GetDependencyGraphAction,
        conversation: "LocalConversation | None" = None,
    ) -> PlanningObservation:
        if _dependency_service is None:
            return PlanningObservation.error("Dependency service not available.")

        try:
            with _db.get_session() as session:
                graph = _dependency_service.get_dependency_graph(
                    ticket_id=action.ticket_id,
                    session=session,
                )

                return PlanningObservation.ok(
                    message=f"Dependency graph for ticket {action.ticket_id}",
                    payload={"graph": graph},
                )
        except Exception as e:
            return PlanningObservation.error(
                f"Failed to get dependency graph: {str(e)}"
            )


class AnalyzeBlockersExecutor(ToolExecutor[AnalyzeBlockersAction, PlanningObservation]):
    """Executor for analyzing blockers."""

    def __call__(
        self,
        action: AnalyzeBlockersAction,
        conversation: "LocalConversation | None" = None,
    ) -> PlanningObservation:
        if _db is None:
            return PlanningObservation.error("Planning tools not initialized.")

        try:
            from omoi_os.models.task import Task
            from sqlalchemy import select

            with _db.get_session() as session:
                pending_tasks = (
                    session.execute(
                        select(Task).where(
                            Task.ticket_id == action.ticket_id,
                            Task.status.in_(["pending", "blocked"]),
                        )
                    )
                    .scalars()
                    .all()
                )

                blockers = []
                for task in pending_tasks:
                    if task.dependencies:
                        dep_ids = task.dependencies.get("depends_on", [])
                        for dep_id in dep_ids:
                            dep_task = session.get(Task, dep_id)
                            if dep_task and dep_task.status != "completed":
                                blockers.append(
                                    {
                                        "blocked_task_id": str(task.id),
                                        "blocked_task_desc": task.description[:100],
                                        "blocking_task_id": str(dep_task.id),
                                        "blocking_task_desc": dep_task.description[
                                            :100
                                        ],
                                        "blocking_status": dep_task.status,
                                    }
                                )

                return PlanningObservation.ok(
                    message=f"Found {len(blockers)} blockers",
                    payload={"blockers": blockers},
                )
        except Exception as e:
            return PlanningObservation.error(f"Failed to analyze blockers: {str(e)}")


class GetProjectStructureExecutor(
    ToolExecutor[GetProjectStructureAction, PlanningObservation]
):
    """Executor for getting project structure."""

    def __call__(
        self,
        action: GetProjectStructureAction,
        conversation: "LocalConversation | None" = None,
    ) -> PlanningObservation:
        try:
            structure = []

            for root, dirs, files in os.walk(action.workspace_path):
                depth = root.replace(action.workspace_path, "").count(os.sep)
                if depth >= action.depth:
                    dirs[:] = []
                    continue

                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in ("node_modules", "__pycache__", "venv", ".git")
                ]

                rel_path = os.path.relpath(root, action.workspace_path)
                structure.append(
                    {
                        "path": rel_path if rel_path != "." else "/",
                        "type": "directory",
                        "depth": depth,
                        "files": [f for f in files if not f.startswith(".")],
                    }
                )

            return PlanningObservation.ok(
                message=f"Project structure ({len(structure)} directories)",
                payload={
                    "workspace_path": action.workspace_path,
                    "structure": structure,
                },
            )
        except Exception as e:
            return PlanningObservation.error(
                f"Failed to get project structure: {str(e)}"
            )


class SearchCodebaseExecutor(ToolExecutor[SearchCodebaseAction, PlanningObservation]):
    """Executor for searching codebase."""

    def __call__(
        self,
        action: SearchCodebaseAction,
        conversation: "LocalConversation | None" = None,
    ) -> PlanningObservation:
        try:
            matches = []
            pattern = re.compile(action.query, re.IGNORECASE)

            for root, dirs, files in os.walk(action.workspace_path):
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in ("node_modules", "__pycache__", "venv", ".git")
                ]

                for filename in fnmatch.filter(files, action.file_pattern):
                    filepath = os.path.join(root, filename)
                    rel_path = os.path.relpath(filepath, action.workspace_path)

                    try:
                        with open(
                            filepath, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            for line_num, line in enumerate(f, 1):
                                if pattern.search(line):
                                    matches.append(
                                        {
                                            "file": rel_path,
                                            "line": line_num,
                                            "content": line.strip()[:200],
                                        }
                                    )
                                    if len(matches) >= 50:
                                        break
                    except Exception:
                        continue

                    if len(matches) >= 50:
                        break

                if len(matches) >= 50:
                    break

            return PlanningObservation.ok(
                message=f"Found {len(matches)} matches",
                payload={
                    "query": action.query,
                    "matches": matches,
                },
            )
        except Exception as e:
            return PlanningObservation.error(f"Failed to search codebase: {str(e)}")


class AnalyzeRequirementsExecutor(
    ToolExecutor[AnalyzeRequirementsAction, PlanningObservation]
):
    """Executor for analyzing requirements."""

    def __call__(
        self,
        action: AnalyzeRequirementsAction,
        conversation: "LocalConversation | None" = None,
    ) -> PlanningObservation:
        try:
            requirements = []
            lines = action.requirements_text.split("\n")

            for line in lines:
                line = line.strip()
                if line and not line.startswith("#"):
                    req = {"text": line, "type": "functional"}
                    if "WHEN" in line.upper():
                        req["type"] = "conditional"
                    elif "SHALL" in line.upper():
                        req["type"] = "mandatory"
                    elif "SHOULD" in line.upper():
                        req["type"] = "recommended"
                    requirements.append(req)

            return PlanningObservation.ok(
                message=f"Parsed {len(requirements)} requirements",
                payload={
                    "ticket_id": action.ticket_id,
                    "requirements": requirements,
                    "raw_text": action.requirements_text,
                },
            )
        except Exception as e:
            return PlanningObservation.error(
                f"Failed to analyze requirements: {str(e)}"
            )


# ---------- Tool Definitions ----------


class GetTicketDetailsTool(ToolDefinition[GetTicketDetailsAction, PlanningObservation]):
    """Tool for getting ticket details."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState"
    ) -> Sequence["GetTicketDetailsTool"]:
        return [
            cls(
                description="Get full details of a ticket including title, description, status, and phase.",
                action_type=GetTicketDetailsAction,
                observation_type=PlanningObservation,
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
                executor=GetTicketDetailsExecutor(),
            )
        ]


class GetPhaseContextTool(ToolDefinition[GetPhaseContextAction, PlanningObservation]):
    """Tool for getting phase context."""

    @classmethod
    def create(cls, conv_state: "ConversationState") -> Sequence["GetPhaseContextTool"]:
        return [
            cls(
                description="Get context about what work has been done in a phase, including task counts and recent completions.",
                action_type=GetPhaseContextAction,
                observation_type=PlanningObservation,
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
                executor=GetPhaseContextExecutor(),
            )
        ]


class SearchSimilarTasksTool(
    ToolDefinition[SearchSimilarTasksAction, PlanningObservation]
):
    """Tool for searching similar tasks from memory."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState"
    ) -> Sequence["SearchSimilarTasksTool"]:
        return [
            cls(
                description=(
                    "Search for similar tasks from memory using semantic search. "
                    "Returns past task executions that are similar to the query, "
                    "including their outcomes and learnings."
                ),
                action_type=SearchSimilarTasksAction,
                observation_type=PlanningObservation,
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
                executor=SearchSimilarTasksExecutor(),
            )
        ]


class GetLearnedPatternsTool(
    ToolDefinition[GetLearnedPatternsAction, PlanningObservation]
):
    """Tool for getting learned patterns."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState"
    ) -> Sequence["GetLearnedPatternsTool"]:
        return [
            cls(
                description="Get learned patterns from past task executions, optionally filtered by task type or phase.",
                action_type=GetLearnedPatternsAction,
                observation_type=PlanningObservation,
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
                executor=GetLearnedPatternsExecutor(),
            )
        ]


class GetDependencyGraphTool(
    ToolDefinition[GetDependencyGraphAction, PlanningObservation]
):
    """Tool for getting dependency graph."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState"
    ) -> Sequence["GetDependencyGraphTool"]:
        return [
            cls(
                description="Get the dependency graph for a ticket's tasks, showing which tasks depend on others.",
                action_type=GetDependencyGraphAction,
                observation_type=PlanningObservation,
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
                executor=GetDependencyGraphExecutor(),
            )
        ]


class AnalyzeBlockersTool(ToolDefinition[AnalyzeBlockersAction, PlanningObservation]):
    """Tool for analyzing blockers."""

    @classmethod
    def create(cls, conv_state: "ConversationState") -> Sequence["AnalyzeBlockersTool"]:
        return [
            cls(
                description="Analyze what's blocking task progress for a ticket, identifying dependency chains.",
                action_type=AnalyzeBlockersAction,
                observation_type=PlanningObservation,
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
                executor=AnalyzeBlockersExecutor(),
            )
        ]


class GetProjectStructureTool(
    ToolDefinition[GetProjectStructureAction, PlanningObservation]
):
    """Tool for getting project structure."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState"
    ) -> Sequence["GetProjectStructureTool"]:
        return [
            cls(
                description="Get project structure information for planning, including directories and file listings.",
                action_type=GetProjectStructureAction,
                observation_type=PlanningObservation,
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
                executor=GetProjectStructureExecutor(),
            )
        ]


class SearchCodebaseTool(ToolDefinition[SearchCodebaseAction, PlanningObservation]):
    """Tool for searching codebase."""

    @classmethod
    def create(cls, conv_state: "ConversationState") -> Sequence["SearchCodebaseTool"]:
        return [
            cls(
                description="Search the codebase for relevant code patterns using regex or text matching.",
                action_type=SearchCodebaseAction,
                observation_type=PlanningObservation,
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
                executor=SearchCodebaseExecutor(),
            )
        ]


class AnalyzeRequirementsTool(
    ToolDefinition[AnalyzeRequirementsAction, PlanningObservation]
):
    """Tool for analyzing requirements."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState"
    ) -> Sequence["AnalyzeRequirementsTool"]:
        return [
            cls(
                description=(
                    "Analyze requirements text and parse them into structured format. "
                    "Supports EARS-style requirements (WHEN/SHALL/SHOULD patterns)."
                ),
                action_type=AnalyzeRequirementsAction,
                observation_type=PlanningObservation,
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
                executor=AnalyzeRequirementsExecutor(),
            )
        ]


# ---------- Tool Registration ----------


def register_omoi_planning_tools() -> None:
    """Register OmoiOS planning tools with OpenHands."""
    register_tool(GetTicketDetailsTool.name, GetTicketDetailsTool)
    register_tool(GetPhaseContextTool.name, GetPhaseContextTool)
    register_tool(SearchSimilarTasksTool.name, SearchSimilarTasksTool)
    register_tool(GetLearnedPatternsTool.name, GetLearnedPatternsTool)
    register_tool(GetDependencyGraphTool.name, GetDependencyGraphTool)
    register_tool(AnalyzeBlockersTool.name, AnalyzeBlockersTool)
    register_tool(GetProjectStructureTool.name, GetProjectStructureTool)
    register_tool(SearchCodebaseTool.name, SearchCodebaseTool)
    register_tool(AnalyzeRequirementsTool.name, AnalyzeRequirementsTool)
