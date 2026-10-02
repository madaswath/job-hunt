-- Job-hunt canonical schema + RLS (deny anon/authenticated; service-role API path)

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE app_users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL UNIQUE,
  clerk_user_id text NOT NULL UNIQUE,
  email text,
  display_name text,
  deletion_requested_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE candidate_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL UNIQUE REFERENCES app_users (user_id) ON DELETE CASCADE,
  full_name text,
  email text,
  phone text,
  headline text,
  skills text[] NOT NULL DEFAULT '{}',
  target_titles text[] NOT NULL DEFAULT '{}',
  title_aliases text[] NOT NULL DEFAULT '{}',
  preferred_cities text[] NOT NULL DEFAULT '{}',
  work_mode text NOT NULL DEFAULT 'hybrid',
  current_ctc_inr_annual numeric,
  expected_ctc_inr_annual numeric,
  min_ctc_inr_annual numeric,
  notice_period_days integer,
  joining_date date,
  employment_types text[] NOT NULL DEFAULT '{full-time}',
  company_preference text NOT NULL DEFAULT 'either',
  deal_breakers text[] NOT NULL DEFAULT '{}',
  banned_companies text[] NOT NULL DEFAULT '{}',
  banned_roles text[] NOT NULL DEFAULT '{}',
  years_experience numeric,
  seniority text,
  us_market_opt_in boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_candidate_profiles_user ON candidate_profiles (user_id);

CREATE TABLE verified_facts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  kind text NOT NULL,
  value text NOT NULL,
  source text NOT NULL DEFAULT 'manual',
  verified boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_verified_facts_user ON verified_facts (user_id, kind);

CREATE TABLE resumes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  title text NOT NULL,
  storage_path text,
  is_base boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_resumes_user ON resumes (user_id, is_base);

CREATE TABLE resume_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  resume_id uuid NOT NULL REFERENCES resumes (id) ON DELETE CASCADE,
  version integer NOT NULL,
  storage_path text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (resume_id, version)
);
CREATE INDEX idx_resume_versions_user ON resume_versions (user_id, resume_id);

CREATE TABLE source_accounts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  connector_id text NOT NULL,
  status text NOT NULL DEFAULT 'disconnected',
  scopes text[] NOT NULL DEFAULT '{}',
  token_ciphertext text,
  kek_id text,
  consent_at timestamptz,
  revoked_at timestamptz,
  last_refresh_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, connector_id)
);
CREATE INDEX idx_source_accounts_user ON source_accounts (user_id, connector_id);

CREATE TABLE source_policies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  connector_id text NOT NULL,
  allowed_operations text[] NOT NULL DEFAULT '{}',
  forbidden_operations text[] NOT NULL DEFAULT '{}',
  retention_days integer NOT NULL DEFAULT 90,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, connector_id)
);
CREATE INDEX idx_source_policies_user ON source_policies (user_id, connector_id);

CREATE TABLE source_captures (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  connector_id text NOT NULL,
  capture_kind text NOT NULL,
  external_id text,
  source_url text,
  canonical_url text,
  company text,
  title text,
  location text,
  excerpt text,
  raw_payload jsonb NOT NULL DEFAULT '{}',
  content_hash text NOT NULL,
  author text,
  extracted_emails text[] NOT NULL DEFAULT '{}',
  extracted_apply_urls text[] NOT NULL DEFAULT '{}',
  capture_method text NOT NULL DEFAULT 'fixture',
  captured_at timestamptz NOT NULL DEFAULT now(),
  idempotency_key text NOT NULL,
  UNIQUE (user_id, idempotency_key)
);
CREATE INDEX idx_source_captures_user ON source_captures (user_id, captured_at DESC);
CREATE INDEX idx_source_captures_hash ON source_captures (user_id, content_hash);
CREATE INDEX idx_source_captures_ext ON source_captures (user_id, connector_id, external_id);

