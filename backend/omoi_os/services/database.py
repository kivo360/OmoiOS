"""Database service for managing database connections and sessions."""

import logging
from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator, Optional

import orjson
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import OperationalError, DisconnectionError

from omoi_os.models.base import Base

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        connection_string: str,
        pool_size: int = 5,
        max_overflow: int = 5,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,
        pool_pre_ping: bool = True,
        pool_use_lifo: bool = True,
        command_timeout: int = 30,
        connect_timeout: int = 10,
    ):
        """
        Initialize database service with both sync and async engines.

        Args:
            connection_string: PostgreSQL connection string (uses psycopg3)
                Example: "postgresql+psycopg://user:pass@localhost:15432/dbname"
            pool_size: Max persistent connections (default: 5)
            max_overflow: Additional connections above pool_size (default: 5)
            pool_timeout: Seconds to wait for connection from pool (default: 30)
            pool_recycle: Recycle connections after N seconds (default: 1800)
            pool_pre_ping: Verify connection is alive before use (default: True)
            pool_use_lifo: Use LIFO for connection reuse (default: True)
            command_timeout: Max time for SQL statements in seconds (default: 30)
            connect_timeout: Max time to establish connection in seconds (default: 10)
        """
        # Store settings for error messages
        self._command_timeout = command_timeout
        self._connect_timeout = connect_timeout

        # Connection args for psycopg3 with timeouts
        # See: https://www.psycopg.org/psycopg3/docs/api/connections.html
        connect_args = {
            "connect_timeout": connect_timeout,
            # command_timeout is set per-connection via options
            "options": f"-c statement_timeout={command_timeout * 1000}",  # PostgreSQL uses milliseconds
        }

        # Sync engine (for backward compatibility)
        # Use orjson for faster JSON serialization and native UUID/datetime support
        # Pool settings: limit connections, recycle stale ones
        self.engine = create_engine(
            connection_string,
            echo=False,
            json_serializer=_orjson_serializer,
            json_deserializer=_orjson_deserializer,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=pool_pre_ping,
            pool_use_lifo=pool_use_lifo,
            connect_args=connect_args,
        )
        self.SessionLocal = sessionmaker(
            bind=self.engine, autocommit=False, autoflush=False
        )

        # Async engine (for new auth system)
        # Convert sync URL to async (replace psycopg with psycopg for async support)
        async_url = connection_string.replace(
            "postgresql+psycopg://", "postgresql+psycopg://"
        )
        self.async_engine = create_async_engine(
            async_url,
            echo=False,
            json_serializer=_orjson_serializer,
            json_deserializer=_orjson_deserializer,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=pool_pre_ping,
            pool_use_lifo=pool_use_lifo,
            connect_args=connect_args,
        )
        self.AsyncSessionLocal = async_sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        logger.info(
            "DatabaseService initialized with pool_size=%d, pool_recycle=%ds, "
            "pool_pre_ping=%s, pool_use_lifo=%s, command_timeout=%ds, connect_timeout=%ds",
            pool_size,
            pool_recycle,
            pool_pre_ping,
            pool_use_lifo,
            command_timeout,
            connect_timeout,
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

        Includes enhanced error handling for connection failures:
        - OperationalError: Connection closed unexpectedly, timeouts
        - DisconnectionError: Connection was invalidated

        Usage:
            async with db.get_async_session() as session:
                user = User(...)
                session.add(user)
                await session.commit()
                # Session commits automatically on success
        """
        session: Optional[AsyncSession] = None
        try:
            session = self.AsyncSessionLocal()
            yield session
            # Don't auto-commit for async, let caller control
        except (OperationalError, DisconnectionError) as e:
            # Connection was closed unexpectedly or timed out
            error_msg = str(e)
            logger.error(
                "Database connection error: %s. "
                "Pool will invalidate stale connections on next request. "
                "Config: connect_timeout=%ds, command_timeout=%ds",
                error_msg,
                self._connect_timeout,
                self._command_timeout,
            )
            if session is not None:
                try:
                    await session.rollback()
                except Exception:
                    pass  # Connection may already be dead
            raise
        except Exception:
            if session is not None:
                await session.rollback()
            raise
        finally:
            if session is not None:
                try:
                    await session.close()
                except Exception:
                    # Session close can fail if connection is dead
                    logger.warning("Failed to close database session cleanly")

    def close(self):
        """Dispose of sync engine and close all connections."""
        self.engine.dispose()

    async def dispose_async(self):
        """Dispose of async engine (cleanup)."""
        await self.async_engine.dispose()

    async def close_all(self):
        """Close both sync and async engines."""
        self.engine.dispose()
        await self.async_engine.dispose()
