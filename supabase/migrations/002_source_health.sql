ALTER TABLE source_accounts
  ADD COLUMN IF NOT EXISTS health_status text NOT NULL DEFAULT 'unknown',
  ADD COLUMN IF NOT EXISTS health_payload jsonb NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS last_ingest_at timestamptz,
  ADD COLUMN IF NOT EXISTS rate_limit_remaining integer;

CREATE TABLE IF NOT EXISTS source_health_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL REFERENCES app_users (user_id) ON DELETE CASCADE,
  connector_id text NOT NULL,
  status text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_source_health_events_user ON source_health_events (user_id, connector_id, created_at DESC);

ALTER TABLE source_health_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS deny_direct ON source_health_events;
CREATE POLICY deny_direct ON source_health_events FOR ALL TO PUBLIC USING (false) WITH CHECK (false);
