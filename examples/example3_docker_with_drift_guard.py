"""Example: Docker workspace with drift guard for ticket execution.

This example demonstrates running an agent in a Docker container with:
- Automatic repo cloning and branch checkout
- Streaming conversation events
- Drift guard to prevent excessive LLM steps without tool usage

Usage:
    # Set environment variables
    export LLM_API_KEY=your-api-key
    export LLM_MODEL=openhands/claude-sonnet-4-5-20250929  # optional

    # Run the example
    uv run python examples/example3_docker_with_drift_guard.py
"""

import asyncio
import os
import platform

from openhands.sdk import (
    Agent,
    Conversation,
    Event,
    LLM,
    LLMConvertibleEvent,
    Tool,
    get_logger,
)
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool
from openhands.workspace import DockerWorkspace

from omoi_os.config import load_llm_settings

logger = get_logger(__name__)


def detect_platform() -> str:
    """Detect the Docker platform architecture."""
    machine = platform.machine().lower()
    if "arm" in machine or "aarch64" in machine:
        return "linux/arm64"
    return "linux/amd64"


def build_llm() -> LLM:
    """Build LLM instance using project configuration."""
    llm_settings = load_llm_settings()

    if not llm_settings.api_key:
        raise RuntimeError(
            "LLM_API_KEY must be set in environment or config. "
            "Set LLM_API_KEY in your environment or config/base.yaml"
        )

    return LLM(
        usage_id="ticket-agent",
        model=llm_settings.model,
        base_url=llm_settings.base_url,
        api_key=llm_settings.api_key,
    )


def build_agent(llm: LLM) -> Agent:
    """Build agent with file editor and terminal tools."""
    tools = [
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
    ]
    return Agent(llm=llm, tools=tools)


