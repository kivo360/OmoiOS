"""
OmoiOS Spec Workflow MCP Server

Provides MCP tools for spec-driven development workflow:
- Create and manage specifications
- Add EARS-style requirements with acceptance criteria
- Define architecture and design artifacts
- Create tasks and tickets
- Move specs through approval phases

Usage with Claude Agent SDK:
    from omoi_os.mcp import create_spec_workflow_mcp_server
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

    mcp_server = create_spec_workflow_mcp_server()
    options = ClaudeAgentOptions(
        model="claude-sonnet-4-20250514",
        mcp_servers=[mcp_server],
        allowed_tools=["mcp__spec_workflow__*"],
    )
"""

import os
from typing import Any

import httpx

# Note: claude_agent_sdk is optional - tools work with or without it
try:
    from claude_agent_sdk import tool, create_sdk_mcp_server

    HAS_CLAUDE_SDK = True
except ImportError:
    HAS_CLAUDE_SDK = False

    # Provide stub decorator when SDK not available
    def tool(name: str, description: str, parameters: dict):
        def decorator(func):
            func._tool_name = name
            func._tool_description = description
            func._tool_parameters = parameters
            return func

        return decorator


# Configuration
API_BASE = os.environ.get("OMOIOS_API_URL", "http://localhost:18000")
API_TIMEOUT = 30.0


def _format_response(text: str) -> dict[str, Any]:
    """Format a text response in MCP tool format."""
    return {"content": [{"type": "text", "text": text}]}


def _format_error(error: str) -> dict[str, Any]:
    """Format an error response in MCP tool format."""
    return {"content": [{"type": "text", "text": f"Error: {error}"}]}


# =============================================================================
# Spec Management Tools
# =============================================================================


@tool(
    "create_spec",
    "Create a new specification for a project. Specs are containers for requirements, design, and tasks.",
    {
        "project_id": "Project ID to create spec under (required)",
        "title": "Title of the specification (required)",
        "description": "Detailed description of what this spec covers (optional)",
    },
)
async def create_spec(args: dict[str, Any]) -> dict[str, Any]:
    """Create a new spec via API."""
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE}/api/v1/specs",
                json={
                    "project_id": args["project_id"],
                    "title": args["title"],
                    "description": args.get("description"),
                },
            )
            response.raise_for_status()
            spec = response.json()
            return _format_response(
                f"Created spec '{spec['title']}'\n"
                f"ID: {spec['id']}\n"
                f"Status: {spec['status']}\n"
                f"Phase: {spec['phase']}"
            )
    except httpx.HTTPStatusError as e:
        return _format_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _format_error(str(e))


@tool(
    "get_spec",
    "Get full details of a specification including requirements, design, and tasks.",
    {"spec_id": "Spec ID to retrieve (required)"},
)
async def get_spec(args: dict[str, Any]) -> dict[str, Any]:
    """Get spec details via API."""
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(f"{API_BASE}/api/v1/specs/{args['spec_id']}")
            response.raise_for_status()
            spec = response.json()

            output = f"Spec: {spec['title']}\n"
            output += f"ID: {spec['id']}\n"
            output += f"Status: {spec['status']} | Phase: {spec['phase']}\n"
            output += f"Progress: {spec['progress']}%\n\n"

            output += f"Requirements ({len(spec['requirements'])}):\n"
            for req in spec["requirements"]:
                output += f"  [{req['status']}] {req['title']}\n"
                output += f"    WHEN {req['condition']}\n"
                output += f"    THE SYSTEM SHALL {req['action']}\n"
                for c in req.get("criteria", []):
                    status = "x" if c["completed"] else " "
                    output += f"    [{status}] {c['text']}\n"

            output += f"\nTasks ({len(spec['tasks'])}):\n"
            for task in spec["tasks"]:
                output += (
                    f"  [{task['status']}] {task['title']} ({task['priority']})\n"
                )

            return _format_response(output)
    except httpx.HTTPStatusError as e:
        return _format_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _format_error(str(e))


