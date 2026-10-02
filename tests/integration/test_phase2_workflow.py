from jobhunt_worker.loop import run_once


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
        "verified_facts": [{"kind": "metric", "value": "Built RAG evaluation at current employer"}],
        "trigger_rematch": False,
    }


def test_approve_prepare_to_tailored(client, auth_a):
    client.put("/api/v1/profile", json=_profile(), headers=auth_a)
    client.post("/api/v1/discovery/scans", json={"connector_id": "public_ats_fixture"}, headers=auth_a)
    run_once()
    inbox = client.get("/api/v1/inbox", headers=auth_a).json()["items"]
    assert inbox
    item_id = inbox[0]["id"]
    client.post(f"/api/v1/inbox/{item_id}/actions", json={"action": "prepare_application"}, headers=auth_a)
    pending = client.get("/api/v1/approvals", headers=auth_a).json()["pending"]
    prepare = next(t for t in pending if t["kind"] == "prepare_application")
    res = client.post(f"/api/v1/approvals/{prepare['id']}/decide", json={"decision": "approved"}, headers=auth_a)
    assert res.status_code == 200
    detail = client.get(f"/api/v1/inbox/{item_id}", headers=auth_a).json()["item"]
    assert detail["state"] == "tailored"
    docs = client.get("/api/v1/documents", headers=auth_a).json()["items"]
    assert docs
    assert all(d["fact_gate_passed"] for d in docs)


def test_ready_to_apply_requires_draft_approval(client, auth_a):
    client.put("/api/v1/profile", json=_profile(), headers=auth_a)
    client.post("/api/v1/discovery/scans", json={"connector_id": "public_ats_fixture"}, headers=auth_a)
    run_once()
    item_id = client.get("/api/v1/inbox", headers=auth_a).json()["items"][0]["id"]
    client.post(f"/api/v1/inbox/{item_id}/actions", json={"action": "prepare_application"}, headers=auth_a)
    prepare = next(t for t in client.get("/api/v1/approvals", headers=auth_a).json()["pending"] if t["kind"] == "prepare_application")
    client.post(f"/api/v1/approvals/{prepare['id']}/decide", json={"decision": "approved"}, headers=auth_a)
    client.post(f"/api/v1/inbox/{item_id}/actions", json={"action": "request_draft_approval"}, headers=auth_a)
    draft_task = next(t for t in client.get("/api/v1/approvals", headers=auth_a).json()["pending"] if t["kind"] == "approve_draft")
    client.post(f"/api/v1/approvals/{draft_task['id']}/decide", json={"decision": "approved"}, headers=auth_a)
    detail = client.get(f"/api/v1/inbox/{item_id}", headers=auth_a).json()["item"]
    assert detail["state"] == "ready_to_apply"
    handoff = client.post(f"/api/v1/inbox/{item_id}/handoff", headers=auth_a)
    assert handoff.status_code == 200
    assert handoff.json()["apply_urls"]


def test_cross_tenant_documents_denied(client, auth_a, auth_b):
    client.put("/api/v1/profile", json=_profile(), headers=auth_a)
    client.post("/api/v1/discovery/scans", json={"connector_id": "public_ats_fixture"}, headers=auth_a)
    run_once()
    client.post(
        f"/api/v1/inbox/{client.get('/api/v1/inbox', headers=auth_a).json()['items'][0]['id']}/actions",
        json={"action": "prepare_application"},
        headers=auth_a,
    )
    b_docs = client.get("/api/v1/documents", headers=auth_b).json()["items"]
    assert b_docs == []
