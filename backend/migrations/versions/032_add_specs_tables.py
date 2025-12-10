"""Add specs tables

Revision ID: 032_add_specs_tables
Revises: 031_workspace_isolation_system
Create Date: 2025-12-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "032_add_specs_tables"
down_revision = "c7dd654683a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create specs table
    op.create_table(
        "specs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="draft",
            comment="draft, requirements, design, executing, completed",
        ),
        sa.Column(
            "phase",
            sa.String(50),
            nullable=False,
            server_default="Requirements",
            comment="Requirements, Design, Implementation, Testing, Done",
        ),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("test_coverage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("active_agents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("linked_tickets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "design",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Design artifact: {architecture, data_model, api_spec}",
        ),
        sa.Column(
            "execution",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Execution metrics: {overall_progress, test_coverage, tests_total, etc.}",
        ),
        sa.Column(
            "requirements_approved",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "requirements_approved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "design_approved", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "design_approved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_specs_project_id"), "specs", ["project_id"], unique=False)
    op.create_index(op.f("ix_specs_status"), "specs", ["status"], unique=False)

    # Create spec_requirements table
    op.create_table(
        "spec_requirements",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("spec_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("condition", sa.Text(), nullable=False, comment="EARS 'WHEN' clause"),
        sa.Column(
            "action",
            sa.Text(),
            nullable=False,
            comment="EARS 'THE SYSTEM SHALL' clause",
        ),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="pending",
            comment="pending, in_progress, completed",
        ),
        sa.Column(
            "linked_design",
            sa.String(100),
            nullable=True,
            comment="Reference to design component",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["spec_id"],
            ["specs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_spec_requirements_spec_id"),
        "spec_requirements",
        ["spec_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_spec_requirements_status"),
        "spec_requirements",
        ["status"],
        unique=False,
    )

    # Create spec_acceptance_criteria table
    op.create_table(
        "spec_acceptance_criteria",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("requirement_id", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["spec_requirements.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_spec_acceptance_criteria_requirement_id"),
        "spec_acceptance_criteria",
        ["requirement_id"],
        unique=False,
    )

    # Create spec_tasks table
    op.create_table(
        "spec_tasks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("spec_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("phase", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="pending",
            comment="pending, in_progress, completed, blocked",
        ),
        sa.Column("assigned_agent", sa.String(), nullable=True),
        sa.Column(
            "dependencies",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("estimated_hours", sa.Float(), nullable=True),
        sa.Column("actual_hours", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["spec_id"],
            ["specs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_spec_tasks_spec_id"), "spec_tasks", ["spec_id"], unique=False
    )
    op.create_index(
        op.f("ix_spec_tasks_status"), "spec_tasks", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_spec_tasks_status"), table_name="spec_tasks")
    op.drop_index(op.f("ix_spec_tasks_spec_id"), table_name="spec_tasks")
    op.drop_table("spec_tasks")

    op.drop_index(
        op.f("ix_spec_acceptance_criteria_requirement_id"),
        table_name="spec_acceptance_criteria",
    )
    op.drop_table("spec_acceptance_criteria")

    op.drop_index(op.f("ix_spec_requirements_status"), table_name="spec_requirements")
    op.drop_index(op.f("ix_spec_requirements_spec_id"), table_name="spec_requirements")
    op.drop_table("spec_requirements")

    op.drop_index(op.f("ix_specs_status"), table_name="specs")
    op.drop_index(op.f("ix_specs_project_id"), table_name="specs")
    op.drop_table("specs")
