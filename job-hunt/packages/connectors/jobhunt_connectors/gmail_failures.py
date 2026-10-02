from enum import Enum


class GmailFailureKind(str, Enum):
    AUTH_EXPIRED = "auth_expired"
    RATE_LIMIT = "rate_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    POLICY_VIOLATION = "policy_violation"
    NOT_CONFIGURED = "not_configured"


class GmailIngestError(Exception):
    def __init__(self, kind: GmailFailureKind, message: str, *, retry_after: int | None = None):
        super().__init__(message)
        self.kind = kind
        self.retry_after = retry_after


def classify_http_status(status: int, body: str = "") -> GmailFailureKind:
    if status in {401, 403}:
        return GmailFailureKind.AUTH_EXPIRED
    if status == 429:
        return GmailFailureKind.RATE_LIMIT
    if status == 403 and "quota" in body.lower():
        return GmailFailureKind.QUOTA_EXCEEDED
    if status >= 500:
        return GmailFailureKind.TRANSIENT
    if status >= 400:
        return GmailFailureKind.PERMANENT
    return GmailFailureKind.TRANSIENT
