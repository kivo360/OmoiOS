-- Supabase Auth Integration: RLS Policies and Triggers
-- Run this SQL in Supabase SQL Editor after migration 025 completes
-- Project: ogqsxfcnpmcslmqfombp

-- ============================================================================
-- RLS POLICIES for public.users
-- ============================================================================

-- Policy: Users can view their own profile
DROP POLICY IF EXISTS "Users can view own profile" ON public.users;
CREATE POLICY "Users can view own profile"
    ON public.users
    FOR SELECT
    USING (auth.uid() = id);

-- Policy: Users can update their own profile
DROP POLICY IF EXISTS "Users can update own profile" ON public.users;
CREATE POLICY "Users can update own profile"
    ON public.users
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- Policy: Service role has full access
DROP POLICY IF EXISTS "Service role full access" ON public.users;
CREATE POLICY "Service role full access"
    ON public.users
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- ============================================================================
-- TRIGGERS on auth.users for replication to public.users
-- ============================================================================

-- Trigger: Replicate new/updated users from auth.users to public.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT OR UPDATE ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- Trigger: Mark users as deleted when removed from auth.users
DROP TRIGGER IF EXISTS on_auth_user_deleted ON auth.users;
CREATE TRIGGER on_auth_user_deleted
    AFTER DELETE ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_user_deleted();

-- ============================================================================
-- OPTIONAL: Backfill existing users from auth.users to public.users
-- ============================================================================
-- Uncomment and run this if you have existing users in auth.users that need
-- to be replicated to public.users

/*
INSERT INTO public.users (
    id, email, email_confirmed_at, phone, phone_confirmed_at,
    name, avatar_url, role,
    created_at, updated_at, last_sign_in_at, user_metadata
)
SELECT
    id,
    email,
    email_confirmed_at,
    phone,
    phone_confirmed_at,
    COALESCE(raw_user_meta_data->>'name', raw_user_meta_data->>'full_name') as name,
    raw_user_meta_data->>'avatar_url' as avatar_url,
    COALESCE(raw_user_meta_data->>'role', 'user') as role,
    created_at,
    updated_at,
    last_sign_in_at,
    COALESCE(raw_user_meta_data, '{}'::jsonb) as user_metadata
FROM auth.users
ON CONFLICT (id) DO UPDATE
SET
    email = EXCLUDED.email,
    email_confirmed_at = EXCLUDED.email_confirmed_at,
    phone = EXCLUDED.phone,
    phone_confirmed_at = EXCLUDED.phone_confirmed_at,
    name = EXCLUDED.name,
    avatar_url = EXCLUDED.avatar_url,
    role = EXCLUDED.role,
    updated_at = EXCLUDED.updated_at,
    last_sign_in_at = EXCLUDED.last_sign_in_at,
    user_metadata = EXCLUDED.user_metadata;
*/
