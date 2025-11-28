"""OmoiOS Tools Package.

This package provides OpenHands-native tools that allow agents to interact
with OmoiOS backend services like task management, collaboration, and planning.
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
    # Task tools
    "initialize_task_tool_services",
    "register_omoi_task_tools",
    # Collaboration tools
    "initialize_collaboration_tool_services",
    "register_omoi_collaboration_tools",
    # Planning tools
    "initialize_planning_tool_services",
    "register_omoi_planning_tools",
    # Combined registration
    "register_omoi_tools",
]
