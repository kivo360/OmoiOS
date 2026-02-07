"""Sandbox Worker Entrypoint for OmoiOS.

This script runs INSIDE a Daytona sandbox and connects back to the OmoiOS
MCP server to execute tasks. It's the bridge between isolated execution
and centralized coordination.

Environment Variables Required:
    AGENT_ID: Assigned agent identifier
    TASK_ID: Task to execute
    MCP_SERVER_URL: URL of the OmoiOS MCP server (e.g., http://host:18000/mcp)

Optional Environment Variables:
    LLM_API_KEY: API key for LLM provider
    LLM_MODEL: Model to use (default: from config)
    AGENT_TYPE: Agent template to use (default: auto from phase)
    DAYTONA_API_KEY: For workspace operations
    LOG_LEVEL: Logging level (default: INFO)

Usage:
    # Inside Daytona sandbox
    AGENT_ID=agent-123 TASK_ID=task-456 MCP_SERVER_URL=http://host:18000/mcp \
        python -m omoi_os.sandbox_worker
"""

import asyncio
import os
import sys
from typing import Any, Dict, Optional

from pydantic import SecretStr

# Configure structured logging before any other imports that might log
from omoi_os.logging import configure_logging, get_logger

import logging as stdlib_logging  # Only for log level constants

_env = os.environ.get("OMOIOS_ENV", "development")
_log_level = os.environ.get("LOG_LEVEL", "INFO")
configure_logging(
    env=_env,  # type: ignore[arg-type]
    log_level=getattr(stdlib_logging, _log_level),
)
logger = get_logger("sandbox_worker")


