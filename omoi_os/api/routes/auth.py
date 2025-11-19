"""Authentication API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional

from omoi_os.api.dependencies import (
    get_supabase_auth_service,
    get_db_service,
)
from omoi_os.models.user import User
from omoi_os.services.supabase_auth import SupabaseAuthService
from omoi_os.services.database import DatabaseService

router = APIRouter()
security = HTTPBearer()


class SignUpRequest(BaseModel):
    """Request model for user signup."""

    email: EmailStr
    password: str
    name: Optional[str] = None


class SignInRequest(BaseModel):
    """Request model for user signin."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Response model for user."""

    id: str
    email: str
    name: Optional[str] = None
    role: str
    avatar_url: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


@router.post("/signup", response_model=UserResponse)
async def signup(
    request: SignUpRequest,
    supabase_auth: SupabaseAuthService = Depends(get_supabase_auth_service),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Create a new user account.

    Note: This endpoint uses Supabase admin API to create users.
    For production, consider using Supabase Auth directly from frontend.
    """
    # Create user via Supabase
    user_data = supabase_auth.create_user(
        email=request.email,
        password=request.password,
        user_metadata={"name": request.name} if request.name else None,
    )
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create user",
        )
    
    # Wait for trigger to replicate to public.users, then fetch
    import time
    time.sleep(0.5)  # Small delay for trigger to execute
    
    with db.get_session() as session:
        user = session.get(User, user_data["id"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User created but not found in database",
            )
        
        return UserResponse.model_validate(user)


@router.post("/signin", response_model=TokenResponse)
async def signin(
    request: SignInRequest,
    supabase_auth: SupabaseAuthService = Depends(get_supabase_auth_service),
):
    """
    Sign in user and return JWT token.

    Note: This endpoint uses Supabase client. For production,
    consider handling sign-in directly from frontend.
    """
    try:
        response = supabase_auth.client.auth.sign_in_with_password(
            {
                "email": request.email,
                "password": request.password,
            }
        )
        
        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        
        return TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            token_type="bearer",
            expires_in=response.session.expires_in,
            user={
                "id": response.user.id,
                "email": response.user.email,
                "user_metadata": response.user.user_metadata or {},
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        ) from e


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase_auth: SupabaseAuthService = Depends(get_supabase_auth_service),
    db: DatabaseService = Depends(get_db_service),
):
    """Get current authenticated user information."""
    from fastapi import HTTPException, status
    
    token = credentials.credentials
    
    # Verify JWT token
    user_info = supabase_auth.verify_jwt_token(token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Load user from public.users
    with db.get_session() as session:
        user = session.get(User, user_info["id"])
        if not user or user.deleted_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return UserResponse.model_validate(user)


@router.post("/signout")
async def signout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase_auth: SupabaseAuthService = Depends(get_supabase_auth_service),
):
    """Sign out current user."""
    # Supabase handles signout on client side
    # This endpoint is mainly for logging/auditing
    return {"message": "Signed out successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    supabase_auth: SupabaseAuthService = Depends(get_supabase_auth_service),
):
    """Refresh access token using refresh token."""
    try:
        response = supabase_auth.client.auth.refresh_session(refresh_token)
        
        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        
        return TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            token_type="bearer",
            expires_in=response.session.expires_in,
            user={
                "id": response.user.id,
                "email": response.user.email,
                "user_metadata": response.user.user_metadata or {},
            },
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

