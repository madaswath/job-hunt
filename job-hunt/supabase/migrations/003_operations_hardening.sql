ALTER TABLE source_accounts
  ADD COLUMN IF NOT EXISTS token_expires_at timestamptz,
  ADD COLUMN IF NOT EXISTS last_failure_reason text,
  ADD COLUMN IF NOT EXISTS ingested_total integer NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS oauth_states (
  state text PRIMARY KEY,
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  connector_id text NOT NULL,
  labels text[] NOT NULL DEFAULT '{}',
  expires_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_oauth_states_expires ON oauth_states (expires_at);

CREATE TABLE IF NOT EXISTS schema_migrations (
  name text PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE oauth_states ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS deny_direct ON oauth_states;
CREATE POLICY deny_direct ON oauth_states FOR ALL TO PUBLIC USING (false) WITH CHECK (false);
