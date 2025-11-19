"""Utility functions for Alembic migrations with existence checks."""

from typing import Optional, List, Dict, Any
from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from alembic import op


def table_exists(table_name: str, schema: str = "public") -> bool:
    """
    Check if table exists in the database.
    
    Args:
        table_name: Name of the table
        schema: Schema name (default: public)
    
    Returns:
        True if table exists, False otherwise
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names(schema=schema)


def column_exists(table_name: str, column_name: str, schema: str = "public") -> bool:
    """
    Check if column exists in a table.
    
    Args:
        table_name: Name of the table
        column_name: Name of the column
        schema: Schema name (default: public)
    
    Returns:
        True if column exists, False otherwise
    """
    if not table_exists(table_name, schema):
        return False
    
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name, schema=schema)]
    return column_name in columns


def index_exists(index_name: str, table_name: str, schema: str = "public") -> bool:
    """
    Check if index exists on a table.
    
    Args:
        index_name: Name of the index
        table_name: Name of the table
        schema: Schema name (default: public)
    
    Returns:
        True if index exists, False otherwise
    """
    if not table_exists(table_name, schema):
        return False
    
    conn = op.get_bind()
    inspector = inspect(conn)
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name, schema=schema)]
    return index_name in indexes


def constraint_exists(constraint_name: str, table_name: str, schema: str = "public") -> bool:
    """
    Check if constraint exists on a table.
    
    Args:
        constraint_name: Name of the constraint
        table_name: Name of the table
        schema: Schema name (default: public)
    
    Returns:
        True if constraint exists, False otherwise
    """
    if not table_exists(table_name, schema):
        return False
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check unique constraints
    unique_constraints = inspector.get_unique_constraints(table_name, schema=schema)
    if any(c['name'] == constraint_name for c in unique_constraints):
        return True
    
    # Check check constraints
    check_constraints = inspector.get_check_constraints(table_name, schema=schema)
    if any(c['name'] == constraint_name for c in check_constraints):
        return True
    
    # Check foreign keys
    foreign_keys = inspector.get_foreign_keys(table_name, schema=schema)
    if any(fk['name'] == constraint_name for fk in foreign_keys):
        return True
    
    return False


def safe_create_table(table_name: str, *args, **kwargs):
    """
    Safely create table only if it doesn't exist.
    
    Usage:
        safe_create_table(
            'users',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('email', sa.String(255))
        )
    """
    if not table_exists(table_name):
        op.create_table(table_name, *args, **kwargs)
        print(f"✓ Created table: {table_name}")
    else:
        print(f"⊘ Table already exists, skipping: {table_name}")


def safe_add_column(table_name: str, column: Any):
    """
    Safely add column only if it doesn't exist.
    
    Usage:
        safe_add_column('users', sa.Column('department', sa.String(100)))
    """
    column_name = column.name
    if not column_exists(table_name, column_name):
        op.add_column(table_name, column)
        print(f"✓ Added column: {table_name}.{column_name}")
    else:
        print(f"⊘ Column already exists, skipping: {table_name}.{column_name}")


def safe_drop_column(table_name: str, column_name: str):
    """
    Safely drop column only if it exists.
    
    Usage:
        safe_drop_column('users', 'old_field')
    """
    if column_exists(table_name, column_name):
        op.drop_column(table_name, column_name)
        print(f"✓ Dropped column: {table_name}.{column_name}")
    else:
        print(f"⊘ Column doesn't exist, skipping: {table_name}.{column_name}")


def safe_create_index(index_name: str, table_name: str, columns: List[str], **kwargs):
    """
    Safely create index only if it doesn't exist.
    
    Usage:
        safe_create_index('idx_users_email', 'users', ['email'], unique=True)
    """
    if not index_exists(index_name, table_name):
        op.create_index(index_name, table_name, columns, **kwargs)
        print(f"✓ Created index: {index_name}")
    else:
        print(f"⊘ Index already exists, skipping: {index_name}")


def safe_drop_index(index_name: str, table_name: Optional[str] = None):
    """
    Safely drop index only if it exists.
    
    Usage:
        safe_drop_index('idx_users_email', 'users')
    """
    if table_name and index_exists(index_name, table_name):
        op.drop_index(index_name, table_name=table_name)
        print(f"✓ Dropped index: {index_name}")
    else:
        print(f"⊘ Index doesn't exist, skipping: {index_name}")


def safe_create_foreign_key(
    constraint_name: str,
    source_table: str,
    referent_table: str,
    local_cols: List[str],
    remote_cols: List[str],
    **kwargs
):
    """
    Safely create foreign key only if it doesn't exist.
    
    Usage:
        safe_create_foreign_key(
            'fk_tickets_project',
            'tickets',
            'projects',
            ['project_id'],
            ['id'],
            ondelete='CASCADE'
        )
    """
    if not constraint_exists(constraint_name, source_table):
        op.create_foreign_key(
            constraint_name,
            source_table,
            referent_table,
            local_cols,
            remote_cols,
            **kwargs
        )
        print(f"✓ Created foreign key: {constraint_name}")
    else:
        print(f"⊘ Foreign key already exists, skipping: {constraint_name}")


def safe_drop_constraint(constraint_name: str, table_name: str, type_: Optional[str] = None):
    """
    Safely drop constraint only if it exists.
    
    Usage:
        safe_drop_constraint('fk_tickets_project', 'tickets', type_='foreignkey')
    """
    if constraint_exists(constraint_name, table_name):
        op.drop_constraint(constraint_name, table_name, type_=type_)
        print(f"✓ Dropped constraint: {constraint_name}")
    else:
        print(f"⊘ Constraint doesn't exist, skipping: {constraint_name}")


def safe_drop_table(table_name: str):
    """
    Safely drop table only if it exists.
    
    Usage:
        safe_drop_table('old_table')
    """
    if table_exists(table_name):
        op.drop_table(table_name)
        print(f"✓ Dropped table: {table_name}")
    else:
        print(f"⊘ Table doesn't exist, skipping: {table_name}")


def get_table_info(table_name: str, schema: str = "public") -> Dict[str, Any]:
    """
    Get detailed information about a table.
    
    Returns dict with:
        - exists: bool
        - columns: List[Dict] (if exists)
        - indexes: List[Dict] (if exists)
        - foreign_keys: List[Dict] (if exists)
        - primary_key: Dict (if exists)
    """
    if not table_exists(table_name, schema):
        return {"exists": False}
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    return {
        "exists": True,
        "columns": inspector.get_columns(table_name, schema=schema),
        "indexes": inspector.get_indexes(table_name, schema=schema),
        "foreign_keys": inspector.get_foreign_keys(table_name, schema=schema),
        "primary_key": inspector.get_pk_constraint(table_name, schema=schema),
        "unique_constraints": inspector.get_unique_constraints(table_name, schema=schema),
        "check_constraints": inspector.get_check_constraints(table_name, schema=schema),
    }


def print_migration_summary():
    """Print summary of current database state."""
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    print("\n" + "="*60)
    print("DATABASE STATE SUMMARY")
    print("="*60)
    print(f"Total tables: {len(tables)}")
    print(f"Tables: {', '.join(sorted(tables))}")
    print("="*60 + "\n")

