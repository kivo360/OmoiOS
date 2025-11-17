"""Agent collaboration API routes for messaging and handoff orchestration."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from omoi_os.api.dependencies import get_collaboration_service
from omoi_os.services.collaboration import CollaborationService
from omoi_os.models.collaboration import (
    AgentHandoffRequest,
    CollaborationMessage,
    CollaborationThread,
)

router = APIRouter()


class ThreadCreateRequest(BaseModel):
    subject: str = Field(..., description="Short summary of the collaboration topic")
    context_type: str = Field(..., description="ticket, task, or custom context")
    context_id: str = Field(..., description="Primary entity identifier (ticket/task id)")
    created_by_agent_id: str = Field(..., description="Agent ID opening the thread")
    participants: Optional[List[str]] = Field(default=None, description="Optional initial participants")
    metadata: Optional[dict] = Field(default=None, description="Arbitrary metadata payload")


class ThreadResponse(BaseModel):
    thread_id: str
    subject: str
    context_type: str
    context_id: str
    created_by_agent_id: str
    participants: List[str]
    metadata: Optional[dict] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_message_at: Optional[str] = None


class MessageCreateRequest(BaseModel):
    sender_agent_id: str = Field(..., description="Agent sending the message")
    body: str = Field(..., description="Message body")
    message_type: str = Field("text", description="text, handoff, system, etc.")
    target_agent_id: Optional[str] = Field(default=None, description="Direct recipient (optional)")
    payload: Optional[dict] = None
    metadata: Optional[dict] = None


class MessageResponse(BaseModel):
    message_id: str
    thread_id: str
    sender_agent_id: str
    target_agent_id: Optional[str] = None
    message_type: str
    body: str
    payload: Optional[dict] = None
    metadata: Optional[dict] = None
    created_at: Optional[str] = None


class HandoffCreateRequest(BaseModel):
    requesting_agent_id: str
    target_agent_id: Optional[str] = Field(default=None, description="Target agent (optional if registry selection later)")
    reason: Optional[str] = Field(default=None, description="Human-readable reason for the handoff")
    required_capabilities: Optional[List[str]] = Field(default=None, description="Skill requirements for target agent")
    ticket_id: Optional[str] = None
    task_id: Optional[str] = None
    metadata: Optional[dict] = None


class HandoffResponse(BaseModel):
    handoff_id: str
    thread_id: str
    requesting_agent_id: str
    target_agent_id: Optional[str] = None
    status: str
    required_capabilities: List[str] = Field(default_factory=list)
    reason: Optional[str] = None
    ticket_id: Optional[str] = None
    task_id: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: Optional[str] = None


def serialize_thread(thread: CollaborationThread) -> ThreadResponse:
    return ThreadResponse(
        thread_id=thread.id,
        subject=thread.subject,
        context_type=thread.context_type,
        context_id=thread.context_id,
        created_by_agent_id=thread.created_by_agent_id,
        participants=thread.participants or [],
        metadata=thread.metadata,
        created_at=thread.created_at.isoformat() if thread.created_at else None,
        updated_at=thread.updated_at.isoformat() if thread.updated_at else None,
        last_message_at=thread.last_message_at.isoformat() if thread.last_message_at else None,
    )


def serialize_message(message: CollaborationMessage) -> MessageResponse:
    return MessageResponse(
        message_id=message.id,
        thread_id=message.thread_id,
        sender_agent_id=message.sender_agent_id,
        target_agent_id=message.target_agent_id,
        message_type=message.message_type,
        body=message.body,
        payload=message.payload,
        metadata=message.metadata,
        created_at=message.created_at.isoformat() if message.created_at else None,
    )


def serialize_handoff(handoff: AgentHandoffRequest) -> HandoffResponse:
    return HandoffResponse(
        handoff_id=handoff.id,
        thread_id=handoff.thread_id,
        requesting_agent_id=handoff.requesting_agent_id,
        target_agent_id=handoff.target_agent_id,
        status=handoff.status,
        required_capabilities=handoff.required_capabilities or [],
        reason=handoff.reason,
        ticket_id=handoff.ticket_id,
        task_id=handoff.task_id,
        metadata=handoff.metadata,
        created_at=handoff.created_at.isoformat() if handoff.created_at else None,
    )


@router.post("/agent-collab/threads", response_model=ThreadResponse, status_code=201)
async def create_thread(
    request: ThreadCreateRequest,
    service: CollaborationService = Depends(get_collaboration_service),
):
    """Create a new collaboration thread."""
    thread = service.create_thread(
        subject=request.subject,
        context_type=request.context_type,
        context_id=request.context_id,
        created_by_agent_id=request.created_by_agent_id,
        participants=request.participants or [],
        metadata=request.metadata,
    )
    return serialize_thread(thread)


@router.get("/agent-collab/threads", response_model=List[ThreadResponse])
async def list_threads(
    agent_id: Optional[str] = Query(None, description="Filter by participant agent id"),
    context_type: Optional[str] = Query(None),
    context_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    service: CollaborationService = Depends(get_collaboration_service),
):
    """List collaboration threads filtered by participant or context."""
    threads = service.list_threads(
        participant_agent_id=agent_id,
        context_type=context_type,
        context_id=context_id,
        limit=limit,
    )
    return [serialize_thread(thread) for thread in threads]


@router.get("/agent-collab/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    service: CollaborationService = Depends(get_collaboration_service),
):
    """Fetch a single collaboration thread."""
    try:
        thread = service.get_thread(thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_thread(thread)


@router.post(
    "/agent-collab/threads/{thread_id}/messages",
    response_model=MessageResponse,
    status_code=201,
)
async def post_message(
    thread_id: str,
    request: MessageCreateRequest,
    service: CollaborationService = Depends(get_collaboration_service),
):
    """Send a message on an existing thread."""
    try:
        message = service.send_message(
            thread_id=thread_id,
            sender_agent_id=request.sender_agent_id,
            body=request.body,
            message_type=request.message_type,
            target_agent_id=request.target_agent_id,
            payload=request.payload,
            metadata=request.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_message(message)


@router.get("/agent-collab/threads/{thread_id}/messages", response_model=List[MessageResponse])
async def list_messages(
    thread_id: str,
    limit: int = Query(50, ge=1, le=200),
    service: CollaborationService = Depends(get_collaboration_service),
):
    """List messages for a collaboration thread."""
    messages = service.list_messages(thread_id=thread_id, limit=limit)
    return [serialize_message(message) for message in messages]


@router.post(
    "/agent-collab/threads/{thread_id}/handoffs",
    response_model=HandoffResponse,
    status_code=201,
)
async def create_handoff_request(
    thread_id: str,
    request: HandoffCreateRequest,
    service: CollaborationService = Depends(get_collaboration_service),
):
    """Request a handoff from within a collaboration thread."""
    try:
        handoff = service.request_handoff(
            thread_id=thread_id,
            requesting_agent_id=request.requesting_agent_id,
            target_agent_id=request.target_agent_id,
            reason=request.reason,
            required_capabilities=request.required_capabilities,
            ticket_id=request.ticket_id,
            task_id=request.task_id,
            metadata=request.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_handoff(handoff)


@router.get(
    "/agent-collab/threads/{thread_id}/handoffs",
    response_model=List[HandoffResponse],
)
async def list_handoffs(
    thread_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    service: CollaborationService = Depends(get_collaboration_service),
):
    """List handoff requests for a thread."""
    handoffs = service.list_handoffs(thread_id=thread_id, status=status)
    return [serialize_handoff(handoff) for handoff in handoffs]
