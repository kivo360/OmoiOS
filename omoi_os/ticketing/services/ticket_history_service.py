from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from omoi_os.ticketing.models import TicketHistory


class TicketHistoryService:
    def __init__(self, session: Session):
        self.session = session

    def record_change(
        self,
        *,
        ticket_id: str,
        agent_id: str,
        change_type: str,
        old_value: Optional[str],
        new_value: Optional[str],
        metadata: Optional[dict[str, Any]],
        field_name: Optional[str],
        change_description: Optional[str],
    ) -> None:
        self.session.add(
            TicketHistory(
                ticket_id=ticket_id,
                agent_id=agent_id,
                change_type=change_type,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                change_description=change_description,
                metadata=metadata,
                changed_at=datetime.utcnow(),
            )
        )

    def record_status_transition(self, *, ticket_id: str, agent_id: str, from_status: str, to_status: str) -> None:
        self.record_change(
            ticket_id=ticket_id,
            agent_id=agent_id,
            change_type="status_changed",
            old_value=from_status,
            new_value=to_status,
            metadata=None,
            field_name="status",
            change_description="Status transition",
        )

    def link_commit(self, *, ticket_id: str, agent_id: str, commit_sha: str, message: str) -> None:
        self.record_change(
            ticket_id=ticket_id,
            agent_id=agent_id,
            change_type="commit_linked",
            old_value=None,
            new_value=commit_sha,
            metadata={"message": message},
            field_name=None,
            change_description="Commit linked",
        )

    def get_ticket_history(self, *, ticket_id: str) -> list[dict]:
        stmt = select(TicketHistory).where(TicketHistory.ticket_id == ticket_id).order_by(TicketHistory.changed_at.asc())
        rows = list(self.session.scalars(stmt))
        return [
            {
                "change_type": r.change_type,
                "field_name": r.field_name,
                "old_value": r.old_value,
                "new_value": r.new_value,
                "change_description": r.change_description,
                "changed_at": r.changed_at.isoformat() if r.changed_at else None,
                "agent_id": r.agent_id,
            }
            for r in rows
        ]


