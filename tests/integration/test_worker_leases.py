import inspect
import json
import uuid

from jobhunt_api import db
from jobhunt_api.services.pipeline import claim_outbox, claim_scan_jobs, complete_scan, deliver_outbox
from jobhunt_worker.loop import run_once


def test_lease_and_stuck_recovery(client, auth_a, user_a, db_ready):
    client.get("/api/v1/me", headers=auth_a)
    job_id = str(uuid.uuid4())
    db.execute(
        """
        INSERT INTO scan_jobs (id, user_id, connector_id, payload, idempotency_key, status, leased_until, attempts)
        VALUES (%s, %s, 'public_ats_fixture', '{}'::jsonb, %s, 'running', now() - interval '5 minutes', 1)
        """,
        (job_id, user_a, f"stuck-{job_id}"),
    )
    claimed = claim_scan_jobs()
    assert any(str(r["id"]) == job_id for r in claimed)


def test_outbox_idempotent(client, auth_a, user_a, db_ready):
    client.get("/api/v1/me", headers=auth_a)
    key = f"note-{uuid.uuid4()}"
    db.execute(
        "INSERT INTO outbox_events (user_id, event_type, payload, idempotency_key) VALUES (%s, 'notification', %s::jsonb, %s)",
        (user_a, json.dumps({"title": "Scan complete", "body": "ok"}), key),
    )
    row = db.fetch_one("SELECT * FROM outbox_events WHERE idempotency_key = %s", (key,))
    deliver_outbox(row)
    deliver_outbox({**row, "status": "pending"})
    notes = db.fetch_all("SELECT * FROM notifications WHERE user_id = %s AND title = 'Scan complete'", (user_a,))
    assert len(notes) == 1


def test_scan_pipeline_creates_inbox(client, auth_a, db_ready):
    client.put(
        "/api/v1/profile",
        headers=auth_a,
        json={
            "skills": ["python", "rag", "fastapi", "postgres"],
            "target_titles": ["GenAI Engineer", "Backend Engineer"],
            "preferred_cities": ["Bengaluru", "Hyderabad", "remote"],
            "work_mode": "hybrid",
            "min_ctc_inr_annual": 2000000,
            "employment_types": ["full-time"],
            "years_experience": 6,
            "seniority": "mid",
        },
    )
    queued = client.post("/api/v1/discovery/scans", json={"connector_id": "public_ats_fixture"}, headers=auth_a)
    assert queued.status_code == 200
    run_once()
    inbox = client.get("/api/v1/inbox", headers=auth_a).json()["items"]
    assert inbox
    events = client.get("/api/v1/dashboard", headers=auth_a).json()
    assert events["recommended"]


def test_claim_sql_uses_skip_locked():
    assert "FOR UPDATE SKIP LOCKED" in inspect.getsource(claim_scan_jobs)
    assert "FOR UPDATE SKIP LOCKED" in inspect.getsource(claim_outbox)


def test_unit_of_work_rolls_back(client, auth_a, user_a, db_ready):
    client.get("/api/v1/me", headers=auth_a)
    try:
        with db.unit_of_work():
            db.execute(
                "INSERT INTO notifications (user_id, title, body) VALUES (%s, %s, %s)",
                (user_a, "uow-rollback", "should not persist"),
            )
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    row = db.fetch_one(
        "SELECT id FROM notifications WHERE user_id = %s AND title = %s",
        (user_a, "uow-rollback"),
    )
    assert row is None


def test_exhausted_scan_moves_to_dead_letter(client, auth_a, user_a, db_ready):
    client.get("/api/v1/me", headers=auth_a)
    job_id = str(uuid.uuid4())
    db.execute(
        """
        INSERT INTO scan_jobs (id, user_id, connector_id, payload, idempotency_key, status, attempts, max_attempts)
        VALUES (%s, %s, 'public_ats_fixture', '{}'::jsonb, %s, 'running', 3, 3)
        """,
        (job_id, user_a, f"dl-{job_id}"),
    )
    complete_scan(job_id, False, "boom")
    row = db.fetch_one("SELECT status FROM scan_jobs WHERE id = %s", (job_id,))
    assert row["status"] == "dead_letter"
    claimed = claim_scan_jobs()
    assert all(str(r["id"]) != job_id for r in claimed)
