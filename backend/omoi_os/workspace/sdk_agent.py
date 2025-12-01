"""
SDK Agent Helper

Provides convenient functions for creating OpenHands agents with tools
that execute in Daytona cloud sandboxes.

Usage:
    from omoi_os.workspace.sdk_agent import create_daytona_agent, run_task

    # Quick one-liner
    result = run_task("Create a Python script that prints hello world and run it")

    # Or manual control
    workspace, agent = create_daytona_agent()
    with workspace:
        conversation = Conversation(agent=agent, workspace=workspace)
        conversation.send_message("Your task here")
        conversation.run()
        conversation.close()
"""

from typing import Optional

from pydantic import SecretStr

# Register tools by importing them
from openhands.tools.terminal import TerminalTool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.grep import GrepTool
from openhands.tools.glob import GlobTool
from openhands.tools.task_tracker import TaskTrackerTool

from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.sdk.tool.registry import list_registered_tools

from omoi_os.config import load_daytona_settings, load_llm_settings
from omoi_os.workspace.daytona_sdk import DaytonaLocalWorkspace


# All available tool names
ALL_TOOLS = ["terminal", "file_editor", "grep", "glob", "task_tracker"]


def create_daytona_agent(
    project_id: str = "sdk-agent",
    tools: Optional[list[str]] = None,
    working_dir: str = "/tmp/sdk-workspace",
) -> tuple[DaytonaLocalWorkspace, Agent]:
    """Create a Daytona workspace and agent with tools.

    Args:
        project_id: Identifier for the Daytona sandbox
        tools: List of tool names to enable. Defaults to all tools.
        working_dir: Local staging directory

    Returns:
        Tuple of (DaytonaLocalWorkspace, Agent)

    Example:
        workspace, agent = create_daytona_agent()
        with workspace:
            conv = Conversation(agent=agent, workspace=workspace)
            conv.send_message("Hello")
            conv.run()
            conv.close()
    """
    # Load settings
    daytona = load_daytona_settings()
    llm_settings = load_llm_settings()

    if not daytona.api_key:
        raise ValueError("DAYTONA_API_KEY not configured")
    if not llm_settings.api_key:
        raise ValueError("LLM API key not configured")

    # Create workspace
    workspace = DaytonaLocalWorkspace(
        working_dir=working_dir,
        daytona_api_key=daytona.api_key,
        daytona_api_url=daytona.api_url,
        sandbox_image=daytona.image,
        project_id=project_id,
    )

    # Create LLM
    llm = LLM(
        model=llm_settings.model,
        api_key=SecretStr(llm_settings.api_key),
        base_url=llm_settings.base_url,
    )

    # Create agent with tools
    tool_names = tools or ALL_TOOLS
    tool_specs = [Tool(name=name) for name in tool_names if name in list_registered_tools()]

    agent = Agent(llm=llm, tools=tool_specs)

    return workspace, agent


def run_task(
    task: str,
    project_id: str = "quick-task",
    tools: Optional[list[str]] = None,
) -> dict:
    """Run a task with an agent in a Daytona sandbox.

    This is a convenience function that creates a workspace, runs the task,
    and cleans up automatically.

    Args:
        task: The task description to send to the agent
        project_id: Identifier for the Daytona sandbox
        tools: List of tool names to enable. Defaults to all tools.

    Returns:
        Dictionary with execution results:
        - status: Execution status
        - events: Number of events generated
        - sandbox_id: Daytona sandbox ID used

    Example:
        result = run_task("Create a file called test.txt with 'hello' and read it back")
        print(result["status"])
    """
    workspace, agent = create_daytona_agent(project_id=project_id, tools=tools)

    with workspace:
        conversation = Conversation(agent=agent, workspace=workspace)
        conversation.send_message(task)
        conversation.run()

        result = {
            "status": str(conversation.state.execution_status),
            "events": len(conversation.state.events),
            "sandbox_id": workspace.sandbox_id,
            "conversation_id": str(conversation.id),
        }

        conversation.close()

    return result


def get_available_tools() -> list[str]:
    """Get list of all registered tool names."""
    return list_registered_tools()
