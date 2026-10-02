# UAT and production

## Env files

- UAT: `infra/deploy/.env.uat.example` → runtime `.env.uat` (never commit secrets)
- Production: `infra/deploy/.env.prod.example` → runtime `.env.prod`

## Images

Build immutable images for `web`, `api`, and `worker`. Deploy them as independent Compose services. Do not bake secrets into images.

## Rollout gate

1. Deploy UAT.
2. `curl` `/api/v1/health` and `/api/v1/ready` must be 200.
3. Run CI integration job labeled UAT.
4. Promote the same image digests to production.
5. Roll back by previous image tag and/or feature flag (`FEATURE_LIVE_ATS_HTTP`, `FEATURE_US_MARKET`).

## Incidents

See `worker-operations.md` for stuck-job recovery. Disable a write path with its feature flag before reverting schema.
