import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from jobhunt_connectors.gmail_alerts import GMAIL_OAUTH_SCOPES

from jobhunt_api import db
from jobhunt_api.services import crypto
from jobhunt_api.services.oauth_security import (
    OAuthSecurityError,
    assert_redirect_allowed,
    filter_allowed_labels,
    generate_pkce,
    sign_state,
    verify_state_signature,
)
from jobhunt_api.settings import settings

GMAIL_SCOPES = GMAIL_OAUTH_SCOPES
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class GmailOAuthError(Exception):
    pass


def oauth_configured() -> bool:
    return bool(settings.gmail_client_id and settings.gmail_client_secret and settings.gmail_redirect_uri)


def start_oauth(user_id: str, labels: list[str]) -> dict[str, str]:
    if not oauth_configured():
        raise GmailOAuthError("Gmail OAuth is not configured")
    assert_redirect_allowed(settings.gmail_redirect_uri)
    labels = filter_allowed_labels(labels)
    verifier, challenge = generate_pkce()
    state = secrets.token_urlsafe(24)
    signature = sign_state(state, user_id, "gmail_alerts")
    db.execute(
        """
        INSERT INTO oauth_states (state, user_id, connector_id, labels, expires_at, code_verifier, state_signature)
        VALUES (%s, %s, 'gmail_alerts', %s, %s, %s, %s)
        """,
        (
            state,
            user_id,
            labels,
            datetime.now(timezone.utc) + timedelta(minutes=15),
            verifier,
            signature,
        ),
    )
    params = {
        "client_id": settings.gmail_client_id,
        "redirect_uri": settings.gmail_redirect_uri,
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return {"auth_url": f"{AUTH_URL}?{urlencode(params)}", "state": state}


def _exchange_code(code: str, code_verifier: str) -> dict[str, Any]:
    assert_redirect_allowed(settings.gmail_redirect_uri)
    with httpx.Client(timeout=30) as client:
        res = client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.gmail_client_id,
                "client_secret": settings.gmail_client_secret,
                "redirect_uri": settings.gmail_redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
        )
    if res.status_code >= 400:
        raise GmailOAuthError(f"token exchange failed: {res.status_code}")
    return res.json()


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    with httpx.Client(timeout=30) as client:
        res = client.post(
            TOKEN_URL,
            data={
                "client_id": settings.gmail_client_id,
                "client_secret": settings.gmail_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    if res.status_code >= 400:
        raise GmailOAuthError(f"refresh failed: {res.status_code}")
    return res.json()


def complete_oauth(state: str, code: str) -> dict[str, Any]:
    row = db.fetch_one(
        "SELECT * FROM oauth_states WHERE state = %s AND expires_at > now()",
        (state,),
    )
    if not row:
        raise GmailOAuthError("invalid or expired OAuth state")
    verify_state_signature(state, row["user_id"], row["connector_id"], row.get("state_signature") or "")
    if not row.get("code_verifier"):
        raise OAuthSecurityError("missing PKCE verifier")
    tokens = _exchange_code(code, row["code_verifier"])
    refresh = tokens.get("refresh_token")
    if not refresh:
        raise GmailOAuthError("Google did not return a refresh token; retry with prompt=consent")
    ciphertext, kek_id = crypto.encrypt_token(refresh)
    expires_in = int(tokens.get("expires_in") or 3600)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    user_id = row["user_id"]
    labels = row["labels"] or []
    db.execute(
        """
        INSERT INTO source_accounts (
          user_id, connector_id, status, scopes, token_ciphertext, kek_id, consent_at, revoked_at,
          token_expires_at, last_refresh_at, health_status
        ) VALUES (%s, 'gmail_alerts', 'connected', %s, %s, %s, now(), NULL, %s, now(), 'oauth_connected')
        ON CONFLICT (user_id, connector_id) DO UPDATE SET
          status = 'connected',
          scopes = EXCLUDED.scopes,
          token_ciphertext = EXCLUDED.token_ciphertext,
          kek_id = EXCLUDED.kek_id,
          consent_at = now(),
          revoked_at = NULL,
          token_expires_at = EXCLUDED.token_expires_at,
          last_refresh_at = now(),
          health_status = 'oauth_connected',
          last_failure_reason = NULL
        """,
        (user_id, labels, ciphertext, kek_id, expires_at),
    )
    db.execute("DELETE FROM oauth_states WHERE state = %s", (state,))
    return {"user_id": user_id, "connector_id": "gmail_alerts", "status": "connected", "token_expires_at": expires_at.isoformat()}


def rotate_stored_refresh_tokens() -> dict[str, int]:
    if not settings.token_encryption_key_previous:
        return {"rotated": 0, "skipped": 0}
    rows = db.fetch_all(
        """
        SELECT user_id, connector_id, token_ciphertext, kek_id
        FROM source_accounts
        WHERE connector_id = 'gmail_alerts' AND token_ciphertext IS NOT NULL AND revoked_at IS NULL
        """,
    )
    rotated = 0
    skipped = 0
    for row in rows:
        updated = crypto.rotate_ciphertext(row["token_ciphertext"], row.get("kek_id"))
        if not updated:
            skipped += 1
            continue
        ciphertext, kek_id = updated
        db.execute(
            """
            UPDATE source_accounts SET token_ciphertext = %s, kek_id = %s, last_refresh_at = now()
            WHERE user_id = %s AND connector_id = %s
            """,
            (ciphertext, kek_id, row["user_id"], row["connector_id"]),
        )
        rotated += 1
    return {"rotated": rotated, "skipped": skipped}


def verify_revoked(user_id: str) -> bool:
    row = db.fetch_one(
        """
        SELECT token_ciphertext, revoked_at, status
        FROM source_accounts WHERE user_id = %s AND connector_id = 'gmail_alerts'
        """,
        (user_id,),
    )
    if not row:
        return True
    return row["revoked_at"] is not None and row["token_ciphertext"] is None and row["status"] == "disconnected"
