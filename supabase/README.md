# Supabase migrations (Job-hunt SaaS)

## Where to find API keys (Supabase Dashboard)

1. Open [https://supabase.com/dashboard](https://supabase.com/dashboard) and select your **project**.
2. Go to **Project Settings** (gear icon) → **API**.
3. Copy:
   - **Project URL** → `SUPABASE_URL` (looks like `https://xxxxxxxx.supabase.co`)
   - **Project API keys** → **anon** `public` → `SUPABASE_ANON_KEY` (browser / RLS client; not used by the Node API yet)
   - **Project API keys** → **service_role** `secret` → `SUPABASE_SERVICE_ROLE_KEY` (**server only** — used by `lib/db/supabase-admin.mjs`)

Never put `service_role` in Next.js `NEXT_PUBLIC_*` or client code. The Job-hunt API on port 3800 uses service role with explicit `user_id` filters.

Put all three in the repo root **`.env`**. The web app does not need Supabase keys until you add a browser client.

### Direct Postgres connection string (migrations)

Dashboard → **Project Settings** → **Database** → **Connection string** → URI.

For project `btinlwtseqtnznublasj`:

```text
postgresql://postgres:[YOUR-PASSWORD]@db.btinlwtseqtnznublasj.supabase.co:5432/postgres
```

Add to root `.env` as `SUPABASE_DATABASE_URL` (or `DATABASE_URL`). If the database password contains `@`, `#`, `/`, etc., **percent-encode** them in the URL.

Apply migrations from your machine (requires `psql`):

```bash
npm run db:migrate
```

Or paste each file below into **SQL Editor** in the dashboard.

Verify: `npm run check:connections` (prints set/missing, probes DB without showing secrets).

### Optional: Supabase Agent Skills (Cursor / Codex)

```bash
npx skills add supabase/agent-skills
```

Gives agents Supabase-specific guidance; not required for Job-hunt to run.

Apply in order in the Supabase SQL editor or via CLI:

1. `migrations/001_initial_schema.sql`
2. `migrations/002_saas.sql`
3. `migrations/003_saas_seed.sql`
4. `migrations/004_decision_events.sql`

Set in root `.env`:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY` (web client, future)
- `SUPABASE_SERVICE_ROLE_KEY` (API server only — never expose to browser)

The API uses the **service role** with explicit `user_id` filters keyed off Clerk (`app_users.clerk_user_id`).
