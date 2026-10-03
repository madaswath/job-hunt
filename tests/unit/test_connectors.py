from pathlib import Path

import pytest
from jobhunt_connectors.catalog import get_connector
from jobhunt_connectors.normalize import content_hash
from jobhunt_policy.rules import assert_connector_operation


def test_fixture_ingest_and_policy():
    conn = get_connector("public_ats_fixture")
    assert conn.status == "live"
    path = Path(__file__).resolve().parents[1] / "fixtures" / "ats" / "postings.json"
    items = conn.ingest({}, {"fixture_path": str(path)})
    assert len(items) >= 2
    norm = conn.normalize(items[0])
    assert norm.content_hash == content_hash(items[0])
    assert_connector_operation("public_ats_fixture", "ingest")


def test_linkedin_demo1_fixture_ingest():
    conn = get_connector("linkedin")
    assert conn.status == "ingestion_ready"
    assert_connector_operation("linkedin", "ingest")
    path = Path(__file__).resolve().parents[1] / "fixtures" / "linkedin" / "postings.json"
    items = conn.ingest({}, {"fixture_path": str(path)})
    assert len(items) >= 3
    assert all(item.connector_id == "linkedin" for item in items)
    assert items[0].capture_method == "linkedin_recorded_scrape"
    with pytest.raises(PermissionError):
        conn.ingest({}, {"fixture_path": str(path), "mode": "unrestricted_scrape"})


def test_catalog_not_live():
    conn = get_connector("naukri")
    assert conn.status == "catalog"
    with pytest.raises(PermissionError):
        assert_connector_operation("naukri", "ingest")
    with pytest.raises(NotImplementedError):
        conn.ingest({}, {})


def test_gmail_alerts_ingestion_ready_narrow_labels():
    conn = get_connector("gmail_alerts")
    assert conn.status == "ingestion_ready"
    assert conn.health().get("production_live") is False
    path = Path(__file__).resolve().parents[1] / "fixtures" / "gmail" / "alerts.json"
    all_items = conn.ingest({}, {"fixture_path": str(path), "labels": ["JobAlerts"]})
    assert len(all_items) == 1
    none = conn.ingest({}, {"fixture_path": str(path), "labels": ["Unrelated"]})
    assert len(none) == 0


def test_browser_capture_live():
    conn = get_connector("browser_capture")
    assert conn.status == "live"
    sample = {
        "source_url": "https://example.com/job/1",
        "title": "Engineer",
        "company": "Co",
        "excerpt": "Role details",
        "extracted_apply_urls": ["https://example.com/apply"],
    }
    items = conn.ingest({}, {"capture": sample})
    assert len(items) == 1
    assert items[0].capture_method == "browser_bookmarklet"
    with pytest.raises(PermissionError):
        conn.normalize(
            items[0].model_copy(update={"capture_method": "scrape_authenticated"}),
        )


def test_candidate_import_normalizes_jobs_and_posts_without_generated_email():
    conn = get_connector("candidate_import")
    assert conn.status == "live"
    assert_connector_operation("candidate_import", "ingest")
    items = conn.ingest(
        {},
        {
            "titles": ["machine learning"],
            "cities": ["bengaluru"],
            "export": {
                "metadata": {"engine": "browserless_http"},
                "jobs": [
                    {
                        "job_id": "123",
                        "title": "Machine Learning Engineer",
                        "company": "Example India",
                        "location": "Bengaluru",
                        "url": "https://www.linkedin.com/jobs/view/123?tracking=discarded",
                        "description": "Python and ML platform role",
                        "application_urls": ["https://company.example/apply/123"],
                    }
                ],
                "posts": [
                    {
                        "post_id": "post-1",
                        "author": "Hiring manager",
                        "content": "Hiring Machine Learning engineers. Contact jobs@example.in",
                        "url": "https://www.linkedin.com/feed/update/post-1",
                        "emails": ["jobs@example.in"],
                        "email_draft": "This field is discarded by the API before connector ingest",
                    }
                ],
            }
        },
    )
    assert len(items) == 2
    assert items[0].capture_method == "candidate_browserless_import"
    assert items[0].source_trusted is False
    assert items[1].capture_kind == "hiring_post"
    assert items[1].extracted_emails == ["jobs@example.in"]
    assert "email_draft" not in items[1].raw["post"]


def test_candidate_import_accepts_a_bounded_hundred_job_batch():
    conn = get_connector("candidate_import")
    jobs = [
        {
            "job_id": f"batch-{n}",
            "title": "Python Engineer",
            "company": f"Example {n}",
            "location": "Bengaluru",
            "url": f"https://www.linkedin.com/jobs/view/batch-{n}",
        }
        for n in range(100)
    ]
    items = conn.ingest({}, {"titles": ["python"], "cities": ["bengaluru"], "export": {"jobs": jobs}})
    assert len(items) == 100
    assert {item.external_id for item in items} == {f"batch-{n}" for n in range(100)}
