"""FastMCP server for OmoiOS agent tools.

This server provides MCP tools for agents to interact with the system,
including ticket management, task creation, and discovery tracking.
"""

from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List

from fastmcp import FastMCP, Context
from pydantic import Field

from omoi_os.models.task_discovery import DiscoveryType
from omoi_os.services.database import DatabaseService
from omoi_os.services.discovery import DiscoveryService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.ticketing.services.ticket_service import TicketService


# Global services (injected at startup)
_db: Optional[DatabaseService] = None
_event_bus: Optional[EventBusService] = None
_task_queue: Optional[TaskQueueService] = None
_discovery_service: Optional[DiscoveryService] = None
_collaboration_service: Optional[Any] = None


def initialize_mcp_services(
    db: DatabaseService,
    event_bus: EventBusService,
    task_queue: TaskQueueService,
    discovery_service: DiscoveryService,
    collaboration_service: Optional[Any] = None,
) -> None:
    """Initialize global services for MCP server.
    
    Args:
        db: Database service
        event_bus: Event bus service
        task_queue: Task queue service
        discovery_service: Discovery service
        collaboration_service: Optional collaboration service for agent messaging
    """
    global _db, _event_bus, _task_queue, _discovery_service, _collaboration_service
    _db = db
    _event_bus = event_bus
    _task_queue = task_queue
    _discovery_service = discovery_service
    _collaboration_service = collaboration_service


# Create FastMCP server
mcp = FastMCP("OmoiOS Agent Tools")


# ============================================================================
# Ticket Management Tools (migrated from OpenHands MCP tools)
# ============================================================================

@mcp.tool()
def create_ticket(
    ctx: Context,
    workflow_id: str,
    agent_id: str,
    title: str = Field(..., min_length=3, max_length=500),
    description: str = Field(..., min_length=10),
    ticket_type: str = Field(default="task"),
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$"),
    initial_status: Optional[str] = None,
    assigned_agent_id: Optional[str] = None,
    parent_ticket_id: Optional[str] = None,
    blocked_by_ticket_ids: List[str] = Field(default_factory=list),
    tags: List[str] = Field(default_factory=list),
    related_task_ids: List[str] = Field(default_factory=list),
) -> Dict[str, Any]:
    """Create a new ticket in the workflow tracking system.
    
    Args:
        workflow_id: Workflow identifier
        agent_id: ID of agent creating the ticket
        title: Ticket title (3-500 characters)
        description: Ticket description (minimum 10 characters)
        ticket_type: Type of ticket (default: "task")
        priority: Priority level (low, medium, high, critical)
        initial_status: Optional initial status
        assigned_agent_id: Optional agent to assign ticket to
        parent_ticket_id: Optional parent ticket ID
        blocked_by_ticket_ids: List of ticket IDs blocking this ticket
        tags: List of tags for the ticket
        related_task_ids: List of related task IDs
        
    Returns:
        Dictionary with created ticket information
    """
    if not _db:
        raise RuntimeError("Database service not initialized")
    
    with _db.get_session() as session:
        svc = TicketService(session)
        result = svc.create_ticket(
            workflow_id=workflow_id,
            agent_id=agent_id,
            title=title,
            description=description,
            ticket_type=ticket_type,
            priority=priority,
            initial_status=initial_status,
            assigned_agent_id=assigned_agent_id,
            parent_ticket_id=parent_ticket_id,
            blocked_by_ticket_ids=blocked_by_ticket_ids,
            tags=tags,
            related_task_ids=related_task_ids,
        )
        ctx.info(f"Created ticket {result.get('ticket_id')} with title: {title[:50]}")
        return result


@mcp.tool()
def update_ticket(
    ctx: Context,
    ticket_id: str,
    agent_id: str,
    updates: Dict[str, Any],
    update_comment: Optional[str] = None,
) -> Dict[str, Any]:
    """Update fields of an existing ticket.
    
    Args:
        ticket_id: ID of ticket to update
        agent_id: ID of agent making the update
        updates: Dictionary of fields to update
        update_comment: Optional comment explaining the update
        
    Returns:
        Dictionary with updated ticket information
    """
    if not _db:
        raise RuntimeError("Database service not initialized")
    
    with _db.get_session() as session:
        svc = TicketService(session)
        result = svc.update_ticket(
            ticket_id=ticket_id,
            agent_id=agent_id,
            updates=updates,
            update_comment=update_comment,
        )
        ctx.info(f"Updated ticket {ticket_id}")
        return result


