"""Decouple sessions (tasks) from tickets.

Spec §03 models `POST /sessions` as `{workspace_id, environment_id, prompt,
share_with, webhook_subscription, metadata}` — with no ticket_id. The current
schema hard-couples every Task (= Session per spec §17 name-mapping) to a
ticket via `tasks.ticket_id NOT NULL`, which forces SDK callers to hand-seed
an org → project → ticket before they can even create a session.

This migration breaks that coupling without touching the workflow engine:

1. `tasks.ticket_id` becomes nullable — existing rows keep their ticket, new
   SDK-direct sessions insert with `ticket_id=NULL`.
2. Four new direct columns on `tasks` (`workspace_id`, `environment_version_id`,
   `created_by`, `github_repo`) give sessions first-class pointers at the
   spec §02 resources they actually need, so runtime code doesn't have to
   chase `ticket.project.*` relationships to figure out org, user, and repo.
3. `workspaces` gains `github_owner`, `github_repo`, `github_connected` (same
   shape as `projects`) so an SDK caller that provides `github_repo="foo/bar"`
   can be resolved to a workspace via a unique partial index, mirroring the
   auto-project pattern in `routes/tickets.py`.

No data backfill — legacy tasks with `ticket_id NOT NULL AND workspace_id
NULL` continue to work via the runtime fallback chain in `SessionSubject`.
The two new indexes are partial (WHERE col IS NOT NULL) so they only index
the SDK-direct rows, keeping the index small during the long tail of
legacy-shaped tasks.

Revision ID: 071_decouple_session_from_ticket
Revises: 070_session_envelope_and_acls
Create Date: 2026-04-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "071_decouple_session_from_ticket"
down_revision: Union[str, None] = "070_session_envelope_and_acls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    if table not in inspector.get_table_names():
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def _has_index(inspector: sa.Inspector, table: str, index_name: str) -> bool:
    if table not in inspector.get_table_names():
        return False
    return index_name in {ix["name"] for ix in inspector.get_indexes(table)}


def upgrade() -> None:
    """Additive changes only: nullable ticket_id, four direct columns on tasks,
    three github columns + unique partial index on workspaces."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Relax tasks.ticket_id from NOT NULL to NULL.
    #    existing FK (tickets.id, CASCADE) is preserved.
    op.alter_column(
        "tasks",
        "ticket_id",
        existing_type=sa.String(),
        nullable=True,
    )

    # 2. Four direct columns on tasks — the spec-aligned path.
    if not _table_has_column(inspector, "tasks", "workspace_id"):
        op.add_column(
            "tasks",
            sa.Column(
                "workspace_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(
                    "workspaces.id",
                    name="fk_tasks_workspace_id",
                    ondelete="SET NULL",
                ),
                nullable=True,
                comment="Spec §02 workspace this session belongs to. NULL for legacy ticket-driven tasks.",
            ),
        )

    if not _table_has_column(inspector, "tasks", "environment_version_id"):
        op.add_column(
            "tasks",
            sa.Column(
                "environment_version_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(
                    "environment_versions.id",
                    name="fk_tasks_environment_version_id",
                    ondelete="SET NULL",
                ),
                nullable=True,
                comment="Spec §05 environment version pinned at session create. Immutable once set.",
            ),
        )

    if not _table_has_column(inspector, "tasks", "created_by"):
        op.add_column(
            "tasks",
            sa.Column(
                "created_by",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey(
                    "users.id",
                    name="fk_tasks_created_by",
                    ondelete="SET NULL",
                ),
                nullable=True,
                comment="Direct creator — used for access control fallback and GitHub token lookup.",
            ),
        )

    if not _table_has_column(inspector, "tasks", "github_repo"):
        op.add_column(
            "tasks",
            sa.Column(
                "github_repo",
                sa.String(511),
                nullable=True,
                comment="Denormalized owner/repo string for SDK-direct sessions without a project.",
            ),
        )

    # 3. Partial indexes so the SDK-direct hot path stays tight, and legacy
    #    rows don't bloat either index.
    if not _has_index(inspector, "tasks", "ix_tasks_workspace_active"):
        op.create_index(
            "ix_tasks_workspace_active",
            "tasks",
            ["workspace_id", "status"],
            postgresql_where=sa.text("workspace_id IS NOT NULL"),
        )

    if not _has_index(inspector, "tasks", "ix_tasks_created_by"):
        op.create_index(
            "ix_tasks_created_by",
            "tasks",
            ["created_by"],
            postgresql_where=sa.text("created_by IS NOT NULL"),
        )

    # 4. Workspace gets the github binding columns — mirrors Project's shape
    #    so the SDK-direct create can auto-bind by (org_id, owner, repo).
    inspector = sa.inspect(bind)  # re-inspect after alterations above
    if not _table_has_column(inspector, "workspaces", "github_owner"):
        op.add_column(
            "workspaces",
            sa.Column("github_owner", sa.String(255), nullable=True),
        )

    if not _table_has_column(inspector, "workspaces", "github_repo"):
        op.add_column(
            "workspaces",
            sa.Column("github_repo", sa.String(255), nullable=True),
        )

    if not _table_has_column(inspector, "workspaces", "github_connected"):
        op.add_column(
            "workspaces",
            sa.Column(
                "github_connected",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    # 5. Unique partial index so `ensure_workspace_for_github_repo` can do an
    #    upsert keyed on (org_id, owner, repo) without racing.
    inspector = sa.inspect(bind)
    if not _has_index(inspector, "workspaces", "ux_workspaces_org_repo"):
        op.create_index(
            "ux_workspaces_org_repo",
            "workspaces",
            ["organization_id", "github_owner", "github_repo"],
            unique=True,
            postgresql_where=sa.text(
                "github_owner IS NOT NULL AND github_repo IS NOT NULL"
            ),
        )


def downgrade() -> None:
    """Reverse upgrade in strict reverse order — indexes first, columns last,
    ticket_id NOT NULL restored only after any NULL rows are purged (caller's
    responsibility)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_index(inspector, "workspaces", "ux_workspaces_org_repo"):
        op.drop_index("ux_workspaces_org_repo", table_name="workspaces")

    if _table_has_column(inspector, "workspaces", "github_connected"):
        op.drop_column("workspaces", "github_connected")
    if _table_has_column(inspector, "workspaces", "github_repo"):
        op.drop_column("workspaces", "github_repo")
    if _table_has_column(inspector, "workspaces", "github_owner"):
        op.drop_column("workspaces", "github_owner")

    inspector = sa.inspect(bind)
    if _has_index(inspector, "tasks", "ix_tasks_created_by"):
        op.drop_index("ix_tasks_created_by", table_name="tasks")
    if _has_index(inspector, "tasks", "ix_tasks_workspace_active"):
        op.drop_index("ix_tasks_workspace_active", table_name="tasks")

    if _table_has_column(inspector, "tasks", "github_repo"):
        op.drop_column("tasks", "github_repo")
    if _table_has_column(inspector, "tasks", "created_by"):
        op.drop_column("tasks", "created_by")
    if _table_has_column(inspector, "tasks", "environment_version_id"):
        op.drop_column("tasks", "environment_version_id")
    if _table_has_column(inspector, "tasks", "workspace_id"):
        op.drop_column("tasks", "workspace_id")

    # ticket_id is restored to NOT NULL. If the DB contains rows with NULL
    # ticket_id at this point, the ALTER will fail — that's intentional;
    # downgrade is only safe on a DB that has purged the SDK-direct rows.
    op.alter_column(
        "tasks",
        "ticket_id",
        existing_type=sa.String(),
        nullable=False,
    )
