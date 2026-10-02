# E2E

Primary Phase 1 flow is `pytest tests/e2e` against Postgres + `AUTH_MODE=test`.

Browser flow (optional Playwright):

```bash
cd tests/e2e && npx playwright test
```

Requires API on :8000, web on :5173, `AUTH_MODE=test`. The spec uses `/dev/token` and never auto-applies.
