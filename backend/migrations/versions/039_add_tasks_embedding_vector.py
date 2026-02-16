"""Add embedding_vector column to tasks table for semantic deduplication.

Revision ID: 039_add_tasks_embedding_vector
Revises: 038_billing_system
Create Date: 2025-12-23

This migration adds a pgvector embedding column to the tasks table,
enabling semantic similarity search for duplicate detection.
This is used as an additional safeguard against runaway diagnostic
task spawning by detecting semantically similar pending tasks.

Changes:
- Adds embedding_vector column to tasks table (1536 dimensions)
- Creates IVFFlat index for fast vector similarity search
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision: str = "039_add_tasks_embedding_vector"
down_revision: Union[str, None] = "038_billing_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Embedding dimension constant - must match DEFAULT_EMBEDDING_DIMENSIONS in embedding.py
EMBEDDING_DIMENSIONS = 1536


def _table_exists(inspector, table_name: str) -> bool:
    """Check if table exists."""
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    """Check if column exists in table."""
    if not _table_exists(inspector, table_name):
        return False
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    """Check if index exists on table."""
    if not _table_exists(inspector, table_name):
        return False
    indexes = [idx["name"] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade() -> None:
    """Add embedding_vector column to tasks table."""
    bind = op.get_bind()
    inspector = inspect(bind)

    table_name = "tasks"
    column_name = "embedding_vector"
    index_name = "idx_tasks_embedding_vector"

    # Step 1: Ensure pgvector extension is installed
    print("Ensuring pgvector extension is installed...")
    try:
        bind.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        print("✓ pgvector extension ready")
    except Exception as e:
        print(f"⚠ Could not create pgvector extension: {e}")
        print("  (This is expected if using a database without pgvector support)")
        return

    # Step 2: Check if tasks table exists
    if not _table_exists(inspector, table_name):
        print(f"⊘ {table_name} table does not exist, skipping")
        return

    # Step 3: Add embedding_vector column if it doesn't exist
    if _column_exists(inspector, table_name, column_name):
        print(f"✓ Column {table_name}.{column_name} already exists")
    else:
        print(f"Creating {table_name}.{column_name} column...")
        try:
            bind.execute(
                text(f"""
                ALTER TABLE {table_name}
                ADD COLUMN {column_name} vector({EMBEDDING_DIMENSIONS})
            """)
            )
            print(
                f"  ✓ Created column {column_name} with vector({EMBEDDING_DIMENSIONS})"
            )
        except Exception as e:
            print(f"  ✗ Failed to create column: {e}")
            return

    # Step 4: Create IVFFlat index for similarity search
    # Refresh inspector to see new column
    inspector = inspect(bind)

    if not _index_exists(inspector, table_name, index_name):
        print(f"Creating index {index_name}...")
        try:
            # IVFFlat with cosine similarity (vector_cosine_ops)
            # lists=100 is a reasonable default for up to ~100k vectors
            bind.execute(
                text(f"""
                CREATE INDEX {index_name}
                ON {table_name}
                USING ivfflat ({column_name} vector_cosine_ops)
                WITH (lists = 100)
            """)
            )
            print("  ✓ Created IVFFlat index with cosine similarity")
        except Exception as e:
            # IVFFlat requires training data, try without index for now
            print(f"  ⚠ Could not create IVFFlat index: {e}")
            print("  Note: IVFFlat indexes require existing data for training.")
            print("  The index can be created later once data is populated.")
    else:
        print(f"  ✓ Index {index_name} already exists")

    print("\n✓ Migration completed successfully")


def downgrade() -> None:
    """Remove embedding_vector column from tasks table."""
    bind = op.get_bind()
    inspector = inspect(bind)

    table_name = "tasks"
    column_name = "embedding_vector"
    index_name = "idx_tasks_embedding_vector"

    if not _table_exists(inspector, table_name):
        print(f"⊘ {table_name} table does not exist, skipping")
        return

    # Drop index first
    if _index_exists(inspector, table_name, index_name):
        try:
            bind.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
            print(f"✓ Dropped index {index_name}")
        except Exception as e:
            print(f"⚠ Could not drop index: {e}")

    # Drop column
    if _column_exists(inspector, table_name, column_name):
        try:
            bind.execute(text(f"ALTER TABLE {table_name} DROP COLUMN {column_name}"))
            print(f"✓ Dropped column {column_name}")
        except Exception as e:
            print(f"⚠ Could not drop column: {e}")
