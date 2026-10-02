from datetime import datetime, timezone

from jobhunt_connectors.gmail_failures import GmailFailureKind

from jobhunt_api import db
from jobhunt_api.services import crypto, gmail_oauth
from jobhunt_api.services.observability import raise_alert


class TokenRefreshFailed(Exception):
    def __init__(self, kind: GmailFailureKind, message: str):
        super().__init__(message)
        self.kind = kind


def handle_refresh_failure(user_id: str, kind: GmailFailureKind, message: str) -> None:
    db.execute(
        """
        UPDATE source_accounts SET
          health_status = 'auth_error',
          last_failure_reason = %s,
          status = CASE WHEN %s = 'auth_expired' THEN 'disconnected' ELSE status END
        WHERE user_id = %s AND connector_id = 'gmail_alerts'
        """,
        (message[:500], kind.value, user_id),
    )
    db.execute(
        """
        INSERT INTO source_health_events (user_id, connector_id, status, payload)
        VALUES (%s, 'gmail_alerts', 'token_refresh_failed', jsonb_build_object('kind', %s, 'message', %s))
        """,
        (user_id, kind.value, message[:500]),
    )
    raise_alert(
        "token_refresh_failed",
        {"user_id": user_id, "kind": kind.value},
        severity="critical" if kind == GmailFailureKind.AUTH_EXPIRED else "warning",
    )
    if kind == GmailFailureKind.AUTH_EXPIRED:
        db.execute(
            """
            UPDATE source_accounts SET token_ciphertext = NULL, kek_id = NULL, revoked_at = now()
            WHERE user_id = %s AND connector_id = 'gmail_alerts'
            """,
            (user_id,),
        )


def get_access_token(user_id: str) -> str:
    row = db.fetch_one(
        """
        SELECT token_ciphertext, kek_id, token_expires_at, status, revoked_at
        FROM source_accounts
        WHERE user_id = %s AND connector_id = 'gmail_alerts'
        """,
        (user_id,),
    )
    if not row or row["revoked_at"] or not row["token_ciphertext"]:
        raise TokenRefreshFailed(GmailFailureKind.AUTH_EXPIRED, "Gmail not connected")
    refresh = crypto.decrypt_token(row["token_ciphertext"], row.get("kek_id"))
    expires_at = row.get("token_expires_at")
    if expires_at and expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
        # Access tokens are short-lived; always refresh when near expiry (< 5 min)
        if (expires_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds() > 300:
            pass
    try:
        tokens = gmail_oauth.refresh_access_token(refresh)
    except gmail_oauth.GmailOAuthError as exc:
        handle_refresh_failure(user_id, GmailFailureKind.AUTH_EXPIRED, str(exc))
        raise TokenRefreshFailed(GmailFailureKind.AUTH_EXPIRED, str(exc)) from exc
    access = tokens.get("access_token")
    if not access:
        handle_refresh_failure(user_id, GmailFailureKind.PERMANENT, "missing access_token")
        raise TokenRefreshFailed(GmailFailureKind.PERMANENT, "missing access_token")
    expires_in = int(tokens.get("expires_in") or 3600)
    db.execute(
        """
        UPDATE source_accounts SET token_expires_at = now() + (%s || ' seconds')::interval, last_refresh_at = now()
        WHERE user_id = %s AND connector_id = 'gmail_alerts'
        """,
        (str(expires_in), user_id),
    )
    return access
