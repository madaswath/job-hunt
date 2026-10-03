# Implementation plan

North star for what to build next: [locked-intent.md](locked-intent.md).

## Demo 1 — Gmail + LinkedIn + ATS → ranked inbox (NEXT)

**Goal:** Local demo for one DS+AI switcher profile, then closed beta (~10–20).

**Build:**

1. Gmail alerts ingest → follow JD links → normalize → Match v2 → inbox (fixture path acceptable in CI; real OAuth for local demo).
2. LinkedIn ingest into a **shared jobs index** via scraper export drops (`data/linkedin-exports/`, JSON + clean CSV): **100 recent jobs per role keyword**, **10–15 feed posts** matched to skills/preferences; fixture fallback when the drop folder is empty. Unrestricted live scrape remains forbidden.
3. Public ATS into the same shared index (`FEATURE_LIVE_ATS_HTTP` or expanded fixtures for demo).
4. Beta title allowlist (DS+AI set in locked-intent) + remote/hybrid + India-primary with abroad listed.
5. Autopilot: scheduled refresh job that re-ingests enabled sources and rematches.
6. `POST /discovery/linkedin-master-ingest` + `scripts/ingest_linkedin_export.py` for master-data load; `POST /discovery/match-shared` to rank master catalogue into inbox.
7. Applications tracker (minimal): handoff → `applications.started`; candidate updates stage; dashboard `applications_by_stage`.

**Acceptance:**

- One test user sees ranked inbox items from **all three** source families in a single demo run.
- Hard filters drop obvious non-DS+AI noise; score breakdown visible.
- No auto-submit / auto-send.
- Metrics hooks (or manual tally) for opens, saves/interested, apply-started (applications table).

**Out of scope for Demo 1:** Pro paywall enforcement, interview agents, follow-up bots, portal partnerships, LLM-heavy research.

## Phase 1 — scaffold, profile, fixture ATS, Match v2, inbox

**Build:** repository, Clerk, Supabase schema/RLS, FastAPI, React shell, profile, public ATS fixtures, deterministic matching, inbox, worker leases, audit/outbox tables.

**Acceptance:** Docs, compose health, fixture scan → inbox, audit events, cross-tenant denial, CI green, honest live vs catalog labels.

## Phase 2 — profile/facts, inbox evidence, approvals, fact-gated drafts

**Build (this slice):**

1. India profile editor with structured verified-fact rows; profile save triggers rematch of existing captures through Ganesha/Arjuna.
2. Inbox evidence detail (source URL, captured text, freshness, breakdown, risks, apply links) and external apply handoff audit.
3. Candidate approval workflow: `review_required → tailored → ready_to_apply` with audit; no transition without `approval_id`.
4. Saraswati deterministic template drafts + Dharma expanded fact gate; Documents page live.

**Out of scope for Phase 2:** Gmail alerts, browser capture, live ATS HTTP, Krishna send, full applications tracker, billing, analytics.

**Acceptance:** Profile changes affect rematch scores; inbox shows original evidence; Dharma must pass before draft is ready; Saraswati/Dharma marked live only with tests; Gmail/browser remain planned.

## Phase 3 — Gmail alerts, browser capture, outreach drafts, notifications

**Build (this slice):**

1. Live `gmail_alerts` and `browser_capture` connectors; encrypted OAuth token storage; connect/revoke with audit; `source_policies` + health events; ingest rate limits.
2. Narada ingest path unchanged: connector scan → immutable `source_captures` → Ganesha/Arjuna → inbox.
3. Krishna outreach drafts API only (`outreach_drafts`, DB constraint blocks `sent_at`); no send endpoint.
4. Sources UI: Gmail connect/sync/revoke; browser capture documented as candidate-initiated.

**Out of scope:** Live Gmail API in CI (fixture-first), marketplace scrapers, auto-send, Gmail draft sync to Google.

**Acceptance:** label-scoped Gmail fixture ingest → inbox; browser capture idempotent; revoke blocks Gmail scans; outreach draft requires explicit request; marketplace connectors stay catalog.

## Phase 3.5 — Operational hardening (in progress)

**Build:**

1. Gmail OAuth callback + refresh-token rotation scaffolding; encryption-key rotation (`TOKEN_ENCRYPTION_KEY_PREVIOUS`); revoke verification flag on API.
2. Connector health dashboard: last sync, ingestion totals, rate-limit remaining, failure reason (`GET /sources/health`, `dashboard.connector_health`).
3. Worker `/metrics` and alert counters: stalled jobs, dead letters, retries, token expiry horizon, source-policy failures.
4. Privacy: synchronous export bundle; confirmed delete wipe; hourly retention purge for orphan captures past policy.
5. UAT: incremental `apply_migrations.py`, `scripts/run_uat_integration.sh`, compose mounts migrations 001–003.

**Production gates (required before `production_live` / external Gmail):**

1. OAuth: PKCE, HMAC state binding, redirect allowlist, narrow label allowlist, refresh-failure → revoke path.
2. Gmail API ingest: pagination, message-id dedupe, backoff/taxonomy (`GmailFailureKind`).
3. Privacy wipe: storage paths, scan/outbox/oauth cleanup, anonymized audit retention.
4. UAT Postgres tests: OAuth callback, refresh rotation, revoke, RLS, deletion, retention purge.
5. Observability: `system_alerts` for token expiry, ingestion failure, stalled/dead-letter jobs, retention failures, policy violations.
6. `POST /uat/signoff` requires **Clerk/test JWT admin** (`UAT_ADMIN_USER_IDS`) **and** `x-uat-signoff-secret`; sign-off expires / auto-revokes on config drift; `FEATURE_EXTERNAL_GMAIL` aligned on API+worker only (never Vite).

**Acceptance:** Gmail stays `ingestion_ready` until sign-off; browser capture stays live; marketplace catalog-only.

## Phase 4 — research, interview prep, analytics, feedback

**Build:** cited web research, Skanda after interview stage, Lakshmi analytics, feedback-based ranking signals.

## Phase 5 — Production rollout

**Build:** health-gated deploy, external-user connector enablement after UAT sign-off, observability dashboards.
