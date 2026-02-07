"""Agent Registration Enhancements (REQ-ALM-001)

Revision ID: 023_agent_registration_enhancements
Revises: 022_add_required_capabilities_to_tasks
Create Date: 2025-01-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "023_agent_registration_enhancements"
down_revision: Union[str, None] = "022_add_required_capabilities_to_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add agent_name field (REQ-ALM-001 Step 2)
    op.add_column(
        "agents",
        sa.Column(
            "agent_name",
            sa.String(length=255),
            nullable=True,
            comment="Human-readable name: {type}-{phase}-{sequence} (REQ-ALM-001)",
        ),
    )
    op.create_index("ix_agents_agent_name", "agents", ["agent_name"], unique=False)

    # Add cryptographic identity fields (REQ-ALM-001 Step 2)
    op.add_column(
        "agents",
        sa.Column(
            "crypto_public_key",
            sa.Text(),
            nullable=True,
            comment="Public key from cryptographic identity pair (REQ-ALM-001)",
        ),
    )
    op.add_column(
        "agents",
        sa.Column(
            "crypto_identity_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Cryptographic identity metadata: key_id, algorithm, created_at (REQ-ALM-001)",
        ),
    )

    # Add metadata field for version, config, resource requirements (REQ-ALM-001)
    op.add_column(
        "agents",
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Additional agent metadata: version, binary_path, config, resource_requirements (REQ-ALM-001)",
        ),
    )

    # Add registered_by field (REQ-ALM-001 Step 3)
    op.add_column(
        "agents",
        sa.Column(
            "registered_by",
            sa.String(length=255),
            nullable=True,
            comment="Orchestrator instance that registered this agent (REQ-ALM-001)",
        ),
    )


def downgrade() -> None:
    # Drop columns
    op.drop_column("agents", "registered_by")
    op.drop_column("agents", "metadata")
    op.drop_column("agents", "crypto_identity_metadata")
    op.drop_column("agents", "crypto_public_key")
    op.drop_index("ix_agents_agent_name", table_name="agents")
    op.drop_column("agents", "agent_name")
