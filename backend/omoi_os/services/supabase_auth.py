"""Supabase authentication service."""

from typing import Optional
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from omoi_os.config import SupabaseSettings, load_supabase_settings


class SupabaseAuthService:
    """Service for Supabase authentication and user management."""

    def __init__(self, settings: Optional[SupabaseSettings] = None):
        """
        Initialize Supabase client.

        Args:
            settings: Optional Supabase settings (defaults to loading from env)
        """
        self.settings = settings or load_supabase_settings()
        
        # Client for admin operations (uses service role key)
        self.admin_client: Client = create_client(
            self.settings.url,
            self.settings.service_role_key,
            options=ClientOptions(
                auto_refresh_token=False,
                persist_session=False,
            ),
        )
        
        # Client for user operations (uses anon key)
        # This is typically used on the frontend, but available here for server-side user ops
        self.client: Client = create_client(
            self.settings.url,
            self.settings.anon_key,
        )

    def verify_jwt_token(self, token: str) -> Optional[dict]:
        """
        Verify JWT token and return user info.

        Args:
            token: JWT token from Authorization header

        Returns:
            User info dict if valid, None otherwise
        """
        try:
            # Use admin client to verify token
            response = self.admin_client.auth.get_user(token)
            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "user_metadata": response.user.user_metadata or {},
                }
        except Exception:
            return None
        
        return None

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """
        Get user by ID using admin client.

        Args:
            user_id: User UUID

        Returns:
            User dict or None
        """
        try:
            response = self.admin_client.auth.admin.get_user_by_id(user_id)
            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "user_metadata": response.user.user_metadata or {},
                    "created_at": response.user.created_at,
                    "last_sign_in_at": response.user.last_sign_in_at,
                }
        except Exception:
            return None
        
        return None

    def create_user(
        self,
        email: str,
        password: str,
        user_metadata: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        Create user via admin API.

        Args:
            email: User email
            password: User password
            user_metadata: Optional user metadata

        Returns:
            Created user dict or None
        """
        try:
            response = self.admin_client.auth.admin.create_user(
                {
                    "email": email,
                    "password": password,
                    "email_confirm": True,  # Auto-confirm email
                    "user_metadata": user_metadata or {},
                }
            )
            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "user_metadata": response.user.user_metadata or {},
                }
        except Exception:
            return None
        
        return None

