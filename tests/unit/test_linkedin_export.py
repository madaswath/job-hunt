from pathlib import Path

from jobhunt_connectors.linkedin_export import (
    load_export_path,
    load_export_tree,
    select_feed_posts,
    select_recent_jobs,
)
from jobhunt_connectors.catalog import get_connector
from jobhunt_policy.rules import assert_connector_operation


def test_linkedin_export_json_and_csv_caps():
    root = Path(__file__).resolve().parents[2] / "data" / "linkedin-exports"
    bundles = load_export_tree(root)
    assert bundles
    ds = next(b for b in bundles if (b.get("metadata") or {}).get("keyword") == "Data Scientist")
    assert len(ds["jobs"]) >= 2
    assert len(ds["posts"]) >= 1
    jobs = select_recent_jobs(ds["jobs"] * 60, limit=100)
    assert len(jobs) == 100
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
    path = Path(__file__).resolve().parents[2] / "data" / "linkedin-exports" / "Data Scientist" / "jobs.json"
    bundle = load_export_path(path)
    assert bundle["jobs"][0]["title"]
    assert bundle["metadata"]["keyword"] == "Data Scientist"
