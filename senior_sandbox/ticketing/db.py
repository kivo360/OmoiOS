from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class DBSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env",), env_file_encoding="utf-8", env_prefix="DB_")

    host: str = "localhost"
    port: int = 5432
    name: str = "hephaestus"
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