async def run_sandbox_worker():
    """Main entry point for sandbox worker."""

    # ==========================================================================
    # 1. Load Environment Configuration
    # ==========================================================================

    agent_id = os.environ.get("AGENT_ID")
    task_id = os.environ.get("TASK_ID")
    mcp_server_url = os.environ.get("MCP_SERVER_URL")
    sandbox_id = os.environ.get("SANDBOX_ID")  # Daytona sandbox identifier

    if not agent_id:
        logger.error("AGENT_ID environment variable required")
        sys.exit(1)
    if not task_id:
        logger.error("TASK_ID environment variable required")
        sys.exit(1)
    if not mcp_server_url:
        logger.error("MCP_SERVER_URL environment variable required")
        sys.exit(1)

    logger.info(f"Sandbox worker starting: agent={agent_id}, task={task_id}")
    logger.info(f"MCP server: {mcp_server_url}")

    # ==========================================================================
    # 2. Connect to MCP Server
    # ==========================================================================

    from omoi_os.services.mcp_client import MCPClientService

    mcp_client = MCPClientService(mcp_url=mcp_server_url)

    try:
        await mcp_client.connect()
        logger.info("Connected to MCP server")
    except Exception as e:
        logger.error(f"Failed to connect to MCP server: {e}")
        sys.exit(1)

    try:
        # ======================================================================
        # 3. Fetch Task Details via MCP
        # ======================================================================

        logger.info(f"Fetching task {task_id}...")
        task_result = await mcp_client.call_tool("get_task", {"task_id": task_id})

        if not task_result or "error" in str(task_result).lower():
            logger.error(f"Failed to fetch task: {task_result}")
            sys.exit(1)

        task_data = (
            task_result
            if isinstance(task_result, dict)
            else {"description": str(task_result)}
        )
        task_description = task_data.get("description", "No description")
        phase_id = task_data.get("phase_id", "PHASE_IMPLEMENTATION")
        ticket_id = task_data.get("ticket_id")

        logger.info(f"Task: {task_description[:100]}...")
        logger.info(f"Phase: {phase_id}")

        # ======================================================================
        # 4. Update Task Status to Running
        # ======================================================================

        logger.info("Updating task status to 'running'...")
        await mcp_client.call_tool(
            "update_task_status",
            {
                "task_id": task_id,
                "status": "running",
            },
        )

        # ======================================================================
        # 5. Load Agent Template Based on Phase
        # ======================================================================

        from omoi_os.agents.templates import (
            get_template_for_phase,
            AgentType,
            get_template,
        )

        # Allow override via env var
        agent_type_override = os.environ.get("AGENT_TYPE")
        if agent_type_override:
            template = get_template(AgentType(agent_type_override))
        else:
            template = get_template_for_phase(phase_id)

        logger.info(f"Using agent template: {template.name}")

        # ======================================================================
        # 6. Load Phase Context for Prompt Injection
        # ======================================================================

        phase_prompt = None
        try:
            # Try to get phase history which includes phase context
            if ticket_id:
                phase_history = await mcp_client.call_tool(
                    "get_phase_history", {"ticket_id": ticket_id}
                )
                # Extract phase prompt from context if available
                if isinstance(phase_history, dict):
                    phase_prompt = phase_history.get("current_phase", {}).get(
                        "phase_prompt"
                    )
        except Exception as e:
            logger.warning(f"Could not load phase context: {e}")

        # Build complete system prompt
        system_prompt = template.build_system_prompt(phase_prompt)

        # ======================================================================
        # 7. Create OpenHands Agent with MCP Tools
        # ======================================================================

        from omoi_os.config import load_llm_settings, load_daytona_settings
        from omoi_os.workspace.daytona_sdk import DaytonaLocalWorkspace
        from omoi_os.tools.mcp_tools import register_mcp_tools_with_agent

        from openhands.sdk import LLM, Agent, Conversation, Tool
        from openhands.sdk.tool.registry import list_registered_tools

        # Load LLM settings (can be overridden by env vars)
        llm_settings = load_llm_settings()
        llm_api_key = os.environ.get("LLM_API_KEY", llm_settings.api_key)
        llm_model = os.environ.get("LLM_MODEL", llm_settings.model)

        if not llm_api_key:
            logger.error("LLM_API_KEY required")
            sys.exit(1)

        # Create LLM
        llm = LLM(
            model=llm_model,
            api_key=SecretStr(llm_api_key),
            base_url=llm_settings.base_url,
        )

        # Get SDK tools based on template
        sdk_tool_names = template.tools.get_sdk_tools()
        sdk_tools = [
            Tool(name=name)
            for name in sdk_tool_names
            if name in list_registered_tools()
        ]

        logger.info(f"SDK tools: {sdk_tool_names}")

        # Create agent
        agent = Agent(llm=llm, tools=sdk_tools)

        # Register MCP tools with the agent
        # This gives the agent access to tickets, tasks, collaboration, etc.
        mcp_tools = register_mcp_tools_with_agent(
            agent_tools=[],
            mcp_url=mcp_server_url,
            conv_state=None,
        )

        logger.info(f"MCP tools registered: {len(mcp_tools)}")

        # ======================================================================
        # 8. Create Workspace (Daytona or Local)
        # ======================================================================

        daytona_settings = load_daytona_settings()
        daytona_api_key = os.environ.get("DAYTONA_API_KEY", daytona_settings.api_key)

        # Determine working directory
        working_dir = os.environ.get("WORKSPACE_DIR", "/workspace")

        if daytona_api_key:
            # Running in Daytona - use Daytona workspace
            workspace = DaytonaLocalWorkspace(
                working_dir=working_dir,
                daytona_api_key=daytona_api_key,
                daytona_api_url=daytona_settings.api_url,
                project_id=f"task-{task_id[:8]}",
            )
            logger.info("Using Daytona workspace")
        else:
            # Local mode - use LocalWorkspace
            from openhands.sdk.workspace import LocalWorkspace
            import tempfile

            if not os.path.exists(working_dir):
                working_dir = tempfile.mkdtemp(prefix="omoios_")

            workspace = LocalWorkspace(working_dir=working_dir)
            logger.info(f"Using local workspace: {working_dir}")

        # ======================================================================
        # 9. Execute Task with OpenHands Conversation
        # ======================================================================

        result: Dict[str, Any] = {}

        with workspace:
            logger.info("Workspace initialized, starting conversation...")

            # Create event callback to stream actions to server for Guardian observation
            async def on_agent_event(event):
                """Stream agent events back to server for Guardian observation."""
                try:
                    event_type = type(event).__name__
                    event_data = {
                        "message": str(event)[:500] if event else "Unknown event",
                    }
                    # Extract useful fields if available
                    if hasattr(event, "action"):
                        event_data["action"] = str(event.action)[:200]
                    if hasattr(event, "observation"):
                        event_data["observation"] = str(event.observation)[:200]
                    if hasattr(event, "content"):
                        event_data["content"] = str(event.content)[:200]

                    await mcp_client.call_tool(
                        "report_agent_event",
                        {
                            "task_id": task_id,
                            "agent_id": agent_id,
                            "event_type": event_type,
                            "event_data": event_data,
                        },
                    )
                except Exception as e:
                    logger.debug(
                        f"Failed to report event: {e}"
                    )  # Don't fail on event reporting

            # Sync wrapper for callback (OpenHands expects sync callbacks)
            def sync_event_callback(event):
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(on_agent_event(event))
                    else:
                        asyncio.run(on_agent_event(event))
                except Exception:
                    pass  # Best effort event reporting

            conversation = Conversation(
                agent=agent,
                workspace=workspace,
                callbacks=[
                    sync_event_callback
                ],  # Stream events for Guardian observation
            )

            # Register conversation with server for Guardian interventions
            conv_id = (
                str(conversation.state.id)
                if hasattr(conversation.state, "id")
                else None
            )
            if conv_id:
                logger.info(f"Registering conversation {conv_id} for interventions...")
                try:
                    await mcp_client.call_tool(
                        "register_conversation",
                        {
                            "task_id": task_id,
                            "conversation_id": conv_id,
                            "sandbox_id": sandbox_id,
                        },
                    )
                    logger.info(f"Conversation {conv_id} registered successfully")
                except Exception as e:
                    logger.warning(f"Failed to register conversation: {e}")

            try:
                # Build task message with context
                task_message = _build_task_message(
                    task_description=task_description,
                    task_id=task_id,
                    ticket_id=ticket_id,
                    agent_id=agent_id,
                    phase_id=phase_id,
                    system_prompt=system_prompt,
                )

                # Send task to agent
                conversation.send_message(task_message)

                # Run agent loop
                logger.info("Running agent...")
                conversation.run()

                # Collect results
                result = {
                    "status": str(conversation.state.execution_status),
                    "event_count": len(conversation.state.events),
                    "conversation_id": str(conversation.state.id),
                    "cost": (
                        conversation.conversation_stats.get_combined_metrics().accumulated_cost
                        if hasattr(conversation, "conversation_stats")
                        else 0
                    ),
                }

                logger.info(f"Execution complete: {result['status']}")

            except Exception as e:
                logger.error(f"Execution error: {e}")
                result = {
                    "status": "error",
                    "error": str(e),
                }
            finally:
                conversation.close()

        # ======================================================================
        # 10. Report Results via MCP
        # ======================================================================

        final_status = (
            "completed"
            if result.get("status") == "ExecutionStatus.COMPLETED"
            else "failed"
        )

        logger.info(f"Reporting task completion: {final_status}")

        await mcp_client.call_tool(
            "update_task_status",
            {
                "task_id": task_id,
                "status": final_status,
                "result": result,
            },
        )

        logger.info("Sandbox worker completed successfully")

    except Exception as e:
        logger.error(f"Sandbox worker error: {e}")

        # Try to report failure
        try:
            await mcp_client.call_tool(
                "update_task_status",
                {
                    "task_id": task_id,
                    "status": "failed",
                    "error_message": str(e),
                },
            )
        except Exception:
            pass

        sys.exit(1)

    finally:
        await mcp_client.disconnect()


