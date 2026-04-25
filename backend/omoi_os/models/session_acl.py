"""Session ACL + fork lineage models.

Per spec §07 (multiplayer ACL) and §03 (fork from seq). Backed by the
`session_acls` and `session_forks` tables created in migration 070.

Note the naming: `task_id` references `tasks.id` (stringified UUID), matching
the convention that `sessions` is the API surface and `tasks` is the DB-level
row — see backend/omoi_os/api/routes/sessions.py.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class SessionACL(Base):
    """A per-session access grant. Role is owner | editor | viewer."""

    __tablename__ = "session_acls"
    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="uq_session_acls_task_user"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    task_id: Mapped[str] = mapped_column(
        String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class SessionFork(Base):
    """Traces a forked session back to its parent at a specific seq."""

    __tablename__ = "session_forks"
    __table_args__ = (UniqueConstraint("child_task_id", name="uq_session_forks_child"),)

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    parent_task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    child_task_id: Mapped[str] = mapped_column(
        String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    from_seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
