from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def get_env_files():
    """Get environment files in priority order: .env.local, .env, then environment variables."""
    # Priority order: .env.local (highest), .env, environment variables
    env_files = []

    # Check for .env.local first (highest priority)
    if os.path.exists(".env.local"):
        env_files.append(".env.local")

    # Then .env
    if os.path.exists(".env"):
        env_files.append(".env")

    return env_files if env_files else None


class DBSettings(BaseSettings):
    """
    Database settings with environment file priority.

    Environment files priority: .env.local > .env > environment variables
    """

    model_config = SettingsConfigDict(
        env_file=get_env_files(),
        env_file_encoding="utf-8",
        env_prefix="DB_",
        extra="ignore",  # Ignore extra environment variables
    )

    host: str = "localhost"
    port: int = 15432  # Updated to match our non-standard port
    name: str = "omoi_os"  # Updated to match local database
    user: str = "postgres"
    password: str = "postgres"
    sslmode: Optional[str] = None  # e.g., "require"

    def url(self) -> str:
        base = f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        if self.sslmode:
            return f"{base}?sslmode={self.sslmode}"
        return base


_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        settings = DBSettings()
        _engine = create_engine(settings.url(), pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def get_session() -> Iterator[Session]:
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
