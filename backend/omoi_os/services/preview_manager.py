"""Preview Manager service for live preview lifecycle management.

Phase 1: Backend Preview Routes + DaytonaSpawner Integration.

Lightweight service that handles preview session CRUD operations
and publishes events when previews become ready.
"""

from typing import Optional

from sqlalchemy import select

from omoi_os.logging import get_logger
from omoi_os.models.preview_session import PreviewSession, PreviewStatus
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)


class PreviewManager:
    """Manages preview session lifecycle and event publishing.

    Usage:
        manager = PreviewManager(db=db_service, event_bus=event_bus_service)

        # Create a preview for a sandbox
        preview = await manager.create_preview(sandbox_id="sb-123", port=3000)

        # Mark as ready when dev server responds
        preview = await manager.mark_ready(preview.id, url="https://...", token="...")
    """

    def __init__(self, db: DatabaseService, event_bus: EventBusService):
        self.db = db
        self.event_bus = event_bus

    async def create_preview(
        self,
        sandbox_id: str,
        task_id: Optional[str] = None,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        port: int = 3000,
        framework: Optional[str] = None,
    ) -> PreviewSession:
        """Create a new preview session in PENDING status.

        Args:
            sandbox_id: Daytona sandbox ID (must be unique)
            task_id: Optional task that triggered this preview
            project_id: Optional project this preview belongs to
            user_id: Optional user who owns the preview
            port: Dev server port (default 3000)
            framework: Detected framework name

        Returns:
            Created PreviewSession

        Raises:
            ValueError: If a preview already exists for this sandbox
        """
        async with self.db.get_async_session() as session:
            # Check for existing preview on this sandbox
            result = await session.execute(
                select(PreviewSession).filter(PreviewSession.sandbox_id == sandbox_id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise ValueError(
                    f"Preview already exists for sandbox {sandbox_id}: {existing.id}"
                )

            preview = PreviewSession(
                sandbox_id=sandbox_id,
                task_id=task_id,
                project_id=project_id,
                user_id=user_id,
                port=port,
                framework=framework,
                status=PreviewStatus.PENDING.value,
            )
            session.add(preview)
            await session.commit()
            await session.refresh(preview)

            logger.info(
                "Preview session created",
                extra={
                    "preview_id": preview.id,
                    "sandbox_id": sandbox_id,
                    "task_id": task_id,
                    "port": port,
                    "framework": framework,
                },
            )
            return preview

    async def mark_starting(self, preview_id: str) -> PreviewSession:
        """Transition preview to STARTING status (dev server launching).

        Args:
            preview_id: Preview session ID

        Returns:
            Updated PreviewSession
        """
        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(PreviewSession).filter(PreviewSession.id == preview_id)
            )
            preview = result.scalar_one_or_none()
            if not preview:
                raise ValueError(f"Preview not found: {preview_id}")

            preview.status = PreviewStatus.STARTING.value
            preview.started_at = utc_now()
            await session.commit()
            await session.refresh(preview)

            logger.info(
                "Preview starting",
                extra={"preview_id": preview_id, "sandbox_id": preview.sandbox_id},
            )
            return preview

    async def mark_ready(
        self,
        preview_id: str,
        preview_url: str,
        preview_token: Optional[str] = None,
    ) -> PreviewSession:
        """Transition preview to READY status and publish PREVIEW_READY event.

        Args:
            preview_id: Preview session ID
            preview_url: Public Daytona preview URL
            preview_token: Optional auth token from get_preview_link()

        Returns:
            Updated PreviewSession
        """
        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(PreviewSession).filter(PreviewSession.id == preview_id)
            )
            preview = result.scalar_one_or_none()
            if not preview:
                raise ValueError(f"Preview not found: {preview_id}")

            preview.status = PreviewStatus.READY.value
            preview.preview_url = preview_url
            preview.preview_token = preview_token
            preview.ready_at = utc_now()
            await session.commit()
            await session.refresh(preview)

            # Publish PREVIEW_READY event for WebSocket broadcast
            self.event_bus.publish(
                SystemEvent(
                    event_type="PREVIEW_READY",
                    entity_type="preview_session",
                    entity_id=str(preview.id),
                    payload={
                        "preview_url": preview_url,
                        "sandbox_id": preview.sandbox_id,
                        "task_id": preview.task_id,
                        "port": preview.port,
                        "framework": preview.framework,
                    },
                )
            )

            logger.info(
                "Preview ready",
                extra={
                    "preview_id": preview_id,
                    "sandbox_id": preview.sandbox_id,
                    "preview_url": preview_url,
                },
            )
            return preview

    async def mark_failed(self, preview_id: str, error_message: str) -> PreviewSession:
        """Transition preview to FAILED status with error details.

        Args:
            preview_id: Preview session ID
            error_message: Description of why the preview failed

        Returns:
            Updated PreviewSession
        """
        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(PreviewSession).filter(PreviewSession.id == preview_id)
            )
            preview = result.scalar_one_or_none()
            if not preview:
                raise ValueError(f"Preview not found: {preview_id}")

            preview.status = PreviewStatus.FAILED.value
            preview.error_message = error_message
            await session.commit()
            await session.refresh(preview)

            logger.warning(
                "Preview failed",
                extra={
                    "preview_id": preview_id,
                    "sandbox_id": preview.sandbox_id,
                    "error": error_message,
                },
            )
            return preview

    async def mark_stopped(self, preview_id: str) -> PreviewSession:
        """Transition preview to STOPPED status.

        Args:
            preview_id: Preview session ID

        Returns:
            Updated PreviewSession
        """
        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(PreviewSession).filter(PreviewSession.id == preview_id)
            )
            preview = result.scalar_one_or_none()
            if not preview:
                raise ValueError(f"Preview not found: {preview_id}")

            preview.status = PreviewStatus.STOPPED.value
            preview.stopped_at = utc_now()
            await session.commit()
            await session.refresh(preview)

            logger.info(
                "Preview stopped",
                extra={"preview_id": preview_id, "sandbox_id": preview.sandbox_id},
            )
            return preview

    async def get_by_id(self, preview_id: str) -> Optional[PreviewSession]:
        """Get preview session by ID.

        Args:
            preview_id: Preview session ID

        Returns:
            PreviewSession or None
        """
        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(PreviewSession).filter(PreviewSession.id == preview_id)
            )
            return result.scalar_one_or_none()

    async def get_by_sandbox(self, sandbox_id: str) -> Optional[PreviewSession]:
        """Get preview session by sandbox ID.

        Args:
            sandbox_id: Daytona sandbox ID

        Returns:
            PreviewSession or None
        """
        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(PreviewSession).filter(PreviewSession.sandbox_id == sandbox_id)
            )
            return result.scalar_one_or_none()

    async def get_by_task(self, task_id: str) -> Optional[PreviewSession]:
        """Get preview session by task ID.

        Args:
            task_id: Task ID

        Returns:
            PreviewSession or None (returns most recent if multiple exist)
        """
        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(PreviewSession)
                .filter(PreviewSession.task_id == task_id)
                .order_by(PreviewSession.created_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
