"""Add exposed_ports + persistent_volume to environment_versions.

Spec §15 §11 calls out two fields that hosted-editor + workspace-persistent
volumes need, and spec §05 says environments are immutable per version.
`credentials` and `egress` already live on `EnvironmentVersion` for that
reason. We follow the same pattern here rather than adding mutable
sandbox-shaping fields to the parent `environments` table.

`exposed_ports`: JSONB list of int ports (e.g. `[8443]`) that the sandbox
should expose via tunnel at spawn. Frozen per version; a tenant rolls a
new version to change it.

`persistent_volume`: boolean — whether this version mounts a workspace-
scoped volume at `/workspace`. The volume's NAME is NOT stored here —
per spec §15 §4 #3 volumes are workspace-scoped, so the spawner
synthesises `f"ws-{task.workspace_id}"` at spawn time.

Revision ID: 072_environment_version_ports_and_volume
Revises: 071_decouple_session_from_ticket
Create Date: 2026-04-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "072_environment_version_ports_and_volume"
down_revision: Union[str, None] = "071_decouple_session_from_ticket"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    if table not in inspector.get_table_names():
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "environment_versions", "exposed_ports"):
        op.add_column(
            "environment_versions",
            sa.Column(
                "exposed_ports",
                postgresql.JSONB,
                nullable=True,
                comment=(
                    "List of int ports to expose via sandbox tunnel "
                    "(e.g. [8443] for hosted-editor). Frozen per version."
                ),
            ),
        )

    if not _has_column(inspector, "environment_versions", "persistent_volume"):
        op.add_column(
            "environment_versions",
            sa.Column(
                "persistent_volume",
                sa.Boolean,
                nullable=False,
                server_default=sa.false(),
                comment=(
                    "Whether this version mounts a workspace-scoped volume "
                    "at /workspace. Volume name derived from workspace_id "
                    "at spawn (spec §15 §4 #3); not stored as a column."
                ),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_column(inspector, "environment_versions", "persistent_volume"):
        op.drop_column("environment_versions", "persistent_volume")
    if _has_column(inspector, "environment_versions", "exposed_ports"):
        op.drop_column("environment_versions", "exposed_ports")
