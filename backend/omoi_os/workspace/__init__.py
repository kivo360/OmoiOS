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

__all__ = [
    "CommandExecutor",
    "CommandResult",
    "DockerCommandExecutor",
    "DockerWorkspaceManager",
    "LocalCommandExecutor",
    "LocalWorkspaceManager",
    "RepositoryManager",
    "WorkspaceManager",
    "detect_platform",
    "find_available_port",
]
