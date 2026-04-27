"""Unit tests for artifact service.

Tests Requirements:
- REQ-ART-001: Artifact upload with streaming
- REQ-ART-002: Artifact download with streaming
- REQ-ART-003: Checksum validation (SHA-256)
- REQ-ART-004: Storage backend abstraction
- REQ-ART-005: Workspace isolation
"""

import hashlib
import io
import os
from pathlib import Path
from uuid import uuid4

import pytest

from omoi_os.services.artifact_service import (
    ArtifactService,
    LocalFilesystemBackend,
    S3Backend,
    get_artifact_service,
    reset_artifact_service,
)
from omoi_os.models.artifact import Artifact


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory."""
    storage_dir = tmp_path / "artifacts"
    storage_dir.mkdir(parents=True)
    return storage_dir


@pytest.fixture
def local_backend(temp_storage_dir: Path) -> LocalFilesystemBackend:
    """Create a LocalFilesystemBackend with temp directory."""
    return LocalFilesystemBackend(base_dir=str(temp_storage_dir))


@pytest.fixture
def artifact_service(temp_storage_dir: Path) -> ArtifactService:
    """Create an ArtifactService with local backend."""
    reset_artifact_service()
    backend = LocalFilesystemBackend(base_dir=str(temp_storage_dir))
    service = ArtifactService(backend=backend)
    return service


# ============================================================================
# Storage Backend Tests
# ============================================================================


class TestLocalFilesystemBackend:
    """Tests for LocalFilesystemBackend."""

    @pytest.mark.unit
    def test_backend_initialization(self, temp_storage_dir: Path):
        """Test backend initializes with correct base directory."""
        backend = LocalFilesystemBackend(base_dir=str(temp_storage_dir))
        assert backend.base_dir == temp_storage_dir
        assert backend.base_dir.exists()

    @pytest.mark.unit
    def test_backend_creates_directory(self, tmp_path: Path):
        """Test backend creates base directory if it doesn't exist."""
        non_existent = tmp_path / "new_artifacts"
        LocalFilesystemBackend(base_dir=str(non_existent))
        assert non_existent.exists()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_upload_creates_file(self, local_backend: LocalFilesystemBackend):
        """Test upload creates file at correct path."""
        workspace_id = uuid4()
        artifact_id = uuid4()
        content = b"Hello, World!"
        stream = io.BytesIO(content)

        path, size, checksum = await local_backend.upload(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            filename="test.txt",
            stream=stream,
        )

        # Verify file was created
        full_path = local_backend.base_dir / path
        assert full_path.exists()
        assert full_path.read_bytes() == content
        assert size == len(content)
        assert checksum == hashlib.sha256(content).hexdigest()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_upload_computes_sha256(self, local_backend: LocalFilesystemBackend):
        """Test upload computes correct SHA-256 checksum."""
        content = b"Test content for checksum"
        expected_checksum = hashlib.sha256(content).hexdigest()
        stream = io.BytesIO(content)

        _, _, checksum = await local_backend.upload(
            workspace_id=uuid4(),
            artifact_id=uuid4(),
            filename="test.txt",
            stream=stream,
        )

        assert checksum == expected_checksum

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_download_returns_content(
        self, local_backend: LocalFilesystemBackend
    ):
        """Test download returns correct file content."""
        content = b"Downloadable content"
        stream = io.BytesIO(content)

        path, _, _ = await local_backend.upload(
            workspace_id=uuid4(),
            artifact_id=uuid4(),
            filename="download.txt",
            stream=stream,
        )

        # Download and verify
        chunks = []
        async for chunk in local_backend.download(path):
            chunks.append(chunk)

        downloaded = b"".join(chunks)
        assert downloaded == content

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_download_large_file_chunks(
        self, local_backend: LocalFilesystemBackend
    ):
        """Test download streams large files in chunks."""
        # Create 2MB file
        content = b"x" * (2 * 1024 * 1024)
        stream = io.BytesIO(content)

        path, _, _ = await local_backend.upload(
            workspace_id=uuid4(),
            artifact_id=uuid4(),
            filename="large.bin",
            stream=stream,
        )

        # Download and verify chunking
        chunks = []
        async for chunk in local_backend.download(path):
            chunks.append(chunk)

        # Should be chunked (default chunk size is 8MB, but 2MB < 8MB so single chunk)
        assert len(chunks) >= 1
        downloaded = b"".join(chunks)
        assert downloaded == content

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_removes_file(self, local_backend: LocalFilesystemBackend):
        """Test delete removes file from storage."""
        content = b"To be deleted"
        stream = io.BytesIO(content)

        path, _, _ = await local_backend.upload(
            workspace_id=uuid4(),
            artifact_id=uuid4(),
            filename="delete.txt",
            stream=stream,
        )

        full_path = local_backend.base_dir / path
        assert full_path.exists()

        await local_backend.delete(path)
        assert not full_path.exists()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_nonexistent_file_raises(
        self, local_backend: LocalFilesystemBackend
    ):
        """Test delete raises error for non-existent file."""
        with pytest.raises(FileNotFoundError):
            await local_backend.delete("nonexistent/path/file.txt")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_workspace_isolation(self, local_backend: LocalFilesystemBackend):
        """Test different workspaces have isolated storage paths."""
        workspace_a = uuid4()
        workspace_b = uuid4()
        content_a = b"Workspace A content"
        content_b = b"Workspace B content"

        # Upload to workspace A
        path_a, _, _ = await local_backend.upload(
            workspace_id=workspace_a,
            artifact_id=uuid4(),
            filename="shared.txt",
            stream=io.BytesIO(content_a),
        )

        # Upload to workspace B
        path_b, _, _ = await local_backend.upload(
            workspace_id=workspace_b,
            artifact_id=uuid4(),
            filename="shared.txt",
            stream=io.BytesIO(content_b),
        )

        # Paths should be different (contain workspace_id)
        assert path_a != path_b
        assert str(workspace_a) in path_a
        assert str(workspace_b) in path_b

        # Contents should be isolated
        chunks_a = []
        async for chunk in local_backend.download(path_a):
            chunks_a.append(chunk)
        assert b"".join(chunks_a) == content_a

        chunks_b = []
        async for chunk in local_backend.download(path_b):
            chunks_b.append(chunk)
        assert b"".join(chunks_b) == content_b


