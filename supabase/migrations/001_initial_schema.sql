-- Supabase PostgreSQL Schema for Job-hunt Multi-User Platform
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Profiles Table (User Layer)
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT NOT NULL,
  email TEXT,
  phone TEXT,
  headline TEXT,
  location TEXT,
  country TEXT,
  city TEXT,
  visa_status TEXT,
  needs_sponsorship BOOLEAN DEFAULT FALSE,
  compensation_target TEXT,
  compensation_minimum TEXT,
  superpowers TEXT[],
  target_roles TEXT[],
  raw_profile_json JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT uq_profiles_user UNIQUE (user_id)
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own profile" ON public.profiles
  FOR ALL USING (auth.uid() = user_id);

-- 2. Job Sources Catalog (Public & Connected)
CREATE TABLE IF NOT EXISTS public.job_sources (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  source_type TEXT NOT NULL, -- PUBLIC_API, PUBLIC_ATS, CAREER_SITE, AGGREGATOR, CONNECTED_ACCOUNT
  base_url TEXT,
  provider TEXT, -- greenhouse, lever, ashby, workday, etc.
  authentication_type TEXT DEFAULT 'NONE', -- NONE, OAUTH, API_KEY, COOKIE_SESSION, EMAIL_CONNECTOR
  enabled BOOLEAN DEFAULT TRUE,
  supports_search BOOLEAN DEFAULT TRUE,
  supports_job_detail BOOLEAN DEFAULT TRUE,
  supports_apply BOOLEAN DEFAULT FALSE,
  supports_saved_jobs BOOLEAN DEFAULT FALSE,
  sync_interval INTEGER DEFAULT 60, -- minutes
  rate_limit INTEGER DEFAULT 60, -- reqs/min
  configuration JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.job_sources ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read on enabled job sources" ON public.job_sources
  FOR SELECT USING (TRUE);

-- 3. Normalized Jobs Table (Shared across users, deduplicated)
CREATE TABLE IF NOT EXISTS public.jobs (
  id TEXT PRIMARY KEY, -- deterministic hash of canonical url
  source_id TEXT REFERENCES public.job_sources(id) ON DELETE SET NULL,
  provider TEXT DEFAULT 'direct',
  url TEXT NOT NULL,
  canonical_url TEXT NOT NULL,
  company TEXT NOT NULL,
  domain TEXT,
  logo_url TEXT,
  title TEXT NOT NULL,
  normalized_title TEXT,
  seniority TEXT,
  employment_type TEXT DEFAULT 'Full-time',
  location TEXT,
  country TEXT,
  city TEXT,
  is_remote BOOLEAN DEFAULT FALSE,
  is_hybrid BOOLEAN DEFAULT FALSE,
  is_onsite BOOLEAN DEFAULT FALSE,
  currency TEXT DEFAULT 'USD',
  min_salary NUMERIC,
  max_salary NUMERIC,
  salary_interval TEXT DEFAULT 'year',
  description TEXT,
  skills TEXT[],
  must_haves TEXT[],
  nice_to_haves TEXT[],
  embedding vector(1536), -- pgvector embeddings for semantic similarity
  state TEXT DEFAULT 'DISCOVERED',
  discovered_at TIMESTAMPTZ DEFAULT NOW(),
  posted_at TIMESTAMPTZ,
  checked_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_canonical_url ON public.jobs(canonical_url);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON public.jobs(company);
CREATE INDEX IF NOT EXISTS idx_jobs_discovered_at ON public.jobs(discovered_at DESC);

ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Authenticated users can read jobs" ON public.jobs
  FOR SELECT TO authenticated USING (TRUE);

-- 4. User-Specific Job Matches & Deterministic Scoring
CREATE TABLE IF NOT EXISTS public.job_matches (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  job_id TEXT NOT NULL REFERENCES public.jobs(id) ON DELETE CASCADE,
  deterministic_score INTEGER NOT NULL,
  semantic_score INTEGER,
  final_score INTEGER NOT NULL,
  must_have_met INTEGER DEFAULT 0,
  must_have_total INTEGER DEFAULT 0,
  breakdown_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  why_it_fits TEXT[],
  risks TEXT[],
  evaluated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT uq_user_job_match UNIQUE (user_id, job_id)
);

ALTER TABLE public.job_matches ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access their own job matches" ON public.job_matches
  FOR ALL USING (auth.uid() = user_id);

-- 5. User Decisions (Approvals, Rejections, Saves)
CREATE TABLE IF NOT EXISTS public.user_job_decisions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  job_id TEXT NOT NULL REFERENCES public.jobs(id) ON DELETE CASCADE,
  decision TEXT NOT NULL, -- APPROVED, REJECTED, SAVED, APPLIED
  rejection_reason TEXT, -- TOO_JUNIOR, WRONG_LOCATION, SALARY_TOO_LOW, etc.
  rejection_note TEXT,
  decided_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT uq_user_job_decision UNIQUE (user_id, job_id)
);

ALTER TABLE public.user_job_decisions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only manage their own decisions" ON public.user_job_decisions
  FOR ALL USING (auth.uid() = user_id);

-- 6. Recruiter & Contact Intelligence
CREATE TABLE IF NOT EXISTS public.recruiters (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  job_id TEXT REFERENCES public.jobs(id) ON DELETE SET NULL,
  company TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT,
  email TEXT,
  linkedin_url TEXT,
  relationship TEXT DEFAULT 'recruiter',
  confidence NUMERIC DEFAULT 0.8,
  source TEXT DEFAULT 'linkedin_search',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.recruiters ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own recruiter contacts" ON public.recruiters
  FOR ALL USING (auth.uid() = user_id);

-- 7. Outreach Drafts (Human Approval Gated)
CREATE TABLE IF NOT EXISTS public.outreach_drafts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  job_id TEXT NOT NULL REFERENCES public.jobs(id) ON DELETE CASCADE,
  recruiter_id UUID REFERENCES public.recruiters(id) ON DELETE SET NULL,
  recipient_name TEXT NOT NULL,
  recipient_role TEXT,
  recipient_email TEXT,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  status TEXT DEFAULT 'DRAFT', -- DRAFT, APPROVED, SENT, REJECTED
  approved_at TIMESTAMPTZ,
  sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.outreach_drafts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own outreach drafts" ON public.outreach_drafts
  FOR ALL USING (auth.uid() = user_id);

-- 8. Applications Tracker
CREATE TABLE IF NOT EXISTS public.applications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  job_id TEXT REFERENCES public.jobs(id) ON DELETE SET NULL,
  company TEXT NOT NULL,
  role TEXT NOT NULL,
  state TEXT DEFAULT 'Applied', -- Applied, Screen, Interview, Offer, Rejected, Withdrawn
  score TEXT,
  report_ref TEXT,
  pdf_path TEXT,
  notes TEXT,
  applied_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own applications" ON public.applications
  FOR ALL USING (auth.uid() = user_id);

-- 9. Connected Accounts & Plugin Vault
CREATE TABLE IF NOT EXISTS public.connector_accounts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL, -- linkedin, naukri, indeed, gmail, outlook, etc.
  status TEXT DEFAULT 'CONNECTED', -- CONNECTED, DISCONNECTED, EXPIRED
  scopes TEXT[] DEFAULT '{}',
  credential_reference TEXT NOT NULL, -- Secret vault reference, NEVER raw token
  connected_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  last_sync_at TIMESTAMPTZ,
  CONSTRAINT uq_user_connector UNIQUE (user_id, provider)
);

ALTER TABLE public.connector_accounts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own connector accounts" ON public.connector_accounts
  FOR ALL USING (auth.uid() = user_id);
