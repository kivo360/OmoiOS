"""Authentication service for user management and token generation."""

from datetime import timedelta
from typing import Optional, Tuple
from uuid import UUID, uuid4
import re
import secrets
import hashlib

import bcrypt
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, update
from pydantic import BaseModel

from omoi_os.models.user import User
from omoi_os.models.auth import Session, APIKey
from omoi_os.utils.datetime import utc_now


def _hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


class TokenData(BaseModel):
    user_id: UUID
    token_type: str
    jti: Optional[str] = None
    iat: Optional[float] = None


class AuthService:
    """Service for authentication operations."""

    def __init__(
        self,
        db: AsyncSession,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
    ):
        self.db = db
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    # Password operations
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return _hash_password(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return _verify_password(plain_password, hashed_password)

    def validate_password_strength(self, password: str) -> Tuple[bool, Optional[str]]:
        if len(password) < 8:
            return False, "Password must be at least 8 characters"

        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"

        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"

        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"

        if not re.search(r'[!@#$%^&*(),.?":{}|<>\[\]\\~`_+\-=/;\']', password):
            return False, "Password must contain at least one special character"

        # Reject extremely common passwords (case-insensitive)
        common = {
            "password",
            "12345678",
            "123456789",
            "1234567890",
            "qwerty123",
            "password1",
            "password123",
            "iloveyou1",
            "admin123",
            "welcome1",
            "letmein1",
            "monkey123",
            "master123",
            "dragon123",
            "login123",
            "abc12345",
            "qwerty12",
            "trustno1",
            "baseball1",
            "shadow123",
        }
        if password.lower() in common:
            return False, "This password is too common. Please choose a stronger one."

        return True, None

    def create_access_token(
        self, user_id: UUID, expires_delta: Optional[timedelta] = None
    ) -> Tuple[str, str]:
        """Create JWT access token. Returns (token, jti)."""
        if expires_delta:
            expire = utc_now() + expires_delta
        else:
            expire = utc_now() + timedelta(minutes=self.access_token_expire_minutes)

        jti = str(uuid4())
        payload = {
            "sub": str(user_id),
            "exp": expire.timestamp(),
            "iat": utc_now().timestamp(),
            "type": "access",
            "jti": jti,
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token, jti

    def create_refresh_token(
        self, user_id: UUID, expires_delta: Optional[timedelta] = None
    ) -> Tuple[str, str]:
        """Create JWT refresh token. Returns (token, jti)."""
        if expires_delta:
            expire = utc_now() + expires_delta
        else:
            expire = utc_now() + timedelta(days=self.refresh_token_expire_days)

        jti = str(uuid4())
        payload = {
            "sub": str(user_id),
            "exp": expire.timestamp(),
            "iat": utc_now().timestamp(),
            "type": "refresh",
            "jti": jti,
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token, jti

    def verify_token(
        self, token: str, token_type: str = "access"
    ) -> Optional[TokenData]:
        try:
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )

            user_id = UUID(payload.get("sub"))
            payload_type = payload.get("type")

            if payload_type != token_type:
                return None

            return TokenData(
                user_id=user_id,
                token_type=payload_type,
                jti=payload.get("jti"),
                iat=payload.get("iat"),
            )

        except (JWTError, ValueError, KeyError):
            return None

    # User operations
    async def register_user(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        department: Optional[str] = None,
        waitlist_metadata: Optional[dict] = None,
    ) -> User:
        """
        Register a new user.

        New users are added to the waitlist by default (waitlist_status='pending').

        Args:
            email: User email
            password: User password
            full_name: Optional full name
            department: Optional department
            waitlist_metadata: Optional metadata (referral_source, etc.)

        Raises:
            ValueError: If email already exists or password is weak
        """
        # Check if user exists
        result = await self.db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")

        # Validate password
        is_valid, error_msg = self.validate_password_strength(password)
        if not is_valid:
            raise ValueError(error_msg)

        # Create user - directly approved (no waitlist)
        user = User(
            email=email,
            hashed_password=self.hash_password(password),
            full_name=full_name,
            department=department,
            is_verified=False,
            is_active=True,
            is_super_admin=False,
            waitlist_status="approved",  # Direct access, no waitlist
            waitlist_metadata=waitlist_metadata,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user by email and password.

        Returns:
            User if authenticated, None if invalid credentials
        """
        result = await self.db.execute(
            select(User).where(
                User.email == email, User.is_active.is_(True), User.deleted_at.is_(None)
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        if not user.hashed_password:
            return None

        if not self.verify_password(password, user.hashed_password):
            return None

        # Update last login
        await self.db.execute(
            update(User).where(User.id == user.id).values(last_login_at=utc_now())
        )
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(
                User.id == user_id, User.is_active.is_(True), User.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    # Session operations
    async def create_session(
        self,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Session:
        """Create a new session for user."""
        # Generate session token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Create session
        expires_at = utc_now() + timedelta(days=self.refresh_token_expire_days)

        session = Session(
            user_id=user_id,
            token_hash=token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def verify_session_token(self, token: str) -> Optional[User]:
        """Verify session token and return user."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        result = await self.db.execute(
            select(Session)
            .where(Session.token_hash == token_hash, Session.expires_at > utc_now())
            .join(User)
            .where(User.is_active.is_(True), User.deleted_at.is_(None))
        )
        session = result.scalar_one_or_none()

        if not session:
            return None

        # Get user
        user_result = await self.db.execute(
            select(User).where(User.id == session.user_id)
        )
        return user_result.scalar_one_or_none()

    async def invalidate_session(self, session_id: UUID):
        """Invalidate a session."""
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()

        if session:
            await self.db.delete(session)
            await self.db.commit()

    async def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        await self.db.execute(delete(Session).where(Session.expires_at <= utc_now()))
        # Delete expired sessions from the database
        await self.db.commit()

    # API Key operations
    def generate_api_key(self) -> Tuple[str, str, str]:
        """
        Generate API key.

        Returns:
            Tuple of (full_key, prefix, hashed_key)
        """
        random_part = secrets.token_urlsafe(32)
        full_key = f"sk_live_{random_part}"
        prefix = full_key[:16]
        hashed_key = hashlib.sha256(full_key.encode()).hexdigest()

        return full_key, prefix, hashed_key

    async def create_api_key(
        self,
        user_id: UUID,
        name: str,
        scopes: Optional[list[str]] = None,
        organization_id: Optional[UUID] = None,
        expires_in_days: Optional[int] = None,
    ) -> Tuple[APIKey, str]:
        """
        Create API key for user.

        Returns:
            Tuple of (APIKey object, full_key_string)

        Note: Full key is returned only once!
        """
        full_key, prefix, hashed_key = self.generate_api_key()

        expires_at = None
        if expires_in_days:
            expires_at = utc_now() + timedelta(days=expires_in_days)

        api_key = APIKey(
            user_id=user_id,
            organization_id=organization_id,
            name=name,
            key_prefix=prefix,
            hashed_key=hashed_key,
            scopes=scopes or [],
            is_active=True,
            expires_at=expires_at,
        )

        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)

        return api_key, full_key

    async def verify_api_key(self, key: str) -> Optional[Tuple[User, APIKey]]:
        """
        Verify API key and return associated user.

        Returns:
            Tuple of (User, APIKey) if valid, None if invalid
        """
        hashed_key = hashlib.sha256(key.encode()).hexdigest()

        result = await self.db.execute(
            select(APIKey)
            .where(APIKey.hashed_key == hashed_key, APIKey.is_active.is_(True))
            .where((APIKey.expires_at.is_(None)) | (APIKey.expires_at > utc_now()))
        )
        api_key = result.scalar_one_or_none()

        if not api_key or not api_key.user_id:
            return None

        # Get user
        user_result = await self.db.execute(
            select(User).where(
                User.id == api_key.user_id,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return None

        # Update last_used_at
        await self.db.execute(
            update(APIKey).where(APIKey.id == api_key.id).values(last_used_at=utc_now())
        )
        await self.db.commit()

        return user, api_key

    async def revoke_api_key(self, key_id: UUID):
        """Revoke an API key."""
        await self.db.execute(
            update(APIKey).where(APIKey.id == key_id).values(is_active=False)
        )
        await self.db.commit()

    # Email verification
    def create_verification_token(self, user_id: UUID) -> Tuple[str, str]:
        """Create email verification token. Returns (token, jti)."""
        expire = utc_now() + timedelta(hours=24)

        jti = str(uuid4())
        payload = {
            "sub": str(user_id),
            "exp": expire.timestamp(),
            "type": "email_verification",
            "jti": jti,
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token, jti

    async def verify_email(self, token: str) -> bool:
        """
        Verify email using verification token.

        Returns:
            True if successful, False if invalid
        """
        token_data = self.verify_token(token, token_type="email_verification")
        if not token_data:
            return False

        # Mark user as verified
        await self.db.execute(
            update(User).where(User.id == token_data.user_id).values(is_verified=True)
        )
        await self.db.commit()

        return True

    # Password reset
    def create_reset_token(self, user_id: UUID) -> Tuple[str, str]:
        """Create password reset token. Returns (token, jti)."""
        expire = utc_now() + timedelta(hours=1)

        jti = str(uuid4())
        payload = {
            "sub": str(user_id),
            "exp": expire.timestamp(),
            "type": "password_reset",
            "jti": jti,
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token, jti

    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset password using reset token.

        Returns:
            True if successful, False if invalid
        """
        token_data = self.verify_token(token, token_type="password_reset")
        if not token_data:
            return False

        # Validate new password
        is_valid, error_msg = self.validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(error_msg)

        # Update password
        await self.db.execute(
            update(User)
            .where(User.id == token_data.user_id)
            .values(hashed_password=self.hash_password(new_password))
        )
        await self.db.commit()

        # Invalidate all sessions for security
        await self.db.execute(
            delete(Session).where(Session.user_id == token_data.user_id)
        )
        await self.db.commit()

        return True
