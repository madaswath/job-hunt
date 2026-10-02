import json

from jobhunt_api import db
from jobhunt_api.redact import sanitize_for_alert


def raise_alert(alert_kind: str, payload: dict, *, severity: str = "warning") -> None:
    safe = sanitize_for_alert(payload)
    db.execute(
        """
        INSERT INTO system_alerts (alert_kind, severity, payload)
        VALUES (%s, %s, %s::jsonb)
        """,
        (alert_kind, severity, json.dumps(safe)),
    )


def recent_alerts(limit: int = 50) -> list[dict]:
    return db.fetch_all(
        """
        SELECT alert_kind, severity, payload, created_at
        FROM system_alerts
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (limit,),
    )


def alert_counts_24h() -> dict:
    rows = db.fetch_all(
        """
        SELECT alert_kind, count(*)::int AS n
        FROM system_alerts
        WHERE created_at > now() - interval '24 hours'
        GROUP BY alert_kind
        """,
    )
    return {r["alert_kind"]: r["n"] for r in rows}
