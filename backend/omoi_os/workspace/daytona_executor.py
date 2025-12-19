"""
Daytona Tool Executor

Custom tool executor that routes SDK tool commands to Daytona sandboxes
instead of local execution.

This allows OpenHands SDK tools (terminal, file_editor, etc.) to execute
in Daytona cloud sandboxes.
"""

from typing import TYPE_CHECKING, Any

from openhands.sdk.tool import ToolExecutor
from openhands.sdk.llm.message import TextContent
from openhands.tools.terminal.definition import (
    ExecuteBashAction,
    ExecuteBashObservation,
)
from openhands.tools.terminal.metadata import CmdOutputMetadata

from omoi_os.logging import get_logger

if TYPE_CHECKING:
    from omoi_os.workspace.daytona_sdk import DaytonaLocalWorkspace

logger = get_logger(__name__)


class DaytonaTerminalExecutor(ToolExecutor):
    """Execute terminal commands in Daytona sandbox.

    This executor wraps a DaytonaLocalWorkspace and routes all command
    execution through the Daytona API instead of local subprocess.

    Usage:
        workspace = DaytonaLocalWorkspace(...)
        with workspace:
            executor = DaytonaTerminalExecutor(workspace)
            # Pass executor to TerminalTool.create()
    """

    def __init__(self, workspace: "DaytonaLocalWorkspace"):
        """Initialize with a Daytona workspace.

        Args:
            workspace: An initialized DaytonaLocalWorkspace (must be in context)
        """
        self.workspace = workspace
        self._working_dir = workspace._daytona_workspace.working_dir if workspace._daytona_workspace else "/workspace"

    def __call__(self, action: ExecuteBashAction, conversation: Any = None) -> ExecuteBashObservation:
        """Execute a bash command in the Daytona sandbox.

        Args:
            action: The bash action to execute
            conversation: Optional conversation context (unused)

        Returns:
            ExecuteBashObservation with command output
        """
        command = action.command
        timeout = action.timeout or 30.0

        logger.debug(f"Executing in Daytona: {command}")

        try:
            result = self.workspace.execute_command(
                command=command,
                cwd=self._working_dir,
                timeout=timeout,
            )

            # Build metadata
            metadata = CmdOutputMetadata(
                exit_code=result.exit_code,
                working_dir=self._working_dir,
                py_interpreter_path=None,
                prefix="",
                suffix="",
            )

            output = result.stdout + result.stderr
            return ExecuteBashObservation(
                content=[TextContent(text=output)],
                command=command,
                exit_code=result.exit_code,
                timeout=result.timeout_occurred,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Daytona command execution failed: {e}")
            return ExecuteBashObservation(
                content=[TextContent(text=f"Error: {str(e)}")],
                command=command,
                exit_code=1,
                is_error=True,
                metadata=CmdOutputMetadata(exit_code=1, working_dir=self._working_dir),
            )

    def close(self) -> None:
        """Cleanup - workspace cleanup is handled separately."""
        pass


# Global reference to active Daytona workspace for tool execution
_ACTIVE_DAYTONA_WORKSPACE: "DaytonaLocalWorkspace | None" = None


def set_active_daytona_workspace(workspace: "DaytonaLocalWorkspace | None") -> None:
    """Set the active Daytona workspace for tool execution.

    This must be called before creating a Conversation to ensure
    tools execute in Daytona instead of locally.
    """
    global _ACTIVE_DAYTONA_WORKSPACE
    _ACTIVE_DAYTONA_WORKSPACE = workspace


def _daytona_terminal_factory(conv_state, **params):
    """Custom terminal tool factory that uses Daytona executor."""
    from openhands.tools.terminal.definition import (
        TerminalTool,
        ExecuteBashAction,
        ExecuteBashObservation,
        TOOL_DESCRIPTION,
    )
    from openhands.sdk.tool import ToolAnnotations

    global _ACTIVE_DAYTONA_WORKSPACE

    if _ACTIVE_DAYTONA_WORKSPACE is not None and _ACTIVE_DAYTONA_WORKSPACE.is_initialized:
        # Use Daytona executor
        executor = DaytonaTerminalExecutor(_ACTIVE_DAYTONA_WORKSPACE)
        logger.info("Using Daytona executor for terminal tool")
    else:
        # Fall back to default local executor
        logger.info("Using local executor for terminal tool")
        return TerminalTool.create(conv_state, **params)

    return [
        TerminalTool(
            action_type=ExecuteBashAction,
            observation_type=ExecuteBashObservation,
            description=TOOL_DESCRIPTION,
            annotations=ToolAnnotations(
                title="terminal",
                readOnlyHint=False,
                destructiveHint=True,
                idempotentHint=False,
                openWorldHint=True,
            ),
            executor=executor,
        )
    ]


def register_daytona_tools() -> None:
    """Register Daytona-aware tool factories.

    Call this once at startup to override the default tool registrations
    with Daytona-aware versions.

    Example:
        from omoi_os.workspace.daytona_executor import register_daytona_tools, set_active_daytona_workspace

        register_daytona_tools()  # Once at startup

        workspace = DaytonaLocalWorkspace(...)
        with workspace:
            set_active_daytona_workspace(workspace)
            conv = Conversation(agent=agent, workspace=workspace)
            conv.send_message("Run: uname -s")
            conv.run()  # Commands run in Daytona!
            set_active_daytona_workspace(None)
    """
    from openhands.sdk.tool.registry import register_tool

    # Override terminal tool with Daytona-aware factory
    register_tool("terminal", _daytona_terminal_factory)
    logger.info("Registered Daytona-aware terminal tool")
