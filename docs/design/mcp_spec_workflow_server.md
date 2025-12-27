# MCP Spec Workflow Server Design

**Created**: 2025-12-27
**Status**: Draft
**Purpose**: Design an MCP server using Claude Agent SDK Python to create specs, requirements, designs, tickets, and tasks via HTTP API calls.

## Overview

This document describes an MCP server implementation that provides tools for the spec-driven development workflow. The server uses the `@tool` decorator from Claude Agent SDK Python to create custom tools that make HTTP calls to the OmoiOS backend API.

## Architecture

```
┌─────────────────────┐     HTTP      ┌─────────────────────┐
│   Claude Agent      │  ──────────>  │   OmoiOS Backend    │
│   (uses MCP tools)  │               │   FastAPI Server    │
└─────────────────────┘               └─────────────────────┘
         │                                      │
         │ uses                                 │ persists
         ▼                                      ▼
┌─────────────────────┐               ┌─────────────────────┐
│  spec_workflow_mcp  │               │     PostgreSQL      │
│  (MCP Server)       │               │     Database        │
└─────────────────────┘               └─────────────────────┘
```

## API Endpoints Used

### Specs API (`/api/v1/specs`)

| Endpoint | Method | Schema | Description |
|----------|--------|--------|-------------|
| `/specs` | POST | `SpecCreate` | Create a new spec |
| `/specs/{spec_id}` | GET | - | Get spec details |
| `/specs/{spec_id}` | PATCH | `SpecUpdate` | Update spec |
| `/specs/{spec_id}/requirements` | POST | `RequirementCreate` | Add requirement |
| `/specs/{spec_id}/requirements/{req_id}/criteria` | POST | `CriterionCreate` | Add acceptance criterion |
| `/specs/{spec_id}/design` | PUT | `DesignArtifact` | Update design |
| `/specs/{spec_id}/tasks` | POST | `TaskCreate` | Add task |
| `/specs/{spec_id}/approve-requirements` | POST | - | Approve requirements |
| `/specs/{spec_id}/approve-design` | POST | - | Approve design |

### Tickets API (`/api/v1/tickets`)

| Endpoint | Method | Schema | Description |
|----------|--------|--------|-------------|
| `/tickets` | POST | `TicketCreate` | Create a new ticket |
| `/tickets/{ticket_id}` | GET | - | Get ticket details |

## MCP Tools Design

### Tool: `create_spec`

Creates a new specification in the system.

```python
@tool(
    "create_spec",
    "Create a new specification for a project. Returns the created spec with ID.",
    {
        "project_id": "Project ID to create spec under (required)",
        "title": "Title of the specification (required)",
        "description": "Detailed description of what this spec covers (optional)",
    }
)
async def create_spec(args: dict[str, Any]) -> dict[str, Any]:
    """Create a new spec via API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/api/v1/specs",
            json={
                "project_id": args["project_id"],
                "title": args["title"],
                "description": args.get("description"),
            }
        )
        response.raise_for_status()
        spec = response.json()
        return {
            "content": [{
                "type": "text",
                "text": f"Created spec '{spec['title']}' with ID: {spec['id']}"
            }]
        }
```

### Tool: `add_requirement`

Adds an EARS-style requirement to a spec.

```python
@tool(
    "add_requirement",
    "Add a requirement to a specification using EARS format (WHEN condition, THE SYSTEM SHALL action).",
    {
        "spec_id": "Spec ID to add requirement to (required)",
        "title": "Brief title for the requirement (required)",
        "condition": "EARS 'WHEN' clause - the trigger condition (required)",
        "action": "EARS 'THE SYSTEM SHALL' clause - what the system does (required)",
    }
)
async def add_requirement(args: dict[str, Any]) -> dict[str, Any]:
    """Add a requirement to a spec."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/api/v1/specs/{args['spec_id']}/requirements",
            json={
                "title": args["title"],
                "condition": args["condition"],
                "action": args["action"],
            }
        )
        response.raise_for_status()
        req = response.json()
        return {
            "content": [{
                "type": "text",
                "text": f"Added requirement '{req['title']}' (ID: {req['id']})"
            }]
        }
```

### Tool: `add_acceptance_criterion`

Adds an acceptance criterion to a requirement.

