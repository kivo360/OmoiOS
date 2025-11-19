"""Add Supabase auth integration: user replication and triggers.

Revision ID: 025_supabase_auth_integration
Revises: 024_add_tsvector_for_hybrid_search
Create Date: 2025-01-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = "025_supabase_auth_integration"
down_revision: Union[str, None] = "024_add_tsvector_for_hybrid_search"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # Create public.users table
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("email_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("phone_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="user"),
        sa.Column("user_metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sign_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Note: Foreign key to auth.users.id is not included because:
        # 1. The auth schema is managed by Supabase and may not be accessible via pooler
        # 2. The trigger handles the relationship and ensures data integrity
        # 3. Application-level validation can enforce the relationship
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_role", "users", ["role"])
    op.create_index("idx_users_deleted_at", "users", ["deleted_at"])

    # Create replication function
    op.execute("""
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO public.users (
                id, email, email_confirmed_at, phone, phone_confirmed_at,
                created_at, updated_at, last_sign_in_at, user_metadata
            )
            VALUES (
                NEW.id,
                NEW.email,
                NEW.email_confirmed_at,
                NEW.phone,
                NEW.phone_confirmed_at,
                NEW.created_at,
                NEW.updated_at,
                NEW.last_sign_in_at,
                COALESCE(NEW.raw_user_meta_data, '{}'::jsonb)
            )
            ON CONFLICT (id) DO UPDATE
            SET
                email = EXCLUDED.email,
                email_confirmed_at = EXCLUDED.email_confirmed_at,
                phone = EXCLUDED.phone,
                phone_confirmed_at = EXCLUDED.phone_confirmed_at,
                updated_at = EXCLUDED.updated_at,
                last_sign_in_at = EXCLUDED.last_sign_in_at,
                user_metadata = EXCLUDED.user_metadata;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    # Create deletion function
    op.execute("""
        CREATE OR REPLACE FUNCTION public.handle_user_deleted()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE public.users
            SET deleted_at = NOW()
            WHERE id = OLD.id;
            
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    # Enable RLS
    op.execute("ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;")

    # Note: RLS policies must be created manually via Supabase SQL Editor
    # The auth schema is not accessible in Alembic's migration context,
    # even with search_path configuration. This appears to be a Supabase-specific
    # limitation where the migration connection cannot see the auth schema.
    #
    # Run these SQL commands in Supabase SQL Editor after the migration completes:
    #
    # CREATE POLICY "Users can view own profile"
    #     ON public.users
    #     FOR SELECT
    #     USING (auth.uid() = id);
    #
    # CREATE POLICY "Users can update own profile"
    #     ON public.users
    #     FOR UPDATE
    #     USING (auth.uid() = id)
    #     WITH CHECK (auth.uid() = id);
    #
    # CREATE POLICY "Service role full access"
    #     ON public.users
    #     FOR ALL
    #     USING (auth.jwt()->>'role' = 'service_role');

    # Note: Triggers on auth.users and backfill must be created manually
    # via Supabase SQL Editor because:
    # 1. The auth schema may not be accessible via the pooler connection
    # 2. Requires direct database connection or Supabase dashboard access
    #
    # To complete the setup, run these SQL commands in Supabase SQL Editor:
    #
    # CREATE TRIGGER on_auth_user_created
    #     AFTER INSERT OR UPDATE ON auth.users
    #     FOR EACH ROW
    #     EXECUTE FUNCTION public.handle_new_user();
    #
    # CREATE TRIGGER on_auth_user_deleted
    #     AFTER DELETE ON auth.users
    #     FOR EACH ROW
    #     EXECUTE FUNCTION public.handle_user_deleted();
    #
    # -- Optional: Backfill existing users
    # INSERT INTO public.users (
    #     id, email, email_confirmed_at, phone, phone_confirmed_at,
    #     created_at, updated_at, last_sign_in_at, user_metadata
    # )
    # SELECT
    #     id, email, email_confirmed_at, phone, phone_confirmed_at,
    #     created_at, updated_at, last_sign_in_at,
    #     COALESCE(raw_user_meta_data, '{}'::jsonb)
    # FROM auth.users
    # ON CONFLICT (id) DO NOTHING;


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;")
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_deleted ON auth.users;")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS public.handle_new_user();")
    op.execute("DROP FUNCTION IF EXISTS public.handle_user_deleted();")

    # Drop RLS policies
    op.execute('DROP POLICY IF EXISTS "Users can view own profile" ON public.users;')
    op.execute('DROP POLICY IF EXISTS "Users can update own profile" ON public.users;')
    op.execute('DROP POLICY IF EXISTS "Service role full access" ON public.users;')

    # Drop table
    op.drop_table("users")
