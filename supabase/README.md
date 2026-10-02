# Supabase

Canonical migrations live in `migrations/`. Apply to local Postgres or Supabase:

```bash
python scripts/apply_migrations.py
```

RLS is enabled on every tenant table. Direct `anon` / `authenticated` access is denied. FastAPI and the worker use a service-role (or table-owner) connection and always filter by `user_id`.
