from pathlib import Path

from jobhunt_api import db
from jobhunt_api.services.pipeline import process_scan_job

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "gmail" / "alerts.json"


def _profile():
    return {
        "skills": ["python", "rag", "fastapi"],
        "target_titles": ["GenAI Engineer"],
        "preferred_cities": ["Bengaluru", "remote"],
        "work_mode": "hybrid",
        "min_ctc_inr_annual": 2000000,
        "employment_types": ["full-time"],
        "years_experience": 6,
        "seniority": "mid",
        "verified_facts": [],
        "trigger_rematch": False,
    }


def test_gmail_connect_ingest_inbox(client, auth_a):
    client.put("/api/v1/profile", json=_profile(), headers=auth_a)
    r = client.post("/api/v1/sources/gmail_alerts/connect", headers=auth_a, json={"labels": ["JobAlerts"]})
    assert r.status_code == 200, r.text
    r = client.post("/api/v1/sources/gmail_alerts/ingest", headers=auth_a, json={"fixture_path": str(FIXTURE)})
    assert r.status_code == 200
    job = db.fetch_one("SELECT * FROM scan_jobs WHERE id = %s", (r.json()["scan_job_id"],))
    process_scan_job(dict(job))
    inbox = client.get("/api/v1/inbox", headers=auth_a).json()
    assert any(i.get("company") == "Example Labs" for i in inbox["items"])
    revoke = client.post("/api/v1/sources/gmail_alerts/revoke", headers=auth_a)
    assert revoke.status_code == 200
    assert revoke.json().get("revoke_verified") is True
    blocked = client.post("/api/v1/discovery/scans", headers=auth_a, json={"connector_id": "gmail_alerts"})
    assert blocked.status_code == 409


def test_browser_capture_immutable_idempotency(client, auth_a):
    client.put("/api/v1/profile", json=_profile(), headers=auth_a)
    payload = {
        "source_url": "https://www.linkedin.com/jobs/view/999001",
        "title": "GenAI Engineer",
        "company": "Phase3 Co",
        "location": "Bengaluru",
        "excerpt": "python rag role in Bengaluru",
        "skills": ["python", "rag"],
        "must_have_skills": ["python"],
        "work_mode": "hybrid",
        "extracted_apply_urls": ["https://example.com/apply/999001"],
    }
    r1 = client.post("/api/v1/sources/browser-capture", headers=auth_a, json=payload)
    assert r1.status_code == 200
    job = db.fetch_one("SELECT * FROM scan_jobs WHERE id = %s", (r1.json()["scan_job_id"],))
    process_scan_job(dict(job))
    r2 = client.post("/api/v1/sources/browser-capture", headers=auth_a, json=payload)
    job2 = db.fetch_one("SELECT * FROM scan_jobs WHERE id = %s", (r2.json()["scan_job_id"],))
    out = process_scan_job(dict(job2))
    assert out["created"] == 0


def test_outreach_draft_never_send(client, auth_a):
    client.put("/api/v1/profile", json=_profile(), headers=auth_a)
    r = client.post("/api/v1/sources/gmail_alerts/connect", headers=auth_a, json={"labels": ["JobAlerts"]})
    assert r.status_code == 200
    r = client.post(
        "/api/v1/sources/gmail_alerts/ingest",
        headers=auth_a,
        json={"fixture_path": str(FIXTURE)},
    )
    job = db.fetch_one("SELECT * FROM scan_jobs WHERE id = %s", (r.json()["scan_job_id"],))
    process_scan_job(dict(job))
    item_id = client.get("/api/v1/inbox", headers=auth_a).json()["items"][0]["id"]
    r = client.post(
        "/api/v1/outreach/drafts",
        headers=auth_a,
        json={"inbox_item_id": item_id, "explicit_outreach_request": True},
    )
    assert r.status_code == 200
    draft = r.json()["draft"]
    assert draft["status"] == "candidate_review"
    assert draft.get("sent_at") is None
