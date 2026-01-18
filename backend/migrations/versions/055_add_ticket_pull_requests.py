"""add_ticket_pull_requests

Revision ID: 055_add_ticket_pull_requests
Revises: 054_add_autonomous_execution_toggle
Create Date: 2025-01-18

Adds ticket_pull_requests table to track PRs linked to tickets.
When a PR is merged, the associated task is marked as completed
and the ticket status is updated to done.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "055_add_ticket_pull_requests"
down_revision: Union[str, Sequence[str], None] = "88c08d730f8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ticket_pull_requests table."""
    op.create_table(
        "ticket_pull_requests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("ticket_id", sa.String(), nullable=False),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("pr_title", sa.String(500), nullable=False),
        sa.Column("pr_body", sa.Text(), nullable=True),
        sa.Column("head_branch", sa.String(200), nullable=False),
        sa.Column("base_branch", sa.String(200), nullable=False),
        sa.Column("repo_owner", sa.String(200), nullable=False),
        sa.Column("repo_name", sa.String(200), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default="open"),
        sa.Column("html_url", sa.String(500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("github_user", sa.String(200), nullable=False),
        sa.Column("merge_commit_sha", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            ondelete="CASCADE",
        ),
    )

    # Create indexes
    op.create_index(
        "ix_ticket_pull_requests_ticket_id",
        "ticket_pull_requests",
        ["ticket_id"],
    )
    op.create_index(
        "ix_ticket_pull_requests_repo_owner",
        "ticket_pull_requests",
        ["repo_owner"],
    )
    op.create_index(
        "ix_ticket_pull_requests_repo_name",
        "ticket_pull_requests",
        ["repo_name"],
    )
    op.create_index(
        "ix_ticket_pull_requests_state",
        "ticket_pull_requests",
        ["state"],
    )
    # Unique constraint on (ticket_id, pr_number)
    op.create_index(
        "idx_unique_ticket_pr",
        "ticket_pull_requests",
        ["ticket_id", "pr_number"],
        unique=True,
    )
    # Composite index for repo + pr_number lookups
    op.create_index(
        "idx_pr_repo",
        "ticket_pull_requests",
        ["repo_owner", "repo_name", "pr_number"],
    )


def downgrade() -> None:
    """Drop ticket_pull_requests table."""
    op.drop_index("idx_pr_repo", table_name="ticket_pull_requests")
    op.drop_index("idx_unique_ticket_pr", table_name="ticket_pull_requests")
    op.drop_index("ix_ticket_pull_requests_state", table_name="ticket_pull_requests")
    op.drop_index("ix_ticket_pull_requests_repo_name", table_name="ticket_pull_requests")
    op.drop_index("ix_ticket_pull_requests_repo_owner", table_name="ticket_pull_requests")
    op.drop_index("ix_ticket_pull_requests_ticket_id", table_name="ticket_pull_requests")
    op.drop_table("ticket_pull_requests")
