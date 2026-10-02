from jobhunt_api import db
from jobhunt_api.services.pipeline import process_scan_job


def _profile():
    return {
        "skills": ["python", "machine learning", "fastapi"],
        "target_titles": ["Machine Learning Engineer"],
        "preferred_cities": ["Bengaluru", "remote"],
        "work_mode": "hybrid",
        "employment_types": ["full-time"],
        "years_experience": 5,
        "seniority": "mid",
        "verified_facts": [],
        "trigger_rematch": False,
    }


def test_candidate_import_queues_and_ingests_job_and_hiring_post(client, auth_a):
    client.put("/api/v1/profile", json=_profile(), headers=auth_a)
    payload = {
        "metadata": {"engine": "browserless_http"},
        "jobs": [
            {
                "job_id": "candidate-import-1",
                "title": "Machine Learning Engineer",
                "company": "Example India",
                "location": "Bengaluru",
                "url": "https://www.linkedin.com/jobs/view/candidate-import-1",
                "description": "Python machine learning FastAPI full-time hybrid Bengaluru",
                "application_urls": ["https://example.in/apply/candidate-import-1"],
            }
        ],
        "posts": [
            {
                "post_id": "candidate-import-post-1",
                "author": "Recruiter",
                "content": "Hiring a Machine Learning Engineer in Bengaluru.",
                "url": "https://www.linkedin.com/feed/update/candidate-import-post-1",
                "emails": ["recruiting@example.in"],
            }
        ],
    }
    queued = client.post("/api/v1/discovery/candidate-imports", json=payload, headers=auth_a)
    assert queued.status_code == 200, queued.text
    job = db.fetch_one("SELECT * FROM scan_jobs WHERE id = %s", (queued.json()["scan_job_id"],))
    process_scan_job(dict(job))
    inbox = client.get("/api/v1/inbox", headers=auth_a)
    assert inbox.status_code == 200
    assert any(item["company"] == "Example India" for item in inbox.json()["items"])


def test_candidate_import_rejects_cookies_and_generated_drafts(client, auth_a):
    for forbidden in ({"session_cookie": "secret"}, {"email_draft": "send this"}):
        response = client.post(
            "/api/v1/discovery/candidate-imports",
            json={"jobs": [{"title": "Engineer", "url": "https://example.test", **forbidden}]},
            headers=auth_a,
        )
        assert response.status_code == 422
