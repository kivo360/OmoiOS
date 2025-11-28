"""OmoiOS Task Management Tools for OpenHands agents.

These tools allow agents to create, update, and query tasks
for work breakdown and progress tracking.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Optional, List, TYPE_CHECKING

from pydantic import Field
from rich.text import Text

from openhands.sdk import Action, Observation, TextContent
from openhands.sdk.tool import ToolDefinition, ToolAnnotations, ToolExecutor, register_tool

from omoi_os.tools.protocols import (
    DatabaseServiceProtocol,
    TaskQueueServiceProtocol,
    DiscoveryServiceProtocol,
    EventBusServiceProtocol,
)

if TYPE_CHECKING:
    from openhands.sdk.conversation import LocalConversation
    from openhands.sdk.conversation.state import ConversationState


# ---------- Module-level service instances (set via initialize_task_tool_services) ----------

_db: Optional[DatabaseServiceProtocol] = None
_task_queue: Optional[TaskQueueServiceProtocol] = None
_discovery_service: Optional[DiscoveryServiceProtocol] = None
_event_bus: Optional[EventBusServiceProtocol] = None


def initialize_task_tool_services(
    db: DatabaseServiceProtocol,
    task_queue: TaskQueueServiceProtocol,
    discovery_service: Optional[DiscoveryServiceProtocol] = None,
    event_bus: Optional[EventBusServiceProtocol] = None,
) -> None:
    """Initialize the module-level service instances for task tools."""
    global _db, _task_queue, _discovery_service, _event_bus
    _db = db
    _task_queue = task_queue
    _discovery_service = discovery_service
    _event_bus = event_bus


# ---------- Actions ----------


class CreateTaskAction(Action):
    """Create a new task for work breakdown."""

    ticket_id: str = Field(description="Parent ticket ID this task belongs to")
    phase_id: str = Field(
        description="Phase ID (e.g., PHASE_REQUIREMENTS, PHASE_IMPLEMENTATION, PHASE_INTEGRATION, PHASE_REFACTORING)"
    )
    description: str = Field(
        min_length=10,
        description="Detailed task description including acceptance criteria",
    )
    task_type: str = Field(
        default="implementation",
        description="Type of task (analyze_requirements, implementation, bug_fix, testing, documentation)",
    )
    priority: str = Field(
        default="MEDIUM",
        pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$",
        description="Task priority",
    )
    discovery_type: Optional[str] = Field(
        default=None,
        description="Type of discovery that triggered this task (e.g., 'bug', 'optimization', 'missing_requirement', 'requirement_breakdown')",
    )
    discovery_description: Optional[str] = Field(
        default=None,
        description="Description of what was discovered that led to creating this task",
    )
    source_task_id: Optional[str] = Field(
        default=None,
        description="ID of the task that discovered this need (for workflow branching)",
    )
    priority_boost: bool = Field(
        default=False,
        description="Whether to boost priority based on discovery importance",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of task IDs this task depends on (must complete before this task can start)",
    )


class UpdateTaskStatusAction(Action):
    """Update a task's status."""

    task_id: str = Field(description="Task ID to update")
    status: str = Field(
        pattern="^(pending|in_progress|completed|failed|cancelled)$",
        description="New task status",
    )
    result_summary: Optional[str] = Field(
        default=None,
        description="Summary of work completed (required for 'completed' status)",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if status is 'failed'",
    )


class GetTaskAction(Action):
    """Get details of a specific task."""

    task_id: str = Field(description="Task ID to retrieve")


class GetTaskDiscoveriesAction(Action):
    """Get discoveries made during a task's execution."""

    task_id: str = Field(description="Task ID to get discoveries for")


class GetWorkflowGraphAction(Action):
    """Get the workflow graph showing task relationships and spawning."""

    ticket_id: str = Field(description="Ticket ID to get workflow graph for")


class ListPendingTasksAction(Action):
    """List pending tasks for a ticket or phase."""

    ticket_id: Optional[str] = Field(
        default=None, description="Filter by ticket ID"
    )
    phase_id: Optional[str] = Field(
        default=None, description="Filter by phase ID"
    )
    limit: int = Field(default=20, ge=1, le=100, description="Maximum tasks to return")


# ---------- Observations ----------


