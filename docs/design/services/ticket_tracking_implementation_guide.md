# Hephaestus Ticket Tracking — Implementation Guide (PostgreSQL + SQLAlchemy)

**Created**: 2025-11-20
**Status**: Active
**Purpose**: Provides step‑by‑step instructions, module layout, and service interfaces for implementing the Ticket Tracking System with PostgreSQL and SQLAlchemy.
**Related**: docs/design/ticket_tracking_postgres.md

---


Version: 1.0  
Status: Ready for Implementation  
Date: 2025-11-16

## Overview
This guide details the concrete steps, module boundaries, and interfaces to implement the Ticket Tracking System using PostgreSQL (psycopg3) and SQLAlchemy. It complements the design in `docs/design/ticket_tracking_postgres.md`.

## Modules & Files
- `senior_sandbox/ticketing/db.py`
  - Pydantic DB settings
  - SQLAlchemy engine/session factory
  - Helper `get_session()` context manager
- `senior_sandbox/ticketing/models.py`
  - Declarative SQLAlchemy models for all tables
- `senior_sandbox/ticketing/services/ticket_service.py`
  - CRUD, status transitions, blockers, comments linkages
- `senior_sandbox/ticketing/services/ticket_history_service.py`
  - History recording & timeline
- `senior_sandbox/ticketing/services/ticket_search_service.py`
  - Hybrid search abstraction (semantic via Qdrant; keyword via SQL)
- `senior_sandbox/ticketing/scripts/init_db.py`
  - Create all tables & recommended indexes

Optional (future):
- Alembic migrations under `migrations/` with autogenerate.

## Environment Variables (loaded via pydantic-settings)
- DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SSLMODE
- QDRANT_URL, QDRANT_API_KEY (optional)
- EMBEDDING_MODEL, EMBEDDING_DIM, EMBEDDING_PROVIDER (optional)

## Database URL
`postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={DB_SSLMODE}`

## Key Service Interfaces
```python
class TicketService:
    async def create_ticket(self, *, workflow_id: str, agent_id: str, title: str, description: str,
                            ticket_type: str, priority: str, initial_status: str | None,
                            assigned_agent_id: str | None, parent_ticket_id: str | None,
                            blocked_by_ticket_ids: list[str], tags: list[str], related_task_ids: list[str]) -> dict:
        ...

    async def update_ticket(self, *, ticket_id: str, agent_id: str, updates: dict, update_comment: str | None) -> dict:
        ...

    async def change_status(self, *, ticket_id: str, agent_id: str, new_status: str,
                            comment: str, commit_sha: str | None) -> dict:
        ...

    async def add_comment(self, *, ticket_id: str, agent_id: str, comment_text: str,
                          comment_type: str, mentions: list[str], attachments: list[str]) -> dict:
        ...

    async def get_ticket(self, *, ticket_id: str) -> dict:
        ...

    async def get_tickets(self, *, workflow_id: str, filters: dict | None, limit: int, offset: int,
                          include_completed: bool, sort_by: str, sort_order: str) -> dict:
        ...

    async def assign_ticket(self, *, ticket_id: str, agent_id: str) -> dict:
        ...

    async def link_commit(self, *, ticket_id: str, agent_id: str, commit_sha: str,
                          commit_message: str | None) -> dict:
        ...

    async def resolve_ticket(self, *, ticket_id: str, agent_id: str, resolution_comment: str,
                             commit_sha: str | None) -> dict:
        ...
```

```python
class TicketHistoryService:
    async def record_change(self, *, ticket_id: str, agent_id: str, change_type: str,
                            old_value: str | None, new_value: str | None, metadata: dict | None,
                            field_name: str | None, change_description: str | None) -> None:
        ...

    async def record_status_transition(self, *, ticket_id: str, agent_id: str,
                                       from_status: str, to_status: str) -> None:
        ...

    async def link_commit(self, *, ticket_id: str, agent_id: str, commit_sha: str, message: str) -> None:
        ...

    async def get_ticket_history(self, *, ticket_id: str) -> list[dict]:
        ...
```

```python
class TicketSearchService:
    async def semantic_search(self, *, query_text: str, workflow_id: str, limit: int, filters: dict | None) -> dict:
        ...

    async def search_by_keywords(self, *, keywords: str, workflow_id: str, filters: dict | None) -> dict:
        ...

    async def hybrid_search(self, *, query_text: str, workflow_id: str, limit: int,
                            filters: dict | None, include_comments: bool) -> dict:
        ...

    async def index_ticket(self, *, ticket_id: str) -> None:
        ...

    async def reindex_ticket(self, *, ticket_id: str) -> None:
        ...
```

## Endpoint Mapping (MCP or HTTP)
- POST `/tickets/create` → `TicketService.create_ticket`
- POST `/tickets/update` → `TicketService.update_ticket`
- POST `/tickets/change-status` → `TicketService.change_status`
- POST `/tickets/comment` → `TicketService.add_comment`
- POST `/tickets/search` → `TicketSearchService.hybrid_search` (default)
- GET `/tickets/get` → `TicketService.get_tickets`
- GET `/tickets/{ticket_id}` → `TicketService.get_ticket` (+ history/comments in aggregator adapter)
- GET `/tickets/board-config/{workflow_id}` → board config loader (simple DAO)
- POST `/tickets/link-commit` → `TicketService.link_commit`
- GET `/tickets/commit-diff/{commit_sha}` → Git adapter (shell + parser) — future file
- POST `/tickets/resolve` → `TicketService.resolve_ticket`

## Data Flow Highlights
1. Create ticket:
   - Validate board config, status, ticket type.
   - Insert ticket, record history, enqueue embedding index (async).
2. Update ticket:
   - Diff fields, apply changes, record per-field history.
   - If title/description changed, reindex.
3. Change status:
   - Enforce blockers, update timing (started/completed), history & comment.
4. Resolve:
   - Mark resolved, link commit if provided, cascade unblock dependents.
5. Search:
   - Semantic (Qdrant) 70% + keyword 30% → RRF/rerank; remove duplicates.

## Indices & Performance
- Add btree indexes listed in the design doc.
- Future: GIN on jsonb where useful (tags).
- Optional materialized view for FTS projection.

## Testing Notes
- Use a dedicated test DB.
- Seed board_config, create few tickets, cover transitions and blockers.


