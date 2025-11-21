"""Database service for managing database connections and sessions."""

from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from omoi_os.models.base import Base


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
        self.engine = create_engine(connection_string, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        
        # Async engine (for new auth system)
        # Convert sync URL to async (replace psycopg with psycopg for async support)
        async_url = connection_string.replace('postgresql+psycopg://', 'postgresql+psycopg://')
        self.async_engine = create_async_engine(async_url, echo=False)
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