class TaskObservation(Observation):
    """Observation returned by task operations."""

    success: bool = Field(default=True)
    message: str = Field(default="")
    task_id: Optional[str] = Field(default=None)
    payload: dict = Field(default_factory=dict)

    @classmethod
    def ok(cls, message: str, task_id: Optional[str] = None, payload: dict = None) -> "TaskObservation":
        return cls(
            content=[TextContent(type="text", text=message)],
            success=True,
            message=message,
            task_id=task_id,
            payload=payload or {},
        )

    @classmethod
    def error(cls, message: str, payload: dict = None) -> "TaskObservation":
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
            text.append("✅ ", style="green")
            text.append(self.message, style="white")
        else:
            text.append("❌ ", style="red")
            text.append(self.message, style="red")
        return text


# ---------- Executors (ToolExecutor subclasses) ----------


class CreateTaskExecutor(ToolExecutor[CreateTaskAction, TaskObservation]):
    """Executor for creating tasks."""

    def __call__(
        self,
        action: CreateTaskAction,
        conversation: "LocalConversation | None" = None,
    ) -> TaskObservation:
        if _db is None or _task_queue is None:
            return TaskObservation.error("Task tools not initialized. Call initialize_task_tool_services first.")

        try:
            with _db.get_session() as session:
                dependencies_dict = None
                if action.dependencies:
                    dependencies_dict = {"depends_on": action.dependencies}

                task = _task_queue.enqueue_task(
                    ticket_id=action.ticket_id,
                    phase_id=action.phase_id,
                    task_type=action.task_type,
                    description=action.description,
                    priority=action.priority,
                    dependencies=dependencies_dict,
                    session=session,
                )

                task_id = str(task.id)

                if _discovery_service and action.discovery_type and action.source_task_id:
                    _discovery_service.record_discovery(
                        source_task_id=action.source_task_id,
                        discovery_type=action.discovery_type,
                        description=action.discovery_description or action.description,
                        spawned_task_id=task_id,
                        priority_boost=action.priority_boost,
                        session=session,
                    )

                session.commit()

                if _event_bus:
                    from omoi_os.models.events import SystemEvent
                    _event_bus.publish(
                        SystemEvent(
                            event_type="TASK_CREATED",
                            entity_type="task",
                            entity_id=task_id,
                            payload={
                                "ticket_id": action.ticket_id,
                                "phase_id": action.phase_id,
                                "task_type": action.task_type,
                                "priority": action.priority,
                                "discovery_type": action.discovery_type,
                            },
                        )
                    )

                return TaskObservation.ok(
                    message=f"Created task {task_id}: {action.description[:50]}...",
                    task_id=task_id,
                    payload={
                        "task_id": task_id,
                        "ticket_id": action.ticket_id,
                        "phase_id": action.phase_id,
                        "status": "pending",
                    },
                )
        except Exception as e:
            return TaskObservation.error(f"Failed to create task: {str(e)}")


class UpdateTaskStatusExecutor(ToolExecutor[UpdateTaskStatusAction, TaskObservation]):
    """Executor for updating task status."""

    def __call__(
        self,
        action: UpdateTaskStatusAction,
        conversation: "LocalConversation | None" = None,
    ) -> TaskObservation:
        if _db is None or _task_queue is None:
            return TaskObservation.error("Task tools not initialized.")

        try:
            result_dict = None
            if action.result_summary:
                result_dict = {"summary": action.result_summary}

            _task_queue.update_task_status(
                task_id=action.task_id,
                status=action.status,
                result=result_dict,
                error_message=action.error_message,
            )

            if _event_bus:
                from omoi_os.models.events import SystemEvent
                _event_bus.publish(
                    SystemEvent(
                        event_type=f"TASK_{action.status.upper()}",
                        entity_type="task",
                        entity_id=action.task_id,
                        payload={"status": action.status, "result_summary": action.result_summary},
                    )
                )

            return TaskObservation.ok(
                message=f"Task {action.task_id} status updated to '{action.status}'",
                task_id=action.task_id,
                payload={"task_id": action.task_id, "status": action.status},
            )
        except Exception as e:
            return TaskObservation.error(f"Failed to update task: {str(e)}")


