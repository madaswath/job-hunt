# Local development

## Prerequisites

- Python 3.11+
- Node 20+
- Docker (for Compose smoke and integration Postgres)

## Environment

Copy `infra/deploy/.env.uat.example` to `apps/api/.env` and `apps/web/.env`.

Required:

- `DATABASE_URL` — Postgres (local Compose or Supabase)
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — service role only on API/worker
- `CLERK_ISSUER`, `CLERK_JWKS_URL` — JWT verification
- `VITE_CLERK_PUBLISHABLE_KEY` — browser only
- `TOKEN_ENCRYPTION_KEY` — 32-byte base64 key for connector token envelope

Do not put service-role keys in Vite env.

## Run

```bash
# API
cd apps/api && pip install -e ../../packages/domain -e ../../packages/connectors \
  -e ../../packages/agents -e ../../packages/policy -e ../../packages/tailoring -e . \
  && uvicorn jobhunt_api.main:app --reload --port 8000

# Worker
cd apps/worker && python -m jobhunt_worker

# Web
cd apps/web && npm install && npm run dev
```

API: `http://localhost:8000/api/v1/health`  
Docs: `http://localhost:8000/docs`  
Web: `http://localhost:5173`

## Tests

```bash
# from repo root
pytest tests/unit tests/integration -q
cd apps/web && npm run typecheck && npm run lint && npm test
```

E2E uses API test tokens (`AUTH_MODE=test`) — see `tests/e2e/README.md`.
