"""merge_billing_branches

Revision ID: 13bc90c22e27
Revises: 038_billing_system, 041_cost_record_billing_integration
Create Date: 2025-12-24 08:54:12.772237

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '13bc90c22e27'
down_revision: Union[str, Sequence[str], None] = ('038_billing_system', '041_cost_record_billing_integration')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
