from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from omoi_os.utils.datetime import utc_now

from sqlalchemy import select
from sqlalchemy.orm import Session

from omoi_os.ticketing.models import BoardConfig, Ticket, TicketComment, TicketCommit, TicketHistory


def _ticket_id() -> str:
    return f"ticket-{uuid4()}"


def _comment_id() -> str:
    return f"comment-{uuid4()}"


def _commit_id() -> str:
    return f"tc-{uuid4()}"


class TicketService:
    def __init__(self, session: Session):
        self.session = session

    # NOTE: These methods are synchronous using a DB-bound Session. If an async engine is introduced,
    # convert these to async and use AsyncSession accordingly.

    def create_ticket(
        self,
        *,
        workflow_id: str,
        agent_id: str,
        title: str,
        description: str,
        ticket_type: str,
        priority: str,
        initial_status: Optional[str],
        assigned_agent_id: Optional[str],
        parent_ticket_id: Optional[str],
        blocked_by_ticket_ids: list[str] | None,
        tags: list[str] | None,
        related_task_ids: list[str] | None,
    ) -> dict[str, Any]:
        # Validate board config / status / type
        board_cfg = self.session.scalar(select(BoardConfig).where(BoardConfig.workflow_id == workflow_id))
        if not board_cfg:
            raise ValueError("Board configuration not found for workflow")
        status = initial_status or board_cfg.initial_status

        ticket = Ticket(
            id=_ticket_id(),
            workflow_id=workflow_id,
            created_by_agent_id=agent_id,
            assigned_agent_id=assigned_agent_id,
            title=title,
            description=description,
            ticket_type=ticket_type,
            priority=priority,
            status=status,
            parent_ticket_id=parent_ticket_id,
            related_task_ids={"ids": related_task_ids or []},
            related_ticket_ids=None,
            tags={"values": tags or []},
            blocked_by_ticket_ids={"ids": blocked_by_ticket_ids or []} if blocked_by_ticket_ids else None,
            created_at=utc_now(),
            updated_at=utc_now(),
            is_resolved=False,
        )
        self.session.add(ticket)
        self.session.add(
            TicketHistory(
                ticket_id=ticket.id,
                agent_id=agent_id,
                change_type="created",
                field_name=None,
                old_value=None,
                new_value=None,
                change_description="Ticket created",
                metadata=None,
                changed_at=utc_now(),
            )
        )
        return {"success": True, "ticket_id": ticket.id, "status": ticket.status}

    def update_ticket(
        self,
        *,
        ticket_id: str,
        agent_id: str,
        updates: dict[str, Any],
        update_comment: Optional[str],
    ) -> dict[str, Any]:
        ticket = self.session.get(Ticket, ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        fields_updated: list[str] = []
        allowed = {"title", "description", "priority", "assigned_agent_id", "ticket_type", "tags", "blocked_by_ticket_ids"}
        for k, v in updates.items():
            if k in allowed:
                old = getattr(ticket, k)
                setattr(ticket, k, v if k not in {"tags", "blocked_by_ticket_ids"} else (v or None))
                fields_updated.append(k)
                self.session.add(
                    TicketHistory(
                        ticket_id=ticket.id,
                        agent_id=agent_id,
                        change_type="field_updated",
                        field_name=k,
                        old_value=str(old) if old is not None else None,
                        new_value=str(v) if v is not None else None,
                        change_description=f"Updated {k}",
                        metadata=None,
                        changed_at=utc_now(),
                    )
                )
        ticket.updated_at = utc_now()
        if update_comment:
            self.add_comment(ticket_id=ticket.id, agent_id=agent_id, comment_text=update_comment, comment_type="general", mentions=[], attachments=[])
        return {"success": True, "ticket_id": ticket.id, "fields_updated": fields_updated}

    def change_status(
        self,
        *,
        ticket_id: str,
        agent_id: str,
        new_status: str,
        comment: str,
        commit_sha: Optional[str],
    ) -> dict[str, Any]:
        ticket = self.session.get(Ticket, ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        # Blocked check
        blocked_ids = (ticket.blocked_by_ticket_ids or {}).get("ids", [])
        if blocked_ids:
            return {"success": False, "ticket_id": ticket.id, "blocked": True, "blocking_ticket_ids": list(blocked_ids)}

        old_status = ticket.status
        ticket.status = new_status
        now = utc_now()
        ticket.updated_at = now
        if old_status != new_status and ticket.started_at is None:
            ticket.started_at = now
        if new_status.lower() in {"done", "complete", "completed"} and ticket.completed_at is None:
            ticket.completed_at = now

        self.session.add(
            TicketHistory(
                ticket_id=ticket.id,
                agent_id=agent_id,
                change_type="status_changed",
                field_name="status",
                old_value=old_status,
                new_value=new_status,
                change_description="Status transition",
                metadata=None,
                changed_at=now,
            )
        )
        self.add_comment(ticket_id=ticket.id, agent_id=agent_id, comment_text=comment, comment_type="status_change", mentions=[], attachments=[])
        if commit_sha:
            self.link_commit(ticket_id=ticket.id, agent_id=agent_id, commit_sha=commit_sha, commit_message=None)
        return {"success": True, "ticket_id": ticket.id, "old_status": old_status, "new_status": new_status}

    def add_comment(
        self,
        *,
        ticket_id: str,
        agent_id: str,
        comment_text: str,
        comment_type: Optional[str],
        mentions: list[str],
        attachments: list[str],
    ) -> dict[str, Any]:
        ticket = self.session.get(Ticket, ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        now = utc_now()
        comment = TicketComment(
            id=_comment_id(),
            ticket_id=ticket.id,
            agent_id=agent_id,
            comment_text=comment_text,
            comment_type=comment_type or "general",
            mentions={"ids": mentions} if mentions else None,
            attachments={"paths": attachments} if attachments else None,
            created_at=now,
            updated_at=now,
            is_edited=False,
        )
        self.session.add(comment)
        self.session.add(
            TicketHistory(
                ticket_id=ticket.id,
                agent_id=agent_id,
                change_type="commented",
                field_name=None,
                old_value=None,
                new_value=None,
                change_description="Comment added",
                metadata=None,
                changed_at=utc_now(),
            )
        )
        return {"success": True, "comment_id": comment.id, "ticket_id": ticket.id}

    def get_ticket(self, *, ticket_id: str) -> dict[str, Any]:
        ticket = self.session.get(Ticket, ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        return {"success": True, "ticket": {"id": ticket.id, "title": ticket.title, "status": ticket.status, "priority": ticket.priority}}

    def get_tickets(
        self,
        *,
        workflow_id: str,
        filters: Optional[dict],
        limit: int,
        offset: int,
        include_completed: bool,
        sort_by: str,
        sort_order: str,
    ) -> dict[str, Any]:
        stmt = select(Ticket).where(Ticket.workflow_id == workflow_id)
        if not include_completed:
            stmt = stmt.where(Ticket.completed_at.is_(None))
        if filters:
            if status := filters.get("status"):
                stmt = stmt.where(Ticket.status == status)
            if ticket_type := filters.get("ticket_type"):
                stmt = stmt.where(Ticket.ticket_type == ticket_type)
            if priority := filters.get("priority"):
                stmt = stmt.where(Ticket.priority == priority)
            if assigned := filters.get("assigned_agent_id"):
                stmt = stmt.where(Ticket.assigned_agent_id == assigned)
        # Sorting
        sortable = {"created_at": Ticket.created_at, "updated_at": Ticket.updated_at, "priority": Ticket.priority, "status": Ticket.status}
        col = sortable.get(sort_by, Ticket.created_at)
        if sort_order.lower() == "asc":
            stmt = stmt.order_by(col.asc())
        else:
            stmt = stmt.order_by(col.desc())
        stmt = stmt.limit(limit).offset(offset)

        rows = list(self.session.scalars(stmt))
        data = [
            {
                "ticket_id": t.id,
                "workflow_id": t.workflow_id,
                "title": t.title,
                "description": t.description,
                "ticket_type": t.ticket_type,
                "priority": t.priority,
                "status": t.status,
                "created_by_agent_id": t.created_by_agent_id,
                "assigned_agent_id": t.assigned_agent_id,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "tags": (t.tags or {}).get("values", []),
                "is_blocked": bool((t.blocked_by_ticket_ids or {}).get("ids")),
                "blocked_by_ticket_ids": (t.blocked_by_ticket_ids or {}).get("ids", []),
            }
            for t in rows
        ]
        return {"success": True, "tickets": data, "total_count": len(data), "has_more": len(data) == limit}

    def link_commit(self, *, ticket_id: str, agent_id: str, commit_sha: str, commit_message: Optional[str]) -> dict[str, Any]:
        ticket = self.session.get(Ticket, ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        commit = TicketCommit(
            id=_commit_id(),
            ticket_id=ticket.id,
            agent_id=agent_id,
            commit_sha=commit_sha,
            commit_message=commit_message or "",
            commit_timestamp=utc_now(),
        )
        self.session.add(commit)
        self.session.add(
            TicketHistory(
                ticket_id=ticket.id,
                agent_id=agent_id,
                change_type="commit_linked",
                field_name=None,
                old_value=None,
                new_value=commit_sha,
                change_description="Commit linked",
                metadata=None,
                changed_at=utc_now(),
            )
        )
        return {"success": True, "ticket_id": ticket.id, "commit_sha": commit_sha}

    def resolve_ticket(self, *, ticket_id: str, agent_id: str, resolution_comment: str, commit_sha: Optional[str]) -> dict[str, Any]:
        ticket = self.session.get(Ticket, ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        now = utc_now()
        ticket.is_resolved = True
        ticket.resolved_at = now
        if commit_sha:
            self.link_commit(ticket_id=ticket.id, agent_id=agent_id, commit_sha=commit_sha, commit_message=None)
        self.add_comment(ticket_id=ticket.id, agent_id=agent_id, comment_text=resolution_comment, comment_type="resolution", mentions=[], attachments=[])

        # Unblock dependents (remove this ticket from their blockers)
        # NOTE: For brevity, this scans tickets in the same workflow. In production, optimize with proper queries.
        stmt = select(Ticket).where(Ticket.workflow_id == ticket.workflow_id)
        dependents = list(self.session.scalars(stmt))
        unblocked: list[str] = []
        for dep in dependents:
            blockers = (dep.blocked_by_ticket_ids or {}).get("ids", [])
            if ticket.id in blockers:
                blockers = [b for b in blockers if b != ticket.id]
                dep.blocked_by_ticket_ids = {"ids": blockers} if blockers else None
                dep.updated_at = now
                unblocked.append(dep.id)
                self.session.add(
                    TicketHistory(
                        ticket_id=dep.id,
                        agent_id=agent_id,
                        change_type="unblocked",
                        field_name=None,
                        old_value=None,
                        new_value=ticket.id,
                        change_description=f"Unblocked - {ticket.id} was resolved",
                        metadata=None,
                        changed_at=now,
                    )
                )
        return {"success": True, "ticket_id": ticket.id, "unblocked_tickets": unblocked}