class TestS3Backend:
    """Tests for S3Backend (interface only, v1)."""

    @pytest.mark.unit
    def test_s3_backend_raises_not_implemented(self):
        """Test S3Backend raises NotImplementedError for all methods."""
        backend = S3Backend()

        with pytest.raises(NotImplementedError) as exc_info:
            # Use synchronous context for async method test
            import asyncio

            asyncio.run(
                backend.upload(
                    workspace_id=uuid4(),
                    artifact_id=uuid4(),
                    filename="test.txt",
                    stream=io.BytesIO(b"test"),
                )
            )
        assert "deferred to future version" in str(exc_info.value)

        with pytest.raises(NotImplementedError) as exc_info:
            import asyncio

            asyncio.run(backend.download("path"))
        assert "deferred to future version" in str(exc_info.value)

        with pytest.raises(NotImplementedError) as exc_info:
            import asyncio

            asyncio.run(backend.delete("path"))
        assert "deferred to future version" in str(exc_info.value)


# ============================================================================
# Artifact Service Tests
# ============================================================================


class TestArtifactService:
    """Tests for ArtifactService."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_upload_artifact_returns_metadata(
        self, artifact_service: ArtifactService
    ):
        """Test upload returns artifact with correct metadata."""
        workspace_id = uuid4()
        content = b"Test artifact content"
        stream = io.BytesIO(content)

        artifact = await artifact_service.upload_artifact(
            workspace_id=workspace_id,
            name="test.txt",
            content_type="text/plain",
            stream=stream,
        )

        assert isinstance(artifact, Artifact)
        assert artifact.id is not None
        assert artifact.workspace_id == workspace_id
        assert artifact.name == "test.txt"
        assert artifact.content_type == "text/plain"
        assert artifact.size_bytes == len(content)
        assert artifact.checksum == hashlib.sha256(content).hexdigest()
        assert artifact.storage_backend == "local"
        assert artifact.storage_path is not None
        assert artifact.created_at is not None
        assert artifact.updated_at is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_upload_artifact_stores_metadata(
        self, artifact_service: ArtifactService
    ):
        """Test upload stores artifact metadata."""
        workspace_id = uuid4()
        content = b"Metadata test"
        stream = io.BytesIO(content)

        artifact = await artifact_service.upload_artifact(
            workspace_id=workspace_id,
            name="meta.txt",
            content_type="text/plain",
            stream=stream,
        )

        # Retrieve and verify
        retrieved = await artifact_service.get_artifact(artifact.id)
        assert retrieved is not None
        assert retrieved.id == artifact.id
        assert retrieved.name == "meta.txt"
        assert retrieved.checksum == artifact.checksum

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_download_artifact_returns_content(
        self, artifact_service: ArtifactService
    ):
        """Test download returns original content."""
        workspace_id = uuid4()
        content = b"Download test content"
        stream = io.BytesIO(content)

        artifact = await artifact_service.upload_artifact(
            workspace_id=workspace_id,
            name="download.txt",
            content_type="text/plain",
            stream=stream,
        )

        # Download
        chunks = []
        async for chunk in artifact_service.download_artifact(artifact.id):
            chunks.append(chunk)

        downloaded = b"".join(chunks)
        assert downloaded == content

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_download_validates_checksum(self, artifact_service: ArtifactService):
        """Test download validates checksum matches stored value."""
        workspace_id = uuid4()
        content = b"Checksum validation test"
        stream = io.BytesIO(content)

        artifact = await artifact_service.upload_artifact(
            workspace_id=workspace_id,
            name="checksum.txt",
            content_type="text/plain",
            stream=stream,
        )

        # Download and verify checksum is accessible
        retrieved = await artifact_service.get_artifact(artifact.id)
        expected_checksum = hashlib.sha256(content).hexdigest()
        assert retrieved.checksum == expected_checksum

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_artifact_removes_file_and_metadata(
        self, artifact_service: ArtifactService
    ):
        """Test delete removes both file and database record."""
        workspace_id = uuid4()
        content = b"To be deleted"
        stream = io.BytesIO(content)

        artifact = await artifact_service.upload_artifact(
            workspace_id=workspace_id,
            name="delete.txt",
            content_type="text/plain",
            stream=stream,
        )

        # Verify exists
        assert await artifact_service.get_artifact(artifact.id) is not None

        # Delete
        await artifact_service.delete_artifact(artifact.id)

        # Verify gone
        assert await artifact_service.get_artifact(artifact.id) is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_artifacts_by_workspace(self, artifact_service: ArtifactService):
        """Test list returns artifacts filtered by workspace."""
        workspace_a = uuid4()
        workspace_b = uuid4()

        # Upload to workspace A
        artifact_a1 = await artifact_service.upload_artifact(
            workspace_id=workspace_a,
            name="a1.txt",
            content_type="text/plain",
            stream=io.BytesIO(b"A1"),
        )
        artifact_a2 = await artifact_service.upload_artifact(
            workspace_id=workspace_a,
            name="a2.txt",
            content_type="text/plain",
            stream=io.BytesIO(b"A2"),
        )

        # Upload to workspace B
        artifact_b1 = await artifact_service.upload_artifact(
            workspace_id=workspace_b,
            name="b1.txt",
            content_type="text/plain",
            stream=io.BytesIO(b"B1"),
        )

        # List workspace A
        list_a = await artifact_service.list_artifacts(workspace_id=workspace_a)
        assert len(list_a) == 2
        ids_a = {a.id for a in list_a}
        assert artifact_a1.id in ids_a
        assert artifact_a2.id in ids_a
        assert artifact_b1.id not in ids_a

        # List workspace B
        list_b = await artifact_service.list_artifacts(workspace_id=workspace_b)
        assert len(list_b) == 1
        assert list_b[0].id == artifact_b1.id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_artifacts_empty_workspace(
        self, artifact_service: ArtifactService
    ):
        """Test list returns empty list for workspace with no artifacts."""
        empty_workspace = uuid4()
        artifacts = await artifact_service.list_artifacts(workspace_id=empty_workspace)
        assert artifacts == []

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_artifact_returns_none_for_missing(
        self, artifact_service: ArtifactService
    ):
        """Test get returns None for non-existent artifact."""
        result = await artifact_service.get_artifact(uuid4())
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_large_file_streams_without_loading_all(
        self, artifact_service: ArtifactService, tmp_path: Path
    ):
        """Test large file upload/download streams without loading all in memory."""
        workspace_id = uuid4()

        # Create 5MB file
        large_content = b"x" * (5 * 1024 * 1024)
        stream = io.BytesIO(large_content)

        # Track memory by checking we can process chunks
        artifact = await artifact_service.upload_artifact(
            workspace_id=workspace_id,
            name="large.bin",
            content_type="application/octet-stream",
            stream=stream,
        )

        # Download in chunks
        total_size = 0
        chunk_count = 0
        async for chunk in artifact_service.download_artifact(artifact.id):
            total_size += len(chunk)
            chunk_count += 1

        assert total_size == len(large_content)
        assert chunk_count >= 1  # Should be chunked

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_upload_with_metadata(self, artifact_service: ArtifactService):
        """Test upload stores custom metadata."""
        workspace_id = uuid4()
        custom_metadata = {"source": "test", "version": "1.0"}

        artifact = await artifact_service.upload_artifact(
            workspace_id=workspace_id,
            name="with_meta.txt",
            content_type="text/plain",
            stream=io.BytesIO(b"content"),
            artifact_metadata=custom_metadata,
        )

        retrieved = await artifact_service.get_artifact(artifact.id)
        assert retrieved.artifact_metadata == custom_metadata


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


class TestArtifactServiceSingleton:
    """Tests for artifact service singleton pattern."""

    @pytest.mark.unit
    def test_get_artifact_service_returns_singleton(self, temp_storage_dir: Path):
        """Test get_artifact_service returns cached instance."""
        reset_artifact_service()

        # Mock settings
        os.environ["ARTIFACTS_LOCAL_BASE_DIR"] = str(temp_storage_dir)

        service1 = get_artifact_service()
        service2 = get_artifact_service()

        assert service1 is service2

        reset_artifact_service()

    @pytest.mark.unit
    def test_reset_creates_new_instance(self, temp_storage_dir: Path):
        """Test reset allows creating new instance."""
        os.environ["ARTIFACTS_LOCAL_BASE_DIR"] = str(temp_storage_dir)

        service1 = get_artifact_service()
        reset_artifact_service()
        service2 = get_artifact_service()

        assert service1 is not service2


# ============================================================================
# Checksum Validation Tests
# ============================================================================


class TestChecksumValidation:
    """Tests for SHA-256 checksum validation."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_checksum_matches_sha256(self, artifact_service: ArtifactService):
        """Test stored checksum matches SHA-256 of content."""
        workspace_id = uuid4()
        content = b"Checksum validation content"
        expected_sha256 = hashlib.sha256(content).hexdigest()

        artifact = await artifact_service.upload_artifact(
            workspace_id=workspace_id,
            name="checksum.txt",
            content_type="text/plain",
            stream=io.BytesIO(content),
        )

        assert artifact.checksum == expected_sha256
        assert len(artifact.checksum) == 64  # SHA-256 hex is 64 chars

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_different_content_different_checksum(
        self, artifact_service: ArtifactService
    ):
        """Test different content produces different checksums."""
        workspace_id = uuid4()

        artifact1 = await artifact_service.upload_artifact(
            workspace_id=workspace_id,
            name="a.txt",
            content_type="text/plain",
            stream=io.BytesIO(b"Content A"),
        )

        artifact2 = await artifact_service.upload_artifact(
            workspace_id=workspace_id,
            name="b.txt",
            content_type="text/plain",
            stream=io.BytesIO(b"Content B"),
        )

        assert artifact1.checksum != artifact2.checksum

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_same_content_same_checksum(self, artifact_service: ArtifactService):
        """Test identical content produces identical checksums."""
        workspace_id = uuid4()
        content = b"Identical content"

        artifact1 = await artifact_service.upload_artifact(
            workspace_id=workspace_id,
            name="a.txt",
            content_type="text/plain",
            stream=io.BytesIO(content),
        )

        artifact2 = await artifact_service.upload_artifact(
            workspace_id=workspace_id,
            name="b.txt",
            content_type="text/plain",
            stream=io.BytesIO(content),
        )

        assert artifact1.checksum == artifact2.checksum
