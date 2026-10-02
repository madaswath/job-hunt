from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request
from jwt import PyJWKClient

from jobhunt_api import db
from jobhunt_api.settings import settings

_jwks: PyJWKClient | None = None


def _jwks_client() -> PyJWKClient:
    global _jwks
    if _jwks is None:
        _jwks = PyJWKClient(settings.clerk_jwks_url)
    return _jwks


def decode_token(token: str) -> dict[str, Any]:
    if settings.auth_mode == "test":
        return jwt.decode(token, settings.test_jwt_secret, algorithms=["HS256"])
    if not settings.clerk_jwks_url:
        raise HTTPException(503, "Clerk JWKS not configured")
    signing = _jwks_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing.key,
        algorithms=["RS256"],
        issuer=settings.clerk_issuer or None,
        options={"verify_aud": False},
    )


def get_bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    return header.split(" ", 1)[1].strip()


def current_user(request: Request, token: str = Depends(get_bearer)) -> dict[str, str]:
    try:
        payload = decode_token(token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(401, "invalid token") from exc
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "token missing sub")
    email = payload.get("email")
    name = payload.get("name") or payload.get("given_name")
    db.execute(
        """
        INSERT INTO app_users (user_id, clerk_user_id, email, display_name)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET email = COALESCE(EXCLUDED.email, app_users.email),
          display_name = COALESCE(EXCLUDED.display_name, app_users.display_name),
          updated_at = now()
        """,
        (user_id, user_id, email, name),
    )
    request.state.user_id = user_id
    return {"user_id": user_id, "email": email or "", "name": name or ""}