```python
@tool(
    "add_acceptance_criterion",
    "Add an acceptance criterion to a requirement. These define how to verify the requirement is met.",
    {
        "spec_id": "Spec ID (required)",
        "requirement_id": "Requirement ID to add criterion to (required)",
        "text": "The acceptance criterion text (required)",
    }
)
async def add_acceptance_criterion(args: dict[str, Any]) -> dict[str, Any]:
    """Add an acceptance criterion to a requirement."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/api/v1/specs/{args['spec_id']}/requirements/{args['requirement_id']}/criteria",
            json={"text": args["text"]}
        )
        response.raise_for_status()
        criterion = response.json()
        return {
            "content": [{
                "type": "text",
                "text": f"Added criterion (ID: {criterion['id']}): {criterion['text']}"
            }]
        }
```

### Tool: `update_design`

Updates the design artifacts for a spec.

```python
@tool(
    "update_design",
    "Update the design for a specification including architecture, data model, and API spec.",
    {
        "spec_id": "Spec ID (required)",
        "architecture": "Architecture description (optional)",
        "data_model": "Data model description (optional)",
        "api_spec": "List of API endpoints: [{method, endpoint, description}] (optional)",
    }
)
async def update_design(args: dict[str, Any]) -> dict[str, Any]:
    """Update design for a spec."""
    async with httpx.AsyncClient() as client:
        design = {
            "architecture": args.get("architecture"),
            "data_model": args.get("data_model"),
            "api_spec": args.get("api_spec", []),
        }
        response = await client.put(
            f"{API_BASE}/api/v1/specs/{args['spec_id']}/design",
            json=design
        )
        response.raise_for_status()
        return {
            "content": [{
                "type": "text",
                "text": f"Updated design for spec {args['spec_id']}"
            }]
        }
```

### Tool: `add_spec_task`

Adds a task to a spec.

```python
@tool(
    "add_spec_task",
    "Add a task to a specification. Tasks are discrete units of work derived from requirements.",
    {
        "spec_id": "Spec ID (required)",
        "title": "Task title (required)",
        "description": "Task description (optional)",
        "phase": "Development phase: Implementation, Testing, Integration, etc. (default: Implementation)",
        "priority": "Priority: low, medium, high, critical (default: medium)",
    }
)
async def add_spec_task(args: dict[str, Any]) -> dict[str, Any]:
    """Add a task to a spec."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/api/v1/specs/{args['spec_id']}/tasks",
            json={
                "title": args["title"],
                "description": args.get("description"),
                "phase": args.get("phase", "Implementation"),
                "priority": args.get("priority", "medium"),
            }
        )
        response.raise_for_status()
        task = response.json()
        return {
            "content": [{
                "type": "text",
                "text": f"Added task '{task['title']}' (ID: {task['id']})"
            }]
        }
```

### Tool: `create_ticket`

Creates a ticket from a spec or independently.

```python
@tool(
    "create_ticket",
    "Create a ticket for the workflow system. Tickets represent work items that agents execute.",
    {
        "title": "Ticket title (required)",
        "description": "Ticket description (optional)",
        "priority": "Priority: LOW, MEDIUM, HIGH, CRITICAL (default: MEDIUM)",
        "phase_id": "Initial phase: PHASE_REQUIREMENTS, PHASE_INITIAL, etc. (default: PHASE_REQUIREMENTS)",
        "project_id": "Project ID (optional)",
    }
)
async def create_ticket(args: dict[str, Any]) -> dict[str, Any]:
    """Create a ticket via API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/api/v1/tickets",
            json={
                "title": args["title"],
                "description": args.get("description"),
                "priority": args.get("priority", "MEDIUM"),
                "phase_id": args.get("phase_id", "PHASE_REQUIREMENTS"),
                "project_id": args.get("project_id"),
            }
        )
        response.raise_for_status()
        ticket = response.json()
        return {
            "content": [{
                "type": "text",
                "text": f"Created ticket '{ticket['title']}' with ID: {ticket['id']}"
            }]
        }
```

### Tool: `approve_requirements`

Approves requirements and moves spec to design phase.

```python
@tool(
    "approve_requirements",
    "Approve all requirements for a spec and transition to the Design phase.",
    {
        "spec_id": "Spec ID to approve requirements for (required)",
    }
)
async def approve_requirements(args: dict[str, Any]) -> dict[str, Any]:
    """Approve requirements for a spec."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/api/v1/specs/{args['spec_id']}/approve-requirements"
        )
        response.raise_for_status()
        return {
            "content": [{
                "type": "text",
                "text": f"Requirements approved for spec {args['spec_id']}. Now in Design phase."
            }]
        }
```

### Tool: `approve_design`

Approves design and moves spec to implementation phase.

