"""Add phase tracking columns to specs table for state machine execution

Revision ID: 048_add_spec_phase_tracking
Revises: 047_add_spec_versions
Create Date: 2025-01-10

This migration adds columns needed for the spec-driven development state machine:
- current_phase: Track which phase the spec is currently in (explore, requirements, etc.)
- phase_data: JSONB storing accumulated context from each phase
- session_transcripts: JSONB storing base64-encoded transcripts for session resumption
- last_checkpoint_at: When the last checkpoint was saved
- last_error: Last error message if phase execution failed
- phase_attempts: JSONB tracking retry attempts per phase

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '048_add_spec_phase_tracking'
down_revision = '047_add_spec_versions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add phase tracking columns to specs table."""
    # Add current_phase column - tracks state machine phase
    op.add_column(
        'specs',
        sa.Column(
            'current_phase',
            sa.String(50),
            nullable=False,
            server_default='explore',
            comment='State machine phase: explore, requirements, design, tasks, sync, complete',
        ),
    )

    # Add phase_data column - stores accumulated context from each phase
    op.add_column(
        'specs',
        sa.Column(
            'phase_data',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}',
            comment='Accumulated phase outputs: {explore: {...}, requirements: {...}, ...}',
        ),
    )

    # Add session_transcripts column - stores base64-encoded transcripts for resumption
    op.add_column(
        'specs',
        sa.Column(
            'session_transcripts',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}',
            comment='Base64-encoded transcripts per phase for session resumption',
        ),
    )

    # Add last_checkpoint_at column - tracks when last checkpoint was saved
    op.add_column(
        'specs',
        sa.Column(
            'last_checkpoint_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='When the last checkpoint was saved',
        ),
    )

    # Add last_error column - stores error message if phase failed
    op.add_column(
        'specs',
        sa.Column(
            'last_error',
            sa.Text(),
            nullable=True,
            comment='Last error message from phase execution',
        ),
    )

    # Add phase_attempts column - tracks retry attempts per phase
    op.add_column(
        'specs',
        sa.Column(
            'phase_attempts',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}',
            comment='Retry attempts per phase: {explore: 1, requirements: 2, ...}',
        ),
    )

    # Create index on current_phase for efficient querying
    op.create_index(
        'ix_specs_current_phase',
        'specs',
        ['current_phase'],
        unique=False,
    )


def downgrade() -> None:
    """Remove phase tracking columns from specs table."""
    op.drop_index('ix_specs_current_phase', table_name='specs')
    op.drop_column('specs', 'phase_attempts')
    op.drop_column('specs', 'last_error')
    op.drop_column('specs', 'last_checkpoint_at')
    op.drop_column('specs', 'session_transcripts')
    op.drop_column('specs', 'phase_data')
    op.drop_column('specs', 'current_phase')