@tool(
    "list_project_specs",
    "List all specifications for a project.",
    {
        "project_id": "Project ID (required)",
        "status": "Filter by status: draft, requirements, design, executing, completed (optional)",
    },
)
async def list_project_specs(args: dict[str, Any]) -> dict[str, Any]:
    """List specs for a project."""
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            url = f"{API_BASE}/api/v1/specs/project/{args['project_id']}"
            params = {}
            if args.get("status"):
                params["status"] = args["status"]
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            output = f"Specs ({data['total']}):\n"
            for spec in data["specs"]:
                output += f"  - {spec['title']} (ID: {spec['id']})\n"
                output += f"    Status: {spec['status']} | Phase: {spec['phase']}\n"

            return _format_response(output)
    except httpx.HTTPStatusError as e:
        return _format_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _format_error(str(e))


# =============================================================================
# Requirements Tools
# =============================================================================


@tool(
    "add_requirement",
    "Add an EARS-style requirement to a spec. Uses 'WHEN condition, THE SYSTEM SHALL action' format.",
    {
        "spec_id": "Spec ID to add requirement to (required)",
        "title": "Brief title for the requirement (required)",
        "condition": "EARS 'WHEN' clause - the trigger condition (required)",
        "action": "EARS 'THE SYSTEM SHALL' clause - what the system does (required)",
    },
)
async def add_requirement(args: dict[str, Any]) -> dict[str, Any]:
    """Add a requirement to a spec."""
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE}/api/v1/specs/{args['spec_id']}/requirements",
                json={
                    "title": args["title"],
                    "condition": args["condition"],
                    "action": args["action"],
                },
            )
            response.raise_for_status()
            req = response.json()
            return _format_response(
                f"Added requirement '{req['title']}'\n"
                f"ID: {req['id']}\n"
                f"WHEN {req['condition']}\n"
                f"THE SYSTEM SHALL {req['action']}"
            )
    except httpx.HTTPStatusError as e:
        return _format_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _format_error(str(e))


@tool(
    "add_acceptance_criterion",
    "Add an acceptance criterion to a requirement. These define how to verify the requirement is met.",
    {
        "spec_id": "Spec ID (required)",
        "requirement_id": "Requirement ID to add criterion to (required)",
        "text": "The acceptance criterion text (required)",
    },
)
async def add_acceptance_criterion(args: dict[str, Any]) -> dict[str, Any]:
    """Add an acceptance criterion to a requirement."""
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE}/api/v1/specs/{args['spec_id']}/requirements/{args['requirement_id']}/criteria",
                json={"text": args["text"]},
            )
            response.raise_for_status()
            criterion = response.json()
            return _format_response(
                f"Added acceptance criterion\n"
                f"ID: {criterion['id']}\n"
                f"Text: {criterion['text']}"
            )
    except httpx.HTTPStatusError as e:
        return _format_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _format_error(str(e))


# =============================================================================
# Design Tools
# =============================================================================


@tool(
    "update_design",
    "Update the design artifacts for a spec including architecture, data model, and API spec.",
    {
        "spec_id": "Spec ID (required)",
        "architecture": "Architecture description/diagram in markdown (optional)",
        "data_model": "Data model description/diagram in markdown (optional)",
        "api_spec": "List of API endpoints: [{method, endpoint, description}] (optional)",
    },
)
async def update_design(args: dict[str, Any]) -> dict[str, Any]:
    """Update design for a spec."""
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            design = {
                "architecture": args.get("architecture"),
                "data_model": args.get("data_model"),
                "api_spec": args.get("api_spec", []),
            }
            response = await client.put(
                f"{API_BASE}/api/v1/specs/{args['spec_id']}/design",
                json=design,
            )
            response.raise_for_status()
            return _format_response(f"Updated design for spec {args['spec_id']}")
    except httpx.HTTPStatusError as e:
        return _format_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _format_error(str(e))


# =============================================================================
# Task Tools
# =============================================================================


