"""Artifact API routes for unified artifact storage.

Provides endpoints for:
- Uploading artifacts (multipart/form-data)
- Listing artifacts by workspace
- Getting artifact metadata
- Downloading artifact content (streaming)
- Deleting artifacts

All routes are guarded by the artifacts_unified_v1 feature flag.
"""

from __future__ import annotations

from io import BytesIO
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from omoi_os.api.dependencies import get_auth_context_full, AuthContext
from omoi_os.config import is_feature_enabled
from omoi_os.logging import get_logger
from omoi_os.models.artifact import Artifact
from omoi_os.services.artifact_service import (
    ArtifactService,
    get_artifact_service,
)


def _require_platform_or_user(auth: AuthContext) -> None:
    """Sandbox session tokens must not authenticate platform endpoints."""
    if auth.token_kind == "session":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="session tokens are not valid on platform endpoints",
        )


logger = get_logger(__name__)
router = APIRouter()


def check_feature_flag() -> None:
    """Check if artifacts feature is enabled.

    Raises:
        HTTPException: 404 if feature flag is disabled
    """
    if not is_feature_enabled("artifacts_unified_v1"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifacts API not available",
        )


def get_service() -> ArtifactService:
    """Get artifact service instance."""
    return get_artifact_service()


# ============================================================================
# Request/Response Models
# ============================================================================


class ArtifactResponse:
    """Response model for artifact metadata."""

    def __init__(self, artifact: Artifact):
        self.id = artifact.id
        self.workspace_id = artifact.workspace_id
        self.name = artifact.name
        self.storage_backend = artifact.storage_backend
        self.checksum = artifact.checksum
        self.size_bytes = artifact.size_bytes
        self.content_type = artifact.content_type
        self.artifact_metadata = artifact.artifact_metadata
        self.created_at = artifact.created_at
        self.updated_at = artifact.updated_at

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "workspace_id": str(self.workspace_id),
            "name": self.name,
            "storage_backend": self.storage_backend,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "content_type": self.content_type,
            "artifact_metadata": self.artifact_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_artifact(
    workspace_id: UUID = Form(..., description="Workspace ID to store artifact in"),
    file: UploadFile = File(..., description="File to upload"),
    content_type: Optional[str] = Form(None, description="MIME type (optional)"),
    metadata: Optional[str] = Form(None, description="JSON metadata string (optional)"),
    auth: AuthContext = Depends(get_auth_context_full),
) -> dict:
    """Upload a new artifact.

    Args:
        workspace_id: Workspace to store the artifact in
        file: File to upload (multipart/form-data)
        content_type: MIME type override (optional, defaults to file.content_type)
        metadata: JSON string with custom metadata (optional)

    Returns:
        Artifact metadata with 201 status

    Raises:
        HTTPException: 404 if feature disabled, 400 if upload fails
    """
    check_feature_flag()
    _require_platform_or_user(auth)

    try:
        service = get_service()

        # Parse metadata JSON if provided
        artifact_metadata = None
        if metadata:
            import json

            try:
                artifact_metadata = json.loads(metadata)
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid metadata JSON: {e}",
                )

        # Use provided content_type or fall back to file's content_type
        final_content_type = content_type or file.content_type

        # Read file content into BytesIO for streaming
        content = await file.read()
        stream = BytesIO(content)

        # Upload artifact
        artifact = await service.upload_artifact(
            workspace_id=workspace_id,
            name=file.filename or "unnamed",
            content_type=final_content_type,
            stream=stream,
            artifact_metadata=artifact_metadata,
        )

        logger.info(
            "Artifact uploaded via API",
            artifact_id=str(artifact.id),
            workspace_id=str(workspace_id),
            filename=file.filename,
        )

        # Fire `artifact.uploaded` webhook if the subscriber feature is on.
        # Best-effort: never block the upload response on delivery.
        if is_feature_enabled("webhooks_enabled"):
            try:
                from sqlalchemy import select
                from omoi_os.config import get_app_settings
                from omoi_os.models.workspace import Workspace
                from omoi_os.services.database import DatabaseService
                from omoi_os.services.webhook_service import get_webhook_service

                settings = get_app_settings()
                db = DatabaseService(connection_string=settings.database.url)
                org_id = None
                with db.get_session() as s:
                    ws = s.execute(
                        select(Workspace).where(Workspace.id == workspace_id)
                    ).scalar_one_or_none()
                    if ws:
                        org_id = ws.organization_id

                if org_id is not None:
                    await get_webhook_service().trigger_event(
                        org_id=org_id,
                        event="artifact.uploaded",
                        payload_data={
                            "artifact_id": str(artifact.id),
                            "workspace_id": str(workspace_id),
                            "name": file.filename,
                            "content_type": final_content_type,
                        },
                    )
            except Exception as hook_exc:  # noqa: BLE001 — intentional best-effort
                logger.warning(
                    "artifact.uploaded webhook dispatch failed",
                    artifact_id=str(artifact.id),
                    error=str(hook_exc),
                )

        return ArtifactResponse(artifact).to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to upload artifact", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload failed: {str(e)}",
        )


