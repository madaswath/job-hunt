ALTER TABLE oauth_states
  ADD COLUMN IF NOT EXISTS code_verifier text,
  ADD COLUMN IF NOT EXISTS state_signature text;

CREATE TABLE IF NOT EXISTS uat_signoffs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  component text NOT NULL,
  signed_by text NOT NULL,
  signed_at timestamptz NOT NULL DEFAULT now(),
  notes text,
  revoked_at timestamptz,
  UNIQUE (component)
);

CREATE TABLE IF NOT EXISTS system_alerts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_kind text NOT NULL,
  severity text NOT NULL DEFAULT 'warning',
  payload jsonb NOT NULL DEFAULT '{}',
  acknowledged_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_system_alerts_kind ON system_alerts (alert_kind, created_at DESC);

ALTER TABLE uat_signoffs ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_alerts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS deny_direct ON uat_signoffs;
DROP POLICY IF EXISTS deny_direct ON system_alerts;
CREATE POLICY deny_direct ON uat_signoffs FOR ALL TO PUBLIC USING (false) WITH CHECK (false);
CREATE POLICY deny_direct ON system_alerts FOR ALL TO PUBLIC USING (false) WITH CHECK (false);
