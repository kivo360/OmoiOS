"""Authentication API routes."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from omoi_os.api.dependencies import get_db_session, get_current_user, get_auth_service
from omoi_os.logging import get_logger
from omoi_os.services.email_service import get_email_service

logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)
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
@limiter.limit("3/hour")
async def register(
    request: Request,
    body: UserCreate,
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user account.

    Creates a new user with email/password authentication.
    User will need to verify email before full access.
    """
    try:
        # Build waitlist metadata
        waitlist_metadata = None
        if body.referral_source:
            waitlist_metadata = {"referral_source": body.referral_source}

        user = await auth_service.register_user(
            email=body.email,
            password=body.password,
            full_name=body.full_name,
            department=body.department,
            waitlist_metadata=waitlist_metadata,
        )

        # Send verification email
        email_service = get_email_service()
        if email_service.enabled:
            verification_token, _vt_jti = auth_service.create_verification_token(
                user.id
            )
            await email_service.send_verification_email(
                to_email=user.email,
                token=verification_token,
                user_name=user.full_name,
            )

        return UserResponse.model_validate(user)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/resend-verification")
@limiter.limit("3/hour")
async def resend_verification(
    request: Request,
    body: ForgotPasswordRequest,  # Reuse - just needs email
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Resend verification email."""
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == body.email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal if email exists
        return {"message": "If an account exists, a verification email has been sent."}

    if user.is_verified:
        return {"message": "Email is already verified."}

    # Send verification email
    email_service = get_email_service()
    if email_service.enabled:
        verification_token, _vt_jti = auth_service.create_verification_token(user.id)
        await email_service.send_verification_email(
            to_email=user.email,
            token=verification_token,
            user_name=user.full_name,
        )

    return {"message": "If an account exists, a verification email has been sent."}


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate user and return JWT tokens.

    Returns access token (15min) and refresh token (7d).
    Includes account lockout after too many failed attempts.
    """
    client_ip = request.client.host if request.client else None

    # Check account lockout
    try:
        from omoi_os.services.token_blacklist import get_token_blacklist
        from omoi_os.config import get_app_settings

        blacklist = get_token_blacklist()
        auth_settings = get_app_settings().auth
        if await blacklist.is_locked_out(
            body.email, max_attempts=auth_settings.max_login_attempts
        ):
            await blacklist.log_auth_event(
                "login_blocked_lockout",
                email=body.email,
                ip_address=client_ip,
                details=f"Account locked after {auth_settings.max_login_attempts} failed attempts",
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account temporarily locked due to too many failed login attempts. Please try again later.",
            )
    except RuntimeError:
        blacklist = None  # Service not initialized (e.g., tests)

    user = await auth_service.authenticate_user(
        email=body.email, password=body.password
    )

    if not user:
        # Record failed attempt
        if blacklist:
            failed_count = await blacklist.record_failed_login(
                body.email,
                window_seconds=auth_settings.login_attempt_window_minutes * 60
                if hasattr(auth_settings, "login_attempt_window_minutes")
                else 900,
            )
            await blacklist.log_auth_event(
                "login_failed",
                email=body.email,
                ip_address=client_ip,
                details=f"Failed attempt #{failed_count}",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Extract user ID before session might close (prevent detached instance error)
    user_id = user.id

    # Clear failed login counter on success
    if blacklist:
        await blacklist.clear_failed_logins(body.email)
        await blacklist.log_auth_event(
            "login_success",
            user_id=str(user_id),
            email=body.email,
            ip_address=client_ip,
        )

    # Create tokens (tuple unpacking: token, jti)
    access_token, _access_jti = auth_service.create_access_token(user_id)
    refresh_token, _refresh_jti = auth_service.create_refresh_token(user_id)

    # Set httpOnly cookies for browser clients
    from fastapi.responses import JSONResponse
    from omoi_os.api.cookie_auth import set_auth_cookies

    response_data = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=auth_service.access_token_expire_minutes * 60,
    )
    response = JSONResponse(content=response_data.model_dump())
    set_auth_cookies(response, access_token, refresh_token)
    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    body: Optional[RefreshTokenRequest] = None,
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Refresh access token using refresh token.

    Accepts refresh token from request body OR httpOnly cookie.
    Implements token rotation: old refresh token is blacklisted,
    new access + refresh token pair is issued.
    """
    # Get refresh token from body or cookie
    refresh_token_value = None
    if body and body.refresh_token:
        refresh_token_value = body.refresh_token
    if not refresh_token_value:
        from omoi_os.api.cookie_auth import get_refresh_token_from_request

        refresh_token_value = get_refresh_token_from_request(request)
    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token"
        )

    # Verify refresh token
    token_data = auth_service.verify_token(refresh_token_value, token_type="refresh")

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Check if this refresh token has been blacklisted (already rotated)
    try:
        from omoi_os.services.token_blacklist import get_token_blacklist

        blacklist = get_token_blacklist()
        if token_data.jti and await blacklist.is_blacklisted(token_data.jti):
            # Potential token reuse attack — blacklist ALL user tokens
            await blacklist.blacklist_all_user_tokens(str(token_data.user_id))
            await blacklist.log_auth_event(
                "refresh_token_reuse",
                user_id=str(token_data.user_id),
                details="Possible token theft: reused refresh token detected",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please log in again.",
            )
    except RuntimeError:
        blacklist = None

    # Verify user still exists and is active
    user = await auth_service.get_user_by_id(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    # Extract user ID before session might close (prevent detached instance error)
    user_id = user.id

    # Blacklist the old refresh token (rotation)
    if blacklist and token_data.jti:
        refresh_ttl = auth_service.refresh_token_expire_days * 86400
        await blacklist.blacklist_token(token_data.jti, ttl_seconds=refresh_ttl)
        await blacklist.log_auth_event(
            "token_refresh", user_id=str(user_id), details="Refresh token rotated"
        )

    # Create new tokens (tuple unpacking)
    access_token, _access_jti = auth_service.create_access_token(user_id)
    new_refresh_token, _refresh_jti = auth_service.create_refresh_token(user_id)

    # Return tokens in body and set httpOnly cookies
    from fastapi.responses import JSONResponse
    from omoi_os.api.cookie_auth import set_auth_cookies

    response_data = TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=auth_service.access_token_expire_minutes * 60,
    )
    response = JSONResponse(content=response_data.model_dump())
    set_auth_cookies(response, access_token, new_refresh_token)
    return response


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
):
    """
    Logout current user.

    Blacklists the current access token so it cannot be reused.
    """
    client_ip = request.client.host if request.client else None

    try:
        from omoi_os.services.token_blacklist import get_token_blacklist

        blacklist = get_token_blacklist()

        # Extract JTI from the current token
        from omoi_os.services.auth_service import AuthService
        from omoi_os.config import settings

        auth_svc = AuthService(
            db=None,  # type: ignore  # Not needed for verify_token
            jwt_secret=settings.jwt_secret_key,
            jwt_algorithm=settings.jwt_algorithm,
        )
        if credentials:
            token_data = auth_svc.verify_token(
                credentials.credentials, token_type="access"
            )
            if token_data and token_data.jti:
                # Blacklist for remaining token lifetime (access token = 15min max)
                access_ttl = settings.access_token_expire_minutes * 60
                await blacklist.blacklist_token(token_data.jti, ttl_seconds=access_ttl)

        await blacklist.log_auth_event(
            "logout", user_id=str(current_user.id), ip_address=client_ip
        )
    except RuntimeError:
        pass  # Blacklist service not initialized

    from fastapi.responses import JSONResponse
    from omoi_os.api.cookie_auth import clear_auth_cookies

    response = JSONResponse(content={"message": "Logged out successfully"})
    clear_auth_cookies(response)
    return response


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
@limiter.limit("10/hour")
async def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Verify user email using verification token."""
    # Check if verification token has already been used (single-use)
    token_data = auth_service.verify_token(body.token, token_type="verification")
    if token_data and token_data.jti:
        try:
            from omoi_os.services.token_blacklist import get_token_blacklist

            blacklist = get_token_blacklist()
            if await blacklist.is_blacklisted(token_data.jti):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This verification link has already been used",
                )
        except RuntimeError:
            pass

    success = await auth_service.verify_email(body.token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    # Blacklist the verification token so it can't be reused
    if token_data and token_data.jti:
        try:
            from omoi_os.services.token_blacklist import get_token_blacklist

            blacklist = get_token_blacklist()
            await blacklist.blacklist_token(token_data.jti, ttl_seconds=86400)  # 24h
            await blacklist.log_auth_event(
                "email_verified",
                user_id=str(token_data.user_id),
                ip_address=request.client.host if request.client else None,
            )
        except RuntimeError:
            pass

    return {"message": "Email verified successfully"}


@router.post("/forgot-password")
@limiter.limit("3/hour")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Request password reset.

    Sends reset token via email (email sending not implemented yet).
    """
    # Validate email format before DB lookup to avoid unnecessary queries.
    # Return the same success message on invalid format to prevent enumeration.
    from email_validator import validate_email, EmailNotValidError

    try:
        validate_email(body.email, check_deliverability=False)
    except EmailNotValidError:
        return {
            "message": "If an account with that email exists, a password reset link has been sent."
        }

    user = await auth_service.get_user_by_email(body.email)

    if user:
        # Extract user ID before session might close (prevent detached instance error)
        user_id = user.id

        # Generate reset token
        reset_token, _reset_jti = auth_service.create_reset_token(user_id)

        # TODO: Send email with reset link
        # In production, this token should be sent via email, not returned
        # For development/testing, log the token (check server logs)
        logger.info(f"Password reset requested for {body.email}")

    # Always return success to prevent email enumeration
    return {
        "message": "If an account with that email exists, a password reset link has been sent."
    }


@router.post("/reset-password")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Reset password using reset token. Token is single-use."""
    # Check if reset token has already been used
    token_data = auth_service.verify_token(body.token, token_type="reset")
    if token_data and token_data.jti:
        try:
            from omoi_os.services.token_blacklist import get_token_blacklist

            blacklist = get_token_blacklist()
            if await blacklist.is_blacklisted(token_data.jti):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This password reset link has already been used",
                )
        except RuntimeError:
            blacklist = None
    else:
        blacklist = None

    try:
        success = await auth_service.reset_password(body.token, body.new_password)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        # Blacklist the reset token (single-use) and all user tokens (password changed)
        if blacklist and token_data:
            if token_data.jti:
                await blacklist.blacklist_token(token_data.jti, ttl_seconds=86400)
            await blacklist.blacklist_all_user_tokens(str(token_data.user_id))
            await blacklist.log_auth_event(
                "password_reset",
                user_id=str(token_data.user_id),
                ip_address=request.client.host if request.client else None,
            )

        return {"message": "Password reset successfully"}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/change-password")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Change password for authenticated user. Invalidates all existing tokens."""
    # Verify current password
    if not auth_service.verify_password(
        body.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password
    is_valid, error_msg = auth_service.validate_password_strength(body.new_password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    # Update password
    from sqlalchemy import update
    from omoi_os.models.user import User as UserModel

    await db.execute(
        update(UserModel)
        .where(UserModel.id == current_user.id)
        .values(hashed_password=auth_service.hash_password(body.new_password))
    )
    await db.commit()

    # Blacklist all existing tokens for this user (force re-login)
    try:
        from omoi_os.services.token_blacklist import get_token_blacklist

        blacklist = get_token_blacklist()
        await blacklist.blacklist_all_user_tokens(str(current_user.id))
        await blacklist.log_auth_event(
            "password_change",
            user_id=str(current_user.id),
            ip_address=request.client.host if request.client else None,
        )
    except RuntimeError:
        pass  # Blacklist service not initialized

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
    If organization_id is provided, validates the user owns or is a member of that org.
    """
    organization_id = None
    if request.organization_id:
        from omoi_os.models.organization import Organization, OrganizationMembership

        # Verify user is owner or member of the requested organization
        is_owner = await db.execute(
            select(Organization.id).where(
                Organization.id == request.organization_id,
                Organization.owner_id == current_user.id,
            )
        )
        is_member = await db.execute(
            select(OrganizationMembership.id).where(
                OrganizationMembership.organization_id == request.organization_id,
                OrganizationMembership.user_id == current_user.id,
            )
        )
        if not is_owner.scalar_one_or_none() and not is_member.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this organization",
            )
        organization_id = request.organization_id

    api_key, full_key = await auth_service.create_api_key(
        user_id=current_user.id,
        name=request.name,
        scopes=request.scopes,
        organization_id=organization_id,
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


# Waitlist management endpoints (admin only)


@router.get("/waitlist")
async def list_waitlist_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    status_filter: str = "pending",
    limit: int = 100,
    offset: int = 0,
):
    """
    List users on the waitlist.

    Only super admins can access this endpoint.
    """
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can manage the waitlist",
        )

    from sqlalchemy import func

    # Get users with matching waitlist status
    query = (
        select(User)
        .where(
            User.waitlist_status == status_filter,
            User.deleted_at.is_(None),
        )
        .order_by(User.created_at.asc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    users = result.scalars().all()

    # Get total count
    count_query = select(func.count(User.id)).where(
        User.waitlist_status == status_filter,
        User.deleted_at.is_(None),
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return {
        "users": [UserResponse.model_validate(u) for u in users],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/waitlist/{user_id}/approve")
async def approve_waitlist_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Approve a user from the waitlist.

    Only super admins can access this endpoint.
    """
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can manage the waitlist",
        )

    from sqlalchemy import update
    from uuid import UUID as PyUUID

    # Update the user's waitlist status
    result = await db.execute(
        update(User)
        .where(User.id == PyUUID(user_id), User.deleted_at.is_(None))
        .values(waitlist_status="approved")
        .returning(User)
    )
    await db.commit()

    updated_user = result.scalar_one_or_none()
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    logger.info(f"User {user_id} approved from waitlist by {current_user.id}")

    return {
        "message": "User approved",
        "user": UserResponse.model_validate(updated_user),
    }


@router.post("/waitlist/approve-all")
async def approve_all_waitlist_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Approve all pending waitlist users.

    Only super admins can access this endpoint.
    Use this when launching or opening the waitlist.
    """
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can manage the waitlist",
        )

    from sqlalchemy import update, func

    # Count before update
    count_result = await db.execute(
        select(func.count(User.id)).where(
            User.waitlist_status == "pending",
            User.deleted_at.is_(None),
        )
    )
    count = count_result.scalar()

    # Update all pending users
    await db.execute(
        update(User)
        .where(User.waitlist_status == "pending", User.deleted_at.is_(None))
        .values(waitlist_status="approved")
    )
    await db.commit()

    logger.info(f"Approved {count} waitlist users by {current_user.id}")

    return {"message": f"Approved {count} users from waitlist", "count": count}
