import hashlib
from typing import Any

from jobhunt_api import db
from jobhunt_api.services import audit, storage_wipe


def export_user_data(user_id: str) -> dict[str, Any]:
    profile = db.fetch_one("SELECT * FROM candidate_profiles WHERE user_id = %s", (user_id,))
    facts = db.fetch_all("SELECT id, kind, value, source, verified, created_at FROM verified_facts WHERE user_id = %s", (user_id,))
    captures = db.fetch_all(
        """
        SELECT id, connector_id, capture_kind, source_url, company, title, captured_at, capture_method
        FROM source_captures WHERE user_id = %s ORDER BY captured_at DESC LIMIT 500
        """,
        (user_id,),
    )
    inbox = db.fetch_all(
        "SELECT id, state, created_at, updated_at FROM inbox_items WHERE user_id = %s ORDER BY created_at DESC LIMIT 200",
        (user_id,),
    )
    accounts = db.fetch_all(
        """
        SELECT connector_id, status, consent_at, revoked_at, last_ingest_at
        FROM source_accounts WHERE user_id = %s
        """,
        (user_id,),
    )
    return {
        "user_id": user_id,
        "profile": profile,
        "verified_facts": facts,
        "source_captures": captures,
        "inbox_items": inbox,
        "source_accounts": accounts,
        "note": "OAuth tokens and ciphertext are never included in exports.",
    }


def _anonymize_audit(user_id: str) -> None:
    token = hashlib.sha256(user_id.encode()).hexdigest()[:32]
    db.execute(
        """
        UPDATE audit_events SET
          user_id = %s,
          metadata = coalesce(metadata, '{}'::jsonb) || jsonb_build_object('anonymized', true)
        WHERE user_id = %s
        """,
        (f"anon_{token}", user_id),
    )


def wipe_user(user_id: str) -> dict[str, Any]:
    paths = storage_wipe.collect_user_storage_paths(user_id)
    storage_result = storage_wipe.delete_storage_paths(paths)
    db.execute("DELETE FROM scan_jobs WHERE user_id = %s", (user_id,))
    db.execute("DELETE FROM outbox_events WHERE user_id = %s", (user_id,))
    db.execute("DELETE FROM oauth_states WHERE user_id = %s", (user_id,))
    db.execute(
        """
        UPDATE source_accounts SET
          token_ciphertext = NULL, kek_id = NULL, token_expires_at = NULL, revoked_at = now(), status = 'disconnected'
        WHERE user_id = %s
        """,
        (user_id,),
    )
    _anonymize_audit(user_id)
    db.execute("DELETE FROM app_users WHERE user_id = %s", (user_id,))
    audit.record(f"anon_{hashlib.sha256(user_id.encode()).hexdigest()[:32]}", "account_wiped", "app_user", user_id, {"cascade": True, "storage": storage_result})
    return {"status": "deleted", "storage": storage_result}


def purge_retention_captures() -> dict[str, int]:
    try:
        row = db.fetch_one(
            """
            WITH doomed AS (
              SELECT sc.id
              FROM source_captures sc
              JOIN source_policies sp ON sp.user_id = sc.user_id AND sp.connector_id = sc.connector_id
              WHERE sc.captured_at < now() - (sp.retention_days || ' days')::interval
                AND NOT EXISTS (SELECT 1 FROM inbox_items i WHERE i.capture_id = sc.id)
            ),
            deleted AS (
              DELETE FROM source_captures WHERE id IN (SELECT id FROM doomed) RETURNING id
            )
            SELECT count(*)::int AS n FROM deleted
            """,
        )
        return {"purged_captures": row["n"] if row else 0}
    except Exception as exc:  # noqa: BLE001
        from jobhunt_api.services.observability import raise_alert

        raise_alert("retention_purge_failed", {"error": str(exc)[:300]}, severity="critical")
        raise
