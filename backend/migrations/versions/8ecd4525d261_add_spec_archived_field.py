"""add_spec_archived_field

Revision ID: 8ecd4525d261
Revises: 056_add_spec_id_to_tickets
Create Date: 2026-01-22 21:13:30.325130

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8ecd4525d261'
down_revision: Union[str, Sequence[str], None] = '056_add_spec_id_to_tickets'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add archived and archived_at fields to specs table."""
    op.add_column(
        'specs',
        sa.Column(
            'archived',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='Whether the spec is archived (soft delete)',
        )
    )
    op.add_column(
        'specs',
        sa.Column(
            'archived_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='When the spec was archived',
        )
    )
    op.create_index('ix_specs_archived', 'specs', ['archived'])


def downgrade() -> None:
    """Remove archived and archived_at fields from specs table."""
    op.drop_index('ix_specs_archived', table_name='specs')
    op.drop_column('specs', 'archived_at')
    op.drop_column('specs', 'archived')
