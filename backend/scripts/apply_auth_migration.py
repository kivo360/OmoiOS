"""Script to manually apply auth migration 030."""

import sys
from pathlib import Path

# Add migrations to path
migrations_path = Path(__file__).parent.parent / "migrations"
sys.path.insert(0, str(migrations_path))

from alembic import op
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text

# Import the migration
from versions.migration_030_auth_system_foundation import upgrade


def apply_migration():
    """Apply migration 030 directly."""
    from omoi_os.config import load_database_settings

    settings = load_database_settings()

    # Create engine
    engine = create_engine(settings.url)

    # Setup alembic context
    with engine.begin() as conn:
        # Create migration context
        ctx = MigrationContext.configure(conn)

        # Check current version
        current = ctx.get_current_revision()
        print(f"Current database version: {current}")

        # Run upgrade
        print("\nApplying migration 030...")
        with op.batch_alter_table as context:
            context.configure(connection=conn)
            upgrade()

        # Update version
        conn.execute(
            text(
                "UPDATE alembic_version SET version_num = '030_auth_system_foundation'"
            )
        )

        print("\n✅ Migration applied successfully!")


if __name__ == "__main__":
    apply_migration()