@tool(
    "add_spec_task",
    "Add a task to a specification. Tasks are discrete units of work derived from requirements.",
    {
        "spec_id": "Spec ID (required)",
        "title": "Task title (required)",
        "description": "Task description (optional)",
        "phase": "Development phase: Implementation, Testing, Integration, etc. (default: Implementation)",
        "priority": "Priority: low, medium, high, critical (default: medium)",
    },
)
async def add_spec_task(args: dict[str, Any]) -> dict[str, Any]:
    """Add a task to a spec."""
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE}/api/v1/specs/{args['spec_id']}/tasks",
                json={
                    "title": args["title"],
                    "description": args.get("description"),
                    "phase": args.get("phase", "Implementation"),
                    "priority": args.get("priority", "medium"),
                },
            )
            response.raise_for_status()
            task = response.json()
            return _format_response(
                f"Added task '{task['title']}'\n"
                f"ID: {task['id']}\n"
                f"Phase: {task['phase']}\n"
                f"Priority: {task['priority']}"
            )
    except httpx.HTTPStatusError as e:
        return _format_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _format_error(str(e))


# =============================================================================
# Ticket Tools
# =============================================================================


@tool(
    "create_ticket",
    "Create a ticket for the workflow system. Tickets represent work items that agents execute.",
    {
        "title": "Ticket title (required)",
        "description": "Ticket description (optional)",
        "priority": "Priority: LOW, MEDIUM, HIGH, CRITICAL (default: MEDIUM)",
        "phase_id": "Initial phase: PHASE_REQUIREMENTS, PHASE_INITIAL, PHASE_IMPLEMENTATION (default: PHASE_REQUIREMENTS)",
        "project_id": "Project ID (optional)",
    },
)
async def create_ticket(args: dict[str, Any]) -> dict[str, Any]:
    """Create a ticket via API."""
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE}/api/v1/tickets",
                json={
                    "title": args["title"],
                    "description": args.get("description"),
                    "priority": args.get("priority", "MEDIUM"),
                    "phase_id": args.get("phase_id", "PHASE_REQUIREMENTS"),
                    "project_id": args.get("project_id"),
                },
            )
            response.raise_for_status()
            ticket = response.json()
            return _format_response(
                f"Created ticket '{ticket['title']}'\n"
                f"ID: {ticket['id']}\n"
                f"Priority: {ticket['priority']}\n"
                f"Phase: {ticket['phase_id']}"
            )
    except httpx.HTTPStatusError as e:
        return _format_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _format_error(str(e))


@tool(
    "get_ticket",
    "Get details of a ticket including its current status and tasks.",
    {"ticket_id": "Ticket ID (required)"},
)
async def get_ticket(args: dict[str, Any]) -> dict[str, Any]:
    """Get ticket details."""
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(
                f"{API_BASE}/api/v1/tickets/{args['ticket_id']}"
            )
            response.raise_for_status()
            ticket = response.json()

            output = f"Ticket: {ticket['title']}\n"
            output += f"ID: {ticket['id']}\n"
            output += f"Status: {ticket['status']}\n"
            output += f"Priority: {ticket['priority']}\n"
            output += f"Phase: {ticket['phase_id']}\n"
            if ticket.get("description"):
                output += f"\nDescription:\n{ticket['description']}\n"

            return _format_response(output)
    except httpx.HTTPStatusError as e:
        return _format_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _format_error(str(e))


@tool(
    "get_task",
    "Get full details of a task including description, acceptance criteria, and parent ticket info. "
    "IMPORTANT: Always use the task UUID, not the task title.",
    {"task_id": "Task UUID (required - use the full UUID, not the title)"},
)
async def get_task(args: dict[str, Any]) -> dict[str, Any]:
    """Get task details including full description."""
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(
                f"{API_BASE}/api/v1/tasks/{args['task_id']}"
            )
            response.raise_for_status()
            task = response.json()

            output = f"# Task: {task['title']}\n\n"
            output += f"**ID:** {task['id']}\n"
            output += f"**Status:** {task['status']}\n"
            output += f"**Priority:** {task.get('priority', 'MEDIUM')}\n"
            output += f"**Phase:** {task.get('phase_id', 'N/A')}\n"
            output += f"**Ticket ID:** {task.get('ticket_id', 'N/A')}\n\n"

            if task.get("description"):
                output += f"## Full Description\n\n{task['description']}\n\n"

            # Also fetch parent ticket for additional context
            if task.get("ticket_id"):
                try:
                    ticket_response = await client.get(
                        f"{API_BASE}/api/v1/tickets/{task['ticket_id']}"
                    )
                    if ticket_response.status_code == 200:
                        ticket = ticket_response.json()
                        output += f"## Parent Ticket Context\n\n"
                        output += f"**Ticket Title:** {ticket['title']}\n"
                        output += f"**Ticket Status:** {ticket['status']}\n\n"
                        if ticket.get("description"):
                            output += f"**Ticket Description:**\n{ticket['description']}\n"
                except Exception:
                    pass  # Parent ticket fetch is optional

            return _format_response(output)
    except httpx.HTTPStatusError as e:
        return _format_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _format_error(str(e))


