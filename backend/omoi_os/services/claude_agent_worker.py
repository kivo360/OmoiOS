"""Claude Agent SDK worker for sandbox execution.

This is an alternative to the OpenHands-based worker that uses
Anthropic's native Claude Agent SDK for tool-using agent execution.

Usage:
    This script runs inside a Daytona sandbox and:
    1. Fetches task details from the orchestrator
    2. Creates a Claude Agent with custom tools
    3. Executes the task using Claude's native tool_use
    4. Reports progress and results back
"""

import asyncio
import os
from pathlib import Path
from typing import Any

from omoi_os.logging import configure_logging, get_logger

# Configure logging for worker
_env = os.environ.get("OMOIOS_ENV", "development")
configure_logging(env=_env)  # type: ignore[arg-type]
logger = get_logger(__name__)

# Environment configuration
TASK_ID = os.environ.get("TASK_ID")
AGENT_ID = os.environ.get("AGENT_ID")
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:18000")
SANDBOX_ID = os.environ.get("SANDBOX_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", os.environ.get("LLM_API_KEY", ""))


async def fetch_task() -> dict | None:
    """Fetch task details from orchestrator."""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{MCP_SERVER_URL}/api/v1/tasks/{TASK_ID}",
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch task: {e}")
    return None


async def report_status(status: str, result: str | None = None):
    """Report task status back to orchestrator."""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.patch(
                f"{MCP_SERVER_URL}/api/v1/tasks/{TASK_ID}",
                json={"status": status, "result": result},
            )
    except Exception as e:
        logger.debug(f"Failed to report status: {e}")


async def report_event(event_type: str, event_data: dict):
    """Report an agent event for Guardian observation."""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{MCP_SERVER_URL}/api/v1/agent-events",
                json={
                    "task_id": TASK_ID,
                    "agent_id": AGENT_ID,
                    "sandbox_id": SANDBOX_ID,
                    "event_type": event_type,
                    "event_data": event_data,
                },
            )
    except Exception as e:
        logger.debug(f"Failed to report event: {e}")


def create_agent_tools():
    """Create custom tools for the Claude agent."""
    try:
        from claude_agent_sdk import tool, create_sdk_mcp_server
    except ImportError:
        logger.error("claude-agent-sdk not installed. Install with: pip install claude-agent-sdk")
        return None, []
    
    @tool("read_file", "Read contents of a file", {"file_path": str})
    async def read_file(args: dict[str, Any]) -> dict[str, Any]:
        """Read a file from the workspace."""
        file_path = Path(args["file_path"])
        try:
            content = file_path.read_text()
            return {
                "content": [{"type": "text", "text": content}]
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error reading file: {e}"}],
                "is_error": True
            }
    
    @tool("write_file", "Write contents to a file", {"file_path": str, "content": str})
    async def write_file(args: dict[str, Any]) -> dict[str, Any]:
        """Write content to a file."""
        file_path = Path(args["file_path"])
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(args["content"])
            asyncio.create_task(report_event("file_written", {"path": str(file_path)}))
            return {
                "content": [{"type": "text", "text": f"Successfully wrote to {file_path}"}]
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error writing file: {e}"}],
                "is_error": True
            }
    
    @tool("run_command", "Execute a shell command", {"command": str, "cwd": str})
    async def run_command(args: dict[str, Any]) -> dict[str, Any]:
        """Execute a shell command."""
        import subprocess
        
        command = args["command"]
        cwd = args.get("cwd", "/workspace")
        
        try:
            asyncio.create_task(report_event("command_started", {"command": command}))
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=cwd
            )
            
            output = result.stdout or ""
            error = result.stderr or ""
            exit_code = result.returncode
            
            return {
                "content": [{
                    "type": "text",
                    "text": f"Exit code: {exit_code}\nStdout:\n{output}\nStderr:\n{error}"
                }]
            }
        except subprocess.TimeoutExpired:
            return {
                "content": [{"type": "text", "text": "Command timed out after 300s"}],
                "is_error": True
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error running command: {e}"}],
                "is_error": True
            }
    
    @tool("list_files", "List files in a directory", {"directory": str})
    async def list_files(args: dict[str, Any]) -> dict[str, Any]:
        """List files in a directory."""
        directory = Path(args["directory"])
        try:
            if not directory.exists():
                return {
                    "content": [{"type": "text", "text": f"Directory does not exist: {directory}"}],
                    "is_error": True
                }
            
            files = []
            for item in directory.iterdir():
                prefix = "[DIR]" if item.is_dir() else "[FILE]"
                files.append(f"{prefix} {item.name}")
            
            return {
                "content": [{"type": "text", "text": "\n".join(files) or "(empty directory)"}]
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error listing directory: {e}"}],
                "is_error": True
            }
    
    @tool("report_progress", "Report progress on the task", {"message": str, "percentage": int})
    async def report_progress(args: dict[str, Any]) -> dict[str, Any]:
        """Report task progress back to the orchestrator."""
        await report_event("progress", {
            "message": args["message"],
            "percentage": args.get("percentage", 0)
        })
        return {
            "content": [{"type": "text", "text": f"Progress reported: {args['message']}"}]
        }
    
    # Create the MCP server with all tools
    server = create_sdk_mcp_server(
        name="workspace",
        version="1.0.0",
        tools=[read_file, write_file, run_command, list_files, report_progress]
    )
    
    tool_names = [
        "mcp__workspace__read_file",
        "mcp__workspace__write_file",
        "mcp__workspace__run_command",
        "mcp__workspace__list_files",
        "mcp__workspace__report_progress",
    ]
    
    return server, tool_names


