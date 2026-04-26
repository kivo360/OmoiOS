"""Add client_metadata JSONB column to tasks for spec §18 §5 opaque metadata.

Spec §18 §5 (the ReactGrab pattern) says clients must be able to attach
arbitrary nested JSON under `metadata` on `sessions.create()`, and the
SDK / backend must round-trip it byte-equally — no schema, no
transformation, no silent drops. The Pydantic SessionCreate model already
accepts `metadata`, but the Task row had no column to persist it, so it
was being discarded silently. Caught by the smoke phase
`session_metadata_opacity`.

Column name is `client_metadata` because SQLAlchemy reserves `metadata`
on the Declarative base — using it would crash model import. See
`docs/rules/sqlalchemy-reserved-keywords.md`.

The API surface (request body and response key) keeps the spec name
`metadata`; the rename is internal only.

Revision ID: 073_add_client_metadata_to_tasks
Revises: a531fd3140dc
Create Date: 2026-04-26

Note: chains off the `a531fd3140dc` merge (heads 069+072+egress) rather
than 072 directly, because 072 was already absorbed into that merge —
chaining off 072 would re-introduce a sibling head and break
`alembic upgrade head` on Railway.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "073_add_client_metadata_to_tasks"
down_revision: Union[str, None] = "a531fd3140dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    if table not in inspector.get_table_names():
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "tasks", "client_metadata"):
        op.add_column(
            "tasks",
            sa.Column(
                "client_metadata",
                postgresql.JSONB,
                nullable=True,
                comment=(
                    "Opaque client-supplied metadata from sessions.create() "
                    "metadata field (spec §18 §5). Round-tripped exactly; "
                    "never transformed by the platform."
                ),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_column(inspector, "tasks", "client_metadata"):
        op.drop_column("tasks", "client_metadata")
