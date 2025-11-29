"""Database service for managing database connections and sessions."""

from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator

import orjson
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from omoi_os.models.base import Base


def _orjson_default(obj):
    """Default handler for types orjson doesn't handle natively."""
    from enum import Enum
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _orjson_serializer(obj):
    """Serialize objects to JSON using orjson.
    
    orjson natively handles UUID, datetime, and other types that
    the standard json module cannot serialize. We add Enum support
    via the default handler.
    """
    return orjson.dumps(
        obj,
        default=_orjson_default,
        option=orjson.OPT_PASSTHROUGH_DATACLASS,
    ).decode("utf-8")


def _orjson_deserializer(s):
    """Deserialize JSON using orjson."""
    return orjson.loads(s)


class DatabaseService:
    """Manages database connections and provides session context manager."""

    def __init__(self, connection_string: str):
        """
        Initialize database service with both sync and async engines.

        Args:
            connection_string: PostgreSQL connection string (uses psycopg3)
                Example: "postgresql+psycopg://user:pass@localhost:15432/dbname"
        """
        # Sync engine (for backward compatibility)
        # Use orjson for faster JSON serialization and native UUID/datetime support
        self.engine = create_engine(
            connection_string,
            echo=False,
            json_serializer=_orjson_serializer,
            json_deserializer=_orjson_deserializer,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        
        # Async engine (for new auth system)
        # Convert sync URL to async (replace psycopg with psycopg for async support)
        async_url = connection_string.replace('postgresql+psycopg://', 'postgresql+psycopg://')
        self.async_engine = create_async_engine(
            async_url,
            echo=False,
            json_serializer=_orjson_serializer,
            json_deserializer=_orjson_deserializer,
        )
        self.AsyncSessionLocal = async_sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )

    def create_tables(self) -> None:
        """Create all database tables defined in Base.metadata."""
        Base.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        """Drop all database tables defined in Base.metadata."""
        Base.metadata.drop_all(self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a synchronous database session with automatic commit/rollback.

        Usage:
            with db.get_session() as session:
                ticket = Ticket(...)
                session.add(ticket)
                # Session commits automatically on success
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session with automatic commit/rollback.

        Usage:
            async with db.get_async_session() as session:
                user = User(...)
                session.add(user)
                await session.commit()
                # Session commits automatically on success
        """
        session = self.AsyncSessionLocal()
        try:
            yield session
            # Don't auto-commit for async, let caller control
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def dispose_async(self):
        """Dispose of async engine (cleanup)."""
        await self.async_engine.dispose()
