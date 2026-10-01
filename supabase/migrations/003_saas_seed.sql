-- Seed plans and entitlements (idempotent)

INSERT INTO public.plans (id, name, description, sort_order) VALUES
  ('free', 'Free', 'Discover and evaluate with daily limits', 0),
  ('premium', 'Premium', 'Full matching, resumes, and connectors', 1),
  ('pro', 'Pro', 'Higher limits and priority processing', 2)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  sort_order = EXCLUDED.sort_order;

INSERT INTO public.entitlements (id, description, unit) VALUES
  ('job_evaluations_monthly', 'Full job evaluations (Brihaspati)', 'count'),
  ('tailored_resumes_monthly', 'ATS-tailored resume generations', 'count'),
  ('recruiter_searches_monthly', 'Recruiter / HM discovery runs', 'count'),
  ('outreach_drafts_monthly', 'Outreach draft generations', 'count'),
  ('connected_plugins', 'Connected account plugins', 'count'),
  ('company_sources', 'Custom company career sites', 'count'),
  ('saved_jobs', 'Saved jobs in pipeline', 'count'),
  ('daily_job_scans', 'Automated scan runs per day', 'count'),
  ('ats_verification_monthly', 'Dharma ATS fact checks', 'count'),
  ('ai_analysis', 'Groq detailed analysis', 'boolean'),
  ('advanced_analytics', 'Advanced funnel analytics', 'boolean'),
  ('interview_ai', 'Interview prep AI sessions', 'boolean'),
  ('priority_processing', 'Priority worker queue', 'boolean'),
  ('gmail_job_alerts', 'Gmail job-alert import', 'boolean')
ON CONFLICT (id) DO NOTHING;

-- Free tier
INSERT INTO public.plan_entitlements (plan_id, entitlement_id, limit_value, limit_period, enabled) VALUES
  ('free', 'job_evaluations_monthly', 10, 'month', true),
  ('free', 'tailored_resumes_monthly', 2, 'month', true),
  ('free', 'recruiter_searches_monthly', 0, 'month', true),
  ('free', 'outreach_drafts_monthly', 0, 'month', true),
  ('free', 'connected_plugins', 0, 'lifetime', true),
  ('free', 'company_sources', 5, 'lifetime', true),
  ('free', 'saved_jobs', 25, 'lifetime', true),
  ('free', 'daily_job_scans', 1, 'day', true),
  ('free', 'ats_verification_monthly', 2, 'month', true),
  ('free', 'ai_analysis', 0, 'month', true),
  ('free', 'advanced_analytics', 0, 'month', true),
  ('free', 'interview_ai', 0, 'month', true),
  ('free', 'priority_processing', 0, 'month', true),
  ('free', 'gmail_job_alerts', 0, 'month', true)
ON CONFLICT (plan_id, entitlement_id) DO UPDATE SET
  limit_value = EXCLUDED.limit_value,
  limit_period = EXCLUDED.limit_period,
  enabled = EXCLUDED.enabled;

-- Premium
INSERT INTO public.plan_entitlements (plan_id, entitlement_id, limit_value, limit_period, enabled) VALUES
  ('premium', 'job_evaluations_monthly', 150, 'month', true),
  ('premium', 'tailored_resumes_monthly', 30, 'month', true),
  ('premium', 'recruiter_searches_monthly', 20, 'month', true),
  ('premium', 'outreach_drafts_monthly', 20, 'month', true),
  ('premium', 'connected_plugins', 2, 'lifetime', true),
  ('premium', 'company_sources', 50, 'lifetime', true),
  ('premium', 'saved_jobs', 250, 'lifetime', true),
  ('premium', 'daily_job_scans', 4, 'day', true),
  ('premium', 'ats_verification_monthly', NULL, 'month', true),
  ('premium', 'ai_analysis', 1, 'month', true),
  ('premium', 'advanced_analytics', 1, 'month', true),
  ('premium', 'interview_ai', 1, 'month', true),
  ('premium', 'priority_processing', 0, 'month', true),
  ('premium', 'gmail_job_alerts', 1, 'month', true)
ON CONFLICT (plan_id, entitlement_id) DO UPDATE SET
  limit_value = EXCLUDED.limit_value,
  limit_period = EXCLUDED.limit_period,
  enabled = EXCLUDED.enabled;

-- Pro (NULL limit_value = fair-use / high cap enforced in app if needed)
INSERT INTO public.plan_entitlements (plan_id, entitlement_id, limit_value, limit_period, enabled) VALUES
  ('pro', 'job_evaluations_monthly', 500, 'month', true),
  ('pro', 'tailored_resumes_monthly', 100, 'month', true),
  ('pro', 'recruiter_searches_monthly', 100, 'month', true),
  ('pro', 'outreach_drafts_monthly', 100, 'month', true),
  ('pro', 'connected_plugins', 10, 'lifetime', true),
  ('pro', 'company_sources', 200, 'lifetime', true),
  ('pro', 'saved_jobs', NULL, 'lifetime', true),
  ('pro', 'daily_job_scans', 12, 'day', true),
  ('pro', 'ats_verification_monthly', NULL, 'month', true),
  ('pro', 'ai_analysis', 1, 'month', true),
  ('pro', 'advanced_analytics', 1, 'month', true),
  ('pro', 'interview_ai', 1, 'month', true),
  ('pro', 'priority_processing', 1, 'month', true),
  ('pro', 'gmail_job_alerts', 1, 'month', true)
ON CONFLICT (plan_id, entitlement_id) DO UPDATE SET
  limit_value = EXCLUDED.limit_value,
  limit_period = EXCLUDED.limit_period,
  enabled = EXCLUDED.enabled;
