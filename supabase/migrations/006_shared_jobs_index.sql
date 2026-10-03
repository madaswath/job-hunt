-- Shared jobs index for Demo 1 (cross-tenant catalogue; ranking remains per-user)

CREATE TABLE IF NOT EXISTS shared_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_connector text NOT NULL,
  external_id text,
  canonical_url text,
  content_hash text NOT NULL,
  title text NOT NULL,
  company text,
  location text,
  work_mode text,
  employment_type text,
  seniority text,
  description text,
  excerpt text,
  skills text[] NOT NULL DEFAULT '{}',
  must_have_skills text[] NOT NULL DEFAULT '{}',
  ctc_inr_annual_min numeric,
  ctc_inr_annual_max numeric,
  source_url text,
  apply_url text,
  extracted_emails text[] NOT NULL DEFAULT '{}',
  capture_kind text NOT NULL DEFAULT 'job_listing',
  raw_payload jsonb NOT NULL DEFAULT '{}',
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (content_hash)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_jobs_connector_ext
  ON shared_jobs (source_connector, external_id)
  WHERE external_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_shared_jobs_title ON shared_jobs (lower(title));
CREATE INDEX IF NOT EXISTS idx_shared_jobs_location ON shared_jobs (lower(coalesce(location, '')));
CREATE INDEX IF NOT EXISTS idx_shared_jobs_last_seen ON shared_jobs (last_seen_at DESC);

CREATE TABLE IF NOT EXISTS autopilot_schedules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  enabled boolean NOT NULL DEFAULT true,
  interval_hours integer NOT NULL DEFAULT 24,
  titles text[] NOT NULL DEFAULT '{}',
  cities text[] NOT NULL DEFAULT '{}',
  work_mode text,
  last_run_at timestamptz,
  next_run_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_autopilot_next ON autopilot_schedules (enabled, next_run_at)
  WHERE enabled = true;

ALTER TABLE shared_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE autopilot_schedules ENABLE ROW LEVEL SECURITY;

-- Service-role only (same pattern as other tables): deny anon/authenticated direct access
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'shared_jobs' AND policyname = 'shared_jobs_deny_all'
  ) THEN
    CREATE POLICY shared_jobs_deny_all ON shared_jobs FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'autopilot_schedules' AND policyname = 'autopilot_deny_all'
  ) THEN
    CREATE POLICY autopilot_deny_all ON autopilot_schedules FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
  END IF;
END $$;
