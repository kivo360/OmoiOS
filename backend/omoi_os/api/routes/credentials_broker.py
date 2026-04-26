"""Credential broker API routes for managing encrypted credentials.

Provides endpoints for:
- Creating credential bindings
- Listing credentials by workspace
- Getting credential metadata
- Deleting credentials

All routes are guarded by the broker_enabled feature flag.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    status,
)

from omoi_os.api.dependencies import get_auth_context_full, AuthContext
from omoi_os.config import is_feature_enabled
from omoi_os.logging import get_logger
from omoi_os.models.credential_binding import CredentialBinding
from omoi_os.services.credential_broker import (
    CredentialBrokerError,
    CredentialBrokerService,
    CredentialNotFoundError,
    InvalidBindingKindError,
    get_credential_broker_service,
)


def _require_platform_or_user(auth: AuthContext) -> None:
    """Reject sandbox session tokens; only platform keys / user JWTs allowed.

    `sess_tok_…` bearers are issued for in-sandbox broker calls and must
    never authenticate platform endpoints. The token classifier already
    routes them to the session verifier, but defense-in-depth requires
    every authenticated platform route to also explicitly reject them.
    """
    if auth.token_kind == "session":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="session tokens are not valid on platform endpoints",
        )


logger = get_logger(__name__)
router = APIRouter()


def check_feature_flag() -> None:
    """Check if credential broker feature is enabled.

    Raises:
        HTTPException: 404 if feature flag is disabled
    """
    if not is_feature_enabled("broker_enabled"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found",
        )


def get_service() -> CredentialBrokerService:
    """Get credential broker service instance."""
    return get_credential_broker_service()


# ============================================================================
# Request/Response Models
# ============================================================================

from pydantic import BaseModel, Field


class CreateCredentialRequest(BaseModel):
    """Request model for creating a credential binding."""

    workspace_id: UUID = Field(..., description="Workspace ID")
    kind: str = Field(
        ...,
        description="Binding kind: bearer_secret, user_oauth, or github_app",
    )
    name: str = Field(..., min_length=1, max_length=255, description="Credential name")
    value: str = Field(..., description="Credential value (will be encrypted)")
    config: Optional[dict] = Field(
        None,
        description="Additional configuration (e.g., OAuth scopes)",
    )


class CredentialResponse(BaseModel):
    """Response model for credential binding (without decrypted value)."""

    id: UUID
    workspace_id: UUID
    kind: str
    name: str
    config: dict
    version: int
    created_at: str
    rotated_at: Optional[str]

    @classmethod
    def from_model(cls, binding: CredentialBinding) -> "CredentialResponse":
        """Create response from model."""
        return cls(
            id=binding.id,
            workspace_id=binding.workspace_id,
            kind=binding.kind,
            name=binding.name,
            config=binding.config or {},
            version=binding.version,
            created_at=binding.created_at.isoformat() if binding.created_at else None,
            rotated_at=binding.rotated_at.isoformat() if binding.rotated_at else None,
        )


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_credential(
    request: CreateCredentialRequest = Body(...),
    auth: AuthContext = Depends(get_auth_context_full),
) -> CredentialResponse:
    """Create a new credential binding.

    Args:
        request: Credential creation request

    Returns:
        Created credential metadata with 201 status

    Raises:
        HTTPException: 404 if feature disabled, 400 if invalid kind,
                      500 if encryption fails
    """
    check_feature_flag()
    _require_platform_or_user(auth)

    try:
        service = get_service()
        binding = service.create_binding(
            workspace_id=request.workspace_id,
            kind=request.kind,
            name=request.name,
            value=request.value,
            config=request.config,
        )

        logger.info(
            "Credential created via API",
            binding_id=str(binding.id),
            workspace_id=str(request.workspace_id),
            kind=request.kind,
            name=request.name,
        )

        return CredentialResponse.from_model(binding)

    except HTTPException:
        raise
    except InvalidBindingKindError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except CredentialBrokerError as e:
        logger.error("Failed to create credential", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Failed to create credential", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create credential: {str(e)}",
        )


@router.get("")
async def list_credentials(
    workspace_id: UUID = Query(..., description="Workspace ID to filter by"),
    auth: AuthContext = Depends(get_auth_context_full),
) -> list[CredentialResponse]:
    """List credentials in a workspace.

    Args:
        workspace_id: Workspace ID to filter by

    Returns:
        Array of credential metadata (without decrypted values)

    Raises:
        HTTPException: 404 if feature disabled
    """
    check_feature_flag()
    _require_platform_or_user(auth)

    try:
        service = get_service()
        bindings = service.list_bindings(workspace_id=workspace_id)

        return [CredentialResponse.from_model(b) for b in bindings]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list credentials", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list credentials: {str(e)}",
        )


@router.get("/{binding_id}")
async def get_credential(
    binding_id: UUID,
    auth: AuthContext = Depends(get_auth_context_full),
) -> CredentialResponse:
    """Get a credential binding by ID.

    Args:
        binding_id: Credential binding ID

    Returns:
        Credential metadata (without decrypted value)

    Raises:
        HTTPException: 404 if feature disabled or credential not found
    """
    check_feature_flag()
    _require_platform_or_user(auth)

    try:
        service = get_service()
        binding = service.get_binding(binding_id=binding_id)

        return CredentialResponse.from_model(binding)

    except CredentialNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get credential", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get credential: {str(e)}",
        )


@router.delete("/{binding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    binding_id: UUID,
    auth: AuthContext = Depends(get_auth_context_full),
) -> None:
    """Delete a credential binding.

    Args:
        binding_id: Credential binding ID

    Returns:
        204 No Content on success

    Raises:
        HTTPException: 404 if feature disabled or credential not found
    """
    check_feature_flag()
    _require_platform_or_user(auth)

    try:
        service = get_service()
        service.delete_binding(binding_id=binding_id)

        logger.info(
            "Credential deleted via API",
            binding_id=str(binding_id),
        )

    except CredentialNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete credential", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete credential: {str(e)}",
        )