# =============================================================================
# Approval Tools
# =============================================================================


@tool(
    "approve_requirements",
    "Approve all requirements for a spec and transition to the Design phase.",
    {"spec_id": "Spec ID to approve requirements for (required)"},
)
async def approve_requirements(args: dict[str, Any]) -> dict[str, Any]:
    """Approve requirements for a spec."""
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE}/api/v1/specs/{args['spec_id']}/approve-requirements"
            )
            response.raise_for_status()
            return _format_response(
                f"Requirements approved for spec {args['spec_id']}.\n"
                f"Spec is now in the Design phase."
            )
    except httpx.HTTPStatusError as e:
        return _format_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _format_error(str(e))


@tool(
    "approve_design",
    "Approve the design for a spec and transition to the Implementation phase.",
    {"spec_id": "Spec ID to approve design for (required)"},
)
async def approve_design(args: dict[str, Any]) -> dict[str, Any]:
    """Approve design for a spec."""
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE}/api/v1/specs/{args['spec_id']}/approve-design"
            )
            response.raise_for_status()
            return _format_response(
                f"Design approved for spec {args['spec_id']}.\n"
                f"Spec is now in the Implementation phase."
            )
    except httpx.HTTPStatusError as e:
        return _format_error(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _format_error(str(e))


# =============================================================================
# MCP Server Factory
# =============================================================================

# All available tools
ALL_TOOLS = [
    create_spec,
    get_spec,
    list_project_specs,
    add_requirement,
    add_acceptance_criterion,
    update_design,
    add_spec_task,
    create_ticket,
    get_ticket,
    get_task,  # Added for task context retrieval
    approve_requirements,
    approve_design,
]


def create_spec_workflow_mcp_server():
    """Create the MCP server with all spec workflow tools.

    Returns an MCP server that can be passed to ClaudeAgentOptions.mcp_servers.

    Requires claude_agent_sdk to be installed.

    Example:
        from omoi_os.mcp import create_spec_workflow_mcp_server
        from claude_agent_sdk import ClaudeAgentOptions

        options = ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",
            mcp_servers=[create_spec_workflow_mcp_server()],
        )
    """
    if not HAS_CLAUDE_SDK:
        raise ImportError(
            "claude_agent_sdk is required to create MCP servers. "
            "Install with: pip install claude-agent-sdk"
        )

    return create_sdk_mcp_server(name="spec_workflow", tools=ALL_TOOLS)


def get_tool_names() -> list[str]:
    """Get list of all tool names in MCP format.

    These can be used in ClaudeAgentOptions.allowed_tools.

    Returns:
        List of tool names in format 'mcp__spec_workflow__<tool_name>'
    """
    return [f"mcp__spec_workflow__{t._tool_name}" for t in ALL_TOOLS]


# =============================================================================
# Standalone Testing
# =============================================================================

if __name__ == "__main__":
    import asyncio

    async def test_tools():
        """Test the tools work correctly."""
        print("Testing spec workflow tools...\n")

        # Test list specs (should work even with no specs)
        print("1. Listing project specs:")
        result = await list_project_specs({"project_id": "test-project"})
        print(result["content"][0]["text"])
        print()

        # Test create spec
        print("2. Creating a spec:")
        result = await create_spec(
            {
                "project_id": "test-project",
                "title": "User Authentication System",
                "description": "Implement secure user authentication with OAuth",
            }
        )
        print(result["content"][0]["text"])
        print()

        print("Tools are working!")

    asyncio.run(test_tools())