@router.get("")
async def list_artifacts(
    workspace_id: UUID = Query(..., description="Workspace ID to filter by"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    auth: AuthContext = Depends(get_auth_context_full),
) -> list[dict]:
    """List artifacts in a workspace.

    Args:
        workspace_id: Workspace to list artifacts from
        limit: Maximum number of results (1-1000)
        offset: Number of results to skip

    Returns:
        Array of artifact metadata

    Raises:
        HTTPException: 404 if feature disabled
    """
    check_feature_flag()
    _require_platform_or_user(auth)

    try:
        service = get_service()
        artifacts = await service.list_artifacts(
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
        )

        return [ArtifactResponse(a).to_dict() for a in artifacts]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list artifacts", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list artifacts: {str(e)}",
        )


@router.get("/{artifact_id}")
async def get_artifact(
    artifact_id: UUID,
    auth: AuthContext = Depends(get_auth_context_full),
) -> dict:
    """Get artifact metadata by ID.

    Args:
        artifact_id: Artifact ID

    Returns:
        Artifact metadata

    Raises:
        HTTPException: 404 if feature disabled or artifact not found
    """
    check_feature_flag()
    _require_platform_or_user(auth)

    try:
        service = get_service()
        artifact = await service.get_artifact(artifact_id)

        if artifact is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact not found: {artifact_id}",
            )

        return ArtifactResponse(artifact).to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get artifact", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get artifact: {str(e)}",
        )


@router.get("/{artifact_id}/download")
async def download_artifact(
    artifact_id: UUID,
    auth: AuthContext = Depends(get_auth_context_full),
) -> StreamingResponse:
    """Download artifact content.

    Args:
        artifact_id: Artifact ID to download

    Returns:
        StreamingResponse with file content

    Raises:
        HTTPException: 404 if feature disabled or artifact not found
    """
    check_feature_flag()
    _require_platform_or_user(auth)

    try:
        service = get_service()

        # Get artifact metadata first
        artifact = await service.get_artifact(artifact_id)
        if artifact is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact not found: {artifact_id}",
            )

        # Stream download
        async def content_generator():
            async for chunk in service.download_artifact(artifact_id):
                yield chunk

        # Determine content type
        media_type = artifact.content_type or "application/octet-stream"

        return StreamingResponse(
            content_generator(),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{artifact.name}"',
                "X-Artifact-Checksum": artifact.checksum,
                "X-Artifact-Size": str(artifact.size_bytes),
            },
        )

    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact file not found: {artifact_id}",
        )
    except Exception as e:
        logger.error("Failed to download artifact", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download artifact: {str(e)}",
        )


@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(
    artifact_id: UUID,
    auth: AuthContext = Depends(get_auth_context_full),
) -> None:
    """Delete an artifact.

    Args:
        artifact_id: Artifact ID to delete

    Returns:
        204 No Content on success

    Raises:
        HTTPException: 404 if feature disabled or artifact not found
    """
    check_feature_flag()
    _require_platform_or_user(auth)

    try:
        service = get_service()
        await service.delete_artifact(artifact_id)

        logger.info("Artifact deleted via API", artifact_id=str(artifact_id))

    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact not found: {artifact_id}",
        )
    except Exception as e:
        logger.error("Failed to delete artifact", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete artifact: {str(e)}",
        )
