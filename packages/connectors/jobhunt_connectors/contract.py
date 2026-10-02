from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

ImplementationStatus = Literal["catalog", "planned", "live", "ingestion_ready", "disconnected"]
CaptureKind = Literal["job_listing", "hiring_post", "email_alert"]


class ConnectorPolicy(BaseModel):
    terms_summary: str
    requires_explicit_consent: bool
    max_requests_per_hour: int = 60
    allowed_operations: list[str]
    forbidden_operations: list[str]
    retention_days: int = 90
    data_classification: str = "public_job_data"


class ConnectorCapabilities(BaseModel):
    can_search: bool = False
    can_ingest_alerts: bool = False
    can_browser_capture: bool = False
    capture_kinds: list[CaptureKind] = Field(default_factory=list)


class RawCapture(BaseModel):
    connector_id: str
    capture_kind: CaptureKind
    external_id: str | None = None
    source_url: str | None = None
    company: str | None = None
    title: str | None = None
    location: str | None = None
    excerpt: str = ""
    description: str = ""
    author: str | None = None
    extracted_emails: list[str] = Field(default_factory=list)
    extracted_apply_urls: list[str] = Field(default_factory=list)
    capture_method: str
    raw: dict[str, Any] = Field(default_factory=dict)
    posted_at: str | None = None
    skills: list[str] = Field(default_factory=list)
    must_have_skills: list[str] = Field(default_factory=list)
    adjacent_skills: list[str] = Field(default_factory=list)
    work_mode: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    ctc_inr_annual_min: float | None = None
    ctc_inr_annual_max: float | None = None
    notice_period_days: int | None = None
    company_type: str | None = None
    source_trusted: bool = True


class NormalizedItem(BaseModel):
    kind: Literal["job", "hiring_post"]
    capture: RawCapture
    canonical_url: str | None = None
    content_hash: str


class SourceConnector(Protocol):
    id: str
    slug: str
    status: ImplementationStatus

    def policy(self) -> ConnectorPolicy: ...
    def capability_report(self) -> ConnectorCapabilities: ...
    def connect(self, ctx: dict[str, Any]) -> dict[str, Any]: ...
    def ingest(self, ctx: dict[str, Any], query: dict[str, Any]) -> list[RawCapture]: ...
    def normalize(self, raw: RawCapture) -> NormalizedItem: ...
    def refresh(self, item: NormalizedItem) -> dict[str, Any]: ...
    def revoke(self, ctx: dict[str, Any]) -> dict[str, Any]: ...
    def health(self) -> dict[str, Any]: ...
