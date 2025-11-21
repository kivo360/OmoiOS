"""Example: Basic ticket run using OpenHands SDK.

This example demonstrates how to run an agent for a single ticket
in an isolated workspace directory.

Usage:
    # Set environment variables
    export LLM_API_KEY=your-api-key
    export LLM_MODEL=openhands/claude-sonnet-4-5-20250929  # optional

    # Run the example
    uv run python examples/example1_basic_ticket_run.py
"""

import os
from pathlib import Path

from openhands.sdk import Agent, Conversation, LLM, Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

from omoi_os.config import load_llm_settings


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


def run_agent_for_ticket(
    ticket_id: str,
    title: str,
    description: str,
    workspace_dir: str,
) -> None:
    """Run agent for a single ticket in an isolated workspace.
    
    Args:
        ticket_id: Unique identifier for the ticket
        title: Ticket title
        description: Detailed ticket description
        workspace_dir: Directory path for the isolated workspace
    """
    llm = build_llm()
    agent = build_agent(llm)
    
    # Ensure workspace directory exists
    workspace_path = Path(workspace_dir)
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    conversation = Conversation(
        agent=agent,
        workspace=str(workspace_path.absolute()),
    )
    
    goal_prompt = f"""
You are working on ticket {ticket_id}: {title}

Ticket description:
{description}

Requirements:
- Work directly in this repository.
- Use the file editor tool to inspect and modify code and tests.
- Use the terminal tool to run tests or commands.
- When you believe the ticket is complete, provide a short summary of the changes.
"""
    
    conversation.send_message(goal_prompt)
    conversation.run()
    
    state = conversation.state
    last_msg = state.messages[-1] if state.messages else None
    last_text = getattr(last_msg, "content", "") if last_msg else ""
    
    print(f"\n=== Ticket {ticket_id} run finished ===")
    print(f"Execution status: {state.execution_status}")
    print("\n--- Final assistant message ---\n")
    print(last_text)


if __name__ == "__main__":
    # Example ticket data - modify as needed
    ticket_id = "T-123"
    title = "Add /health endpoint"
    description = (
        "Add a /health endpoint that returns JSON {{status, version}} "
        "and wire it into the router."
    )
    
    # Use a temporary workspace directory for isolation
    # In production, this would be a dedicated workspace per ticket
    workspace_dir = os.path.join(os.getcwd(), "examples", "workspaces", ticket_id)
    
    run_agent_for_ticket(ticket_id, title, description, workspace_dir)

