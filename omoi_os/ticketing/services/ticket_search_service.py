from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from omoi_os.ticketing.models import Ticket


class TicketSearchService:
    def __init__(self, session: Session):
        self.session = session

    # Placeholder for semantic search integration with Qdrant.
    def semantic_search(self, *, query_text: str, workflow_id: str, limit: int, filters: Optional[dict]) -> dict[str, Any]:
        # TODO: integrate with Qdrant client; return shape unified with keyword results.
        return {"results": [], "total_found": 0}

    # Basic keyword search using ILIKE across title/description and (optionally) recent comments.
    def search_by_keywords(self, *, keywords: str, workflow_id: str, filters: Optional[dict]) -> dict[str, Any]:
        stmt = select(Ticket).where(Ticket.workflow_id == workflow_id)
        kw = f"%{keywords}%"
        stmt = stmt.where(or_(Ticket.title.ilike(kw), Ticket.description.ilike(kw)))
        rows = list(self.session.scalars(stmt.limit(50)))
        results = [
            {
                "ticket_id": t.id,
                "title": t.title,
                "description": t.description[:280],
                "status": t.status,
                "priority": t.priority,
                "ticket_type": t.ticket_type,
                "relevance_score": 0.5,  # placeholder
                "matched_in": ["title" if keywords.lower() in (t.title or "").lower() else "description"],
                "preview": (t.description or "")[:200],
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "assigned_agent_id": t.assigned_agent_id,
            }
            for t in rows
        ]
        return {"results": results, "total_found": len(results)}

    def hybrid_search(
        self,
        *,
        query_text: str,
        workflow_id: str,
        limit: int = 10,
        filters: Optional[dict] = None,
        include_comments: bool = True,
    ) -> dict[str, Any]:
        sem = self.semantic_search(query_text=query_text, workflow_id=workflow_id, limit=limit, filters=filters)
        kw = self.search_by_keywords(keywords=query_text, workflow_id=workflow_id, filters=filters)
        # Simple merge (placeholder for RRF)
        merged: list[dict[str, Any]] = []
        merged.extend(sem.get("results", []))
        merged.extend(kw.get("results", []))
        # Deduplicate by ticket_id
        seen: set[str] = set()
        de_duped: list[dict[str, Any]] = []
        for r in merged:
            tid = r.get("ticket_id")
            if tid and tid not in seen:
                seen.add(tid)
                de_duped.append(r)
        return {"success": True, "query": query_text, "results": de_duped[:limit], "total_found": len(de_duped)}

    def index_ticket(self, *, ticket_id: str) -> None:
        # TODO: push embedding to Qdrant
        return None

    def reindex_ticket(self, *, ticket_id: str) -> None:
        # TODO: re-generate and upsert embedding
        return None


