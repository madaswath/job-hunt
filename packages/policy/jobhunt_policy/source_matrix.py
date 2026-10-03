from pydantic import BaseModel, Field

CapabilityLabel = str


class SourceCapability(BaseModel):
    source_id: str
    source_class: str
    acquisition_mode: str
    implementation_status: str
    refresh: str
    storage_policy: str
    allowed_operations: list[str] = Field(default_factory=list)
    forbidden_operations: list[str] = Field(default_factory=list)
    capability_label: CapabilityLabel
    notes: str = ""


SOURCE_CAPABILITY_MATRIX: dict[str, SourceCapability] = {
    "greenhouse": SourceCapability(
        source_id="greenhouse",
        source_class="public_ats",
        acquisition_mode="public_job_board_api",
        implementation_status="planned",
        refresh="15-60 minutes",
        storage_policy="normalized posting plus permitted source evidence",
        allowed_operations=["ingest", "normalize", "health"],
        forbidden_operations=["submit_application", "send_email", "scrape_authenticated"],
        capability_label="planned",
        notes="Public Job Board API. Adapter ships in Sprint 1–2.",
    ),
    "lever": SourceCapability(
        source_id="lever",
        source_class="public_ats",
        acquisition_mode="public_postings_api",
        implementation_status="planned",
        refresh="15-60 minutes",
        storage_policy="normalized posting plus permitted source evidence",
        allowed_operations=["ingest", "normalize", "health"],
        forbidden_operations=["submit_application", "send_email", "scrape_authenticated"],
        capability_label="planned",
        notes="Lever Postings API. Adapter ships in Sprint 1–2.",
    ),
    "ashby": SourceCapability(
        source_id="ashby",
        source_class="public_ats",
        acquisition_mode="public_job_posting_api",
        implementation_status="planned",
        refresh="15-60 minutes",
        storage_policy="normalized posting plus permitted source evidence",
        allowed_operations=["ingest", "normalize", "health"],
        forbidden_operations=["submit_application", "send_email", "scrape_authenticated"],
        capability_label="planned",
        notes="Ashby public Job Postings API. Adapter ships in Sprint 1–2.",
    ),
    "public_ats_fixture": SourceCapability(
        source_id="public_ats_fixture",
        source_class="public_ats",
        acquisition_mode="offline_fixture",
        implementation_status="live",
        refresh="on_demand",
        storage_policy="fixture postings into tenant captures until shared catalogue lands",
        allowed_operations=["ingest", "normalize", "health"],
        forbidden_operations=["submit_application", "send_email", "scrape_authenticated"],
        capability_label="live",
    ),
    "gmail_alerts": SourceCapability(
        source_id="gmail_alerts",
        source_class="email_alert",
        acquisition_mode="user_oauth_readonly",
        implementation_status="ingestion_ready",
        refresh="incremental cursor",
        storage_policy="derived job data; minimum necessary email evidence",
        allowed_operations=["connect", "ingest", "revoke", "health"],
        forbidden_operations=["send_email", "submit_application", "scrape_authenticated"],
        capability_label="beta",
        notes="Requires UAT sign-off and FEATURE_EXTERNAL_GMAIL before production_live.",
    ),
    "browser_capture": SourceCapability(
        source_id="browser_capture",
        source_class="user_capture",
        acquisition_mode="candidate_initiated",
        implementation_status="live",
        refresh="on_demand",
        storage_policy="captured page/post evidence private to the user",
        allowed_operations=["ingest", "normalize", "health"],
        forbidden_operations=["submit_application", "send_email", "scrape_authenticated"],
        capability_label="user_capture",
    ),
    "candidate_import": SourceCapability(
        source_id="candidate_import",
        source_class="manual",
        acquisition_mode="url_or_paste",
        implementation_status="live",
        refresh="on_demand",
        storage_policy="archived evidence tied to user and job",
        allowed_operations=["ingest", "normalize", "health"],
        forbidden_operations=["submit_application", "send_email", "scrape_authenticated"],
        capability_label="user_capture",
    ),
    "linkedin": SourceCapability(
        source_id="linkedin",
        source_class="restricted_portal",
        acquisition_mode="recorded_scrape_fixture",
        implementation_status="ingestion_ready",
        refresh="on_demand_demo1",
        storage_policy="normalized listing into shared_jobs + per-user captures; no credentials",
        allowed_operations=["connect", "ingest", "normalize", "revoke", "health"],
        forbidden_operations=[
            "send_email",
            "submit_application",
            "scrape_authenticated",
            "unrestricted_scrape",
            "store_session_cookie",
        ],
        capability_label="beta",
        notes=(
            "Demo 1: recorded LinkedIn-shaped fixtures (FEATURE_LINKEDIN_INGEST). "
            "Unrestricted live scrape remains forbidden; partnership is the long-term path."
        ),
    ),
    "indeed": SourceCapability(
        source_id="indeed",
        source_class="restricted_portal",
        acquisition_mode="partner_api_or_user_capture",
        implementation_status="catalog",
        refresh="not_scheduled",
        storage_policy="do not retain credentials",
        allowed_operations=[],
        forbidden_operations=["ingest", "scrape", "send_email", "submit_application"],
        capability_label="partner_required",
    ),
    "naukri": SourceCapability(
        source_id="naukri",
        source_class="restricted_portal",
        acquisition_mode="email_alert_or_user_capture",
        implementation_status="catalog",
        refresh="not_scheduled",
        storage_policy="do not retain credentials",
        allowed_operations=[],
        forbidden_operations=["ingest", "scrape", "send_email", "submit_application"],
        capability_label="planned",
    ),
}


RESTRICTED_UNAPPROVED_MODES = frozenset({"unrestricted_scrape", "stored_password_login"})


def capability_for(source_id: str) -> SourceCapability:
    if source_id not in SOURCE_CAPABILITY_MATRIX:
        raise KeyError(f"unknown source {source_id}")
    return SOURCE_CAPABILITY_MATRIX[source_id]


def assert_acquisition_allowed(source_id: str, acquisition_mode: str) -> None:
    cap = capability_for(source_id)
    if acquisition_mode in RESTRICTED_UNAPPROVED_MODES:
        raise PermissionError(f"{source_id} forbids {acquisition_mode}")
    if cap.implementation_status in {"catalog", "planned"} and acquisition_mode not in {
        "partner_api_or_user_capture",
        "email_alert_or_user_capture",
        "not_scheduled",
    }:
        raise PermissionError(f"{source_id} is {cap.implementation_status}; {acquisition_mode} is not enabled")
    if cap.capability_label == "partner_required" and acquisition_mode not in {
        "partner_api_or_user_capture",
        "candidate_initiated",
    }:
        raise PermissionError(f"{source_id} requires partner access or candidate-initiated capture")
    if (
        source_id == "linkedin"
        and cap.implementation_status == "ingestion_ready"
        and acquisition_mode
        not in {
            "recorded_scrape_fixture",
            "partner_api_or_user_capture",
            "candidate_initiated",
        }
    ):
        raise PermissionError(f"linkedin Demo 1 only allows recorded fixtures or partner/user-capture modes, not {acquisition_mode}")
