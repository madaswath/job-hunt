-- Shared catalogue and source registry (E3/E5).
-- Tenant-owned jobs/source_captures remain the current matching path.
-- catalogue_jobs is the shared vacancy store; matching materialization lands later.

CREATE TABLE source_definitions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id text NOT NULL UNIQUE,
  display_name text NOT NULL,
  source_type text NOT NULL,
  acquisition_mode text NOT NULL,
  implementation_status text NOT NULL,
  capability_label text NOT NULL,
  base_url text,
  schedule_cron text,
  refresh_interval_minutes integer,
  safe_concurrency integer NOT NULL DEFAULT 1,
  geographic_scope text[] NOT NULL DEFAULT '{}',
  job_title_scope text[] NOT NULL DEFAULT '{}',
  allowed_operations text[] NOT NULL DEFAULT '{}',
  forbidden_operations text[] NOT NULL DEFAULT '{submit_application,send_email,scrape_authenticated}',
  retention_days integer NOT NULL DEFAULT 30,
  terms_summary text NOT NULL DEFAULT '',
  enabled boolean NOT NULL DEFAULT false,
  quarantined boolean NOT NULL DEFAULT false,
  config jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE source_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id text NOT NULL REFERENCES source_definitions (source_id),
  trigger text NOT NULL DEFAULT 'schedule',
  actor_user_id text,
  idempotency_key text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'queued',
  cursor jsonb NOT NULL DEFAULT '{}',
  started_at timestamptz,
  finished_at timestamptz,
  heartbeat_at timestamptz,
  leased_by text,
  leased_until timestamptz,
  fetched integer NOT NULL DEFAULT 0,
  created_new integer NOT NULL DEFAULT 0,
  updated_count integer NOT NULL DEFAULT 0,
  unchanged integer NOT NULL DEFAULT 0,
  duplicated integer NOT NULL DEFAULT 0,
  closed integer NOT NULL DEFAULT 0,
  failed integer NOT NULL DEFAULT 0,
  last_error text,
  config_version text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_source_runs_source ON source_runs (source_id, created_at DESC);
CREATE INDEX idx_source_runs_claim ON source_runs (status, leased_until, created_at);

CREATE TABLE raw_captures (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id text NOT NULL REFERENCES source_definitions (source_id),
  source_run_id uuid REFERENCES source_runs (id) ON DELETE SET NULL,
  owner_user_id text,
  external_job_id text,
  source_url text,
  content_hash text NOT NULL,
  body jsonb NOT NULL DEFAULT '{}',
  captured_at timestamptz NOT NULL DEFAULT now(),
  acquisition_mode text NOT NULL,
  retention_until timestamptz NOT NULL,
  UNIQUE (source_id, content_hash, captured_at)
);
CREATE INDEX idx_raw_captures_source ON raw_captures (source_id, captured_at DESC);
CREATE INDEX idx_raw_captures_owner ON raw_captures (owner_user_id, captured_at DESC) WHERE owner_user_id IS NOT NULL;
CREATE INDEX idx_raw_captures_retention ON raw_captures (retention_until);

CREATE TABLE companies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_id text NOT NULL UNIQUE,
  display_name text NOT NULL,
  aliases text[] NOT NULL DEFAULT '{}',
  career_url text,
  country text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE catalogue_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_job_id text NOT NULL UNIQUE,
  company_id uuid REFERENCES companies (id),
  job_title text NOT NULL,
  normalized_title text,
  designation_family text,
  seniority text,
  employment_type text,
  department text,
  location_raw text,
  city text,
  state text,
  country text,
  work_mode text,
  remote_eligible boolean,
  posted_at timestamptz,
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  last_verified_at timestamptz,
  expires_at timestamptz,
  description_raw text,
  description_clean text,
  apply_url text,
  source_url text,
  content_hash text,
  status text NOT NULL DEFAULT 'active',
  closed_at timestamptz,
  inactive_until timestamptz,
  duplicate_of uuid REFERENCES catalogue_jobs (id),
  quality_score numeric,
  field_completeness numeric,
  quarantine_reason text,
  parser_version text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_catalogue_jobs_status ON catalogue_jobs (status, last_seen_at DESC);
