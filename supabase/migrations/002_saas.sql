-- Job-hunt SaaS: identity (Clerk), plans, entitlements, billing, usage metering

-- Clerk-backed app users (API uses service role + explicit user_id filters)
CREATE TABLE IF NOT EXISTS public.app_users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  clerk_user_id TEXT NOT NULL UNIQUE,
  email TEXT,
  display_name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_app_users_clerk ON public.app_users(clerk_user_id);

ALTER TABLE public.app_users ENABLE ROW LEVEL SECURITY;

-- Plans
CREATE TABLE IF NOT EXISTS public.plans (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  sort_order INTEGER DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.plans ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Anyone can read active plans" ON public.plans
  FOR SELECT USING (is_active = TRUE);

-- Entitlement catalog
CREATE TABLE IF NOT EXISTS public.entitlements (
  id TEXT PRIMARY KEY,
  description TEXT,
  unit TEXT DEFAULT 'count'
);

ALTER TABLE public.entitlements ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Anyone can read entitlements" ON public.entitlements
  FOR SELECT USING (TRUE);

CREATE TABLE IF NOT EXISTS public.plan_entitlements (
  plan_id TEXT NOT NULL REFERENCES public.plans(id) ON DELETE CASCADE,
  entitlement_id TEXT NOT NULL REFERENCES public.entitlements(id) ON DELETE CASCADE,
  limit_value NUMERIC,
  limit_period TEXT DEFAULT 'month',
  enabled BOOLEAN DEFAULT TRUE,
  PRIMARY KEY (plan_id, entitlement_id)
);

ALTER TABLE public.plan_entitlements ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Anyone can read plan entitlements" ON public.plan_entitlements
  FOR SELECT USING (TRUE);

-- Subscriptions
CREATE TABLE IF NOT EXISTS public.subscriptions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.app_users(id) ON DELETE CASCADE,
  plan_id TEXT NOT NULL REFERENCES public.plans(id),
  status TEXT NOT NULL DEFAULT 'active',
  razorpay_subscription_id TEXT,
  razorpay_customer_id TEXT,
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  cancel_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON public.subscriptions(user_id);

ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.subscription_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  subscription_id UUID REFERENCES public.subscriptions(id) ON DELETE SET NULL,
  user_id UUID REFERENCES public.app_users(id) ON DELETE SET NULL,
  event_type TEXT NOT NULL,
  provider TEXT DEFAULT 'razorpay',
  provider_event_id TEXT,
  payload JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_subscription_events_provider
  ON public.subscription_events(provider, provider_event_id)
  WHERE provider_event_id IS NOT NULL;

ALTER TABLE public.subscription_events ENABLE ROW LEVEL SECURITY;

-- Usage
CREATE TABLE IF NOT EXISTS public.usage_counters (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.app_users(id) ON DELETE CASCADE,
  entitlement_id TEXT NOT NULL REFERENCES public.entitlements(id),
  period_key TEXT NOT NULL,
  used NUMERIC NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT uq_usage_counter UNIQUE (user_id, entitlement_id, period_key)
);

CREATE INDEX IF NOT EXISTS idx_usage_counters_lookup
  ON public.usage_counters(user_id, entitlement_id, period_key);

ALTER TABLE public.usage_counters ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.usage_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.app_users(id) ON DELETE CASCADE,
  entitlement_id TEXT NOT NULL,
  feature TEXT,
  quantity NUMERIC DEFAULT 1,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_events_user_created
  ON public.usage_events(user_id, created_at DESC);

ALTER TABLE public.usage_events ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.ai_usage_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES public.app_users(id) ON DELETE SET NULL,
  feature TEXT NOT NULL,
  workflow TEXT,
  provider TEXT DEFAULT 'groq',
  model TEXT,
  input_tokens INTEGER,
  output_tokens INTEGER,
  latency_ms INTEGER,
  estimated_cost_usd NUMERIC(12, 6),
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_usage_user_created
  ON public.ai_usage_events(user_id, created_at DESC);

ALTER TABLE public.ai_usage_events ENABLE ROW LEVEL SECURITY;

-- Payments & invoices
CREATE TABLE IF NOT EXISTS public.payments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.app_users(id) ON DELETE CASCADE,
  plan_id TEXT REFERENCES public.plans(id),
  razorpay_order_id TEXT UNIQUE,
  razorpay_payment_id TEXT,
  amount_paise INTEGER NOT NULL,
  currency TEXT DEFAULT 'INR',
  status TEXT DEFAULT 'created',
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.invoices (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.app_users(id) ON DELETE CASCADE,
  payment_id UUID REFERENCES public.payments(id),
  amount_paise INTEGER NOT NULL,
  currency TEXT DEFAULT 'INR',
  status TEXT DEFAULT 'draft',
  issued_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.invoices ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.promo_codes (
  code TEXT PRIMARY KEY,
  plan_id TEXT REFERENCES public.plans(id),
  discount_percent INTEGER,
  max_redemptions INTEGER,
  redemptions INTEGER DEFAULT 0,
  valid_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.promo_codes ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.founder_plans (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.app_users(id) ON DELETE CASCADE,
  plan_id TEXT NOT NULL REFERENCES public.plans(id),
  note TEXT,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.founder_plans ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.connector_permissions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.app_users(id) ON DELETE CASCADE,
  connector_account_id UUID,
  permission TEXT NOT NULL,
  granted_at TIMESTAMPTZ DEFAULT NOW(),
  revoked_at TIMESTAMPTZ
);

ALTER TABLE public.connector_permissions ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.audit_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES public.app_users(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  resource_type TEXT,
  resource_id TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_user_created ON public.audit_events(user_id, created_at DESC);

ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.app_users(id) ON DELETE CASCADE,
  channel TEXT DEFAULT 'in_app',
  title TEXT NOT NULL,
  body TEXT,
  read_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.user_preferences (
  user_id UUID PRIMARY KEY REFERENCES public.app_users(id) ON DELETE CASCADE,
  preferences JSONB DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;

-- Link legacy profiles to app_users when present
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS app_user_id UUID REFERENCES public.app_users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_profiles_app_user ON public.profiles(app_user_id);