class GetTaskExecutor(ToolExecutor[GetTaskAction, TaskObservation]):
    """Executor for getting task details."""

    def __call__(
        self,
        action: GetTaskAction,
        conversation: "LocalConversation | None" = None,
    ) -> TaskObservation:
        if _db is None:
            return TaskObservation.error("Task tools not initialized.")

        try:
            from omoi_os.models.task import Task

            with _db.get_session() as session:
                task = session.get(Task, action.task_id)
                if not task:
                    return TaskObservation.error(f"Task {action.task_id} not found")

                return TaskObservation.ok(
                    message=f"Task {action.task_id}: {task.description[:100]}",
                    task_id=action.task_id,
                    payload={
                        "task_id": str(task.id),
                        "ticket_id": str(task.ticket_id),
                        "phase_id": task.phase_id,
                        "status": task.status,
                        "description": task.description,
                        "priority": task.priority,
                        "task_type": task.task_type,
                        "result": task.result,
                        "error_message": task.error_message,
                        "dependencies": task.dependencies,
                    },
                )
        except Exception as e:
            return TaskObservation.error(f"Failed to get task: {str(e)}")


class GetTaskDiscoveriesExecutor(ToolExecutor[GetTaskDiscoveriesAction, TaskObservation]):
    """Executor for getting task discoveries."""

    def __call__(
        self,
        action: GetTaskDiscoveriesAction,
        conversation: "LocalConversation | None" = None,
    ) -> TaskObservation:
        if _discovery_service is None:
            return TaskObservation.error("Discovery service not available.")

        try:
            with _db.get_session() as session:
                discoveries = _discovery_service.get_task_discoveries(action.task_id, session=session)
                return TaskObservation.ok(
                    message=f"Found {len(discoveries)} discoveries for task {action.task_id}",
                    task_id=action.task_id,
                    payload={"discoveries": discoveries},
                )
        except Exception as e:
            return TaskObservation.error(f"Failed to get discoveries: {str(e)}")


class GetWorkflowGraphExecutor(ToolExecutor[GetWorkflowGraphAction, TaskObservation]):
    """Executor for getting workflow graph."""

    def __call__(
        self,
        action: GetWorkflowGraphAction,
        conversation: "LocalConversation | None" = None,
    ) -> TaskObservation:
        if _discovery_service is None:
            return TaskObservation.error("Discovery service not available.")

        try:
            with _db.get_session() as session:
                graph = _discovery_service.get_workflow_graph(action.ticket_id, session=session)
                return TaskObservation.ok(
                    message=f"Workflow graph for ticket {action.ticket_id}",
                    payload={"graph": graph},
                )
        except Exception as e:
            return TaskObservation.error(f"Failed to get workflow graph: {str(e)}")


class ListPendingTasksExecutor(ToolExecutor[ListPendingTasksAction, TaskObservation]):
    """Executor for listing pending tasks."""

    def __call__(
        self,
        action: ListPendingTasksAction,
        conversation: "LocalConversation | None" = None,
    ) -> TaskObservation:
        if _db is None:
            return TaskObservation.error("Task tools not initialized.")

        try:
            from omoi_os.models.task import Task
            from sqlalchemy import select

            with _db.get_session() as session:
                query = select(Task).where(Task.status == "pending")

                if action.ticket_id:
                    query = query.where(Task.ticket_id == action.ticket_id)
                if action.phase_id:
                    query = query.where(Task.phase_id == action.phase_id)

                query = query.limit(action.limit)
                tasks = session.execute(query).scalars().all()

                task_list = [
                    {
                        "task_id": str(t.id),
                        "description": t.description[:100],
                        "priority": t.priority,
                        "phase_id": t.phase_id,
                    }
                    for t in tasks
                ]

                return TaskObservation.ok(
                    message=f"Found {len(task_list)} pending tasks",
                    payload={"tasks": task_list, "count": len(task_list)},
                )
        except Exception as e:
            return TaskObservation.error(f"Failed to list pending tasks: {str(e)}")


# ---------- Tool Definitions (OpenHands SDK Pattern) ----------


CREATE_TASK_DESCRIPTION = """Create a new task for work breakdown.

Use this tool to break down high-level requirements into discrete, actionable subtasks.
Include discovery_type when creating tasks that were discovered during analysis
(e.g., 'bug', 'optimization', 'missing_requirement', 'requirement_breakdown').

## Parameters
- ticket_id: Parent ticket ID this task belongs to
- phase_id: Phase (PHASE_REQUIREMENTS, PHASE_IMPLEMENTATION, PHASE_INTEGRATION, PHASE_REFACTORING)
- description: Detailed task description with acceptance criteria (min 10 chars)
- task_type: Type of task (analyze_requirements, implementation, bug_fix, testing, documentation)
- priority: LOW, MEDIUM, HIGH, or CRITICAL
- discovery_type: Optional - what triggered this task (bug, optimization, missing_requirement)
- source_task_id: Optional - ID of task that discovered this need
- dependencies: Optional - list of task IDs that must complete first
"""