CREATE TABLE jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  capture_id uuid NOT NULL REFERENCES source_captures (id) ON DELETE CASCADE,
  title text NOT NULL,
  company text,
  location text,
  work_mode text,
  employment_type text,
  seniority text,
  description text,
  skills text[] NOT NULL DEFAULT '{}',
  ctc_inr_annual_min numeric,
  ctc_inr_annual_max numeric,
  notice_period_days integer,
  source_url text,
  apply_url text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_jobs_user ON jobs (user_id, created_at DESC);

CREATE TABLE hiring_posts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  capture_id uuid NOT NULL REFERENCES source_captures (id) ON DELETE CASCADE,
  title text,
  company text,
  author text,
  excerpt text,
  source_url text NOT NULL,
  extracted_emails text[] NOT NULL DEFAULT '{}',
  extracted_apply_urls text[] NOT NULL DEFAULT '{}',
  captured_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_hiring_posts_user ON hiring_posts (user_id, captured_at DESC);

CREATE TABLE match_decisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  capture_id uuid NOT NULL REFERENCES source_captures (id) ON DELETE CASCADE,
  job_id uuid REFERENCES jobs (id) ON DELETE SET NULL,
  hiring_post_id uuid REFERENCES hiring_posts (id) ON DELETE SET NULL,
  passed_hard_filters boolean NOT NULL,
  hard_filter_reasons text[] NOT NULL DEFAULT '{}',
  overall_score numeric NOT NULL,
  confidence numeric NOT NULL,
  breakdown jsonb NOT NULL DEFAULT '{}',
  matched_skills text[] NOT NULL DEFAULT '{}',
  missing_skills text[] NOT NULL DEFAULT '{}',
  unknown_inputs text[] NOT NULL DEFAULT '{}',
  reasons_to_apply text[] NOT NULL DEFAULT '{}',
  risks text[] NOT NULL DEFAULT '{}',
  freshness_hours numeric,
  evidence_ids uuid[] NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_match_decisions_user ON match_decisions (user_id, created_at DESC);

CREATE TABLE inbox_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  capture_id uuid NOT NULL REFERENCES source_captures (id) ON DELETE CASCADE,
  job_id uuid REFERENCES jobs (id) ON DELETE SET NULL,
  hiring_post_id uuid REFERENCES hiring_posts (id) ON DELETE SET NULL,
  match_decision_id uuid REFERENCES match_decisions (id) ON DELETE SET NULL,
  state text NOT NULL,
  saved boolean NOT NULL DEFAULT false,
  rejected boolean NOT NULL DEFAULT false,
  duplicate_of uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, capture_id)
);
CREATE INDEX idx_inbox_items_user_state ON inbox_items (user_id, state, created_at DESC);

CREATE TABLE inbox_state_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  inbox_item_id uuid NOT NULL REFERENCES inbox_items (id) ON DELETE CASCADE,
  from_state text,
  to_state text NOT NULL,
  reason text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_inbox_state_events_user ON inbox_state_events (user_id, inbox_item_id, created_at);

CREATE TABLE agent_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id text NOT NULL UNIQUE,
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  agent_name text NOT NULL,
  status text NOT NULL,
  input_hash text,
  model_version text,
  allowed_tools text[] NOT NULL DEFAULT '{}',
  evidence_ids uuid[] NOT NULL DEFAULT '{}',
  cost numeric NOT NULL DEFAULT 0,
  duration_ms integer,
  error text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_agent_runs_user ON agent_runs (user_id, created_at DESC);

CREATE TABLE agent_artifacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  run_id text NOT NULL REFERENCES agent_runs (run_id) ON DELETE CASCADE,
  kind text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_agent_artifacts_user ON agent_artifacts (user_id, run_id);

CREATE TABLE approval_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  inbox_item_id uuid REFERENCES inbox_items (id) ON DELETE CASCADE,
  kind text NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  payload jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  decided_at timestamptz
);
CREATE INDEX idx_approval_tasks_user ON approval_tasks (user_id, status, created_at DESC);

CREATE TABLE tailored_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  inbox_item_id uuid REFERENCES inbox_items (id) ON DELETE SET NULL,
  kind text NOT NULL,
  status text NOT NULL DEFAULT 'draft',
  content text,
  fact_gate_passed boolean NOT NULL DEFAULT false,
  version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_tailored_documents_user ON tailored_documents (user_id, kind);

