#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export DATABASE_URL="${DATABASE_URL:-postgresql://jobhunt:jobhunt@127.0.0.1:5432/jobhunt}"
export AUTH_MODE="${AUTH_MODE:-test}"
export TEST_JWT_SECRET="${TEST_JWT_SECRET:-jobhunt-test-secret-32b-minimum-key!}"
python scripts/apply_migrations.py
pytest tests/integration tests/e2e -q
