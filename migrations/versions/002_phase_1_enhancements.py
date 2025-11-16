"""Phase 1 enhancements

Revision ID: 002_phase1
Revises: 001_initial
Create Date: 2025-11-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_phase1'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Stream A: Task Dependencies & Blocking
    # Add dependencies JSONB field to tasks table
    op.add_column('tasks', sa.Column('dependencies', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index('idx_tasks_dependencies', 'tasks', ['dependencies'], postgresql_using='gin')
    
    # Stream B: Error Handling & Retries
    op.add_column('tasks', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tasks', sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'))
    
    # Stream D: Task Timeout & Cancellation
    op.add_column('tasks', sa.Column('timeout_seconds', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Stream D
    op.drop_column('tasks', 'timeout_seconds')
    
    # Stream B
    op.drop_column('tasks', 'max_retries')
    op.drop_column('tasks', 'retry_count')
    
    # Stream A
    op.drop_index('idx_tasks_dependencies', table_name='tasks')
    op.drop_column('tasks', 'dependencies')

