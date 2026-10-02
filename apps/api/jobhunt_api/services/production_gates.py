from datetime import datetime, timezone

from fastapi import HTTPException

from jobhunt_api import db
from jobhunt_api.services.signoff_fingerprint import gmail_config_fingerprint
from jobhunt_api.settings import settings


def _invalidate_stale_signoffs(component: str) -> None:
    current = gmail_config_fingerprint() if component == "gmail_alerts" else None
    db.execute(
        """
        UPDATE uat_signoffs SET revoked_at = now(), notes = coalesce(notes, '') || ' [auto-revoked: config drift]'
        WHERE component = %s AND revoked_at IS NULL AND (
          (expires_at IS NOT NULL AND expires_at <= now())
          OR (config_fingerprint IS NOT NULL AND config_fingerprint <> %s)
        )
        """,
        (component, current),
    )


def uat_signoff_active(component: str) -> bool:
    if component == "gmail_alerts":
        _invalidate_stale_signoffs(component)
    row = db.fetch_one(
        """
        SELECT signed_at, expires_at, config_fingerprint FROM uat_signoffs
        WHERE component = %s AND revoked_at IS NULL
        """,
        (component,),
    )
    if not row:
        return False
    if row.get("expires_at") and row["expires_at"] <= datetime.now(timezone.utc):
        revoke_uat_signoff(component, reason="expired")
        return False
    expected = gmail_config_fingerprint() if component == "gmail_alerts" else row.get("config_fingerprint")
    if row.get("config_fingerprint") and expected and row["config_fingerprint"] != expected:
        revoke_uat_signoff(component, reason="config_drift")
        return False
    return True


def external_connector_allowed(connector_id: str) -> bool:
    if connector_id != "gmail_alerts":
        return True
    if not settings.feature_external_gmail:
        return False
    return uat_signoff_active("gmail_alerts")


def assert_external_connector(connector_id: str) -> None:
    if external_connector_allowed(connector_id):
        return
    if connector_id == "gmail_alerts":
        raise HTTPException(
            403,
            "Gmail external enablement blocked until UAT sign-off and FEATURE_EXTERNAL_GMAIL=true",
        )


def gmail_oauth_permitted() -> bool:
    if uat_signoff_active("gmail_alerts"):
        return True
    return settings.allow_gmail_oauth_dev and settings.environment in {"local", "test", "uat"}


def assert_gmail_oauth() -> None:
    if not gmail_oauth_permitted():
        raise HTTPException(403, "Gmail OAuth blocked until UAT sign-off (or ALLOW_GMAIL_OAUTH_DEV in non-prod)")


def gmail_production_live() -> bool:
    return uat_signoff_active("gmail_alerts") and settings.feature_external_gmail


def record_uat_signoff(component: str, signed_by: str, notes: str | None = None) -> dict:
    fingerprint = gmail_config_fingerprint() if component == "gmail_alerts" else None
    ttl_days = settings.uat_signoff_ttl_days
    row = db.fetch_one(
        """
        INSERT INTO uat_signoffs (component, signed_by, notes, revoked_at, config_fingerprint, expires_at)
        VALUES (%s, %s, %s, NULL, %s, now() + (%s || ' days')::interval)
        ON CONFLICT (component) DO UPDATE SET
          signed_by = EXCLUDED.signed_by,
          signed_at = now(),
          notes = EXCLUDED.notes,
          revoked_at = NULL,
          config_fingerprint = EXCLUDED.config_fingerprint,
          expires_at = EXCLUDED.expires_at
        RETURNING component, signed_by, signed_at, notes, config_fingerprint, expires_at
        """,
        (component, signed_by, notes, fingerprint, str(ttl_days)),
    )
    return dict(row)


def revoke_uat_signoff(component: str, *, reason: str | None = None) -> None:
    note = f" [revoked: {reason}]" if reason else ""
    db.execute(
        """
        UPDATE uat_signoffs SET revoked_at = now(), notes = coalesce(notes, '') || %s
        WHERE component = %s AND revoked_at IS NULL
        """,
        (note, component),
    )
