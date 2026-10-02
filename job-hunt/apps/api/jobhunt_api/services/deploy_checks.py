import os

import httpx

from jobhunt_api.services import production_gates
from jobhunt_api.services.signoff_fingerprint import gmail_config_fingerprint
from jobhunt_api.settings import settings


def api_external_gmail_flag() -> bool:
    return settings.feature_external_gmail


def worker_external_gmail_flag() -> bool | None:
    url = settings.worker_internal_url.rstrip("/") + "/health" if settings.worker_internal_url else ""
    if not url:
        return None
    try:
        with httpx.Client(timeout=5) as client:
            res = client.get(url)
        if res.status_code >= 400:
            return None
        return bool(res.json().get("feature_external_gmail"))
    except Exception:  # noqa: BLE001
        return None


def external_gmail_deployment_ready() -> dict:
    api_flag = api_external_gmail_flag()
    worker_flag = worker_external_gmail_flag()
    aligned = api_flag and worker_flag is True
    signoff = production_gates.uat_signoff_active("gmail_alerts")
    return {
        "api_feature_external_gmail": api_flag,
        "worker_feature_external_gmail": worker_flag,
        "flags_aligned": aligned,
        "browser_exposure_forbidden": True,
        "uat_signoff_active": signoff,
        "config_fingerprint": gmail_config_fingerprint(),
        "ready_for_external_gmail": aligned and signoff and production_gates.gmail_production_live(),
    }


def assert_no_browser_feature_leak() -> bool:
    # Build-time guard: Vite must never receive FEATURE_EXTERNAL_GMAIL.
    leaked = os.getenv("VITE_FEATURE_EXTERNAL_GMAIL") or os.getenv("NEXT_PUBLIC_FEATURE_EXTERNAL_GMAIL")
    return not leaked
