"""API routes for agent collaboration and messaging."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from omoi_os.api.dependencies import get_collaboration_service
from omoi_os.services.collaboration import CollaborationService

router = APIRouter()


# ---------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------


class CreateThreadRequest(BaseModel):
    thread_type: str = Field(..., description="Type: handoff, review, consultation")
    participants: List[str] = Field(..., description="List of agent IDs")
    ticket_id: Optional[str] = Field(None)
    task_id: Optional[str] = Field(None)
    thread_metadata: Optional[dict] = Field(None)


class ThreadDTO(BaseModel):
    thread_id: str
    thread_type: str
    ticket_id: Optional[str]
    task_id: Optional[str]
    participants: List[str]
    status: str
    thread_metadata: Optional[dict]
    created_at: str
    closed_at: Optional[str]


class SendMessageRequest(BaseModel):
    thread_id: str
    from_agent_id: str
    message_type: str = Field(..., description="info, question, handoff_request, etc.")
    content: str
    to_agent_id: Optional[str] = Field(None, description="None for broadcast")
    message_metadata: Optional[dict] = Field(None)


class MessageDTO(BaseModel):
    message_id: str
    thread_id: str
    from_agent_id: str
    to_agent_id: Optional[str]
    message_type: str
    content: str
    message_metadata: Optional[dict]
    read_at: Optional[str]
    created_at: str


class HandoffRequest(BaseModel):
    from_agent_id: str
    to_agent_id: str
    task_id: str
    reason: str
    context: Optional[dict] = Field(None)


class HandoffResponse(BaseModel):
    thread_id: str
    message_id: str


# ---------------------------------------------------------------------
# Thread Endpoints
# ---------------------------------------------------------------------


@router.post("/collaboration/threads", response_model=ThreadDTO, status_code=201)
async def create_thread(
    request: CreateThreadRequest,
    collab_service: CollaborationService = Depends(get_collaboration_service),
):
    """Create a new collaboration thread."""
    try:
        thread = collab_service.create_thread(
            thread_type=request.thread_type,
            participants=request.participants,
            ticket_id=request.ticket_id,
            task_id=request.task_id,
            thread_metadata=request.thread_metadata,
        )
        return ThreadDTO(
            thread_id=thread.id,
            thread_type=thread.thread_type,
            ticket_id=thread.ticket_id,
            task_id=thread.task_id,
            participants=thread.participants,
            status=thread.status,
            thread_metadata=thread.thread_metadata,
            created_at=thread.created_at.isoformat(),
            closed_at=thread.closed_at.isoformat() if thread.closed_at else None,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to create thread: {exc}"
        ) from exc


@router.get("/collaboration/threads", response_model=List[ThreadDTO])
async def list_threads(
    agent_id: Optional[str] = None,
    ticket_id: Optional[str] = None,
    status: Optional[str] = None,
    collab_service: CollaborationService = Depends(get_collaboration_service),
):
    """List collaboration threads with optional filters."""
    try:
        threads = collab_service.list_threads(
            agent_id=agent_id,
            ticket_id=ticket_id,
            status=status,
        )
        return [
            ThreadDTO(
                thread_id=t.id,
                thread_type=t.thread_type,
                ticket_id=t.ticket_id,
                task_id=t.task_id,
                participants=t.participants,
                status=t.status,
                thread_metadata=t.thread_metadata,
                created_at=t.created_at.isoformat(),
                closed_at=t.closed_at.isoformat() if t.closed_at else None,
            )
            for t in threads
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to list threads: {exc}"
        ) from exc


@router.post("/collaboration/threads/{thread_id}/close", response_model=dict)
async def close_thread(
    thread_id: str,
    collab_service: CollaborationService = Depends(get_collaboration_service),
):
    """Close a collaboration thread."""
    success = collab_service.close_thread(thread_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")
    return {"success": True, "thread_id": thread_id}


# ---------------------------------------------------------------------
# Messaging Endpoints
# ---------------------------------------------------------------------


@router.post("/collaboration/messages", response_model=MessageDTO, status_code=201)
async def send_message(
    request: SendMessageRequest,
    collab_service: CollaborationService = Depends(get_collaboration_service),
):
    """Send a message in a collaboration thread."""
    try:
        message = collab_service.send_message(
            thread_id=request.thread_id,
            from_agent_id=request.from_agent_id,
            to_agent_id=request.to_agent_id,
            message_type=request.message_type,
            content=request.content,
            message_metadata=request.message_metadata,
        )
        return MessageDTO(
            message_id=message.id,
            thread_id=message.thread_id,
            from_agent_id=message.from_agent_id,
            to_agent_id=message.to_agent_id,
            message_type=message.message_type,
            content=message.content,
            message_metadata=message.message_metadata,
            read_at=message.read_at.isoformat() if message.read_at else None,
            created_at=message.created_at.isoformat(),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to send message: {exc}"
        ) from exc


@router.get("/collaboration/threads/{thread_id}/messages", response_model=List[MessageDTO])
async def get_thread_messages(
    thread_id: str,
    limit: int = 50,
    unread_only: bool = False,
    collab_service: CollaborationService = Depends(get_collaboration_service),
):
    """Get messages in a thread."""
    try:
        messages = collab_service.get_thread_messages(
            thread_id=thread_id,
            limit=limit,
            unread_only=unread_only,
        )
        return [
            MessageDTO(
                message_id=m.id,
                thread_id=m.thread_id,
                from_agent_id=m.from_agent_id,
                to_agent_id=m.to_agent_id,
                message_type=m.message_type,
                content=m.content,
                message_metadata=m.message_metadata,
                read_at=m.read_at.isoformat() if m.read_at else None,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to get messages: {exc}"
        ) from exc


@router.post("/collaboration/messages/{message_id}/read", response_model=dict)
async def mark_message_read(
    message_id: str,
    collab_service: CollaborationService = Depends(get_collaboration_service),
):
    """Mark a message as read."""
    success = collab_service.mark_message_read(message_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Message {message_id} not found")
    return {"success": True, "message_id": message_id}


# ---------------------------------------------------------------------
# Handoff Endpoints
# ---------------------------------------------------------------------


@router.post("/collaboration/handoff/request", response_model=HandoffResponse)
async def request_handoff(
    request: HandoffRequest,
    collab_service: CollaborationService = Depends(get_collaboration_service),
):
    """Request a task handoff to another agent."""
    try:
        thread, message = collab_service.request_handoff(
            from_agent_id=request.from_agent_id,
            to_agent_id=request.to_agent_id,
            task_id=request.task_id,
            reason=request.reason,
            context=request.context,
        )
        return HandoffResponse(thread_id=thread.id, message_id=message.id)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to request handoff: {exc}"
        ) from exc


@router.post("/collaboration/handoff/{thread_id}/accept", response_model=MessageDTO)
async def accept_handoff(
    thread_id: str,
    accepting_agent_id: str,
    message: str = "Handoff accepted",
    collab_service: CollaborationService = Depends(get_collaboration_service),
):
    """Accept a handoff request."""
    try:
        response_msg = collab_service.accept_handoff(
            thread_id=thread_id,
            accepting_agent_id=accepting_agent_id,
            message=message,
        )
        return MessageDTO(
            message_id=response_msg.id,
            thread_id=response_msg.thread_id,
            from_agent_id=response_msg.from_agent_id,
            to_agent_id=response_msg.to_agent_id,
            message_type=response_msg.message_type,
            content=response_msg.content,
            message_metadata=response_msg.message_metadata,
            read_at=response_msg.read_at.isoformat() if response_msg.read_at else None,
            created_at=response_msg.created_at.isoformat(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to accept handoff: {exc}"
        ) from exc


@router.post("/collaboration/handoff/{thread_id}/decline", response_model=MessageDTO)
async def decline_handoff(
    thread_id: str,
    declining_agent_id: str,
    reason: str,
    collab_service: CollaborationService = Depends(get_collaboration_service),
):
    """Decline a handoff request."""
    try:
        response_msg = collab_service.decline_handoff(
            thread_id=thread_id,
            declining_agent_id=declining_agent_id,
            reason=reason,
        )
        return MessageDTO(
            message_id=response_msg.id,
            thread_id=response_msg.thread_id,
            from_agent_id=response_msg.from_agent_id,
            to_agent_id=response_msg.to_agent_id,
            message_type=response_msg.message_type,
            content=response_msg.content,
            message_metadata=response_msg.message_metadata,
            read_at=response_msg.read_at.isoformat() if response_msg.read_at else None,
            created_at=response_msg.created_at.isoformat(),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to decline handoff: {exc}"
        ) from exc

