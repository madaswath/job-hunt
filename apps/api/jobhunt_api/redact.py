import re

SECRET_RE = re.compile(
    r"(api[_-]?key|secret|token|password|bearer|service.role|refresh_token|access_token|code_verifier|authorization)[=:]\s*\S+",
    re.I,
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
OAUTH_CODE_RE = re.compile(r"(code=|state=)[A-Za-z0-9._~-]+", re.I)
JWTISH_RE = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


def redact(text: str) -> str:
    out = SECRET_RE.sub("[REDACTED]", text)
    out = OAUTH_CODE_RE.sub(r"\1[REDACTED]", out)
    out = JWTISH_RE.sub("[REDACTED_JWT]", out)
    return EMAIL_RE.sub("[REDACTED_EMAIL]", out)


_SENSITIVE_KEYS = frozenset(
    {
        "body",
        "description",
        "excerpt",
        "raw",
        "refresh_token",
        "access_token",
        "token",
        "code",
        "code_verifier",
        "token_ciphertext",
        "email",
        "authorization",
    }
)


def sanitize_for_alert(payload: dict) -> dict:
    clean: dict = {}
    for key, value in payload.items():
        lk = str(key).lower()
        if lk in _SENSITIVE_KEYS:
            clean[key] = "[REDACTED]"
        elif isinstance(value, dict):
            clean[key] = sanitize_for_alert(value)
        elif isinstance(value, str):
            clean[key] = redact(value[:500])
        else:
            clean[key] = value
    return clean
