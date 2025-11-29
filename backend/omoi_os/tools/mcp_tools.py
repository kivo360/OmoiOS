"""OpenHands tools for MCP server access.

These tools allow agents to call MCP tools on a central server,
enabling distributed agent architectures where workers only need
HTTP access to the MCP server.
"""

from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING
from pydantic import Field

from openhands.sdk.tool import ToolDefinition, ToolExecutor
from openhands.sdk.tool.schema import Action, Observation

if TYPE_CHECKING:
    from openhands.sdk.core import ConversationState


# ============================================================================
# Action/Observation Models (must inherit from OpenHands schema classes)
# ============================================================================


class ListMCPToolsAction(Action):
    """Action to list all available MCP tools."""

    refresh: bool = Field(
        default=False,
        description="Force refresh of cached tools list",
    )


class CallMCPToolAction(Action):
    """Action to call any MCP tool by name."""

    tool_name: str = Field(
        ...,
        description="Name of the MCP tool to call (e.g., 'create_ticket', 'get_task')",
    )
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments to pass to the tool as a dictionary",
    )


class MCPToolsObservation(Observation):
    """Observation from MCP tools operations."""

    success: bool = Field(description="Whether the operation succeeded")
    result: Any = Field(default=None, description="Operation result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    tools_count: Optional[int] = Field(
        default=None,
        description="Number of tools (for list operation)",
    )


# ============================================================================
# Tool Executors
# ============================================================================


class ListMCPToolsExecutor(ToolExecutor[ListMCPToolsAction, MCPToolsObservation]):
    """Executor for listing available MCP tools."""

    def __init__(self, mcp_url: str):
        self.mcp_url = mcp_url

    def __call__(
        self,
        action: ListMCPToolsAction,
        conversation: Any = None,
    ) -> MCPToolsObservation:
        import asyncio
        from omoi_os.services.mcp_client import MCPClientService

        async def _list_tools():
            client = MCPClientService(mcp_url=self.mcp_url)
            try:
                await client.connect()
                tools = await client.list_tools(refresh=action.refresh)
                return [
                    {
                        "name": t.name,
                        "description": t.description[:100] + "..."
                        if len(t.description) > 100
                        else t.description,
                    }
                    for t in tools
                ]
            finally:
                await client.disconnect()

        try:
            # Run async operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                tools = loop.run_until_complete(_list_tools())
            finally:
                loop.close()

            return MCPToolsObservation(
                success=True,
                result={"tools": tools},
                tools_count=len(tools),
            )
        except Exception as e:
            return MCPToolsObservation(
                success=False,
                error=str(e),
            )


class CallMCPToolExecutor(ToolExecutor[CallMCPToolAction, MCPToolsObservation]):
    """Executor for calling any MCP tool."""

    def __init__(self, mcp_url: str):
        self.mcp_url = mcp_url

    def __call__(
        self,
        action: CallMCPToolAction,
        conversation: Any = None,
    ) -> MCPToolsObservation:
        import asyncio
        from omoi_os.services.mcp_client import MCPClientService

        async def _call_tool():
            client = MCPClientService(mcp_url=self.mcp_url)
            try:
                await client.connect()
                result = await client.call_tool(action.tool_name, action.arguments)
                return result
            finally:
                await client.disconnect()

        try:
            # Run async operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_call_tool())
            finally:
                loop.close()

            return MCPToolsObservation(
                success=True,
                result=result,
            )
        except Exception as e:
            return MCPToolsObservation(
                success=False,
                error=f"Failed to call MCP tool '{action.tool_name}': {str(e)}",
            )


# ============================================================================
# Tool Definitions
# ============================================================================


