from jobhunt_connectors.catalog import CONNECTOR_CATALOG, get_connector

from jobhunt_api import db


def rate_limit_status(user_id: str, connector_id: str) -> dict:
    conn = get_connector(connector_id)
    policy = conn.policy()
    row = db.fetch_one(
        """
        SELECT count(*)::int AS n FROM scan_jobs
        WHERE user_id = %s AND connector_id = %s AND created_at > now() - interval '1 hour'
        """,
        (user_id, connector_id),
    )
    used = row["n"] if row else 0
    limit = policy.max_requests_per_hour
    return {"used_last_hour": used, "limit_per_hour": limit, "remaining": max(0, limit - used)}


def connector_dashboard(user_id: str) -> list[dict]:
    accounts = {
        a["connector_id"]: a
        for a in db.fetch_all(
            """
            SELECT connector_id, status, consent_at, revoked_at, last_ingest_at, health_status,
                   health_payload, last_failure_reason, ingested_total, token_expires_at, rate_limit_remaining
            FROM source_accounts WHERE user_id = %s
            """,
            (user_id,),
        )
    }
    stats = {
        r["connector_id"]: r
        for r in db.fetch_all(
            """
            SELECT connector_id,
              count(*) FILTER (WHERE status = 'completed')::int AS completed,
              count(*) FILTER (WHERE status IN ('failed','dead_letter'))::int AS failed,
              count(*) FILTER (WHERE status IN ('queued','running'))::int AS backlog
            FROM scan_jobs WHERE user_id = %s
            GROUP BY connector_id
            """,
            (user_id,),
        )
    }
    last_failures = {
        r["connector_id"]: r
        for r in db.fetch_all(
            """
            SELECT DISTINCT ON (connector_id) connector_id, last_error, updated_at
            FROM scan_jobs
            WHERE user_id = %s AND last_error IS NOT NULL
            ORDER BY connector_id, updated_at DESC
            """,
            (user_id,),
        )
    }
    rows: list[dict] = []
    for conn_id, conn in CONNECTOR_CATALOG.items():
        acct = accounts.get(conn_id)
        st = stats.get(conn_id, {})
        fail = last_failures.get(conn_id)
        rl = rate_limit_status(user_id, conn_id) if conn.status in {"live", "ingestion_ready"} else None
        rows.append(
            {
                "connector_id": conn_id,
                "implementation_status": conn.status,
                "health": conn.health(),
                "account_status": acct["status"] if acct else "not_connected",
                "last_successful_sync": acct.get("last_ingest_at") if acct else None,
                "ingestion_count": acct.get("ingested_total", 0) if acct else 0,
                "rate_limit": rl,
                "scan_backlog": st.get("backlog", 0),
                "scan_failures": st.get("failed", 0),
                "failure_reason": (acct or {}).get("last_failure_reason") or (fail or {}).get("last_error"),
                "token_expires_at": (acct or {}).get("token_expires_at"),
            }
        )
    return rows


def worker_connector_summary() -> dict:
    stalled = db.fetch_one(
        """
        SELECT count(*)::int AS n FROM scan_jobs
        WHERE status = 'running' AND leased_until IS NOT NULL AND leased_until < now() - interval '5 minutes'
        """,
    )
    dead = db.fetch_one("SELECT count(*)::int AS n FROM scan_jobs WHERE status IN ('failed','dead_letter')")
    retries = db.fetch_one(
        "SELECT count(*)::int AS n FROM scan_jobs WHERE attempts > 1 AND status IN ('queued','running','failed','dead_letter')",
    )
    expiring = db.fetch_one(
        """
        SELECT count(*)::int AS n FROM source_accounts
        WHERE revoked_at IS NULL AND token_expires_at IS NOT NULL AND token_expires_at < now() + interval '7 days'
        """,
    )
    policy_failures = db.fetch_one(
        """
        SELECT count(*)::int AS n FROM source_health_events
        WHERE status IN ('error','policy_denied') AND created_at > now() - interval '24 hours'
        """,
    )
    return {
        "stalled_jobs": stalled["n"] if stalled else 0,
        "dead_letter_jobs": dead["n"] if dead else 0,
        "jobs_with_retries": retries["n"] if retries else 0,
        "tokens_expiring_soon": expiring["n"] if expiring else 0,
        "source_policy_failures_24h": policy_failures["n"] if policy_failures else 0,
    }
