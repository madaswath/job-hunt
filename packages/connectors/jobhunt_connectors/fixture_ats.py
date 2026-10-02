from pathlib import Path
from typing import Any

from jobhunt_connectors.contract import ConnectorCapabilities, ConnectorPolicy, RawCapture
from jobhunt_connectors.normalize import normalize_capture

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "ats" / "postings.json"


class PublicAtsFixtureConnector:
    id = "public_ats_fixture"
    slug = "public-ats-fixture"
    status = "live"

    def policy(self) -> ConnectorPolicy:
        return ConnectorPolicy(
            terms_summary="Offline public ATS fixtures for Phase 1. No marketplace scraping.",
            requires_explicit_consent=False,
            allowed_operations=["ingest", "normalize", "health"],
            forbidden_operations=["send_email", "submit_application", "scrape_authenticated"],
            data_classification="public_job_data",
        )

    def capability_report(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(can_search=True, capture_kinds=["job_listing", "hiring_post"])

    def connect(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"status": "live", "user_id": ctx.get("user_id")}

    def ingest(self, ctx: dict[str, Any], query: dict[str, Any]) -> list[RawCapture]:
        import json

        path = Path(query.get("fixture_path") or ctx.get("fixture_path") or FIXTURE_PATH)
        items = json.loads(path.read_text())
        captures = [RawCapture.model_validate(item) for item in items]
        cities = {c.lower() for c in query.get("cities") or []}
        titles = {t.lower() for t in query.get("titles") or []}
        filtered = []
        for cap in captures:
            if cities and cap.location and cap.location.lower() not in cities and cap.work_mode != "remote":
                continue
            if titles and cap.title and not any(t in cap.title.lower() for t in titles):
                continue
            filtered.append(cap)
        return filtered

    def normalize(self, raw: RawCapture):
        if "scrape_authenticated" in self.policy().forbidden_operations and raw.capture_method == "scrape_authenticated":
            raise PermissionError("connector policy forbids authenticated scrape")
        return normalize_capture(raw)

    def refresh(self, item) -> dict[str, Any]:
        return {"status": "unchanged", "hash": item.content_hash}

    def revoke(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"status": "disconnected", "user_id": ctx.get("user_id")}

    def health(self) -> dict[str, Any]:
        return {"status": "live", "fixture_exists": FIXTURE_PATH.exists()}