```python
@tool(
    "approve_design",
    "Approve the design for a spec and transition to the Implementation phase.",
    {
        "spec_id": "Spec ID to approve design for (required)",
    }
)
async def approve_design(args: dict[str, Any]) -> dict[str, Any]:
    """Approve design for a spec."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/api/v1/specs/{args['spec_id']}/approve-design"
        )
        response.raise_for_status()
        return {
            "content": [{
                "type": "text",
                "text": f"Design approved for spec {args['spec_id']}. Now in Implementation phase."
            }]
        }
```

### Tool: `get_spec`

Retrieves a spec with all its details.

```python
@tool(
    "get_spec",
    "Get full details of a specification including requirements, design, and tasks.",
    {
        "spec_id": "Spec ID to retrieve (required)",
    }
)
async def get_spec(args: dict[str, Any]) -> dict[str, Any]:
    """Get spec details."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/api/v1/specs/{args['spec_id']}"
        )
        response.raise_for_status()
        spec = response.json()

        # Format for display
        output = f"""Spec: {spec['title']} (ID: {spec['id']})
Status: {spec['status']} | Phase: {spec['phase']}
Progress: {spec['progress']}%

Requirements ({len(spec['requirements'])}):
"""
        for req in spec['requirements']:
            output += f"  - [{req['status']}] {req['title']}\n"
            output += f"    WHEN {req['condition']}\n"
            output += f"    THE SYSTEM SHALL {req['action']}\n"

        output += f"\nTasks ({len(spec['tasks'])}):\n"
        for task in spec['tasks']:
            output += f"  - [{task['status']}] {task['title']} ({task['priority']})\n"

        return {
            "content": [{
                "type": "text",
                "text": output
            }]
        }
```

## Complete MCP Server Implementation

