from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from omoi_os.ticketing.models import Ticket


class TicketSearchService:
    def __init__(self, session: Session):
        self.session = session

    # Placeholder for semantic search integration with Qdrant.
    def semantic_search(
        self, *, query_text: str, workflow_id: str, limit: int, filters: Optional[dict]
    ) -> dict[str, Any]:
        # TODO: integrate with Qdrant client; return shape unified with keyword results.
        return {"results": [], "total_found": 0}

    # Basic keyword search using ILIKE across title/description and (optionally) recent comments.
    def search_by_keywords(
        self, *, keywords: str, workflow_id: str, filters: Optional[dict]
    ) -> dict[str, Any]:
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
                "matched_in": [
                    (
                        "title"
                        if keywords.lower() in (t.title or "").lower()
                        else "description"
                    )
                ],
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
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ) -> dict[str, Any]:
        """
        Hybrid search combining semantic and keyword search using RRF (REQ-MEM-SEARCH-001).

        Args:
            query_text: Search query text
            workflow_id: Workflow ID to filter by
            limit: Maximum number of results to return
            filters: Optional filters to apply
            include_comments: Whether to include comments in search
            semantic_weight: Weight for semantic search in RRF (default: 0.6)
            keyword_weight: Weight for keyword search in RRF (default: 0.4)

        Returns:
            Dictionary with search results merged using RRF algorithm
        """
        # Run both searches with expanded limit for better RRF results
        sem = self.semantic_search(
            query_text=query_text,
            workflow_id=workflow_id,
            limit=limit * 2,
            filters=filters,
        )
        kw = self.search_by_keywords(
            keywords=query_text, workflow_id=workflow_id, filters=filters
        )

        # Merge using Reciprocal Rank Fusion
        merged_results = self._merge_results_rrf(
            sem.get("results", []),
            kw.get("results", []),
            semantic_weight,
            keyword_weight,
        )

        return {
            "success": True,
            "query": query_text,
            "results": merged_results[:limit],
            "total_found": len(merged_results),
        }

    def _merge_results_rrf(
        self,
        semantic_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        semantic_weight: float,
        keyword_weight: float,
    ) -> list[dict[str, Any]]:
        """
        Merge results using Reciprocal Rank Fusion (RRF) algorithm.

        Formula:
        score = semantic_weight * (1 / (k + semantic_rank)) +
                keyword_weight * (1 / (k + keyword_rank))

        Where k = 60 (typical RRF constant)
        """
        k = 60  # RRF constant

        # Create rank maps (1-indexed for RRF)
        semantic_ranks = {
            r.get("ticket_id"): idx + 1
            for idx, r in enumerate(semantic_results)
            if r.get("ticket_id")
        }
        keyword_ranks = {
            r.get("ticket_id"): idx + 1
            for idx, r in enumerate(keyword_results)
            if r.get("ticket_id")
        }

        # Get all unique ticket IDs
        all_ids = set(semantic_ranks.keys()) | set(keyword_ranks.keys())

        # Create result maps for quick lookup
        semantic_map = {
            r.get("ticket_id"): r for r in semantic_results if r.get("ticket_id")
        }
        keyword_map = {
            r.get("ticket_id"): r for r in keyword_results if r.get("ticket_id")
        }

        # Calculate combined scores
        combined_results = []
        for ticket_id in all_ids:
            sem_rank = semantic_ranks.get(ticket_id, len(semantic_results) + 10)
            kw_rank = keyword_ranks.get(ticket_id, len(keyword_results) + 10)

            # RRF score calculation
            rrf_score = semantic_weight * (1.0 / (k + sem_rank)) + keyword_weight * (
                1.0 / (k + kw_rank)
            )

            # Get the result object (prefer semantic as it has more info)
            result = semantic_map.get(ticket_id) or keyword_map.get(ticket_id)
            if not result:
                continue

            # Create merged result with RRF score
            merged_result = result.copy()
            merged_result["relevance_score"] = rrf_score
            merged_result["semantic_score"] = (
                result.get("relevance_score") if ticket_id in semantic_map else None
            )
            merged_result["keyword_score"] = (
                result.get("relevance_score") if ticket_id in keyword_map else None
            )
            combined_results.append(merged_result)

        # Sort by combined RRF score descending
        combined_results.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)

        return combined_results

    def index_ticket(self, *, ticket_id: str) -> None:
        # TODO: push embedding to Qdrant
        return None

    def reindex_ticket(self, *, ticket_id: str) -> None:
        # TODO: re-generate and upsert embedding
        return None
