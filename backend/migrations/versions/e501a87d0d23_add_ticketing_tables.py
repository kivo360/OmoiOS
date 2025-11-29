"""add_ticketing_tables

Revision ID: e501a87d0d23
Revises: b3c27dc6fc52
Create Date: 2025-11-29 08:46:27.953627

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e501a87d0d23'
down_revision: Union[str, Sequence[str], None] = 'b3c27dc6fc52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create ticket_history table
    op.create_table(
        'ticket_history',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('ticket_id', sa.String, sa.ForeignKey('tickets.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('agent_id', sa.String, index=True, nullable=False),
        sa.Column('change_type', sa.String(50), nullable=False, index=True),
        sa.Column('field_name', sa.String(100), nullable=True),
        sa.Column('old_value', sa.Text, nullable=True),
        sa.Column('new_value', sa.Text, nullable=True),
        sa.Column('change_description', sa.Text, nullable=True),
        sa.Column('change_metadata', sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False, index=True),
    )
    
    # Create ticket_commits table
    op.create_table(
        'ticket_commits',
        sa.Column('id', sa.String, primary_key=True),
        sa.Column('ticket_id', sa.String, sa.ForeignKey('tickets.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('agent_id', sa.String, index=True, nullable=False),
        sa.Column('commit_sha', sa.String(40), nullable=False),
        sa.Column('commit_message', sa.Text, nullable=False),
        sa.Column('branch_name', sa.String(255), nullable=True),
        sa.Column('files_changed', sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column('commit_metadata', sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column('committed_at', sa.DateTime(timezone=True), nullable=False, index=True),
    )
    
    # Create ticket_comments table
    op.create_table(
        'ticket_comments',
        sa.Column('id', sa.String, primary_key=True),
        sa.Column('ticket_id', sa.String, sa.ForeignKey('tickets.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('author_id', sa.String, index=True, nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('comment_type', sa.String(50), nullable=False, index=True),
        sa.Column('comment_metadata', sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, index=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('ticket_comments')
    op.drop_table('ticket_commits')
    op.drop_table('ticket_history')