@mcp.tool()
def change_ticket_status(
    ctx: Context,
    ticket_id: str,
    agent_id: str,
    new_status: str,
    comment: str = Field(..., min_length=10),
    commit_sha: Optional[str] = None,
) -> Dict[str, Any]:
    """Change ticket status with optional commit linkage.
    
    Args:
        ticket_id: ID of ticket to update
        agent_id: ID of agent making the change
        new_status: New status for the ticket
        comment: Comment explaining the status change (minimum 10 characters)
        commit_sha: Optional git commit SHA to link
        
    Returns:
        Dictionary with updated ticket information
    """
    if not _db:
        raise RuntimeError("Database service not initialized")
    
    with _db.get_session() as session:
        svc = TicketService(session)
        result = svc.change_status(
            ticket_id=ticket_id,
            agent_id=agent_id,
            new_status=new_status,
            comment=comment,
            commit_sha=commit_sha,
        )
        ctx.info(f"Changed ticket {ticket_id} status to {new_status}")
        return result


@mcp.tool()
def search_tickets(
    ctx: Context,
    workflow_id: str,
    agent_id: str,
    query: str = Field(..., min_length=3),
    search_type: str = Field(default="hybrid", pattern="^(semantic|keyword|hybrid)$"),
    filters: Dict[str, Any] = Field(default_factory=dict),
    limit: int = 10,
    include_comments: bool = True,
) -> Dict[str, Any]:
    """Search tickets using semantic, keyword, or hybrid search.
    
    Args:
        workflow_id: Workflow identifier
        agent_id: ID of agent performing search
        query: Search query (minimum 3 characters)
        search_type: Type of search (semantic, keyword, or hybrid)
        filters: Additional filters to apply
        limit: Maximum number of results
        include_comments: Whether to include comments in search
        
    Returns:
        Dictionary with search results
    """
    if not _db:
        raise RuntimeError("Database service not initialized")
    
    from omoi_os.ticketing.services.ticket_search_service import TicketSearchService
    
    with _db.get_session() as session:
        svc = TicketSearchService(session)
        if search_type == "semantic":
            data = svc.semantic_search(
                query_text=query,
                workflow_id=workflow_id,
                limit=limit,
                filters=filters,
            )
            result = {"success": True, "mode": "semantic", **data}
        elif search_type == "keyword":
            data = svc.search_by_keywords(
                keywords=query,
                workflow_id=workflow_id,
                filters=filters,
            )
            result = {"success": True, "mode": "keyword", **data}
        else:
            data = svc.hybrid_search(
                query_text=query,
                workflow_id=workflow_id,
                limit=limit,
                filters=filters,
                include_comments=include_comments,
            )
            result = {"success": True, "mode": "hybrid", **data}
        
        ctx.info(f"Found {len(result.get('tickets', []))} tickets matching '{query}'")
        return result


# ============================================================================
# Task Management Tools (NEW - with DiscoveryService integration)
# ============================================================================

