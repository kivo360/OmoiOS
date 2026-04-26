"""Environment API routes for managing environments and versioned configs.

Provides endpoints for:
- Creating environments
- Listing environments by organization
- Getting environment with latest version
- Creating immutable versions with variables

All routes are guarded by the environments_v1 feature flag.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Query,
    status,
)

from omoi_os.config import is_feature_enabled
from omoi_os.logging import get_logger
from omoi_os.models.environment import Environment, EnvironmentVersion
from omoi_os.services.environment_service import (
    EnvironmentService,
    EnvironmentServiceError,
    InvalidVariableError,
    get_environment_service,
)

logger = get_logger(__name__)
router = APIRouter()


def check_feature_flag() -> None:
    """Check if environments feature is enabled.

    Raises:
        HTTPException: 404 if feature flag is disabled
    """
    if not is_feature_enabled("environments_v1"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Environments API not available",
        )


def get_service() -> EnvironmentService:
    """Get environment service instance."""
    return get_environment_service()


# ============================================================================
# Request/Response Models
# ============================================================================

from pydantic import BaseModel, Field


class CreateEnvironmentRequest(BaseModel):
    """Request model for creating an environment."""

    name: str = Field(..., min_length=1, max_length=255, description="Environment name")
    description: Optional[str] = Field(
        None, description="Optional environment description"
    )
    org_id: UUID = Field(..., description="Organization ID")


class CreateVersionRequest(BaseModel):
    """Request model for creating a version."""

    variables: dict[str, dict] = Field(
        ...,
        description="Variables dict: {name: {type: 'string|secret|json', value: '...'}}",
    )


class EnvironmentResponse(BaseModel):
    """Response model for environment metadata."""

    id: UUID
    org_id: UUID
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, env: Environment) -> "EnvironmentResponse":
        return cls(
            id=env.id,
            org_id=env.org_id,
            name=env.name,
            description=env.description,
            created_at=env.created_at.isoformat() if env.created_at else None,
            updated_at=env.updated_at.isoformat() if env.updated_at else None,
        )


class EnvironmentVersionResponse(BaseModel):
    """Response model for environment version."""

    id: UUID
    environment_id: UUID
    version_number: int
    variables: dict[str, dict]
    created_at: str

    @classmethod
    def from_model(
        cls,
        version: EnvironmentVersion,
        masked: bool = True,
    ) -> "EnvironmentVersionResponse":
        """Create response from model.

        Args:
            version: EnvironmentVersion model
            masked: If True, mask secret values as "***"
        """
        variables = version.variables or {}

        if masked:
            # Mask secret values
            service = get_service()
            variables = service.mask_secret_variables(variables)

        return cls(
            id=version.id,
            environment_id=version.environment_id,
            version_number=version.version_number,
            variables=variables,
            created_at=version.created_at.isoformat() if version.created_at else None,
        )


class EnvironmentWithVersionResponse(BaseModel):
    """Response model for environment with latest version."""

    environment: EnvironmentResponse
    latest_version: Optional[EnvironmentVersionResponse]


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_environment(
    request: CreateEnvironmentRequest = Body(...),
) -> EnvironmentResponse:
    """Create a new environment.

    Args:
        request: Environment creation request

    Returns:
        Created environment metadata with 201 status

    Raises:
        HTTPException: 404 if feature disabled, 400 if creation fails
    """
    check_feature_flag()

    try:
        service = get_service()
        environment = service.create_environment(
            org_id=request.org_id,
            name=request.name,
            description=request.description,
        )

        logger.info(
            "Environment created via API",
            environment_id=str(environment.id),
            org_id=str(request.org_id),
            name=request.name,
        )

        return EnvironmentResponse.from_model(environment)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create environment", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create environment: {str(e)}",
        )


@router.get("")
async def list_environments(
    org_id: UUID = Query(..., description="Organization ID to filter by"),
) -> list[EnvironmentResponse]:
    """List environments in an organization.

    Args:
        org_id: Organization ID to filter by

    Returns:
        Array of environment metadata

    Raises:
        HTTPException: 404 if feature disabled
    """
    check_feature_flag()

    try:
        service = get_service()
        environments = service.list_environments(org_id=org_id)

        return [EnvironmentResponse.from_model(env) for env in environments]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list environments", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list environments: {str(e)}",
        )


@router.get("/{env_id}")
async def get_environment(
    env_id: UUID,
) -> EnvironmentWithVersionResponse:
    """Get environment by ID with its latest version.

    Args:
        env_id: Environment ID

    Returns:
        Environment metadata with latest version (if any)

    Raises:
        HTTPException: 404 if feature disabled or environment not found
    """
    check_feature_flag()

    try:
        service = get_service()
        environment, latest_version = service.get_environment(env_id)

        return EnvironmentWithVersionResponse(
            environment=EnvironmentResponse.from_model(environment),
            latest_version=EnvironmentVersionResponse.from_model(latest_version)
            if latest_version
            else None,
        )

    except EnvironmentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get environment", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get environment: {str(e)}",
        )


@router.get("/{env_id}/versions/{version_number}")
async def get_version(
    env_id: UUID,
    version_number: int,
) -> EnvironmentVersionResponse:
    """Fetch a specific version of an environment by its sequential number.

    Spec rule: versions are immutable. This endpoint exists so callers
    (CLI rollback, audit logs, sandbox rehydration) can read v(N-1)
    without relying on the latest pointer.

    Raises:
        HTTPException: 404 if env or version doesn't exist.
    """
    check_feature_flag()
    try:
        service = get_service()
        version = service.get_version_by_number(env_id, version_number)
        return EnvironmentVersionResponse.from_model(version, masked=True)
    except EnvironmentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{env_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_version(
    env_id: UUID,
    request: CreateVersionRequest = Body(...),
) -> EnvironmentVersionResponse:
    """Create a new immutable version for an environment.

    Args:
        env_id: Environment ID
        request: Version creation request with variables

    Returns:
        Created version metadata with 201 status

    Raises:
        HTTPException: 404 if feature disabled or environment not found,
                      400 if variable structure is invalid
    """
    check_feature_flag()

    try:
        service = get_service()
        version = service.create_version(
            env_id=env_id,
            variables=request.variables,
        )

        logger.info(
            "Environment version created via API",
            version_id=str(version.id),
            environment_id=str(env_id),
            version_number=version.version_number,
        )

        return EnvironmentVersionResponse.from_model(version, masked=True)

    except EnvironmentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InvalidVariableError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create version", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create version: {str(e)}",
        )
