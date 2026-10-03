import json
import uuid
from typing import Any

from fastapi import HTTPException
from jobhunt_connectors.catalog import get_connector
from jobhunt_connectors.config import gmail_allowed_labels
from jobhunt_policy.rules import assert_connector_operation

from jobhunt_api import db
from jobhunt_api.services import audit, crypto, production_gates


def _ensure_policy(user_id: str, connector_id: str) -> None:
    conn = get_connector(connector_id)
    policy = conn.policy()
    db.execute(
        """
        INSERT INTO source_policies (user_id, connector_id, allowed_operations, forbidden_operations, retention_days)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id, connector_id) DO UPDATE SET
          allowed_operations = EXCLUDED.allowed_operations,
          forbidden_operations = EXCLUDED.forbidden_operations,
          retention_days = EXCLUDED.retention_days
        """,
        (
            user_id,
            connector_id,
            policy.allowed_operations,
            policy.forbidden_operations,
            policy.retention_days,
        ),
    )


def list_accounts(user_id: str) -> list[dict]:
    return db.fetch_all(
        """
        SELECT connector_id, status, scopes, consent_at, revoked_at, last_refresh_at,
               health_status, health_payload, last_ingest_at, rate_limit_remaining
        FROM source_accounts
        WHERE user_id = %s
        ORDER BY connector_id
        """,
        (user_id,),
    )


def require_connected(user_id: str, connector_id: str) -> dict:
    row = db.fetch_one(
        """
        SELECT * FROM source_accounts
        WHERE user_id = %s AND connector_id = %s AND revoked_at IS NULL AND status = 'connected'
        """,
        (user_id, connector_id),
    )
    if not row:
        raise HTTPException(409, f"Connect {connector_id} before ingest")
    return row


def assert_ingest_rate(user_id: str, connector_id: str) -> None:
    conn = get_connector(connector_id)
    policy = conn.policy()
    row = db.fetch_one(
        """
        SELECT count(*)::int AS n FROM scan_jobs
        WHERE user_id = %s AND connector_id = %s AND created_at > now() - interval '1 hour'
        """,
        (user_id, connector_id),
    )
    if row and row["n"] >= policy.max_requests_per_hour:
        raise HTTPException(429, "connector rate limit exceeded")


def connect(user_id: str, connector_id: str, body: dict[str, Any]) -> dict:
    assert_connector_operation(connector_id, "connect")
    conn = get_connector(connector_id)
    labels = body.get("labels") or gmail_allowed_labels()
    ctx = {"user_id": user_id, "labels": labels}
    result = conn.connect(ctx)
    token_plain = body.get("refresh_token") or body.get("oauth_refresh_token") or "fixture-consent"
    ciphertext, kek_id = crypto.encrypt_token(token_plain)
    db.execute(
        """
        INSERT INTO source_accounts (user_id, connector_id, status, scopes, token_ciphertext, kek_id, consent_at, revoked_at)
        VALUES (%s, %s, 'connected', %s, %s, %s, now(), NULL)
        ON CONFLICT (user_id, connector_id) DO UPDATE SET
          status = 'connected',
          scopes = EXCLUDED.scopes,
          token_ciphertext = EXCLUDED.token_ciphertext,
          kek_id = EXCLUDED.kek_id,
          consent_at = now(),
          revoked_at = NULL,
          last_refresh_at = now(),
          health_status = 'connected'
        """,
        (user_id, connector_id, labels, ciphertext, kek_id),
    )
    _ensure_policy(user_id, connector_id)
    record_health(user_id, connector_id, "connected", {"labels": labels, **result})
    audit.record(user_id, "source_connected", "source_account", connector_id, {"connector": connector_id, "labels": labels})
    return {"connector_id": connector_id, "status": "connected", "labels": labels, "policy": conn.policy().model_dump()}


def revoke(user_id: str, connector_id: str) -> dict:
    conn = get_connector(connector_id)
    conn.revoke({"user_id": user_id})
    db.execute(
        """
        UPDATE source_accounts SET
          status = 'disconnected',
          token_ciphertext = NULL,
          kek_id = NULL,
          token_expires_at = NULL,
          revoked_at = now(),
          health_status = 'revoked',
          last_failure_reason = NULL
        WHERE user_id = %s AND connector_id = %s
        """,
        (user_id, connector_id),
    )
    db.execute("DELETE FROM oauth_states WHERE user_id = %s AND connector_id = %s", (user_id, connector_id))
    record_health(user_id, connector_id, "revoked", {"tokens_cleared": True})
    audit.record(user_id, "source_revoked", "source_account", connector_id, {"connector": connector_id})
    tok = db.fetch_one(
        "SELECT token_ciphertext, revoked_at, status FROM source_accounts WHERE user_id = %s AND connector_id = %s",
        (user_id, connector_id),
    )
    verified = bool(tok and tok["revoked_at"] and tok["token_ciphertext"] is None and tok["status"] == "disconnected")
    return {"connector_id": connector_id, "status": "disconnected", "revoke_verified": verified}


def record_health(user_id: str, connector_id: str, status: str, payload: dict) -> None:
    db.execute(
        """
        UPDATE source_accounts SET health_status = %s, health_payload = %s::jsonb
        WHERE user_id = %s AND connector_id = %s
        """,
        (status, json.dumps(payload), user_id, connector_id),
    )
    db.execute(
        """
        INSERT INTO source_health_events (user_id, connector_id, status, payload)
        VALUES (%s, %s, %s, %s::jsonb)
        """,
        (user_id, connector_id, status, json.dumps(payload)),
    )


def queue_ingest(user_id: str, connector_id: str, payload: dict[str, Any]) -> dict:
    assert_connector_operation(connector_id, "ingest")
    if connector_id == "gmail_alerts" and payload.get("use_gmail_api"):
        production_gates.assert_external_connector("gmail_alerts")
    if connector_id in {"gmail_alerts", "linkedin"}:
        require_connected(user_id, connector_id)
    assert_ingest_rate(user_id, connector_id)
    account = db.fetch_one(
        "SELECT scopes FROM source_accounts WHERE user_id = %s AND connector_id = %s AND revoked_at IS NULL",
        (user_id, connector_id),
    )
    merged = {**payload, "labels": payload.get("labels") or (account or {}).get("scopes") or gmail_allowed_labels()}
    key = f"{connector_id}:{uuid.uuid4()}"
    row = db.fetch_one(
        """
        INSERT INTO scan_jobs (user_id, connector_id, payload, idempotency_key)
        VALUES (%s, %s, %s::jsonb, %s)
        RETURNING id, status
        """,
        (user_id, connector_id, json.dumps(merged), key),
    )
    audit.record(user_id, "scan_queued", "scan_job", str(row["id"]), {"connector": connector_id})
    return {"scan_job_id": str(row["id"]), "status": row["status"]}


def mark_ingest_complete(user_id: str, connector_id: str, summary: dict) -> None:
    db.execute(
        """
        UPDATE source_accounts SET
          last_ingest_at = now(),
          health_status = 'ok',
          health_payload = %s::jsonb,
          last_failure_reason = NULL,
          ingested_total = ingested_total + %s
        WHERE user_id = %s AND connector_id = %s
        """,
        (json.dumps(summary), int(summary.get("created", 0)), user_id, connector_id),
    )
