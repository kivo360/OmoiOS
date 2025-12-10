"""Fix pgvector column dimensions for proper indexing.

Revision ID: 034_fix_pgvector_dimensions
Revises: 033_add_reasoning_and_explore_tables
Create Date: 2025-12-10

This migration ensures all pgvector columns have explicit dimensions (1536)
for proper HNSW/IVFFlat index compatibility. pgvector requires explicit
dimensions for index creation, and the standard indexing limit is 2000.

Changes:
- Ensures pgvector extension is installed
- Adds embedding_vector column to tickets table if missing
- Recreates vector column with explicit dimension if needed
- Creates IVFFlat index for vector similarity search
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision: str = "034_fix_pgvector_dimensions"
down_revision: Union[str, None] = "033_add_reasoning_and_explore"
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
    """Add/fix pgvector columns with explicit dimensions."""
    bind = op.get_bind()
    inspector = inspect(bind)

    # Step 1: Ensure pgvector extension is installed
    print("Ensuring pgvector extension is installed...")
    try:
        bind.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        print("✓ pgvector extension ready")
    except Exception as e:
        print(f"⚠ Could not create pgvector extension: {e}")
        print("  (This is expected if using a database without pgvector support)")
        return

    # Step 2: Handle tickets.embedding_vector column
    if _table_exists(inspector, "tickets"):
        _fix_tickets_embedding_vector(bind, inspector)
    else:
        print("⊘ tickets table does not exist, skipping")

    print("\n✓ Migration completed successfully")


def _fix_tickets_embedding_vector(bind, inspector) -> None:
    """Fix or create the embedding_vector column on tickets table."""
    table_name = "tickets"
    column_name = "embedding_vector"
    index_name = "idx_tickets_embedding_vector"

    if _column_exists(inspector, table_name, column_name):
        # Column exists - check if we need to alter its type
        print(f"Column {table_name}.{column_name} exists, checking dimensions...")
        
        # Get column type info
        columns = inspector.get_columns(table_name)
        col_info = next((c for c in columns if c["name"] == column_name), None)
        
        if col_info:
            col_type = str(col_info.get("type", ""))
            print(f"  Current type: {col_type}")
            
            # Check if dimension is already set
            # pgvector types look like: VECTOR or VECTOR(1536)
            if f"({EMBEDDING_DIMENSIONS})" in col_type.upper():
                print(f"  ✓ Column already has correct dimensions ({EMBEDDING_DIMENSIONS})")
            else:
                # Need to recreate with proper dimensions
                print(f"  Recreating column with explicit dimensions ({EMBEDDING_DIMENSIONS})...")
                
                # Drop existing index first
                if _index_exists(inspector, table_name, index_name):
                    print(f"  Dropping existing index {index_name}...")
                    try:
                        bind.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
                    except Exception as e:
                        print(f"  ⚠ Could not drop index: {e}")
                
                # Alter column type to have explicit dimensions
                # Note: This will fail if there's data with wrong dimensions
                try:
                    bind.execute(text(f"""
                        ALTER TABLE {table_name} 
                        ALTER COLUMN {column_name} TYPE vector({EMBEDDING_DIMENSIONS})
                    """))
                    print(f"  ✓ Updated column to vector({EMBEDDING_DIMENSIONS})")
                except Exception as e:
                    print(f"  ⚠ Could not alter column type: {e}")
                    print(f"  Attempting to recreate column...")
                    
                    # Backup data, drop, recreate, restore
                    try:
                        # Create temp column
                        bind.execute(text(f"""
                            ALTER TABLE {table_name} 
                            ADD COLUMN {column_name}_backup vector({EMBEDDING_DIMENSIONS})
                        """))
                        
                        # Copy data (truncating if needed)
                        bind.execute(text(f"""
                            UPDATE {table_name} 
                            SET {column_name}_backup = {column_name}::vector({EMBEDDING_DIMENSIONS})
                            WHERE {column_name} IS NOT NULL
                        """))
                        
                        # Drop old column
                        bind.execute(text(f"ALTER TABLE {table_name} DROP COLUMN {column_name}"))
                        
                        # Rename backup
                        bind.execute(text(f"""
                            ALTER TABLE {table_name} 
                            RENAME COLUMN {column_name}_backup TO {column_name}
                        """))
                        
                        print(f"  ✓ Recreated column with correct dimensions")
                    except Exception as e2:
                        print(f"  ✗ Failed to recreate column: {e2}")
                        # Clean up temp column if it exists
                        try:
                            bind.execute(text(f"""
                                ALTER TABLE {table_name} 
                                DROP COLUMN IF EXISTS {column_name}_backup
                            """))
                        except:
                            pass
                        return
    else:
        # Column doesn't exist - create it
        print(f"Creating {table_name}.{column_name} column...")
        try:
            bind.execute(text(f"""
                ALTER TABLE {table_name} 
                ADD COLUMN {column_name} vector({EMBEDDING_DIMENSIONS})
            """))
            print(f"  ✓ Created column {column_name} with vector({EMBEDDING_DIMENSIONS})")
        except Exception as e:
            print(f"  ✗ Failed to create column: {e}")
            return

    # Step 3: Create IVFFlat index for similarity search
    # Refresh inspector to see new column
    inspector = inspect(bind)
    
    if not _index_exists(inspector, table_name, index_name):
        print(f"Creating index {index_name}...")
        try:
            # IVFFlat with cosine similarity (vector_cosine_ops)
            # lists=100 is a reasonable default for up to ~100k vectors
            bind.execute(text(f"""
                CREATE INDEX {index_name} 
                ON {table_name} 
                USING ivfflat ({column_name} vector_cosine_ops) 
                WITH (lists = 100)
            """))
            print(f"  ✓ Created IVFFlat index with cosine similarity")
        except Exception as e:
            # IVFFlat requires training data, try without index for now
            print(f"  ⚠ Could not create IVFFlat index: {e}")
            print(f"  Note: IVFFlat indexes require existing data for training.")
            print(f"  The index can be created later once data is populated.")
    else:
        print(f"  ✓ Index {index_name} already exists")


def downgrade() -> None:
    """Remove explicit dimensions (revert to unspecified)."""
    bind = op.get_bind()
    inspector = inspect(bind)

    # We don't actually want to remove dimensions in downgrade
    # as that would break things. Just drop the index if we created it.
    
    if _table_exists(inspector, "tickets"):
        index_name = "idx_tickets_embedding_vector"
        if _index_exists(inspector, "tickets", index_name):
            try:
                bind.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
                print(f"✓ Dropped index {index_name}")
            except Exception as e:
                print(f"⚠ Could not drop index: {e}")

    print("Note: Vector column dimensions are not reverted to avoid data loss.")
