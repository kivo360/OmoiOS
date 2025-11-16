from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Optional

from pydantic import Field

from openhands.sdk import Action, Observation, TextContent, ToolDefinition
from openhands.sdk.tool import register_tool

from omoi_os.ticketing.db import get_session
from omoi_os.ticketing.services.ticket_search_service import TicketSearchService
from omoi_os.ticketing.services.ticket_service import TicketService


# ---------- Actions ----------

class CreateTicketAction(Action):
    workflow_id: str
    agent_id: str
    title: str = Field(min_length=3, max_length=500)
    description: str = Field(min_length=10)
    ticket_type: str = Field(default="task")
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    initial_status: Optional[str] = None
    assigned_agent_id: Optional[str] = None
    parent_ticket_id: Optional[str] = None
    blocked_by_ticket_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    related_task_ids: list[str] = Field(default_factory=list)


class UpdateTicketAction(Action):
    ticket_id: str
    agent_id: str
    updates: dict[str, Any]
    update_comment: Optional[str] = None


class ChangeStatusAction(Action):
    ticket_id: str
    agent_id: str
    new_status: str
    comment: str = Field(min_length=10)
    commit_sha: Optional[str] = None


class AddCommentAction(Action):
    ticket_id: str
    agent_id: str
    comment_text: str = Field(min_length=1)
    comment_type: str = Field(default="general")
    mentions: list[str] = Field(default_factory=list)
    attachments: list[str] = Field(default_factory=list)


class SearchTicketsAction(Action):
    workflow_id: str
    agent_id: str
    query: str = Field(min_length=3)
    search_type: str = Field(default="hybrid", pattern="^(semantic|keyword|hybrid)$")
    filters: dict[str, Any] = Field(default_factory=dict)
    limit: int = 10
    include_comments: bool = True