async def run_claude_agent(task_description: str, workspace_dir: str = "/workspace"):
    """Run the Claude Agent SDK to complete a task."""
    try:
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher
    except ImportError:
        logger.error("claude-agent-sdk not installed")
        return False, "claude-agent-sdk not installed"
    
    # Create custom tools
    tools_server, tool_names = create_agent_tools()
    if tools_server is None:
        return False, "Failed to create tools"
    
    # Define a hook to track tool usage
    async def track_tool_use(input_data, tool_use_id, _context):
        """Track tool usage for Guardian observation."""
        tool_name = input_data.get("tool_name", "unknown")
        await report_event("tool_use", {"tool": tool_name, "tool_use_id": tool_use_id})
        return {}
    
    # Configure the agent
    options = ClaudeAgentOptions(
        allowed_tools=tool_names + ["Read", "Write", "Bash", "Edit", "Glob", "Grep"],
        permission_mode="bypassPermissions",  # Auto-approve all in sandbox
        system_prompt=f"""You are an AI coding agent working on a software development task.
        
Your workspace is at {workspace_dir}. You have access to tools for reading/writing files,
running commands, and reporting progress.

Always report your progress as you work. Be thorough and test your changes.
""",
        cwd=Path(workspace_dir),
        max_turns=50,
        max_budget_usd=10.0,  # Safety limit
        model="claude-sonnet-4-5",  # or claude-sonnet-4-20250514
        mcp_servers={"workspace": tools_server},
        hooks={
            "PostToolUse": [HookMatcher(matcher=None, hooks=[track_tool_use])]
        },
    )
    
    try:
        async with ClaudeSDKClient(options=options) as client:
            # Send the task
            await client.query(task_description)
            
            # Process responses
            final_output = []
            async for message in client.receive_response():
                # Log messages for debugging
                message_str = str(message)[:500]
                logger.info(f"Agent message: {message_str}")
                final_output.append(message_str)
            
            return True, "\n".join(final_output[-5:])  # Last 5 messages
            
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        return False, str(e)


async def main():
    """Main entry point for the Claude Agent worker."""
    logger.info(f"Claude Agent Worker starting for task {TASK_ID}")
    
    if not TASK_ID or not AGENT_ID:
        logger.error("TASK_ID and AGENT_ID required")
        return
    
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY required")
        await report_status("failed", "Missing ANTHROPIC_API_KEY")
        return
    
    # Set API key for Claude SDK
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    
    # Fetch task details
    task = await fetch_task()
    if not task:
        logger.error(f"Could not fetch task {TASK_ID}")
        await report_status("failed", "Could not fetch task details")
        return
    
    task_description = task.get("description", "No description provided")
    logger.info(f"Task: {task_description}")
    
    # Update status to running
    await report_status("in_progress")
    await report_event("agent_started", {"task": task_description[:200]})
    
    # Run the agent
    success, result = await run_claude_agent(task_description)
    
    if success:
        logger.info("Agent completed successfully")
        await report_status("completed", result)
        await report_event("agent_completed", {"success": True})
    else:
        logger.error(f"Agent failed: {result}")
        await report_status("failed", result)
        await report_event("agent_failed", {"error": result})


if __name__ == "__main__":
    asyncio.run(main())