class ListMCPToolsTool(ToolDefinition[ListMCPToolsAction, MCPToolsObservation]):
    """Tool to list all available MCP tools."""

    @classmethod
    def create(
        cls,
        conv_state: "ConversationState",
        **kwargs,
    ) -> Sequence["ListMCPToolsTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = ListMCPToolsExecutor(mcp_url=mcp_url)

        return [
            cls(
                name="mcp__list_tools",
                description=(
                    "List all available MCP tools on the central server. "
                    "Use this to discover what operations are available, including "
                    "ticket management, task management, discovery tracking, "
                    "collaboration, and history/trajectory tools."
                ),
                action_type=ListMCPToolsAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class CallMCPToolTool(ToolDefinition[CallMCPToolAction, MCPToolsObservation]):
    """Tool to call any MCP tool on the central server."""

    @classmethod
    def create(
        cls,
        conv_state: "ConversationState",
        **kwargs,
    ) -> Sequence["CallMCPToolTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = CallMCPToolExecutor(mcp_url=mcp_url)

        return [
            cls(
                name="mcp__call_tool",
                description=(
                    "Call any MCP tool on the central server by name. "
                    "This is the primary way for distributed agents to interact "
                    "with the OmoiOS system. Available tools include:\n\n"
                    "**Ticket Management:**\n"
                    "- create_ticket, update_ticket, get_ticket, get_tickets\n"
                    "- get_ticket_history, resolve_ticket, add_ticket_comment\n"
                    "- link_commit, add_ticket_dependency, remove_ticket_dependency\n\n"
                    "**Task Management:**\n"
                    "- create_task, update_task_status, get_task\n\n"
                    "**Discovery:**\n"
                    "- get_task_discoveries, get_workflow_graph, get_discoveries_by_type\n\n"
                    "**Collaboration:**\n"
                    "- broadcast_message, send_message, get_messages, request_handoff\n\n"
                    "**History & Trajectory:**\n"
                    "- get_phase_history, get_task_timeline, get_agent_trajectory\n\n"
                    "Example: call_tool('create_ticket', {'workflow_id': '...', 'title': '...'})"
                ),
                action_type=CallMCPToolAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


# ============================================================================
# Convenience Tool Definitions (Typed wrappers for common operations)
# ============================================================================


class MCPCreateTicketAction(Action):
    """Action to create a ticket via MCP."""

    workflow_id: str = Field(..., description="Workflow identifier")
    agent_id: str = Field(..., description="ID of agent creating the ticket")
    title: str = Field(..., min_length=3, max_length=500, description="Ticket title")
    description: str = Field(..., min_length=10, description="Ticket description")
    ticket_type: str = Field(default="task", description="Type of ticket")
    priority: str = Field(
        default="medium", description="Priority (low/medium/high/critical)"
    )
    parent_ticket_id: Optional[str] = Field(
        default=None, description="Parent ticket ID for sub-tickets"
    )
    blocked_by_ticket_ids: List[str] = Field(
        default_factory=list,
        description="List of ticket IDs blocking this ticket",
    )
    tags: List[str] = Field(default_factory=list, description="Tags for the ticket")


class CreateTicketMCPExecutor(ToolExecutor[MCPCreateTicketAction, MCPToolsObservation]):
    """Typed executor for creating tickets via MCP."""

    def __init__(self, mcp_url: str):
        self.mcp_url = mcp_url

    def __call__(
        self,
        action: MCPCreateTicketAction,
        conversation: Any = None,
    ) -> MCPToolsObservation:
        import asyncio
        from omoi_os.services.mcp_client import MCPClientService

        async def _create_ticket():
            client = MCPClientService(mcp_url=self.mcp_url)
            try:
                await client.connect()
                result = await client.call_tool(
                    "create_ticket",
                    {
                        "workflow_id": action.workflow_id,
                        "agent_id": action.agent_id,
                        "title": action.title,
                        "description": action.description,
                        "ticket_type": action.ticket_type,
                        "priority": action.priority,
                        "parent_ticket_id": action.parent_ticket_id,
                        "blocked_by_ticket_ids": action.blocked_by_ticket_ids,
                        "tags": action.tags,
                    },
                )
                return result
            finally:
                await client.disconnect()

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_create_ticket())
            finally:
                loop.close()

            return MCPToolsObservation(success=True, result=result)
        except Exception as e:
            return MCPToolsObservation(success=False, error=str(e))


class CreateTicketMCPTool(ToolDefinition[MCPCreateTicketAction, MCPToolsObservation]):
    """Typed tool for creating tickets via MCP."""

    @classmethod
    def create(
        cls,
        conv_state: "ConversationState",
        **kwargs,
    ) -> Sequence["CreateTicketMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = CreateTicketMCPExecutor(mcp_url=mcp_url)

        return [
            cls(
                name="mcp__create_ticket",
                description=(
                    "Create a new ticket via the MCP server. This is the recommended "
                    "way for agents to create tickets, especially in distributed setups. "
                    "Supports parent tickets for sub-tickets and blockers for dependencies."
                ),
                action_type=MCPCreateTicketAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class MCPCreateTaskAction(Action):
    """Action to create a task via MCP."""

    ticket_id: str = Field(..., description="ID of the ticket this task belongs to")
    phase_id: str = Field(
        ..., description="Phase identifier (e.g., 'PHASE_IMPLEMENTATION')"
    )
    description: str = Field(..., min_length=10, description="Task description")
    task_type: str = Field(default="implementation", description="Type of task")
    priority: str = Field(
        default="MEDIUM", description="Priority (LOW/MEDIUM/HIGH/CRITICAL)"
    )
    discovery_type: Optional[str] = Field(
        default=None,
        description="Type of discovery that triggered this task (for Hephaestus pattern)",
    )
    source_task_id: Optional[str] = Field(
        default=None,
        description="ID of the task that discovered this need (for workflow branching)",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of task IDs this task depends on",
    )


class CreateTaskMCPExecutor(ToolExecutor[MCPCreateTaskAction, MCPToolsObservation]):
    """Typed executor for creating tasks via MCP."""

    def __init__(self, mcp_url: str):
        self.mcp_url = mcp_url

    def __call__(
        self,
        action: MCPCreateTaskAction,
        conversation: Any = None,
    ) -> MCPToolsObservation:
        import asyncio
        from omoi_os.services.mcp_client import MCPClientService

        async def _create_task():
            client = MCPClientService(mcp_url=self.mcp_url)
            try:
                await client.connect()
                result = await client.call_tool(
                    "create_task",
                    {
                        "ticket_id": action.ticket_id,
                        "phase_id": action.phase_id,
                        "description": action.description,
                        "task_type": action.task_type,
                        "priority": action.priority,
                        "discovery_type": action.discovery_type,
                        "source_task_id": action.source_task_id,
                        "dependencies": action.dependencies,
                    },
                )
                return result
            finally:
                await client.disconnect()

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_create_task())
            finally:
                loop.close()

            return MCPToolsObservation(success=True, result=result)
        except Exception as e:
            return MCPToolsObservation(success=False, error=str(e))


class CreateTaskMCPTool(ToolDefinition[MCPCreateTaskAction, MCPToolsObservation]):
    """Typed tool for creating tasks via MCP."""

    @classmethod
    def create(
        cls,
        conv_state: "ConversationState",
        **kwargs,
    ) -> Sequence["CreateTaskMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = CreateTaskMCPExecutor(mcp_url=mcp_url)

        return [
            cls(
                name="mcp__create_task",
                description=(
                    "Create a new task via the MCP server. Supports discovery-based "
                    "task creation for the Hephaestus pattern - when discovery_type "
                    "and source_task_id are provided, the task is tracked as spawned "
                    "from a discovery."
                ),
                action_type=MCPCreateTaskAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


# ============================================================================
# Collaboration Tools (MCP-backed)
# ============================================================================


class MCPBroadcastMessageAction(Action):
    """Action to broadcast a message to all agents."""

    sender_agent_id: str = Field(..., description="Your agent ID")
    message: str = Field(..., min_length=1, description="Message content to broadcast")
    message_type: str = Field(
        default="info", description="Type: info, question, warning, discovery"
    )
    ticket_id: Optional[str] = Field(
        default=None, description="Optional ticket ID for context"
    )
    task_id: Optional[str] = Field(
        default=None, description="Optional task ID for context"
    )


class MCPSendMessageAction(Action):
    """Action to send a direct message to a specific agent."""

    sender_agent_id: str = Field(..., description="Your agent ID")
    recipient_agent_id: str = Field(..., description="Target agent ID")
    message: str = Field(..., min_length=1, description="Message content")
    message_type: str = Field(
        default="info", description="Type: info, question, handoff_request, etc."
    )
    ticket_id: Optional[str] = Field(
        default=None, description="Optional ticket ID for context"
    )
    task_id: Optional[str] = Field(
        default=None, description="Optional task ID for context"
    )


class MCPGetMessagesAction(Action):
    """Action to get messages for an agent."""

    agent_id: str = Field(..., description="ID of the agent to get messages for")
    thread_id: Optional[str] = Field(default=None, description="Filter by thread ID")
    limit: int = Field(default=50, description="Maximum messages to return")
    unread_only: bool = Field(default=False, description="Only return unread messages")


class MCPRequestHandoffAction(Action):
    """Action to request a task handoff to another agent."""

    from_agent_id: str = Field(..., description="Your agent ID")
    to_agent_id: str = Field(..., description="Target agent ID to hand off to")
    task_id: str = Field(..., description="Task ID to hand off")
    reason: str = Field(..., min_length=10, description="Reason for handoff")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional handoff context"
    )


def _create_mcp_executor(mcp_url: str, tool_name: str, action_fields: List[str]):
    """Factory to create MCP-backed executors."""

    class MCPBackedExecutor(ToolExecutor):
        def __init__(self):
            self.mcp_url = mcp_url
            self.tool_name = tool_name
            self.action_fields = action_fields

        def __call__(
            self, action: Action, conversation: Any = None
        ) -> MCPToolsObservation:
            import asyncio
            from omoi_os.services.mcp_client import MCPClientService

            # Extract arguments from action
            args = {field: getattr(action, field) for field in self.action_fields}

            async def _call():
                client = MCPClientService(mcp_url=self.mcp_url)
                try:
                    await client.connect()
                    result = await client.call_tool(self.tool_name, args)
                    return result
                finally:
                    await client.disconnect()

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(_call())
                finally:
                    loop.close()

                return MCPToolsObservation(success=True, result=result)
            except Exception as e:
                return MCPToolsObservation(success=False, error=str(e))

    return MCPBackedExecutor()


class BroadcastMessageMCPTool(
    ToolDefinition[MCPBroadcastMessageAction, MCPToolsObservation]
):
    """Tool to broadcast a message to all agents via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["BroadcastMessageMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(
            mcp_url,
            "broadcast_message",
            ["sender_agent_id", "message", "message_type", "ticket_id", "task_id"],
        )
        return [
            cls(
                name="mcp__broadcast_message",
                description=(
                    "Broadcast a message to all active agents in the system. "
                    "Use this for announcements, discoveries, or alerts that all agents "
                    "should be aware of."
                ),
                action_type=MCPBroadcastMessageAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class SendMessageMCPTool(ToolDefinition[MCPSendMessageAction, MCPToolsObservation]):
    """Tool to send a direct message to a specific agent via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["SendMessageMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(
            mcp_url,
            "send_message",
            [
                "sender_agent_id",
                "recipient_agent_id",
                "message",
                "message_type",
                "ticket_id",
                "task_id",
            ],
        )
        return [
            cls(
                name="mcp__send_message",
                description=(
                    "Send a direct message to a specific agent. "
                    "Use for coordination, questions, or sharing specific information "
                    "with another agent."
                ),
                action_type=MCPSendMessageAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class GetMessagesMCPTool(ToolDefinition[MCPGetMessagesAction, MCPToolsObservation]):
    """Tool to get messages for an agent via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["GetMessagesMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(
            mcp_url, "get_messages", ["agent_id", "thread_id", "limit", "unread_only"]
        )
        return [
            cls(
                name="mcp__get_messages",
                description=(
                    "Get messages for an agent. Can filter by thread or unread status. "
                    "Use this to check for incoming communications or review conversation history."
                ),
                action_type=MCPGetMessagesAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class RequestHandoffMCPTool(
    ToolDefinition[MCPRequestHandoffAction, MCPToolsObservation]
):
    """Tool to request a task handoff via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["RequestHandoffMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(
            mcp_url,
            "request_handoff",
            ["from_agent_id", "to_agent_id", "task_id", "reason", "context"],
        )
        return [
            cls(
                name="mcp__request_handoff",
                description=(
                    "Request a task handoff to another agent. Use when you cannot complete "
                    "a task yourself (e.g., requires different expertise, blocked, or at capacity). "
                    "Provide a clear reason and any relevant context."
                ),
                action_type=MCPRequestHandoffAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


# ============================================================================
# Task Management Tools (MCP-backed)
# ============================================================================


class MCPUpdateTaskStatusAction(Action):
    """Action to update a task's status."""

    task_id: str = Field(..., description="ID of the task to update")
    status: str = Field(
        ...,
        description="New status: pending, assigned, running, completed, failed, cancelled",
    )
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Task result (for completed tasks)"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message (for failed tasks)"
    )


class MCPGetTaskAction(Action):
    """Action to get a task's details."""

    task_id: str = Field(..., description="ID of the task to retrieve")


class MCPGetTaskDiscoveriesAction(Action):
    """Action to get discoveries made by a task."""

    task_id: str = Field(..., description="ID of the task")


class MCPGetWorkflowGraphAction(Action):
    """Action to get the workflow graph for a ticket."""

    ticket_id: str = Field(..., description="ID of the ticket")


class UpdateTaskStatusMCPTool(
    ToolDefinition[MCPUpdateTaskStatusAction, MCPToolsObservation]
):
    """Tool to update task status via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["UpdateTaskStatusMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(
            mcp_url,
            "update_task_status",
            ["task_id", "status", "result", "error_message"],
        )
        return [
            cls(
                name="mcp__update_task_status",
                description=(
                    "Update the status of a task. Use to mark tasks as running, completed, "
                    "failed, or cancelled. Include result data for completed tasks or "
                    "error messages for failed tasks."
                ),
                action_type=MCPUpdateTaskStatusAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class GetTaskMCPTool(ToolDefinition[MCPGetTaskAction, MCPToolsObservation]):
    """Tool to get task details via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["GetTaskMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(mcp_url, "get_task", ["task_id"])
        return [
            cls(
                name="mcp__get_task",
                description=(
                    "Get detailed information about a specific task including status, "
                    "dependencies, assigned agent, and results."
                ),
                action_type=MCPGetTaskAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class GetTaskDiscoveriesMCPTool(
    ToolDefinition[MCPGetTaskDiscoveriesAction, MCPToolsObservation]
):
    """Tool to get task discoveries via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["GetTaskDiscoveriesMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(mcp_url, "get_task_discoveries", ["task_id"])
        return [
            cls(
                name="mcp__get_task_discoveries",
                description=(
                    "Get all discoveries made by a specific task. Discoveries track "
                    "bugs, optimizations, or new requirements found during task execution."
                ),
                action_type=MCPGetTaskDiscoveriesAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class GetWorkflowGraphMCPTool(
    ToolDefinition[MCPGetWorkflowGraphAction, MCPToolsObservation]
):
    """Tool to get workflow graph via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["GetWorkflowGraphMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(mcp_url, "get_workflow_graph", ["ticket_id"])
        return [
            cls(
                name="mcp__get_workflow_graph",
                description=(
                    "Get the complete workflow graph for a ticket, showing all tasks, "
                    "discoveries, and their relationships. Use to understand the full "
                    "scope of work for a ticket."
                ),
                action_type=MCPGetWorkflowGraphAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


# ============================================================================
# Ticket Management Tools (MCP-backed)
# ============================================================================


class MCPGetTicketAction(Action):
    """Action to get a ticket's details."""

    ticket_id: str = Field(..., description="ID of the ticket to retrieve")


class MCPGetTicketHistoryAction(Action):
    """Action to get a ticket's change history."""

    ticket_id: str = Field(..., description="ID of the ticket")


class MCPResolveTicketAction(Action):
    """Action to resolve a ticket."""

    ticket_id: str = Field(..., description="ID of the ticket to resolve")
    resolution: str = Field(..., min_length=10, description="Resolution summary")
    commit_sha: Optional[str] = Field(
        default=None, description="Git commit SHA for the resolution"
    )


class MCPAddTicketCommentAction(Action):
    """Action to add a comment to a ticket."""

    ticket_id: str = Field(..., description="ID of the ticket")
    author_id: str = Field(..., description="ID of the comment author")
    content: str = Field(..., min_length=1, description="Comment content")


class MCPAddTicketDependencyAction(Action):
    """Action to add a dependency to a ticket."""

    ticket_id: str = Field(..., description="ID of the ticket")
    blocked_by_ticket_id: str = Field(..., description="ID of the blocking ticket")


class MCPRemoveTicketDependencyAction(Action):
    """Action to remove a dependency from a ticket."""

    ticket_id: str = Field(..., description="ID of the ticket")
    blocked_by_ticket_id: str = Field(
        ..., description="ID of the blocking ticket to remove"
    )


class GetTicketMCPTool(ToolDefinition[MCPGetTicketAction, MCPToolsObservation]):
    """Tool to get ticket details via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["GetTicketMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(mcp_url, "get_ticket", ["ticket_id"])
        return [
            cls(
                name="mcp__get_ticket",
                description=(
                    "Get detailed information about a specific ticket including status, "
                    "phase, priority, and related tasks."
                ),
                action_type=MCPGetTicketAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class GetTicketHistoryMCPTool(
    ToolDefinition[MCPGetTicketHistoryAction, MCPToolsObservation]
):
    """Tool to get ticket history via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["GetTicketHistoryMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(mcp_url, "get_ticket_history", ["ticket_id"])
        return [
            cls(
                name="mcp__get_ticket_history",
                description=(
                    "Get the complete change history for a ticket. Shows all status "
                    "transitions, field updates, comments, and commit linkages."
                ),
                action_type=MCPGetTicketHistoryAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class ResolveTicketMCPTool(ToolDefinition[MCPResolveTicketAction, MCPToolsObservation]):
    """Tool to resolve a ticket via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["ResolveTicketMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(
            mcp_url, "resolve_ticket", ["ticket_id", "resolution", "commit_sha"]
        )
        return [
            cls(
                name="mcp__resolve_ticket",
                description=(
                    "Resolve a ticket and automatically unblock dependent tickets. "
                    "Provide a resolution summary and optionally link the resolving commit."
                ),
                action_type=MCPResolveTicketAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class AddTicketCommentMCPTool(
    ToolDefinition[MCPAddTicketCommentAction, MCPToolsObservation]
):
    """Tool to add a comment to a ticket via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["AddTicketCommentMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(
            mcp_url, "add_ticket_comment", ["ticket_id", "author_id", "content"]
        )
        return [
            cls(
                name="mcp__add_ticket_comment",
                description=(
                    "Add a comment to a ticket. Use for notes, questions, or updates "
                    "that don't change the ticket's status."
                ),
                action_type=MCPAddTicketCommentAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class AddTicketDependencyMCPTool(
    ToolDefinition[MCPAddTicketDependencyAction, MCPToolsObservation]
):
    """Tool to add a ticket dependency via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["AddTicketDependencyMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(
            mcp_url, "add_ticket_dependency", ["ticket_id", "blocked_by_ticket_id"]
        )
        return [
            cls(
                name="mcp__add_ticket_dependency",
                description=(
                    "Add a blocker dependency to a ticket. The ticket will be marked as "
                    "blocked until the blocking ticket is resolved."
                ),
                action_type=MCPAddTicketDependencyAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class RemoveTicketDependencyMCPTool(
    ToolDefinition[MCPRemoveTicketDependencyAction, MCPToolsObservation]
):
    """Tool to remove a ticket dependency via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["RemoveTicketDependencyMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(
            mcp_url, "remove_ticket_dependency", ["ticket_id", "blocked_by_ticket_id"]
        )
        return [
            cls(
                name="mcp__remove_ticket_dependency",
                description=(
                    "Remove a blocker dependency from a ticket. Use when a dependency "
                    "is no longer relevant or was added in error."
                ),
                action_type=MCPRemoveTicketDependencyAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


# ============================================================================
# History & Trajectory Tools (MCP-backed)
# ============================================================================


class MCPGetPhaseHistoryAction(Action):
    """Action to get phase transition history for a ticket."""

    ticket_id: str = Field(..., description="ID of the ticket")


class MCPGetTaskTimelineAction(Action):
    """Action to get execution timeline for a task."""

    task_id: str = Field(..., description="ID of the task")


class MCPGetAgentTrajectoryAction(Action):
    """Action to get an agent's trajectory and context."""

    agent_id: str = Field(..., description="ID of the agent")


class MCPGetDiscoveriesByTypeAction(Action):
    """Action to get discoveries by type."""

    discovery_type: str = Field(
        ...,
        description="Type of discovery: bug, optimization, clarification_needed, etc.",
    )
    limit: int = Field(default=20, description="Maximum discoveries to return")


class GetPhaseHistoryMCPTool(
    ToolDefinition[MCPGetPhaseHistoryAction, MCPToolsObservation]
):
    """Tool to get phase history via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["GetPhaseHistoryMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(mcp_url, "get_phase_history", ["ticket_id"])
        return [
            cls(
                name="mcp__get_phase_history",
                description=(
                    "Get the phase transition history for a ticket. Shows when the ticket "
                    "moved between phases (Requirements → Implementation → Integration, etc.)."
                ),
                action_type=MCPGetPhaseHistoryAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class GetTaskTimelineMCPTool(
    ToolDefinition[MCPGetTaskTimelineAction, MCPToolsObservation]
):
    """Tool to get task timeline via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["GetTaskTimelineMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(mcp_url, "get_task_timeline", ["task_id"])
        return [
            cls(
                name="mcp__get_task_timeline",
                description=(
                    "Get the execution timeline for a task. Shows when the task was created, "
                    "assigned, started, and completed, along with any retries or errors."
                ),
                action_type=MCPGetTaskTimelineAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class GetAgentTrajectoryMCPTool(
    ToolDefinition[MCPGetAgentTrajectoryAction, MCPToolsObservation]
):
    """Tool to get agent trajectory via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["GetAgentTrajectoryMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(mcp_url, "get_agent_trajectory", ["agent_id"])
        return [
            cls(
                name="mcp__get_agent_trajectory",
                description=(
                    "Get an agent's accumulated context and trajectory summary. "
                    "Shows the agent's task history, discoveries, and learned patterns."
                ),
                action_type=MCPGetAgentTrajectoryAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


class GetDiscoveriesByTypeMCPTool(
    ToolDefinition[MCPGetDiscoveriesByTypeAction, MCPToolsObservation]
):
    """Tool to get discoveries by type via MCP."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **kwargs
    ) -> Sequence["GetDiscoveriesByTypeMCPTool"]:
        mcp_url = kwargs.get("mcp_url", "http://localhost:18000/mcp/")
        executor = _create_mcp_executor(
            mcp_url, "get_discoveries_by_type", ["discovery_type", "limit"]
        )
        return [
            cls(
                name="mcp__get_discoveries_by_type",
                description=(
                    "Get all discoveries of a specific type across the system. "
                    "Useful for finding patterns like recurring bugs or optimization opportunities."
                ),
                action_type=MCPGetDiscoveriesByTypeAction,
                observation_type=MCPToolsObservation,
                executor=executor,
            )
        ]


# ============================================================================
# Tool Registration
# ============================================================================


def get_mcp_tools(mcp_url: str = "http://localhost:18000/mcp/") -> List[type]:
    """Get all MCP tool classes for registration.

    Args:
        mcp_url: URL of the MCP server

    Returns:
        List of tool definition classes
    """
    return [
        # Core MCP tools
        ListMCPToolsTool,
        CallMCPToolTool,
        # Ticket management
        CreateTicketMCPTool,
        GetTicketMCPTool,
        GetTicketHistoryMCPTool,
        ResolveTicketMCPTool,
        AddTicketCommentMCPTool,
        AddTicketDependencyMCPTool,
        RemoveTicketDependencyMCPTool,
        # Task management
        CreateTaskMCPTool,
        UpdateTaskStatusMCPTool,
        GetTaskMCPTool,
        GetTaskDiscoveriesMCPTool,
        GetWorkflowGraphMCPTool,
        # Collaboration
        BroadcastMessageMCPTool,
        SendMessageMCPTool,
        GetMessagesMCPTool,
        RequestHandoffMCPTool,
        # History & Trajectory
        GetPhaseHistoryMCPTool,
        GetTaskTimelineMCPTool,
        GetAgentTrajectoryMCPTool,
        GetDiscoveriesByTypeMCPTool,
    ]


def register_mcp_tools_with_agent(
    agent_tools: List,
    mcp_url: str = "http://localhost:18000/mcp/",
    conv_state: Any = None,
) -> List:
    """Register all MCP tools with an agent's tool list.

    This provides agents with full access to:
    - Ticket management (create, update, resolve, dependencies)
    - Task management (create, update status, get discoveries)
    - Collaboration (messaging, handoffs)
    - History & Trajectory (phase history, timelines, agent context)

    Args:
        agent_tools: Existing list of agent tools
        mcp_url: URL of the MCP server
        conv_state: Conversation state (can be None for creation)

    Returns:
        Extended list of tools including all MCP tools
    """
    mcp_tool_classes = get_mcp_tools(mcp_url)

    for tool_cls in mcp_tool_classes:
        tools = tool_cls.create(conv_state, mcp_url=mcp_url)
        agent_tools.extend(tools)

    return agent_tools
