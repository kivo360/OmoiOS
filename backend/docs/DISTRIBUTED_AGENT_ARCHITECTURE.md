# OmoiOS Distributed Agent Architecture

## Overview

OmoiOS enables AI agents to run in isolated cloud sandboxes while sharing centralized state through MCP (Model Context Protocol). This architecture provides security, scalability, and coordination for multi-agent workflows.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          COORDINATOR AGENT                               │
│                    (orchestrates workflows)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
           ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
           │   Worker 1   │ │   Worker 2   │ │   Worker 3   │
           │   (Daytona)  │ │   (Daytona)  │ │   (Daytona)  │
           └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
                  │                │                │
                  └────────────────┼────────────────┘
                                   │ HTTP/MCP
                                   ▼
                    ┌──────────────────────────────┐
                    │     OmoiOS MCP Server        │
                    │   (Railway Production)       │
                    │                              │
                    │  • Ticket Management         │
                    │  • Task Tracking             │
                    │  • Agent Collaboration       │
                    │  • Discovery Recording       │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │ Postgres │  │  Redis   │  │ pgvector │
              │ (tickets)│  │ (queues) │  │ (search) │
              └──────────┘  └──────────┘  └──────────┘
```

## Why This Architecture?

### Problem
OpenHands SDK agents need to:
- Execute code safely (can't run untrusted code on the host)
- Share state with other agents (tickets, tasks, discoveries)
- Collaborate and hand off work
- Maintain traceability (who did what, when)

### Solution
- **Daytona Sandboxes**: Isolated Linux environments for safe code execution
- **MCP Server**: Centralized backend accessible via HTTP
- **Typed Tool Wrappers**: OpenHands-native tools that call MCP endpoints

Agents only need HTTP access to the MCP server. No direct database connections, no shared filesystem, no security concerns.

## Production Deployment

### URLs
- **API**: `https://api.omoios.dev`
- **MCP Endpoint**: `https://api.omoios.dev/mcp/`

### Services (Railway)
| Service | Purpose |
|---------|---------|
| `omoi-api` | FastAPI backend + MCP server |
| `pgvector` | PostgreSQL with vector search |
| `Redis` | Task queues and caching |

## MCP Tools Reference

### Registration

```python
from omoi_os.tools.mcp_tools import register_mcp_tools_with_agent

# Add all 27 MCP tools to an agent
agent_tools = register_mcp_tools_with_agent(
    agent_tools=[],
    mcp_url="https://api.omoios.dev/mcp/"
)
```

### Available Tools (27 total)

#### Core Meta-Tools
| Tool | Description |
|------|-------------|
| `mcp__list_tools` | List all available MCP tools |
| `mcp__call_tool` | Call any MCP tool by name (low-level) |

#### Ticket Management
| Tool | Description |
|------|-------------|
| `mcp__create_ticket` | Create a new ticket |
| `mcp__get_ticket` | Get ticket details |
| `mcp__get_tickets` | List tickets with filters and pagination |
| `mcp__get_ticket_history` | Get complete change history |
| `mcp__update_ticket` | Update ticket fields |
| `mcp__change_ticket_status` | Change status with commit linking |
| `mcp__resolve_ticket` | Resolve and unblock dependents |
| `mcp__search_tickets` | Semantic/keyword/hybrid search |
| `mcp__add_ticket_comment` | Add a comment |
| `mcp__add_ticket_dependency` | Add a blocker |
| `mcp__remove_ticket_dependency` | Remove a blocker |
| `mcp__link_commit` | Link git commit to ticket |

#### Task Management
| Tool | Description |
|------|-------------|
| `mcp__create_task` | Create task for a ticket |
| `mcp__update_task_status` | Update task status |
| `mcp__get_task` | Get task details |
| `mcp__get_task_discoveries` | Get discoveries from a task |
| `mcp__get_workflow_graph` | Get full workflow visualization |

#### Agent Collaboration
| Tool | Description |
|------|-------------|
| `mcp__broadcast_message` | Message all agents |
| `mcp__send_message` | Direct message to specific agent |
| `mcp__get_messages` | Retrieve messages |
| `mcp__request_handoff` | Hand off task to another agent |

#### History & Trajectory
| Tool | Description |
|------|-------------|
| `mcp__get_phase_history` | Phase transitions for a ticket |
| `mcp__get_task_timeline` | Task execution timeline |
| `mcp__get_agent_trajectory` | Agent's accumulated context |
| `mcp__get_discoveries_by_type` | Find patterns across discoveries |

## Daytona Integration

### Purpose
Daytona provides isolated Linux sandboxes where agents can safely execute code. The integration makes these sandboxes work seamlessly with OpenHands SDK.

### Key Components

