import base64
import hashlib
import hmac
import secrets
from urllib.parse import urlparse

from jobhunt_api.settings import settings


class OAuthSecurityError(Exception):
    pass


def generate_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


def _state_secret() -> bytes:
    raw = settings.oauth_state_secret or settings.test_jwt_secret
    return raw.encode()


def sign_state(state: str, user_id: str, connector_id: str) -> str:
    msg = f"{state}|{user_id}|{connector_id}".encode()
    return hmac.new(_state_secret(), msg, hashlib.sha256).hexdigest()


def verify_state_signature(state: str, user_id: str, connector_id: str, signature: str) -> None:
    expected = sign_state(state, user_id, connector_id)
    if not hmac.compare_digest(expected, signature or ""):
        raise OAuthSecurityError("invalid OAuth state signature")


def _normalize_redirect(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"


def assert_redirect_allowed(redirect_uri: str) -> None:
    raw = settings.gmail_redirect_allowlist or ""
    allowlist = [u.strip() for u in raw.split(",") if u.strip()]
    if not allowlist and settings.gmail_redirect_uri:
        allowlist = [settings.gmail_redirect_uri]
    candidate = _normalize_redirect(redirect_uri)
    normalized = {_normalize_redirect(u) for u in allowlist}
    if candidate not in normalized:
        raise OAuthSecurityError("redirect URI not allowlisted")


def filter_allowed_labels(requested: list[str]) -> list[str]:
    allowed = {label.lower() for label in settings.gmail_allowed_labels.split(",") if label.strip()}
    if not allowed:
        return requested
    picked = [label for label in requested if label.lower() in allowed]
    if requested and not picked:
        raise OAuthSecurityError("no Gmail labels in allowlisted scope")
    return picked or list(allowed)


def oauth_state_secret_fingerprint() -> str:
    return hashlib.sha256(_state_secret()).hexdigest()[:12]