CREATE TABLE outreach_drafts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  inbox_item_id uuid REFERENCES inbox_items (id) ON DELETE SET NULL,
  channel text NOT NULL DEFAULT 'email',
  body text,
  status text NOT NULL DEFAULT 'draft',
  sent_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT outreach_never_auto_sent CHECK (sent_at IS NULL)
);
CREATE INDEX idx_outreach_drafts_user ON outreach_drafts (user_id, status);

CREATE TABLE applications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  inbox_item_id uuid REFERENCES inbox_items (id) ON DELETE SET NULL,
  state text NOT NULL DEFAULT 'approved',
  apply_url text,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_applications_user ON applications (user_id, state, updated_at DESC);

CREATE TABLE application_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  application_id uuid NOT NULL REFERENCES applications (id) ON DELETE CASCADE,
  from_state text,
  to_state text NOT NULL,
  note text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_application_events_user ON application_events (user_id, application_id);

CREATE TABLE follow_ups (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  application_id uuid REFERENCES applications (id) ON DELETE CASCADE,
  due_at timestamptz NOT NULL,
  note text,
  done boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_follow_ups_user ON follow_ups (user_id, due_at);

CREATE TABLE interview_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  application_id uuid REFERENCES applications (id) ON DELETE CASCADE,
  scheduled_at timestamptz,
  kind text,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_interview_sessions_user ON interview_sessions (user_id, scheduled_at);

CREATE TABLE feedback_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  inbox_item_id uuid REFERENCES inbox_items (id) ON DELETE SET NULL,
  signal text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_feedback_events_user ON feedback_events (user_id, created_at DESC);

CREATE TABLE notification_preferences (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL UNIQUE REFERENCES app_users (user_id) ON DELETE CASCADE,
  email_enabled boolean NOT NULL DEFAULT true,
  in_app_enabled boolean NOT NULL DEFAULT true,
  scan_complete boolean NOT NULL DEFAULT true,
  follow_up_reminders boolean NOT NULL DEFAULT true
);

CREATE TABLE notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  title text NOT NULL,
  body text,
  read boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_notifications_user ON notifications (user_id, created_at DESC);

CREATE TABLE scan_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  connector_id text NOT NULL,
  status text NOT NULL DEFAULT 'queued',
  payload jsonb NOT NULL DEFAULT '{}',
  idempotency_key text NOT NULL,
  attempts integer NOT NULL DEFAULT 0,
  max_attempts integer NOT NULL DEFAULT 5,
  leased_until timestamptz,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, idempotency_key)
);
CREATE INDEX idx_scan_jobs_claim ON scan_jobs (status, leased_until, created_at);
CREATE INDEX idx_scan_jobs_user ON scan_jobs (user_id, status, created_at DESC);

CREATE TABLE outbox_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  event_type text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}',
  idempotency_key text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'pending',
  attempts integer NOT NULL DEFAULT 0,
  leased_until timestamptz,
  delivered_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_outbox_claim ON outbox_events (status, leased_until, created_at);

CREATE TABLE audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL,
  action text NOT NULL,
  resource_type text,
  resource_id text,
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_events_user ON audit_events (user_id, created_at DESC);

CREATE TABLE saved_searches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  name text NOT NULL,
  query jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_saved_searches_user ON saved_searches (user_id, created_at DESC);

-- RLS: deny browser/direct roles; API/worker use service role (bypasses RLS) + user_id filters
DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'app_users','candidate_profiles','verified_facts','resumes','resume_versions',
    'source_accounts','source_policies','source_captures','jobs','hiring_posts',
    'match_decisions','inbox_items','inbox_state_events','agent_runs','agent_artifacts',
    'approval_tasks','tailored_documents','outreach_drafts','applications','application_events',
    'follow_ups','interview_sessions','feedback_events','notification_preferences','notifications',
    'scan_jobs','outbox_events','audit_events','saved_searches'
  ]
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS deny_direct ON %I', t);
    EXECUTE format('CREATE POLICY deny_direct ON %I FOR ALL TO PUBLIC USING (false) WITH CHECK (false)', t);
  END LOOP;
END $$;
