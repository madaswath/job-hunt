from pathlib import Path

from jobhunt_connectors.linkedin_export import (
    load_export_path,
    load_export_tree,
    select_feed_posts,
    select_recent_jobs,
)
from jobhunt_connectors.catalog import get_connector
from jobhunt_policy.rules import assert_connector_operation


def test_browserless_results_json_and_clean_csv_aliases():
    root = Path(__file__).resolve().parents[1] / "fixtures" / "linkedin"
    bundle = load_export_path(root / "results_sample.json")
    assert bundle["metadata"]["keyword"] == "Python Developer"
    assert bundle["jobs"][0]["job_id"] == "4468058393"
    assert bundle["jobs"][0]["employment_type"] == "full-time"
    assert bundle["jobs"][0]["workplace_type"] == "hybrid"
    assert bundle["posts"][0]["emails"] == ["r.yaneza@gravitasgroup.com"]
    assert "email_draft" not in bundle["posts"][0]

    csv_jobs = load_export_path(root / "jobs_clean.csv")
    assert csv_jobs["jobs"][0]["title"] == "Python Developer"
    assert csv_jobs["jobs"][0]["employment_type"] == "full-time"

    csv_posts = load_export_path(root / "recruiter_posts_drafts.csv")
    assert csv_posts["posts"][0]["author"] == "Roxanne Y."
    assert csv_posts["posts"][0]["emails"] == ["r.yaneza@gravitasgroup.com"]
    assert "email_draft" not in str(csv_posts["posts"][0])


def test_linkedin_export_json_and_csv_caps():
    root = Path(__file__).resolve().parents[2] / "data" / "linkedin-exports"
    bundles = load_export_tree(root)
    assert bundles
    ds = next(b for b in bundles if (b.get("metadata") or {}).get("keyword") == "Data Scientist")
    assert len(ds["jobs"]) >= 5
    assert len(ds["posts"]) >= 2
    jobs = select_recent_jobs(ds["jobs"] * 60, limit=100)
    assert len(jobs) == len({j.get("job_id") or j.get("url") for j in ds["jobs"]})
    assert len(jobs) <= 100
    posts = select_feed_posts(
        ds["posts"] + [{"content": "unrelated cooking recipe", "url": "https://example.com/x"}],
        skills=["python", "sql"],
        preferences=["Data Scientist"],
        limit=15,
    )
    assert 1 <= len(posts) <= 15
    assert all("cooking" not in (p.get("content") or "").lower() for p in posts)


def test_linkedin_connector_reads_export_dir():
    conn = get_connector("linkedin")
    assert_connector_operation("linkedin", "ingest")
    root = Path(__file__).resolve().parents[2] / "data" / "linkedin-exports"
    items = conn.ingest(
        {},
        {
            "use_export_dir": True,
            "export_dir": str(root),
            "jobs_per_keyword": 100,
            "posts_limit": 15,
            "skills": ["python", "sql"],
            "preferences": ["Data Scientist"],
        },
    )
    assert len(items) >= 3
    assert any(i.capture_kind == "job_listing" for i in items)
    assert any(i.capture_kind == "hiring_post" for i in items)
    assert all(i.capture_method == "linkedin_scraper_export" for i in items)


def test_load_single_bundle_path():
    path = Path(__file__).resolve().parents[2] / "data" / "linkedin-exports" / "Data Scientist" / "results.json"
    bundle = load_export_path(path)
    assert bundle["jobs"][0]["title"]
    assert bundle["metadata"]["keyword"] == "Data Scientist"
    assert len(bundle["jobs"]) >= 5
    assert all("email_draft" not in p for p in bundle["posts"])