class GetTicketsAction(Action):
    workflow_id: str
    agent_id: str
    status: Optional[str] = None
    ticket_type: Optional[str] = None
    priority: Optional[str] = None
    assigned_agent_id: Optional[str] = None
    include_completed: bool = True
    limit: int = 50
    offset: int = 0
    sort_by: str = Field(default="created_at", pattern="^(created_at|updated_at|priority|status)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class GetTicketAction(Action):
    ticket_id: str


class ResolveTicketAction(Action):
    ticket_id: str
    agent_id: str
    resolution_comment: str = Field(min_length=10)
    commit_sha: Optional[str] = None


class LinkCommitAction(Action):
    ticket_id: str
    agent_id: str
    commit_sha: str
    commit_message: Optional[str] = None


# ---------- Observation ----------

class GenericObservation(Observation):
    payload: dict[str, Any] = Field(default_factory=dict)

    @property
    def to_llm_content(self) -> Sequence[TextContent]:
        return [TextContent(text=str(self.payload))]


# ---------- Executors ----------

def _obs(data: dict[str, Any]) -> GenericObservation:
    return GenericObservation(payload=data)


def _with_service(func):
    def wrapper(action, conversation=None):  # noqa: ARG001
        with get_session() as session:
            return func(session, action)
    return wrapper


@_with_service
def exec_create_ticket(session, action: CreateTicketAction) -> GenericObservation:
    svc = TicketService(session)
    result = svc.create_ticket(
        workflow_id=action.workflow_id,
        agent_id=action.agent_id,
        title=action.title,
        description=action.description,
        ticket_type=action.ticket_type,
        priority=action.priority,
        initial_status=action.initial_status,
        assigned_agent_id=action.assigned_agent_id,
        parent_ticket_id=action.parent_ticket_id,
        blocked_by_ticket_ids=action.blocked_by_ticket_ids,
        tags=action.tags,
        related_task_ids=action.related_task_ids,
    )
    return _obs(result)


@_with_service
def exec_update_ticket(session, action: UpdateTicketAction) -> GenericObservation:
    svc = TicketService(session)
    result = svc.update_ticket(
        ticket_id=action.ticket_id,
        agent_id=action.agent_id,
        updates=action.updates,
        update_comment=action.update_comment,
    )
    return _obs(result)


@_with_service
def exec_change_status(session, action: ChangeStatusAction) -> GenericObservation:
    svc = TicketService(session)
    result = svc.change_status(
        ticket_id=action.ticket_id,
        agent_id=action.agent_id,
        new_status=action.new_status,
        comment=action.comment,
        commit_sha=action.commit_sha,
    )
    return _obs(result)


@_with_service
def exec_add_comment(session, action: AddCommentAction) -> GenericObservation:
    svc = TicketService(session)
    result = svc.add_comment(
        ticket_id=action.ticket_id,
        agent_id=action.agent_id,
        comment_text=action.comment_text,
        comment_type=action.comment_type,
        mentions=action.mentions,
        attachments=action.attachments,
    )
    return _obs(result)


@_with_service
def exec_search_tickets(session, action: SearchTicketsAction) -> GenericObservation:
    svc = TicketSearchService(session)
    if action.search_type == "semantic":
        data = svc.semantic_search(query_text=action.query, workflow_id=action.workflow_id, limit=action.limit, filters=action.filters)
        result = {"success": True, "mode": "semantic", **data}
    elif action.search_type == "keyword":
        data = svc.search_by_keywords(keywords=action.query, workflow_id=action.workflow_id, filters=action.filters)
        result = {"success": True, "mode": "keyword", **data}
    else:
        data = svc.hybrid_search(query_text=action.query, workflow_id=action.workflow_id, limit=action.limit, filters=action.filters, include_comments=action.include_comments)
        result = {"success": True, "mode": "hybrid", **data}
    return _obs(result)


@_with_service
def exec_get_tickets(session, action: GetTicketsAction) -> GenericObservation:
    svc = TicketService(session)
    filters = {
        k: v
        for k, v in {
            "status": action.status,
            "ticket_type": action.ticket_type,
            "priority": action.priority,
            "assigned_agent_id": action.assigned_agent_id,
        }.items()
        if v is not None
    }
    result = svc.get_tickets(
        workflow_id=action.workflow_id,
        filters=filters,
        limit=action.limit,
        offset=action.offset,
        include_completed=action.include_completed,
        sort_by=action.sort_by,
        sort_order=action.sort_order,
    )
    return _obs(result)


@_with_service
def exec_get_ticket(session, action: GetTicketAction) -> GenericObservation:
    svc = TicketService(session)
    result = svc.get_ticket(ticket_id=action.ticket_id)
    return _obs(result)


@_with_service
def exec_resolve_ticket(session, action: ResolveTicketAction) -> GenericObservation:
    svc = TicketService(session)
    result = svc.resolve_ticket(
        ticket_id=action.ticket_id,
        agent_id=action.agent_id,
        resolution_comment=action.resolution_comment,
        commit_sha=action.commit_sha,
    )
    return _obs(result)


@_with_service
def exec_link_commit(session, action: LinkCommitAction) -> GenericObservation:
    svc = TicketService(session)
    result = svc.link_commit(
        ticket_id=action.ticket_id,
        agent_id=action.agent_id,
        commit_sha=action.commit_sha,
        commit_message=action.commit_message,
    )
    return _obs(result)


# ---------- Toolset Registration ----------

def register_hephaestus_mcp_tools() -> None:
    tools: list[ToolDefinition] = [
        ToolDefinition(
            name="mcp__hephaestus__create_ticket",
            description="Create a new ticket in the workflow tracking system.",
            action_type=CreateTicketAction,
            observation_type=GenericObservation,
            executor=exec_create_ticket,
        ),
        ToolDefinition(
            name="mcp__hephaestus__update_ticket",
            description="Update fields of an existing ticket.",
            action_type=UpdateTicketAction,
            observation_type=GenericObservation,
            executor=exec_update_ticket,
        ),
        ToolDefinition(
            name="mcp__hephaestus__change_ticket_status",
            description="Change ticket status with optional commit linkage.",
            action_type=ChangeStatusAction,
            observation_type=GenericObservation,
            executor=exec_change_status,
        ),
        ToolDefinition(
            name="mcp__hephaestus__add_ticket_comment",
            description="Add a comment to a ticket.",
            action_type=AddCommentAction,
            observation_type=GenericObservation,
            executor=exec_add_comment,
        ),
        ToolDefinition(
            name="mcp__hephaestus__search_tickets",
            description="Search tickets (hybrid by default: semantic + keyword).",
            action_type=SearchTicketsAction,
            observation_type=GenericObservation,
            executor=exec_search_tickets,
        ),
        ToolDefinition(
            name="mcp__hephaestus__get_tickets",
            description="List tickets with filters and pagination.",
            action_type=GetTicketsAction,
            observation_type=GenericObservation,
            executor=exec_get_tickets,
        ),
        ToolDefinition(
            name="mcp__hephaestus__get_ticket",
            description="Get details of a single ticket.",
            action_type=GetTicketAction,
            observation_type=GenericObservation,
            executor=exec_get_ticket,
        ),
        ToolDefinition(
            name="mcp__hephaestus__link_commit",
            description="Link a git commit to a ticket.",
            action_type=LinkCommitAction,
            observation_type=GenericObservation,
            executor=exec_link_commit,
        ),
        ToolDefinition(
            name="mcp__hephaestus__resolve_ticket",
            description="Resolve a ticket and automatically unblock dependents.",
            action_type=ResolveTicketAction,
            observation_type=GenericObservation,
            executor=exec_resolve_ticket,
        ),
    ]

    def _factory(conv_state) -> list[ToolDefinition]:  # noqa: ARG001
        return tools

    register_tool("HephaestusTicketTools", _factory)


