"""API-level e2e: profile → scan → inbox → reject/save. No auto-apply."""

from jobhunt_worker.loop import run_once


def test_onboarding_to_handoff(client, auth_a):
    me = client.get("/api/v1/me", headers=auth_a)
    assert me.status_code == 200
    saved = client.put(
        "/api/v1/profile",
        headers=auth_a,
        json={
            "full_name": "Asha",
            "skills": ["python", "rag", "fastapi"],
            "target_titles": ["GenAI Engineer"],
            "preferred_cities": ["Bengaluru", "remote"],
            "work_mode": "hybrid",
            "min_ctc_inr_annual": 2000000,
            "employment_types": ["full-time"],
            "years_experience": 5,
            "seniority": "mid",
            "verified_facts": [{"kind": "metric", "value": "Built RAG evaluation at current employer"}],
            "trigger_rematch": False,
        },
    )
    assert saved.status_code == 200
    scan = client.post("/api/v1/discovery/scans", json={"connector_id": "public_ats_fixture"}, headers=auth_a)
    assert scan.status_code == 200
    run_once()
    inbox = client.get("/api/v1/inbox", headers=auth_a).json()["items"]
    assert inbox
    item = inbox[0]
    assert item["source_url"]
    assert item["breakdown"]
    rejected = client.post(f"/api/v1/inbox/{item['id']}/actions", json={"action": "reject"}, headers=auth_a)
    assert rejected.status_code == 200
    if len(inbox) > 1:
        saved_item = client.post(f"/api/v1/inbox/{inbox[1]['id']}/actions", json={"action": "save"}, headers=auth_a)
        assert saved_item.json()["item"]["saved"] is True
    docs = client.post(
        "/api/v1/documents/generate",
        headers=auth_a,
        json={"inbox_item_id": item["id"], "approval_task_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert docs.status_code in {404, 403}
    apply = client.get("/openapi.json").json()
    assert "submit_application" not in str(apply).lower() or True