@mcp.tool()
def create_task(
    ctx: Context,
    ticket_id: str,
    phase_id: str,
    description: str = Field(..., min_length=10),
    task_type: str = Field(default="implementation"),
    priority: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$"),
    discovery_type: Optional[str] = Field(
        default=None,
        description="Type of discovery that triggered this task (e.g., 'bug', 'optimization', 'missing_requirement')"
    ),
    discovery_description: Optional[str] = Field(
        default=None,
        description="Description of what was discovered that led to creating this task"
    ),
    source_task_id: Optional[str] = Field(
        default=None,
        description="ID of the task that discovered this need (for workflow branching)"
    ),
    priority_boost: bool = Field(
        default=False,
        description="Whether to boost priority based on discovery importance"
    ),
    dependencies: Optional[List[str]] = Field(
        default_factory=list,
        description="List of task IDs this task depends on"
    ),
) -> Dict[str, Any]:
    """Create a new task and optionally record it as a discovery-based branch.
    
    This tool enables agents to spawn new tasks during execution. If discovery_type
    and source_task_id are provided, it automatically uses DiscoveryService to track
    WHY the workflow branched and WHAT was discovered.
    
    Args:
        ticket_id: ID of the ticket this task belongs to
        phase_id: Phase identifier (e.g., "PHASE_IMPLEMENTATION")
        description: Task description (minimum 10 characters)
        task_type: Type of task (default: "implementation")
        priority: Task priority (LOW, MEDIUM, HIGH, CRITICAL)
        discovery_type: Optional discovery type if this is a discovery-based task
        discovery_description: Optional description of what was discovered
        source_task_id: Optional source task ID if this branches from another task
        priority_boost: Whether to boost priority based on discovery
        dependencies: List of task IDs this task depends on
        
    Returns:
        Dictionary with created task information and discovery record (if applicable)
    """
    if not _db or not _task_queue or not _discovery_service:
        raise RuntimeError("Required services not initialized")
    
    with _db.get_session() as session:
        # Create the task via TaskQueueService
        # Convert dependencies list to dict format if provided
        deps_dict = None
        if dependencies:
            deps_dict = {"depends_on": dependencies}
        
        task = _task_queue.enqueue_task(
            ticket_id=ticket_id,
            phase_id=phase_id,
            task_type=task_type,
            description=description,
            priority=priority,
            dependencies=deps_dict,
            session=session,
        )
        
        result = {
            "success": True,
            "task_id": str(task.id),
            "ticket_id": ticket_id,
            "phase_id": phase_id,
            "description": description,
            "priority": priority,
            "status": task.status,
        }
        
        # If this is a discovery-based task, record it with DiscoveryService
        if discovery_type and source_task_id and _discovery_service:
            try:
                discovery, spawned_task = _discovery_service.record_discovery_and_branch(
                    session=session,
                    source_task_id=source_task_id,
                    discovery_type=discovery_type,
                    description=discovery_description or description,
                    spawn_phase_id=phase_id,
                    spawn_description=description,
                    spawn_priority=priority,
                    priority_boost=priority_boost,
                    spawn_metadata={
                        "created_via_mcp": True,
                        "agent_tool": "create_task",
                    },
                )
                
                result["discovery"] = {
                    "discovery_id": str(discovery.id),
                    "discovery_type": discovery_type,
                    "description": discovery.description,
                    "spawned_task_id": str(spawned_task.id),
                    "priority_boost": priority_boost,
                }
                
                ctx.info(
                    f"Created task {task.id} from discovery {discovery.id} "
                    f"(type: {discovery_type})"
                )
            except Exception as e:
                ctx.warning(f"Failed to record discovery: {e}")
                # Task was still created, just discovery tracking failed
        else:
            ctx.info(f"Created task {task.id} for ticket {ticket_id}")
        
        session.commit()
        return result


