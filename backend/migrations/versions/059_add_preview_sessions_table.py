"""Add preview_sessions table for live preview lifecycle tracking.

Revision ID: 059_add_preview_sessions
Revises: 058_add_merge_attempts
Create Date: 2026-02-07

Phase 1: Backend Preview Routes + DaytonaSpawner Integration.
Tracks preview sessions per sandbox for live preview URL management.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "059_add_preview_sessions"
down_revision = "058_add_merge_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create preview_sessions table."""
    op.create_table(
        "preview_sessions",
        # Primary key
        sa.Column("id", sa.String(), primary_key=True),
        # Related entities
        sa.Column(
            "sandbox_id",
            sa.String(255),
            nullable=False,
            unique=True,
            comment="Daytona sandbox ID (one preview per sandbox)",
        ),
        sa.Column(
            "task_id",
            sa.String(),
            sa.ForeignKey("tasks.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="Task that triggered this preview",
        ),
        sa.Column(
            "project_id",
            sa.String(),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.String(),
            nullable=True,
            index=True,
            comment="User who owns this preview session",
        ),
        # Status
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            default="pending",
            index=True,
        ),
        # Preview URL and auth
        sa.Column(
            "preview_url",
            sa.Text(),
            nullable=True,
            comment="Public Daytona preview URL",
        ),
        sa.Column(
            "preview_token",
            sa.Text(),
            nullable=True,
            comment="Auth token from sandbox.get_preview_link()",
        ),
        # Dev server config
        sa.Column(
            "port",
            sa.Integer(),
            nullable=False,
            default=3000,
            comment="Dev server port",
        ),
        sa.Column(
            "framework",
            sa.String(50),
            nullable=True,
            comment="Detected framework: vite, next, vue, etc.",
        ),
        sa.Column(
            "session_id",
            sa.String(255),
            nullable=True,
            comment="Daytona session ID for dev server process",
        ),
        sa.Column(
            "command_id",
            sa.String(255),
            nullable=True,
            comment="Daytona command ID for dev server process",
        ),
        # Error tracking
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error details if preview failed to start",
        ),
        # Timestamps
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When dev server was started",
        ),
        sa.Column(
            "ready_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When preview became available",
        ),
        sa.Column(
            "stopped_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When preview was stopped",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Composite indexes for common query patterns
    op.create_index(
        "ix_preview_sessions_sandbox_id",
        "preview_sessions",
        ["sandbox_id"],
        unique=True,
    )
    op.create_index(
        "ix_preview_sessions_status_created",
        "preview_sessions",
        ["status", "created_at"],
    )


def downgrade() -> None:
    """Drop preview_sessions table."""
    op.drop_index("ix_preview_sessions_status_created", table_name="preview_sessions")
    op.drop_index("ix_preview_sessions_sandbox_id", table_name="preview_sessions")
    op.drop_table("preview_sessions")
