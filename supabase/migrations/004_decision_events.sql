-- Jev / rules / Groq-gate decision audit log

CREATE TABLE IF NOT EXISTS public.decision_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES public.app_users(id) ON DELETE SET NULL,
  job_id TEXT,
  agent TEXT NOT NULL,
  decision_type TEXT NOT NULL,
  provider TEXT NOT NULL,
  decision TEXT,
  confidence NUMERIC,
  input_hash TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decision_events_user_created
  ON public.decision_events(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_decision_events_job
  ON public.decision_events(job_id);

ALTER TABLE public.decision_events ENABLE ROW LEVEL SECURITY;