```python
"""
OmoiOS Spec Workflow MCP Server

Provides tools for spec-driven development workflow:
- Create and manage specifications
- Add EARS-style requirements with acceptance criteria
- Define architecture and design artifacts
- Create tasks and tickets
- Move specs through approval phases
"""

import os
from typing import Any

import httpx
from claude_agent_sdk import tool, create_sdk_mcp_server

# Configuration
API_BASE = os.environ.get("OMOIOS_API_URL", "http://localhost:18000")
API_TIMEOUT = 30.0


# =============================================================================
# Spec Management Tools
# =============================================================================

@tool(
    "create_spec",
    "Create a new specification for a project",
    {
        "project_id": "Project ID (required)",
        "title": "Spec title (required)",
        "description": "Spec description (optional)",
    }
)
async def create_spec(args: dict[str, Any]) -> dict[str, Any]:
    """Create a new spec."""
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(
            f"{API_BASE}/api/v1/specs",
            json={
                "project_id": args["project_id"],
                "title": args["title"],
                "description": args.get("description"),
            }
        )
        response.raise_for_status()
        spec = response.json()
        return {"content": [{"type": "text", "text": f"Created spec '{spec['title']}' (ID: {spec['id']})"}]}


@tool(
    "get_spec",
    "Get full details of a specification",
    {"spec_id": "Spec ID (required)"}
)
async def get_spec(args: dict[str, Any]) -> dict[str, Any]:
    """Get spec details."""
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.get(f"{API_BASE}/api/v1/specs/{args['spec_id']}")
        response.raise_for_status()
        spec = response.json()

        output = f"Spec: {spec['title']} (ID: {spec['id']})\n"
        output += f"Status: {spec['status']} | Phase: {spec['phase']}\n\n"
        output += f"Requirements ({len(spec['requirements'])}):\n"
        for req in spec['requirements']:
            output += f"  - {req['title']}: WHEN {req['condition']}, THE SYSTEM SHALL {req['action']}\n"
        output += f"\nTasks ({len(spec['tasks'])}):\n"
        for task in spec['tasks']:
            output += f"  - [{task['priority']}] {task['title']}\n"

        return {"content": [{"type": "text", "text": output}]}


# =============================================================================
# Requirements Tools
# =============================================================================

@tool(
    "add_requirement",
    "Add an EARS-style requirement to a spec",
    {
        "spec_id": "Spec ID (required)",
        "title": "Requirement title (required)",
        "condition": "EARS WHEN clause (required)",
        "action": "EARS THE SYSTEM SHALL clause (required)",
    }
)
async def add_requirement(args: dict[str, Any]) -> dict[str, Any]:
    """Add a requirement."""
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(
            f"{API_BASE}/api/v1/specs/{args['spec_id']}/requirements",
            json={"title": args["title"], "condition": args["condition"], "action": args["action"]}
        )
        response.raise_for_status()
        req = response.json()
        return {"content": [{"type": "text", "text": f"Added requirement '{req['title']}' (ID: {req['id']})"}]}


@tool(
    "add_acceptance_criterion",
    "Add an acceptance criterion to a requirement",
    {
        "spec_id": "Spec ID (required)",
        "requirement_id": "Requirement ID (required)",
        "text": "Criterion text (required)",
    }
)
async def add_acceptance_criterion(args: dict[str, Any]) -> dict[str, Any]:
    """Add acceptance criterion."""
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(
            f"{API_BASE}/api/v1/specs/{args['spec_id']}/requirements/{args['requirement_id']}/criteria",
            json={"text": args["text"]}
        )
        response.raise_for_status()
        criterion = response.json()
        return {"content": [{"type": "text", "text": f"Added criterion: {criterion['text']}"}]}


# =============================================================================
# Design Tools
# =============================================================================

@tool(
    "update_design",
    "Update design artifacts for a spec",
    {
        "spec_id": "Spec ID (required)",
        "architecture": "Architecture description (optional)",
        "data_model": "Data model description (optional)",
        "api_spec": "List of API endpoints [{method, endpoint, description}] (optional)",
    }
)
async def update_design(args: dict[str, Any]) -> dict[str, Any]:
    """Update design."""
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.put(
            f"{API_BASE}/api/v1/specs/{args['spec_id']}/design",
            json={
                "architecture": args.get("architecture"),
                "data_model": args.get("data_model"),
                "api_spec": args.get("api_spec", []),
            }
        )
        response.raise_for_status()
        return {"content": [{"type": "text", "text": f"Updated design for spec {args['spec_id']}"}]}


# =============================================================================
# Task Tools
# =============================================================================

@tool(
    "add_spec_task",
    "Add a task to a specification",
    {
        "spec_id": "Spec ID (required)",
        "title": "Task title (required)",
        "description": "Task description (optional)",
        "phase": "Phase: Implementation, Testing, etc. (default: Implementation)",
        "priority": "Priority: low, medium, high, critical (default: medium)",
    }
)
async def add_spec_task(args: dict[str, Any]) -> dict[str, Any]:
    """Add task to spec."""
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(
            f"{API_BASE}/api/v1/specs/{args['spec_id']}/tasks",
            json={
                "title": args["title"],
                "description": args.get("description"),
                "phase": args.get("phase", "Implementation"),
                "priority": args.get("priority", "medium"),
            }
        )
        response.raise_for_status()
        task = response.json()
        return {"content": [{"type": "text", "text": f"Added task '{task['title']}' (ID: {task['id']})"}]}


# =============================================================================
# Ticket Tools
# =============================================================================

@tool(
    "create_ticket",
    "Create a ticket for the workflow system",
    {
        "title": "Ticket title (required)",
        "description": "Ticket description (optional)",
        "priority": "Priority: LOW, MEDIUM, HIGH, CRITICAL (default: MEDIUM)",
        "phase_id": "Initial phase (default: PHASE_REQUIREMENTS)",
        "project_id": "Project ID (optional)",
    }
)
async def create_ticket(args: dict[str, Any]) -> dict[str, Any]:
    """Create a ticket."""
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(
            f"{API_BASE}/api/v1/tickets",
            json={
                "title": args["title"],
                "description": args.get("description"),
                "priority": args.get("priority", "MEDIUM"),
                "phase_id": args.get("phase_id", "PHASE_REQUIREMENTS"),
                "project_id": args.get("project_id"),
            }
        )
        response.raise_for_status()
        ticket = response.json()
        return {"content": [{"type": "text", "text": f"Created ticket '{ticket['title']}' (ID: {ticket['id']})"}]}


# =============================================================================
# Approval Tools
# =============================================================================

@tool(
    "approve_requirements",
    "Approve requirements and move to Design phase",
    {"spec_id": "Spec ID (required)"}
)
async def approve_requirements(args: dict[str, Any]) -> dict[str, Any]:
    """Approve requirements."""
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(f"{API_BASE}/api/v1/specs/{args['spec_id']}/approve-requirements")
        response.raise_for_status()
        return {"content": [{"type": "text", "text": f"Requirements approved. Spec {args['spec_id']} now in Design phase."}]}


@tool(
    "approve_design",
    "Approve design and move to Implementation phase",
    {"spec_id": "Spec ID (required)"}
)
async def approve_design(args: dict[str, Any]) -> dict[str, Any]:
    """Approve design."""
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(f"{API_BASE}/api/v1/specs/{args['spec_id']}/approve-design")
        response.raise_for_status()
        return {"content": [{"type": "text", "text": f"Design approved. Spec {args['spec_id']} now in Implementation phase."}]}


# =============================================================================
# MCP Server Creation
# =============================================================================

def create_spec_workflow_mcp_server():
    """Create the MCP server with all spec workflow tools."""
    return create_sdk_mcp_server(
        name="spec_workflow",
        tools=[
            create_spec,
            get_spec,
            add_requirement,
            add_acceptance_criterion,
            update_design,
            add_spec_task,
            create_ticket,
            approve_requirements,
            approve_design,
        ]
    )


# For standalone testing
if __name__ == "__main__":
    import asyncio

    async def test_tools():
        # Test creating a spec
        result = await create_spec({
            "project_id": "test-project",
            "title": "Test Spec",
            "description": "Testing the MCP tools"
        })
        print(result)

    asyncio.run(test_tools())
```

