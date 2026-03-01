-- Create useful extensions on first database init
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;

-- vchord is only available in tensorchord/vchord-suite images.
-- Attempt to create it but don't fail if unavailable.
DO $$
BEGIN
  CREATE EXTENSION IF NOT EXISTS vchord CASCADE;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'vchord extension not available, skipping (this is normal for pgvector images)';
END;
$$;