def _build_task_message(
    task_description: str,
    task_id: str,
    ticket_id: Optional[str],
    agent_id: str,
    phase_id: str,
    system_prompt: str,
) -> str:
    """Build the complete task message for the agent."""

    parts = []

    # Add system prompt if present
    if system_prompt:
        parts.append(system_prompt)
        parts.append("---")

    # Add task context
    parts.append("## Task Assignment\n")
    parts.append(f"- **Task ID**: {task_id}")
    if ticket_id:
        parts.append(f"- **Ticket ID**: {ticket_id}")
    parts.append(f"- **Agent ID**: {agent_id}")
    parts.append(f"- **Phase**: {phase_id}")
    parts.append("")

    # Add task description
    parts.append("## Task Description\n")
    parts.append(task_description)
    parts.append("")

    # Add MCP tool reminder
    parts.append("## Available MCP Tools\n")
    parts.append("You have access to MCP tools for coordination:")
    parts.append("- `mcp__create_task` - Create sub-tasks")
    parts.append("- `mcp__update_task_status` - Update your progress")
    parts.append("- `mcp__broadcast_message` - Notify other agents")
    parts.append("- `mcp__change_ticket_status` - Update ticket status")
    parts.append("- `mcp__link_commit` - Link commits to tickets")
    parts.append("")
    parts.append("Use these tools to coordinate with the system.")

    return "\n".join(parts)


def main():
    """Synchronous entry point."""
    asyncio.run(run_sandbox_worker())


if __name__ == "__main__":
    main()
