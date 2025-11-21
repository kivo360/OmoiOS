from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import project modules after path modification (required for Alembic)
from omoi_os.models.base import Base  # noqa: E402

# Import all models to register them with Base.metadata
from omoi_os.models import Agent, Event, Task, Ticket, User  # noqa: E402, F401
from omoi_os.config import load_database_settings

database_url = load_database_settings().url
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", database_url)

# add your model's MetaData object here
target_metadata = Base.metadata


# Reflect auth schema tables into metadata so Alembic can see them
# This allows references to auth.users and auth functions in migrations
def include_object(object, name, type_, reflected, compare_to):
    """Include objects from both public and auth schemas."""
    if type_ == "schema":
        return name in ("public", "auth")
    if hasattr(object, "schema"):
        return object.schema in ("public", "auth")
    return True


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    print(connectable.url)
    print(config.get_section(config.config_ini_section))
    with connectable.begin() as connection:
        # Reflect auth schema into metadata
        from sqlalchemy import inspect, Table

        # Reflect auth.users table so it's visible to Alembic
        inspector = inspect(connection)
        if "auth" in inspector.get_schema_names():
            try:
                # Reflect auth.users table directly into target_metadata
                Table(
                    "users",
                    target_metadata,
                    autoload_with=connection,
                    schema="auth",
                )
            except Exception:
                # If reflection fails, continue without it
                # This is expected if auth schema is not accessible
                pass

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        context.run_migrations()


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
