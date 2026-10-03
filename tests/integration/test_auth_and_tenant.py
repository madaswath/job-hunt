import os

import psycopg
from jobhunt_worker.loop import run_once


def test_unauth_rejected(client):
    assert client.get("/api/v1/me").status_code == 401


def test_cross_tenant_inbox_denied(client, auth_a, auth_b):
    profile = {
        "full_name": "A",
        "skills": ["python", "rag", "fastapi"],
        "target_titles": ["GenAI Engineer"],
        "preferred_cities": ["Bengaluru", "remote"],
        "work_mode": "hybrid",
        "min_ctc_inr_annual": 2000000,
        "employment_types": ["full-time"],
        "years_experience": 6,
        "seniority": "mid",
        "verified_facts": [{"kind": "metric", "value": "Built RAG evaluation at current employer"}],
        "trigger_rematch": False,
    }
    assert client.put("/api/v1/profile", json=profile, headers=auth_a).status_code == 200
    assert client.post("/api/v1/discovery/scans", json={"connector_id": "public_ats_fixture"}, headers=auth_a).status_code == 200
    run_once()
    a_inbox = client.get("/api/v1/inbox", headers=auth_a).json()["items"]
    b_inbox = client.get("/api/v1/inbox", headers=auth_b).json()["items"]
    assert b_inbox == []
    if a_inbox:
        item_id = a_inbox[0]["id"]
        assert client.get(f"/api/v1/inbox/{item_id}", headers=auth_b).status_code == 404


def test_rls_denies_authenticated_role(db_ready, client, auth_a):
    client.get("/api/v1/me", headers=auth_a)
    # CI/compose use POSTGRES_USER=jobhunt (superuser). Prefer explicit ADMIN_DATABASE_URL
    # when set; otherwise use DATABASE_URL — do not assume a postgres/postgres role exists.
    admin = os.environ.get("ADMIN_DATABASE_URL") or os.environ["DATABASE_URL"]
    with psycopg.connect(admin) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("DO $$ BEGIN CREATE ROLE authenticated; EXCEPTION WHEN duplicate_object THEN NULL; END $$")
            cur.execute("GRANT USAGE ON SCHEMA public TO authenticated")
            cur.execute("GRANT SELECT ON inbox_items TO authenticated")
            cur.execute("SET ROLE authenticated")
            cur.execute("SELECT count(*) FROM inbox_items")
            count = cur.fetchone()[0]
            cur.execute("RESET ROLE")
    assert count == 0
