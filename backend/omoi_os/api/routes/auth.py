"""Authentication API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from omoi_os.api.dependencies import get_db_session, get_current_user, get_auth_service
from omoi_os.models.user import User
from omoi_os.schemas.auth import (
    UserCreate,
    UserResponse,
    UserUpdate,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyWithSecret,
    ChangePasswordRequest,
)
from omoi_os.services.auth_service import AuthService

router = APIRouter()
security = HTTPBearer()


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    request: UserCreate,
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user account.

    Creates a new user with email/password authentication.
    User will need to verify email before full access.
    """
    try:
        user = await auth_service.register_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            department=request.department,
        )

        return UserResponse.model_validate(user)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate user and return JWT tokens.

    Returns access token (15min) and refresh token (7d).
    """
    user = await auth_service.authenticate_user(
        email=request.email, password=request.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Create tokens
    access_token = auth_service.create_access_token(user.id)
    refresh_token = auth_service.create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=auth_service.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Refresh access token using refresh token.

    Returns new access token and refresh token.
    """
    # Verify refresh token
    token_data = auth_service.verify_token(request.refresh_token, token_type="refresh")

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Verify user still exists and is active
    user = await auth_service.get_user_by_id(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    # Create new tokens
    access_token = auth_service.create_access_token(user.id)
    new_refresh_token = auth_service.create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=auth_service.access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Logout current user.

    Invalidates current session (if using session-based auth).
    For JWT, client should discard tokens.
    """
    # TODO: Track logout in audit log
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    request: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update current user profile."""
    from sqlalchemy import update
    from omoi_os.models.user import User as UserModel

    # Update user
    update_data = {}
    if request.full_name is not None:
        update_data["full_name"] = request.full_name
    if request.department is not None:
        update_data["department"] = request.department
    if request.attributes is not None:
        update_data["attributes"] = request.attributes

    if update_data:
        await db.execute(
            update(UserModel)
            .where(UserModel.id == current_user.id)
            .values(**update_data)
        )
        await db.commit()

        # Refresh user
        result = await db.execute(
            select(UserModel).where(UserModel.id == current_user.id)
        )
        user = result.scalar_one()
        return UserResponse.model_validate(user)

    return UserResponse.model_validate(current_user)


@router.post("/verify-email")
async def verify_email(
    request: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Verify user email using verification token."""
    success = await auth_service.verify_email(request.token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    return {"message": "Email verified successfully"}


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Request password reset.

    Sends reset token via email (email sending not implemented yet).
    """
    user = await auth_service.get_user_by_email(request.email)

    if user:
        # Generate reset token
        reset_token = auth_service.create_reset_token(user.id)

        # TODO: Send email with reset link
        # In production, this token should be sent via email, not returned
        # For development/testing, log the token (check server logs)
        import logging

        logging.getLogger(__name__).info(
            f"Password reset requested for {request.email}. "
            f"Token (DEV ONLY - remove in production): {reset_token}"
        )

    # Always return success to prevent email enumeration
    return {
        "message": "If an account with that email exists, a password reset link has been sent."
    }


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Reset password using reset token."""
    try:
        success = await auth_service.reset_password(request.token, request.new_password)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        return {"message": "Password reset successfully"}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Change password for authenticated user."""
    # Verify current password
    if not auth_service.verify_password(
        request.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password
    is_valid, error_msg = auth_service.validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    # Update password
    from sqlalchemy import update
    from omoi_os.models.user import User as UserModel

    await db.execute(
        update(UserModel)
        .where(UserModel.id == current_user.id)
        .values(hashed_password=auth_service.hash_password(request.new_password))
    )
    await db.commit()

    return {"message": "Password changed successfully"}


# API Key endpoints


@router.post(
    "/api-keys", response_model=APIKeyWithSecret, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    request: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Create API key for programmatic access.

    Returns the full key ONLY ONCE - save it securely!
    """
    api_key, full_key = await auth_service.create_api_key(
        user_id=current_user.id,
        name=request.name,
        scopes=request.scopes,
        organization_id=request.organization_id,
        expires_in_days=request.expires_in_days,
    )

    response = APIKeyWithSecret.model_validate(api_key)
    response.key = full_key  # Add full key to response

    return response


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List user's API keys."""
    from sqlalchemy import select
    from omoi_os.models.auth import APIKey

    result = await db.execute(select(APIKey).where(APIKey.user_id == current_user.id))
    api_keys = result.scalars().all()

    return [APIKeyResponse.model_validate(key) for key in api_keys]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Revoke an API key."""
    from uuid import UUID
    from sqlalchemy import select
    from omoi_os.models.auth import APIKey

    # Verify key belongs to user
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == UUID(key_id), APIKey.user_id == current_user.id
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    await auth_service.revoke_api_key(UUID(key_id))

    return {"message": "API key revoked successfully"}
