"""Database service for managing database connections and sessions."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseService:
    """Manages database connections and provides session context manager."""

    def __init__(self, connection_string: str):
        """
        Initialize database service.

        Args:
            connection_string: PostgreSQL connection string
                Example: "postgresql://user:pass@localhost:15432/dbname"
        """
        self.engine = create_engine(connection_string, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic commit/rollback.

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
