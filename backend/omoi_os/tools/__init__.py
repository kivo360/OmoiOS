"""OmoiOS Tools Package.

This package provides OpenHands-native tools that allow agents to interact
with OmoiOS backend services like task management, collaboration, and planning.

Tools are organized into:
- **Task tools**: Create/update tasks, track discoveries
- **Collaboration tools**: Agent messaging and handoffs
- **Planning tools**: Context gathering and analysis
- **MCP tools**: Access MCP server tools from distributed agents
"""

from omoi_os.tools.task_tools import (
    initialize_task_tool_services,
    register_omoi_task_tools,
)
from omoi_os.tools.collaboration_tools import (
    initialize_collaboration_tool_services,
    register_omoi_collaboration_tools,
)
from omoi_os.tools.planning_tools import (
    initialize_planning_tool_services,
    register_omoi_planning_tools,
)
from omoi_os.tools.mcp_tools import (
    # Registration functions
    get_mcp_tools,
    register_mcp_tools_with_agent,
    # Core MCP tools
    ListMCPToolsTool,
    CallMCPToolTool,
    # Ticket management tools
    CreateTicketMCPTool,
    GetTicketMCPTool,
    GetTicketsMCPTool,
    GetTicketHistoryMCPTool,
    UpdateTicketMCPTool,
    ChangeTicketStatusMCPTool,
    ResolveTicketMCPTool,
    SearchTicketsMCPTool,
    AddTicketCommentMCPTool,
    AddTicketDependencyMCPTool,
    RemoveTicketDependencyMCPTool,
    LinkCommitMCPTool,
    # Task management tools
    CreateTaskMCPTool,
    UpdateTaskStatusMCPTool,
    GetTaskMCPTool,
    GetTaskDiscoveriesMCPTool,
    GetWorkflowGraphMCPTool,
    # Collaboration tools
    BroadcastMessageMCPTool,
    SendMessageMCPTool,
    GetMessagesMCPTool,
    RequestHandoffMCPTool,
    # History & Trajectory tools
    GetPhaseHistoryMCPTool,
    GetTaskTimelineMCPTool,
    GetAgentTrajectoryMCPTool,
    GetDiscoveriesByTypeMCPTool,
)

_registered = False


def register_omoi_tools() -> None:
    """Register all OmoiOS tools with OpenHands.

    This should be called once after initializing the tool services.
    """
    global _registered
    if _registered:
        return

    register_omoi_task_tools()
    register_omoi_collaboration_tools()
    register_omoi_planning_tools()

    _registered = True


__all__ = [
    # Task tools (native)
    "initialize_task_tool_services",
    "register_omoi_task_tools",
    # Collaboration tools (native)
    "initialize_collaboration_tool_services",
    "register_omoi_collaboration_tools",
    # Planning tools (native)
    "initialize_planning_tool_services",
    "register_omoi_planning_tools",
    # MCP tools (for distributed agents)
    "get_mcp_tools",
    "register_mcp_tools_with_agent",
    # Core MCP tools
    "ListMCPToolsTool",
    "CallMCPToolTool",
    # Ticket management MCP tools
    "CreateTicketMCPTool",
    "GetTicketMCPTool",
    "GetTicketsMCPTool",
    "GetTicketHistoryMCPTool",
    "UpdateTicketMCPTool",
    "ChangeTicketStatusMCPTool",
    "ResolveTicketMCPTool",
    "SearchTicketsMCPTool",
    "AddTicketCommentMCPTool",
    "AddTicketDependencyMCPTool",
    "RemoveTicketDependencyMCPTool",
    "LinkCommitMCPTool",
    # Task management MCP tools
    "CreateTaskMCPTool",
    "UpdateTaskStatusMCPTool",
    "GetTaskMCPTool",
    "GetTaskDiscoveriesMCPTool",
    "GetWorkflowGraphMCPTool",
    # Collaboration MCP tools
    "BroadcastMessageMCPTool",
    "SendMessageMCPTool",
    "GetMessagesMCPTool",
    "RequestHandoffMCPTool",
    # History & Trajectory MCP tools
    "GetPhaseHistoryMCPTool",
    "GetTaskTimelineMCPTool",
    "GetAgentTrajectoryMCPTool",
    "GetDiscoveriesByTypeMCPTool",
    # Combined registration
    "register_omoi_tools",
]