CREATE INDEX idx_catalogue_jobs_company ON catalogue_jobs (company_id, status);
CREATE INDEX idx_catalogue_jobs_geo ON catalogue_jobs (country, city);

CREATE TABLE job_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  catalogue_job_id uuid NOT NULL REFERENCES catalogue_jobs (id) ON DELETE CASCADE,
  raw_capture_id uuid REFERENCES raw_captures (id) ON DELETE SET NULL,
  content_hash text NOT NULL,
  parser_version text,
  description_raw text,
  captured_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (catalogue_job_id, content_hash)
);

CREATE TABLE job_sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  catalogue_job_id uuid NOT NULL REFERENCES catalogue_jobs (id) ON DELETE CASCADE,
  source_id text NOT NULL REFERENCES source_definitions (source_id),
  external_job_id text,
  source_url text,
  apply_url text,
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_id, external_job_id)
);
CREATE INDEX idx_job_sources_job ON job_sources (catalogue_job_id);

CREATE TABLE job_liveness (
  catalogue_job_id uuid PRIMARY KEY REFERENCES catalogue_jobs (id) ON DELETE CASCADE,
  state text NOT NULL DEFAULT 'unknown',
  last_verified_at timestamptz,
  evidence text,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE job_matches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  catalogue_job_id uuid NOT NULL REFERENCES catalogue_jobs (id) ON DELETE CASCADE,
  score numeric NOT NULL,
  confidence numeric NOT NULL,
  ranking_version text NOT NULL DEFAULT 'match_v2',
  feature_breakdown jsonb NOT NULL DEFAULT '{}',
  passed_hard_filters boolean NOT NULL DEFAULT true,
  hard_filter_reasons text[] NOT NULL DEFAULT '{}',
  computed_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, catalogue_job_id, ranking_version)
);
CREATE INDEX idx_job_matches_user ON job_matches (user_id, score DESC, computed_at DESC);

INSERT INTO source_definitions (
  source_id, display_name, source_type, acquisition_mode, implementation_status, capability_label,
  base_url, refresh_interval_minutes, allowed_operations, enabled, terms_summary, geographic_scope
) VALUES
  (
    'greenhouse', 'Greenhouse public job board', 'public_ats', 'public_job_board_api', 'planned', 'planned',
    'https://boards-api.greenhouse.io/v1/boards', 60, '{ingest,normalize,health}', false,
    'Public Job Board API. Adapter ships in Sprint 1–2.', '{IN}'
  ),
  (
    'lever', 'Lever postings API', 'public_ats', 'public_postings_api', 'planned', 'planned',
    'https://api.lever.co/v0/postings', 60, '{ingest,normalize,health}', false,
    'Lever Postings API. Adapter ships in Sprint 1–2.', '{IN}'
  ),
  (
    'ashby', 'Ashby public job postings', 'public_ats', 'public_job_posting_api', 'planned', 'planned',
    'https://api.ashbyhq.com/posting-api/job-board', 60, '{ingest,normalize,health}', false,
    'Ashby public Job Postings API. Adapter ships in Sprint 1–2.', '{IN}'
  ),
  (
    'public_ats_fixture', 'Public ATS fixtures', 'public_ats', 'offline_fixture', 'live', 'live',
    NULL, NULL, '{ingest,normalize,health}', true,
    'Offline fixtures until live adapters are scheduled.', '{IN}'
  )
ON CONFLICT (source_id) DO NOTHING;

DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'source_definitions','source_runs','raw_captures','companies',
    'catalogue_jobs','job_versions','job_sources','job_liveness','job_matches'
  ]
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS deny_direct ON %I', t);
    EXECUTE format('CREATE POLICY deny_direct ON %I FOR ALL TO PUBLIC USING (false) WITH CHECK (false)', t);
  END LOOP;
END $$;