class CreateTaskTool(ToolDefinition[CreateTaskAction, TaskObservation]):
    """Tool for creating new tasks."""

    @classmethod
    def create(cls, conv_state: "ConversationState") -> Sequence["CreateTaskTool"]:
        return [
            cls(
                description=CREATE_TASK_DESCRIPTION,
                action_type=CreateTaskAction,
                observation_type=TaskObservation,
                annotations=ToolAnnotations(
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=False,
                    openWorldHint=False,
                ),
                executor=CreateTaskExecutor(),
            )
        ]


class UpdateTaskStatusTool(ToolDefinition[UpdateTaskStatusAction, TaskObservation]):
    """Tool for updating task status."""

    @classmethod
    def create(cls, conv_state: "ConversationState") -> Sequence["UpdateTaskStatusTool"]:
        return [
            cls(
                description=(
                    "Update a task's status. Use 'in_progress' when starting work, "
                    "'completed' when done (include result_summary), "
                    "'failed' if unable to complete (include error_message)."
                ),
                action_type=UpdateTaskStatusAction,
                observation_type=TaskObservation,
                annotations=ToolAnnotations(
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
                executor=UpdateTaskStatusExecutor(),
            )
        ]


class GetTaskTool(ToolDefinition[GetTaskAction, TaskObservation]):
    """Tool for getting task details."""

    @classmethod
    def create(cls, conv_state: "ConversationState") -> Sequence["GetTaskTool"]:
        return [
            cls(
                description="Get details of a specific task including its current status, description, and results.",
                action_type=GetTaskAction,
                observation_type=TaskObservation,
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
                executor=GetTaskExecutor(),
            )
        ]


class GetTaskDiscoveriesTool(ToolDefinition[GetTaskDiscoveriesAction, TaskObservation]):
    """Tool for getting task discoveries."""

    @classmethod
    def create(cls, conv_state: "ConversationState") -> Sequence["GetTaskDiscoveriesTool"]:
        return [
            cls(
                description=(
                    "Get discoveries made during a task's execution. "
                    "Useful for understanding what was found that led to new tasks being created."
                ),
                action_type=GetTaskDiscoveriesAction,
                observation_type=TaskObservation,
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
                executor=GetTaskDiscoveriesExecutor(),
            )
        ]


class GetWorkflowGraphTool(ToolDefinition[GetWorkflowGraphAction, TaskObservation]):
    """Tool for getting workflow graph."""

    @classmethod
    def create(cls, conv_state: "ConversationState") -> Sequence["GetWorkflowGraphTool"]:
        return [
            cls(
                description=(
                    "Get the workflow graph showing how tasks have spawned from discoveries. "
                    "Shows task relationships, discovery types, and workflow branching."
                ),
                action_type=GetWorkflowGraphAction,
                observation_type=TaskObservation,
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
                executor=GetWorkflowGraphExecutor(),
            )
        ]


class ListPendingTasksTool(ToolDefinition[ListPendingTasksAction, TaskObservation]):
    """Tool for listing pending tasks."""

    @classmethod
    def create(cls, conv_state: "ConversationState") -> Sequence["ListPendingTasksTool"]:
        return [
            cls(
                description=(
                    "List pending tasks, optionally filtered by ticket_id or phase_id. "
                    "Use this to see what work is waiting to be done."
                ),
                action_type=ListPendingTasksAction,
                observation_type=TaskObservation,
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
                executor=ListPendingTasksExecutor(),
            )
        ]


# ---------- Tool Registration ----------


def register_omoi_task_tools() -> None:
    """Register OmoiOS task management tools with OpenHands."""
    register_tool(CreateTaskTool.name, CreateTaskTool)
    register_tool(UpdateTaskStatusTool.name, UpdateTaskStatusTool)
    register_tool(GetTaskTool.name, GetTaskTool)
    register_tool(GetTaskDiscoveriesTool.name, GetTaskDiscoveriesTool)
    register_tool(GetWorkflowGraphTool.name, GetWorkflowGraphTool)
    register_tool(ListPendingTasksTool.name, ListPendingTasksTool)
