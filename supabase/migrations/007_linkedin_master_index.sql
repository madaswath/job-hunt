-- Enrich shared master index for LinkedIn scraper keyword batches

ALTER TABLE shared_jobs
  ADD COLUMN IF NOT EXISTS search_keyword text,
  ADD COLUMN IF NOT EXISTS posted_at timestamptz,
  ADD COLUMN IF NOT EXISTS preference_tags text[] NOT NULL DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_shared_jobs_keyword ON shared_jobs (lower(coalesce(search_keyword, '')));
CREATE INDEX IF NOT EXISTS idx_shared_jobs_posted_at ON shared_jobs (posted_at DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_shared_jobs_skills_gin ON shared_jobs USING gin (skills);
CREATE INDEX IF NOT EXISTS idx_shared_jobs_kind_keyword ON shared_jobs (capture_kind, search_keyword);

CREATE TABLE IF NOT EXISTS linkedin_master_ingest_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text REFERENCES app_users (user_id) ON DELETE SET NULL,
  export_dir text,
  keywords text[] NOT NULL DEFAULT '{}',
  jobs_upserted integer NOT NULL DEFAULT 0,
  posts_upserted integer NOT NULL DEFAULT 0,
  jobs_per_keyword integer NOT NULL DEFAULT 100,
  posts_limit integer NOT NULL DEFAULT 15,
  status text NOT NULL DEFAULT 'completed',
  summary jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_linkedin_master_runs_created ON linkedin_master_ingest_runs (created_at DESC);

ALTER TABLE linkedin_master_ingest_runs ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'linkedin_master_ingest_runs' AND policyname = 'linkedin_master_runs_deny_all'
  ) THEN
    CREATE POLICY linkedin_master_runs_deny_all ON linkedin_master_ingest_runs
      FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
  END IF;
END $$;
