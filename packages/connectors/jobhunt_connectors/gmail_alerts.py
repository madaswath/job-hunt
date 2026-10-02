import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from jobhunt_connectors.contract import ConnectorCapabilities, ConnectorPolicy, RawCapture
from jobhunt_connectors.normalize import normalize_capture

# Bump when connector ingest/OAuth behavior changes (invalidates UAT sign-off).
GMAIL_CONNECTOR_VERSION = "2026-04-01-ingestion-ready-v2"

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "gmail" / "alerts.json"
DEFAULT_LABELS = ("JobAlerts", "Jobs")

# Minimum scope: read-only Gmail; ingestion uses label-scoped search only (no send/modify).
GMAIL_OAUTH_SCOPES = ("https://www.googleapis.com/auth/gmail.readonly",)


class GmailIngestRequest(BaseModel):
    use_gmail_api: bool = False
    fixture_path: str | None = None
    labels: list[str] = Field(default_factory=lambda: list(DEFAULT_LABELS))
    max_messages: int = Field(default=25, ge=1, le=100)
    seen_message_ids: list[str] = Field(default_factory=list)

    @field_validator("labels")
    @classmethod
    def _nonempty_labels(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        return cleaned or list(DEFAULT_LABELS)


class GmailAlertsConnector:
    id = "gmail_alerts"
    slug = "gmail-alerts"
    status = "ingestion_ready"

    def policy(self) -> ConnectorPolicy:
        return ConnectorPolicy(
            terms_summary="Candidate-authorized Gmail alert ingestion with narrow label scope. Read-only job-alert messages; never send mail.",
            requires_explicit_consent=True,
            max_requests_per_hour=30,
            allowed_operations=["connect", "ingest", "revoke", "health"],
            forbidden_operations=["send_email", "submit_application", "scrape_authenticated"],
            retention_days=90,
            data_classification="email_alert_derived",
        )

    def capability_report(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(can_ingest_alerts=True, capture_kinds=["email_alert"])

    def connect(self, ctx: dict[str, Any]) -> dict[str, Any]:
        labels = ctx.get("labels") or list(DEFAULT_LABELS)
        return {"status": "connected", "labels": labels, "consent_required": True}

    def ingest(self, ctx: dict[str, Any], query: dict[str, Any]) -> list[RawCapture]:
        req = GmailIngestRequest.model_validate(query or {})
        if req.use_gmail_api or ctx.get("access_token"):
            return self._ingest_gmail_api(ctx, req)
        path = Path(req.fixture_path or ctx.get("fixture_path") or FIXTURE_PATH)
        if not path.exists():
            return []
        items = json.loads(path.read_text())
        allowed = {label.lower() for label in req.labels}
        captures: list[RawCapture] = []
        for item in items:
            labels = {str(x).lower() for x in (item.get("labels") or [])}
            if allowed and labels and not (allowed & labels):
                continue
            captures.append(
                RawCapture.model_validate(
                    {
                        **item,
                        "connector_id": self.id,
                        "capture_kind": "email_alert",
                        "capture_method": "gmail_alert",
                        "source_trusted": True,
                    }
                )
            )
        return captures[: req.max_messages]

    def _ingest_gmail_api(self, ctx: dict[str, Any], req: GmailIngestRequest) -> list[RawCapture]:
        from jobhunt_connectors.gmail_api import fetch_labeled_messages
        from jobhunt_connectors.gmail_failures import GmailFailureKind, GmailIngestError

        token = ctx.get("access_token")
        if not token:
            raise GmailIngestError(GmailFailureKind.NOT_CONFIGURED, "missing access_token")
        items, _page = fetch_labeled_messages(
            token,
            req.labels,
            max_messages=req.max_messages,
            seen_ids=set(req.seen_message_ids),
        )
        captures: list[RawCapture] = []
        for item in items:
            captures.append(
                RawCapture.model_validate(
                    {
                        **item,
                        "connector_id": self.id,
                        "capture_kind": "email_alert",
                        "capture_method": "gmail_api",
                        "source_trusted": True,
                    }
                )
            )
        return captures

    def normalize(self, raw: RawCapture):
        return normalize_capture(raw)

    def refresh(self, item) -> dict[str, Any]:
        return {"status": "unchanged", "hash": item.content_hash}

    def revoke(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"status": "disconnected", "tokens_cleared": True}

    def health(self) -> dict[str, Any]:
        return {
            "status": "ingestion_ready",
            "label": "fixture / live-ingestion ready",
            "production_live": False,
            "connector_version": GMAIL_CONNECTOR_VERSION,
            "oauth_scopes": list(GMAIL_OAUTH_SCOPES),
            "access_mode": "label_scoped_readonly",
            "fixture_exists": FIXTURE_PATH.exists(),
            "mode": "fixture_first",
            "pending_hardening": [
                "uat_suite_evidence",
                "authorized_signoff",
            ],
        }
