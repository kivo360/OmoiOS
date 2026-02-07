"""Add embedding vectors and content hashes for spec deduplication

Revision ID: 049_add_spec_deduplication_vectors
Revises: 048_add_spec_phase_tracking
Create Date: 2025-01-10

This migration adds deduplication support to prevent duplicate specs,
requirements, and design components from being created during the
spec-driven development workflow.

Deduplication strategy:
1. content_hash: Fast exact-match check (SHA256 of normalized content)
2. embedding_vector: Semantic similarity check via pgvector cosine distance

Scoping:
- Specs: Deduplicated within project_id
- Requirements: Deduplicated within spec_id
- Acceptance criteria: Deduplicated within requirement_id

Uses pgvector's native vector type for efficient similarity search.
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "049_add_spec_deduplication_vectors"
down_revision = "048_add_spec_phase_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add embedding vectors and content hashes for deduplication."""

    # Ensure pgvector extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ==========================================================================
    # Specs table - deduplicated within project
    # ==========================================================================

    # Add embedding vector for semantic similarity (using pgvector)
    op.add_column(
        "specs",
        sa.Column(
            "embedding_vector",
            Vector(1536),  # pgvector native type
            nullable=True,
            comment="Embedding vector (1536 dims) for semantic deduplication",
        ),
    )

    # Add content hash for exact-match fast path
    op.add_column(
        "specs",
        sa.Column(
            "content_hash",
            sa.String(64),
            nullable=True,
            comment="SHA256 hash of normalized title+description for exact match",
        ),
    )

    # Index for fast content_hash lookups within project
    op.create_index(
        "ix_specs_project_content_hash",
        "specs",
        ["project_id", "content_hash"],
        unique=False,  # Not unique - we check and reject, not constraint
    )

    # ==========================================================================
    # Spec Requirements table - deduplicated within spec
    # ==========================================================================

    # Add embedding vector for semantic similarity (using pgvector)
    op.add_column(
        "spec_requirements",
        sa.Column(
            "embedding_vector",
            Vector(1536),  # pgvector native type
            nullable=True,
            comment="Embedding vector (1536 dims) for semantic deduplication",
        ),
    )

    # Add content hash for exact-match fast path
    op.add_column(
        "spec_requirements",
        sa.Column(
            "content_hash",
            sa.String(64),
            nullable=True,
            comment="SHA256 hash of normalized condition+action for exact match",
        ),
    )

    # Index for fast content_hash lookups within spec
    op.create_index(
        "ix_spec_requirements_spec_content_hash",
        "spec_requirements",
        ["spec_id", "content_hash"],
        unique=False,
    )

    # ==========================================================================
    # Spec Acceptance Criteria table - deduplicated within requirement
    # ==========================================================================

    # Add content hash for exact-match (criteria are short, hash is sufficient)
    op.add_column(
        "spec_acceptance_criteria",
        sa.Column(
            "content_hash",
            sa.String(64),
            nullable=True,
            comment="SHA256 hash of normalized text for exact match",
        ),
    )

    # Index for fast content_hash lookups within requirement
    op.create_index(
        "ix_spec_acceptance_criteria_req_content_hash",
        "spec_acceptance_criteria",
        ["requirement_id", "content_hash"],
        unique=False,
    )

    # ==========================================================================
    # Spec Tasks table - deduplicated within spec
    # ==========================================================================

    # Add embedding vector for semantic similarity (using pgvector)
    op.add_column(
        "spec_tasks",
        sa.Column(
            "embedding_vector",
            Vector(1536),  # pgvector native type
            nullable=True,
            comment="Embedding vector (1536 dims) for semantic deduplication",
        ),
    )

    # Add content hash for exact-match fast path
    op.add_column(
        "spec_tasks",
        sa.Column(
            "content_hash",
            sa.String(64),
            nullable=True,
            comment="SHA256 hash of normalized title+description for exact match",
        ),
    )

    # Index for fast content_hash lookups within spec
    op.create_index(
        "ix_spec_tasks_spec_content_hash",
        "spec_tasks",
        ["spec_id", "content_hash"],
        unique=False,
    )


def downgrade() -> None:
    """Remove embedding vectors and content hashes."""

    # Spec Tasks
    op.drop_index("ix_spec_tasks_spec_content_hash", table_name="spec_tasks")
    op.drop_column("spec_tasks", "content_hash")
    op.drop_column("spec_tasks", "embedding_vector")

    # Spec Acceptance Criteria
    op.drop_index(
        "ix_spec_acceptance_criteria_req_content_hash",
        table_name="spec_acceptance_criteria",
    )
    op.drop_column("spec_acceptance_criteria", "content_hash")

    # Spec Requirements
    op.drop_index(
        "ix_spec_requirements_spec_content_hash", table_name="spec_requirements"
    )
    op.drop_column("spec_requirements", "content_hash")
    op.drop_column("spec_requirements", "embedding_vector")

    # Specs
    op.drop_index("ix_specs_project_content_hash", table_name="specs")
    op.drop_column("specs", "content_hash")
    op.drop_column("specs", "embedding_vector")
