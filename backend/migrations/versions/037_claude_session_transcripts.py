"""Add claude_session_transcripts table for cross-sandbox session resumption.

Revision ID: 037_claude_session_transcripts
Revises: b52490b4c2a8
Create Date: 2025-12-17

Enables storing Claude Code session transcripts in the database for cross-sandbox
resumption. Transcripts are stored as base64-encoded JSONL files, allowing
conversations to continue across different sandbox instances.

Phase: Claude Sandbox Agent - Session Portability
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.exc import NoSuchTableError


# revision identifiers, used by Alembic.
revision: str = "037_claude_session_transcripts"
down_revision: Union[str, None] = "b52490b4c2a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: Inspector, table_name: str) -> bool:
    """Check if a table exists."""
    return table_name in inspector.get_table_names()


def _index_exists(inspector: Inspector, table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    try:
        indexes = inspector.get_indexes(table_name)
        return index_name in {idx["name"] for idx in indexes}
    except NoSuchTableError:
        return False


def upgrade() -> None:
    """Create claude_session_transcripts table for session portability."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Check if table already exists (from partial migration)
    if _table_exists(inspector, "claude_session_transcripts"):
        print(
            "⚠️  Table claude_session_transcripts already exists, skipping table creation"
        )
        # Just ensure indexes exist
        table_name = "claude_session_transcripts"
        if not _index_exists(
            inspector, table_name, "ix_claude_session_transcripts_session_id"
        ):
            op.create_index(
                "ix_claude_session_transcripts_session_id",
                table_name,
                ["session_id"],
                unique=True,
            )
        if not _index_exists(
            inspector, table_name, "ix_claude_session_transcripts_sandbox_id"
        ):
            op.create_index(
                "ix_claude_session_transcripts_sandbox_id",
                table_name,
                ["sandbox_id"],
            )
        if not _index_exists(
            inspector, table_name, "ix_claude_session_transcripts_task_id"
        ):
            op.create_index(
                "ix_claude_session_transcripts_task_id",
                table_name,
                ["task_id"],
            )
        if not _index_exists(
            inspector, table_name, "ix_claude_session_transcripts_created_at"
        ):
            op.create_index(
                "ix_claude_session_transcripts_created_at",
                table_name,
                ["created_at"],
            )
        return

    op.create_table(
        "claude_session_transcripts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "session_id",
            sa.String(255),
            nullable=False,
            unique=True,
            comment="Claude Code session ID (UUID format)",
        ),
        sa.Column(
            "transcript_b64",
            sa.Text(),
            nullable=False,
            comment="Base64-encoded JSONL transcript file content for cross-sandbox resumption",
        ),
        sa.Column(
            "sandbox_id",
            sa.String(255),
            nullable=True,
            comment="Daytona sandbox ID where this session was created",
        ),
        sa.Column(
            "task_id",
            sa.String(),
            sa.ForeignKey("tasks.id", ondelete="SET NULL"),
            nullable=True,
            comment="Optional task ID associated with this session",
        ),
        sa.Column(
            "session_metadata",
            JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Additional session metadata: cost, turns, model, etc.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="When the session transcript was first stored",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="When the session transcript was last updated",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )

    # Create indexes for efficient querying
    op.create_index(
        "ix_claude_session_transcripts_session_id",
        "claude_session_transcripts",
        ["session_id"],
        unique=True,
    )
    op.create_index(
        "ix_claude_session_transcripts_sandbox_id",
        "claude_session_transcripts",
        ["sandbox_id"],
    )
    op.create_index(
        "ix_claude_session_transcripts_task_id",
        "claude_session_transcripts",
        ["task_id"],
    )
    op.create_index(
        "ix_claude_session_transcripts_created_at",
        "claude_session_transcripts",
        ["created_at"],
    )


def downgrade() -> None:
    """Remove claude_session_transcripts table."""
    op.drop_index(
        "ix_claude_session_transcripts_created_at",
        table_name="claude_session_transcripts",
    )
    op.drop_index(
        "ix_claude_session_transcripts_task_id",
        table_name="claude_session_transcripts",
    )
    op.drop_index(
        "ix_claude_session_transcripts_sandbox_id",
        table_name="claude_session_transcripts",
    )
    op.drop_index(
        "ix_claude_session_transcripts_session_id",
        table_name="claude_session_transcripts",
    )
    op.drop_table("claude_session_transcripts")
