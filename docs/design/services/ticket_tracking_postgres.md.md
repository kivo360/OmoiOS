# Hephaestus Ticket Tracking System — PostgreSQL Design (SQLAlchemy)

**Created**: 2025-11-20
**Status**: Review
**Purpose**: Design specification for the PostgreSQL implementation of the Hephaestus Ticket Tracking System using SQLAlchemy.
**Related**: docs/requirements/ticket_tracking.md, docs/design/services/ticket_tracking_sqlite.md, docs/architecture/db_choice_adr.md, docs/implementation/ticket_tracking_postgres_migration.md, docs/guide/ticket_tracking_search.md

---


Version: 1.0  
Status: Ready for Review  
Date: 2025-11-16

## Objectives
- Replace SQLite with PostgreSQL (psycopg3) while keeping SQLAlchemy ORM.
- Preserve the original feature set: Kanban board, tickets/comments/history/commits, blockers, hybrid search (semantic + keyword), MCP endpoints.
- Remain optional-by-default and fully configurable per workflow.

## Tech Choices
- Database: PostgreSQL 14+ (UTF-8, timezone-aware).
- Driver: psycopg (psycopg3).
- ORM: SQLAlchemy 2.x (Declarative with async engine optional in future).
- Migrations: Alembic (future-ready; initial script provided via `init_db.py`).
- JSON fields: `JSONB` for tags, relationships, and payloads.
- Time: `TIMESTAMP WITH TIME ZONE` for all timestamps.

## Entities (Tables)
- `tickets`
- `ticket_comments`
- `ticket_history`
- `ticket_commits`
- `board_configs`

### tickets
- id (PK, varchar: `ticket-{uuid}`)
- workflow_id (varchar, indexed)
- created_by_agent_id (varchar)
- assigned_agent_id (varchar, nullable)
- title (varchar(500))
- description (text)
- ticket_type (varchar(50))
- priority (varchar(20))
- status (varchar(50))
- created_at, updated_at, started_at, completed_at, resolved_at (timestamptz)
- parent_ticket_id (varchar, FK to tickets.id, nullable)
- related_task_ids (jsonb)
- related_ticket_ids (jsonb)
- tags (jsonb)
- embedding (jsonb) — cached embedding
- embedding_id (varchar) — Qdrant reference
- blocked_by_ticket_ids (jsonb)
- is_resolved (boolean)

Indexes:
- (workflow_id), (status), (assigned_agent_id), (ticket_type), (priority), (created_at), (is_resolved), (workflow_id, status)

### ticket_comments
- id (PK, varchar: `comment-{uuid}`)
- ticket_id (FK → tickets.id ON DELETE CASCADE)
- agent_id (varchar)
- comment_text (text)
- comment_type (varchar(50), default 'general')
- mentions (jsonb), attachments (jsonb)
- created_at (timestamptz), updated_at (timestamptz, nullable), is_edited (boolean)

Indexes:
- (ticket_id), (agent_id), (created_at)

### ticket_history
- id (PK, bigserial)
- ticket_id (FK → tickets.id ON DELETE CASCADE)
- agent_id (varchar)
- change_type (varchar(50))
- field_name (varchar(100), nullable)
- old_value (text), new_value (text)
- change_description (text)
- metadata (jsonb)
- changed_at (timestamptz)

Indexes:
- (ticket_id), (change_type), (changed_at)

### ticket_commits
- id (PK, varchar: `tc-{uuid}`)
- ticket_id (FK → tickets.id ON DELETE CASCADE)
- agent_id (varchar)
- commit_sha (varchar(64))
- commit_message (text)
- commit_timestamp (timestamptz)
- files_changed (int), insertions (int), deletions (int)
- files_list (jsonb)
- linked_at (timestamptz, default now())
- link_method (varchar(50), default 'manual')

Indexes:
- (ticket_id), (commit_sha), unique(ticket_id, commit_sha)

### board_configs
- id (PK, varchar: `board-{uuid}`)
- workflow_id (varchar, unique, indexed)
- name (varchar(200))
- columns (jsonb) — [{id, name, order, color}]
- ticket_types (jsonb)
- default_ticket_type (varchar(50), nullable)
- initial_status (varchar(50))
- settings (jsonb)
- created_at, updated_at (timestamptz)

## Status/Transitions
- No hardcoded status values. Enforced by board config. Transitions validated by service layer.

## Blocking Rules
- If `blocked_by_ticket_ids` is non-empty, prevent status changes (except permitted administrative operations). Resolution of a blocker cascades to unblock dependent tickets.

## Search Strategy
- Hybrid search remains: semantic (Qdrant) + keyword (SQL).
- For keyword search (PostgreSQL): use `to_tsvector`/`to_tsquery` on title/description/comments materialized projection (future optimization). Initial implementation: ILIKE filters with indexes where feasible; upgrade path documented.

## Observability
- All mutating operations recorded in `ticket_history`.
- Future: add triggers for updated_at and history capture via SQL or ORM events.

## Configuration
Environment variables (loaded via `pydantic-settings`):
- DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SSLMODE (optional)
- QDRANT_URL, QDRANT_API_KEY (optional)
- EMBEDDING_MODEL, EMBEDDING_DIM, EMBEDDING_PROVIDER (optional)

## Risks & Mitigations
- Large JSONB fields: keep payloads minimal; avoid storing large blobs.
- Search performance: start simple; later add GIN indexes and tsvector materialization.
- Migrations: Alembic planned; initial bootstrap via script.


