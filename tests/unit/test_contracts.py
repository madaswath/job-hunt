import pytest
from jobhunt_connectors.gmail_alerts import GmailIngestRequest
from jobhunt_domain.schemas import JobMatch, JobPosting, SourceDefinition, VerifiedFact
from jobhunt_policy.source_matrix import SOURCE_CAPABILITY_MATRIX, assert_acquisition_allowed, capability_for
from pydantic import ValidationError


def test_canonical_contracts_require_identity_fields():
    posting = JobPosting(
        title="GenAI Engineer",
        company="Example Labs",
        source_id="greenhouse",
        external_job_id="gh-123",
        source_url="https://boards.greenhouse.io/example/jobs/123",
        apply_url="https://boards.greenhouse.io/example/jobs/123",
        content_hash="abc",
    )
    assert posting.title
    source = SourceDefinition(
        source_id="greenhouse",
        source_type="public_ats",
        display_name="Greenhouse",
        acquisition_mode="public_job_board_api",
        implementation_status="planned",
    )
    fact = VerifiedFact(kind="skill", value="Python", verified=True)
    match = JobMatch(
        overall_score=0.8,
        confidence=0.7,
        breakdown=[],
        matched_skills=["python"],
        missing_skills=[],
        unknown_inputs=[],
        reasons_to_apply=["title family"],
        risks=[],
        ranking_version="match_v2",
        job_id="job-1",
        user_id="user-1",
    )
    assert source.source_id == "greenhouse"
    assert fact.verified is True
    assert match.ranking_version == "match_v2"


def test_source_matrix_blocks_unrestricted_scraping():
    assert capability_for("linkedin").capability_label == "partner_required"
    assert capability_for("public_ats_fixture").capability_label == "live"
    with pytest.raises(PermissionError):
        assert_acquisition_allowed("linkedin", "unrestricted_scrape")
    with pytest.raises(PermissionError):
        assert_acquisition_allowed("naukri", "stored_password_login")
    assert "greenhouse" in SOURCE_CAPABILITY_MATRIX
    assert SOURCE_CAPABILITY_MATRIX["greenhouse"].implementation_status == "planned"


def test_gmail_ingest_request_rejects_invalid_limits():
    req = GmailIngestRequest(labels=["JobAlerts"], max_messages=10)
    assert req.labels == ["JobAlerts"]
    with pytest.raises(ValidationError):
        GmailIngestRequest(max_messages=0)
    with pytest.raises(ValidationError):
        GmailIngestRequest(max_messages=500)
