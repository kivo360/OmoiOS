"""Workspace management module for OmoiOS.

Provides classes for managing isolated workspaces, executing commands,
and handling Git repository operations.
"""

from omoi_os.workspace.managers import (
    CommandExecutor,
    CommandResult,
    DockerCommandExecutor,
    DockerWorkspaceManager,
    LocalCommandExecutor,
    LocalWorkspaceManager,
    RepositoryManager,
    WorkspaceManager,
    detect_platform,
    find_available_port,
)
from omoi_os.workspace.daytona import (
    AsyncDaytonaCommandExecutor,
    DaytonaCommandExecutor,
    DaytonaWorkspace,
    DaytonaWorkspaceConfig,
    DaytonaWorkspaceManager,
    OpenHandsDaytonaWorkspace,
)

__all__ = [
    # Base classes
    "CommandExecutor",
    "CommandResult",
    "RepositoryManager",
    "WorkspaceManager",
    # Local
    "LocalCommandExecutor",
    "LocalWorkspaceManager",
    # Docker
    "DockerCommandExecutor",
    "DockerWorkspaceManager",
    # Daytona
    "AsyncDaytonaCommandExecutor",
    "DaytonaCommandExecutor",
    "DaytonaWorkspace",
    "DaytonaWorkspaceConfig",
    "DaytonaWorkspaceManager",
    "OpenHandsDaytonaWorkspace",
    # Utilities
    "detect_platform",
    "find_available_port",
]
