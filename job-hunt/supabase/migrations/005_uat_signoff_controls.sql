ALTER TABLE uat_signoffs
  ADD COLUMN IF NOT EXISTS config_fingerprint text,
  ADD COLUMN IF NOT EXISTS expires_at timestamptz;
