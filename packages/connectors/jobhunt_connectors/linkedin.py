"""LinkedIn jobs connector for Demo 1.

Ingests recorded / fixture LinkedIn-shaped listings into the shared job index
and per-user capture pipeline. Does not perform authenticated LinkedIn login,
cookie replay, or unrestricted live scraping.

When FEATURE_LINKEDIN_SCRAPE is on, optional public URL fetch may be added later
behind assert_acquisition_allowed — unrestricted_scrape remains forbidden.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jobhunt_connectors.config import env_flag
from jobhunt_connectors.contract import ConnectorCapabilities, ConnectorPolicy, RawCapture
from jobhunt_connectors.normalize import normalize_capture

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "linkedin" / "postings.json"

# Bump when ingest behavior changes.
LINKEDIN_CONNECTOR_VERSION = "2026-10-03-demo1-fixture-v1"


class LinkedInJobsConnector:
    id = "linkedin"
    slug = "linkedin"
    status = "ingestion_ready"

    def policy(self) -> ConnectorPolicy:
        return ConnectorPolicy(
            terms_summary=(
                "Demo 1: recorded LinkedIn-shaped job fixtures into the shared index. "
                "No authenticated session, no cookie store, no auto-apply/send. "
                "Live unrestricted scrape remains forbidden; partnership is the long-term path."
            ),
            requires_explicit_consent=True,
            max_requests_per_hour=20,
            allowed_operations=["connect", "ingest", "normalize", "revoke", "health"],
            forbidden_operations=[
                "send_email",
                "submit_application",
                "scrape_authenticated",
                "unrestricted_scrape",
                "store_session_cookie",
            ],
            retention_days=90,
            data_classification="marketplace_derived_demo",
        )

    def capability_report(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(can_search=True, capture_kinds=["job_listing", "hiring_post"])

    def connect(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "connected",
            "method": "demo_consent",
            "user_id": ctx.get("user_id"),
            "scrape_enabled": env_flag("FEATURE_LINKEDIN_SCRAPE", False),
        }

    def ingest(self, ctx: dict[str, Any], query: dict[str, Any]) -> list[RawCapture]:
        from jobhunt_policy.source_matrix import assert_acquisition_allowed

        # Always allow fixture / recorded ingest for Demo 1.
        assert_acquisition_allowed(self.id, "recorded_scrape_fixture")
        if query.get("mode") == "unrestricted_scrape" or query.get("use_live_scrape"):
            assert_acquisition_allowed(self.id, "unrestricted_scrape")

        path = Path(query.get("fixture_path") or ctx.get("fixture_path") or FIXTURE_PATH)
        if not path.exists():
            return []
        items = json.loads(path.read_text())
        titles = {str(t).lower() for t in (query.get("titles") or []) if str(t).strip()}
        cities = {str(c).lower() for c in (query.get("cities") or []) if str(c).strip()}
        captures: list[RawCapture] = []
        for item in items:
            title = str(item.get("title") or "")
            location = str(item.get("location") or "")
            work_mode = str(item.get("work_mode") or "").lower()
            if titles and not any(t in title.lower() for t in titles):
                continue
            if cities and "remote" not in work_mode and location.lower() not in cities and not any(c in location.lower() for c in cities):
                continue
            captures.append(
                RawCapture.model_validate(
                    {
                        **item,
                        "connector_id": self.id,
                        "capture_kind": item.get("capture_kind") or "job_listing",
                        "capture_method": item.get("capture_method") or "linkedin_recorded_scrape",
                        "source_trusted": bool(item.get("source_trusted", False)),
                    }
                )
            )
        return captures

    def normalize(self, raw: RawCapture):
        if raw.capture_method in {"scrape_authenticated", "unrestricted_scrape"}:
            raise PermissionError("linkedin connector forbids authenticated/unrestricted scrape captures")
        return normalize_capture(raw)

    def refresh(self, item) -> dict[str, Any]:
        return {"status": "unchanged", "hash": getattr(item, "content_hash", None)}

    def revoke(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"status": "disconnected", "user_id": ctx.get("user_id")}

    def health(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "connector_version": LINKEDIN_CONNECTOR_VERSION,
            "fixture_exists": FIXTURE_PATH.exists(),
            "feature_linkedin_scrape": env_flag("FEATURE_LINKEDIN_SCRAPE", False),
            "production_live": False,
        }