#### DaytonaLocalWorkspace
```python
# omoi_os/workspace/daytona_sdk.py
class DaytonaLocalWorkspace(LocalWorkspace):
    """Workspace that passes SDK assertions while routing to Daytona."""
    
    def __init__(self, daytona_workspace: DaytonaWorkspace, **kwargs):
        self._daytona = daytona_workspace
        super().__init__(**kwargs)
```

#### DaytonaTerminalExecutor
```python
# omoi_os/workspace/daytona_executor.py
class DaytonaTerminalExecutor:
    """Routes terminal commands to Daytona sandbox."""
    
    async def execute(self, action: ExecuteBashAction) -> ExecuteBashObservation:
        # Runs in Daytona, not locally
        result = self.sandbox.process.exec(action.command)
        return ExecuteBashObservation(content=[TextContent(text=result.output)])
```

### Verification
```bash
# Running in Daytona returns "Linux", not "Darwin" (macOS)
uname -s  # -> Linux
```

## Usage Examples

### Creating a Ticket
```python
from omoi_os.tools.mcp_tools import MCPCreateTicketAction

action = MCPCreateTicketAction(
    workflow_id="my-project",
    agent_id="worker-1",
    title="Implement user authentication",
    description="Add JWT-based auth to the API endpoints",
    priority="high",
    tags=["security", "api"]
)
```

### Searching Tickets
```python
from omoi_os.tools.mcp_tools import MCPSearchTicketsAction

action = MCPSearchTicketsAction(
    workflow_id="my-project",
    agent_id="worker-1",
    query="authentication bug",
    search_type="hybrid",  # semantic + keyword
    limit=10
)
```

### Agent Collaboration
```python
# Broadcast discovery to all agents
from omoi_os.tools.mcp_tools import MCPBroadcastMessageAction

action = MCPBroadcastMessageAction(
    sender_agent_id="worker-1",
    message="Found security vulnerability in auth module",
    message_type="discovery",
    ticket_id="ticket-123"
)

# Request handoff when blocked
from omoi_os.tools.mcp_tools import MCPRequestHandoffAction

action = MCPRequestHandoffAction(
    from_agent_id="worker-1",
    to_agent_id="security-specialist",
    task_id="task-456",
    reason="Requires security expertise",
    context={"vulnerability_type": "SQL injection"}
)
```

## File Reference

| File | Purpose |
|------|---------|
| `omoi_os/tools/mcp_tools.py` | All 27 typed MCP tool wrappers |
| `omoi_os/tools/__init__.py` | Package exports |
| `omoi_os/services/mcp_client.py` | HTTP client for MCP server |
| `omoi_os/mcp/fastmcp_server.py` | Server-side MCP tool implementations |
| `omoi_os/workspace/daytona_sdk.py` | Daytona workspace adapter |
| `omoi_os/workspace/daytona_executor.py` | Terminal command routing |
| `railway.json` | Railway deployment config |
| `config/production.yaml` | Production environment settings |

## Deployment

### Railway CLI
```bash
# Deploy to Railway
just deploy

# View logs
railway logs

# Run command in production
railway run python -c "..."
```

### Environment Variables
```
OMOIOS_ENV=production
DATABASE_URL=postgresql+psycopg://...
REDIS_URL=redis://...
JWT_SECRET_KEY=...
LLM_API_KEY=...
DAYTONA_API_KEY=...
```

## Workflow Example: Multi-Agent Bug Fix

```
1. Coordinator creates ticket: "Fix login timeout bug"
   └── mcp__create_ticket

2. Coordinator spawns Worker-1 in Daytona sandbox
   └── Worker-1 gets ticket via mcp__get_ticket

3. Worker-1 investigates, creates task
   └── mcp__create_task (phase: investigation)

4. Worker-1 finds root cause, broadcasts discovery
   └── mcp__broadcast_message (type: discovery)

5. Worker-1 needs database expertise, requests handoff
   └── mcp__request_handoff (to: db-specialist)

6. DB-Specialist implements fix in their sandbox
   └── mcp__update_task_status (status: completed)

7. DB-Specialist links commit and resolves ticket
   └── mcp__link_commit
   └── mcp__resolve_ticket

8. Resolution automatically unblocks dependent tickets
```

## Security Considerations

- **Sandbox Isolation**: Agents run in Daytona, can't access host filesystem
- **HTTP-Only Access**: Agents never have direct database credentials
- **Agent Identity**: All actions are attributed to specific agent IDs
- **Audit Trail**: Complete history via ticket_history and task timelines

## Next Steps

1. **Agent Templates**: Pre-configured agent types (researcher, implementer, reviewer)
2. **Workflow Automation**: Auto-spawn agents based on ticket type
3. **Discovery Patterns**: ML on discoveries to predict blockers
4. **Cost Tracking**: Monitor sandbox usage per workflow
