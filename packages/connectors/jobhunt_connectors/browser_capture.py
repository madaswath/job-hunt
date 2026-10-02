from typing import Any

from jobhunt_connectors.contract import ConnectorCapabilities, ConnectorPolicy, RawCapture
from jobhunt_connectors.normalize import normalize_capture


class BrowserCaptureConnector:
    id = "browser_capture"
    slug = "browser-capture"
    status = "live"

    def policy(self) -> ConnectorPolicy:
        return ConnectorPolicy(
            terms_summary="Candidate-initiated capture only. User submits URL, excerpt, and apply links; no automated marketplace scraping.",
            requires_explicit_consent=True,
            max_requests_per_hour=60,
            allowed_operations=["connect", "browser_capture", "ingest", "health"],
            forbidden_operations=["send_email", "submit_application", "scrape_authenticated"],
            retention_days=180,
            data_classification="candidate_initiated_capture",
        )

    def capability_report(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(can_browser_capture=True, capture_kinds=["job_listing", "hiring_post"])

    def connect(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"status": "connected", "method": "bookmarklet_or_extension"}

    def ingest(self, ctx: dict[str, Any], query: dict[str, Any]) -> list[RawCapture]:
        payload = query.get("capture") or query
        if not payload.get("source_url"):
            raise ValueError("source_url required for browser capture")
        kind = payload.get("capture_kind") or ("hiring_post" if payload.get("author") else "job_listing")
        raw = RawCapture.model_validate(
            {
                "connector_id": self.id,
                "capture_kind": kind,
                "source_url": payload["source_url"],
                "company": payload.get("company"),
                "title": payload.get("title"),
                "location": payload.get("location"),
                "excerpt": payload.get("excerpt") or "",
                "description": payload.get("description") or payload.get("excerpt") or "",
                "author": payload.get("author"),
                "extracted_emails": payload.get("extracted_emails") or [],
                "extracted_apply_urls": payload.get("extracted_apply_urls") or [],
                "capture_method": payload.get("capture_method") or "browser_bookmarklet",
                "skills": payload.get("skills") or [],
                "must_have_skills": payload.get("must_have_skills") or [],
                "work_mode": payload.get("work_mode"),
                "source_trusted": True,
                "external_id": payload.get("external_id"),
            }
        )
        return [raw]

    def normalize(self, raw: RawCapture):
        if raw.capture_method == "scrape_authenticated":
            raise PermissionError("browser capture forbids authenticated scrape")
        return normalize_capture(raw)

    def refresh(self, item) -> dict[str, Any]:
        return {"status": "unchanged", "hash": item.content_hash}

    def revoke(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"status": "disconnected"}

    def health(self) -> dict[str, Any]:
        return {"status": "live", "mode": "candidate_initiated"}