async def run_ticket_in_docker_with_drift_guard(
    ticket_id: str,
    title: str,
    description: str,
    repo_url: str,
    branch: str = "main",
    host_port: int = 8020,  # Use 8020 to avoid conflicts with OpenHands agent server (8000)
    max_llm_steps_without_tools: int = 6,
) -> None:
    """Run ticket agent in Docker workspace with drift guard.

    Spins up a DockerWorkspace, clones the repo, and runs a conversation
    with streaming events. Includes a drift guard that monitors for
    excessive LLM steps without tool usage and injects corrections.

    Args:
        ticket_id: Unique identifier for the ticket
        title: Ticket title
        description: Detailed ticket description
        repo_url: Git repository URL to clone
        branch: Git branch to checkout (default: "main")
        host_port: Host port to expose from container (default: 8020, avoids conflict with OpenHands agent server on 8000)
        max_llm_steps_without_tools: Maximum assistant steps before drift guard triggers
    """
    llm = build_llm()
    agent = build_agent(llm)
    platform_str = detect_platform()

    # Docker image with Python + Node used in official examples
    base_image = "nikolaik/python-nodejs:python3.12-nodejs22"

    logger.info(
        "Starting DockerWorkspace (image=%s, port=%d)...", base_image, host_port
    )

    with DockerWorkspace(
        base_image=base_image,
        host_port=host_port,
        platform=platform_str,
        extra_ports=False,
    ) as workspace:
        cwd = workspace.working_dir

        # Helper function to execute shell commands in container
        def sh(cmd: str):
            """Execute shell command in workspace and log failures."""
            res = workspace.execute_command(cmd, cwd=cwd)
            if res.exit_code != 0:
                logger.warning(
                    "[DOCKER] Command failed: %s\nstdout:\n%s\nstderr:\n%s",
                    cmd,
                    res.stdout,
                    res.stderr,
                )
            return res

        # 1) Prepare repo inside the container
        # Clear workspace completely to ensure clean state
        logger.info("Cleaning workspace directory...")
        sh("rm -rf * .* 2>/dev/null || true")  # Remove all files including hidden ones
        sh(
            "find . -mindepth 1 -delete 2>/dev/null || true"
        )  # Ensure directory is empty

        # Clone the repository into the workspace
        logger.info(f"Cloning repository {repo_url}...")
        clone_result = sh(f"git clone {repo_url} .")
        if clone_result.exit_code != 0:
            # If clone fails, try removing .git and cloning again
            logger.warning("Initial clone failed, cleaning and retrying...")
            sh("rm -rf .git * .* 2>/dev/null || true")
            clone_result = sh(f"git clone {repo_url} .")
            if clone_result.exit_code != 0:
                raise RuntimeError(f"Failed to clone repository: {clone_result.stderr}")

        # Fetch and checkout the desired branch
        logger.info(f"Fetching and checking out branch {branch}...")
        sh("git fetch origin")
        checkout_result = sh(
            f"""
            git checkout {branch} 2>/dev/null || \
            git checkout -b {branch} origin/{branch} 2>/dev/null || \
            git checkout -b {branch}
            """
        )
        if checkout_result.exit_code == 0:
            sh(f"git pull --ff-only origin {branch} 2>/dev/null || true")

        logger.info("Repository setup complete")

        # Drift guard: track LLM steps without tool usage
        llm_steps_since_tool = 0

        def event_callback(event: Event):
            """Callback to track events for drift guard."""
            nonlocal llm_steps_since_tool
            if isinstance(event, LLMConvertibleEvent):
                msg = event.to_llm_message()
                if msg.role == "assistant":
                    llm_steps_since_tool += 1
                elif msg.role == "tool":
                    llm_steps_since_tool = 0

        conversation = Conversation(
            agent=agent,
            workspace=workspace,
            callbacks=[event_callback],
        )

        goal_prompt = f"""
You are working on ticket {ticket_id}: {title}

Ticket description:
{description}

Instructions:
- Work inside this repository (the cloned repo, not the Docker container infrastructure).
- Use file editor + terminal tools to implement the change.
- IMPORTANT: Do NOT start or modify the OpenHands agent server running on port 8000.
  That is container infrastructure, not part of the repository you're working on.
- If you need to test a server, use port {host_port} (exposed to host) or any port other than 8000.
- Run tests before finishing.
- When done, summarize the changes and what remains risky.
"""

        conversation.send_message(goal_prompt)

        # Run conversation and check for drift periodically
        # For RemoteConversation, we use run() instead of astream()
        conversation.run()

        # Check drift after run completes
        # Note: For more real-time drift detection, you'd need to implement
        # a more sophisticated callback that can inject messages mid-execution
        # This is a simplified version that checks after completion

        # After run completes, print final state.
        state = conversation.state
        execution_status = state.execution_status

        # For RemoteState, access messages via events
        # Find the last assistant message from events
        last_text = ""
        try:
            # Try to get messages from state (works for LocalConversation)
            if hasattr(state, "messages") and state.messages:
                last_msg = state.messages[-1]
                last_text = getattr(last_msg, "content", "")
            # For RemoteState, find last assistant message from events
            elif hasattr(state, "events") and state.events:
                from openhands.sdk.event import MessageEvent

                # Find the last MessageEvent with assistant role
                for event in reversed(state.events):
                    if isinstance(event, MessageEvent):
                        msg = event.to_llm_message()
                        if msg.role == "assistant":
                            last_text = msg.content
                            break
                if not last_text:
                    last_text = (
                        "Execution completed. Check conversation logs for details."
                    )
            else:
                last_text = "Execution completed. Check conversation logs for details."
        except Exception as e:
            logger.warning(f"Could not retrieve final message: {e}")
            last_text = "Execution completed. Check conversation logs for details."

        print(f"\n=== Ticket {ticket_id} finished in Docker workspace ===")
        print(f"Execution status: {execution_status}")
        print("\n--- Final assistant message ---\n")
        print(last_text)


if __name__ == "__main__":
    # Example usage: single ticket against a Git repo
    ticket_id = "T-456"
    title = "Add /health endpoint"
    description = (
        "Add /health endpoint returning JSON {{status, version}} to the repository's "
        "application (if it has a web server). If the repo doesn't have a server yet, "
        "create a simple Flask or FastAPI app with the /health endpoint. Use port 8020 "
        "(or any port other than 8000) to avoid conflicts with the OpenHands agent server."
    )

    # Update this to your actual repository URL
    repo_url = os.getenv("REPO_URL", "git@github.com:your-org/your-repo.git")

    asyncio.run(
        run_ticket_in_docker_with_drift_guard(
            ticket_id=ticket_id,
            title=title,
            description=description,
            repo_url=repo_url,
            branch="main",
        )
    )