## Usage with Claude Agent SDK

### Option 1: In-Process MCP Server

```python
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from spec_workflow_mcp import create_spec_workflow_mcp_server

# Create the MCP server
mcp_server = create_spec_workflow_mcp_server()

# Use with Claude Agent
async def run_agent():
    options = ClaudeAgentOptions(
        model="claude-sonnet-4-20250514",
        mcp_servers=[mcp_server],
        allowed_tools=[
            "mcp__spec_workflow__create_spec",
            "mcp__spec_workflow__add_requirement",
            "mcp__spec_workflow__add_acceptance_criterion",
            "mcp__spec_workflow__update_design",
            "mcp__spec_workflow__add_spec_task",
            "mcp__spec_workflow__create_ticket",
            "mcp__spec_workflow__approve_requirements",
            "mcp__spec_workflow__approve_design",
            "mcp__spec_workflow__get_spec",
        ],
    )

    async with ClaudeSDKClient(options) as client:
        result = await client.query(
            "Create a spec for user authentication with requirements, "
            "design, and tasks. Then create a ticket from it."
        )
        print(result)
```

### Option 2: Standalone MCP Server

Run as a subprocess that Claude Code connects to:

```python
# spec_workflow_server.py
import asyncio
from mcp import Server
from spec_workflow_mcp import (
    create_spec, get_spec, add_requirement, add_acceptance_criterion,
    update_design, add_spec_task, create_ticket,
    approve_requirements, approve_design
)

server = Server("spec_workflow")

# Register all tools with the server
@server.list_tools()
async def list_tools():
    return [
        create_spec.mcp_tool,
        get_spec.mcp_tool,
        add_requirement.mcp_tool,
        add_acceptance_criterion.mcp_tool,
        update_design.mcp_tool,
        add_spec_task.mcp_tool,
        create_ticket.mcp_tool,
        approve_requirements.mcp_tool,
        approve_design.mcp_tool,
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    tools = {
        "create_spec": create_spec,
        "get_spec": get_spec,
        "add_requirement": add_requirement,
        "add_acceptance_criterion": add_acceptance_criterion,
        "update_design": update_design,
        "add_spec_task": add_spec_task,
        "create_ticket": create_ticket,
        "approve_requirements": approve_requirements,
        "approve_design": approve_design,
    }
    return await tools[name](arguments)

if __name__ == "__main__":
    asyncio.run(server.run())
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OMOIOS_API_URL` | Base URL for OmoiOS API | `http://localhost:18000` |

## Workflow Example

A typical spec-driven development flow using these tools:

1. **Create Spec**: `create_spec` with project_id and title
2. **Add Requirements**: Multiple `add_requirement` calls with EARS format
3. **Add Criteria**: `add_acceptance_criterion` for each requirement
4. **Approve Requirements**: `approve_requirements` to move to Design
5. **Update Design**: `update_design` with architecture and API spec
6. **Approve Design**: `approve_design` to move to Implementation
7. **Add Tasks**: `add_spec_task` for each implementation unit
8. **Create Ticket**: `create_ticket` to start workflow execution

## Next Steps

1. Implement the MCP server in `backend/omoi_os/mcp/spec_workflow.py`
2. Add authentication support (API key or JWT)
3. Add error handling with user-friendly messages
4. Create integration tests
5. Add to Claude Code's MCP server configuration
