"""Artifact service with multi-backend storage abstraction.

Provides unified artifact storage with support for:
- Local filesystem backend (v1)
- S3 backend (interface only, v1)

All file operations use streaming to support large files without
loading entire content into memory.
"""

from __future__ import annotations

import abc
import hashlib
import os
from pathlib import Path
from typing import AsyncIterator, BinaryIO, Optional, Tuple
from uuid import UUID

from omoi_os.config import OmoiBaseSettings, get_app_settings
from omoi_os.logging import get_logger
from omoi_os.models.artifact import Artifact
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)

# Default chunk size for streaming (8MB)
DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024


class ArtifactSettings(OmoiBaseSettings):
    """Artifact storage configuration settings.

    Precedence: YAML defaults (config/base.yaml + config/<env>.yaml) < environment variables < init kwargs.
    """

    yaml_section = "artifacts"
    model_config = {"env_prefix": "ARTIFACTS_", "extra": "ignore"}

    # Local filesystem settings
    local_base_dir: str = "/tmp/omoios-artifacts"

    # S3 settings (v1 interface only)
    s3_bucket: Optional[str] = None
    s3_region: str = "us-east-1"
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None


def load_artifact_settings() -> ArtifactSettings:
    """Load artifact settings (cached)."""
    return get_app_settings().artifacts


