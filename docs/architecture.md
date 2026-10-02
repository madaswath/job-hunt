# Job-hunt architecture

PocketFi-style modular monolith. One FastAPI backend with routers and domain services. No microservices.

```text
Browser
  → Caddy (TLS, CSP, security headers, / and /api/v1)
  → Vite React SPA (apps/web)
  → FastAPI (apps/api, prefix /api/v1)
  → Supabase Postgres (service-role only; RLS deny-by-default)
  → Python worker (apps/worker)
```

## Repository

| Path | Role |
| --- | --- |
| `apps/web` | React + Vite + TypeScript SPA |
| `apps/api` | FastAPI modular monolith |
| `apps/worker` | Scan, outbox, retries, stuck-job recovery |
| `packages/domain` | Schemas, inbox state machine, Match v2, India defaults |
| `packages/connectors` | Connector contract and implementations |
| `packages/agents` | Named agent definitions and orchestration contracts |
| `packages/policy` | Consent, retention, source capabilities, audit rules |

Connector implementation labels: `catalog` / `planned` (no ingest), `ingestion_ready` (fixture or pipeline-ready, e.g. Gmail before production OAuth hardening), `live` (production-ready). Service-role secrets stay on API/worker only; browser gets publishable Clerk key only.
| `packages/tailoring` | Fact-gated generation contracts |
| `infra/deploy` | Dockerfiles, Caddy, Compose, UAT/prod env examples |
| `supabase/migrations` | Canonical Postgres + RLS |
| `tests` | Unit, integration, e2e, fixtures |

Python packages (`jobhunt_domain`, `jobhunt_connectors`, `jobhunt_agents`, `jobhunt_policy`, `jobhunt_tailoring`) are imported by API and worker. Agents never query tables; they call typed services.

## Auth and tenancy

- Clerk issues JWTs. FastAPI verifies them via Clerk JWKS.
- First authenticated request upserts `app_users` from Clerk `sub`.
- Tenant-owned tables include `user_id` and indexes on `(user_id, …)`.
- Supabase RLS is enabled. `anon` and `authenticated` are denied direct table access. The service-role key is used only by API and worker, always with explicit `user_id` filters.
- No service-role keys, provider credentials, or encryption keys are returned to the browser, prompts, logs, or agent artifacts.

## Reliability

- Transactional outbox for external side effects (Phase 1: in-app notifications only).
- Idempotency keys on captures, inbox inserts, and outbox delivery.
- Job leases on `scan_jobs` (`leased_until`, `attempts`, `status`).
- Exponential backoff and expired-lease recovery.
- Persist outcomes before marking delivery complete.
- Audit events for approvals, consent, and state transitions.
- `/api/v1/health` (liveness) and `/api/v1/ready` (database reachable).

## Feature flags and rollback

Every migrated write/read path is gated. Phase 1 flags:

- `FEATURE_US_MARKET` (default false)
- `FEATURE_LIVE_ATS_HTTP` (default false; fixture ingest is the live path)

Disable the flag to roll back a path without redeploying schema.

## Live vs catalog

A connector or agent is live only when executable code and passing tests exist. Catalog entries and planned agents appear in the UI with an honest status.

## Security

- Caddy sets CSP, HSTS (prod), `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`.
- API writes use Bearer JWT (CSRF-aware: no cookie session for API).
- Rate limits and correlation IDs on every request.
- Structured logs with secret/PII redaction.
- Connector tokens stored as envelope ciphertext (`token_ciphertext`, `kek_id`). Phase 1 uses local AES-GCM with `TOKEN_ENCRYPTION_KEY` (KMS-shaped interface; cloud KMS in a later phase).
- Export/delete: synchronous export bundle; delete wipes DB cascade, Supabase storage paths, queued jobs, connector tokens; audit rows anonymized.
- Gmail external enablement: `FEATURE_EXTERNAL_GMAIL` + `uat_signoffs` row; OAuth uses PKCE + signed state + redirect allowlist.

## Deployment

Docker Compose services: `web`, `api`, `worker` (plus `caddy` and optional `postgres` for local/UAT). Separate `infra/deploy/.env.uat.example` and `.env.prod.example`. Immutable images. Rollout gated on health and readiness.

## Testing

Unit tests cover schemas, matching, transitions, fact gate, connectors, and agent permissions. Integration tests cover RLS, Clerk auth, leases, outbox, and cross-tenant denial. E2E covers onboarding → fixture scan → inbox → reject/save. CI runs frontend typecheck/lint/tests, Python lint/tests, OpenAPI drift, migration validation, compose smoke, and UAT-labeled integration tests.
