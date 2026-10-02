from typing import Any

from jobhunt_connectors.browser_capture import BrowserCaptureConnector
from jobhunt_connectors.candidate_import import CandidateImportConnector
from jobhunt_connectors.config import env_flag
from jobhunt_connectors.contract import ConnectorCapabilities, ConnectorPolicy, RawCapture
from jobhunt_connectors.fixture_ats import PublicAtsFixtureConnector
from jobhunt_connectors.gmail_alerts import GmailAlertsConnector


class CatalogConnector:
    def __init__(self, connector_id: str, slug: str, status: str, summary: str, planned_ops: list[str]):
        self.id = connector_id
        self.slug = slug
        self.status = status
        self._summary = summary
        self._ops = planned_ops

    def policy(self) -> ConnectorPolicy:
        return ConnectorPolicy(
            terms_summary=self._summary,
            requires_explicit_consent=True,
            allowed_operations=[],
            forbidden_operations=["ingest", "scrape", "send_email", "submit_application"],
            data_classification="restricted_until_approved",
        )

    def capability_report(self) -> ConnectorCapabilities:
        return ConnectorCapabilities()

    def connect(self, ctx: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(f"{self.id} is {self.status}, not live")

    def ingest(self, ctx: dict[str, Any], query: dict[str, Any]) -> list[RawCapture]:
        raise NotImplementedError(f"{self.id} is {self.status}, not live")

    def normalize(self, raw: RawCapture):
        raise NotImplementedError(f"{self.id} is {self.status}, not live")

    def refresh(self, item) -> dict[str, Any]:
        raise NotImplementedError(f"{self.id} is {self.status}, not live")

    def revoke(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"status": "disconnected"}

    def health(self) -> dict[str, Any]:
        return {"status": self.status}


_LIVE = PublicAtsFixtureConnector()
_CANDIDATE_IMPORT = CandidateImportConnector()

CONNECTOR_CATALOG: dict[str, Any] = {
    _LIVE.id: _LIVE,
    _CANDIDATE_IMPORT.id: _CANDIDATE_IMPORT,
    "naukri": CatalogConnector("naukri", "naukri", "catalog", "Catalog only until an approved integration exists.", []),
    "hirist": CatalogConnector("hirist", "hirist", "catalog", "Catalog only until an approved integration exists.", []),
    "indeed": CatalogConnector("indeed", "indeed", "catalog", "Catalog only until an approved integration exists.", []),
    "linkedin": CatalogConnector("linkedin", "linkedin", "catalog", "Hiring posts stored separately; catalog until approved.", []),
    "instahyre": CatalogConnector("instahyre", "instahyre", "catalog", "Catalog only until an approved integration exists.", []),
    "cutshort": CatalogConnector("cutshort", "cutshort", "catalog", "Catalog only until an approved integration exists.", []),
}

if env_flag("FEATURE_GMAIL_ALERTS", True):
    CONNECTOR_CATALOG["gmail_alerts"] = GmailAlertsConnector()
else:
    CONNECTOR_CATALOG["gmail_alerts"] = CatalogConnector(
        "gmail_alerts",
        "gmail-alerts",
        "planned",
        "Candidate-authorized Gmail alert ingestion (disabled by flag).",
        ["ingest_alerts"],
    )

if env_flag("FEATURE_BROWSER_CAPTURE", True):
    CONNECTOR_CATALOG["browser_capture"] = BrowserCaptureConnector()
else:
    CONNECTOR_CATALOG["browser_capture"] = CatalogConnector(
        "browser_capture",
        "browser-capture",
        "planned",
        "Candidate-initiated capture (disabled by flag).",
        ["browser_capture"],
    )


def get_connector(connector_id: str):
    conn = CONNECTOR_CATALOG.get(connector_id)
    if not conn:
        raise KeyError(connector_id)
    return conn