class StorageBackend(abc.ABC):
    """Abstract base class for storage backends.

    Implementations must support streaming upload/download for large files.
    """

    @abc.abstractmethod
    async def upload(
        self,
        workspace_id: UUID,
        artifact_id: UUID,
        filename: str,
        stream: BinaryIO,
    ) -> Tuple[str, int, str]:
        """Upload a file to storage.

        Args:
            workspace_id: Workspace ID for path isolation
            artifact_id: Artifact ID for unique path
            filename: Original filename
            stream: Binary stream to upload

        Returns:
            Tuple of (storage_path, size_bytes, checksum_sha256)
        """
        ...

    @abc.abstractmethod
    async def download(self, path: str) -> AsyncIterator[bytes]:
        """Download a file from storage.

        Args:
            path: Storage path returned by upload()

        Yields:
            File content chunks
        """
        ...

    @abc.abstractmethod
    async def delete(self, path: str) -> None:
        """Delete a file from storage.

        Args:
            path: Storage path returned by upload()

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        ...


class LocalFilesystemBackend(StorageBackend):
    """Local filesystem storage backend.

    Stores files in a directory structure:
        {base_dir}/{workspace_id}/{artifact_id}/{safe_filename}

    Uses streaming for all operations to support large files.
    """

    def __init__(self, base_dir: str, chunk_size: int = DEFAULT_CHUNK_SIZE):
        """Initialize local filesystem backend.

        Args:
            base_dir: Base directory for artifact storage
            chunk_size: Chunk size for streaming operations
        """
        self.base_dir = Path(base_dir)
        self.chunk_size = chunk_size

        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _make_safe_filename(self, filename: str) -> str:
        """Create a safe filename by removing path separators.

        Args:
            filename: Original filename

        Returns:
            Safe filename for storage
        """
        # Remove path separators and null bytes
        safe = filename.replace("/", "_").replace("\\", "_").replace("\x00", "")
        # Limit length
        if len(safe) > 255:
            name, ext = os.path.splitext(safe)
            safe = name[: 255 - len(ext)] + ext
        return safe

    def _get_storage_path(
        self, workspace_id: UUID, artifact_id: UUID, filename: str
    ) -> Path:
        """Get the full storage path for an artifact.

        Args:
            workspace_id: Workspace ID
            artifact_id: Artifact ID
            filename: Original filename

        Returns:
            Full Path to store the file
        """
        safe_filename = self._make_safe_filename(filename)
        return self.base_dir / str(workspace_id) / str(artifact_id) / safe_filename

    async def upload(
        self,
        workspace_id: UUID,
        artifact_id: UUID,
        filename: str,
        stream: BinaryIO,
    ) -> Tuple[str, int, str]:
        """Upload file to local filesystem.

        Computes SHA-256 checksum incrementally during upload.
        """
        storage_path = self._get_storage_path(workspace_id, artifact_id, filename)

        # Ensure parent directories exist
        storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Stream write and compute checksum
        sha256_hash = hashlib.sha256()
        total_size = 0

        with open(storage_path, "wb") as f:
            while True:
                chunk = stream.read(self.chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                sha256_hash.update(chunk)
                total_size += len(chunk)

        # Return relative path from base_dir
        relative_path = str(storage_path.relative_to(self.base_dir))
        checksum = sha256_hash.hexdigest()

        logger.debug(
            "Uploaded artifact to local storage",
            workspace_id=str(workspace_id),
            artifact_id=str(artifact_id),
            path=relative_path,
            size=total_size,
        )

        return relative_path, total_size, checksum

    async def download(self, path: str) -> AsyncIterator[bytes]:
        """Download file from local filesystem in chunks."""
        full_path = self.base_dir / path

        if not full_path.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")

        with open(full_path, "rb") as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                yield chunk

    async def delete(self, path: str) -> None:
        """Delete file from local filesystem."""
        full_path = self.base_dir / path

        if not full_path.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")

        full_path.unlink()

        # Clean up empty parent directories
        try:
            parent = full_path.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
                grandparent = parent.parent
                if grandparent.exists() and not any(grandparent.iterdir()):
                    grandparent.rmdir()
        except OSError:
            # Ignore errors during cleanup
            pass

        logger.debug("Deleted artifact from local storage", path=path)


class S3Backend(StorageBackend):
    """S3 storage backend (interface only, v1).

    Full implementation deferred to future version.
    """

    async def upload(
        self,
        workspace_id: UUID,
        artifact_id: UUID,
        filename: str,
        stream: BinaryIO,
    ) -> Tuple[str, int, str]:
        """Upload file to S3 (not implemented in v1)."""
        raise NotImplementedError("S3 backend deferred to future version")

    async def download(self, path: str) -> AsyncIterator[bytes]:
        """Download file from S3 (not implemented in v1)."""
        raise NotImplementedError("S3 backend deferred to future version")

    async def delete(self, path: str) -> None:
        """Delete file from S3 (not implemented in v1)."""
        raise NotImplementedError("S3 backend deferred to future version")


class ArtifactService:
    """Service for managing artifact storage and retrieval.

    Provides unified interface for:
    - Uploading artifacts with streaming
    - Downloading artifacts with streaming
    - Deleting artifacts (file + metadata)
    - Listing artifacts by workspace

    Uses storage backend abstraction for pluggable storage.
    """

    def __init__(
        self,
        backend: StorageBackend,
        db: Optional[DatabaseService] = None,
    ):
        """Initialize artifact service.

        Args:
            backend: Storage backend implementation
            db: Database service (optional, for testing)
        """
        self.backend = backend
        self._db = db

    def _get_db(self) -> DatabaseService:
        """Get database service, initializing if needed."""
        if self._db is None:
            from omoi_os.services.database import DatabaseService

            settings = get_app_settings()
            self._db = DatabaseService(connection_string=settings.database.url)
        return self._db

    async def upload_artifact(
        self,
        workspace_id: UUID,
        name: str,
        content_type: Optional[str],
        stream: BinaryIO,
        artifact_metadata: Optional[dict] = None,
    ) -> Artifact:
        """Upload an artifact.

        Args:
            workspace_id: Workspace that owns the artifact
            name: Original filename
            content_type: MIME type (optional)
            stream: Binary stream to upload
            artifact_metadata: Custom metadata (optional)

        Returns:
            Artifact model with metadata
        """
        # Generate artifact ID
        artifact_id = UUID(int=0)  # Placeholder, will be set by DB

        # Upload to storage backend
        storage_path, size_bytes, checksum = await self.backend.upload(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            filename=name,
            stream=stream,
        )

        # Create database record
        db = self._get_db()
        with db.get_session() as session:
            artifact = Artifact(
                workspace_id=workspace_id,
                name=name,
                storage_backend="local",  # v1 only supports local
                storage_path=storage_path,
                checksum=checksum,
                size_bytes=size_bytes,
                content_type=content_type,
                artifact_metadata=artifact_metadata or {},
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(artifact)
            session.commit()
            session.refresh(artifact)

            logger.info(
                "Artifact uploaded",
                artifact_id=str(artifact.id),
                workspace_id=str(workspace_id),
                name=name,
                size=size_bytes,
            )

            session.expunge(artifact)
            return artifact

    async def download_artifact(self, artifact_id: UUID) -> AsyncIterator[bytes]:
        """Download an artifact's content.

        Args:
            artifact_id: ID of the artifact to download

        Yields:
            Content chunks

        Raises:
            FileNotFoundError: If artifact doesn't exist
        """
        # Get artifact metadata
        artifact = await self.get_artifact(artifact_id)
        if artifact is None:
            raise FileNotFoundError(f"Artifact not found: {artifact_id}")

        # Stream from storage backend
        async for chunk in self.backend.download(artifact.storage_path):
            yield chunk

    async def get_artifact(self, artifact_id: UUID) -> Optional[Artifact]:
        """Get artifact metadata by ID.

        Args:
            artifact_id: Artifact ID

        Returns:
            Artifact model or None if not found
        """
        db = self._get_db()
        with db.get_session() as session:
            artifact = (
                session.query(Artifact).filter(Artifact.id == artifact_id).first()
            )
            if artifact is not None:
                session.expunge(artifact)
            return artifact

    async def list_artifacts(
        self,
        workspace_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Artifact]:
        """List artifacts in a workspace.

        Args:
            workspace_id: Workspace ID to filter by
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            List of artifact models
        """
        db = self._get_db()
        with db.get_session() as session:
            artifacts = (
                session.query(Artifact)
                .filter(Artifact.workspace_id == workspace_id)
                .order_by(Artifact.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            for a in artifacts:
                session.expunge(a)
            return artifacts

    async def delete_artifact(self, artifact_id: UUID) -> None:
        """Delete an artifact (file + metadata).

        Args:
            artifact_id: ID of the artifact to delete

        Raises:
            FileNotFoundError: If artifact doesn't exist
        """
        db = self._get_db()
        with db.get_session() as session:
            artifact = (
                session.query(Artifact).filter(Artifact.id == artifact_id).first()
            )
            if artifact is None:
                raise FileNotFoundError(f"Artifact not found: {artifact_id}")

            storage_path = artifact.storage_path

            # Delete from storage
            await self.backend.delete(storage_path)

            # Delete from database
            session.delete(artifact)
            session.commit()

            logger.info(
                "Artifact deleted",
                artifact_id=str(artifact_id),
                workspace_id=str(artifact.workspace_id),
            )


# Global singleton instance
_artifact_service: Optional[ArtifactService] = None


def get_artifact_service() -> ArtifactService:
    """Get the global artifact service instance (singleton pattern).

    Returns:
        ArtifactService instance with configured backend
    """
    global _artifact_service

    if _artifact_service is None:
        settings = load_artifact_settings()
        backend = LocalFilesystemBackend(base_dir=settings.local_base_dir)
        _artifact_service = ArtifactService(backend=backend)

    return _artifact_service


def reset_artifact_service() -> None:
    """Reset the global artifact service instance.

    Useful for testing to ensure clean state between tests.
    """
    global _artifact_service
    _artifact_service = None