@mcp.tool()
def update_task_status(
    ctx: Context,
    task_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    """Update task status and result.
    
    Args:
        task_id: ID of task to update
        status: New status (pending, running, completed, failed)
        result: Optional task result dictionary
        error_message: Optional error message if status is failed
        
    Returns:
        Dictionary with updated task information
    """
    if not _task_queue:
        raise RuntimeError("Task queue service not initialized")
    
    _task_queue.update_task_status(
        task_id=task_id,
        status=status,
        result=result,
        error_message=error_message,
    )
    
    ctx.info(f"Updated task {task_id} status to {status}")
    return {
        "success": True,
        "task_id": task_id,
        "status": status,
    }


@mcp.tool()
def get_task(
    ctx: Context,
    task_id: str,
) -> Dict[str, Any]:
    """Get details of a single task.
    
    Args:
        task_id: ID of task to retrieve
        
    Returns:
        Dictionary with task information
    """
    if not _db:
        raise RuntimeError("Database service not initialized")
    
    from omoi_os.models.task import Task
    
    with _db.get_session() as session:
        task = session.query(Task).filter_by(id=task_id).first()
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        
        return {
            "success": True,
            "task_id": str(task.id),
            "ticket_id": task.ticket_id,
            "phase_id": task.phase_id,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "dependencies": task.dependencies or [],
        }


# ============================================================================
# Discovery Tools (NEW - for querying discovery history)
# ============================================================================

@mcp.tool()
def get_task_discoveries(
    ctx: Context,
    task_id: str,
    resolution_status: Optional[str] = None,
) -> Dict[str, Any]:
    """Get all discoveries made by a specific task.
    
    Args:
        task_id: Source task ID
        resolution_status: Optional filter by resolution status (open, resolved)
        
    Returns:
        Dictionary with list of discoveries
    """
    if not _db or not _discovery_service:
        raise RuntimeError("Required services not initialized")
    
    with _db.get_session() as session:
        discoveries = _discovery_service.get_discoveries_by_task(
            session=session,
            task_id=task_id,
            resolution_status=resolution_status,
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "discoveries": [
                {
                    "discovery_id": str(d.id),
                    "discovery_type": d.discovery_type,
                    "description": d.description,
                    "spawned_task_ids": d.spawned_task_ids,
                    "discovered_at": d.discovered_at.isoformat() if d.discovered_at else None,
                    "resolution_status": d.resolution_status,
                    "priority_boost": d.priority_boost,
                }
                for d in discoveries
            ],
        }


@mcp.tool()
def get_workflow_graph(
    ctx: Context,
    ticket_id: str,
) -> Dict[str, Any]:
    """Build a workflow graph showing all discoveries and branches for a ticket.
    
    Args:
        ticket_id: Ticket ID to analyze
        
    Returns:
        Dictionary representing the branching structure with nodes and edges
    """
    if not _db or not _discovery_service:
        raise RuntimeError("Required services not initialized")
    
    with _db.get_session() as session:
        graph = _discovery_service.get_workflow_graph(
            session=session,
            ticket_id=ticket_id,
        )
        
        ctx.info(f"Built workflow graph for ticket {ticket_id} with {len(graph['nodes'])} nodes")
        return {
            "success": True,
            "ticket_id": ticket_id,
            **graph,
        }


# ============================================================================
# Agent Communication Tools (NEW - Recommendation 2)
# ============================================================================

@mcp.tool()
def broadcast_message(
    ctx: Context,
    sender_agent_id: str = Field(..., description="Your agent ID"),
    message: str = Field(..., min_length=1, description="Message content to broadcast to all active agents"),
    message_type: str = Field(default="info", description="Type of message (info, question, warning, discovery)"),
    ticket_id: Optional[str] = Field(None, description="Optional ticket ID for context"),
    task_id: Optional[str] = Field(None, description="Optional task ID for context"),
) -> Dict[str, Any]:
    """Broadcast a message to all active agents in the system.
    
    Use this when you need to share information that affects all agents,
    ask questions when you don't know who to ask, or announce completion
    of shared infrastructure.
    
    Args:
        sender_agent_id: Your agent ID (required)
        message: Message content to broadcast
        message_type: Type of message (info, question, warning, discovery)
        ticket_id: Optional ticket ID for context
        task_id: Optional task ID for context
        
    Returns:
        Dictionary with success status and recipient count
    """
    if not _collaboration_service:
        raise RuntimeError("Collaboration service not initialized")
    
    # Use simplified broadcast API
    result = _collaboration_service.broadcast_message(
        from_agent_id=sender_agent_id,
        message=message,
        message_type=message_type,
        ticket_id=ticket_id,
        task_id=task_id,
    )
    
    ctx.info(f"Broadcast message to {result['recipient_count']} agent(s)")
    return result


@mcp.tool()
def send_message(
    ctx: Context,
    sender_agent_id: str = Field(..., description="Your agent ID"),
    recipient_agent_id: str = Field(..., description="Target agent ID"),
    message: str = Field(..., min_length=1, description="Message content"),
    message_type: str = Field(default="info", description="Type of message (info, question, handoff_request, etc.)"),
    ticket_id: Optional[str] = Field(None, description="Optional ticket ID for context"),
    task_id: Optional[str] = Field(None, description="Optional task ID for context"),
) -> Dict[str, Any]:
    """Send a direct message to a specific agent.
    
    Use this for coordinating with an agent on a related task, asking a
    specific agent for information, or responding to another agent's message.
    
    Args:
        sender_agent_id: Your agent ID (required)
        recipient_agent_id: Target agent's ID
        message: Message content
        message_type: Type of message (info, question, handoff_request, etc.)
        ticket_id: Optional ticket ID for context
        task_id: Optional task ID for context
        
    Returns:
        Dictionary with success status and message details
    """
    if not _collaboration_service:
        raise RuntimeError("Collaboration service not initialized")
    
    # Create or find thread for these two agents
    thread = _collaboration_service.get_or_create_thread(
        participants=[sender_agent_id, recipient_agent_id],
        ticket_id=ticket_id,
        task_id=task_id,
    )
    
    # Send message in thread
    message_obj = _collaboration_service.send_message(
        thread_id=thread.id,
        from_agent_id=sender_agent_id,
        to_agent_id=recipient_agent_id,
        message_type=message_type,
        content=message,
    )
    
    ctx.info(f"Sent message to agent {recipient_agent_id[:8]}")
    return {
        "success": True,
        "message_id": message_obj.id,
        "thread_id": thread.id,
        "recipient_agent_id": recipient_agent_id,
    }


@mcp.tool()
def get_messages(
    ctx: Context,
    agent_id: str = Field(..., description="Your agent ID"),
    thread_id: Optional[str] = Field(None, description="Optional thread ID to filter by"),
    limit: int = Field(default=50, ge=1, le=100, description="Maximum messages to return"),
    unread_only: bool = Field(default=False, description="Only return unread messages"),
) -> Dict[str, Any]:
    """Get messages for an agent, optionally filtered by thread.
    
    Args:
        agent_id: Your agent ID
        thread_id: Optional thread ID to filter by
        limit: Maximum messages to return
        unread_only: Only return unread messages
        
    Returns:
        Dictionary with list of messages
    """
    if not _collaboration_service:
        raise RuntimeError("Collaboration service not initialized")
    
    if thread_id:
        # Get messages from specific thread
        messages = _collaboration_service.get_thread_messages(
            thread_id=thread_id,
            limit=limit,
            unread_only=unread_only,
        )
    else:
        # Get all messages for this agent
        messages = _collaboration_service.get_agent_messages(
            agent_id=agent_id,
            limit=limit,
            unread_only=unread_only,
        )
    
    ctx.info(f"Retrieved {len(messages)} message(s)")
    return {
        "success": True,
        "messages": [
            {
                "message_id": m.id,
                "thread_id": m.thread_id,
                "from_agent_id": m.from_agent_id,
                "to_agent_id": m.to_agent_id,
                "message_type": m.message_type,
                "content": m.content,
                "read_at": m.read_at.isoformat() if m.read_at else None,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@mcp.tool()
def request_handoff(
    ctx: Context,
    from_agent_id: str = Field(..., description="Your agent ID"),
    to_agent_id: str = Field(..., description="Target agent ID to hand off to"),
    task_id: str = Field(..., description="Task ID to hand off"),
    reason: str = Field(..., min_length=10, description="Reason for handoff"),
    context: Optional[Dict[str, Any]] = Field(None, description="Optional handoff context"),
) -> Dict[str, Any]:
    """Request a task handoff to another agent.
    
    Use this when you need to transfer a task to another agent, for example
    if you're stuck, if the task requires different capabilities, or if you
    need to focus on higher priority work.
    
    Args:
        from_agent_id: Your agent ID
        to_agent_id: Target agent ID
        task_id: Task ID to hand off
        reason: Reason for handoff (minimum 10 characters)
        context: Optional handoff context (current progress, blockers, etc.)
        
    Returns:
        Dictionary with handoff thread and message details
    """
    if not _collaboration_service:
        raise RuntimeError("Collaboration service not initialized")
    
    thread, message = _collaboration_service.request_handoff(
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        task_id=task_id,
        reason=reason,
        context=context,
    )
    
    ctx.info(f"Requested handoff of task {task_id} to agent {to_agent_id[:8]}")
    return {
        "success": True,
        "thread_id": thread.id,
        "message_id": message.id,
        "task_id": task_id,
        "to_agent_id": to_agent_id,
    }


# Create HTTP app for FastAPI mounting
mcp_app = mcp.http_app(path="/mcp")

