import json
import time

from jobhunt_api import db
from jobhunt_api.services import connector_health, gmail_oauth, observability, privacy

_last_retention = 0.0
_last_ops_alert = 0.0


def record_scan_failure(user_id: str, connector_id: str, reason: str) -> None:
    db.execute(
        """
        UPDATE source_accounts SET last_failure_reason = %s, health_status = 'error'
        WHERE user_id = %s AND connector_id = %s AND revoked_at IS NULL
        """,
        (reason[:500], user_id, connector_id),
    )
    db.execute(
        """
        INSERT INTO source_health_events (user_id, connector_id, status, payload)
        VALUES (%s, %s, 'error', %s::jsonb)
        """,
        (user_id, connector_id, json.dumps({"reason": reason[:500]})),
    )


def maintenance_tick() -> dict:
    global _last_retention, _last_ops_alert
    out: dict = {"retention": None, "token_rotation": None}
    now = time.time()
    if now - _last_retention > 3600:
        try:
            out["retention"] = privacy.purge_retention_captures()
        except Exception as exc:  # noqa: BLE001
            out["retention"] = {"error": str(exc)}
        _last_retention = now
    out["token_rotation"] = gmail_oauth.rotate_stored_refresh_tokens()
    summary = connector_health.worker_connector_summary()
    out["worker_alerts"] = summary
    if now - _last_ops_alert > 3600:
        if summary.get("stalled_jobs", 0) > 0:
            observability.raise_alert("stalled_worker_jobs", summary, severity="warning")
        if summary.get("dead_letter_jobs", 0) > 0:
            observability.raise_alert("dead_letter_jobs", summary, severity="warning")
        if summary.get("tokens_expiring_soon", 0) > 0:
            observability.raise_alert("token_expiry_soon", summary, severity="critical")
        if summary.get("source_policy_failures_24h", 0) > 0:
            observability.raise_alert("connector_policy_violation", summary, severity="warning")
        _last_ops_alert = now
    return out
