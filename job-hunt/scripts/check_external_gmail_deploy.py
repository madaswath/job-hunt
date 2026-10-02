#!/usr/bin/env python3
"""Fail CI/deploy if API and worker FEATURE_EXTERNAL_GMAIL flags are misaligned or leaked to browser env."""
import os
import sys

import httpx

from jobhunt_api.services.deploy_checks import assert_no_browser_feature_leak


def main() -> int:
    if not assert_no_browser_feature_leak():
        print("FAIL: FEATURE_EXTERNAL_GMAIL exposed via Vite/Next public env")
        return 1
    api_flag = os.getenv("FEATURE_EXTERNAL_GMAIL", "false").lower() in {"1", "true", "yes", "on"}
    worker_url = os.getenv("WORKER_INTERNAL_URL", "http://127.0.0.1:8001").rstrip("/") + "/health"
    try:
        worker_flag = bool(httpx.get(worker_url, timeout=5).json().get("feature_external_gmail"))
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: could not reach worker at {worker_url}: {exc}")
        worker_flag = None
    if api_flag != worker_flag:
        print(f"FAIL: API FEATURE_EXTERNAL_GMAIL={api_flag} worker={worker_flag}")
        return 1
    print(f"OK: external gmail flags aligned (enabled={api_flag})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
