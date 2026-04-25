"""Add session event envelope columns + session_acls + session_forks tables.

Supports the spec §03 event envelope (monotonic `seq` per session, `actor`
attribution) and the spec §07 multiplayer ACL model (owner/editor/viewer grants
per session). Also introduces `session_forks` so a forked session can trace
back to its parent at a specific event seq (spec §03 POST /fork).

The new columns on `events` are nullable — historical rows keep `seq=NULL`
intentionally. The `SessionEventEnvelope` service populates both fields for
every emit going forward; SSE replay code synthesizes a reading order via
ORDER BY timestamp for rows where `seq IS NULL`.

A composite index `(entity_id, seq)` supports `Last-Event-ID` resume: the
SSE handler does `SELECT ... WHERE entity_id = :task_id AND seq > :last LIMIT
N ORDER BY seq`.

NOTE on migration numbering: 068 (environment_versions.credentials) and 069
(sandbox_sessions) are owned by the agent-platform-gaps.md plan. This plan
reserves 070 to avoid collision. The `events.seq` column here is the session
envelope sequence — distinct from the sandbox-session bearer tokens in 069.

Revision ID: 070_session_envelope_and_acls
Revises: 069_add_sandbox_sessions
Create Date: 2026-04-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "070_session_envelope_and_acls"
# Chain on 068 because that's head-of-branch right now. 069 (sandbox_sessions,
# owned by agent-platform-gaps.md) is still in flight. Whichever plan lands
# second must rebase its down_revision or add a merge migration — see
# `alembic merge` if both heads coexist briefly.
down_revision: Union[str, None] = "068_add_environment_credentials_alias_map"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    if table not in inspector.get_table_names():
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    """Add envelope columns to events, create session_acls and session_forks."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. events.seq and events.actor — both nullable, no backfill.
    if not _table_has_column(inspector, "events", "seq"):
        op.add_column(
            "events",
            sa.Column(
                "seq",
                sa.BigInteger(),
                nullable=True,
                comment="Monotonic sequence per session (entity_id). NULL for legacy rows.",
            ),
        )

    if not _table_has_column(inspector, "events", "actor"):
        op.add_column(
            "events",
            sa.Column(
                "actor",
                sa.String(100),
                nullable=True,
                comment="Event originator: 'agent', 'user:<uuid>', or 'system'.",
            ),
        )

    # 2. Composite index for SSE Last-Event-ID resume queries.
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("events")}
    if "ix_events_entity_seq" not in existing_indexes:
        op.create_index(
            "ix_events_entity_seq",
            "events",
            ["entity_id", "seq"],
            # seq can be NULL for historical rows; skip them in the index
            # to keep the resume query plan tight.
            postgresql_where=sa.text("seq IS NOT NULL"),
        )

    # 3. session_acls — multiplayer grants per session.
    if "session_acls" not in inspector.get_table_names():
        op.create_table(
            "session_acls",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            # tasks.id is a stringified UUID (see models/task.py) — match that
            # type to preserve referential integrity without a column-type migration.
            sa.Column("task_id", sa.String(), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("role", sa.String(10), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["task_id"],
                ["tasks.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("task_id", "user_id", name="uq_session_acls_task_user"),
            sa.CheckConstraint(
                "role IN ('owner', 'editor', 'viewer')",
                name="ck_session_acls_role",
            ),
            comment="Spec §07 multiplayer ACL — who can read/edit/own a session",
        )
        op.create_index(
            "ix_session_acls_task",
            "session_acls",
            ["task_id"],
        )
        op.create_index(
            "ix_session_acls_user",
            "session_acls",
            ["user_id"],
        )

    # 4. session_forks — fork lineage for POST /sessions/{id}/fork.
    if "session_forks" not in inspector.get_table_names():
        op.create_table(
            "session_forks",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("parent_task_id", sa.String(), nullable=False),
            sa.Column("child_task_id", sa.String(), nullable=False),
            sa.Column(
                "from_seq",
                sa.BigInteger(),
                nullable=False,
                comment="Parent event seq the fork branches from",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["parent_task_id"],
                ["tasks.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["child_task_id"],
                ["tasks.id"],
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("child_task_id", name="uq_session_forks_child"),
            comment="Spec §03 fork lineage — child sessions branched from a parent seq",
        )
        op.create_index(
            "ix_session_forks_parent",
            "session_forks",
            ["parent_task_id"],
        )


def downgrade() -> None:
    """Reverse upgrade: drop tables, then indexes, then columns."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "session_forks" in inspector.get_table_names():
        op.drop_index("ix_session_forks_parent", table_name="session_forks")
        op.drop_table("session_forks")

    if "session_acls" in inspector.get_table_names():
        op.drop_index("ix_session_acls_user", table_name="session_acls")
        op.drop_index("ix_session_acls_task", table_name="session_acls")
        op.drop_table("session_acls")

    # Re-inspect: events table remains, check current state.
    inspector = sa.inspect(bind)
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("events")}
    if "ix_events_entity_seq" in existing_indexes:
        op.drop_index("ix_events_entity_seq", table_name="events")

    if _table_has_column(inspector, "events", "actor"):
        op.drop_column("events", "actor")
    if _table_has_column(inspector, "events", "seq"):
        op.drop_column("events", "seq")
